"""
Geometry utilities for violation detection
Các hàm tính toán hình học: point-in-polygon, line intersection, distance, etc.
"""

import math
from typing import Tuple, List


def point_in_polygon(point: Tuple[float, float], polygon: List[Tuple[float, float]]) -> bool:
    """
    Kiểm tra điểm có nằm trong polygon không (Ray casting algorithm)
    
    Args:
        point: (x, y) điểm cần kiểm tra
        polygon: List of (x, y) các đỉnh polygon
        
    Returns:
        True nếu điểm nằm trong polygon
    """
    if len(polygon) < 3:
        return False
    
    x, y = point
    inside = False
    
    j = len(polygon) - 1
    for i in range(len(polygon)):
        xi, yi = polygon[i]
        xj, yj = polygon[j]
        
        if ((yi > y) != (yj > y)) and (x < (xj - xi) * (y - yi) / (yj - yi) + xi):
            inside = not inside
        
        j = i
    
    return inside


def distance_point_to_line(
    point: Tuple[float, float],
    line_p1: Tuple[float, float],
    line_p2: Tuple[float, float]
) -> float:
    """
    Tính khoảng cách từ điểm đến đoạn thẳng
    
    Args:
        point: (x, y) điểm
        line_p1: (x, y) điểm đầu đoạn thẳng
        line_p2: (x, y) điểm cuối đoạn thẳng
        
    Returns:
        Khoảng cách (pixels)
    """
    x0, y0 = point
    x1, y1 = line_p1
    x2, y2 = line_p2
    
    # Vector từ p1 đến p2
    dx = x2 - x1
    dy = y2 - y1
    
    # Độ dài đoạn thẳng
    length_sq = dx * dx + dy * dy
    
    if length_sq == 0:
        # p1 và p2 trùng nhau
        return math.sqrt((x0 - x1) ** 2 + (y0 - y1) ** 2)
    
    # Tính projection của point lên line
    t = max(0, min(1, ((x0 - x1) * dx + (y0 - y1) * dy) / length_sq))
    
    # Điểm gần nhất trên đoạn thẳng
    proj_x = x1 + t * dx
    proj_y = y1 + t * dy
    
    # Khoảng cách
    return math.sqrt((x0 - proj_x) ** 2 + (y0 - proj_y) ** 2)


def segment_intersects_segment(
    p1: Tuple[float, float],
    p2: Tuple[float, float],
    q1: Tuple[float, float],
    q2: Tuple[float, float]
) -> bool:
    """
    Kiểm tra 2 đoạn thẳng có cắt nhau không
    
    Args:
        p1, p2: Đoạn thẳng 1
        q1, q2: Đoạn thẳng 2
        
    Returns:
        True nếu 2 đoạn thẳng cắt nhau
    """
    def ccw(a, b, c):
        """Counter-clockwise test"""
        return (c[1] - a[1]) * (b[0] - a[0]) > (b[1] - a[1]) * (c[0] - a[0])
    
    return ccw(p1, q1, q2) != ccw(p2, q1, q2) and ccw(p1, p2, q1) != ccw(p1, p2, q2)


def calculate_heading(
    p1: Tuple[float, float],
    p2: Tuple[float, float]
) -> float:
    """
    Tính góc hướng di chuyển từ p1 đến p2 (degrees, 0-360)
    0° = North (lên trên), 90° = East (sang phải), 180° = South, 270° = West
    
    Args:
        p1: (x, y) điểm trước
        p2: (x, y) điểm sau
        
    Returns:
        Góc (degrees) trong khoảng [0, 360)
    """
    dx = p2[0] - p1[0]
    dy = p1[1] - p2[1]  # Đảo dấu vì y tăng từ trên xuống
    
    angle_rad = math.atan2(dx, dy)
    angle_deg = math.degrees(angle_rad)
    
    # Normalize về [0, 360)
    return (angle_deg + 360) % 360


