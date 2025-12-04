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
