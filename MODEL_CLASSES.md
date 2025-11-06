# 🚗 Model Classes Reference

## Vehicle Detection Model - 4 Classes

### Class Mapping

```python
# YOLO model classes
0: bus      # 🚌 Xe buýt
1: car      # 🚗 Xe hơi
2: bike     # 🏍️ Xe máy
3: truck    # 🚚 Xe tải
```

---

## 🎨 BBox Color Coding

| Class ID | Class Name | Icon | Color | Hex Code | RGB |
|----------|-----------|------|-------|----------|-----|
| **0** | `bus` | 🚌 | 🟠 Orange | `#e67e22` | `rgb(230, 126, 34)` |
| **1** | `car` | 🚗 | 🔵 Blue | `#3498db` | `rgb(52, 152, 219)` |
| **2** | `bike` | 🏍️ | 🟢 Green | `#2ecc71` | `rgb(46, 204, 113)` |
| **3** | `truck` | 🚚 | 🔴 Red | `#e74c3c` | `rgb(231, 76, 60)` |

---

## 📊 Visual Guide

```
┌──────────────────────────────────────────────┐
│  Frame 102 - 4 objects detected              │
│                                              │
│  ┌─────────┐                                 │
│  │ 🟠 bus  │                                 │
│  │  85%    │                                 │
│  └─────────┘                                 │
│                                              │
│      ┌─────────┐  ┌─────────┐               │
│      │ 🔵 car  │  │ 🟢 bike │               │
│      │  92%    │  │  78%    │               │
│      └─────────┘  └─────────┘               │
│                                              │
│                          ┌──────────┐        │
│                          │ 🔴 truck │        │
│                          │   88%    │        │
│                          └──────────┘        │
└──────────────────────────────────────────────┘
```

---

## 🔧 Code Implementation

### Frontend (JavaScript)

```javascript
// src/components/DetectionCardRealtime.jsx

const CLASS_COLORS = {
  bus: '#e67e22',        // 🟠 Orange - Class 0
  car: '#3498db',        // 🔵 Blue - Class 1
  bike: '#2ecc71',       // 🟢 Green - Class 2
  truck: '#e74c3c',      // 🔴 Red - Class 3
  default: '#95a5a6'     // Gray (fallback)
};

// Usage in canvas drawing
const color = CLASS_COLORS[obj.label.toLowerCase()] || CLASS_COLORS.default;
ctx.strokeStyle = color;
ctx.strokeRect(x, y, width, height);
```

### Backend (Python)

```python
# traffic-server/app/modules/yolo.py

# Model automatically returns class names
cls_name = self._models.vehicle.names[cls_id]
# cls_id=0 → cls_name="bus"
# cls_id=1 → cls_name="car"
# cls_id=2 → cls_name="bike"
# cls_id=3 → cls_name="truck"

tracks.append({
    "bbox": (x1, y1, x2, y2),
    "confidence": conf,
    "class": cls_name,  # "bus", "car", "bike", or "truck"
    "track_id": track_id
})
```

---

## 📝 YOLO Model Configuration

### Model File Structure

```
traffic-server/models/vehicle/v10m/
├── yolo_vehicle_v10m.engine    ← TensorRT (fastest)
├── yolo_vehicle_v10m.onnx      ← ONNX Runtime
└── yolo_vehicle_v10m.pt        ← PyTorch (slowest)
```

### Class Names in Model

```python
# Check model classes
from ultralytics import YOLO

model = YOLO('models/vehicle/v10m/yolo_vehicle_v10m.pt')
print(model.names)
# Expected output:
# {0: 'bus', 1: 'car', 2: 'bike', 3: 'truck'}
```

---

## 🎯 Detection Output Format

### WebSocket Message

```json
{
  "type": "detection",
  "frame": 102,
  "objects": [
    {
      "label": "car",
      "conf": 0.92,
      "bbox": [120, 340, 580, 720],
      "track_id": 5
    },
    {
      "label": "bus",
      "conf": 0.85,
      "bbox": [800, 200, 1400, 900],
      "track_id": 12
    },
    {
      "label": "bike",
      "conf": 0.78,
      "bbox": [50, 500, 250, 850],
      "track_id": 3
    },
    {
      "label": "truck",
      "conf": 0.88,
      "bbox": [1200, 300, 1800, 950],
      "track_id": 8
    }
  ]
}
```

---

## 🎨 CSS Styling (Optional)

```css
/* Class-specific badge styles */
.badge-bus {
  background-color: #e67e22 !important; /* Orange */
}

.badge-car {
  background-color: #3498db !important; /* Blue */
}

.badge-bike {
  background-color: #2ecc71 !important; /* Green */
}

.badge-truck {
  background-color: #e74c3c !important; /* Red */
}
```

---

## 📊 Statistics by Class

### Example Output

```
Detection Summary:
├─ 🟠 bus:    12 detections (15%)
├─ 🔵 car:    45 detections (56%)
├─ 🟢 bike:   18 detections (23%)
└─ 🔴 truck:   5 detections (6%)
──────────────────────────────────
Total:        80 detections (100%)
```

---

## 🔍 Validation

### Check Model Classes

```python
# Run this to verify your model classes
import sys
sys.path.append('traffic-server')

from app.utils.model_loader import load_yolo_model

model = load_yolo_model('models/vehicle/v10m/yolo_vehicle_v10m.pt')
print("Model classes:", model.names)
# Expected: {0: 'bus', 1: 'car', 2: 'bike', 3: 'truck'}
```

### Test Detection

```python
import cv2

frame = cv2.imread('test_image.jpg')
results = model.predict(frame, conf=0.5)

for box in results[0].boxes:
    cls_id = int(box.cls[0])
    cls_name = model.names[cls_id]
    print(f"Detected: {cls_name} (class {cls_id})")
```

---

## 📚 Related Files

- **Color Mapping**: `src/components/DetectionCardRealtime.jsx` (line 11-17)
- **Model Config**: `traffic-server/app/core/config.py`
- **YOLO Module**: `traffic-server/app/modules/yolo.py`
- **Model Loader**: `traffic-server/app/utils/model_loader.py`

---

## 🎯 Summary

Your model has **4 vehicle classes** with clear color coding:

| Class | Color | Purpose |
|-------|-------|---------|
| 🟠 **bus** | Orange | Large public transport |
| 🔵 **car** | Blue | Standard passenger vehicle |
| 🟢 **bike** | Green | Motorcycle/motorbike |
| 🔴 **truck** | Red | Heavy vehicle/cargo |

**All detection outputs will use these 4 classes consistently across the entire system!** 🚀

