"""
Binary Annotation Stream - 30 FPS với TurboJPEG + Multithreading
Pipeline: Capture → Infer/Track → Annotate+Encode → Send
Queues: Latest-wins (drop old frames when full)
"""
import cv2
import time
import math
import numpy as np
import logging
import glob
from typing import Optional, Tuple, List
from queue import Queue, Empty
from threading import Thread, Event, Lock
from pathlib import Path
import os

logger = logging.getLogger(__name__)

# Global YOLO model cache to avoid re-loading on each connection
GLOBAL_YOLO_MODEL = None
GLOBAL_YOLO_DEVICE = None
GLOBAL_YOLO_PATH = None

# Default realtime detection model (ONNX preferred - optimized for RTX 3050)
DEFAULT_REALTIME_MODEL_PATH = "models/vehicle/11s/yolo_vehicle_11s.onnx"

try:
    import torch
    from ultralytics import YOLO
except Exception as e:
    logger.error(f"Failed to import YOLO/torch: {e}")
    torch = None
    YOLO = None

# ByteTrack (boxmot) - preferred
# Use centralised loader to handle different boxmot versions and module layouts
from app.services.boxmot_loader import BYTETracker, HAVE_BOXMOT, instantiate_tracker
if HAVE_BOXMOT:
    logger.info("✅ boxmot BYTETracker discovered by boxmot_loader")
else:
    logger.warning("⚠️  boxmot not available - ByteTrack will not work (boxmot_loader did not find a tracker)")

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
from app.core.performance_config import BYTETRACK_SETTINGS, TRACK_SMOOTHING_SETTINGS, OCR_SETTINGS
from app.services.plate_ocr_service import get_ocr_service, PlateOCRService

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
    3: (219, 112, 147)   # truck - purple (#9370db in BGR)
}

ROI_COLORS = [
    (50, 205, 50),
    (60, 180, 255),
    (255, 165, 0),
    (147, 112, 219),
    (255, 99, 71),
]


