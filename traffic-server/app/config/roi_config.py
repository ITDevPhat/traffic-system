"""Utility helpers for persisting traffic-light ROI and stopline configs.

All coordinates are stored in normalized format relative to the source frame size
so they remain valid across different resolutions. Per-camera config files are
kept under ``app/data/traffic_light/``.
"""
from __future__ import annotations

import json
import json
import logging
from pathlib import Path
from typing import Dict, Optional, Tuple

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parents[1] / "data" / "traffic_light"
BASE_DIR.mkdir(parents=True, exist_ok=True)


class RoiConfigError(RuntimeError):
    """Raised when ROI or stopline config cannot be loaded or saved."""


def _camera_config_path(camera_id: str) -> Path:
    safe_id = "".join(c for c in camera_id if c.isalnum() or c in {"_", "-"})
    return BASE_DIR / f"{safe_id}.json"


def _load_config(camera_id: str) -> Dict[str, object]:
    path = _camera_config_path(camera_id)
    if not path.exists():
        return {
            "camera_id": camera_id,
            "traffic_light_roi": None,
            "stopline": None,
            "violation_region": None,
            "video_dimensions": None,
        }
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise RoiConfigError("Invalid config format: expected JSON object")
        data.setdefault("camera_id", camera_id)
        data.setdefault("traffic_light_roi", None)
        data.setdefault("stopline", None)
        data.setdefault("violation_region", None)
        data.setdefault("video_dimensions", None)
        return data
    except Exception as exc:  # noqa: BLE001
        logger.exception("Failed to load ROI config for %s", camera_id)
        raise RoiConfigError(str(exc)) from exc


def _save_config(camera_id: str, payload: Dict[str, object]) -> Dict[str, object]:
    path = _camera_config_path(camera_id)
    try:
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return payload
    except Exception as exc:  # noqa: BLE001
        logger.exception("Failed to save ROI config for %s", camera_id)
        raise RoiConfigError(str(exc)) from exc


def save_traffic_light_roi(camera_id: str, roi_norm: Dict[str, float]) -> Dict[str, object]:
    """Persist the normalized traffic light ROI for a camera."""
    cfg = _load_config(camera_id)
    cfg["traffic_light_roi"] = roi_norm
    return _save_config(camera_id, cfg)


def get_traffic_light_roi(camera_id: str) -> Optional[Dict[str, float]]:
    """Return the saved normalized traffic light ROI if present."""
    return _load_config(camera_id).get("traffic_light_roi")


def save_stopline(camera_id: str, stopline_norm: Dict[str, float]) -> Dict[str, object]:
    """Persist the normalized stopline rectangle for a camera."""
    cfg = _load_config(camera_id)
    cfg["stopline"] = stopline_norm
    return _save_config(camera_id, cfg)


def get_stopline(camera_id: str) -> Optional[Dict[str, float]]:
    """Return the saved normalized stopline rectangle if present."""
    return _load_config(camera_id).get("stopline")


def save_violation_region(
    camera_id: str, points: list[tuple[float, float]], video_dimensions: Optional[Dict[str, int]] = None
) -> Dict[str, object]:
    """Persist the violation region polygon for a camera."""
    cfg = _load_config(camera_id)
    cfg["violation_region"] = {"points": points, "video_dimensions": video_dimensions}
    if video_dimensions:
        cfg["video_dimensions"] = video_dimensions
    return _save_config(camera_id, cfg)


def get_violation_region(camera_id: str) -> Optional[Dict[str, object]]:
    """Return the saved violation region if present."""
    return _load_config(camera_id).get("violation_region")


def normalized_rect_to_pixels(rect: Dict[str, float], frame_shape: Tuple[int, int]) -> Tuple[int, int, int, int]:
    """Convert a normalized rectangle into pixel coordinates.

    Args:
        rect: ``{"x": float, "y": float, "width": float, "height": float}``
        frame_shape: (height, width) of the full frame.
    """
    fh, fw = frame_shape
    x = int(rect["x"] * fw)
    y = int(rect["y"] * fh)
    w = int(rect["width"] * fw)
    h = int(rect["height"] * fh)
    return x, y, x + w, y + h


def normalized_stopline_to_pixels(stopline: Dict[str, float], frame_shape: Tuple[int, int]) -> Tuple[int, int, int, int]:
    """Convert a normalized stopline rectangle to pixel bounds."""
    fh, fw = frame_shape
    x1 = int(stopline["x1"] * fw)
    y1 = int(stopline["y1"] * fh)
    x2 = int(stopline["x2"] * fw)
    y2 = int(stopline["y2"] * fh)
    return x1, y1, x2, y2