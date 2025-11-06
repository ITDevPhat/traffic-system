# 🚦 Traffic Detection System - Hướng Dẫn Hoàn Chỉnh

## 📋 Mục Lục

1. [Tổng Quan Hệ Thống](#tổng-quan-hệ-thống)
2. [Cài Đặt & Setup](#cài-đặt--setup)
3. [Kiến Trúc Hệ Thống](#kiến-trúc-hệ-thống)
4. [Luồng Xử Lý](#luồng-xử-lý)
5. [Model YOLO & Định Dạng](#model-yolo--định-dạng)
6. [Confidence Threshold](#confidence-threshold)
7. [Cấu Hình & Tối Ưu](#cấu-hình--tối-ưu)
8. [Frontend & Backend](#frontend--backend)
9. [Troubleshooting](#troubleshooting)

---

## 🎯 Tổng Quan Hệ Thống

### Hệ Thống Phát Hiện Vi Phạm Giao Thông

**Mục đích:** Phát hiện và theo dõi phương tiện giao thông, nhận dạng biển số, phát hiện vi phạm (đèn đỏ, tốc độ, v.v.)

**Công nghệ:**
- **Frontend:** Next.js (React) - Giao diện quản lý
- **Backend:** FastAPI (Python) - Xử lý AI/ML
- **Database:** PostgreSQL - Lưu trữ dữ liệu
- **AI Models:** YOLOv10/v11 - Object Detection
- **Tracking:** ByteTrack - Multi-object Tracking
- **OCR:** YOLO OCR - Nhận dạng biển số

### Tính Năng Chính

✅ **Real-time Detection:** Phát hiện phương tiện real-time qua WebSocket (30+ FPS)  
✅ **Multi-object Tracking:** Theo dõi nhiều phương tiện với ByteTrack  
✅ **License Plate Recognition:** Nhận dạng biển số xe Việt Nam  
✅ **Violation Detection:** Phát hiện vi phạm (đèn đỏ, tốc độ, ROI)  
✅ **Smooth Tracking:** Bbox smoothing để giảm jitter  
✅ **In-memory Processing:** Không lưu dữ liệu trừ khi vi phạm  

---

## 🛠️ Cài Đặt & Setup

### 1. Yêu Cầu Hệ Thống

#### Phần Cứng
- **GPU:** NVIDIA GPU với CUDA support (khuyến nghị RTX 3050 trở lên)
- **VRAM:** Tối thiểu 4GB (khuyến nghị 6GB+)
- **RAM:** 8GB+ (khuyến nghị 16GB)
- **CPU:** Intel i5 / AMD Ryzen 5 trở lên

#### Phần Mềm
- **OS:** Windows 10/11, Linux, macOS
- **Python:** 3.8 - 3.11
- **Node.js:** 16.x - 18.x
- **Anaconda/Miniconda:** Để quản lý môi trường Python
- **PostgreSQL:** 12.x - 15.x
- **CUDA:** 11.8+ (nếu dùng GPU)

### 2. Setup Anaconda Environment

#### Bước 1: Tạo Environment

```bash
# Mở Anaconda Prompt hoặc Terminal
conda create -n LVTN python=3.10
conda activate LVTN
```

#### Bước 2: Cài Đặt CUDA (Nếu dùng GPU)

```bash
# Check CUDA version
nvidia-smi

# Cài PyTorch với CUDA support
# Vào https://pytorch.org/get-started/locally/
# Chọn: CUDA 11.8, Windows, pip

pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
```

#### Bước 3: Cài Đặt Dependencies

```bash
# Di chuyển vào thư mục backend
cd traffic-server

# Cài đặt dependencies
pip install -r requirements.txt
```

#### Bước 4: Verify GPU

```bash
# Test GPU
python -c "import torch; print(f'CUDA available: {torch.cuda.is_available()}'); print(f'GPU: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else \"N/A\"}')"
```

**Expected output:**
```
CUDA available: True
GPU: NVIDIA GeForce RTX 3050 Laptop GPU
```

### 3. Setup Database (PostgreSQL)

#### Bước 1: Cài PostgreSQL

- Download từ: https://www.postgresql.org/download/
- Cài đặt với default settings
- Ghi nhớ password cho user `postgres`

#### Bước 2: Tạo Database

```sql
-- Mở pgAdmin hoặc psql
CREATE DATABASE traffic_db;
CREATE USER traffic_user WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE traffic_db TO traffic_user;
```

#### Bước 3: Cấu Hình Environment

Tạo file `.env` trong `traffic-server/`:

```env
# Database
DATABASE_URL=postgresql://traffic_user:your_password@localhost:5432/traffic_db

# Security
SECRET_KEY=your-secret-key-here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Paths
STATIC_DIR=static
VIDEOS_DIR=videos
EVIDENCE_DIR=evidence

# Device
DEVICE=cuda:0  # hoặc cpu nếu không có GPU
```

### 4. Setup Frontend (Next.js)

```bash
# Từ thư mục root
npm install
# hoặc
yarn install
```

### 5. Chạy Hệ Thống

#### Terminal 1: Backend (FastAPI)

```bash
cd traffic-server
conda activate LVTN
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

#### Terminal 2: Frontend (Next.js)

```bash
# Từ thư mục root
npm run dev
# hoặc
yarn dev
```

#### Terminal 3: Database (Nếu chưa chạy)

```bash
# PostgreSQL service nên tự động start
# Nếu không, start manually:
# Windows: Services → PostgreSQL
# Linux: sudo systemctl start postgresql
```

**Access:**
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

---

## 🏗️ Kiến Trúc Hệ Thống

### Sơ Đồ Tổng Quan

```
┌─────────────────────────────────────────────────────────────┐
│                    FRONTEND (Next.js)                        │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │   Dashboard  │  │  Detection   │  │   Admin      │      │
│  │   Component  │  │   Component  │  │   Panel      │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│         │                  │                  │              │
│         └──────────────────┼──────────────────┘              │
│                            │                                  │
│                    WebSocket / REST API                       │
└────────────────────────────┼──────────────────────────────────┘
                             │
┌────────────────────────────┼──────────────────────────────────┐
│                    BACKEND (FastAPI)                          │
│  ┌──────────────────────────────────────────────────────┐    │
│  │         Real-time Binary Stream Service              │    │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐          │    │
│  │  │ Capture  │→ │  Detect  │→ │  Track   │          │    │
│  │  │  Thread  │  │  Thread  │  │  Thread  │          │    │
│  │  └──────────┘  └──────────┘  └──────────┘          │    │
│  │         │            │            │                  │    │
│  │         └────────────┼────────────┘                  │    │
│  │                      ↓                                │    │
│  │              ┌──────────────┐                        │    │
│  │              │  OCR Service │                        │    │
│  │              │  (Plate)     │                        │    │
│  │              └──────────────┘                        │    │
│  └──────────────────────────────────────────────────────┘    │
│                            │                                  │
│  ┌──────────────────────────────────────────────────────┐    │
│  │              YOLO Models (GPU)                       │    │
│  │  • Vehicle Detection (v10m/v11s)                    │    │
│  │  • License Plate Detection                          │    │
│  │  • OCR (Character Recognition)                      │    │
│  │  • Traffic Light Detection                          │    │
│  └──────────────────────────────────────────────────────┘    │
│                            │                                  │
│  ┌──────────────────────────────────────────────────────┐    │
│  │              ByteTrack Tracker                       │    │
│  │  • Multi-object Tracking                            │    │
│  │  • Track ID Assignment                              │    │
│  │  • Track Smoothing                                  │    │
│  └──────────────────────────────────────────────────────┘    │
│                            │                                  │
│                    Violation Detector                         │
│                            │                                  │
└────────────────────────────┼──────────────────────────────────┘
                             │
┌────────────────────────────┼──────────────────────────────────┐
│                    DATABASE (PostgreSQL)                      │
│  • video_jobs    - Video processing jobs                     │
│  • vehicles      - Detected vehicles                         │
│  • violations    - Violation records                         │
│  • rois          - Region of Interest                        │
│  • users         - User accounts                             │
└───────────────────────────────────────────────────────────────┘
```

### Component Architecture

#### Backend Components

1. **`realtime_binary_stream.py`** - Main streaming service
   - Multi-threaded pipeline (Capture → Detect → Track → Encode)
   - WebSocket streaming
   - ByteTrack integration
   - OCR integration

2. **`plate_ocr_service.py`** - OCR service
   - License plate detection
   - Character recognition
   - Debounce logic
   - In-memory cache

3. **`violation_detector.py`** - Violation detection
   - Rules engine
   - Evidence storage
   - Only save when violation detected

4. **`performance_config.py`** - Configuration
   - CUDA optimizations
   - Model settings
   - Tracking settings
   - OCR settings

#### Frontend Components

1. **`DetectionCardRealtime.jsx`** - Real-time detection card
   - WebSocket connection
   - Video player
   - Canvas overlay for bboxes
   - Plate text display

2. **`DetectionGrid.jsx`** - Grid layout
   - Multiple video streams
   - Responsive layout

---

## 🔄 Luồng Xử Lý

### 1. Real-time Detection Pipeline

```
┌─────────────────────────────────────────────────────────────┐
│                    VIDEO INPUT                               │
│  (File / Webcam / RTSP Stream)                              │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ↓
┌─────────────────────────────────────────────────────────────┐
│              THREAD 1: CAPTURE                              │
│  • Read frames from video source                            │
│  • Pace to target FPS (30 FPS)                              │
│  • Put frames into queue (q_cap)                            │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ↓
┌─────────────────────────────────────────────────────────────┐
│              THREAD 2: DETECT & TRACK                       │
│                                                              │
│  ┌────────────────────────────────────────────────────┐    │
│  │  Step 1: YOLO Detection (every N frames)          │    │
│  │  • Detect vehicles (car, bus, truck, bike)        │    │
│  │  • Output: bbox, confidence, class                │    │
│  └──────────────────────┬─────────────────────────────┘    │
│                         │                                    │
│                         ↓                                    │
│  ┌────────────────────────────────────────────────────┐    │
│  │  Step 2: ByteTrack Tracking (every frame)         │    │
│  │  • Assign track_id to each detection              │    │
│  │  • Maintain track history                         │    │
│  │  • Predict positions between detections           │    │
│  └──────────────────────┬─────────────────────────────┘    │
│                         │                                    │
│                         ↓                                    │
│  ┌────────────────────────────────────────────────────┐    │
│  │  Step 3: Track Smoothing                          │    │
│  │  • Low-pass filter for position                   │    │
│  │  • Low-pass filter for size                       │    │
│  │  • Reduce jitter                                  │    │
│  └──────────────────────┬─────────────────────────────┘    │
│                         │                                    │
│                         ↓                                    │
│  ┌────────────────────────────────────────────────────┐    │
│  │  Step 4: OCR (with debounce)                      │    │
│  │  • Crop vehicle bbox                              │    │
│  │  • Detect license plate                           │    │
│  │  • Recognize characters                           │    │
│  │  • Cache result (1s debounce)                     │    │
│  └──────────────────────┬─────────────────────────────┘    │
│                         │                                    │
│                         ↓                                    │
│  ┌────────────────────────────────────────────────────┐    │
│  │  Step 5: Violation Check                          │    │
│  │  • Check rules (red light, speed, ROI)            │    │
│  │  • Save evidence if violation                     │    │
│  └──────────────────────┬─────────────────────────────┘    │
│                         │                                    │
└─────────────────────────┼────────────────────────────────────┘
                          │
                          ↓
┌─────────────────────────────────────────────────────────────┐
│              THREAD 3: ANNOTATE & ENCODE                    │
│  • Draw bboxes on frame                                     │
│  • Draw plate text                                          │
│  • Draw ROI overlays                                        │
│  • Encode to JPEG (TurboJPEG)                               │
│  • Put into queue (q_enc)                                   │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ↓
┌─────────────────────────────────────────────────────────────┐
│              MAIN THREAD: WEBSOCKET SEND                    │
│  • Get encoded frame from queue                             │
│  • Build metadata (bbox, track_id, plate, etc.)            │
│  • Send via WebSocket to frontend                           │
│  • Maintain target FPS (30 FPS)                             │
└─────────────────────────────────────────────────────────────┘
```

### 2. Data Flow

```
Frame → YOLO → Detections → ByteTrack → Track IDs
                                    ↓
                            Track State (in-memory)
                                    ↓
                            OCR Service (debounce)
                                    ↓
                            Plate Text (cached)
                                    ↓
                            Violation Check
                                    ↓
                    ┌───────────────┴───────────────┐
                    │                               │
            No Violation                    Violation Detected
                    │                               │
                    │                       Save Evidence
                    │                       Save to DB
                    │
            WebSocket Stream
            (bbox + plate text)
                    │
                    ↓
            Frontend Display
```

### 3. Track State Management

```
┌─────────────────────────────────────────────────────────────┐
│                    TRACK STATE (In-Memory)                  │
│                                                              │
│  track_id → {                                                │
│    "cx": float,          # Center X (smoothed)              │
│    "cy": float,          # Center Y (smoothed)              │
│    "w": float,           # Width (smoothed)                 │
│    "h": float,           # Height (smoothed)                │
│    "vx": float,          # Velocity X                       │
│    "vy": float,          # Velocity Y                       │
│    "plate": str,         # Plate text (from OCR)            │
│    "plate_conf": float,  # Plate confidence                 │
│    "last_seen_time": float  # Timestamp                     │
│  }                                                           │
│                                                              │
│  • Updated every detection frame                            │
│  • Cleaned up after 0.5s inactivity                        │
│  • Used for prediction between keyframes                    │
└─────────────────────────────────────────────────────────────┘
```

---

## 🤖 Model YOLO & Định Dạng

### 1. Các Loại Model

#### A. PyTorch (.pt)
- **Định dạng:** Native PyTorch model
- **Ưu điểm:** Dễ sử dụng, flexible
- **Nhược điểm:** Chậm nhất (baseline)
- **Performance:** ~20-25 FPS (RTX 3050)
- **Kích thước:** Lớn nhất (66MB cho vehicle model)

#### B. ONNX (.onnx)
- **Định dạng:** Open Neural Network Exchange
- **Ưu điểm:** Nhanh hơn .pt, cross-platform
- **Nhược điểm:** Cần ONNX Runtime
- **Performance:** ~25-30 FPS (RTX 3050)
- **Kích thước:** Trung bình (62MB cho vehicle model)

#### C. TensorRT (.engine)
- **Định dạng:** NVIDIA TensorRT optimized
- **Ưu điểm:** Nhanh nhất (3-5x so với .pt)
- **Nhược điểm:** Chỉ chạy trên NVIDIA GPU, cần build
- **Performance:** ~30-35 FPS (RTX 3050)
- **Kích thước:** Nhỏ nhất (36MB cho vehicle model)

### 2. Model Priority (Auto-detect)

Hệ thống tự động chọn model theo thứ tự ưu tiên:

```
1. .engine (TensorRT) → Nhanh nhất
2. .onnx (ONNX Runtime) → Nhanh
3. .pt (PyTorch) → Baseline
```

**Code logic:**
```python
# traffic-server/app/utils/model_loader.py
def get_model_info(model_path):
    # Check .engine first
    if Path(model_path.replace('.pt', '.engine')).exists():
        return {"type": "engine", "path": ...}
    # Check .onnx second
    elif Path(model_path.replace('.pt', '.onnx')).exists():
        return {"type": "onnx", "path": ...}
    # Fallback to .pt
    else:
        return {"type": "pt", "path": ...}
```

### 3. Model Structure

```
traffic-server/models/
├── vehicle/                    # Vehicle Detection
│   ├── v10m/                  # YOLOv10 Medium (DEFAULT)
│   │   ├── yolo_vehicle_v10m.engine
│   │   ├── yolo_vehicle_v10m.onnx
│   │   └── yolo_vehicle_v10m.pt
│   └── 11s/                   # YOLOv11 Small (Faster)
│       ├── yolo_vehicle_11s.engine
│       ├── yolo_vehicle_11s.onnx
│       └── yolo_vehicle_11s.pt
│
├── license_plate/              # Plate Detection
│   ├── yolo_plate_v10n.engine
│   ├── yolo_plate_v10n.onnx
│   └── yolo_plate_v10n.pt
│
├── ocr/                        # Character Recognition
│   ├── yolo_ocr_chars_v8n.engine
│   ├── yolo_ocr_chars_v8n.onnx
│   └── yolo_ocr_chars_v8n.pt
│
└── traffic_light/              # Traffic Light Detection
    ├── yolo_trafficlight_v10n.engine
    ├── yolo_trafficlight_v10n.onnx
    └── yolo_trafficlight_v10n.pt
```

### 4. Model Classes

#### Vehicle Model (4 classes)
- **Class 0:** Bus
- **Class 1:** Car
- **Class 2:** Bike (Motorbike)
- **Class 3:** Truck

#### License Plate Model (1 class)
- **Class 0:** License Plate

#### OCR Model (36 classes)
- **Classes 0-9:** Digits (0-9)
- **Classes 10-35:** Letters (A-Z, một số ký tự đặc biệt)

### 5. Convert Model Format

#### Convert .pt → .onnx
```bash
# Using ultralytics
yolo export model=yolo_vehicle_v10m.pt format=onnx imgsz=640
```

#### Convert .pt → .engine (TensorRT)
```bash
# Using ultralytics (requires TensorRT)
yolo export model=yolo_vehicle_v10m.pt format=engine imgsz=640 device=0
```

---

## 📊 Confidence Threshold

### 1. Confidence là gì?

**Confidence** là độ tin cậy của model khi phát hiện object. Giá trị từ **0.0 đến 1.0**:
- **1.0** = 100% chắc chắn (perfect detection)
- **0.5** = 50% chắc chắn (uncertain)
- **0.0** = 0% chắc chắn (no detection)

### 2. Confidence trong YOLO

YOLO output cho mỗi detection:
```
bbox: [x1, y1, x2, y2]  # Tọa độ bounding box
confidence: 0.85         # Độ tin cậy detection
class: 1                 # Class ID (0=bus, 1=car, 2=bike, 3=truck)
```

### 3. Confidence Thresholds trong Hệ Thống

#### A. Detection Confidence (`conf`)

**Location:** `traffic-server/app/core/performance_config.py`

```python
INFERENCE_SETTINGS = {
    "conf": 0.5,  # Confidence threshold for YOLO detection
}
```

**Ý nghĩa:**
- Chỉ giữ detections có confidence ≥ 0.5
- Detections < 0.5 sẽ bị loại bỏ (false positives)

**Tuning:**
- **Tăng (0.6-0.7):** Ít detections hơn, chính xác hơn (ít false positives)
- **Giảm (0.3-0.4):** Nhiều detections hơn, nhưng có thể có false positives

#### B. ByteTrack Thresholds

**Location:** `traffic-server/app/core/performance_config.py`

```python
BYTETRACK_SETTINGS = {
    "track_thresh": 0.3,      # Threshold để bắt đầu track mới
    "match_thresh": 0.6,      # Threshold để match tracks giữa frames
}
```

**Ý nghĩa:**
- **`track_thresh`:** Detection phải có confidence ≥ 0.3 để bắt đầu track mới
- **`match_thresh`:** Tracks phải match với confidence ≥ 0.6 để được liên kết

**Tuning:**
- **Tăng `track_thresh`:** Chỉ track objects chắc chắn (ít tracks mới)
- **Giảm `track_thresh`:** Track nhiều objects hơn (nhiều tracks mới)
- **Tăng `match_thresh`:** Khó match hơn (tracks dễ bị mất)
- **Giảm `match_thresh`:** Dễ match hơn (tracks ổn định hơn)

#### C. OCR Confidence

**Location:** `traffic-server/app/core/performance_config.py`

```python
OCR_SETTINGS = {
    "plate_conf_threshold": 0.6,  # Threshold cho plate detection
}
```

**Ý nghĩa:**
- Plate detection phải có confidence ≥ 0.6 để chạy OCR
- Giảm false OCR calls

#### D. Violation Confidence

**Location:** `traffic-server/app/services/violation_detector.py`

```python
min_confidence_to_save = 0.7  # Chỉ lưu violations có plate confidence ≥ 0.7
```

**Ý nghĩa:**
- Chỉ lưu violations khi plate confidence cao (tránh false positives)

### 4. Confidence Flow

```
YOLO Detection
    ↓
confidence = 0.85
    ↓
Check: conf >= 0.5? ✅
    ↓
ByteTrack
    ↓
Check: conf >= 0.3? ✅ (track_thresh)
    ↓
Assign track_id
    ↓
OCR (if plate detected)
    ↓
plate_conf = 0.92
    ↓
Check: plate_conf >= 0.6? ✅
    ↓
Store plate text
    ↓
Violation Check
    ↓
Check: plate_conf >= 0.7? ✅
    ↓
Save to DB
```

### 5. Tuning Confidence cho Use Case

#### Use Case 1: High Accuracy (ít false positives)
```python
INFERENCE_SETTINGS = {"conf": 0.6}  # Tăng detection threshold
BYTETRACK_SETTINGS = {"track_thresh": 0.5}  # Tăng track threshold
OCR_SETTINGS = {"plate_conf_threshold": 0.7}  # Tăng OCR threshold
```

#### Use Case 2: High Recall (nhiều detections)
```python
INFERENCE_SETTINGS = {"conf": 0.3}  # Giảm detection threshold
BYTETRACK_SETTINGS = {"track_thresh": 0.2}  # Giảm track threshold
OCR_SETTINGS = {"plate_conf_threshold": 0.5}  # Giảm OCR threshold
```

#### Use Case 3: Balanced (default)
```python
INFERENCE_SETTINGS = {"conf": 0.5}  # Balanced
BYTETRACK_SETTINGS = {"track_thresh": 0.3}  # Balanced
OCR_SETTINGS = {"plate_conf_threshold": 0.6}  # Balanced
```

---

## ⚙️ Cấu Hình & Tối Ưu

### 1. Performance Configuration

**File:** `traffic-server/app/core/performance_config.py`

#### A. CUDA Optimizations
```python
# Tự động enable khi import
setup_cuda_optimizations()
# • TF32 for Ampere GPUs
# • cudnn benchmarking
# • Memory allocator optimization
```

#### B. Inference Settings
```python
INFERENCE_SETTINGS = {
    "imgsz": 640,        # Input size (640 = standard, 1280 = higher accuracy)
    "conf": 0.5,         # Confidence threshold
    "iou": 0.45,         # NMS IOU threshold
    "half": True,        # FP16 precision (2x faster on GPU)
    "device": "cuda:0",  # GPU device
}
```

#### C. ByteTrack Settings
```python
BYTETRACK_SETTINGS = {
    "track_thresh": 0.3,      # Start new track threshold
    "track_buffer": 60,       # Track buffer (frames) - 2s at 30fps
    "match_thresh": 0.6,      # Match threshold
    "min_box_area": 100,      # Minimum bbox area
}
```

#### D. Track Smoothing
```python
TRACK_SMOOTHING_SETTINGS = {
    "enabled": True,
    "position_alpha": 0.75,       # Position smoothing (0-1, higher = smoother)
    "size_alpha": 0.65,           # Size smoothing
    "max_center_shift": 150.0,    # Max pixel jump before bypass
    "max_scale_change": 2.0,      # Max scale change before bypass
}
```

#### E. OCR Settings
```python
OCR_SETTINGS = {
    "enabled": True,
    "model_type": "auto",           # auto | pt | onnx | engine
    "plate_conf_threshold": 0.6,
    "ocr_debounce_sec": 1.0,        # Min time between OCR calls
    "min_track_frames": 3,          # Min frames before OCR
    "bbox_expand_ratio": 0.15,      # Expand bbox 15% before crop
}
```

### 2. Tối Ưu Performance

#### A. GPU Memory (RTX 3050 4GB)

```python
# Limit VRAM usage
torch.cuda.set_per_process_memory_fraction(0.8, device=0)  # 80% VRAM
```

#### B. Model Selection

- **Fast:** Use `.engine` (TensorRT) models
- **Balanced:** Use `.onnx` models
- **Compatible:** Use `.pt` models

#### C. Input Size

- **640:** Standard, fast (30+ FPS)
- **1280:** Higher accuracy, slower (15-20 FPS)

#### D. Detection Frequency

```python
# Detect every N frames (reduce CPU/GPU load)
veh_detect_hz = 25  # 25 detections/second (instead of 30)
```

### 3. Tuning cho Use Case

#### Use Case: Real-time Streaming (30 FPS)
```python
INFERENCE_SETTINGS = {"imgsz": 640, "conf": 0.5}
BYTETRACK_SETTINGS = {"track_buffer": 60}
TRACK_SMOOTHING_SETTINGS = {"position_alpha": 0.75}
```

#### Use Case: High Accuracy (Offline Processing)
```python
INFERENCE_SETTINGS = {"imgsz": 1280, "conf": 0.6}
BYTETRACK_SETTINGS = {"track_buffer": 90}
TRACK_SMOOTHING_SETTINGS = {"position_alpha": 0.8}
```

---

## 🎨 Frontend & Backend

### 1. Frontend (Next.js)

#### Structure
```
src/
├── app/
│   ├── (admin)/
│   │   ├── detection/          # Detection pages
│   │   │   ├── page.jsx        # Main detection page
│   │   │   └── live/           # Real-time detection
│   │   └── ...
│   └── ...
├── components/
│   ├── DetectionCardRealtime.jsx  # Real-time detection card
│   ├── DetectionGrid.jsx          # Grid layout
│   └── ...
└── ...
```

#### Key Components

**A. DetectionCardRealtime.jsx**
- WebSocket connection
- Video player với canvas overlay
- Bbox drawing
- Plate text display

**B. DetectionGrid.jsx**
- Grid layout cho multiple streams
- Responsive design

#### WebSocket Integration

```javascript
// Connect to WebSocket
const ws = new WebSocket('ws://localhost:8000/ws/realtime/binary');

// Receive frames
ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  if (data.type === 'frame') {
    // Draw bboxes on canvas
    drawOverlays(ctx, data.detections, videoEl);
  }
};
```

### 2. Backend (FastAPI)

#### Structure
```
traffic-server/app/
├── main.py                      # FastAPI app
├── core/
│   ├── config.py               # Configuration
│   ├── performance_config.py   # Performance settings
│   └── database.py             # DB connection
├── routers/
│   ├── detection.py            # Detection endpoints
│   ├── realtime_ws_binary.py  # WebSocket endpoint
│   └── ...
├── services/
│   ├── realtime_binary_stream.py  # Main streaming service
│   ├── plate_ocr_service.py       # OCR service
│   └── violation_detector.py      # Violation detection
├── models/
│   ├── vehicle.py              # Vehicle model
│   ├── violation.py            # Violation model
│   └── ...
└── ...
```

#### Key Endpoints

**A. WebSocket: `/ws/realtime/binary`**
- Real-time video streaming
- Binary frame data
- Metadata (bbox, track_id, plate)

**B. REST API: `/api/detection/...`**
- Upload video
- Get detection results
- Get violations

### 3. Database (PostgreSQL)

#### Tables

**A. `video_jobs`**
- Video processing jobs
- Status tracking

**B. `vehicles`**
- Detected vehicles
- Track information
- Plate text

**C. `violations`**
- Violation records
- Evidence paths
- Timestamps

**D. `rois`**
- Region of Interest
- Polygon coordinates

**E. `users`**
- User accounts
- Authentication

---

## 🐛 Troubleshooting

### 1. GPU Issues

#### Problem: CUDA not available
```bash
# Check CUDA
python -c "import torch; print(torch.cuda.is_available())"

# Solution: Install PyTorch with CUDA
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
```

#### Problem: Out of Memory (OOM)
```python
# Solution: Reduce VRAM usage
# In performance_config.py
torch.cuda.set_per_process_memory_fraction(0.7, device=0)  # 70% instead of 80%
```

### 2. Model Issues

#### Problem: Model not found
```bash
# Check model files
ls traffic-server/models/vehicle/v10m/

# Solution: Download models or convert from .pt
```

#### Problem: ONNX model error
```bash
# Error: Unsupported model IR version
# Solution: Re-export model with newer ultralytics
yolo export model=model.pt format=onnx imgsz=640
```

### 3. Performance Issues

#### Problem: Low FPS (< 20 FPS)
```python
# Solution 1: Use TensorRT models
# Solution 2: Reduce input size
INFERENCE_SETTINGS = {"imgsz": 640}  # Instead of 1280

# Solution 3: Reduce detection frequency
veh_detect_hz = 20  # Instead of 25
```

#### Problem: High CPU usage
```python
# Solution: Enable GPU
DEVICE = "cuda:0"  # Instead of "cpu"
```

### 4. Tracking Issues

#### Problem: Tracks rời rạc
```python
# Solution: Adjust ByteTrack settings
BYTETRACK_SETTINGS = {
    "track_buffer": 90,      # Increase buffer
    "match_thresh": 0.5,     # Decrease match threshold
}
```

#### Problem: Too many ghost boxes
```python
# Solution: Aggressive cleanup
cleanup_threshold = 0.3  # Instead of 0.5
```

### 5. OCR Issues

#### Problem: OCR not working
```bash
# Check OCR models
ls traffic-server/app/modules/OCR/models/

# Solution: Disable OCR if not needed
OCR_SETTINGS = {"enabled": False}
```

### 6. Database Issues

#### Problem: Connection error
```bash
# Check PostgreSQL service
# Windows: Services → PostgreSQL
# Linux: sudo systemctl status postgresql

# Check connection string in .env
DATABASE_URL=postgresql://user:password@localhost:5432/dbname
```

---

## 📚 Tài Liệu Tham Khảo

### Links
- **YOLO:** https://docs.ultralytics.com/
- **ByteTrack:** https://github.com/ifzhang/ByteTrack
- **FastAPI:** https://fastapi.tiangolo.com/
- **Next.js:** https://nextjs.org/docs

### Contact
- **Issues:** GitHub Issues
- **Support:** Team contact

---

## ✅ Checklist Setup

- [ ] Anaconda environment created (`LVTN`)
- [ ] CUDA installed and verified
- [ ] Dependencies installed (`pip install -r requirements.txt`)
- [ ] PostgreSQL installed and database created
- [ ] `.env` file configured
- [ ] Models downloaded/placed in correct directories
- [ ] Backend running (`uvicorn app.main:app`)
- [ ] Frontend running (`npm run dev`)
- [ ] WebSocket connection working
- [ ] GPU detected and working

---

**🎉 Chúc bạn sử dụng hệ thống thành công!**

