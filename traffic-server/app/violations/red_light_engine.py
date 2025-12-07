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
    position_when_red: Position = "BEFORE"
    first_seen_time: datetime = field(default_factory=datetime.utcnow)
    last_update_time: datetime = field(default_factory=datetime.utcnow)
    front_history: list[Tuple[float, float]] = field(default_factory=list)


@dataclass
class ViolationRecord:
    camera_id: str
    track_id: int
    violation_type: str
    timestamp: datetime
    details: Dict[str, object]


class RedLightViolationEngine:
    """Red-light violation detection with per-vehicle state tracking."""

    def __init__(self, camera_id: str, stopline_rect: Dict[str, float]):
        self.camera_id = camera_id
        self.stopline_rect = stopline_rect
        self.vehicles: Dict[int, VehicleViolationState] = {}
        self.last_light_state: Optional[LightState] = None
        self.last_red_on: Optional[datetime] = None

    def _front_point(self, bbox: Tuple[float, float, float, float]) -> Tuple[float, float]:
        x1, y1, x2, _ = bbox
        cx = (x1 + x2) / 2.0
        return cx, y1

    def _position_vs_stopline(self, point: Tuple[float, float]) -> Position:
        """
        Determine if point is BEFORE, ON, or AFTER the stopline.
        
        For a line from (x1,y1) to (x2,y2), we use the cross product to determine
        which side of the line the point is on.
        
        Cross product: (x2-x1)*(py-y1) - (y2-y1)*(px-x1)
        - Positive: point is on the RIGHT side (AFTER for top-to-bottom traffic)
        - Negative: point is on the LEFT side (BEFORE)
        - ~Zero: point is ON the line
        """
        px, py = point
        x1 = self.stopline_rect.get("x1", 0)
        y1 = self.stopline_rect.get("y1", 0)
        x2 = self.stopline_rect.get("x2", 0)
        y2 = self.stopline_rect.get("y2", 0)

        # Calculate cross product
        cross = (x2 - x1) * (py - y1) - (y2 - y1) * (px - x1)
        
        # Threshold for "ON" the line (in pixels)
        threshold = 10.0
        
        if abs(cross) < threshold:
            return "ON"
        elif cross > 0:
            # Point is below/after the line (in direction of traffic)
            return "AFTER"
        else:
            # Point is above/before the line
            return "BEFORE"

    def _ensure_vehicle(self, track_id: int) -> tuple[VehicleViolationState, bool]:
        if track_id not in self.vehicles:
            self.vehicles[track_id] = VehicleViolationState(track_id=track_id)
            return self.vehicles[track_id], True
        return self.vehicles[track_id], False

    def _update_light(self, light_state: LightState, timestamp: datetime) -> None:
        if light_state != self.last_light_state and light_state == "RED":
            self.last_red_on = timestamp
            for v in self.vehicles.values():
                v.position_when_red = v.position_vs_line
        self.last_light_state = light_state

    def _is_vehicle_stopped(self, vehicle: VehicleViolationState, threshold_px: float = 6.0) -> bool:
        """Rudimentary stop detector using recent front-point displacement."""
        if len(vehicle.front_history) < 3:
            return False

        recent = vehicle.front_history[-5:]
        xs = [p[0] for p in recent]
        ys = [p[1] for p in recent]
        return (max(xs) - min(xs) <= threshold_px) and (max(ys) - min(ys) <= threshold_px)

    def update(
        self, vehicle_tracks: List[Dict[str, object]], light_state: LightState, timestamp: datetime
    ) -> List[ViolationRecord]:
        """Process the current frame and return any new violations."""
        self._update_light(light_state, timestamp)
        violations: List[ViolationRecord] = []

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
            position = self._position_vs_stopline(front_point)
            vehicle.position_vs_line = position
            vehicle.front_history.append(front_point)
            if len(vehicle.front_history) > 15:
                vehicle.front_history = vehicle.front_history[-15:]

            if is_new and self.last_light_state == "RED" and self.last_red_on:
                vehicle.position_when_red = position
                logger.info(
                    f"[VIOLATION] Track {track_id} NEW while RED: position={position}, front_point={front_point}"
                )

            crossed = previous_position == "BEFORE" and position in {"ON", "AFTER"}
            if crossed:
                logger.info(
                    f"[VIOLATION] Track {track_id} crossed stopline: {previous_position} -> {position}"
                )

            y1_line = self.stopline_rect.get("y1", 0)
            y2_bbox = float(bbox[3])
            touched = y2_bbox >= y1_line
            if touched:
                logger.info(
                    f"[VIOLATION] Track {track_id} touched stopline 50% at y2={y2_bbox}, stopline_y1={y1_line}, position={position}, position_when_red={vehicle.position_when_red}"
                )
            violation_type: Optional[str] = None

            if (
                light_state == "RED"
                and vehicle.position_when_red == "BEFORE"
                and (crossed or touched)
                and not vehicle.violated
                and self.last_red_on is not None
            ):
                violation_type = "RED_LIGHT_RUN"
                logger.warning(
                    f"🚨 RED LIGHT VIOLATION RUN — camera={self.camera_id}, track={track_id}, from={previous_position} -> {position}"
                )

            stopped_on_line = (
                light_state == "RED"
                and position in {"ON", "AFTER"}
                and not crossed
                and self._is_vehicle_stopped(vehicle)
                and not vehicle.violated
            )
            if violation_type is None and stopped_on_line:
                violation_type = "RED_LIGHT_STOPLINE"
                logger.warning(
                    f"🚨 RED LIGHT VIOLATION STOPLINE — camera={self.camera_id}, track={track_id}, position={position}"
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
                        "position_when_red": vehicle.position_when_red,
                        "position_now": position,
                    },
                )
                violations.append(violation_record)
            elif light_state == "RED" and (crossed or touched):
                logger.info(
                    f"[VIOLATION] Track {track_id} NOT violated: position_when_red={vehicle.position_when_red}, violated={vehicle.violated}, last_red_on={self.last_red_on is not None}"
                )

        self._prune_stale(timestamp)
        return violations

    def _prune_stale(self, now: datetime, ttl_s: float = 5.0) -> None:
        stale_ids = [tid for tid, v in self.vehicles.items() if (now - v.last_update_time).total_seconds() > ttl_s]
        for tid in stale_ids:
            del self.vehicles[tid]

    def reset_stopline(self, stopline_rect: Dict[str, float]) -> None:
        self.stopline_rect = stopline_rect
        self.vehicles.clear()
        self.last_light_state = None
        self.last_red_on = None
