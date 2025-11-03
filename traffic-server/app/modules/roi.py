from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from sqlmodel import Session, select

from app.modules.base import DetectionModule, ModuleContext
from app.models.roi import ROI
from app.utils.roi_utils import denormalize_polygon_coords, draw_polygon_on_frame

logger = logging.getLogger(__name__)


class ROIModule(DetectionModule):
    """Load and optionally render ROI polygons."""

    def __init__(
        self,
        *,
        session: Session,
        video_job_id: int,
        frame_size: Tuple[int, int],
        enabled: bool = True,
        draw_enabled: bool = True,
        roi_json_path: Optional[str] = None,
    ) -> None:
        super().__init__(name="roi", enabled=enabled)
        self._session = session
        self._video_job_id = video_job_id
        self._frame_size = frame_size
        self.draw_enabled = draw_enabled
        self.roi_json_path = Path(roi_json_path) if roi_json_path else None
        self._rois: Dict[str, List[List[float]]] = {}

    def setup(self, context: ModuleContext) -> None:
        if not self.enabled:
            return
        self._rois = {}
        self._rois.update(self._load_from_db())

        if self.roi_json_path and self.roi_json_path.exists():
            try:
                self._rois.update(self._load_from_json(self.roi_json_path))
                logger.info("Loaded ROI JSON configuration from %s", self.roi_json_path)
            except Exception as exc:  # pragma: no cover - defensive log
                logger.warning("Failed to load ROI JSON %s: %s", self.roi_json_path, exc)
        elif self.roi_json_path:
            logger.warning("ROI JSON path %s does not exist", self.roi_json_path)

        context.rois = self._rois

    def process(self, context: ModuleContext) -> None:
        if not self.enabled:
            context.rois = {}
            return

        context.rois = self._rois

        if not self.draw_enabled or not self._rois:
            return

        annotated = context.ensure_annotated_frame()
        for roi_type, polygon in self._rois.items():
            color = (0, 255, 0)
            if "violation" in roi_type:
                color = (0, 0, 255)
            draw_polygon_on_frame(annotated, polygon, color=color)

    def _load_from_db(self) -> Dict[str, List[List[float]]]:
        rois: Dict[str, List[List[float]]] = {}
        query = select(ROI).where(
            ROI.video_job_id == self._video_job_id,
            ROI.is_active == True,  # noqa: E712 - SQLAlchemy requirement
        )
        results = self._session.exec(query).all()
        height, width = self._frame_size[1], self._frame_size[0]

        for roi in results:
            coords = roi.coordinates
            if roi.is_normalized:
                coords = denormalize_polygon_coords(coords, width, height)
            rois[roi.roi_type] = coords

        return rois

    def _load_from_json(self, path: Path) -> Dict[str, List[List[float]]]:
        data = json.loads(path.read_text(encoding="utf-8"))
        height, width = self._frame_size[1], self._frame_size[0]

        if isinstance(data, dict) and "rois" in data:
            items = data["rois"]
        else:
            items = data

        rois: Dict[str, List[List[float]]] = {}
        if isinstance(items, dict):
            iterator = items.items()
        else:
            iterator = ((item.get("type", f"roi_{idx}"), item) for idx, item in enumerate(items))

        for key, value in iterator:
            if isinstance(value, dict):
                coords = value.get("coordinates") or value.get("points") or []
                normalized = value.get("is_normalized", False)
            else:
                coords = value
                normalized = False

            if not coords:
                continue

            if normalized:
                coords = denormalize_polygon_coords(coords, width, height)

            rois[str(key)] = coords

        return rois

    @property
    def rois(self) -> Dict[str, List[List[float]]]:
        return self._rois
