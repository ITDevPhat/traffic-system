"""
Traffic Light Worker Manager

Manages lifecycle of traffic light detection workers.
Enforces worker limits and handles cleanup.

Author: Traffic System Team
Version: 1.0.0
"""
import asyncio
import logging
from typing import Optional, Dict
from app.services.traffic_light_worker import TrafficLightWorker

logger = logging.getLogger(__name__)


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
