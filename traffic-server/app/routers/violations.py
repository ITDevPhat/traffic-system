from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Form
from sqlmodel import Session, select
from app.core.database import get_session
from app.models.violation import Violation
from typing import Optional, List
from pydantic import BaseModel
from datetime import datetime
import os
import uuid
from pathlib import Path

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


class LocationUpdate(BaseModel):
    """Schema để cập nhật thông tin địa điểm"""
    name: Optional[str] = None
    address: Optional[str] = None


class ViolationUpdate(BaseModel):
    """Schema để cập nhật vi phạm"""
    video_job_id: Optional[int] = None
    vehicle_id: Optional[int] = None
    violation_type_code: Optional[str] = None
    frame: Optional[int] = None
    timestamp: Optional[datetime] = None
    roi_type: Optional[str] = None
    evidence_img: Optional[str] = None
    plate: Optional[str] = None
    confidence: Optional[float] = None
    model_id: Optional[int] = None
    verification_status: Optional[str] = None
    verified_by: Optional[int] = None
    verified_source: Optional[str] = None
    verified_at: Optional[datetime] = None
    location: Optional[LocationUpdate] = None


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


@router.get("/{violation_id}")
async def get_violation_detail(
    violation_id: int,
    session: Session = Depends(get_session)
):
    """Lấy chi tiết một vi phạm cụ thể với thông tin joined."""
    from app.models.video_job import VideoJob
    from app.models.camera import Camera
    from app.models.location import Location
    from app.models.violation_type import ViolationType
    from app.models.bbox import BBox
    
    # Get violation
    violation = session.exec(
        select(Violation).where(Violation.violation_id == violation_id)
    ).first()
    
    if not violation:
        raise HTTPException(status_code=404, detail="Không tìm thấy vi phạm")
    
    # Get related data
    video_job = None
    camera = None
    location = None
    violation_type = None
    bboxes = []
    
    if violation.video_job_id:
        video_job = session.exec(
            select(VideoJob).where(VideoJob.video_job_id == violation.video_job_id)
        ).first()
        
        if video_job and video_job.camera_id:
            camera = session.exec(
                select(Camera).where(Camera.camera_id == video_job.camera_id)
            ).first()
            
            if camera and camera.location_id:
                location = session.exec(
                    select(Location).where(Location.location_id == camera.location_id)
                ).first()
    
    if violation.violation_type_code:
        violation_type = session.exec(
            select(ViolationType).where(ViolationType.violation_type_code == violation.violation_type_code)
        ).first()
    
    # Get bounding boxes
    bboxes = session.exec(
        select(BBox).where(BBox.violation_id == violation_id)
    ).all()
    
    # Build response
    result = {
        "violation_id": violation.violation_id,
        "video_job_id": violation.video_job_id,
        "vehicle_id": violation.vehicle_id,
        "violation_type_code": violation.violation_type_code,
        "frame": violation.frame,
        "timestamp": violation.timestamp,
        "roi_type": violation.roi_type,
        "evidence_img": violation.evidence_img,
        "plate": violation.plate,
        "confidence": violation.confidence,
        "verification_status": violation.verification_status,
        "verified_by": violation.verified_by,
        "verified_at": violation.verified_at,
        "created_at": violation.created_at,
        
        # Joined data
        "violation_type": {
            "description": violation_type.description if violation_type else None,
            "fine_amount": violation_type.fine_amount if violation_type else None,
            "severity": violation_type.severity if violation_type else None,
        } if violation_type else None,
        
        "camera": {
            "name": camera.name if camera else None,
            "model": camera.model if camera else None,
        } if camera else None,
        
        "location": {
            "name": location.name if location else None,
            "address": location.address if location else None,
        } if location else None,
        
        "bboxes": [
            {
                "x1": bbox.x1,
                "y1": bbox.y1,
                "x2": bbox.x2,
                "y2": bbox.y2,
                "label": bbox.label,
                "confidence": bbox.confidence,
            }
            for bbox in bboxes
        ]
    }
    
    return result


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
    
    # Validate verification_status if provided
    if violation_data.verification_status is not None:
        valid_statuses = ['unverified', 'verified', 'rejected']
        if violation_data.verification_status not in valid_statuses:
            raise HTTPException(
                status_code=400,
                detail=f"Trạng thái xác minh phải là một trong: {', '.join(valid_statuses)}"
            )
    
    # Validate verified_source if provided
    if violation_data.verified_source is not None:
        valid_sources = ['manual', 'ai', 'external']
        if violation_data.verified_source not in valid_sources:
            raise HTTPException(
                status_code=400,
                detail=f"Nguồn xác minh phải là một trong: {', '.join(valid_sources)}"
            )
    
    # Validate confidence if provided
    if violation_data.confidence is not None and not (0 <= violation_data.confidence <= 1):
        raise HTTPException(
            status_code=400,
            detail="Độ tin cậy phải từ 0 đến 1"
        )
    
    # Cập nhật chỉ các field có giá trị
    update_data = violation_data.model_dump(exclude_unset=True)
    
    # Handle location update separately
    location_update = update_data.pop('location', None)
    
    # Update violation fields
    for field, value in update_data.items():
        if value is not None:
            setattr(violation, field, value)
    
    # Handle location update if provided
    if location_update:
        from app.models.video_job import VideoJob
        from app.models.camera import Camera
        from app.models.location import Location
        
        # Get the location through video_job -> camera -> location
        video_job = session.exec(
            select(VideoJob).where(VideoJob.video_job_id == violation.video_job_id)
        ).first()
        
        if video_job and video_job.camera_id:
            camera = session.exec(
                select(Camera).where(Camera.camera_id == video_job.camera_id)
            ).first()
            
            if camera and camera.location_id:
                location = session.exec(
                    select(Location).where(Location.location_id == camera.location_id)
                ).first()
                
                if location:
                    # Update location fields
                    if location_update.get('name') is not None:
                        location.name = location_update['name']
                    if location_update.get('address') is not None:
                        location.address = location_update['address']
                    
                    session.add(location)
    
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


