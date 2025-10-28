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

## 🚀 Quick Start

### Prerequisites

- Python 3.8+
- Node.js 16+
- CUDA-capable GPU (recommended)
- Anaconda/Miniconda

### Installation

1. **Clone the repository**
```bash
git clone https://github.com/yourusername/traffic-system.git
cd traffic-system
```

2. **Set up the backend (FastAPI + YOLO)**
```bash
cd traffic-server

# Create conda environment
conda create -n LVTN python=3.8
conda activate LVTN

# Install dependencies
pip install -r requirements.txt

# Download YOLO models (if not included)
# Models should be placed in traffic-server/models/
```

3. **Set up the frontend (Next.js)**
```bash
# From project root
npm install
# or
yarn install
```

4. **Configure environment variables**

Create `.env` file in traffic-server directory:
```env
DATABASE_URL=sqlite:///./traffic.db
SECRET_KEY=your-secret-key-here
DEVICE=cuda  # or cpu
STATIC_DIR=./static
OUTPUT_DIR=./static/outputs
```

### Running the Application

**Terminal 1 - Start the backend server:**
```bash
cd traffic-server
conda activate LVTN
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

**Terminal 2 - Start the frontend:**
```bash
npm run dev
# or
yarn dev
```

Access the application at `http://localhost:3000`

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
| OCR | `yolo_ocr_chars_v8n.pt` | Read plate text | 85%+ |
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