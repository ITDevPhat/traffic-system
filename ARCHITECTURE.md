# 🏗️ Kiến Trúc Hệ Thống Traffic Violation Detection

## 📋 Tổng Quan

Hệ thống **Traffic Violation Detection** là một ứng dụng web full-stack sử dụng AI/Computer Vision để phát hiện vi phạm giao thông tự động. Hệ thống được xây dựng với kiến trúc microservices, tách biệt frontend và backend, giao tiếp qua REST API và WebSocket.

## 🎯 Mục Tiêu Hệ Thống

1. **Phát hiện phương tiện real-time** với độ chính xác cao
2. **Nhận dạng biển số xe** tự động (hỗ trợ biển số Việt Nam)
3. **Phát hiện vi phạm** đèn đỏ và các vi phạm khác
4. **Tracking đa phương tiện** xuyên suốt video
5. **Giao diện web** hiện đại, responsive cho quản lý và giám sát
6. **Xử lý video** với tốc độ cao (25+ FPS trên GPU)

## 🏛️ Kiến Trúc Tổng Quan

```
┌─────────────────────────────────────────────────────────────────┐
│                        Client Browser                            │
│  ┌─────────────────┐  ┌──────────────┐  ┌─────────────────┐   │
│  │   Next.js App   │  │  WebSocket   │  │   REST APIs    │   │
│  │  (React + TS)   │  │   Client     │  │    Client      │   │
│  └────────┬────────┘  └──────┬───────┘  └────────┬────────┘   │
└───────────┼──────────────────┼──────────────────┼─────────────┘
            │                  │                   │
            ▼                  ▼                   ▼
┌─────────────────────────────────────────────────────────────────┐
│                      FastAPI Backend                             │
│  ┌─────────────────┐  ┌──────────────┐  ┌─────────────────┐   │
│  │   REST API      │  │  WebSocket   │  │   Static Files  │   │
│  │   Endpoints     │  │   Server     │  │     Server      │   │
│  └────────┬────────┘  └──────┬───────┘  └─────────────────┘   │
│           │                  │                                   │
│           ▼                  ▼                                   │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │              Business Logic Layer                        │   │
│  │  ┌─────────────┐  ┌──────────────┐  ┌───────────────┐  │   │
│  │  │  Detection  │  │   Tracking   │  │   Violation   │  │   │
│  │  │   Service   │  │   Service    │  │   Service     │  │   │
│  │  └─────────────┘  └──────────────┘  └───────────────┘  │   │
│  └─────────────────────────────────────────────────────────┘   │
│                              │                                   │
│                              ▼                                   │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                    AI/ML Layer                           │   │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌─────────┐ │   │
│  │  │  YOLO    │  │ ByteTrack│  │   OCR    │  │  ROI    │ │   │
│  │  │ Models   │  │ Tracker  │  │  Engine  │  │ Manager │ │   │
│  │  └──────────┘  └──────────┘  └──────────┘  └─────────┘ │   │
│  └─────────────────────────────────────────────────────────┘   │
│                              │                                   │
│                              ▼                                   │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                  Data Layer                              │   │
│  │  ┌──────────┐  ┌──────────────┐  ┌─────────────────┐   │   │
│  │  │  SQLite  │  │ File Storage │  │  Redis Cache    │   │   │
│  │  │    DB    │  │   (Videos)   │  │   (Optional)    │   │   │
│  │  └──────────┘  └──────────────┘  └─────────────────┘   │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

## 🔧 Chi Tiết Các Thành Phần

### 1. Frontend Layer (Next.js + React)

#### Tech Stack:
- **Framework**: Next.js 14 với App Router
- **UI Library**: React 18 + TypeScript
- **Styling**: Tailwind CSS + SCSS modules
- **State Management**: React Context API
- **Real-time**: Native WebSocket API
- **HTTP Client**: Axios
- **UI Components**: Custom components + Headless UI

#### Các Module Chính:

```
src/app/
├── (admin)/              # Admin dashboard routes
│   ├── dashboards/      # Trang tổng quan
│   ├── detection/       # Giao diện detection real-time
│   ├── violations/      # Quản lý vi phạm
│   └── agents/          # Quản lý tài xế/phương tiện
├── (auth)/              # Authentication pages
└── api/                 # API routes (if needed)
```

#### Features:
- **Real-time Detection View**: Canvas overlay hiển thị bounding boxes
- **Video Player**: Tích hợp với detection overlay
- **Dashboard**: Thống kê vi phạm, biểu đồ
- **Responsive Design**: Hoạt động tốt trên mobile/tablet
- **Dark Mode**: Hỗ trợ theme tối/sáng

### 2. Backend Layer (FastAPI)

#### Tech Stack:
- **Framework**: FastAPI (async Python)
- **Database ORM**: SQLModel (SQLAlchemy + Pydantic)
- **WebSocket**: FastAPI WebSocket
- **Task Queue**: Threading + Queue (có thể upgrade lên Celery)
- **File Storage**: Local filesystem (có thể upgrade lên S3)

#### API Structure:

```
/api/v1/
├── /auth/              # Authentication endpoints
│   ├── POST /login
│   └── POST /register
├── /videos/            # Video management
│   ├── POST /upload
│   ├── GET /list
│   └── GET /{id}/status
├── /violations/        # Violation records
│   ├── GET /list
│   ├── GET /{id}
│   └── DELETE /{id}
├── /detection/         # Detection control
│   ├── POST /process
│   └── GET /config
└── /ws/               # WebSocket endpoints
    └── /realtime      # Real-time detection stream
