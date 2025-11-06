# ⚡ Quick Start - Realtime Detection System

## 🚀 Chạy Ngay (3 Bước)

### Bước 1: Start Backend (FastAPI)

```bash
cd traffic-server
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

**✅ Check backend:**
```bash
curl http://localhost:8000/api/realtime/health
```

**Expected output:**
```json
{
  "status": "ok",
  "models_loaded": true,
  "device": "cuda:0",
  "gpu_available": true
}
```

---

### Bước 2: Start Frontend (Next.js)

```bash
# Từ thư mục root
npm run dev
```

**✅ Check frontend:**
- Truy cập: http://localhost:3000

---

### Bước 3: Sử dụng Realtime Detection

1. **Truy cập Detection Dashboard**
   ```
   http://localhost:3000/detection
   ```

2. **Bật Realtime Mode**
   - Toggle switch: "🔴 Realtime Detection" → ON
   - Sẽ thấy banner: "⚡ Realtime Detection Active"

3. **Start Detection trên Video Card**
   - Click nút **"▶️ Start Detection"** trên card video
   - Quan sát:
     - 🔴 LIVE badge góc trên trái
     - FPS counter hiển thị
     - Bbox overlay vẽ realtime
     - Frame counter + object count

4. **Stop Detection**
   - Click nút **"⏹️ Stop Detection"**
   - Canvas sẽ clear, WebSocket disconnect

---

## 🎨 Visual Guide

### Grid View Layout

```
┌─────────────────────────────────────────────────────┐
│  📹 Detection Dashboard          [Toggle Switches]  │
│                                                      │
│  ┌──────────────────────┐  ┌──────────────────────┐ │
│  │ 🔴 LIVE 15 FPS       │  │ 🔴 LIVE 15 FPS       │ │
│  │ [Video with BBox]    │  │ [Video with BBox]    │ │
│  │                      │  │                      │ │
│  │ ┌──────┐  ┌──────┐  │  │ ┌──────┐  ┌──────┐  │ │
│  │ │ car  │  │ bus  │  │  │ │ car  │  │truck │  │ │
│  │ └──────┘  └──────┘  │  │ └──────┘  └──────┘  │ │
│  │ Frame 102 | 2 objs  │  │ Frame 98 | 2 objs   │ │
│  │                      │  │                      │ │
│  │ [▶️ Start] [📊 Chi tiết] │  │ [⏹️ Stop] [📊 Chi tiết] │ │
│  └──────────────────────┘  └──────────────────────┘ │
│                                                      │
│  ┌──────────────────────┐  ┌──────────────────────┐ │
│  │ [Video 3]            │  │ [Video 4]            │ │
│  └──────────────────────┘  └──────────────────────┘ │
└─────────────────────────────────────────────────────┘
```

---

## 🎯 BBox Color Coding

Model classes: **0=bus, 1=car, 2=bike, 3=truck**

| Class ID | Vehicle Class | Color | Hex Code |
|----------|--------------|-------|----------|
| 0 | 🚌 bus | 🟠 Orange | `#e67e22` |
| 1 | 🚗 car | 🔵 Blue | `#3498db` |
| 2 | 🏍️ bike | 🟢 Green | `#2ecc71` |
| 3 | 🚚 truck | 🔴 Red | `#e74c3c` |

---

## 🔍 Debug Checklist

### Backend không chạy?
```bash
# Check port 8000
netstat -an | grep 8000

# Check logs
cd traffic-server
tail -f app.log
```

### Frontend không connect WebSocket?
```bash
# Check browser console (F12)
# Expected: "✅ WebSocket connected"

# If error: "❌ WebSocket connection failed"
# → Check backend running
# → Check CORS settings
```

### BBox không hiển thị?
```bash
# Check console logs:
# - "🔌 Connecting to WebSocket: ws://localhost:8000/..."
# - Message received: {"type":"detection", ...}

# Debug canvas:
# - Canvas size = Video size?
# - Scale factors correct?
```

---

## 📊 Performance Tips

### 1. **Optimize FPS**
```javascript
// Giảm FPS để giảm lag (trong DetectionCardRealtime.jsx)
const wsUrl = `${WS_URL}/api/realtime/ws/detect/${videoId}?fps=10`; // Thay đổi 15 → 10
```

### 2. **Use TensorRT (.engine)**
```bash
# Convert model to TensorRT (nhanh hơn 3-5x)
cd traffic-server/models
python convert.py
```

### 3. **Reduce VRAM**
```python
# In backend config (traffic-server/app/core/config.py)
INFERENCE_CONFIDENCE_VEHICLE = 0.6  # Tăng threshold → ít bbox hơn
```

---

## 🎁 Demo Data

### Test Videos
Hệ thống tự động load videos từ:
```
traffic-server/videos/
├── video.mp4
├── video2.mp4
├── video3.mp4
└── ...
```

Nếu database rỗng, fallback load từ folder tự động.

---

## 🆘 Troubleshooting Common Issues

### 1. Model Not Found
```bash
# Check models directory
ls -R traffic-server/models/vehicle/v10m/

# Expected:
# yolo_vehicle_v10m.engine
# yolo_vehicle_v10m.onnx
# yolo_vehicle_v10m.pt
```

### 2. CORS Error
```python
# In traffic-server/app/main.py
# Ensure:
allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"]
```

### 3. Canvas Not Syncing
```javascript
// In DetectionCardRealtime.jsx, handleVideoLoaded()
canvasRef.current.width = videoRef.current.videoWidth;
canvasRef.current.height = videoRef.current.videoHeight;
```

---

## 📚 Tài Liệu Đầy Đủ

- **Chi tiết kỹ thuật**: `DETECTION_SYSTEM_README.md`
- **Tóm tắt implementation**: `IMPLEMENTATION_SUMMARY.md`
- **Quick start**: `QUICK_START.md` (file này)

---

## 🎉 Hoàn Thành!

Bây giờ bạn có:
- ✅ Backend WebSocket API
- ✅ Frontend Grid View với Canvas Overlay
- ✅ Model auto-loader (`.engine` > `.onnx` > `.pt`)
- ✅ YOLO + ByteTrack realtime inference
- ✅ Tài liệu đầy đủ

**Enjoy your realtime detection system! 🚀**

---

**Questions?** Xem `DETECTION_SYSTEM_README.md` section 🐛 Troubleshooting

