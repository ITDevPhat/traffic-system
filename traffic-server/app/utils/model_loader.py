"""
Unified YOLO Model Loader - Hỗ trợ .pt, .onnx, .engine
Tối ưu cho RTX 3050 4GB VRAM, đảm bảo >30fps

Ưu tiên: .engine (TensorRT) > .onnx > .pt
"""

import os
import logging
from typing import Optional, Tuple
import torch

logger = logging.getLogger(__name__)

# Try imports
try:
    from ultralytics import YOLO
    HAVE_ULTRALYTICS = True
except Exception as e:
    logger.error(f"Failed to import ultralytics: {e}")
    YOLO = None
    HAVE_ULTRALYTICS = False

try:
    import onnxruntime as ort
    HAVE_ONNX = True
except Exception:
    HAVE_ONNX = False
    ort = None

try:
    import tensorrt as trt
    HAVE_TENSORRT = True
except Exception:
    HAVE_TENSORRT = False
    trt = None


def find_model_file(base_path: str, model_name: str = None) -> Tuple[Optional[str], str]:
    """
    Tìm file model theo thứ tự ưu tiên: .engine > .onnx > .pt
    
    Args:
        base_path: Đường dẫn cơ sở (có thể là file hoặc thư mục)
        model_name: Tên model (tùy chọn, sẽ tự động extract từ base_path nếu None)
    
    Returns:
        (model_path, model_type) - model_path=None nếu không tìm thấy
        model_type: "engine", "onnx", "pt", hoặc "none"
    """
    # Nếu base_path là file, dùng trực tiếp
    if os.path.isfile(base_path):
        ext = os.path.splitext(base_path)[1].lower()
        if ext in [".engine", ".onnx", ".pt"]:
            return base_path, ext[1:]  # Remove dot
    
    # Extract model_name từ base_path nếu không có
    if model_name is None:
        model_name = os.path.splitext(os.path.basename(base_path))[0]
    
    # Xác định thư mục tìm kiếm
    if os.path.isdir(base_path):
        model_dir = base_path
    else:
        # Lấy thư mục chứa base_path
        model_dir = os.path.dirname(base_path) if base_path else "models"
    
    # Tìm các file có thể
    possible_extensions = [".engine", ".onnx", ".pt"]
    possible_names = [
        model_name,
        os.path.splitext(os.path.basename(base_path))[0] if base_path else model_name,
    ]
    
    # Ưu tiên: .engine > .onnx > .pt
    for ext in possible_extensions:
        for name in possible_names:
            # Try exact match trong thư mục hiện tại
            model_path = os.path.join(model_dir, name + ext)
            if os.path.exists(model_path):
                return model_path, ext[1:]
            
            # Try với subdirectories (vehicle/v10m, vehicle/11s, license_plate, etc.)
            for subdir in ["vehicle/v10m", "vehicle/11s", "license_plate", "ocr", "traffic_light"]:
                model_path = os.path.join(model_dir, subdir, name + ext)
                if os.path.exists(model_path):
                    return model_path, ext[1:]
            
            # Try trong thư mục models trực tiếp
            if not model_dir.endswith("models"):
                models_root = os.path.join(os.path.dirname(model_dir), "models")
                if os.path.exists(models_root):
                    for subdir in ["vehicle/v10m", "vehicle/11s", "license_plate", "ocr", "traffic_light", ""]:
                        if subdir:
                            model_path = os.path.join(models_root, subdir, name + ext)
                        else:
                            model_path = os.path.join(models_root, name + ext)
                        if os.path.exists(model_path):
                            return model_path, ext[1:]
    
    logger.warning(f"⚠️  Model not found: {model_name} in {model_dir}")
    return None, "none"


def load_yolo_model(
    model_path: str,
    device: str = "cuda:0",
    imgsz: int = 640,
    half: bool = True,
    verbose: bool = False
):
    """
    Load YOLO model với auto-detect format (.engine > .onnx > .pt)
    Tối ưu cho RTX 3050 4GB VRAM
    
    Args:
        model_path: Đường dẫn model (có thể là file hoặc thư mục)
        device: "cuda:0" hoặc "cpu"
        imgsz: Input image size
        half: Use FP16 (cho GPU) - BẮT BUỘC cho RTX 3050 4GB
        verbose: Log chi tiết
    
    Returns:
        Model object (YOLO wrapper)
    """
    # Tìm file model
    actual_path, model_type = find_model_file(model_path)
    
    if actual_path is None:
        raise FileNotFoundError(f"Model not found: {model_path}")
    
    logger.info(f"📦 Loading model: {actual_path} (type: {model_type})")
    
    # Load theo format
    if model_type == "engine":
        return load_tensorrt_model(actual_path, device, imgsz, half)
    elif model_type == "onnx":
        return load_onnx_model(actual_path, device, imgsz, half)
    elif model_type == "pt":
        return load_pytorch_model(actual_path, device, imgsz, half)
    else:
        raise ValueError(f"Unsupported model type: {model_type}")


