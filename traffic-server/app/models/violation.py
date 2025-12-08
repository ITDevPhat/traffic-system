from sqlmodel import SQLModel, Field
from datetime import datetime
from typing import Optional
from pydantic import ConfigDict


class Violation(SQLModel, table=True):
    """
    Model lưu thông tin vi phạm giao thông được phát hiện.
    Schema theo db.sql v1.6
    
    Attributes:
        violation_id: ID tự động tăng (PRIMARY KEY)
        video_job_id: ID của video job (FK)
        vehicle_id: ID của phương tiện vi phạm (FK, nullable)
        violation_type_code: Mã loại vi phạm (FK to violation_types)
        frame: Số thứ tự frame trong video
        timestamp: Thời gian phát hiện vi phạm
        roi_type: Loại ROI liên quan (VARCHAR(50))
        evidence_img: Đường dẫn đến ảnh bằng chứng (TEXT)
        plate: Biển số xe (VARCHAR(20))
        confidence: Độ tin cậy của model (FLOAT, 0-1)
        model_id: ID model AI được sử dụng (FK, nullable)
        verification_status: Trạng thái xác minh (TEXT: unverified | verified | rejected)
        verified_by: ID người xác minh (FK to users, nullable)
        verified_source: Nguồn xác minh (TEXT: manual | ai | external)
        verified_at: Thời gian xác minh (TIMESTAMP, nullable)
        created_at: Thời gian tạo (TIMESTAMP DEFAULT NOW())
    """
    __tablename__ = "violations"
    
    # Fix Pydantic warning about model_id conflicting with protected namespace "model_"
    # Also include json_schema_extra for API docs
    model_config = ConfigDict(
        protected_namespaces=(),
        json_schema_extra={
            "example": {
                "video_job_id": 1,
                "violation_type_code": "red_light",
                "plate": "59A-123.45",
                "confidence": 0.95,
                "frame": 150,
                "timestamp": "2025-01-01T12:00:00"
            }
        }
    )
    
    violation_id: Optional[int] = Field(default=None, primary_key=True)
    video_job_id: Optional[int] = Field(default=None, foreign_key="video_jobs.video_job_id")
    vehicle_id: Optional[int] = Field(default=None, foreign_key="vehicles.vehicle_id")
    violation_type_code: Optional[str] = Field(default=None, foreign_key="violation_types.violation_type_code", max_length=50)
    frame: Optional[int] = Field(default=None)
    timestamp: Optional[datetime] = Field(default=None)
    roi_type: Optional[str] = Field(default=None, max_length=50)
    evidence_img: Optional[str] = Field(default=None)
    plate: Optional[str] = Field(default=None, max_length=20)
    confidence: Optional[float] = Field(default=None)
    model_id: Optional[int] = Field(default=None, foreign_key="models.model_id")
    verification_status: str = Field(default="unverified", max_length=50)  # unverified | verified | rejected
    verified_by: Optional[int] = Field(default=None, foreign_key="users.user_id")
    verified_source: str = Field(default="manual", max_length=50)  # manual | ai | external
    verified_at: Optional[datetime] = Field(default=None)
    created_at: Optional[datetime] = Field(default_factory=datetime.now)
