"""
FastAPI Router - License Plate Recognition API
Module con để tích hợp vào FastAPI app chính
"""

from fastapi import APIRouter, File, UploadFile, HTTPException, Form
from fastapi.responses import StreamingResponse, JSONResponse
import cv2
import numpy as np
import io
import base64
from typing import Dict, Any, Optional
import time

# Import core module - hỗ trợ cả relative và absolute import
try:
    from .core import create_detector
except ImportError:
    from core import create_detector

try:
    from .core_optimized import create_detector_optimized
except ImportError:
    try:
        from core_optimized import create_detector_optimized
    except ImportError:
        create_detector_optimized = None

# Tạo router
router = APIRouter(
    prefix="/ocr",
    tags=["OCR"],
    responses={404: {"description": "Not found"}},
)

# DISABLED: Auto-loading models on import (use plate_ocr_service.py instead)
# This router is for standalone OCR API mode only
# When integrated into main app, use app.services.plate_ocr_service

# Lazy loading: models sẽ được load khi cần (on first request)
detectors = {}
detector = None

def _lazy_load_models():
    """Lazy load models on first request (standalone mode only)"""
    global detectors, detector
    
    if detectors:  # Already loaded
        return
    
    print("Loading OCR models (standalone mode)...")
    import torch
    if torch.cuda.is_available():
        print(f"✅ CUDA available! GPU: {torch.cuda.get_device_name(0)}")
        print(f"   GPU Memory: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.1f}GB")
        device = "cuda"
    else:
        print("⚠️  CUDA not available, using CPU")
        device = "cpu"
    
    # Load detectors cho từng model type
    try:
        from .core import create_detector
        detectors['pt'] = create_detector("default", device=device)
        print(f"✅ PyTorch model loaded on {detectors['pt'].device.upper()}!")
    except Exception as e:
        print(f"⚠️  Failed to load PyTorch model: {e}")
    
    try:
        if create_detector_optimized:
            detectors['onnx'] = create_detector_optimized(model_type='onnx', device=device)
            print(f"✅ ONNX model loaded!")
    except Exception as e:
        print(f"⚠️  Failed to load ONNX model: {e}")
    
    try:
        if create_detector_optimized:
            detectors['engine'] = create_detector_optimized(model_type='engine', device=device)
            print(f"✅ TensorRT engine loaded!")
    except Exception as e:
        print(f"⚠️  Failed to load TensorRT engine: {e}")
    
    # Default detector (PyTorch)
    detector = detectors.get('pt', None)
    if detector is None and len(detectors) > 0:
        detector = list(detectors.values())[0]


@router.get("/")
async def root():
    """Homepage - API info"""
    return {
        "name": "License Plate Recognition API",
        "version": "2.0.0",
        "status": "running",
        "device": detector.device if detector else "unknown",
        "available_models": list(detectors.keys()),
        "endpoints": {
            "/ocr/detect": "POST - Nhận dạng biển số từ ảnh (multipart)",
            "/ocr/detect_base64": "POST - Nhận dạng biển số từ base64 (nhanh hơn)",
            "/ocr/detect_with_image": "POST - Nhận dạng và trả về ảnh có bbox",
            "/ocr/health": "GET - Health check",
            "/ocr/stats": "GET - Thống kê",
            "/docs": "GET - API documentation (Swagger UI)"
        }
    }


@router.get("/health")
async def health_check():
    """Health check endpoint"""
    device_info = detector.get_device_info() if detector else {}
    return {
        "status": "healthy",
        "device": device_info.get('device', 'unknown'),
        "cuda_available": device_info.get('cuda_available', False),
        "gpu_name": device_info.get('gpu_name', 'N/A'),
        "available_models": list(detectors.keys())
    }


@router.get("/stats")
async def get_stats():
    """Lấy thống kê hệ thống"""
    if detector:
        stats = detector.get_stats()
        return stats
    return {"error": "No detector available"}


