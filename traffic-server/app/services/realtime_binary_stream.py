"""
Binary Annotation Stream - 30 FPS với TurboJPEG + Multithreading
Pipeline: Capture → Infer/Track → Annotate+Encode → Send
Queues: Latest-wins (drop old frames when full)
"""
import cv2
import time
import numpy as np
import logging
from typing import Optional, Tuple, List
from queue import Queue, Empty
from threading import Thread, Event, Lock
import os

logger = logging.getLogger(__name__)

# Global YOLO model cache to avoid re-loading on each connection
GLOBAL_YOLO_MODEL = None
GLOBAL_YOLO_DEVICE = None
GLOBAL_YOLO_PATH = None

try:
    import torch
    from ultralytics import YOLO
except Exception as e:
    logger.error(f"Failed to import YOLO/torch: {e}")
    torch = None
    YOLO = None

# ByteTrack (boxmot) - preferred
try:
    from boxmot.trackers.bytetrack.byte_tracker import BYTETracker
    HAVE_BOXMOT = True
    logger.info("✅ Using boxmot BYTETracker")
except Exception:
    BYTETracker = None
    HAVE_BOXMOT = False
    logger.info("⚠️  boxmot not available, using ultralytics built-in tracker")

# TurboJPEG - required for 30 FPS
try:
    from turbojpeg import TurboJPEG
    # Optional flags/constants for faster encoding and smaller size
    try:
        from turbojpeg import TJSAMP_420, TJSAMP_422, TJSAMP_444, TJFLAG_FASTDCT
    except Exception:
        TJSAMP_420 = None
        TJSAMP_422 = None
        TJSAMP_444 = None
        TJFLAG_FASTDCT = 0
    HAVE_TURBOJPEG = True
    logger.info("✅ TurboJPEG available")
except Exception:
    HAVE_TURBOJPEG = False
    logger.warning("⚠️  TurboJPEG not available, falling back to cv2.imencode (slower)")

from app.utils.roi_utils import draw_polygon_on_frame, point_in_polygon
from app.utils.model_loader import load_yolo_model, get_model_info

# Custom YOLO model class IDs (0-indexed, not COCO)
# User's model: 0=bus, 1=car, 2=bike, 3=truck
VEHICLE_IDS = {0, 1, 2, 3}  # bus, car, bike, truck

# Class names (match your custom model)
CLASS_NAMES = {
    0: "bus",
    1: "car", 
    2: "bike",    # Fixed: was "motorbike"
    3: "truck"
}

# Colors for different classes (BGR format)
# Match DetectionCardRealtime.jsx color scheme
CLASS_COLORS = {
    0: (34, 126, 230),   # bus - orange (#e67e22 in BGR)
    1: (219, 152, 52),   # car - blue (#3498db in BGR)
    2: (113, 204, 46),   # bike - green (#2ecc71 in BGR)
    3: (60, 76, 231)     # truck - red (#e74c3c in BGR)
}

ROI_COLORS = [
    (50, 205, 50),
    (60, 180, 255),
    (255, 165, 0),
    (147, 112, 219),
    (255, 99, 71),
]


