"""
Model Vehicle - Thông tin phương tiện được phát hiện.
Schema theo db.sql v1.6

Lưu trữ thông tin về từng phương tiện bao gồm:
- Biển số xe (UNIQUE)
- Loại phương tiện (xe máy, ô tô, xe tải...)
- Màu sắc, thương hiệu
- Tổng số vi phạm
- Thời gian phát hiện lần đầu và cuối cùng
"""

from datetime import datetime
from typing import Optional
from sqlmodel import Field, SQLModel


class Vehicle(SQLModel, table=True):
    """
    Bảng lưu thông tin phương tiện theo db.sql v1.6.
    
    Mỗi vehicle được identify bởi biển số (plate) - UNIQUE.
    Có thể có nhiều violations từ cùng 1 vehicle.
    """
    __tablename__ = "vehicles"
    
    vehicle_id: Optional[int] = Field(default=None, primary_key=True)
    plate: Optional[str] = Field(default=None, unique=True, max_length=20)  # UNIQUE in db.sql
    type: Optional[str] = Field(default=None, max_length=20)  # car, motorbike, truck, bus
    color: Optional[str] = Field(default=None, max_length=50)
    brand: Optional[str] = Field(default=None, max_length=100)
    total_violations: int = Field(default=0)  # Changed from total_detections
    first_seen: Optional[datetime] = Field(default=None)
    last_seen: Optional[datetime] = Field(default=None)


class VehicleCreate(SQLModel):
    """
    Schema để tạo vehicle mới.
    """
    plate: Optional[str] = None
    type: Optional[str] = None
    color: Optional[str] = None
    brand: Optional[str] = None


class VehicleRead(SQLModel):
    """
    Schema để đọc thông tin vehicle.
    """
    vehicle_id: int
    plate: Optional[str]
    type: Optional[str]
    color: Optional[str]
    brand: Optional[str]
    total_violations: int
    first_seen: Optional[datetime]
    last_seen: Optional[datetime]
