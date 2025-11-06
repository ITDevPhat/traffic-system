# ⚡ Quick Fix Guide - Áp Dụng Ngay

## 🔧 Đã Sửa 3 Lỗi Chính

### 1. ✅ **TensorRT Input Size** (480 → 640)
### 2. ✅ **Invalid BBox Validation** 
### 3. ✅ **Class Names** (motorbike → bike)

---

## 🚀 Áp Dụng Fix (3 Bước)

### Step 1: Restart Backend

```bash
# Stop server (Ctrl+C)
# Then restart:
cd traffic-server
conda activate LVTN
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

**Expected logs:**
```
Loading models\vehicle\11s\yolo_vehicle_11s.engine for TensorRT inference...
[TRT] [I] Loaded engine size: 23 MiB
✅ No shape mismatch error
```

---

### Step 2: Rebuild Frontend (Clear Cache)

```bash
# Stop frontend (Ctrl+C)
# Clear cache and rebuild:
rm -rf .next
npm run dev
```

**Or Windows:**
```bash
# Delete .next folder manually, then:
npm run dev
```

---

### Step 3: Test Detection

1. **Open:** http://localhost:3000/detection
2. **Toggle:** "🔴 Realtime Detection" → ON
3. **Click:** "▶️ Start Detection"

**Expected results:**
- ✅ No TensorRT errors in backend
- ✅ BBox vẽ mượt mà
- ✅ No "Invalid bbox" warnings
- ✅ FPS: 35-40

---

## ✅ Verification Checklist

### Backend Logs (Should See):
```bash
✅ Loading models\vehicle\11s\yolo_vehicle_11s.engine
✅ [TRT] [I] Loaded engine size: 23 MiB
✅ 📊 FPS: 37.0 | Inference: 27.0ms | Objects: 5
✅ ✅ Successfully drew 5 bboxes on frame 121
```

### Backend Logs (Should NOT See):
```bash
❌ [TRT] [E] Parameter check failed (shape mismatch)
❌ ⚠️  Invalid bbox: (x, 1080, x, 1080)
❌ No detections from YOLO
```

### Frontend (Should See):
```
🔴 LIVE 37 FPS
Frame 1250 | 5 objects

[BBox với 4 màu:]
🟠 bus
🔵 car
🟢 bike
🔴 truck
```

---

## 🐛 Nếu Vẫn Lỗi

### Lỗi: TensorRT Shape Mismatch
**Check:**
```bash
# In backend logs, find:
imgsz: int = Query(640, ...)  # Must be 640, not 480
```

**Fix:**
```python
# traffic-server/app/routers/realtime_ws_binary.py line 32
imgsz: int = Query(640, description="YOLO inference size - MUST be 640 for TensorRT models")
```

---

### Lỗi: Invalid BBox
**Check:**
```bash
# Backend logs show:
⚠️  Invalid bbox: (x, 1080, x, 1080)
```

**Already fixed in code, but if still happens:**
```bash
# Check model is loading correctly
ls models/vehicle/11s/*.engine
# Should exist
```

---

### Lỗi: Frontend TypeError
**Fix:**
```bash
# Clear all caches
rm -rf .next
rm -rf node_modules/.cache
npm run dev
```

**Or:**
```bash
# Hard reload browser
Ctrl+Shift+R (Windows)
Cmd+Shift+R (Mac)
```

---

## 📊 Expected Performance

| Metric | Expected Value |
|--------|---------------|
| **FPS** | 35-40 (11s.engine) |
| **Inference** | 22-27ms |
| **VRAM** | 2.2-2.5GB |
| **BBox** | Smooth, no invalid warnings |
| **Classes** | bus, car, bike, truck |
| **TensorRT** | No errors |

---

## 🎯 Quick Test Commands

### Test 1: Check Model
```bash
cd traffic-server/models
ls vehicle/11s/*.engine
# Should show: yolo_vehicle_11s.engine (24 MB)
```

### Test 2: Check Config
```bash
cd traffic-server
python -c "from app.core.config import settings; print(settings.YOLO_VEHICLE_MODEL)"
# Should show path with /11s/ or /v10m/
```

### Test 3: Check TensorRT
```bash
python -c "import torch; print(f'CUDA: {torch.cuda.is_available()}, GPU: {torch.cuda.get_device_name(0)}')"
# Should show: CUDA: True, GPU: NVIDIA GeForce RTX 3050
```

---

## 🔥 Common Issues

### Issue 1: "Module not found"
```bash
cd traffic-server
conda activate LVTN
pip install -r requirements.txt
```

### Issue 2: "Frontend won't start"
```bash
rm -rf .next node_modules
npm install
npm run dev
```

### Issue 3: "Backend 404"
```bash
# Check backend running:
curl http://localhost:8000/health
# Should return: {"status":"healthy"}
```

---

## ✅ Success Indicators

### Backend Console:
```bash
🖥️  Device: cuda:0
✅ CUDA optimizations enabled
📦 Loading model: .../yolo_vehicle_11s.engine
✅ Vehicle model loaded successfully
📊 FPS: 37.0 | Inference: 27.0ms | Objects: 5
✅ Successfully drew 5 bboxes on frame 121
```

### Frontend Browser:
```
🔴 LIVE 37 FPS
Frame 1250 | 5 objects
[Smooth bbox animation]
No console errors
```

---

## 🎁 Summary

**3 Fixes Applied:**
1. ✅ TensorRT input: 640x640 (was 480)
2. ✅ BBox validation: 3-level checks
3. ✅ Class names: bike (was motorbike)

**How to Apply:**
1. Restart backend
2. Rebuild frontend (rm -rf .next)
3. Test detection

**Expected:** 35-40 FPS, smooth bbox, no errors ✅

---

**If still issues, check:** `BUGFIX_SUMMARY.md` for detailed fixes

