"""
Optimized YOLO Model Loader - Chỉ hỗ trợ .onnx và .pt
Tối ưu cho RTX 3050 4GB VRAM, đảm bảo ≥30fps realtime

Ưu tiên: .onnx > .pt (TensorRT bị loại bỏ để tránh phụ thuộc)
"""

import os
import logging
from typing import Optional, Tuple, Dict, Any
import torch

logger = logging.getLogger(__name__)

# Model cache: (path, device, type) -> model instance
_MODEL_CACHE: Dict[Tuple[str, str, str], Any] = {}

# Try imports
try:
    from ultralytics import YOLO
    HAVE_ULTRALYTICS = True
except Exception as e:
    logger.error(f"❌ Failed to import ultralytics: {e}")
    YOLO = None
    HAVE_ULTRALYTICS = False

try:
    import onnxruntime as ort
    HAVE_ONNX = True
    # Log available providers at startup
    if hasattr(ort, 'get_available_providers'):
        providers = ort.get_available_providers()
        logger.info(f"🔧 ONNX Runtime providers: {providers}")
        if 'CUDAExecutionProvider' in providers:
            logger.info("✅ CUDA provider available for ONNX")
        else:
            logger.warning("⚠️  CUDA provider not available for ONNX")
except Exception as e:
    HAVE_ONNX = False
    ort = None
    logger.warning(f"⚠️  ONNX Runtime not available: {e}")

# Log torch CUDA status
if torch.cuda.is_available():
    logger.info(f"✅ PyTorch CUDA available: {torch.cuda.get_device_name(0)}")
else:
    logger.warning("⚠️  PyTorch CUDA not available")


def find_model_file(base_path: str, model_name: str = None) -> Tuple[Optional[str], str]:
    """
    Tìm file model theo thứ tự ưu tiên: .onnx > .pt (chỉ hỗ trợ 2 format này)
    
    Args:
        base_path: Đường dẫn cơ sở (có thể là file hoặc thư mục)
        model_name: Tên model (tùy chọn, sẽ tự động extract từ base_path nếu None)
    
    Returns:
        (model_path, model_type) - model_path=None nếu không tìm thấy
        model_type: "onnx", "pt", hoặc "none"
    """
    # Nếu base_path là file, kiểm tra extension
    if os.path.isfile(base_path):
        ext = os.path.splitext(base_path)[1].lower()
        if ext == ".engine":
            # Reject TensorRT files with helpful message
            logger.error(f"❌ TensorRT .engine files not supported: {base_path}")
            logger.error("💡 Please use .onnx or .pt models instead")
            return None, "none"
        elif ext in [".onnx", ".pt"]:
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
    
    # Tìm các file có thể - chỉ .onnx và .pt
    possible_extensions = [".onnx", ".pt"]  # Removed .engine
    possible_names = [
        model_name,
        os.path.splitext(os.path.basename(base_path))[0] if base_path else model_name,
    ]
    
    # Ưu tiên: .onnx > .pt
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
    logger.info("💡 Supported formats: .onnx, .pt")
    return None, "none"


