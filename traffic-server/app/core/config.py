from pydantic_settings import BaseSettings
from typing import Optional
import os


class Settings(BaseSettings):
    """
    Cấu hình ứng dụng FastAPI cho hệ thống phát hiện vi phạm giao thông.
    
    Các biến môi trường được load từ file .env trong thư mục gốc.
    """
    DATABASE_URL: str = "postgresql+psycopg2://postgres:postgres@localhost:5432/traffic_db"
    STATIC_DIR: str = "app/static/outputs"
    
    # ============================================
    # 🧠 Multiple YOLO Models Configuration
    # Auto-detect format: .engine > .onnx > .pt
    # ============================================
    # Base paths (without extension) - sẽ auto-detect .engine/.onnx/.pt
    MODELS_DIR: str = os.path.join(os.path.dirname(__file__), "..", "..", "models")
    
    # Vehicle model selection: "v10m" (chính xác cao) hoặc "11s" (nhanh hơn)
    VEHICLE_MODEL_VERSION: str = os.getenv("VEHICLE_MODEL_VERSION", "v10m")  # v10m | 11s
    
    # Dynamic vehicle model path based on version
    @property
    def vehicle_model_path(self) -> str:
        if self.VEHICLE_MODEL_VERSION == "11s":
            return os.path.join(self.MODELS_DIR, "vehicle", "11s", "yolo_vehicle_11s")
        else:  # default v10m
            return os.path.join(self.MODELS_DIR, "vehicle", "v10m", "yolo_vehicle_v10m")
    
    YOLO_VEHICLE_MODEL: str = None  # Will be set dynamically
    YOLO_PLATE_MODEL: str = os.path.join(MODELS_DIR, "license_plate", "yolo_plate_v10n")
    YOLO_OCR_MODEL: str = os.path.join(MODELS_DIR, "ocr", "yolo_ocr_chars_v8n")
    YOLO_TRAFFIC_LIGHT_MODEL: str = os.path.join(MODELS_DIR, "traffic_light", "yolo_trafficlight_v10n")
    
    # ============================================
    # ⚙️ Inference Configuration
    # ============================================
    INFERENCE_CONFIDENCE_VEHICLE: float = 0.5
    INFERENCE_CONFIDENCE_PLATE: float = 0.5
    INFERENCE_CONFIDENCE_OCR: float = 0.25
    INFERENCE_CONFIDENCE_LIGHT: float = 0.5
    
    # GPU/CPU
    DEVICE: str = "cuda"  # cuda hoặc cpu, auto-detect nếu không có GPU
    
    # Frame sampling (xử lý 1 frame mỗi N frame để tăng tốc)
    FRAME_SKIP: int = 15  # Ví dụ: 30 FPS → xử lý 2 FPS
    
    # ============================================
    # 🔍 EasyOCR Fallback
    # ============================================
    USE_EASYOCR_FALLBACK: bool = True
    EASYOCR_LANGUAGES: list = ["en"]  # Có thể thêm "vi" nếu cần
    
    # ============================================
    # 🧩 Modular pipeline toggles
    # ============================================
    MODULE_ENABLE_ROI: bool = True
    MODULE_ENABLE_ROI_DRAWING: bool = True
    MODULE_ENABLE_ROI_JSON: bool = False
    ROI_JSON_PATH: Optional[str] = None
    MODULE_ENABLE_VEHICLE_YOLO: bool = True
    MODULE_ENABLE_BYTETRACK: bool = True
    MODULE_ENABLE_DRAW_BBOX: bool = True

    # ============================================
    # 🚦 Violation Detection Settings
    # ============================================
    ENABLE_RED_LIGHT_DETECTION: bool = True
    ENABLE_STOP_LINE_DETECTION: bool = False  # Cần ROI polygon
    ENABLE_WRONG_LANE_DETECTION: bool = False  # Future
    
    # API Config
    API_V1_PREFIX: str = "/api"
    PROJECT_NAME: str = "Traffic Violation Detection API"
    VERSION: str = "1.1.0"
    
    # ============================================
    # 🔐 Auth / JWT Settings
    # ============================================
    JWT_SECRET: str = os.getenv("JWT_SECRET", "CHANGE_ME_SECRET")
    ACCESS_TOKEN_EXPIRE_DAYS: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_DAYS", "7"))
    COOKIE_SECURE: bool = bool(int(os.getenv("COOKIE_SECURE", "0")))  # 1 on prod with HTTPS
    COOKIE_SAMESITE: str = os.getenv("COOKIE_SAMESITE", "lax")  # lax|strict|none
    
    # CORS - Allow frontend origins
    BACKEND_CORS_ORIGINS: list = [
        "http://localhost:3000",
        "http://localhost:3001",
        "http://localhost:3002",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3001",
        "http://127.0.0.1:3002",
    ]
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()

# Set vehicle model path dynamically
settings.YOLO_VEHICLE_MODEL = settings.vehicle_model_path

