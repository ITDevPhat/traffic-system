"""Stateful red-light violation engine.

This engine fuses vehicle tracks, the stabilized traffic light state, and a
stopline ROI to determine which vehicles run a red light. The implementation
follows the time-based rule set described in the product brief:

- Track each vehicle's position relative to the stopline (BEFORE/ON/AFTER)
- Record when the light turns RED
- Flag a violation when a vehicle crosses the stopline after the light turns
  RED and it was still BEFORE the line at the red onset time
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


Position = str  # "BEFORE" | "ON" | "AFTER"
LightState = str  # "RED" | "GREEN" | "YELLOW"


@dataclass
class VehicleViolationState:
    track_id: int
    position_vs_line: Position = "BEFORE"
    violated: bool = False
    position_when_red: Position = "BEFORE"  # Informational only, not used in violation logic
    first_seen_time: datetime = field(default_factory=datetime.utcnow)
    last_update_time: datetime = field(default_factory=datetime.utcnow)
    # NEW: đánh dấu xe đã chạm vạch trong pha vàng/đỏ
    touched_during_yellow_or_before_red: bool = False


@dataclass
class ViolationRecord:
    camera_id: str
    track_id: int
    violation_type: str
    timestamp: datetime
    details: Dict[str, object]
    
    def to_dict(self) -> Dict[str, object]:
        """Convert ViolationRecord to JSON-serializable dict"""
        return {
            "camera_id": self.camera_id,
            "track_id": self.track_id,
            "violation_type": self.violation_type,
            "timestamp": self.timestamp.isoformat(),
            "details": self.details,
        }


class RedLightViolationEngine:
    """Red-light violation detection with per-vehicle state tracking."""

    def __init__(
        self,
        camera_id: str,
        stopline_rect: Dict[str, float],
        violation_region: Optional[List[Tuple[float, float]]] = None,
    ):
        self.camera_id = camera_id
        self.stopline_rect = stopline_rect
        self.direction = stopline_rect.get("direction", "bottom_to_top")
        self.violation_region: List[Tuple[float, float]] = violation_region or []
        self.vehicles: Dict[int, VehicleViolationState] = {}
        self.last_light_state: Optional[LightState] = None
        self.last_red_on: Optional[datetime] = None

    def _front_point(self, bbox: Tuple[float, float, float, float]) -> Tuple[float, float]:
        """Get front point of vehicle depending on travel direction."""
        x1, y1, x2, y2 = bbox
        cx = (x1 + x2) / 2.0
        if self.direction == "top_to_bottom":
            return cx, y2
        return cx, y1

    def _stopline_overlap_ratio(self, bbox: Tuple[float, float, float, float]) -> float:
        """
        Tính % chiều cao bbox đã vượt qua vạch dừng theo hướng chuyển động.
        
        Cam01 & Cam02: xe chạy từ dưới lên trên (bottom → top)
        → đầu xe là cạnh trên bbox (y_top = bbox[1])
        
        Returns:
            float in [0.0, 1.0]:
            - 0.0: chưa chạm vạch
            - 0.4: đầu xe vượt vạch 40% chiều cao xe
            - >=0.4: đè vạch đủ để bắt lỗi
        """
        x1, y_top, x2, y_bottom = bbox
        h = y_bottom - y_top
        
        if h <= 0:
            return 0.0
        
        # Stopline y coordinate (horizontal line)
        line_y = self.stopline_rect.get("y1", 0)

        if self.direction == "top_to_bottom":
            # Xe di chuyển từ trên xuống dưới: đầu xe là đáy bbox
            depth = y_bottom - line_y  # >0 khi đầu xe đã vượt qua vạch
        else:
            # Hướng dưới → lên: xe chưa chạm khi y_top > line_y
            depth = line_y - y_top  # >0 khi đầu xe đã vượt qua vạch

        if depth <= 0:
            return 0.0

        ratio = depth / h
        return max(0.0, min(1.0, ratio))

    def _point_in_violation_region(self, x: float, y: float) -> bool:
        """Return True if point is inside the configured violation region polygon."""
        if not self.violation_region:
            # No region configured → keep legacy behaviour (always consider it inside)
            return True

        pts = self.violation_region
        inside = False
        n = len(pts)

        for i in range(n):
            x1, y1 = pts[i]
            x2, y2 = pts[(i + 1) % n]
            if ((y1 > y) != (y2 > y)) and (
                x < (x2 - x1) * (y - y1) / (y2 - y1 + 1e-9) + x1
            ):
                inside = not inside

        return inside

    def _position_vs_stopline(self, point: Tuple[float, float]) -> Position:
        """
        Determine if point is BEFORE, ON, or AFTER the stopline.
        
        For bottom-to-top traffic (cam01 & cam02):
        - BEFORE: y > line_y (below the line)
        - ON: y ≈ line_y (on the line)
        - AFTER: y < line_y (above the line)
        """
        px, py = point
        line_y = self.stopline_rect.get("y1", 0)
        
        # Threshold for "ON" the line (in pixels)
        threshold = 10.0

        if abs(py - line_y) < threshold:
            return "ON"

        if self.direction == "top_to_bottom":
            if py < line_y:
                return "BEFORE"
            return "AFTER"

        if py > line_y:
            # Point is below the line (BEFORE for bottom-to-top traffic)
            return "BEFORE"
        return "AFTER"

    def _ensure_vehicle(self, track_id: int) -> tuple[VehicleViolationState, bool]:
        if track_id not in self.vehicles:
            self.vehicles[track_id] = VehicleViolationState(track_id=track_id)
            return self.vehicles[track_id], True
        return self.vehicles[track_id], False

    def _update_light(self, light_state: LightState, timestamp: datetime) -> None:
        """Update light state and record when it turns RED"""
        
        # Reset state when light turns GREEN (new cycle)
        if self.last_light_state == "RED" and light_state == "GREEN":
            logger.info(f"🟢 Light turned GREEN - resetting violation states")
            for v in self.vehicles.values():
                v.touched_during_yellow_or_before_red = False
                v.violated = False  # Reset for new cycle
        
        # Record when light turns RED
        if light_state != self.last_light_state and light_state == "RED":
            self.last_red_on = timestamp
            # Record position when red for informational purposes only
            for v in self.vehicles.values():
                v.position_when_red = v.position_vs_line
            logger.info(f"🔴 Light turned RED at {timestamp.isoformat()}")
        
        # Log when light turns YELLOW
        if light_state != self.last_light_state and light_state == "YELLOW":
            logger.info(f"🟡 Light turned YELLOW at {timestamp.isoformat()}")
        
        self.last_light_state = light_state



    def update(
        self, vehicle_tracks: List[Dict[str, object]], light_state: LightState, timestamp: datetime
    ) -> List[ViolationRecord]:
        """Process the current frame and return any new violations."""
        self._update_light(light_state, timestamp)
        violations: List[ViolationRecord] = []

        inside_count = 0

        logger.info(
            f"[VIOLATION] tracks={len(vehicle_tracks)}, light={light_state}, stopline={self.stopline_rect}"
        )

        for track in vehicle_tracks:
            track_id_raw = track.get("track_id") or track.get("id")
            if track_id_raw is None:
                continue
            track_id = int(track_id_raw)
            bbox = track.get("bbox")
            if bbox is None or len(bbox) != 4:
                continue

            vehicle, is_new = self._ensure_vehicle(track_id)
            vehicle.last_update_time = timestamp

            previous_position = vehicle.position_vs_line
            front_point = self._front_point(tuple(bbox))

            inside_region = self._point_in_violation_region(*front_point)
            if inside_region:
                inside_count += 1
            if not inside_region:
                vehicle.position_vs_line = "BEFORE"
                vehicle.last_update_time = timestamp
                continue

            position = self._position_vs_stopline(front_point)
            vehicle.position_vs_line = position

            # Record position when red for new vehicles (informational only)
            if is_new and self.last_light_state == "RED" and self.last_red_on:
                vehicle.position_when_red = position

            # Calculate overlap ratio (how much of vehicle height has crossed the stopline)
            overlap_ratio = self._stopline_overlap_ratio(tuple(bbox))
            
            # Log overlap when vehicle is near/on stopline
            if overlap_ratio > 0.0:
                logger.debug(
                    f"[VIOLATION] Track {track_id} overlap_ratio={overlap_ratio:.2f}, "
                    f"light={light_state}, prev={previous_position}, pos={position}"
                )
            
            if light_state == "YELLOW":
                logger.info(
                    f"[YELLOW] cam={self.camera_id} track={track_id} front={front_point} "
                    f"inside={inside_region} overlap={overlap_ratio:.2f} prev={previous_position} pos={position}"
                )

            # ==================================================================
            # YELLOW PHASE: "Arm" vehicles that touch stopline during yellow
            # ==================================================================
            if light_state == "YELLOW" and overlap_ratio > 0.0:
                if not vehicle.touched_during_yellow_or_before_red:
                    vehicle.touched_during_yellow_or_before_red = True
                    logger.info(
                        f"🟡 Track {track_id} touched stopline during YELLOW "
                        f"(overlap={overlap_ratio:.2f}, pos={position})"
                    )
            
            # Track crossing for logging purposes
            crossed = previous_position == "BEFORE" and position in {"ON", "AFTER"}
            if crossed and light_state == "RED":
                logger.info(
                    f"[VIOLATION] Track {track_id} crossed stopline: {previous_position} -> {position}, "
                    f"overlap={overlap_ratio:.2f}"
                )

            violation_type: Optional[str] = None

            # ==================================================================
            # RED PHASE: Check violations immediately
            # Chỉ xét xe đã chạm vạch (overlap > 0)
            # ==================================================================
            if light_state == "RED" and not vehicle.violated:
                logger.info(
                    f"[RED] cam={self.camera_id} track={track_id} inside={inside_region} "
                    f"overlap={overlap_ratio:.2f} prev={previous_position} pos={position} "
                    f"touched_yellow={vehicle.touched_during_yellow_or_before_red}"
                )
                # Chỉ xét các xe thực sự chạm vạch (overlap > 0)
                if overlap_ratio > 0.0:
                    # Nếu đè vạch >= 40% chiều cao → đây là vi phạm
                    if overlap_ratio >= 0.4:
                        # Phân loại vi phạm:
                        # - Nếu trước đó còn BEFORE và chưa chạm vạch trong pha vàng → vượt đèn đỏ
                        # - Nếu đã chạm trong pha vàng hoặc đang nằm trên/qua vạch → dừng sai vạch
                        if previous_position == "BEFORE" and not vehicle.touched_during_yellow_or_before_red:
                            violation_type = "RED_LIGHT_RUN"
                        else:
                            violation_type = "RED_LIGHT_STOPLINE"
                        
                        logger.warning(
                            f"🚨 RED LIGHT VIOLATION — camera={self.camera_id}, "
                            f"track={track_id}, type={violation_type}, "
                            f"overlap={overlap_ratio:.2f}, prev={previous_position}, now={position}, "
                            f"touched_during_yellow={vehicle.touched_during_yellow_or_before_red}"
                        )
                else:
                    logger.debug(
                        f"[VIOLATION] Track {track_id} RED but has not touched stopline "
                        f"(overlap={overlap_ratio:.2f})"
                    )

            if violation_type:
                vehicle.violated = True
                violation_record = ViolationRecord(
                    camera_id=self.camera_id,
                    track_id=vehicle.track_id,
                    violation_type=violation_type,
                    timestamp=timestamp,
                    details={
                        "stopline": self.stopline_rect,
                        "light_state": light_state,
                        "red_since": self.last_red_on.isoformat() if self.last_red_on else None,
                        "position_now": position,
                        "overlap_ratio": overlap_ratio,
                        "touched_during_yellow": vehicle.touched_during_yellow_or_before_red,
                    },
                )
                violations.append(violation_record)
            elif light_state == "RED" and crossed:
                logger.debug(
                    f"[VIOLATION] Track {track_id} crossed stopline but no violation "
                    f"(overlap={overlap_ratio:.2f}, violated={vehicle.violated})"
                )

        
        logger.info(
            f"[TL] camera={self.camera_id}, light={light_state}, tracks={len(vehicle_tracks)}, inside_region={inside_count}"
        )
        self._prune_stale(timestamp)
        return violations

    def _prune_stale(self, now: datetime, ttl_s: float = 5.0) -> None:
        stale_ids = [tid for tid, v in self.vehicles.items() if (now - v.last_update_time).total_seconds() > ttl_s]
        for tid in stale_ids:
            del self.vehicles[tid]

    def reset_stopline(self, stopline_rect: Dict[str, float]) -> None:
        self.stopline_rect = stopline_rect
        self.direction = stopline_rect.get("direction", "bottom_to_top")
        self.vehicles.clear()
        self.last_light_state = None
        self.last_red_on = None

    def reset_violation_region(self, violation_region: Optional[List[Tuple[float, float]]]) -> None:
        self.violation_region = violation_region or []
