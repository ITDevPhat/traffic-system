"""
Traffic Light Detection WebSocket Router
Separate pipeline for traffic light violation detection
"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, HTTPException
from fastapi.encoders import jsonable_encoder
from app.services.realtime_binary_stream import (
    BinaryAnnotStream,
    DEFAULT_REALTIME_MODEL_PATH,
)
import json
import logging
import asyncio
import base64
import cv2
import numpy as np
import time
from datetime import datetime
from pathlib import Path
from app.core.config import settings
from app.schemas.traffic_light_violation import TrafficLightViolationIn
from app.services.traffic_light_violation_service import (
    create_traffic_light_violation_with_session,
)
from app.violations.violation_manager import violation_manager
from app.services.traffic_light_manager import traffic_light_manager
from app.services.plate_ocr_service import recognize_plate_from_crop

logger = logging.getLogger(__name__)

# Import ROI storage from router
from app.routers.traffic_light_router import roi_storage, clear_roi

router = APIRouter(
    prefix="/api/traffic-light",
    tags=["Traffic Light Detection"],
)


def crop_tl_roi(frame: np.ndarray, camera_id: str) -> tuple:
    """
    Crop traffic light ROI from frame
    
    Returns:
        (roi_frame, roi_data) or (None, None) if no ROI
    """
    roi_data = roi_storage.get(camera_id) or traffic_light_manager.get_roi(camera_id)
    if not roi_data:
        roi_data = traffic_light_manager.load_roi_from_config(camera_id)
        if roi_data:
            roi_storage[camera_id] = roi_data

    if not roi_data:
        return None, None

    h, w = frame.shape[:2]

    if roi_data.get("type") == "pixel":
        # Store normalized version for consistent downstream use
        x1 = max(0, min(int(roi_data["x1"]), w - 1))
        y1 = max(0, min(int(roi_data["y1"]), h - 1))
        x2 = max(x1 + 1, min(int(roi_data["x2"]), w))
        y2 = max(y1 + 1, min(int(roi_data["y2"]), h))
        roi_norm = {
            "x": x1 / w,
            "y": y1 / h,
            "width": (x2 - x1) / w,
            "height": (y2 - y1) / h,
        }
        traffic_light_manager.set_roi(camera_id, roi_norm)
    else:
        # Normalized
        x1 = int(roi_data["x"] * w)
        y1 = int(roi_data["y"] * h)
        x2 = int((roi_data["x"] + roi_data["width"]) * w)
        y2 = int((roi_data["y"] + roi_data["height"]) * h)

    # Clamp to frame bounds
    x1 = max(0, min(x1, w - 1))
    y1 = max(0, min(y1, h - 1))
    x2 = max(x1 + 1, min(x2, w))
    y2 = max(y1 + 1, min(y2, h))
    
    roi_frame = frame[y1:y2, x1:x2]

    if roi_frame.size == 0:
        logger.warning(
            f"⚠️ Empty ROI crop: cam={camera_id} pixels=({x1},{y1}) -> ({x2},{y2}) w={w} h={h}"
        )
        return None, None

    logger.debug(
        f"[TL ROI] cam={camera_id} pix=({x1},{y1},{x2},{y2}) norm={traffic_light_manager.get_roi(camera_id)}"
    )

    return roi_frame, {"x1": x1, "y1": y1, "x2": x2, "y2": y2}


def encode_roi_frame(roi_frame: np.ndarray, quality: int = 80) -> str:
    """Encode ROI frame to base64 JPEG"""
    if roi_frame is None or roi_frame.size == 0:
        return None
    
    _, buffer = cv2.imencode('.jpg', roi_frame, [cv2.IMWRITE_JPEG_QUALITY, quality])
    return base64.b64encode(buffer).decode('utf-8')


def detect_traffic_light_state(roi_frame: np.ndarray) -> tuple:
    """
    Simple traffic light detection based on color analysis
    
    Returns:
        (state, confidence)
    """
    if roi_frame is None or roi_frame.size == 0:
        return None, 0.0
    
    # Convert to HSV
    hsv = cv2.cvtColor(roi_frame, cv2.COLOR_BGR2HSV)
    
    # Define color ranges
    # Red (two ranges because red wraps around in HSV)
    red_lower1 = np.array([0, 100, 100])
    red_upper1 = np.array([10, 255, 255])
    red_lower2 = np.array([160, 100, 100])
    red_upper2 = np.array([180, 255, 255])
    
    # Yellow
    yellow_lower = np.array([15, 100, 100])
    yellow_upper = np.array([35, 255, 255])
    
    # Green
    green_lower = np.array([40, 100, 100])
    green_upper = np.array([80, 255, 255])
    
    # Create masks
    red_mask1 = cv2.inRange(hsv, red_lower1, red_upper1)
    red_mask2 = cv2.inRange(hsv, red_lower2, red_upper2)
    red_mask = cv2.bitwise_or(red_mask1, red_mask2)
    yellow_mask = cv2.inRange(hsv, yellow_lower, yellow_upper)
    green_mask = cv2.inRange(hsv, green_lower, green_upper)
    
    # Count pixels
    total_pixels = roi_frame.shape[0] * roi_frame.shape[1]
    red_pixels = cv2.countNonZero(red_mask)
    yellow_pixels = cv2.countNonZero(yellow_mask)
    green_pixels = cv2.countNonZero(green_mask)
    
    # Determine state
    max_pixels = max(red_pixels, yellow_pixels, green_pixels)
    
    if max_pixels < total_pixels * 0.001:  # Less than 0.1% colored pixels (adjusted for small ROIs)
        # Not enough signal — keep previous effective state
        return None, 0.0
    
    confidence = min(max_pixels / (total_pixels * 0.1), 1.0)  # Normalize
    
    if red_pixels == max_pixels:
        return "RED", confidence
    elif yellow_pixels == max_pixels:
        return "YELLOW", confidence
    else:
        return "GREEN", confidence

@router.websocket("/realtime")
async def ws_traffic_light_realtime(
    websocket: WebSocket,
    source: str = Query("0", description="Video source"),
    conf: float = Query(0.5, description="Confidence threshold"),
    fps: int = Query(30, description="Target FPS"),
    imgsz: int = Query(640, description="YOLO inference size"),
    quality: int = Query(60, description="JPEG quality"),
    encode_width: int = Query(960, description="Encode width"),
    model_path: str = Query(DEFAULT_REALTIME_MODEL_PATH, description="Model path"),
    enable_traffic_light: bool = Query(True, description="Enable traffic light detection"),
    enable_violation: bool = Query(True, description="Enable violation detection"),
    camera_id: str = Query("cam01", description="Camera ID for ROI lookup"),
):
    """
    Traffic Light Detection WebSocket - Separate pipeline
    
    Features:
    - Traffic light detection (red/yellow/green)
    - Violation detection (running red light)
    - ROI support for stoplines
    - Real-time streaming
    """
    logger.info(f"🚦 Traffic Light WS connection from: {websocket.client}")
    logger.info(f"📹 Source: {source}, TL: {enable_traffic_light}, Violation: {enable_violation}")
    
    await websocket.accept()
    logger.info("✅ WebSocket accepted")
    
    # ÉP imgsz về 640 nếu model là ONNX để tránh lỗi "Got: 320 Expected: 640"
    try:
        model_ext = Path(model_path).suffix.lower()
        if model_ext == ".onnx" and imgsz != 640:
            logger.warning(
                f"[TL WS] ONNX model fixed 640x640, overriding imgsz {imgsz} -> 640 "
                f"for model {model_path}"
            )
            imgsz = 640
    except Exception as e:
        logger.warning(f"[TL WS] Failed to normalize imgsz for ONNX: {e}")
    
    # RESET STATE ON NEW CONNECTION
    # When a new connection is made for a specific camera, clear any old state
    # to prevent "ghost" ROIs or stale violation tracking.
    clear_roi(camera_id)
    traffic_light_manager.clear_roi(camera_id)
    violation_manager.clear(camera_id)
    logger.info(f"[RESET] Cleared ROI and violation state for {camera_id}")
    
    stream = None
    
    try:
        # Initialize stream with traffic light enabled
        stream = BinaryAnnotStream(
            source=source,
            camera_id=camera_id,
            conf=conf,
            imgsz=imgsz,
            target_fps=fps,
            jpeg_quality=quality,
            encode_width=encode_width,
            model_path=model_path,
            enable_yolo=True,
            enable_tracking=True,
            enable_bbox_drawing=True,
            enable_roi=True,
            enable_roi_drawing=True,
            # Traffic light specific settings would go here
            # For now, use same stream but can be extended
        )
        
        stream.start()
        
        # Load stopline configuration for violation detection
        try:
            config_path = Path(__file__).parent.parent / "data" / "traffic_light" / f"{camera_id}.json"
            if config_path.exists():
                with open(config_path) as f:
                    config = json.load(f)

                tl_roi = config.get("traffic_light_roi")
                if tl_roi:
                    traffic_light_manager.set_roi(camera_id, tl_roi)
                    roi_storage[camera_id] = tl_roi
                    logger.info(f"[TL ROI] camera={camera_id}, roi={tl_roi}")
                else:
                    logger.warning(f"⚠️ No traffic_light_roi found for {camera_id}")

                if enable_violation:
                    stopline = config.get("stopline")
                    if stopline:
                        violation_manager.set_stopline(
                            camera_id=camera_id,
                            stopline=stopline
                        )
                        logger.info(f"[STOPLINE] camera={camera_id}, stopline={stopline}")
                    else:
                        logger.warning(f"⚠️ No stopline in config for {camera_id} - violations will not be detected")

                    violation_region = config.get("violation_region", {})
                    violation_points = violation_region.get("points") if isinstance(violation_region, dict) else None
                    if violation_points:
                        violation_manager.set_violation_region(
                            camera_id,
                            [tuple(map(float, pt)) for pt in violation_points],
                        )
                        logger.info(
                            f"[VIOLATION REGION] camera={camera_id}, points={len(violation_points)}"
                        )
            else:
                logger.warning(f"⚠️ Config file not found: {config_path}")
        except Exception as e:
            logger.error(f"❌ Failed to load TL config: {e}", exc_info=True)
        
        # Send info packet
        info = stream.info_packet()
        info['traffic_light_enabled'] = enable_traffic_light
        info['violation_enabled'] = enable_violation
        await websocket.send_text(json.dumps(jsonable_encoder(info)))
        logger.info(f"📤 Sent info: {info}")
        
        # Stream loop
        async def send_frames():
            """Send frames with traffic light data"""
            frame_count = 0
            consecutive_errors = 0
            max_consecutive_errors = 3
            last_tl_update = 0
            tl_update_interval = 0.2   # Update TL every 200ms (5 FPS) for better responsiveness
            
            # Cache traffic light state to use for all frames
            cached_tl_state = {
                'state': 'GREEN',
                'confidence': 0.0,
                'roi_frame': None,
                'roi_bounds': None
            }

            seen_violation_keys = set()

            static_root = Path(settings.STATIC_DIR).resolve()

            def to_static_url(path: Path) -> str:
                try:
                    rel = path.resolve().relative_to(static_root)
                    return f"/static/{rel.as_posix()}"
                except Exception:
                    return str(path)

            def clamp_bbox_to_frame(bbox, frame_shape):
                if bbox is None or len(bbox) != 4 or frame_shape is None:
                    return None
                x1, y1, x2, y2 = [int(v) for v in bbox]
                h, w = frame_shape[:2]
                x1 = max(0, min(x1, w - 1))
                y1 = max(0, min(y1, h - 1))
                x2 = max(x1 + 1, min(x2, w))
                y2 = max(y1 + 1, min(y2, h))
                if y2 <= y1 or x2 <= x1:
                    return None
                return (x1, y1, x2, y2)

            def save_crop_and_ocr(
                vehicle_state,
                bbox,
                frame_bgr,
                evidence_dir: Path,
                filename_prefix: str,
            ):
                """Save crop for bbox and run OCR once if not done."""

                if frame_bgr is None:
                    return None, vehicle_state.plate_text if vehicle_state else None, vehicle_state.plate_conf if vehicle_state else None

                clamped_bbox = clamp_bbox_to_frame(bbox, frame_bgr.shape)
                if clamped_bbox is None:
                    return None, vehicle_state.plate_text if vehicle_state else None, vehicle_state.plate_conf if vehicle_state else None

                x1, y1, x2, y2 = clamped_bbox
                crop = frame_bgr[y1:y2, x1:x2].copy()
                if crop.size == 0:
                    return None, vehicle_state.plate_text if vehicle_state else None, vehicle_state.plate_conf if vehicle_state else None

                evidence_dir.mkdir(parents=True, exist_ok=True)
                crop_path = evidence_dir / f"{filename_prefix}_crop.jpg"
                try:
                    cv2.imwrite(str(crop_path), crop)
                except Exception as e:
                    logger.warning(f"[TL-SNAPSHOT] Failed to save crop {crop_path}: {e}")
                    crop_path = None

                plate_text = vehicle_state.plate_text if vehicle_state else None
                plate_conf = vehicle_state.plate_conf if vehicle_state else None

                if vehicle_state and not vehicle_state.plate_ocr_done:
                    ocr_text, ocr_conf = recognize_plate_from_crop(crop)
                    if ocr_text is not None:
                        plate_text = ocr_text
                        plate_conf = ocr_conf
                        vehicle_state.plate_text = ocr_text
                        vehicle_state.plate_conf = ocr_conf
                        vehicle_state.plate_ocr_done = True

                return crop_path, plate_text, plate_conf

            while True:
                # Check connection
                if websocket.client_state.name == 'DISCONNECTED':
                    logger.info("🔌 WebSocket disconnected")
                    break
                
                if stream and stream.stop_ev.is_set():
                    logger.info("🛑 Stream stopped")
                    break
                
                try:
                    header, jpeg_bytes = stream.next_frame()

                    if header is None or jpeg_bytes is None:
                        await asyncio.sleep(0.001)
                        continue

                    frame_array = np.frombuffer(jpeg_bytes, dtype=np.uint8)
                    frame = cv2.imdecode(frame_array, cv2.IMREAD_COLOR)

                    if websocket.client_state.name == 'DISCONNECTED':
                        break
                    
                    # Use camera_id from query param (already available from function signature)
                    
                    # Add traffic light ROI data to header
                    import time
                    current_time = time.time()
                    
                    # Update traffic light detection every 500ms
                    if enable_traffic_light and (current_time - last_tl_update) >= tl_update_interval:
                        if frame is not None:
                            # Log ROI storage status periodically
                            if frame_count % 100 == 0:
                                logger.info(f"🔍 ROI storage keys: {list(roi_storage.keys())}, looking for: {camera_id}")
                            
                            # Crop and detect traffic light
                            roi_frame, roi_data = crop_tl_roi(frame, camera_id)
                            
                            if roi_frame is not None:
                                # Detect state
                                raw_state, raw_confidence = detect_traffic_light_state(roi_frame)
                                normalized_raw = raw_state if raw_state in {"RED", "YELLOW", "GREEN"} else None
                                state, confidence = traffic_light_manager.stabilize_state(
                                    camera_id, normalized_raw, raw_confidence, timestamp=datetime.utcnow()
                                )

                                # Encode ROI frame
                                roi_frame_b64 = encode_roi_frame(roi_frame, quality=80)
                                
                                # Update cached state
                                cached_tl_state = {
                                    'state': state,
                                    'confidence': confidence,
                                    'roi_frame': roi_frame_b64,
                                    'roi_bounds': roi_data
                                }
                                
                                if frame_count % 50 == 0:
                                    logger.info(f"🚦 TL state: {state} ({confidence:.2f}), ROI frame: {len(roi_frame_b64) if roi_frame_b64 else 0} bytes")
                            else:
                                # Update cached state with error but keep default GREEN fallback
                                cached_tl_state = {
                                    'state': 'GREEN',
                                    'confidence': 0.0,
                                    'roi_frame': None,
                                    'roi_bounds': None,
                                    'error': f'No ROI configured for camera_id={camera_id}'
                                }
                                if frame_count % 100 == 0:
                                    logger.warning(f"⚠️ No ROI for camera_id={camera_id}, available: {list(roi_storage.keys())}")

                        last_tl_update = current_time
                    
                    # Always add cached traffic light state to header (for all frames)
                    header['traffic_light'] = cached_tl_state

                    # Violation detection using cached state
                    if enable_violation:
                        traffic_light_state = cached_tl_state.get("state") or "GREEN"
                        tracks = header.get("detections", [])
                        frame_idx = header.get("frame_idx") or frame_count

                        if frame_count % 20 == 0:
                            logger.info(
                                f"[DEBUG VIOLATION] cam={camera_id}, "
                                f"tl_state={traffic_light_state}, "
                                f"tracks={len(tracks)}, "
                                f"sample_track={tracks[0] if tracks else None}"
                            )

                        header["light"] = traffic_light_state

                        violation_result = violation_manager.compute_violations(
                            camera_id=camera_id,
                            tracks=tracks,
                            light_state=traffic_light_state,
                            timestamp=datetime.utcnow(),
                            frame_index=frame_idx,
                        )
                        violations = violation_result.violations if violation_result else []
                        yellow_candidates = (
                            violation_result.yellow_candidates if violation_result else []
                        )
                        violation_flags = (
                            violation_result.violation_flags if violation_result else {}
                        )

                        # DEBUG: Log violation detection result
                        if frame_count % 30 == 0:
                            logger.warning(
                                f"[VIOLATION-RESULT] cam={camera_id}, light={traffic_light_state}, "
                                f"tracks={len(tracks)}, violations={len(violations) if violations else 0}"
                            )

                        engine = violation_manager.engines.get(camera_id)
                        yellow_evidence_payload = []

                        if yellow_candidates:
                            header["yellow_candidates"] = yellow_candidates

                            if frame is not None:
                                evidence_dir_yellow = (
                                    Path(settings.STATIC_DIR)
                                    / "evidence"
                                    / "traffic_light"
                                    / str(camera_id)
                                    / "yellow_candidates"
                                )
                                for cand in yellow_candidates:
                                    track_id = cand.get("track_id")
                                    if track_id is None:
                                        continue
                                    vehicle_state = engine.vehicles.get(track_id) if engine else None
                                    if vehicle_state and vehicle_state.last_snapshot_saved_frame == frame_idx:
                                        continue

                                    best_bbox = None
                                    if vehicle_state and vehicle_state.best_view_bbox:
                                        best_bbox = vehicle_state.best_view_bbox
                                    else:
                                        best_bbox = cand.get("best_view_bbox") or cand.get("bbox")

                                    filename_prefix = f"{camera_id}_{track_id}_yellow_{frame_idx}"
                                    crop_path, plate_text, plate_conf = save_crop_and_ocr(
                                        vehicle_state,
                                        best_bbox,
                                        frame,
                                        evidence_dir_yellow,
                                        filename_prefix,
                                    )

                                    if vehicle_state:
                                        vehicle_state.last_snapshot_saved_frame = frame_idx

                                    if crop_path:
                                        yellow_evidence_payload.append(
                                            {
                                                "track_id": track_id,
                                                "class_name": cand.get("class_name"),
                                                "frame": frame_idx,
                                                "first_seen_frame": cand.get("first_seen_frame"),
                                                "snapshot_frame": cand.get("snapshot_frame"),
                                                "bbox": clamp_bbox_to_frame(best_bbox, frame.shape),
                                                "image_url": to_static_url(crop_path),
                                                "plate_text": plate_text,
                                                "plate_conf": plate_conf,
                                                "light": traffic_light_state,
                                            }
                                        )
                                        logger.info(
                                            f"[YELLOW-SNAPSHOT] cam={camera_id}, track={track_id}, frame={frame_idx}, path={crop_path}"
                                        )

                        violation_evidence_payload = []

                        if violations:
                            for viol in violations:
                                plate_text = viol.details.get("plate_text")
                                plate_conf = viol.details.get("plate_conf")

                                best_bbox = viol.details.get("best_view_bbox") or viol.details.get(
                                    "first_in_region_bbox"
                                )

                                if (plate_text is None or plate_conf is None) and best_bbox and frame is not None:
                                    x1, y1, x2, y2 = [int(v) for v in best_bbox]
                                    h, w = frame.shape[:2]
                                    x1 = max(0, min(x1, w - 1))
                                    y1 = max(0, min(y1, h - 1))
                                    x2 = max(x1 + 1, min(x2, w))
                                    y2 = max(y1 + 1, min(y2, h))

                                    if y2 > y1 and x2 > x1:
                                        crop = frame[y1:y2, x1:x2].copy()
                                        ocr_text, ocr_conf = recognize_plate_from_crop(crop)
                                        if ocr_text is not None:
                                            plate_text = ocr_text
                                            plate_conf = ocr_conf
                                            viol.details["plate_text"] = plate_text
                                            viol.details["plate_conf"] = plate_conf

                                            engine = violation_manager.engines.get(camera_id)
                                            if engine:
                                                vehicle_state = engine.vehicles.get(viol.track_id)
                                                if vehicle_state:
                                                    vehicle_state.plate_text = plate_text
                                                    vehicle_state.plate_conf = plate_conf
                                                    vehicle_state.plate_ocr_done = True

                                        logger.info(
                                            f"[TL-PLATE] cam={camera_id}, track={viol.track_id}, "
                                            f"plate={plate_text}, conf={plate_conf}, violation={viol.violation_type}"
                                        )
                                    else:
                                        logger.debug(
                                            f"[TL-PLATE] Skipping OCR due to invalid bbox for track={viol.track_id}: {best_bbox}"
                                        )

                                if tracks:
                                    for det in tracks:
                                        if det.get("track_id") == viol.track_id:
                                            det["plate"] = {
                                                "text": plate_text,
                                                "conf": plate_conf,
                                            }
                                            det["plate_text"] = plate_text
                                            det["plate_conf"] = plate_conf
                                            det["violation"] = viol.violation_type
                                            break

                        # Map violation to detections for frontend
                        if tracks:
                            if violation_flags:
                                for det in tracks:
                                    tid = det.get("track_id")
                                    if tid in violation_flags:
                                        det["violation"] = violation_flags[tid]

                            if violations:
                                viol_by_tid = {v.track_id: v for v in violations}
                                for det in tracks:
                                    tid = det.get("track_id")
                                    if tid in viol_by_tid:
                                        det.setdefault("plate", {
                                            "text": viol_by_tid[tid].details.get("plate_text"),
                                            "conf": viol_by_tid[tid].details.get("plate_conf"),
                                        })

                        formatted_violations = []
                        for viol in violations:
                            payload_bbox = (
                                viol.details.get("bbox")
                                or viol.details.get("best_view_bbox")
                                or viol.details.get("first_in_region_bbox")
                            )
                            payload_violation_type = viol.violation_type
                            if payload_violation_type not in {"STOPLINE", "RED_LIGHT"}:
                                payload_violation_type = (
                                    "STOPLINE" if "STOPLINE" in payload_violation_type else "RED_LIGHT"
                                )
                            formatted_violations.append({
                                "track_id": viol.track_id,
                                "class_name": viol.details.get("class_name"),
                                "bbox": list(payload_bbox) if payload_bbox else None,
                                "violation_type": payload_violation_type,
                                "position": viol.details.get("position_now"),
                                "overlap": viol.details.get("overlap_ratio"),
                                "from_yellow": bool(viol.details.get("snapshot_frame_yellow")),
                                "snapshot_frame_yellow": viol.details.get("snapshot_frame_yellow"),
                                "best_view_frame": viol.details.get("best_view_frame"),
                            })

                        if formatted_violations:
                            header["violations"] = formatted_violations

                        if violations and frame is not None:
                            evidence_dir_violation = (
                                Path(settings.STATIC_DIR)
                                / "evidence"
                                / "traffic_light"
                                / str(camera_id)
                                / "violation_crops"
                            )
                            for viol in violations:
                                best_bbox = (
                                    viol.details.get("best_view_bbox")
                                    or viol.details.get("first_in_region_bbox")
                                    or viol.details.get("bbox")
                                )
                                vehicle_state = engine.vehicles.get(viol.track_id) if engine else None
                                filename_prefix = f"{camera_id}_{viol.track_id}_{viol.violation_type}_{frame_idx}"
                                crop_path, plate_text, plate_conf = save_crop_and_ocr(
                                    vehicle_state,
                                    best_bbox,
                                    frame,
                                    evidence_dir_violation,
                                    filename_prefix,
                                )

                                if vehicle_state:
                                    vehicle_state.last_snapshot_saved_frame = frame_idx

                                if crop_path:
                                    violation_evidence_payload.append(
                                        {
                                            "track_id": viol.track_id,
                                            "violation_type": viol.violation_type,
                                            "bbox": clamp_bbox_to_frame(best_bbox, frame.shape),
                                            "frame": frame_idx,
                                            "image_url": to_static_url(crop_path),
                                            "plate_text": plate_text,
                                            "plate_conf": plate_conf,
                                            "first_seen_frame": viol.details.get("first_in_region_frame"),
                                            "best_view_frame": viol.details.get("best_view_frame"),
                                            "light": traffic_light_state,
                                        }
                                    )
                                    logger.info(
                                        f"[RED-SNAPSHOT] cam={camera_id}, track={viol.track_id}, frame={frame_idx}, path={crop_path}"
                                    )

                        if yellow_evidence_payload:
                            header["yellow_evidence"] = yellow_evidence_payload

                        if violation_evidence_payload:
                            header["violation_evidence"] = violation_evidence_payload

                        if violations:
                            clean_frame, annotated_frame = stream.get_latest_frames()
                            evidence_dir = (
                                Path(settings.STATIC_DIR)
                                / "evidence"
                                / "traffic_light"
                                / str(camera_id)
                            )
                            evidence_dir.mkdir(parents=True, exist_ok=True)

                            for violation in violations:
                                key = (violation.track_id, violation.violation_type)
                                if key in seen_violation_keys:
                                    continue

                                seen_violation_keys.add(key)

                                matching_det = next(
                                    (
                                        det
                                        for det in (tracks or [])
                                        if det.get("track_id") == violation.track_id
                                    ),
                                    None,
                                )

                                bbox = (
                                    tuple(matching_det.get("bbox"))
                                    if matching_det and matching_det.get("bbox")
                                    else None
                                )
                                label = matching_det.get("class_name") if matching_det else None
                                det_confidence = matching_det.get("confidence") if matching_det else None
                                
                                # Extract plate text from dict or use plate_text field
                                plate_data = matching_det.get("plate") if matching_det else None
                                if isinstance(plate_data, dict):
                                    plate_text = plate_data.get("text")
                                    plate_conf = plate_data.get("conf")
                                else:
                                    plate_text = matching_det.get("plate_text") if matching_det else None
                                    plate_conf = matching_det.get("plate_conf") if matching_det else None

                                filename_prefix = f"{camera_id}_{violation.track_id}_{int(time.time())}"
                                raw_path = bbox_path = None

                                if clean_frame is not None:
                                    raw_path = evidence_dir / f"{filename_prefix}_raw.jpg"
                                    try:
                                        cv2.imwrite(str(raw_path), clean_frame)
                                    except Exception as e:
                                        logger.warning(
                                            f"[TL-VIOLATION] Failed to save raw frame: {e}"
                                        )

                                if annotated_frame is not None:
                                    bbox_path = evidence_dir / f"{filename_prefix}_bbox.jpg"
                                    try:
                                        cv2.imwrite(str(bbox_path), annotated_frame)
                                    except Exception as e:
                                        logger.warning(
                                            f"[TL-VIOLATION] Failed to save annotated frame: {e}"
                                        )

                                evidence_raw_url = (
                                    to_static_url(raw_path)
                                    if raw_path is not None and raw_path.exists()
                                    else None
                                )
                                evidence_bbox_url = (
                                    to_static_url(bbox_path)
                                    if bbox_path is not None and bbox_path.exists()
                                    else None
                                )

                                violation_code = None
                                if label:
                                    if label.lower() == "bike":
                                        violation_code = "BIKE_RED_LIGHT"
                                    elif label.lower() == "car":
                                        violation_code = "CAR_RED_LIGHT"
                                elif violation.violation_type in {
                                    "RED_LIGHT_RUN",
                                    "RED_LIGHT_STOPLINE",
                                    "RED_LIGHT",
                                    "STOPLINE",
                                }:
                                    violation_code = "RED_LIGHT"

                                # Build payload for DB - plate must be string or None
                                payload = TrafficLightViolationIn(
                                    camera_id=int(camera_id)
                                    if str(camera_id).isdigit()
                                    else None,
                                    camera_name=str(camera_id),
                                    video_job_id=None,
                                    violation_type_code=violation_code,
                                    frame=header.get("frame_idx"),
                                    timestamp=violation.timestamp,
                                    plate=plate_text if plate_text else None,  # Must be string or None, not dict
                                    confidence=plate_conf if plate_conf is not None else det_confidence,
                                    bbox=bbox,
                                    label=label,
                                    traffic_light_state=traffic_light_state,
                                    violation_engine_type=violation.violation_type,
                                    evidence_img_with_bbox=evidence_bbox_url,
                                    evidence_img_raw=evidence_raw_url,
                                    roi_type="traffic_light_stopline",
                                )

                                # Persist to DB - don't let DB errors block anything
                                try:
                                    create_traffic_light_violation_with_session(payload)
                                    logger.info(
                                        f"[TL-VIOLATION-DB] ✅ Saved: camera={camera_id}, type={violation.violation_type}, "
                                        f"frame={payload.frame}, plate={plate_text}, bbox={bbox}"
                                    )
                                except Exception as e:
                                    logger.warning(
                                        f"[TL-VIOLATION-DB] ⚠️ Failed to persist violation (non-blocking): {e}",
                                        exc_info=True,
                                    )

                    try:
                        # Send header with traffic light data
                        # Use jsonable_encoder to handle datetime, Decimal, ORM objects, etc.
                        safe_header = jsonable_encoder(header)
                        await asyncio.wait_for(
                            websocket.send_text(json.dumps(safe_header)),
                            timeout=1.0
                        )
                        
                        # Send JPEG
                        await asyncio.wait_for(
                            websocket.send_bytes(jpeg_bytes),
                            timeout=1.0
                        )
                        
                        frame_count += 1
                        consecutive_errors = 0
                        
                    except asyncio.TimeoutError:
                        logger.warning(f"⏱️ Send timeout at frame {frame_count}")
                        consecutive_errors += 1
                        if consecutive_errors >= max_consecutive_errors:
                            logger.error(f"❌ Too many timeouts - stopping")
                            break
                            
                except Exception as send_error:
                    error_str = str(send_error)
                    if "disconnect" in error_str.lower() or "closed" in error_str.lower():
                        logger.info(f"🔌 Client disconnected: {send_error}")
                        break
                    else:
                        logger.warning(f"⚠️ Send error: {send_error}")
                        consecutive_errors += 1
                        if consecutive_errors >= max_consecutive_errors:
                            logger.error(f"❌ Too many errors - stopping")
                            break
                        await asyncio.sleep(0.01)
            
            logger.info(f"✅ send_frames() ended after {frame_count} frames")
        
        async def receive_commands():
            """Receive commands from client"""
            disconnected = False
            while not disconnected:
                try:
                    if websocket.client_state.name == 'DISCONNECTED':
                        disconnected = True
                        break
                    
                    message = await asyncio.wait_for(websocket.receive(), timeout=0.1)
                    
                    if 'text' in message:
                        data = message['text']
                        cmd = json.loads(data)
                        
                        # Handle traffic light specific commands
                        if cmd.get('command') == 'set_roi':
                            rois_payload = cmd.get('rois')
                            if isinstance(rois_payload, list):
                                rois_payload = {
                                    f"roi_{idx + 1}": item for idx, item in enumerate(rois_payload)
                                }
                            if stream:
                                count = stream.set_roi_polygons(rois_payload)
                                logger.info(f"🗺️ ROI polygons updated ({count})")
                                await websocket.send_text(json.dumps(jsonable_encoder({
                                    "type": "roi_ack",
                                    "count": count
                                })))
                        elif cmd.get('command') == 'clear_roi':
                            if stream:
                                stream.clear_roi_polygons()
                                logger.info("🧹 ROI cleared")
                                await websocket.send_text(json.dumps(jsonable_encoder({
                                    "type": "roi_cleared"
                                })))
                
                except asyncio.TimeoutError:
                    continue
                except WebSocketDisconnect:
                    disconnected = True
                    break
                except Exception as e:
                    error_str = str(e)
                    if "disconnect" in error_str.lower():
                        disconnected = True
                        break
                    logger.warning(f"Command receive error: {e}")
                    await asyncio.sleep(0.01)
        
        # Run both tasks
        send_task = asyncio.create_task(send_frames())
        recv_task = asyncio.create_task(receive_commands())
        
        done, pending = await asyncio.wait(
            {send_task, recv_task},
            return_when=asyncio.FIRST_COMPLETED
        )
        
        # Cancel pending tasks
        for task in pending:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        
        # Check exceptions
        for task in done:
            try:
                task.result()
            except Exception as e:
                logger.warning(f"Task exception: {e}")
        
        logger.info("✅ Stream ended normally")
    
    except WebSocketDisconnect as e:
        logger.info(f"❌ Client disconnected: {e}")
    
    except Exception as e:
        logger.error(f"❌ Error: {e}", exc_info=True)
        try:
            await websocket.send_text(json.dumps(jsonable_encoder({
                "type": "error",
                "message": str(e)
            })))
        except:
            pass
    
    finally:
        # Force stop stream
        if stream:
            logger.info("🧹 Force stopping stream...")
            import time
            start_time = time.time()
            
            try:
                stream.stop()
                stream.close()
                
                elapsed = time.time() - start_time
                if elapsed > 2.0:
                    logger.warning(f"⚠️ Stream cleanup took {elapsed:.2f}s")
                else:
                    logger.info(f"✅ Stream stopped in {elapsed:.2f}s")
            except Exception as e:
                logger.error(f"❌ Stream cleanup error: {e}")
        
        # Close WebSocket
        try:
            await websocket.close()
        except:
            pass
        
        logger.info("✅ Traffic Light WebSocket handler complete")


@router.get("/health")
async def traffic_light_health():
    """Health check for traffic light detection"""
    return {
        "status": "healthy",
        "service": "traffic_light_detection",
        "features": [
            "Traffic light detection",
            "Violation detection",
            "ROI support",
            "Real-time streaming"
        ]
    }