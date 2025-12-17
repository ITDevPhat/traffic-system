# 🚦 Hệ Thống Phát Hiện Vi Phạm Giao Thông - LVTN

Hệ thống phát hiện vi phạm giao thông thời gian thực sử dụng computer vision và deep learning, được xây dựng với Next.js frontend và FastAPI backend.

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.11-blue.svg)
![Node](https://img.shields.io/badge/node-18+-green.svg)

## 🌟 Tính Năng Chính

- **Phát hiện xe thời gian thực**: Phát hiện và theo dõi các loại xe (ô tô, xe buýt, xe tải, xe máy) sử dụng YOLOv10
- **Nhận dạng biển số xe**: Pipeline OCR biển số - YOLO detection → character detection → OCR refinement (EasyOCR/PaddleOCR)
- **Phát hiện đèn giao thông**: Giám sát trạng thái đèn giao thông (đỏ/vàng/xanh)
- **Phát hiện vi phạm**: Tự động phát hiện vi phạm vượt đèn đỏ
- **Live Streaming**: Real-time video processing via WebSocket (≈20–30 FPS depending on hardware)
- **Hệ thống theo dõi**: Multi-object tracking framework (using ByteTrack algorithm)
- **Dashboard Web**: Giao diện React/Next.js hiện đại để giám sát và quản lý
- **REST API & WebSocket**: REST API for management & configuration, WebSocket for real-time video inference and violation events

## 🏗️ Kiến Trúc Hệ Thống

```
Frontend (Next.js)     ←→     WebSocket     ←→     Backend (FastAPI)
       ↓                          ↓                        ↓
   Dashboard              Real-time Stream           YOLO Models
   Video Player           Bounding Boxes             ByteTrack
   Admin Panel            Violations                 OCR Engine
```

## 🚀 Hướng Dẫn Cài Đặt

### Yêu Cầu Hệ Thống

- Python 3.11 (khuyến nghị)
- Node.js 18.x
- CUDA-capable GPU (khuyến nghị RTX 3050+)
- Anaconda/Miniconda
- PostgreSQL 12+

### Cài Đặt

1. **Tạo môi trường Anaconda**
```bash
conda create -n LVTN python=3.11
conda activate LVTN
```

2. **Cài đặt PyTorch với CUDA**
```bash
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
```

3. **Cài đặt Backend dependencies**
```bash
cd traffic-server
pip install -r requirements.txt
```

4. **Cài đặt Frontend dependencies**
```bash
npm install
```

5. **Cấu hình biến môi trường**

Tạo file `.env` trong `traffic-server/`:
```env
DATABASE_URL=postgresql://user:password@localhost:5432/traffic_db
SECRET_KEY=your-secret-key-here
DEVICE=cuda:0
STATIC_DIR=static
VIDEOS_DIR=videos
EVIDENCE_DIR=evidence
```

### Chạy Ứng Dụng

**Terminal 1 - Backend (FastAPI):**
```bash
cd traffic-server
conda activate LVTN
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

**Terminal 2 - Frontend (Next.js):**
```bash
npm run dev
```

**Truy cập:**
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

## 📚 Thư Viện Sử Dụng

### Backend (Python)

#### Computer Vision & Deep Learning
- **PyTorch 2.5.1** - Framework deep learning chính
- **TorchVision 0.20.1** - Xử lý ảnh và computer vision
- **Ultralytics 8.3.0** - YOLO-based object detection framework (YOLOv8/YOLOv10-compatible)
- **OpenCV 4.10.0** - Xử lý ảnh và video
- **EasyOCR 1.7.2** - Nhận dạng ký tự quang học
- **PaddleOCR 3.2.0** - OCR engine cho tiếng Việt
- **BoxMOT 15.0.9** - Multi-object tracking framework (using ByteTrack)
- **Supervision 0.21.0** - Computer vision utilities

#### Web Framework & API
- **FastAPI 0.104.1** - Web framework async
- **Uvicorn 0.24.0** - ASGI server
- **Starlette 0.27.0** - Web framework core
- **WebSockets 15.0.1** - Real-time communication
- **Python-multipart 0.0.6** - File upload support

#### Database & ORM
- **SQLAlchemy 2.0.43** - ORM framework
- **SQLModel 0.0.14** - Type-safe SQL models
- **AsyncPG 0.30.0** - PostgreSQL async driver
- **Psycopg2 2.9.10** - PostgreSQL adapter

#### Authentication & Security
- **Python-jose 3.3.0** - JWT tokens
- **Passlib 1.7.4** - Password hashing
- **BCrypt 5.0.0** - Password encryption
- **Cryptography 44.0.3** - Cryptographic recipes

#### Data Processing
- **NumPy 1.26.4** - Numerical computing
- **Pandas 2.3.2** - Data manipulation
- **Pillow 11.3.0** - Image processing
- **Matplotlib 3.10.5** - Data visualization
- **SciPy 1.16.1** - Scientific computing
- **Scikit-learn 1.7.2** - Machine learning
- **Scikit-image 0.25.2** - Image processing

#### Utilities
- **Pydantic 2.5.0** - Data validation
- **Python-dotenv 1.0.0** - Environment variables
- **Requests 2.32.4** - HTTP client
- **Loguru 0.7.3** - Logging
- **TQDM 4.67.1** - Progress bars

### Frontend (Node.js/React)

#### Core Framework
- **Next.js 14.2.6** - React framework
- **React 18.3.1** - UI library
- **TypeScript 5.5.4** - Type safety

#### UI Components & Styling
- **React-Bootstrap 2.10.4** - UI components
- **Bootstrap 5.3.3** - CSS framework
- **React-Icons 5.5.0** - Icon library
- **SASS 1.77.8** - CSS preprocessor

#### Data Visualization
- **ApexCharts 3.52.0** - Charts library
- **React-ApexCharts 1.4.1** - React wrapper
- **JSVectorMap 1.3.2** - Interactive maps

#### Form Handling
- **React-Hook-Form 7.53.0** - Form management
- **Yup 1.4.0** - Schema validation
- **React-Select 5.8.0** - Select components

#### Real-time & Communication
- **WebSocket client** - Real-time updates
- **SweetAlert2 11.25.0** - Beautiful alerts
- **React-Toastify 10.0.5** - Notifications

#### Development Tools
- **ESLint** - Code linting
- **Prettier 3.3.3** - Code formatting
- **Vitest 4.0.15** - Testing framework

## 📁 Cấu Trúc Dự Án

```
traffic-system/
├── src/                    # Frontend Next.js application
│   ├── app/               # App router pages
│   ├── components/        # React components
│   ├── context/          # React context providers
│   └── services/         # API services
├── traffic-server/        # Backend FastAPI application
│   ├── app/
│   │   ├── core/         # Core configurations
│   │   ├── models/       # SQLModel database models
│   │   ├── routers/      # API endpoints
│   │   ├── services/     # Business logic
│   │   └── utils/        # Utility functions
│   └── models/           # YOLO model files
└── videos/               # Sample videos for testing
```

## 🎯 YOLO Models

| Model | File | Mục đích | Độ chính xác |
|-------|------|----------|--------------|
| Phát hiện xe | `yolo_vehicle_v10m.pt` | Phát hiện các loại xe | 95%+ |
| Biển số xe | `yolo_plate_v10n.pt` | Phát hiện biển số | 90%+ |
| OCR | `yolo_ocr_chars_v10n.pt` | Đọc ký tự biển số | 85%+ |
| Đèn giao thông | `yolo_trafficlight_v10n.pt` | Phát hiện trạng thái đèn | 92%+ |

## 🔬 Experimental Setup

- **Input resolution**: 1280×720
- **Inference device**: NVIDIA RTX 3050+ (CUDA 12.1)
- **Average inference latency**: ~30–40 ms/frame
- **Memory usage**: ~4-6GB VRAM (depending on model size)
- **Supported video formats**: MP4, AVI, MOV, RTSP streams

## 🔧 Cấu Hình

### Cấu hình Backend (config.py)
- Điều chỉnh ngưỡng confidence detection
- Cấu hình GPU/CPU device
- Thiết lập kết nối database
- Định nghĩa vùng ROI

### Cấu hình Frontend
- API endpoint trong `services/api.ts`
- WebSocket URL cho streaming thời gian thực
- Cài đặt theme và layout UI

## 📊 Tài Liệu API

Khi backend đang chạy, truy cập tài liệu API tương tác tại:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## 🛠️ Phát Triển

### Backend Development
```bash
# Chạy với auto-reload
uvicorn app.main:app --reload

# Chạy tests
pytest

# Format code
black .
```

### Frontend Development
```bash
# Development server
npm run dev

# Build cho production
npm run build

# Chạy production build
npm start

# Lint code
npm run lint
```

## 📄 Giấy Phép

Dự án này được cấp phép theo MIT License.

## 👥 Tác Giả

- Nguyễn Thành Phát - Dự án LVTN

## 🙏 Lời Cảm Ơn

- YOLOv10-based models for object detection
- ByteTrack algorithm for multi-object tracking
- FastAPI framework
- Next.js and React community

---

**Lưu ý**: Đây là dự án học thuật cho mục đích học tập. Để sử dụng trong production, cần thêm các biện pháp bảo mật và tối ưu hóa.