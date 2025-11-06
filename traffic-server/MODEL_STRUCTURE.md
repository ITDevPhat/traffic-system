# 📂 Cấu Trúc Model - Traffic Detection System

## 🗂️ Directory Structure

```
traffic-server/models/
├── license_plate/              # Phát hiện biển số xe
│   ├── yolo_plate_v10n.engine   (9.2 MB)  ← Ưu tiên 1 (fastest)
│   ├── yolo_plate_v10n.onnx     (9.3 MB)  ← Ưu tiên 2
│   └── yolo_plate_v10n.pt       (5.9 MB)  ← Ưu tiên 3
│
├── ocr/                        # Nhận diện ký tự trên biển số
│   ├── yolo_ocr_chars_v8n.engine   (10.2 MB)
│   ├── yolo_ocr_chars_v8n.onnx     (12.3 MB)
│   └── yolo_ocr_chars_v8n.pt       (6.3 MB)
│
├── traffic_light/              # Phát hiện đèn giao thông
│   ├── yolo_trafficlight_v10n.engine   (8.8 MB)
│   ├── yolo_trafficlight_v10n.onnx     (9.3 MB)
│   └── yolo_trafficlight_v10n.pt       (5.9 MB)
│
└── vehicle/                    # Phát hiện phương tiện (CHÍNH - dùng ByteTrack)
    ├── 11s/                    # YOLOv11s - Nhanh hơn, nhẹ hơn
    │   ├── yolo_vehicle_11s.engine   (24.3 MB)
    │   ├── yolo_vehicle_11s.onnx     (37.9 MB)
    │   └── yolo_vehicle_11s.pt       (19.2 MB)
    │
    └── v10m/                   # YOLOv10m - Chính xác cao hơn (DEFAULT)
        ├── yolo_vehicle_v10m.engine   (35.6 MB)
        ├── yolo_vehicle_v10m.onnx     (61.6 MB)
        └── yolo_vehicle_v10m.pt       (66.7 MB)
```

---

## 🎯 Model Usage

### 1. **Vehicle Detection** (4 classes: bus, car, bike, truck)

**Purpose:** Phát hiện phương tiện + ByteTrack tracking + bbox overlay

**Default:** `v10m` (chính xác cao)
```python
# Config: traffic-server/app/core/config.py
VEHICLE_MODEL_VERSION = "v10m"  # v10m | 11s
```

**Performance:**

| Version | Accuracy | Speed (FPS) | VRAM | Model Size | Use Case |
|---------|----------|-------------|------|------------|----------|
| **v10m** | ⭐⭐⭐⭐⭐ | 35-40 FPS | 2.5GB | 35.6 MB | **Default** - Chính xác cao |
| **11s** | ⭐⭐⭐⭐ | 45-55 FPS | 2.2GB | 24.3 MB | Tốc độ cao, ít VRAM |

**Switch Version:**
```bash
# Method 1: Environment variable
export VEHICLE_MODEL_VERSION=11s

# Method 2: Edit config.py
VEHICLE_MODEL_VERSION: str = "11s"
```

### 2. **License Plate Detection**

**Model:** `yolo_plate_v10n`  
**Purpose:** Phát hiện vùng biển số trên phương tiện

### 3. **OCR Character Recognition**

**Model:** `yolo_ocr_chars_v8n`  
**Purpose:** Nhận diện từng ký tự trên biển số

### 4. **Traffic Light Detection**

**Model:** `yolo_trafficlight_v10n`  
**Purpose:** Phát hiện trạng thái đèn giao thông (red/green/yellow)

---

## 🚀 Model Loading Priority

Hệ thống tự động load theo thứ tự:

```
1. .engine (TensorRT)  → Nhanh nhất (3-5x faster than .pt)
2. .onnx (ONNX Runtime) → Nhanh (2-3x faster than .pt)
3. .pt (PyTorch)        → Chậm nhất (fallback)
```

