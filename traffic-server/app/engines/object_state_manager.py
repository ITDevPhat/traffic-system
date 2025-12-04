"""
Object State Manager - Stateful tracking for violation detection
Lưu lịch sử di chuyển của mỗi xe theo track_id để phát hiện vi phạm temporal
"""
import time
import logging
from typing import Dict, List, Optional, Tuple, Deque
from collections import deque, defaultdict
from dataclasses import dataclass, field
import numpy as np

logger = logging.getLogger(__name__)

@dataclass
class ObjectState:
    """
    State của một object (vehicle) theo track_id
    Lưu lịch sử để phát hiện vi phạm temporal (crossing lines, speed, etc.)
    """
    track_id: int
    class_name: str
    
    # Current state
    last_bbox: Tuple[float, float, float, float] = (0, 0, 0, 0)
    last_position: Tuple[float, float] = (0, 0)  # Center point (cx, cy)
    last_update_time: float = 0.0
    
    # Movement tracking
    speed_kmh: float = 0.0
    direction_deg: float = 0.0  # 0-360 degrees
    
    # Violation tracking
    crossed_stopline: bool = False
    entered_forbidden_zone: bool = False
    time_enter_zone: Optional[float] = None
    time_exit_zone: Optional[float] = None
    
    # History for temporal analysis (last 30 positions)
    history: Deque[Tuple[float, float, float]] = field(default_factory=lambda: deque(maxlen=30))  # (cx, cy, timestamp)
    bbox_history: Deque[Tuple[float, float, float, float, float]] = field(default_factory=lambda: deque(maxlen=10))  # (x1,y1,x2,y2,timestamp)
    
    # Flags for violation detection
    violation_flags: Dict[str, bool] = field(default_factory=dict)
    violation_timestamps: Dict[str, float] = field(default_factory=dict)

