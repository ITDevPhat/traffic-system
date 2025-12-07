# 📚 Hướng Dẫn Hoàn Chỉnh - Các Module Quản Lý

Tài liệu này tổng hợp tất cả các module CRUD đã được tạo cho hệ thống phát hiện vi phạm giao thông.

## 🎯 Tổng Quan

Đã tạo xong **5 module CRUD** hoàn chỉnh:

1. ✅ **Violation Types** - Quản lý loại vi phạm
2. ✅ **AI Models** - Quản lý mô hình AI
3. ✅ **Locations** - Quản lý vị trí
4. ✅ **Cameras** - Quản lý camera
5. ✅ **Video Jobs** - Quản lý video jobs

---

## 📁 Cấu Trúc File Đã Tạo

### Backend (FastAPI + Python)

```
traffic-server/app/
├── models/
│   ├── violation_type.py          ✅ Loại vi phạm
│   ├── model.py                   ✅ Mô hình AI
│   ├── location.py                ✅ Vị trí
│   ├── camera.py                  ✅ Camera
│   └── video_job_extended.py      ✅ Video jobs
│
├── routers/
│   ├── violation_types.py         ✅ API loại vi phạm
│   ├── models.py                  ✅ API mô hình AI
│   ├── locations.py               ✅ API vị trí
│   ├── cameras.py                 ✅ API camera
│   └── video_jobs.py              ✅ API video jobs
│
└── scripts/
    └── seed_violation_types.py    ✅ Seed data mẫu
```

### Frontend (Next.js + TypeScript)

```
src/
├── services/
│   ├── violationTypesApi.ts       ✅ API client loại vi phạm
│   ├── modelsApi.ts               ✅ API client mô hình AI
│   ├── locationsApi.ts            ✅ API client vị trí
│   ├── camerasApi.ts              ✅ API client camera
│   └── videoJobsApi.ts            ✅ API client video jobs
│
└── app/(admin)/
    ├── violations/types/          ✅ UI loại vi phạm
    │   ├── page.tsx               (Danh sách)
    │   ├── create/page.tsx        (Thêm mới)
    │   └── edit/[code]/page.tsx   (Chỉnh sửa)
    │
    └── models/                    ✅ UI mô hình AI
        ├── page.tsx               (Danh sách)
        ├── create/page.tsx        (Thêm mới)
        └── edit/[id]/page.tsx     (Chỉnh sửa)
```

**⚠️ LƯU Ý:** Frontend cho Locations, Cameras, Video Jobs chưa được tạo UI pages. Bạn có thể tạo tương tự như 2 module đã có.

---

## 🚀 API Endpoints Đã Đăng Ký

Tất cả đã được đăng ký trong `traffic-server/app/main.py`:

### 1. Violation Types
- `GET /api/violation-types` - Danh sách
- `GET /api/violation-types/{code}` - Chi tiết
- `POST /api/violation-types` - Tạo mới
- `PUT /api/violation-types/{code}` - Cập nhật
- `DELETE /api/violation-types/{code}` - Xóa

### 2. AI Models
- `GET /api/models` - Danh sách (filter: model_type)
- `GET /api/models/{id}` - Chi tiết
- `POST /api/models` - Tạo mới
- `PUT /api/models/{id}` - Cập nhật
- `DELETE /api/models/{id}` - Xóa

### 3. Locations
- `GET /api/locations` - Danh sách
- `GET /api/locations/{id}` - Chi tiết
- `POST /api/locations` - Tạo mới
- `PUT /api/locations/{id}` - Cập nhật
- `DELETE /api/locations/{id}` - Xóa

### 4. Cameras
- `GET /api/cameras` - Danh sách (filter: status, location_id)
- `GET /api/cameras/{id}` - Chi tiết
- `POST /api/cameras` - Tạo mới
- `PUT /api/cameras/{id}` - Cập nhật
- `DELETE /api/cameras/{id}` - Xóa

### 5. Video Jobs
- `GET /api/video-jobs` - Danh sách (filter: status, camera_id)
- `GET /api/video-jobs/{id}` - Chi tiết
- `POST /api/video-jobs` - Tạo mới
- `PUT /api/video-jobs/{id}` - Cập nhật
- `DELETE /api/video-jobs/{id}` - Xóa

---

## 🔧 Cách Chạy

### 1. Khởi động Backend

```bash
cd traffic-server
uvicorn app.main:app --reload --port 8000
```

Truy cập API docs: http://localhost:8000/docs

### 2. Seed dữ liệu mẫu (Violation Types)

```bash
cd traffic-server
python -m app.scripts.seed_violation_types
```

### 3. Khởi động Frontend

```bash
npm run dev
# hoặc
yarn dev
```

Truy cập: http://localhost:3000

---

## 📊 Database Schema

