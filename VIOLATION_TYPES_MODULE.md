# 📋 Module Quản Lý Loại Vi Phạm

Module CRUD hoàn chỉnh để quản lý các loại vi phạm giao thông trong hệ thống.

## 🎯 Tính năng

### Frontend (Next.js + TypeScript)
- ✅ **Danh sách loại vi phạm** (`/violations/types`)
  - Hiển thị table với đầy đủ thông tin
  - Nút Edit/Delete cho từng item
  - Nút thêm mới
  - Nút làm mới dữ liệu
  - Delete chỉ ẩn item trên UI (không xóa DB)

- ✅ **Thêm loại vi phạm** (`/violations/types/create`)
  - Form validation đầy đủ với Yup
  - Các trường: mã, mô tả, mức phạt, mức độ
  - Toast notification khi thành công/thất bại
  - Redirect về danh sách sau khi tạo

- ✅ **Chỉnh sửa loại vi phạm** (`/violations/types/edit/[code]`)
  - Load dữ liệu hiện tại
  - Lock trường mã (không cho sửa)
  - Form validation
  - Toast notification
  - Redirect về danh sách sau khi cập nhật

### Backend (FastAPI + PostgreSQL)
- ✅ **GET /api/violation-types** - Lấy danh sách
- ✅ **GET /api/violation-types/{code}** - Lấy chi tiết
- ✅ **POST /api/violation-types** - Tạo mới
- ✅ **PUT /api/violation-types/{code}** - Cập nhật
- ✅ **DELETE /api/violation-types/{code}** - Xóa (có kiểm tra ràng buộc)

## 📁 Cấu trúc file

### Frontend
```
src/
├── app/(admin)/violations/types/
│   ├── page.tsx                    # Danh sách loại vi phạm
│   ├── create/
│   │   └── page.tsx                # Form thêm mới
│   └── edit/[code]/
│       └── page.tsx                # Form chỉnh sửa
└── services/
    └── violationTypesApi.ts        # API client
```

### Backend
```
traffic-server/app/
├── models/
│   └── violation_type.py           # SQLModel cho violation_types
├── routers/
│   └── violation_types.py          # API endpoints
└── scripts/
    └── seed_violation_types.py     # Script seed dữ liệu mẫu
```

## 🚀 Cách sử dụng

### 1. Seed dữ liệu mẫu (Backend)

```bash
cd traffic-server
python -m app.scripts.seed_violation_types
```

Script sẽ thêm 8 loại vi phạm mẫu:
- RED_LIGHT - Vượt đèn đỏ
- WRONG_LANE - Đi sai làn
- SPEEDING - Vượt quá tốc độ
- NO_HELMET - Không đội mũ bảo hiểm
- STOP_LINE - Vượt vạch dừng
- ILLEGAL_TURN - Rẽ không đúng quy định
- NO_PARKING - Đỗ xe sai quy định
- PHONE_USE - Sử dụng điện thoại khi lái xe

### 2. Khởi động Backend

```bash
cd traffic-server
uvicorn app.main:app --reload --port 8000
```

API docs: http://localhost:8000/docs

### 3. Khởi động Frontend

```bash
npm run dev
# hoặc
yarn dev
```

Frontend: http://localhost:3000

### 4. Truy cập module

Vào menu sidebar → **Quản lý loại vi phạm** hoặc truy cập trực tiếp:
- Danh sách: http://localhost:3000/violations/types
- Thêm mới: http://localhost:3000/violations/types/create

## 🔧 API Endpoints

### GET /api/violation-types
Lấy danh sách tất cả loại vi phạm

**Response:**
```json
[
  {
    "violation_type_code": "RED_LIGHT",
    "description": "Vượt đèn đỏ",
    "fine_amount": 800000,
    "severity": "high"
  }
]
```

### GET /api/violation-types/{code}
Lấy chi tiết một loại vi phạm

**Response:**
```json
{
  "violation_type_code": "RED_LIGHT",
  "description": "Vượt đèn đỏ - Phương tiện di chuyển qua vạch dừng khi đèn tín hiệu màu đỏ",
  "fine_amount": 800000,
  "severity": "high"
}
```

### POST /api/violation-types
Tạo loại vi phạm mới

**Request Body:**
```json
{
  "violation_type_code": "NEW_VIOLATION",
  "description": "Mô tả vi phạm",
  "fine_amount": 500000,
  "severity": "medium"
}
```

**Response:** Trả về object vừa tạo

### PUT /api/violation-types/{code}
Cập nhật loại vi phạm

**Request Body:**
```json
{
  "description": "Mô tả mới",
  "fine_amount": 600000,
  "severity": "high"
}
```

**Response:** Trả về object sau khi cập nhật

### DELETE /api/violation-types/{code}
Xóa loại vi phạm

**Note:** Sẽ báo lỗi nếu có vi phạm đang tham chiếu đến loại này

## 🎨 UI Components sử dụng

- `TextFormInput` - Input text với validation
- `TextAreaFormInput` - Textarea với validation
- `SelectFormInput` - Dropdown select với react-select
- `PageTitle` - Tiêu đề trang
- `Card`, `Table`, `Button`, `Badge` - React Bootstrap components

## ✅ Validation

### Frontend (Yup Schema)
- `violation_type_code`: Bắt buộc, chỉ chữ in hoa, số và dấu gạch dưới
- `description`: Bắt buộc
- `fine_amount`: Bắt buộc, phải là số >= 0
- `severity`: Bắt buộc, phải là 'low', 'medium' hoặc 'high'

### Backend
- Kiểm tra trùng mã khi tạo mới
- Kiểm tra severity hợp lệ
- Kiểm tra ràng buộc khi xóa (không cho xóa nếu có vi phạm đang dùng)

## 🔐 Database Schema

```sql
CREATE TABLE violation_types (
    violation_type_code VARCHAR(50) PRIMARY KEY,
    description TEXT NOT NULL,
    fine_amount DECIMAL(12,2),
    severity TEXT DEFAULT 'medium'  -- low | medium | high
);
```

## 📝 Notes

- **Delete UI-only**: Nút Delete trên danh sách chỉ ẩn item khỏi UI, không gọi API DELETE
- **Code immutable**: Mã loại vi phạm không thể thay đổi sau khi tạo
- **Toast notifications**: Sử dụng react-toastify cho thông báo
- **Form validation**: Sử dụng react-hook-form + yup resolver
- **Type safety**: Full TypeScript với interfaces rõ ràng

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
- Đảm bảo mã loại vi phạm chỉ chứa chữ in hoa, số và dấu gạch dưới
- Đảm bảo severity là một trong: low, medium, high
- Đảm bảo fine_amount là số hợp lệ

## 🎉 Hoàn thành!

Module đã sẵn sàng sử dụng với đầy đủ chức năng CRUD, validation, error handling và UI đẹp mắt.
