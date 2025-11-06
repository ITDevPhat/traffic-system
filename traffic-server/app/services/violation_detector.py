"""
Violation Detection Service
Chỉ lưu dữ liệu khi phát hiện vi phạm (không lưu gì mặc định)

Rules:
- Red light violation (crossing stop line when light is red)
- Speed violation (over speed limit)
- No helmet violation (for motorbikes)
- Wrong lane violation
- ROI violation (enter restricted area)
"""

import time
import logging
from typing import Dict, List, Optional, Tuple
import numpy as np
from pathlib import Path
import cv2
import os

logger = logging.getLogger(__name__)


class ViolationRule:
    """Base class cho violation rules"""
    
    def __init__(self, rule_id: str, rule_name: str):
        self.rule_id = rule_id
        self.rule_name = rule_name
        self.enabled = True
    
    def check(self, track_context: Dict, frame: np.ndarray) -> Optional[Dict]:
        """
        Check violation cho track
        
        Args:
            track_context: {track_id, bbox, class_id, class_name, plate, track_history, ...}
            frame: Current frame (BGR)
        
        Returns:
            Dict với violation info hoặc None nếu không vi phạm
        """
        raise NotImplementedError


class RedLightViolation(ViolationRule):
    """Vi phạm đèn đỏ - xe vượt vạch dừng khi đèn đỏ"""
    
    def __init__(self, stop_line_roi: Optional[List[List[float]]] = None):
        super().__init__("red_light", "Red Light Violation")
        self.stop_line_roi = stop_line_roi
        self.traffic_light_state = "green"  # TODO: integrate traffic light detector
    
    def check(self, track_context: Dict, frame: np.ndarray) -> Optional[Dict]:
        """Check red light violation"""
        if not self.stop_line_roi or self.traffic_light_state != "red":
            return None
        
        # Check if vehicle crossed stop line
        bbox = track_context.get("bbox", [])
        if len(bbox) < 4:
            return None
        
        # Simple check: bottom-center of bbox crossed the line
        x1, y1, x2, y2 = bbox
        cx = (x1 + x2) / 2
        cy = y2  # Bottom of bbox
        
        # TODO: implement proper line crossing logic
        # For now, just placeholder
        return None


class SpeedViolation(ViolationRule):
    """Vi phạm tốc độ"""
    
    def __init__(self, speed_limit_kmh: float = 50.0):
        super().__init__("speed", "Speed Violation")
        self.speed_limit_kmh = speed_limit_kmh
    
    def check(self, track_context: Dict, frame: np.ndarray) -> Optional[Dict]:
        """Check speed violation"""
        # TODO: calculate speed from track history
        # Cần: pixel_to_meter conversion, fps, track positions over time
        return None


