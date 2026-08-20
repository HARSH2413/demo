"""
Google Drive Adapter — Glean-like integration with recursive crawl.

Supports ALL Google Workspace types:
  - Google Docs    → export as PDF
  - Google Sheets  → export as CSV
  - Google Slides  → export as plain text
  - Native files   → download directly (PDF, DOCX, TXT, CSV, XLSX)

MEMORY SAFE: Large files are streamed to disk in 10MB chunks.
RECURSIVE: Crawls all subfolders automatically.
PAGINATED: Handles folders with 100+ files via pageToken.
"""
import io
import os
import hashlib
from pathlib import Path
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from app.core.logger import logger

SCOPES = ['https://www.googleapis.com/auth/drive.readonly']

BASE_DIR = Path(__file__).resolve().parent.parent.parent
CREDENTIALS_FILE = os.path.join(BASE_DIR, 'google_credentials.json')

import tempfile

TEMP_DIR = os.path.join(tempfile.gettempdir(), "actionrag_uploads")
os.makedirs(TEMP_DIR, exist_ok=True)

# ── Google Workspace MIME types and their export targets ──
GOOGLE_WORKSPACE_EXPORTS = {
    "application/vnd.google-apps.document":     ("application/pdf", ".pdf"),
    "application/vnd.google-apps.spreadsheet":  ("text/csv", ".csv"),
    "application/vnd.google-apps.presentation": ("text/plain", ".txt"),
}

# ── Native file types we can ingest directly ──
NATIVE_SUPPORTED_MIMES = [
    "application/pdf",
    "text/plain",
    "text/csv",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",  # .docx
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",        # .xlsx
    "application/vnd.ms-excel",                                                  # .xls
]

# All supported MIME types (Google Workspace + native)
ALL_SUPPORTED_MIMES = list(GOOGLE_WORKSPACE_EXPORTS.keys()) + NATIVE_SUPPORTED_MIMES


class GoogleDriveAdapter:
    def __init__(self):
        if not os.path.exists(CREDENTIALS_FILE):
            raise FileNotFoundError(f"Missing credentials at: {CREDENTIALS_FILE}")

        self.credentials = Credentials.from_service_account_file(CREDENTIALS_FILE, scopes=SCOPES)
        self.service = build('drive', 'v3', credentials=self.credentials)

    # ── Folder listing ──

    def get_files_in_folder(self, folder_id: str) -> list:
        """Lists all files in a single folder (flat, paginated)."""
        query = f"'{folder_id}' in parents and trashed = false"
        all_files = []
        page_token = None

        while True:
            results = self.service.files().list(
                q=query,
                spaces='drive',
                fields='nextPageToken, files(id, name, mimeType, modifiedTime, size)',
                pageToken=page_token,
                pageSize=100,
            ).execute()

            all_files.extend(results.get('files', []))
            page_token = results.get('nextPageToken')
            if not page_token:
                break

        return all_files

    def get_all_files_recursive(self, folder_id: str) -> list:
        """
        Recursively crawls a folder and all subfolders.

        Returns a flat list of all supported files with their full folder path.
        Handles deeply nested folder structures like Glean does.
        """
        all_files = []
        self._crawl_folder(folder_id, "", all_files)
        logger.info(f"Recursive crawl complete: {len(all_files)} supported files found")
        return all_files

    def _crawl_folder(self, folder_id: str, path_prefix: str, result_list: list):
        """Internal recursive crawler."""
        items = self.get_files_in_folder(folder_id)

        for item in items:
            mime = item.get("mimeType", "")
            name = item.get("name", "")

            if mime == "application/vnd.google-apps.folder":
                # Recurse into subfolder
                subfolder_path = f"{path_prefix}{name}/"
                logger.debug(f"Crawling subfolder: {subfolder_path}")
                self._crawl_folder(item["id"], subfolder_path, result_list)
            elif mime in ALL_SUPPORTED_MIMES:
                # Add the folder path context to the file
                item["folder_path"] = path_prefix
                result_list.append(item)
            else:
                logger.debug(f"Skipping unsupported type: {name} ({mime})")

    # ── File downloads (memory-safe, streamed to disk) ──

    def download_file_to_disk(self, file_id: str, dest_path: str) -> str:
        """Downloads a native file directly to disk. Returns SHA-256 hash."""
        request = self.service.files().get_media(fileId=file_id)
        sha256 = hashlib.sha256()

        with open(dest_path, "wb") as f:
            downloader = MediaIoBaseDownload(f, request, chunksize=10 * 1024 * 1024)
            done = False
            while not done:
                status, done = downloader.next_chunk()
                if status:
                    logger.debug(f"Download progress: {int(status.progress() * 100)}%")

        with open(dest_path, "rb") as f:
            while True:
                chunk = f.read(65536)
                if not chunk:
                    break
                sha256.update(chunk)

        return sha256.hexdigest()

    def export_workspace_file_to_disk(self, file_id: str, export_mime: str, dest_path: str) -> str:
        """
        Exports a Google Workspace file (Docs/Sheets/Slides) to disk.

        Args:
            file_id: Google Drive file ID
            export_mime: Target MIME type (e.g., 'application/pdf', 'text/csv')
            dest_path: Where to save the exported file

        Returns: SHA-256 hash of the exported file
        """
        request = self.service.files().export_media(fileId=file_id, mimeType=export_mime)
        sha256 = hashlib.sha256()

        with open(dest_path, "wb") as f:
            downloader = MediaIoBaseDownload(f, request, chunksize=10 * 1024 * 1024)
            done = False
            while not done:
                status, done = downloader.next_chunk()
                if status:
                    logger.debug(f"Export progress: {int(status.progress() * 100)}%")

        with open(dest_path, "rb") as f:
            while True:
                chunk = f.read(65536)
                if not chunk:
                    break
                sha256.update(chunk)

        return sha256.hexdigest()

    # ── Keep backward compat ──

    def download_file(self, file_id: str) -> bytes:
        """Downloads a file into RAM. Only use for small files (<50MB)."""
        request = self.service.files().get_media(fileId=file_id)
        file_stream = io.BytesIO()
        downloader = MediaIoBaseDownload(file_stream, request)
        done = False
        while done is False:
            status, done = downloader.next_chunk()
        return file_stream.getvalue()

    def export_google_doc_to_disk(self, file_id: str, dest_path: str) -> str:
        """Legacy wrapper — exports Google Doc as PDF to disk."""
        return self.export_workspace_file_to_disk(file_id, "application/pdf", dest_path)