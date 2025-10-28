import os
import logging

# Fix OpenMP duplicate library warning
# This happens when multiple packages (PyTorch, NumPy, etc.) include OpenMP
os.environ['KMP_DUPLICATE_LIB_OK'] = 'TRUE'

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.core.config import settings
from app.core.database import create_db_and_tables
from app.core.check_db import check_database_connection, test_database_query
from app.routers import detection, violations, videos
from app.routers import realtime_ws_binary  # Binary WS for 30 FPS
from app.routers import auth as auth_router

# =========================================================
# 📝 Cấu hình logging - Reduced for production
# =========================================================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s: %(message)s",
)
logger = logging.getLogger("main")

# Suppress SQLAlchemy logs
logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)
logging.getLogger('sqlalchemy.pool').setLevel(logging.WARNING)
logging.getLogger('sqlalchemy.dialects').setLevel(logging.WARNING)
logging.getLogger('sqlalchemy.orm').setLevel(logging.WARNING)

# =========================================================
# 🚦 1️⃣ Kiểm tra DB trước khi chạy FastAPI
# =========================================================
logger.info("🔍 Checking database connection...")
check_database_connection()

# =========================================================
# 🚀 2️⃣ Khởi tạo ứng dụng FastAPI
# =========================================================
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="API cho hệ thống phát hiện vi phạm giao thông sử dụng YOLO và OCR"
)

# Cấu hình CORS để frontend Next.js có thể gọi API
# Dev-friendly: nếu cấu hình env không khớp, fallback cho phép tất cả origin (chỉ nên dùng môi trường dev)
try:
    origins = settings.BACKEND_CORS_ORIGINS
    if not origins or not isinstance(origins, list):
        origins = ["*"]
except Exception:
    origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files để serve ảnh và video outputs
app.mount("/static", StaticFiles(directory=settings.STATIC_DIR), name="static")

# Register routers
app.include_router(detection.router, prefix=f"{settings.API_V1_PREFIX}/detection", tags=["Detection"])
app.include_router(violations.router, prefix=f"{settings.API_V1_PREFIX}/violations", tags=["Violations"])
app.include_router(videos.router, prefix=f"{settings.API_V1_PREFIX}/videos", tags=["Videos"])
# Binary realtime endpoint - 30 FPS with TurboJPEG + Multithreading
app.include_router(realtime_ws_binary.router, tags=["Realtime Binary"])
# Auth routes
app.include_router(auth_router.router, prefix=f"{settings.API_V1_PREFIX}")


@app.on_event("startup")
def on_startup():
    """
    Khởi tạo database và tables khi ứng dụng start.
    """
    create_db_and_tables()


@app.get("/")
def root():
    """
    Health check endpoint.
    """
    return {
        "message": "Traffic Violation Detection Server Running 🚦",
        "version": settings.VERSION,
        "docs": "/docs"
    }


@app.get("/api/auth/me")
def auth_me(current_user = Depends(auth_router.get_current_user)):
    return {
        "user_id": current_user.user_id,
        "username": current_user.username,
        "role": getattr(current_user, "role", "user")
    }

@app.get("/health")
def health_check():
    """
    Endpoint để kiểm tra trạng thái server.
    """
    return {"status": "healthy"}


@app.get("/api/db/status")
def database_status():
    """
    Endpoint để kiểm tra kết nối database.
    
    Sử dụng để debug hoặc demo khi trình bày luận văn.
    
    Returns:
        JSON chứa thông tin kết nối database và trạng thái
    """
    return test_database_query()

