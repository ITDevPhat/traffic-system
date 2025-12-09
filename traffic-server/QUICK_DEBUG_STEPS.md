# Quick Debug Steps - Tại sao không bắt được vi phạm?

## Bước 1: Restart Server với Log Debug

```bash
cd traffic-server
python -m uvicorn app.main:app --reload --port 8000
```

## Bước 2: Load Video và Quan Sát Log

Khi load video3.mp4 cho cam01, tìm các log sau:

### A. Config Loaded?
```
[TL ROI] camera=cam01, roi={...}
[STOPLINE] camera=cam01, stopline={'x1': 59, 'y1': 293, 'x2': 782, 'y2': 276}
[VIOLATION REGION] camera=cam01, points=6
```

✅ **Nếu thấy**: Config đã load OK
❌ **Nếu không thấy**: File config không tồn tại hoặc bị lỗi

### B. Traffic Light State?
```
[DEBUG VIOLATION] cam=cam01, tl_state=RED, tracks=3, sample_track={...}
```

✅ **Nếu `tl_state=RED`**: Đèn đỏ được detect đúng
❌ **Nếu `tl_state=GREEN`**: Đèn không được detect, cần điều chỉnh ROI

### C. Tracks Inside Violation Region?
```
[TRACK-DEBUG] cam=cam01, track=315, bbox=[100, 200, 300, 400], front_point=(200, 200), inside_region=True, light=RED
```

✅ **Nếu `inside_region=True`**: Xe đã vào violation region
❌ **Nếu `inside_region=False`**: Xe chưa vào region, cần vẽ lại region

### D. Violation Detected?
```
[DEBUG RED] cam=cam01, track=315, inside_region=True, overlap=0.55, ...
🚨 RED LIGHT VIOLATION — camera=cam01, track=315, type=RED_LIGHT_RUN
🚨 1 violations detected for camera cam01
```

✅ **Nếu thấy**: Vi phạm đã được detect
❌ **Nếu không thấy**: Kiểm tra overlap ratio

### E. Violation Result Summary?
```
[VIOLATION-RESULT] cam=cam01, light=RED, tracks=3, violations=1
```

✅ **Nếu `violations=1`**: Vi phạm đã được tạo
❌ **Nếu `violations=0`**: Không có vi phạm nào được tạo

## Bước 3: Phân Tích Vấn Đề

### Vấn đề 1: Config không load
**Triệu chứng**: Không thấy log `[STOPLINE]` hoặc `[VIOLATION REGION]`

**Giải pháp**:
```bash
# Kiểm tra file tồn tại
ls traffic-server/app/data/traffic_light/cam01.json

# Xem nội dung
cat traffic-server/app/data/traffic_light/cam01.json
```

### Vấn đề 2: Traffic light luôn GREEN
**Triệu chứng**: Log `tl_state=GREEN` khi đèn đỏ

**Giải pháp**:
1. Kiểm tra `traffic_light_roi` có đúng vị trí đèn không
2. Đèn có đủ sáng để detect không
3. Thử điều chỉnh threshold trong `detect_traffic_light_state()`

### Vấn đề 3: Tracks không vào violation region
**Triệu chứng**: Log `inside_region=False` cho tất cả tracks

**Giải pháp**:
1. Violation region có bao phủ khu vực xe chạy không?
2. Coordinates có đúng không? (pixel vs normalized)
3. Vẽ lại region bằng frontend tool

### Vấn đề 4: Overlap < 0.4
**Triệu chứng**: Thấy `[DEBUG RED] overlap=0.25` nhưng không có vi phạm

**Giải pháp**:
- Đợi xe vượt hẳn vạch (overlap >= 0.4)
- Hoặc giảm threshold trong code:
  ```python
  # Trong red_light_engine.py, dòng ~397
  if overlap_ratio >= 0.4:  # Thử giảm xuống 0.3
  ```

### Vấn đề 5: Stopline coordinates sai
**Triệu chứng**: Xe đã vượt vạch nhưng `inside_region=False`

**Giải pháp**:
Kiểm tra stopline trong config:
```json
{
  "stopline": {
    "x1": 59,    // Tọa độ pixel, không phải normalized
    "y1": 293,
    "x2": 782,
    "y2": 276
  }
}
```

Đảm bảo:
- Coordinates dùng pixel (không phải 0-1)
- y1, y2 là vị trí ngang của vạch
- Vạch nằm TRƯỚC violation region

## Bước 4: Test Lại

Sau khi sửa config:
1. Restart server
2. Clear browser cache
3. Load lại video
4. Quan sát log mới

## Expected Log Flow (Khi Hoạt Động Đúng)

```
[TL ROI] camera=cam01, roi={...}
[STOPLINE] camera=cam01, stopline={...}
[VIOLATION REGION] camera=cam01, points=6
...
🔴 Light turned RED at 2025-12-09T...
[DEBUG VIOLATION] cam=cam01, tl_state=RED, tracks=3, sample_track={...}
[TRACK-DEBUG] cam=cam01, track=315, bbox=[...], front_point=(...), inside_region=True, light=RED
[DEBUG RED] cam=cam01, track=315, inside_region=True, overlap=0.55, ...
🚨 RED LIGHT VIOLATION — camera=cam01, track=315, type=RED_LIGHT_RUN
🚨 1 violations detected for camera cam01
[VIOLATION-RESULT] cam=cam01, light=RED, tracks=3, violations=1
[TL-VIOLATION-DB] ✅ Saved: camera=cam01, type=RED_LIGHT_RUN, frame=4028, plate=None, bbox=(...)
```

## Nếu Vẫn Không Được

Gửi log đầy đủ từ khi start server đến khi xe vượt đèn đỏ, bao gồm:
- Log `[STOPLINE]`
- Log `[VIOLATION REGION]`
- Log `[DEBUG VIOLATION]`
- Log `[TRACK-DEBUG]`
- Log `[VIOLATION-RESULT]`

Điều này sẽ giúp xác định chính xác vấn đề ở đâu.
