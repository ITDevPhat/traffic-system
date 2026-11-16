#!/usr/bin/env python3
"""
Script kiểm tra và sửa lỗi model loading
Chạy script này để debug model paths và ONNX compatibility
"""

import os
import sys
from pathlib import Path

def check_model_files():
    """Kiểm tra các file model có tồn tại không"""
    print("🔍 KIỂM TRA MODEL FILES")
    print("=" * 50)
    
    models_dir = Path("models")
    if not models_dir.exists():
        print("❌ Thư mục models không tồn tại!")
        return False
    
    # Các model paths theo cấu hình mới
    model_paths = {
        "Vehicle": "models/vehicle/v10m/yolo_vehicle_v10m.pt",
        "License Plate": "models/license_plate/yolo_plate_v10n.pt", 
        "OCR": "models/ocr/yolo_ocr_chars_v10n.pt",
        "Traffic Light": "models/traffic_light/yolo_trafficlight_v10n.pt"
    }
    
    all_exist = True
    for name, path in model_paths.items():
        if Path(path).exists():
            size = Path(path).stat().st_size / (1024*1024)  # MB
            print(f"✅ {name}: {path} ({size:.1f} MB)")
        else:
            print(f"❌ {name}: {path} - KHÔNG TỒN TẠI")
            all_exist = False
    
    return all_exist

def check_onnx_compatibility():
    """Kiểm tra ONNX runtime compatibility"""
    print("\n🔧 KIỂM TRA ONNX COMPATIBILITY")
    print("=" * 50)
    
    try:
        import onnxruntime as ort
        print(f"✅ ONNXRuntime installed: {ort.__name__}")
        
        # Kiểm tra providers
        providers = ort.get_available_providers()
        print(f"✅ Available providers: {providers}")
        
        if 'CUDAExecutionProvider' in providers:
            print("✅ CUDA provider available")
        else:
            print("⚠️ CUDA provider not available - sẽ dùng CPU")
            
    except ImportError:
        print("❌ ONNXRuntime chưa được cài đặt")
        print("💡 Chạy: pip install onnxruntime-gpu")
        return False
    
    return True

def test_model_loading():
    """Test loading các model"""
    print("\n🧪 TEST MODEL LOADING")
    print("=" * 50)
    
    try:
        from ultralytics import YOLO
        
        # Test vehicle model
        vehicle_path = "models/vehicle/v10m/yolo_vehicle_v10m.pt"
        if Path(vehicle_path).exists():
            print(f"🔄 Loading {vehicle_path}...")
            model = YOLO(vehicle_path)
            print(f"✅ Vehicle model loaded successfully")
            print(f"   - Classes: {len(model.names)} classes")
            print(f"   - Names: {list(model.names.values())}")
        else:
            print(f"❌ Vehicle model not found: {vehicle_path}")
            
    except Exception as e:
        print(f"❌ Error loading model: {e}")
        return False
    
    return True

def check_gpu_status():
    """Kiểm tra GPU status"""
    print("\n🎮 KIỂM TRA GPU STATUS")
    print("=" * 50)
    
    try:
        import torch
        print(f"✅ PyTorch version: {torch.__version__}")
        print(f"✅ CUDA available: {torch.cuda.is_available()}")
        
        if torch.cuda.is_available():
            print(f"✅ CUDA version: {torch.version.cuda}")
            print(f"✅ GPU count: {torch.cuda.device_count()}")
            for i in range(torch.cuda.device_count()):
                name = torch.cuda.get_device_name(i)
                print(f"   - GPU {i}: {name}")
        else:
            print("⚠️ CUDA not available - sẽ dùng CPU")
            
    except ImportError:
        print("❌ PyTorch chưa được cài đặt")
        return False
    
    return True

def check_config_files():
    """Kiểm tra config files"""
    print("\n⚙️ KIỂM TRA CONFIG FILES")
    print("=" * 50)
    
    # Check .env
    if Path(".env").exists():
        print("✅ .env file exists")
        with open(".env", "r") as f:
            lines = f.readlines()
            for line in lines:
                if line.startswith("YOLO_") and "MODEL" in line:
                    print(f"   {line.strip()}")
    else:
        print("❌ .env file not found")
    
    # Check config.py
    config_path = Path("app/core/config.py")
    if config_path.exists():
        print("✅ config.py exists")
    else:
        print("❌ config.py not found")

def main():
    """Main function"""
    print("🚦 TRAFFIC SYSTEM - MODEL DIAGNOSTIC")
    print("=" * 60)
    
    # Change to traffic-server directory if needed
    if Path("traffic-server").exists() and not Path("models").exists():
        os.chdir("traffic-server")
        print("📁 Changed to traffic-server directory")
    
    success = True
    success &= check_model_files()
    success &= check_onnx_compatibility() 
    success &= check_gpu_status()
    success &= test_model_loading()
    check_config_files()
    
    print("\n" + "=" * 60)
    if success:
        print("✅ TẤT CẢ KIỂM TRA THÀNH CÔNG!")
        print("💡 Hệ thống sẵn sàng chạy")
    else:
        print("❌ CÓ LỖI CẦN SỬA")
        print("💡 Xem log ở trên để biết cách sửa")
    
    print("\n🚀 Để chạy server:")
    print("   cd traffic-server")
    print("   conda activate LVTN") 
    print("   uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload")

if __name__ == "__main__":
    main()