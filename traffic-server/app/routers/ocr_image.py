"""
FastAPI Router - OCR Static Image API
Module để nhận dạng biển số từ ảnh tĩnh

FIX: Multi-scale detection để xử lý biển số quá lớn/gần camera
"""

from fastapi import APIRouter, File, UploadFile, Form, HTTPException
from typing import Dict, Any, Optional, List, Tuple
import cv2
import numpy as np
import time
import logging

from app.modules.OCR import LicensePlateDetectorOptimized

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/ocr",
    tags=["OCR Image"],
    responses={404: {"description": "Not found"}},
)

# Initialize OCR detector (singleton pattern)
ocr_detector = None

def get_ocr_detector():
    """Get or initialize OCR detector"""
    global ocr_detector
    if ocr_detector is None:
        try:
            ocr_detector = LicensePlateDetectorOptimized(
                detector_model_path='models/license_plate/yolo_plate_v10n.pt',
                ocr_model_path='models/ocr/yolo_ocr_chars_v10n.pt',
                model_type='auto',
                confidence_threshold=0.60,
                device='auto'
            )
            logger.info("✅ OCR detector initialized successfully")
        except Exception as e:
            logger.error(f"❌ Failed to initialize OCR detector: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to initialize OCR detector: {str(e)}"
            )
    
    return ocr_detector


def add_black_padding(image: np.ndarray, target_size: int = 640, pad_color: Tuple[int, int, int] = (0, 0, 0)) -> Tuple[np.ndarray, float, Tuple[int, int]]:
    """
    Thêm padding đen 4 bên để ảnh nhỏ có context giống training data.
    Letterbox style - giữ nguyên tỷ lệ ảnh gốc, thêm padding để đạt target_size.
    
    Args:
        image: Ảnh gốc
        target_size: Kích thước mục tiêu (vuông)
        pad_color: Màu padding (mặc định đen)
    
    Returns:
        (padded_image, scale_used, (pad_x, pad_y))
    """
    h, w = image.shape[:2]
    
    if h == 0 or w == 0:
        return image, 1.0, (0, 0)
    
    # Tính scale để fit vào target_size mà giữ tỷ lệ
    scale = min(target_size / w, target_size / h)
    
    # Resize ảnh
    new_w = int(w * scale)
    new_h = int(h * scale)
    
    if scale < 1:
        resized = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_AREA)
    else:
        resized = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_LINEAR)
    
    # Tạo canvas đen với target_size
    canvas = np.full((target_size, target_size, 3), pad_color, dtype=np.uint8)
    
    # Tính vị trí để đặt ảnh vào giữa canvas
    pad_x = (target_size - new_w) // 2
    pad_y = (target_size - new_h) // 2
    
    # Đặt ảnh vào giữa canvas
    canvas[pad_y:pad_y + new_h, pad_x:pad_x + new_w] = resized
    
    return canvas, scale, (pad_x, pad_y)


def normalize_plate_size(plate_crop: np.ndarray, target_height: int = 80) -> np.ndarray:
    """
    Normalize biển số về kích thước phù hợp với training data.
    Biển số quá lớn sẽ được resize xuống để OCR hoạt động tốt hơn.
    
    Args:
        plate_crop: Ảnh biển số đã crop
        target_height: Chiều cao mục tiêu (80-120px thường tốt cho OCR)
    
    Returns:
        Ảnh đã normalize
    """
    h, w = plate_crop.shape[:2]
    
    if h == 0 or w == 0:
        return plate_crop
    
    # Tính scale factor để đưa về target_height
    scale = target_height / h
    new_w = int(w * scale)
    new_h = target_height
    
    # Resize với interpolation phù hợp
    if scale < 1:
        # Shrink - dùng INTER_AREA để giảm aliasing
        resized = cv2.resize(plate_crop, (new_w, new_h), interpolation=cv2.INTER_AREA)
    else:
        # Enlarge - dùng INTER_LINEAR
        resized = cv2.resize(plate_crop, (new_w, new_h), interpolation=cv2.INTER_LINEAR)
    
    return resized


