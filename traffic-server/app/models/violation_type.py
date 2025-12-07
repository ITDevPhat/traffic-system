from sqlmodel import SQLModel, Field
from typing import Optional
from pydantic import ConfigDict


class ViolationType(SQLModel, table=True):
    """
    Model lưu thông tin loại vi phạm giao thông.
    
    Attributes:
        violation_type_code: Mã loại vi phạm (PRIMARY KEY)
        description: Mô tả chi tiết loại vi phạm
        fine_amount: Mức phạt (VNĐ)
        severity: Mức độ nghiêm trọng (low | medium | high)
    """
    __tablename__ = "violation_types"
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "violation_type_code": "RED_LIGHT",
                "description": "Vượt đèn đỏ",
                "fine_amount": 500000,
                "severity": "high"
            }
        }
    )
    
    violation_type_code: str = Field(primary_key=True, max_length=50)
    description: str = Field()
    fine_amount: Optional[float] = Field(default=None)
    severity: str = Field(default="medium", max_length=50)  # low | medium | high


class ViolationTypeCreate(SQLModel):
    """Schema để tạo loại vi phạm mới"""
    violation_type_code: str = Field(max_length=50)
    description: str
    fine_amount: Optional[float] = None
    severity: str = Field(default="medium")


class ViolationTypeUpdate(SQLModel):
    """Schema để cập nhật loại vi phạm (không cho phép thay đổi code)"""
    description: str
    fine_amount: Optional[float] = None
    severity: str
