# Traffic Violation Detection System

An academic project for detecting traffic violations from live video and recorded footage. The system combines a Next.js dashboard with a FastAPI service for vehicle detection, license plate recognition, traffic-light monitoring, and violation tracking.

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.11-blue.svg)
![Node.js](https://img.shields.io/badge/node.js-18%2B-green.svg)

## Features

- Detect and track cars, buses, trucks, and motorcycles with YOLO-based models.
- Detect license plates and recognize their characters using an OCR pipeline.
- Detect traffic-light states and identify red-light violations.
- Process live video through WebSocket streams.
- Store violation records and supporting evidence.
- Manage the system through a web dashboard built with Next.js and React.
- Expose REST endpoints for configuration and administration.

## Architecture

```text
Next.js frontend  <-->  WebSocket / REST  <-->  FastAPI backend
     Dashboard                Streams              Computer vision
     Video player             Events                YOLO + OCR
     Admin tools              Evidence              ByteTrack
```

## Requirements

- Python 3.11
- Node.js 18 or later
- PostgreSQL 12 or later
- An NVIDIA GPU with CUDA support is recommended for real-time inference.
- Conda or Miniconda is recommended for managing the Python environment.

## Installation

### 1. Set up the Python environment

```bash
conda create -n LVTN python=3.11
conda activate LVTN
```

Install PyTorch. For a CUDA 12.1 installation:

```bash
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
```

For CPU-only environments, use the CPU index instead:

```bash
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu
```

Install the backend dependencies:

```bash
cd traffic-server
pip install -r requirements.txt
cd ..
```

### 2. Install frontend dependencies

```bash
npm install
```

### 3. Configure the backend

Create `traffic-server/.env` and update the values for your environment:

```env
DATABASE_URL=postgresql://username:password@localhost:5432/traffic_db
SECRET_KEY=replace-with-a-long-random-value
DEVICE=cuda:0
STATIC_DIR=static
VIDEOS_DIR=videos
EVIDENCE_DIR=evidence
```

Before starting the application, create a PostgreSQL database named `traffic_db` or change `DATABASE_URL` to use an existing database.

## Running the Application

Start the backend in one terminal:

```bash
cd traffic-server
conda activate LVTN
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Start the frontend in a second terminal:

```bash
npm run dev
```

The application will be available at:

- Frontend: <http://localhost:3000>
- Backend API: <http://localhost:8000>
- Swagger UI: <http://localhost:8000/docs>
- ReDoc: <http://localhost:8000/redoc>

## Project Structure

```text
traffic-system/
├── src/                 # Next.js frontend
│   ├── app/             # App Router pages
│   ├── components/     # Reusable React components
│   ├── context/         # React context providers
│   └── services/        # API and WebSocket clients
├── traffic-server/     # FastAPI backend
│   ├── app/
│   │   ├── core/        # Application configuration
│   │   ├── models/      # Database models
│   │   ├── routers/     # API routes
│   │   ├── services/    # Application services
│   │   └── utils/       # Backend utilities
│   └── models/          # Detection model files
└── videos/              # Local test videos
```

## Model Components

The backend uses separate models for the main stages of the pipeline:

| Component | Purpose |
| --- | --- |
| Vehicle detector | Detect vehicles by class |
| License-plate detector | Locate license plates in a frame |
| Character detector | Detect individual plate characters |
| Traffic-light detector | Detect traffic lights and their states |
| OCR engine | Refine and recognize plate text |
| ByteTrack | Track objects across video frames |

Model files are expected in the backend's model directory. Check the backend configuration if your files are stored elsewhere.

## Development

Backend:

```bash
cd traffic-server
pytest
black .
```

Frontend:

```bash
npm run lint
npm run test:run
npm run build
```

## Notes

This project was developed for academic purposes. Running it in a production environment would require additional work around authentication, data retention, monitoring, model validation, and deployment security.

## License

This project is released under the MIT License.

## Author

Nguyen Thanh Phat
