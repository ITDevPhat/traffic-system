"""
Performance Configuration for >30 FPS
Optimized for RTX 3050 4GB VRAM với ONNX/TensorRT
"""

import os
import torch

# ============================================
# 🚀 CUDA Performance Optimizations
# ============================================

def setup_cuda_optimizations():
    """Setup CUDA optimizations cho >30 FPS"""
    if torch.cuda.is_available():
        # Enable TF32 for faster matmul on Ampere GPUs
        torch.backends.cuda.matmul.allow_tf32 = True
        torch.backends.cudnn.allow_tf32 = True
        
        # Enable cudnn benchmarking - tự động tìm algorithm tốt nhất
        torch.backends.cudnn.benchmark = True
        
        # Enable cudnn deterministic mode OFF (nhanh hơn)
        torch.backends.cudnn.deterministic = False
        
        # Enable cudnn
        torch.backends.cudnn.enabled = True
        
        # Set CUDA memory allocator
        os.environ['PYTORCH_CUDA_ALLOC_CONF'] = 'max_split_size_mb:512'
        
        print("✅ CUDA optimizations enabled for >30 FPS")
    else:
        print("⚠️  CUDA not available - running on CPU (slower)")


# ============================================
# 🎯 Model Inference Settings
# ============================================

# Target FPS và frame skip
TARGET_FPS = 32  # Target >30 FPS with headroom
FRAME_SKIP = 1   # Process every frame (no skip)
MAX_BATCH_SIZE = 1  # Single frame inference (lowest latency)

# Fixed detection interval for stable FPS (no adaptive throttling)
FIXED_DETECT_INTERVAL = 0.067  # 15 FPS = 67ms per frame (balanced for RTX 3050)
ENABLE_ADAPTIVE_INTERVAL = False  # Disable adaptive FPS throttling for consistent performance

# Inference settings - Optimized for RTX 3050 Performance
INFERENCE_SETTINGS = {
    "imgsz": 320,           # Much smaller for better RTX 3050 performance
    "conf": 0.5,            # Higher confidence for better performance (fewer detections)
    "iou": 0.45,            # NMS IOU threshold
    "max_det": 50,          # Further reduced for RTX 3050 performance
    "half": False,          # FP32 precision (ONNX FP32 compatibility)
    "device": "cuda:0",     # GPU device
    "verbose": False,       # No verbose output
    "stream": False,        # Don't stream (single frame)
    "agnostic_nms": False,  # Class-specific NMS (faster)
}

# ONNX Runtime settings - Simplified for compatibility
ONNX_SETTINGS = {
    "providers": [
        'CUDAExecutionProvider',  # Simplified CUDA provider
        'CPUExecutionProvider',
    ],
    "sess_options": {
        "graph_optimization_level": 99,  # ORT_ENABLE_ALL
        "intra_op_num_threads": 4,
        "inter_op_num_threads": 4,
        "execution_mode": 0,  # ORT_SEQUENTIAL
    }
}

# TensorRT settings
TENSORRT_SETTINGS = {
    "workspace": 2 << 30,  # 2GB workspace
    "fp16_mode": True,     # FP16 precision
    "int8_mode": False,    # INT8 (requires calibration)
    "max_batch_size": 1,   # Single frame
    "dla_core": None,      # No DLA (for embedded devices)
}


# ============================================
# 📊 WebSocket Streaming Settings
# ============================================

# WebSocket FPS settings
WS_DEFAULT_FPS = 30      # Default streaming FPS
WS_MAX_FPS = 60          # Maximum allowed FPS
WS_MIN_FPS = 5           # Minimum allowed FPS

# Frame buffer settings
FRAME_BUFFER_SIZE = 2    # Small buffer for low latency
ENABLE_FRAME_DROP = True # Drop frames if backend is slow

# Async settings
ASYNC_WORKERS = 2        # Number of async workers
ENABLE_ASYNC_INFERENCE = True  # Enable async inference


# ============================================
# 🔧 ByteTrack Settings (Optimized)
# ============================================

BYTETRACK_SETTINGS = {
    "track_thresh": 0.45,     # Tăng lên để chỉ track detections tốt (giảm noise)
    "track_buffer": 15,       # Giảm buffer xuống để track mất nhanh hơn (0.5s @30fps)
    "match_thresh": 0.8,      # Giảm xuống để match linh hoạt hơn với xe di chuyển nhanh
    "frame_rate": 30,         # Expected realtime FPS for buffer scaling
    "min_box_area": 100,      # Tăng lên để loại bỏ detections quá nhỏ (noise)
    "mot20": False,           # MOT17 mode (faster)
}


