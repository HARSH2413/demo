import pytest
from unittest.mock import MagicMock, patch
from app.services.chat_service import ChatService

@pytest.fixture
def chat_service():
    with patch('app.services.chat_service.settings') as mock_settings:
        mock_settings.ANSWER_MIN_RELEVANCE_SCORE = 0.12
        db = MagicMock()
    lexical_store = MagicMock()
    embedder = MagicMock()
    class MockLLM:
        def generate_response(self, *args, **kwargs):
            return "mock"
        def chat_with_messages(self, *args, **kwargs):
            return "The answer is based on [E1]."
            
    llm = MockLLM()
    reranker = MagicMock()
    
    service = ChatService(
        db=db,
        lexical_store=lexical_store,
        embedder=embedder,
        llm=llm,
        reranker=reranker,
        retrieval_top_k=5,
        reranker_top_k=5,
        min_relevance_score=0.15,
        min_relevance_score_low=0.05,
    )
    
    # Mock internal engines for easy testing
    service.retrieval_engine = MagicMock()
    service.evidence_engine = MagicMock()
    service.router = MagicMock()
    service.query_expansion = MagicMock()
    
    yield service

def test_chat_service_first_pass_good(chat_service):
    """
    Test when the first pass yields a good score, rescue is bypassed.
    """
    chat_service.router.route.return_value = {"route": "normal", "reasoning": ""}
    chat_service.db.get_chat_history.return_value = []
    
    mock_doc = {"document_id": "doc1", "content": "hello", "chunk_index": 0, "rerank_score": 0.8}
    chat_service.retrieval_engine.retrieve_documents.return_value = [mock_doc]
    chat_service.evidence_engine.filter_and_expand.return_value = [mock_doc]
    chat_service.evidence_engine.get_doc_relevance_score.return_value = 0.8
    chat_service.evidence_engine.assign_evidence_ids.return_value = [{"evidence_id": "[E1]", **mock_doc}]
    chat_service.evidence_engine.build_context_text.return_value = "Context"
    
    # LLM is MockLLM, returning "The answer is based on [E1]." by default
    
    res = chat_service.ask_question("test question", "box_id", "session_id")
    
    # Assert query expansion was NEVER called (since it's a normal route and first pass was good)
    chat_service.query_expansion.expand.assert_not_called()
    # Assert multi-query rescue was NEVER called
    chat_service.retrieval_engine.retrieve_documents_multi.assert_not_called()
    
    assert res["answer"] == "The answer is based on [E1]."
    assert len(res["citations"]) == 1
    assert len(res["closest_matches"]) == 0

def test_chat_service_rescue_pass_triggered(chat_service):
    """
    Test when first pass is weak, rescue pass is triggered exactly once.
    """
    chat_service.router.route.return_value = {"route": "normal", "reasoning": ""}
    chat_service.db.get_chat_history.return_value = []
    
    # First pass: weak
    mock_doc_weak = {"document_id": "doc1", "content": "hello", "chunk_index": 0, "rerank_score": -1.0}
    chat_service.retrieval_engine.retrieve_documents.return_value = [mock_doc_weak]
    chat_service.evidence_engine.filter_and_expand.side_effect = [[mock_doc_weak], [mock_doc_weak]] # Side effect for first and rescue pass
    chat_service.evidence_engine.get_doc_relevance_score.side_effect = [-1.0, 0.9] # First check, then second check
    
    # Query expansion mock
    chat_service.query_expansion.expand.return_value = {
        "rewritten_query": "expanded test",
        "variants": ["variant 1"]
    }
    
    # Rescue pass: strong
    mock_doc_strong = {"document_id": "doc2", "content": "world", "chunk_index": 0, "rerank_score": 0.9}
    chat_service.retrieval_engine.retrieve_documents_multi.return_value = [mock_doc_strong]
    
    chat_service.evidence_engine.assign_evidence_ids.return_value = [{"evidence_id": "[E1]", **mock_doc_strong}]
    # LLM returns "The answer is based on [E1]."
    chat_service.llm.chat_with_messages = lambda *args, **kwargs: "The answer is [E1]."
    
    res = chat_service.ask_question("test question", "box_id", "session_id")
    
    # Assert expansion was called ONCE during rescue (because route was normal)
    chat_service.query_expansion.expand.assert_called_once_with("test question", [])
    
    # Assert rescue multi-search was called
    chat_service.retrieval_engine.retrieve_documents_multi.assert_called_once_with(
        queries=["expanded test", "variant 1"],
        box_id="box_id",
        reranker_query="expanded test"
    )
    
    assert "The answer is" in res["answer"]
    assert len(res["closest_matches"]) == 0

def test_chat_service_fallback(chat_service):
    """
    Test when both first pass and rescue pass are weak, it returns a fallback and closest_matches.
    """
    chat_service.router.route.return_value = {"route": "normal", "reasoning": ""}
    chat_service.db.get_chat_history.return_value = []
    
    mock_doc_weak = {"document_id": "doc1", "content": "hello", "chunk_index": 0, "rerank_score": -1.0}
    
    chat_service.retrieval_engine.retrieve_documents.return_value = [mock_doc_weak]
    chat_service.retrieval_engine.retrieve_documents_multi.return_value = [mock_doc_weak]
    chat_service.evidence_engine.filter_and_expand.return_value = [mock_doc_weak]
    chat_service.evidence_engine.get_doc_relevance_score.return_value = -1.0 # Always weak
    
    chat_service.query_expansion.expand.return_value = {"rewritten_query": "test", "variants": ["v1"]}
    
    res = chat_service.ask_question("test question", "box_id", "session_id")
    
    assert "could not find the answer" in res["answer"]
    assert len(res["citations"]) == 0
    assert len(res["closest_matches"]) == 1
    assert res["closest_matches"][0]["document_id"] == "doc1"

def test_citation_integrity(chat_service):
    """
    Test that invalid evidence IDs are stripped and valid ones are preserved.
    """
    chat_service.router.route.return_value = {"route": "normal", "reasoning": ""}
    chat_service.db.get_chat_history.return_value = []
    
    mock_doc = {"document_id": "doc1", "content": "hello", "chunk_index": 0, "rerank_score": 0.8}
    chat_service.retrieval_engine.retrieve_documents.return_value = [mock_doc]
    chat_service.evidence_engine.filter_and_expand.return_value = [mock_doc]
    chat_service.evidence_engine.get_doc_relevance_score.return_value = 0.8
    chat_service.evidence_engine.assign_evidence_ids.return_value = [{"evidence_id": "[E1]", **mock_doc}]
    
    # LLM hallucinates [E2] which doesn't exist
    chat_service.llm.chat_with_messages = lambda *args, **kwargs: "Valid [E1] and invalid [E2]."
    
    res = chat_service.ask_question("test question", "box_id", "session_id")
    
    # E2 should be stripped
    assert res["answer"] == "Valid [E1] and invalid ."
    assert len(res["citations"]) == 1
    assert res["citations"][0]["evidence_id"] == "[E1]"
