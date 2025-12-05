"""Lightweight worker to detect traffic light state on ROI crops.

This worker runs in its own thread and periodically crops the Region of
Interest (ROI) around the traffic light from a shared frame source, runs a
small YOLO model, and emits a debounced traffic light state together with the
ROI frame for frontend display.
"""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Callable, Optional

import cv2
import numpy as np
from ultralytics import YOLO

from app.config.roi_config import normalized_rect_to_pixels
from app.core.config import settings
from app.utils.model_loader import get_model_info, load_yolo_model

TrafficLightUpdateFn = Callable[[str, "TrafficLightState", Optional[np.ndarray]], None]
FrameProvider = Callable[[], Optional[np.ndarray]]


@dataclass
class TrafficLightState:
    camera_id: str
    state: str  # GREEN | RED | YELLOW
    confidence: Optional[float]
    timestamp: datetime


class TrafficLightWorker:
    """Background worker that polls frames and detects traffic light state."""

    def __init__(
        self,
        camera_id: str,
        roi_norm: dict,
        frame_provider: FrameProvider,
        update_callback: TrafficLightUpdateFn,
        interval_s: float = 0.75,
    ) -> None:
        self.camera_id = camera_id
        self.roi_norm = roi_norm
        self.frame_provider = frame_provider
        self.update_callback = update_callback
        self.interval_s = max(interval_s, 0.1)
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._model = self._load_model()
        self._stable_state: Optional[str] = None
        self._candidate_state: Optional[str] = None
        self._candidate_since: Optional[float] = None

    def _load_model(self) -> Optional[YOLO]:
        info = get_model_info(settings.YOLO_TRAFFIC_LIGHT_MODEL)
        if not info["found"]:
            return None
        return load_yolo_model(
            info["path"],
            device=settings.DEVICE,
            imgsz=320,
            half=True,
            verbose=False,
        )

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=2.0)

    def _run(self) -> None:
        while not self._stop_event.is_set():
            frame = self.frame_provider()
            if frame is None:
                time.sleep(self.interval_s)
                continue

            state, confidence, crop = self._detect_state(frame)
            stable_state = self._apply_smoothing(state)
            if stable_state:
                tl_state = TrafficLightState(
                    camera_id=self.camera_id,
                    state=stable_state,
                    confidence=confidence if stable_state == state else None,
                    timestamp=datetime.utcnow(),
                )
                self.update_callback(self.camera_id, tl_state, crop)

            time.sleep(self.interval_s)

    def _apply_smoothing(self, new_state: str) -> Optional[str]:
        now = time.time()
        if self._stable_state is None:
            self._stable_state = new_state
            return new_state

        if new_state == self._stable_state:
            self._candidate_state = None
            self._candidate_since = None
            return new_state

        if self._candidate_state != new_state:
            self._candidate_state = new_state
            self._candidate_since = now
            return None

        if self._candidate_since and (now - self._candidate_since) >= 0.75:
            self._stable_state = new_state
            return new_state

        return None

    def _detect_state(self, frame: np.ndarray) -> tuple[str, Optional[float], Optional[np.ndarray]]:
        import logging
        logger = logging.getLogger(__name__)
        
        try:
            frame_height, frame_width = frame.shape[:2]
            
            # Convert normalized ROI to pixel coordinates
            x1, y1, x2, y2 = normalized_rect_to_pixels(self.roi_norm, frame.shape[:2])
            
            # Clamp to frame bounds
            x1 = max(0, min(x1, frame_width - 1))
            y1 = max(0, min(y1, frame_height - 1))
            x2 = max(x1 + 1, min(x2, frame_width))
            y2 = max(y1 + 1, min(y2, frame_height))
            
            logger.debug("🎯 ROI crop: (%d,%d) -> (%d,%d) from frame %dx%d", 
                        x1, y1, x2, y2, frame_width, frame_height)
            
            crop = frame[y1:y2, x1:x2]
            
            if crop is None or crop.size == 0:
                logger.warning("⚠️ Empty ROI crop for camera %s: (%d,%d,%d,%d)", 
                              self.camera_id, x1, y1, x2, y2)
                return "UNKNOWN", None, None

            # Make a copy to ensure the crop is contiguous
            crop = crop.copy()
            
            logger.debug("✅ ROI crop successful: %dx%d", crop.shape[1], crop.shape[0])

            if self._model is None:
                logger.warning("⚠️ No model loaded, returning UNKNOWN with crop")
                return "UNKNOWN", None, crop

            results = self._model.predict(crop, conf=0.25, imgsz=320, half=True, verbose=False)
            if not results or not results[0].boxes:
                return "UNKNOWN", None, crop

            boxes = results[0].boxes
            conf = float(boxes.conf.max().item()) if boxes.conf.numel() else None
            cls_id = int(boxes.cls[boxes.conf.argmax()].item()) if boxes.conf.numel() else -1

            if cls_id == 0:
                return "GREEN", conf, crop
            if cls_id == 1:
                return "RED", conf, crop
            return "YELLOW", conf, crop
            
        except Exception as e:
            logger.error("❌ Error in _detect_state: %s", e, exc_info=True)
            return "UNKNOWN", None, None