@router.delete("/{violation_id}/delete-image")
async def delete_violation_image(
    violation_id: int,
    image_url: str = Query(..., description="URL của ảnh cần xóa"),
    session: Session = Depends(get_session)
):
    """Xóa hình ảnh của vi phạm."""
    
    # Validate violation exists
    violation = session.exec(
        select(Violation).where(Violation.violation_id == violation_id)
    ).first()
    
    if not violation:
        raise HTTPException(status_code=404, detail="Không tìm thấy vi phạm")
    
    try:
        # Extract filename from URL
        # URL format: /static/violations/{violation_id}/{filename}
        if not image_url.startswith('/static/violations/'):
            raise HTTPException(status_code=400, detail="URL ảnh không hợp lệ")
        
        # Get file path
        from app.core.config import settings
        static_base = Path(settings.STATIC_DIR)
        
        # Remove /static/ prefix and construct file path
        relative_path = image_url.replace('/static/', '')
        file_path = static_base / relative_path
        
        # Check if file exists and delete
        if file_path.exists():
            file_path.unlink()
            
        # If this was the main evidence image, clear it from violation
        if violation.evidence_img == image_url:
            violation.evidence_img = None
            session.add(violation)
            session.commit()
            session.refresh(violation)
        
        return {
            "ok": True,
            "message": "Đã xóa ảnh thành công",
            "deleted_url": image_url
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi xóa file: {str(e)}")


@router.post("/{violation_id}/upload-image")
async def upload_violation_image(
    violation_id: int,
    file: UploadFile = File(...),
    image_type: str = Form(...),  # 'plate', 'location', 'evidence'
    session: Session = Depends(get_session)
):
    """Upload hình ảnh cho vi phạm (biển số, địa điểm, bằng chứng)."""
    
    # Validate violation exists
    violation = session.exec(
        select(Violation).where(Violation.violation_id == violation_id)
    ).first()
    
    if not violation:
        raise HTTPException(status_code=404, detail="Không tìm thấy vi phạm")
    
    # Validate image type
    valid_types = ['plate', 'location', 'evidence']
    if image_type not in valid_types:
        raise HTTPException(
            status_code=400, 
            detail=f"Loại ảnh phải là một trong: {', '.join(valid_types)}"
        )
    
    # Validate file type
    if not file.content_type or not file.content_type.startswith('image/'):
        raise HTTPException(status_code=400, detail="File phải là hình ảnh")
    
    # Validate file size (max 20MB)
    if file.size and file.size > 20 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Kích thước file không được vượt quá 20MB")
    
    try:
        # Use static directory for uploads
        from app.core.config import settings
        # Tạo thư mục trong STATIC_DIR
        static_base = Path(settings.STATIC_DIR)
        upload_dir = static_base / "violations" / str(violation_id)
        upload_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate unique filename
        file_extension = Path(file.filename or "").suffix or ".jpg"
        unique_filename = f"{image_type}_{uuid.uuid4().hex}{file_extension}"
        file_path = upload_dir / unique_filename
        
        # Save file
        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        
        # Generate URL path
        url_path = f"/static/violations/{violation_id}/{unique_filename}"
        
        # Update violation if it's evidence image
        if image_type == 'evidence':
            violation.evidence_img = url_path
            session.add(violation)
            session.commit()
            session.refresh(violation)
        
        return {
            "ok": True,
            "message": f"Đã upload {image_type} thành công",
            "url": url_path,
            "filename": unique_filename
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi upload file: {str(e)}")



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