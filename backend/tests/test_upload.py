import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from fastapi import FastAPI
from app.api.upload import router
from app.core.dependencies import get_ingestion_service
from app.core.auth import get_current_user
from app.services.ingestion_service import IngestionService
import io

app = FastAPI()
app.include_router(router)

mock_ingestion_service = MagicMock(spec=IngestionService)
mock_ingestion_service.db = MagicMock()

def override_get_ingestion_service():
    return mock_ingestion_service

def override_get_current_user():
    user = MagicMock()
    user.user_id = "test-user-id"
    return user

app.dependency_overrides[get_ingestion_service] = override_get_ingestion_service
app.dependency_overrides[get_current_user] = override_get_current_user

client = TestClient(app)

@pytest.fixture(autouse=True)
def reset_mocks():
    mock_ingestion_service.reset_mock()
    mock_ingestion_service.db.reset_mock()

@patch('app.api.upload.verify_box_access')
def test_upload_success(mock_verify):
    mock_verify.return_value = None
    mock_ingestion_service.db.create_document.return_value = "doc-123"

    file_content = b"%PDF-1.4 mock pdf content"
    response = client.post(
        "/api/v1/upload/box",
        data={"box_id": "test-box-id"},
        files={"file": ("test.pdf", io.BytesIO(file_content), "application/pdf")}
    )

    assert response.status_code == 200
    assert response.json() == {
        "status": "processing",
        "message": "'test.pdf' is processing in the background."
    }
    mock_ingestion_service.db.create_document.assert_called_once()
    create_args = mock_ingestion_service.db.create_document.call_args[0][0]
    assert create_args["filename"] == "test.pdf"
    assert create_args["status"] == "processing"

@patch('app.api.upload.verify_box_access')
def test_upload_duplicate_rejection(mock_verify):
    mock_verify.return_value = None
    # Simulate DB unique constraint violation
    mock_ingestion_service.db.create_document.side_effect = Exception("duplicate key value violates unique constraint 'unique_document_hash_per_box'")

    file_content = b"duplicate content"
    response = client.post(
        "/api/v1/upload/box",
        data={"box_id": "test-box-id"},
        files={"file": ("dup.txt", io.BytesIO(file_content), "text/plain")}
    )

    assert response.status_code == 409
    assert "Duplicate rejected" in response.json()["detail"]

@patch('app.api.upload.verify_box_access')
def test_upload_invalid_extension(mock_verify):
    mock_verify.return_value = None
    response = client.post(
        "/api/v1/upload/box",
        data={"box_id": "test-box-id"},
        files={"file": ("test.exe", io.BytesIO(b"MZ..."), "application/x-msdownload")}
    )

    assert response.status_code == 415
    assert "Supported file types" in response.json()["detail"]

@patch('app.api.upload.verify_box_access')
def test_upload_invalid_mime(mock_verify):
    mock_verify.return_value = None
    response = client.post(
        "/api/v1/upload/box",
        data={"box_id": "test-box-id"},
        files={"file": ("test.pdf", io.BytesIO(b"bad content"), "image/jpeg")}
    )

    assert response.status_code == 415
    assert "Invalid file content type" in response.json()["detail"]