def load_tensorrt_model(
    model_path: str,
    device: str = "cuda:0",
    imgsz: int = 640,
    half: bool = True
):
    """
    Load TensorRT .engine model
    Tối ưu nhất cho RTX 3050 4GB
    """
    if not HAVE_ULTRALYTICS:
        raise RuntimeError("ultralytics not available")
    
    logger.info(f"🚀 Loading TensorRT engine: {model_path}")
    
    # YOLO có thể load .engine trực tiếp
    model = YOLO(model_path)
    
    # Move to device
    if device.startswith("cuda"):
        model.to(device)
        if torch.cuda.is_available():
            try:
                # Enable FP16
                if half:
                    model.half()
                # Optimize
                model.fuse()
                # Set CUDA optimizations
                torch.backends.cudnn.benchmark = True
                torch.backends.cuda.matmul.allow_tf32 = True
                torch.backends.cudnn.allow_tf32 = True
            except Exception as e:
                logger.warning(f"CUDA optimization failed: {e}")
    
    logger.info(f"✅ TensorRT model loaded successfully")
    return model


def load_onnx_model(
    model_path: str,
    device: str = "cuda:0",
    imgsz: int = 640,
    half: bool = True
):
    """
    Load ONNX model với ONNX Runtime
    Tối ưu cho GPU với ExecutionProvider
    """
    if not HAVE_ULTRALYTICS:
        raise RuntimeError("ultralytics not available")
    
    logger.info(f"⚡ Loading ONNX model: {model_path}")
    
    # YOLO có thể load .onnx trực tiếp
    model = YOLO(model_path)
    
    # Move to device
    if device.startswith("cuda"):
        model.to(device)
        if torch.cuda.is_available():
            try:
                # Enable FP16
                if half:
                    model.half()
                # Optimize
                model.fuse()
                # Set CUDA optimizations
                torch.backends.cudnn.benchmark = True
                torch.backends.cuda.matmul.allow_tf32 = True
                torch.backends.cudnn.allow_tf32 = True
            except Exception as e:
                logger.warning(f"CUDA optimization failed: {e}")
    
    logger.info(f"✅ ONNX model loaded successfully")
    return model


def load_pytorch_model(
    model_path: str,
    device: str = "cuda:0",
    imgsz: int = 640,
    half: bool = True
):
    """
    Load PyTorch .pt model (fallback)
    """
    if not HAVE_ULTRALYTICS:
        raise RuntimeError("ultralytics not available")
    
    logger.info(f"📦 Loading PyTorch model: {model_path}")
    
    model = YOLO(model_path)
    
    # Move to device
    if device.startswith("cuda"):
        model.to(device)
        if torch.cuda.is_available():
            try:
                # Enable FP16 for GPU (2x faster, 50% memory)
                if half:
                    model.half()
                # Fuse layers for faster inference
                model.fuse()
                # CUDA optimizations
                torch.backends.cudnn.benchmark = True
                torch.backends.cuda.matmul.allow_tf32 = True
                torch.backends.cudnn.allow_tf32 = True
            except Exception as e:
                logger.warning(f"CUDA optimization failed: {e}")
    
    logger.info(f"✅ PyTorch model loaded successfully")
    return model


def get_model_info(model_path: str) -> dict:
    """
    Lấy thông tin về model (format, size, etc.)
    """
    actual_path, model_type = find_model_file(model_path)
    
    if actual_path is None:
        return {
            "found": False,
            "path": model_path,
            "type": "none",
            "size_mb": 0,
            "priority": 999
        }
    
    size_mb = os.path.getsize(actual_path) / (1024 * 1024)
    
    return {
        "found": True,
        "path": actual_path,
        "type": model_type,
        "size_mb": round(size_mb, 2),
        "priority": {
            "engine": 1,
            "onnx": 2,
            "pt": 3,
            "none": 999
        }.get(model_type, 999)
    }

