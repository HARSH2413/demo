from unittest.mock import MagicMock
from app.services.chat_service import ChatService
from app.api.chat import ChatRequest

def test_citation_hallucination_ignored():
    """
    Ensures that if the LLM hallucinates an invalid citation [E99],
    it is ignored and not appended to the response citations list.
    """
    # Create mock dependencies
    mock_db = MagicMock()
    class DummyLLM:
        def chat_with_messages(self, messages, temperature):
            return "This is a hallucinated fact [E99]."
    
    mock_llm = DummyLLM()
    mock_embedder = MagicMock()
    mock_reranker = MagicMock()
    
    # Init service
    service = ChatService(
        db=mock_db, 
        embedder=mock_embedder, 
        llm=mock_llm, 
        reranker=mock_reranker
    )
    
    # Mock the retrieved documents (only E1 exists)
    service.retrieval_engine.retrieve_documents = MagicMock(return_value=[
        {
            "id": "chunk-1",
            "document_id": "doc-1",
            "content": "Valid fact",
            "embedding_score": 0.8,
            "filename": "doc1.txt"
        }
    ])
    
    # Force context and no LLM call failure
    result = service.ask_question(
        question="test",
        box_id="test-box",
        session_id="session"
    )
    
    # Check that citations are empty because [E99] does not exist in retrieved docs
    assert len(result["citations"]) == 0, f"Expected 0 citations, got {len(result['citations'])}"
