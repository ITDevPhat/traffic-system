"""
Detection Service - Full Multi-YOLO + ByteTrack + OCR Pipeline

Pipeline (module-based):
1. ROI Module → Load ROI from DB/JSON & optional overlay
2. YOLO Vehicle Module → Detect vehicles (with optional ByteTrack)
3. Plate Module → Detect & OCR license plates (YOLO + EasyOCR fallback)
4. Traffic Light Module → Detect traffic light status
5. Violation Logic → Combine all to detect violations
6. Drawing Module → Render annotations (optional)
7. Persistence → Save evidence + DB records

Author: Traffic System Team
Version: 2.0.0 (ByteTrack Integration)
"""

import os
import uuid
import cv2
import torch
import numpy as np
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from ultralytics import YOLO

from sqlmodel import Session, select

from app.core.config import settings
from app.models.violation import Violation
from app.models.vehicle import Vehicle
from app.models.video_job import VideoJob, JobStatus

from app.modules import (
    ModuleContext,
    ROIModule,
    VehicleYOLOModule,
    BoundingBoxDrawerModule,
)
from app.utils.model_loader import load_yolo_model, get_model_info
from app.utils.plate_utils import (
    deskew_and_crop,
    split_two_lines,
    normalize_plate_text,
    validate_plate,
    format_plate_display,
    preprocess_plate_for_ocr,
    is_two_line_plate
)
from app.utils.roi_utils import (
    centroid_of_bbox,
    point_in_polygon,
)

logger = logging.getLogger("detection_service")

# ============================================
# 🔧 GPU Configuration
# ============================================
torch.backends.cudnn.benchmark = True
DEVICE = settings.DEVICE if torch.cuda.is_available() else "cpu"
logger.info(f"🖥️  Using device: {DEVICE}")

# ============================================
# 🧠 Load YOLO Models (Singleton Pattern)
# Unified loader: .engine > .onnx > .pt
# ============================================
class YOLOModelsV2:
    """
    Singleton class để load tất cả YOLO models + ByteTrack tracker.
    
    V3: Unified loader hỗ trợ .engine (TensorRT) > .onnx > .pt
    Tối ưu cho RTX 3050 4GB VRAM, đảm bảo >30fps
    """
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        logger.info("📦 Loading YOLO models (auto-detect: .engine > .onnx > .pt)...")
        
        try:
            # Vehicle detection
            vehicle_info = get_model_info(settings.YOLO_VEHICLE_MODEL)
            if vehicle_info["found"]:
                self.vehicle = load_yolo_model(
                    vehicle_info["path"],
                    device=DEVICE,
                    imgsz=640,
                    half=True,
                    verbose=False
                )
                logger.info(f"✅ Vehicle model loaded: {vehicle_info['path']} ({vehicle_info['type']}, {vehicle_info['size_mb']}MB)")
            else:
                logger.warning(f"⚠️  Vehicle model not found: {settings.YOLO_VEHICLE_MODEL}")
                self.vehicle = None
            
            # Plate detection
            plate_info = get_model_info(settings.YOLO_PLATE_MODEL)
            if plate_info["found"]:
                self.plate = load_yolo_model(
                    plate_info["path"],
                    device=DEVICE,
                    imgsz=640,
                    half=True,
                    verbose=False
                )
                logger.info(f"✅ Plate model loaded: {plate_info['path']} ({plate_info['type']}, {plate_info['size_mb']}MB)")
            else:
                logger.warning(f"⚠️  Plate model not found: {settings.YOLO_PLATE_MODEL}")
                self.plate = None
            
            # OCR detection
            ocr_info = get_model_info(settings.YOLO_OCR_MODEL)
            if ocr_info["found"]:
                self.ocr = load_yolo_model(
                    ocr_info["path"],
                    device=DEVICE,
                    imgsz=640,
                    half=True,
                    verbose=False
                )
                logger.info(f"✅ OCR model loaded: {ocr_info['path']} ({ocr_info['type']}, {ocr_info['size_mb']}MB)")
            else:
                logger.warning(f"⚠️  OCR model not found: {settings.YOLO_OCR_MODEL}")
                self.ocr = None
            
            # Traffic light detection
            light_info = get_model_info(settings.YOLO_TRAFFIC_LIGHT_MODEL)
            if light_info["found"]:
                self.traffic_light = load_yolo_model(
                    light_info["path"],
                    device=DEVICE,
                    imgsz=640,
                    half=True,
                    verbose=False
                )
                logger.info(f"✅ Traffic light model loaded: {light_info['path']} ({light_info['type']}, {light_info['size_mb']}MB)")
            else:
                logger.warning(f"⚠️  Traffic light model not found: {settings.YOLO_TRAFFIC_LIGHT_MODEL}")
                self.traffic_light = None
            
            self._initialized = True
            
            # Summary
            loaded = sum([
                self.vehicle is not None,
                self.plate is not None,
                self.ocr is not None,
                self.traffic_light is not None
            ])
            logger.info(f"🎉 {loaded}/4 models loaded successfully!")
            
            # GPU memory check
            if torch.cuda.is_available():
                try:
                    vram_gb = torch.cuda.get_device_properties(0).total_memory / (1024 ** 3)
                    allocated_gb = torch.cuda.memory_allocated(0) / (1024 ** 3)
                    logger.info(f"💾 GPU VRAM: {allocated_gb:.2f}GB / {vram_gb:.2f}GB allocated")
                except Exception as e:
                    logger.debug(f"GPU memory check failed: {e}")
            
        except Exception as e:
            logger.error(f"❌ Error loading models: {e}", exc_info=True)
            raise

