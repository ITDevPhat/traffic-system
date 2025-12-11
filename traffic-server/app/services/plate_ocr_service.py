"""
Plate OCR Service - Tích hợp OCR module vào pipeline detection
Pipeline: Detect Vehicle → Track → Plate Detect → OCR (với debounce)
Chiến lược: Chỉ OCR khi confidence cao, debounce per track, không lưu trừ khi vi phạm
"""

import cv2
import numpy as np
import time
import logging
from typing import Optional, Dict, List, Tuple
from pathlib import Path
import os

logger = logging.getLogger(__name__)

# Import OCR module
try:
    from app.modules.OCR.core_optimized import LicensePlateDetectorOptimized
    OCR_AVAILABLE = True
except ImportError:
    try:
        from app.modules.OCR.core import LicensePlateDetector as LicensePlateDetectorOptimized
        OCR_AVAILABLE = True
    except ImportError:
        LicensePlateDetectorOptimized = None
        OCR_AVAILABLE = False
        logger.warning("⚠️  OCR module not available")


class PlateOCRService:
    """
    Service xử lý OCR biển số xe với debounce và tối ưu hiệu năng
    
    Features:
    - Debounce OCR per track (tránh OCR liên tục cho cùng 1 xe)
    - In-memory cache cho plate text
    - Chỉ OCR khi plate detection confidence cao
    - Tự động expand bbox trước khi crop (tránh mất ký tự)
    - Hỗ trợ .engine > .onnx > .pt (fallback)
    """
    
    def __init__(
        self,
        model_type: str = 'auto',
        device: str = 'auto',
        plate_conf_threshold: float = 0.6,
        ocr_debounce_sec: float = 1.0,
        min_track_frames: int = 3,
        bbox_expand_ratio: float = 0.15,
        enable_ocr: bool = True
    ):
        """
        Args:
            model_type: 'auto', 'pt', 'onnx', 'engine' (auto sẽ ưu tiên .engine > .onnx > .pt)
            device: 'auto', 'cuda', 'cpu'
            plate_conf_threshold: Ngưỡng confidence cho plate detection (0.6)
            ocr_debounce_sec: Khoảng thời gian tối thiểu giữa 2 lần OCR cho cùng track (1s)
            min_track_frames: Số frame tối thiểu track phải tồn tại trước khi OCR (3)
            bbox_expand_ratio: Tỷ lệ mở rộng bbox trước crop (0.15 = 15%)
            enable_ocr: Bật/tắt OCR (để test performance)
        """
        self.model_type = model_type
        self.device = device
        self.plate_conf_threshold = plate_conf_threshold
        self.ocr_debounce_sec = ocr_debounce_sec
        self.min_track_frames = min_track_frames
        self.bbox_expand_ratio = bbox_expand_ratio
        self.enable_ocr = enable_ocr
        
        # OCR detector
        self.detector: Optional[LicensePlateDetectorOptimized] = None
        
        # In-memory cache
        # track_id -> {"plate": "51A-123.45", "conf": 0.92, "last_ocr_ts": timestamp, "frame_count": N}
        self._track_cache: Dict[int, Dict] = {}
        
        # Stats
        self.stats = {
            'total_ocr_calls': 0,
            'total_ocr_success': 0,
            'total_ocr_failed': 0,
            'total_ocr_skipped_debounce': 0,
            'total_ocr_skipped_min_frames': 0,
            'total_ocr_time': 0.0
        }
        
        # Load model nếu enable
        if self.enable_ocr and OCR_AVAILABLE:
            self._load_model()
        else:
            if not OCR_AVAILABLE:
                logger.warning("⚠️  OCR not available - skipping OCR initialization")
            else:
                logger.info("ℹ️  OCR disabled by config")
    
    def _load_model(self):
        """Load OCR model với fallback .engine > .onnx > .pt"""
        if not OCR_AVAILABLE or LicensePlateDetectorOptimized is None:
            logger.error("❌ OCR module not available")
            return
        
        # Auto-detect model paths (ưu tiên theo thứ tự: engine > onnx > pt)
        model_dir = Path("traffic-server/app/modules/OCR/models")
        if not model_dir.exists():
            model_dir = Path("app/modules/OCR/models")
        if not model_dir.exists():
            logger.error(f"❌ OCR model directory not found: {model_dir}")
            return
        
        detector_paths = {
            'engine': model_dir / "license_plate" / "yolo_plate_v10n.engine",
            'onnx': model_dir / "license_plate" / "yolo_plate_v10n.onnx",
            'pt': model_dir / "license_plate" / "yolo_plate_v10n.pt"
        }
        
        ocr_paths = {
            'engine': model_dir / "ocr" / "yolo_ocr_chars_v10n.engine",
            'onnx': model_dir / "ocr" / "yolo_ocr_chars_v10n.onnx",
            'pt': model_dir / "ocr" / "yolo_ocr_chars_v10n.pt"
        }
        
        # Determine model type
        if self.model_type == 'auto':
            # Ưu tiên: engine > onnx > pt
            for mtype in ['engine', 'onnx', 'pt']:
                if detector_paths[mtype].exists() and ocr_paths[mtype].exists():
                    self.model_type = mtype
                    logger.info(f"🎯 Auto-detected OCR model type: {mtype}")
                    break
            else:
                logger.error("❌ No OCR models found")
                return
        
        detector_path = str(detector_paths[self.model_type])
        ocr_path = str(ocr_paths[self.model_type])
        
        if not Path(detector_path).exists() or not Path(ocr_path).exists():
            logger.error(f"❌ OCR model files not found: {detector_path}, {ocr_path}")
            return
        
        try:
            logger.info(f"⚙️  Loading OCR models ({self.model_type})...")
            logger.info(f"   Detector: {detector_path}")
            logger.info(f"   OCR: {ocr_path}")
            
            self.detector = LicensePlateDetectorOptimized(
                detector_model_path=detector_path,
                ocr_model_path=ocr_path,
                model_type=self.model_type,
                confidence_threshold=self.plate_conf_threshold,
                device=self.device
            )
            
            logger.info(f"✅ OCR models loaded successfully on {self.detector.device.upper()}")
            
        except Exception as e:
            logger.error(f"❌ Failed to load OCR models: {e}")
            self.detector = None
    
    def update_track_frame_count(self, track_id: int):
        """Cập nhật frame count cho track (gọi mỗi khi track được detect)"""
        if track_id not in self._track_cache:
            self._track_cache[track_id] = {
                'plate': None,
                'conf': 0.0,
                'last_ocr_ts': 0.0,
                'frame_count': 0
            }
        self._track_cache[track_id]['frame_count'] += 1
    
    def should_run_ocr(self, track_id: int) -> bool:
        """
        Kiểm tra có nên chạy OCR cho track này không (debounce logic)
        
        Returns:
            True nếu nên chạy OCR, False nếu skip
        """
        if not self.enable_ocr or self.detector is None:
            return False
        
        now = time.time()
        
        # Nếu track chưa tồn tại trong cache, khởi tạo
        if track_id not in self._track_cache:
            self._track_cache[track_id] = {
                'plate': None,
                'conf': 0.0,
                'last_ocr_ts': 0.0,
                'frame_count': 0
            }
        
        cache = self._track_cache[track_id]
        
        # Check 1: Track phải tồn tại >= min_track_frames
        if cache['frame_count'] < self.min_track_frames:
            self.stats['total_ocr_skipped_min_frames'] += 1
            return False
        
        # Check 2: Debounce - không OCR quá thường xuyên
        time_since_last_ocr = now - cache['last_ocr_ts']
        if time_since_last_ocr < self.ocr_debounce_sec:
            self.stats['total_ocr_skipped_debounce'] += 1
            return False
        
        return True
    
    def run_ocr_on_vehicle_crop(
        self,
        frame: np.ndarray,
        vehicle_bbox: List[float],
        track_id: int
    ) -> Optional[Dict]:
        """
        Chạy OCR trên crop của xe (tự động detect plate trong crop)
        
        Args:
            frame: Frame gốc (BGR)
            vehicle_bbox: [x1, y1, x2, y2] của xe
            track_id: Track ID của xe
        
        Returns:
            Dict với {plate: str, conf: float, plate_bbox: [x1,y1,x2,y2]} hoặc None
        """
        if not self.enable_ocr or self.detector is None:
            return None
        
        if not self.should_run_ocr(track_id):
            # Trả về plate cached (nếu có)
            cached = self._track_cache.get(track_id, {})
            if cached.get('plate'):
                return {
                    'plate': cached['plate'],
                    'conf': cached['conf'],
                    'plate_bbox': None,  # Không có bbox vì lấy từ cache
                    'cached': True
                }
            return None
        
        try:
            start_time = time.time()
            
            # Crop vehicle bbox với expand để đảm bảo plate nằm trong crop
            x1, y1, x2, y2 = [int(v) for v in vehicle_bbox]
            h, w = frame.shape[:2]
            
            # Expand bbox
            expand_w = int((x2 - x1) * self.bbox_expand_ratio)
            expand_h = int((y2 - y1) * self.bbox_expand_ratio)
            
            x1 = max(0, x1 - expand_w)
            y1 = max(0, y1 - expand_h)
            x2 = min(w, x2 + expand_w)
            y2 = min(h, y2 + expand_h)
            
            crop = frame[y1:y2, x1:x2]
            
            if crop.size == 0:
                logger.warning(f"⚠️  Empty crop for track {track_id}")
                return None
            
            # Run plate detection + OCR
            result = self.detector.process_image(crop, draw_bbox=False)
            
            ocr_time = time.time() - start_time
            self.stats['total_ocr_calls'] += 1
            self.stats['total_ocr_time'] += ocr_time
            
            if result['success'] and len(result['plates_recognized']) > 0:
                # Lấy plate có confidence cao nhất
                best_plate = max(result['plates_recognized'], key=lambda p: p.get('confidence', 0.0))
                
                plate_text = best_plate['text']
                plate_conf = best_plate['confidence']
                
                # Convert bbox từ crop coords về frame coords
                plate_bbox_crop = best_plate['bbox']
                plate_bbox_frame = [
                    plate_bbox_crop[0] + x1,
                    plate_bbox_crop[1] + y1,
                    plate_bbox_crop[2] + x1,
                    plate_bbox_crop[3] + y1
                ]
                
                # Update cache
                self._track_cache[track_id].update({
                    'plate': plate_text,
                    'conf': plate_conf,
                    'last_ocr_ts': time.time()
                })
                
                self.stats['total_ocr_success'] += 1
                
                logger.info(f"✅ OCR track {track_id}: {plate_text} (conf={plate_conf:.2f}, time={ocr_time:.3f}s)")
                
                return {
                    'plate': plate_text,
                    'conf': plate_conf,
                    'plate_bbox': plate_bbox_frame,
                    'cached': False
                }
            else:
                self.stats['total_ocr_failed'] += 1
                # Update timestamp để tránh retry liên tục
                self._track_cache[track_id]['last_ocr_ts'] = time.time()
                return None
        
        except Exception as e:
            logger.error(f"❌ OCR error for track {track_id}: {e}")
            self.stats['total_ocr_failed'] += 1
            return None
    
    def get_cached_plate(self, track_id: int) -> Optional[Dict]:
        """Lấy plate text từ cache (nếu có)"""
        cached = self._track_cache.get(track_id)
        if cached and cached.get('plate'):
            return {
                'plate': cached['plate'],
                'conf': cached['conf'],
                'cached': True
            }
        return None
    
    def cleanup_old_tracks(self, active_track_ids: List[int], max_age_sec: float = 5.0):
        """Xóa tracks cũ khỏi cache (gọi định kỳ để tránh memory leak)"""
        now = time.time()
        to_remove = []
        
        for tid, cache in self._track_cache.items():
            if tid not in active_track_ids:
                # Track không còn active, check age
                age = now - cache.get('last_ocr_ts', now)
                if age > max_age_sec:
                    to_remove.append(tid)
        
        for tid in to_remove:
            del self._track_cache[tid]
        
        if to_remove:
            logger.info(f"🧹 Cleaned {len(to_remove)} old tracks from OCR cache")
    
    def get_stats(self) -> Dict:
        """Lấy thống kê OCR"""
        stats = self.stats.copy()
        if stats['total_ocr_calls'] > 0:
            stats['avg_ocr_time'] = stats['total_ocr_time'] / stats['total_ocr_calls']
            stats['success_rate'] = stats['total_ocr_success'] / stats['total_ocr_calls']
        else:
            stats['avg_ocr_time'] = 0.0
            stats['success_rate'] = 0.0
        
        stats['cache_size'] = len(self._track_cache)
        return stats
    
    def reset_stats(self):
        """Reset stats"""
        self.stats = {
            'total_ocr_calls': 0,
            'total_ocr_success': 0,
            'total_ocr_failed': 0,
            'total_ocr_skipped_debounce': 0,
            'total_ocr_skipped_min_frames': 0,
            'total_ocr_time': 0.0
        }


