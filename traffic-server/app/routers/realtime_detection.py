"""
WebSocket API for Realtime Detection Streaming
Phát hiện vi phạm realtime và stream bbox về frontend

Features:
- Load model tự động (.engine > .onnx > .pt)
- YOLO + ByteTrack inference
- Stream bbox data qua WebSocket theo FPS
- Hỗ trợ nhiều video đồng thời

Author: Traffic System Team
"""

import asyncio
import cv2
import json
import logging
import numpy as np
import time
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query
from sqlmodel import Session, select
import torch

from app.core.database import get_session
from app.models.video_job import VideoJob
from app.utils.model_loader import load_yolo_model, get_model_info
from app.core.config import settings
from app.modules import ModuleContext, VehicleYOLOModule
from app.core.performance_config import (
    INFERENCE_SETTINGS,
    WS_DEFAULT_FPS,
    WS_MAX_FPS,
    WS_MIN_FPS,
    TARGET_FPS,
    print_performance_config
)

logger = logging.getLogger("realtime_detection")
router = APIRouter()

# Print performance config on startup
print_performance_config()

# ============================================
# 🧠 Singleton Model Loader
# ============================================
class DetectionModels:
    """Singleton để load models một lần duy nhất"""
    _instance = None
    _initialized = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        logger.info("🔧 Initializing detection models...")
        
        # Device setup
        self.device = settings.DEVICE if torch.cuda.is_available() else "cpu"
        logger.info(f"🖥️  Using device: {self.device}")
        
        # Load vehicle model
        try:
            vehicle_info = get_model_info(settings.YOLO_VEHICLE_MODEL)
            if vehicle_info["found"]:
                self.vehicle = load_yolo_model(
                    vehicle_info["path"],
                    device=self.device,
                    imgsz=640,
                    half=True,
                    verbose=False
                )
                logger.info(f"✅ Vehicle model loaded: {vehicle_info['type']} ({vehicle_info['size_mb']}MB)")
            else:
                logger.error(f"❌ Vehicle model not found: {settings.YOLO_VEHICLE_MODEL}")
                self.vehicle = None
        except Exception as e:
            logger.error(f"❌ Failed to load vehicle model: {e}")
            self.vehicle = None
        
        self._initialized = True

# Global models instance
models = DetectionModels()


