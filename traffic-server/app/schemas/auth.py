from typing import Optional
from datetime import datetime
from pydantic import BaseModel, EmailStr, constr, Field


# ===============================
# 🔐 Authentication Schemas
# ===============================

class RegisterRequest(BaseModel):
    """Schema cho đăng ký tài khoản mới"""
    username: constr(min_length=3, max_length=50) = Field(..., description="Username (3-50 ký tự)")
    password: constr(min_length=8) = Field(..., description="Mật khẩu (tối thiểu 8 ký tự)")
    email: Optional[EmailStr] = Field(None, description="Email (tùy chọn)")
    full_name: Optional[str] = Field(None, max_length=100, description="Họ tên đầy đủ")

    class Config:
        json_schema_extra = {
            "example": {
                "username": "admin",
                "password": "Admin@123",
                "email": "admin@example.com",
                "full_name": "Administrator"
            }
        }


class LoginRequest(BaseModel):
    """Schema cho đăng nhập (dùng cho JSON, ngoài OAuth2PasswordRequestForm)"""
    username: str = Field(..., description="Username hoặc email")
    password: str = Field(..., description="Mật khẩu")

    class Config:
        json_schema_extra = {
            "example": {
                "username": "admin",
                "password": "Admin@123"
            }
        }


class UserResponse(BaseModel):
    """Schema trả về thông tin user (không bao gồm password_hash)"""
    user_id: int
    username: str
    full_name: Optional[str] = None
    email: Optional[str] = None
    role: str
    avatar_url: Optional[str] = None
    last_login: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True  # For SQLModel compatibility


class LoginResponse(BaseModel):
    """Schema trả về khi đăng nhập thành công"""
    access_token: str
    token_type: str = "bearer"
    user: UserResponse

    class Config:
        json_schema_extra = {
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "token_type": "bearer",
                "user": {
                    "user_id": 1,
                    "username": "admin",
                    "full_name": "Administrator",
                    "email": "admin@example.com",
                    "role": "admin",
                    "avatar_url": None,
                    "last_login": "2025-10-29T10:00:00",
                    "created_at": "2025-01-01T00:00:00"
                }
            }
        }


class RegisterResponse(BaseModel):
    """Schema trả về khi đăng ký thành công"""
    message: str
    user_id: int
    username: str

    class Config:
        json_schema_extra = {
            "example": {
                "message": "User registered successfully",
                "user_id": 1,
                "username": "admin"
            }
        }


class ChangePasswordRequest(BaseModel):
    """Schema cho đổi mật khẩu"""
    current_password: constr(min_length=1) = Field(..., description="Mật khẩu hiện tại")
    new_password: constr(min_length=8) = Field(..., description="Mật khẩu mới (tối thiểu 8 ký tự)")

    class Config:
        json_schema_extra = {
            "example": {
                "current_password": "OldPass@123",
                "new_password": "NewPass@456"
            }
        }


class MessageResponse(BaseModel):
    """Schema chung cho các response chỉ có message"""
    message: str

    class Config:
        json_schema_extra = {
            "example": {
                "message": "Operation completed successfully"
            }
        }