# Global models instance
try:
    models = YOLOModelsV2()
except Exception as e:
    logger.error(f"Failed to initialize YOLO models: {e}")
    models = None

# ============================================
# 🔍 EasyOCR Fallback (Lazy Load)
# ============================================
_easyocr_reader = None

def get_easyocr_reader():
    """Lazy load EasyOCR reader."""
    global _easyocr_reader
    if _easyocr_reader is None and settings.USE_EASYOCR_FALLBACK:
        try:
            import easyocr
            _easyocr_reader = easyocr.Reader(
                settings.EASYOCR_LANGUAGES,
                gpu=torch.cuda.is_available()
            )
            logger.info("✅ EasyOCR reader initialized")
        except Exception as e:
            logger.warning(f"⚠️  EasyOCR initialization failed: {e}")
    return _easyocr_reader


def ocr_with_easyocr(plate_crop: np.ndarray) -> str:
    """
    Sử dụng EasyOCR để đọc biển số khi YOLO OCR thất bại.
    
    Args:
        plate_crop: numpy array của vùng biển số
    
    Returns:
        Chuỗi biển số, hoặc "UNKNOWN" nếu không đọc được
    """
    try:
        reader = get_easyocr_reader()
        if reader is None:
            return "UNKNOWN"
        
        # Preprocess
        plate_crop = preprocess_plate_for_ocr(plate_crop)
        
        results = reader.readtext(plate_crop)
        if len(results) > 0:
            # Lấy text có confidence cao nhất
            text = max(results, key=lambda x: x[2])[1]
            # Loại bỏ khoảng trắng
            text = text.replace(" ", "").upper()
            logger.info(f"📝 EasyOCR result: {text}")
            return text
    except Exception as e:
        logger.warning(f"EasyOCR failed: {e}")
    
    return "UNKNOWN"


# ============================================
# 🚦 Traffic Light Detection
# ============================================
def detect_traffic_light_status(frame: np.ndarray) -> str:
    """
    Phát hiện trạng thái đèn giao thông.
    
    Returns:
        "red", "green", "yellow", hoặc "unknown"
    """
    if models is None or models.traffic_light is None:
        return "unknown"
    
    try:
        results = models.traffic_light.predict(
            frame,
            conf=settings.INFERENCE_CONFIDENCE_LIGHT,
            device=DEVICE,
            verbose=False
        )
        
        if len(results) == 0 or results[0].boxes is None or len(results[0].boxes) == 0:
            return "unknown"
        
        # Lấy detection có confidence cao nhất
        best_light = max(results[0].boxes, key=lambda b: b.conf[0])
        cls_name = models.traffic_light.names[int(best_light.cls[0])]
        
        return cls_name.lower()
    
    except Exception as e:
        logger.warning(f"Traffic light detection failed: {e}")
        return "unknown"


