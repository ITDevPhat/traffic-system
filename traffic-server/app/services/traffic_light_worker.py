"""Traffic light worker that consumes frames from the shared buffer.

Responsibilities
----------------
* Crop ROI A (traffic light) using **pixel coordinates**
* Run YOLO-TL on the crop (0=GREEN, 1=RED)
* If no detection -> YELLOW, if ROI invalid -> UNKNOWN
* Detect red-light violations using full temporal logic
* Respect PAUSE/RESUME/STOP flags shared with the main pipeline
"""
from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import cv2
import numpy as np
from ultralytics import YOLO

from app.config.roi_config import normalized_rect_to_pixels, normalized_stopline_to_pixels
from app.core.config import settings
from app.utils.model_loader import get_model_info, load_yolo_model
from app.violations.red_light_engine import RedLightViolationEngine

logger = logging.getLogger(__name__)


@dataclass
class TrafficLightState:
    camera_id: str
    state: str  # GREEN | RED | YELLOW | UNKNOWN
    confidence: Optional[float]
    timestamp: datetime
    frame_index: int = 0
    violations: List[Dict[str, Any]] = field(default_factory=list)
    roi_frame: Optional[np.ndarray] = None


class TrafficLightWorker:
    """Consumes frames and tracks from the shared buffer to detect TL state."""

    def __init__(
        self,
        camera_id: str,
        tl_roi: Optional[Dict[str, float]] = None,
        stopline_roi: Optional[Dict[str, float]] = None,
        interval_s: float = 0.5,
        violation_tolerance: float = 2.0,
    ) -> None:
        self.camera_id = camera_id
        self.tl_roi_raw = tl_roi
        self.stopline_roi_raw = stopline_roi
        self.interval_s = max(interval_s, 0.1)
        self.violation_tolerance = violation_tolerance

        self._tl_roi_px: Optional[Tuple[int, int, int, int]] = None
        self._stopline_px: Optional[Dict[str, float]] = None

        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._pause_event = threading.Event()

        self._model = self._load_model()
        self._violation_engine: Optional[RedLightViolationEngine] = None

        self._stable_state: Optional[str] = None
        self._candidate_state: Optional[str] = None
        self._candidate_since: Optional[float] = None

        self._latest_state: Optional[TrafficLightState] = None
        self._state_lock = threading.Lock()

        logger.info("🚦 TrafficLightWorker created for camera %s", camera_id)

    # ------------------- Lifecycle -------------------
    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            logger.warning("⚠️ Worker already running for camera: %s", self.camera_id)
            return

        self._stop_event.clear()
        self._pause_event.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        logger.info("▶️ Worker started for camera: %s", self.camera_id)

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=2.0)
        logger.info("⏹️ Worker stopped for camera: %s", self.camera_id)

    def pause(self) -> None:
        self._pause_event.set()
        logger.info("⏸️ Worker paused for camera: %s", self.camera_id)

    def resume(self) -> None:
        self._pause_event.clear()
        logger.info("▶️ Worker resumed for camera: %s", self.camera_id)

    # ------------------- Core loop -------------------
    def _run(self) -> None:
        from app.services.traffic_light_manager import frame_buffer

        logger.info("🎬 Worker thread running for camera: %s", self.camera_id)

        while not self._stop_event.is_set():
            if self._pause_event.is_set() or not frame_buffer.is_running(self.camera_id):
                time.sleep(0.1)
                continue

            frame, tracks, frame_index = frame_buffer.get_frame(self.camera_id, timeout=0.5)
            if frame is None:
                continue

            self._resolve_rois(frame)

            state, confidence, crop = self._detect_state(frame)
            stable_state = self._apply_smoothing(state)
            if stable_state is None:
                time.sleep(self.interval_s)
                continue

            violations: List[Dict[str, Any]] = []
            if self._stopline_px and tracks:
                if self._violation_engine is None:
                    self._violation_engine = RedLightViolationEngine(
                        camera_id=self.camera_id,
                        stopline_rect=self._stopline_px,
                        tolerance=self.violation_tolerance,
                    )

                violations = self._violation_engine.update(
                    vehicle_tracks=tracks,
                    light_state=stable_state,
                    timestamp=datetime.utcnow(),
                    stopline_rect=self._stopline_px,
                )

            tl_state = TrafficLightState(
                camera_id=self.camera_id,
                state=stable_state,
                confidence=confidence if stable_state == state else None,
                timestamp=datetime.utcnow(),
                frame_index=frame_index,
                violations=violations,
                roi_frame=crop,
            )

            with self._state_lock:
                self._latest_state = tl_state

            time.sleep(self.interval_s)

        logger.info("🛑 Worker thread stopped for camera: %s", self.camera_id)

    # ------------------- Helpers -------------------
    def _load_model(self) -> Optional[YOLO]:
        info = get_model_info(settings.YOLO_TRAFFIC_LIGHT_MODEL)
        if not info["found"]:
            logger.warning("⚠️ Traffic light model not found: %s", settings.YOLO_TRAFFIC_LIGHT_MODEL)
            return None

        logger.info("📦 Loading TL model: %s", info["path"])
        return load_yolo_model(
            info["path"],
            device=settings.DEVICE,
            imgsz=320,
            half=True,
            verbose=False,
        )

    def _resolve_rois(self, frame: np.ndarray) -> None:
        frame_h, frame_w = frame.shape[:2]

        # Traffic light ROI (pixel only in pipeline)
        if self.tl_roi_raw:
            if {"x1", "y1", "x2", "y2"}.issubset(self.tl_roi_raw):
                x1, y1, x2, y2 = (
                    int(self.tl_roi_raw["x1"]),
                    int(self.tl_roi_raw["y1"]),
                    int(self.tl_roi_raw["x2"]),
                    int(self.tl_roi_raw["y2"]),
                )
            else:
                x1, y1, x2, y2 = normalized_rect_to_pixels(self.tl_roi_raw, (frame_h, frame_w))

            if 0 <= x1 < x2 <= frame_w and 0 <= y1 < y2 <= frame_h:
                self._tl_roi_px = (x1, y1, x2, y2)
            else:
                logger.warning("⚠️ Invalid TL ROI for camera %s (outside frame)", self.camera_id)
                self._tl_roi_px = None

        # Stopline ROI (pixel rect)
        if self.stopline_roi_raw:
            if {"x1", "y1", "x2", "y2"}.issubset(self.stopline_roi_raw):
                x1 = float(self.stopline_roi_raw["x1"])
                y1 = float(self.stopline_roi_raw["y1"])
                x2 = float(self.stopline_roi_raw["x2"])
                y2 = float(self.stopline_roi_raw["y2"])
            else:
                x1, y1, x2, y2 = normalized_stopline_to_pixels(self.stopline_roi_raw, (frame_h, frame_w))

            if 0 <= x1 < x2 <= frame_w and 0 <= y1 < y2 <= frame_h:
                self._stopline_px = {"x1": x1, "y1": y1, "x2": x2, "y2": y2}
            else:
                logger.warning("⚠️ Invalid stopline ROI for camera %s (outside frame)", self.camera_id)
                self._stopline_px = None

    def _detect_state(self, frame: np.ndarray) -> tuple[str, Optional[float], Optional[np.ndarray]]:
        if not self._tl_roi_px:
            return "UNKNOWN", None, None

        x1, y1, x2, y2 = self._tl_roi_px
        crop = frame[y1:y2, x1:x2]
        if crop is None or crop.size == 0:
            return "UNKNOWN", None, None

        if self._model is None:
            return "YELLOW", 0.0, crop

        results = self._model.predict(crop, conf=0.25, imgsz=320, half=True, verbose=False)
        if not results or not results[0].boxes or len(results[0].boxes) == 0:
            return "YELLOW", 0.0, crop

        boxes = results[0].boxes
        confs = boxes.conf.cpu().numpy()
        classes = boxes.cls.cpu().numpy().astype(int)

        best_idx = int(confs.argmax())
        best_conf = float(confs[best_idx]) if confs.size else 0.0
        best_cls = int(classes[best_idx]) if classes.size else -1

        if best_cls == 0:
            return "GREEN", best_conf, crop
        if best_cls == 1:
            return "RED", best_conf, crop
        return "YELLOW", best_conf, crop

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

    def get_latest_state(self) -> Optional[TrafficLightState]:
        with self._state_lock:
            return self._latest_state
