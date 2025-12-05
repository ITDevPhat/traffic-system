from __future__ import annotations

import asyncio
import base64
import logging
from typing import Callable, Dict, Optional

import cv2
from fastapi import APIRouter, HTTPException, Query, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field, model_validator

from app.config.roi_config import (
    RoiConfigError,
    get_stopline,
    get_traffic_light_roi,
    save_stopline,
    save_traffic_light_roi,
)
from app.services.traffic_light_worker import TrafficLightState, TrafficLightWorker

router = APIRouter(prefix="/api/traffic-light", tags=["Traffic Light Config"])

log = logging.getLogger(__name__)


class NormalizedRoi(BaseModel):
    x: float = Field(..., ge=0.0, le=1.0)
    y: float = Field(..., ge=0.0, le=1.0)
    width: float = Field(..., gt=0.0, le=1.0)
    height: float = Field(..., gt=0.0, le=1.0)


class PixelRoi(BaseModel):
    """Pixel-based ROI coordinates"""
    x1: int = Field(..., ge=0, description="Top-left X")
    y1: int = Field(..., ge=0, description="Top-left Y")
    x2: int = Field(..., ge=0, description="Bottom-right X")
    y2: int = Field(..., ge=0, description="Bottom-right Y")


class StoplineRect(BaseModel):
    x1: float = Field(..., ge=0.0, le=1.0)
    y1: float = Field(..., ge=0.0, le=1.0)
    x2: float = Field(..., ge=0.0, le=1.0)
    y2: float = Field(..., ge=0.0, le=1.0)


class RoiPayload(BaseModel):
    camera_id: str
    roi: Optional[NormalizedRoi] = None
    roi_pixel: Optional[PixelRoi] = None
    frame_width: Optional[int] = Field(None, description="Frame width for pixel to normalized conversion")
    frame_height: Optional[int] = Field(None, description="Frame height for pixel to normalized conversion")
    
    @model_validator(mode='after')
    def check_roi_provided(self):
        if not self.roi and not self.roi_pixel:
            raise ValueError("Either 'roi' or 'roi_pixel' must be provided")
        return self


class StoplinePayload(BaseModel):
    camera_id: str
    stopline: StoplineRect


class TrafficLightManager:
    """In-memory manager for TL workers and websocket subscribers."""

    def __init__(self) -> None:
        self.workers: Dict[str, TrafficLightWorker] = {}
        self.frame_providers: Dict[str, Callable[[], object]] = {}
        self.queues: Dict[str, asyncio.Queue] = {}
        self.loop: Optional[asyncio.AbstractEventLoop] = None
        # Store ROI configs (both normalized and pixel)
        self.roi_configs: Dict[str, Dict] = {}

    def ensure_loop(self) -> None:
        if self.loop is None:
            try:
                self.loop = asyncio.get_event_loop()
            except RuntimeError:
                self.loop = None

    def set_frame_provider(self, camera_id: str, provider: Callable[[], object]) -> None:
        self.frame_providers[camera_id] = provider
        log.info("📹 Frame provider set for camera %s", camera_id)

    def set_roi(self, camera_id: str, roi_config: Dict) -> None:
        """Store ROI config (can be normalized or pixel-based)"""
        self.roi_configs[camera_id] = roi_config
        log.info("🎯 ROI config stored for camera %s: %s", camera_id, roi_config)

    def get_roi(self, camera_id: str) -> Optional[Dict]:
        """Get stored ROI config"""
        return self.roi_configs.get(camera_id)

    def start_worker(self, camera_id: str, roi_norm: Dict[str, float]) -> None:
        provider = self.frame_providers.get(camera_id, lambda: None)
        if camera_id in self.workers:
            self.workers[camera_id].stop()
        worker = TrafficLightWorker(
            camera_id=camera_id,
            roi_norm=roi_norm,
            frame_provider=provider,
            update_callback=self._handle_update,
        )
        self.workers[camera_id] = worker
        worker.start()
        log.info("🚦 Started traffic light worker for %s with ROI: %s", camera_id, roi_norm)

    def stop_worker(self, camera_id: str) -> None:
        worker = self.workers.pop(camera_id, None)
        if worker:
            worker.stop()
            log.info("🛑 Stopped traffic light worker for %s", camera_id)

    def _handle_update(self, camera_id: str, state: TrafficLightState, crop) -> None:
        if self.loop is None:
            self.ensure_loop()
        if self.loop is None:
            log.warning("⚠️ No event loop available for camera %s", camera_id)
            return
        queue = self.queues.get(camera_id)
        if queue is None:
            log.debug("No queue for camera %s, skipping update", camera_id)
            return
        payload = {
            "camera_id": camera_id,
            "state": state.state,
            "confidence": state.confidence,
            "timestamp": state.timestamp.isoformat(),
        }
        # CRITICAL: Always include roi_frame if crop is available
        if crop is not None and crop.size > 0:
            success, encoded = cv2.imencode(".jpg", crop, [cv2.IMWRITE_JPEG_QUALITY, 80])
            if success:
                payload["roi_frame"] = base64.b64encode(encoded.tobytes()).decode()
                log.debug("📤 Sending roi_frame for camera %s (size: %d bytes)", camera_id, len(payload["roi_frame"]))
            else:
                log.warning("⚠️ Failed to encode roi_frame for camera %s", camera_id)
        else:
            log.warning("⚠️ No crop available for camera %s", camera_id)
        
        try:
            self.loop.call_soon_threadsafe(queue.put_nowait, payload)
        except Exception as e:
            log.error("❌ Failed to send update for camera %s: %s", camera_id, e)

    async def subscribe(self, camera_id: str) -> asyncio.Queue:
        self.ensure_loop()
        queue = self.queues.get(camera_id)
        if queue is None:
            queue = asyncio.Queue()
            self.queues[camera_id] = queue
            log.info("📬 Created queue for camera %s", camera_id)
        return queue


