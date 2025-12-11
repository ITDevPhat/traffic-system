"""
Detection Configuration
Cấu hình confidence threshold và detection settings cho từng loại phương tiện
"""

# Confidence thresholds cho từng class
# Giá trị càng cao = càng chặt chẽ (ít false positive nhưng có thể miss detection)
# Giá trị càng thấp = càng nhạy (nhiều detection nhưng có thể có false positive)
CLASS_CONFIDENCE_THRESHOLDS = {
    "bus": 0.70,        # Bus: 40% - Dễ nhận diện (kích thước lớn)
    "car": 0.4,        # Car: 35% - Standard (phổ biến nhất)
    "bike": 0.25,       # Bike: 30% - Khó hơn (kích thước nhỏ, nhiều góc nhìn)
    "truck": 0.70,      # Truck: 40% - Dễ nhận diện (kích thước lớn)
}

# Global confidence threshold (fallback)
DEFAULT_CONFIDENCE = 0.35

# IOU threshold cho NMS (Non-Maximum Suppression)
# Giá trị càng thấp = loại bỏ overlap nhiều hơn
IOU_THRESHOLD = 0.45

# Detection settings
DETECTION_SETTINGS = {
    # Confidence thresholds
    "confidence": {
        "default": DEFAULT_CONFIDENCE,
        "per_class": CLASS_CONFIDENCE_THRESHOLDS,
    },
    
    # NMS settings
    "nms": {
        "iou_threshold": IOU_THRESHOLD,
        "max_detections": 300,  # Max số detection per frame
    },
    
    # ✅ FIX 4: NỚI LỎNG SIZE FILTER - giảm min size để không mất detection
    "size_filter": {
        "min_width": 10,    # Giảm từ 20 -> 10 để giữ xe máy xa
        "min_height": 10,   # Giảm từ 20 -> 10 để giữ xe máy xa
        "max_width": 2000,  # Max bbox width
        "max_height": 2000, # Max bbox height
    },
    
    # ✅ FIX 4: NỚI LỎNG ASPECT RATIO - tránh loại detection khi xe quay góc
    "aspect_ratio": {
        "min": 0.1,   # Giảm từ 0.2 -> 0.1 để giữ xe đứng
        "max": 10.0,  # Tăng từ 5.0 -> 10.0 để giữ xe ngang
    },
}


def get_confidence_threshold(class_name: str) -> float:
    """
    Get confidence threshold cho class
    
    Args:
        class_name: Tên class (bus, car, bike, truck)
        
    Returns:
        Confidence threshold (0.0 - 1.0)
    """
    return CLASS_CONFIDENCE_THRESHOLDS.get(class_name.lower(), DEFAULT_CONFIDENCE)


def should_keep_detection(
    class_name: str,
    confidence: float,
    bbox_width: float,
    bbox_height: float
) -> bool:
    """
    Kiểm tra detection có nên giữ lại không
    
    Args:
        class_name: Tên class
        confidence: Confidence score
        bbox_width: Bbox width
        bbox_height: Bbox height
        
    Returns:
        True nếu nên giữ detection
    """
    # Check confidence
    threshold = get_confidence_threshold(class_name)
    if confidence < threshold:
        return False
    
    # Check size
    size_filter = DETECTION_SETTINGS["size_filter"]
    if bbox_width < size_filter["min_width"] or bbox_width > size_filter["max_width"]:
        return False
    if bbox_height < size_filter["min_height"] or bbox_height > size_filter["max_height"]:
        return False
    
    # Check aspect ratio
    aspect_ratio = bbox_width / bbox_height if bbox_height > 0 else 0
    ar_filter = DETECTION_SETTINGS["aspect_ratio"]
    if aspect_ratio < ar_filter["min"] or aspect_ratio > ar_filter["max"]:
        return False
    
    return True


