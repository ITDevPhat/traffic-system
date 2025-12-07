# 🧠 Module Quản Lý Mô Hình AI

Module CRUD hoàn chỉnh để quản lý các mô hình AI (YOLO, OCR, Traffic Light, ...) trong hệ thống phát hiện vi phạm giao thông.

## 🎯 Tính năng

### Frontend (Next.js + TypeScript)
- ✅ **Danh sách mô hình** (`/models`)
  - Hiển thị table với đầy đủ thông tin
  - Filter theo loại mô hình
  - Nút Edit/Delete cho từng item
  - Nút thêm mới
  - Nút làm mới dữ liệu
  - Delete chỉ ẩn item trên UI (không xóa DB)

- ✅ **Thêm mô hình** (`/models/create`)
  - Form validation đầy đủ với Yup
  - Các trường: tên, loại, đường dẫn, phiên bản, framework, confidence, mô tả
  - Toast notification khi thành công/thất bại
  - Redirect về danh sách sau khi tạo

- ✅ **Chỉnh sửa mô hình** (`/models/edit/[id]`)
  - Load dữ liệu hiện tại
  - Form validation
  - Toast notification
  - Redirect về danh sách sau khi cập nhật

### Backend (FastAPI + PostgreSQL)
- ✅ **GET /api/models** - Lấy danh sách (có filter theo loại)
- ✅ **GET /api/models/{id}** - Lấy chi tiết
- ✅ **POST /api/models** - Tạo mới
- ✅ **PUT /api/models/{id}** - Cập nhật
- ✅ **DELETE /api/models/{id}** - Xóa (có kiểm tra ràng buộc)

## 📁 Cấu trúc file

### Frontend
```
src/
├── app/(admin)/models/
│   ├── page.tsx                    # Danh sách mô hình
│   ├── create/
│   │   └── page.tsx                # Form thêm mới
│   └── edit/[id]/
│       └── page.tsx                # Form chỉnh sửa
└── services/
    └── modelsApi.ts                # API client
```

### Backend
```
traffic-server/app/
├── models/
│   └── model.py                    # SQLModel cho models
└── routers/
    └── models.py                   # API endpoints
```

## 🚀 Cách sử dụng

### 1. Khởi động Backend

```bash
cd traffic-server
uvicorn app.main:app --reload --port 8000
```

API docs: http://localhost:8000/docs

### 2. Khởi động Frontend

```bash
npm run dev
# hoặc
yarn dev
```

Frontend: http://localhost:3000

### 3. Truy cập module

Vào menu sidebar → **Quản lý mô hình AI** hoặc truy cập trực tiếp:
- Danh sách: http://localhost:3000/models
- Thêm mới: http://localhost:3000/models/create

## 🔧 API Endpoints

### GET /api/models
Lấy danh sách mô hình AI

**Query Parameters:**
- `skip` (optional): Số record bỏ qua
- `limit` (optional): Số record tối đa
- `model_type` (optional): Lọc theo loại (vehicle, plate, ocr, traffic_light, violation)

**Response:**
```json
[
  {
    "model_id": 1,
    "name": "yolo_vehicle_11s",
    "model_type": "vehicle",
    "file_path": "models/vehicle/yolo_vehicle_11s.pt",
    "version": "11s",
    "framework": "YOLOv11s",
    "confidence_threshold": 0.5,
    "description": "Phát hiện phương tiện - phiên bản nhẹ",
    "created_at": "2025-01-01T00:00:00"
  }
]
```

### GET /api/models/{id}
Lấy chi tiết một mô hình

**Response:**
```json
{
  "model_id": 1,
  "name": "yolo_vehicle_11s",
  "model_type": "vehicle",
  "file_path": "models/vehicle/yolo_vehicle_11s.pt",
  "version": "11s",
  "framework": "YOLOv11s",
  "confidence_threshold": 0.5,
  "description": "Phát hiện phương tiện - phiên bản nhẹ",
  "created_at": "2025-01-01T00:00:00"
}
```

### POST /api/models
Tạo mô hình mới

**Request Body:**
```json
{
  "name": "yolo_vehicle_11s",
  "model_type": "vehicle",
  "file_path": "models/vehicle/yolo_vehicle_11s.pt",
  "version": "11s",
  "framework": "YOLOv11s",
  "confidence_threshold": 0.5,
  "description": "Phát hiện phương tiện - phiên bản nhẹ"
}
```