```

### 3. AI/ML Layer

#### YOLO Models Pipeline:

```python
Frame → Vehicle Detection → Tracking → Plate Detection → OCR → Violation Check
   ↓          ↓                ↓            ↓              ↓          ↓
 Input    YOLOv10m        ByteTrack    YOLOv10n      YOLOv8n    Business
 Video    (4 classes)     (ID assign)  (1 class)   (36 chars)    Logic
```

#### Model Details:

1. **Vehicle Detection Model**
   - Model: YOLOv10m
   - Classes: car, bus, truck, motorbike
   - Input: 640x640 (dynamic)
   - FPS: 30+ on RTX 3060

2. **License Plate Detection**
   - Model: YOLOv10n
   - Classes: license_plate
   - Input: 384x384
   - Accuracy: 90%+

3. **OCR Model**
   - Model: YOLOv8n (character detection)
   - Classes: 0-9, A-Z (36 classes)
   - Vietnamese plate format support
   - Two-line plate support

4. **Traffic Light Detection**
   - Model: YOLOv10n
   - Classes: red, yellow, green
   - Used for violation logic

#### Optimization Techniques:

- **FP16 Inference**: Half precision for 2x speedup
- **Batch Processing**: Process multiple ROIs together
- **Frame Skipping**: Configurable skip rate
- **Threading**: Separate threads for capture/inference
- **Object Pooling**: Reuse YOLO instances

### 4. Data Layer

#### Database Schema (SQLModel):

```python
# Core Models
User
├── id: UUID
├── username: str
├── email: str
└── role: str

VideoJob
├── id: int
├── filename: str
├── status: JobStatus
├── created_at: datetime
└── completed_at: datetime

Vehicle
├── id: int
├── track_id: int
├── vehicle_type: str
├── plate_number: str
├── confidence: float
└── video_job_id: int

Violation
├── id: int
├── vehicle_id: int
├── violation_type: str
├── timestamp: datetime
├── evidence_path: str
└── location: str

ROI (Region of Interest)
├── id: int
├── name: str
├── type: str
└── coordinates: JSON
```

## 🚀 Luồng Xử Lý Chính

### 1. Video Upload Flow
```
User Upload → Save File → Create Job → Process Video → Save Results → Notify User
```

### 2. Real-time Detection Flow
```
Video Stream → Frame Queue → YOLO Inference → ByteTrack → WebSocket Emit → Frontend Render
     ↓              ↓              ↓               ↓             ↓              ↓
  30 FPS      Buffer: 10      GPU Process    Assign IDs    JSON Data    Canvas Draw
```

### 3. Violation Detection Logic
```python
if traffic_light == "red" and vehicle_in_roi("violation_zone"):
    create_violation("RED_LIGHT", vehicle, evidence_frame)
```

## 📊 Performance Metrics

### Target Performance:
- **Processing Speed**: 25+ FPS real-time
- **Latency**: < 100ms end-to-end
- **Accuracy**: 
  - Vehicle Detection: 95%+
  - Plate Recognition: 85%+
  - Violation Detection: 90%+

### Scalability:
- **Concurrent Streams**: 5-10 (per GPU)
- **Storage**: ~1GB per hour of video
- **Database**: SQLite (dev) → PostgreSQL (prod)

## 🔒 Security Considerations

1. **Authentication**: JWT tokens cho API
2. **Authorization**: Role-based access (Admin/User)
3. **Data Privacy**: Blur faces trong evidence
4. **Rate Limiting**: Prevent API abuse
5. **Input Validation**: Sanitize all inputs

## 🚢 Deployment Architecture

### Development:
```
Local Machine
├── Frontend: localhost:3000
├── Backend: localhost:8000
└── Database: SQLite file
```

### Production (Recommended):
```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Nginx     │────▶│  Next.js    │     │  FastAPI    │
│   Reverse   │     │   Server    │     │   Server    │
│   Proxy     │     │  (PM2/Node) │     │  (Gunicorn) │
└─────────────┘     └─────────────┘     └──────┬──────┘
                                               │
                    ┌─────────────┐     ┌──────▼──────┐
                    │ PostgreSQL  │     │    Redis    │
                    │  Database   │     │   Cache     │
                    └─────────────┘     └─────────────┘
```

## 📈 Tương Lai & Mở Rộng

### Phase 2:
- [ ] Multi-camera support
- [ ] Cloud storage integration (S3)
- [ ] Mobile app (React Native)
- [ ] Advanced analytics dashboard

### Phase 3:
- [ ] Edge deployment (Jetson Nano)
- [ ] Kubernetes orchestration
- [ ] Multi-tenant architecture
- [ ] AI model versioning

## 🛠️ Development Workflow

### Local Development:
1. Start backend: `uvicorn app.main:app --reload`
2. Start frontend: `npm run dev`
3. Open browser: `http://localhost:3000`

### Testing:
- Backend: `pytest` với test coverage
- Frontend: Jest + React Testing Library
- E2E: Cypress hoặc Playwright

### CI/CD Pipeline:
```
Git Push → GitHub Actions → Run Tests → Build Docker → Deploy → Health Check
```

---

**Note**: Đây là kiến trúc cho môi trường development và small-scale production. Với large-scale deployment cần consider thêm load balancing, caching strategies, và distributed processing.
