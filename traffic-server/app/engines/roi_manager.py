"""
ROI Manager - Standardized ROI handling for violation detection
Load, validate, and provide API for ROI-based violation checking
"""
import json
import logging
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum
import numpy as np

logger = logging.getLogger(__name__)

class ROIType(Enum):
    """Standardized ROI types"""
    STOPLINE = "stopline"
    SOLID_LINE = "solid_line"
    TRAFFIC_LIGHT = "traffic_light"
    NO_ENTRY_ZONE = "no_entry_zone"
    WRONG_DIRECTION = "wrong_direction"
    DETECTION_ZONE = "detection_zone"
    LANE_CAR = "lane_car"
    LANE_BIKE = "lane_bike"
    LANE_BUS = "lane_bus"
    LANE_TRUCK = "lane_truck"
    CUSTOM = "custom"

@dataclass
class ROI:
    """
    Standardized ROI structure
    """
    id: str
    type: ROIType
    name: str
    points: List[Tuple[float, float]]  # [(x1,y1), (x2,y2), ...]
    metadata: Dict[str, Any]  # Additional properties specific to ROI type
    
    def __post_init__(self):
        """Validate ROI after creation"""
        if len(self.points) < 2:
            raise ValueError(f"ROI {self.id} must have at least 2 points")
        
        # Validate specific ROI types
        if self.type == ROIType.STOPLINE and len(self.points) != 2:
            raise ValueError(f"Stopline ROI {self.id} must have exactly 2 points")

