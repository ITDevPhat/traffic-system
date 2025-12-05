"""
Traffic Light Detection Worker

Implements independent worker for ROI-based traffic light detection.
Runs at ~0.75s intervals to minimize resource usage.

Author: Traffic System Team
Version: 1.0.0
"""
import asyncio
import base64
import cv2
import numpy as np
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, AsyncGenerator, List, Dict, Any
from collections import deque

logger = logging.getLogger(__name__)


# =========================================================
# ROI Configuration
# =========================================================

@dataclass
class ROIConfig:
    """
    Normalized ROI coordinates [0, 1]
    
    Attributes:
        x: Left edge (normalized)
        y: Top edge (normalized)
        width: Width (normalized)
        height: Height (normalized)
    """
    x: float
    y: float
    width: float
    height: float
    
    def to_pixel_coords(self, frame_width: int, frame_height: int) -> Dict[str, int]:
        """
        Convert normalized coordinates to pixel coordinates
        
        Args:
            frame_width: Frame width in pixels
            frame_height: Frame height in pixels
            
        Returns:
            Dictionary with pixel coordinates: {x1, y1, x2, y2}
        """
        x1 = int(self.x * frame_width)
        y1 = int(self.y * frame_height)
        x2 = int((self.x + self.width) * frame_width)
        y2 = int((self.y + self.height) * frame_height)
        
        # Ensure coordinates are within frame bounds
        x1 = max(0, min(x1, frame_width - 1))
        y1 = max(0, min(y1, frame_height - 1))
        x2 = max(0, min(x2, frame_width))
        y2 = max(0, min(y2, frame_height))
        
        return {
            'x1': x1,
            'y1': y1,
            'x2': x2,
            'y2': y2
        }


# =========================================================
# Traffic Light Detection Worker
# =========================================================

