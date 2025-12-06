"""
Traffic Light Worker - Frame Consumer Mode

Refactored worker that:
1. Consumes frames from shared buffer (no own video capture)
2. Runs YOLO Traffic Light detection on ROI crop
3. Calls Red Light Violation Engine with ByteTrack tracks from main pipeline
4. Synchronizes with main pipeline PAUSE/RESUME/STOP states
5. Pushes {state, roi_frame, violations} through WebSocket
"""
from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

import cv2
import numpy as np
from ultralytics import YOLO

from app.config.roi_config import normalized_rect_to_pixels, normalized_stopline_to_pixels
from app.core.config import settings
from app.utils.model_loader import get_model_info, load_yolo_model

logger = logging.getLogger(__name__)


@dataclass
class TrafficLightState:
    """Traffic light state with violation data"""
    camera_id: str
    state: str  # GREEN | RED | YELLOW | UNKNOWN
    confidence: Optional[float]
    timestamp: datetime
    frame_index: int = 0
    violations: List[Dict[str, Any]] = field(default_factory=list)
    roi_frame: Optional[np.ndarray] = None


class RedLightViolationEngine:
    """
    Penetration-based red light violation detection.
    
    Violation occurs when:
    - Traffic light is RED
    - Vehicle crosses stopline
    - penetration_ratio = depth / bbox_width >= threshold
    - depth = bbox_bottom_y - stopline_y
    """
    
    def __init__(self, stopline_y: int, threshold: float = 0.5):
        self.stopline_y = stopline_y
        self.threshold = threshold
        self.violated_tracks: Dict[int, Dict[str, Any]] = {}  # track_id -> violation data
        self.current_light_state = "GREEN"
        self.red_cycle_start: Optional[float] = None
        logger.info(f"🚨 RedLightViolationEngine initialized: stopline_y={stopline_y}, threshold={threshold}")
    
    def update(self, tracks: List[Dict[str, Any]], light_state: str, timestamp: float) -> List[Dict[str, Any]]:
        """
        Update violation engine with new tracks and light state.
        
        Args:
            tracks: List of track dicts with {track_id, bbox, class_id, confidence}
            light_state: Current traffic light state (RED/GREEN/YELLOW)
            timestamp: Current timestamp
            
        Returns:
            List of new violations detected in this frame
        """
        new_violations = []
        
        # Track light state changes
        if light_state != self.current_light_state:
            logger.info(f"🚦 Light state changed: {self.current_light_state} → {light_state}")
            self.current_light_state = light_state
            
            if light_state == "RED":
                self.red_cycle_start = timestamp
                # Clear violated tracks on new red cycle
                self.violated_tracks.clear()
            elif light_state in ("GREEN", "YELLOW"):
                self.red_cycle_start = None
        
        # Only check violations during RED light
        if light_state != "RED":
            return new_violations
        
        # Check each track for violations
        for track in tracks:
            track_id = track.get("track_id")
            bbox = track.get("bbox")  # [x1, y1, x2, y2]
            
            if track_id is None or bbox is None or len(bbox) < 4:
                continue
            
            # Skip if already violated in this red cycle
            if track_id in self.violated_tracks:
                continue
            
            x1, y1, x2, y2 = bbox
            bbox_bottom_y = y2
            bbox_width = x2 - x1
            
            # Calculate penetration
            depth = bbox_bottom_y - self.stopline_y
            
            # Only consider vehicles that have crossed the line
            if depth <= 0:
                continue
            
            penetration_ratio = depth / bbox_width if bbox_width > 0 else 0
            
            # Check if violation threshold exceeded
            if penetration_ratio >= self.threshold:
                violation = {
                    "track_id": track_id,
                    "violation_type": "red_light",
                    "timestamp": timestamp,
                    "bbox": bbox,
                    "penetration_ratio": float(penetration_ratio),
                    "depth": float(depth),
                    "stopline_y": self.stopline_y,
                    "class_id": track.get("class_id", 0),
                    "class_name": track.get("class_name", "vehicle"),
                    "confidence": track.get("confidence", 1.0),
                }
                
                self.violated_tracks[track_id] = violation
                new_violations.append(violation)
                
                logger.warning(
                    f"🚨 RED LIGHT VIOLATION: track_id={track_id}, "
                    f"penetration={penetration_ratio:.2f}, depth={depth:.1f}px"
                )
        
        return new_violations


