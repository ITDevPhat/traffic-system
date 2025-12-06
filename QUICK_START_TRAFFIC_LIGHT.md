# TRAFFIC LIGHT SYSTEM - QUICK START GUIDE

## 🚀 How to Use the Traffic Light System

### Step 1: Start Main Detection Pipeline

**Frontend:**
```javascript
// Connect to main detection WebSocket with camera_id
const ws = new WebSocket(
  'ws://localhost:8000/api/detection/realtime?' +
  'source=/videos/video4.mp4&' +
  'camera_id=cam01&' +  // ⚠️ IMPORTANT: Set camera_id
  'enable_tracking=true'
);
```

**Or via URL:**
```
http://localhost:3000/detection/cameras/cam01?video=/videos/video4.mp4
```

### Step 2: Configure Traffic Light ROI

**API Call:**
```bash
curl -X POST "http://localhost:8000/api/traffic-light/roi" \
  -H "Content-Type: application/json" \
  -d '{
    "camera_id": "cam01",
    "roi": {
      "x": 0.1,
      "y": 0.1,
      "width": 0.2,
      "height": 0.3
    }
  }'
```

**Response:**
```json
{
  "ok": true,
  "status": "ok",
  "worker_id": "cam01_tl_worker",
  "message": "Traffic light ROI saved"
}
```

### Step 3: (Optional) Configure Stopline for Violations

```bash
curl -X POST "http://localhost:8000/api/traffic-light/stopline" \
  -H "Content-Type: application/json" \
  -d '{
    "camera_id": "cam01",
    "stopline": {
      "x1": 0.0,
      "y1": 0.6,
      "x2": 1.0,
      "y2": 0.6
    }
  }'
```

### Step 4: Connect to Traffic Light WebSocket

```javascript
const tlWs = new WebSocket(
  'ws://localhost:8000/api/traffic-light/realtime?camera_id=cam01'
);

tlWs.onmessage = (event) => {
  const data = JSON.parse(event.data);
  
  if (data.type === 'traffic_light_update') {
    console.log('TL State:', data.traffic_light.state);
    console.log('Confidence:', data.traffic_light.confidence);
    console.log('Violations:', data.violations);
    
    // Display ROI frame
    if (data.roi_frame) {
      const img = new Image();
      img.src = 'data:image/jpeg;base64,' + data.roi_frame;
      document.getElementById('tl-roi').appendChild(img);
    }
  }
};
```

---

## 📊 WebSocket Message Format

### Traffic Light Update Message

```json
{
  "type": "traffic_light_update",
  "camera_id": "cam01",
  "frame_index": 1234,
  "traffic_light": {
    "state": "RED",           // RED | GREEN | YELLOW | UNKNOWN
    "confidence": 0.85
  },
  "roi_frame": "base64_jpeg_data...",
  "violations": [
    {
      "track_id": 42,
      "violation_type": "red_light",
      "timestamp": 1234567890.123,
      "bbox": [100, 200, 300, 400],
      "penetration_ratio": 0.65,
      "depth": 50.0,
      "stopline_y": 500,
      "class_name": "car",
      "confidence": 0.85
    }
  ],
  "timestamp": "2025-12-06T10:30:45.123456"
}
```

---

## 🎨 Frontend Integration Example

