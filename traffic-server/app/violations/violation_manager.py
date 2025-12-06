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
        logger.info("ViolationManager initialized")
    
    def set_stopline(self, camera_id: str, stopline: Dict[str, float]) -> None:
        """
        Set or update stopline for a camera.
        
        Args:
            camera_id: Camera identifier
            stopline: Stopline coordinates {x1, y1, x2, y2}
        """
        self.stoplines[camera_id] = stopline
        
        # Update or create engine
        if camera_id in self.engines:
            self.engines[camera_id].reset_stopline(stopline)
            logger.info(f"✅ Updated stopline for camera {camera_id}")
        else:
            self.engines[camera_id] = RedLightViolationEngine(camera_id, stopline)
            logger.info(f"✅ Created violation engine for camera {camera_id}")
    
    def get_stopline(self, camera_id: str) -> Optional[Dict[str, float]]:
        """Get stopline for a camera"""
        return self.stoplines.get(camera_id)
    
    def compute_violations(
        self,
        camera_id: str,
        tracks: List[Dict[str, Any]],
        light_state: Optional[str],
        timestamp: Optional[datetime] = None
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
        
        # Get or create engine
        engine = self.engines.get(camera_id)
        if engine is None:
            # No stopline configured yet
            return []
        
        try:
            violations = engine.update(tracks, light_state, timestamp)
            if violations:
                logger.info(f"🚨 {len(violations)} violations detected for camera {camera_id}")
            return violations
        except Exception as e:
            logger.error(f"❌ Error computing violations for camera {camera_id}: {e}", exc_info=True)
            return []
    
    def remove_camera(self, camera_id: str) -> None:
        """Remove engine and stopline for a camera"""
        self.engines.pop(camera_id, None)
        self.stoplines.pop(camera_id, None)
        logger.info(f"🗑️ Removed violation engine for camera {camera_id}")


# Global violation manager instance
violation_manager = ViolationManager()
