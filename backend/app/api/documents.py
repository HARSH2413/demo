from fastapi import APIRouter, Depends, HTTPException
from app.core.logger import logger
from app.services.ingestion_service import IngestionService
from app.core.dependencies import get_ingestion_service

router = APIRouter(prefix="/api/v1/documents", tags=["Document Management"])

from app.core.auth import get_current_user, verify_box_access, UserContext

@router.delete("/")
def delete_document(
    filename: str,
    box_id: str,
    ingestion_service: IngestionService = Depends(get_ingestion_service),
    user: UserContext = Depends(get_current_user),
):
    if not verify_box_access(box_id, user.user_id):
        raise HTTPException(status_code=403, detail="Access denied to this Box.")
    try:
        success = ingestion_service.delete_file(filename=filename, box_id=box_id)
        if not success:
            raise HTTPException(status_code=404, detail="Document not found.")
        return {"status": "success", "message": f"Successfully deleted {filename} and all its vectors."}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Document deletion failed: {e}")
        raise HTTPException(status_code=500, detail="Unable to delete the document.")
    
@router.get("/")
def get_documents(
    box_id: str,
    ingestion_service: IngestionService = Depends(get_ingestion_service),
    user: UserContext = Depends(get_current_user),
):
    if not verify_box_access(box_id, user.user_id):
        raise HTTPException(status_code=403, detail="Access denied to this Box.")
    try:
        files = ingestion_service.list_files(box_id=box_id)
        documents = ingestion_service.db.get_document_metadata(box_id=box_id)
        return {"status": "success", "files": files, "documents": documents}
    except Exception as e:
        logger.exception(f"Document list failed: {e}")
        raise HTTPException(status_code=500, detail="Unable to load documents.")
