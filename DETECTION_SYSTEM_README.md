# 🚀 Traffic Detection System - Realtime Multi-Format Model Support

## 📌 Tổng Quan

Hệ thống phát hiện vi phạm giao thông với khả năng:

- ✅ **Auto-load model**: Tự động detect và load `.engine` (TensorRT) > `.onnx` > `.pt`
- ✅ **YOLO + ByteTrack**: Vehicle detection với tracking ổn định
- ✅ **Realtime BBox Overlay**: Canvas vẽ bbox realtime trên video
- ✅ **Grid View Dashboard**: Hiển thị nhiều video detection đồng thời
- ✅ **WebSocket Streaming**: FPS cao, độ trễ thấp
- ✅ **GPU/CPU Compatible**: Tự động fallback CPU nếu không có GPU

---

## 🏗️ Kiến Trúc Hệ Thống

```
┌─────────────────────────────────────────────────────────────┐
│                    FRONTEND (Next.js)                       │
│  ┌────────────────────────────────────────────────────┐    │
│  │  /detection Page                                    │    │
│  │  ├─ Toggle: Realtime / Static mode                 │    │
│  │  └─ DetectionGrid (2 columns)                      │    │
│  │      └─ DetectionCardRealtime × N                  │    │
│  │          ├─ Video element                          │    │
│  │          ├─ Canvas overlay (bbox rendering)        │    │
│  │          ├─ WebSocket connection                   │    │
│  │          └─ Start/Stop detection button            │    │
│  └────────────────────────────────────────────────────┘    │
│                          ↕ WebSocket (ws://)                │
└─────────────────────────────────────────────────────────────┘
                             ↕
┌─────────────────────────────────────────────────────────────┐
│                   BACKEND (FastAPI)                         │
│  ┌────────────────────────────────────────────────────┐    │
│  │  /api/realtime/ws/detect/{video_id}                │    │
│  │  ├─ VideoDetectionStream                           │    │
│  │  │   ├─ Open video with OpenCV                     │    │
│  │  │   ├─ YOLO inference (vehicle detection)         │    │
│  │  │   ├─ ByteTrack tracking                         │    │
│  │  │   └─ Stream bbox JSON via WebSocket             │    │
│  │  └─ ModelLoader (Singleton)                        │    │
│  │      ├─ Auto-detect: .engine > .onnx > .pt         │    │
│  │      ├─ TensorRT optimization (if GPU)             │    │
│  │      └─ Fallback to CPU (if needed)                │    │
│  └────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

---

## 📂 Cấu Trúc Files Đã Tạo/Cập Nhật

### Backend (FastAPI)

```
traffic-server/app/
├── routers/
│   └── realtime_detection.py          ← 🆕 WebSocket API cho realtime detection
├── utils/
│   └── model_loader.py                 ← ✅ Đã có (auto-load .engine/.onnx/.pt)
├── modules/
│   └── yolo.py                         ← ✅ Đã có (YOLO + ByteTrack)
└── main.py                             ← ✏️ Đã cập nhật (register router mới)
```

### Frontend (Next.js)

```
src/
├── app/
│   ├── api/
│   │   └── videos/
│   │       ├── route.ts                ← 🆕 API proxy to backend /api/videos
│   │       ├── [id]/route.ts           ← 🆕 API proxy to backend /api/videos/{id}
│   │       └── from-folder/route.ts    ← 🆕 API fallback load từ folder
│   └── (admin)/
│       └── detection/
│           └── page.jsx                ← ✏️ Đã cập nhật (toggle realtime mode)
└── components/
    ├── DetectionCardRealtime.jsx       ← 🆕 Card với canvas overlay + WebSocket
    ├── DetectionGrid.jsx               ← ✏️ Đã cập nhật (support realtime mode)
    └── DetectionCard.jsx               ← ✅ Giữ nguyên (static mode)
```

---

## 🔧 Cách Sử Dụng

### 1️⃣ **Backend Setup**

```bash
# Di chuyển vào thư mục backend
cd traffic-server

# Cài đặt dependencies (nếu chưa)
pip install -r requirements.txt

# Đảm bảo models đã có trong thư mục models/
# Cấu trúc:
# models/
# ├── vehicle/v10m/
# │   ├── yolo_vehicle_v10m.engine  ← Ưu tiên cao nhất
# │   ├── yolo_vehicle_v10m.onnx
# │   └── yolo_vehicle_v10m.pt
# ├── license_plate/
# ├── ocr/
# └── traffic_light/

# Chạy server
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

**Kiểm tra health:**

```bash
curl http://localhost:8000/api/realtime/health
# Expected output:
# {
#   "status": "ok",
#   "models_loaded": true,
#   "device": "cuda:0",
#   "gpu_available": true
# }
```

### 2️⃣ **Frontend Setup**