### Violation Types
```sql
CREATE TABLE violation_types (
    violation_type_code VARCHAR(50) PRIMARY KEY,
    description TEXT NOT NULL,
    fine_amount DECIMAL(12,2),
    severity TEXT DEFAULT 'medium'
);
```

### Models
```sql
CREATE TABLE models (
    model_id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    model_type TEXT NOT NULL,
    file_path TEXT NOT NULL,
    version VARCHAR(50) DEFAULT '1.0',
    framework VARCHAR(50) DEFAULT 'YOLO',
    confidence_threshold FLOAT DEFAULT 0.5,
    description TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);
```

### Locations
```sql
CREATE TABLE locations (
    location_id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    address TEXT,
    latitude DECIMAL(9,6),
    longitude DECIMAL(9,6),
    description TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    CONSTRAINT unique_location UNIQUE (latitude, longitude)
);
```

### Cameras
```sql
CREATE TABLE cameras (
    camera_id SERIAL PRIMARY KEY,
    location_id INT REFERENCES locations(location_id) ON DELETE SET NULL,
    name VARCHAR(100) NOT NULL,
    model VARCHAR(100),
    ip_address VARCHAR(45),
    stream_url TEXT,
    status TEXT DEFAULT 'active',
    install_date TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);
```

### Video Jobs
```sql
CREATE TABLE video_jobs (
    video_job_id SERIAL PRIMARY KEY,
    camera_id INT REFERENCES cameras(camera_id) ON DELETE SET NULL,
    file_name VARCHAR(255) NOT NULL,
    upload_time TIMESTAMP DEFAULT NOW(),
    status TEXT DEFAULT 'pending',
    processing_stage VARCHAR(30) DEFAULT 'uploaded',
    processed_at TIMESTAMP,
    output_path TEXT,
    fps FLOAT,
    duration FLOAT,
    notes TEXT
);
```

---

## ✅ Tính Năng Đã Hoàn Thành

### Backend
- ✅ SQLModel cho tất cả 5 bảng
- ✅ CRUD endpoints đầy đủ
- ✅ Validation dữ liệu
- ✅ Kiểm tra ràng buộc foreign key khi xóa
- ✅ Filter theo các trường liên quan
- ✅ Pagination (skip, limit)
- ✅ Error handling

### Frontend (Violation Types & Models)
- ✅ Danh sách với table đẹp
- ✅ Form thêm mới với validation
- ✅ Form chỉnh sửa
- ✅ Toast notifications
- ✅ Loading states
- ✅ Error handling
- ✅ Filter theo loại
- ✅ Delete UI-only (không xóa DB)

---

## 📝 Cần Làm Thêm

### Frontend cho 3 module còn lại

Bạn cần tạo UI pages cho:

1. **Locations** (`/locations`)
   - Danh sách vị trí
   - Thêm/sửa vị trí
   - Hiển thị tọa độ (latitude, longitude)

2. **Cameras** (`/cameras`)
   - Danh sách camera
   - Thêm/sửa camera
   - Filter theo status và location
   - Hiển thị stream URL

3. **Video Jobs** (`/video-jobs`)
   - Danh sách video jobs
   - Thêm/sửa video job
   - Filter theo status và camera
   - Hiển thị progress (processing_stage)

### Cách tạo nhanh

Copy từ module **Models** hoặc **Violation Types** và thay đổi:
- Tên model/interface
- Các trường form
- API endpoints
- Labels và tiêu đề

---

## 🎨 UI Components Có Sẵn

Dự án đã có sẵn các component:
- `TextFormInput` - Input text
- `TextAreaFormInput` - Textarea
- `SelectFormInput` - Dropdown select
- `PageTitle` - Tiêu đề trang
- `Card`, `Table`, `Button`, `Badge`, `Form` - React Bootstrap

---

## 🐛 Troubleshooting

### Backend không khởi động
- Kiểm tra PostgreSQL đã chạy
- Kiểm tra `.env` connection string
- Chạy lại migration nếu cần

### Frontend không load dữ liệu
- Kiểm tra backend chạy ở port 8000
- Kiểm tra CORS settings
- Kiểm tra `NEXT_PUBLIC_API_URL`

### Lỗi import model
- Đảm bảo tất cả model files đã được tạo
- Restart backend sau khi tạo model mới

---

## 📚 Tài Liệu Chi Tiết

- [Violation Types Module](./VIOLATION_TYPES_MODULE.md)
- [AI Models Module](./MODELS_MODULE.md)

---

## 🎉 Kết Luận

Đã hoàn thành:
- ✅ 5 backend modules với CRUD đầy đủ
- ✅ 5 API services (TypeScript)
- ✅ 2 frontend UI modules hoàn chỉnh
- ✅ Validation, error handling, pagination
- ✅ Kiểm tra ràng buộc foreign key

Còn lại:
- ⏳ Tạo UI pages cho Locations, Cameras, Video Jobs (copy pattern từ 2 module đã có)

Tất cả code đã được kiểm tra và sẵn sàng sử dụng! 🚀
