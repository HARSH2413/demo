import pytest
from unittest.mock import MagicMock, patch
from app.services.chat_service import ChatService
from app.utils.citation_validator import split_into_sentences, extract_normalized_numbers, is_factual_sentence

def test_split_sentences():
    text = "Dr. Smith went to the store. He bought 3.5 apples! They cost Rs. 50, e.g. a good deal. No. 1 is best."
    sentences = split_into_sentences(text)
    assert len(sentences) == 4
    assert sentences[0] == "Dr. Smith went to the store."
    assert sentences[1] == "He bought 3.5 apples!"
    assert sentences[2] == "They cost Rs. 50, e.g. a good deal."
    assert sentences[3] == "No. 1 is best."

def test_extract_normalized_numbers():
    text = "Revenue grew by 15 percent to $1,500,000 in Q1. We saw 1/2 of users drop off, but 3.5m stayed."
    nums = extract_normalized_numbers(text)
    assert "15" in nums
    assert "1500000" in nums
    assert "3.5" in nums
    # "1" and "2" from 1/2 should be ignored if they are small integers not tied to %
    assert "1" not in nums
    assert "2" not in nums

def test_is_factual_sentence():
    assert is_factual_sentence("The revenue was $5M.")
    assert not is_factual_sentence("I don't have enough information to answer that.")
    assert not is_factual_sentence("# Revenue Report")
    assert not is_factual_sentence("Hello")

@patch("app.core.config.settings")
def test_citation_firewall(mock_settings):
    mock_settings.CITATION_ENFORCEMENT_MODE = "soft"
    mock_settings.CITATION_SUPPORT_THRESHOLD = 0.3
    mock_settings.FALLBACK_PHRASE = "I could not find the answer to this in the provided company documents."
    
    # Mock dependencies
    mock_llm = MagicMock()
    mock_db = MagicMock()
    mock_reranker = MagicMock()
    
    # Setup mock reranker to return 0.9 for support, 0.1 for unsupported
    def mock_score_pairs(pairs):
        scores = []
        for q, p in pairs:
            if "unrelated" in q.lower():
                scores.append(0.1)
            else:
                scores.append(0.9)
        return scores
    mock_reranker.score_pairs.side_effect = mock_score_pairs
    
    # Init ChatService with mocked dependencies
    service = ChatService(
        db=mock_db, lexical_store=MagicMock(), embedder=MagicMock(), llm=mock_llm,
        reranker=mock_reranker, retrieval_top_k=5, reranker_top_k=5,
        min_relevance_score=0.3, min_relevance_score_low=0.1
    )
    
    docs = [
        {"evidence_id": "[E1]", "document_id": "doc1", "content": "The revenue is 1500000."},
        {"evidence_id": "[E2]", "document_id": "doc2", "content": "The company was founded in 2020."},
        {"evidence_id": "[E3]", "document_id": "doc3", "content": "Our revenue increased by 20 percent this quarter."}
    ]
    fallback = mock_settings.FALLBACK_PHRASE
    
    # (a) Hallucinated [E99] stripped
    ans = "The revenue is good [E1]. We also sell cars [E99]."
    final_ans, cites, unsup, stripped = service._validate_and_build_citations(ans, docs, fallback)
    assert "[E99]" not in final_ans
    assert "[E99]" in stripped
    
    # (b) Valid ID but unrelated claim flagged
    ans = "The revenue is 1500000 [E1]. The company sells unrelated toys [E2]."
    final_ans, cites, unsup, stripped = service._validate_and_build_citations(ans, docs, fallback)
    # Because 'unrelated' triggers score 0.1, it should be unsupported
    assert len(unsup) == 1
    assert "unrelated" in unsup[0].lower()
    
    # (b2) Number mismatch test (Phase 2 constraint)
    # Sentence: "Revenue grew by 15% [E3]." Chunk: "Our revenue increased by 20 percent this quarter."
    # Score is 0.9 (passed reranker), but number check should fail it!
    ans_num = "Revenue grew by 15% [E3]."
    final_ans_num, cites_num, unsup_num, stripped_num = service._validate_and_build_citations(ans_num, docs, fallback)
    assert len(unsup_num) == 1
    assert "15%" in unsup_num[0]
    
    # (c) Uncited answer triggers exactly one retry
    # (We test this via the main ask_question flow, or just simulate the loop)
    # Setup ask_question mock
    mock_llm.chat_with_messages.side_effect = [
        "I know the answer but won't cite.", # First response
        "The revenue is 1500000 [E1]." # Retry response
    ]
    
    # We bypass the retrieval pipeline by mocking it
    service.query_expansion = MagicMock()
    service.query_expansion.expand.return_value = {"rewritten_query": "q", "variants": []}
    service.retrieval_engine = MagicMock()
    service.retrieval_engine.retrieve_documents.return_value = docs
    service.evidence_engine = MagicMock()
    service.evidence_engine.get_doc_relevance_score.return_value = 0.9
    service.evidence_engine.filter_and_expand.return_value = docs
    service.evidence_engine.assign_evidence_ids.return_value = docs
    service.evidence_engine.build_context_text.return_value = "context"
    
    res = service.ask_question("q", "box_id", "session_id")
    assert mock_llm.chat_with_messages.call_count == 2
    assert res["validation_metadata"]["retried"] is True
    assert "[E1]" in res["answer"]
    
    # (d) Fallback phrase after failed retry
    mock_llm.chat_with_messages.side_effect = [
        "I know the answer but won't cite.", # First response
        "I still won't cite." # Retry response
    ]
    res2 = service.ask_question("q", "box_id", "session_id")
    assert res2["answer"] == fallback
    
    # (e) "I don't have enough information" answer is not flagged
    mock_llm.chat_with_messages.side_effect = [
        fallback # First response
    ]
    res3 = service.ask_question("q", "box_id", "session_id")
    assert res3["answer"] == fallback
    assert res3["validation_metadata"]["retried"] is False
