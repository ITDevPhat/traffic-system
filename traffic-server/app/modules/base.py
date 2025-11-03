from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

import numpy as np


@dataclass
class ModuleContext:
    """Shared mutable state that flows through detection modules."""

    frame: np.ndarray
    frame_idx: int
    frame_size: Tuple[int, int]
    rois: Dict[str, List[List[float]]] = field(default_factory=dict)
    tracks: List[Dict[str, Any]] = field(default_factory=list)
    annotated_frame: Optional[np.ndarray] = None
    violating_track_ids: Set[int] = field(default_factory=set)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def ensure_annotated_frame(self) -> np.ndarray:
        """Return a drawable frame, cloning the original if needed."""
        if self.annotated_frame is None:
            self.annotated_frame = self.frame.copy()
        return self.annotated_frame


class DetectionModule(ABC):
    """Base class for pluggable detection modules."""

    def __init__(self, name: str, enabled: bool = True) -> None:
        self.name = name
        self.enabled = enabled

    def setup(self, context: ModuleContext) -> None:
        """One-time initialization hook executed before frame loop."""

    @abstractmethod
    def process(self, context: ModuleContext) -> None:
        """Handle per-frame processing."""
        raise NotImplementedError


class ModuleManager:
    """Utility to orchestrate a list of modules with optional stages."""

    def __init__(self, modules: List[DetectionModule]) -> None:
        self.modules = modules

    def setup(self, context: ModuleContext) -> None:
        for module in self.modules:
            if module.enabled:
                module.setup(context)

    def run(self, context: ModuleContext) -> None:
        for module in self.modules:
            if module.enabled:
                module.process(context)
