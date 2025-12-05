from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, Form, Query
from typing import Optional
from sqlmodel import Session
from app.core.database import get_session
from app.services.detection_service import process_video

router = APIRouter()


@router.post("/video")
async def detect_violation(
    file: UploadFile = File(..., description="Video file để phát hiện vi phạm"),
    session: Session = Depends(get_session),
    # Module configuration flags
    module_enable_roi: bool = Form(True, description="Enable ROI module"),
    module_enable_roi_drawing: bool = Form(True, description="Enable ROI drawing"),
    module_enable_roi_json: bool = Form(False, description="Enable ROI from JSON"),
    roi_json_path: Optional[str] = Form(None, description="Path to ROI JSON file"),
    module_enable_vehicle_yolo: bool = Form(True, description="Enable vehicle YOLO detection"),
    module_enable_bytetrack: bool = Form(True, description="Enable ByteTrack tracking"),
    module_enable_draw_bbox: bool = Form(True, description="Enable bounding box drawing"),
    # Inference settings
    inference_confidence_vehicle: Optional[float] = Form(None, description="Vehicle detection confidence threshold"),
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
        # Build module configuration from form data
        module_config = {
            "enable_roi": module_enable_roi,
            "enable_roi_drawing": module_enable_roi_drawing,
            "enable_roi_json": module_enable_roi_json,
            "roi_json_path": roi_json_path if module_enable_roi_json else None,
            "enable_vehicle_yolo": module_enable_vehicle_yolo,
            "enable_bytetrack": module_enable_bytetrack,
            "enable_draw_bbox": module_enable_draw_bbox,
            "inference_confidence_vehicle": inference_confidence_vehicle,
        }
        
        result = await process_video(file, session, module_config=module_config)
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



@router.get("/probe-video")
async def probe_video(path: str = Query(..., description="Video file path")):
    """
    Probe video file to get dimensions and metadata.
    
    Args:
        path: Path to video file
    
    Returns:
        JSON with video width, height, fps, duration
    """
    import cv2
    import os
    
    try:
        # Check if file exists
        if not os.path.exists(path):
            raise HTTPException(status_code=404, detail=f"Video file not found: {path}")
        
        # Open video
        cap = cv2.VideoCapture(path)
        
        if not cap.isOpened():
            raise HTTPException(status_code=400, detail="Failed to open video file")
        
        # Get video properties
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = cap.get(cv2.CAP_PROP_FPS)
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration = frame_count / fps if fps > 0 else 0
        
        cap.release()
        
        return {
            "ok": True,
            "width": width,
            "height": height,
            "fps": fps,
            "frame_count": frame_count,
            "duration": duration,
            "path": path
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error probing video: {str(e)}")