**Code:**
```python
# traffic-server/app/utils/model_loader.py

def find_model_file(base_path: str) -> Tuple[str, str]:
    """Auto-detect: .engine > .onnx > .pt"""
    for ext in [".engine", ".onnx", ".pt"]:
        model_path = base_path + ext
        if os.path.exists(model_path):
            return model_path, ext[1:]
    return None, "none"
```

---

## 📊 Performance Comparison (RTX 3050 4GB)

### Vehicle Detection

| Model | Format | FPS | Inference | VRAM | Status |
|-------|--------|-----|-----------|------|--------|
| **v10m** | .engine | **37 FPS** | **27ms** | **2.5GB** | ✅ DEFAULT |
| v10m | .onnx | 28 FPS | 35ms | 2.8GB | ✅ OK |
| v10m | .pt | 18 FPS | 55ms | 3.2GB | ❌ Slow |
| **11s** | .engine | **45 FPS** | **22ms** | **2.2GB** | ✅ FAST |
| 11s | .onnx | 35 FPS | 28ms | 2.5GB | ✅ OK |
| 11s | .pt | 25 FPS | 40ms | 2.8GB | ⚠️ Acceptable |

---

## 🔧 Configuration Files

### 1. Main Config
```python
# traffic-server/app/core/config.py

MODELS_DIR = "traffic-server/models"

# Vehicle model (dynamic)
VEHICLE_MODEL_VERSION = "v10m"  # v10m | 11s
YOLO_VEHICLE_MODEL = f"{MODELS_DIR}/vehicle/{VERSION}/yolo_vehicle_{VERSION}"

# Other models (fixed)
YOLO_PLATE_MODEL = f"{MODELS_DIR}/license_plate/yolo_plate_v10n"
YOLO_OCR_MODEL = f"{MODELS_DIR}/ocr/yolo_ocr_chars_v8n"
YOLO_TRAFFIC_LIGHT_MODEL = f"{MODELS_DIR}/traffic_light/yolo_trafficlight_v10n"
```

### 2. Performance Config
```python
# traffic-server/app/core/performance_config.py

# Inference settings
INFERENCE_SETTINGS = {
    "imgsz": 640,
    "conf": 0.5,
    "half": True,  # FP16
    "device": "cuda:0",
}

# Model priority
MODEL_PRIORITY = ["engine", "onnx", "pt"]
```

---

## 📝 Model Classes

### Vehicle Model (4 classes)

```python
{
    0: "bus",      # 🚌 Xe buýt
    1: "car",      # 🚗 Xe hơi
    2: "bike",     # 🏍️ Xe máy
    3: "truck"     # 🚚 Xe tải
}
```

**Color Coding:**
- 🟠 **bus** - Orange (`#e67e22`)
- 🔵 **car** - Blue (`#3498db`)
- 🟢 **bike** - Green (`#2ecc71`)
- 🔴 **truck** - Red (`#e74c3c`)

---

## 🎯 Recommendation

### For Accuracy (Production)
✅ Use **v10m** with **.engine** format
```
Performance: 35-40 FPS
Accuracy: High
VRAM: 2.5GB
```

### For Speed (Testing/Demo)
✅ Use **11s** with **.engine** format
```
Performance: 45-55 FPS
Accuracy: Good
VRAM: 2.2GB
```

### For Low VRAM (<3GB)
✅ Use **11s** with **.onnx** format
```
Performance: 35 FPS
Accuracy: Good
VRAM: 2.0GB
```

---

## 🔄 Converting Models

### Convert .pt to .engine (TensorRT)

```bash
cd traffic-server/models
python convert.py
```

**Script Content:**
```python
# convert.py
from ultralytics import YOLO

model = YOLO("vehicle/v10m/yolo_vehicle_v10m.pt")
model.export(
    format="engine",
    half=True,      # FP16
    device=0,       # GPU 0
    imgsz=640,
)
```

---

## 📈 Benchmark

```bash
cd traffic-server
conda activate LVTN
python benchmark_fps.py
```

