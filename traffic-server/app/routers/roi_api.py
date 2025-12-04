from __future__ import annotations
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field, validator
from typing import Any, Dict, List, Literal, Optional, Tuple
from pathlib import Path
import json
import logging

from app.core.config import settings

router = APIRouter(prefix=f"{settings.API_V1_PREFIX}/roi", tags=["ROI"])

log = logging.getLogger(__name__)
ROI_DIR = Path(__file__).resolve().parents[1] / "data" / "rois"
ROI_DIR.mkdir(parents=True, exist_ok=True)

RoiType = Literal[
    "detection_zone", "lane_car", "lane_bike", "direction_zone",
    "stopline", "forbidden_area", "crosswalk", "traffic_light"
]


class RoiItem(BaseModel):
    name: str = Field(..., min_length=1, max_length=64, description="Unique name in a camera scope")
    type: RoiType
    points: List[Tuple[float, float]] = Field(..., description="List of (x, y) pixel coordinates")
    color: str = Field("#00FFFF", description="Hex color #RRGGBB")
    allowed_classes: Optional[List[str]] = None
    allowed_heading: Optional[Tuple[float, float]] = None  # degrees [min, max]
    related_light: Optional[str] = None  # for stopline -> traffic_light name

    @validator("color")
    def valid_hex(cls, v):
        if not isinstance(v, str) or len(v) != 7 or not v.startswith("#"):
            raise ValueError("color must be #RRGGBB")
        return v.upper()

    @validator("points")
    def points_shape(cls, v, values):
        t = values.get("type")
        if t == "stopline" and len(v) != 2:
            raise ValueError("stopline requires exactly 2 points")
        if t == "traffic_light" and len(v) not in (2, 4):
            # 2 points (x1,y1,x2,y2) rectangle corners; 4 points polygon clockwise
            raise ValueError("traffic_light must have 2 or 4 points")
        if t not in ("stopline", "traffic_light") and len(v) < 3:
            raise ValueError(f"{t} requires >=3 points")
        return v


class RoiPayload(BaseModel):
    camera_id: str = Field(..., min_length=1)
    items: List[RoiItem] = Field(default_factory=list)


def roi_path(camera_id: str) -> Path:
    safe = "".join(c for c in camera_id if c.isalnum() or c in ("_", "-"))
    return ROI_DIR / f"{safe}.json"


@router.get("", response_model=RoiPayload)
def get_rois(camera_id: str = Query(..., description="Camera ID")):
    p = roi_path(camera_id)
    if not p.exists():
        return RoiPayload(camera_id=camera_id, items=[])
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        # Backward-compat: accept either list or payload
        if isinstance(data, list):
            return RoiPayload(camera_id=camera_id, items=data)
        return RoiPayload(**data)
    except Exception as e:
        log.exception("Failed to read ROI JSON")
        raise HTTPException(500, f"Failed to read ROI JSON: {e}")


@router.post("", response_model=RoiPayload)
def save_rois(payload: RoiPayload):
    # Validate unique names within camera
    names = [i.name for i in payload.items]
    if len(names) != len(set(names)):
        raise HTTPException(400, "ROI names must be unique within the same camera")

    # Additional sanity checks: coords >=0
    for item in payload.items:
        for x, y in item.points:
            if x < 0 or y < 0:
                raise HTTPException(400, "Point coordinates must be >= 0")

    p = roi_path(payload.camera_id)
    try:
        p.write_text(payload.model_dump_json(indent=2, ensure_ascii=False), encoding="utf-8")
        log.info("Saved ROI file: %s (%d items)", p, len(payload.items))
        return payload
    except Exception as e:
        log.exception("Failed to save ROI JSON")
        raise HTTPException(500, f"Failed to save ROI JSON: {e}")


@router.get("/types")
def get_roi_types():
    # Default palette & shape hints for frontend
    return {
        "types": [
            {"type": "detection_zone", "color": "#00FFFF", "shape": "polygon"},
            {"type": "lane_car",       "color": "#00FF00", "shape": "polygon"},
            {"type": "lane_bike",      "color": "#0066FF", "shape": "polygon"},
            {"type": "direction_zone", "color": "#FFA500", "shape": "polygon"},
            {"type": "stopline",       "color": "#FF0000", "shape": "line"},
            {"type": "forbidden_area", "color": "#800080", "shape": "polygon"},
            {"type": "crosswalk",      "color": "#FFFF00", "shape": "polygon"},
            {"type": "traffic_light",  "color": "#FFFFFF", "shape": "rect_or_polygon"}
        ]
    }