class ROIManager:
    """
    Manager for all ROI operations
    Load from database/JSON, validate, and provide violation checking APIs
    """
    
    def __init__(self):
        """Initialize ROI Manager"""
        self.rois: Dict[str, ROI] = {}
        self.rois_by_type: Dict[ROIType, List[ROI]] = {}
        
        # Statistics
        self.total_rois_loaded = 0
        self.violation_checks_performed = 0
        
        logger.info("🗺️  ROIManager initialized")
    
    def load_from_json(self, json_data: str) -> bool:
        """
        Load ROIs from JSON string
        
        Args:
            json_data: JSON string containing ROI definitions
            
        Returns:
            True if loaded successfully
        """
        try:
            data = json.loads(json_data)
            
            if "rois" not in data:
                logger.error("❌ JSON missing 'rois' key")
                return False
            
            loaded_count = 0
            
            for roi_data in data["rois"]:
                roi = self._parse_roi_data(roi_data)
                if roi:
                    self.add_roi(roi)
                    loaded_count += 1
            
            logger.info(f"✅ Loaded {loaded_count} ROIs from JSON")
            self.total_rois_loaded += loaded_count
            return True
            
        except json.JSONDecodeError as e:
            logger.error(f"❌ Invalid JSON: {e}")
            return False
        except Exception as e:
            logger.error(f"❌ Error loading ROIs: {e}")
            return False
    
    def load_from_dict(self, roi_dict: Dict[str, List[Tuple[float, float]]]) -> bool:
        """
        Load ROIs from simple dictionary format (for WebSocket ROI updates)
        
        Args:
            roi_dict: Dict mapping ROI name to list of points
            
        Returns:
            True if loaded successfully
        """
        try:
            loaded_count = 0
            
            for name, points in roi_dict.items():
                # Auto-detect ROI type from name
                roi_type = self._detect_roi_type(name)
                
                roi = ROI(
                    id=f"ws_{name}",
                    type=roi_type,
                    name=name,
                    points=[(float(p[0]), float(p[1])) for p in points],
                    metadata={}
                )
                
                self.add_roi(roi)
                loaded_count += 1
            
            logger.info(f"✅ Loaded {loaded_count} ROIs from WebSocket")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error loading ROIs from dict: {e}")
            return False
    
    def _parse_roi_data(self, roi_data: Dict) -> Optional[ROI]:
        """
        Parse ROI data from JSON format
        
        Args:
            roi_data: Dict containing ROI definition
            
        Returns:
            ROI object if valid, None otherwise
        """
        try:
            roi_id = roi_data.get("id", f"roi_{len(self.rois)}")
            roi_type_str = roi_data.get("type", "custom")
            name = roi_data.get("name", roi_id)
            coordinates = roi_data.get("coordinates", [])
            metadata = roi_data.get("metadata", {})
            
            # Convert type string to enum
            try:
                roi_type = ROIType(roi_type_str)
            except ValueError:
                logger.warning(f"⚠️  Unknown ROI type '{roi_type_str}', using CUSTOM")
                roi_type = ROIType.CUSTOM
            
            # Convert coordinates to points
            points = []
            for coord in coordinates:
                if isinstance(coord, (list, tuple)) and len(coord) >= 2:
                    points.append((float(coord[0]), float(coord[1])))
            
            if len(points) < 2:
                logger.warning(f"⚠️  ROI {roi_id} has insufficient points: {len(points)}")
                return None
            
            return ROI(
                id=roi_id,
                type=roi_type,
                name=name,
                points=points,
                metadata=metadata
            )
            
        except Exception as e:
            logger.error(f"❌ Error parsing ROI data: {e}")
            return None
    
    def _detect_roi_type(self, name: str) -> ROIType:
        """
        Auto-detect ROI type from name
        
        Args:
            name: ROI name
            
        Returns:
            Detected ROI type
        """
        name_lower = name.lower()
        
        if "stopline" in name_lower or "stop_line" in name_lower:
            return ROIType.STOPLINE
        elif "solid" in name_lower and "line" in name_lower:
            return ROIType.SOLID_LINE
        elif "traffic" in name_lower and "light" in name_lower:
            return ROIType.TRAFFIC_LIGHT
        elif "no_entry" in name_lower or "forbidden" in name_lower:
            return ROIType.NO_ENTRY_ZONE
        elif "wrong" in name_lower and "direction" in name_lower:
            return ROIType.WRONG_DIRECTION
        elif "lane" in name_lower:
            if "car" in name_lower:
                return ROIType.LANE_CAR
            elif "bike" in name_lower or "bicycle" in name_lower:
                return ROIType.LANE_BIKE
            elif "bus" in name_lower:
                return ROIType.LANE_BUS
            elif "truck" in name_lower:
                return ROIType.LANE_TRUCK
        elif "detection" in name_lower or "zone" in name_lower:
            return ROIType.DETECTION_ZONE
        
        return ROIType.CUSTOM
    
    def add_roi(self, roi: ROI):
        """
        Add ROI to manager
        
        Args:
            roi: ROI object to add
        """
        self.rois[roi.id] = roi
        
        # Add to type-based index
        if roi.type not in self.rois_by_type:
            self.rois_by_type[roi.type] = []
        self.rois_by_type[roi.type].append(roi)
        
        logger.debug(f"➕ Added ROI: {roi.id} ({roi.type.value}) - {roi.name}")
    
    def get_roi(self, roi_id: str) -> Optional[ROI]:
        """Get ROI by ID"""
        return self.rois.get(roi_id)
    
    def get_rois_by_type(self, roi_type: ROIType) -> List[ROI]:
        """Get all ROIs of a specific type"""
        return self.rois_by_type.get(roi_type, [])
    
    def clear_rois(self):
        """Clear all ROIs"""
        count = len(self.rois)
        self.rois.clear()
        self.rois_by_type.clear()
        logger.info(f"🧹 Cleared {count} ROIs")
    
    # ============================================
    # Violation Checking APIs
    # ============================================
    
    def check_line_crossing(self, bbox: List[float], roi: ROI) -> bool:
        """
        Check if bounding box crosses a line ROI
        
        Args:
            bbox: Bounding box [x1, y1, x2, y2]
            roi: Line ROI (stopline, solid_line)
            
        Returns:
            True if bbox intersects the line
        """
        self.violation_checks_performed += 1
        
        if len(roi.points) < 2:
            return False
        
        # Get bbox center
        x1, y1, x2, y2 = bbox
        cx = (x1 + x2) / 2
        cy = (y1 + y2) / 2
        
        # Check if center point is near the line
        line_start = roi.points[0]
        line_end = roi.points[1]
        
        distance = self._point_to_line_distance(cx, cy, line_start, line_end)
        
        # Consider crossing if within bbox width/2 of the line
        bbox_width = x2 - x1
        threshold = bbox_width / 2
        
        return distance < threshold
    
    def check_zone_intersect(self, bbox: List[float], roi: ROI) -> bool:
        """
        Check if bounding box intersects with a zone ROI
        
        Args:
            bbox: Bounding box [x1, y1, x2, y2]
            roi: Zone ROI (polygon)
            
        Returns:
            True if bbox intersects the zone
        """
        self.violation_checks_performed += 1
        
        if len(roi.points) < 3:
            return False
        
        # Get bbox center
        x1, y1, x2, y2 = bbox
        cx = (x1 + x2) / 2
        cy = (y1 + y2) / 2
        
        # Check if center point is inside polygon
        return self._point_in_polygon(cx, cy, roi.points)
    
    def check_direction_violation(self, object_direction: float, roi: ROI) -> bool:
        """
        Check if object direction violates ROI direction constraints
        
        Args:
            object_direction: Object direction in degrees (0-360)
            roi: Direction ROI with allowed_heading in metadata
            
        Returns:
            True if direction is violated
        """
        self.violation_checks_performed += 1
        
        allowed_heading = roi.metadata.get("allowed_heading")
        if not allowed_heading or len(allowed_heading) != 2:
            return False
        
        min_heading, max_heading = allowed_heading
        
        # Handle wrap-around (e.g., 350-10 degrees)
        if min_heading <= max_heading:
            return not (min_heading <= object_direction <= max_heading)
        else:
            return not (object_direction >= min_heading or object_direction <= max_heading)
    
    def _point_to_line_distance(self, px: float, py: float, 
                               line_start: Tuple[float, float], 
                               line_end: Tuple[float, float]) -> float:
        """
        Calculate distance from point to line segment
        
        Args:
            px, py: Point coordinates
            line_start, line_end: Line segment endpoints
            
        Returns:
            Distance from point to line
        """
        x1, y1 = line_start
        x2, y2 = line_end
        
        # Vector from line start to end
        dx = x2 - x1
        dy = y2 - y1
        
        if dx == 0 and dy == 0:
            # Line is a point
            return np.sqrt((px - x1)**2 + (py - y1)**2)
        
        # Parameter t for closest point on line
        t = max(0, min(1, ((px - x1) * dx + (py - y1) * dy) / (dx**2 + dy**2)))
        
        # Closest point on line
        closest_x = x1 + t * dx
        closest_y = y1 + t * dy
        
        # Distance from point to closest point on line
        return np.sqrt((px - closest_x)**2 + (py - closest_y)**2)
    
    def _point_in_polygon(self, px: float, py: float, polygon: List[Tuple[float, float]]) -> bool:
        """
        Check if point is inside polygon using ray casting algorithm
        
        Args:
            px, py: Point coordinates
            polygon: List of polygon vertices
            
        Returns:
            True if point is inside polygon
        """
        n = len(polygon)
        inside = False
        
        p1x, p1y = polygon[0]
        for i in range(1, n + 1):
            p2x, p2y = polygon[i % n]
            
            if py > min(p1y, p2y):
                if py <= max(p1y, p2y):
                    if px <= max(p1x, p2x):
                        if p1y != p2y:
                            xinters = (py - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                        if p1x == p2x or px <= xinters:
                            inside = not inside
            
            p1x, p1y = p2x, p2y
        
        return inside
    
    def get_stats(self) -> Dict:
        """
        Get ROI manager statistics
        
        Returns:
            Dict with statistics
        """
        roi_type_counts = {}
        for roi_type, rois in self.rois_by_type.items():
            roi_type_counts[roi_type.value] = len(rois)
        
        return {
            "total_rois": len(self.rois),
            "total_rois_loaded": self.total_rois_loaded,
            "violation_checks_performed": self.violation_checks_performed,
            "roi_type_counts": roi_type_counts,
            "roi_types_available": [t.value for t in ROIType]
        }
    
    def reset_stats(self):
        """Reset statistics"""
        self.total_rois_loaded = 0
        self.violation_checks_performed = 0
        logger.info("📊 ROI manager stats reset")