import pytest
from app.api.upload import ALLOWED_EXTENSIONS
from app.services.ingestion_service import IngestionService

def test_allowed_extensions_consistency():
    # .xls should be rejected everywhere
    assert ".xls" not in ALLOWED_EXTENSIONS
    
    # Test valid extensions
    valid_exts = {".pdf", ".txt", ".docx", ".csv", ".xlsx"}
    assert ALLOWED_EXTENSIONS == valid_exts

def test_ingestion_service_rejects_xls():
    service = IngestionService(db=None, embedder=None)
    
    with pytest.raises(ValueError, match="Unsupported file type"):
        service._extract_text_from_disk("dummy.xls", "dummy.xls")

    try:
        service._extract_text_from_disk("dummy.xlsx", "dummy.xlsx")
    except ValueError as e:
        if "Unsupported file type" in str(e):
            pytest.fail(".xlsx should not raise Unsupported file type")
    except Exception:
        pass # Expected since the file doesn't exist
