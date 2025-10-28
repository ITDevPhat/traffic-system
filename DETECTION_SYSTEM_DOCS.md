# 🚗 Traffic Detection System - Technical Documentation

## 📋 Tổng quan hệ thống

Hệ thống **Traffic Detection** sử dụng **YOLO + ByteTrack + OCR** để nhận diện và theo dõi phương tiện giao thông realtime với GPU acceleration.

### 🏗️ Kiến trúc hệ thống

```
Frontend (Next.js) ←→ WebSocket ←→ Backend (FastAPI) ←→ YOLO Models (GPU)
     ↓                    ↓              ↓                    ↓
  Canvas Overlay    Real-time Data   Inference Engine    CUDA Processing
  Video Player      Bbox + FPS       ByteTrack ID        FP16 Optimization
```

---

## 🧠 YOLO Models & ByteTrack

### 📦 Models được sử dụng

| Model | File | Mục đích | Input Size | Device |
|-------|------|----------|------------|---------|
| **Vehicle** | `yolo_vehicle_v10m.pt` | Nhận diện xe (bus, car, motorbike, truck) | 384x384 | CUDA |
| **Plate** | `yolo_plate_v10n.pt` | Nhận diện biển số xe | 384x384 | CUDA |
| **OCR** | `yolo_ocr_chars_v8n.pt` | Đọc ký tự biển số | 384x384 | CUDA |
| **Traffic Light** | `yolo_trafficlight_v10n.pt` | Nhận diện đèn giao thông | 384x384 | CUDA |

### 🎯 Class Mapping (Vehicle Model)

```python
# Backend override trong RealtimeDetector.__init__()
self.m_vehicle.names = {
    0: "bus",      # Xe buýt
    1: "car",      # Ô tô
    2: "motorbike", # Xe máy
    3: "truck"     # Xe tải
}
```

### 🔄 ByteTrack Integration

**ByteTrack** được tích hợp sẵn trong YOLO models để tracking objects:

```python
# Trong YOLO inference
results = model.track(
    frame, 
    persist=True,           # ByteTrack persistence
    conf=RUNTIME_CFG["conf_vehicle"],
    imgsz=RUNTIME_CFG["imgsz"],
    half=RUNTIME_CFG["half"]  # FP16 optimization
)
```

**Track ID** được extract từ `box.id[0]` và gửi qua WebSocket.

---

## ⚙️ Runtime Configuration

### 🚀 Performance Settings

```python
RUNTIME_CFG = {
    "conf_vehicle": 0.40,    # Confidence threshold
    "imgsz": 384,           # Input size (optimized for speed)
    "frame_skip": 1,        # Process every frame
    "max_det": 50,          # Max detections per frame
    "half": True,           # FP16 inference (2x faster)
    "modules": {
        "vehicle": True,     # Vehicle detection
        "plate": False,      # Plate detection (disabled for speed)
        "ocr": False,        # OCR processing (disabled for speed)
        "bbox": True,        # Bounding box display
        "tracking": True     # ByteTrack ID
    }
}
```

### 🎛️ GPU Optimization

```python
# CUDA optimizations
torch.backends.cudnn.benchmark = True
torch.backends.cuda.matmul.allow_tf32 = True
torch.backends.cudnn.allow_tf32 = True

# FP16 inference
with torch.autocast(device_type='cuda', dtype=torch.float16):
    results = model.track(frame, ...)
```

---

## 🔄 Bbox Scaling Pipeline

### ❌ Vấn đề hiện tại

**Bbox "nhảy lung tung"** do mismatch giữa:
- **Backend**: YOLO inference ở `imgsz=384` 
- **Frontend**: Video display ở resolution khác (1280x720, 1920x1080, etc.)

### 🔧 Backend Scaling (realtime_ws.py)

```python
# Scale từ YOLO inference size → original frame size
img_h, img_w = frame.shape[:2]  # Original frame dimensions
scale_x = img_w / float(RUNTIME_CFG["imgsz"])  # 1280/384 = 3.33
scale_y = img_h / float(RUNTIME_CFG["imgsz"])  # 720/384 = 1.875

# Scale bbox coordinates
bx1, by1, bx2, by2 = box.xyxy[0].tolist()  # YOLO coordinates (0-384)
x1 = int(bx1 * scale_x)  # Scale to original frame
y1 = int(by1 * scale_y)
x2 = int(bx2 * scale_x)
y2 = int(by2 * scale_y)
```

### 🎨 Frontend Scaling (page.jsx)

```javascript
// Scale từ video dimensions → canvas dimensions
const scaleX = canvas.width / (video.videoWidth || 1);
const scaleY = canvas.height / (video.videoHeight || 1);

// Draw bbox với scale
ctx.strokeRect(
  x1 * scaleX, y1 * scaleY, 
  (x2 - x1) * scaleX, (y2 - y1) * scaleY
);
```

### 🐛 Root Cause Analysis

1. **Backend scaling**: ✅ Đúng - scale từ 384 → original frame size
2. **Frontend scaling**: ❌ **Có thể sai** - scale từ video → canvas
3. **Canvas sizing**: ❌ **Có thể sai** - canvas size không match video

---

## 🔍 Debugging Bbox Issues

