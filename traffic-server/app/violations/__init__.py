"""
Violation Detection Engine
Phát hiện vi phạm giao thông dựa trên ROI và tracking data
"""

from .engine import ViolationEngine, create_default_violation_engine
from .models import VehicleState, ViolationEvent, ViolationContext, BBox
from .rules import (
    # New Rule Engine functions
    red_light_rule,
    solid_line_rule,
    forbidden_area_rule,
    # Legacy functions (kept for backward compatibility)
    check_lane_violation,
    check_wrong_direction,
    check_forbidden_area,
    check_stopline,
    check_solid_line,
    check_red_light,
)

__all__ = [
    # New Rule Engine
    "ViolationEngine",
    "create_default_violation_engine",
    "VehicleState",
    "ViolationEvent", 
    "ViolationContext",
    "BBox",
    "red_light_rule",
    "solid_line_rule",
    "forbidden_area_rule",
    # Legacy (backward compatibility)
    "check_lane_violation",
    "check_wrong_direction",
    "check_forbidden_area",
    "check_stopline",
    "check_solid_line",
    "check_red_light",
]
