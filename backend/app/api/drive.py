"""
Google Drive API — Glean-like integration with recursive folder sync.

Supports ALL Google Workspace types + native files:
  Google Docs → PDF | Google Sheets → CSV | Google Slides → Text
  Native: PDF, DOCX, TXT, CSV, XLSX

Features:
  - Recursive subfolder crawling
  - Smart export per file type
  - Memory-safe disk streaming for large files
  - Hash-based deduplication
"""
import os
import hashlib
import httpx
from fastapi import APIRouter, Form, Depends, HTTPException, BackgroundTasks
from app.services.ingestion_service import IngestionService
from app.core.dependencies import get_ingestion_service
from app.core.config import settings
from app.core.logger import logger
from app.infrastructure.google_drive_adapter import (
    GoogleDriveAdapter,
    GOOGLE_WORKSPACE_EXPORTS,
    ALL_SUPPORTED_MIMES,
)

router = APIRouter(prefix="/api/v1/drive", tags=["Google Drive Integration"])

import tempfile

TEMP_DIR = os.path.join(tempfile.gettempdir(), "actionrag_uploads")
os.makedirs(TEMP_DIR, exist_ok=True)


def _clean_drive_filename(raw_name: str, mime_type: str) -> str:
    """
    Cleans Google Drive filenames and assigns correct extensions.

    Google appends suffixes like ' - Google Docs' to names.
    For Workspace types, we strip the suffix and use the export extension.
    """
    # Strip Google's type suffixes
    for suffix in [" - Google Docs", " - Google Sheets", " - Google Slides",
                   " - Google Forms", " - Google Drawings"]:
        if raw_name.endswith(suffix):
            raw_name = raw_name[:-len(suffix)]

    # For Google Workspace types → use the export extension
    if mime_type in GOOGLE_WORKSPACE_EXPORTS:
        _, ext = GOOGLE_WORKSPACE_EXPORTS[mime_type]
        base = os.path.splitext(raw_name)[0]
        return f"{base}{ext}"

    return raw_name


def _get_safe_ext(file_name: str, mime_type: str) -> str:
    """Returns a safe file extension for any supported MIME type."""
    if mime_type in GOOGLE_WORKSPACE_EXPORTS:
        _, ext = GOOGLE_WORKSPACE_EXPORTS[mime_type]
        return ext

    ext = os.path.splitext(file_name)[1]
    if ext and len(ext) <= 10:
        return ext
    return ".pdf"  # fallback


# ==========================================
# 🚀 ENDPOINT: SINGLE FILE IMPORT (user token)
# ==========================================
from app.core.auth import get_current_user, verify_workspace_access, UserContext

