"""
Pipeline Manager - Orchestrates all detection engines
Chuẩn hóa pipeline: Capture → Detection → Tracking → State → ROI → Violation → Output
"""
import time
import logging
from typing import Dict, List, Optional, Any
import numpy as np

from .detection_engine import DetectionEngine
from .tracking_engine import TrackingEngine
from .object_state_manager import ObjectStateManager
from .roi_manager import ROIManager
from .violation_engine import ViolationEngine, ViolationResult

logger = logging.getLogger(__name__)

class PipelineManager:
    """
    Orchestrates the complete detection pipeline
    Provides clean API for processing frames and getting results
    """
    
    def __init__(
        self,
        model_path: str,
        device: str = "cuda:0",
        conf_threshold: float = 0.35,
        imgsz: int = 640,
        enable_demo_violations: bool = False,
        enable_violations: bool = None,  # Use config if None
        debug_mode: bool = False
    ):
        """
        Initialize Pipeline Manager with all engines
        
        Args:
            model_path: Path to YOLO model
            device: Device for inference
            conf_threshold: Detection confidence threshold
            imgsz: YOLO input size
            enable_demo_violations: Enable demo violations for testing
            enable_violations: Master switch to enable/disable all violations (None = use config)
            debug_mode: Enable detailed logging
        """
        self.debug_mode = debug_mode
        
        # Initialize all engines
        logger.info("🔧 Initializing Pipeline Manager...")
        
        # 1. Detection Engine (YOLO)
        self.detection_engine = DetectionEngine(
            model_path=model_path,
            device=device,
            conf_threshold=conf_threshold,
            imgsz=imgsz
        )
        
        # 2. Tracking Engine (ByteTrack)
        self.tracking_engine = TrackingEngine()
        
        # 3. Object State Manager (Stateful tracking)
        self.state_manager = ObjectStateManager()
        
        # 4. ROI Manager (Spatial constraints)
        self.roi_manager = ROIManager()
        
        # 5. Violation Engine (Rule evaluation)
        self.violation_engine = ViolationEngine(
            object_state_manager=self.state_manager,
            roi_manager=self.roi_manager,
            enable_demo_violations=enable_demo_violations,
            enable_violations=enable_violations  # Use config if None
        )
        
        # Pipeline metrics
        self.frame_count = 0
        self.pipeline_times = []
        self.last_stats_log = time.time()
        
        logger.info("✅ Pipeline Manager initialized with all engines")
    
    def process_frame(self, frame: np.ndarray, frame_idx: int = 0) -> Dict[str, Any]:
        """
        Process a single frame through the complete pipeline
        
        Args:
            frame: Input frame (H, W, 3) BGR format
            frame_idx: Frame index for debugging
            
        Returns:
            Dict containing all pipeline results:
            {
                "objects": [
                    {
                        "track_id": int,
                        "bbox": [x1, y1, x2, y2],
                        "class_name": str,
                        "confidence": float,
                        "is_violation": bool,
                        "violation_type": str,
                        "violation_details": str
                    },
                    ...
                ],
                "stats": {...},
                "frame_idx": int
            }
        """
        start_time = time.time()
        
        try:
            # Step 1: Object Detection (YOLO)
            detections = self.detection_engine.detect(frame)
            
            if self.debug_mode and frame_idx % 30 == 0:
                logger.debug(f"🧠 Frame {frame_idx}: {len(detections)} detections")
            
            # Step 2: Object Tracking (ByteTrack)
            tracked_objects = self.tracking_engine.track(detections, frame_idx)
            
            if self.debug_mode and frame_idx % 30 == 0:
                logger.debug(f"🎯 Frame {frame_idx}: {len(tracked_objects)} tracked objects")
            
            # Step 3: Violation Detection (Combined State + ROI + Rules)
            violation_results = self.violation_engine.evaluate_violations(tracked_objects)
            
            # Step 4: Combine results into standardized format
            objects = []
            violation_count = 0
            
            for obj in tracked_objects:
                track_id = obj["track_id"]
                violation_result = violation_results.get(track_id)
                
                # Build standardized object result
                object_result = {
                    "track_id": track_id,
                    "bbox": obj["bbox"],  # Already standardized [x1, y1, x2, y2]
                    "class_id": obj["class_id"],
                    "class_name": obj["class_name"],
                    "confidence": obj["confidence"],
                    "is_violation": False,
                    "violation_type": None,
                    "violation_details": None
                }
                
                # Add violation information if present
                if violation_result and violation_result.is_violation:
                    object_result.update({
                        "is_violation": True,
                        "violation_type": violation_result.violation_type.value if violation_result.violation_type else "unknown",
                        "violation_details": violation_result.violation_details,
                        "violation_confidence": violation_result.confidence,
                        "roi_id": violation_result.roi_id
                    })
                    violation_count += 1
                
                objects.append(object_result)
            
            # Pipeline timing
            pipeline_time = time.time() - start_time
            self.pipeline_times.append(pipeline_time)
            self.frame_count += 1
            
            # Keep only last 100 pipeline times
            if len(self.pipeline_times) > 100:
                self.pipeline_times = self.pipeline_times[-100:]
            
            # Periodic stats logging
            if self.debug_mode and time.time() - self.last_stats_log > 10.0:
                self._log_pipeline_stats()
                self.last_stats_log = time.time()
            
            # Build result
            result = {
                "objects": objects,
                "frame_idx": frame_idx,
                "violation_count": violation_count,
                "total_objects": len(objects),
                "pipeline_time": pipeline_time,
                "timestamp": time.time()
            }
            
            if self.debug_mode:
                result["stats"] = self.get_pipeline_stats()
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Pipeline error on frame {frame_idx}: {e}")
            return {
                "objects": [],
                "frame_idx": frame_idx,
                "violation_count": 0,
                "total_objects": 0,
                "pipeline_time": time.time() - start_time,
                "error": str(e),
                "timestamp": time.time()
            }
    
    def update_roi_config(self, roi_dict: Dict[str, List[List[float]]]) -> bool:
        """
        Update ROI configuration from WebSocket or API
        
        Args:
            roi_dict: Dict mapping ROI name to list of points
            
        Returns:
            True if updated successfully
        """
        try:
            # Clear existing ROIs
            self.roi_manager.clear_rois()
            
            # Load new ROIs
            success = self.roi_manager.load_from_dict(roi_dict)
            
            if success:
                logger.info(f"✅ Updated ROI config: {len(roi_dict)} ROIs loaded")
            else:
                logger.error("❌ Failed to update ROI config")
            
            return success
            
        except Exception as e:
            logger.error(f"❌ Error updating ROI config: {e}")
            return False
    
    def clear_roi_config(self):
        """Clear all ROI configuration"""
        self.roi_manager.clear_rois()
        logger.info("🧹 ROI configuration cleared")
    
    def _log_pipeline_stats(self):
        """Log detailed pipeline statistics"""
        if not self.pipeline_times:
            return
        
        avg_pipeline_time = np.mean(self.pipeline_times[-30:])
        pipeline_fps = 1.0 / avg_pipeline_time if avg_pipeline_time > 0 else 0
        
        logger.info("=" * 60)
        logger.info("📊 PIPELINE PERFORMANCE STATS")
        logger.info("=" * 60)
        logger.info(f"🎬 Frames processed: {self.frame_count}")
        logger.info(f"⚡ Pipeline FPS: {pipeline_fps:.1f}")
        logger.info(f"⏱️  Avg pipeline time: {avg_pipeline_time*1000:.1f}ms")
        
        # Engine-specific stats
        detection_stats = self.detection_engine.get_stats()
        if detection_stats.get("status") == "active":
            logger.info(f"🧠 Detection FPS: {detection_stats.get('fps', 0):.1f}")
        
        tracking_stats = self.tracking_engine.get_stats()
        if tracking_stats.get("status") in ["active", "fallback"]:
            logger.info(f"🎯 Tracking FPS: {tracking_stats.get('fps', 0):.1f}")
            logger.info(f"🎯 Active tracks: {tracking_stats.get('active_tracks', 0)}")
        
        state_stats = self.state_manager.get_stats()
        logger.info(f"🗂️  Active objects: {state_stats.get('active_objects', 0)}")
        logger.info(f"🗂️  Avg speed: {state_stats.get('avg_speed_kmh', 0):.1f} km/h")
        
        roi_stats = self.roi_manager.get_stats()
        logger.info(f"🗺️  ROIs loaded: {roi_stats.get('total_rois', 0)}")
        
        violation_stats = self.violation_engine.get_stats()
        logger.info(f"🚨 Total violations: {violation_stats.get('total_violations_detected', 0)}")
        logger.info(f"🚨 Violating objects: {violation_stats.get('unique_violating_objects', 0)}")
        
        logger.info("=" * 60)
    
    def get_pipeline_stats(self) -> Dict[str, Any]:
        """
        Get comprehensive pipeline statistics
        
        Returns:
            Dict with all engine statistics
        """
        avg_pipeline_time = 0.0
        pipeline_fps = 0.0
        
        if self.pipeline_times:
            avg_pipeline_time = np.mean(self.pipeline_times)
            pipeline_fps = 1.0 / avg_pipeline_time if avg_pipeline_time > 0 else 0
        
        return {
            "pipeline": {
                "frames_processed": self.frame_count,
                "avg_pipeline_time": avg_pipeline_time,
                "pipeline_fps": pipeline_fps,
                "debug_mode": self.debug_mode
            },
            "detection_engine": self.detection_engine.get_stats(),
            "tracking_engine": self.tracking_engine.get_stats(),
            "state_manager": self.state_manager.get_stats(),
            "roi_manager": self.roi_manager.get_stats(),
            "violation_engine": self.violation_engine.get_stats()
        }
    
    def reset_all_stats(self):
        """Reset statistics for all engines"""
        self.frame_count = 0
        self.pipeline_times = []
        
        self.detection_engine.reset_stats()
        self.tracking_engine.reset_stats()
        self.state_manager.reset_stats()
        self.roi_manager.reset_stats()
        self.violation_engine.reset_stats()
        
        logger.info("📊 All pipeline stats reset")
    
    def cleanup(self):
        """Cleanup pipeline resources"""
        # Cleanup stale object states
        self.state_manager.cleanup_stale_objects(time.time())
        
        # Cleanup stale track history
        self.tracking_engine.cleanup_stale_tracks()
        
        logger.debug("🧹 Pipeline cleanup completed")