# Global singleton instance (lazy initialization)
_ocr_service: Optional[PlateOCRService] = None


def get_ocr_service(
    model_type: str = 'auto',
    device: str = 'auto',
    enable_ocr: bool = True,
    force_reload: bool = False
) -> Optional[PlateOCRService]:
    """
    Get global OCR service instance (singleton)
    
    Args:
        model_type: 'auto', 'pt', 'onnx', 'engine'
        device: 'auto', 'cuda', 'cpu'
        enable_ocr: Enable/disable OCR
        force_reload: Force reload model (for testing)
    
    Returns:
        PlateOCRService instance hoặc None nếu OCR không available
    """
    global _ocr_service
    
    if _ocr_service is None or force_reload:
        if not OCR_AVAILABLE:
            logger.warning("⚠️  OCR module not available")
            return None
        
        logger.info("🔧 Initializing global OCR service...")
        _ocr_service = PlateOCRService(
            model_type=model_type,
            device=device,
            enable_ocr=enable_ocr
        )
    
    return _ocr_service


def recognize_plate_from_crop(crop_bgr: np.ndarray) -> tuple[str | None, float | None]:
    """
    Nhận 1 ảnh crop (BGR) và trả về (plate_text, plate_confidence).

    Args:
        crop_bgr: Ảnh crop BGR chứa vùng biển số/xe.

    Returns:
        Tuple (text, confidence) hoặc (None, None) nếu không nhận dạng được.
    """
    if crop_bgr is None or crop_bgr.size == 0:
        return None, None

    service = get_ocr_service(enable_ocr=True)
    if service is None or service.detector is None:
        logger.warning("[PLATE-OCR] OCR service not available, skipping plate recognition")
        return None, None

    try:
        result = service.detector.process_image(crop_bgr, draw_bbox=False)
    except Exception as exc:
        logger.warning(f"[PLATE-OCR] Failed to run OCR on crop: {exc}")
        return None, None

    plates = result.get('plates_recognized') if isinstance(result, dict) else None
    if not plates:
        return None, None

    best_plate = max(plates, key=lambda p: p.get('confidence', 0.0))
    text = (best_plate.get('text') or '').strip()
    confidence = best_plate.get('confidence')

    if not text:
        return None, None

    return text, float(confidence) if confidence is not None else None

