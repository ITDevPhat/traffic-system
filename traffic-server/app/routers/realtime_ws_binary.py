"""
Binary WebSocket Router - 2-phase (text header + binary JPEG)
Optimized for 30 FPS with TurboJPEG + multithreading
"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, HTTPException, UploadFile
from app.services.realtime_binary_stream import BinaryAnnotStream
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
    conf: float = Query(0.35, description="Confidence threshold"),
    fps: int = Query(30, description="Target FPS (default 30)"),
    imgsz: int = Query(480, description="YOLO inference size (480/640/960)"),
    quality: int = Query(55, description="JPEG quality (1-100, lower=faster)"),
    encode_width: int = Query(960, description="Downscale width before encoding"),
    model_path: str = Query("models/yolov8n.pt", description="YOLO model path (nano)"),
    veh_detect_hz: int = Query(25, description="Vehicle detect frequency for keyframes (Hz)"),
    enable_yolo: bool = Query(True, description="Enable YOLO detection"),
    enable_tracking: bool = Query(True, description="Enable ByteTrack tracking"),
    enable_bbox_drawing: bool = Query(True, description="Enable bbox drawing")
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
               f"Quality: {quality}, EncodeWidth: {encode_width}")
    
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
            enable_bbox_drawing=enable_bbox_drawing
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
                while True:
                    try:
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
                        
                    except asyncio.TimeoutError:
                        # Normal timeout, continue loop
                        continue
                    except Exception as e:
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
    # Quick GPU check without heavy imports
    cuda_available = False
    device_name = "Unknown"
    
    if torch is not None:
        cuda_available = torch.cuda.is_available()
        if cuda_available:
            device_name = torch.cuda.get_device_name(0)
    
    if not cuda_available:
        detail = {
            "error": "GPU not detected: CUDA required.",
            "torch_cuda_available": cuda_available,
        }
        raise HTTPException(status_code=400, detail=detail)
    
    # Just verify CUDA is available
    # Actual model loading happens in BinaryAnnotStream
    return {
        "status": "models ready",
        "device": "cuda",
        "device_name": device_name,
        "note": "Models will be loaded when detection starts"
    }


@router.get("/models/available")
async def get_available_models():
    """Get list of available YOLO models from traffic-server/models/"""
    # Always use traffic-server/models as the standard location
    models_dir = "models"
    if not os.path.exists(models_dir):
        models_dir = os.path.join("traffic-server", "models")
    
    if not os.path.exists(models_dir):
        return {"ok": False, "error": "Models directory not found"}
    
    logger.info(f"📂 Scanning models in: {models_dir}")
    pt_files = glob.glob(os.path.join(models_dir, "*.pt"))
    
    models = {
        "vehicle": [],
        "plate": [],
        "ocr": [],
        "traffic_light": []
    }
    
    for pt_file in pt_files:
        basename = os.path.basename(pt_file)
        if "vehicle" in basename.lower():
            models["vehicle"].append(basename)
        elif "plate" in basename.lower():
            models["plate"].append(basename)
        elif "ocr" in basename.lower():
            models["ocr"].append(basename)
        elif "light" in basename.lower() or "traffic" in basename.lower():
            models["traffic_light"].append(basename)
    
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

