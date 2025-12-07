from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select
from app.core.database import get_session
from app.models.violation import Violation
from typing import Optional, List
from pydantic import BaseModel
from datetime import datetime

router = APIRouter()


class ViolationCreate(BaseModel):
    """Schema để tạo vi phạm mới"""
    video_job_id: int
    vehicle_id: Optional[int] = None
    violation_type_code: Optional[str] = None
    frame: Optional[int] = None
    timestamp: Optional[datetime] = None
    roi_type: Optional[str] = None
    evidence_img: Optional[str] = None
    plate: Optional[str] = None
    confidence: Optional[float] = None
    model_id: Optional[int] = None
    verification_status: str = "unverified"
    verified_source: str = "manual"


class ViolationUpdate(BaseModel):
    """Schema để cập nhật vi phạm"""
    video_job_id: int
    vehicle_id: Optional[int] = None
    violation_type_code: Optional[str] = None
    frame: Optional[int] = None
    timestamp: Optional[datetime] = None
    roi_type: Optional[str] = None
    evidence_img: Optional[str] = None
    plate: Optional[str] = None
    confidence: Optional[float] = None
    model_id: Optional[int] = None
    verification_status: str
    verified_by: Optional[int] = None
    verified_source: str
    verified_at: Optional[datetime] = None


@router.get("/", response_model=List[Violation])
async def get_violations(
    skip: int = Query(0, ge=0, description="Số record bỏ qua"),
    limit: int = Query(100, ge=1, le=1000, description="Số record tối đa trả về"),
    violation_type_code: Optional[str] = Query(None, description="Lọc theo loại vi phạm"),
    video_job_id: Optional[int] = Query(None, description="Lọc theo video job ID"),
    verification_status: Optional[str] = Query(None, description="Lọc theo trạng thái xác minh"),
    plate: Optional[str] = Query(None, description="Lọc theo biển số"),
    session: Session = Depends(get_session)
):
    """Lấy danh sách các vi phạm đã phát hiện."""
    query = select(Violation)
    
    # Apply filters
    if violation_type_code:
        query = query.where(Violation.violation_type_code == violation_type_code)
    if video_job_id:
        query = query.where(Violation.video_job_id == video_job_id)
    if verification_status:
        query = query.where(Violation.verification_status == verification_status)
    if plate:
        query = query.where(Violation.plate.ilike(f"%{plate}%"))
    
    # Apply pagination and order by newest first
    violations = session.exec(
        query.order_by(Violation.created_at.desc()).offset(skip).limit(limit)
    ).all()
    
    return violations


@router.get("/{violation_id}", response_model=Violation)
async def get_violation_detail(
    violation_id: int,
    session: Session = Depends(get_session)
):
    """Lấy chi tiết một vi phạm cụ thể."""
    violation = session.exec(
        select(Violation).where(Violation.violation_id == violation_id)
    ).first()
    
    if not violation:
        raise HTTPException(status_code=404, detail="Không tìm thấy vi phạm")
    
    return violation


@router.post("/", response_model=Violation)
async def create_violation(
    violation_data: ViolationCreate,
    session: Session = Depends(get_session)
):
    """Tạo vi phạm mới."""
    # Validate verification_status
    valid_statuses = ['unverified', 'verified', 'rejected']
    if violation_data.verification_status not in valid_statuses:
        raise HTTPException(
            status_code=400,
            detail=f"Trạng thái xác minh phải là một trong: {', '.join(valid_statuses)}"
        )
    
    # Validate verified_source
    valid_sources = ['manual', 'ai', 'external']
    if violation_data.verified_source not in valid_sources:
        raise HTTPException(
            status_code=400,
            detail=f"Nguồn xác minh phải là một trong: {', '.join(valid_sources)}"
        )
    
    # Validate confidence
    if violation_data.confidence is not None and not (0 <= violation_data.confidence <= 1):
        raise HTTPException(
            status_code=400,
            detail="Độ tin cậy phải từ 0 đến 1"
        )
    
    # Kiểm tra video_job_id tồn tại
    from app.models.video_job import VideoJob
    video_job = session.exec(
        select(VideoJob).where(VideoJob.video_job_id == violation_data.video_job_id)
    ).first()
    if not video_job:
        raise HTTPException(status_code=404, detail="Không tìm thấy video job")
    
    # Tạo mới
    violation = Violation(**violation_data.model_dump())
    session.add(violation)
    session.commit()
    session.refresh(violation)
    
    return violation


@router.put("/{violation_id}", response_model=Violation)
async def update_violation(
    violation_id: int,
    violation_data: ViolationUpdate,
    session: Session = Depends(get_session)
):
    """Cập nhật thông tin vi phạm."""
    violation = session.exec(
        select(Violation).where(Violation.violation_id == violation_id)
    ).first()
    
    if not violation:
        raise HTTPException(status_code=404, detail="Không tìm thấy vi phạm")
    
    # Validate verification_status
    valid_statuses = ['unverified', 'verified', 'rejected']
    if violation_data.verification_status not in valid_statuses:
        raise HTTPException(
            status_code=400,
            detail=f"Trạng thái xác minh phải là một trong: {', '.join(valid_statuses)}"
        )
    
    # Validate verified_source
    valid_sources = ['manual', 'ai', 'external']
    if violation_data.verified_source not in valid_sources:
        raise HTTPException(
            status_code=400,
            detail=f"Nguồn xác minh phải là một trong: {', '.join(valid_sources)}"
        )
    
    # Validate confidence
    if violation_data.confidence is not None and not (0 <= violation_data.confidence <= 1):
        raise HTTPException(
            status_code=400,
            detail="Độ tin cậy phải từ 0 đến 1"
        )
    
    # Cập nhật
    violation.video_job_id = violation_data.video_job_id
    violation.vehicle_id = violation_data.vehicle_id
    violation.violation_type_code = violation_data.violation_type_code
    violation.frame = violation_data.frame
    violation.timestamp = violation_data.timestamp
    violation.roi_type = violation_data.roi_type
    violation.evidence_img = violation_data.evidence_img
    violation.plate = violation_data.plate
    violation.confidence = violation_data.confidence
    violation.model_id = violation_data.model_id
    violation.verification_status = violation_data.verification_status
    violation.verified_by = violation_data.verified_by
    violation.verified_source = violation_data.verified_source
    violation.verified_at = violation_data.verified_at
    
    session.add(violation)
    session.commit()
    session.refresh(violation)
    
    return violation


@router.delete("/{violation_id}")
async def delete_violation(
    violation_id: int,
    session: Session = Depends(get_session)
):
    """Xóa một vi phạm."""
    violation = session.exec(
        select(Violation).where(Violation.violation_id == violation_id)
    ).first()
    
    if not violation:
        raise HTTPException(status_code=404, detail="Không tìm thấy vi phạm")
    
    session.delete(violation)
    session.commit()
    
    return {"message": "Đã xóa vi phạm thành công", "violation_id": violation_id}



# === STOPLINE CONFIGURATION ===
from pydantic import BaseModel, Field
from app.violations.violation_manager import violation_manager

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

        violation_manager.set_stopline(request.camera_id, stoplines_storage[request.camera_id])
        
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