"""
Traffic Light Worker Manager

Manages lifecycle of traffic light detection workers.
Enforces worker limits and handles cleanup.

Author: Traffic System Team
Version: 1.0.0
"""
import asyncio
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Tuple, List

import numpy as np

from app.services.traffic_light_worker import TrafficLightWorker
from app.utils.timezone_utils import now_vietnam

logger = logging.getLogger(__name__)


class TrafficLightFrameBuffer:
    """Lightweight frame buffer for traffic light workers.

    Stores the latest frame + tracks per camera so that dedicated TL workers
    (and debugging utilities) can fetch a consistent view without coupling
    tightly to the realtime stream threads.
    """

    def __init__(self):
        self.frames: Dict[str, Dict[str, object]] = {}
        self.state: Dict[str, str] = {}

    def update_frame(
        self,
        camera_id: str,
        frame: np.ndarray,
        tracks: List[Dict[str, object]],
        frame_index: int,
    ) -> None:
        self.frames[camera_id] = {
            "frame": frame,
            "tracks": tracks,
            "frame_index": frame_index,
        }

    def get_latest(self, camera_id: str) -> Optional[Dict[str, object]]:
        return self.frames.get(camera_id)

    def set_state(self, camera_id: str, state: str) -> None:
        self.state[camera_id] = state

    def clear(self, camera_id: str) -> None:
        self.frames.pop(camera_id, None)
        self.state.pop(camera_id, None)


class TrafficLightStateMachine:
    """Finite-state machine that outputs only GREEN/YELLOW/RED."""

    def __init__(self) -> None:
        self.effective_state: str = "GREEN"
        self.raw_state: Optional[str] = None
        self.last_raw_state: Optional[str] = None
        self.green_streak: int = 0
        self.yellow_started_at: Optional[datetime] = None
        self.red_started_at: Optional[datetime] = None

    def update(self, raw_state: Optional[str], timestamp: datetime) -> str:
        """Update FSM with the latest raw detection and return effective state."""
        prev = self.effective_state or "GREEN"

        # Hold current state if detector is unsure
        if raw_state is None:
            return prev

        self.raw_state = raw_state
        self.last_raw_state = raw_state

        # GREEN branch
        if prev == "GREEN":
            if raw_state == "YELLOW":
                self.effective_state = "YELLOW"
                self.yellow_started_at = timestamp
                self.green_streak = 0
            elif raw_state == "RED":
                # Allow direct GREEN -> RED observations to enter YELLOW first
                self.effective_state = "YELLOW"
                self.yellow_started_at = timestamp
                self.green_streak = 0
            else:
                self.effective_state = "GREEN"

            return self.effective_state

        # YELLOW branch
        if prev == "YELLOW":
            if raw_state == "RED":
                self.effective_state = "RED"
                self.red_started_at = timestamp
                self.green_streak = 0
            elif raw_state == "GREEN":
                self.effective_state = "GREEN"
                self.green_streak = 0
            else:
                # raw_state == "YELLOW" keeps us here; UNKNOWN handled above
                self.effective_state = "YELLOW"
            return self.effective_state

        # RED branch
        if prev == "RED":
            if raw_state == "GREEN":
                self.green_streak += 1
                if self.green_streak >= 2:
                    self.effective_state = "GREEN"
                    self.green_streak = 0
            else:
                # Stay RED until GREEN stabilises again
                self.green_streak = 0
                self.effective_state = "RED"
            return self.effective_state

        # Fallback (should not happen)
        self.effective_state = prev
        return self.effective_state

    def clear(self) -> None:
        self.effective_state = "GREEN"
        self.raw_state = None
        self.last_raw_state = None
        self.green_streak = 0
        

