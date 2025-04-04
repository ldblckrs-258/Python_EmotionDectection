from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, status, Response, Cookie
from typing import List, Optional
from app.services.emotion_detection import detect_emotions
from app.models.detection import DetectionResponse
from app.auth.router import get_current_user, increment_guest_usage, GUEST_COOKIE_NAME
from app.models.user import User
from app.core.config import settings
from app.services.storage import get_detections_by_user, get_detection, delete_detection

router = APIRouter()

@router.post("/detect", response_model=DetectionResponse)
async def detect_emotion(
    response: Response,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    guest_cookie: Optional[str] = Cookie(None, alias=GUEST_COOKIE_NAME)
):
    """
    Upload ảnh để xác định cảm xúc.
    Guest sẽ bị giới hạn số lần sử dụng.
    """
    # Check if user is a guest and has reached usage limit
    if current_user.is_guest:
        # Get current usage and increment it
        new_usage_count = increment_guest_usage(response, guest_cookie)
        
        # Check if user has exceeded the limit
        if new_usage_count > settings.GUEST_MAX_USAGE:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Guest users are limited to {settings.GUEST_MAX_USAGE} detections. Please log in for unlimited use."
            )
    
    try:
        result = await detect_emotions(file, current_user)
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.get("/history", response_model=List[DetectionResponse])
async def get_detection_history(
    current_user: User = Depends(get_current_user),
    skip: int = 0,
    limit: int = 10
):
    """
    Trả về lịch sử sử dụng của người dùng.
    """
    return await get_detections_by_user(current_user.user_id, skip, limit)

@router.get("/history/{detection_id}", response_model=DetectionResponse)
async def get_detection_detail(
    detection_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Lấy chi tiết một detection theo ID.
    """
    detection = await get_detection(detection_id)
    if not detection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Detection with ID {detection_id} not found"
        )
    
    # Check if the detection belongs to the current user
    if detection.user_id != current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to access this detection"
        )
        
    return detection

@router.delete("/history/{detection_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_detection_endpoint(
    detection_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Xóa một detection theo ID.
    """
    detection = await get_detection(detection_id)
    if not detection:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete detection"
        )
    
    # Check if the detection belongs to the current user
    if detection.user_id != current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to delete this detection"
        )
    
    success = await delete_detection(detection_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete detection"
        )
    
    return None
