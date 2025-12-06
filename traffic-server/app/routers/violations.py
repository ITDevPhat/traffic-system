from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select
from app.core.database import get_session
from app.models.violation import Violation
from typing import Optional

router = APIRouter()


@router.get("/")
async def get_violations(
    skip: int = Query(0, ge=0, description="Số record bỏ qua"),
    limit: int = Query(100, ge=1, le=1000, description="Số record tối đa trả về"),
    violation_type: Optional[str] = Query(None, description="Lọc theo loại vi phạm"),
    video_job_id: Optional[int] = Query(None, description="Lọc theo video job ID"),
    session: Session = Depends(get_session)
):
    """
    Lấy danh sách các vi phạm đã phát hiện.
    
    Args:
        skip: Số record bỏ qua (pagination)
        limit: Số record tối đa trả về
        violation_type: Lọc theo loại vi phạm (optional)
        video_job_id: Lọc theo video job ID (optional)
        session: Database session
    
    Returns:
        JSON chứa danh sách vi phạm và metadata
    """
    query = select(Violation)
    
    # Apply filters
    if violation_type:
        query = query.where(Violation.violation_type == violation_type)
    if video_job_id:
        query = query.where(Violation.video_job_id == video_job_id)
    
    # Get total count
    total = len(session.exec(query).all())
    
    # Apply pagination
    violations = session.exec(query.offset(skip).limit(limit)).all()
    
    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "violations": violations
    }


@router.get("/{violation_id}")
async def get_violation_detail(
    violation_id: int,
    session: Session = Depends(get_session)
):
    """
    Lấy chi tiết một vi phạm cụ thể.
    
    Args:
        violation_id: ID của vi phạm
        session: Database session
    
    Returns:
        JSON chứa chi tiết vi phạm
    """
    violation = session.exec(
        select(Violation).where(Violation.id == violation_id)
    ).first()
    
    if not violation:
        raise HTTPException(status_code=404, detail="Không tìm thấy vi phạm")
    
    return violation


@router.delete("/{violation_id}")
async def delete_violation(
    violation_id: int,
    session: Session = Depends(get_session)
):
    """
    Xóa một vi phạm.
    
    Args:
        violation_id: ID của vi phạm cần xóa
        session: Database session
    
    Returns:
        JSON xác nhận xóa thành công
    """
    violation = session.exec(
        select(Violation).where(Violation.id == violation_id)
    ).first()
    
    if not violation:
        raise HTTPException(status_code=404, detail="Không tìm thấy vi phạm")
    
    session.delete(violation)
    session.commit()
    
    return {"message": "Đã xóa vi phạm thành công", "violation_id": violation_id}



# === STOPLINE CONFIGURATION ===
from pydantic import BaseModel, Field

# In-memory storage for stoplines (per camera)
stoplines_storage = {}

class StoplineRequest(BaseModel):
    """Request to save stopline configuration"""
    camera_id: str = Field(..., min_length=1, description="Camera identifier")
    stopline: dict = Field(..., description="Stopline coordinates {x1, y1, x2, y2}")


@router.post("/stopline")
async def save_stopline(request: StoplineRequest):
    """
    Save stopline configuration for violation detection.
    
    Args:
        request: StoplineRequest with camera_id and stopline coordinates
    
    Returns:
        JSON confirmation
    """
    try:
        # Validate stopline format
        stopline = request.stopline
        required_keys = ['x1', 'y1', 'x2', 'y2']
        if not all(key in stopline for key in required_keys):
            raise HTTPException(
                status_code=400, 
                detail=f"Stopline must contain: {required_keys}"
            )
        
        # Store in memory
        stoplines_storage[request.camera_id] = {
            'x1': int(stopline['x1']),
            'y1': int(stopline['y1']),
            'x2': int(stopline['x2']),
            'y2': int(stopline['y2'])
        }
        
        return {
            "ok": True,
            "message": "Stopline saved successfully",
            "camera_id": request.camera_id,
            "stopline": stoplines_storage[request.camera_id]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stopline/{camera_id}")
async def get_stopline(camera_id: str):
    """
    Get stopline configuration for a camera.
    
    Args:
        camera_id: Camera identifier
    
    Returns:
        Stopline coordinates or null if not configured
    """
    stopline = stoplines_storage.get(camera_id)
    return {
        "camera_id": camera_id,
        "stopline": stopline
    }


@router.delete("/stopline/{camera_id}")
async def delete_stopline(camera_id: str):
    """
    Delete stopline configuration for a camera.
    
    Args:
        camera_id: Camera identifier
    
    Returns:
        JSON confirmation
    """
    if camera_id in stoplines_storage:
        del stoplines_storage[camera_id]
        return {
            "ok": True,
            "message": "Stopline deleted successfully",
            "camera_id": camera_id
        }
    else:
        raise HTTPException(status_code=404, detail="Stopline not found")