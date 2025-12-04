"""
Violation detection rules for the new Rule Engine
Các rule phát hiện vi phạm giao thông với VehicleState model
"""

from typing import List, Dict, Any, Optional
import time
from .models import VehicleState, ViolationEvent, ViolationContext
from .geometry import (
    point_in_polygon,
    segment_intersects_segment,
    is_heading_in_range,
    bbox_center,
    bbox_intersects_polygon,
)


def check_lane_violation(track: Dict[str, Any], rois: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Kiểm tra vi phạm làn đường
    
    Args:
        track: {
            'id': int,
            'bbox': (x1, y1, x2, y2),
            'class_name': str,
            'center': (x, y),
            'heading_deg': float,
            ...
        }
        rois: List of ROI objects
        
    Returns:
        List of violations
    """
    violations = []
    bbox = track.get('bbox')
    class_name = track.get('class_name', '').lower()
    
    if not bbox:
        return violations
    
    # Mapping loại xe cho phép theo từng loại làn
    lane_rules = {
        'lane_car': ['car', 'bus', 'truck'],
        'lane_bike': ['motorbike', 'bicycle'],
        'lane_bus': ['bus'],
        'lane_truck': ['truck'],
    }
    
    for roi in rois:
        roi_type = roi.get('roi_type', '')
        
        if roi_type not in lane_rules:
            continue
        
        # FIX: Use bbox intersection instead of center point for more accurate detection
        points = roi.get('coordinates', [])
        if len(points) < 3:
            continue
        
        polygon = [(p['x'], p['y']) if isinstance(p, dict) else p for p in points]
        
        if bbox_intersects_polygon(bbox, polygon):
            allowed_classes = lane_rules[roi_type]
            
            # Kiểm tra metadata allowed_classes nếu có
            metadata = roi.get('metadata', {})
            if 'allowed_classes' in metadata:
                allowed_classes = metadata['allowed_classes']
            
            if class_name not in allowed_classes:
                violations.append({
                    'type': 'wrong_lane',
                    'roi_name': roi.get('name', 'Unknown'),
                    'roi_type': roi_type,
                    'severity': 'high',
                    'message': f'{class_name} đi vào làn {roi_type}',
                })
    
    return violations


def check_wrong_direction(track: Dict[str, Any], rois: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Kiểm tra vi phạm đi ngược chiều
    
    Args:
        track: Track object với heading_deg
        rois: List of ROI objects
        
    Returns:
        List of violations
    """
    violations = []
    bbox = track.get('bbox')
    heading = track.get('heading_deg')
    
    if not bbox or heading is None:
        return violations
    
    for roi in rois:
        roi_type = roi.get('roi_type', '')
        
        if roi_type not in ['direction_zone', 'wrong_direction']:
            continue
        
        # FIX: Use bbox intersection for more accurate direction zone detection
        points = roi.get('coordinates', [])
        if len(points) < 3:
            continue
        
        polygon = [(p['x'], p['y']) if isinstance(p, dict) else p for p in points]
        
        if bbox_intersects_polygon(bbox, polygon):
            # Lấy allowed_heading từ metadata
            metadata = roi.get('metadata', {})
            allowed_heading = metadata.get('allowed_heading')
            
            if allowed_heading and len(allowed_heading) == 2:
                if not is_heading_in_range(heading, tuple(allowed_heading)):
                    violations.append({
                        'type': 'wrong_direction',
                        'roi_name': roi.get('name', 'Unknown'),
                        'roi_type': roi_type,
                        'severity': 'critical',
                        'message': f'Xe đi ngược chiều (heading: {heading:.0f}°)',
                    })
    
    return violations


def check_forbidden_area(track: Dict[str, Any], rois: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Kiểm tra vi phạm vào vùng cấm
    
    Args:
        track: Track object
        rois: List of ROI objects
        
    Returns:
        List of violations
    """
    violations = []
    bbox = track.get('bbox')
    
    if not bbox:
        return violations
    
    for roi in rois:
        roi_type = roi.get('roi_type', '')
        
        if roi_type != 'forbidden_area':
            continue
        
        points = roi.get('coordinates', [])
        if len(points) < 3:
            continue
        
        polygon = [(p['x'], p['y']) if isinstance(p, dict) else p for p in points]
        
        # FIX: Use bbox intersection for more accurate forbidden area detection
        if bbox_intersects_polygon(bbox, polygon):
            violations.append({
                'type': 'forbidden_area',
                'roi_name': roi.get('name', 'Unknown'),
                'roi_type': roi_type,
                'severity': 'critical',
                'message': 'Xe đi vào vùng cấm',
            })
    
    return violations


def check_opposite_lane(track: Dict[str, Any], rois: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Kiểm tra vi phạm đi vào làn ngược chiều
    
    Args:
        track: Track object
        rois: List of ROI objects
        
    Returns:
        List of violations
    """
    violations = []
    bbox = track.get('bbox')
    heading = track.get('heading_deg')
    
    if not bbox:
        return violations
    
    for roi in rois:
        roi_type = roi.get('roi_type', '')
        
        if roi_type != 'opposite_lane':
            continue
        
        points = roi.get('coordinates', [])
        if len(points) < 3:
            continue
        
        polygon = [(p['x'], p['y']) if isinstance(p, dict) else p for p in points]
        
        if bbox_intersects_polygon(bbox, polygon):
            # Nếu có heading, kiểm tra xem có đi ngược chiều không (optional)
            # Hoặc mặc định cứ vào opposite_lane là lỗi
            
            # Lấy metadata allowed_heading nếu có
            metadata = roi.get('metadata', {})
            allowed_heading = metadata.get('allowed_heading')
            
            is_violation = True
            if allowed_heading and len(allowed_heading) == 2 and heading is not None:
                # Nếu hướng đi nằm trong allowed_heading thì KHÔNG vi phạm (cho phép cắt qua?)
                # Nhưng opposite_lane thường là cấm hoàn toàn chiều ngược lại.
                # Logic: Nếu xe đang đi hướng ngược lại với làn này -> vi phạm
                pass
            
            if is_violation:
                violations.append({
                    'type': 'opposite_lane',
                    'roi_name': roi.get('name', 'Unknown'),
                    'roi_type': roi_type,
                    'severity': 'critical',
                    'message': 'Xe đi vào làn ngược chiều',
                })
    
    return violations


def check_stopline(track: Dict[str, Any], rois: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Kiểm tra vi phạm vạch dừng
    
    Args:
        track: Track object với center_history
        rois: List of ROI objects
        
    Returns:
        List of violations
    """
    violations = []
    center_history = track.get('center_history', [])
    
    if len(center_history) < 2:
        return violations
    
    # Lấy 2 điểm gần nhất
    p1 = center_history[-2]
    p2 = center_history[-1]
    
    for roi in rois:
        roi_type = roi.get('roi_type', '')
        
        if roi_type != 'stopline':
            continue
        
        points = roi.get('coordinates', [])
        if len(points) != 2:
            continue
        
        # Stopline là đoạn thẳng 2 điểm
        q1 = (points[0]['x'], points[0]['y']) if isinstance(points[0], dict) else points[0]
        q2 = (points[1]['x'], points[1]['y']) if isinstance(points[1], dict) else points[1]
        
        # Kiểm tra đường đi có cắt stopline không
        if segment_intersects_segment(p1, p2, q1, q2):
            violations.append({
                'type': 'stopline_cross',
                'roi_name': roi.get('name', 'Unknown'),
                'roi_type': roi_type,
                'severity': 'high',
                'message': 'Xe vượt vạch dừng',
            })
    
    return violations


def check_solid_line(track: Dict[str, Any], rois: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Kiểm tra vi phạm vạch kẻ liền
    
    Args:
        track: Track object với center_history
        rois: List of ROI objects
        
    Returns:
        List of violations
    """
    violations = []
    center_history = track.get('center_history', [])
    
    if len(center_history) < 2:
        return violations
    
    # Lấy 2 điểm gần nhất
    p1 = center_history[-2]
    p2 = center_history[-1]
    
    for roi in rois:
        roi_type = roi.get('roi_type', '')
        
        if roi_type != 'solid_line':
            continue
        
        points = roi.get('coordinates', [])
        if len(points) != 2:
            continue
        
        # Solid line là đoạn thẳng 2 điểm
        q1 = (points[0]['x'], points[0]['y']) if isinstance(points[0], dict) else points[0]
        q2 = (points[1]['x'], points[1]['y']) if isinstance(points[1], dict) else points[1]
        
        # Kiểm tra đường đi có cắt solid line không
        if segment_intersects_segment(p1, p2, q1, q2):
            violations.append({
                'type': 'solid_line_cross',
                'roi_name': roi.get('name', 'Unknown'),
                'roi_type': roi_type,
                'severity': 'medium',
                'message': 'Xe cắt qua vạch liền',
            })
    
    return violations


def check_red_light(
    track: Dict[str, Any],
    rois: List[Dict[str, Any]],
    traffic_state: Optional[Dict[str, str]] = None
) -> List[Dict[str, Any]]:
    """
    Kiểm tra vi phạm vượt đèn đỏ
    
    Args:
        track: Track object
        rois: List of ROI objects
        traffic_state: Dict mapping traffic_light_name -> state ("red", "yellow", "green")
        
    Returns:
        List of violations
    """
    violations = []
    
    if not traffic_state:
        return violations
    
    center_history = track.get('center_history', [])
    
    if len(center_history) < 2:
        return violations
    
    # Lấy 2 điểm gần nhất
    p1 = center_history[-2]
    p2 = center_history[-1]
    
    # Tìm stopline liên quan đến traffic light đang đỏ
    for roi in rois:
        roi_type = roi.get('roi_type', '')
        
        if roi_type != 'stopline':
            continue
        
        # Kiểm tra metadata có related_light không
        metadata = roi.get('metadata', {})
        related_light = metadata.get('related_light')
        
        if not related_light:
            continue
        
        # Kiểm tra đèn có đỏ không
        light_state = traffic_state.get(related_light, 'unknown')
        
        if light_state != 'red':
            continue
        
        # Kiểm tra có vượt stopline không
        points = roi.get('coordinates', [])
        if len(points) != 2:
            continue
        
        q1 = (points[0]['x'], points[0]['y']) if isinstance(points[0], dict) else points[0]
        q2 = (points[1]['x'], points[1]['y']) if isinstance(points[1], dict) else points[1]
        
        if segment_intersects_segment(p1, p2, q1, q2):
            violations.append({
                'type': 'red_light',
                'roi_name': roi.get('name', 'Unknown'),
                'roi_type': roi_type,
                'severity': 'critical',
                'message': f'Xe vượt đèn đỏ ({related_light})',
            })
    
    return violations

# ===================== NEW RULE ENGINE FUNCTIONS =====================

def red_light_rule(vehicle: VehicleState, ctx: ViolationContext) -> Optional[ViolationEvent]:
    """
    Rule: Red light violation - vehicle crossed stopline when traffic light is red
    
    Args:
        vehicle: VehicleState object with track history
        ctx: ViolationContext with traffic light states and ROIs
        
    Returns:
        ViolationEvent if violation detected, None otherwise
    """
    # Check if vehicle has crossed any stoplines
    for line_name in vehicle.crossed_lines:
        roi = ctx.rois.get(line_name)
        if not roi or roi.get("type") != "stopline":
            continue

        # Get related traffic light from metadata
        related_light_name = roi.get("metadata", {}).get("related_light")
        if not related_light_name:
            continue

        # Check if traffic light is red
        light_state = ctx.traffic_lights.get(related_light_name)
        if light_state == "red":
            return ViolationEvent(
                track_id=vehicle.track_id,
                violation_type="red_light",
                frame_idx=ctx.frame_idx,
                timestamp=ctx.timestamp,
                details={
                    "stopline": line_name,
                    "traffic_light": related_light_name,
                    "light_state": light_state,
                    "vehicle_class": vehicle.cls
                }
            )
    
    return None

def solid_line_rule(vehicle: VehicleState, ctx: ViolationContext) -> Optional[ViolationEvent]:
    """
    Rule: Solid line violation - vehicle crossed solid line
    
    Args:
        vehicle: VehicleState object
        ctx: ViolationContext with ROIs
        
    Returns:
        ViolationEvent if violation detected, None otherwise
    """
    # Check if vehicle has crossed any solid lines
    for line_name in vehicle.crossed_lines:
        roi = ctx.rois.get(line_name)
        if not roi or roi.get("type") != "solid_line":
            continue

        return ViolationEvent(
            track_id=vehicle.track_id,
            violation_type="solid_line",
            frame_idx=ctx.frame_idx,
            timestamp=ctx.timestamp,
            details={
                "solid_line": line_name,
                "vehicle_class": vehicle.cls
            }
        )
    
    return None

def forbidden_area_rule(vehicle: VehicleState, ctx: ViolationContext) -> Optional[ViolationEvent]:
    """
    Rule: Forbidden area violation - vehicle entered forbidden area
    
    Args:
        vehicle: VehicleState object
        ctx: ViolationContext with ROIs
        
    Returns:
        ViolationEvent if violation detected, None otherwise
    """
    # Check if vehicle is currently in any forbidden areas
    for roi_name in vehicle.current_rois:
        roi = ctx.rois.get(roi_name)
        if not roi or roi.get("type") != "forbidden_area":
            continue

        return ViolationEvent(
            track_id=vehicle.track_id,
            violation_type="forbidden_area",
            frame_idx=ctx.frame_idx,
            timestamp=ctx.timestamp,
            details={
                "forbidden_area": roi_name,
                "vehicle_class": vehicle.cls
            }
        )
    
    return None