"""
Traffic Light Detection WebSocket Router
Separate pipeline for traffic light violation detection
"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, HTTPException
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
from datetime import datetime
from app.violations.violation_manager import violation_manager
from app.services.traffic_light_manager import traffic_light_manager

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
        # Normalized ROI (preferred path)
        traffic_light_manager.set_roi(camera_id, roi_data)
        pixel_bounds = traffic_light_manager.roi_to_pixels(camera_id, (h, w))
        if not pixel_bounds:
            return None, None
        x1, y1, x2, y2 = pixel_bounds

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
        return "UNKNOWN", 0.0
    
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
    
    if max_pixels < total_pixels * 0.01:  # Less than 1% colored pixels
        return "GREEN", 0.0
    
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
            from pathlib import Path

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
            else:
                logger.warning(f"⚠️ Config file not found: {config_path}")
        except Exception as e:
            logger.error(f"❌ Failed to load TL config: {e}", exc_info=True)
        
        # Send info packet
        info = stream.info_packet()
        info['traffic_light_enabled'] = enable_traffic_light
        info['violation_enabled'] = enable_violation
        await websocket.send_text(json.dumps(info))
        logger.info(f"📤 Sent info: {info}")
        
        # Stream loop
        async def send_frames():
            """Send frames with traffic light data"""
            frame_count = 0
            consecutive_errors = 0
            max_consecutive_errors = 3
            last_tl_update = 0
            tl_update_interval = 0.5  # Update TL every 500ms
            
            # Cache traffic light state to use for all frames
            cached_tl_state = {
                'state': 'UNKNOWN',
                'confidence': 0.0,
                'roi_frame': None,
                'roi_bounds': None
            }
            
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
                    
                    if websocket.client_state.name == 'DISCONNECTED':
                        break
                    
                    # Use camera_id from query param (already available from function signature)
                    
                    # Add traffic light ROI data to header
                    import time
                    current_time = time.time()
                    
                    # Update traffic light detection every 500ms
                    if enable_traffic_light and (current_time - last_tl_update) >= tl_update_interval:
                        # Decode JPEG to get frame for TL detection
                        frame_array = np.frombuffer(jpeg_bytes, dtype=np.uint8)
                        frame = cv2.imdecode(frame_array, cv2.IMREAD_COLOR)

                        if frame is not None:
                            # Log ROI storage status periodically
                            if frame_count % 100 == 0:
                                logger.info(f"🔍 ROI storage keys: {list(roi_storage.keys())}, looking for: {camera_id}")
                            
                            # Crop and detect traffic light
                            roi_frame, roi_data = crop_tl_roi(frame, camera_id)
                            
                            if roi_frame is not None:
                                # Detect state
                                raw_state, raw_confidence = detect_traffic_light_state(roi_frame)
                                state, confidence = traffic_light_manager.stabilize_state(
                                    camera_id, raw_state, raw_confidence
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
                                # Update cached state with error
                                cached_tl_state = {
                                    'state': 'UNKNOWN',
                                    'confidence': 0.0,
                                    'roi_frame': None,
                                    'error': f'No ROI configured for camera_id={camera_id}'
                                }
                                if frame_count % 100 == 0:
                                    logger.warning(f"⚠️ No ROI for camera_id={camera_id}, available: {list(roi_storage.keys())}")

                        last_tl_update = current_time
                    
                    # Always add cached traffic light state to header (for all frames)
                    header['traffic_light'] = cached_tl_state

                    # Violation detection using cached state
                    if enable_violation:
                        traffic_light_state = cached_tl_state.get("state", "UNKNOWN")
                        tracks = header.get("detections", [])

                        if frame_count % 20 == 0:
                            logger.info(
                                f"[DEBUG VIOLATION] cam={camera_id}, "
                                f"tl_state={traffic_light_state}, "
                                f"tracks={len(tracks)}, "
                                f"sample_track={tracks[0] if tracks else None}"
                            )

                        violations = violation_manager.compute_violations(
                            camera_id=camera_id,
                            tracks=tracks,
                            light_state=traffic_light_state,
                            timestamp=datetime.utcnow(),
                        )
                        header["violations"] = [v.__dict__ for v in violations]

                        # Map violation to detections for frontend
                        if violations and tracks:
                            viol_by_tid = {v.track_id: v for v in violations}
                            for det in tracks:
                                tid = det.get("track_id")
                                if tid in viol_by_tid:
                                    det["violation"] = viol_by_tid[tid].violation_type

                    try:
                        # Send header with traffic light data
                        await asyncio.wait_for(
                            websocket.send_text(json.dumps(header)),
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
                                await websocket.send_text(json.dumps({
                                    "type": "roi_ack",
                                    "count": count
                                }))
                        elif cmd.get('command') == 'clear_roi':
                            if stream:
                                stream.clear_roi_polygons()
                                logger.info("🧹 ROI cleared")
                                await websocket.send_text(json.dumps({
                                    "type": "roi_cleared"
                                }))
                
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
            await websocket.send_text(json.dumps({
                "type": "error",
                "message": str(e)
            }))
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