# 🚀 Hướng Dẫn Chạy Hệ Thống - Optimized >30 FPS

## ⚡ Quick Start (3 Steps)

### Step 1: Activate Conda Environment LVTN

```bash
cd traffic-server
setup_lvtn_env.bat
```

**Expected output:**
```
========================================
  Traffic Detection System - LVTN
  Performance Optimized Setup
========================================

[OK] Conda environment 'LVTN' activated
Setting performance optimization flags...
[OK] Performance flags set

Checking GPU status...
CUDA Available: True
GPU: NVIDIA GeForce RTX 3050 Laptop GPU
CUDA Version: 11.8

========================================
  Environment Ready!
  Run: uvicorn app.main:app --host 0.0.0.0 --port 8000
========================================
```

---

### Step 2: Run Optimized Backend

**Option A: Using batch script (Recommended)**
```bash
run_optimized.bat
```

**Option B: Manual command**
```bash
cd app
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 1 --loop uvloop
```

**Expected output:**
```
============================================================
🚀 PERFORMANCE CONFIGURATION - TARGET >30 FPS
============================================================
📊 Target FPS: 30
🎯 Frame Skip: 1 (process every frame)
💾 Max Batch Size: 1
🔧 FP16 Precision: True
🖥️  Device: cuda:0
📐 Input Size: 640
🎚️  Confidence: 0.5
🌐 WebSocket FPS: 30 (default)
📦 Model Priority: engine > onnx > pt
🔄 ByteTrack Buffer: 30 frames
============================================================

✅ CUDA optimizations enabled for >30 FPS
📦 Loading YOLO models (auto-detect: .engine > .onnx > .pt)...
✅ Vehicle model loaded: models/vehicle/v10m/yolo_vehicle_v10m.engine (engine, 42.1MB)
🎉 1/4 models loaded successfully!
💾 GPU VRAM: 0.32GB / 4.00GB allocated

INFO:     Started server process [12345]
INFO:     Uvicorn running on http://0.0.0.0:8000
```

---

### Step 3: Run Frontend

**Open new terminal:**
```bash
cd traffic-system
npm run dev
```

**Expected output:**
```
> traffic-web@0.1.0 dev
> next dev

  ▲ Next.js 14.x.x
  - Local:        http://localhost:3000
  - Ready in 2.3s
```

---

## ✅ Verify System

### 1. Check Backend Health

```bash
curl http://localhost:8000/api/realtime/health
```

**Expected:**
```json
{
  "status": "ok",
  "models_loaded": true,
  "device": "cuda:0",
  "gpu_available": true
}
```

### 2. Check Frontend

Open browser: **http://localhost:3000/detection**

Expected:
- ✅ Grid view with video cards
- ✅ Toggle "🔴 Realtime Detection" available
- ✅ "▶️ Start Detection" button on each card

### 3. Test Realtime Detection

1. Click toggle **"🔴 Realtime Detection"** → ON
2. Click **"▶️ Start Detection"** on a video card
3. Observe:
   - 🔴 **LIVE 30+ FPS** badge appears
   - Bbox overlay vẽ realtime
   - Frame counter updates
   - Object count displays

---

## 📊 Performance Benchmark

### Run Benchmark Script

```bash
cd traffic-server
conda activate LVTN
python benchmark_fps.py
```

### Expected Results (RTX 3050 4GB)

```
============================================================
📊 BENCHMARK SUMMARY
============================================================
Format     FPS        Inference (ms)  Target Met
------------------------------------------------------------
engine     37.0       27.0            ✅
onnx       28.5       35.1            ❌
pt         18.2       54.9            ❌
============================================================

🏆 BEST: ENGINE - 37.0 FPS
✅ TensorRT engine is fastest (as expected)
```

---

## 🎯 Performance Expectations

### RTX 3050 4GB Laptop

| Metric | Target | Expected |
|--------|--------|----------|
| FPS | >30 | **35-40** |
| Inference Time | <35ms | **25-30ms** |
| VRAM Usage | <3.5GB | **2.5GB** |
| Model Format | .engine | **.engine** |

### RTX 3060+ Desktop

| Metric | Target | Expected |
|--------|--------|----------|
| FPS | >30 | **45-60** |
| Inference Time | <25ms | **16-20ms** |
| VRAM Usage | <4GB | **2.5GB** |
| Model Format | .engine | **.engine** |

---

## 🛠️ Troubleshooting

### Issue 1: "Conda environment 'LVTN' not found"

**Solution:**
```bash
# Create environment
conda create -n LVTN python=3.10

# Activate
conda activate LVTN

# Install requirements
cd traffic-server
pip install -r requirements.txt
```

### Issue 2: "Model not found"

**Check models exist:**
```bash
cd traffic-server/models/vehicle/v10m
ls -la
```

**Expected files:**
```
yolo_vehicle_v10m.engine  ← Priority 1 (fastest)
yolo_vehicle_v10m.onnx    ← Priority 2
yolo_vehicle_v10m.pt      ← Priority 3 (slowest)
```

**If .engine missing, convert:**
```bash
cd traffic-server/models
python convert.py
```

### Issue 3: FPS < 30

