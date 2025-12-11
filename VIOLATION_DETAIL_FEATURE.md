# Tính Năng Xem Chi Tiết Vi Phạm

## Mô tả
Đã tạo giao diện xem chi tiết vi phạm chuyên nghiệp giống biên bản xử phạt với khả năng chỉnh sửa thông tin và hiển thị bounding box trên hình ảnh bằng chứng.

## Tính năng chính

### 1. Giao diện biên bản xử phạt chuyên nghiệp
- **Header chính thức**: "HỆ THỐNG GIÁM SÁT TRẬT TỰ GIAO THÔNG, ĐƯỜNG BỘ BẰNG HÌNH ẢNH"
- **Thông tin đầy đủ**: Hành vi vi phạm, thời gian, địa điểm, biển số xe, đơn vị vận hành
- **Màu sắc phù hợp**: Đỏ cho header, các badge màu theo mức độ nghiêm trọng

### 2. Hiển thị hình ảnh bằng chứng với bounding box
- **Hình ảnh toàn cảnh**: Hiển thị hình ảnh vi phạm với kích thước phù hợp
- **Bounding box màu sắc**: 
  - Xanh dương: Phương tiện (vehicle)
  - Cam: Biển số (plate) 
  - Đỏ: Vi phạm (violation)
  - Xanh lá: Các đối tượng khác
- **Label thông tin**: Hiển thị tên đối tượng và độ tin cậy

### 3. Khả năng chỉnh sửa thông tin
- **Chế độ chỉnh sửa**: Nút "✏️ Chỉnh sửa" để bật/tắt chế độ edit
- **Các trường có thể chỉnh sửa**:
  - Mã vi phạm (violation_type_code)
  - Thời gian vi phạm (timestamp)
  - Hướng/Chiều (roi_type)
  - Biển số xe (plate)
  - Trạng thái xác minh (verification_status)
- **Lưu/Hủy**: Nút "💾 Lưu" và "❌ Hủy" khi đang chỉnh sửa

### 4. Thông tin kỹ thuật chi tiết
- **Metadata**: ID vi phạm, Video Job ID, Frame, Camera
- **Thời gian**: Thời gian tạo và xác minh
- **Mức phạt**: Hiển thị số tiền phạt theo loại vi phạm

## Cấu trúc URL
```
http://localhost:3000/violations/management/[id]
```
Ví dụ: `http://localhost:3000/violations/management/1`

## API Backend

### Endpoint chi tiết vi phạm
```
GET /api/violations/{violation_id}
```

**Response format:**
```json
{
  "violation_id": 1,
  "video_job_id": 1,
  "violation_type_code": "RED_LIGHT",
  "timestamp": "2024-12-11T08:30:15",
  "plate": "51A-12345",
  "confidence": 0.95,
  "verification_status": "verified",
  "evidence_img": "/evidence/violation_1.jpg",
  
  "violation_type": {
    "description": "Vượt đèn đỏ",
    "fine_amount": 1000000,
    "severity": "high"
  },
  
  "camera": {
    "name": "CAM_Q7_01",
    "model": "Hikvision DS-2CD2085FWD"
  },
  
  "location": {
    "name": "Nguyễn Văn Linh - 3/2",
    "address": "Quận 7, TP.HCM"
  },
  
  "bboxes": [
    {
      "x1": 100, "y1": 150, "x2": 300, "y2": 350,
      "label": "vehicle", "confidence": 0.95
    },
    {
      "x1": 120, "y1": 180, "x2": 180, "y2": 220,
      "label": "plate", "confidence": 0.88
    }
  ]
}
```

### Endpoint cập nhật vi phạm
```
PUT /api/violations/{violation_id}
```

## Dữ liệu mẫu
Đã tạo file `traffic-server/add_sample_violations.sql` với:
- 8 loại vi phạm phổ biến
- 8 vi phạm mẫu với thông tin đầy đủ
- Bounding boxes cho từng vi phạm

## Cách sử dụng

### 1. Thêm dữ liệu mẫu (nếu cần)
```bash
# Chạy trong PostgreSQL
psql -d your_database -f traffic-server/add_sample_violations.sql
```

### 2. Khởi động backend
```bash
cd traffic-server
python -m uvicorn app.main:app --reload --port 8000
```

### 3. Khởi động frontend
```bash
npm run dev
# hoặc
yarn dev
```

### 4. Truy cập trang quản lý vi phạm
1. Vào `http://localhost:3000/violations/management`
2. Nhấn nút "Chi tiết" hoặc "Xem chi tiết" ở cột "Bằng chứng"
3. Xem thông tin chi tiết vi phạm
4. Nhấn "✏️ Chỉnh sửa" để chỉnh sửa thông tin
5. Nhấn "💾 Lưu" để lưu thay đổi

## Tính năng nổi bật

### Giao diện chuyên nghiệp
- Thiết kế giống biên bản xử phạt thực tế
- Màu sắc và typography phù hợp với tính chất nghiêm túc
- Layout responsive, hoạt động tốt trên mọi thiết bị

### Hiển thị bằng chứng trực quan
- Hình ảnh bằng chứng với bounding box overlay
- Màu sắc phân biệt các loại đối tượng
- Thông tin chi tiết về độ tin cậy

### Khả năng chỉnh sửa linh hoạt
- Chỉnh sửa trực tiếp trên giao diện
- Validation dữ liệu phù hợp
- Lưu thay đổi real-time qua API

### Thông tin đầy đủ
- Tất cả thông tin cần thiết cho biên bản xử phạt
- Metadata kỹ thuật cho việc audit
- Liên kết với camera và địa điểm

## Lưu ý kỹ thuật
- Sử dụng Canvas API để vẽ bounding box
- Responsive design với Bootstrap
- TypeScript cho type safety
- Error handling đầy đủ
- Loading states cho UX tốt hơn