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

from app.violations.geometry import (
    classify_position,
    is_inside_violation_region,
    stopline_overlap,
)

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
    touched_during_yellow: bool = False

    # Frame đánh dấu lần đầu xe vào vùng vi phạm
    first_seen_in_vr_frame: int | None = None

    # Snapshot đầu tiên khi object vào Violation Region
    first_in_region_frame: int | None = None
    first_in_region_bbox: tuple[float, float, float, float] | None = None

    # Snapshot trong pha vàng để liên kết với vi phạm đỏ
    snapshot_yellow_frame: int | None = None
    snapshot_yellow_bbox: tuple[float, float, float, float] | None = None

    # "Best view" trong Violation Region (bbox to nhất, biển rõ nhất)
    best_view_frame: int | None = None
    best_view_bbox: tuple[float, float, float, float] | None = None
    best_view_area: float | None = None

    # Kết quả OCR biển (nếu đã chạy)
    plate_text: str | None = None
    plate_conf: float | None = None
    plate_ocr_done: bool = False

    # Frame đã lưu snapshot gần nhất để tránh ghi trùng
    last_snapshot_saved_frame: int | None = None


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


@dataclass
class ViolationFrameResult:
    violations: List[ViolationRecord]
    yellow_candidates: List[Dict[str, object]]
    violation_flags: Dict[int, str]


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
        self.violation_region: List[Tuple[float, float]] = violation_region or []
        self.vehicles: Dict[int, VehicleViolationState] = {}
        self.last_light_state: Optional[LightState] = None
        self.last_red_on: Optional[datetime] = None
        self.direction = stopline_rect.get("direction", "bottom_to_top")
        self.frame_index: int = 0
        
        # Log direction info on init
        if self.violation_region:
            self._log_direction_info()

    def _get_effective_direction(self) -> str:
        """Auto-detect traffic direction based on violation_region vs stopline position.
        
        Logic: Violation region là vùng xe đi vào SAU KHI vượt stopline.
        - Nếu violation_region ở TRÊN stopline (y nhỏ hơn) → xe đi từ dưới lên (bottom_to_top)
        - Nếu violation_region ở DƯỚI stopline (y lớn hơn) → xe đi từ trên xuống (top_to_bottom)
        """
        if self.violation_region:
            region_center_y = sum(pt[1] for pt in self.violation_region) / len(self.violation_region)
            line_y = self.stopline_rect.get("y1", 0)
            if region_center_y < line_y:
                # Violation region is ABOVE stopline (smaller y) 
                # → traffic goes from bottom to top (y decreases)
                return "bottom_to_top"
            else:
                # Violation region is BELOW stopline (larger y)
                # → traffic goes from top to bottom (y increases)
                return "top_to_bottom"
        return self.direction
    
    def _log_direction_info(self) -> None:
        """Log direction detection info for debugging."""
        if self.violation_region:
            region_center_y = sum(pt[1] for pt in self.violation_region) / len(self.violation_region)
            line_y = self.stopline_rect.get("y1", 0)
            direction = self._get_effective_direction()
            logger.info(
                f"[DIRECTION] cam={self.camera_id}, region_center_y={region_center_y:.1f}, "
                f"stopline_y={line_y}, direction={direction}"
            )

    def _stopline_band(self) -> Tuple[float, float]:
        y1 = float(self.stopline_rect.get("y1", 0))
        y2 = float(self.stopline_rect.get("y2", y1))
        band_min, band_max = (min(y1, y2), max(y1, y2))
        if band_min == band_max:
            padding = 2.0
            return (band_min - padding, band_max + padding)
        return (band_min, band_max)

    def _front_point(self, bbox: Tuple[float, float, float, float]) -> Tuple[float, float]:
        """Get front point of vehicle depending on travel direction."""
        x1, y1, x2, y2 = bbox
        cx = (x1 + x2) / 2.0
        effective_direction = self._get_effective_direction()
        if effective_direction == "top_to_bottom":
            return cx, y2  # Front is bottom of bbox
        return cx, y1  # Front is top of bbox

    def _stopline_overlap_ratio(self, bbox: Tuple[float, float, float, float]) -> float:
        """
        Tính % chiều cao bbox đã vượt qua vạch dừng theo hướng chuyển động.
        
        Hướng di chuyển được tự động xác định dựa trên vị trí violation_region vs stopline:
        - Nếu violation_region ở TRÊN stopline (y nhỏ hơn) → xe đi từ dưới lên (bottom_to_top)
        - Nếu violation_region ở DƯỚI stopline (y lớn hơn) → xe đi từ trên xuống (top_to_bottom)
        
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
        
        effective_direction = self._get_effective_direction()

        if effective_direction == "top_to_bottom":
            # Xe di chuyển từ trên xuống dưới: đầu xe là đáy bbox (y_bottom)
            # Xe vượt vạch khi y_bottom > line_y
            depth = y_bottom - line_y  # >0 khi đầu xe đã vượt qua vạch
        else:
            # Hướng dưới → lên: đầu xe là đỉnh bbox (y_top)
            # Xe vượt vạch khi y_top < line_y
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
        
        Direction is auto-detected based on violation_region vs stopline:
        - top_to_bottom: BEFORE means y < line_y, AFTER means y > line_y
        - bottom_to_top: BEFORE means y > line_y, AFTER means y < line_y
        """
        px, py = point
        line_y = self.stopline_rect.get("y1", 0)
        
        # Threshold for "ON" the line (in pixels)
        threshold = 10.0

        if abs(py - line_y) < threshold:
            return "ON"

        effective_direction = self._get_effective_direction()
        
        if effective_direction == "top_to_bottom":
            # Traffic goes from top to bottom (y increases)
            # BEFORE: point is above the line (y < line_y)
            # AFTER: point is below the line (y > line_y)
            if py < line_y:
                return "BEFORE"
            return "AFTER"
        else:
            # Traffic goes from bottom to top (y decreases)
            # BEFORE: point is below the line (y > line_y)
            # AFTER: point is above the line (y < line_y)
            if py > line_y:
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
                v.touched_during_yellow = False
                v.violated = False  # Reset for new cycle
                v.snapshot_yellow_frame = None
                v.snapshot_yellow_bbox = None

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
        self,
        vehicle_tracks: List[Dict[str, object]],
        light_state: LightState,
        timestamp: datetime,
        frame_index: Optional[int] = None,
    ) -> ViolationFrameResult:
        """Process the current frame and return any new violations."""
        previous_light_state = self.last_light_state
        self._update_light(light_state, timestamp)
        bootstrap_red = previous_light_state is None and light_state == "RED"

        violations: List[ViolationRecord] = []
        yellow_candidates: List[Dict[str, object]] = []
        violation_flags: Dict[int, str] = {}

        inside_count = 0

        if frame_index is not None:
            self.frame_index = frame_index
        else:
            self.frame_index += 1

        current_frame_index = self.frame_index

        logger.info(
            f"[VIOLATION] tracks={len(vehicle_tracks)}, light={light_state}, stopline={self.stopline_rect}"
        )

        stopline_band = self._stopline_band()

        for track in vehicle_tracks:
            track_id_raw = track.get("track_id") or track.get("id")
            if track_id_raw is None:
                continue
            track_id = int(track_id_raw)
            bbox = track.get("bbox")
            if bbox is None or len(bbox) != 4:
                continue

            bbox_tuple = tuple(bbox)
            class_name = track.get("class_name")

            vehicle, is_new = self._ensure_vehicle(track_id)
            vehicle.last_update_time = timestamp

            previous_position = vehicle.position_vs_line
            position = classify_position(bbox_tuple, stopline_band)
            overlap_ratio = stopline_overlap(bbox_tuple, stopline_band)
            inside_region = is_inside_violation_region(bbox_tuple, self.violation_region)

            # DEBUG: Log every track's position
            if self.frame_index % 30 == 0:
                logger.warning(
                    f"[TRACK-DEBUG] cam={self.camera_id}, track={track_id}, "
                    f"bbox={bbox}, inside_region={inside_region}, "
                    f"light={light_state}, position={position}, overlap={overlap_ratio:.2f}"
                )

            if not inside_region:
                vehicle.position_vs_line = position
                vehicle.last_update_time = timestamp
                continue

            # Snapshot logic inside violation region
            if vehicle.first_in_region_frame is None:
                vehicle.first_in_region_frame = current_frame_index
                vehicle.first_in_region_bbox = bbox_tuple
                logger.info(
                    f"[PLATE-SNAPSHOT-FIRST] cam={self.camera_id}, "
                    f"track={track_id}, frame={current_frame_index}, bbox={bbox}"
                )

            x1, y1, x2, y2 = bbox_tuple
            area = max(0.0, (x2 - x1) * (y2 - y1))
            if vehicle.best_view_area is None or area > vehicle.best_view_area:
                vehicle.best_view_area = area
                vehicle.best_view_frame = current_frame_index
                vehicle.best_view_bbox = bbox_tuple
                logger.info(
                    f"[PLATE-SNAPSHOT-BEST] cam={self.camera_id}, "
                    f"track={track_id}, frame={current_frame_index}, area={area}, bbox={bbox}"
                )

            inside_count += 1  # Đếm số xe trong vùng vi phạm

            vehicle.position_vs_line = position

            # Record position when red for new vehicles (informational only)
            if is_new and self.last_light_state == "RED" and self.last_red_on:
                vehicle.position_when_red = position

            # ==================================================================
            # YELLOW PHASE: track candidates inside violation region
            # Start-up RED shortcut: if stream starts while RED, still seed state
            # quickly so stopline violations can be evaluated without waiting for
            # a full cycle.
            # ==================================================================
            yellow_arm_phase = light_state == "YELLOW" or bootstrap_red

            if yellow_arm_phase:
                if vehicle.first_seen_in_vr_frame is None:
                    vehicle.first_seen_in_vr_frame = current_frame_index
                if vehicle.snapshot_yellow_frame is None:
                    vehicle.snapshot_yellow_frame = current_frame_index
                    vehicle.snapshot_yellow_bbox = bbox_tuple
                if overlap_ratio >= 0.4:
                    vehicle.touched_during_yellow = True

                yellow_candidates.append({
                    "track_id": track_id,
                    "class_name": class_name,
                    "bbox": list(bbox_tuple),
                    "position": position,
                    "overlap": overlap_ratio,
                    "snapshot_frame": vehicle.snapshot_yellow_frame or current_frame_index,
                    "first_seen_frame": vehicle.first_in_region_frame,
                    "best_view_frame": vehicle.best_view_frame,
                    "best_view_bbox": list(vehicle.best_view_bbox)
                    if vehicle.best_view_bbox
                    else list(bbox_tuple),
                })
                continue

            violation_type: Optional[str] = None

            # Track crossing for logging purposes
            crossed = previous_position == "BEFORE" and position in {"ON", "AFTER"}
            if crossed and light_state == "RED":
                logger.info(
                    f"[VIOLATION] Track {track_id} crossed stopline: {previous_position} -> {position}, "
                    f"overlap={overlap_ratio:.2f}"
                )

            if light_state == "RED" and not vehicle.violated:
                if overlap_ratio >= 0.4:
                    if vehicle.touched_during_yellow and position == "ON":
                        violation_type = "STOPLINE"
                    elif (
                        previous_position == "BEFORE"
                        and position == "AFTER"
                        and vehicle.position_when_red == "BEFORE"
                    ):
                        violation_type = "RED_LIGHT"

                if violation_type:
                    vehicle.violated = True
                    violation_flags[track_id] = violation_type
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
                            "previous_position": previous_position,
                            "overlap_ratio": overlap_ratio,
                            "touched_during_yellow": vehicle.touched_during_yellow,
                            "is_new_track": is_new,
                            "first_in_region_frame": vehicle.first_in_region_frame,
                            "first_in_region_bbox": vehicle.first_in_region_bbox,
                            "best_view_frame": vehicle.best_view_frame,
                            "best_view_bbox": vehicle.best_view_bbox,
                            "plate_text": vehicle.plate_text,
                            "plate_conf": vehicle.plate_conf,
                            "snapshot_frame_yellow": vehicle.snapshot_yellow_frame,
                            "snapshot_bbox_yellow": vehicle.snapshot_yellow_bbox,
                            "class_name": class_name,
                            "bbox": bbox_tuple,
                        },
                    )
                    violations.append(violation_record)
                elif light_state == "RED" and crossed:
                    logger.debug(
                        f"[VIOLATION] Track {track_id} crossed stopline but no violation "
                        f"(overlap={overlap_ratio:.2f}, violated={vehicle.violated})"
                    )

        if light_state == "YELLOW":
            logger.info(
                "YELLOW-ARM frame=%d, candidates=%d, ids=%s",
                current_frame_index,
                len(yellow_candidates),
                [c["track_id"] for c in yellow_candidates],
            )

        if bootstrap_red:
            logger.info(
                "RED-BOOT frame=%d, candidates=%d, ids=%s",
                current_frame_index,
                len(yellow_candidates),
                [c["track_id"] for c in yellow_candidates],
            )

        if light_state == "RED":
            logger.info(
                "RED-CHECK frame=%d, violations=%d, ids=%s",
                current_frame_index,
                len(violations),
                [v.track_id for v in violations],
            )

        logger.info(
            f"[TL] camera={self.camera_id}, light={light_state}, tracks={len(vehicle_tracks)}, inside_region={inside_count}"
        )
        self._prune_stale(timestamp)
        return ViolationFrameResult(
            violations=violations,
            yellow_candidates=yellow_candidates,
            violation_flags=violation_flags,
        )

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
        # Log direction info when region is updated
        if self.violation_region:
            self._log_direction_info()
