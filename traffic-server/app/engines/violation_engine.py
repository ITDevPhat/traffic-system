"""
Violation Engine - Comprehensive traffic violation detection
Sử dụng ObjectStateManager + ROIManager để phát hiện vi phạm temporal và spatial
"""
import logging
import time
from typing import Dict, List, Optional, Tuple, Set
from enum import Enum
from dataclasses import dataclass

from .object_state_manager import ObjectStateManager, ObjectState
from .roi_manager import ROIManager, ROI, ROIType
from ..core.violation_config import ENABLE_VIOLATIONS, VIOLATION_SETTINGS, get_violation_status

logger = logging.getLogger(__name__)

class ViolationType(Enum):
    """Standardized violation types"""
    RED_LIGHT = "red_light"
    STOPLINE_CROSSING = "stopline_crossing"
    SOLID_LINE_CROSSING = "solid_line_crossing"
    WRONG_LANE = "wrong_lane"
    WRONG_DIRECTION = "wrong_direction"
    NO_ENTRY_ZONE = "no_entry_zone"
    SPEEDING = "speeding"
    NO_HELMET = "no_helmet"
    CUSTOM = "custom"

@dataclass
class ViolationResult:
    """Result of violation detection for an object"""
    track_id: int
    is_violation: bool
    violation_type: Optional[ViolationType] = None
    violation_details: Optional[str] = None
    confidence: float = 1.0
    timestamp: float = 0.0
    roi_id: Optional[str] = None