```bash
# Di chuyển vào thư mục root
cd traffic-system

# Cài đặt dependencies (nếu chưa)
npm install

# Chạy dev server
npm run dev
```

### 3️⃣ **Sử Dụng Realtime Detection**

1. **Truy cập**: http://localhost:3000/detection
2. **Bật Realtime Mode**: Toggle switch "🔴 Realtime Detection"
3. **Start Detection**: Click nút "▶️ Start Detection" trên card video
4. **Quan sát**:
   - Bbox overlay vẽ realtime trên video
   - FPS counter hiển thị góc trên trái
   - Frame number + object count hiển thị góc dưới trái
   - Màu sắc khác nhau theo class:
     - 🟠 **bus** (class 0): Orange
     - 🔵 **car** (class 1): Blue
     - 🟢 **bike** (class 2): Green
     - 🔴 **truck** (class 3): Red

---

## ⚙️ Model Loading Logic

### Thứ tự ưu tiên:

1. **`.engine`** (TensorRT) - Nhanh nhất, GPU only
2. **`.onnx`** (ONNX Runtime) - Tương thích GPU/CPU
3. **`.pt`** (PyTorch) - Fallback, chậm nhất

### Code Example (Backend):

```python
from app.utils.model_loader import load_yolo_model, get_model_info

# Auto-detect và load model
model_info = get_model_info("models/vehicle/v10m/yolo_vehicle_v10m")
# → Sẽ tự tìm: yolo_vehicle_v10m.engine > .onnx > .pt

model = load_yolo_model(
    model_info["path"],
    device="cuda:0",  # hoặc "cpu"
    imgsz=640,
    half=True,  # FP16 cho GPU (tiết kiệm VRAM)
    verbose=False
)
```

### Log Output:

```
📦 Loading model: models/vehicle/v10m/yolo_vehicle_v10m.engine (type: engine)
🚀 Loading TensorRT engine: models/vehicle/v10m/yolo_vehicle_v10m.engine
✅ TensorRT model loaded successfully (device will be set in predict())
```

---

## 🌐 WebSocket API

### Endpoint:

```
ws://localhost:8000/api/realtime/ws/detect/{video_id}?fps=15
```

### Parameters:

- `video_id`: ID của video trong database
- `fps`: Target FPS cho streaming (default: 15, max: 60)

### Message Format:

**Server → Client:**

```json
{
  "type": "detection",
  "frame": 102,
  "total_frames": 5000,
  "fps": 15.0,
  "objects": [
    {
      "label": "car",
      "conf": 0.92,
      "bbox": [120, 340, 580, 720],
      "track_id": 5
    },
    {
      "label": "bus",
      "conf": 0.83,
      "bbox": [800, 200, 1400, 900],
      "track_id": 12
    }
  ],
  "video_size": [1920, 1080]
}
```

**Error Message:**

```json
{
  "type": "error",
  "message": "Video file not found: /path/to/video.mp4"
}
```

---

## 🎨 Frontend Implementation

### DetectionCardRealtime Component

**Key Features:**

1. **Canvas Overlay**: Vẽ bbox lên video realtime
2. **WebSocket Client**: Kết nối và nhận detection data
3. **Auto Scaling**: Bbox tự động scale theo kích thước video
4. **Color Coding**: Mỗi class có màu riêng
5. **FPS Counter**: Hiển thị FPS realtime
6. **Lazy Loading**: Chỉ load WebSocket khi card visible

**Code Snippet:**

```javascript
const drawDetections = (objects, videoSize) => {
  const canvas = canvasRef.current;
  const ctx = canvas.getContext('2d');
  
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  
  const scaleX = canvas.width / videoSize[0];
  const scaleY = canvas.height / videoSize[1];
  
  objects.forEach((obj) => {
    const [x1, y1, x2, y2] = obj.bbox;
    const color = CLASS_COLORS[obj.label.toLowerCase()] || '#95a5a6';
    
    // Draw bbox
    ctx.strokeStyle = color;
    ctx.lineWidth = 3;
    ctx.strokeRect(x1 * scaleX, y1 * scaleY, (x2-x1) * scaleX, (y2-y1) * scaleY);
    
    // Draw label
    ctx.fillStyle = color;
    ctx.fillRect(x1 * scaleX, y1 * scaleY - 24, labelWidth, 24);
    ctx.fillStyle = '#fff';
    ctx.fillText(`${obj.label} ${(obj.conf * 100).toFixed(0)}%`, x1 * scaleX + 4, y1 * scaleY - 8);
  });
};
```

---

## 🚀 Performance Optimization

### Backend:

- ✅ **TensorRT FP16**: Giảm 50% VRAM, tăng 2x tốc độ
- ✅ **ByteTrack Persistence**: Tracking ổn định giữa frames
- ✅ **Model Singleton**: Load model 1 lần duy nhất
- ✅ **CUDA Optimizations**: `cudnn.benchmark=True`, TF32 enabled
- ✅ **Frame Delay Control**: FPS configurable qua WebSocket query param

### Frontend:

- ✅ **Lazy Loading**: WebSocket chỉ connect khi card visible
- ✅ **Canvas 2D**: Hardware accelerated
- ✅ **IntersectionObserver**: Auto disconnect khi scroll khỏi viewport
- ✅ **Debounced Drawing**: Vẽ bbox tối ưu theo FPS

---

## 📊 Testing Checklist

### ✅ Backend Tests:

- [x] Model auto-load: `.engine` > `.onnx` > `.pt`
- [x] WebSocket connection successful
- [x] YOLO inference with ByteTrack
- [x] JSON streaming stable at 15 FPS
- [x] GPU/CPU fallback works

### ✅ Frontend Tests:

- [x] Grid view hiển thị 2 cột
- [x] Video autoplay khi visible
- [x] Canvas overlay sync với video size
- [x] Bbox vẽ đúng tỷ lệ (scaled)
- [x] Color coding theo class
- [x] FPS counter hiển thị chính xác
- [x] Start/Stop detection hoạt động
- [x] WebSocket auto disconnect khi card invisible

### ✅ Integration Tests:

- [x] API `/api/videos` fetch data từ backend
- [x] WebSocket `/api/realtime/ws/detect/{id}` stream bbox
- [x] Toggle realtime/static mode
- [x] Multiple videos detect đồng thời

---

## 🐛 Troubleshooting

### 1. **WebSocket Connection Failed**

**Lỗi:** `Failed to connect WebSocket`

**Nguyên nhân:**
- Backend không chạy
- Firewall block port 8000
- CORS configuration

**Giải pháp:**
```bash
# Check backend running
curl http://localhost:8000/health

# Check CORS settings in traffic-server/app/main.py
# Đảm bảo allow_origins bao gồm frontend URL
```

### 2. **Model Not Found**

**Lỗi:** `❌ Vehicle model not found`

**Nguyên nhân:**
- Model files không có trong thư mục `models/`

**Giải pháp:**
```bash
# Check models directory
ls -R traffic-server/models/

# Convert .pt to .engine (nếu cần)
cd traffic-server/models
python convert.py
```

### 3. **BBox Không Khớp Video**

**Lỗi:** Bbox vẽ sai vị trí

**Nguyên nhân:**
- Canvas size không sync với video size
- Scale factor sai

**Giải pháp:**
```javascript
// Đảm bảo canvas size = video size
canvasRef.current.width = videoRef.current.videoWidth;
canvasRef.current.height = videoRef.current.videoHeight;

// Scale bbox chính xác
const scaleX = canvas.width / data.video_size[0];
const scaleY = canvas.height / data.video_size[1];
```

### 4. **Low FPS**

**Lỗi:** Detection chậm (<10 FPS)

**Nguyên nhân:**
- Chạy trên CPU
- Model `.pt` chưa convert sang `.engine`
- VRAM không đủ

**Giải pháp:**
```bash
# Check GPU available
python -c "import torch; print(torch.cuda.is_available())"

# Convert to TensorRT (nhanh hơn 3-5x)
cd traffic-server/models
python convert.py

# Reduce FPS in WebSocket
# ws://localhost:8000/api/realtime/ws/detect/1?fps=10
```

---

## 📈 Future Enhancements

- [ ] **Multi-camera grid**: Hiển thị 4-6 cameras cùng lúc
- [ ] **Recording**: Lưu video với bbox overlay
- [ ] **Alert System**: Thông báo realtime khi phát hiện vi phạm
- [ ] **Statistics Dashboard**: Biểu đồ realtime (violations/hour)
- [ ] **Mobile Support**: Responsive grid layout
- [ ] **Cloud Deployment**: Docker + Kubernetes setup

---

## 🎯 Kết Luận

Hệ thống đã được nâng cấp hoàn toàn để hỗ trợ:

✅ **Multi-format model loading** (`.engine` / `.onnx` / `.pt`)  
✅ **Realtime detection grid** với WebSocket streaming  
✅ **Canvas overlay** vẽ bbox mượt mà  
✅ **YOLO + ByteTrack** inference ổn định  
✅ **GPU optimization** với TensorRT FP16  

**Tất cả hoạt động ổn định, không phá pipeline cũ!** 🚀

---

## 📝 Credits

- **YOLO**: Ultralytics (YOLOv8/v10/v11)
- **ByteTrack**: ByteDance Research
- **TensorRT**: NVIDIA
- **FastAPI**: Sebastián Ramírez
- **Next.js**: Vercel

---

**Developed by Traffic System Team** 🚦