def is_heading_in_range(
    heading: float,
    allowed_range: Tuple[float, float]
) -> bool:
    """
    Kiểm tra heading có nằm trong range cho phép không
    
    Args:
        heading: Góc hiện tại (0-360)
        allowed_range: (min, max) góc cho phép
        
    Returns:
        True nếu heading nằm trong range
    """
    min_deg, max_deg = allowed_range
    
    # Normalize
    heading = heading % 360
    min_deg = min_deg % 360
    max_deg = max_deg % 360
    
    if min_deg <= max_deg:
        # Range không cross 0°
        return min_deg <= heading <= max_deg
    else:
        # Range cross 0° (ví dụ: 350° - 10°)
        return heading >= min_deg or heading <= max_deg


def bbox_center(bbox: Tuple[float, float, float, float]) -> Tuple[float, float]:
    """
    Tính center của bounding box
    
    Args:
        bbox: (x1, y1, x2, y2)
        
    Returns:
        (cx, cy) center point
    """
    x1, y1, x2, y2 = bbox
    return ((x1 + x2) / 2, (y1 + y2) / 2)


def bbox_intersects_polygon(
    bbox: Tuple[float, float, float, float],
    polygon: List[Tuple[float, float]]
) -> bool:
    """
    Kiểm tra bbox có giao với polygon không
    
    Args:
        bbox: (x1, y1, x2, y2)
        polygon: List of (x, y) points
        
    Returns:
        True nếu có giao nhau
    """
    # Kiểm tra center
    center = bbox_center(bbox)
    if point_in_polygon(center, polygon):
        return True
    
    # Kiểm tra 4 góc bbox
    x1, y1, x2, y2 = bbox
    corners = [(x1, y1), (x2, y1), (x2, y2), (x1, y2)]
    
    for corner in corners:
        if point_in_polygon(corner, polygon):
            return True

    return False


def is_inside_violation_region(bbox: Tuple[float, float, float, float], polygon: List[Tuple[float, float]]):
    """
    Check if bbox center is inside violation region polygon.

    >>> is_inside_violation_region((0, 0, 10, 10), [(0, 0), (10, 0), (10, 10), (0, 10)])
    True
    >>> is_inside_violation_region((20, 20, 30, 30), [(0, 0), (10, 0), (10, 10), (0, 10)])
    False
    """
    if not polygon or len(polygon) < 3:
        return False

    cx, cy = bbox_center(bbox)
    return point_in_polygon((cx, cy), polygon)


def stopline_overlap(bbox: Tuple[float, float, float, float], stopline_band: Tuple[float, float]) -> float:
    """
    Compute vertical overlap ratio between bbox and stopline band (y_min, y_max).

    >>> round(stopline_overlap((0, 0, 10, 10), (4, 6)), 2)
    0.2
    >>> stopline_overlap((0, 10, 10, 20), (0, 5))
    0.0
    """
    if not stopline_band or len(stopline_band) < 2:
        return 0.0

    y1, y2 = stopline_band
    band_min, band_max = min(y1, y2), max(y1, y2)

    x1, y_top, x2, y_bottom = bbox
    height = max(1e-6, y_bottom - y_top)

    overlap_min = max(y_top, band_min)
    overlap_max = min(y_bottom, band_max)

    if overlap_max <= overlap_min:
        return 0.0

    return max(0.0, min(1.0, (overlap_max - overlap_min) / height))


def classify_position(bbox: Tuple[float, float, float, float], stopline_band: Tuple[float, float]) -> str:
    """
    Classify bbox position relative to stopline band using bbox center.

    BEFORE: Center is below the band (larger y)
    ON: Center is inside the band
    AFTER: Center is above the band (smaller y)

    >>> classify_position((0, 0, 10, 10), (4, 6))
    'ON'
    >>> classify_position((0, 6, 10, 16), (4, 6))
    'BEFORE'
    >>> classify_position((0, -10, 10, 0), (4, 6))
    'AFTER'
    """
    if not stopline_band or len(stopline_band) < 2:
        return "BEFORE"

    y1, y2 = stopline_band
    band_min, band_max = min(y1, y2), max(y1, y2)
    _, y_top, _, y_bottom = bbox
    center_y = (y_top + y_bottom) / 2.0

    if band_min <= center_y <= band_max:
        return "ON"
    if center_y > band_max:
        return "BEFORE"
    return "AFTER"
