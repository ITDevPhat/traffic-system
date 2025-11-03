from __future__ import annotations

from typing import Tuple

import cv2

from app.modules.base import DetectionModule, ModuleContext


class BoundingBoxDrawerModule(DetectionModule):
    """Render bounding boxes for tracks with optional violation highlighting."""

    def __init__(
        self,
        *,
        enabled: bool = True,
        normal_color: Tuple[int, int, int] = (0, 255, 0),
        violation_color: Tuple[int, int, int] = (0, 0, 255),
        thickness: int = 2,
    ) -> None:
        super().__init__(name="bbox_drawer", enabled=enabled)
        self.normal_color = normal_color
        self.violation_color = violation_color
        self.thickness = thickness

    def process(self, context: ModuleContext) -> None:
        if not self.enabled or not context.tracks:
            return

        annotated = context.ensure_annotated_frame()
        for track in context.tracks:
            x1, y1, x2, y2 = track["bbox"]
            track_id = track.get("track_id", -1)
            color = (
                self.violation_color
                if track_id in context.violating_track_ids
                else self.normal_color
            )
            cv2.rectangle(annotated, (x1, y1), (x2, y2), color, self.thickness)
            label = f"ID:{track_id}" if track_id != -1 else track.get("class", "veh")
            cv2.putText(
                annotated,
                label,
                (x1, max(0, y1 - 10)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                color,
                2,
            )
