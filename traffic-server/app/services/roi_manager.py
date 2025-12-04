from __future__ import annotations
from pathlib import Path
from typing import Any, Dict, List, Tuple
import json

from app.core.roi_types import ROI_TYPES, bgr_to_hex


class ROIStorage:
    """File-based ROI storage per camera_id."""

    def __init__(self, base_dir: Path | None = None) -> None:
        if base_dir is None:
            base_dir = Path(__file__).parent.parent / "data" / "rois"
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def path_for(self, camera_id: str) -> Path:
        safe = "".join(c for c in camera_id if c.isalnum() or c in ("_", "-"))
        return self.base_dir / f"{safe}.json"

    def load(self, camera_id: str) -> List[Dict[str, Any]]:
        p = self.path_for(camera_id)
        if not p.exists():
            return []
        try:
            with p.open("r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, list):
                return data
        except Exception:
            pass
        return []

    def save(self, camera_id: str, rois: List[Dict[str, Any]]) -> bool:
        p = self.path_for(camera_id)
        with p.open("w", encoding="utf-8") as f:
            json.dump(rois, f, ensure_ascii=False, indent=2)
        return True


def validate_point(pt: Any) -> bool:
    return (
        isinstance(pt, (list, tuple)) and len(pt) == 2 and
        isinstance(pt[0], (int, float)) and isinstance(pt[1], (int, float))
    )


def validate_roi(roi: Dict[str, Any]) -> Tuple[bool, str]:
    name = roi.get("name")
    typ = roi.get("type")
    pts = roi.get("points")

    if not isinstance(name, str) or not name:
        return False, "Invalid name"
    if not isinstance(typ, str) or typ not in ROI_TYPES:
        return False, f"Invalid type: {typ}"
    if not isinstance(pts, list) or not all(validate_point(p) for p in pts):
        return False, "Invalid points"

    shape = ROI_TYPES[typ]["shape"]
    if shape == "polygon" and len(pts) < 3:
        return False, "Polygon requires >= 3 points"
    if shape == "line" and len(pts) != 2:
        return False, "Line requires exactly 2 points"
    if shape == "rect" and len(pts) != 4:
        return False, "Rect must be provided as 4 points"

    # color optional; normalize to hex if present
    col = roi.get("color")
    if col is not None and not isinstance(col, str):
        return False, "Color must be hex string if provided"

    return True, "ok"


def validate_rois(rois: List[Dict[str, Any]]) -> Tuple[bool, str]:
    if not isinstance(rois, list):
        return False, "Body must be a list of ROIs"
    names = set()
    for r in rois:
        ok, msg = validate_roi(r)
        if not ok:
            return False, msg
        nm = r.get("name")
        if nm in names:
            return False, f"Duplicate ROI name: {nm}"
        names.add(nm)
    return True, "ok"
