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
from threading import Thread, Event
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

# Custom YOLO model class IDs (0-indexed, not COCO)
VEHICLE_IDS = {0, 1, 2, 3}  # bus, car, motorbike, truck

# Class names (match your custom model)
CLASS_NAMES = {
    0: "bus",
    1: "car", 
    2: "motorbike",
    3: "truck"
}

# Colors for different classes (BGR)
CLASS_COLORS = {
    0: (255, 0, 0),      # bus - blue
    1: (0, 255, 0),      # car - green
    2: (0, 255, 255),    # motorbike - yellow
    3: (255, 165, 0)     # truck - orange
}


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
        enable_roi_drawing: bool = True
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
        self.device = "cuda" if (torch and torch.cuda.is_available()) else "cpu"
        logger.info(f"🖥️  Device: {self.device}")
        
        # CUDA optimizations
        if torch and self.device == "cuda":
            torch.backends.cudnn.benchmark = True
            try:
                torch.backends.cuda.matmul.allow_tf32 = True
                torch.backends.cudnn.allow_tf32 = True
                logger.info("✅ CUDA optimizations enabled")
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
        self.detect_interval = 1.0 / max(self.veh_detect_hz, 1)
        self.last_detect_ts = 0.0

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
        
        # Model path auto-detection
        possible_paths = [
            self.model_path,
            os.path.join("traffic-server", self.model_path),
            os.path.join("models", os.path.basename(self.model_path))
        ]
        
        actual_path = None
        for path in possible_paths:
            if os.path.exists(path):
                actual_path = path
                break
        
        if actual_path is None:
            # Fallback: scan models directory and pick a reasonable default
            search_dirs = [
                "models",
                os.path.join("traffic-server", "models")
            ]
            found_files = []
            for d in search_dirs:
                try:
                    if os.path.exists(d):
                        for name in os.listdir(d):
                            if name.lower().endswith(".pt"):
                                found_files.append(os.path.join(d, name))
                except Exception:
                    continue

            # Selection priority
            def score(path: str) -> int:
                name = os.path.basename(path).lower()
                s = 0
                if "vehicle" in name:
                    s += 100
                if any(k in name for k in ["v8n", "v10n", "yolov8n", "yolo_vehicle_v10n"]):
                    s += 50  # prefer nano
                if any(k in name for k in ["v8m", "v10m", "m.pt"]):
                    s += 10  # medium as fallback
                return s

            if found_files:
                found_files.sort(key=score, reverse=True)
                actual_path = found_files[0]
                logger.warning(
                    f"⚠️  Model '{self.model_path}' not found. Using fallback: {actual_path}"
                )
            else:
                raise RuntimeError(
                    f"❌ Model not found. Tried: {possible_paths} and no *.pt found in {search_dirs}"
                )
        
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

            logger.info(f"⚙️  Loading YOLO from: {actual_path}")
            self.model = YOLO(actual_path)
            self.model.to(self.device)
        
        # Performance optimizations
        try:
            self.model.fuse()
        except:
            pass
        
        # Enable FP16 for GPU (2x faster)
        if self.device == "cuda":
            try:
                # Some models may already be half; call guardedly
                if hasattr(self.model, "half"):
                    self.model.half()
                logger.info("✅ FP16 enabled")
            except Exception as e:
                logger.warning(f"⚠️  FP16 failed: {e}")

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
            self.detect_interval = 1.0 / max(self.veh_detect_hz, 1)
        
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
                # YOLO detect (keyframe)
                try:
                    results = self.model.predict(
                        frame,
                        conf=self.conf,
                        imgsz=self.imgsz,
                        verbose=False,
                        classes=list(VEHICLE_IDS),
                        device=self.device,
                        half=True
                    )[0]
                except Exception as e:
                    if self.stop_ev.is_set() or self.model is None:
                        break
                    raise e

                boxes = results.boxes
                if boxes is not None and len(boxes) > 0:
                    cls = boxes.cls.cpu().numpy().astype(int)
                    if self.frame_idx % 30 == 1:
                        logger.info(f"🔍 Frame {self.frame_idx}: Raw detections: {len(cls)} objects, classes: {cls}")
                    mask = np.isin(cls, list(VEHICLE_IDS))
                    xyxy = boxes.xyxy.cpu().numpy()[mask]
                    confs = boxes.conf.cpu().numpy()[mask]
                    clss = cls[mask]
                    if self.frame_idx % 30 == 1 and len(clss) > 0:
                        logger.info(f"🔍 Frame {self.frame_idx}: Filtered: {len(clss)} vehicles, classes: {clss}")
                else:
                    xyxy = np.empty((0, 4), dtype=float)
                    confs = np.empty((0,), dtype=float)
                    clss = np.empty((0,), dtype=int)
                    if self.frame_idx % 30 == 1:
                        logger.info(f"⚠️ Frame {self.frame_idx}: No detections from YOLO")

                if HAVE_BOXMOT and self.tracker is not None and self.enable_tracking:
                    online_targets = self.tracker.update(
                        dets=xyxy,
                        scores=confs,
                        cls_ids=clss,
                        img=frame
                    )
                    tracks = online_targets
                elif self.enable_tracking:
                    # Fallback: run ultralytics tracker (still heavy)
                    if self.stop_ev.is_set() or self.model is None:
                        break
                    try:
                        res2 = self.model.track(
                            frame,
                            conf=self.conf,
                            persist=True,
                            verbose=False,
                            classes=list(VEHICLE_IDS),
                            device=self.device,
                            imgsz=self.imgsz,
                            half=True
                        )[0]
                    except Exception as e:
                        if self.stop_ev.is_set() or self.model is None:
                            break
                        raise e
                    if res2.boxes is not None and len(res2.boxes) > 0:
                        for box in res2.boxes:
                            cls_id = int(box.cls[0])
                            if cls_id not in VEHICLE_IDS:
                                continue
                            x1, y1, x2, y2 = map(float, box.xyxy[0].tolist())
                            tid = int(box.id[0]) if box.id is not None else -1
                            tracks.append(np.array([x1, y1, x2, y2, tid, cls_id], dtype=float))
                else:
                    # No tracking - just raw detections
                    if len(xyxy) > 0:
                        for i, (x1, y1, x2, y2) in enumerate(xyxy):
                            cls_id = int(clss[i]) if i < len(clss) else 0
                            tracks.append(np.array([x1, y1, x2, y2, i, cls_id], dtype=float))

                # Update track state and velocities
                dt = (now - self.last_detect_ts) if self.last_detect_ts else (1.0 / max(self.veh_detect_hz, 1))
                new_state: dict[int, dict] = {}
                for tr in tracks:
                    x1, y1, x2, y2, tid, cid = tr
                    tid = int(tid)
                    cx = 0.5 * (x1 + x2)
                    cy = 0.5 * (y1 + y2)
                    w = max(1.0, x2 - x1)
                    h = max(1.0, y2 - y1)
                    vx = vy = 0.0
                    if tid in self._track_state and dt > 1e-3:
                        vx = (cx - self._track_state[tid]["cx"]) / dt
                        vy = (cy - self._track_state[tid]["cy"]) / dt
                    new_state[tid] = {"cx": cx, "cy": cy, "w": w, "h": h, "cid": int(cid), "vx": vx, "vy": vy}
                self._track_state = new_state
                self.last_detect_ts = now
            else:
                # Predict tracks between keyframes for perceived 60 fps
                dt = min(now - self.last_detect_ts, 0.5)
                for tid, s in self._track_state.items():
                    cx = s["cx"] + s["vx"] * dt
                    cy = s["cy"] + s["vy"] * dt
                    w, h = s["w"], s["h"]
                    # Clamp to frame
                    cx = max(0.5 * w, min(cx, self.w - 0.5 * w))
                    cy = max(0.5 * h, min(cy, self.h - 0.5 * h))
                    x1 = cx - 0.5 * w
                    y1 = cy - 0.5 * h
                    x2 = cx + 0.5 * w
                    y2 = cy + 0.5 * h
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
            
            # Prepare detections metadata (ALWAYS, for future violations detection)
            detections = []
            if tracks is not None and len(tracks) > 0:
                for t in tracks:
                    x1, y1, x2, y2, tid, cls_id = t
                    detections.append({
                        "bbox": [float(x1), float(y1), float(x2), float(y2)],
                        "track_id": int(tid),
                        "class_id": int(cls_id),
                        "class_name": CLASS_NAMES.get(int(cls_id), "vehicle"),
                        "confidence": 1.0,  # TODO: add real confidence from YOLO results
                        "violation": None   # TODO: integrate violation detection logic
                    })
            
            # Store detections for this frame (accessible in send thread)
            self._current_detections = detections
            
            # Optionally draw bbox on frame (backward compatible mode)
            if self.enable_bbox_drawing and len(detections) > 0:
                # DEBUG: Log first detection
                if self.frame_idx % 30 == 1:
                    logger.info(f"🎯 Frame {self.frame_idx}: {len(detections)} detections")
                
                for det in detections:
                    x1, y1, x2, y2 = [int(v) for v in det["bbox"]]
                    tid = det["track_id"]
                    cls_id = det["class_id"]
                    cls_name = det["class_name"]
                    
                    # Get color
                    color = CLASS_COLORS.get(cls_id, (0, 255, 0))
                    
                    # Draw bbox
                    cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2, cv2.LINE_AA)
                    
                    # Draw label with background
                    label = f"{cls_name} #{tid}"
                    (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
                    cv2.rectangle(frame, (x1, y1 - th - 8), (x1 + tw + 4, y1), color, -1)
                    cv2.putText(frame, label, (x1 + 2, y1 - 4),
                              cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2, cv2.LINE_AA)
            else:
                # DEBUG: No tracks
                if self.frame_idx % 30 == 1:
                    logger.info(f"⚠️ Frame {self.frame_idx}: No detections")
            
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
            "modules": {
                "yolo": self.enable_yolo,
                "tracking": self.enable_tracking,
                "bbox_drawing": self.enable_bbox_drawing
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

