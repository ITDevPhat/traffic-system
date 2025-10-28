from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, Response, Request
from pydantic import BaseModel, constr
from fastapi.security import OAuth2PasswordRequestForm
from jose import jwt, JWTError
from passlib.context import CryptContext
from sqlmodel import Session, select

from app.core.config import settings
from app.core.database import get_session
from app.models import User  # ensure User model is available

router = APIRouter(prefix="/auth", tags=["Auth"])

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(days=settings.ACCESS_TOKEN_EXPIRE_DAYS))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.JWT_SECRET, algorithm="HS256")


class ChangePasswordIn(BaseModel):
    current_password: constr(min_length=1)
    new_password: constr(min_length=8)


@router.post("/login")
def login(response: Response, form_data: OAuth2PasswordRequestForm = Depends(), session: Session = Depends(get_session)):
    # NOTE: Replace this with real User model when available; using demo inline query
    # Expect a table users(username, hashed_password, is_active, is_superuser)
    user_row = session.exec(select(User).where(User.username == form_data.username)).first()

    if not user_row or not verify_password(form_data.password, user_row.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    is_superuser = (getattr(user_row, "role", "user") == "admin")
    token_data = {"sub": str(user_row.user_id), "username": user_row.username, "is_superuser": is_superuser}
    access_token = create_access_token(token_data)

    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=bool(settings.COOKIE_SECURE),
        samesite=settings.COOKIE_SAMESITE,
        max_age=60 * 60 * 24 * settings.ACCESS_TOKEN_EXPIRE_DAYS,
        path="/"
    )
    return {"msg": "login successful", "user": {"user_id": user_row.user_id, "username": user_row.username, "role": user_row.role}}


@router.post("/logout")
def logout(response: Response):
    response.delete_cookie("access_token", path="/")
    return {"msg": "logged out"}


def get_current_user(request: Request, session: Session = Depends(get_session)):
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=["HS256"])
        user_id = int(payload.get("sub"))
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    user_row = session.get(User, user_id)
    if not user_row:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or inactive")
    return user_row


def require_superuser(current_user = Depends(get_current_user)):
    if not getattr(current_user, "is_superuser", False):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough privileges")
    return current_user


@router.post("/change-password")
def change_password(payload: ChangePasswordIn, response: Response, current_user = Depends(get_current_user), session: Session = Depends(get_session)):
    # Verify current password
    if not verify_password(payload.current_password, current_user.password_hash):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Current password is incorrect")
    # Basic policy
    if payload.current_password == payload.new_password:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="New password must be different")
    # Update hash
    current_user.password_hash = hash_password(payload.new_password)
    session.add(current_user)
    session.commit()
    # Optional: rotate JWT so old token can't be reused (recommended)
    token_data = {
        "sub": str(current_user.user_id),
        "username": current_user.username,
        "is_superuser": (getattr(current_user, "role", "user") == "admin")
    }
    new_token = create_access_token(token_data)
    response.set_cookie(
        key="access_token",
        value=new_token,
        httponly=True,
        secure=bool(settings.COOKIE_SECURE),
        samesite=settings.COOKIE_SAMESITE,
        max_age=60 * 60 * 24 * settings.ACCESS_TOKEN_EXPIRE_DAYS,
        path="/"
    )
    return {"msg": "password changed"}

