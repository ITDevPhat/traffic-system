"""Temporal red-light violation engine.

Implements full temporal logic:
- Track vehicle position relative to stopline (BEFORE/ON/AFTER)
- Capture each vehicle's position when the light turns RED
- Emit a violation only when a vehicle that was BEFORE the line at red-onset
  later crosses to AFTER the line during the same red phase
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Tuple


Position = str  # "BEFORE_LINE" | "ON_LINE" | "AFTER_LINE"
LightState = str  # "RED" | "GREEN" | "YELLOW"


@dataclass
class VehicleState:
    """Per-vehicle temporal state."""

    track_id: int
    last_position: Position = "BEFORE_LINE"
    position_when_red: Optional[Position] = None
    violated: bool = False
    last_seen: datetime = field(default_factory=datetime.utcnow)


class RedLightViolationEngine:
    """Full temporal logic for red-light violations."""

    def __init__(self, camera_id: str, stopline_rect: Dict[str, float], tolerance: float = 2.0):
        self.camera_id = camera_id
        self.stopline_rect = stopline_rect
        self.tolerance = tolerance
        self.vehicles: Dict[int, VehicleState] = {}
        self.last_light_state: Optional[LightState] = None
        self.red_on_timestamp: Optional[datetime] = None

    def reset_stopline(self, stopline_rect: Dict[str, float]) -> None:
        self.stopline_rect = stopline_rect
        self.vehicles.clear()
        self.last_light_state = None
        self.red_on_timestamp = None

    def _stopline_y(self) -> Optional[float]:
        y1 = self.stopline_rect.get("y1")
        y2 = self.stopline_rect.get("y2")
        if y1 is None or y2 is None:
            return None
        return (float(y1) + float(y2)) / 2.0

    def _front_point(self, bbox: Tuple[float, float, float, float]) -> Tuple[float, float]:
        x1, _, x2, y2 = bbox
        cx = (x1 + x2) / 2.0
        return cx, y2  # bottom-center represents forward motion direction

    def _position_vs_stopline(self, front_y: float, stopline_y: float) -> Position:
        if front_y < stopline_y - self.tolerance:
            return "BEFORE_LINE"
        if abs(front_y - stopline_y) <= self.tolerance:
            return "ON_LINE"
        return "AFTER_LINE"

    def _get_vehicle(self, track_id: int) -> VehicleState:
        if track_id not in self.vehicles:
            self.vehicles[track_id] = VehicleState(track_id=track_id)
        return self.vehicles[track_id]

    def _handle_light_transition(self, light_state: LightState, timestamp: datetime) -> None:
        if light_state == "RED" and self.last_light_state != "RED":
            self.red_on_timestamp = timestamp
            for vehicle in self.vehicles.values():
                vehicle.position_when_red = None
                vehicle.violated = False
        elif light_state in {"GREEN", "YELLOW"} and self.last_light_state == "RED":
            self.red_on_timestamp = None
            for vehicle in self.vehicles.values():
                vehicle.position_when_red = None
                vehicle.violated = False
        self.last_light_state = light_state

    def update(
        self,
        vehicle_tracks: List[Dict[str, object]],
        light_state: LightState,
        timestamp: datetime,
        stopline_rect: Optional[Dict[str, float]] = None,
    ) -> List[Dict[str, object]]:
        """Process current frame and return new violation payloads."""

        if stopline_rect:
            self.stopline_rect = stopline_rect

        stopline_y = self._stopline_y()
        if stopline_y is None:
            return []

        self._handle_light_transition(light_state, timestamp)

        violations: List[Dict[str, object]] = []

        for track in vehicle_tracks:
            track_id_raw = track.get("track_id") or track.get("id")
            bbox = track.get("bbox")
            if track_id_raw is None or bbox is None or len(bbox) != 4:
                continue

            track_id = int(track_id_raw)
            vehicle = self._get_vehicle(track_id)
            vehicle.last_seen = timestamp

            _, front_y = self._front_point(tuple(map(float, bbox)))
            position = self._position_vs_stopline(front_y, stopline_y)

            if light_state == "RED" and vehicle.position_when_red is None:
                vehicle.position_when_red = position

            previous_position = vehicle.last_position
            vehicle.last_position = position

            crossed = previous_position in {"BEFORE_LINE", "ON_LINE"} and position == "AFTER_LINE"

            if (
                light_state == "RED"
                and vehicle.position_when_red == "BEFORE_LINE"
                and crossed
                and not vehicle.violated
            ):
                vehicle.violated = True
                violations.append(
                    {
                        "track_id": track_id,
                        "violation_type": "RED_LIGHT",
                        "timestamp": timestamp.isoformat(),
                        "bbox": list(map(float, bbox)),
                        "position_when_red": vehicle.position_when_red,
                        "t_cross": timestamp.isoformat(),
                        "stopline": self.stopline_rect,
                    }
                )

        self._prune_stale(timestamp)
        return violations

    def _prune_stale(self, now: datetime, ttl_s: float = 2.0) -> None:
        stale_ids = [tid for tid, v in self.vehicles.items() if (now - v.last_seen).total_seconds() > ttl_s]
        for tid in stale_ids:
            del self.vehicles[tid]
