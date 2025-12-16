# Video8.mp4 Traffic Light Detection Fix

## Vấn đề đã sửa

### 1. **Auto-load Configuration cho Video8.mp4**
- ✅ Thêm logic auto-detect video8.mp4 trong traffic-light page
- ✅ Auto-load Traffic Light ROI: `(935, 109, 147, 87)`
- ✅ Auto-load Stopline: `(146, 885) → (1306, 879)`
- ✅ Auto-save ROI vào backend khi load video

### 2. **Camera ID Mapping**
- ✅ Cập nhật `resolveCameraId()` để map video8.mp4 → cam03
- ✅ Đảm bảo backend load đúng config cam03.json

### 3. **Console Logging cho Debug**
- ✅ Thêm console.log cho Traffic Light ROI coordinates
- ✅ Thêm console.log cho Stopline coordinates và midpoint
- ✅ Thêm console.log cho Violation Region polygon points
- ✅ Thêm logging cho việc save/load từ backend

### 4. **Backend Configuration**
- ✅ Cập nhật `cam03.json` với coordinates chính xác
- ✅ Traffic Light ROI: `x: 935, y: 109, width: 147, height: 87`
- ✅ Stopline: `(146, 885) → (1306, 879)`
- ✅ Violation Region: 5-point polygon từ backend response

### 5. **Violation Region Auto-load**
- ✅ Auto-load violation region cho video8.mp4
- ✅ Points: `[(16,796), (59,624), (216,482), (1283,450), (1414,799)]`
- ✅ Console log tất cả points và midpoint

## Cách sử dụng

1. **Khởi động servers:**
   ```bash
   # Backend (port 8000)
   python start_server.py
   
   # Frontend (port 3001)
   npm run dev
   ```

2. **Truy cập trang:**
   ```
   http://localhost:3001/detection/traffic-light
   ```

3. **Load video8.mp4:**
   - Upload video8.mp4 hoặc
   - Truy cập trực tiếp: `http://localhost:3001/detection/traffic-light?video=video8.mp4`

## Console Output mong đợi

Khi load video8.mp4, bạn sẽ thấy:

```
🎬 Video8.mp4 detected - Loading cam03 config...
🚦 Traffic Light ROI: {x: 935, y: 109, w: 147, h: 87}
🛑 Stopline: {x1: 146, y1: 885, x2: 1306, y2: 879}
📍 Stopline Midpoint: {x: 726, y: 882}
✅ TL ROI auto-saved for video8.mp4
```

Khi auto-load Violation Region:
```
🚧 Violation Region (Polygon) auto-loaded:
  Point 1: (16, 796)
  Point 2: (59, 624)
  Point 3: (216, 482)
  Point 4: (1283, 450)
  Point 5: (1414, 799)
📍 Violation Region Midpoint: (597, 630)
```

## Kiểm tra việc lưu

Tất cả operations save sẽ có detailed logging:
- 💾 Saving to backend...
- 📤 Camera ID: cam03
- 📤 Coordinates/Points payload
- 📥 Response status
- ✅ Success hoặc ❌ Error messages

## Files đã sửa

1. `src/app/(admin)/detection/traffic-light/page.jsx`
   - Thêm auto-load logic cho video8.mp4
   - Cập nhật resolveCameraId mapping
   - Thêm console.log cho tất cả coordinates
   - Thêm detailed logging cho save operations

2. `traffic-server/app/data/traffic_light/cam03.json`
   - Cập nhật với coordinates chính xác cho video8.mp4
   - Traffic Light ROI: (935, 109, 147, 87)
   - Stopline: (146, 885) → (1306, 879)
   - Violation Region: 5-point polygon từ backend response

## Status

✅ **HOÀN THÀNH** - Video8.mp4 giờ đây sẽ:
- Auto-load đúng ROI, Stopline và Violation Region
- Map với cam03 config
- Console.log tất cả coordinates và midpoints
- Save thành công vào backend
- Hiển thị detailed logging cho debug
- Violation region 5-point polygon được auto-load từ backend response