# ============================================
# 🎯 Track Smoothing for Visualization Stability
# ============================================

# Track smoothing for front-end visualization stability - DISABLED for tight bbox fit
TRACK_SMOOTHING_SETTINGS = {
    "enabled": False,             # TẮT smoothing để bbox ôm sát 100% (no lag)
    "position_alpha": 0.9,        # Nếu bật lại: 90% new data = rất responsive
    "size_alpha": 0.85,           # Nếu bật lại: 85% new data
    "max_center_shift": 30.0,     # Giảm xuống để bbox không nhảy quá xa
    "max_scale_change": 1.4,      # Giảm xuống để size không thay đổi đột ngột
    "min_confidence": 0.0,        # Reserved for future confidence-aware smoothing
}


# ============================================
# 💾 Memory Management
# ============================================

# Garbage collection settings
ENABLE_AUTO_GC = False        # Disable auto GC (faster but more memory)
GC_INTERVAL_FRAMES = 300      # Run GC every 300 frames (10 sec at 30fps)

# CUDA memory settings
CUDA_EMPTY_CACHE_INTERVAL = 100  # Empty cache every 100 frames
MAX_VRAM_USAGE_MB = 3500         # Max VRAM usage (3.5GB for RTX 3050 4GB)


# ============================================
# 📈 Performance Monitoring
# ============================================

ENABLE_FPS_COUNTER = True     # Show FPS in logs
ENABLE_PROFILING = False      # Disable profiling (faster)
LOG_INTERVAL_FRAMES = 30      # Log every 30 frames (1 sec)


# ============================================
# 🎨 Canvas Rendering (Frontend)
# ============================================

CANVAS_SETTINGS = {
    "line_width": 2,           # Thinner lines (faster)
    "font_size": 12,           # Smaller font
    "enable_labels": True,     # Show labels
    "enable_confidence": True, # Show confidence
    "enable_track_id": True,   # Show track ID
    "label_format": "{label} {conf}% [{id}]",
}


# ============================================
# 🚦 Priority Model Loading
# ============================================

MODEL_PRIORITY = [
    "onnx",    # ONNX Runtime (preferred) - FP32 compatible, RTX 3050 optimized
    "pt",      # PyTorch (fallback) - slower but compatible
]


# ============================================
# 🔤 OCR Settings (License Plate Recognition)
# ============================================

OCR_SETTINGS = {
    "enabled": False,                   # Disable OCR for better performance
    "model_type": "auto",               # Auto-detect: onnx > pt
    "plate_conf_threshold": 0.6,        # Confidence threshold for plate detection
    "ocr_debounce_sec": 1.0,            # Min time between OCR calls per track (seconds)
    "min_track_frames": 3,              # Min frames before OCR (stability check)
    "bbox_expand_ratio": 0.15,          # Expand vehicle bbox before crop (15%)
    "cleanup_interval_sec": 10.0,       # Cleanup old tracks every N seconds
    "max_track_age_sec": 5.0,           # Remove tracks inactive for N seconds
}


# ============================================
# 🔍 Debug & Benchmarking
# ============================================

DEBUG_SETTINGS = {
    "print_inference_time": False,  # Don't print each inference time
    "print_tracking_time": False,   # Don't print tracking time
    "print_memory_usage": False,    # Don't print memory usage
    "save_benchmark_csv": False,    # Don't save benchmark
}


# ============================================
# 📝 Summary
# ============================================

def print_performance_config():
    """Print performance configuration summary"""
    print("\n" + "="*60)
    print("🚀 PERFORMANCE CONFIGURATION - TARGET >30 FPS")
    print("="*60)
    print(f"📊 Target FPS: {TARGET_FPS}")
    print(f"🎯 Frame Skip: {FRAME_SKIP} (process every frame)")
    print(f"💾 Max Batch Size: {MAX_BATCH_SIZE}")
    precision_mode = "FP16" if INFERENCE_SETTINGS['half'] else "FP32"
    print(f"🔧 Precision Mode: {precision_mode} (ONNX FP32 Compatible)")
    print(f"🖥️  Device: {INFERENCE_SETTINGS['device']}")
    print(f"📐 Input Size: {INFERENCE_SETTINGS['imgsz']}")
    print(f"🎚️  Confidence: {INFERENCE_SETTINGS['conf']}")
    print(f"🌐 WebSocket FPS: {WS_DEFAULT_FPS} (default)")
    print(f"📦 Model Priority: {' > '.join(MODEL_PRIORITY)}")
    print(f"🔄 ByteTrack Buffer: {BYTETRACK_SETTINGS['track_buffer']} frames")
    print("="*60 + "\n")


# Auto setup on import
setup_cuda_optimizations()

