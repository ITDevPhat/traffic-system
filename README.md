# 🚦 Traffic Violation Detection System

A real-time traffic violation detection system using computer vision and deep learning, built with Next.js frontend and FastAPI backend.

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.8+-blue.svg)
![Node](https://img.shields.io/badge/node-16+-green.svg)

## 🌟 Features

- **Real-time Vehicle Detection**: Detect and track vehicles (cars, buses, trucks, motorbikes) using YOLOv10
- **License Plate Recognition**: Automatic license plate detection and OCR for Vietnamese plates
- **Traffic Light Detection**: Monitor traffic light status (red/yellow/green)
- **Violation Detection**: Automatically detect red light violations
- **Live Streaming**: WebSocket-based real-time video processing with 25+ FPS
- **Tracking System**: ByteTrack integration for stable multi-object tracking
- **Web Dashboard**: Modern React/Next.js interface for monitoring and management

## 🏗️ System Architecture

```
Frontend (Next.js)     ←→     WebSocket     ←→     Backend (FastAPI)
       ↓                          ↓                        ↓
   Dashboard              Real-time Stream           YOLO Models
   Video Player           Bounding Boxes             ByteTrack
   Admin Panel            Violations                 OCR Engine
```

## 📖 Documentation

**👉 Xem [COMPLETE_GUIDE.md](COMPLETE_GUIDE.md) để có hướng dẫn chi tiết đầy đủ!**

Bao gồm:
- ✅ Hướng dẫn cài đặt từ A-Z (Anaconda, GPU, Database)
- ✅ Kiến trúc hệ thống chi tiết
- ✅ Luồng xử lý (Pipeline)
- ✅ Model YOLO (.pt, .onnx, .engine)
- ✅ Giải thích Confidence Threshold
- ✅ Cấu hình & Tối ưu
- ✅ Frontend & Backend
- ✅ Troubleshooting

## 🚀 Quick Start

### Prerequisites

- Python 3.8 - 3.11
- Node.js 16+ - 18.x
- CUDA-capable GPU (recommended, RTX 3050+)
- Anaconda/Miniconda
- PostgreSQL 12+

### Installation

1. **Clone the repository**
```bash
git clone https://github.com/yourusername/traffic-system.git
cd traffic-system
```

2. **Set up Anaconda environment**
```bash
conda create -n LVTN python=3.10
conda activate LVTN
```

3. **Install PyTorch with CUDA** (if using GPU)
```bash
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
```

4. **Set up the backend**
```bash
cd traffic-server
pip install -r requirements.txt
```

5. **Set up the frontend**
```bash
# From project root
npm install
```

6. **Configure environment variables**

Create `.env` file in `traffic-server/`:
```env
DATABASE_URL=postgresql://user:password@localhost:5432/traffic_db
SECRET_KEY=your-secret-key-here
DEVICE=cuda:0
STATIC_DIR=static
VIDEOS_DIR=videos
EVIDENCE_DIR=evidence
```

### Running the Application

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

**Access:**
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

## 📁 Project Structure

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

| Model | File | Purpose | Accuracy |
|-------|------|---------|----------|
| Vehicle Detection | `yolo_vehicle_v10m.pt` | Detect vehicles | 95%+ |
| License Plate | `yolo_plate_v10n.pt` | Detect plates | 90%+ |
| OCR | `yolo_ocr_chars_v10n.pt` | Read plate text | 85%+ |
| Traffic Light | `yolo_trafficlight_v10n.pt` | Detect light status | 92%+ |

## 🔧 Configuration

### Backend Configuration (config.py)
- Adjust detection confidence thresholds
- Configure GPU/CPU device
- Set database connection
- Define ROI zones

### Frontend Configuration
- API endpoint in `services/api.ts`
- WebSocket URL for real-time streaming
- UI theme and layout settings

## 📊 API Documentation

Once the backend is running, access the interactive API documentation at:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## 🛠️ Development

### Backend Development
```bash
# Run with auto-reload
uvicorn app.main:app --reload

# Run tests
pytest

# Format code
black .
```

### Frontend Development
```bash
# Development server
npm run dev

# Build for production
npm run build

# Run production build
npm start

# Lint code
npm run lint
```

## 🐳 Docker Deployment (Coming Soon)

```bash
# Build and run with Docker Compose
docker-compose up -d
```

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🤝 Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 👥 Authors

- Traffic System Team - LVTN Project

## 🙏 Acknowledgments

- YOLOv10 by Ultralytics
- ByteTrack for object tracking
- FastAPI framework
- Next.js and React community

## 📞 Support

For support, email support@trafficsystem.com or open an issue in the GitHub repository.

---

**Note**: This is an academic project for learning purposes. For production use, additional security and optimization measures should be implemented.