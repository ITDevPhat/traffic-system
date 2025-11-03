from __future__ import annotations

from typing import Any, Dict, List, Optional

from ultralytics.engine.results import Results

from app.modules.base import DetectionModule, ModuleContext


class VehicleYOLOModule(DetectionModule):
    """YOLO-based vehicle detection with optional ByteTrack tracking."""

    def __init__(
        self,
        models: Any,
        *,
        enabled: bool = True,
        use_tracking: bool = True,
        confidence: float = 0.5,
        device: str = "cpu",
    ) -> None:
        super().__init__(name="vehicle_yolo", enabled=enabled)
        self._models = models
        self.use_tracking = use_tracking
        self.confidence = confidence
        self.device = device
        self._id_counter = 0

    def _next_track_id(self) -> int:
        self._id_counter += 1
        return self._id_counter

    def _run_inference(self, frame) -> List[Results]:
        if self._models is None or getattr(self._models, "vehicle", None) is None:
            return []

        vehicle_model = self._models.vehicle
        if self.use_tracking:
            return vehicle_model.track(
                frame,
                conf=self.confidence,
                device=self.device,
                persist=True,
                verbose=False,
            )
        return vehicle_model.predict(
            frame,
            conf=self.confidence,
            device=self.device,
            verbose=False,
        )

    def process(self, context: ModuleContext) -> None:
        if not self.enabled:
            context.tracks = []
            return

        results = self._run_inference(context.frame)
        if not results:
            context.tracks = []
            return

        boxes = results[0].boxes if results[0].boxes is not None else []
        tracks: List[Dict[str, Any]] = []

        for box in boxes:
            xyxy = box.xyxy[0].tolist()
            x1, y1, x2, y2 = map(int, xyxy)
            conf = float(box.conf[0])
            cls_id = int(box.cls[0]) if box.cls is not None else 0
            cls_name = (
                self._models.vehicle.names[cls_id]
                if self._models is not None and getattr(self._models.vehicle, "names", None)
                else "vehicle"
            )

            track_id: Optional[int]
            if self.use_tracking and box.id is not None:
                track_id = int(box.id[0])
            else:
                track_id = self._next_track_id()

            tracks.append(
                {
                    "bbox": (x1, y1, x2, y2),
                    "confidence": conf,
                    "class": cls_name,
                    "track_id": track_id if track_id is not None else -1,
                }
            )

        context.tracks = tracks
