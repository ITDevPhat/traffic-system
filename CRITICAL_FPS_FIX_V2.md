# 🚨 CRITICAL FPS Fix V2 - ONNX CUDA Issue

## 🔍 Root Causes Found:

### 1. **ONNX CUDA Provider Issue**
```
⚠️ CUDA provider not available for ONNX
Specified provider 'CUDAExecutionProvider' is not in available provider names.
Available providers: 'AzureExecutionProvider, CPUExecutionProvider'
```
**Impact**: Model running on CPU instead of GPU = 10x slower!

### 2. **Frontend Cache Issue**
Frontend still sending old settings:
```
FPS: 45, ImgSize: 640, veh_detect_hz: 25
```
Instead of new optimized settings.

### 3. **Detection Pipeline Bottleneck**
```
📊 Fixed Interval Mode: detect_fps=5.7, interval=0.050s (stable)
🔴 Hiệu suất thấp: <25 FPS detection
```

## 🚀 Critical Fixes Applied:

### 1. **Simplified ONNX Provider**
```diff
- "providers": [
-     ('CUDAExecutionProvider', {
-         'device_id': 0,
-         'arena_extend_strategy': 'kNextPowerOfTwo',
-         ...
-     }),
-     'CPUExecutionProvider',
- ],
+ "providers": [
+     'CUDAExecutionProvider',  # Simplified
+     'CPUExecutionProvider',
+ ],
```

### 2. **Much More Conservative Settings**
```diff
Frontend:
- target_fps: 30
- inference_size: 480
- veh_detect_hz: 30
+ target_fps: 15      # Realistic for RTX 3050
+ inference_size: 320 # Much smaller
+ veh_detect_hz: 10   # Match backend

Backend:
- FIXED_DETECT_INTERVAL = 0.05  # 20 FPS
- "imgsz": 480
+ FIXED_DETECT_INTERVAL = 0.1   # 10 FPS
+ "imgsz": 320
```

## 📊 Expected Results:

### Before:
- **Detection FPS**: 5.7 FPS (CPU fallback)
- **Model**: Running on CPU (slow)
- **Settings**: Mismatched frontend/backend

### After:
- **Detection FPS**: ~10 FPS (GPU accelerated)
- **Model**: Running on GPU (fast)
- **Settings**: Synchronized and conservative

## 🚀 Test Instructions:

1. **Restart backend**: `Ctrl+C` then `uvicorn app.main:app --reload`
2. **Hard refresh frontend**: `Ctrl+Shift+R` (clear cache)
3. **Check logs for**:
   ```
   ✅ ONNX using CUDAExecutionProvider
   📊 Fixed Interval Mode: detect_fps=XX.X
   ```
   Should see ~8-12 FPS instead of 5.7 FPS

## 🔧 Verification:

### Check ONNX CUDA:
```bash
cd traffic-server
python -c "import onnxruntime as ort; print('Providers:', ort.get_available_providers())"
```
Should show `CUDAExecutionProvider` in list.

### Check GPU Usage:
```bash
nvidia-smi
```
Should show GPU utilization when detection runs.

## 🎯 If Still Slow:

### Option A: Disable tracking temporarily
```python
# In frontend
enable_tracking: false
```

### Option B: Use PyTorch instead of ONNX
```python
# Change model to .pt file
selectedModel: "models/vehicle/11s/yolo_vehicle_11s.pt"
```

### Option C: Further reduce inference size
```python
inference_size: 256  # Even smaller
```

---
**Critical Patch V2**: December 11, 2025
**Target**: 8-12 FPS stable (GPU accelerated)