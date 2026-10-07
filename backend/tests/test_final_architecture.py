import pytest
from unittest.mock import MagicMock
from app.services.chat_service import ChatService
from app.services.retrieval_engine import RetrievalEngine

@pytest.fixture
def final_architecture_service():
    db = MagicMock()
    lexical_store = MagicMock()
    embedder = MagicMock()
    llm = MagicMock()
    reranker = MagicMock()
    
    # We will instantiate the real RetrievalEngine so we can test the pipeline
    service = ChatService(
        db=db,
        lexical_store=lexical_store,
        embedder=embedder,
        llm=llm,
        reranker=reranker,
        retrieval_top_k=5,
        reranker_top_k=3,
        min_relevance_score=0.15,
        min_relevance_score_low=0.05,
    )
    
    # We will also inject mocks for external network calls, but use the real classes
    return service

def test_full_first_pass_flow_success(final_architecture_service):
    """
    Test the full flow:
    Router (normal) -> Dense + BM25 -> RRF -> Reranker -> Gate (success) -> LLM
    """
    service = final_architecture_service
    
    # Mocks for router bypass
    service.router.route = MagicMock(return_value={"route": "normal", "reasoning": ""})
    service.db.get_chat_history.return_value = []
    
    # Mocks for dense search
    service.embedder.embed_text.return_value = [[0.1, 0.2]]
    service.db.search_dense.return_value = [
        {"document_id": "doc1", "chunk_index": 0, "content": "Dense result", "embedding_score": 0.9}
    ]
    
    # Mocks for lexical search
    service.lexical_store.search.return_value = [
        {"document_id": "doc2", "chunk_index": 0, "content": "BM25 result", "lexical_score": 10.0}
    ]
    
    # Mocks for reranker (RRF merges them, then reranker reranks)
    def mock_rerank(query, documents, top_k):
        # Assign high score to doc1, low to doc2
        for doc in documents:
            if doc["document_id"] == "doc1":
                doc["rerank_score"] = 0.9 # Passes gate
            else:
                doc["rerank_score"] = 0.01
        # Sort by rerank score
        return sorted(documents, key=lambda x: x["rerank_score"], reverse=True)[:top_k]
        
    service.reranker.rerank.side_effect = mock_rerank
    
    # Mocks for LLM
    service.llm.chat_with_messages.return_value = "The answer is based on [E1]."
    
    # Spy on Evidence Engine
    service.evidence_engine.get_doc_relevance_score = MagicMock(side_effect=lambda doc: doc.get("rerank_score", 0.0))
    
    res = service.ask_question("test query", "box_id", "session_id")
    
    # Assertions
    service.router.route.assert_called_once()
    service.db.search_dense.assert_called_once()
    service.lexical_store.search.assert_called_once()
    service.reranker.rerank.assert_called_once()
    
    # Should not have called rescue
    assert "The answer is based on [E1]." in res["answer"]
    assert len(res["citations"]) == 1
    assert res["citations"][0]["document_id"] == "doc1"
    assert len(res["closest_matches"]) == 0
