import math
from typing import List, Tuple, Optional
import cv2
import numpy as np

Point = Tuple[int, int]


def dist(p1: Point, p2: Point) -> float:
    return math.hypot(p1[0] - p2[0], p1[1] - p2[1])


def near(p1: Point, p2: Point, thresh: float = 10.0) -> bool:
    return dist(p1, p2) <= thresh


def to_np(points: List[Point]) -> np.ndarray:
    if not points:
        return np.zeros((0, 1, 2), dtype=np.int32)
    return np.array(points, dtype=np.int32).reshape((-1, 1, 2))


def draw_polygon(img: np.ndarray, points: List[Point], color=(0, 255, 255), thickness=2, closed=True):
    if len(points) >= 2:
        cv2.polylines(img, [to_np(points)], closed, color, thickness, lineType=cv2.LINE_AA)


def fill_polygon(img: np.ndarray, points: List[Point], color=(0, 255, 255), alpha=0.2):
    if len(points) < 3:
        return
    overlay = img.copy()
    cv2.fillPoly(overlay, [to_np(points)], color)
    cv2.addWeighted(overlay, alpha, img, 1 - alpha, 0, img)


def draw_line(img: np.ndarray, p1: Point, p2: Point, color=(0, 0, 255), thickness=2):
    cv2.line(img, p1, p2, color, thickness, lineType=cv2.LINE_AA)


def draw_rect(img: np.ndarray, p1: Point, p2: Point, color=(255, 255, 255), thickness=2):
    cv2.rectangle(img, p1, p2, color, thickness, lineType=cv2.LINE_AA)


def draw_circle(img: np.ndarray, center: Point, radius: int, color=(255, 255, 255), thickness=2):
    cv2.circle(img, center, radius, color, thickness, lineType=cv2.LINE_AA)


def draw_text(img: np.ndarray, text: str, org: Point, color=(255, 255, 255)):
    cv2.putText(img, text, org, cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2, cv2.LINE_AA)


def arrow_for_heading(center: Point, heading_deg: float, length: int = 60) -> Tuple[Point, Point]:
    rad = math.radians(heading_deg)
    dx = int(math.cos(rad) * length)
    dy = int(math.sin(rad) * length)
    # Image Y increases downward, so invert dy
    return center, (center[0] + dx, center[1] - dy)


def draw_heading(img: np.ndarray, center: Point, heading_deg: float, color=(0, 255, 255)):
    p1, p2 = arrow_for_heading(center, heading_deg)
    cv2.arrowedLine(img, p1, p2, color, 2, tipLength=0.2)


def point_in_polygon(pt: Point, polygon: List[Point]) -> bool:
    # Ray casting algorithm
    x, y = pt
    inside = False
    n = len(polygon)
    if n < 3:
        return False
    for i in range(n):
        x1, y1 = polygon[i]
        x2, y2 = polygon[(i + 1) % n]
        if ((y1 > y) != (y2 > y)):
            xinters = (x2 - x1) * (y - y1) / (y2 - y1 + 1e-9) + x1
            if x < xinters:
                inside = not inside
    return inside


def point_on_line_segment(pt: Point, a: Point, b: Point, tol: float = 3.0) -> bool:
    # Distance to segment
    px, py = pt
    ax, ay = a
    bx, by = b
    abx, aby = bx - ax, by - ay
    apx, apy = px - ax, py - ay
    ab_len2 = abx * abx + aby * aby
    if ab_len2 == 0:
        return dist(pt, a) <= tol
    t = max(0.0, min(1.0, (apx * abx + apy * aby) / ab_len2))
    cx, cy = ax + t * abx, ay + t * aby
    return dist(pt, (int(cx), int(cy))) <= tol


def rect_from_points(p1: Point, p2: Point) -> Tuple[Point, Point]:
    x1, y1 = p1
    x2, y2 = p2
    return (min(x1, x2), min(y1, y2)), (max(x1, x2), max(y1, y2))


def clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))
