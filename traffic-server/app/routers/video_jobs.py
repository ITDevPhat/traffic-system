from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select
from app.core.database import get_session
from app.models.video_job import VideoJob
from typing import List, Optional
from pydantic import BaseModel

router = APIRouter()


class VideoJobCreate(BaseModel):
    """Schema để tạo video job mới"""
    camera_id: Optional[int] = None
    file_name: str
    status: str = "pending"
    processing_stage: str = "uploaded"
    output_path: Optional[str] = None
    fps: Optional[float] = None
    duration: Optional[float] = None
    notes: Optional[str] = None


class VideoJobUpdate(BaseModel):
    """Schema để cập nhật video job"""
    camera_id: Optional[int] = None
    file_name: str
    status: str
    processing_stage: str
    processed_at: Optional[str] = None
    output_path: Optional[str] = None
    fps: Optional[float] = None
    duration: Optional[float] = None
    notes: Optional[str] = None


@router.get("/", response_model=List[VideoJob])
async def get_video_jobs(
    skip: int = Query(0, ge=0, description="Số record bỏ qua"),
    limit: int = Query(100, ge=1, le=1000, description="Số record tối đa trả về"),
    status: Optional[str] = Query(None, description="Lọc theo trạng thái"),
    camera_id: Optional[int] = Query(None, description="Lọc theo camera"),
    session: Session = Depends(get_session)
):
    """Lấy danh sách các video job."""
    query = select(VideoJob)
    
    if status:
        query = query.where(VideoJob.status == status)
    if camera_id:
        query = query.where(VideoJob.camera_id == camera_id)
    
    video_jobs = session.exec(query.offset(skip).limit(limit)).all()
    return video_jobs


@router.get("/{video_job_id}", response_model=VideoJob)
async def get_video_job_by_id(
    video_job_id: int,
    session: Session = Depends(get_session)
):
    """Lấy chi tiết một video job theo ID."""
    video_job = session.exec(
        select(VideoJob).where(VideoJob.video_job_id == video_job_id)
    ).first()
    
    if not video_job:
        raise HTTPException(status_code=404, detail="Không tìm thấy video job")
    
    return video_job


@router.post("/", response_model=VideoJob)
async def create_video_job(
    video_job_data: VideoJobCreate,
    session: Session = Depends(get_session)
):
    """Tạo video job mới."""
    valid_statuses = ['pending', 'processing', 'done', 'failed']
    if video_job_data.status not in valid_statuses:
        raise HTTPException(
            status_code=400,
            detail=f"Trạng thái phải là một trong: {', '.join(valid_statuses)}"
        )
    
    valid_stages = ['uploaded', 'detecting', 'tracking', 'completed']
    if video_job_data.processing_stage not in valid_stages:
        raise HTTPException(
            status_code=400,
            detail=f"Giai đoạn xử lý phải là một trong: {', '.join(valid_stages)}"
        )
    
    if video_job_data.camera_id:
        from app.models.camera import Camera
        camera = session.exec(
            select(Camera).where(Camera.camera_id == video_job_data.camera_id)
        ).first()
        if not camera:
            raise HTTPException(status_code=404, detail="Không tìm thấy camera")
    
    video_job = VideoJob(**video_job_data.model_dump())
    session.add(video_job)
    session.commit()
    session.refresh(video_job)
    
    return video_job


@router.put("/{video_job_id}", response_model=VideoJob)
async def update_video_job(
    video_job_id: int,
    video_job_data: VideoJobUpdate,
    session: Session = Depends(get_session)
):
    """Cập nhật thông tin video job."""
    video_job = session.exec(
        select(VideoJob).where(VideoJob.video_job_id == video_job_id)
    ).first()
    
    if not video_job:
        raise HTTPException(status_code=404, detail="Không tìm thấy video job")
    
    valid_statuses = ['pending', 'processing', 'done', 'failed']
    if video_job_data.status not in valid_statuses:
        raise HTTPException(
            status_code=400,
            detail=f"Trạng thái phải là một trong: {', '.join(valid_statuses)}"
        )
    
    valid_stages = ['uploaded', 'detecting', 'tracking', 'completed']
    if video_job_data.processing_stage not in valid_stages:
        raise HTTPException(
            status_code=400,
            detail=f"Giai đoạn xử lý phải là một trong: {', '.join(valid_stages)}"
        )
    
    if video_job_data.camera_id:
        from app.models.camera import Camera
        camera = session.exec(
            select(Camera).where(Camera.camera_id == video_job_data.camera_id)
        ).first()
        if not camera:
            raise HTTPException(status_code=404, detail="Không tìm thấy camera")
    
    video_job.camera_id = video_job_data.camera_id
    video_job.file_name = video_job_data.file_name
    video_job.status = video_job_data.status
    video_job.processing_stage = video_job_data.processing_stage
    video_job.output_path = video_job_data.output_path
    video_job.fps = video_job_data.fps
    video_job.duration = video_job_data.duration
    video_job.notes = video_job_data.notes
    
    session.add(video_job)
    session.commit()
    session.refresh(video_job)
    
    return video_job


@router.delete("/{video_job_id}")
async def delete_video_job(
    video_job_id: int,
    session: Session = Depends(get_session)
):
    """Xóa video job."""
    video_job = session.exec(
        select(VideoJob).where(VideoJob.video_job_id == video_job_id)
    ).first()
    
    if not video_job:
        raise HTTPException(status_code=404, detail="Không tìm thấy video job")
    
    from app.models.violation import Violation
    violations_count = len(session.exec(
        select(Violation).where(Violation.video_job_id == video_job_id)
    ).all())
    
    if violations_count > 0:
        raise HTTPException(
            status_code=400,
            detail=f"Không thể xóa video job này vì có {violations_count} vi phạm liên quan"
        )
    
    session.delete(video_job)
    session.commit()
    
    return {
        "message": "Đã xóa video job thành công",
        "video_job_id": video_job_id
    }
