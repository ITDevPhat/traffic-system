from sqlmodel import SQLModel, Field
from datetime import datetime
from typing import Optional


class Camera(SQLModel, table=True):
    """
    Model lưu thông tin camera giám sát giao thông.
    
    Attributes:
        camera_id: ID tự động tăng (PRIMARY KEY)
        location_id: ID vị trí (FK)
        name: Tên camera
        model: Model camera
        ip_address: Địa chỉ IP
        stream_url: URL stream video
        status: Trạng thái (active | inactive | maintenance)
        install_date: Ngày lắp đặt
        created_at: Thời gian tạo
    """
    __tablename__ = "cameras"
    
    camera_id: Optional[int] = Field(default=None, primary_key=True)
    location_id: Optional[int] = Field(default=None, foreign_key="locations.location_id")
    name: str = Field(max_length=100)
    model: Optional[str] = Field(default=None, max_length=100)
    ip_address: Optional[str] = Field(default=None, max_length=45)
    stream_url: Optional[str] = Field(default=None)
    status: str = Field(default="active")  # active | inactive | maintenance
    install_date: Optional[datetime] = Field(default=None)
    created_at: Optional[datetime] = Field(default_factory=datetime.now)


class CameraCreate(SQLModel):
    """Schema để tạo camera mới"""
    location_id: Optional[int] = None
    name: str = Field(max_length=100)
    model: Optional[str] = None
    ip_address: Optional[str] = None
    stream_url: Optional[str] = None
    status: str = Field(default="active")
    install_date: Optional[datetime] = None


class CameraUpdate(SQLModel):
    """Schema để cập nhật camera"""
    location_id: Optional[int] = None
    name: str
    model: Optional[str] = None
    ip_address: Optional[str] = None
    stream_url: Optional[str] = None
    status: str
    install_date: Optional[datetime] = None