**Check model format being used:**
```bash
# Look for this in backend logs:
✅ Vehicle model loaded: .../yolo_vehicle_v10m.engine (engine, 42.1MB)
```

**If using .pt or .onnx instead of .engine:**
```bash
# Convert to TensorRT
cd traffic-server/models
python convert.py
```

### Issue 4: CUDA not available

**Check CUDA:**
```bash
python -c "import torch; print(f'CUDA: {torch.cuda.is_available()}, GPU: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else \"None\"}')"
```

**Expected:** `CUDA: True, GPU: NVIDIA GeForce RTX 3050 Laptop GPU`

**If False:**
- Update GPU drivers: https://www.nvidia.com/drivers
- Reinstall PyTorch with CUDA: `pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118`

### Issue 5: WebSocket connection failed

**Check backend running:**
```bash
curl http://localhost:8000/health
```

**Check logs for errors:**
```bash
# In backend terminal, look for:
INFO:     Started server process
INFO:     Uvicorn running on http://0.0.0.0:8000
```

**Check CORS settings:**
```python
# In traffic-server/app/main.py
allow_origins = ["http://localhost:3000", "*"]
```

---

## 📝 Performance Monitoring

### Backend Logs (Real-time)

```bash
# Every second, you'll see:
📊 FPS: 37.0 | Inference: 27.0ms | Objects: 5
📊 FPS: 36.8 | Inference: 27.2ms | Objects: 3
📊 FPS: 37.1 | Inference: 26.9ms | Objects: 7
```

### Frontend Display

- **🔴 LIVE badge**: Shows actual FPS
- **Frame counter**: `Frame 1250 | 5 objects`
- **Inference time**: Shown in WebSocket message (check browser console F12)

---

## 🔥 Performance Tips

### 1. Use TensorRT (.engine)

```bash
# Always use .engine for best performance
# 3-5x faster than .pt
cd traffic-server/models
python convert.py
```

### 2. Close Other GPU Apps

```bash
# Close:
- Games
- Video editing software
- Other ML/AI applications
- Chrome tabs with hardware acceleration
```

### 3. Monitor VRAM

```bash
# Check VRAM usage
nvidia-smi

# Expected: 2.5-3.0 GB used
```

### 4. Optimize Confidence Threshold

```python
# In traffic-server/app/core/performance_config.py

# Lower confidence = more detections = slower
INFERENCE_SETTINGS["conf"] = 0.5  # Default (balanced)

# Higher confidence = fewer detections = faster
INFERENCE_SETTINGS["conf"] = 0.6  # If you want >40 FPS
```

---

## 📂 Project Structure

```
traffic-system/
├── traffic-server/
│   ├── setup_lvtn_env.bat        ← Step 1: Setup
│   ├── run_optimized.bat         ← Step 2: Run backend
│   ├── benchmark_fps.py          ← Benchmark tool
│   ├── app/
│   │   ├── main.py
│   │   ├── core/
│   │   │   └── performance_config.py  ← Performance settings
│   │   └── routers/
│   │       └── realtime_detection.py  ← Optimized WebSocket
│   └── models/
│       └── vehicle/v10m/
│           ├── yolo_vehicle_v10m.engine  ← Use this!
│           ├── yolo_vehicle_v10m.onnx
│           └── yolo_vehicle_v10m.pt
└── src/
    └── components/
        └── DetectionCardRealtime.jsx  ← 30 FPS frontend
```

---

## ✅ Success Checklist

- [ ] Conda environment `LVTN` activated
- [ ] Backend running with no errors
- [ ] Frontend running at http://localhost:3000
- [ ] Health check returns `"models_loaded": true`
- [ ] Backend logs show `✅ Vehicle model loaded: ...engine`
- [ ] Frontend detection page loads
- [ ] Start Detection button works
- [ ] FPS counter shows **30+**
- [ ] Bbox overlay renders smoothly
- [ ] Backend logs show **FPS: 35+ | Inference: ~27ms**

---

## 🎯 Expected Final Result

### Backend Console
```
📊 FPS: 37.0 | Inference: 27.0ms | Objects: 5
📊 FPS: 36.8 | Inference: 27.2ms | Objects: 3
📊 FPS: 37.1 | Inference: 26.9ms | Objects: 7
```

### Frontend Display
```
🔴 LIVE 37 FPS
Frame 1250 | 5 objects

[Bbox overlay vẽ mượt mà với 4 màu:]
🟠 bus (orange)
🔵 car (blue)
🟢 bike (green)
🔴 truck (red)
```

---

## 📚 Documentation

- **Performance Guide**: `PERFORMANCE_OPTIMIZATION.md`
- **Quick Start**: `QUICK_START.md`
- **Model Classes**: `MODEL_CLASSES.md`
- **Full System Docs**: `DETECTION_SYSTEM_README.md`

---

## 🎁 Summary

**3 Steps to >30 FPS:**
1. `setup_lvtn_env.bat` → Activate LVTN
2. `run_optimized.bat` → Start backend (optimized)
3. `npm run dev` → Start frontend

**Verify with:** `python benchmark_fps.py`

**Expected:** **35-40 FPS** với RTX 3050 4GB 🚀

---

**Questions? Check `PERFORMANCE_OPTIMIZATION.md` for detailed troubleshooting!**

