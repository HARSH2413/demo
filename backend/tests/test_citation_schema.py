import pytest
from app.api.chat import Citation

def test_citation_schema():
    # Test that rich citation validation works
    valid_citation_data = {
        "evidence_id": "ev-123",
        "document_id": "doc-abc",
        "filename": "annual_report.pdf",
        "chunk_index": 5,
        "page_start": 10,
        "page_end": 11,
        "section_title": "Financials",
        "content": "Revenue grew by 20%.",
        "embedding_score": 0.85,
        "lexical_score": 10.2,
        "rrf_score": 0.03,
        "rerank_score": 0.95
    }

    citation = Citation(**valid_citation_data)
    assert citation.evidence_id == "ev-123"
    assert citation.document_id == "doc-abc"
    assert citation.filename == "annual_report.pdf"
    assert citation.chunk_index == 5
    assert citation.page_start == 10
    assert citation.page_end == 11
    assert citation.section_title == "Financials"
    assert citation.content == "Revenue grew by 20%."
    assert citation.embedding_score == 0.85
    assert citation.lexical_score == 10.2
    assert citation.rrf_score == 0.03
    assert citation.rerank_score == 0.95

    # Test minimal validation (optional fields missing)
    minimal_citation = {
        "filename": "simple.txt",
        "content": "Just text."
    }
    
    citation = Citation(**minimal_citation)
    assert citation.filename == "simple.txt"
    assert citation.content == "Just text."
    assert citation.embedding_score is None
    assert citation.rerank_score is None
