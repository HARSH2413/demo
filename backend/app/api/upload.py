"""
Upload API — stream-hashed file uploads to prevent memory spikes.
"""
import os
import hashlib
import tempfile
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException, BackgroundTasks
from app.services.ingestion_service import IngestionService
from app.core.dependencies import get_ingestion_service
from app.core.config import settings
from app.core.logger import logger

router = APIRouter(prefix="/api/v1/upload", tags=["Document Management"])

TEMP_DIR = os.path.join(tempfile.gettempdir(), "actionrag_uploads")
os.makedirs(TEMP_DIR, exist_ok=True)

# 64KB chunks for stream hashing
HASH_CHUNK_SIZE = 65536
ALLOWED_EXTENSIONS = {".pdf", ".txt", ".docx", ".csv", ".xlsx"}


from app.core.auth import get_current_user, verify_workspace_access, UserContext

@router.post("/")
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    tenant_id: str = Form(...),
    ingestion_service: IngestionService = Depends(get_ingestion_service),
    user: UserContext = Depends(get_current_user),
):
    if not verify_workspace_access(tenant_id, user.user_id):
        raise HTTPException(status_code=403, detail="Access denied to this workspace.")
    original_filename = Path(file.filename or "").name
    safe_ext = Path(original_filename).suffix.lower()
    if not original_filename or safe_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=415, detail="Supported file types: PDF, TXT, DOCX, CSV, XLSX.")

    try:
        # 1. Stream-hash: compute SHA-256 WITHOUT loading entire file into memory
        sha256 = hashlib.sha256()
        max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
        bytes_written = 0

        # Write to a temp file AND hash simultaneously
        fd, temp_path = tempfile.mkstemp(prefix="upload_", suffix=safe_ext, dir=TEMP_DIR)
        os.close(fd)
        with open(temp_path, "wb") as f:
            while True:
                chunk = await file.read(HASH_CHUNK_SIZE)
                if not chunk:
                    break
                bytes_written += len(chunk)
                if bytes_written > max_bytes:
                    raise HTTPException(
                        status_code=413,
                        detail=f"File exceeds the {settings.MAX_UPLOAD_SIZE_MB} MB upload limit.",
                    )
                sha256.update(chunk)
                f.write(chunk)

        file_hash = sha256.hexdigest()

        # 2. Check Database for this exact fingerprint
        if ingestion_service.db.document_exists(file_hash=file_hash, tenant_id=tenant_id):
            os.remove(temp_path)  # Clean up temp file
            raise HTTPException(status_code=409, detail="Exact file content already exists. Duplicate rejected.")

        # 3. Rename temp file to hash-based filename
        file_path = os.path.join(TEMP_DIR, f"{file_hash}{safe_ext}")
        os.rename(temp_path, file_path)

        # 4. Fire and Forget: Send to the Background Worker
        background_tasks.add_task(
            _process_upload_safely,
            ingestion_service,
            file_path=file_path,
            filename=original_filename,
            file_hash=file_hash,
            tenant_id=tenant_id,
        )

        logger.info(f"Upload accepted: '{original_filename}' (hash={file_hash[:12]}...)")

        # 5. Instantly return success to the frontend
        return {
            "status": "processing",
            "message": f"'{original_filename}' is processing in the background.",
        }
    except HTTPException:
        if 'temp_path' in locals() and os.path.exists(temp_path):
            os.remove(temp_path)
        raise
    except Exception as e:
        logger.exception(f"Upload failed for '{original_filename}': {e}")
        if 'temp_path' in locals() and os.path.exists(temp_path):
            os.remove(temp_path)
        raise HTTPException(status_code=500, detail="Unable to process the uploaded file.")


def _process_upload_safely(
    ingestion_service: IngestionService,
    file_path: str,
    filename: str,
    file_hash: str,
    tenant_id: str,
) -> None:
    """Keep an ingestion failure isolated and emit an actionable server log."""
    try:
        ingestion_service.process_file_background(
            file_path=file_path,
            filename=filename,
            file_hash=file_hash,
            tenant_id=tenant_id,
        )
    except Exception:
        # This is deliberately a final boundary around the background task.
        # The service already logs detailed extraction/batch failures.
        logger.exception(f"Background ingestion crashed for '{filename}'")
