import pytest
from fastapi import APIRouter, HTTPException
from fastapi.testclient import TestClient

from main import app

# Create a temporary router to inject test endpoints
router = APIRouter()

@router.get("/test-unhandled-exception")
async def unhandled_exception_endpoint():
    raise ValueError("This is a simulated unhandled exception")

@router.get("/test-http-exception")
async def http_exception_endpoint():
    raise HTTPException(status_code=400, detail="This is a known client error")

# Include the router in the app just for testing
app.include_router(router)
client = TestClient(app, raise_server_exceptions=False)


def test_unhandled_exception_returns_500_json():
    """
    Ensures that unexpected application exceptions (like ValueError)
    are caught by the global handler and returned as a JSON 500
    without leaking internal traceback details.
    """
    response = client.get("/test-unhandled-exception")
    assert response.status_code == 500
    assert response.headers["content-type"] == "application/json"
    data = response.json()
    assert data["detail"] == "Internal Server Error"
    assert "ValueError" not in response.text
    assert "simulated unhandled exception" not in response.text


def test_http_exception_returns_original_status_code():
    """
    Ensures that FastAPI's native HTTPException handling is preserved
    and not masked by the new global exception handler.
    """
    response = client.get("/test-http-exception")
    assert response.status_code == 400
    assert response.headers["content-type"] == "application/json"
    data = response.json()
    assert data["detail"] == "This is a known client error"