# ✅ INFERENCE SETTINGS - Cấu hình suy luận YOLO/ONNX
INFERENCE_SETTINGS = {
    # Dùng FP32 mặc định để tránh lỗi dtype half/float khi chạy CUDA/CPU
    # Nếu sau này muốn tối ưu hơn mới bật half-precision cho mô hình phù hợp.
    "half": False,
    # Kích thước suy luận mặc định (frontend vẫn gửi imgsz riêng)
    "default_imgsz": 640,
}

# ✅ DETECTION INTERVAL SETTINGS - Cấu hình tần suất detect
# Bật/tắt adaptive interval (tự điều chỉnh theo FPS thực tế)
ENABLE_ADAPTIVE_INTERVAL = False  # Để False cho ổn định, dùng fixed interval

# Interval cố định giữa các lần chạy YOLO (giây)
# 1/30 ≈ 0.033s ~ 30Hz. Nếu target_fps là 15 thì backend vẫn đủ nhanh.
FIXED_DETECT_INTERVAL = 1.0 / 30.0

# ✅ WEBSOCKET FPS SETTINGS - Cấu hình FPS cho WebSocket streaming
WS_DEFAULT_FPS = 15     # FPS mặc định cho WebSocket
WS_MAX_FPS = 30         # FPS tối đa cho WebSocket
WS_MIN_FPS = 5          # FPS tối thiểu cho WebSocket
TARGET_FPS = 15         # Target FPS cho streaming

# ✅ BYTETRACK SETTINGS - Cấu hình tracking
BYTETRACK_SETTINGS = {
    "track_thresh": 0.5,        # Threshold để bắt đầu track
    "track_buffer": 30,         # Số frame buffer cho track
    "match_thresh": 0.8,        # Threshold để match detection với track
    "frame_rate": 30,           # FPS của video
    "mot20": False,             # MOT20 format
}

# ✅ TRACK SMOOTHING SETTINGS - Cấu hình làm mượt track
TRACK_SMOOTHING_SETTINGS = {
    "enabled": True,            # Bật/tắt smoothing
    "window_size": 5,           # Số frame để smooth
    "min_track_length": 3,      # Độ dài track tối thiểu
    "position_alpha": 0.7,      # Alpha cho position smoothing
    "size_alpha": 0.5,          # Alpha cho size smoothing
}

# ✅ OCR SETTINGS - Cấu hình OCR biển số
OCR_SETTINGS = {
    "enabled": True,            # Bật/tắt OCR
    "confidence_threshold": 0.6, # Threshold confidence cho OCR
    "min_plate_width": 50,      # Chiều rộng tối thiểu của biển số
    "min_plate_height": 20,     # Chiều cao tối thiểu của biển số
    "max_plate_width": 300,     # Chiều rộng tối đa của biển số
    "max_plate_height": 150,    # Chiều cao tối đa của biển số
    "preprocessing": {
        "resize_factor": 2.0,   # Factor để resize ảnh trước OCR
        "blur_kernel": 3,       # Kernel size cho blur
        "sharpen": True,        # Bật/tắt sharpen
    }
}


def print_performance_config():
    """
    In ra cấu hình performance hiện tại
    """
    print("=== PERFORMANCE CONFIGURATION ===")
    print(f"Detection Settings: {DETECTION_SETTINGS}")
    print(f"Inference Settings: {INFERENCE_SETTINGS}")
    print(f"ByteTrack Settings: {BYTETRACK_SETTINGS}")
    print(f"Track Smoothing: {TRACK_SMOOTHING_SETTINGS}")
    print(f"OCR Settings: {OCR_SETTINGS}")
    print(f"WebSocket FPS: Default={WS_DEFAULT_FPS}, Max={WS_MAX_FPS}, Min={WS_MIN_FPS}")
    print(f"Target FPS: {TARGET_FPS}")
    print(f"Adaptive Interval: {ENABLE_ADAPTIVE_INTERVAL}")
    print(f"Fixed Detect Interval: {FIXED_DETECT_INTERVAL}")
    print("=================================")