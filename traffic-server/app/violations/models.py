"""
Data models for the Rule Engine
VehicleObject & ViolationEvent models for stateful violation detection
"""

from dataclasses import dataclass, field
from collections import deque
from typing import Deque, Dict, List, Optional, Set, Tuple
import time

Point = Tuple[float, float]  # normalized (0-1) or pixel coordinates

@dataclass
class BBox:
    """Bounding box representation"""
    x1: float
    y1: float
    x2: float
    y2: float

    @property
    def center(self) -> Tuple[float, float]:
        return ((self.x1 + self.x2) / 2.0, (self.y1 + self.y2) / 2.0)

    @property
    def width(self) -> float:
        return max(0.0, self.x2 - self.x1)

    @property
    def height(self) -> float:
        return max(0.0, self.y2 - self.y1)

@dataclass
class ViolationEvent:
    """Represents a detected violation"""
    track_id: int
    violation_type: str          # e.g. "red_light", "solid_line", "wrong_lane"
    frame_idx: int
    timestamp: float
    details: Dict[str, object] = field(default_factory=dict)

@dataclass
class VehicleState:
    """Stateful representation of a tracked vehicle"""
    track_id: int
    cls: str
    bbox: BBox
    speed: float = 0.0           # pixel/s or m/s if calibrated
    direction: float = 0.0       # angle in degrees (0-360), optional
    last_updated_frame: int = 0
    last_updated_ts: float = field(default_factory=time.time)

    # History for behavior analysis
    history: Deque[Tuple[int, BBox]] = field(default_factory=lambda: deque(maxlen=30))

    # ROI interactions
    entered_rois: Set[str] = field(default_factory=set)        # ROI names entered
    current_rois: Set[str] = field(default_factory=set)        # ROI names currently in
    crossed_lines: Set[str] = field(default_factory=set)       # stopline/solid_line ids crossed

    # Current violation, if any
    violation: Optional[ViolationEvent] = None

@dataclass
class ViolationContext:
    """Global context for rule evaluation"""
    frame_idx: int
    timestamp: float
    traffic_lights: Dict[str, str]  # e.g. {"Đèn 1": "RED"}
    rois: Dict[str, Dict]           # ROI definition (type, geometry, metadata)