@router.post("/detect_base64")
async def detect_plate_base64(
    image_base64: str = Form(...),
    draw_bbox: bool = Form(False),
    confidence_threshold: float = Form(0.60),
    model_type: str = Form("pt")
) -> Dict[str, Any]:
    """
    Nhận dạng biển số từ base64 (NHANH HƠN - giảm network overhead)
    
    Args:
        image_base64: Ảnh dạng base64 string
        draw_bbox: Có vẽ bounding box không
        confidence_threshold: Ngưỡng confidence (0-1)
        model_type: Loại model ("pt", "onnx", "engine")
    
    Returns:
        JSON response với thông tin biển số
    """
    try:
        timings = {}
        
        # Decode base64 (nhanh hơn multipart)
        timings['decode_start'] = time.time()
        image_bytes = base64.b64decode(image_base64)
        nparr = np.frombuffer(image_bytes, np.uint8)
        image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        timings['decode_time'] = time.time() - timings['decode_start']
        
        if image is None:
            raise HTTPException(status_code=400, detail="Invalid image data")
        
        # Resize nếu quá lớn
        h, w = image.shape[:2]
        max_dimension = 1920
        if max(h, w) > max_dimension:
            scale = max_dimension / max(h, w)
            new_w = int(w * scale)
            new_h = int(h * scale)
            image = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_AREA)
        
        # Chọn detector
        current_detector = detectors.get(model_type, detector)
        if current_detector is None:
            raise HTTPException(status_code=400, detail=f"Model type '{model_type}' not available")
        
        # Process
        original_threshold = current_detector.confidence_threshold
        current_detector.confidence_threshold = confidence_threshold
        
        timings['inference_start'] = time.time()
        result = current_detector.process_image(image, draw_bbox=draw_bbox)
        timings['inference_time'] = time.time() - timings['inference_start']
        
        current_detector.confidence_threshold = original_threshold
        
        # Format response
        response = {
            "success": result['success'],
            "processing_time": timings['inference_time'],
            "model_type": model_type,
            "image_size": {
                "width": image.shape[1],
                "height": image.shape[0]
            },
            "plates_detected": len(result['plates_detected']),
            "plates_recognized": len(result['plates_recognized']),
            "plates": [],
            "timings": timings
        }
        
        for plate in result['plates_recognized']:
            xmin, ymin, xmax, ymax = plate['bbox']
            response['plates'].append({
                "text": plate['text'],
                "confidence": round(float(plate['confidence']), 4),
                "bbox": {
                    "x": float(xmin),
                    "y": float(ymin),
                    "width": float(xmax - xmin),
                    "height": float(ymax - ymin),
                    "xmin": float(xmin),
                    "ymin": float(ymin),
                    "xmax": float(xmax),
                    "ymax": float(ymax)
                }
            })
        
        return response
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/detect")
async def detect_plate(
    file: UploadFile = File(...),
    draw_bbox: bool = False,
    confidence_threshold: float = 0.60,
    model_type: str = "pt"  # "pt", "onnx", "engine"
) -> Dict[str, Any]:
    """
    Nhận dạng biển số từ ảnh (multipart form)
    
    Args:
        file: File ảnh (JPG, PNG)
        draw_bbox: Có vẽ bounding box không
        confidence_threshold: Ngưỡng confidence (0-1)
        model_type: Loại model ("pt", "onnx", "engine")
    
    Returns:
        JSON response với thông tin biển số
    """
    try:
        # Đo thời gian từng bước để debug
        timings = {}
        
        # Đọc file upload (tối ưu: đọc một lần)
        timings['read_start'] = time.time()
        contents = await file.read()
        timings['read_time'] = time.time() - timings['read_start']
        timings['file_size'] = len(contents) / 1024  # KB
        
        # Decode ảnh (tối ưu: sử dụng flag để decode nhanh hơn)
        timings['decode_start'] = time.time()
        nparr = np.frombuffer(contents, np.uint8)
        # Sử dụng IMREAD_REDUCED_COLOR_2 nếu ảnh quá lớn để decode nhanh hơn
        image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        timings['decode_time'] = time.time() - timings['decode_start']
        
        if image is None:
            raise HTTPException(status_code=400, detail="Invalid image file")
        
        # Resize ảnh nếu quá lớn (giảm processing time)
        h, w = image.shape[:2]
        max_dimension = 1920  # Giới hạn kích thước
        if max(h, w) > max_dimension:
            scale = max_dimension / max(h, w)
            new_w = int(w * scale)
            new_h = int(h * scale)
            timings['resize_start'] = time.time()
            image = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_AREA)
            timings['resize_time'] = time.time() - timings['resize_start']
        
        # Chọn detector dựa trên model_type
        current_detector = detectors.get(model_type, detector)
        if current_detector is None:
            raise HTTPException(status_code=400, detail=f"Model type '{model_type}' not available")
        
        # Update confidence threshold nếu cần
        original_threshold = current_detector.confidence_threshold
        current_detector.confidence_threshold = confidence_threshold
        
        # Nhận dạng
        timings['inference_start'] = time.time()
        result = current_detector.process_image(image, draw_bbox=draw_bbox)
        timings['inference_time'] = time.time() - timings['inference_start']
        
        processing_time = timings['inference_time']
        
        # Restore threshold
        current_detector.confidence_threshold = original_threshold
        
        # Format response
        response = {
            "success": result['success'],
            "processing_time": processing_time,
            "model_type": model_type,
            "image_size": {
                "width": image.shape[1],
                "height": image.shape[0]
            },
            "plates_detected": len(result['plates_detected']),
            "plates_recognized": len(result['plates_recognized']),
            "plates": [],
            "timings": timings  # Thêm chi tiết timing
        }
        
        # Thêm thông tin từng biển số đã trích xuất
        for plate in result['plates_recognized']:
            xmin, ymin, xmax, ymax = plate['bbox']
            response['plates'].append({
                "text": plate['text'],  # Thông tin trích xuất biển số
                "confidence": round(float(plate['confidence']), 4),  # Độ tin cậy
                "bbox": {  # Vùng bbox nhận diện ra
                    "x": float(xmin),
                    "y": float(ymin),
                    "width": float(xmax - xmin),
                    "height": float(ymax - ymin),
                    "xmin": float(xmin),
                    "ymin": float(ymin),
                    "xmax": float(xmax),
                    "ymax": float(ymax)
                }
            })
        
        return response
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/detect_with_image")
async def detect_plate_with_image(
    file: UploadFile = File(...),
    confidence_threshold: float = 0.60,
    model_type: str = "pt"
):
    """
    Nhận dạng biển số và trả về ảnh có bbox
    
    Returns:
        Image với bounding boxes vẽ sẵn
    """
    try:
        # Đọc file upload
        contents = await file.read()
        nparr = np.frombuffer(contents, np.uint8)
        image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if image is None:
            raise HTTPException(status_code=400, detail="Invalid image file")
        
        # Resize nếu quá lớn
        h, w = image.shape[:2]
        max_dimension = 1920
        if max(h, w) > max_dimension:
            scale = max_dimension / max(h, w)
            new_w = int(w * scale)
            new_h = int(h * scale)
            image = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_AREA)
        
        # Chọn detector
        current_detector = detectors.get(model_type, detector)
        if current_detector is None:
            raise HTTPException(status_code=400, detail=f"Model type '{model_type}' not available")
        
        # Update confidence threshold
        original_threshold = current_detector.confidence_threshold
        current_detector.confidence_threshold = confidence_threshold
        
        # Nhận dạng với bbox
        result = current_detector.process_image(image, draw_bbox=True, draw_stats=True)
        
        # Restore threshold
        current_detector.confidence_threshold = original_threshold
        
        # Convert ảnh sang bytes để trả về
        _, buffer = cv2.imencode('.jpg', result['image'], [cv2.IMWRITE_JPEG_QUALITY, 85])
        io_buf = io.BytesIO(buffer)
        
        return StreamingResponse(io_buf, media_type="image/jpeg")
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/benchmark")
async def benchmark():
    """
    Benchmark hiệu suất hệ thống
    """
    try:
        # Tạo ảnh test
        test_image = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
        
        # Chạy benchmark
        if detector:
            result = detector.benchmark_device(test_image)
            
            return {
                "device": result['device'],
                "detection_time": result['detection_time'],
                "ocr_time": result['ocr_time'],
                "total_time": result['total_time'],
                "fps": result['fps']
            }
        else:
            return {"error": "No detector available"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