class TrafficLightWorker:
    """
    Independent worker for traffic light detection on ROI.
    
    Features:
    - Runs at ~0.75s intervals (1.33 FPS)
    - Crops ROI from video stream
    - Runs YOLO TL model inference
    - Applies temporal smoothing
    - Broadcasts results via WebSocket
    """
    
    def __init__(
        self,
        camera_id: str,
        roi: ROIConfig,
        video_stream,
        model=None,
        detection_interval: float = 0.75
    ):
        """
        Initialize traffic light worker
        
        Args:
            camera_id: Camera identifier
            roi: ROI configuration
            video_stream: Video stream manager
            model: YOLO TL model (optional, will be loaded if None)
            detection_interval: Detection interval in seconds (default: 0.75)
        """
        self.camera_id = camera_id
        self.roi = roi
        self.video_stream = video_stream
        self.model = model
        self.detection_interval = detection_interval
        
        self.is_running = False
        self.current_state = 'UNKNOWN'
        self.state_history: deque = deque(maxlen=3)  # Keep last 3 states for smoothing
        self.subscribers: List[asyncio.Queue] = []
        
        self.worker_id = f"{camera_id}_tl_worker"
        
        logger.info(f"TrafficLightWorker initialized: {self.worker_id}")
    
    async def start(self):
        """Initialize and start detection loop"""
        try:
            # Load model if not provided
            if self.model is None:
                self.model = await self.load_model()
            
            self.is_running = True
            logger.info(f"TrafficLightWorker started: {self.worker_id}")
            
            # Start detection loop in background
            asyncio.create_task(self.detection_loop())
            
        except Exception as e:
            logger.error(f"Failed to start worker {self.worker_id}: {e}", exc_info=True)
            raise
    
    async def load_model(self):
        """
        Load YOLO TL model (lazy loading)
        
        Implements lazy loading with retry logic and fallback to CPU.
        
        Returns:
            YOLO model instance
            
        Raises:
            Exception: If model loading fails after all retries
        """
        max_retries = 3
        retry_delay = 1.0  # seconds
        
        for attempt in range(max_retries):
            try:
                from app.utils.model_loader import load_yolo_model, get_model_info
                from app.core.config import settings
                import torch
                
                logger.info(
                    f"Loading YOLO TL model for worker {self.worker_id} "
                    f"(attempt {attempt + 1}/{max_retries})..."
                )
                
                # Get model info (auto-detect .engine > .onnx > .pt)
                model_info = get_model_info(settings.YOLO_TRAFFIC_LIGHT_MODEL)
                
                if not model_info["found"]:
                    raise FileNotFoundError(
                        f"YOLO TL model not found: {settings.YOLO_TRAFFIC_LIGHT_MODEL}"
                    )
                
                # Determine device with fallback to CPU
                device = settings.DEVICE if torch.cuda.is_available() else "cpu"
                
                # Try GPU first, fallback to CPU on CUDA errors
                try:
                    model = load_yolo_model(
                        model_info["path"],
                        device=device,
                        imgsz=640,
                        half=True if device == "cuda" else False,
                        verbose=False
                    )
                except RuntimeError as cuda_error:
                    if "CUDA" in str(cuda_error) or "out of memory" in str(cuda_error):
                        logger.warning(
                            f"GPU loading failed ({cuda_error}), falling back to CPU"
                        )
                        device = "cpu"
                        model = load_yolo_model(
                            model_info["path"],
                            device=device,
                            imgsz=640,
                            half=False,
                            verbose=False
                        )
                    else:
                        raise
                
                logger.info(
                    f"YOLO TL model loaded: {model_info['path']} "
                    f"({model_info['type']}, {model_info['size_mb']}MB) on {device}"
                )
                
                return model
                
            except Exception as e:
                logger.error(
                    f"Failed to load YOLO TL model (attempt {attempt + 1}/{max_retries}): {e}",
                    exc_info=True
                )
                
                if attempt < max_retries - 1:
                    # Wait before retry with exponential backoff
                    wait_time = retry_delay * (2 ** attempt)
                    logger.info(f"Retrying in {wait_time}s...")
                    await asyncio.sleep(wait_time)
                else:
                    # Final attempt failed
                    logger.error(f"Failed to load YOLO TL model after {max_retries} attempts")
                    raise
    
    async def detection_loop(self):
        """
        Main detection loop - runs every ~0.75s
        
        Process:
        1. Get latest frame from video stream
        2. Crop ROI
        3. Run YOLO inference
        4. Classify state
        5. Apply temporal smoothing
        6. Encode frame to JPEG
        7. Broadcast to subscribers
        
        Implements comprehensive error handling:
        - Stream interruption handling (None frame check)
        - Exception catching with error broadcasting
        - Graceful degradation on errors
        """
        logger.info(f"Detection loop started for {self.worker_id}")
        consecutive_errors = 0
        max_consecutive_errors = 10
        
        while self.is_running:
            try:
                # Get latest frame from video stream
                frame = await self._get_latest_frame()
                
                if frame is None:
                    # Stream interrupted - skip this iteration
                    logger.debug(f"Stream interrupted for {self.worker_id}, skipping iteration")
                    await asyncio.sleep(self.detection_interval)
                    continue
                
                # Crop ROI
                roi_frame = self.crop_roi(frame)
                
                if roi_frame is None or roi_frame.size == 0:
                    logger.warning(f"Empty ROI frame for {self.worker_id}")
                    await asyncio.sleep(self.detection_interval)
                    continue
                
                # Run YOLO inference
                detections = await self._run_inference(roi_frame)
                
                # Classify state
                state, confidence = self.classify_state(detections)
                
                # Apply temporal smoothing
                smoothed_state = self.apply_smoothing(state)
                
                # Encode ROI frame to JPEG
                frame_b64 = self._encode_frame(roi_frame)
                
                # Broadcast to subscribers
                message = {
                    'type': 'state_update',
                    'state': smoothed_state,
                    'confidence': confidence,
                    'timestamp': datetime.now().isoformat(),
                    'frame': frame_b64
                }
                
                await self.broadcast(message)
                
                # Reset error counter on success
                consecutive_errors = 0
                
            except asyncio.CancelledError:
                # Task was cancelled - exit gracefully
                logger.info(f"Detection loop cancelled for {self.worker_id}")
                break
                
            except Exception as e:
                consecutive_errors += 1
                logger.error(
                    f"Detection error in {self.worker_id} "
                    f"(error {consecutive_errors}/{max_consecutive_errors}): {e}",
                    exc_info=True
                )
                
                # Broadcast error to subscribers
                error_message = {
                    'type': 'error',
                    'error': str(e),
                    'timestamp': datetime.now().isoformat()
                }
                
                try:
                    await self.broadcast(error_message)
                except Exception as broadcast_error:
                    logger.error(f"Failed to broadcast error message: {broadcast_error}")
                
                # Stop worker if too many consecutive errors
                if consecutive_errors >= max_consecutive_errors:
                    logger.error(
                        f"Too many consecutive errors ({consecutive_errors}) in {self.worker_id}, "
                        "stopping worker"
                    )
                    self.is_running = False
                    break
            
            # Wait for next detection interval
            await asyncio.sleep(self.detection_interval)
        
        logger.info(f"Detection loop stopped for {self.worker_id}")
    
    async def _get_latest_frame(self) -> Optional[np.ndarray]:
        """
        Get latest frame from video stream
        
        Returns:
            Frame as numpy array, or None if stream unavailable
        """
        try:
            # This is a placeholder - actual implementation depends on video stream manager
            # For now, return None to indicate stream not available
            # TODO: Integrate with actual video stream manager in task 3
            return None
        except Exception as e:
            logger.warning(f"Failed to get frame for {self.worker_id}: {e}")
            return None
    
    async def _run_inference(self, roi_frame: np.ndarray) -> List[Any]:
        """
        Run YOLO inference on ROI frame
        
        Args:
            roi_frame: Cropped ROI frame
            
        Returns:
            List of detections
        """
        if self.model is None:
            return []
        
        try:
            from app.core.config import settings
            
            # Run inference
            results = self.model.predict(
                roi_frame,
                conf=settings.INFERENCE_CONFIDENCE_LIGHT,
                verbose=False
            )
            
            if len(results) == 0 or results[0].boxes is None:
                return []
            
            return results[0].boxes
            
        except Exception as e:
            logger.warning(f"YOLO inference failed for {self.worker_id}: {e}")
            return []
    
    def crop_roi(self, frame: np.ndarray) -> Optional[np.ndarray]:
        """
        Crop ROI from frame
        
        Args:
            frame: Full frame
            
        Returns:
            Cropped ROI frame, or None if invalid
        """
        try:
            h, w = frame.shape[:2]
            coords = self.roi.to_pixel_coords(w, h)
            
            # Validate coordinates
            if coords['x2'] <= coords['x1'] or coords['y2'] <= coords['y1']:
                logger.warning(f"Invalid ROI coordinates for {self.worker_id}: {coords}")
                return None
            
            # Crop
            roi_frame = frame[coords['y1']:coords['y2'], coords['x1']:coords['x2']]
            
            return roi_frame
            
        except Exception as e:
            logger.error(f"Failed to crop ROI for {self.worker_id}: {e}")
            return None
    
    def classify_state(self, detections: List[Any]) -> tuple[str, float]:
        """
        Classify traffic light state from YOLO detections
        
        Args:
            detections: YOLO detection boxes
            
        Returns:
            Tuple of (state, confidence)
            - state: 'GREEN', 'RED', 'YELLOW', or 'UNKNOWN'
            - confidence: Detection confidence [0, 1]
        """
        if not detections or len(detections) == 0:
            # No detection - default to YELLOW
            return 'YELLOW', 0.0
        
        # Get highest confidence detection
        best_det = max(detections, key=lambda d: d.conf[0])
        confidence = float(best_det.conf[0])
        class_id = int(best_det.cls[0])
        
        # Map class ID to state
        # Assuming: 0 = green, 1 = red
        if class_id == 0:
            return 'GREEN', confidence
        elif class_id == 1:
            return 'RED', confidence
        else:
            return 'YELLOW', confidence
    
    def apply_smoothing(self, new_state: str) -> str:
        """
        Apply temporal smoothing to reduce flickering
        
        Uses majority voting over last 3 states.
        State must be consistent for 2/3 frames to change.
        
        Args:
            new_state: New detected state
            
        Returns:
            Smoothed state
        """
        # Add new state to history
        self.state_history.append(new_state)
        
        # Need at least 2 states for smoothing
        if len(self.state_history) < 2:
            self.current_state = new_state
            return self.current_state
        
        # Check if last 2 states are consistent
        if self.state_history[-1] == self.state_history[-2]:
            self.current_state = self.state_history[-1]
        
        # Otherwise keep current state (requires consistency to change)
        return self.current_state
    
    def _encode_frame(self, frame: np.ndarray, quality: int = 70) -> str:
        """
        Encode frame to base64 JPEG
        
        Args:
            frame: Frame to encode
            quality: JPEG quality (0-100)
            
        Returns:
            Base64 encoded JPEG string with data URI prefix
        """
        try:
            # Encode to JPEG
            _, buffer = cv2.imencode(
                '.jpg',
                frame,
                [cv2.IMWRITE_JPEG_QUALITY, quality]
            )
            
            # Convert to base64
            frame_b64 = base64.b64encode(buffer).decode('utf-8')
            
            # Add data URI prefix
            return f'data:image/jpeg;base64,{frame_b64}'
            
        except Exception as e:
            logger.error(f"Failed to encode frame for {self.worker_id}: {e}")
            return ''
    
    async def broadcast(self, message: Dict[str, Any]):
        """
        Broadcast message to all subscribers
        
        Args:
            message: Message dictionary to broadcast
        """
        # Remove disconnected subscribers
        active_subscribers = []
        
        for queue in self.subscribers:
            try:
                # Non-blocking put
                queue.put_nowait(message)
                active_subscribers.append(queue)
            except asyncio.QueueFull:
                logger.warning(f"Subscriber queue full for {self.worker_id}, dropping message")
                active_subscribers.append(queue)
            except Exception as e:
                logger.warning(f"Failed to send to subscriber for {self.worker_id}: {e}")
                # Don't add to active_subscribers (remove this subscriber)
        
        self.subscribers = active_subscribers
    
    async def stop(self):
        """
        Stop detection and cleanup resources
        
        Implements comprehensive cleanup with exception handling:
        - Stops detection loop
        - Cleans up model resources
        - Clears all subscribers
        - Handles exceptions gracefully to ensure cleanup completes
        """
        logger.info(f"Stopping worker {self.worker_id}...")
        
        # Track cleanup errors but don't stop cleanup process
        cleanup_errors = []
        
        try:
            # Stop detection loop
            self.is_running = False
            
        except Exception as e:
            error_msg = f"Error stopping detection loop: {e}"
            logger.error(error_msg, exc_info=True)
            cleanup_errors.append(error_msg)
        
        # Cleanup model
        try:
            if self.model is not None:
                # YOLO models don't have explicit cleanup, but we can delete the reference
                # This allows garbage collection to free GPU/CPU memory
                del self.model
                self.model = None
                logger.debug(f"Model cleaned up for {self.worker_id}")
        except Exception as e:
            error_msg = f"Error cleaning up model: {e}"
            logger.warning(error_msg, exc_info=True)
            cleanup_errors.append(error_msg)
        
        # Clear subscribers
        try:
            # Send final message to subscribers before clearing
            if self.subscribers:
                final_message = {
                    'type': 'info',
                    'info': 'Worker stopped',
                    'timestamp': datetime.now().isoformat()
                }
                try:
                    await self.broadcast(final_message)
                except Exception as broadcast_error:
                    logger.debug(f"Failed to send final message: {broadcast_error}")
            
            self.subscribers.clear()
            logger.debug(f"Subscribers cleared for {self.worker_id}")
            
        except Exception as e:
            error_msg = f"Error clearing subscribers: {e}"
            logger.warning(error_msg, exc_info=True)
            cleanup_errors.append(error_msg)
        
        # Clear state history
        try:
            self.state_history.clear()
        except Exception as e:
            error_msg = f"Error clearing state history: {e}"
            logger.debug(error_msg)
            cleanup_errors.append(error_msg)
        
        # Log final status
        if cleanup_errors:
            logger.warning(
                f"Worker {self.worker_id} stopped with {len(cleanup_errors)} cleanup errors: "
                f"{'; '.join(cleanup_errors)}"
            )
        else:
            logger.info(f"Worker stopped successfully: {self.worker_id}")
        
        # Always return successfully - we've done our best to cleanup
        return True
    
    async def stream(self) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Generator for streaming updates to WebSocket clients
        
        Yields:
            Message dictionaries
        """
        # Create queue for this subscriber
        queue: asyncio.Queue = asyncio.Queue(maxsize=10)
        self.subscribers.append(queue)
        
        logger.info(f"New subscriber for {self.worker_id} (total: {len(self.subscribers)})")
        
        try:
            while True:
                # Wait for next message
                message = await queue.get()
                yield message
        finally:
            # Remove subscriber on disconnect
            if queue in self.subscribers:
                self.subscribers.remove(queue)
            logger.info(f"Subscriber disconnected from {self.worker_id} (remaining: {len(self.subscribers)})")