# ============================================
# 🎯 Video Detection Stream
# ============================================
class VideoDetectionStream:
    """Class để quản lý detection stream cho một video"""
    
    def __init__(self, video_path: str, fps: float = 30.0):
        self.video_path = video_path
        self.target_fps = min(fps, TARGET_FPS)  # Cap at TARGET_FPS
        self.cap = None
        self.vehicle_module = None
        self.last_inference_time = 0
        self.fps_counter = []
        self.frame_times = []
        
    def __enter__(self):
        """Context manager: mở video"""
        self.cap = cv2.VideoCapture(self.video_path)
        
        if not self.cap.isOpened():
            raise RuntimeError(f"Cannot open video: {self.video_path}")
        
        # Get video metadata
        self.video_fps = self.cap.get(cv2.CAP_PROP_FPS) or self.target_fps
        self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        
        # Initialize vehicle detection module with optimized settings
        self.vehicle_module = VehicleYOLOModule(
            models=models,
            enabled=True,
            use_tracking=True,  # ByteTrack
            confidence=INFERENCE_SETTINGS["conf"],  # Use optimized confidence
            device=models.device
        )
        
        # Pre-warm model (first inference is slow)
        logger.info("🔥 Warming up model...")
        dummy_frame = np.zeros((self.height, self.width, 3), dtype=np.uint8)
        dummy_context = ModuleContext(
            frame=dummy_frame,
            frame_idx=0,
            frame_size=(self.width, self.height)
        )
        self.vehicle_module.process(dummy_context)
        logger.info("✅ Model warmed up")
        
        logger.info(f"📹 Video opened: {self.width}x{self.height} @ {self.video_fps}fps ({self.total_frames} frames)")
        
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager: đóng video"""
        if self.cap:
            self.cap.release()
            logger.info("📹 Video released")
    
    async def stream_detections(self, websocket: WebSocket):
        """
        Stream detection results qua WebSocket - OPTIMIZED for >30 FPS
        
        Args:
            websocket: FastAPI WebSocket connection
        """
        frame_idx = 0
        frame_delay = 1.0 / self.target_fps  # Delay giữa các frame
        
        # Performance tracking
        last_log_time = time.time()
        frames_since_log = 0
        
        try:
            while True:
                loop_start = time.time()
                
                # Read frame
                ret, frame = self.cap.read()
                
                if not ret:
                    # Video ended - loop lại
                    self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    frame_idx = 0
                    self.fps_counter = []
                    logger.info("🔄 Video loop - restarting from frame 0")
                    continue
                
                frame_idx += 1
                frames_since_log += 1
                
                # Inference timing
                inference_start = time.time()
                
                # Prepare context
                context = ModuleContext(
                    frame=frame,
                    frame_idx=frame_idx,
                    frame_size=(self.width, self.height)
                )
                
                # Run vehicle detection + tracking
                self.vehicle_module.process(context)
                
                inference_time = time.time() - inference_start
                
                # Prepare detection data (optimized)
                detections = [
                    {
                        "label": track["class"],
                        "conf": round(track["confidence"], 2),
                        "bbox": [int(track["bbox"][0]), int(track["bbox"][1]), 
                                int(track["bbox"][2]), int(track["bbox"][3])],
                        "track_id": track["track_id"]
                    }
                    for track in context.tracks
                ]
                
                # Calculate actual FPS
                loop_time = time.time() - loop_start
                current_fps = 1.0 / loop_time if loop_time > 0 else 0
                self.fps_counter.append(current_fps)
                if len(self.fps_counter) > 30:
                    self.fps_counter.pop(0)
                avg_fps = sum(self.fps_counter) / len(self.fps_counter)
                
                # Send to frontend
                message = {
                    "type": "detection",
                    "frame": frame_idx,
                    "total_frames": self.total_frames,
                    "fps": round(avg_fps, 1),  # Actual FPS
                    "inference_ms": round(inference_time * 1000, 1),
                    "objects": detections,
                    "video_size": [self.width, self.height]
                }
                
                await websocket.send_json(message)
                
                # Log performance every second
                if time.time() - last_log_time >= 1.0:
                    logger.info(f"📊 FPS: {avg_fps:.1f} | Inference: {inference_time*1000:.1f}ms | Objects: {len(detections)}")
                    last_log_time = time.time()
                    frames_since_log = 0
                
                # Dynamic frame delay to maintain target FPS
                elapsed = time.time() - loop_start
                remaining_delay = max(0, frame_delay - elapsed)
                if remaining_delay > 0:
                    await asyncio.sleep(remaining_delay)
                
        except WebSocketDisconnect:
            logger.info("🔌 WebSocket disconnected")
        except Exception as e:
            logger.error(f"❌ Stream error: {e}", exc_info=True)
            await websocket.send_json({
                "type": "error",
                "message": str(e)
            })


# ============================================
# 🌐 WebSocket Endpoints
# ============================================
@router.websocket("/ws/detect/{video_id}")
async def websocket_detect_video_by_id(
    websocket: WebSocket,
    video_id: int,
    fps: float = Query(default=WS_DEFAULT_FPS, ge=WS_MIN_FPS, le=WS_MAX_FPS, description="Target FPS for streaming"),
    session: Session = Depends(get_session)
):
    """
    WebSocket endpoint: stream detection cho video từ database
    
    Args:
        video_id: ID của video job trong database
        fps: FPS mong muốn cho stream (mặc định 15fps để giảm lag)
    
    Protocol:
        Client -> Server: (connection)
        Server -> Client: JSON messages với detection data
        
    Message format:
        {
            "type": "detection",
            "frame": 102,
            "total_frames": 5000,
            "fps": 15.0,
            "objects": [
                {
                    "label": "car",
                    "conf": 0.92,
                    "bbox": [x1, y1, x2, y2],
                    "track_id": 5
                }
            ],
            "video_size": [1920, 1080]
        }
    """
    await websocket.accept()
    logger.info(f"🔌 WebSocket connected for video_id={video_id}")
    
    # Get video from database
    video = session.exec(
        select(VideoJob).where(VideoJob.video_job_id == video_id)
    ).first()
    
    if not video or not video.output_path:
        await websocket.send_json({
            "type": "error",
            "message": f"Video {video_id} not found or no output path"
        })
        await websocket.close()
        return
    
    video_path = video.output_path
    
    # Check if file exists
    import os
    if not os.path.exists(video_path):
        await websocket.send_json({
            "type": "error",
            "message": f"Video file not found: {video_path}"
        })
        await websocket.close()
        return
    
    # Stream detections
    try:
        with VideoDetectionStream(video_path, fps=fps) as stream:
            await stream.stream_detections(websocket)
    except Exception as e:
        logger.error(f"❌ Detection stream failed: {e}", exc_info=True)
        await websocket.send_json({
            "type": "error",
            "message": str(e)
        })
    finally:
        await websocket.close()
        logger.info(f"🔌 WebSocket closed for video_id={video_id}")


@router.websocket("/ws/detect/path")
async def websocket_detect_video_by_path(
    websocket: WebSocket,
    video_path: str = Query(..., description="Path to video file"),
    fps: float = Query(default=WS_DEFAULT_FPS, ge=WS_MIN_FPS, le=WS_MAX_FPS, description="Target FPS for streaming")
):
    """
    WebSocket endpoint: stream detection cho video từ đường dẫn
    
    Args:
        video_path: Đường dẫn đến file video
        fps: FPS mong muốn cho stream
    """
    await websocket.accept()
    logger.info(f"🔌 WebSocket connected for video_path={video_path}")
    
    # Check if file exists
    import os
    if not os.path.exists(video_path):
        await websocket.send_json({
            "type": "error",
            "message": f"Video file not found: {video_path}"
        })
        await websocket.close()
        return
    
    # Stream detections
    try:
        with VideoDetectionStream(video_path, fps=fps) as stream:
            await stream.stream_detections(websocket)
    except Exception as e:
        logger.error(f"❌ Detection stream failed: {e}", exc_info=True)
        await websocket.send_json({
            "type": "error",
            "message": str(e)
        })
    finally:
        await websocket.close()
        logger.info(f"🔌 WebSocket closed for video_path={video_path}")


@router.get("/health")
async def health_check():
    """Health check: kiểm tra model đã load chưa"""
    return {
        "status": "ok",
        "models_loaded": models.vehicle is not None,
        "device": models.device,
        "gpu_available": torch.cuda.is_available()
    }