# ============================================
# 🔳 Plate Detection + OCR
# ============================================
def detect_and_read_plate(vehicle_crop: np.ndarray) -> Tuple[Optional[str], float]:
    """
    Phát hiện biển số và đọc nội dung với OCR Vietnamese.
    
    Pipeline:
    1. Detect plate region
    2. Deskew and crop
    3. Check if 2-line plate
    4. Try YOLO OCR first
    5. Fallback to EasyOCR if needed
    6. Normalize and validate
    
    Args:
        vehicle_crop: numpy array của vùng phương tiện
    
    Returns:
        (plate_text, confidence)
    """
    if models is None or models.plate is None:
        return None, 0.0
    
    try:
        # 1. Phát hiện vùng biển số
        results_plate = models.plate.predict(
            vehicle_crop,
            conf=settings.INFERENCE_CONFIDENCE_PLATE,
            device=DEVICE,
            verbose=False
        )
        
        if len(results_plate[0].boxes) == 0:
            return None, 0.0
        
        # Lấy detection có confidence cao nhất (hoặc area lớn nhất)
        best_plate = max(results_plate[0].boxes, key=lambda b: b.conf[0])
        px1, py1, px2, py2 = map(int, best_plate.xyxy[0].tolist())
        plate_conf = float(best_plate.conf[0])
        
        # Crop plate region
        plate_crop = vehicle_crop[max(0, py1):max(0, py2), max(0, px1):max(0, px2)]
        
        if plate_crop.size == 0:
            return None, 0.0
        
        # 2. Deskew and crop
        plate_crop = deskew_and_crop(plate_crop)
        
        # 3. Check if 2-line plate
        two_line = is_two_line_plate(plate_crop)
        
        plate_text = "UNKNOWN"
        
        # 4. Try YOLO OCR (if available)
        if models.ocr is not None:
            try:
                if two_line:
                    # Split and OCR each line separately
                    upper, lower = split_two_lines(plate_crop)
                    
                    def yolo_ocr_line(img):
                        results = models.ocr.predict(
                            img,
                            conf=settings.INFERENCE_CONFIDENCE_OCR,
                            device=DEVICE,
                            verbose=False
                        )
                        
                        if len(results) == 0 or len(results[0].boxes) == 0:
                            return ""
                        
                        # Sort characters by x-coordinate (left to right)
                        chars = sorted(results[0].boxes, key=lambda b: b.xyxy[0][0])
                        return "".join([models.ocr.names[int(c.cls[0])] for c in chars])
                    
                    upper_text = yolo_ocr_line(upper)
                    lower_text = yolo_ocr_line(lower)
                    plate_text = upper_text + lower_text
                else:
                    # Single line OCR
                    results_ocr = models.ocr.predict(
                        plate_crop,
                        conf=settings.INFERENCE_CONFIDENCE_OCR,
                        device=DEVICE,
                        verbose=False
                    )
                    
                    if len(results_ocr[0].boxes) > 0:
                        # Sort by x-coordinate
                        chars = sorted(results_ocr[0].boxes, key=lambda b: b.xyxy[0][0])
                        plate_text = "".join([
                            models.ocr.names[int(c.cls[0])] for c in chars
                        ])
                
                if plate_text != "UNKNOWN":
                    logger.info(f"📝 YOLO OCR result: {plate_text}")
            
            except Exception as e:
                logger.warning(f"YOLO OCR failed: {e}")
                plate_text = "UNKNOWN"
        
        # 5. Fallback EasyOCR nếu YOLO OCR thất bại
        if plate_text == "UNKNOWN" and settings.USE_EASYOCR_FALLBACK:
            plate_text = ocr_with_easyocr(plate_crop)
        
        # 6. Normalize and validate
        plate_text = normalize_plate_text(plate_text)
        
        # Format for display
        if validate_plate(plate_text):
            plate_text = format_plate_display(plate_text)
        
        return plate_text, plate_conf
    
    except Exception as e:
        logger.warning(f"Plate detection failed: {e}")
        return None, 0.0


