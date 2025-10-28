"""
ROI Utils - Region of Interest utilities

Features:
- Point in polygon detection
- Centroid calculation
- Line crossing detection
- ROI visualization
"""

import numpy as np
import cv2
from typing import List, Tuple, Optional


def point_in_polygon(pt: Tuple[float, float], polygon: List[List[float]]) -> bool:
    """
    Kiểm tra xem điểm có nằm trong polygon không.
    
    Args:
        pt: (x, y) tuple
        polygon: List of [x, y] coordinates defining polygon vertices
    
    Returns:
        True if point is inside polygon
    """
    if not polygon or len(polygon) < 3:
        return False
    
    try:
        contour = np.array(polygon, dtype=np.int32)
        result = cv2.pointPolygonTest(
            contour,
            (int(pt[0]), int(pt[1])),
            False
        )
        return result >= 0  # >= 0 means inside or on edge
    except Exception:
        return False


def centroid_of_bbox(x1: float, y1: float, x2: float, y2: float) -> Tuple[float, float]:
    """
    Tính tâm của bounding box.
    
    Args:
        x1, y1, x2, y2: Bounding box coordinates
    
    Returns:
        (cx, cy) center point
    """
    cx = (x1 + x2) / 2.0
    cy = (y1 + y2) / 2.0
    return (cx, cy)


def bottom_center_of_bbox(x1: float, y1: float, x2: float, y2: float) -> Tuple[float, float]:
    """
    Tính điểm giữa cạnh dưới của bounding box.
    Useful cho vehicle tracking (position at ground level).
    
    Args:
        x1, y1, x2, y2: Bounding box coordinates
    
    Returns:
        (cx, y2) bottom center point
    """
    cx = (x1 + x2) / 2.0
    return (cx, y2)


def line_crossing_detection(
    prev_pos: Tuple[float, float],
    curr_pos: Tuple[float, float],
    line_start: Tuple[float, float],
    line_end: Tuple[float, float]
) -> bool:
    """
    Phát hiện xem vehicle có cross qua line không.
    
    Sử dụng line segment intersection để detect crossing.
    
    Args:
        prev_pos: Previous position (x, y)
        curr_pos: Current position (x, y)
        line_start: Line start point (x, y)
        line_end: Line end point (x, y)
    
    Returns:
        True if vehicle crossed the line
    """
    def ccw(A, B, C):
        """Counter-clockwise test"""
        return (C[1] - A[1]) * (B[0] - A[0]) > (B[1] - A[1]) * (C[0] - A[0])
    
    def intersect(A, B, C, D):
        """Check if line segments AB and CD intersect"""
        return ccw(A, C, D) != ccw(B, C, D) and ccw(A, B, C) != ccw(A, B, D)
    
    return intersect(prev_pos, curr_pos, line_start, line_end)


def bbox_iou(box1: Tuple[float, float, float, float],
             box2: Tuple[float, float, float, float]) -> float:
    """
    Tính IoU (Intersection over Union) của 2 bounding boxes.
    
    Args:
        box1: (x1, y1, x2, y2)
        box2: (x1, y1, x2, y2)
    
    Returns:
        IoU score (0-1)
    """
    x1_1, y1_1, x2_1, y2_1 = box1
    x1_2, y1_2, x2_2, y2_2 = box2
    
    # Intersection rectangle
    xi1 = max(x1_1, x1_2)
    yi1 = max(y1_1, y1_2)
    xi2 = min(x2_1, x2_2)
    yi2 = min(y2_1, y2_2)
    
    inter_area = max(0, xi2 - xi1) * max(0, yi2 - yi1)
    
    # Union area
    box1_area = (x2_1 - x1_1) * (y2_1 - y1_1)
    box2_area = (x2_2 - x1_2) * (y2_2 - y1_2)
    union_area = box1_area + box2_area - inter_area
    
    if union_area == 0:
        return 0.0
    
    return inter_area / union_area


def draw_polygon_on_frame(
    frame: np.ndarray,
    polygon: List[List[float]],
    color: Tuple[int, int, int] = (0, 255, 0),
    thickness: int = 2,
    alpha: float = 0.3
) -> np.ndarray:
    """
    Vẽ polygon lên frame với transparency.
    
    Args:
        frame: Input frame
        polygon: List of [x, y] coordinates
        color: BGR color
        thickness: Line thickness
        alpha: Transparency (0-1)
    
    Returns:
        Frame with polygon drawn
    """
    if not polygon or len(polygon) < 3:
        return frame
    
    overlay = frame.copy()
    pts = np.array(polygon, dtype=np.int32)
    
    # Fill polygon với alpha blending
    cv2.fillPoly(overlay, [pts], color)
    
    # Blend với original frame
    cv2.addWeighted(overlay, alpha, frame, 1 - alpha, 0, frame)
    
    # Draw outline
    cv2.polylines(frame, [pts], True, color, thickness)
    
    return frame


def draw_line_on_frame(
    frame: np.ndarray,
    start: Tuple[float, float],
    end: Tuple[float, float],
    color: Tuple[int, int, int] = (0, 0, 255),
    thickness: int = 3
) -> np.ndarray:
    """
    Vẽ line lên frame.
    
    Args:
        frame: Input frame
        start: (x, y) start point
        end: (x, y) end point
        color: BGR color
        thickness: Line thickness
    
    Returns:
        Frame with line drawn
    """
    pt1 = (int(start[0]), int(start[1]))
    pt2 = (int(end[0]), int(end[1]))
    cv2.line(frame, pt1, pt2, color, thickness)
    return frame


def calculate_distance(pt1: Tuple[float, float], pt2: Tuple[float, float]) -> float:
    """
    Tính khoảng cách Euclidean giữa 2 điểm.
    
    Args:
        pt1: (x, y)
        pt2: (x, y)
    
    Returns:
        Distance in pixels
    """
    return np.sqrt((pt2[0] - pt1[0])**2 + (pt2[1] - pt1[1])**2)


def normalize_polygon_coords(
    polygon: List[List[float]],
    img_width: int,
    img_height: int
) -> List[List[float]]:
    """
    Normalize polygon coordinates to 0-1 range.
    Useful cho lưu trong database (independent của resolution).
    
    Args:
        polygon: List of [x, y] absolute coordinates
        img_width: Image width
        img_height: Image height
    
    Returns:
        Normalized polygon coordinates
    """
    normalized = []
    for pt in polygon:
        x_norm = pt[0] / img_width if img_width > 0 else 0
        y_norm = pt[1] / img_height if img_height > 0 else 0
        normalized.append([x_norm, y_norm])
    return normalized


def denormalize_polygon_coords(
    polygon: List[List[float]],
    img_width: int,
    img_height: int
) -> List[List[float]]:
    """
    Denormalize polygon coordinates từ 0-1 range về absolute pixels.
    
    Args:
        polygon: List of [x, y] normalized coordinates (0-1)
        img_width: Target image width
        img_height: Target image height
    
    Returns:
        Denormalized polygon coordinates
    """
    denormalized = []
    for pt in polygon:
        x_abs = pt[0] * img_width
        y_abs = pt[1] * img_height
        denormalized.append([x_abs, y_abs])
    return denormalized