```javascript
// TrafficLightMonitor.jsx
import { useEffect, useState } from 'react';

export function TrafficLightMonitor({ cameraId }) {
  const [tlState, setTlState] = useState('UNKNOWN');
  const [violations, setViolations] = useState([]);
  const [roiFrame, setRoiFrame] = useState(null);

  useEffect(() => {
    const ws = new WebSocket(
      `ws://localhost:8000/api/traffic-light/realtime?camera_id=${cameraId}`
    );

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      
      if (data.type === 'traffic_light_update') {
        setTlState(data.traffic_light.state);
        setViolations(data.violations);
        
        if (data.roi_frame) {
          setRoiFrame(`data:image/jpeg;base64,${data.roi_frame}`);
        }
      }
    };

    return () => ws.close();
  }, [cameraId]);

  return (
    <div className="traffic-light-monitor">
      {/* Traffic Light Indicator */}
      <div className={`light-indicator ${tlState.toLowerCase()}`}>
        <div className="light-bulb" />
        <span>{tlState}</span>
      </div>

      {/* ROI Frame */}
      {roiFrame && (
        <img src={roiFrame} alt="Traffic Light ROI" />
      )}

      {/* Violations */}
      {violations.length > 0 && (
        <div className="violations-alert">
          <h4>🚨 Red Light Violations</h4>
          {violations.map((v, i) => (
            <div key={i} className="violation-item">
              Track #{v.track_id} - {v.class_name} - 
              Penetration: {(v.penetration_ratio * 100).toFixed(0)}%
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
```

---

## 🎯 ROI Configuration Tips

### Traffic Light ROI (ROI A)

**Purpose:** Crop region containing traffic light

**Recommended Size:**
- Width: 10-20% of frame
- Height: 15-30% of frame
- Position: Where traffic light is visible

**Example:**
```json
{
  "x": 0.1,      // 10% from left
  "y": 0.1,      // 10% from top
  "width": 0.15, // 15% of frame width
  "height": 0.25 // 25% of frame height
}
```

### Stopline ROI

**Purpose:** Horizontal line where vehicles should stop

**Recommended:**
- Full width: `x1=0.0, x2=1.0`
- Y position: Where stopline is on road
- Thin line: `y1 ≈ y2` (same or 1-2 pixels apart)

**Example:**
```json
{
  "x1": 0.0,   // Left edge
  "y1": 0.6,   // 60% from top
  "x2": 1.0,   // Right edge
  "y2": 0.6    // Same Y (horizontal line)
}
```

---

## 🔧 Violation Detection Parameters

### Penetration Ratio

**Formula:**
```
penetration_ratio = depth / bbox_width
depth = bbox_bottom_y - stopline_y
```

**Default Threshold:** 0.5 (50% of vehicle width)

**Meaning:**
- 0.5 = Vehicle crossed line by 50% of its width
- 1.0 = Vehicle fully crossed line
- 0.2 = Only front bumper crossed

**Adjust Threshold:**
```python
# In traffic_light_worker.py
worker = TrafficLightWorker(
    camera_id="cam01",
    violation_threshold=0.3  # More sensitive (30%)
)
```

---

## 📝 API Endpoints

### Traffic Light ROI

```bash
# Set ROI
POST /api/traffic-light/roi
Body: {
  "camera_id": "cam01",
  "roi": { "x": 0.1, "y": 0.1, "width": 0.2, "height": 0.3 }
}

# Get ROI
GET /api/traffic-light/roi/cam01

# Stop Detection
POST /api/traffic-light/stop
Body: { "camera_id": "cam01" }
```

### WebSocket

```bash
# Traffic Light Stream
WS /api/traffic-light/realtime?camera_id=cam01
```

---

## 🐛 Common Issues

### Issue: "No worker found"

**Cause:** TL worker not created

**Fix:**
```bash
# Create worker by setting ROI
POST /api/traffic-light/roi
```

### Issue: No TL detections

**Cause:** ROI not configured or wrong position

**Fix:**
1. Check ROI covers traffic light
2. Adjust ROI position
3. Check YOLO-TL model is loaded

### Issue: No violations detected

**Cause:** Stopline not configured

**Fix:**
```bash
# Set stopline
POST /api/traffic-light/stopline
```

### Issue: Track IDs not showing

**Status:** ✅ Already implemented

Track IDs show as `[42]` in detection labels.

If not visible:
1. Enable tracking: `enable_tracking=true`
2. Check detections are being sent
3. Verify ByteTrack is working

---

## 🎉 Success Checklist

- [ ] Main pipeline running with `camera_id`
- [ ] TL ROI configured
- [ ] TL worker created (check logs)
- [ ] TL WebSocket connected
- [ ] Receiving TL state updates
- [ ] ROI frame visible
- [ ] Stopline configured (optional)
- [ ] Violations detected (if applicable)
- [ ] Track IDs visible on detections

---

**Quick Start Guide**  
**Version:** 1.0  
**Date:** December 6, 2025