# ============================================
# 🚨 Violation Detection Logic
# ============================================
def check_violation(
    track_info: Dict[str, Any],
    traffic_light_status: str,
    rois: Dict[str, Any],
    frame_number: int
) -> Optional[Dict[str, Any]]:
    """
    Kiểm tra xem vehicle có vi phạm hay không.
    
    Logic:
    1. Red light violation: Đèn đỏ + xe trong violation_zone
    2. Stop line violation: Đèn đỏ + xe vượt stop_line (future)
    3. Wrong lane violation: (future)
    
    Args:
        track_info: Vehicle tracking info
        traffic_light_status: "red"/"green"/"yellow"/"unknown"
        rois: Dictionary of ROI polygons
        frame_number: Frame index
    
    Returns:
        Violation info dict or None
    """
    violation_type = None
    violation_code = None
    
    # Get vehicle position
    x1, y1, x2, y2 = track_info["bbox"]
    cx, cy = centroid_of_bbox(x1, y1, x2, y2)
    
    # Logic 1: Red light violation
    if settings.ENABLE_RED_LIGHT_DETECTION and traffic_light_status == "red":
        violation_zone = rois.get("violation_zone")
        
        if violation_zone:
            # Check if vehicle center is in violation zone
            if point_in_polygon((cx, cy), violation_zone):
                violation_type = "red_light"
                violation_code = "RED_LIGHT"
        else:
            # No ROI configured - mark as potential violation
            # (for demo purposes, sau này phải có ROI mới chính xác)
            violation_type = "red_light"
            violation_code = "RED_LIGHT"
    
    # Logic 2: Stop line violation (TODO: implement)
    # if settings.ENABLE_STOP_LINE_DETECTION:
    #     stop_line = rois.get("stop_line")
    #     if stop_line and check_stop_line_crossing(...):
    #         violation_type = "stop_line"
    #         violation_code = "STOP_LINE"
    
    if violation_type:
        return {
            "violation_type": violation_type,
            "violation_code": violation_code,
            "vehicle_class": track_info["class"],
            "plate": track_info.get("plate", "UNKNOWN"),
            "confidence": track_info["confidence"],
            "frame_number": frame_number,
            "traffic_light_status": traffic_light_status,
            "bbox": track_info["bbox"],
            "track_id": track_info["track_id"]
        }
    
    return None


# ============================================
# 💾 Evidence & Database
# ============================================
def save_evidence(frame: np.ndarray, track_info: Dict[str, Any], violation_info: Dict[str, Any]) -> str:
    """
    Lưu ảnh bằng chứng với annotations.
    
    Args:
        frame: Original frame
        track_info: Vehicle tracking info
        violation_info: Violation details
    
    Returns:
        Path to saved evidence image
    """
    os.makedirs(settings.STATIC_DIR, exist_ok=True)
    
    # Draw bounding box
    x1, y1, x2, y2 = track_info["bbox"]
    annotated = frame.copy()
    
    # Red box for violation
    cv2.rectangle(annotated, (x1, y1), (x2, y2), (0, 0, 255), 1)
    
    # Text: Plate + Violation type
    text = f"{track_info.get('plate', 'UNKNOWN')} - {violation_info['violation_type']}"
    cv2.putText(
        annotated,
        text,
        (x1, y1 - 10),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.6,
        (0, 0, 255),
        2
    )
    
    # Track ID
    cv2.putText(
        annotated,
        f"ID:{track_info['track_id']}",
        (x1, y2 + 20),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.5,
        (255, 255, 0),
        2
    )
    
    # Save
    evidence_filename = f"evidence_{uuid.uuid4().hex}.jpg"
    evidence_path = os.path.join(settings.STATIC_DIR, evidence_filename)
    cv2.imwrite(evidence_path, annotated)
    
    return evidence_path


