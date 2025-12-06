"""
Traffic Light Manager - Shared Frame Buffer & Worker Lifecycle

Manages:
1. Shared frame buffer between main pipeline and TL worker
2. Traffic light worker lifecycle (start/pause/resume/stop)
3. Per-camera state synchronization

Architecture:
- Pipeline A (main) publishes frames + tracks to shared buffer
- Pipeline B (TL) consumes from shared buffer, runs TL detection
- Both pipelines share the same state machine (STOPPED/RUNNING/PAUSED)

Author: Traffic System Team
Version: 2.0.0
"""
import asyncio
import logging
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class SharedFrameData:
    """Shared frame data between main pipeline and TL worker"""
    frame: Optional[np.ndarray] = None
    tracks: List[Dict[str, Any]] = field(default_factory=list)
    frame_index: int = 0
    timestamp: float = 0.0
    frame_width: int = 0
    frame_height: int = 0


@dataclass
class CameraState:
    """Per-camera state for TL pipeline synchronization"""
    # Shared frame buffer
    frame_data: SharedFrameData = field(default_factory=SharedFrameData)
    frame_lock: threading.Lock = field(default_factory=threading.Lock)
    
    # State machine: STOPPED | RUNNING | PAUSED
    state: str = "STOPPED"
    state_lock: threading.Lock = field(default_factory=threading.Lock)
    
    # Frame update event (signals new frame available)
    frame_event: threading.Event = field(default_factory=threading.Event)
    
    # Last update timestamp
    last_update: float = 0.0


class TrafficLightFrameBuffer:
    """
    Thread-safe shared frame buffer for traffic light pipeline.
    
    Main pipeline (Pipeline A) publishes frames here.
    TL worker (Pipeline B) consumes frames from here.
    """
    
    def __init__(self):
        self._cameras: Dict[str, CameraState] = {}
        self._global_lock = threading.Lock()
        logger.info("🚦 TrafficLightFrameBuffer initialized")
    
    def _ensure_camera(self, camera_id: str) -> CameraState:
        """Ensure camera state exists"""
        with self._global_lock:
            if camera_id not in self._cameras:
                self._cameras[camera_id] = CameraState()
                logger.info(f"📷 Created camera state for: {camera_id}")
            return self._cameras[camera_id]
    
    def update_frame(
        self,
        camera_id: str,
        frame: np.ndarray,
        tracks: List[Dict[str, Any]],
        frame_index: int = 0
    ) -> None:
        """
        Publish new frame + tracks from main pipeline.
        
        Called by Pipeline A (realtime_binary_stream) after YOLO+ByteTrack inference.
        
        Args:
            camera_id: Camera identifier
            frame: Current BGR frame
            tracks: List of track dicts with {track_id, bbox, class_id, confidence}
            frame_index: Current frame index
        """
        camera = self._ensure_camera(camera_id)
        
        with camera.frame_lock:
            camera.frame_data.frame = frame.copy() if frame is not None else None
            camera.frame_data.tracks = tracks.copy() if tracks else []
            camera.frame_data.frame_index = frame_index
            camera.frame_data.timestamp = time.time()
            if frame is not None:
                camera.frame_data.frame_height, camera.frame_data.frame_width = frame.shape[:2]
            camera.last_update = time.time()
        
        # Signal new frame available
        camera.frame_event.set()
    
    def get_frame(
        self,
        camera_id: str,
        timeout: float = 0.5
    ) -> Tuple[Optional[np.ndarray], List[Dict[str, Any]], int]:
        """
        Get latest frame + tracks for TL worker.
        
        Called by Pipeline B (traffic_light_worker) to consume frames.
        
        Args:
            camera_id: Camera identifier
            timeout: Max wait time for new frame
            
        Returns:
            (frame, tracks, frame_index) or (None, [], 0) if no frame
        """
        camera = self._ensure_camera(camera_id)
        
        # Wait for new frame with timeout
        if not camera.frame_event.wait(timeout=timeout):
            return None, [], 0
        
        # Clear event after consuming
        camera.frame_event.clear()
        
        with camera.frame_lock:
            frame = camera.frame_data.frame.copy() if camera.frame_data.frame is not None else None
            tracks = camera.frame_data.tracks.copy()
            frame_index = camera.frame_data.frame_index
        
        return frame, tracks, frame_index
    
    def get_frame_nowait(
        self,
        camera_id: str
    ) -> Tuple[Optional[np.ndarray], List[Dict[str, Any]], int]:
        """
        Get latest frame without waiting (non-blocking).
        
        Returns:
            (frame, tracks, frame_index) or (None, [], 0) if no frame
        """
        camera = self._ensure_camera(camera_id)
        
        with camera.frame_lock:
            frame = camera.frame_data.frame.copy() if camera.frame_data.frame is not None else None
            tracks = camera.frame_data.tracks.copy()
            frame_index = camera.frame_data.frame_index
        
        return frame, tracks, frame_index
    
    def get_frame_dimensions(self, camera_id: str) -> Tuple[int, int]:
        """Get frame dimensions for camera"""
        camera = self._ensure_camera(camera_id)
        with camera.frame_lock:
            return camera.frame_data.frame_width, camera.frame_data.frame_height
    
    def set_state(self, camera_id: str, state: str) -> None:
        """
        Set pipeline state for camera.
        
        Args:
            camera_id: Camera identifier
            state: One of STOPPED, RUNNING, PAUSED
        """
        camera = self._ensure_camera(camera_id)
        with camera.state_lock:
            old_state = camera.state
            camera.state = state
            logger.info(f"🔄 Camera {camera_id} state: {old_state} → {state}")
    
    def get_state(self, camera_id: str) -> str:
        """Get current pipeline state for camera"""
        camera = self._ensure_camera(camera_id)
        with camera.state_lock:
            return camera.state
    
    def is_running(self, camera_id: str) -> bool:
        """Check if pipeline is running (not paused or stopped)"""
        return self.get_state(camera_id) == "RUNNING"
    
    def is_paused(self, camera_id: str) -> bool:
        """Check if pipeline is paused"""
        return self.get_state(camera_id) == "PAUSED"
    
    def cleanup_camera(self, camera_id: str) -> None:
        """Cleanup camera state"""
        with self._global_lock:
            if camera_id in self._cameras:
                del self._cameras[camera_id]
                logger.info(f"🧹 Cleaned up camera state: {camera_id}")


