from sqlmodel import SQLModel, Field
from datetime import datetime
from typing import Optional
from pydantic import ConfigDict


class Model(SQLModel, table=True):
    """
    Model lưu thông tin các mô hình AI (YOLO, OCR, Traffic Light, ...).
    
    Attributes:
        model_id: ID tự động tăng (PRIMARY KEY)
        name: Tên mô hình
        model_type: Loại mô hình (vehicle | plate | ocr | traffic_light | violation)
        file_path: Đường dẫn file mô hình
        version: Phiên bản mô hình
        framework: Framework sử dụng (YOLO, TensorFlow, ...)
        confidence_threshold: Ngưỡng confidence mặc định
        description: Mô tả chi tiết
        created_at: Thời gian tạo
    """
    __tablename__ = "models"
    
    model_config = ConfigDict(
        protected_namespaces=(),
        json_schema_extra={
            "example": {
                "name": "yolo_vehicle_11s",
                "model_type": "vehicle",
                "file_path": "models/vehicle/yolo_vehicle_11s.pt",
                "version": "11s",
                "framework": "YOLOv11s",
                "confidence_threshold": 0.5,
                "description": "Phát hiện phương tiện - phiên bản nhẹ"
            }
        }
    )
    
    model_id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(max_length=100)
    model_type: str = Field()  # vehicle | plate | ocr | traffic_light | violation
    file_path: str = Field()
    version: str = Field(default="1.0", max_length=50)
    framework: str = Field(default="YOLO", max_length=50)
    confidence_threshold: float = Field(default=0.5)
    description: Optional[str] = Field(default=None)
    created_at: Optional[datetime] = Field(default_factory=datetime.now)


class ModelCreate(SQLModel):
    """Schema để tạo mô hình mới"""
    name: str = Field(max_length=100)
    model_type: str
    file_path: str
    version: str = Field(default="1.0")
    framework: str = Field(default="YOLO")
    confidence_threshold: float = Field(default=0.5)
    description: Optional[str] = None


class ModelUpdate(SQLModel):
    """Schema để cập nhật mô hình"""
    name: str
    model_type: str
    file_path: str
    version: str
    framework: str
    confidence_threshold: float
    description: Optional[str] = None
