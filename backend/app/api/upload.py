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


from app.core.auth import get_current_user, verify_box_access, UserContext

@router.post("/box")
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    box_id: str = Form(...),
    ingestion_service: IngestionService = Depends(get_ingestion_service),
    user: UserContext = Depends(get_current_user),
):
    verify_box_access(box_id, user.user_id)
    original_filename = Path(file.filename or "").name
    safe_ext = Path(original_filename).suffix.lower()
    if not original_filename or safe_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=415, detail="Supported file types: PDF, TXT, DOCX, CSV, XLSX.")

    valid_mime_types = {
        ".pdf": "application/pdf",
        ".txt": "text/plain",
        ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ".csv": "text/csv",
        ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    }
    expected_mime = valid_mime_types.get(safe_ext)
    # Basic validation: ensure content_type matches the extension conceptually (e.g. not an image)
    if file.content_type and not file.content_type.startswith(("application/", "text/")):
        raise HTTPException(status_code=415, detail="Invalid file content type.")

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

        # 2. Rename temp file to hash-based filename
        file_path = os.path.join(TEMP_DIR, f"{file_hash}{safe_ext}")
        os.replace(temp_path, file_path)

        # 3. Create document record immediately to prevent race conditions and mark as processing
        try:
            document_id = ingestion_service.db.create_document({
                "box_id": box_id,
                "filename": original_filename,
                "file_hash": file_hash,
                "mime_type": file.content_type or expected_mime,
                "status": "processing"
            })
        except Exception as e:
            if os.path.exists(file_path):
                os.remove(file_path)
            if "unique_document_hash_per_box" in str(e) or "duplicate key" in str(e):
                raise HTTPException(status_code=409, detail="Exact file content already exists. Duplicate rejected.")
            raise HTTPException(status_code=500, detail="Failed to initialize document processing.")

        background_tasks.add_task(
            _process_upload_safely,
            ingestion_service,
            file_path=file_path,
            filename=original_filename,
            file_hash=file_hash,
            box_id=box_id,
            document_id=document_id
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
    box_id: str,
    document_id: str,
) -> None:
    """Keep an ingestion failure isolated and emit an actionable server log."""
    try:
        ingestion_service.process_file_background(
            file_path=file_path,
            filename=filename,
            file_hash=file_hash,
            box_id=box_id,
            document_id=document_id,
        )
    except Exception as e:
        # This is deliberately a final boundary around the background task.
        # The service already logs detailed extraction/batch failures.
        logger.exception(f"Background ingestion crashed for '{filename}'")
        try:
            ingestion_service.db.update_document_status(document_id, "failed", str(e))
        except Exception as db_e:
            logger.exception(f"Failed to update document {document_id} status to failed: {db_e}")