def multi_scale_ocr(detector, plate_crop: np.ndarray) -> Tuple[str, float]:
    """
    Thử OCR với nhiều scale khác nhau để tìm kết quả tốt nhất.
    Giải quyết vấn đề biển số quá lớn/nhỏ so với training data.
    
    Args:
        detector: OCR detector instance
        plate_crop: Ảnh biển số đã crop
    
    Returns:
        (license_plate_text, confidence)
    """
    h, w = plate_crop.shape[:2]
    
    # Các target height để thử (từ nhỏ đến lớn)
    # Training data thường có biển số ~60-120px height
    target_heights = [60, 80, 100, 120, 150]
    
    best_result = "unknown"
    best_confidence = 0.0
    best_char_count = 0
    
    for target_h in target_heights:
        try:
            # Normalize về target height
            normalized = normalize_plate_size(plate_crop, target_h)
            
            # Thử OCR
            result = detector.recognize_license_plate(normalized)
            
            if result and result != "unknown":
                # Đánh giá chất lượng kết quả
                # Biển số VN thường có 7-9 ký tự (không tính dấu -)
                clean_result = result.replace("-", "")
                char_count = len(clean_result)
                
                # Ưu tiên kết quả có 7-9 ký tự
                is_valid_length = 7 <= char_count <= 9
                
                # Tính confidence dựa trên độ dài và format
                confidence = 0.5  # Base confidence
                if is_valid_length:
                    confidence += 0.3
                if char_count >= 7:
                    confidence += 0.1
                if "-" in result:  # Có format 2 dòng
                    confidence += 0.1
                
                # Cập nhật best result
                if confidence > best_confidence or (confidence == best_confidence and char_count > best_char_count):
                    best_result = result
                    best_confidence = confidence
                    best_char_count = char_count
                    
                    logger.debug(f"🔍 Scale {target_h}px: '{result}' (conf={confidence:.2f}, chars={char_count})")
                    
                    # Nếu đã tìm được kết quả tốt, dừng sớm
                    if is_valid_length and confidence >= 0.8:
                        break
                        
        except Exception as e:
            logger.debug(f"⚠️ Scale {target_h}px failed: {e}")
            continue
    
    return best_result, best_confidence


def is_plate_too_large(bbox: List[float], image_shape: Tuple[int, int]) -> bool:
    """
    Kiểm tra biển số có quá lớn so với ảnh không.
    Biển số chiếm >30% diện tích ảnh thường là quá gần camera.
    """
    img_h, img_w = image_shape[:2]
    img_area = img_h * img_w
    
    plate_w = bbox[2] - bbox[0]
    plate_h = bbox[3] - bbox[1]
    plate_area = plate_w * plate_h
    
    ratio = plate_area / img_area
    return ratio > 0.15  # >15% diện tích ảnh


