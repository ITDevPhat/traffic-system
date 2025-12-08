from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel


class BBox(SQLModel, table=True):
    """SQLModel mapping for bboxes table."""

    __tablename__ = "bboxes"

    bbox_id: Optional[int] = Field(default=None, primary_key=True)
    violation_id: Optional[int] = Field(default=None, foreign_key="violations.violation_id")
    x1: float
    y1: float
    x2: float
    y2: float
    confidence: Optional[float] = Field(default=None)
    label: Optional[str] = Field(default=None, max_length=50)
    created_at: Optional[datetime] = Field(default_factory=datetime.utcnow)
