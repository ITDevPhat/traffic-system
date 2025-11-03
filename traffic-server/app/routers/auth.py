from datetime import datetime, timedelta, timezone
from typing import Optional, Union

from fastapi import APIRouter, Depends, HTTPException, status, Response, Request
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from jose import jwt, JWTError
import bcrypt
from sqlmodel import Session, select

from app.core.config import settings
from app.core.database import get_session
from app.models import User
from app.schemas.auth import (
    RegisterRequest,
    RegisterResponse,
    LoginResponse,
    UserResponse,
    ChangePasswordRequest,
    MessageResponse,
)

router = APIRouter(prefix="/auth", tags=["Auth"])

# ===============================
# 🔐 Security utilities
# ===============================

# OAuth2PasswordBearer cho Bearer token authentication
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_PREFIX}/auth/login", auto_error=False)


def hash_password(password: str) -> str:
    """Hash password bằng bcrypt"""
    # Convert password to bytes
    password_bytes = password.encode('utf-8')
    # Generate salt and hash
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password_bytes, salt)
    # Return as string
    return hashed.decode('utf-8')


def verify_password(plain: str, hashed: str) -> bool:
    """Verify password với bcrypt hash"""
    try:
        plain_bytes = plain.encode('utf-8')
        hashed_bytes = hashed.encode('utf-8')
        return bcrypt.checkpw(plain_bytes, hashed_bytes)
    except Exception:
        return False


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Tạo JWT access token"""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(days=settings.ACCESS_TOKEN_EXPIRE_DAYS))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.JWT_SECRET, algorithm="HS256")


def get_user_by_username(session: Session, username: str) -> Optional[User]:
    """Tìm user theo username"""
    stmt = select(User).where(User.username == username)
    return session.exec(stmt).first()


def get_user_by_email(session: Session, email: str) -> Optional[User]:
    """Tìm user theo email"""
    stmt = select(User).where(User.email == email)
    return session.exec(stmt).first()


# ===============================
# 🔑 Authentication endpoints
# ===============================

@router.post("/register", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED)
def register_user(
    data: RegisterRequest,
    session: Session = Depends(get_session)
):
    """
    Đăng ký tài khoản mới
    
    - **username**: Tên đăng nhập (3-50 ký tự, duy nhất)
    - **password**: Mật khẩu (tối thiểu 8 ký tự)
    - **email**: Email (tùy chọn, nếu có thì phải duy nhất)
    - **full_name**: Họ tên đầy đủ (tùy chọn)
    """
    # Kiểm tra username đã tồn tại
    existing_user = get_user_by_username(session, data.username)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already exists"
        )
    
    # Kiểm tra email đã tồn tại (nếu có)
    if data.email:
        existing_email = get_user_by_email(session, data.email)
        if existing_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
    
    # Hash password
    hashed_pw = hash_password(data.password)
    
    # Tạo user mới
    new_user = User(
        username=data.username,
        full_name=data.full_name,
        email=data.email,
        password_hash=hashed_pw,
        role="user",  # Default role
        created_at=datetime.now(timezone.utc)
    )
    
    session.add(new_user)
    session.commit()
    session.refresh(new_user)
    
    return RegisterResponse(
        message="User registered successfully",
        user_id=new_user.user_id,
        username=new_user.username
    )


@router.post("/login", response_model=LoginResponse)
def login(
    response: Response,
    form_data: OAuth2PasswordRequestForm = Depends(),
    session: Session = Depends(get_session)
):
    """
    Đăng nhập bằng username/email và password
    
    Hỗ trợ đăng nhập bằng:
    - Username: admin, demo
    - Email: admin@traffic-system.com
    
    Trả về JWT access token và thông tin user.
    Token cũng được set vào cookie để sử dụng cho web app.
    """
    # Tìm user theo username hoặc email
    # Nếu input có '@', tìm theo email trước, không thì tìm theo username
    username_or_email = form_data.username.strip()
    
    if '@' in username_or_email:
        # Có thể là email, thử tìm theo email trước
        user = get_user_by_email(session, username_or_email)
        # Nếu không tìm thấy theo email, thử tìm theo username (edge case)
        if not user:
            user = get_user_by_username(session, username_or_email)
    else:
        # Không có @, tìm theo username trước
        user = get_user_by_username(session, username_or_email)
        # Nếu không tìm thấy theo username, thử tìm theo email (edge case)
        if not user:
            user = get_user_by_email(session, username_or_email)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username/email or password"
        )
    
    # Verify password
    if not verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username/email or password"
        )
    
    # Cập nhật last_login
    user.last_login = datetime.now(timezone.utc)
    session.add(user)
    session.commit()
    session.refresh(user)
    
    # Tạo JWT token
    is_superuser = (user.role == "admin")
    token_data = {
        "sub": str(user.user_id),
        "username": user.username,
        "role": user.role,
        "is_superuser": is_superuser
    }
    access_token = create_access_token(token_data)
    
    # Set cookie cho web app
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=bool(settings.COOKIE_SECURE),
        samesite=settings.COOKIE_SAMESITE,
        max_age=60 * 60 * 24 * settings.ACCESS_TOKEN_EXPIRE_DAYS,
        path="/"
    )
    
    # Trả về response
    user_response = UserResponse.model_validate(user)
    
    return LoginResponse(
        access_token=access_token,
        token_type="bearer",
        user=user_response
    )


@router.post("/logout", response_model=MessageResponse)
def logout(response: Response):
    """
    Đăng xuất - xóa cookie chứa access token
    """
    response.delete_cookie("access_token", path="/")
    return MessageResponse(message="Logged out successfully")


# ===============================
# 🔒 Protected endpoints
# ===============================

def get_current_user(
    request: Request,
    token: Optional[str] = Depends(oauth2_scheme),
    session: Session = Depends(get_session)
) -> User:
    """
    Dependency để lấy current user từ JWT token
    
    Hỗ trợ 2 cách authentication:
    1. Bearer token trong Authorization header (cho API/mobile)
    2. Cookie token (cho web app)
    """
    # Thử lấy token từ cookie trước (web app)
    if not token:
        token = request.cookies.get("access_token")
    
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=["HS256"])
        user_id = int(payload.get("sub"))
    except (JWTError, ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
    
    return user


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    """
    Dependency yêu cầu user phải có role admin
    """
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required"
        )
    return current_user


@router.get("/me", response_model=UserResponse)
def get_current_user_info(current_user: User = Depends(get_current_user)):
    """
    Lấy thông tin user hiện tại
    
    Yêu cầu authentication (Bearer token hoặc cookie).
    """
    return UserResponse.model_validate(current_user)


@router.post("/change-password", response_model=MessageResponse)
def change_password(
    payload: ChangePasswordRequest,
    response: Response,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """
    Đổi mật khẩu cho user hiện tại
    
    Yêu cầu mật khẩu hiện tại để xác thực.
    """
    # Verify current password
    if not verify_password(payload.current_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect"
        )
    
    # Validate new password khác old password
    if payload.current_password == payload.new_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must be different from current password"
        )
    
    # Update password hash
    current_user.password_hash = hash_password(payload.new_password)
    session.add(current_user)
    session.commit()
    
    # Rotate JWT token (recommended security practice)
    token_data = {
        "sub": str(current_user.user_id),
        "username": current_user.username,
        "role": current_user.role,
        "is_superuser": (current_user.role == "admin")
    }
    new_token = create_access_token(token_data)
    
    # Update cookie
    response.set_cookie(
        key="access_token",
        value=new_token,
        httponly=True,
        secure=bool(settings.COOKIE_SECURE),
        samesite=settings.COOKIE_SAMESITE,
        max_age=60 * 60 * 24 * settings.ACCESS_TOKEN_EXPIRE_DAYS,
        path="/"
    )
    
    return MessageResponse(message="Password changed successfully")