def preload_realtime_resources(
    model_path: Optional[str] = None,
    device: Optional[str] = None,
    imgsz: int = 640,
) -> bool:
    """Pre-load the realtime YOLO detector at application startup.

    Args:
        model_path: Optional custom model path. Defaults to the realtime engine.
        device: Optional device hint ("cuda:0" / "cpu"). Auto-detect when None.
        imgsz: Inference size to initialise internal buffers with.

    Returns:
        True if the model was loaded into the global cache, False otherwise.
    """

    if not YOLO or not load_yolo_model:
        logger.warning("⚠️  Ultralytics YOLO not available - skipping realtime preload")
        return False

    target_path = model_path or DEFAULT_REALTIME_MODEL_PATH
    info = get_model_info(target_path)

    if not info.get("found", False):
        logger.warning("⚠️  Realtime model not found for preload: %s", target_path)
        return False

    chosen_device = device
    if not chosen_device:
        if torch and torch.cuda.is_available():
            chosen_device = "cuda:0"
        else:
            chosen_device = "cpu"

    half_precision = chosen_device.startswith("cuda")

    global GLOBAL_YOLO_MODEL, GLOBAL_YOLO_PATH, GLOBAL_YOLO_DEVICE

    # If already loaded with the same path/device, skip reloading
    if (
        GLOBAL_YOLO_MODEL is not None
        and GLOBAL_YOLO_PATH == info.get("path")
        and GLOBAL_YOLO_DEVICE == chosen_device
    ):
        logger.info("ℹ️  Realtime detector already preloaded (%s on %s)", info.get("type"), chosen_device)
        return True

    try:
        logger.info(
            "🚀 Preloading realtime YOLO model: %s (%s) on %s",
            info.get("path"),
            info.get("type"),
            chosen_device,
        )
        model = load_yolo_model(
            info.get("path"),
            device=chosen_device,
            imgsz=imgsz,
            half=half_precision,
            verbose=False,
        )
    except FileNotFoundError as exc:
        logger.warning("⚠️  Unable to preload realtime model (%s): %s", target_path, exc)
        return False
    except Exception as exc:
        logger.error("❌ Failed to preload realtime model %s: %s", target_path, exc)
        return False

    GLOBAL_YOLO_MODEL = model
    GLOBAL_YOLO_PATH = info.get("path")
    GLOBAL_YOLO_DEVICE = chosen_device

    logger.info(
        "✅ Realtime YOLO model ready: %s (size %.2f MB)",
        info.get("path"),
        info.get("size_mb", 0.0),
    )
    return True


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
        camera_id: str = "default",
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
        force_gpu: bool = True,
        warmup_seconds: float = 5.0,
    ):
        """
        Args:
            source: "0" for webcam, path for video file
            camera_id: Camera identifier for traffic light integration
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
        self.camera_id = str(camera_id)
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

        try:
            self.warmup_seconds = max(0.0, float(warmup_seconds))
        except (TypeError, ValueError):
            self.warmup_seconds = 0.0
        
        # OCR settings
        ocr_cfg = OCR_SETTINGS or {}
        self.enable_ocr = bool(ocr_cfg.get("enabled", True))
        self.ocr_model_type = str(ocr_cfg.get("model_type", "auto"))

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
        self.ocr_service: Optional[PlateOCRService] = None
        
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

        # Model path auto-detection - Normalize to ONNX only
        # Always use ONNX format for ByteTrack compatibility
        script_dir = Path(__file__).parent.parent.parent
        models_base = script_dir / "models" / "vehicle"
        
        if model_path:
            # Keep original extension - support both .engine and .onnx
            model_path_norm = model_path

            # If it's a relative path, try to resolve against models dir
            if not os.path.isabs(model_path):
                # Handle various input formats from frontend:
                # - models/yolo_vehicle_11s.engine -> models/vehicle/11s/yolo_vehicle_11s.engine
                # - models/vehicle/11s/yolo_vehicle_11s.engine -> (unchanged)
                # - yolo_vehicle_11s.engine -> models/vehicle/11s/yolo_vehicle_11s.engine
                
                base_name = os.path.basename(model_path)
                ext = os.path.splitext(base_name)[1].lower()
                
                # Determine version (11s or v10m) from model name or path
                if "11s" in base_name or "11s" in model_path:
                    version_dir = "11s"
                elif "v10m" in base_name or "v10m" in model_path:
                    version_dir = "v10m"
                else:
                    # Default to 11s (faster for realtime)
                    version_dir = "11s"
                
                # Try to find the model in models/vehicle/VERSION/
                model_path_norm = str(models_base / version_dir / base_name)
                if not os.path.exists(model_path_norm):
                    # Try the other version if not found
                    other_dir = "v10m" if version_dir == "11s" else "11s"
                    other_path = models_base / other_dir / base_name
                    if other_path.exists():
                        model_path_norm = str(other_path)
            
            self.model_path = model_path_norm
            logger.info(f"🔄 Using model: {model_path} → {self.model_path}")
        else:
            # Use default: 11s model
            self.model_path = DEFAULT_REALTIME_MODEL_PATH
        
        # Metrics
        self.frame_idx = 0
        self.last_sent_ts = time.perf_counter()
        self.interval = 1.0 / max(self.target_fps, 1)
        self._base_detect_interval = 1.0 / max(self.veh_detect_hz, 1)
        self.detect_interval = self._base_detect_interval
        self.last_detect_ts = 0.0
        self._last_detect_duration = 0.0

        # Warmup control
        self._warmup_until: Optional[float] = None
        self._warmup_logged = False

        # Track state for prediction between keyframes
        # tid -> {cx, cy, w, h, cid, vx, vy}
        self._track_state: dict[int, dict] = {}
        
        # Track smoothing configuration
        smoothing_cfg = TRACK_SMOOTHING_SETTINGS or {}
        
        def _clamp_alpha(val, fallback):
            try:
                val_f = float(val)
            except (TypeError, ValueError):
                return fallback
            return max(0.0, min(1.0, val_f))
        
        self._smooth_tracks = bool(smoothing_cfg.get("enabled", True))
        # Optimized smoothing for snappier response (per requirements)
        self._smooth_position_alpha = _clamp_alpha(smoothing_cfg.get("position_alpha", 0.55), 0.55)  # More responsive
        self._smooth_size_alpha = _clamp_alpha(smoothing_cfg.get("size_alpha", 0.5), 0.5)  # More responsive
        
        try:
            # Reduced max shift for snappier tracking (was 120, now 80)
            self._smooth_max_center_shift = float(smoothing_cfg.get("max_center_shift", 80.0))
        except (TypeError, ValueError):
            self._smooth_max_center_shift = 80.0
        self._smooth_max_center_shift = max(0.0, self._smooth_max_center_shift)
        
        try:
            # Reduced max scale change for stability (was 1.9, now 1.6)
            self._smooth_max_scale_change = float(smoothing_cfg.get("max_scale_change", 1.6))
        except (TypeError, ValueError):
            self._smooth_max_scale_change = 1.6
        self._smooth_max_scale_change = max(1.0, self._smooth_max_scale_change)
        
        try:
            self._smooth_min_confidence = float(smoothing_cfg.get("min_confidence", 0.0))
        except (TypeError, ValueError):
            self._smooth_min_confidence = 0.0
        self._smooth_min_confidence = max(0.0, self._smooth_min_confidence)
        
        # Current frame detections (for sending metadata to client)
        self._current_detections: list[dict] = []
        
        logger.info(f"⚡ Config: FPS={self.target_fps}, Quality={self.jpeg_quality}, "
                   f"ImgSize={self.imgsz}, EncodeWidth={self.encode_width}")
        logger.info(f"🔧 Modules: YOLO={self.enable_yolo}, Tracking={self.enable_tracking}, "
                   f"BBox={self.enable_bbox_drawing}")
        logger.info(f"🎯 Track smoothing: {'ON' if self._smooth_tracks else 'OFF'} "
                   f"(αpos={self._smooth_position_alpha:.2f}, αsize={self._smooth_size_alpha:.2f}, "
                   f"max_shift={self._smooth_max_center_shift:.1f}, max_scale={self._smooth_max_scale_change:.2f})")
    
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
        
        # Load either .engine or .onnx model
        script_dir = Path(__file__).parent.parent.parent
        
        # Try the model path directly first
        if os.path.isabs(self.model_path):
            model_path = Path(self.model_path)
        else:
            model_path = script_dir / self.model_path
        
        # Validate model exists
        if not model_path.exists():
            raise RuntimeError(f"❌ Model file does not exist: {model_path}")
        
        actual_path = str(model_path)
        model_ext = model_path.suffix.lower()
        
        # Check model type - only .onnx and .pt supported (reject .engine)
        if model_ext == '.engine':
            raise RuntimeError(
                f"❌ TensorRT .engine files are no longer supported: {actual_path}\n"
                f"💡 Please use .onnx or .pt models instead for better compatibility\n"
                f"   Example: {actual_path.replace('.engine', '.onnx')}"
            )
        elif model_ext not in ['.onnx', '.pt']:
            raise RuntimeError(
                f"❌ Invalid model type: {model_ext}\n"
                f"   Supported formats: .onnx, .pt\n"
                f"   Got: {actual_path}"
            )
        
        # Get model info for logging
        model_info = get_model_info(actual_path)
        size_mb = model_info.get("size_mb", 0) if model_info.get("found") else 0
        
        model_type_name = "ONNX" if model_ext == ".onnx" else "PyTorch"
        logger.info(f"✅ Using {model_type_name} model: {actual_path} ({size_mb}MB)")
        
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

            # Load model based on extension
            is_engine = actual_path.lower().endswith('.engine')
            logger.info(
                f"⚙️  Loading YOLO model ({'.engine' if is_engine else '.onnx'}): "
                f"{actual_path} ({model_info['size_mb']}MB)"
            )

            # Use performance config for half precision (ONNX FP32 compatible)
            from app.core.performance_config import INFERENCE_SETTINGS
            use_half = INFERENCE_SETTINGS.get('half', False)
            
            self.model = load_yolo_model(
                actual_path,
                device=self.device,
                imgsz=self.imgsz,
                half=use_half,
                verbose=False
            )
            # Verify model is loaded correctly
            if self.model is None:
                raise RuntimeError(f"❌ Failed to load model: {actual_path}")
            
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
        
        # Initialize ByteTrack tracker (REQUIRED for ONNX models)
        if not HAVE_BOXMOT:
            raise RuntimeError(
                "❌ ByteTrack (boxmot) is required but not available. "
                "Install with: pip install boxmot>=10.0.0"
            )
        
        # Optimized ByteTrack parameters for snappier, stable tracking (RTX 3050 30+ FPS)
        tracker_cfg = dict(BYTETRACK_SETTINGS) if BYTETRACK_SETTINGS else {}
        
        # Improved defaults for better responsiveness and fewer ID flips
        try:
            track_thresh = float(tracker_cfg.get("track_thresh", 0.5))  # Higher = more stable tracks
        except (TypeError, ValueError):
            track_thresh = 0.5
        try:
            # Optimized buffer: fps + 10 for 30fps = 40 frames buffer
            default_buffer = max(40, int(self.target_fps) + 10) if self.target_fps else 40
            track_buffer = int(tracker_cfg.get("track_buffer", default_buffer))
        except (TypeError, ValueError):
            track_buffer = 40
        try:
            match_thresh = float(tracker_cfg.get("match_thresh", 0.85))  # Higher = less ID switches
        except (TypeError, ValueError):
            match_thresh = 0.85
        try:
            frame_rate = float(tracker_cfg.get("frame_rate", self.target_fps or 30))
        except (TypeError, ValueError):
            frame_rate = float(self.target_fps or 30)
        try:
            min_box_area = float(tracker_cfg.get("min_box_area", 100))
        except (TypeError, ValueError):
            min_box_area = 100.0
        mot20 = bool(tracker_cfg.get("mot20", False))

        self.tracker = BYTETracker(
            track_thresh=track_thresh,
            track_buffer=track_buffer,
            match_thresh=match_thresh,
            frame_rate=frame_rate,
            min_box_area=min_box_area,
            mot20=mot20,
        )
        logger.info(
            "✅ ByteTrack optimized for ≥30 FPS (thresh=%.2f, buffer=%d, match=%.2f, fps=%.1f, min_area=%.1f)",
            track_thresh,
            track_buffer,
            match_thresh,
            frame_rate,
            min_box_area,
        )
        
        # Initialize OCR service
        if self.enable_ocr:
            try:
                logger.info("🔧 Initializing OCR service...")
                self.ocr_service = get_ocr_service(
                    model_type=self.ocr_model_type,
                    device=self.device,
                    enable_ocr=True
                )
                if self.ocr_service and self.ocr_service.detector:
                    logger.info("✅ OCR service initialized")
                else:
                    logger.warning("⚠️  OCR service initialization failed - OCR disabled")
                    self.enable_ocr = False
                    self.ocr_service = None
            except Exception as e:
                logger.error(f"❌ Failed to initialize OCR service: {e}")
                self.enable_ocr = False
                self.ocr_service = None
        else:
            logger.info("ℹ️  OCR disabled by config")

        # Final startup summary with Vietnamese emoji logging
        model_type = "ONNX" if actual_path.lower().endswith('.onnx') else "PyTorch"
        device_name = self.device
        if torch and torch.cuda.is_available():
            try:
                device_name = f"{self.device} ({torch.cuda.get_device_name(0)})"
            except:
                pass
        
        logger.info("=" * 60)
        logger.info("✅ READY: Traffic Detection System Optimized for RTX 3050")
        logger.info(f"🎯 Target FPS: ≥{self.target_fps} | Model: {model_type}")
        logger.info(f"🖥️  Device: {device_name}")
        logger.info(f"📹 Resolution: {self.w}x{self.h} | Encode: {self.encode_width}px")
        logger.info(f"🎛️  Modules: YOLO={self.enable_yolo}, Tracking={self.enable_tracking}")
        logger.info(f"🗺️  ROI: {len(self._roi_polygons)} regions | OCR: {self.enable_ocr}")
        logger.info(f"⚡ Optimizations: FP16=True, TurboJPEG={HAVE_TURBOJPEG}")
        logger.info("=" * 60)
    
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

        # Check if adaptive interval is enabled
        from app.core.performance_config import ENABLE_ADAPTIVE_INTERVAL, FIXED_DETECT_INTERVAL
        
        if not ENABLE_ADAPTIVE_INTERVAL:
            # Use fixed interval for stable FPS (no oscillation)
            self.detect_interval = FIXED_DETECT_INTERVAL
            self._last_detect_duration = duration
            
            # Log performance metrics periodically
            if self.frame_idx % 150 == 1:  # Every ~5 seconds at 30fps
                current_fps = 1.0 / duration if duration > 0 else 0
                logger.info(f"📊 Fixed Interval Mode: detect_fps={current_fps:.1f}, interval={self.detect_interval:.3f}s (stable)")
                
                # Vietnamese emoji log for clear monitoring
                if current_fps >= 30:
                    logger.info("✅ Hiệu suất ổn định: ≥30 FPS detection")
                elif current_fps >= 25:
                    logger.info("🟡 Hiệu suất khá: 25-30 FPS detection") 
                else:
                    logger.info("🔴 Hiệu suất thấp: <25 FPS detection")
            return

        # Legacy adaptive FPS monitoring (if enabled)
        current_fps = 1.0 / duration if duration > 0 else 0
        target_detect_fps = self.veh_detect_hz or 25
        
        # If detection is too slow (< 28 FPS), increase interval to maintain overall pipeline FPS
        if current_fps < 28 and current_fps > 0:
            # Automatically increase detect_interval to reduce detection load
            adaptive_interval = max(self._base_detect_interval, duration * 1.2)
            if self.frame_idx % 30 == 1:  # Log every 30 frames
                logger.warning(f"⚠️ Detection FPS low ({current_fps:.1f} < 28), adapting interval: {adaptive_interval:.3f}s")
        else:
            # Normal adaptation
            adaptive_interval = max(self._base_detect_interval, duration * 1.05)
        
        # Cap maximum interval to prevent too slow detection
        adaptive_interval = min(adaptive_interval, 0.5)

        if self.detect_interval <= 0:
            self.detect_interval = adaptive_interval
        else:
            # Smooth adaptation
            self.detect_interval = (0.7 * self.detect_interval) + (0.3 * adaptive_interval)

        self._last_detect_duration = duration
        
        # Log performance metrics periodically
        if self.frame_idx % 150 == 1:  # Every ~5 seconds at 30fps
            pipeline_fps = 1.0 / (duration + 0.001)  # Avoid division by zero
            logger.info(f"📊 Adaptive Mode: detect_fps={current_fps:.1f}, interval={self.detect_interval:.3f}s, pipeline_fps={pipeline_fps:.1f}")
            
            # Vietnamese emoji log for clear monitoring
            if current_fps >= 30:
                logger.info("✅ Hiệu suất tốt: ≥30 FPS detection")
            elif current_fps >= 25:
                logger.info("🟡 Hiệu suất khá: 25-30 FPS detection") 
            else:
                logger.info("🔴 Hiệu suất thấp: <25 FPS detection - tự động điều chỉnh")

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
                    
                    # Use performance config for half precision (ONNX FP32 compatible)
                    from app.core.performance_config import INFERENCE_SETTINGS
                    use_half = INFERENCE_SETTINGS.get('half', False)
                    
                    results = self.model.predict(
                        frame,
                        conf=self.conf,
                        iou=0.65,  # IOU threshold cao hơn để bbox ôm sát hơn (default: 0.45)
                        imgsz=self.imgsz,
                        verbose=False,
                        classes=list(VEHICLE_IDS),
                        device=self.device,
                        half=use_half,  # Use config setting (FP32 for ONNX compatibility)
                        agnostic_nms=False,  # Disable để tăng tốc
                        max_det=300,  # Giới hạn detections để tăng tốc
                    )[0]
                except Exception as e:
                    # Handle ONNX Runtime unsupported IR version more gracefully
                    msg = str(e)
                    if self.stop_ev.is_set() or self.model is None:
                        break

                    # Typical error when onnxruntime does not support the model IR
                    if "Unsupported model IR version" in msg or "onnxruntime" in msg.lower():
                        logger.error("❌ ONNX Runtime failed to load the ONNX model: %s", msg)
                        logger.error("🔧 Suggested fixes:")
                        logger.error("   - Upgrade onnxruntime to a version that supports the model IR (e.g. pip install -U onnxruntime or onnxruntime-gpu)")
                        logger.error("   - Re-export the ONNX model with a lower IR/opset compatible with your onnxruntime version")
                        logger.error("   - Alternatively, use a TensorRT .engine or a .pt model if available")
                        # Stop the stream gracefully
                        try:
                            self.stop_ev.set()
                        except Exception:
                            pass
                        break
                    # Unknown error - re-raise so it surfaces for debugging
                    raise

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

                if len(xyxy) > 0:
                    frame_h, frame_w = frame.shape[:2]
                    orig_shape = getattr(results, "orig_shape", (frame_h, frame_w))
                    try:
                        orig_h, orig_w = int(orig_shape[0]), int(orig_shape[1])
                    except (TypeError, ValueError, IndexError):
                        orig_h, orig_w = frame_h, frame_w
                    if orig_w and orig_h and (orig_w != frame_w or orig_h != frame_h):
                        scale_x = frame_w / float(orig_w)
                        scale_y = frame_h / float(orig_h)
                        xyxy = xyxy.astype(np.float32)
                        xyxy[:, [0, 2]] *= scale_x
                        xyxy[:, [1, 3]] *= scale_y

                tracker_inputs = np.empty((0, 6), dtype=np.float32)
                if len(xyxy) > 0:
                    min_len = min(len(xyxy), len(confs), len(clss))
                    if min_len != len(xyxy):
                        logger.warning(
                            "⚠️ Frame %s: detection tensors misaligned (xyxy=%d, conf=%d, cls=%d) — truncating to %d entries",
                            self.frame_idx,
                            len(xyxy),
                            len(confs),
                            len(clss),
                            min_len,
                        )
                    if min_len > 0:
                        tracker_inputs = np.concatenate(
                            [
                                xyxy[:min_len].astype(np.float32),
                                confs[:min_len].reshape(-1, 1).astype(np.float32),
                                clss[:min_len].reshape(-1, 1).astype(np.float32),
                            ],
                            axis=1,
                        )

                if HAVE_BOXMOT and self.tracker is not None and self.enable_tracking:
                    # Use ByteTrack (boxmot) - preferred method
                    if self.frame_idx % 100 == 1:
                        logger.info(
                            "✅ Using ByteTrack for frame %s, tracker_inputs=%s",
                            self.frame_idx,
                            tracker_inputs.shape,
                        )
                        if tracker_inputs.size > 0:
                            logger.info(
                                "   Confidence range: min=%.3f, max=%.3f, mean=%.3f",
                                float(tracker_inputs[:, 4].min()),
                                float(tracker_inputs[:, 4].max()),
                                float(tracker_inputs[:, 4].mean()),
                            )

                    online_targets = self.tracker.update(tracker_inputs, frame)
                    tracks = online_targets if online_targets is not None else []

                    if self.frame_idx % 100 == 1:
                        logger.info(
                            "📊 ByteTrack returned %d tracks",
                            0 if tracks is None else len(tracks),
                        )
                        if tracks is not None and len(tracks) > 0:
                            track_ids = [int(t[4]) for t in tracks if len(t) >= 5]
                            logger.info(
                                "🔗 Track IDs: %s (unique: %d)",
                                sorted(set(track_ids)),
                                len(set(track_ids)),
                            )
                else:
                    # ByteTrack should always be available when using ONNX
                    # This fallback should never be reached, but keep it for safety
                    if self.frame_idx % 100 == 1:
                        logger.warning(
                            f"⚠️ ByteTrack not initialized (this should not happen with ONNX). "
                            f"Using raw detections. xyxy.shape={xyxy.shape if xyxy is not None else 'None'}"
                        )
                    if len(xyxy) > 0:
                        for i, (x1, y1, x2, y2) in enumerate(xyxy):
                            cls_id = int(clss[i]) if i < len(clss) else 0
                            conf_val = float(confs[i]) if i < len(confs) else 1.0
                            # Use frame_idx + i as pseudo track ID for stability
                            tid = (self.frame_idx * 1000 + i) % 999999
                            tracks.append(np.array([x1, y1, x2, y2, tid, conf_val, cls_id], dtype=float))
                        if self.frame_idx % 100 == 1:
                            logger.info(f"✅ Created {len(tracks)} tracks with pseudo IDs")

                tracks = self._filter_tracks_by_roi(tracks)
                
                if self.frame_idx % 100 == 1:
                    logger.info(f"📍 After ROI filter: {len(tracks) if tracks is not None else 0} tracks")

                # Prepare iterable for smoothing/state update
                if tracks is None:
                    track_iterable: List[np.ndarray] = []
                elif isinstance(tracks, np.ndarray):
                    track_iterable = [np.array(tr, dtype=float).reshape(-1) for tr in tracks]
                else:
                    track_iterable = [np.array(tr, dtype=float).reshape(-1) for tr in tracks]
                
                dt = (now - self.last_detect_ts) if self.last_detect_ts else (1.0 / max(self.veh_detect_hz, 1))
                new_state: dict[int, dict] = {}
                output_tracks: List[np.ndarray] = []
                
                for arr in track_iterable:
                    if arr.size < 5:
                        continue
                    coords = np.array(arr[:4], dtype=float)
                    if not np.isfinite(coords).all():
                        continue
                    x1, y1, x2, y2 = coords.tolist()
                    
                    try:
                        tid = int(arr[4])
                    except (TypeError, ValueError):
                        if self.frame_idx % 100 == 1:
                            logger.debug("⚠️ Skipping track with invalid ID: %s", arr[4])
                        continue
                    
                    if x1 >= x2 or y1 >= y2:
                        if self.frame_idx % 100 == 1:
                            logger.warning(f"⚠️ Skipping invalid track {tid}: bbox ({x1}, {y1}, {x2}, {y2})")
                        continue
                    
                    conf_val = float(arr[5]) if arr.size >= 6 else 1.0
                    cid = int(arr[6]) if arr.size >= 7 else 0
                    det_index = int(arr[7]) if arr.size >= 8 else -1
                    
                    # Raw measurements
                    raw_cx = 0.5 * (x1 + x2)
                    raw_cy = 0.5 * (y1 + y2)
                    raw_w = max(1.0, x2 - x1)
                    raw_h = max(1.0, y2 - y1)
                    
                    # Initialize smoothed values with raw
                    smooth_cx = raw_cx
                    smooth_cy = raw_cy
                    smooth_w = raw_w
                    smooth_h = raw_h
                    
                    prev_state = self._track_state.get(tid)
                    prev_age = int(prev_state.get("age", 0)) if prev_state else 0

                    if (
                        self._smooth_tracks
                        and prev_state is not None
                        and (self._smooth_min_confidence <= 0.0 or conf_val >= self._smooth_min_confidence)
                    ):
                        prev_cx = prev_state.get("cx", raw_cx)
                        prev_cy = prev_state.get("cy", raw_cy)
                        prev_w = max(1.0, prev_state.get("w", raw_w))
                        prev_h = max(1.0, prev_state.get("h", raw_h))
                        
                        # Position smoothing (low-pass filter)
                        # alpha = weight of NEW data (higher = more responsive)
                        center_shift = math.hypot(raw_cx - prev_cx, raw_cy - prev_cy)
                        if self._smooth_max_center_shift <= 0.0 or center_shift <= self._smooth_max_center_shift:
                            alpha_pos = self._smooth_position_alpha
                            # FIX: alpha should be weight of NEW data, not old
                            smooth_cx = alpha_pos * raw_cx + (1.0 - alpha_pos) * prev_cx
                            smooth_cy = alpha_pos * raw_cy + (1.0 - alpha_pos) * prev_cy
                        
                        # Size smoothing (low-pass filter)
                        max_ratio = self._smooth_max_scale_change
                        ratio_w = raw_w / prev_w if prev_w > 0 else 1.0
                        ratio_h = raw_h / prev_h if prev_h > 0 else 1.0
                        
                        alpha_size = self._smooth_size_alpha
                        if max_ratio <= 1.0 or (ratio_w <= max_ratio and ratio_w >= (1.0 / max_ratio)):
                            # FIX: alpha should be weight of NEW data
                            smooth_w = alpha_size * raw_w + (1.0 - alpha_size) * prev_w
                        if max_ratio <= 1.0 or (ratio_h <= max_ratio and ratio_h >= (1.0 / max_ratio)):
                            smooth_h = alpha_size * raw_h + (1.0 - alpha_size) * prev_h
                    
                    # Ensure valid dimensions
                    smooth_w = max(1.0, smooth_w)
                    smooth_h = max(1.0, smooth_h)
                    
                    # Convert back to bbox coordinates
                    smooth_x1 = smooth_cx - 0.5 * smooth_w
                    smooth_y1 = smooth_cy - 0.5 * smooth_h
                    smooth_x2 = smooth_cx + 0.5 * smooth_w
                    smooth_y2 = smooth_cy + 0.5 * smooth_h
                    
                    # Clamp to frame boundaries
                    if self.w > 0:
                        smooth_x1 = max(0.0, min(smooth_x1, self.w - 1.0))
                        smooth_x2 = max(smooth_x1 + 1.0, min(smooth_x2, self.w - 1.0))
                    if self.h > 0:
                        smooth_y1 = max(0.0, min(smooth_y1, self.h - 1.0))
                        smooth_y2 = max(smooth_y1 + 1.0, min(smooth_y2, self.h - 1.0))
                    
                    # Recalculate after clamping
                    smooth_w = max(1.0, smooth_x2 - smooth_x1)
                    smooth_h = max(1.0, smooth_y2 - smooth_y1)
                    smooth_cx = smooth_x1 + 0.5 * smooth_w
                    smooth_cy = smooth_y1 + 0.5 * smooth_h
                    
                    # Calculate velocity
                    vx = vy = 0.0
                    if prev_state is not None and dt > 1e-3:
                        vx = (smooth_cx - prev_state.get("cx", smooth_cx)) / dt
                        vy = (smooth_cy - prev_state.get("cy", smooth_cy)) / dt

                    age_frames = prev_age + 1

                    # Store state
                    state_entry = {
                        "cx": smooth_cx,
                        "cy": smooth_cy,
                        "w": smooth_w,
                        "h": smooth_h,
                        "cid": cid,
                        "vx": vx,
                        "vy": vy,
                        "raw_cx": raw_cx,
                        "raw_cy": raw_cy,
                        "raw_w": raw_w,
                        "raw_h": raw_h,
                        "confidence": conf_val,
                        "last_seen_time": time.time(),  # Track when last seen for cleanup
                        "age": age_frames,
                        "missed": 0,
                        "det_index": det_index,
                    }
                    if prev_state is not None:
                        for key in ("plate", "plate_conf", "plate_cached"):
                            if key in prev_state and key not in state_entry:
                                state_entry[key] = prev_state[key]
                    new_state[tid] = state_entry

                    # Update array with smoothed coordinates
                    smoothed_arr = arr.copy()
                    smoothed_arr[:4] = [smooth_x1, smooth_y1, smooth_x2, smooth_y2]
                    if smoothed_arr.size >= 6:
                        smoothed_arr[5] = conf_val
                    if smoothed_arr.size >= 7:
                        smoothed_arr[6] = cid

                    # Giảm warmup xuống 1 frame để bbox hiện ngay lập tức
                    if age_frames > 0:  # Chỉ cần 1 frame là đủ (giảm lag)
                        output_tracks.append(smoothed_arr)
                        if age_frames == 1:
                            logger.debug("🆕 Track %d active immediately (age=%d)", tid, age_frames)
                    else:
                        if self.frame_idx % 60 == 1:
                            logger.debug("⏳ Track %d initializing (age=%d)", tid, age_frames)

                tracks = output_tracks
                
                # Merge new_state with existing track_state (preserve old tracks for continuity)
                # Only update tracks that appear in current frame, keep others for prediction
                for tid, state in new_state.items():
                    self._track_state[tid] = state

                # Cleanup old tracks aggressively (not seen for > 0.5 seconds) to prevent memory leak
                # Only keep tracks that are actively being detected or very recently seen
                cleanup_threshold = 0.5  # seconds - AGGRESSIVE cleanup to prevent ghost boxes
                current_time = time.time()
                tracks_to_remove = []
                for tid, state in list(self._track_state.items()):
                    if tid in new_state:
                        continue

                    prev_age = int(state.get('age', 0))
                    missed = int(state.get('missed', 0)) + 1
                    state['missed'] = missed
                    self._track_state[tid] = state

                    if prev_age <= 2 or missed >= 2:
                        tracks_to_remove.append(tid)
                        continue

                    last_seen = state.get('last_seen_time', current_time)
                    age = current_time - last_seen
                    if age > cleanup_threshold:
                        tracks_to_remove.append(tid)
                
                # Remove old tracks
                if tracks_to_remove:
                    for tid in tracks_to_remove:
                        del self._track_state[tid]
                    if self.frame_idx % 100 == 0:
                        logger.info(f"🧹 Removed {len(tracks_to_remove)} old tracks (not seen for >{cleanup_threshold}s)")
                
                # Update last_seen_time for active tracks
                for tid in new_state.keys():
                    if tid in self._track_state:
                        self._track_state[tid]['last_seen_time'] = current_time
                
                if output_tracks and self.frame_idx % 30 == 1:
                    stable_ids = sorted({int(arr[4]) for arr in output_tracks if arr.size >= 5})
                    if stable_ids:
                        logger.info("🎯 Stable track IDs (>2 frames): %s", stable_ids)

                self.last_detect_ts = now
                detect_duration = time.perf_counter() - detect_start
                self._update_detect_interval(detect_duration)
                
                # Run OCR on detected vehicles (with debounce)
                if self.enable_ocr and self.ocr_service and len(output_tracks) > 0:
                    for arr in output_tracks:
                        if arr.size < 5:
                            continue
                        try:
                            x1, y1, x2, y2 = arr[:4].tolist()
                            tid = int(arr[4])
                            
                            # Update frame count for this track
                            self.ocr_service.update_track_frame_count(tid)
                            
                            # Try to run OCR (debounce logic inside)
                            ocr_result = self.ocr_service.run_ocr_on_vehicle_crop(
                                frame=frame,
                                vehicle_bbox=[x1, y1, x2, y2],
                                track_id=tid
                            )
                            
                            # Store OCR result in track state for later use
                            if ocr_result and tid in new_state:
                                new_state[tid]['plate'] = ocr_result.get('plate')
                                new_state[tid]['plate_conf'] = ocr_result.get('conf', 0.0)
                                new_state[tid]['plate_cached'] = ocr_result.get('cached', False)
                        
                        except Exception as e:
                            logger.debug(f"OCR error for track: {e}")
                    
                    # Cleanup old tracks every 100 frames
                    if self.frame_idx % 100 == 0:
                        active_tids = [int(arr[4]) for arr in output_tracks if arr.size >= 5]
                        ocr_cfg = OCR_SETTINGS or {}
                        max_age = float(ocr_cfg.get("max_track_age_sec", 5.0))
                        self.ocr_service.cleanup_old_tracks(active_tids, max_age_sec=max_age)
                
                if self.frame_idx % 100 == 1:
                    active_tids = list(new_state.keys())
                    total_tids = list(self._track_state.keys())
                    logger.info(f"✅ Detection complete: {len(new_state)} active tracks, {len(total_tids)} total tracks in state (smoothed: {self._smooth_tracks})")
                    if len(active_tids) > 0:
                        logger.info(f"🔗 Active track IDs: {sorted(active_tids)[:10]}..." if len(active_tids) > 10 else f"🔗 Active track IDs: {sorted(active_tids)}")
                    if len(total_tids) > len(active_tids):
                        predicted_tids = [tid for tid in total_tids if tid not in active_tids]
                        logger.info(f"📊 Predicted tracks (not in frame): {len(predicted_tids)} tracks (will be cleaned up if >0.5s old)")
                
                # === TRAFFIC LIGHT INTEGRATION ===
                # Publish frame + tracks to Traffic Light buffer
                try:
                    from app.services.traffic_light_manager import frame_buffer
                    
                    # Convert tracks to dict format for TL worker
                    tracks_dict = []
                    for arr in output_tracks:
                        if arr.size < 5:
                            continue
                        try:
                            x1, y1, x2, y2 = arr[:4].tolist()
                            tid = int(arr[4])
                            conf_val = float(arr[5]) if arr.size >= 6 else 1.0
                            cls_id = int(arr[6]) if arr.size >= 7 else 0
                            
                            tracks_dict.append({
                                "track_id": tid,
                                "bbox": [float(x1), float(y1), float(x2), float(y2)],
                                "confidence": conf_val,
                                "class_id": cls_id,
                                "class_name": CLASS_NAMES.get(cls_id, "vehicle")
                            })
                        except Exception as e:
                            logger.debug(f"Failed to convert track for TL buffer: {e}")
                    
                    # Publish to TL buffer (only if camera_id is set)
                    if self.camera_id and self.camera_id != "default":
                        frame_buffer.update_frame(
                            camera_id=self.camera_id,
                            frame=frame,
                            tracks=tracks_dict,
                            frame_index=self.frame_idx
                        )
                        
                        if self.frame_idx % 100 == 1:
                            logger.info(f"📤 Published to TL buffer: camera={self.camera_id}, tracks={len(tracks_dict)}")
                except Exception as e:
                    # Don't crash main pipeline if TL buffer fails
                    if self.frame_idx % 100 == 1:
                        logger.debug(f"TL buffer update failed: {e}")
            else:
                # Predict tracks between keyframes for perceived 60 fps
                # IMPORTANT: Only predict tracks that were recently seen (within 0.3s) to avoid ghost boxes
                dt = min(now - self.last_detect_ts, 0.5)
                current_time = time.time()
                max_prediction_age = 0.3  # Only predict tracks seen within 0.3 seconds
                
                for tid, s in self._track_state.items():
                    # Skip tracks that are too old (not seen recently)
                    last_seen = s.get('last_seen_time', 0.0)
                    age = current_time - last_seen
                    if age > max_prediction_age:
                        continue  # Skip old tracks - don't predict them

                    age_frames = int(s.get("age", 0))
                    if age_frames <= 2:
                        continue  # Wait for track to stabilise before predicting

                    if int(s.get("missed", 0)) > 0:
                        continue  # Skip tracks that are currently missing detections

                    # Get smoothed state
                    prev_cx = s.get("cx", 0.0)
                    prev_cy = s.get("cy", 0.0)
                    prev_w = max(1.0, s.get("w", 1.0))
                    prev_h = max(1.0, s.get("h", 1.0))
                    
                    # Predict new position using velocity
                    vx = s.get("vx", 0.0)
                    vy = s.get("vy", 0.0)
                    pred_cx = prev_cx + vx * dt
                    pred_cy = prev_cy + vy * dt
                    pred_w = prev_w
                    pred_h = prev_h
                    
                    # Apply smoothing to predicted position (if enabled)
                    if self._smooth_tracks:
                        # Smooth predicted position with previous position
                        alpha_pred = 0.3  # Light smoothing for predictions (30% new, 70% previous)
                        smooth_cx = (1.0 - alpha_pred) * prev_cx + alpha_pred * pred_cx
                        smooth_cy = (1.0 - alpha_pred) * prev_cy + alpha_pred * pred_cy
                    else:
                        smooth_cx = pred_cx
                        smooth_cy = pred_cy
                    
                    # Use smoothed values
                    cx = smooth_cx
                    cy = smooth_cy
                    w, h = pred_w, pred_h
                    
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

                    conf_val = float(s.get("confidence", 1.0))
                    cls_id = int(s.get("cid", 0))
                    tracks.append(np.array([x1, y1, x2, y2, tid, conf_val, cls_id], dtype=float))

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
                        # ByteTrack format: [x1, y1, x2, y2, tid, score, cls, *extras]
                        if len(t) >= 7:
                            x1, y1, x2, y2, tid, conf_val, cls_id = t[:7]
                        elif len(t) >= 6:
                            x1, y1, x2, y2, tid, conf_val = t[:6]
                            cls_id = 0  # default when class missing
                        elif len(t) >= 5:
                            x1, y1, x2, y2, tid = t[:5]
                            conf_val = 1.0
                            cls_id = 0
                        else:
                            x1, y1, x2, y2 = t[:4]
                            tid = -1
                            conf_val = 1.0
                            cls_id = 0

                        # Get plate info from track state (if OCR enabled)
                        plate_text = None
                        plate_conf = 0.0
                        if self.enable_ocr and tid >= 0:
                            track_state = self._track_state.get(int(tid))
                            if track_state:
                                plate_text = track_state.get('plate')
                                plate_conf = track_state.get('plate_conf', 0.0)
                        
                        detection_obj = {
                            "bbox": [float(x1), float(y1), float(x2), float(y2)],
                            "track_id": int(tid),
                            "class_id": int(cls_id),
                            "class_name": CLASS_NAMES.get(int(cls_id), "vehicle"),
                            "confidence": float(conf_val),
                            "violation": None   # TODO: integrate violation detection logic
                        }
                        
                        # Add plate info if available
                        if plate_text:
                            detection_obj["plate"] = plate_text
                            detection_obj["plate_conf"] = float(plate_conf)
                        
                        detections.append(detection_obj)
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
                    plate_text = det.get("plate")
                    plate_conf = det.get("plate_conf", 0.0)
                    
                    # Validate bbox coordinates
                    if x1 >= x2 or y1 >= y2 or x1 < 0 or y1 < 0:
                        logger.warning(f"⚠️  Invalid bbox: ({x1}, {y1}, {x2}, {y2})")
                        continue
                    
                    # Get color (bright, high contrast colors)
                    color = CLASS_COLORS.get(cls_id, (0, 255, 0))
                    
                    # Draw bbox with VERY THICK lines for maximum visibility
                    cv2.rectangle(frame, (x1, y1), (x2, y2), color, 1, cv2.LINE_AA)
                    
                    # Draw label with background (larger, bold)
                    label = f"{cls_name}"
                    if plate_text:
                        label += f" | {plate_text}"
                    
                    font_scale = 0.7
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
        if self.warmup_seconds > 0:
            self._warmup_until = time.perf_counter() + self.warmup_seconds
            self._warmup_logged = False
            logger.info("⏳ Holding frames for %.1fs warmup before streaming", self.warmup_seconds)
        else:
            self._warmup_until = None
            self._warmup_logged = False

        self._open()

        self.t_cap = Thread(target=self._thread_capture, daemon=True, name="capture")
        self.t_det = Thread(target=self._thread_infer, daemon=True, name="infer")
        self.t_enc = Thread(target=self._thread_annotate_encode, daemon=True, name="encode")
        
        self.t_cap.start()
        self.t_det.start()
        self.t_enc.start()

        try:
            if self.camera_id and self.camera_id != "default":
                from app.services.traffic_light_manager import frame_buffer

                frame_buffer.set_state(self.camera_id, "RUNNING")
        except Exception:
            logger.debug("Unable to mark TL pipeline running", exc_info=True)

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

        try:
            if self.camera_id and self.camera_id != "default":
                from app.services.traffic_light_manager import frame_buffer

                frame_buffer.set_state(self.camera_id, "STOPPED")
        except Exception:
            logger.debug("Unable to mark TL pipeline stopped", exc_info=True)
    
    def close(self):
        """Stop threads (idempotent) then release all resources safely"""
        # Ensure threads have been asked to stop and given time to exit
        self.stop()
        logger.info("🧹 Releasing resources...")
        self._release()

    # --------- Controls ---------
    def pause(self):
        self.pause_ev.set()
        try:
            if self.camera_id and self.camera_id != "default":
                from app.services.traffic_light_manager import frame_buffer

                frame_buffer.set_state(self.camera_id, "PAUSED")
        except Exception:
            logger.debug("Unable to mark TL pipeline paused", exc_info=True)
        logger.info("⏸️  Paused")

    def resume(self):
        self.pause_ev.clear()
        try:
            if self.camera_id and self.camera_id != "default":
                from app.services.traffic_light_manager import frame_buffer

                frame_buffer.set_state(self.camera_id, "RUNNING")
        except Exception:
            logger.debug("Unable to mark TL pipeline resumed", exc_info=True)
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
        packet = {
            "type": "info",
            "frame_width": self.w,
            "frame_height": self.h,
            "total_frames": self.total,
            "model": "yolo",
            "tracker": "bytetrack",  # Always use ByteTrack with ONNX models
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
                "roi_drawing": self.enable_roi_drawing,
                "ocr": self.enable_ocr
            },
            "warmup_seconds": self.warmup_seconds,
            "warmup_active": bool(self._warmup_until),
        }

        # Add OCR info if enabled
        if self.enable_ocr and self.ocr_service:
            packet["ocr"] = {
                "model_type": self.ocr_model_type,
                "device": self.ocr_service.device if hasattr(self.ocr_service, 'device') else "unknown",
                "stats": self.ocr_service.get_stats()
            }
        
        return packet
    
    def next_frame(self) -> Tuple[Optional[dict], Optional[bytes]]:
        """
        Get next frame with server-side pacing
        
        Returns:
            (header_dict, jpeg_bytes) - header=None if not ready yet
        
        Pacing: Sleep to maintain target_fps, preventing overwhelming the client
        """
        # Warmup phase: keep processing but do not stream frames yet
        if self._warmup_until is not None:
            remaining = self._warmup_until - time.perf_counter()
            if remaining > 0:
                if not self._warmup_logged:
                    logger.info("⏳ Warmup in progress - streaming will start in %.1fs", remaining)
                    self._warmup_logged = True
                # Light sleep to avoid busy loop while letting pipelines fill queues
                time.sleep(min(0.05, max(0.0, remaining)))
                return None, None

            logger.info("🚀 Warmup complete - starting realtime stream")
            self._warmup_until = None
            self._warmup_logged = False
            # Reset pacing baseline after warmup to avoid large FPS spikes
            self.last_sent_ts = time.perf_counter()

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
            "detections": self._current_detections,  # Include detections metadata
            "objects": self._current_detections  # Backward compatibility (same as detections)
        }
        
        # Log progress every 30 frames
        if self.frame_idx % 30 == 0:
            logger.info(f"🎬 Frame {self.frame_idx}: {fps} FPS")
        
        return header, jpeg_bytes