@router.post("/process")
async def process_drive_file(
    background_tasks: BackgroundTasks,
    file_id: str = Form(...),
    file_name: str = Form(...),
    access_token: str = Form(...),
    tenant_id: str = Form(...),
    ingestion_service: IngestionService = Depends(get_ingestion_service),
    user: UserContext = Depends(get_current_user),
):
    """Endpoint for importing a specific, single file using user's access token."""
    if not verify_workspace_access(tenant_id, user.user_id):
        raise HTTPException(status_code=403, detail="Access denied to this workspace.")
    try:
        headers = {"Authorization": f"Bearer {access_token}"}

        async with httpx.AsyncClient(timeout=settings.REQUEST_TIMEOUT) as client:
            meta_url = f"https://www.googleapis.com/drive/v3/files/{file_id}?fields=mimeType"
            meta_response = await client.get(meta_url, headers=headers)

            if meta_response.status_code != 200:
                raise HTTPException(status_code=400, detail="Could not access Google Drive file metadata.")

            mime_type = meta_response.json().get("mimeType", "")

            if mime_type.startswith("application/vnd.google-apps."):
                drive_url = f"https://www.googleapis.com/drive/v3/files/{file_id}/export?mimeType=application/pdf"
                safe_ext = ".pdf"
            else:
                drive_url = f"https://www.googleapis.com/drive/v3/files/{file_id}?alt=media"
                safe_ext = os.path.splitext(file_name)[1]
                if not safe_ext:
                    safe_ext = ".pdf"

            response = await client.get(drive_url, headers=headers)

        if response.status_code != 200:
            raise HTTPException(status_code=400, detail="Failed to download file from Google Drive.")

        file_bytes = response.content
        file_hash = hashlib.sha256(file_bytes).hexdigest()

        if ingestion_service.db.document_exists(file_hash=file_hash, tenant_id=tenant_id):
            raise HTTPException(status_code=409, detail="Exact file content already exists in the database.")

        file_path = os.path.join(TEMP_DIR, f"{file_hash}{safe_ext}")
        with open(file_path, "wb") as f:
            f.write(file_bytes)

        final_filename = _clean_drive_filename(file_name, mime_type)

        background_tasks.add_task(
            ingestion_service.process_file_background,
            file_path=file_path,
            filename=final_filename,
            file_hash=file_hash,
            tenant_id=tenant_id,
        )

        logger.info(f"Drive file accepted: '{final_filename}' (hash={file_hash[:12]}...)")

        return {
            "status": "processing",
            "message": f"Google Drive file '{final_filename}' is downloading and indexing in the background.",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Drive processing failed for '{file_name}': {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==========================================
# 🚀 ENDPOINT: RECURSIVE FOLDER SYNC (service account)
# ==========================================
@router.post("/sync")
async def sync_google_drive_folder(
    background_tasks: BackgroundTasks,
    tenant_id: str = Form(...),
    force_resync: bool = Form(False),
    ingestion_service: IngestionService = Depends(get_ingestion_service),
    user: UserContext = Depends(get_current_user),
):
    """
    One-click sync — recursively crawls GOOGLE_DRIVE_FOLDER_ID.
    Handles ALL Google Workspace types + native files.

    Set force_resync=true to delete and re-process all files (fixes partial ingestion from crashes).
    """
    if not verify_workspace_access(tenant_id, user.user_id):
        raise HTTPException(status_code=403, detail="Access denied to this workspace.")
        
    folder_id = settings.GOOGLE_DRIVE_FOLDER_ID
    if not folder_id:
        raise HTTPException(status_code=400, detail="GOOGLE_DRIVE_FOLDER_ID not set in .env")

    try:
        # 1. Recursive crawl (subfolders included)
        drive_adapter = GoogleDriveAdapter()
        drive_files = drive_adapter.get_all_files_recursive(folder_id)

        if not drive_files:
            return {
                "status": "success",
                "message": "No supported files found in the shared folder (including subfolders).",
                "queued_files": [],
                "total_found": 0,
            }

        # 2. Get what we already have in Supabase
        existing_filenames = ingestion_service.list_files(tenant_id=tenant_id)

        queued_files = []
        skipped_files = []

        # 3. Compare and queue missing files
        for drive_file in drive_files:
            file_name = drive_file.get("name", "")
            file_id = drive_file.get("id", "")
            mime_type = drive_file.get("mimeType", "")
            folder_path = drive_file.get("folder_path", "")

            # Clean filename (strip Google suffixes, fix extension)
            final_filename = _clean_drive_filename(file_name, mime_type)

            # Prefix with folder path for context (e.g., "HR/Policies/leave_policy.pdf")
            if folder_path:
                display_name = f"{folder_path}{final_filename}"
            else:
                display_name = final_filename

            # Skip if already in Supabase (unless force re-sync)
            if not force_resync and (final_filename in existing_filenames or display_name in existing_filenames):
                skipped_files.append(display_name)
                continue

            # Force re-sync: delete old chunks first
            if force_resync and (final_filename in existing_filenames or display_name in existing_filenames):
                try:
                    ingestion_service.delete_file(filename=final_filename, tenant_id=tenant_id)
                    ingestion_service.delete_file(filename=display_name, tenant_id=tenant_id)
                    logger.info(f"Force re-sync: deleted old chunks for '{display_name}'")
                except Exception as e:
                    logger.warning(f"Failed to delete old chunks for '{display_name}': {e}")

            # Queue for background ingestion
            queued_files.append(display_name)
            background_tasks.add_task(
                _sync_single_file,
                drive_adapter=drive_adapter,
                file_id=file_id,
                file_name=display_name,
                mime_type=mime_type,
                tenant_id=tenant_id,
                ingestion_service=ingestion_service,
            )

        logger.info(
            f"Drive Sync: {len(drive_files)} files found | "
            f"{len(queued_files)} new | {len(skipped_files)} already synced"
        )

        return {
            "status": "success",
            "message": f"Sync started. {len(queued_files)} new files queued from {len(drive_files)} total found.",
            "queued_files": queued_files,
            "total_found": len(drive_files),
            "already_synced": len(skipped_files),
        }

    except FileNotFoundError as e:
        logger.error(f"Drive Sync failed — missing credentials: {e}")
        raise HTTPException(status_code=500, detail="Google Drive service account credentials not configured.")
    except Exception as e:
        logger.error(f"Drive Sync failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==========================================
# Background worker — routes each file type to the right handler
# ==========================================
def _sync_single_file(
    drive_adapter: GoogleDriveAdapter,
    file_id: str,
    file_name: str,
    mime_type: str,
    tenant_id: str,
    ingestion_service: IngestionService,
):
    """
    Background task: download/export a file and ingest it.

    Smart routing per file type:
      Google Docs    → export as PDF
      Google Sheets  → export as CSV (→ ingested as text)
      Google Slides  → export as plain text
      Native files   → download directly
    """
    safe_ext = _get_safe_ext(file_name, mime_type)
    temp_download_path = os.path.join(TEMP_DIR, f"drive_dl_{file_id}{safe_ext}")

    try:
        # Route to the correct download/export method
        if mime_type in GOOGLE_WORKSPACE_EXPORTS:
            export_mime, _ = GOOGLE_WORKSPACE_EXPORTS[mime_type]
            file_hash = drive_adapter.export_workspace_file_to_disk(
                file_id, export_mime, temp_download_path
            )
            logger.info(f"Exported '{file_name}' as {export_mime}")
        else:
            file_hash = drive_adapter.download_file_to_disk(file_id, temp_download_path)

        # Skip if already exists (hash-based dedup)
        if ingestion_service.db.document_exists(file_hash=file_hash, tenant_id=tenant_id):
            logger.info(f"Skipped '{file_name}' — duplicate hash")
            if os.path.exists(temp_download_path):
                os.remove(temp_download_path)
            return

        # Rename to hash-based filename for processing
        file_path = os.path.join(TEMP_DIR, f"{file_hash}{safe_ext}")
        os.rename(temp_download_path, file_path)

        ingestion_service.process_file_background(
            file_path=file_path,
            filename=file_name,
            file_hash=file_hash,
            tenant_id=tenant_id,
        )
        logger.info(f"Auto-sync ingested: '{file_name}'")

    except Exception as e:
        logger.error(f"Background sync failed for '{file_name}': {e}")
        if os.path.exists(temp_download_path):
            os.remove(temp_download_path)