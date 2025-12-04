"""
Traffic Detection Engines Package
Modular pipeline: Detection → Tracking → State Management → ROI → Violation Detection
"""

from .detection_engine import DetectionEngine
from .tracking_engine import TrackingEngine
from .object_state_manager import ObjectStateManager, ObjectState
from .roi_manager import ROIManager, ROI, ROIType
from .violation_engine import ViolationEngine, ViolationType, ViolationResult

__all__ = [
    "DetectionEngine",
    "TrackingEngine", 
    "ObjectStateManager",
    "ObjectState",
    "ROIManager",
    "ROI",
    "ROIType",
    "ViolationEngine",
    "ViolationType", 
    "ViolationResult"
]