class ROIViolation(ViolationRule):
    """Vi phạm ROI - xe vào khu vực cấm"""
    
    def __init__(self, restricted_rois: Optional[List[List[List[float]]]] = None):
        super().__init__("roi", "ROI Violation")
        self.restricted_rois = restricted_rois or []
    
    def check(self, track_context: Dict, frame: np.ndarray) -> Optional[Dict]:
        """Check ROI violation"""
        if not self.restricted_rois:
            return None
        
        bbox = track_context.get("bbox", [])
        if len(bbox) < 4:
            return None
        
        x1, y1, x2, y2 = bbox
        cx = (x1 + x2) / 2
        cy = (y1 + y2) / 2
        
        # Check if center point is in any restricted ROI
        for roi in self.restricted_rois:
            if self._point_in_polygon((cx, cy), roi):
                return {
                    "violation_type": "roi",
                    "violation_name": "ROI Violation",
                    "severity": "medium",
                    "description": "Vehicle entered restricted area",
                    "timestamp": time.time()
                }
        
        return None
    
    def _point_in_polygon(self, point: Tuple[float, float], polygon: List[List[float]]) -> bool:
        """Check if point is inside polygon"""
        x, y = point
        n = len(polygon)
        inside = False
        
        p1x, p1y = polygon[0]
        for i in range(1, n + 1):
            p2x, p2y = polygon[i % n]
            if y > min(p1y, p2y):
                if y <= max(p1y, p2y):
                    if x <= max(p1x, p2x):
                        if p1y != p2y:
                            xinters = (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                        if p1x == p2x or x <= xinters:
                            inside = not inside
            p1x, p1y = p2x, p2y
        
        return inside


class ViolationDetector:
    """
    Violation Detector Service
    
    Quản lý các rules và quyết định khi nào lưu violation event
    """
    
    def __init__(
        self,
        evidence_dir: str = "evidence",
        enable_auto_save: bool = True,
        min_confidence_to_save: float = 0.7
    ):
        """
        Args:
            evidence_dir: Thư mục lưu evidence images
            enable_auto_save: Tự động lưu evidence khi phát hiện vi phạm
            min_confidence_to_save: Confidence tối thiểu để lưu (filter false positives)
        """
        self.evidence_dir = Path(evidence_dir)
        self.evidence_dir.mkdir(parents=True, exist_ok=True)
        
        self.enable_auto_save = enable_auto_save
        self.min_confidence_to_save = min_confidence_to_save
        
        # Violation rules
        self.rules: List[ViolationRule] = []
        
        # Statistics
        self.stats = {
            'total_violations': 0,
            'total_saved': 0,
            'total_skipped_low_confidence': 0,
            'violations_by_type': {}
        }
        
        logger.info("✅ ViolationDetector initialized")
    
    def add_rule(self, rule: ViolationRule):
        """Add violation rule"""
        self.rules.append(rule)
        logger.info(f"➕ Added rule: {rule.rule_name}")
    
    def check_violations(
        self,
        track_context: Dict,
        frame: np.ndarray
    ) -> List[Dict]:
        """
        Check all rules for violations
        
        Args:
            track_context: Track metadata
            frame: Current frame
        
        Returns:
            List of violation dicts
        """
        violations = []
        
        for rule in self.rules:
            if not rule.enabled:
                continue
            
            try:
                violation = rule.check(track_context, frame)
                if violation:
                    # Add common fields
                    violation.update({
                        'track_id': track_context.get('track_id'),
                        'plate': track_context.get('plate'),
                        'plate_conf': track_context.get('plate_conf', 0.0),
                        'bbox': track_context.get('bbox'),
                        'class_name': track_context.get('class_name'),
                        'rule_id': rule.rule_id,
                        'frame_shape': frame.shape
                    })
                    violations.append(violation)
            
            except Exception as e:
                logger.error(f"Error checking rule {rule.rule_name}: {e}")
        
        return violations
    
    def save_violation_event(
        self,
        violation: Dict,
        frame: np.ndarray,
        video_job_id: Optional[int] = None,
        frame_idx: Optional[int] = None
    ) -> Optional[str]:
        """
        Lưu violation event (evidence image + metadata)
        
        Args:
            violation: Violation dict
            frame: Frame chứa vi phạm
            video_job_id: Video job ID (for DB tracking)
            frame_idx: Frame index
        
        Returns:
            Evidence file path hoặc None nếu skip
        """
        # Filter by confidence
        plate_conf = violation.get('plate_conf', 0.0)
        if plate_conf < self.min_confidence_to_save:
            self.stats['total_skipped_low_confidence'] += 1
            logger.debug(f"Skipped violation (low conf={plate_conf:.2f})")
            return None
        
        try:
            # Generate evidence filename
            timestamp = int(time.time() * 1000)
            track_id = violation.get('track_id', 'unknown')
            rule_id = violation.get('rule_id', 'unknown')
            
            filename = f"{timestamp}_{rule_id}_{track_id}.jpg"
            if video_job_id:
                filename = f"job{video_job_id}_{filename}"
            
            filepath = self.evidence_dir / filename
            
            # Draw violation info on frame
            annotated_frame = self._annotate_violation(frame.copy(), violation)
            
            # Save image
            cv2.imwrite(str(filepath), annotated_frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
            
            self.stats['total_violations'] += 1
            self.stats['total_saved'] += 1
            
            vtype = violation.get('violation_type', 'unknown')
            self.stats['violations_by_type'][vtype] = self.stats['violations_by_type'].get(vtype, 0) + 1
            
            logger.info(f"💾 Saved violation: {filename} ({vtype}, plate={violation.get('plate', 'N/A')})")
            
            return str(filepath)
        
        except Exception as e:
            logger.error(f"Failed to save violation: {e}")
            return None
    
    def _annotate_violation(self, frame: np.ndarray, violation: Dict) -> np.ndarray:
        """Draw violation info on frame"""
        bbox = violation.get('bbox')
        if bbox and len(bbox) >= 4:
            x1, y1, x2, y2 = [int(v) for v in bbox]
            
            # Draw red bbox (violation)
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 0, 255), 3)
            
            # Draw violation text
            text = f"{violation.get('violation_name', 'Violation')}"
            plate = violation.get('plate')
            if plate:
                text += f" | {plate}"
            
            cv2.putText(frame, text, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
        
        return frame
    
    def get_stats(self) -> Dict:
        """Get violation statistics"""
        return self.stats.copy()
    
    def reset_stats(self):
        """Reset statistics"""
        self.stats = {
            'total_violations': 0,
            'total_saved': 0,
            'total_skipped_low_confidence': 0,
            'violations_by_type': {}
        }


# Global singleton
_violation_detector: Optional[ViolationDetector] = None


def get_violation_detector(
    evidence_dir: str = "evidence",
    enable_auto_save: bool = True,
    force_reload: bool = False
) -> ViolationDetector:
    """
    Get global violation detector instance (singleton)
    
    Args:
        evidence_dir: Evidence directory
        enable_auto_save: Auto-save violations
        force_reload: Force reload detector
    
    Returns:
        ViolationDetector instance
    """
    global _violation_detector
    
    if _violation_detector is None or force_reload:
        logger.info("🔧 Initializing global ViolationDetector...")
        _violation_detector = ViolationDetector(
            evidence_dir=evidence_dir,
            enable_auto_save=enable_auto_save
        )
        
        # Add default rules
        # TODO: load rules from config
        _violation_detector.add_rule(ROIViolation())
    
    return _violation_detector