### 📊 Debug Information

**Backend logs:**
```
🚗 Frame 1234: Detected 3 vehicles
📦 Bbox sent: [{"x1": 100, "y1": 50, "x2": 200, "y2": 150, "track_id": 5}]
```

**Frontend logs:**
```javascript
console.log('Video dimensions:', video.videoWidth, 'x', video.videoHeight);
console.log('Canvas dimensions:', canvas.width, 'x', canvas.height);
console.log('Scale factors:', scaleX, scaleY);
console.log('Bbox received:', box);
```

### 🛠️ Fixes cần thực hiện

1. **Canvas sizing fix:**
```javascript
// Đảm bảo canvas size = video size
const targetW = Math.max(1, Math.floor(video.videoWidth || 1280));
const targetH = Math.max(1, Math.floor(video.videoHeight || 720));
if (canvas.width !== targetW || canvas.height !== targetH) {
  canvas.width = targetW;
  canvas.height = targetH;
}
```

2. **Scale factor validation:**
```javascript
// Validate scale factors
if (scaleX <= 0 || scaleY <= 0 || !isFinite(scaleX) || !isFinite(scaleY)) {
  console.error('Invalid scale factors:', scaleX, scaleY);
  return;
}
```

3. **Bbox coordinate validation:**
```javascript
// Validate bbox coordinates
if (x1 < 0 || y1 < 0 || x2 <= x1 || y2 <= y1) {
  console.warn('Invalid bbox:', {x1, y1, x2, y2});
  return;
}
```

---

## 🌐 WebSocket Protocol

### 📡 Message Format

**Frame data:**
```json
{
  "type": "frame",
  "frame_idx": 1234,
  "fps": 32.5,
  "bbox": [
    {
      "x1": 100, "y1": 50, "x2": 200, "y2": 150,
      "cls": "car",
      "conf": 0.85,
      "track_id": 5
    }
  ]
}
```

**Error message:**
```json
{
  "type": "error",
  "message": "GPU not detected: CUDA required."
}
```

### 🔄 Message Flow

1. **Backend**: YOLO inference → scale bbox → send via WebSocket
2. **Frontend**: receive → validate → draw on canvas
3. **Rate**: 12 Hz (configurable via `WS_RATE`)

---

## 🚀 Performance Metrics

### 📈 Target Performance

| Metric | Target | Current |
|--------|--------|---------|
| **Inference FPS** | 30+ | ~32 FPS |
| **WebSocket Rate** | 12 Hz | 12 Hz |
| **Latency** | <100ms | ~80ms |
| **GPU Memory** | <4GB | ~3.2GB |
| **CPU Usage** | <50% | ~35% |

### 🎯 Optimization Flags

```python
# Speed optimizations
"imgsz": 384,        # Small input size
"half": True,        # FP16 inference
"max_det": 50,       # Limit detections
"frame_skip": 1,     # Process every frame

# Disabled for speed
"plate": False,      # Skip plate detection
"ocr": False,        # Skip OCR
"roi": False,        # Skip ROI check
```

---

## 🔧 Troubleshooting

### ❌ Common Issues

1. **"GPU not detected"**
   - Check CUDA installation: `torch.cuda.is_available()`
   - Verify GPU drivers
   - Check PyTorch CUDA version

2. **"Bbox jumping around"**
   - Check canvas sizing logic
   - Validate scale factors
   - Debug coordinate transformation

3. **"Low FPS"**
   - Reduce `imgsz` (384 → 320)
   - Enable `half=True` (FP16)
   - Disable unused modules

4. **"WebSocket connection failed"**
   - Check CORS settings
   - Verify backend running on port 8000
   - Check firewall/network

### 🛠️ Debug Commands

```bash
# Check CUDA
python -c "import torch; print('CUDA:', torch.cuda.is_available())"

# Check models
ls -la traffic-server/models/

# Test WebSocket
curl -i -N -H "Connection: Upgrade" -H "Upgrade: websocket" \
  "http://localhost:8000/api/detection/realtime?source=0"
```

---

## 📝 API Endpoints

### 🔌 REST API

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/detection/models/load` | POST | Load models to GPU |
| `/api/detection/health` | GET | Health check |
| `/api/detection/gpu` | GET | GPU status |
| `/api/detection/upload-temp-video` | POST | Upload video file |
| `/api/detection/settings` | GET/POST | Runtime settings |

### 🌐 WebSocket

| Endpoint | Purpose |
|----------|---------|
| `/api/detection/realtime?source=0` | Webcam detection |
| `/api/detection/realtime?source=/path/to/video` | Video file detection |

---

## 🎯 Next Steps

### 🔧 Immediate Fixes

1. **Fix bbox scaling** - debug canvas sizing
2. **Add coordinate validation** - prevent invalid bbox
3. **Improve error handling** - better user feedback
4. **Add performance monitoring** - FPS tracking

### 🚀 Future Enhancements

1. **Multi-camera support** - multiple video sources
2. **ROI-based detection** - zone-specific analysis
3. **Violation detection** - traffic rule enforcement
4. **Database integration** - store detection results
5. **Real-time alerts** - notification system

---

*Tài liệu này được tạo tự động từ codebase. Cập nhật lần cuối: 2025-01-22*
