from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select
from app.core.database import get_session
from app.models.video_job import VideoJob, JobStatus
from typing import Optional

router = APIRouter()


@router.get("/")
async def list_videos(
    skip: int = Query(0, ge=0, description="Số record bỏ qua"),
    limit: int = Query(100, ge=1, le=1000, description="Số record tối đa trả về"),
    status: Optional[JobStatus] = Query(None, description="Lọc theo trạng thái"),
    session: Session = Depends(get_session)
):
    """
    Lấy danh sách các video job.
    
    Args:
        skip: Số record bỏ qua (pagination)
        limit: Số record tối đa trả về
        status: Lọc theo trạng thái (optional)
        session: Database session
    
    Returns:
        JSON chứa danh sách video jobs và metadata
    """
    query = select(VideoJob)
    
    # Apply filter
    if status:
        query = query.where(VideoJob.status == status)
    
    # Get total count
    total = len(session.exec(query).all())
    
    # Apply pagination and order by created_at desc
    videos = session.exec(
        query.order_by(VideoJob.created_at.desc()).offset(skip).limit(limit)
    ).all()
    
    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "videos": videos
    }


@router.get("/{video_id}")
async def get_video_detail(
    video_id: int,
    session: Session = Depends(get_session)
):
    """
    Lấy chi tiết một video job cụ thể.
    
    Args:
        video_id: ID của video job
        session: Database session
    
    Returns:
        JSON chứa chi tiết video job
    """
    video = session.exec(
        select(VideoJob).where(VideoJob.id == video_id)
    ).first()
    
    if not video:
        raise HTTPException(status_code=404, detail="Không tìm thấy video")
    
    return video


@router.delete("/{video_id}")
async def delete_video(
    video_id: int,
    session: Session = Depends(get_session)
):
    """
    Xóa một video job và các vi phạm liên quan.
    
    Args:
        video_id: ID của video job cần xóa
        session: Database session
    
    Returns:
        JSON xác nhận xóa thành công
    """
    from app.models.violation import Violation
    
    video = session.exec(
        select(VideoJob).where(VideoJob.id == video_id)
    ).first()
    
    if not video:
        raise HTTPException(status_code=404, detail="Không tìm thấy video")
    
    # Xóa tất cả violations liên quan
    violations = session.exec(
        select(Violation).where(Violation.video_job_id == video_id)
    ).all()
    
    for violation in violations:
        session.delete(violation)
    
    # Xóa video job
    session.delete(video)
    session.commit()
    
    return {
        "message": "Đã xóa video thành công",
        "video_id": video_id,
        "violations_deleted": len(violations)
    }

