"""
Model Vehicle - Thông tin phương tiện được phát hiện.

Lưu trữ thông tin về từng phương tiện bao gồm:
- Biển số xe
- Loại phương tiện (xe máy, ô tô, xe tải...)
- Thời gian phát hiện lần đầu và cuối cùng
- Track ID (từ ByteTrack nếu có)
"""

from datetime import datetime
from typing import Optional
from sqlmodel import Field, SQLModel, Relationship


class Vehicle(SQLModel, table=True):
    """
    Bảng lưu thông tin phương tiện.
    
    Mỗi vehicle được identify bởi biển số (plate).
    Có thể có nhiều violations từ cùng 1 vehicle.
    """
    __tablename__ = "vehicles"
    
    vehicle_id: Optional[int] = Field(default=None, primary_key=True)
    
    # Thông tin nhận dạng
    plate: str = Field(index=True)  # Biển số xe (có thể "UNKNOWN")
    type: str = Field(default="unknown")  # car, motorbike, truck, bus
    
    # Tracking info
    track_id: Optional[int] = Field(default=None)  # ByteTrack ID nếu có
    
    # Timestamps
    first_seen: datetime = Field(default_factory=datetime.now)
    last_seen: datetime = Field(default_factory=datetime.now)
    
    # Confidence
    avg_confidence: float = Field(default=0.0)  # Độ tin cậy trung bình
    
    # Metadata
    total_detections: int = Field(default=1)  # Số lần được phát hiện
    notes: Optional[str] = Field(default=None)  # Ghi chú
    
    # Relationship: 1 vehicle → nhiều violations
    # violations: list["Violation"] = Relationship(back_populates="vehicle")


class VehicleCreate(SQLModel):
    """
    Schema để tạo vehicle mới.
    """
    plate: str
    type: str = "unknown"
    track_id: Optional[int] = None
    avg_confidence: float = 0.0


class VehicleRead(SQLModel):
    """
    Schema để đọc thông tin vehicle.
    """
    vehicle_id: int
    plate: str
    type: str
    track_id: Optional[int]
    first_seen: datetime
    last_seen: datetime
    avg_confidence: float
    total_detections: int
    notes: Optional[str]

