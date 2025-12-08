from datetime import datetime
from typing import Optional, Tuple

from pydantic import BaseModel


class TrafficLightViolationIn(BaseModel):
    camera_id: Optional[int] = None
    camera_name: Optional[str] = None
    video_job_id: Optional[int] = None
    violation_type_code: Optional[str] = "RED_LIGHT"
    frame: Optional[int] = None
    timestamp: Optional[datetime] = None
    plate: Optional[str] = None
    confidence: Optional[float] = None
    bbox: Optional[Tuple[float, float, float, float]] = None
    label: Optional[str] = None
    traffic_light_state: Optional[str] = None
    violation_engine_type: Optional[str] = None
    evidence_img_with_bbox: Optional[str] = None
    evidence_img_raw: Optional[str] = None
    roi_type: Optional[str] = None
    model_id: Optional[int] = None