**Response:** Trả về object vừa tạo

### PUT /api/models/{id}
Cập nhật mô hình

**Request Body:**
```json
{
  "name": "yolo_vehicle_11s_updated",
  "model_type": "vehicle",
  "file_path": "models/vehicle/yolo_vehicle_11s.pt",
  "version": "11s",
  "framework": "YOLOv11s",
  "confidence_threshold": 0.6,
  "description": "Mô tả mới"
}
```

**Response:** Trả về object sau khi cập nhật

### DELETE /api/models/{id}
Xóa mô hình

**Note:** Sẽ báo lỗi nếu có vi phạm đang tham chiếu đến mô hình này

## 🎨 UI Components sử dụng

- `TextFormInput` - Input text với validation
- `TextAreaFormInput` - Textarea với validation
- `SelectFormInput` - Dropdown select với react-select
- `PageTitle` - Tiêu đề trang
- `Card`, `Table`, `Button`, `Badge`, `Form` - React Bootstrap components

## ✅ Validation

### Frontend (Yup Schema)
- `name`: Bắt buộc
- `model_type`: Bắt buộc, phải là một trong: vehicle, plate, ocr, traffic_light, violation
- `file_path`: Bắt buộc
- `version`: Bắt buộc
- `framework`: Bắt buộc
- `confidence_threshold`: Bắt buộc, phải là số từ 0 đến 1
- `description`: Tùy chọn

### Backend
- Kiểm tra model_type hợp lệ
- Kiểm tra confidence_threshold trong khoảng [0, 1]
- Kiểm tra ràng buộc khi xóa (không cho xóa nếu có vi phạm đang dùng)

## 🔐 Database Schema

```sql
CREATE TABLE models (
    model_id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    model_type TEXT NOT NULL,                -- vehicle | plate | ocr | traffic_light | violation
    file_path TEXT NOT NULL,
    version VARCHAR(50) DEFAULT '1.0',
    framework VARCHAR(50) DEFAULT 'YOLO',
    confidence_threshold FLOAT DEFAULT 0.5,
    description TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);
```

## 📊 Loại mô hình

| Loại | Mô tả | Badge Color |
|------|-------|-------------|
| `vehicle` | Phát hiện phương tiện | Primary (xanh dương) |
| `plate` | Nhận dạng biển số | Success (xanh lá) |
| `ocr` | Nhận diện ký tự OCR | Info (xanh nhạt) |
| `traffic_light` | Phát hiện đèn giao thông | Warning (vàng) |
| `violation` | Phát hiện vi phạm | Danger (đỏ) |

## 📝 Notes

- **Delete UI-only**: Nút Delete trên danh sách chỉ ẩn item khỏi UI, không gọi API DELETE
- **Filter by type**: Có thể lọc danh sách theo loại mô hình
- **Toast notifications**: Sử dụng react-toastify cho thông báo
- **Form validation**: Sử dụng react-hook-form + yup resolver
- **Type safety**: Full TypeScript với interfaces rõ ràng
- **Confidence threshold**: Hiển thị dưới dạng phần trăm trong table

## 🐛 Troubleshooting

### Backend không khởi động được
- Kiểm tra PostgreSQL đã chạy chưa
- Kiểm tra connection string trong `.env`
- Chạy lại migration nếu cần

### Frontend không load được dữ liệu
- Kiểm tra backend đã chạy ở port 8000
- Kiểm tra CORS settings
- Kiểm tra biến môi trường `NEXT_PUBLIC_API_URL`

### Lỗi validation
- Đảm bảo model_type là một trong: vehicle, plate, ocr, traffic_light, violation
- Đảm bảo confidence_threshold là số từ 0 đến 1
- Đảm bảo tất cả trường bắt buộc đã được điền

## 🎉 Hoàn thành!

Module đã sẵn sàng sử dụng với đầy đủ chức năng CRUD, validation, error handling, filter và UI đẹp mắt.

## 🔗 Liên quan

- [Module Quản lý Loại Vi Phạm](./VIOLATION_TYPES_MODULE.md)
- Database schema: `traffic-server/db.sql`