# Global shared frame buffer instance
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
    - State synchronization with main pipeline
    """
    
    def __init__(self):
        """Initialize worker manager"""
        self.workers: Dict[str, Any] = {}  # camera_id -> TrafficLightWorker
        self.max_workers_per_camera = 1
        self.disconnect_cleanup_tasks: Dict[str, asyncio.Task] = {}
        self.disconnect_timeout = 5.0  # seconds
        logger.info("TrafficLightWorkerManager initialized")
    
    async def create_worker(
        self,
        camera_id: str,
        tl_roi: Optional[dict] = None,
        stopline_roi: Optional[dict] = None,
    ) -> Any:
        """
        Create and start a new traffic light worker.
        
        If a worker already exists for the camera, it will be stopped first.
        This enforces the max 1 worker per camera limit.
        
        Args:
            camera_id: Camera identifier
            tl_roi: Traffic light ROI (normalized coordinates)
            stopline_roi: Stopline ROI (normalized coordinates)
            
        Returns:
            Created and started TrafficLightWorker instance
        """
        from app.services.traffic_light_worker import TrafficLightWorker
        from app.config.roi_config import get_traffic_light_roi, get_stopline
        
        try:
            # Stop existing worker if any (enforce max 1 per camera)
            if camera_id in self.workers:
                logger.info(f"Stopping existing worker for camera {camera_id}")
                await self.stop_worker(camera_id)
            
            # Load ROI from config if not provided
            if tl_roi is None:
                tl_roi = get_traffic_light_roi(camera_id)
                if tl_roi:
                    logger.info(f"📦 Loaded TL ROI from config: {tl_roi}")
            
            if stopline_roi is None:
                stopline_roi = get_stopline(camera_id)
                if stopline_roi:
                    logger.info(f"📦 Loaded stopline from config: {stopline_roi}")
            
            # Validate ROI
            if not tl_roi:
                logger.warning(f"⚠️ No TL ROI configured for camera {camera_id}")
            
            # Create new worker (frame consumer mode)
            worker = TrafficLightWorker(
                camera_id=camera_id,
                tl_roi=tl_roi,
                stopline_roi=stopline_roi,
            )
            
            # Start worker
            worker.start()
            
            # Register worker
            self.workers[camera_id] = worker
            
            # Set pipeline state to RUNNING
            frame_buffer.set_state(camera_id, "RUNNING")
            
            logger.info(
                f"✅ Created TL worker for camera: {camera_id} "
                f"(total workers: {len(self.workers)})"
            )
            
            return worker
            
        except Exception as e:
            logger.error(f"Failed to create worker for camera {camera_id}: {e}", exc_info=True)
            raise
    
    def get_worker(self, camera_id: str) -> Optional[Any]:
        """Get active worker for camera"""
        return self.workers.get(camera_id)
    
    async def stop_worker(self, camera_id: str) -> None:
        """Stop and remove worker for camera"""
        worker = self.workers.pop(camera_id, None)
        
        if worker is None:
            logger.warning(f"No worker found for camera: {camera_id}")
            return
        
        try:
            worker.stop()
            frame_buffer.set_state(camera_id, "STOPPED")
            logger.info(
                f"Stopped TL worker for camera: {camera_id} "
                f"(remaining workers: {len(self.workers)})"
            )
        except Exception as e:
            logger.error(f"Error stopping worker for camera {camera_id}: {e}", exc_info=True)
            raise
    
    def pause_worker(self, camera_id: str) -> None:
        """Pause worker for camera"""
        worker = self.workers.get(camera_id)
        if worker:
            worker.pause()
            frame_buffer.set_state(camera_id, "PAUSED")
            logger.info(f"⏸️ Paused TL worker for camera: {camera_id}")
    
    def resume_worker(self, camera_id: str) -> None:
        """Resume worker for camera"""
        worker = self.workers.get(camera_id)
        if worker:
            worker.resume()
            frame_buffer.set_state(camera_id, "RUNNING")
            logger.info(f"▶️ Resumed TL worker for camera: {camera_id}")
    
    async def cleanup_all(self) -> None:
        """Stop all workers and cleanup resources"""
        logger.info(f"Cleaning up all TL workers ({len(self.workers)} active)...")
        
        camera_ids = list(self.workers.keys())
        
        for camera_id in camera_ids:
            try:
                await self.stop_worker(camera_id)
            except Exception as e:
                logger.error(f"Error cleaning up worker for camera {camera_id}: {e}")
        
        logger.info("All TL workers cleaned up")
    
    def get_active_worker_count(self) -> int:
        """Get number of active workers"""
        return len(self.workers)
    
    def get_active_cameras(self) -> List[str]:
        """Get list of camera IDs with active workers"""
        return list(self.workers.keys())
    
    async def _cleanup_worker_after_timeout(self, camera_id: str) -> None:
        """Cleanup worker after timeout if no new connections"""
        try:
            logger.info(
                f"WebSocket disconnected for camera {camera_id}, "
                f"will cleanup worker in {self.disconnect_timeout}s if no reconnection"
            )
            
            await asyncio.sleep(self.disconnect_timeout)
            
            worker = self.get_worker(camera_id)
            if worker:
                logger.info(
                    f"No reconnection within {self.disconnect_timeout}s for camera {camera_id}, "
                    "stopping worker"
                )
                await self.stop_worker(camera_id)
                
        except Exception as e:
            logger.error(
                f"Error in cleanup timeout for camera {camera_id}: {e}",
                exc_info=True
            )
        finally:
            if camera_id in self.disconnect_cleanup_tasks:
                del self.disconnect_cleanup_tasks[camera_id]
    
    def schedule_disconnect_cleanup(self, camera_id: str) -> None:
        """Schedule worker cleanup after WebSocket disconnect"""
        if camera_id in self.disconnect_cleanup_tasks:
            existing_task = self.disconnect_cleanup_tasks[camera_id]
            if not existing_task.done():
                existing_task.cancel()
                logger.debug(f"Cancelled existing cleanup task for camera {camera_id}")
        
        task = asyncio.create_task(self._cleanup_worker_after_timeout(camera_id))
        self.disconnect_cleanup_tasks[camera_id] = task
        
        logger.debug(f"Scheduled disconnect cleanup for camera {camera_id}")
    
    def cancel_disconnect_cleanup(self, camera_id: str) -> None:
        """Cancel scheduled disconnect cleanup"""
        if camera_id in self.disconnect_cleanup_tasks:
            task = self.disconnect_cleanup_tasks[camera_id]
            if not task.done():
                task.cancel()
                logger.info(f"Cancelled disconnect cleanup for camera {camera_id} (reconnected)")
            del self.disconnect_cleanup_tasks[camera_id]


# Global worker manager instance
worker_manager = TrafficLightWorkerManager()