@router.post("/image")
async def ocr_image(
    file: UploadFile = File(..., description="Image file for license plate recognition"),
    confidence_threshold: Optional[float] = Form(0.60, description="Confidence threshold (0-1)"),
    draw_bbox: Optional[bool] = Form(False, description="Draw bounding boxes on result"),
    return_padded_image: Optional[bool] = Form(True, description="Return padded image for small images (better visualization)")
) -> Dict[str, Any]:
    """
    Nhận dạng biển số từ ảnh tĩnh
    
    Args:
        file: File ảnh (JPG, PNG, etc.)
        confidence_threshold: Ngưỡng confidence (0-1)
        draw_bbox: Có vẽ bounding box không
        return_padded_image: Trả về ảnh đã padding (cho ảnh nhỏ)
    
    Returns:
        JSON response với thông tin biển số nhận dạng được
    """
    start_time = time.time()
    
    try:
        # Validate file type
        if not file.content_type or not file.content_type.startswith('image/'):
            raise HTTPException(
                status_code=400,
                detail="File phải là ảnh (JPG, PNG, etc.)"
            )
        
        # Read and decode image
        logger.info(f"📸 Processing image: {file.filename}")
        contents = await file.read()
        
        if len(contents) == 0:
            raise HTTPException(status_code=400, detail="File ảnh trống")
        
        # Decode image
        nparr = np.frombuffer(contents, np.uint8)
        image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if image is None:
            raise HTTPException(status_code=400, detail="Không thể đọc file ảnh")
        
        # Get original dimensions
        h, w = image.shape[:2]
        original_h, original_w = h, w
        scale_factor = 1.0
        used_padding = False
        pad_info = None
        
        # Resize if too large (optimize processing)
        max_dimension = 1920
        if max(h, w) > max_dimension:
            scale_factor = max_dimension / max(h, w)
            new_w = int(w * scale_factor)
            new_h = int(h * scale_factor)
            image = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_AREA)
            h, w = image.shape[:2]
            logger.info(f"🔄 Resized image from {original_w}x{original_h} to {new_w}x{new_h}")
        
        # Nếu ảnh quá nhỏ (< 300px), thêm padding đen để detect tốt hơn
        # Ảnh nhỏ thường là ảnh crop biển số, cần context để YOLO detect
        min_dimension = 300
        if max(h, w) < min_dimension:
            logger.info(f"📏 Small image detected ({w}x{h}px), adding black padding...")
            image, pad_scale, (pad_x, pad_y) = add_black_padding(image, target_size=640)
            used_padding = True
            pad_info = {
                'pad_scale': pad_scale,
                'pad_x': pad_x,
                'pad_y': pad_y,
                'original_w': w,
                'original_h': h
            }
            logger.info(f"✅ Padded to 640x640 (scale={pad_scale:.2f}, offset=({pad_x},{pad_y}))")
        
        # Get OCR detector
        detector = get_ocr_detector()
        
        # Update confidence threshold
        original_threshold = detector.confidence_threshold
        detector.confidence_threshold = confidence_threshold
        
        # Process image - detect plates first
        inference_start = time.time()
        
        # Step 1: Detect license plates
        plates_detected = detector.detect_license_plates(image)
        
        plates_recognized = []
        
        if len(plates_detected) == 0:
            # Không tìm thấy biển số
            logger.info("📸 No plates detected in initial scan...")
            
            # Nếu chưa thử padding, thử thêm padding và detect lại
            if not used_padding:
                logger.info("🔄 Trying with black padding...")
                padded_img, pad_scale, (pad_x, pad_y) = add_black_padding(image, target_size=640)
                plates_detected = detector.detect_license_plates(padded_img)
                
                if len(plates_detected) > 0:
                    logger.info(f"✅ Found {len(plates_detected)} plates after padding!")
                    # Chuyển đổi bbox về tọa độ ảnh gốc
                    for i, plate in enumerate(plates_detected):
                        # Trừ padding offset và chia scale
                        plates_detected[i] = [
                            (plate[0] - pad_x) / pad_scale,
                            (plate[1] - pad_y) / pad_scale,
                            (plate[2] - pad_x) / pad_scale,
                            (plate[3] - pad_y) / pad_scale,
                            plate[4] if len(plate) > 4 else 1.0,
                            plate[5] if len(plate) > 5 else 0
                        ]
            
            # Nếu vẫn không detect được, thử OCR trực tiếp
            if len(plates_detected) == 0:
                logger.info("📸 Still no plates, trying direct OCR on full image...")
                
                # Thử multi-scale OCR trên toàn ảnh (có thể là ảnh chỉ chứa biển số)
                text, conf = multi_scale_ocr(detector, image)
                
                if text != "unknown":
                    plates_recognized.append({
                        'text': text,
                        'bbox': [0, 0, image.shape[1], image.shape[0]],
                        'confidence': conf,
                        'method': 'direct_ocr'
                    })
                    logger.info(f"✅ Direct OCR: '{text}' (conf={conf:.2f})")
        else:
            # Step 2: OCR từng biển số với multi-scale
            for plate in plates_detected:
                bbox = plate[:4]
                det_conf = plate[4] if len(plate) > 4 else 1.0
                
                # Crop biển số
                x1, y1, x2, y2 = int(bbox[0]), int(bbox[1]), int(bbox[2]), int(bbox[3])
                x1 = max(0, x1)
                y1 = max(0, y1)
                x2 = min(image.shape[1], x2)
                y2 = min(image.shape[0], y2)
                
                plate_crop = image[y1:y2, x1:x2]
                
                if plate_crop.size == 0:
                    continue
                
                # Kiểm tra biển số có quá lớn không
                plate_is_large = is_plate_too_large(bbox, image.shape)
                
                if plate_is_large:
                    # Biển số lớn -> dùng multi-scale OCR
                    logger.info(f"📏 Large plate detected ({x2-x1}x{y2-y1}px), using multi-scale OCR...")
                    text, ocr_conf = multi_scale_ocr(detector, plate_crop)
                else:
                    # Biển số bình thường -> OCR trực tiếp
                    text = detector.recognize_license_plate(plate_crop)
                    ocr_conf = det_conf
                
                if text and text != "unknown":
                    plates_recognized.append({
                        'text': text,
                        'bbox': bbox,
                        'confidence': ocr_conf,
                        'method': 'multi_scale' if plate_is_large else 'standard'
                    })
                    logger.info(f"✅ Plate OCR: '{text}' (method={'multi_scale' if plate_is_large else 'standard'})")
        
        inference_time = time.time() - inference_start
        
        # Restore original threshold
        detector.confidence_threshold = original_threshold
        
        # Prepare response
        total_time = time.time() - start_time
        
        response = {
            "success": len(plates_recognized) > 0 or len(plates_detected) > 0,
            "processing_time": round(inference_time, 4),
            "total_time": round(total_time, 4),
            "image_info": {
                "filename": file.filename,
                "original_size": {"width": original_w, "height": original_h},
                "processed_size": {"width": image.shape[1], "height": image.shape[0]},
                "scale_factor": round(scale_factor, 4),
                "used_padding": used_padding,
                "padding_info": pad_info
            },
            "detection_results": {
                "plates_detected": len(plates_detected),
                "plates_recognized": len(plates_recognized)
            },
            "plates": []
        }
        
        # Add recognized plates with scaled coordinates
        for plate in plates_recognized:
            bbox = plate['bbox']
            if scale_factor != 1.0:
                bbox = [
                    bbox[0] / scale_factor,
                    bbox[1] / scale_factor,
                    bbox[2] / scale_factor,
                    bbox[3] / scale_factor
                ]
            
            plate_info = {
                "text": plate['text'],
                "confidence": round(float(plate['confidence']), 4),
                "method": plate.get('method', 'standard'),
                "bbox": {
                    "x1": round(float(bbox[0]), 2),
                    "y1": round(float(bbox[1]), 2),
                    "x2": round(float(bbox[2]), 2),
                    "y2": round(float(bbox[3]), 2),
                    "width": round(float(bbox[2] - bbox[0]), 2),
                    "height": round(float(bbox[3] - bbox[1]), 2)
                }
            }
            response['plates'].append(plate_info)
        
        # Add padded image to response if requested and image was small
        if return_padded_image and used_padding:
            try:
                import base64
                # Encode padded image to base64
                _, buffer = cv2.imencode('.jpg', image, [cv2.IMWRITE_JPEG_QUALITY, 90])
                img_base64 = base64.b64encode(buffer).decode('utf-8')
                response['padded_image'] = {
                    'data': f'data:image/jpeg;base64,{img_base64}',
                    'width': image.shape[1],
                    'height': image.shape[0],
                    'note': 'Ảnh đã được thêm padding đen để dễ nhìn hơn'
                }
                logger.info("📸 Padded image included in response")
            except Exception as e:
                logger.warning(f"⚠️ Failed to encode padded image: {e}")
        
        # Log results
        if response['plates']:
            plates_text = [p['text'] for p in response['plates']]
            logger.info(f"✅ OCR Success: Found {len(plates_text)} plates: {plates_text}")
        else:
            logger.info("⚠️ No license plates detected")
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ OCR processing error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Lỗi khi xử lý ảnh: {str(e)}"
        )


