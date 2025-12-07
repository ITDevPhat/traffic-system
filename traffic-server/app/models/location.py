from sqlmodel import SQLModel, Field
from datetime import datetime
from typing import Optional


class Location(SQLModel, table=True):
    """
    Model lưu thông tin vị trí địa lý của camera và khu vực giám sát.
    
    Attributes:
        location_id: ID tự động tăng (PRIMARY KEY)
        name: Tên vị trí
        address: Địa chỉ chi tiết
        latitude: Vĩ độ (DECIMAL(9,6))
        longitude: Kinh độ (DECIMAL(9,6))
        description: Mô tả
        created_at: Thời gian tạo
    """
    __tablename__ = "locations"
    
    location_id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(max_length=255)
    address: Optional[str] = Field(default=None)
    latitude: Optional[float] = Field(default=None)
    longitude: Optional[float] = Field(default=None)
    description: Optional[str] = Field(default=None)
    created_at: Optional[datetime] = Field(default_factory=datetime.now)


class LocationCreate(SQLModel):
    """Schema để tạo vị trí mới"""
    name: str = Field(max_length=255)
    address: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    description: Optional[str] = None


class LocationUpdate(SQLModel):
    """Schema để cập nhật vị trí"""
    name: str
    address: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    description: Optional[str] = None