class ObjectStateManager:
    """
    Manager cho tất cả object states
    Cập nhật state theo track_id, cleanup stale objects
    """
    
    def __init__(
        self,
        max_age_seconds: float = 10.0,
        cleanup_interval: float = 5.0,
        pixel_to_meter_ratio: float = 0.05  # Approximate: 1 pixel = 0.05 meters
    ):
        """
        Initialize Object State Manager
        
        Args:
            max_age_seconds: Maximum age before object is considered stale
            cleanup_interval: How often to cleanup stale objects (seconds)
            pixel_to_meter_ratio: Conversion ratio for speed calculation
        """
        self.max_age_seconds = max_age_seconds
        self.cleanup_interval = cleanup_interval
        self.pixel_to_meter_ratio = pixel_to_meter_ratio
        
        # State storage
        self.states: Dict[int, ObjectState] = {}
        self.last_cleanup_time = time.time()
        
        # Statistics
        self.total_objects_tracked = 0
        self.objects_cleaned_up = 0
        
        logger.info(f"🗂️  ObjectStateManager initialized")
        logger.info(f"⚙️  Config: max_age={max_age_seconds}s, cleanup_interval={cleanup_interval}s")
    
    def update(self, tracked_objects: List[Dict]) -> Dict[int, ObjectState]:
        """
        Update states for all tracked objects
        
        Args:
            tracked_objects: List of tracked objects from TrackingEngine
            
        Returns:
            Dict mapping track_id to ObjectState
        """
        current_time = time.time()
        updated_states = {}
        
        for obj in tracked_objects:
            track_id = obj["track_id"]
            bbox = obj["bbox"]
            class_name = obj["class_name"]
            
            # Get or create state
            if track_id not in self.states:
                self.states[track_id] = ObjectState(
                    track_id=track_id,
                    class_name=class_name
                )
                self.total_objects_tracked += 1
                logger.debug(f"🆕 New object tracked: #{track_id} ({class_name})")
            
            state = self.states[track_id]
            
            # Calculate center position
            x1, y1, x2, y2 = bbox
            cx = (x1 + x2) / 2
            cy = (y1 + y2) / 2
            
            # Update movement if we have previous position
            if state.last_update_time > 0:
                self._update_movement(state, cx, cy, current_time)
            
            # Update current state
            state.last_bbox = tuple(bbox)
            state.last_position = (cx, cy)
            state.last_update_time = current_time
            
            # Add to history
            state.history.append((cx, cy, current_time))
            state.bbox_history.append((x1, y1, x2, y2, current_time))
            
            updated_states[track_id] = state
        
        # Periodic cleanup
        if current_time - self.last_cleanup_time > self.cleanup_interval:
            self.cleanup_stale_objects(current_time)
            self.last_cleanup_time = current_time
        
        return updated_states
    
    def _update_movement(self, state: ObjectState, cx: float, cy: float, current_time: float):
        """
        Update movement metrics (speed, direction) for an object
        
        Args:
            state: Object state to update
            cx, cy: Current center position
            current_time: Current timestamp
        """
        last_cx, last_cy = state.last_position
        time_diff = current_time - state.last_update_time
        
        if time_diff <= 0:
            return
        
        # Calculate distance moved (in pixels)
        dx = cx - last_cx
        dy = cy - last_cy
        distance_pixels = np.sqrt(dx**2 + dy**2)
        
        # Convert to speed (km/h)
        distance_meters = distance_pixels * self.pixel_to_meter_ratio
        speed_ms = distance_meters / time_diff
        state.speed_kmh = speed_ms * 3.6  # Convert m/s to km/h
        
        # Calculate direction (0-360 degrees, 0 = North, 90 = East)
        if distance_pixels > 1.0:  # Only update direction if significant movement
            angle_rad = np.arctan2(dx, -dy)  # -dy because y increases downward
            angle_deg = np.degrees(angle_rad)
            if angle_deg < 0:
                angle_deg += 360
            state.direction_deg = angle_deg
    
    def get_state(self, track_id: int) -> Optional[ObjectState]:
        """
        Get state for a specific track_id
        
        Args:
            track_id: Track ID to get state for
            
        Returns:
            ObjectState if exists, None otherwise
        """
        return self.states.get(track_id)
    
    def set_violation_flag(self, track_id: int, violation_type: str, is_violation: bool = True):
        """
        Set violation flag for an object
        
        Args:
            track_id: Track ID
            violation_type: Type of violation (e.g., "stopline", "speed", "zone")
            is_violation: Whether this is a violation or not
        """
        if track_id in self.states:
            state = self.states[track_id]
            state.violation_flags[violation_type] = is_violation
            if is_violation:
                state.violation_timestamps[violation_type] = time.time()
                logger.info(f"🚨 Violation flagged: Track #{track_id} - {violation_type}")
    
    def has_violation(self, track_id: int, violation_type: Optional[str] = None) -> bool:
        """
        Check if object has any violations
        
        Args:
            track_id: Track ID to check
            violation_type: Specific violation type, or None for any violation
            
        Returns:
            True if object has violation(s)
        """
        if track_id not in self.states:
            return False
        
        state = self.states[track_id]
        
        if violation_type:
            return state.violation_flags.get(violation_type, False)
        else:
            return any(state.violation_flags.values())
    
    def get_violations(self, track_id: int) -> Dict[str, bool]:
        """
        Get all violations for an object
        
        Args:
            track_id: Track ID
            
        Returns:
            Dict of violation_type -> bool
        """
        if track_id not in self.states:
            return {}
        
        return self.states[track_id].violation_flags.copy()
    
    def check_line_crossing(self, track_id: int, line_points: List[Tuple[float, float]]) -> bool:
        """
        Check if object has crossed a line (e.g., stopline, solid line)
        
        Args:
            track_id: Track ID to check
            line_points: List of points defining the line [(x1,y1), (x2,y2)]
            
        Returns:
            True if object crossed the line
        """
        if track_id not in self.states or len(line_points) < 2:
            return False
        
        state = self.states[track_id]
        
        # Need at least 2 history points to detect crossing
        if len(state.history) < 2:
            return False
        
        # Get last two positions
        prev_pos = state.history[-2][:2]  # (cx, cy)
        curr_pos = state.history[-1][:2]  # (cx, cy)
        
        # Check if trajectory crosses the line
        return self._line_intersection(prev_pos, curr_pos, line_points[0], line_points[1])
    
    def _line_intersection(self, p1: Tuple[float, float], p2: Tuple[float, float], 
                          p3: Tuple[float, float], p4: Tuple[float, float]) -> bool:
        """
        Check if line segment p1-p2 intersects with line segment p3-p4
        
        Args:
            p1, p2: First line segment (object trajectory)
            p3, p4: Second line segment (ROI line)
            
        Returns:
            True if lines intersect
        """
        x1, y1 = p1
        x2, y2 = p2
        x3, y3 = p3
        x4, y4 = p4
        
        # Calculate the direction of the lines
        denom = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
        
        if abs(denom) < 1e-10:  # Lines are parallel
            return False
        
        # Calculate intersection parameters
        t = ((x1 - x3) * (y3 - y4) - (y1 - y3) * (x3 - x4)) / denom
        u = -((x1 - x2) * (y1 - y3) - (y1 - y2) * (x1 - x3)) / denom
        
        # Check if intersection is within both line segments
        return 0 <= t <= 1 and 0 <= u <= 1
    
    def cleanup_stale_objects(self, current_time: float):
        """
        Remove objects that haven't been updated recently
        
        Args:
            current_time: Current timestamp
        """
        stale_tracks = []
        
        for track_id, state in self.states.items():
            age = current_time - state.last_update_time
            if age > self.max_age_seconds:
                stale_tracks.append(track_id)
        
        for track_id in stale_tracks:
            del self.states[track_id]
            self.objects_cleaned_up += 1
        
        if stale_tracks:
            logger.debug(f"🧹 Cleaned up {len(stale_tracks)} stale objects: {stale_tracks}")
    
    def get_stats(self) -> Dict:
        """
        Get object state manager statistics
        
        Returns:
            Dict with statistics
        """
        current_time = time.time()
        active_objects = len(self.states)
        
        # Calculate average speed of active objects
        speeds = [state.speed_kmh for state in self.states.values() if state.speed_kmh > 0]
        avg_speed = np.mean(speeds) if speeds else 0.0
        
        # Count violations
        violation_counts = defaultdict(int)
        for state in self.states.values():
            for violation_type, has_violation in state.violation_flags.items():
                if has_violation:
                    violation_counts[violation_type] += 1
        
        return {
            "active_objects": active_objects,
            "total_objects_tracked": self.total_objects_tracked,
            "objects_cleaned_up": self.objects_cleaned_up,
            "avg_speed_kmh": avg_speed,
            "violation_counts": dict(violation_counts),
            "config": {
                "max_age_seconds": self.max_age_seconds,
                "cleanup_interval": self.cleanup_interval,
                "pixel_to_meter_ratio": self.pixel_to_meter_ratio
            }
        }
    
    def reset_stats(self):
        """Reset statistics"""
        self.total_objects_tracked = 0
        self.objects_cleaned_up = 0
        logger.info("📊 Object state manager stats reset")