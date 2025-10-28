"""
ROI Model - Region of Interest configuration

Lưu trữ các vùng ROI (polygon) cho từng video job hoặc camera.
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
    Bảng lưu ROI configurations.
    
    Mỗi ROI là một polygon được định nghĩa bởi list of coordinates.
    Có thể có nhiều ROI cho 1 video_job (stop_line, violation_zone, etc.)
    """
    __tablename__ = "rois"
    
    roi_id: Optional[int] = Field(default=None, primary_key=True)
    
    # Link với video job hoặc camera
    video_job_id: Optional[int] = Field(default=None, foreign_key="video_jobs.id")
    camera_id: Optional[str] = Field(default=None, max_length=100)  # For future camera streaming
    
    # ROI type
    roi_type: str = Field(max_length=50)  # "stop_line", "violation_zone", "lane", "speed_zone"
    
    # Polygon coordinates
    # Format: [[x1, y1], [x2, y2], ..., [xn, yn]]
    # Can be normalized (0-1) or absolute pixels
    coordinates: List[List[float]] = Field(sa_column=Column(JSON))
    
    # Metadata
    is_normalized: bool = Field(default=False)  # True if coords are 0-1 normalized
    name: Optional[str] = Field(default=None, max_length=200)  # User-friendly name
    description: Optional[str] = Field(default=None)
    color: Optional[str] = Field(default=None, max_length=20)  # Hex color for visualization
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: Optional[datetime] = Field(default=None)
    
    # Status
    is_active: bool = Field(default=True)
    
    class Config:
        json_schema_extra = {
            "example": {
                "video_job_id": 1,
                "roi_type": "stop_line",
                "coordinates": [[100, 300], [500, 300], [500, 350], [100, 350]],
                "is_normalized": False,
                "name": "Main Stop Line",
                "color": "#FF0000"
            }
        }


class ROICreate(SQLModel):
    """
    Schema để tạo ROI mới.
    """
    video_job_id: Optional[int] = None
    camera_id: Optional[str] = None
    roi_type: str
    coordinates: List[List[float]]
    is_normalized: bool = False
    name: Optional[str] = None
    description: Optional[str] = None
    color: Optional[str] = None


class ROIRead(SQLModel):
    """
    Schema để đọc thông tin ROI.
    """
    roi_id: int
    video_job_id: Optional[int]
    camera_id: Optional[str]
    roi_type: str
    coordinates: List[List[float]]
    is_normalized: bool
    name: Optional[str]
    description: Optional[str]
    color: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]
    is_active: bool


class ROIUpdate(SQLModel):
    """
    Schema để update ROI.
    """
    coordinates: Optional[List[List[float]]] = None
    name: Optional[str] = None
    description: Optional[str] = None
    color: Optional[str] = None
    is_active: Optional[bool] = None

