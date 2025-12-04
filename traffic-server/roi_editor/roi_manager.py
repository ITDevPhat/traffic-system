import json
from typing import List, Dict, Any
from pathlib import Path

from .roi_types import ROI_TYPES, bgr_to_hex


class ROIManager:
    def __init__(self):
        self.rois: List[Dict[str, Any]] = []

    def clear(self):
        self.rois.clear()

    def add_roi(self, roi: Dict[str, Any]):
        # Normalize fields
        r = dict(roi)
        # Ensure color hex
        color = r.get("color")
        if isinstance(color, (tuple, list)) and len(color) == 3:
            r["color"] = bgr_to_hex(tuple(color))
        # Normalize type
        t = r.get("type")
        if t not in ROI_TYPES:
            # Allow semantic names mapping, else store as is
            pass
        self.rois.append(r)

    def delete_roi_by_name(self, name: str) -> bool:
        n = len(self.rois)
        self.rois = [r for r in self.rois if r.get("name") != name]
        return len(self.rois) != n

    def update_roi(self, name: str, updates: Dict[str, Any]) -> bool:
        for r in self.rois:
            if r.get("name") == name:
                r.update(updates)
                return True
        return False

    def load(self, path: str) -> bool:
        p = Path(path)
        if not p.exists():
            return False
        with p.open("r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, list):
            return False
        self.rois = data
        return True

    def save(self, path: str) -> bool:
        p = Path(path)
        with p.open("w", encoding="utf-8") as f:
            json.dump(self.rois, f, ensure_ascii=False, indent=2)
        return True

    def to_list(self) -> List[Dict[str, Any]]:
        return list(self.rois)