**Expected Output:**
```
============================================================
📊 BENCHMARK SUMMARY
============================================================
Format     FPS        Inference (ms)  Target Met
------------------------------------------------------------
v10m.engine    37.0       27.0            ✅
v10m.onnx      28.5       35.1            ❌
v10m.pt        18.2       54.9            ❌
11s.engine     45.0       22.2            ✅
11s.onnx       35.0       28.6            ✅
11s.pt         25.0       40.0            ❌
============================================================

🏆 FASTEST: 11s.engine - 45.0 FPS
✅ RECOMMENDED: v10m.engine - 37.0 FPS (accuracy + speed balanced)
```

---

## 🗄️ Database Models Table

```sql
-- Table: models
CREATE TABLE models (
    model_id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    model_type VARCHAR(50) NOT NULL,  -- vehicle, plate, ocr, traffic_light
    file_path VARCHAR(255) NOT NULL,
    version VARCHAR(50),
    framework VARCHAR(50),
    confidence_threshold FLOAT DEFAULT 0.5,
    description TEXT
);

-- Insert vehicle models
INSERT INTO models (name, model_type, file_path, version, framework, confidence_threshold, description)
VALUES
-- v10m models
('yolo_vehicle_v10m_engine', 'vehicle', 'models/vehicle/v10m/yolo_vehicle_v10m.engine', 'v10m', 'YOLOv10m', 0.5, 'Phương tiện chính xác cao (TensorRT)'),
('yolo_vehicle_v10m_onnx', 'vehicle', 'models/vehicle/v10m/yolo_vehicle_v10m.onnx', 'v10m', 'YOLOv10m', 0.5, 'Phương tiện chính xác cao (ONNX)'),
('yolo_vehicle_v10m_pt', 'vehicle', 'models/vehicle/v10m/yolo_vehicle_v10m.pt', 'v10m', 'YOLOv10m', 0.5, 'Phương tiện chính xác cao (PyTorch)'),
-- 11s models
('yolo_vehicle_11s_engine', 'vehicle', 'models/vehicle/11s/yolo_vehicle_11s.engine', '11s', 'YOLOv11s', 0.5, 'Phương tiện nhanh (TensorRT)'),
('yolo_vehicle_11s_onnx', 'vehicle', 'models/vehicle/11s/yolo_vehicle_11s.onnx', '11s', 'YOLOv11s', 0.5, 'Phương tiện nhanh (ONNX)'),
('yolo_vehicle_11s_pt', 'vehicle', 'models/vehicle/11s/yolo_vehicle_11s.pt', '11s', 'YOLOv11s', 0.5, 'Phương tiện nhanh (PyTorch)');
```

---

## ✅ Verification

### Check Model Files
```bash
cd traffic-server/models

# Vehicle models
ls vehicle/v10m/*.engine  # Should exist
ls vehicle/11s/*.engine   # Should exist

# Other models
ls license_plate/*.engine
ls ocr/*.engine
ls traffic_light/*.engine
```

### Check Config
```python
from app.core.config import settings

print(f"Vehicle Model: {settings.YOLO_VEHICLE_MODEL}")
print(f"Version: {settings.VEHICLE_MODEL_VERSION}")
```

### Test Loading
```python
from app.utils.model_loader import load_yolo_model, get_model_info

info = get_model_info(settings.YOLO_VEHICLE_MODEL)
print(f"Model: {info['path']}")
print(f"Type: {info['type']}")
print(f"Size: {info['size_mb']} MB")
```

---

## 🎯 Summary

✅ **4 Model Types:**
- Vehicle (v10m/11s)
- License Plate
- OCR
- Traffic Light

✅ **3 Formats per Model:**
- .engine (fastest)
- .onnx (fast)
- .pt (slowest)

✅ **Auto-Loading:**
- Priority: engine > onnx > pt
- Fallback: CPU if no GPU

✅ **Vehicle Options:**
- v10m: Accuracy (default)
- 11s: Speed

**Total Models:** 12 files (4 types × 3 formats)  
**All Located:** `traffic-server/models/`  
**Total Size:** ~200 MB

