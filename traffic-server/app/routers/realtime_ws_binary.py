"""
Binary WebSocket Router - 2-phase (text header + binary JPEG)
Optimized for 30 FPS with TurboJPEG + multithreading
"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, HTTPException, UploadFile
from app.services.realtime_binary_stream import (
    BinaryAnnotStream,
    DEFAULT_REALTIME_MODEL_PATH,
)
from typing import Dict, Any
from fastapi import Body
import json
import logging
import os
import glob
import uuid

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/detection", tags=["realtime-binary"])

# Import torch for GPU checks
try:
    import torch
except:
    torch = None


@router.websocket("/realtime")
async def ws_realtime_binary(
    websocket: WebSocket,
    source: str = Query("0", description="Video source: '0' for webcam, path for file"),
    conf: float = Query(0.5, description="Confidence threshold"),
    fps: int = Query(30, description="Target FPS (default 30)"),
    imgsz: int = Query(640, description="YOLO inference size - MUST be 640 for TensorRT models"),
    quality: int = Query(60, description="JPEG quality (1-100, lower=faster)"),
    encode_width: int = Query(960, description="Downscale width before encoding"),
    model_path: str = Query(
        DEFAULT_REALTIME_MODEL_PATH,
        description="YOLO model path (default: 11s TensorRT)",
    ),
    veh_detect_hz: int = Query(25, description="Vehicle detect frequency for keyframes (Hz)"),
    enable_yolo: bool = Query(True, description="Enable YOLO detection"),
    enable_tracking: bool = Query(True, description="Enable ByteTrack tracking"),
    enable_bbox_drawing: bool = Query(True, description="Enable bbox drawing"),
    enable_roi: bool = Query(True, description="Enable ROI module"),
    enable_roi_drawing: bool = Query(True, description="Enable ROI drawing"),
    force_gpu: bool = Query(True, description="Require CUDA GPU (disable for CPU fallback)"),
    warmup: float = Query(5.0, description="Seconds to keep backend warming before streaming"),
):
    """
    Binary WebSocket - 30 FPS optimized
    
    Protocol:
    1. Send `info` packet (text JSON) once at start
    2. Loop:
       a) Send `frame` header (text JSON) with frame_idx, fps
       b) Send JPEG bytes (binary) immediately after
    
    Client receives:
    - text message → parse JSON
    - binary message → decode JPEG with createImageBitmap
    
    Optimizations:
    - TurboJPEG: 2-3x faster encoding
    - Multithreading: 4-stage pipeline
    - Latest-wins queues: drop old frames
    - Server-side pacing: stable FPS
    - No base64: direct binary transfer
    """
    logger.info(f"🔔 Binary WS connection from: {websocket.client}")
    logger.info(f"📹 Source: {source}, Conf: {conf}, FPS: {fps}, ImgSize: {imgsz}, "
               f"Quality: {quality}, EncodeWidth: {encode_width}, ForceGPU: {force_gpu}")
    
    await websocket.accept()
    logger.info("✅ WebSocket accepted")
    
    stream = None
    
    try:
        # Initialize stream
        stream = BinaryAnnotStream(
            source=source,
            conf=conf,
            imgsz=imgsz,
            target_fps=fps,
            jpeg_quality=quality,
            encode_width=encode_width,
            model_path=model_path,
            veh_detect_hz=veh_detect_hz,
            enable_yolo=enable_yolo,
            enable_tracking=enable_tracking,
            enable_bbox_drawing=enable_bbox_drawing,
            enable_roi=enable_roi,
            enable_roi_drawing=enable_roi_drawing,
            force_gpu=force_gpu,
            warmup_seconds=warmup,
        )
        
        # Start all threads
        stream.start()
        
        # Send info packet first (text)
        info = stream.info_packet()
        await websocket.send_text(json.dumps(info))
        logger.info(f"📤 Sent info: {info}")
        
        # Stream loop: header (text) + binary (jpeg)
        # Use asyncio to handle both sending frames and receiving commands
        import asyncio
        
        # Create tasks for concurrent execution
        send_task = None
        recv_task = None
        
        try:
            async def send_frames():
                while True:
                    header, jpeg_bytes = stream.next_frame()
                    
                    if header is None or jpeg_bytes is None:
                        await asyncio.sleep(0.001)
                        continue
                    
                    # 1) Send header (text JSON)
                    await websocket.send_text(json.dumps(header))
                    
                    # 2) Send binary JPEG immediately after
                    await websocket.send_bytes(jpeg_bytes)
            
            async def receive_commands():
                disconnected = False
                while not disconnected:
                    try:
                        # Check if websocket is still connected before receiving
                        if websocket.client_state.name == 'DISCONNECTED':
                            disconnected = True
                            break
                        
                        # Use receive() to get any message type
                        message = await asyncio.wait_for(websocket.receive(), timeout=0.1)
                        
                        # Only process text messages (commands)
                        if 'text' in message:
                            data = message['text']
                            cmd = json.loads(data)
                            
                            if cmd.get('command') == 'toggle_bbox':
                                enabled = cmd.get('enabled', True)
                                stream.enable_bbox_drawing = enabled
                                logger.info(f"🎨 BBox drawing toggled to: {enabled}")
                            elif cmd.get('command') == 'update_settings':
                                # Live settings update during detection
                                settings = cmd.get('settings', {})
                                updated = []
                                
                                # Update confidence threshold
                                if 'conf' in settings:
                                    new_conf = float(settings['conf'])
                                    if 0.1 <= new_conf <= 0.9:
                                        stream.conf = new_conf
                                        updated.append(f"conf={new_conf:.2f}")
                                
                                # Update target FPS
                                if 'target_fps' in settings:
                                    new_fps = int(settings['target_fps'])
                                    if 15 <= new_fps <= 60:
                                        stream.target_fps = new_fps
                                        updated.append(f"fps={new_fps}")
                                
                                # Update JPEG quality
                                if 'jpeg_quality' in settings:
                                    new_quality = int(settings['jpeg_quality'])
                                    if 50 <= new_quality <= 95:
                                        stream.jpeg_quality = new_quality
                                        updated.append(f"quality={new_quality}")
                                
                                # Update inference size (requires restart)
                                if 'inference_size' in settings:
                                    new_size = int(settings['inference_size'])
                                    if new_size in [480, 640, 832, 960]:
                                        stream.imgsz = new_size
                                        updated.append(f"imgsz={new_size}")
                                
                                if updated:
                                    logger.info(f"⚙️ Live settings updated: {', '.join(updated)}")
                                    # Send confirmation back to frontend
                                    await websocket.send_text(json.dumps({
                                        "type": "settings_updated",
                                        "message": f"Updated: {', '.join(updated)}"
                                    }))
                            elif cmd.get('command') == 'set_roi':
                                rois_payload = cmd.get('rois')
                                if isinstance(rois_payload, list):
                                    rois_payload = {
                                        f"roi_{idx + 1}": item for idx, item in enumerate(rois_payload)
                                    }
                                if not isinstance(rois_payload, dict):
                                    await websocket.send_text(json.dumps({
                                        "type": "roi_error",
                                        "message": "Invalid ROI payload"
                                    }))
                                    continue
                                count = 0
                                if stream:
                                    count = stream.set_roi_polygons(rois_payload)
                                logger.info(f"🗺️  ROI polygons updated ({count})")
                                await websocket.send_text(json.dumps({
                                    "type": "roi_ack",
                                    "count": count
                                }))
                            elif cmd.get('command') == 'clear_roi':
                                if stream:
                                    stream.clear_roi_polygons()
                                logger.info("🧹 ROI polygons cleared via command")
                                await websocket.send_text(json.dumps({
                                    "type": "roi_cleared"
                                }))

                    except asyncio.TimeoutError:
                        # Normal timeout, continue loop
                        continue
                    except WebSocketDisconnect:
                        disconnected = True
                        break
                    except Exception as e:
                        # Check if it's a disconnect-related error
                        error_str = str(e)
                        if "disconnect" in error_str.lower() or "Cannot call" in error_str:
                            disconnected = True
                            break
                        logger.warning(f"Command receive error: {e}")
                        await asyncio.sleep(0.01)
            
            # Run both tasks concurrently
            send_task = asyncio.create_task(send_frames())
            recv_task = asyncio.create_task(receive_commands())
            
            await asyncio.gather(send_task, recv_task)
        
        finally:
            # Cancel tasks on exit
            if send_task and not send_task.done():
                send_task.cancel()
            if recv_task and not recv_task.done():
                recv_task.cancel()
        
        logger.info("✅ Stream ended normally")
    
    except WebSocketDisconnect:
        logger.info("❌ Client disconnected")
        if stream:
            stream.stop()
    
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
        if stream:
            logger.info("🧹 Cleaning up stream...")
            stream.stop()
            stream.close()
        
        try:
            await websocket.close()
        except:
            pass
        
        logger.info("✅ WebSocket closed")


# -------------------- Control Endpoints (Pause/Resume/Seek) --------------------

@router.post("/realtime/pause")
async def realtime_pause():
    """Pause the current stream (if any)."""
    try:
        # Access global/cached stream is not tracked here; in production, map by client
        # For demo, respond OK (frontend will pause locally)
        return {"ok": True}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@router.post("/realtime/resume")
async def realtime_resume():
    """Resume the current stream (if any)."""
    try:
        return {"ok": True}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@router.post("/realtime/seek")
async def realtime_seek(payload: Dict[str, Any] = Body(...)):
    """Request a relative seek in seconds (negative=backward)."""
    try:
        seconds = float(payload.get("seconds", 0))
        # The stream instance is not globally tracked; client will reconnect with new offset in future
        # Here we simply ack.
        return {"ok": True, "seconds": seconds}
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ========================== REST API Endpoints ==========================

@router.post("/models/load")
async def load_models():
    """Load YOLO models onto GPU - Fast check only"""
    try:
        # Quick GPU check without heavy imports
        cuda_available = False
        device_name = "Unknown"
        
        if torch is not None:
            cuda_available = torch.cuda.is_available()
            if cuda_available:
                try:
                    device_name = torch.cuda.get_device_name(0)
                except Exception as e:
                    logger.warning(f"Failed to get device name: {e}")
                    device_name = "CUDA Device"
        else:
            raise HTTPException(
                status_code=500,
                detail={
                    "error": "PyTorch not available",
                    "message": "PyTorch library is not installed or not accessible"
                }
            )
        
        if not cuda_available:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "GPU not detected: CUDA required.",
                    "message": "CUDA is not available. Please ensure NVIDIA GPU drivers and CUDA are installed.",
                    "torch_cuda_available": cuda_available,
                }
            )
        
        # Just verify CUDA is available
        # Actual model loading happens in BinaryAnnotStream
        return {
            "status": "models ready",
            "device": "cuda",
            "device_name": device_name,
            "note": "Models will be loaded when detection starts"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in load_models: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "error": str(e),
                "message": "Internal server error while checking GPU status"
            }
        )


@router.get("/models/available")
async def get_available_models():
    """Get list of available YOLO models from traffic-server/models/
    Supports .onnx, .pt formats only (TensorRT .engine files excluded)
    """
    # Always use traffic-server/models as the standard location
    models_dir = "models"
    if not os.path.exists(models_dir):
        models_dir = os.path.join("traffic-server", "models")
    
    if not os.path.exists(models_dir):
        return {"ok": False, "error": "Models directory not found"}
    
    logger.info(f"📂 Scanning models in: {models_dir}")
    
    # Scan supported formats: .onnx > .pt (TensorRT .engine excluded)
    model_extensions = ["*.onnx", "*.pt"]
    all_files = []
    for ext in model_extensions:
        files = glob.glob(os.path.join(models_dir, "**", ext), recursive=True)
        all_files.extend(files)
    
    # Also scan root directory
    for ext in model_extensions:
        files = glob.glob(os.path.join(models_dir, ext))
        all_files.extend(files)
    
    models = {
        "vehicle": [],
        "plate": [],
        "ocr": [],
        "traffic_light": []
    }
    
    # Track which models we've found (to avoid duplicates, prioritize .onnx > .pt)
    found_models = {}
    
    for model_file in all_files:
        basename = os.path.basename(model_file)
        model_name = os.path.splitext(basename)[0]  # Without extension
        ext = os.path.splitext(basename)[1].lower()
        
        # Priority: onnx=1, pt=2 (engine removed)
        priority = {"onnx": 1, "pt": 2}.get(ext[1:], 999)
        
        category = None
        if "vehicle" in basename.lower():
            category = "vehicle"
        elif "plate" in basename.lower():
            category = "plate"
        elif "ocr" in basename.lower():
            category = "ocr"
        elif "light" in basename.lower() or "traffic" in basename.lower():
            category = "traffic_light"
        
        if category:
            # Only add if we haven't seen this model, or if this format has higher priority
            key = f"{category}_{model_name}"
            if key not in found_models or found_models[key][1] > priority:
                # Remove old entry if exists
                if key in found_models:
                    old_entry = found_models[key][0]
                    if old_entry in models[category]:
                        models[category].remove(old_entry)
                
                # Add new entry with format info
                model_info = {
                    "name": basename,
                    "format": ext[1:],  # "onnx" or "pt"
                    "path": os.path.relpath(model_file, models_dir).replace("\\", "/")
                }
                models[category].append(model_info)
                found_models[key] = (model_info, priority)
    
    return {"ok": True, "models": models}


@router.get("/gpu")
async def gpu_status():
    """Get GPU status"""
    if torch is None:
        return {"ok": False, "error": "torch not available"}
    
    status = {
        "cuda_available": torch.cuda.is_available(),
        "device_count": torch.cuda.device_count() if torch.cuda.is_available() else 0,
    }
    
    if torch.cuda.is_available():
        status["device_name"] = torch.cuda.get_device_name(0)
        status["memory_allocated"] = torch.cuda.memory_allocated(0)
        status["memory_reserved"] = torch.cuda.memory_reserved(0)
    
    return {"ok": True, "gpu": status}


@router.post("/upload-temp-video")
async def upload_temp_video(file: UploadFile):
    """Upload temporary video file for detection"""
    try:
        # Create temp directory
        temp_dirs = [
            "traffic-server/static/temp",
            "static/temp"
        ]
        
        temp_dir = None
        for dir_path in temp_dirs:
            try:
                os.makedirs(dir_path, exist_ok=True)
                temp_dir = dir_path
                break
            except:
                continue
        
        if temp_dir is None:
            return {"ok": False, "error": "Cannot create temp directory"}
        
        # Generate unique filename
        unique_id = uuid.uuid4().hex[:16]
        safe_filename = file.filename.replace(" ", "_")
        temp_filename = f"temp_{unique_id}_{safe_filename}"
        temp_path = os.path.join(temp_dir, temp_filename)
        
        # Save file
        with open(temp_path, "wb") as f:
            content = await file.read()
            f.write(content)
        
        logger.info(f"✅ Uploaded: {temp_path}")
        
        return {
            "ok": True,
            "temp_path": temp_path,
            "filename": safe_filename,
            "size": len(content)
        }
    
    except Exception as e:
        logger.error(f"Upload error: {e}")
        return {"ok": False, "error": str(e)}


@router.post("/models/hot-swap")
async def hot_swap_model(request: dict):
    """
    Hot-swap YOLO model without restarting server
    Supports .onnx and .pt formats only (TensorRT .engine files rejected)
    """
    try:
        model_path = request.get("model_path")
        device = request.get("device", "cuda:0")
        
        if not model_path:
            raise HTTPException(
                status_code=400,
                detail="model_path is required"
            )
        
        # Validate model format - reject .engine files
        if model_path.lower().endswith('.engine'):
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "TensorRT .engine files are no longer supported",
                    "message": "Please use .onnx or .pt models instead for better compatibility",
                    "suggestion": f"Try: {model_path.replace('.engine', '.onnx')}"
                }
            )
        
        if not model_path.lower().endswith(('.onnx', '.pt')):
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "Unsupported model format",
                    "supported_formats": [".onnx", ".pt"],
                    "provided": model_path
                }
            )
        
        # Check if model file exists
        if not os.path.exists(model_path):
            raise HTTPException(
                status_code=404,
                detail=f"Model file not found: {model_path}"
            )
        
        # Hot-swap the model
        from app.utils.model_loader import hot_swap_model
        
        success = hot_swap_model(model_path, device)
        
        if success:
            model_type = "onnx" if model_path.lower().endswith('.onnx') else "pt"
            logger.info(f"♻️ Hot-swapped model: {model_path} ({model_type.upper()})")
            
            return {
                "ok": True,
                "message": f"Model hot-swapped successfully to {model_type.upper()}",
                "model_path": model_path,
                "model_type": model_type,
                "device": device
            }
        else:
            raise HTTPException(
                status_code=500,
                detail="Failed to hot-swap model"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Hot-swap error: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": str(e),
                "message": "Internal server error during model hot-swap"
            }
        )


@router.get("/models/versions")
async def get_model_versions():
    """Get available model versions (11s, v10m) with their formats"""
    try:
        models_dir = "models/vehicle"
        if not os.path.exists(models_dir):
            return {"ok": False, "error": "Vehicle models directory not found"}
        
        versions = {}
        
        # Check for 11s models
        v11s_dir = os.path.join(models_dir, "11s")
        if os.path.exists(v11s_dir):
            v11s_models = []
            for ext in [".onnx", ".pt"]:
                model_file = os.path.join(v11s_dir, f"yolo_vehicle_11s{ext}")
                if os.path.exists(model_file):
                    size_mb = os.path.getsize(model_file) / (1024 * 1024)
                    v11s_models.append({
                        "format": ext[1:],  # Remove dot
                        "path": model_file,
                        "size_mb": round(size_mb, 1),
                        "optimized_for": "Speed & Efficiency"
                    })
            
            if v11s_models:
                versions["11s"] = {
                    "name": "YOLO11s",
                    "description": "Fast and efficient for real-time detection",
                    "models": v11s_models
                }
        
        # Check for v10m models
        v10m_dir = os.path.join(models_dir, "v10m")
        if os.path.exists(v10m_dir):
            v10m_models = []
            for ext in [".onnx", ".pt"]:
                model_file = os.path.join(v10m_dir, f"yolo_vehicle_v10m{ext}")
                if os.path.exists(model_file):
                    size_mb = os.path.getsize(model_file) / (1024 * 1024)
                    v10m_models.append({
                        "format": ext[1:],  # Remove dot
                        "path": model_file,
                        "size_mb": round(size_mb, 1),
                        "optimized_for": "Accuracy & Precision"
                    })
            
            if v10m_models:
                versions["v10m"] = {
                    "name": "YOLO10m",
                    "description": "Higher accuracy for precise detection",
                    "models": v10m_models
                }
        
        return {
            "ok": True,
            "versions": versions,
            "current_version": os.getenv("VEHICLE_MODEL_VERSION", "v10m")
        }
        
    except Exception as e:
        logger.error(f"❌ Error getting model versions: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": str(e),
                "message": "Failed to get model versions"
            }
        )


@router.post("/models/switch-version")
async def switch_model_version(request: dict):
    """Switch between model versions (11s <-> v10m) and formats (onnx <-> pt)"""
    try:
        version = request.get("version")  # "11s" or "v10m"
        format_type = request.get("format", "onnx")  # "onnx" or "pt"
        
        if not version:
            raise HTTPException(
                status_code=400,
                detail="version is required (11s or v10m)"
            )
        
        if version not in ["11s", "v10m"]:
            raise HTTPException(
                status_code=400,
                detail="version must be '11s' or 'v10m'"
            )
        
        if format_type not in ["onnx", "pt"]:
            raise HTTPException(
                status_code=400,
                detail="format must be 'onnx' or 'pt'"
            )
        
        # Build model path
        if version == "11s":
            model_path = f"models/vehicle/11s/yolo_vehicle_11s.{format_type}"
        else:  # v10m
            model_path = f"models/vehicle/v10m/yolo_vehicle_v10m.{format_type}"
        
        # Check if model exists
        if not os.path.exists(model_path):
            raise HTTPException(
                status_code=404,
                detail=f"Model not found: {model_path}"
            )
        
        # Update environment variable
        os.environ['VEHICLE_MODEL_VERSION'] = version
        
        # Hot-swap the model
        from app.utils.model_loader import hot_swap_model
        
        success = hot_swap_model(model_path, "cuda:0")
        
        if success:
            logger.info(f"🔄 Switched to model version: {version} ({format_type.upper()})")
            
            return {
                "ok": True,
                "message": f"Successfully switched to {version.upper()} ({format_type.upper()})",
                "version": version,
                "format": format_type,
                "model_path": model_path,
                "optimizations": {
                    "11s": "Speed & Real-time performance",
                    "v10m": "Accuracy & Detection precision"
                }.get(version, "Unknown")
            }
        else:
            raise HTTPException(
                status_code=500,
                detail="Failed to switch model version"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Model version switch error: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": str(e),
                "message": "Internal server error during model version switch"
            }
        )


@router.post("/settings/update")
async def update_settings(payload: Dict[str, Any]):
    """Update detection settings (confidence, modules, etc.)"""
    try:
        logger.info(f"⚙️  Settings update: {payload}")
        
        # Note: Settings are passed as query params to WebSocket
        # This endpoint just acknowledges the update
        
        return {
            "ok": True,
            "message": "Settings will be applied on next detection start",
            "settings": payload
        }
    except Exception as e:
        logger.error(f"Settings update error: {e}")
        return {"ok": False, "error": str(e)}

