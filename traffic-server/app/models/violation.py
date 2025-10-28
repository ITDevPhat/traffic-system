from sqlmodel import SQLModel, Field, Relationship
from datetime import datetime
from typing import Optional


class Violation(SQLModel, table=True):
    """
    Model lưu thông tin vi phạm giao thông được phát hiện.
    
    Attributes:
        id: ID tự động tăng
        video_job_id: ID của video job tương ứng
        vehicle_id: ID của phương tiện vi phạm (link với bảng vehicles)
        violation_type: Loại vi phạm (red_light, stop_line, wrong_lane, no_helmet, etc.)
        plate: Biển số xe (sau khi OCR, có thể UNKNOWN)
        timestamp: Thời gian phát hiện vi phạm
        confidence: Độ tin cậy của model (0-1)
        evidence_img: Đường dẫn đến ảnh bằng chứng
        frame_number: Số thứ tự frame trong video
        location: Vị trí phát hiện (nếu có)
        traffic_light_status: Trạng thái đèn tín hiệu lúc vi phạm (red, green, yellow)
    """
    __tablename__ = "violations"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    video_job_id: int = Field(foreign_key="video_jobs.id")
    vehicle_id: Optional[int] = Field(default=None, foreign_key="vehicles.vehicle_id")
    violation_type: str = Field(max_length=50)
    plate: Optional[str] = Field(default=None, max_length=20)
    timestamp: datetime = Field(default_factory=datetime.now)
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    evidence_img: Optional[str] = Field(default=None)
    frame_number: Optional[int] = Field(default=None)
    location: Optional[str] = Field(default=None, max_length=200)
    traffic_light_status: Optional[str] = Field(default=None, max_length=10)  # red/green/yellow
    
    # Relationship (optional, nếu muốn query ngược lại)
    # vehicle: Optional["Vehicle"] = Relationship(back_populates="violations")
    
    class Config:
        json_schema_extra = {
            "example": {
                "video_job_id": 1,
                "violation_type": "red_light",
                "plate": "59A-123.45",
                "confidence": 0.95,
                "frame_number": 150
            }
        }