class ViolationEngine:
    """
    Comprehensive violation detection engine
    Combines temporal (ObjectStateManager) and spatial (ROIManager) analysis
    """
    
    def __init__(
        self,
        object_state_manager: ObjectStateManager,
        roi_manager: ROIManager,
        speed_limit_kmh: float = 50.0,
        enable_demo_violations: bool = False,
        enable_violations: bool = None  # Use config if None
    ):
        """
        Initialize Violation Engine
        
        Args:
            object_state_manager: Manager for object states
            roi_manager: Manager for ROI definitions
            speed_limit_kmh: Speed limit for speeding violations
            enable_demo_violations: Enable demo violations for testing
            enable_violations: Master switch to enable/disable all violations
        """
        self.state_manager = object_state_manager
        self.roi_manager = roi_manager
        self.speed_limit_kmh = speed_limit_kmh
        self.enable_demo_violations = enable_demo_violations
        
        # Use config value if not explicitly set
        if enable_violations is None:
            self.enable_violations = ENABLE_VIOLATIONS
        else:
            self.enable_violations = enable_violations
        
        # Violation tracking
        self.violation_history: Dict[int, List[ViolationResult]] = {}
        self.total_violations_detected = 0
        
        # Performance metrics
        self.evaluation_times = []
        
        logger.info("🚨 ViolationEngine initialized")
        logger.info(f"⚙️  Config: violations={self.enable_violations}, speed_limit={speed_limit_kmh}km/h, demo={enable_demo_violations}")
        
        if not self.enable_violations:
            logger.info("⚠️  VIOLATIONS DISABLED - No violation detection will occur")
            status = get_violation_status()
            logger.info(f"📋 Status: {status['message']}")
    
    def evaluate_violations(self, tracked_objects: List[Dict]) -> Dict[int, ViolationResult]:
        """
        Evaluate violations for all tracked objects
        
        Args:
            tracked_objects: List of tracked objects from TrackingEngine
            
        Returns:
            Dict mapping track_id to ViolationResult
        """
        start_time = time.time()
        
        # MASTER SWITCH: If violations disabled, return no violations
        if not self.enable_violations:
            violation_results = {}
            for obj in tracked_objects:
                track_id = obj["track_id"]
                violation_results[track_id] = ViolationResult(
                    track_id=track_id,
                    is_violation=False,
                    timestamp=time.time()
                )
            
            evaluation_time = time.time() - start_time
            self.evaluation_times.append(evaluation_time)
            return violation_results
        
        # Update object states first
        object_states = self.state_manager.update(tracked_objects)
        
        violation_results = {}
        
        for obj in tracked_objects:
            track_id = obj["track_id"]
            state = object_states.get(track_id)
            
            if not state:
                continue
            
            # Evaluate all violation types for this object
            violation_result = self._evaluate_object_violations(obj, state)
            violation_results[track_id] = violation_result
            
            # Store in history if violation detected
            if violation_result.is_violation:
                if track_id not in self.violation_history:
                    self.violation_history[track_id] = []
                self.violation_history[track_id].append(violation_result)
                self.total_violations_detected += 1
        
        evaluation_time = time.time() - start_time
        self.evaluation_times.append(evaluation_time)
        
        # Keep only last 100 evaluation times
        if len(self.evaluation_times) > 100:
            self.evaluation_times = self.evaluation_times[-100:]
        
        return violation_results
    
    def _evaluate_object_violations(self, obj: Dict, state: ObjectState) -> ViolationResult:
        """
        Evaluate all possible violations for a single object
        
        Args:
            obj: Tracked object data
            state: Object state with history
            
        Returns:
            ViolationResult for this object
        """
        track_id = obj["track_id"]
        bbox = obj["bbox"]
        class_name = obj["class_name"]
        
        # Check each violation type in priority order
        
        # 1. Demo violations (for testing)
        if self.enable_demo_violations:
            demo_result = self._check_demo_violations(track_id, class_name)
            if demo_result.is_violation:
                return demo_result
        
        # 2. ROI-based violations
        roi_result = self._check_roi_violations(bbox, state)
        if roi_result.is_violation:
            return roi_result
        
        # 3. Speed violations
        speed_result = self._check_speed_violations(state)
        if speed_result.is_violation:
            return speed_result
        
        # 4. Direction violations
        direction_result = self._check_direction_violations(state)
        if direction_result.is_violation:
            return direction_result
        
        # No violations detected
        return ViolationResult(
            track_id=track_id,
            is_violation=False,
            timestamp=time.time()
        )
    
    def _check_demo_violations(self, track_id: int, class_name: str) -> ViolationResult:
        """
        Demo violations for testing UI - DISABLED
        
        Args:
            track_id: Track ID
            class_name: Object class name
            
        Returns:
            ViolationResult (always no violation)
        """
        # DISABLED: No demo violations - waiting for real traffic rules
        return ViolationResult(track_id=track_id, is_violation=False, timestamp=time.time())
    
    def _check_roi_violations(self, bbox: List[float], state: ObjectState) -> ViolationResult:
        """
        Check ROI-based violations (stoplines, zones, etc.)
        
        Args:
            bbox: Object bounding box
            state: Object state with history
            
        Returns:
            ViolationResult
        """
        track_id = state.track_id
        
        # Check stopline crossings
        stoplines = self.roi_manager.get_rois_by_type(ROIType.STOPLINE)
        for roi in stoplines:
            if self.roi_manager.check_line_crossing(bbox, roi):
                # Check if this is a new crossing (not already flagged)
                if not self.state_manager.has_violation(track_id, "stopline"):
                    self.state_manager.set_violation_flag(track_id, "stopline", True)
                    
                    return ViolationResult(
                        track_id=track_id,
                        is_violation=True,
                        violation_type=ViolationType.STOPLINE_CROSSING,
                        violation_details=f"Crossed stopline: {roi.name}",
                        confidence=0.95,
                        timestamp=time.time(),
                        roi_id=roi.id
                    )
        
        # Check no-entry zones
        no_entry_zones = self.roi_manager.get_rois_by_type(ROIType.NO_ENTRY_ZONE)
        for roi in no_entry_zones:
            if self.roi_manager.check_zone_intersect(bbox, roi):
                return ViolationResult(
                    track_id=track_id,
                    is_violation=True,
                    violation_type=ViolationType.NO_ENTRY_ZONE,
                    violation_details=f"Entered forbidden zone: {roi.name}",
                    confidence=0.9,
                    timestamp=time.time(),
                    roi_id=roi.id
                )
        
        # Check solid line crossings
        solid_lines = self.roi_manager.get_rois_by_type(ROIType.SOLID_LINE)
        for roi in solid_lines:
            if self.roi_manager.check_line_crossing(bbox, roi):
                return ViolationResult(
                    track_id=track_id,
                    is_violation=True,
                    violation_type=ViolationType.SOLID_LINE_CROSSING,
                    violation_details=f"Crossed solid line: {roi.name}",
                    confidence=0.85,
                    timestamp=time.time(),
                    roi_id=roi.id
                )
        
        return ViolationResult(track_id=track_id, is_violation=False, timestamp=time.time())
    
    def _check_speed_violations(self, state: ObjectState) -> ViolationResult:
        """
        Check speed-based violations
        
        Args:
            state: Object state with speed information
            
        Returns:
            ViolationResult
        """
        if state.speed_kmh > self.speed_limit_kmh:
            excess_speed = state.speed_kmh - self.speed_limit_kmh
            
            return ViolationResult(
                track_id=state.track_id,
                is_violation=True,
                violation_type=ViolationType.SPEEDING,
                violation_details=f"Speed: {state.speed_kmh:.1f} km/h (limit: {self.speed_limit_kmh} km/h, excess: +{excess_speed:.1f})",
                confidence=0.8,
                timestamp=time.time()
            )
        
        return ViolationResult(track_id=state.track_id, is_violation=False, timestamp=time.time())
    
    def _check_direction_violations(self, state: ObjectState) -> ViolationResult:
        """
        Check direction-based violations
        
        Args:
            state: Object state with direction information
            
        Returns:
            ViolationResult
        """
        # Check wrong direction in direction zones
        direction_zones = self.roi_manager.get_rois_by_type(ROIType.WRONG_DIRECTION)
        
        for roi in direction_zones:
            # Check if object is in this zone
            if self.roi_manager.check_zone_intersect(list(state.last_bbox), roi):
                # Check direction violation
                if self.roi_manager.check_direction_violation(state.direction_deg, roi):
                    return ViolationResult(
                        track_id=state.track_id,
                        is_violation=True,
                        violation_type=ViolationType.WRONG_DIRECTION,
                        violation_details=f"Wrong direction: {state.direction_deg:.0f}° in zone {roi.name}",
                        confidence=0.85,
                        timestamp=time.time(),
                        roi_id=roi.id
                    )
        
        return ViolationResult(track_id=state.track_id, is_violation=False, timestamp=time.time())
    
    def get_violation_summary(self, track_id: int) -> Dict:
        """
        Get violation summary for a specific track
        
        Args:
            track_id: Track ID
            
        Returns:
            Dict with violation summary
        """
        if track_id not in self.violation_history:
            return {"track_id": track_id, "violations": [], "total_violations": 0}
        
        violations = self.violation_history[track_id]
        
        return {
            "track_id": track_id,
            "violations": [
                {
                    "type": v.violation_type.value if v.violation_type else "unknown",
                    "details": v.violation_details,
                    "confidence": v.confidence,
                    "timestamp": v.timestamp,
                    "roi_id": v.roi_id
                }
                for v in violations
            ],
            "total_violations": len(violations)
        }
    
    def get_stats(self) -> Dict:
        """
        Get violation engine statistics
        
        Returns:
            Dict with statistics
        """
        # Count violations by type
        violation_type_counts = {}
        for violations in self.violation_history.values():
            for violation in violations:
                if violation.violation_type:
                    vtype = violation.violation_type.value
                    violation_type_counts[vtype] = violation_type_counts.get(vtype, 0) + 1
        
        # Calculate average evaluation time
        avg_eval_time = 0.0
        if self.evaluation_times:
            avg_eval_time = sum(self.evaluation_times) / len(self.evaluation_times)
        
        return {
            "total_violations_detected": self.total_violations_detected,
            "unique_violating_objects": len(self.violation_history),
            "violation_type_counts": violation_type_counts,
            "avg_evaluation_time": avg_eval_time,
            "config": {
                "enable_violations": self.enable_violations,
                "speed_limit_kmh": self.speed_limit_kmh,
                "enable_demo_violations": self.enable_demo_violations
            },
            "state_manager_stats": self.state_manager.get_stats(),
            "roi_manager_stats": self.roi_manager.get_stats()
        }
    
    def reset_stats(self):
        """Reset all statistics"""
        self.violation_history.clear()
        self.total_violations_detected = 0
        self.evaluation_times = []
        self.state_manager.reset_stats()
        self.roi_manager.reset_stats()
        logger.info("📊 Violation engine stats reset")