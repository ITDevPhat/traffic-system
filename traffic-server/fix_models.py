#!/usr/bin/env python3
"""
Script sửa lỗi model loading và ONNX compatibility
"""

import os
import shutil
from pathlib import Path

def fix_env_file():
    """Sửa file .env với đường dẫn model đúng"""
    print("🔧 FIXING .env FILE")
    print("=" * 40)
    
    env_content = """# Database - PostgreSQL Local
DATABASE_URL=postgresql+psycopg2://postgres:WGUw9ANk@localhost:5432/traffic-db

# Static files
STATIC_DIR=app/static/outputs

# Models - Fixed paths
YOLO_VEHICLE_MODEL=models/vehicle/v10m/yolo_vehicle_v10m.pt
YOLO_PLATE_MODEL=models/license_plate/yolo_plate_v10n.pt
YOLO_OCR_MODEL=models/ocr/yolo_ocr_chars_v10n.pt
YOLO_TRAFFIC_LIGHT_MODEL=models/traffic_light/yolo_trafficlight_v10n.pt

# Model version selection
VEHICLE_MODEL_VERSION=v10m

# Inference confidence thresholds
INFERENCE_CONFIDENCE_VEHICLE=0.35
INFERENCE_CONFIDENCE_PLATE=0.35
INFERENCE_CONFIDENCE_LIGHT=0.4
INFERENCE_CONFIDENCE_OCR=0.35

# Performance - Force PT models to avoid ONNX issues
DEVICE=cuda
FRAME_SKIP=15
FORCE_PT_MODELS=True

# OCR Settings
USE_EASYOCR_FALLBACK=True
EASYOCR_LANGUAGES=["vi", "en"]

# Features
ENABLE_RED_LIGHT_DETECTION=True
ENABLE_STOP_LINE_DETECTION=False
ENABLE_WRONG_LANE_DETECTION=False

# API Settings
PROJECT_NAME=Traffic Violation Detection API
VERSION=2.0.0
API_V1_PREFIX=/api
BACKEND_CORS_ORIGINS=["http://localhost:3000","http://localhost:8000"]
"""
    
    with open(".env", "w", encoding="utf-8") as f:
        f.write(env_content)
    
    print("✅ .env file updated")

def create_model_loader_fix():
    """Tạo file fix cho model loading"""
    print("\n🔧 CREATING MODEL LOADER FIX")
    print("=" * 40)
    
    fix_content = '''"""
Model Loading Fix - Ưu tiên .pt models thay vì ONNX
"""

import os
from pathlib import Path
from typing import Optional

def get_best_model_path(base_path: str) -> Optional[str]:
    """
    Tìm model tốt nhất theo thứ tự ưu tiên:
    1. .pt (PyTorch - ổn định nhất)
    2. .engine (TensorRT - nhanh nhưng cần GPU tương thích)
    3. .onnx (ONNX - có thể có lỗi compatibility)
    
    Args:
        base_path: Đường dẫn base không có extension
        
    Returns:
        Đường dẫn model tốt nhất hoặc None
    """
    extensions = ['.pt', '.engine', '.onnx']
    
    for ext in extensions:
        model_path = base_path + ext
        if Path(model_path).exists():
            print(f"✅ Found model: {model_path}")
            return model_path
    
    print(f"❌ No model found for base path: {base_path}")
    return None

def load_model_safe(model_path: str, device: str = "cuda"):
    """
    Load model an toàn với fallback
    """
    try:
        from ultralytics import YOLO
        
        # Force sử dụng .pt nếu có
        base_path = str(Path(model_path).with_suffix(''))
        best_path = get_best_model_path(base_path)
        
        if not best_path:
            raise FileNotFoundError(f"No model found for {model_path}")
        
        print(f"🔄 Loading model: {best_path}")
        model = YOLO(best_path)
        
        # Set device
        if device == "cuda" and not torch.cuda.is_available():
            print("⚠️ CUDA not available, using CPU")
            device = "cpu"
        
        model.to(device)
        print(f"✅ Model loaded on {device}")
        
        return model
        
    except Exception as e:
        print(f"❌ Error loading model {model_path}: {e}")
        raise

# Patch cho config.py
def patch_config():
    """Patch config để ưu tiên .pt models"""
    import app.core.config as config
    
    # Override model paths để ưu tiên .pt
    original_vehicle_path = config.settings.YOLO_VEHICLE_MODEL
    if original_vehicle_path and not original_vehicle_path.endswith('.pt'):
        base_path = str(Path(original_vehicle_path).with_suffix(''))
        pt_path = base_path + '.pt'
        if Path(pt_path).exists():
            config.settings.YOLO_VEHICLE_MODEL = pt_path
            print(f"✅ Switched to PT model: {pt_path}")
'''
    
    fix_dir = Path("app/core")
    fix_dir.mkdir(parents=True, exist_ok=True)
    
    with open(fix_dir / "model_loader_fix.py", "w", encoding="utf-8") as f:
        f.write(fix_content)
    
    print("✅ Model loader fix created")

def create_startup_script():
    """Tạo script khởi động với fix"""
    print("\n🔧 CREATING STARTUP SCRIPT")
    print("=" * 40)
    
    startup_content = '''#!/usr/bin/env python3
"""
Startup script với model fixes
"""

import os
import sys
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

def apply_fixes():
    """Apply all fixes before starting server"""
    print("🔧 Applying model fixes...")
    
    # Force PT models
    os.environ['FORCE_PT_MODELS'] = 'True'
    os.environ['KMP_DUPLICATE_LIB_OK'] = 'TRUE'
    
    # Disable ONNX by default
    os.environ['DISABLE_ONNX'] = 'True'
    
    print("✅ Fixes applied")

def main():
    """Main startup function"""
    print("🚦 STARTING TRAFFIC SYSTEM WITH FIXES")
    print("=" * 50)
    
    apply_fixes()
    
    # Import and run FastAPI
    try:
        import uvicorn
        from app.main import app
        
        print("🚀 Starting server on http://0.0.0.0:8000")
        uvicorn.run(
            app,
            host="0.0.0.0",
            port=8000,
            reload=True,
            log_level="info"
        )
        
    except Exception as e:
        print(f"❌ Error starting server: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
'''
    
    with open("start_fixed.py", "w", encoding="utf-8") as f:
        f.write(startup_content)
    
    print("✅ Startup script created: start_fixed.py")

def main():
    """Main function"""
    print("🔧 TRAFFIC SYSTEM - MODEL FIXES")
    print("=" * 50)
    
    # Change to traffic-server directory if needed
    if Path("traffic-server").exists() and not Path("models").exists():
        os.chdir("traffic-server")
        print("📁 Changed to traffic-server directory")
    
    fix_env_file()
    create_model_loader_fix()
    create_startup_script()
    
    print("\n" + "=" * 50)
    print("✅ TẤT CẢ FIXES ĐÃ ĐƯỢC ÁP DỤNG!")
    print("\n🚀 Để chạy server với fixes:")
    print("   cd traffic-server")
    print("   conda activate LVTN")
    print("   python start_fixed.py")
    print("\n💡 Hoặc chạy bình thường:")
    print("   uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload")

if __name__ == "__main__":
    main()
'''