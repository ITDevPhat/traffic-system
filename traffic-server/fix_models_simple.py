#!/usr/bin/env python3
"""
Script sửa lỗi model loading đơn giản
"""

import os
from pathlib import Path

def fix_env_file():
    """Sửa file .env với đường dẫn model đúng"""
    print("🔧 FIXING .env FILE")
    print("=" * 40)
    
    env_content = """# Database - PostgreSQL Local
DATABASE_URL=postgresql+psycopg2://postgres:WGUw9ANk@localhost:5432/traffic-db

# Static files
STATIC_DIR=app/static/outputs

# Models - Fixed paths (ưu tiên .pt files)
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

# Performance - Tắt ONNX để tránh lỗi
DEVICE=cuda
FRAME_SKIP=15
FORCE_PT_MODELS=True
DISABLE_ONNX=True

# OCR Settings
USE_EASYOCR_FALLBACK=True
EASYOCR_LANGUAGES=["vi", "en"]

# Features
ENABLE_RED_LIGHT_DETECTION=True
ENABLE_STOP_LINE_DETECTION=False
ENABLE_WRONG_LANE_DETECTION=False

# API Settings
PROJECT_NAME=Traffic Violation Detection API - LVTN
VERSION=2.0.0
API_V1_PREFIX=/api
BACKEND_CORS_ORIGINS=["http://localhost:3000","http://localhost:8000"]
"""
    
    with open(".env", "w", encoding="utf-8") as f:
        f.write(env_content)
    
    print("✅ .env file updated với PT models")

def check_models():
    """Kiểm tra models có tồn tại không"""
    print("\n🔍 CHECKING MODELS")
    print("=" * 40)
    
    models = {
        "Vehicle": "models/vehicle/v10m/yolo_vehicle_v10m.pt",
        "Plate": "models/license_plate/yolo_plate_v10n.pt", 
        "OCR": "models/ocr/yolo_ocr_chars_v10n.pt",
        "Traffic Light": "models/traffic_light/yolo_trafficlight_v10n.pt"
    }
    
    all_good = True
    for name, path in models.items():
        if Path(path).exists():
            size = Path(path).stat().st_size / (1024*1024)
            print(f"✅ {name}: {path} ({size:.1f} MB)")
        else:
            print(f"❌ {name}: {path} - MISSING!")
            all_good = False
    
    return all_good

def create_run_script():
    """Tạo script chạy server đơn giản"""
    print("\n🚀 CREATING RUN SCRIPT")
    print("=" * 40)
    
    run_content = """@echo off
echo 🚦 Starting Traffic System - LVTN
echo ================================

echo 🔧 Activating conda environment...
call conda activate LVTN

echo 🚀 Starting FastAPI server...
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

pause
"""
    
    with open("run_server.bat", "w", encoding="utf-8") as f:
        f.write(run_content)
    
    print("✅ Created run_server.bat")

def main():
    """Main function"""
    print("🔧 TRAFFIC SYSTEM - SIMPLE MODEL FIX")
    print("=" * 50)
    
    fix_env_file()
    models_ok = check_models()
    create_run_script()
    
    print("\n" + "=" * 50)
    if models_ok:
        print("✅ TẤT CẢ MODELS OK!")
        print("\n🚀 Để chạy server:")
        print("   1. Double-click run_server.bat")
        print("   2. Hoặc chạy: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload")
        print("\n🌐 Truy cập:")
        print("   - API: http://localhost:8000")
        print("   - Docs: http://localhost:8000/docs")
    else:
        print("❌ THIẾU MODELS - Cần copy models vào đúng thư mục")

if __name__ == "__main__":
    main()