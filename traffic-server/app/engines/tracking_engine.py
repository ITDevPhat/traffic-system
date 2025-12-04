"""
Tracking Engine - Pure ByteTrack Tracking Module
Nhận detections từ Detection Engine, trả về tracked objects
"""
import numpy as np
import logging
import time
from typing import List, Dict, Optional
from collections import deque, defaultdict

logger = logging.getLogger(__name__)

class TrackingEngine:
    """
    Pure ByteTrack tracking engine
    Input: list of detections from DetectionEngine
    Output: list of tracked objects with track_id
    """
    
    def __init__(
        self,
        track_thresh: float = 0.4,
        track_buffer: int = 30,
        match_thresh: float = 0.85,
        frame_rate: int = 30,
        min_box_area: int = 80
    ):
        """
        Initialize ByteTrack tracking engine
        
        Args:
            track_thresh: Threshold for track confidence
            track_buffer: Number of frames to keep lost tracks
            match_thresh: Matching threshold for association
            frame_rate: Expected frame rate for buffer scaling
            min_box_area: Minimum bounding box area
        """
        self.track_thresh = track_thresh
        self.track_buffer = track_buffer
        self.match_thresh = match_thresh
        self.frame_rate = frame_rate
        self.min_box_area = min_box_area
        
        # ByteTracker instance
        self.tracker = None
        self.tracker_initialized = False
        
        # Performance metrics
        self.tracking_times = []
        self.total_tracks = 0
        self.active_tracks = 0
        
        # Track history for smoothing
        self.track_history = defaultdict(lambda: deque(maxlen=10))
        
        logger.info(f"🎯 TrackingEngine initialized")
        logger.info(f"⚙️  Config: thresh={track_thresh}, buffer={track_buffer}, match={match_thresh}")
    
    def _init_tracker(self) -> bool:
        """
        Initialize ByteTracker (lazy loading)
        
        Returns:
            bool: True if initialized successfully
        """
        if self.tracker_initialized:
            return True
            
        try:
            from app.services.boxmot_loader import instantiate_tracker, HAVE_BOXMOT
            
            if not HAVE_BOXMOT:
                logger.error("❌ ByteTrack not available - boxmot not found")
                return False
            
            logger.info("🔄 Initializing ByteTracker...")
            
            self.tracker = instantiate_tracker(
                tracker_type="bytetrack",
                tracker_config=None,
                reid_weights=None,
                device="cpu",  # ByteTrack runs on CPU
                half=False
            )
            
            if self.tracker is None:
                logger.error("❌ Failed to instantiate ByteTracker")
                return False
            
            logger.info("✅ ByteTracker initialized successfully")
            self.tracker_initialized = True
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize ByteTracker: {e}")
            return False
    
    def track(self, detections: List[Dict], frame_idx: int = 0) -> List[Dict]:
        """
        Track objects using ByteTrack
        
        Args:
            detections: List of detections from DetectionEngine
            frame_idx: Current frame index for debugging
            
        Returns:
            List of tracked objects:
            [
                {
                    "track_id": int,
                    "bbox": [x1, y1, x2, y2],  # STANDARDIZED FORMAT
                    "class_id": int,
                    "class_name": str,
                    "confidence": float,
                    "track_confidence": float  # ByteTrack confidence
                },
                ...
            ]
        """
        if not detections:
            return []
        
        if not self.tracker_initialized:
            if not self._init_tracker():
                # Fallback: return detections with dummy track IDs
                return self._fallback_tracking(detections)
        
        try:
            start_time = time.time()
            
            # Convert detections to ByteTrack format
            # ByteTrack expects: [[x1, y1, x2, y2, conf, class_id], ...]
            det_array = []
            for det in detections:
                bbox = det["bbox"]
                conf = det["confidence"]
                class_id = det["class_id"]
                
                # Validate bbox
                x1, y1, x2, y2 = bbox
                if x2 <= x1 or y2 <= y1 or (x2 - x1) * (y2 - y1) < self.min_box_area:
                    continue
                
                det_array.append([x1, y1, x2, y2, conf, class_id])
            
            if not det_array:
                return []
            
            det_array = np.array(det_array, dtype=np.float32)
            
            # Run ByteTrack
            tracks = self.tracker.update(det_array, None)  # No image needed for ByteTrack
            
            tracking_time = time.time() - start_time
            self.tracking_times.append(tracking_time)
            
            # Keep only last 100 tracking times
            if len(self.tracking_times) > 100:
                self.tracking_times = self.tracking_times[-100:]
            
            # Convert tracks to standardized format
            tracked_objects = []
            
            if tracks is not None and len(tracks) > 0:
                for track in tracks:
                    try:
                        # ByteTrack format: [x1, y1, x2, y2, track_id, score, class_id, ...]
                        if len(track) >= 7:
                            x1, y1, x2, y2, track_id, track_conf, class_id = track[:7]
                        else:
                            continue
                        
                        # Apply smoothing
                        bbox = self._smooth_bbox(int(track_id), [x1, y1, x2, y2])
                        
                        tracked_obj = {
                            "track_id": int(track_id),
                            "bbox": [float(bbox[0]), float(bbox[1]), float(bbox[2]), float(bbox[3])],
                            "class_id": int(class_id),
                            "class_name": self._get_class_name(int(class_id)),
                            "confidence": float(track_conf),
                            "track_confidence": float(track_conf)
                        }
                        
                        tracked_objects.append(tracked_obj)
                        
                    except Exception as e:
                        logger.warning(f"⚠️  Failed to parse track: {e}")
                        continue
            
            self.active_tracks = len(tracked_objects)
            self.total_tracks += len(tracked_objects)
            
            # Log performance periodically
            if len(self.tracking_times) % 30 == 0:
                avg_time = np.mean(self.tracking_times[-30:])
                fps = 1.0 / avg_time if avg_time > 0 else 0
                logger.debug(f"🎯 Tracking Engine: {fps:.1f} FPS, {len(tracked_objects)} tracks")
            
            return tracked_objects
            
        except Exception as e:
            logger.error(f"❌ Tracking error: {e}")
            return self._fallback_tracking(detections)
    
    def _smooth_bbox(self, track_id: int, bbox: List[float], alpha: float = 0.35) -> List[float]:
        """
        Apply exponential smoothing to bounding box
        
        Args:
            track_id: Track ID
            bbox: Current bounding box [x1, y1, x2, y2]
            alpha: Smoothing factor (0.35 recommended)
            
        Returns:
            Smoothed bounding box
        """
        history = self.track_history[track_id]
        
        if len(history) == 0:
            # First detection for this track
            history.append(bbox)
            return bbox
        
        # Get last smoothed bbox
        last_bbox = history[-1]
        
        # Apply exponential smoothing
        smoothed_bbox = [
            alpha * bbox[i] + (1 - alpha) * last_bbox[i]
            for i in range(4)
        ]
        
        # Store smoothed bbox
        history.append(smoothed_bbox)
        
        return smoothed_bbox
    
    def _fallback_tracking(self, detections: List[Dict]) -> List[Dict]:
        """
        Fallback tracking when ByteTrack is not available
        Assigns dummy track IDs based on detection order
        
        Args:
            detections: List of detections
            
        Returns:
            List of tracked objects with dummy track IDs
        """
        tracked_objects = []
        
        for i, det in enumerate(detections):
            tracked_obj = {
                "track_id": i + 1,  # Dummy track ID
                "bbox": det["bbox"],
                "class_id": det["class_id"],
                "class_name": det["class_name"],
                "confidence": det["confidence"],
                "track_confidence": det["confidence"]
            }
            tracked_objects.append(tracked_obj)
        
        logger.warning(f"⚠️  Using fallback tracking: {len(tracked_objects)} objects")
        return tracked_objects
    
    def _get_class_name(self, class_id: int) -> str:
        """Get class name from class ID"""
        class_names = {
            0: "person", 1: "bicycle", 2: "car", 3: "motorcycle", 
            5: "bus", 7: "truck", 9: "traffic_light"
        }
        return class_names.get(class_id, f"class_{class_id}")
    
    def cleanup_stale_tracks(self, max_age_frames: int = 100):
        """
        Clean up stale track history
        
        Args:
            max_age_frames: Maximum age in frames before cleanup
        """
        # This is a simple cleanup - in production you'd track frame timestamps
        if len(self.track_history) > max_age_frames:
            # Keep only recent tracks (simple heuristic)
            recent_tracks = dict(list(self.track_history.items())[-max_age_frames//2:])
            self.track_history = defaultdict(lambda: deque(maxlen=10), recent_tracks)
            logger.debug(f"🧹 Cleaned up track history: {len(recent_tracks)} tracks kept")
    
    def get_stats(self) -> Dict:
        """
        Get tracking engine statistics
        
        Returns:
            Dict with performance metrics
        """
        if not self.tracking_times:
            return {"status": "no_data"}
        
        avg_tracking_time = np.mean(self.tracking_times)
        fps = 1.0 / avg_tracking_time if avg_tracking_time > 0 else 0
        
        return {
            "status": "active" if self.tracker_initialized else "fallback",
            "avg_tracking_time": avg_tracking_time,
            "fps": fps,
            "active_tracks": self.active_tracks,
            "total_tracks": self.total_tracks,
            "track_history_size": len(self.track_history),
            "config": {
                "track_thresh": self.track_thresh,
                "track_buffer": self.track_buffer,
                "match_thresh": self.match_thresh
            }
        }
    
    def reset_stats(self):
        """Reset performance statistics"""
        self.tracking_times = []
        self.total_tracks = 0
        self.active_tracks = 0
        logger.info("📊 Tracking engine stats reset")