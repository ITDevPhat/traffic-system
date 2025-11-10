---
trigger: manual
---

# traffic-system architecture rules

## main modules
core:
  - app/main.py
  - app/utils/model_loader.py
  - app/services/realtime_binary_stream.py
  - app/services/plate_ocr_service.py
  - app/routers/realtime_ws_binary.py

## functional flow
1. load YOLO model (on GPU)
2. initialize ByteTrack tracker
3. initialize OCR service (optional TensorRT)
4. start realtime threads:
    - capture: read frame
    - infer: YOLO + ByteTrack
    - encode: draw + stream WS
5. send metadata via websocket
6. save events to database

## async threading model
- all realtime threads run concurrently
- lock-protected queues between threads
- GPU inference always runs in infer thread

## database layer
uses SQLAlchemy with PostgreSQL
schema: violations, vehicles, video_jobs, rois, users
transaction scope: per API request

## module dependency order
main.py → services → routers → models → db
never import routers from services (avoid circular deps)

## design constraints
- realtime pipeline order fixed: YOLO → ByteTrack → OCR
- no blocking I/O in infer thread
- only encode thread interacts with OpenCV
- model caching required (no reload per request)
