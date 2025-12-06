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

        if py < y1:
            return "BEFORE"
        if y1 <= py <= y2 and x1 <= px <= x2:
            return "ON"
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
            position = self._position_vs_stopline(self._front_point(tuple(bbox)))
            vehicle.position_vs_line = position

            if is_new and self.last_light_state == "RED" and self.last_red_on:
                vehicle.position_when_red = position

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
                    f"[VIOLATION] Track {track_id} touched stopline 50% at y2={y2_bbox}, stopline_y1={y1_line}"
                )

            should_violate = (
                light_state == "RED"
                and vehicle.position_when_red == "BEFORE"
                and (crossed or touched)
                and not vehicle.violated
                and self.last_red_on is not None
            )

            if should_violate:
                vehicle.violated = True
                violation_record = ViolationRecord(
                    camera_id=self.camera_id,
                    track_id=vehicle.track_id,
                    violation_type="RED_LIGHT",
                    timestamp=timestamp,
                    details={
                        "stopline": self.stopline_rect,
                        "light_state": light_state,
                        "red_since": self.last_red_on.isoformat(),
                        "position_when_red": vehicle.position_when_red,
                        "position_now": position,
                    },
                )
                violations.append(violation_record)
                logger.warning(
                    f"🚨 RED LIGHT VIOLATION — camera={self.camera_id}, track={track_id}"
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
