# 🚨 Emergency FPS Fix - Detection Pipeline Bottleneck

## 🔍 Problem Analysis
From logs:
- **Stream FPS**: 44.49 FPS, 41.72 FPS ✅ (WebSocket OK)
- **Detection FPS**: 5.6 FPS ❌ (Detection pipeline bottleneck)

## 🎯 Root Cause
Detection pipeline is the bottleneck, not WebSocket streaming.

## 🚀 Emergency Fixes Applied

### 1. Reduced Inference Size
```diff
Frontend:
- inference_size: 640
+ inference_size: 480

Backend:
- "imgsz": 640
+ "imgsz": 480
```

### 2. Relaxed Detection Interval
```diff
- FIXED_DETECT_INTERVAL = 0.033  # 30 FPS
+ FIXED_DETECT_INTERVAL = 0.05   # 20 FPS (more stable)
```

### 3. Reduced Detection Load
```diff
- "max_det": 100
+ "max_det": 50

- "conf": 0.35
+ "conf": 0.5

Frontend:
- conf: 0.5
+ conf: 0.6
```

### 4. Disabled OCR (Performance Killer)
```diff
- "enabled": True,    # Enable OCR
+ "enabled": False,   # Disable OCR for better performance
```

## 📊 Expected Results

### Before:
- Detection FPS: 5.6 FPS
- Stream FPS: 44 FPS
- **Bottleneck**: Detection pipeline

### After:
- Detection FPS: ~20 FPS (target)
- Stream FPS: ~30 FPS
- **Balanced**: Both pipelines optimized

## 🔧 Performance Impact

1. **Inference Size**: 640→480 = ~44% fewer pixels = ~44% faster
2. **Max Detections**: 100→50 = 50% fewer objects to process
3. **Confidence**: 0.35→0.5 = Fewer false positives to track
4. **OCR Disabled**: No plate recognition overhead
5. **Detection Interval**: 33ms→50ms = 20 FPS target (more achievable)

## 🚀 Test Instructions

1. **Restart backend**: `python start_server.py`
2. **Refresh frontend**
3. **Load video and start detection**
4. **Check logs for**:
   ```
   📊 Fixed Interval Mode: detect_fps=XX.X
   ```
   Should see ~15-20 FPS instead of 5.6 FPS

## 🎯 If Still Slow

Try these additional fixes:

### Option A: Further reduce inference size
```python
# performance_config.py
"imgsz": 320,  # Even smaller
```

### Option B: Increase detection interval
```python
# performance_config.py
FIXED_DETECT_INTERVAL = 0.1  # 10 FPS
```

### Option C: Reduce tracking buffer
```python
# performance_config.py
BYTETRACK_SETTINGS = {
    "track_buffer": 5,  # Reduced from 15
}
```

## 📝 Rollback if Needed

If detection quality degrades too much:

1. **Re-enable OCR**: `"enabled": True`
2. **Increase inference size**: `"imgsz": 640`
3. **Lower confidence**: `"conf": 0.35`

---
**Emergency Patch Applied**: December 11, 2025
**Target**: 15-20 FPS detection (stable performance)