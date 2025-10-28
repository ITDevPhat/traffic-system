from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from sqlmodel import Session
from app.core.database import get_session
from app.services.detection_service import process_video

router = APIRouter()


@router.post("/video")
async def detect_violation(
    file: UploadFile = File(..., description="Video file để phát hiện vi phạm"),
    session: Session = Depends(get_session)
):
    """
    Upload video và phát hiện vi phạm giao thông.
    
    Args:
        file: Video file (mp4, avi, mov, etc.)
        session: Database session
    
    Returns:
        JSON chứa thông tin video job và kết quả phát hiện
    """
    # Kiểm tra định dạng file
    allowed_extensions = [".mp4", ".avi", ".mov", ".mkv", ".flv"]
    file_extension = file.filename.split(".")[-1].lower()
    
    if f".{file_extension}" not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"File không hợp lệ. Chỉ chấp nhận: {', '.join(allowed_extensions)}"
        )
    
    try:
        result = await process_video(file, session)
        return {
            "status": "success",
            "message": "Video đã được xử lý thành công",
            "result": result
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Lỗi khi xử lý video: {str(e)}"
        )


@router.get("/status/{job_id}")
async def get_detection_status(
    job_id: int,
    session: Session = Depends(get_session)
):
    """
    Kiểm tra trạng thái xử lý video.
    
    Args:
        job_id: ID của video job
        session: Database session
    
    Returns:
        JSON chứa trạng thái hiện tại của job
    """
    from app.models.video_job import VideoJob
    from sqlmodel import select
    
    video_job = session.exec(select(VideoJob).where(VideoJob.id == job_id)).first()
    
    if not video_job:
        raise HTTPException(status_code=404, detail="Không tìm thấy video job")
    
    return {
        "job_id": video_job.id,
        "status": video_job.status,
        "violations_count": video_job.violations_count,
        "progress": {
            "created_at": video_job.created_at,
            "started_at": video_job.started_at,
            "completed_at": video_job.completed_at
        }
    }