manager = TrafficLightManager()


@router.post("/config/roi")
def set_traffic_light_roi_config(payload: RoiPayload):
    """
    Set traffic light ROI - supports both normalized and pixel coordinates.
    
    If roi_pixel is provided, it will be converted to normalized coordinates
    using frame_width and frame_height (defaults to 1920x1080 if not provided).
    """
    try:
        roi_norm = None
        
        # Handle pixel-based ROI
        if payload.roi_pixel:
            # Use provided frame dimensions or defaults
            frame_width = payload.frame_width or 1920
            frame_height = payload.frame_height or 1080
            
            x1 = payload.roi_pixel.x1
            y1 = payload.roi_pixel.y1
            x2 = payload.roi_pixel.x2
            y2 = payload.roi_pixel.y2
            
            # Validate pixel coordinates
            if x2 <= x1 or y2 <= y1:
                raise HTTPException(status_code=400, detail="Invalid ROI: x2 must be > x1 and y2 must be > y1")
            
            # Convert to normalized coordinates
            roi_norm = {
                "x": x1 / frame_width,
                "y": y1 / frame_height,
                "width": (x2 - x1) / frame_width,
                "height": (y2 - y1) / frame_height
            }
            
            log.info("🔄 Converted pixel ROI (%d,%d,%d,%d) to normalized: %s", x1, y1, x2, y2, roi_norm)
            
            # Store pixel ROI config for reference
            manager.set_roi(payload.camera_id, {
                "type": "pixel",
                "x1": x1, "y1": y1, "x2": x2, "y2": y2,
                "frame_width": frame_width,
                "frame_height": frame_height,
                "normalized": roi_norm
            })
        
        # Handle normalized ROI
        elif payload.roi:
            roi_norm = payload.roi.model_dump()
            manager.set_roi(payload.camera_id, {
                "type": "normalized",
                **roi_norm
            })
        
        # Save to persistent storage
        save_traffic_light_roi(payload.camera_id, roi_norm)
        
        # Start worker with normalized ROI
        manager.start_worker(payload.camera_id, roi_norm)
        
        return {
            "ok": True,
            "camera_id": payload.camera_id,
            "roi": roi_norm,
            "message": "Traffic light ROI saved and worker started"
        }
        
    except RoiConfigError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except HTTPException:
        raise
    except Exception as e:
        log.error("❌ Error setting TL ROI: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/stop")
def stop_traffic_light_worker(camera_id: str):
    manager.stop_worker(camera_id)
    return {"camera_id": camera_id, "status": "stopped"}


@router.post("/config/stopline")
def set_stopline(payload: StoplinePayload):
    try:
        save_stopline(payload.camera_id, payload.stopline.model_dump())
    except RoiConfigError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return payload


@router.get("/config/stopline")
def get_stopline_config(camera_id: str = Query(..., description="Camera ID")):
    try:
        stopline = get_stopline(camera_id)
    except RoiConfigError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return {"camera_id": camera_id, "stopline": stopline}


@router.websocket("/ws/traffic-light")
async def traffic_light_ws(websocket: WebSocket, camera_id: str):
    """
    WebSocket endpoint for streaming traffic light detection results.
    
    Sends JSON messages with:
    - state: GREEN | RED | YELLOW | UNKNOWN
    - confidence: float 0-1
    - timestamp: ISO timestamp
    - roi_frame: base64 encoded JPEG of the ROI crop (ALWAYS included when available)
    """
    await websocket.accept()
    log.info("🔌 Traffic Light WebSocket connected for camera: %s", camera_id)

    roi = get_traffic_light_roi(camera_id)
    if not roi:
        log.warning("⚠️ No ROI configured for camera %s", camera_id)
        await websocket.send_json({
            "error": "ROI not configured",
            "message": "Please set ROI first using POST /api/traffic-light/roi"
        })
        await websocket.close(code=4000)
        return

    log.info("✅ ROI found for camera %s: %s", camera_id, roi)
    
    queue = await manager.subscribe(camera_id)
    manager.start_worker(camera_id, roi)
    
    # Send initial confirmation
    await websocket.send_json({
        "type": "connected",
        "camera_id": camera_id,
        "roi": roi,
        "message": "Traffic light detection started"
    })

    try:
        while True:
            data = await queue.get()
            # Ensure roi_frame is always sent
            if "roi_frame" not in data:
                log.warning("⚠️ No roi_frame in data for camera %s", camera_id)
            await websocket.send_json(data)
            log.debug("📤 Sent TL update: state=%s, has_frame=%s", 
                     data.get("state"), "roi_frame" in data)
    except WebSocketDisconnect:
        log.info("🔌 WebSocket disconnected for camera %s", camera_id)
    except Exception as e:
        log.error("❌ WebSocket error for camera %s: %s", camera_id, e)
    finally:
        # Keep worker alive for other subscribers unless no more
        log.info("🧹 Cleaning up WebSocket for camera %s", camera_id)