class BinaryAnnotStream:
    """
    Multithreaded binary stream for 30 FPS
    
    Pipeline:
    1. Thread 1 (Capture): Read frames from video → q_cap
    2. Thread 2 (Infer): YOLO + ByteTrack → q_det
    3. Thread 3 (Encode): Annotate + TurboJPEG → q_enc
    4. Main thread (Send): Send via WebSocket with pacing
    
    All queues use "latest-wins" strategy (drop old when full)
    """
    
    def __init__(
        self,
        source: str,
        conf: float = 0.35,
        imgsz: int = 640,
        target_fps: int = 30,
        jpeg_quality: int = 60,
        encode_width: int = 960,
        model_path: Optional[str] = None,
        veh_detect_hz: int = 25,
        enable_yolo: bool = True,
        enable_tracking: bool = True,
        enable_bbox_drawing: bool = True,
        enable_roi: bool = True,
        enable_roi_drawing: bool = True,
        force_gpu: bool = True
    ):
        """
        Args:
            source: "0" for webcam, path for video file
            conf: Confidence threshold
            imgsz: YOLO inference size (480/640/960)
            target_fps: Target FPS (default 30)
            jpeg_quality: JPEG quality (1-100, lower=faster)
            encode_width: Downscale width before encoding
            model_path: Path to YOLO model
            enable_yolo: Enable YOLO detection
            enable_tracking: Enable ByteTrack tracking
            enable_bbox_drawing: Enable bbox drawing on frames
            enable_roi: Enable ROI module (for future use)
            enable_roi_drawing: Enable ROI drawing on frames (for future use)
            force_gpu: Require CUDA-capable GPU (raises if unavailable when True)
        """
        self.source = int(source) if source.isdigit() else source
        self.conf = float(conf)
        self.imgsz = int(imgsz)
        self.target_fps = int(target_fps)
        self.jpeg_quality = int(jpeg_quality)
        self.encode_width = int(encode_width)
        self.veh_detect_hz = int(veh_detect_hz)
        self.enable_yolo = bool(enable_yolo)
        self.enable_tracking = bool(enable_tracking)
        self.enable_bbox_drawing = bool(enable_bbox_drawing)
        self.enable_roi = bool(enable_roi)
        self.enable_roi_drawing = bool(enable_roi_drawing)

        # Device setup
        self.force_gpu = bool(force_gpu)
        if torch and torch.cuda.is_available():
            try:
                torch.cuda.set_device(0)
            except Exception:
                pass
            self.device = "cuda:0"
            logger.info("🖥️  Device: cuda:0")
        else:
            self.device = "cpu"
            if self.force_gpu:
                raise RuntimeError(
                    "GPU (CUDA) is required but not available. Set force_gpu=false to allow CPU fallback."
                )
            logger.warning("⚠️  CUDA not available, falling back to CPU mode")

        # CUDA optimizations cho RTX 3050 4GB
        if torch and self.device.startswith("cuda"):
            torch.backends.cudnn.benchmark = True
            try:
                torch.backends.cuda.matmul.allow_tf32 = True
                torch.backends.cudnn.allow_tf32 = True
                # Tối ưu memory allocation cho 4GB VRAM
                torch.cuda.empty_cache()
                # Set memory fraction để tránh OOM (reserve 20% cho hệ thống)
                if hasattr(torch.cuda, "set_per_process_memory_fraction"):
                    try:
                        torch.cuda.set_per_process_memory_fraction(0.8, device=0)
                    except Exception:
                        pass  # Ignore if not supported
                logger.info("✅ CUDA optimizations enabled (RTX 3050 4GB optimized)")
            except Exception as e:
                logger.warning(f"⚠️  CUDA optimization failed: {e}")
        
        # Resources
        self.cap = None
        self.model = None
        self.tracker = None
        
        # TurboJPEG encoder
        if HAVE_TURBOJPEG:
            self.jpeg = TurboJPEG()
        else:
            self.jpeg = None
        
        # Control
        self.stop_ev = Event()
        self.pause_ev = Event()  # when set, pipeline is paused
        self._seek_to_frame: Optional[int] = None
        
        # Video info
        self.w = 0
        self.h = 0
        self.total = 0
        self.fps_cap = 0.0
        self.capture_interval = None  # computed after opening source
        
        # ROI configuration (runtime adjustable)
        self._roi_lock = Lock()
        self._roi_polygons: dict[str, List[List[float]]] = {}

        # Queues (bounded, latest-wins)
        self.q_cap = Queue(maxsize=3)   # Raw frames
        self.q_det = Queue(maxsize=3)   # (frame, tracks)
        self.q_enc = Queue(maxsize=2)   # JPEG bytes
        
        # Threads
        self.t_cap: Optional[Thread] = None
        self.t_det: Optional[Thread] = None
        self.t_enc: Optional[Thread] = None
        
        # Model path auto-detection
        self.model_path = model_path or "models/yolo_vehicle_v10m.pt"
        
        # Metrics
        self.frame_idx = 0
        self.last_sent_ts = time.perf_counter()
        self.interval = 1.0 / max(self.target_fps, 1)
        self._base_detect_interval = 1.0 / max(self.veh_detect_hz, 1)
        self.detect_interval = self._base_detect_interval
        self.last_detect_ts = 0.0
        self._last_detect_duration = 0.0

        # Track state for prediction between keyframes
        # tid -> {cx, cy, w, h, cid, vx, vy}
        self._track_state: dict[int, dict] = {}
        
        # Current frame detections (for sending metadata to client)
        self._current_detections: list[dict] = []
        
        logger.info(f"⚡ Config: FPS={self.target_fps}, Quality={self.jpeg_quality}, "
                   f"ImgSize={self.imgsz}, EncodeWidth={self.encode_width}")
        logger.info(f"🔧 Modules: YOLO={self.enable_yolo}, Tracking={self.enable_tracking}, "
                   f"BBox={self.enable_bbox_drawing}")
    
    def _open(self):
        """Open video source and load YOLO model"""
        # Resolve video path - try multiple possible locations
        source_str = str(self.source) if not isinstance(self.source, int) else str(self.source)
        
        # If it's a webcam (integer), use it directly
        if isinstance(self.source, int) or (isinstance(self.source, str) and source_str.isdigit()):
            logger.info(f"📹 Opening webcam: {self.source}")
            self.cap = cv2.VideoCapture(int(self.source))
            if not self.cap.isOpened():
                raise RuntimeError(f"❌ Cannot open webcam: {self.source}")
        else:
            # It's a video file path - try multiple locations
            possible_paths = []
            
            # Add original path if it's absolute
            if os.path.isabs(source_str):
                possible_paths.append(source_str)
            
            # Add relative paths
            if source_str.startswith('/'):
                # Remove leading slash and try relative paths
                source_str_clean = source_str.lstrip('/')
                possible_paths.extend([
                    source_str_clean,  # videos/video4.mp4
                    os.path.join("traffic-server", source_str_clean),  # traffic-server/videos/video4.mp4
                    os.path.join("videos", os.path.basename(source_str)),  # videos/video4.mp4
                    os.path.join("traffic-server", "videos", os.path.basename(source_str)),  # traffic-server/videos/video4.mp4
                ])
            else:
                # Already relative path
                possible_paths.extend([
                    source_str,  # videos/video4.mp4
                    os.path.join("traffic-server", source_str),  # traffic-server/videos/video4.mp4
                    os.path.join("videos", os.path.basename(source_str)),  # videos/video4.mp4
                    os.path.join("traffic-server", "videos", os.path.basename(source_str)),  # traffic-server/videos/video4.mp4
                ])
            
            # Try to find the video file
            # Get current working directory and project root
            cwd = os.getcwd()
            script_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.dirname(os.path.dirname(script_dir))  # traffic-server/app/services -> traffic-server
            
            video_path = None
            for path in possible_paths:
                # Try from current working directory
                abs_path_cwd = os.path.join(cwd, path) if not os.path.isabs(path) else path
                if os.path.exists(abs_path_cwd) and os.path.isfile(abs_path_cwd):
                    video_path = abs_path_cwd
                    logger.info(f"✅ Found video at: {video_path}")
                    break
                
                # Try from project root (traffic-server/)
                abs_path_root = os.path.join(project_root, path) if not os.path.isabs(path) else path
                if os.path.exists(abs_path_root) and os.path.isfile(abs_path_root):
                    video_path = abs_path_root
                    logger.info(f"✅ Found video at: {video_path}")
                    break
                
                # Try absolute path
                abs_path = os.path.abspath(path)
                if os.path.exists(abs_path) and os.path.isfile(abs_path):
                    video_path = abs_path
                    logger.info(f"✅ Found video at: {video_path}")
                    break
            
            if not video_path:
                # Last attempt: try with original path
                logger.info(f"📹 Opening source: {self.source}")
                self.cap = cv2.VideoCapture(self.source)
                if not self.cap.isOpened():
                    logger.error(f"❌ Tried paths: {possible_paths}")
                    raise RuntimeError(f"❌ Cannot open source: {self.source}. Tried: {possible_paths[:3]}")
            else:
                logger.info(f"📹 Opening video: {video_path}")
                self.cap = cv2.VideoCapture(video_path)
                if not self.cap.isOpened():
                    raise RuntimeError(f"❌ Cannot open video file: {video_path}")
        
        # Get video info
        self.w = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
        self.h = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
        self.total = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
        self.fps_cap = float(self.cap.get(cv2.CAP_PROP_FPS) or 30.0)
        # Pace capture to avoid finishing the file too fast
        # Use the minimum of source FPS and target FPS
        effective_capture_fps = max(min(self.fps_cap if self.fps_cap > 0 else self.target_fps, self.target_fps), 1.0)
        self.capture_interval = 1.0 / effective_capture_fps
        
        logger.info(f"📊 Video: {self.w}x{self.h} @ {self.fps_cap} FPS, {self.total} frames")
        
        # Unified model loader: auto-detect .engine > .onnx > .pt
        model_info = get_model_info(self.model_path)
        
        if not model_info["found"]:
            # Fallback: try to find any vehicle model
            from app.core.config import settings
            fallback_info = get_model_info(settings.YOLO_VEHICLE_MODEL)
            if fallback_info["found"]:
                model_info = fallback_info
                logger.warning(f"⚠️  Model '{self.model_path}' not found. Using fallback: {fallback_info['path']}")
            else:
                raise RuntimeError(f"❌ Model not found: {self.model_path}")
        
        actual_path = model_info["path"]
        
        # Load YOLO with global cache
        global GLOBAL_YOLO_MODEL, GLOBAL_YOLO_DEVICE, GLOBAL_YOLO_PATH
        if (
            GLOBAL_YOLO_MODEL is not None
            and GLOBAL_YOLO_PATH == actual_path
            and GLOBAL_YOLO_DEVICE == self.device
        ):
            logger.info("🔁 Reusing cached YOLO model")
            self.model = GLOBAL_YOLO_MODEL
        else:
            # If cached model exists but path/device differs, release it to avoid VRAM leaks
            if GLOBAL_YOLO_MODEL is not None and (
                GLOBAL_YOLO_PATH != actual_path or GLOBAL_YOLO_DEVICE != self.device
            ):
                logger.info("♻️ Replacing cached YOLO model (path/device changed)")
                try:
                    # Drop reference and free CUDA cache
                    del GLOBAL_YOLO_MODEL
                except Exception:
                    pass
                finally:
                    try:
                        if torch and torch.cuda.is_available():
                            torch.cuda.empty_cache()
                    except Exception:
                        pass
                # Reset cache markers
                globals()["GLOBAL_YOLO_MODEL"] = None
                globals()["GLOBAL_YOLO_PATH"] = None
                globals()["GLOBAL_YOLO_DEVICE"] = None

            logger.info(f"⚙️  Loading YOLO ({model_info['type']}): {actual_path} ({model_info['size_mb']}MB)")
            self.model = load_yolo_model(
                actual_path,
                device=self.device,
                imgsz=self.imgsz,
                half=True,
                verbose=False
            )
            
            if torch and self.device.startswith("cuda"):
                try:
                    dev_index = torch.cuda.current_device()
                    props = torch.cuda.get_device_properties(dev_index)
                    vram_gb = props.total_memory / (1024 ** 3)
                    allocated_gb = torch.cuda.memory_allocated(dev_index) / (1024 ** 3)
                    logger.info("🧠 CUDA device: %s (%.1f GB VRAM, %.2f GB allocated)", 
                              props.name, vram_gb, allocated_gb)
                except Exception as exc:
                    logger.debug("Unable to query CUDA device properties: %s", exc)

        # Update global cache
        GLOBAL_YOLO_MODEL = self.model
        GLOBAL_YOLO_DEVICE = self.device
        GLOBAL_YOLO_PATH = actual_path
        
        # Initialize tracker
        if HAVE_BOXMOT:
            self.tracker = BYTETracker(
                track_thresh=0.25,
                track_buffer=30,
                match_thresh=0.8,
                frame_rate=self.fps_cap
            )
            logger.info("✅ Initialized boxmot BYTETracker")
        else:
            self.tracker = None
            logger.info("⚠️  ByteTrack not available - using ultralytics built-in tracker")
            # Fall back: lower detect rate to avoid overload
            self.veh_detect_hz = min(self.veh_detect_hz, 10)
            self._base_detect_interval = 1.0 / max(self.veh_detect_hz, 1)
            self.detect_interval = self._base_detect_interval

        logger.info("✅ Stream initialized")
    
    def _release(self):
        """Release resources"""
        try:
            if self.cap:
                self.cap.release()
        except Exception as e:
            logger.error(f"Error releasing capture: {e}")
        finally:
            self.cap = None
            self.model = None
            self.tracker = None
            try:
                if torch and torch.cuda.is_available():
                    torch.cuda.empty_cache()
            except Exception:
                pass
    
    def _put_latest(self, q: Queue, item):
        """
        Put item in queue, drop oldest if full (latest-wins strategy)
        """
        if not q.full():
            q.put(item)
        else:
            try:
                q.get_nowait()  # Drop oldest
            except Empty:
                pass
            q.put(item)

    # ----------------------- ROI Helpers -----------------------

    def _copy_roi_polygons(self) -> dict[str, List[List[float]]]:
        with self._roi_lock:
            return {
                str(name): [
                    [float(pt[0]), float(pt[1])] for pt in points if isinstance(pt, (list, tuple)) and len(pt) >= 2
                ]
                for name, points in self._roi_polygons.items()
            }

    def set_roi_polygons(self, polygons: dict) -> int:
        """Update ROI polygons at runtime."""
        if not isinstance(polygons, dict):
            return 0

        cleaned: dict[str, List[List[float]]] = {}
        for raw_name, raw_points in polygons.items():
            if raw_points is None:
                continue
            points: List[List[float]] = []
            if isinstance(raw_points, dict) and "coordinates" in raw_points:
                raw_points = raw_points.get("coordinates")
            for pt in raw_points:
                if not isinstance(pt, (list, tuple)) or len(pt) < 2:
                    continue
                try:
                    x = float(pt[0])
                    y = float(pt[1])
                except (TypeError, ValueError):
                    continue
                points.append([x, y])
            if len(points) >= 3:
                cleaned[str(raw_name)] = points

        with self._roi_lock:
            self._roi_polygons = cleaned

        logger.info("🎯 Updated ROI polygons: %s", list(cleaned.keys()))
        return len(cleaned)

    def clear_roi_polygons(self) -> None:
        with self._roi_lock:
            self._roi_polygons = {}
        logger.info("🧹 Cleared ROI polygons")

    def _roi_polygons_list(self) -> List[List[List[float]]]:
        with self._roi_lock:
            return [
                [
                    [float(pt[0]), float(pt[1])] for pt in polygon if isinstance(pt, (list, tuple)) and len(pt) >= 2
                ]
                for polygon in self._roi_polygons.values()
            ]

    def _update_detect_interval(self, duration: float) -> None:
        if duration <= 0:
            return

        # Keep detection cadence within hardware limits
        target = max(self._base_detect_interval, duration * 1.05)
        target = min(target, 0.5)

        if self.detect_interval <= 0:
            self.detect_interval = target
        else:
            self.detect_interval = (0.7 * self.detect_interval) + (0.3 * target)

        self._last_detect_duration = duration

    def _filter_keyframe_detections(
        self,
        xyxy: np.ndarray,
        confs: np.ndarray,
        clss: np.ndarray,
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        if not self.enable_roi:
            return xyxy, confs, clss

        rois = self._roi_polygons_list()
        if not rois or xyxy is None or len(xyxy) == 0:
            return xyxy, confs, clss

        keep_indices: List[int] = []
        for idx, (x1, y1, x2, y2) in enumerate(xyxy):
            cx = 0.5 * (float(x1) + float(x2))
            cy = 0.5 * (float(y1) + float(y2))
            if any(point_in_polygon((cx, cy), roi) for roi in rois):
                keep_indices.append(idx)

        if not keep_indices:
            empty_xy = np.empty((0, 4), dtype=float)
            empty_conf = np.empty((0,), dtype=float)
            empty_cls = np.empty((0,), dtype=int)
            return empty_xy, empty_conf, empty_cls

        keep_idx = np.array(keep_indices, dtype=int)
        return xyxy[keep_idx], confs[keep_idx], clss[keep_idx]

    def _filter_tracks_by_roi(self, tracks):
        if not self.enable_roi:
            return tracks

        rois = self._roi_polygons_list()
        if not rois or tracks is None:
            return tracks

        filtered = []
        for tr in tracks:
            try:
                x1, y1, x2, y2 = map(float, tr[:4])
            except Exception:
                continue
            cx = 0.5 * (x1 + x2)
            cy = 0.5 * (y1 + y2)
            if any(point_in_polygon((cx, cy), roi) for roi in rois):
                filtered.append(np.array(tr, dtype=float))

        if isinstance(tracks, np.ndarray):
            if not filtered:
                return np.empty((0, tracks.shape[1] if tracks.ndim == 2 else 6), dtype=float)
            return np.vstack(filtered)

        return filtered

    def _draw_rois_on_frame(self, frame: np.ndarray) -> None:
        if not self.enable_roi or not self.enable_roi_drawing:
            return

        rois = self._copy_roi_polygons()
        if not rois:
            return

        for idx, (name, polygon) in enumerate(rois.items()):
            if len(polygon) < 3:
                continue
            color = ROI_COLORS[idx % len(ROI_COLORS)]
            try:
                draw_polygon_on_frame(frame, polygon, color=color, alpha=0.18)
            except Exception as exc:
                logger.debug("ROI draw failed for %s: %s", name, exc)
    
    def _downscale_for_encode(self, frame):
        """Downscale frame before encoding for faster JPEG compression"""
        if self.encode_width <= 0 or self.w <= self.encode_width:
            return frame
        scale = self.encode_width / float(self.w)
        new_w = self.encode_width
        new_h = int(self.h * scale)
        # INTER_LINEAR is faster than INTER_AREA
        return cv2.resize(frame, (new_w, new_h), interpolation=cv2.INTER_LINEAR)
    
    def _encode_jpeg_bytes(self, bgr) -> bytes:
        """Encode BGR frame to JPEG bytes using TurboJPEG (fast) or cv2 (fallback).
        For higher FPS (~60), prefer 4:2:0 subsampling and FASTDCT when available.
        """
        if HAVE_TURBOJPEG and self.jpeg:
            try:
                # Use 4:2:0 subsampling (smaller, faster) with fast DCT if available
                kwargs = {"quality": self.jpeg_quality}
                if 'subsampling' in self.jpeg.encode.__code__.co_varnames and TJSAMP_420 is not None:
                    kwargs["subsampling"] = TJSAMP_420
                if 'flags' in self.jpeg.encode.__code__.co_varnames and TJFLAG_FASTDCT:
                    kwargs["flags"] = TJFLAG_FASTDCT
                return self.jpeg.encode(bgr, **kwargs)
            except Exception:
                # Fallback to default encode
                return self.jpeg.encode(bgr, quality=self.jpeg_quality)
        else:
            # Fallback to cv2.imencode
            ok, buf = cv2.imencode('.jpg', bgr, 
                                  [int(cv2.IMWRITE_JPEG_QUALITY), self.jpeg_quality])
            if not ok:
                raise RuntimeError("JPEG encode failed")
            return buf.tobytes()
    
    # ----------------------- Pipeline Threads -----------------------
    
    def _thread_capture(self):
        """Thread 1: Capture frames from video"""
        logger.info("🎬 Capture thread started")
        last_capture_ts = time.perf_counter()
        while not self.stop_ev.is_set():
            # Pause handling
            if self.pause_ev.is_set():
                time.sleep(0.02)
                continue

            # Seek handling (only for file source)
            if self._seek_to_frame is not None and isinstance(self.source, str):
                try:
                    target = max(0, min(int(self._seek_to_frame), max(self.total - 1, 0)))
                    self.cap.set(cv2.CAP_PROP_POS_FRAMES, target)
                    # Drain capture queue to avoid stale frames
                    try:
                        while True:
                            self.q_cap.get_nowait()
                    except Empty:
                        pass
                    logger.info(f"⏩ Seeked to frame {target}")
                except Exception as e:
                    logger.warning(f"Seek failed: {e}")
                finally:
                    self._seek_to_frame = None

            ok, frame = self.cap.read()
            if not ok:
                logger.info("⚠️  End of video or read error")
                break
            # Pace capture to avoid finishing the file too fast
            if self.capture_interval is not None:
                now = time.perf_counter()
                dt = now - last_capture_ts
                if dt < self.capture_interval:
                    time.sleep(self.capture_interval - dt)
                    now = time.perf_counter()
                last_capture_ts = now
            self._put_latest(self.q_cap, frame)
        logger.info("🛑 Capture thread stopped")
    
    def _thread_infer(self):
        """Thread 2: YOLO inference + ByteTrack"""
        logger.info("🎬 Infer thread started")
        frame_count = 0
        
        while not self.stop_ev.is_set():
            try:
                frame = self.q_cap.get(timeout=0.5)
            except Empty:
                continue
            
            if self.stop_ev.is_set() or self.model is None:
                break

            frame_count += 1
            self.frame_idx = frame_count  # Update frame index
            now = time.perf_counter()
            
            # Skip frames if detect interval hasn't passed (for better FPS)
            # Only run detection every detect_interval seconds
            detect_due = (self.last_detect_ts == 0.0) or ((now - self.last_detect_ts) >= self.detect_interval)
            
            # If not due for detection, skip YOLO and use previous tracks
            # This allows pipeline to run at full FPS while detection runs at detect_hz

            tracks = []
            if detect_due and self.enable_yolo:
                detect_start = time.perf_counter()
                # YOLO detect (keyframe) - tối ưu cho RTX 3050
                try:
                    # Clear cache trước inference để tránh memory leak
                    if torch and torch.cuda.is_available():
                        torch.cuda.empty_cache()
                    
                    results = self.model.predict(
                        frame,
                        conf=self.conf,
                        imgsz=self.imgsz,
                        verbose=False,
                        classes=list(VEHICLE_IDS),
                        device=self.device,
                        half=True,  # FP16 bắt buộc cho 4GB VRAM
                        agnostic_nms=False,  # Disable để tăng tốc
                        max_det=300,  # Giới hạn detections để tăng tốc
                    )[0]
                except Exception as e:
                    if self.stop_ev.is_set() or self.model is None:
                        break
                    raise e

                boxes = results.boxes
                if boxes is not None and len(boxes) > 0:
                    cls = boxes.cls.cpu().numpy().astype(int)
                    if self.frame_idx % 100 == 1:
                        logger.info(f"🔍 Frame {self.frame_idx}: Raw detections: {len(cls)} objects, classes: {cls}")
                    mask = np.isin(cls, list(VEHICLE_IDS))
                    xyxy = boxes.xyxy.cpu().numpy()[mask]
                    confs = boxes.conf.cpu().numpy()[mask]
                    clss = cls[mask]
                    if self.frame_idx % 100 == 1 and len(clss) > 0:
                        logger.info(f"🔍 Frame {self.frame_idx}: Filtered: {len(clss)} vehicles, classes: {clss}, HAVE_BOXMOT={HAVE_BOXMOT}, enable_tracking={self.enable_tracking}")
                else:
                    xyxy = np.empty((0, 4), dtype=float)
                    confs = np.empty((0,), dtype=float)
                    clss = np.empty((0,), dtype=int)
                    if self.frame_idx % 30 == 1:
                        logger.info(f"⚠️ Frame {self.frame_idx}: No detections from YOLO")

                xyxy, confs, clss = self._filter_keyframe_detections(xyxy, confs, clss)

                if HAVE_BOXMOT and self.tracker is not None and self.enable_tracking:
                    # Use ByteTrack (boxmot) - preferred method
                    if self.frame_idx % 100 == 1:
                        logger.info(f"✅ Using ByteTrack for frame {self.frame_idx}, input: xyxy.shape={xyxy.shape}, confs.shape={confs.shape}, clss.shape={clss.shape}")
                    
                    online_targets = self.tracker.update(
                        dets=xyxy,
                        scores=confs,
                        cls_ids=clss,
                        img=frame
                    )
                    tracks = online_targets
                    
                    if self.frame_idx % 100 == 1:
                        logger.info(f"📊 ByteTrack returned {len(tracks) if tracks is not None else 0} tracks")
                        if tracks is not None and len(tracks) > 0:
                            first_track = tracks[0]
                            logger.info(f"🔬 First track type: {type(first_track)}, shape/len: {first_track.shape if hasattr(first_track, 'shape') else len(first_track) if hasattr(first_track, '__len__') else 'N/A'}, content: {first_track}")
                else:
                    # No tracking or tracking not available
                    # For .engine and .onnx models, tracking doesn't work with ultralytics
                    # Use raw detections with sequential IDs
                    if self.frame_idx % 100 == 1:
                        logger.info(f"⚠️ ByteTrack not available, using raw detections. xyxy.shape={xyxy.shape if xyxy is not None else 'None'}")
                    if len(xyxy) > 0:
                        for i, (x1, y1, x2, y2) in enumerate(xyxy):
                            cls_id = int(clss[i]) if i < len(clss) else 0
                            conf_val = float(confs[i]) if i < len(confs) else 1.0
                            # Use frame_idx + i as pseudo track ID for stability
                            tid = (self.frame_idx * 1000 + i) % 999999
                            tracks.append(np.array([x1, y1, x2, y2, tid, cls_id], dtype=float))
                        if self.frame_idx % 100 == 1:
                            logger.info(f"✅ Created {len(tracks)} tracks with pseudo IDs")

                tracks = self._filter_tracks_by_roi(tracks)
                
                if self.frame_idx % 100 == 1:
                    logger.info(f"📍 After ROI filter: {len(tracks) if tracks is not None else 0} tracks")

                # Update track state and velocities
                dt = (now - self.last_detect_ts) if self.last_detect_ts else (1.0 / max(self.veh_detect_hz, 1))
                new_state: dict[int, dict] = {}
                for tr in tracks:
                    x1, y1, x2, y2, tid, cid = tr
                    tid = int(tid)
                    
                    # Validate bbox before adding to state
                    if x1 >= x2 or y1 >= y2:
                        if self.frame_idx % 100 == 1:
                            logger.warning(f"⚠️ Skipping invalid track {tid}: bbox ({x1}, {y1}, {x2}, {y2})")
                        continue
                    
                    cx = 0.5 * (x1 + x2)
                    cy = 0.5 * (y1 + y2)
                    w = max(1.0, x2 - x1)  # Ensure w >= 1
                    h = max(1.0, y2 - y1)  # Ensure h >= 1
                    vx = vy = 0.0
                    if tid in self._track_state and dt > 1e-3:
                        vx = (cx - self._track_state[tid]["cx"]) / dt
                        vy = (cy - self._track_state[tid]["cy"]) / dt
                    new_state[tid] = {"cx": cx, "cy": cy, "w": w, "h": h, "cid": int(cid), "vx": vx, "vy": vy}
                self._track_state = new_state
                self.last_detect_ts = now
                detect_duration = time.perf_counter() - detect_start
                self._update_detect_interval(detect_duration)
                
                if self.frame_idx % 100 == 1:
                    logger.info(f"✅ Detection complete: {len(new_state)} tracks in state")
            else:
                # Predict tracks between keyframes for perceived 60 fps
                dt = min(now - self.last_detect_ts, 0.5)
                for tid, s in self._track_state.items():
                    cx = s["cx"] + s["vx"] * dt
                    cy = s["cy"] + s["vy"] * dt
                    w, h = s["w"], s["h"]
                    
                    # Validate w, h > 0
                    if w <= 0 or h <= 0:
                        continue  # Skip invalid tracks
                    
                    # Clamp to frame
                    cx = max(0.5 * w, min(cx, self.w - 0.5 * w))
                    cy = max(0.5 * h, min(cy, self.h - 0.5 * h))
                    x1 = cx - 0.5 * w
                    y1 = cy - 0.5 * h
                    x2 = cx + 0.5 * w
                    y2 = cy + 0.5 * h
                    
                    # Final validation
                    if x1 >= x2 or y1 >= y2 or x1 < 0 or y1 < 0 or x2 > self.w or y2 > self.h:
                        continue  # Skip invalid bbox
                    
                    tracks.append(np.array([x1, y1, x2, y2, tid, s["cid"]], dtype=float))

            self._put_latest(self.q_det, (frame, tracks))
        
        logger.info("🛑 Infer thread stopped")
    
    def _thread_annotate_encode(self):
        """Thread 3: Annotate frame + TurboJPEG encode"""
        logger.info("🎬 Encode thread started")
        
        while not self.stop_ev.is_set():
            try:
                frame, tracks = self.q_det.get(timeout=0.5)
            except Empty:
                continue

            if frame is None:
                continue

            # Draw ROI overlays first so detections appear above
            self._draw_rois_on_frame(frame)

            # Prepare detections metadata (ALWAYS, for future violations detection)
            detections = []
            if tracks is not None and len(tracks) > 0:
                for t in tracks:
                    try:
                        # ByteTrack format: [x1, y1, x2, y2, tid, cid]
                        if len(t) >= 6:
                            x1, y1, x2, y2, tid, cls_id = t[:6]
                        elif len(t) >= 5:
                            x1, y1, x2, y2, tid = t[:5]
                            cls_id = 0  # default
                        else:
                            x1, y1, x2, y2 = t[:4]
                            tid = -1
                            cls_id = 0
                        
                        detections.append({
                            "bbox": [float(x1), float(y1), float(x2), float(y2)],
                            "track_id": int(tid),
                            "class_id": int(cls_id),
                            "class_name": CLASS_NAMES.get(int(cls_id), "vehicle"),
                            "confidence": 1.0,  # TODO: add real confidence from YOLO results
                            "violation": None   # TODO: integrate violation detection logic
                        })
                    except Exception as e:
                        logger.warning(f"⚠️  Failed to parse track: {e}, track shape: {t.shape if hasattr(t, 'shape') else len(t) if hasattr(t, '__len__') else 'unknown'}")
                        continue
            
            # Store detections for this frame (accessible in send thread)
            self._current_detections = detections
            
            # DEBUG: Log frame info periodically
            if self.frame_idx % 30 == 1:
                logger.info(f"📊 Frame {self.frame_idx}: tracks={len(tracks) if tracks is not None else 0}, detections={len(detections)}, enable_bbox={self.enable_bbox_drawing}, frame.shape={frame.shape}")
            
            # Optionally draw bbox on frame (backward compatible mode)
            if self.enable_bbox_drawing and len(detections) > 0:
                # DEBUG: Log first detection
                if self.frame_idx % 30 == 1:
                    logger.info(f"🎯 Frame {self.frame_idx}: Drawing {len(detections)} bboxes. First bbox: {detections[0]}")
                
                for det in detections:
                    x1, y1, x2, y2 = [int(v) for v in det["bbox"]]
                    tid = det["track_id"]
                    cls_id = det["class_id"]
                    cls_name = det["class_name"]
                    
                    # Validate bbox coordinates
                    if x1 >= x2 or y1 >= y2 or x1 < 0 or y1 < 0:
                        logger.warning(f"⚠️  Invalid bbox: ({x1}, {y1}, {x2}, {y2})")
                        continue
                    
                    # Get color (bright, high contrast colors)
                    color = CLASS_COLORS.get(cls_id, (0, 255, 0))
                    
                    # Draw bbox with VERY THICK lines for maximum visibility
                    cv2.rectangle(frame, (x1, y1), (x2, y2), color, 5, cv2.LINE_AA)
                    
                    # Draw label with background (larger, bold)
                    label = f"{cls_name} #{tid}"
                    font_scale = 0.8
                    font_thickness = 2
                    (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, font_scale, font_thickness)
                    label_y1 = max(y1 - th - 12, 0)
                    label_y2 = y1
                    cv2.rectangle(frame, (x1, label_y1), (x1 + tw + 10, label_y2), color, -1, cv2.LINE_AA)
                    # Draw label text (white, bold, larger)
                    cv2.putText(frame, label, (x1 + 5, y1 - 8), cv2.FONT_HERSHEY_SIMPLEX, font_scale, (255, 255, 255), font_thickness, cv2.LINE_AA)
                    
                if self.frame_idx % 30 == 1:
                    logger.info(f"✅ Successfully drew {len(detections)} bboxes on frame {self.frame_idx}")
            elif self.enable_bbox_drawing and self.frame_idx % 30 == 1:
                logger.info(f"⚠️  BBox drawing enabled but no detections to draw (frame {self.frame_idx})")
            elif not self.enable_bbox_drawing and self.frame_idx % 100 == 1:
                logger.info(f"ℹ️  BBox drawing is DISABLED (frame {self.frame_idx})")
            
            # Downscale before encode (faster JPEG compression)
            enc_frame = self._downscale_for_encode(frame)
            
            # Encode to JPEG bytes (TurboJPEG is 2-3x faster than cv2)
            jpeg_bytes = self._encode_jpeg_bytes(enc_frame)
            
            self._put_latest(self.q_enc, jpeg_bytes)
        
        logger.info("🛑 Encode thread stopped")
    
    # ----------------------- Public API -----------------------
    
    def start(self):
        """Start all pipeline threads"""
        self._open()
        
        self.t_cap = Thread(target=self._thread_capture, daemon=True, name="capture")
        self.t_det = Thread(target=self._thread_infer, daemon=True, name="infer")
        self.t_enc = Thread(target=self._thread_annotate_encode, daemon=True, name="encode")
        
        self.t_cap.start()
        self.t_det.start()
        self.t_enc.start()
        
        logger.info("✅ All threads started")
    
    def stop(self):
        """Signal all threads to stop"""
        logger.info("🛑 Stop signal sent")
        self.stop_ev.set()
        # Join threads to avoid races with resource release
        for t in (self.t_cap, self.t_det, self.t_enc):
            try:
                if t and t.is_alive():
                    t.join(timeout=1.5)
            except Exception:
                pass
    
    def close(self):
        """Stop threads (idempotent) then release all resources safely"""
        # Ensure threads have been asked to stop and given time to exit
        self.stop()
        logger.info("🧹 Releasing resources...")
        self._release()

    # --------- Controls ---------
    def pause(self):
        self.pause_ev.set()
        logger.info("⏸️  Paused")

    def resume(self):
        self.pause_ev.clear()
        logger.info("▶️  Resumed")

    def seek_relative(self, seconds: float):
        """Request a relative seek by seconds (only for file sources)."""
        if not isinstance(self.source, str):
            logger.warning("Seek ignored: not a file source")
            return
        fps = self.fps_cap if self.fps_cap > 0 else self.target_fps
        try:
            current = int(self.cap.get(cv2.CAP_PROP_POS_FRAMES) or 0)
        except Exception:
            current = 0
        offset = int(seconds * fps)
        self._seek_to_frame = current + offset
        logger.info(f"⏩ Seek request: seconds={seconds}, target_frame={self._seek_to_frame}")
    
    def info_packet(self) -> dict:
        """Get stream info packet (send once at start)"""
        return {
            "type": "info",
            "frame_width": self.w,
            "frame_height": self.h,
            "total_frames": self.total,
            "model": "yolo",
            "tracker": "bytetrack" if HAVE_BOXMOT else "ultralytics_persist",
            "fps_cap": self.target_fps,
            "device": self.device,
            "turbo_jpeg": HAVE_TURBOJPEG,
            "force_gpu": self.force_gpu,
            "detect_interval": round(self.detect_interval, 4),
            "last_detect_duration": round(self._last_detect_duration, 4),
            "roi_enabled": self.enable_roi,
            "roi_count": len(self._roi_polygons),
            "rois": self._copy_roi_polygons(),
            "modules": {
                "yolo": self.enable_yolo,
                "tracking": self.enable_tracking,
                "bbox_drawing": self.enable_bbox_drawing,
                "roi_drawing": self.enable_roi_drawing
            }
        }
    
    def next_frame(self) -> Tuple[Optional[dict], Optional[bytes]]:
        """
        Get next frame with server-side pacing
        
        Returns:
            (header_dict, jpeg_bytes) - header=None if not ready yet
        
        Pacing: Sleep to maintain target_fps, preventing overwhelming the client
        """
        # Server-side pacing: maintain target FPS
        now = time.perf_counter()
        dt = now - self.last_sent_ts
        
        if dt < self.interval:
            time.sleep(self.interval - dt)
            now = time.perf_counter()
            dt = now - self.last_sent_ts
        
        self.last_sent_ts = now
        
        # Get encoded frame from queue
        try:
            jpeg_bytes = self.q_enc.get(timeout=0.5)
        except Empty:
            return None, None
        
        # Build header
        self.frame_idx += 1
        fps = round(1.0 / max(dt, 1e-6), 2)
        
        header = {
            "type": "frame",
            "frame_idx": self.frame_idx,
            "fps": fps,
            "detections": self._current_detections  # Include detections metadata
        }
        
        # Log progress every 30 frames
        if self.frame_idx % 30 == 0:
            logger.info(f"🎬 Frame {self.frame_idx}: {fps} FPS")
        
        return header, jpeg_bytes