# ============================================
# 🎬 Main Video Processing Pipeline
# ============================================
async def process_video(file, session: Session, module_config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Full pipeline: YOLO + ByteTrack + OCR + Violation Detection.
    
    Pipeline:
    1. Save uploaded video
    2. Create VideoJob in DB
    3. Open video and get metadata
    4. Load ROIs (if configured)
    5. Initialize ByteTrack tracker
    6. Process each frame:
       - Detect traffic light
       - Detect vehicles with YOLO
       - Track vehicles with ByteTrack (built-in tracker)
       - For each tracked vehicle:
         - Detect plate
         - OCR plate text
         - Check violations
         - Save evidence if violation detected
         - Save to DB (Vehicle + Violation)
    7. Close video and update job status
    8. Return summary
    
    Args:
        file: UploadFile from FastAPI
        session: Database session
    
    Returns:
        Dictionary with processing results
    """
    logger.info(f"📹 Starting video processing: {file.filename}")
    
    # 1. Save video
    unique_filename = f"{uuid.uuid4().hex}_{file.filename}"
    video_path = os.path.join(settings.STATIC_DIR, unique_filename)
    
    os.makedirs(settings.STATIC_DIR, exist_ok=True)
    
    with open(video_path, "wb") as f:
        f.write(await file.read())
    
    logger.info(f"📁 Video saved: {video_path}")
    
    # 2. Create video job
    video_job = VideoJob(
        file_name=file.filename,
        output_path=video_path,
        status="pending",  # Match db.sql (TEXT, not enum)
        upload_time=datetime.now()
    )
    session.add(video_job)
    session.commit()
    session.refresh(video_job)
    
    logger.info(f"📊 Video job created: ID={video_job.video_job_id}")
    
    try:
        # Update status to PROCESSING
        video_job.status = "processing"  # Match db.sql (TEXT, not enum)
        session.add(video_job)
        session.commit()
        
        # 3. Open video
        cap = cv2.VideoCapture(video_path)
        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration = total_frames / fps if fps > 0 else 0
        frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        frame_size = (frame_width, frame_height)
        
        video_job.fps = fps
        video_job.duration = duration
        # Note: total_frames doesn't exist in DB schema
        session.add(video_job)
        session.commit()
        
        logger.info(f"📊 Video info: {total_frames} frames, {fps} FPS, {duration:.2f}s")
        
        # Use module_config if provided, otherwise fallback to settings
        if module_config is None:
            module_config = {}
        
        # 4. Initialize modular pipeline components
        roi_module = ROIModule(
            session=session,
            video_job_id=video_job.video_job_id,
            frame_size=frame_size,
            enabled=module_config.get("enable_roi", settings.MODULE_ENABLE_ROI),
            draw_enabled=module_config.get("enable_roi_drawing", settings.MODULE_ENABLE_ROI_DRAWING),
            roi_json_path=module_config.get("roi_json_path") if module_config.get("enable_roi_json", settings.MODULE_ENABLE_ROI_JSON) else None,
        )
        vehicle_module = VehicleYOLOModule(
            models=models,
            enabled=module_config.get("enable_vehicle_yolo", settings.MODULE_ENABLE_VEHICLE_YOLO),
            use_tracking=module_config.get("enable_bytetrack", settings.MODULE_ENABLE_BYTETRACK),
            confidence=module_config.get("inference_confidence_vehicle", settings.INFERENCE_CONFIDENCE_VEHICLE),
            device=DEVICE,
        )
        bbox_module = BoundingBoxDrawerModule(
            enabled=module_config.get("enable_draw_bbox", settings.MODULE_ENABLE_DRAW_BBOX),
        )

        # Run setup hooks once before processing frames
        dummy_frame = np.zeros((max(1, frame_height), max(1, frame_width), 3), dtype=np.uint8)
        setup_context = ModuleContext(
            frame=dummy_frame,
            frame_idx=0,
            frame_size=frame_size,
        )
        roi_module.setup(setup_context)
        logger.info(f"🎯 Loaded {len(roi_module.rois)} ROIs")
        
        # 5. Process frames
        frame_idx = 0
        violations_count = 0
        summary = []
        
        # Track history for deduplication (avoid duplicate violations from same track)
        detected_violations = set()  # Set of (track_id, violation_type)
        
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            frame_idx += 1
            
            # Frame sampling
            if frame_idx % settings.FRAME_SKIP != 0:
                continue
            
            logger.info(f"🔍 Processing frame {frame_idx}/{total_frames}")
            
            # Prepare modular context for this frame
            frame_context = ModuleContext(
                frame=frame,
                frame_idx=frame_idx,
                frame_size=frame_size,
                rois=roi_module.rois,
            )

            # 6.1 ROI overlay (optional)
            roi_module.process(frame_context)

            # 6.2 Detect traffic light
            traffic_light_status = detect_traffic_light_status(frame)

            # 6.3 Vehicle detection/tracking
            vehicle_module.process(frame_context)

            if not frame_context.tracks:
                continue

            # Process each tracked vehicle
            for track in frame_context.tracks:
                x1, y1, x2, y2 = track["bbox"]
                track_id = track["track_id"]
                cls_name = track["class"]
                conf = track["confidence"]

                # Crop vehicle region
                vehicle_crop = frame[max(0, y1):max(0, y2), max(0, x1):max(0, x2)]

                if vehicle_crop.size == 0:
                    continue

                # 6.4 Detect plate + OCR
                plate_text, plate_conf = detect_and_read_plate(vehicle_crop)

                if plate_text is None:
                    plate_text = "UNKNOWN"

                track_info = {
                    **track,
                    "plate": plate_text,
                    "plate_confidence": plate_conf,
                }

                # 6.5 Check violation
                violation_info = check_violation(
                    track_info,
                    traffic_light_status,
                    frame_context.rois,
                    frame_idx
                )

                if violation_info:
                    frame_context.violating_track_ids.add(track_id)
                    # Deduplication: only save once per track_id + violation_type
                    violation_key = (track_id, violation_info["violation_type"])

                    if violation_key not in detected_violations:
                        detected_violations.add(violation_key)

                        # 6.6 Save evidence
                        evidence_path = save_evidence(frame, track_info, violation_info)

                        # 6.7 Save to DB
                        # Upsert vehicle
                        vehicle_entry = session.exec(
                            select(Vehicle).where(Vehicle.plate == plate_text)
                        ).first()
                        
                        if not vehicle_entry:
                            vehicle_entry = Vehicle(
                                plate=plate_text,
                                type=cls_name,
                                # Remove track_id, avg_confidence - not in db.sql schema
                                first_seen=datetime.now(),
                                last_seen=datetime.now(),
                                total_violations=1
                            )
                            session.add(vehicle_entry)
                            session.commit()
                            session.refresh(vehicle_entry)
                        else:
                            vehicle_entry.last_seen = datetime.now()
                            vehicle_entry.total_violations += 1  # Changed from total_detections to match db.sql
                            session.add(vehicle_entry)
                            session.commit()
                        
                        # Create violation
                        violation = Violation(
                            video_job_id=video_job.video_job_id,
                            vehicle_id=vehicle_entry.vehicle_id,
                            violation_type_code=violation_info.get("violation_type"),  # Changed to violation_type_code to match db.sql
                            plate=plate_text,
                            timestamp=datetime.now(),
                            confidence=conf,
                            evidence_img=evidence_path,
                            frame=frame_idx,  # Changed from frame_number to frame to match db.sql
                            roi_type=None  # Can be set based on ROI detection
                        )
                        session.add(violation)
                        session.commit()
                        
                        violations_count += 1
                        
                        summary.append({
                            "frame": frame_idx,
                            "track_id": track_id,
                            "vehicle": cls_name,
                            "plate": plate_text,
                            "light": traffic_light_status,
                            "violation": violation_info["violation_type"]
                        })

                        logger.info(f"🚨 Violation #{violations_count}: {violation_info['violation_type']} - {plate_text} (Track {track_id})")

            # 6.8 Optional annotation rendering
            bbox_module.process(frame_context)
        
        cap.release()
        
        # 7. Update job status
        video_job.status = "done"  # Changed from JobStatus.COMPLETED to match db.sql
        video_job.processed_at = datetime.now()
        # Note: violations_count doesn't exist in DB schema, stored separately in violations table
        session.add(video_job)
        session.commit()
        
        logger.info(f"✅ Processing completed: {violations_count} violations detected")
        
        return {
            "video_job_id": video_job.video_job_id,
            "filename": file.filename,
            "total_frames": total_frames,
            "fps": fps,
            "duration": duration,
            "violations_detected": violations_count,
            "status": "completed",
            "detections": summary
        }
    
    except Exception as e:
        logger.error(f"❌ Error processing video: {e}", exc_info=True)
        
        # Update job status to FAILED
        video_job.status = "failed"  # Match db.sql (TEXT, not enum)
        video_job.processed_at = datetime.now()
        video_job.notes = f"Error: {str(e)}"  # Use notes field instead of error_message
        session.add(video_job)
        session.commit()
        
        raise Exception(f"Lỗi khi xử lý video: {str(e)}")
