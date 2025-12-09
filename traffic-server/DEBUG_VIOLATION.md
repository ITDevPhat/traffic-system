# Debug Traffic Light Violation Detection

## Checklist để debug tại sao không bắt được vi phạm

### 1. Kiểm tra Log Server

Khi chạy video, tìm các log sau:

#### A. Stopline Configuration
```
[STOPLINE] camera=cam01, stopline={...}
[VIOLATION REGION] camera=cam01, points=...
```

**Nếu KHÔNG thấy**: Config file không load được hoặc không có stopline
- Kiểm tra file: `traffic-server/app/data/traffic_light/cam01.json`
- Phải có field `stopline` và `violation_region`

#### B. Traffic Light State
```
[DEBUG VIOLATION] cam=cam01, tl_state=RED, tracks=4, sample_track={...}
```

**Kiểm tra `tl_state`**:
- Nếu luôn là `GREEN` → Traffic light detection không hoạt động
- Nếu là `RED` khi xe vượt → OK

#### C. Engine Detection
```
[DEBUG RED] cam=cam01, track=315, inside_region=True, overlap=0.55, ...
🚨 RED LIGHT VIOLATION — camera=cam01, track=315, type=RED_LIGHT_RUN
🚨 1 violations detected for camera cam01
```

**Nếu KHÔNG thấy `[DEBUG RED]`**:
- Xe không nằm trong violation region
- Hoặc stopline không được set

**Nếu thấy `[DEBUG RED]` nhưng overlap < 0.4**:
- Xe chưa đè vạch đủ 40%
- Cần điều chỉnh stopline hoặc đợi xe vượt hẳn

#### D. WebSocket Send
```
[TL-VIOLATION-DB] ✅ Saved: camera=cam01, type=RED_LIGHT_RUN, frame=4028, plate=None, bbox=(...)
```

**Nếu thấy log này**: Vi phạm đã được lưu DB và gửi WebSocket

### 2. Kiểm tra Config File

```bash
cat traffic-server/app/data/traffic_light/cam01.json
```

Phải có cấu trúc:
```json
{
  "traffic_light_roi": {
    "x": 0.1,
    "y": 0.1,
    "width": 0.2,
    "height": 0.3
  },
  "stopline": {
    "x1": 0.3,
    "y1": 0.6,
    "x2": 0.7,
    "y2": 0.65
  },
  "violation_region": {
    "points": [
      [0.2, 0.5],
      [0.8, 0.5],
      [0.8, 0.9],
      [0.2, 0.9]
    ]
  }
}
```

**Nếu thiếu `stopline` hoặc `violation_region`**: Engine không thể detect vi phạm

### 3. Kiểm tra Frontend

Mở DevTools Console, tìm:
```javascript
WebSocket message: {...}
```

Kiểm tra trong message có:
```json
{
  "violations": [
    {
      "track_id": 315,
      "violation_type": "RED_LIGHT_RUN",
      ...
    }
  ],
  "detections": [
    {
      "track_id": 315,
      "violation": "RED_LIGHT_RUN",
      ...
    }
  ]
}
```

**Nếu có `violations` array nhưng frontend không hiển thị**:
- Vấn đề ở frontend rendering
- Kiểm tra component xử lý violation

**Nếu KHÔNG có `violations` array**:
- Backend không gửi vi phạm
- Quay lại kiểm tra log server

### 4. Test Nhanh

Thêm log tạm vào `traffic_light_ws.py` sau dòng 397:

```python
violations = violation_manager.compute_violations(...)

# THÊM LOG DEBUG
logger.warning(f"[VIOLATION-DEBUG] violations={len(violations) if violations else 0}")
if violations:
    for v in violations:
        logger.warning(f"[VIOLATION-DEBUG] {v.track_id} -> {v.violation_type}")
```

Restart server và chạy lại video. Nếu thấy:
```
[VIOLATION-DEBUG] violations=0
```
→ Engine không detect được vi phạm

Nếu thấy:
```
[VIOLATION-DEBUG] violations=1
[VIOLATION-DEBUG] 315 -> RED_LIGHT_RUN
```
→ Engine detect OK, vấn đề ở WebSocket hoặc frontend

### 5. Common Issues

#### Issue 1: Stopline không được set
**Triệu chứng**: Không thấy log `[STOPLINE]` khi start
**Fix**: 
- Tạo/sửa file `traffic-server/app/data/traffic_light/cam01.json`
- Restart server

#### Issue 2: Traffic light luôn GREEN
**Triệu chứng**: Log `[DEBUG VIOLATION] tl_state=GREEN`
**Fix**:
- Kiểm tra ROI có đúng vị trí đèn không
- Đèn có đủ sáng để detect không
- Thử điều chỉnh threshold trong `detect_traffic_light_state()`

#### Issue 3: Xe không trong violation region
**Triệu chứng**: Không thấy log `[DEBUG RED]`
**Fix**:
- Vẽ lại violation region bao phủ khu vực xe chạy
- Đảm bảo region nằm sau stopline

#### Issue 4: Overlap < 0.4
**Triệu chứng**: Thấy `[DEBUG RED] overlap=0.25` nhưng không có vi phạm
**Fix**:
- Đợi xe vượt hẳn vạch (overlap >= 0.4)
- Hoặc giảm threshold trong code (dòng 397: `if overlap_ratio >= 0.4`)

### 6. Quick Test Command

```bash
# Xem log realtime
cd traffic-server
python -m uvicorn app.main:app --reload --port 8000 | grep -E "VIOLATION|RED|STOPLINE"
```

Hoặc trên Windows:
```powershell
# Chạy server và filter log
python -m uvicorn app.main:app --reload --port 8000
# Trong terminal khác, xem log file nếu có
```

### 7. Expected Flow

Khi mọi thứ hoạt động đúng, log sẽ như sau:

```
[TL ROI] camera=cam01, roi={...}
[STOPLINE] camera=cam01, stopline={...}
[VIOLATION REGION] camera=cam01, points=4
...
[DEBUG VIOLATION] cam=cam01, tl_state=RED, tracks=3, sample_track={...}
[DEBUG RED] cam=cam01, track=315, inside_region=True, overlap=0.55, ...
🚨 RED LIGHT VIOLATION — camera=cam01, track=315, type=RED_LIGHT_RUN
🚨 1 violations detected for camera cam01
[TL-PLATE] cam=cam01, track=315, plate=None, conf=None, violation=RED_LIGHT_RUN
[TL-VIOLATION-DB] ✅ Saved: camera=cam01, type=RED_LIGHT_RUN, frame=4028, plate=None, bbox=(...)
```

Frontend sẽ thấy bbox đỏ với label "RED_LIGHT_RUN".