@router.get("/health")
async def ocr_health_check():
    """
    Health check cho OCR module
    """
    try:
        detector = get_ocr_detector()
        stats = detector.get_stats() if hasattr(detector, 'get_stats') else {}
        
        return {
            "status": "healthy",
            "ocr_available": True,
            "device": getattr(detector, 'device', 'unknown'),
            "model_type": getattr(detector, 'model_type', 'unknown'),
            "stats": stats
        }
    except Exception as e:
        return {
            "status": "error",
            "ocr_available": False,
            "error": str(e)
        }


@router.get("/")
async def ocr_info():
    """
    Thông tin về OCR API
    """
    return {
        "name": "OCR Static Image API",
        "version": "1.0.0",
        "description": "API nhận dạng biển số từ ảnh tĩnh",
        "endpoints": {
            "/api/ocr/image": "POST - Nhận dạng biển số từ ảnh",
            "/api/ocr/health": "GET - Kiểm tra trạng thái OCR",
            "/api/ocr/": "GET - Thông tin API"
        },
        "supported_formats": ["JPG", "JPEG", "PNG", "BMP", "TIFF"],
        "max_image_size": "1920px (auto-resize)",
        "features": [
            "Automatic license plate detection",
            "Vietnamese license plate OCR",
            "Confidence scoring",
            "Bounding box coordinates",
            "Auto image resizing"
        ]
    }