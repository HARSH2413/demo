from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import Optional
from app.core.logger import logger
from app.core.auth import get_current_user, UserContext, verify_box_access
from app.services.box_service import BoxService
from app.core.dependencies import get_box_service

router = APIRouter(prefix="/api/v1/boxes", tags=["Boxes"])

class BoxCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None

class BoxUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None

@router.post("/")
def create_box(
    data: BoxCreate,
    box_service: BoxService = Depends(get_box_service),
    user: UserContext = Depends(get_current_user)
):
    try:
        box_name = data.name.strip()
        if not box_name:
            raise HTTPException(status_code=400, detail="Box name cannot be empty.")
            
        box = box_service.create_box(
            name=box_name,
            user_id=user.user_id,
            description=data.description
        )
        return {"status": "success", "data": box}
    except Exception as e:
        error_msg = str(e)
        if "boxes_user_name_lower_idx" in error_msg or "duplicate key" in error_msg or "idx_boxes_user_name_lower" in error_msg:
            raise HTTPException(status_code=409, detail="A box with this name already exists.")
        logger.exception(f"Box creation failed: {e}")
        raise HTTPException(status_code=500, detail="Unable to create box.")

@router.get("/")
def list_boxes(
    box_service: BoxService = Depends(get_box_service),
    user: UserContext = Depends(get_current_user)
):
    try:
        boxes = box_service.list_boxes(user_id=user.user_id)
        return {"status": "success", "data": boxes}
    except Exception as e:
        logger.exception(f"Box listing failed: {e}")
        raise HTTPException(status_code=500, detail="Unable to list boxes.")

@router.get("/{box_id}")
def get_box(
    box_id: str,
    box_service: BoxService = Depends(get_box_service),
    user: UserContext = Depends(get_current_user)
):
    box = box_service.get_box(box_id=box_id, user_id=user.user_id)
    if not box:
        raise HTTPException(status_code=404, detail="Box not found or unauthorized")
    return {"status": "success", "data": box}

@router.patch("/{box_id}")
def update_box(
    box_id: str,
    data: BoxUpdate,
    box_service: BoxService = Depends(get_box_service),
    user: UserContext = Depends(get_current_user)
):
    verify_box_access(box_id, user.user_id)
    
    update_data = data.model_dump(exclude_unset=True)
    if 'name' in update_data and update_data['name'] is not None:
        update_data['name'] = update_data['name'].strip()
        if not update_data['name']:
            raise HTTPException(status_code=400, detail="Box name cannot be empty.")
            
    if not update_data:
        raise HTTPException(status_code=400, detail="No fields provided to update.")
        
    try:
        box = box_service.update_box(box_id=box_id, user_id=user.user_id, data=update_data)
        if not box:
             raise HTTPException(status_code=404, detail="Box not found.")
        return {"status": "success", "data": box}
    except Exception as e:
        error_msg = str(e)
        if "boxes_user_name_lower_idx" in error_msg or "duplicate key" in error_msg or "idx_boxes_user_name_lower" in error_msg:
            raise HTTPException(status_code=409, detail="A box with this name already exists.")
        logger.exception(f"Box update failed: {e}")
        raise HTTPException(status_code=500, detail="Unable to update box.")

@router.delete("/{box_id}")
def delete_box(
    box_id: str,
    box_service: BoxService = Depends(get_box_service),
    user: UserContext = Depends(get_current_user)
):
    verify_box_access(box_id, user.user_id)
    
    try:
        success = box_service.delete_box(box_id=box_id, user_id=user.user_id)
        if not success:
            raise HTTPException(status_code=404, detail="Box not found.")
        return {"status": "success", "message": "Box deleted."}
    except Exception as e:
        logger.exception(f"Box deletion failed: {e}")
        raise HTTPException(status_code=500, detail="Unable to delete box.")
