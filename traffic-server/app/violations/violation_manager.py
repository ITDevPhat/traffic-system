"""
Violation Manager - Manages violation engines per camera
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Dict, List, Optional, Any

from app.violations.red_light_engine import RedLightViolationEngine, ViolationRecord

logger = logging.getLogger(__name__)


class ViolationManager:
    """
    Manages violation detection engines for multiple cameras.

    Each camera has its own RedLightViolationEngine instance.
    """

    def __init__(self):
        self.engines: Dict[str, RedLightViolationEngine] = {}
        self.stoplines: Dict[str, Dict[str, float]] = {}
        self.violation_regions: Dict[str, List[tuple[float, float]]] = {}
        logger.info("ViolationManager initialized")

    def set_stopline(self, camera_id: str, stopline: Dict[str, float]) -> None:
        """
        Set or update stopline for a camera.

        Args:
            camera_id: Camera identifier
            stopline: Stopline coordinates {x1, y1, x2, y2}
        """
        self.stoplines[camera_id] = stopline

        if camera_id in self.engines:
            self.engines[camera_id].reset_stopline(stopline)
            logger.info(f"✅ Updated stopline for camera {camera_id}")
        else:
            self.engines[camera_id] = RedLightViolationEngine(
                camera_id,
                stopline,
                self.violation_regions.get(camera_id),
            )
            logger.info(f"✅ Created violation engine for camera {camera_id}")

        if camera_id in self.violation_regions and camera_id in self.engines:
            self.engines[camera_id].reset_violation_region(
                self.violation_regions[camera_id]
            )

    def get_stopline(self, camera_id: str) -> Optional[Dict[str, float]]:
        """Get stopline for a camera"""
        return self.stoplines.get(camera_id)

    def set_violation_region(
        self, camera_id: str, violation_region: Optional[List[tuple[float, float]]]
    ) -> None:
        self.violation_regions[camera_id] = violation_region or []

        if camera_id in self.engines:
            self.engines[camera_id].reset_violation_region(
                self.violation_regions[camera_id]
            )
            logger.info(f"✅ Updated violation region for camera {camera_id}")
        elif camera_id in self.stoplines:
            # Create engine if stopline already present
            self.engines[camera_id] = RedLightViolationEngine(
                camera_id,
                self.stoplines[camera_id],
                self.violation_regions[camera_id],
            )
            logger.info(f"✅ Created engine with violation region for {camera_id}")

    def compute_violations(
        self,
        camera_id: str,
        tracks: List[Dict[str, Any]],
        light_state: Optional[str],
        timestamp: Optional[datetime] = None,
        frame_index: Optional[int] = None,
    ) -> List[ViolationRecord]:
        """
        Compute violations for current frame.

        Args:
            camera_id: Camera identifier
            tracks: List of tracked objects with bbox
            light_state: Current traffic light state (RED/GREEN/YELLOW)
            timestamp: Frame timestamp

        Returns:
            List of ViolationRecord objects
        """
        if timestamp is None:
            timestamp = datetime.utcnow()

        engine = self.engines.get(camera_id)
        if engine is None:
            logger.warning(f"[VIOLATION] No stopline/engine for camera {camera_id}")
            return []

        if not tracks:
            logger.debug(f"[VIOLATION] No tracks for camera {camera_id} at {timestamp.isoformat()}")
            return []

        effective_light = light_state if light_state in {"RED", "YELLOW", "GREEN"} else "GREEN"

        logger.info(
            f"[VIOLATION] Computing for camera={camera_id}, tracks={len(tracks)}, light={effective_light}"
        )

        violations = engine.update(tracks, effective_light, timestamp, frame_index=frame_index)
        if violations:
            logger.info(f"🚨 {len(violations)} violations detected for camera {camera_id}")
        return violations

    def remove_camera(self, camera_id: str) -> None:
        """Remove engine and stopline for a camera"""
        self.engines.pop(camera_id, None)
        self.stoplines.pop(camera_id, None)
        self.violation_regions.pop(camera_id, None)
        logger.info(f"🗑️ Removed violation engine for camera {camera_id}")

    def clear(self, camera_id: str) -> None:
        """Alias for remove_camera to clear state"""
        self.remove_camera(camera_id)


# Global violation manager instance
violation_manager = ViolationManager()
