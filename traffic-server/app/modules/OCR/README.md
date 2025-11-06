# OCR Module - License Plate Recognition

Module con cho FastAPI để nhận dạng biển số xe Việt Nam sử dụng YOLO v10.

## 🚀 Cài đặt

```bash
pip install -r requirements.txt
```

## 📦 Sử dụng

### Cách 1: Chạy trực tiếp (Standalone)

```bash
python main.py
```

API sẽ chạy tại: `http://localhost:8000`

### Cách 2: Tích hợp vào FastAPI app

```python
from fastapi import FastAPI
from ocr import router as ocr_router

app = FastAPI()
app.include_router(ocr_router)
```

## 🔌 API Endpoints

- `GET /ocr/` - API info
- `GET /ocr/health` - Health check
- `GET /ocr/stats` - Statistics
- `POST /ocr/detect` - Nhận dạng biển số (JSON)
- `POST /ocr/detect_base64` - Nhận dạng từ base64 (nhanh hơn)
- `POST /ocr/detect_with_image` - Nhận dạng và trả về ảnh có bbox
- `POST /ocr/benchmark` - Benchmark hiệu suất

### POST `/ocr/detect`

**Input:**
- `file`: File ảnh (multipart/form-data)
- `model_type`: "pt", "onnx", hoặc "engine" (default: "pt")
- `confidence_threshold`: 0.0-1.0 (default: 0.60)
- `draw_bbox`: bool (default: false)

**Output:**
```json
{
  "success": true,
  "processing_time": 0.111,
  "model_type": "pt",
  "plates": [
    {
      "text": "29A12345",
      "confidence": 0.95,
      "bbox": {
        "x": 120.0,
        "y": 80.0,
        "width": 200.0,
        "height": 70.0
      }
    }
  ]
}
```

### POST `/ocr/detect_base64`

**Input:**
- `image_base64`: Base64 string của ảnh
- `model_type`: "pt", "onnx", hoặc "engine"
- `confidence_threshold`: 0.0-1.0

**Output:** Tương tự `/ocr/detect` nhưng nhanh hơn (giảm network overhead)

## 📁 Cấu trúc

```
OCR/
├── __init__.py              # Module exports
├── main.py                  # Entry point (standalone server)
├── core.py                  # PyTorch implementation
├── core_optimized.py        # ONNX/TensorRT support
├── router.py                # FastAPI router
├── function/                # Utilities
│   ├── __init__.py
│   └── utils_rotate.py
├── models/                  # Model files
│   ├── license_plate/       # Detection models
│   └── ocr/                 # OCR models
├── requirements.txt
└── README.md
```

## 🎯 Model Types

Module hỗ trợ 3 loại model:
- **PyTorch (.pt)**: Mặc định, dễ sử dụng
- **ONNX (.onnx)**: Nhanh hơn ~5-10%
- **TensorRT (.engine)**: Nhanh nhất, ~10-15% so với PyTorch

## 📝 Ghi Chú

- Tự động phát hiện GPU/CPU
- Models được load khi khởi động (singleton)
- Tự động resize ảnh nếu quá lớn (>1920px)
- Hỗ trợ biển số 1 dòng và 2 dòng
