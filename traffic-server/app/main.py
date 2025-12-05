import os
import logging

# Fix OpenMP duplicate library warning
# This happens when multiple packages (PyTorch, NumPy, etc.) include OpenMP
os.environ['KMP_DUPLICATE_LIB_OK'] = 'TRUE'

# =========================================================
# 🔧 ONNX FP32 Compatibility Patch (RTX 3050 Optimized)
# =========================================================
# Force FP32 precision for ONNX models to avoid float16 mismatch
os.environ['FORCE_FP32_ONNX'] = '1'
os.environ['CUDA_VISIBLE_DEVICES'] = '0'

# Apply runtime patches for ONNX FP32 compatibility
def apply_onnx_fp32_patches():
    """Apply runtime patches to ensure ONNX FP32 compatibility"""
    try:
        # Patch YOLO model loading to force FP32
        from ultralytics import YOLO
        original_init = YOLO.__init__
        
        def patched_init(self, model='yolov8n.pt', task=None, verbose=True):
            result = original_init(self, model, task, verbose)
            # Force FP32 for ONNX models
            if hasattr(self, 'model') and str(model).endswith('.onnx'):
                if hasattr(self.model, 'half'):
                    self.model.half = lambda: self.model  # No-op for ONNX
            return result
        
        YOLO.__init__ = patched_init
        
        # Patch predict method to respect FP32 setting
        original_predict = YOLO.predict
        
        def patched_predict(self, source=None, **kwargs):
            # Force half=False for ONNX models
            if hasattr(self, 'ckpt_path') and str(self.ckpt_path).endswith('.onnx'):
                kwargs['half'] = False
            elif 'half' not in kwargs:
                # Use config setting
                from app.core.performance_config import INFERENCE_SETTINGS
                kwargs['half'] = INFERENCE_SETTINGS.get('half', False)
            return original_predict(self, source, **kwargs)
        
        YOLO.predict = patched_predict
        
        logging.getLogger("main").info("✅ ONNX FP32 patches applied successfully")
        
    except Exception as e:
        logging.getLogger("main").warning(f"⚠️ ONNX patch warning: {e}")

# Apply patches before importing other modules
apply_onnx_fp32_patches()

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.core.config import settings
from app.core.database import create_db_and_tables
from app.core.check_db import check_database_connection, test_database_query
from app.routers import detection, violations, videos
from app.routers import realtime_ws_binary  # Binary WS for 30 FPS
from app.routers import realtime_detection  # JSON WS for detection grid
from app.routers import auth as auth_router
from app.routers import ocr_image  # OCR Static Image API
from app.routers import traffic_light_ws  # Traffic Light Detection WS
from app.services.realtime_binary_stream import (
    preload_realtime_resources,
    DEFAULT_REALTIME_MODEL_PATH,
)

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

# Mount videos directory để serve video files
# FastAPI chạy từ traffic-server/, videos nằm ở traffic-server/videos/
from pathlib import Path

# Try multiple possible video directory paths (relative to traffic-server/)
possible_video_dirs = [
    Path(__file__).parent.parent / "videos",  # traffic-server/app/main.py -> traffic-server/videos/
    Path("videos"),  # Relative to current working directory
    Path("traffic-server/videos"),  # If running from parent directory
]

videos_dir = None
for video_dir in possible_video_dirs:
    if video_dir.exists() and video_dir.is_dir():
        videos_dir = str(video_dir.resolve())
        logger.info(f"📹 Found videos directory: {videos_dir}")
        break

if videos_dir:
    try:
        app.mount("/videos", StaticFiles(directory=videos_dir), name="videos")
        logger.info(f"✅ Mounted /videos endpoint to {videos_dir}")
    except Exception as e:
        logger.error(f"❌ Failed to mount /videos: {e}")
else:
    logger.warning("⚠️ Videos directory not found, /videos endpoint will not work")

# Register routers
app.include_router(detection.router, prefix=f"{settings.API_V1_PREFIX}/detection", tags=["Detection"])
app.include_router(violations.router, prefix=f"{settings.API_V1_PREFIX}/violations", tags=["Violations"])
app.include_router(videos.router, prefix=f"{settings.API_V1_PREFIX}/videos", tags=["Videos"])
# Binary realtime endpoint - 30 FPS with TurboJPEG + Multithreading
app.include_router(realtime_ws_binary.router, tags=["Realtime Binary"])
# JSON realtime detection - for detection grid view
app.include_router(realtime_detection.router, prefix=f"{settings.API_V1_PREFIX}/realtime", tags=["Realtime Detection"])
# OCR Static Image API
app.include_router(ocr_image.router, tags=["OCR"])
# Traffic Light Detection - Separate pipeline
app.include_router(traffic_light_ws.router, tags=["Traffic Light"])
# Auth routes
app.include_router(auth_router.router, prefix=f"{settings.API_V1_PREFIX}")


@app.on_event("startup")
def on_startup():
    """
    Khởi tạo database và tables khi ứng dụng start.
    """
    create_db_and_tables()
    
    # Print optimization summary
    logger.info("=" * 60)
    logger.info("🚀 TRAFFIC DETECTION SERVER - RTX 3050 OPTIMIZED")
    logger.info("=" * 60)
    
    # Show ONNX FP32 status
    from app.core.performance_config import INFERENCE_SETTINGS, FIXED_DETECT_INTERVAL, ENABLE_ADAPTIVE_INTERVAL
    precision_mode = "FP32" if not INFERENCE_SETTINGS.get('half', True) else "FP16"
    logger.info(f"🔧 Precision Mode: {precision_mode} (ONNX Compatible)")
    logger.info(f"⚡ Fixed Interval: {FIXED_DETECT_INTERVAL:.3f}s ({1/FIXED_DETECT_INTERVAL:.1f} FPS target)")
    logger.info(f"📊 Adaptive FPS: {'Disabled' if not ENABLE_ADAPTIVE_INTERVAL else 'Enabled'}")
    logger.info(f"🎯 Inference Size: {INFERENCE_SETTINGS.get('imgsz', 640)}px")
    logger.info(f"🔍 Confidence: {INFERENCE_SETTINGS.get('conf', 0.35)}")
    
    # Check GPU status
    try:
        import torch
        if torch.cuda.is_available():
            gpu_name = torch.cuda.get_device_name(0)
            logger.info(f"🎮 GPU: {gpu_name} (CUDA {torch.version.cuda})")
        else:
            logger.warning("⚠️ CUDA not available - falling back to CPU")
    except Exception:
        logger.warning("⚠️ Could not detect GPU status")
    
    logger.info("=" * 60)
    
    try:
        if preload_realtime_resources(DEFAULT_REALTIME_MODEL_PATH):
            logger.info("🚀 Realtime detection model preloaded on startup")
        else:
            logger.warning("⚠️  Skipped realtime detector preload (model missing or load error)")
    except Exception as exc:
        logger.error("❌ Failed to preload realtime detector: %s", exc)


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
    """
    Alias endpoint cho /api/auth/me (để tương thích với frontend)
    """
    from app.schemas.auth import UserResponse
    return UserResponse.model_validate(current_user)

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

