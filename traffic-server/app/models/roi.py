"""
ROI Model - Region of Interest configuration
Schema theo db.sql v1.6

Lưu trữ các vùng ROI (polygon) cho từng video job.
Dùng cho:
- Stop line detection
- Violation zone detection
- Lane detection
- Speed measurement zones
"""

from datetime import datetime
from typing import Optional, List
from sqlmodel import Field, SQLModel, Column
from sqlalchemy import JSON


class ROI(SQLModel, table=True):
    """
    Bảng lưu ROI configurations theo db.sql v1.6.
    
    Mỗi ROI là một polygon được định nghĩa bởi list of coordinates (JSONB).
    Chỉ link với video_job (không có camera_id trong schema mới).
    """
    __tablename__ = "rois"
    
    roi_id: Optional[int] = Field(default=None, primary_key=True)
    video_job_id: Optional[int] = Field(default=None, foreign_key="video_jobs.video_job_id")
    roi_type: str = Field(max_length=50)  # "stop_line", "violation_zone", "lane", "speed_zone"
    coordinates: List[List[float]] = Field(sa_column=Column(JSON))  # JSONB in PostgreSQL
    created_at: Optional[datetime] = Field(default_factory=datetime.now)
    
    class Config:
        json_schema_extra = {
            "example": {
                "video_job_id": 1,
                "roi_type": "stop_line",
                "coordinates": [[100, 300], [500, 300], [500, 350], [100, 350]],
                "created_at": "2025-01-01T12:00:00"
            }
        }


class ROICreate(SQLModel):
    """
    Schema để tạo ROI mới.
    """
    video_job_id: Optional[int] = None
    roi_type: str
    coordinates: List[List[float]]


class ROIRead(SQLModel):
    """
    Schema để đọc thông tin ROI.
    """
    roi_id: int
    video_job_id: Optional[int]
    roi_type: str
    coordinates: List[List[float]]
    created_at: datetime


class ROIUpdate(SQLModel):
    """
    Schema để update ROI.
    """
    roi_type: Optional[str] = None
    coordinates: Optional[List[List[float]]] = None
