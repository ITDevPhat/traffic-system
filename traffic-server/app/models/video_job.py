from sqlmodel import SQLModel, Field
from datetime import datetime
from typing import Optional
from enum import Enum


class JobStatus(str, Enum):
    """Trạng thái của video job theo db.sql."""
    PENDING = "pending"
    PROCESSING = "processing"
    DONE = "done"  # Changed from "completed" to "done" to match db.sql
    FAILED = "failed"


class VideoJob(SQLModel, table=True):
    """
    Model lưu thông tin về video job được xử lý.
    Schema theo db.sql v1.6
    
    Attributes:
        video_job_id: ID tự động tăng (PRIMARY KEY)
        camera_id: ID camera (FK)
        file_name: Tên file video (VARCHAR(255) NOT NULL)
        upload_time: Thời gian upload (TIMESTAMP DEFAULT NOW())
        status: Trạng thái (TEXT: pending | processing | done | failed)
        processing_stage: Giai đoạn xử lý (VARCHAR(30): uploaded | detecting | tracking | completed)
        processed_at: Thời gian hoàn thành (TIMESTAMP)
        output_path: Đường dẫn video output (TEXT)
        fps: Frame per second (FLOAT)
        duration: Thời lượng video (FLOAT)
        notes: Ghi chú (TEXT)
    """
    __tablename__ = "video_jobs"
    
    video_job_id: Optional[int] = Field(default=None, primary_key=True)
    camera_id: Optional[int] = Field(default=None, foreign_key="cameras.camera_id")
    file_name: str = Field(max_length=255)
    upload_time: Optional[datetime] = Field(default_factory=datetime.now)
    status: str = Field(default="pending", max_length=50)  # pending | processing | done | failed (TEXT in db.sql)
    processing_stage: Optional[str] = Field(default="uploaded", max_length=30)  # uploaded | detecting | tracking | completed
    processed_at: Optional[datetime] = Field(default=None)
    output_path: Optional[str] = Field(default=None)
    fps: Optional[float] = Field(default=None)
    duration: Optional[float] = Field(default=None)
    notes: Optional[str] = Field(default=None)
    
    class Config:
        json_schema_extra = {
            "example": {
                "filename": "traffic_video.mp4",
                "file_path": "/static/uploads/video_123.mp4",
                "status": "completed",
                "violations_count": 5
            }
        }