class TrafficLightWorker:
    """
    Traffic Light Worker - Frame Consumer Mode
    
    Consumes frames + tracks from main pipeline's shared buffer.
    Runs YOLO-TL detection on ROI crop.
    Detects red-light violations using penetration-based engine.
    """

    def __init__(
        self,
        camera_id: str,
        tl_roi: Optional[Dict[str, float]] = None,
        stopline_roi: Optional[Dict[str, float]] = None,
        interval_s: float = 0.5,
        violation_threshold: float = 0.5,
    ) -> None:
        """
        Initialize Traffic Light Worker.
        
        Args:
            camera_id: Camera identifier
            tl_roi: Traffic light ROI (normalized coordinates)
            stopline_roi: Stopline ROI (normalized coordinates)
            interval_s: Detection interval in seconds
            violation_threshold: Penetration ratio threshold for violations
        """
        self.camera_id = camera_id
        self.tl_roi = tl_roi
        self.stopline_roi = stopline_roi
        self.interval_s = max(interval_s, 0.1)
        self.violation_threshold = violation_threshold
        
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._pause_event = threading.Event()
        
        self._model = self._load_model()
        self._violation_engine: Optional[RedLightViolationEngine] = None
        
        # State smoothing
        self._stable_state: Optional[str] = None
        self._candidate_state: Optional[str] = None
        self._candidate_since: Optional[float] = None
        
        # Latest state for WebSocket streaming
        self._latest_state: Optional[TrafficLightState] = None
        self._state_lock = threading.Lock()
        
        logger.info(f"🚦 TrafficLightWorker created for camera: {camera_id}")
        logger.info(f"   TL ROI: {tl_roi}")
        logger.info(f"   Stopline: {stopline_roi}")
        logger.info(f"   Interval: {interval_s}s, Violation threshold: {violation_threshold}")

    def _load_model(self) -> Optional[YOLO]:
        """Load YOLO traffic light model"""
        info = get_model_info(settings.YOLO_TRAFFIC_LIGHT_MODEL)
        if not info["found"]:
            logger.warning(f"⚠️ Traffic light model not found: {settings.YOLO_TRAFFIC_LIGHT_MODEL}")
            return None
        
        logger.info(f"📦 Loading TL model: {info['path']} ({info.get('size_mb', 0):.1f}MB)")
        return load_yolo_model(
            info["path"],
            device=settings.DEVICE,
            imgsz=320,
            half=True,
            verbose=False,
        )

    def start(self) -> None:
        """Start worker thread"""
        if self._thread and self._thread.is_alive():
            logger.warning(f"⚠️ Worker already running for camera: {self.camera_id}")
            return
        
        self._stop_event.clear()
        self._pause_event.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        logger.info(f"▶️ Worker started for camera: {self.camera_id}")

    def stop(self) -> None:
        """Stop worker thread"""
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=2.0)
        logger.info(f"⏹️ Worker stopped for camera: {self.camera_id}")
    
    def pause(self) -> None:
        """Pause worker (stop processing but keep thread alive)"""
        self._pause_event.set()
        logger.info(f"⏸️ Worker paused for camera: {self.camera_id}")
    
    def resume(self) -> None:
        """Resume worker from pause"""
        self._pause_event.clear()
        logger.info(f"▶️ Worker resumed for camera: {self.camera_id}")

    def _run(self) -> None:
        """Main worker loop - consumes frames from shared buffer"""
        from app.services.traffic_light_manager import frame_buffer
        
        logger.info(f"🎬 Worker thread running for camera: {self.camera_id}")
        
        # Initialize violation engine if stopline is configured
        if self.stopline_roi:
            # Get frame dimensions from buffer
            frame_width, frame_height = frame_buffer.get_frame_dimensions(self.camera_id)
            if frame_width > 0 and frame_height > 0:
                # Convert stopline to pixels
                _, stopline_y, _, _ = normalized_stopline_to_pixels(
                    self.stopline_roi, (frame_height, frame_width)
                )
                self._violation_engine = RedLightViolationEngine(
                    stopline_y=stopline_y,
                    threshold=self.violation_threshold
                )
                logger.info(f"✅ Violation engine initialized with stopline_y={stopline_y}")
        
        while not self._stop_event.is_set():
            # Check if paused
            if self._pause_event.is_set():
                time.sleep(0.1)
                continue
            
            # Check if main pipeline is running
            if not frame_buffer.is_running(self.camera_id):
                time.sleep(0.1)
                continue
            
            # Get frame + tracks from shared buffer
            frame, tracks, frame_index = frame_buffer.get_frame(
                self.camera_id, timeout=0.5
            )
            
            if frame is None:
                continue
            
            # Detect traffic light state
            state, confidence, crop = self._detect_state(frame)
            stable_state = self._apply_smoothing(state)
            
            if stable_state is None:
                continue
            
            # Detect violations if engine is initialized
            violations = []
            if self._violation_engine and tracks:
                violations = self._violation_engine.update(
                    tracks=tracks,
                    light_state=stable_state,
                    timestamp=time.time()
                )
            
            # Create state object
            tl_state = TrafficLightState(
                camera_id=self.camera_id,
                state=stable_state,
                confidence=confidence if stable_state == state else None,
                timestamp=datetime.utcnow(),
                frame_index=frame_index,
                violations=violations,
                roi_frame=crop,
            )
            
            # Store latest state for WebSocket streaming
            with self._state_lock:
                self._latest_state = tl_state
            
            time.sleep(self.interval_s)
        
        logger.info(f"🛑 Worker thread stopped for camera: {self.camera_id}")
    
    def get_latest_state(self) -> Optional[TrafficLightState]:
        """Get latest traffic light state (thread-safe)"""
        with self._state_lock:
            return self._latest_state

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
        """
        Detect traffic light state from frame.
        
        Returns:
            (state, confidence, roi_crop)
        """
        try:
            # If no ROI configured, return YELLOW (default safe state)
            if not self.tl_roi:
                logger.warning(f"⚠️ No TL ROI configured for camera {self.camera_id}")
                return "YELLOW", 0.0, None
            
            frame_height, frame_width = frame.shape[:2]
            
            # Convert normalized ROI to pixel coordinates
            x1, y1, x2, y2 = normalized_rect_to_pixels(self.tl_roi, frame.shape[:2])
            
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
                return "YELLOW", 0.0, None

            # Make a copy to ensure the crop is contiguous
            crop = crop.copy()
            
            logger.debug("✅ ROI crop successful: %dx%d", crop.shape[1], crop.shape[0])

            # If no model loaded, return YELLOW (safe default)
            if self._model is None:
                logger.warning("⚠️ No model loaded, returning YELLOW with crop")
                return "YELLOW", 0.0, crop

            # Run YOLO-TL detection on crop
            results = self._model.predict(crop, conf=0.25, imgsz=320, half=True, verbose=False)
            
            # If no detection, return YELLOW (per spec)
            if not results or not results[0].boxes or len(results[0].boxes) == 0:
                logger.debug("🟡 No TL detection, returning YELLOW")
                return "YELLOW", 0.0, crop

            boxes = results[0].boxes
            conf = float(boxes.conf.max().item()) if boxes.conf.numel() else 0.0
            cls_id = int(boxes.cls[boxes.conf.argmax()].item()) if boxes.conf.numel() else -1

            # Map class ID to state (model specific - adjust if needed)
            # Assuming: 0=GREEN, 1=RED, others=YELLOW
            if cls_id == 0:
                return "GREEN", conf, crop
            elif cls_id == 1:
                return "RED", conf, crop
            else:
                return "YELLOW", conf, crop
            
        except Exception as e:
            logger.error("❌ Error in _detect_state: %s", e, exc_info=True)
            return "YELLOW", 0.0, None
