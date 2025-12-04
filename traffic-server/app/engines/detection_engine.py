"""
Detection Engine - Pure YOLO Detection Module
Chỉ làm object detection, không tracking, không ROI, không violation
"""
import cv2
import numpy as np
import logging
import time
from typing import List, Dict, Optional, Tuple
from pathlib import Path

logger = logging.getLogger(__name__)

# Vehicle class IDs from YOLO model
VEHICLE_IDS = {0, 1, 2, 3, 5, 7}  # person, bicycle, car, motorcycle, bus, truck
CLASS_NAMES = {
    0: "person", 1: "bicycle", 2: "car", 3: "motorcycle", 
    5: "bus", 7: "truck", 9: "traffic_light"
}

class DetectionEngine:
    """
    Pure YOLO detection engine
    Input: frame (numpy array)
    Output: list of detections with standardized format
    """
    
    def __init__(
        self,
        model_path: str,
        device: str = "cuda:0",
        conf_threshold: float = 0.35,
        imgsz: int = 640,
        half: bool = False
    ):
        """
        Initialize YOLO detection engine
        
        Args:
            model_path: Path to YOLO model (.pt, .onnx, .engine)
            device: Device to run inference on
            conf_threshold: Confidence threshold for detections
            imgsz: Input image size for YOLO
            half: Use FP16 precision (faster but less accurate)
        """
        self.model_path = model_path
        self.device = device
        self.conf_threshold = conf_threshold
        self.imgsz = imgsz
        self.half = half
        
        # Model will be loaded lazily
        self.model = None
        self.model_loaded = False
        
        # Performance metrics
        self.inference_times = []
        self.total_detections = 0
        
        logger.info(f"🧠 DetectionEngine initialized: {model_path}")
        logger.info(f"⚙️  Config: device={device}, conf={conf_threshold}, imgsz={imgsz}")
    
    def load_model(self) -> bool:
        """
        Load YOLO model (lazy loading)
        
        Returns:
            bool: True if loaded successfully
        """
        if self.model_loaded:
            return True
            
        try:
            from ultralytics import YOLO
            
            logger.info(f"🔄 Loading YOLO model: {self.model_path}")
            start_time = time.time()
            
            self.model = YOLO(self.model_path)
            
            # Move to device and set precision
            if hasattr(self.model.model, 'to'):
                self.model.model.to(self.device)
                if self.half and 'cuda' in self.device:
                    self.model.model.half()
            
            load_time = time.time() - start_time
            logger.info(f"✅ YOLO model loaded in {load_time:.2f}s")
            
            self.model_loaded = True
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to load YOLO model: {e}")
            return False
    
    def detect(self, frame: np.ndarray) -> List[Dict]:
        """
        Run YOLO detection on frame
        
        Args:
            frame: Input frame (H, W, 3) BGR format
            
        Returns:
            List of detection dictionaries with standardized format:
            [
                {
                    "bbox": [x1, y1, x2, y2],  # ALWAYS this format
                    "class_id": int,
                    "class_name": str,
                    "confidence": float
                },
                ...
            ]
        """
        if not self.model_loaded:
            if not self.load_model():
                return []
        
        try:
            start_time = time.time()
            
            # Run YOLO inference
            results = self.model.predict(
                frame,
                conf=self.conf_threshold,
                imgsz=self.imgsz,
                half=self.half,
                verbose=False,
                device=self.device
            )
            
            inference_time = time.time() - start_time
            self.inference_times.append(inference_time)
            
            # Keep only last 100 inference times for averaging
            if len(self.inference_times) > 100:
                self.inference_times = self.inference_times[-100:]
            
            # Parse results
            detections = []
            
            if results and len(results) > 0:
                result = results[0]  # First (and only) result
                
                if hasattr(result, 'boxes') and result.boxes is not None:
                    boxes = result.boxes
                    
                    # Extract data
                    xyxy = boxes.xyxy.cpu().numpy()  # [x1, y1, x2, y2]
                    conf = boxes.conf.cpu().numpy()
                    cls = boxes.cls.cpu().numpy().astype(int)
                    
                    # Filter for vehicle classes only
                    vehicle_mask = np.isin(cls, list(VEHICLE_IDS))
                    
                    xyxy = xyxy[vehicle_mask]
                    conf = conf[vehicle_mask]
                    cls = cls[vehicle_mask]
                    
                    # Convert to standardized format
                    for i in range(len(xyxy)):
                        x1, y1, x2, y2 = xyxy[i]
                        class_id = int(cls[i])
                        confidence = float(conf[i])
                        
                        detection = {
                            "bbox": [float(x1), float(y1), float(x2), float(y2)],  # STANDARDIZED FORMAT
                            "class_id": class_id,
                            "class_name": CLASS_NAMES.get(class_id, f"class_{class_id}"),
                            "confidence": confidence
                        }
                        
                        detections.append(detection)
            
            self.total_detections += len(detections)
            
            # Log performance periodically
            if len(self.inference_times) % 30 == 0:
                avg_time = np.mean(self.inference_times[-30:])
                fps = 1.0 / avg_time if avg_time > 0 else 0
                logger.debug(f"🧠 Detection Engine: {fps:.1f} FPS, {len(detections)} objects")
            
            return detections
            
        except Exception as e:
            logger.error(f"❌ Detection error: {e}")
            return []
    
    def get_stats(self) -> Dict:
        """
        Get detection engine statistics
        
        Returns:
            Dict with performance metrics
        """
        if not self.inference_times:
            return {"status": "no_data"}
        
        avg_inference_time = np.mean(self.inference_times)
        fps = 1.0 / avg_inference_time if avg_inference_time > 0 else 0
        
        return {
            "status": "active",
            "model_path": self.model_path,
            "device": self.device,
            "avg_inference_time": avg_inference_time,
            "fps": fps,
            "total_detections": self.total_detections,
            "conf_threshold": self.conf_threshold,
            "imgsz": self.imgsz
        }
    
    def reset_stats(self):
        """Reset performance statistics"""
        self.inference_times = []
        self.total_detections = 0
        logger.info("📊 Detection engine stats reset")