class TrafficLightManager:
    """Per-camera ROI + state smoothing helper."""

    def __init__(self):
        self.roi_by_camera: Dict[str, Dict[str, float]] = {}
        self.state_machines: Dict[str, TrafficLightStateMachine] = {}

    def load_roi_from_config(self, camera_id: str) -> Optional[Dict[str, float]]:
        config_path = Path(__file__).parent.parent / "data" / "traffic_light" / f"{camera_id}.json"
        if not config_path.exists():
            return None

        try:
            import json

            with config_path.open("r", encoding="utf-8") as f:
                cfg = json.load(f)
            roi = cfg.get("traffic_light_roi")
            if roi:
                self.set_roi(camera_id, roi)
                logger.info(f"[ROI] Loaded ROI for {camera_id} from {config_path}")
            return roi
        except Exception:
            logger.exception(f"Failed to load ROI config for {camera_id}")
            return None

    def set_roi(self, camera_id: str, roi_norm: Dict[str, float]) -> None:
        self.roi_by_camera[camera_id] = roi_norm
        logger.info(f"[ROI] Set ROI for {camera_id}: {roi_norm}")

    def get_roi(self, camera_id: str) -> Optional[Dict[str, float]]:
        return self.roi_by_camera.get(camera_id)

    def clear_roi(self, camera_id: str) -> None:
        if camera_id in self.roi_by_camera:
            del self.roi_by_camera[camera_id]
        if camera_id in self.state_machines:
            self.state_machines[camera_id].clear()
        logger.info(f"[ROI] Cleared ROI and smoothing cache for {camera_id}")

    def roi_to_pixels(self, camera_id: str, frame_shape: Tuple[int, int]) -> Optional[Tuple[int, int, int, int]]:
        roi = self.get_roi(camera_id)
        if not roi:
            return None

        h, w = frame_shape[:2]
        x1 = int(roi.get("x", 0.0) * w)
        y1 = int(roi.get("y", 0.0) * h)
        x2 = int((roi.get("x", 0.0) + roi.get("width", 0.0)) * w)
        y2 = int((roi.get("y", 0.0) + roi.get("height", 0.0)) * h)

        x1 = max(0, min(x1, w - 1))
        y1 = max(0, min(y1, h - 1))
        x2 = max(x1 + 1, min(x2, w))
        y2 = max(y1 + 1, min(y2, h))
        return x1, y1, x2, y2

    def stabilize_state(
        self, camera_id: str, raw_state: Optional[str], confidence: float, timestamp: Optional[datetime] = None
    ) -> Tuple[str, float]:
        """Apply FSM smoothing and return effective state with passthrough confidence."""
        machine = self.state_machines.setdefault(camera_id, TrafficLightStateMachine())
        effective_state = machine.update(raw_state, timestamp or now_vietnam())
        return effective_state, confidence


traffic_light_manager = TrafficLightManager()
frame_buffer = TrafficLightFrameBuffer()


