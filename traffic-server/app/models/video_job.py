from sqlmodel import SQLModel, Field
from datetime import datetime
from typing import Optional
from enum import Enum


class JobStatus(str, Enum):
    """Trạng thái của video job."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class VideoJob(SQLModel, table=True):
    """
    Model lưu thông tin về video job được xử lý.
    
    Attributes:
        id: ID tự động tăng
        filename: Tên file video gốc
        file_path: Đường dẫn lưu trữ video
        status: Trạng thái xử lý (pending, processing, completed, failed)
        total_frames: Tổng số frame trong video
        fps: Frame per second của video
        duration: Thời lượng video (giây)
        violations_count: Số lượng vi phạm phát hiện được
        created_at: Thời gian tạo job
        started_at: Thời gian bắt đầu xử lý
        completed_at: Thời gian hoàn thành
        error_message: Thông báo lỗi (nếu có)
    """
    __tablename__ = "video_jobs"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    filename: str = Field(max_length=255)
    file_path: str = Field(max_length=500)
    status: JobStatus = Field(default=JobStatus.PENDING)
    total_frames: Optional[int] = Field(default=None)
    fps: Optional[float] = Field(default=None)
    duration: Optional[float] = Field(default=None)
    violations_count: int = Field(default=0)
    created_at: datetime = Field(default_factory=datetime.now)
    started_at: Optional[datetime] = Field(default=None)
    completed_at: Optional[datetime] = Field(default=None)
    error_message: Optional[str] = Field(default=None)
    
    class Config:
        json_schema_extra = {
            "example": {
                "filename": "traffic_video.mp4",
                "file_path": "/static/uploads/video_123.mp4",
                "status": "completed",
                "violations_count": 5
            }
        }

