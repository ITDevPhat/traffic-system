"""
Plate Utils - Xử lý biển số xe Việt Nam

Features:
- Deskew và crop biển số
- Xử lý biển số 1 dòng và 2 dòng
- Normalize text (O↔0, I↔1, xóa ký tự rác)
- Validate format biển số Việt Nam
"""

import re
import cv2
import numpy as np
from typing import Tuple, Optional

# Vietnam plate formats
VN_PLATE_REGEXES = [
    r"[0-9]{2}[A-Z][0-9]{3}\.[0-9]{2}",      # 59A123.45 (standard 1-line)
    r"[0-9]{2}[A-Z]{1}[0-9]{4,5}",           # 59A12345 (standard without dots)
    r"[0-9]{2}[A-Z]{2}[0-9]{3}\.[0-9]{2}",   # 59AB123.45 (2-letter province)
    r"[0-9]{2}[A-Z]{1}[0-9]{3}[0-9]{2}",     # 59A12345 (no separator)
]


def deskew_and_crop(img: np.ndarray) -> np.ndarray:
    """
    Deskew (straighten) và crop biển số.
    
    Sử dụng contour detection để tìm vùng biển số và
    perspective transform để straighten.
    
    Args:
        img: Input image (BGR)
    
    Returns:
        Deskewed and cropped image
    """
    if img is None or img.size == 0:
        return img
    
    try:
        # Convert to grayscale
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # Denoise với bilateral filter (preserve edges)
        gray = cv2.bilateralFilter(gray, 9, 75, 75)
        
        # Adaptive threshold
        thr = cv2.adaptiveThreshold(
            gray, 255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            31, 15
        )
        
        # Find contours
        contours, _ = cv2.findContours(
            thr,
            cv2.RETR_EXTERNAL,
            cv2.CHAIN_APPROX_SIMPLE
        )
        
        if not contours:
            return img
        
        # Get largest contour
        c = max(contours, key=cv2.contourArea)
        rect = cv2.minAreaRect(c)
        box = cv2.boxPoints(rect).astype(np.float32)
        
        # Get width and height
        w, h = int(rect[1][0]), int(rect[1][1])
        if w == 0 or h == 0:
            return img
        
        # Destination points for perspective transform
        dst_pts = np.array([
            [0, h - 1],
            [0, 0],
            [w - 1, 0],
            [w - 1, h - 1]
        ], dtype=np.float32)
        
        # Perspective transform
        M = cv2.getPerspectiveTransform(box, dst_pts)
        warped = cv2.warpPerspective(img, M, (w, h))
        
        # Rotate if width < height (vertical plate)
        if w < h:
            warped = cv2.rotate(warped, cv2.ROTATE_90_CLOCKWISE)
        
        return warped
    
    except Exception as e:
        # If deskew fails, return original
        return img


def split_two_lines(img: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    """
    Tách biển số 2 dòng thành 2 phần: trên và dưới.
    
    Args:
        img: Input plate image
    
    Returns:
        (upper_half, lower_half)
    """
    h = img.shape[0]
    upper = img[:h // 2, :]
    lower = img[h // 2:, :]
    return upper, lower


def normalize_plate_text(text: str) -> str:
    """
    Chuẩn hóa text biển số:
    - Uppercase
    - Remove spaces, hyphens
    - O → 0, I → 1 (common OCR errors)
    - Z → 2, S → 5 (trong một số trường hợp)
    - Remove special characters (giữ lại A-Z, 0-9)
    
    Args:
        text: Raw OCR text
    
    Returns:
        Normalized text
    """
    t = text.upper()
    
    # Remove separators
    t = t.replace(" ", "").replace("-", "")
    
    # Common OCR error corrections
    t = t.replace("O", "0")  # Letter O → Number 0
    t = t.replace("I", "1")  # Letter I → Number 1
    
    # Less common but possible
    # t = t.replace("Z", "2")  # Sometimes Z looks like 2
    # t = t.replace("S", "5")  # Sometimes S looks like 5
    
    # Remove dots and special chars (keep only alphanumeric)
    # But keep dots for validation
    # t = re.sub(r"[^A-Z0-9]", "", t)
    
    return t


def validate_plate(text: str) -> bool:
    """
    Kiểm tra xem text có match format biển số VN không.
    
    Formats:
    - 59A123.45 (standard)
    - 59A12345 (no dot)
    - 59AB123.45 (2-letter province)
    
    Args:
        text: Normalized plate text
    
    Returns:
        True if valid format, False otherwise
    """
    for regex in VN_PLATE_REGEXES:
        if re.fullmatch(regex, text):
            return True
    
    # Fallback: loose validation (at least has format-like structure)
    # 2 digits + 1-2 letters + 4-5 digits
    loose_pattern = r"[0-9]{2}[A-Z]{1,2}[0-9]{4,5}"
    if re.fullmatch(loose_pattern, text):
        return True
    
    return False


def format_plate_display(text: str) -> str:
    """
    Format plate text cho display (thêm dấu chấm nếu thiếu).
    
    Example: 59A12345 → 59A-123.45
    
    Args:
        text: Normalized plate text
    
    Returns:
        Formatted plate text
    """
    # Remove existing separators
    t = text.replace("-", "").replace(".", "").replace(" ", "")
    
    # Try to match standard format: 2 digits + 1-2 letters + 4-5 digits
    match = re.match(r"([0-9]{2})([A-Z]{1,2})([0-9]{3})([0-9]{2})", t)
    if match:
        province, letter, first_part, second_part = match.groups()
        return f"{province}{letter}-{first_part}.{second_part}"
    
    # If doesn't match, return as-is
    return text


def preprocess_plate_for_ocr(img: np.ndarray) -> np.ndarray:
    """
    Tiền xử lý biển số trước khi OCR để tăng accuracy.
    
    - Resize to optimal size
    - Enhance contrast
    - Denoise
    
    Args:
        img: Input plate crop
    
    Returns:
        Preprocessed image
    """
    if img is None or img.size == 0:
        return img
    
    try:
        # Resize to reasonable size (width ~300px)
        h, w = img.shape[:2]
        if w > 300:
            ratio = 300 / w
            new_h = int(h * ratio)
            img = cv2.resize(img, (300, new_h), interpolation=cv2.INTER_CUBIC)
        
        # Convert to grayscale if BGR
        if len(img.shape) == 3:
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        else:
            gray = img
        
        # Enhance contrast with CLAHE
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(gray)
        
        # Denoise
        denoised = cv2.fastNlMeansDenoising(enhanced, h=10)
        
        # Threshold (optional, depends on OCR method)
        # _, thresh = cv2.threshold(denoised, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        return denoised
    
    except Exception as e:
        return img


def is_two_line_plate(img: np.ndarray) -> bool:
    """
    Heuristic để detect biển số 2 dòng.
    
    Biển số 2 dòng thường có aspect ratio gần 1:1 hoặc cao hơn rộng.
    Biển số 1 dòng có aspect ratio ~2-3:1 (rộng hơn cao).
    
    Args:
        img: Plate image
    
    Returns:
        True if likely 2-line plate
    """
    h, w = img.shape[:2]
    aspect_ratio = w / h if h > 0 else 999
    
    # If width/height < 1.5, likely 2-line
    return aspect_ratio < 1.5