class TrafficLightWorkerManager:
    """
    Manages traffic light detection workers.
    
    Features:
    - Create and start workers
    - Retrieve active workers
    - Stop and cleanup workers
    - Enforce worker limits (max 1 per camera)
    - WebSocket disconnect cleanup with timeout
    - Cleanup all workers on shutdown
    """
    
    def __init__(self):
        """Initialize worker manager"""
        self.workers: Dict[str, TrafficLightWorker] = {}
        self.max_workers_per_camera = 1
        self.disconnect_cleanup_tasks: Dict[str, asyncio.Task] = {}
        self.disconnect_timeout = 5.0  # seconds
        logger.info("TrafficLightWorkerManager initialized")
    
    async def create_worker(
        self,
        camera_id: str,
        roi: dict,
        video_stream,
        model=None
    ) -> TrafficLightWorker:
        """
        Create and start a new traffic light worker.
        
        If a worker already exists for the camera, it will be stopped first.
        This enforces the max 1 worker per camera limit.
        
        Args:
            camera_id: Camera identifier
            roi: ROI configuration
            video_stream: Video stream manager
            model: Optional YOLO model (will be loaded if None)
            
        Returns:
            Created and started TrafficLightWorker instance
            
        Raises:
            Exception: If worker creation or startup fails
        """
        try:
            # Stop existing worker if any (enforce max 1 per camera)
            if camera_id in self.workers:
                logger.info(f"Stopping existing worker for camera {camera_id}")
                await self.stop_worker(camera_id)
            
            # Create new worker
            worker = TrafficLightWorker(
                camera_id=camera_id,
                roi=roi,
                video_stream=video_stream,
                model=model
            )
            
            # Start worker
            await worker.start()
            
            # Register worker
            self.workers[camera_id] = worker
            
            logger.info(
                f"Created TL worker for camera: {camera_id} "
                f"(total workers: {len(self.workers)})"
            )
            
            return worker
            
        except Exception as e:
            logger.error(f"Failed to create worker for camera {camera_id}: {e}", exc_info=True)
            raise
    
    def get_worker(self, camera_id: str) -> Optional[TrafficLightWorker]:
        """
        Get active worker for camera.
        
        Args:
            camera_id: Camera identifier
            
        Returns:
            TrafficLightWorker instance if exists, None otherwise
        """
        return self.workers.get(camera_id)
    
    async def stop_worker(self, camera_id: str):
        """
        Stop and remove worker for camera.
        
        Args:
            camera_id: Camera identifier
            
        Raises:
            KeyError: If no worker exists for camera_id
        """
        worker = self.workers.pop(camera_id, None)
        
        if worker is None:
            raise KeyError(f"No worker found for camera: {camera_id}")
        
        try:
            await worker.stop()
            logger.info(
                f"Stopped TL worker for camera: {camera_id} "
                f"(remaining workers: {len(self.workers)})"
            )
        except Exception as e:
            logger.error(f"Error stopping worker for camera {camera_id}: {e}", exc_info=True)
            # Re-raise to propagate error
            raise
    
    async def cleanup_all(self):
        """
        Stop all workers and cleanup resources.
        
        This should be called on application shutdown.
        """
        logger.info(f"Cleaning up all TL workers ({len(self.workers)} active)...")
        
        # Get list of camera IDs to avoid modifying dict during iteration
        camera_ids = list(self.workers.keys())
        
        for camera_id in camera_ids:
            try:
                await self.stop_worker(camera_id)
            except Exception as e:
                logger.error(f"Error cleaning up worker for camera {camera_id}: {e}")
                # Continue cleanup even if one fails
        
        logger.info("All TL workers cleaned up")
    
    def get_active_worker_count(self) -> int:
        """
        Get number of active workers.
        
        Returns:
            Number of active workers
        """
        return len(self.workers)
    
    def get_active_cameras(self) -> list[str]:
        """
        Get list of camera IDs with active workers.
        
        Returns:
            List of camera IDs
        """
        return list(self.workers.keys())
    
    async def _cleanup_worker_after_timeout(self, camera_id: str):
        """
        Cleanup worker after timeout if no new connections.
        
        This is called when a WebSocket disconnects. If no new connection
        is established within the timeout period, the worker is stopped.
        
        Args:
            camera_id: Camera identifier
        """
        try:
            logger.info(
                f"WebSocket disconnected for camera {camera_id}, "
                f"will cleanup worker in {self.disconnect_timeout}s if no reconnection"
            )
            
            # Wait for timeout
            await asyncio.sleep(self.disconnect_timeout)
            
            # Check if worker still exists and has no subscribers
            worker = self.get_worker(camera_id)
            if worker and len(worker.subscribers) == 0:
                logger.info(
                    f"No reconnection within {self.disconnect_timeout}s for camera {camera_id}, "
                    "stopping worker"
                )
                await self.stop_worker(camera_id)
            else:
                logger.info(
                    f"Worker for camera {camera_id} has active subscribers, "
                    "skipping cleanup"
                )
                
        except KeyError:
            # Worker already stopped by another process
            logger.debug(f"Worker for camera {camera_id} already stopped")
        except Exception as e:
            logger.error(
                f"Error in cleanup timeout for camera {camera_id}: {e}",
                exc_info=True
            )
        finally:
            # Remove cleanup task from tracking
            if camera_id in self.disconnect_cleanup_tasks:
                del self.disconnect_cleanup_tasks[camera_id]
    
    def schedule_disconnect_cleanup(self, camera_id: str):
        """
        Schedule worker cleanup after WebSocket disconnect.
        
        If a cleanup is already scheduled, it will be cancelled and rescheduled.
        This allows for reconnection grace period.
        
        Args:
            camera_id: Camera identifier
        """
        # Cancel existing cleanup task if any
        if camera_id in self.disconnect_cleanup_tasks:
            existing_task = self.disconnect_cleanup_tasks[camera_id]
            if not existing_task.done():
                existing_task.cancel()
                logger.debug(f"Cancelled existing cleanup task for camera {camera_id}")
        
        # Schedule new cleanup task
        task = asyncio.create_task(self._cleanup_worker_after_timeout(camera_id))
        self.disconnect_cleanup_tasks[camera_id] = task
        
        logger.debug(f"Scheduled disconnect cleanup for camera {camera_id}")
    
    def cancel_disconnect_cleanup(self, camera_id: str):
        """
        Cancel scheduled disconnect cleanup.
        
        This should be called when a new WebSocket connection is established,
        to prevent the worker from being stopped.
        
        Args:
            camera_id: Camera identifier
        """
        if camera_id in self.disconnect_cleanup_tasks:
            task = self.disconnect_cleanup_tasks[camera_id]
            if not task.done():
                task.cancel()
                logger.info(f"Cancelled disconnect cleanup for camera {camera_id} (reconnected)")
            del self.disconnect_cleanup_tasks[camera_id]


# Global worker manager instance
worker_manager = TrafficLightWorkerManager()