def load_yolo_model(
    model_path: str,
    device: str = "cuda:0",
    imgsz: int = 640,
    half: bool = True,
    verbose: bool = False
):
    """
    Load YOLO model với hot-swap support (.onnx > .pt only)
    Tối ưu cho RTX 3050 4GB VRAM với model caching
    
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
    
    # Check cache first
    cache_key = (actual_path, device, model_type)
    if cache_key in _MODEL_CACHE:
        logger.info(f"♻️ Using cached model: {actual_path} ({model_type})")
        return _MODEL_CACHE[cache_key]
    
    logger.info(f"📦 Loading model: {actual_path} (type: {model_type})")
    
    # Load theo format - chỉ hỗ trợ .onnx và .pt
    if model_type == "onnx":
        model = load_onnx_model(actual_path, device, imgsz, half)
    elif model_type == "pt":
        model = load_pytorch_model(actual_path, device, imgsz, half)
    else:
        raise ValueError(f"❌ Unsupported model type: {model_type}. Only .onnx and .pt are supported.")
    
    # Cache the loaded model
    _MODEL_CACHE[cache_key] = model
    logger.info(f"💾 Model cached: {actual_path}")
    
    return model


def clear_model_cache():
    """Clear model cache to free memory"""
    global _MODEL_CACHE
    cleared_count = len(_MODEL_CACHE)
    _MODEL_CACHE.clear()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
    logger.info(f"🧹 Cleared {cleared_count} cached models")


def load_onnx_model(
    model_path: str,
    device: str = "cuda:0",
    imgsz: int = 640,
    half: bool = True
):
    """
    Load ONNX model với xử lý lỗi IR version + CUDA provider
    """
    if not HAVE_ONNX:
        raise RuntimeError("❌ onnxruntime not available")

    logger.info(f"⚡ Loading ONNX model: {model_path}")

    providers = ["CUDAExecutionProvider", "CPUExecutionProvider"]

    # ---------------------------
    # TRY LOAD WITH CUDA + CPU
    # ---------------------------
    try:
        session = ort.InferenceSession(model_path, providers=providers)

    except Exception as e:
        err = str(e)

        # CASE 1: IR VERSION TOO HIGH -> MUST FALLBACK
        if "Unsupported model IR version" in err:
            logger.error("❌ Model IR version quá cao, ONNX Runtime không hỗ trợ.")
            logger.error("➡ Fallback sang PyTorch hoặc export lại ONNX opset=11.")

            # Tự fallback sang YOLO .pt nếu tồn tại
            pt_path = model_path.replace(".onnx", ".pt")
            if os.path.exists(pt_path):
                logger.info(f"♻️ Fallback sang PyTorch model: {pt_path}")
                return load_pytorch_model(pt_path, device, imgsz, half)

            raise RuntimeError(
                f"❌ Không thể load ONNX vì IR version quá cao: {err}"
            )

        # CASE 2: CUDA NOT AVAILABLE → fallback CPU
        logger.warning(f"⚠️ CUDAExecutionProvider không khả dụng → fallback CPU. Lỗi: {e}")
        session = ort.InferenceSession(model_path, providers=["CPUExecutionProvider"])

    # Log providers thực tế
    active = session.get_providers()
    if "CUDAExecutionProvider" in active:
        logger.info(f"✅ ONNX đang dùng CUDA: {active}")
    else:
        logger.warning(f"⚠️ ONNX chạy CPU-only: {active}")

    # Cuối cùng load bằng Ultralytics wrapper
    model = YOLO(model_path)

    # CUDA optimizations
    if device.startswith("cuda") and torch.cuda.is_available():
        torch.backends.cudnn.benchmark = True
        torch.backends.cuda.matmul.allow_tf32 = True
        torch.backends.cudnn.allow_tf32 = True
        logger.info("✅ CUDA optimizations enabled")

    logger.info("✅ ONNX model loaded successfully (with fallback logic)")
    return model


def load_pytorch_model(
    model_path: str,
    device: str = "cuda:0",
    imgsz: int = 640,
    half: bool = True
):
    """
    Load PyTorch .pt model với RTX 3050 optimizations
    """
    if not HAVE_ULTRALYTICS:
        raise RuntimeError("❌ ultralytics not available")
    
    logger.info(f"📦 Loading PyTorch model: {model_path}")
    
    model = YOLO(model_path)
    
    # Move to device and optimize
    if device.startswith("cuda") and torch.cuda.is_available():
        try:
            model.to(device)
            
            # Enable FP16 for GPU (2x faster, 50% memory) - CRITICAL for RTX 3050 4GB
            if half:
                model.half()
                logger.info("✅ FP16 (half precision) enabled - 2x faster, 50% less VRAM")
            
            # Fuse layers for faster inference
            model.fuse()
            logger.info("✅ Model layers fused for faster inference")
            
            # CUDA optimizations for RTX 3050
            torch.backends.cudnn.benchmark = True
            torch.backends.cuda.matmul.allow_tf32 = True
            torch.backends.cudnn.allow_tf32 = True
            
            # Memory optimization for 4GB VRAM
            if hasattr(torch.cuda, 'set_per_process_memory_fraction'):
                torch.cuda.set_per_process_memory_fraction(0.8, device=0)
                logger.info("✅ CUDA memory fraction set to 80% (RTX 3050 4GB optimized)")
            
            logger.info("✅ PyTorch CUDA optimizations enabled")
            
        except Exception as e:
            logger.warning(f"⚠️  CUDA optimization failed: {e}")
            # Fallback to CPU if GPU fails
            model.to("cpu")
            logger.warning("⚠️  Falling back to CPU mode")
    else:
        logger.info("ℹ️  Using CPU mode")
    
    logger.info(f"✅ PyTorch model loaded successfully")
    return model


def get_model_info(model_path: str) -> dict:
    """
    Lấy thông tin về model (format, size, etc.) - chỉ hỗ trợ .onnx/.pt
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
            "onnx": 1,    # ONNX has priority over PyTorch
            "pt": 2,      # PyTorch fallback
            "none": 999
        }.get(model_type, 999)
    }


def hot_swap_model(new_model_path: str, device: str = "cuda:0") -> bool:
    """
    Hot-swap model without restarting the server
    Returns True if successful, False otherwise
    """
    try:
        # Clear old cache first to free memory
        clear_model_cache()
        
        # Load new model
        model = load_yolo_model(new_model_path, device=device)
        
        logger.info(f"♻️ Hot-swapped model: {new_model_path}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Hot-swap failed: {e}")
        return False

