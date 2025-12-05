from __future__ import annotations

import asyncio
import base64
import logging
from typing import Callable, Dict, Optional

import cv2
from fastapi import APIRouter, HTTPException, Query, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field

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


class StoplineRect(BaseModel):
    x1: float = Field(..., ge=0.0, le=1.0)
    y1: float = Field(..., ge=0.0, le=1.0)
    x2: float = Field(..., ge=0.0, le=1.0)
    y2: float = Field(..., ge=0.0, le=1.0)


class RoiPayload(BaseModel):
    camera_id: str
    roi: NormalizedRoi


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

    def ensure_loop(self) -> None:
        if self.loop is None:
            try:
                self.loop = asyncio.get_event_loop()
            except RuntimeError:
                self.loop = None

    def set_frame_provider(self, camera_id: str, provider: Callable[[], object]) -> None:
        self.frame_providers[camera_id] = provider

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
        log.info("🚦 Started traffic light worker for %s", camera_id)

    def stop_worker(self, camera_id: str) -> None:
        worker = self.workers.pop(camera_id, None)
        if worker:
            worker.stop()
            log.info("🛑 Stopped traffic light worker for %s", camera_id)

    def _handle_update(self, camera_id: str, state: TrafficLightState, crop) -> None:
        if self.loop is None:
            return
        queue = self.queues.get(camera_id)
        if queue is None:
            return
        payload = {
            "camera_id": camera_id,
            "state": state.state,
            "confidence": state.confidence,
            "timestamp": state.timestamp.isoformat(),
        }
        if crop is not None and crop.size:
            success, encoded = cv2.imencode(".jpg", crop)
            if success:
                payload["roi_frame"] = base64.b64encode(encoded.tobytes()).decode()
        self.loop.call_soon_threadsafe(queue.put_nowait, payload)

    async def subscribe(self, camera_id: str) -> asyncio.Queue:
        self.ensure_loop()
        queue = self.queues.get(camera_id)
        if queue is None:
            queue = asyncio.Queue()
            self.queues[camera_id] = queue
        return queue


manager = TrafficLightManager()


@router.post("/roi")
def set_traffic_light_roi(payload: RoiPayload):
    try:
        save_traffic_light_roi(payload.camera_id, payload.roi.model_dump())
    except RoiConfigError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    manager.start_worker(payload.camera_id, payload.roi.model_dump())
    return {"camera_id": payload.camera_id, "roi": payload.roi}


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
    await websocket.accept()

    roi = get_traffic_light_roi(camera_id)
    if not roi:
        await websocket.send_json({"error": "ROI not configured"})
        await websocket.close(code=4000)
        return

    queue = await manager.subscribe(camera_id)
    manager.start_worker(camera_id, roi)

    try:
        while True:
            data = await queue.get()
            await websocket.send_json(data)
    except WebSocketDisconnect:
        pass
    finally:
        # Keep worker alive for other subscribers unless no more
        pass
