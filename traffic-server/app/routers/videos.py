from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select
from app.core.database import get_session
from app.models.video_job import VideoJob, JobStatus
from typing import Optional
import os
import glob
from pathlib import Path

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
    
    # Apply filter (status is TEXT in db.sql, not enum)
    if status:
        # Convert enum to string if needed
        status_str = status.value if hasattr(status, 'value') else str(status)
        query = query.where(VideoJob.status == status_str)
    
    # Get total count
    total = len(session.exec(query).all())
    
    # Apply pagination and order by upload_time desc
    videos = session.exec(
        query.order_by(VideoJob.upload_time.desc()).offset(skip).limit(limit)
    ).all()
    
    # Convert to dict and add computed fields for frontend compatibility
    videos_list = []
    for v in videos:
        vid_dict = v.model_dump()
        # Map database fields to frontend expected fields
        vid_dict['id'] = vid_dict.get('video_job_id')
        vid_dict['filename'] = vid_dict.get('file_name', vid_dict.get('filename'))
        vid_dict['file_path'] = vid_dict.get('output_path') or vid_dict.get('file_path')
        vid_dict['created_at'] = vid_dict.get('upload_time') or vid_dict.get('created_at')
        videos_list.append(vid_dict)
    
    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "videos": videos_list
    }


@router.get("/from-folder")
async def list_videos_from_folder():
    """
    Fallback: Load videos từ thư mục traffic-server/videos nếu database không có data.
    
    Returns:
        JSON chứa danh sách video files từ thư mục
    """
    import os
    from pathlib import Path
    
    # Try different video directories
    possible_dirs = [
        Path("traffic-server/videos"),
        Path("videos"),
        Path("traffic-server/app/static/uploads"),
        Path(os.getcwd()) / "traffic-server" / "videos",
        Path(os.getcwd()) / "videos"
    ]
    
    videos_dir = None
    for d in possible_dirs:
        if d.exists() and d.is_dir():
            videos_dir = d
            break
    
    video_files = []
    if videos_dir:
        # Find all video files
        video_extensions = [".mp4", ".avi", ".mov", ".mkv", ".flv", ".wmv"]
        for ext in video_extensions:
            video_files.extend(glob.glob(str(videos_dir / f"*{ext}")))
            video_files.extend(glob.glob(str(videos_dir / f"*{ext.upper()}")))
    
    # Convert to list of dicts
    videos_list = []
    for idx, video_path in enumerate(sorted(set(video_files)), start=1):
        video_path_obj = Path(video_path)
        # Normalize path to use forward slashes
        normalized_path = str(video_path_obj).replace("\\", "/")
        videos_list.append({
            "id": idx,
            "video_job_id": idx,
            "filename": video_path_obj.name,
            "file_name": video_path_obj.name,
            "file_path": normalized_path,
            "output_path": normalized_path,
            "status": "completed",
            "fps": None,
            "duration": None,
            "violations_count": 0,
            "created_at": None,
            "upload_time": None,
            "camera_name": "Unknown",
            "location_name": "Unknown"
        })
    
    return {
        "total": len(videos_list),
        "skip": 0,
        "limit": len(videos_list),
        "videos": videos_list
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
        select(VideoJob).where(VideoJob.video_job_id == video_id)
    ).first()
    
    if not video:
        raise HTTPException(status_code=404, detail="Không tìm thấy video")
    
    vid_dict = video.model_dump()
    vid_dict['id'] = vid_dict.get('video_job_id')
    vid_dict['filename'] = vid_dict.get('file_name', vid_dict.get('filename'))
    vid_dict['file_path'] = vid_dict.get('output_path') or vid_dict.get('file_path')
    vid_dict['created_at'] = vid_dict.get('upload_time') or vid_dict.get('created_at')
    return vid_dict


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
        select(VideoJob).where(VideoJob.video_job_id == video_id)
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

