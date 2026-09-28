import pytest
import asyncio
import io
import time
from httpx import AsyncClient, ASGITransport
from unittest.mock import MagicMock, patch
from main import app
from app.core.dependencies import get_ingestion_service
from app.core.auth import get_current_user
from app.services.ingestion_service import IngestionService

@pytest.mark.asyncio
async def test_concurrent_uploads_unblocked_health_endpoint():
    mock_ingestion_service = MagicMock(spec=IngestionService)
    mock_ingestion_service.db = MagicMock()
    mock_ingestion_service.db.create_document.return_value = "doc-concurrent"
    
    def override_get_ingestion_service():
        return mock_ingestion_service

    def override_get_current_user():
        user = MagicMock()
        user.user_id = "test-user-id"
        return user

    app.dependency_overrides[get_ingestion_service] = override_get_ingestion_service
    app.dependency_overrides[get_current_user] = override_get_current_user

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        # We will mock verify_box_access to simulate a synchronous delay (e.g. 0.5s network call)
        # to ensure it does not block the event loop because of run_in_threadpool
        with patch('app.api.upload.verify_box_access') as mock_verify:
            def slow_verify(*args, **kwargs):
                time.sleep(0.5)
            mock_verify.side_effect = slow_verify
            
            # Start 5 concurrent uploads
            async def single_upload(i):
                file_content = f"content {i}".encode()
                response = await client.post(
                    "/api/v1/upload/box",
                    data={"box_id": "test-box-id"},
                    files={"file": (f"test{i}.txt", io.BytesIO(file_content), "text/plain")}
                )
                return response
            
            upload_tasks = [single_upload(i) for i in range(5)]
            
            # While uploads are happening, ping the health endpoint
            # We wait 0.1s to ensure the uploads have started and are blocked in slow_verify
            await asyncio.sleep(0.1)
            
            start_time = time.time()
            # If the event loop is blocked, this health check will take ~0.5s to 2.5s
            # If unblocked, it should return instantly.
            health_response = await client.get("/")
            health_duration = time.time() - start_time
            
            # Await the uploads
            upload_responses = await asyncio.gather(*upload_tasks)
            
            success_count = sum(1 for r in upload_responses if r.status_code == 200)
            
            print(f"Health Response Time: {health_duration:.4f}s")
            print(f"Upload Successes: {success_count}/5")
            print(f"Health Status: {health_response.status_code}")
            
            # Since verify_box_access takes 0.5s but runs in threadpool, 
            # the health endpoint should respond almost instantly (<< 0.1s)
            assert health_duration < 0.1, "Health endpoint was blocked!"
            assert success_count == 5, "Not all uploads succeeded"
            assert health_response.status_code == 200
