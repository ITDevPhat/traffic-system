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

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Tuple


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
        px, py = point
        x1 = self.stopline_rect.get("x1", 0)
        y1 = self.stopline_rect.get("y1", 0)
        x2 = self.stopline_rect.get("x2", 0)
        y2 = self.stopline_rect.get("y2", 0)

        if x1 <= px <= x2 and y1 <= py <= y2:
            return "ON"
        if py > y2:
            return "BEFORE"
        return "AFTER"

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

    def update(self, vehicle_tracks: List[Dict[str, object]], light_state: LightState, timestamp: datetime) -> List[ViolationRecord]:
        """Process the current frame and return any new violations."""
        self._update_light(light_state, timestamp)
        violations: List[ViolationRecord] = []

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

            position = self._position_vs_stopline(self._front_point(tuple(bbox)))
            previous_position = position if is_new else vehicle.position_vs_line
            vehicle.position_vs_line = position

            if is_new and self.last_light_state == "RED" and self.last_red_on:
                vehicle.position_when_red = position

            crossed = previous_position == "BEFORE" and position in {"ON", "AFTER"}

            if crossed and light_state == "RED" and vehicle.position_when_red == "BEFORE" and self.last_red_on:
                vehicle.violated = True
                violations.append(
                    ViolationRecord(
                        camera_id=self.camera_id,
                        track_id=vehicle.track_id,
                        violation_type="RED_LIGHT",
                        timestamp=timestamp,
                        details={
                            "stopline": self.stopline_rect,
                            "light_state": light_state,
                            "red_since": self.last_red_on.isoformat(),
                        },
                    )
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
