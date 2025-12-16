# 🚨 Tính năng Tự động Tạo Vi phạm cho Video8.mp4

## 📋 Tổng quan

Tính năng này tự động tạo vi phạm với hình ảnh có sẵn khi phát hiện vi phạm vượt đèn đỏ từ video8.mp4.

## 🎯 Chức năng

### Khi phát hiện vi phạm từ video8.mp4:
- **CAR_RED_LIGHT** → Tự động upload:
  - 🖼️ Biển số: `plate_car_red_line.png`
  - 📸 Bằng chứng: `main_car_red_light.png`

- **BIKE_RED_LIGHT** → Tự động upload:
  - 🖼️ Biển số: `plate_bike_red_line.png`
  - 📸 Bằng chứng: `bike_red_light.png`

### Kết quả:
- ✅ Vi phạm được tạo trong database
- 📁 Hình ảnh được copy vào `/static/violations/{violation_id}/`
- 🔗 URL hình ảnh được lưu trong violation record
- 📱 Thông báo realtime trên giao diện
- 📋 Hiển thị trong trang quản lý vi phạm

## 🚀 Cách sử dụng

### 1. Khởi động hệ thống
```bash
# Backend
cd traffic-server
uvicorn app.main:app --reload --port 8000

# Frontend
npm run dev
```

### 2. Truy cập trang phát hiện
```
http://localhost:3000/detection/traffic-light
```

### 3. Load video8.mp4
- **Cách 1:** Upload video8.mp4 từ giao diện
- **Cách 2:** Truy cập trực tiếp:
  ```
  http://localhost:3000/detection/traffic-light?video=video8.mp4
  ```

### 4. Bắt đầu phát hiện
- Click "Start Detection"
- Hệ thống sẽ tự động load ROI, stopline và violation region
- Khi phát hiện vi phạm → Tự động tạo violation với hình ảnh

### 5. Xem kết quả
- **Thông báo realtime:** Popup notification ở góc phải màn hình
- **Trang quản lý:** `http://localhost:3000/violations/management`

## 🔧 API Endpoints

### Tạo vi phạm tự động
```http
POST /api/violations/auto-create-video8
Content-Type: application/json

{
  "violation_type": "CAR_RED_LIGHT",  // hoặc "BIKE_RED_LIGHT"
  "track_id": 123,
  "frame": 1500,
  "confidence": 0.85,
  "plate": "30A-12345"
}
```

### Response
```json
{
  "ok": true,
  "message": "Auto-created CAR_RED_LIGHT violation successfully",
  "violation_id": 42,
  "track_id": 123,
  "violation_type": "CAR_RED_LIGHT",
  "images": {
    "plate": "/static/violations/42/plate_abc123.png",
    "evidence": "/static/violations/42/evidence_def456.png"
  },
  "video_job_id": 5
}
```

## 📁 Cấu trúc File

### Hình ảnh nguồn
```
traffic-server/app/static/violations/
├── bike_red_light.png          # Bằng chứng xe máy
├── main_car_red_light.png      # Bằng chứng ô tô
├── plate_bike_red_line.png     # Biển số xe máy
└── plate_car_red_line.png      # Biển số ô tô
```

### Hình ảnh đích (sau khi tạo vi phạm)
```
traffic-server/app/static/violations/{violation_id}/
├── plate_{uuid}.png            # Biển số (copy từ nguồn)
└── evidence_{uuid}.png         # Bằng chứng (copy từ nguồn)
```

## 🎨 Giao diện

### Notification Component
- 📍 Vị trí: Góc phải màn hình
- ⏰ Thời gian: Tự động ẩn sau 10 giây
- 🔗 Nút: "Xem danh sách" và "Chi tiết"

### Trang quản lý vi phạm
- 📋 Danh sách: Hiển thị tất cả vi phạm
- 🔍 Filter: Theo trạng thái, biển số
- 👁️ Chi tiết: Xem hình ảnh và thông tin đầy đủ

## 🧪 Test

### Chạy test script
```bash
python test_auto_violation.py
```

### Test thủ công
```bash
# Test CAR_RED_LIGHT
curl -X POST http://localhost:8000/api/violations/auto-create-video8 \
  -H "Content-Type: application/json" \
  -d '{"violation_type":"CAR_RED_LIGHT","track_id":123,"frame":1500}'

# Test BIKE_RED_LIGHT  
curl -X POST http://localhost:8000/api/violations/auto-create-video8 \
  -H "Content-Type: application/json" \
  -d '{"violation_type":"BIKE_RED_LIGHT","track_id":456,"frame":2000}'
```

## 🔍 Debug

### Console logs
```javascript
// Khi phát hiện vi phạm
🚨 VIOLATION CONFIRMED: Track 123 type=CAR_RED_LIGHT

// Khi tạo tự động
🤖 Auto-creating violation: CAR_RED_LIGHT for track 123
✅ Auto-created violation ID: 42
📸 Images: plate=/static/violations/42/plate_abc.png, evidence=/static/violations/42/evidence_def.png
```

### Backend logs
```python
# API call
POST /api/violations/auto-create-video8 - 200 OK

# File operations
✅ Copied plate_car_red_line.png → /static/violations/42/plate_abc123.png
✅ Copied main_car_red_light.png → /static/violations/42/evidence_def456.png
```

## ⚠️ Lưu ý

1. **Chỉ áp dụng cho video8.mp4** - Tính năng chỉ hoạt động khi source chứa "video8"
2. **Không tạo trùng lặp** - Mỗi track_id + violation_type chỉ tạo 1 lần
3. **Reset khi đổi video** - Khi load video khác, danh sách auto-created sẽ được reset
4. **Cần hình ảnh nguồn** - Đảm bảo 4 file PNG có trong `/static/violations/`

## 🎉 Kết quả mong đợi

Khi chạy video8.mp4 và phát hiện vi phạm:
- ✅ Notification popup hiển thị ngay lập tức
- ✅ Vi phạm xuất hiện trong trang management
- ✅ Hình ảnh được upload và hiển thị đúng
- ✅ Console logs chi tiết quá trình
- ✅ Toast notification xác nhận thành công

## 📞 Hỗ trợ

Nếu gặp vấn đề:
1. Kiểm tra backend chạy trên port 8000
2. Kiểm tra 4 file PNG có trong `/static/violations/`
3. Xem console logs để debug
4. Kiểm tra network tab trong DevTools