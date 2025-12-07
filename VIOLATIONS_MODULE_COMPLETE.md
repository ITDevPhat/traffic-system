# 🚨 Module Quản Lý Vi Phạm - Hướng Dẫn Chi Tiết

Module CRUD hoàn chỉnh để quản lý vi phạm giao thông được phát hiện bởi hệ thống AI.

---

## 📋 Mục Lục

1. [Tổng Quan](#tổng-quan)
2. [Cấu Trúc Database](#cấu-trúc-database)
3. [Backend API](#backend-api)
4. [Frontend UI](#frontend-ui)
5. [Cách Sử Dụng](#cách-sử-dụng)
6. [Components Có Sẵn](#components-có-sẵn)
7. [Validation Rules](#validation-rules)

---

## 🎯 Tổng Quan

### Tính Năng Chính

✅ **Danh sách vi phạm** (`/violations/management`)
- Hiển thị table với đầy đủ thông tin
- Filter theo trạng thái xác minh (unverified, verified, rejected)
- Tìm kiếm theo biển số xe
- Hiển thị ảnh bằng chứng
- Nút Edit/Delete cho từng item
- Delete chỉ ẩn item trên UI (không xóa DB)

✅ **Thêm vi phạm** (`/violations/management/create`)
- Form validation đầy đủ
- Các trường: video_job_id, violation_type_code, plate, confidence, verification_status, v.v.
- Toast notification
- Redirect về danh sách sau khi tạo

✅ **Chỉnh sửa vi phạm** (`/violations/management/edit/[id]`)
- Load dữ liệu hiện tại
- Form validation
- Cập nhật trạng thái xác minh
- Toast notification
- Redirect về danh sách sau khi cập nhật

---

## 🗄️ Cấu Trúc Database

### Bảng `violations`

```sql
CREATE TABLE violations (
    violation_id SERIAL PRIMARY KEY,
    video_job_id INT REFERENCES video_jobs(video_job_id) ON DELETE CASCADE,
    vehicle_id INT REFERENCES vehicles(vehicle_id) ON DELETE SET NULL,
    violation_type_code VARCHAR(50) REFERENCES violation_types(violation_type_code) ON DELETE SET NULL,
    frame INT,
    timestamp TIMESTAMP,
    roi_type VARCHAR(50),
    evidence_img TEXT,
    plate VARCHAR(20),
    confidence FLOAT,
    model_id INT REFERENCES models(model_id) ON DELETE SET NULL,
    verification_status TEXT DEFAULT 'unverified',  -- unverified | verified | rejected
    verified_by INT REFERENCES users(user_id) ON DELETE SET NULL,
    verified_source TEXT DEFAULT 'manual',          -- manual | ai | external
    verified_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);
```

### Các Trường Quan Trọng

| Trường | Kiểu | Mô Tả | Bắt Buộc |
|--------|------|-------|----------|
| `violation_id` | SERIAL | ID tự động tăng | ✅ (PK) |
| `video_job_id` | INT | ID video job | ✅ (FK) |
| `violation_type_code` | VARCHAR(50) | Mã loại vi phạm | ❌ (FK) |
| `plate` | VARCHAR(20) | Biển số xe | ❌ |
| `confidence` | FLOAT | Độ tin cậy (0-1) | ❌ |
| `verification_status` | TEXT | Trạng thái xác minh | ✅ |
| `evidence_img` | TEXT | Đường dẫn ảnh bằng chứng | ❌ |
| `timestamp` | TIMESTAMP | Thời gian vi phạm | ❌ |
| `frame` | INT | Số frame trong video | ❌ |

---

## 🔧 Backend API

### File Structure

```
traffic-server/app/
├── models/
│   └── violation.py              ✅ SQLModel cho violations
└── routers/
    └── violations.py             ✅ API endpoints CRUD
```

### API Endpoints

#### 1. GET /api/violations

**Mô tả:** Lấy danh sách vi phạm với filter và pagination

**Query Parameters:**
- `skip` (int, optional): Số record bỏ qua (default: 0)
- `limit` (int, optional): Số record tối đa (default: 100, max: 1000)
- `violation_type_code` (string, optional): Lọc theo loại vi phạm
- `video_job_id` (int, optional): Lọc theo video job
- `verification_status` (string, optional): Lọc theo trạng thái (unverified, verified, rejected)
- `plate` (string, optional): Tìm kiếm theo biển số (LIKE search)

**Response:**
```json
[
  {
    "violation_id": 1,
    "video_job_id": 5,
    "vehicle_id": 10,
    "violation_type_code": "RED_LIGHT",
    "frame": 150,
    "timestamp": "2025-01-01T10:30:00",
    "roi_type": "stopline",
    "evidence_img": "/static/outputs/violation_1.jpg",
    "plate": "59A-12345",
    "confidence": 0.95,
    "model_id": 1,
    "verification_status": "unverified",
    "verified_by": null,
    "verified_source": "ai",
    "verified_at": null,
    "created_at": "2025-01-01T10:30:05"
  }
]
```

**Ví dụ:**
```bash
# Lấy tất cả vi phạm
GET http://localhost:8000/api/violations

# Lọc theo trạng thái chưa xác minh
GET http://localhost:8000/api/violations?verification_status=unverified

# Tìm theo biển số
GET http://localhost:8000/api/violations?plate=59A

# Lọc theo video job
GET http://localhost:8000/api/violations?video_job_id=5

# Pagination
GET http://localhost:8000/api/violations?skip=0&limit=20
```

---

#### 2. GET /api/violations/{violation_id}

**Mô tả:** Lấy chi tiết một vi phạm

**Path Parameters:**
- `violation_id` (int, required): ID của vi phạm

**Response:**
```json
{
  "violation_id": 1,
  "video_job_id": 5,
  "violation_type_code": "RED_LIGHT",
  "plate": "59A-12345",
  "confidence": 0.95,
  "verification_status": "verified",
  "evidence_img": "/static/outputs/violation_1.jpg",
  "timestamp": "2025-01-01T10:30:00",
  "created_at": "2025-01-01T10:30:05"
}
```

**Ví dụ:**
```bash
GET http://localhost:8000/api/violations/1
```

---

#### 3. POST /api/violations

**Mô tả:** Tạo vi phạm mới

**Request Body:**
```json
{
  "video_job_id": 5,
  "vehicle_id": 10,
  "violation_type_code": "RED_LIGHT",
  "frame": 150,
  "timestamp": "2025-01-01T10:30:00",
  "roi_type": "stopline",
  "evidence_img": "/static/outputs/violation_new.jpg",
  "plate": "59A-12345",
  "confidence": 0.95,
  "model_id": 1,
  "verification_status": "unverified",
  "verified_source": "ai"
}
```

**Response:** Trả về object vừa tạo

**Validation:**
- `video_job_id`: Bắt buộc, phải tồn tại trong bảng video_jobs
- `verification_status`: Phải là một trong: unverified, verified, rejected
- `verified_source`: Phải là một trong: manual, ai, external
- `confidence`: Phải từ 0 đến 1

**Ví dụ:**
```bash
POST http://localhost:8000/api/violations
Content-Type: application/json

{
  "video_job_id": 5,
  "violation_type_code": "RED_LIGHT",
  "plate": "59A-12345",
  "confidence": 0.95,
  "verification_status": "unverified",
  "verified_source": "ai"
}
```

---

#### 4. PUT /api/violations/{violation_id}

**Mô tả:** Cập nhật thông tin vi phạm

**Path Parameters:**
- `violation_id` (int, required): ID của vi phạm

**Request Body:**
```json
{
  "video_job_id": 5,
  "violation_type_code": "RED_LIGHT",
  "plate": "59A-12345",
  "confidence": 0.98,
  "verification_status": "verified",
  "verified_by": 1,
  "verified_source": "manual",
  "verified_at": "2025-01-01T11:00:00"
}
```

**Response:** Trả về object sau khi cập nhật

**Ví dụ:**
```bash
PUT http://localhost:8000/api/violations/1
Content-Type: application/json

{
  "video_job_id": 5,
  "verification_status": "verified",
  "verified_by": 1,
  "verified_source": "manual",
  "verified_at": "2025-01-01T11:00:00"
}
```

---

#### 5. DELETE /api/violations/{violation_id}

**Mô tả:** Xóa vi phạm

**Path Parameters:**
- `violation_id` (int, required): ID của vi phạm

**Response:**
```json
{
  "message": "Đã xóa vi phạm thành công",
  "violation_id": 1
}
```

**Ví dụ:**
```bash
DELETE http://localhost:8000/api/violations/1
```

---

## 🎨 Frontend UI

### File Structure

```
src/
├── app/(admin)/violations/management/
│   ├── page.tsx                    ✅ Danh sách vi phạm
│   ├── create/
│   │   └── page.tsx                ⏳ Form thêm mới (cần tạo)
│   └── edit/[id]/
│       └── page.tsx                ⏳ Form chỉnh sửa (cần tạo)
└── services/
    └── violationsApi.ts            ✅ API client
```

### 1. Trang Danh Sách (`/violations/management`)

**File:** `src/app/(admin)/violations/management/page.tsx`

**Tính năng:**
- ✅ Hiển thị table với đầy đủ thông tin
- ✅ Filter theo trạng thái xác minh
- ✅ Tìm kiếm theo biển số
- ✅ Hiển thị ảnh bằng chứng
- ✅ Nút Edit/Delete
- ✅ Delete chỉ ẩn item (không xóa DB)
- ✅ Badge màu sắc cho trạng thái

**Components sử dụng:**
- `PageTitle` - Tiêu đề trang
- `Card`, `Table`, `Badge`, `Button`, `Form` - React Bootstrap
- `Link` - Next.js navigation

**API calls:**
```typescript
import { fetchViolationsManagement } from '@/services/violationsApi';

// Load danh sách
const data = await fetchViolationsManagement({
  verification_status: 'unverified',
  plate: '59A'
});
```

---

### 2. Trang Thêm Mới (`/violations/management/create`)

**File:** `src/app/(admin)/violations/management/create/page.tsx` ⏳ **CẦN TẠO**

**Form fields:**
```typescript
{
  video_job_id: number;           // Required - Dropdown select
  violation_type_code: string;    // Optional - Dropdown select
  plate: string;                  // Optional - Text input
  confidence: number;             // Optional - Number input (0-1)
  frame: number;                  // Optional - Number input
  timestamp: datetime;            // Optional - Datetime picker
  roi_type: string;               // Optional - Text input
  evidence_img: string;           // Optional - Text input (file path)
  verification_status: string;    // Required - Select (unverified, verified, rejected)
  verified_source: string;        // Required - Select (manual, ai, external)
}
```

**Components cần dùng:**
- `TextFormInput` - Input text
- `SelectFormInput` - Dropdown select
- `PageTitle` - Tiêu đề trang
- `Card`, `Button`, `Row`, `Col` - React Bootstrap

**Validation schema (Yup):**
```typescript
const schema = yup.object({
  video_job_id: yup.number().required('Video job là bắt buộc'),
  violation_type_code: yup.string(),
  plate: yup.string().max(20, 'Biển số tối đa 20 ký tự'),
  confidence: yup.number()
    .min(0, 'Độ tin cậy từ 0 đến 1')
    .max(1, 'Độ tin cậy từ 0 đến 1'),
  verification_status: yup.string()
    .required('Trạng thái là bắt buộc')
    .oneOf(['unverified', 'verified', 'rejected']),
  verified_source: yup.string()
    .required('Nguồn xác minh là bắt buộc')
    .oneOf(['manual', 'ai', 'external']),
});
```

**API call:**
```typescript
import { createViolation } from '@/services/violationsApi';

const onSubmit = async (data) => {
  await createViolation(data);
  toast.success('Tạo vi phạm thành công!');
  router.push('/violations/management');
};
```

---

### 3. Trang Chỉnh Sửa (`/violations/management/edit/[id]`)

**File:** `src/app/(admin)/violations/management/edit/[id]/page.tsx` ⏳ **CẦN TẠO**

**Tính năng:**
- Load dữ liệu hiện tại từ API
- Form giống trang Create
- Thêm trường `verified_by`, `verified_at`
- Cập nhật trạng thái xác minh

**API calls:**
```typescript
import { fetchViolationById, updateViolation } from '@/services/violationsApi';

// Load dữ liệu
useEffect(() => {
  const loadData = async () => {
    const data = await fetchViolationById(violationId);
    reset(data);
  };
  loadData();
}, [violationId]);

// Cập nhật
const onSubmit = async (data) => {
  await updateViolation(violationId, data);
  toast.success('Cập nhật vi phạm thành công!');
  router.push('/violations/management');
};
```

---

## 🚀 Cách Sử Dụng

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

### 3. Truy cập Module

Vào menu sidebar → **Quản lý vi phạm** hoặc:
- Danh sách: http://localhost:3000/violations/management
- Thêm mới: http://localhost:3000/violations/management/create

---

## 🎨 Components Có Sẵn

### Form Components

```typescript
import TextFormInput from '@/components/from/TextFormInput';
import TextAreaFormInput from '@/components/from/TextAreaFormInput';
import SelectFormInput from '@/components/from/SelectFormInput';
```

**Ví dụ sử dụng:**

```tsx
<TextFormInput
  name="plate"
  control={control}
  label="Biển số xe"
  placeholder="59A-12345"
  containerClassName="mb-3"
  id="plate"
  noValidate={false}
  labelClassName=""
/>

<SelectFormInput
  name="verification_status"
  control={control}
  label="Trạng thái xác minh"
  options={[
    { value: 'unverified', label: 'Chưa xác minh' },
    { value: 'verified', label: 'Đã xác minh' },
    { value: 'rejected', label: 'Từ chối' },
  ]}
  containerClassName="mb-3"
  id="verification_status"
  className=""
  labelClassName=""
  noValidate={false}
/>
```

### UI Components

```typescript
import { Card, Table, Badge, Button, Form, Row, Col } from 'react-bootstrap';
import PageTitle from '@/components/PageTitle';
import Link from 'next/link';
```

---

## ✅ Validation Rules

### Backend Validation

1. **video_job_id**
   - Bắt buộc
   - Phải tồn tại trong bảng `video_jobs`

2. **verification_status**
   - Bắt buộc
   - Phải là: `unverified`, `verified`, hoặc `rejected`

3. **verified_source**
   - Bắt buộc
   - Phải là: `manual`, `ai`, hoặc `external`

4. **confidence**
   - Optional
   - Nếu có, phải từ 0 đến 1

5. **plate**
   - Optional
   - Tối đa 20 ký tự

### Frontend Validation (Yup)

```typescript
const schema = yup.object({
  video_job_id: yup.number().required('Video job là bắt buộc'),
  plate: yup.string().max(20, 'Biển số tối đa 20 ký tự'),
  confidence: yup.number()
    .min(0, 'Độ tin cậy từ 0 đến 1')
    .max(1, 'Độ tin cậy từ 0 đến 1'),
  verification_status: yup.string()
    .required('Trạng thái là bắt buộc')
    .oneOf(['unverified', 'verified', 'rejected']),
  verified_source: yup.string()
    .required('Nguồn xác minh là bắt buộc')
    .oneOf(['manual', 'ai', 'external']),
});
```

---

## 📊 Badge Colors

### Verification Status

| Status | Badge Color | Label |
|--------|-------------|-------|
| `unverified` | Warning (vàng) | Chưa xác minh |
| `verified` | Success (xanh lá) | Đã xác minh |
| `rejected` | Danger (đỏ) | Từ chối |

### Violation Type

| Type | Badge Color |
|------|-------------|
| `RED_LIGHT` | Danger (đỏ) |
| `WRONG_LANE` | Warning (vàng) |
| `SPEEDING` | Danger (đỏ) |
| Khác | Secondary (xám) |

---

## 🔗 API Client (TypeScript)

**File:** `src/services/violationsApi.ts`

```typescript
import { fetchViolationsManagement, fetchViolationById, 
         createViolation, updateViolation, deleteViolationItem } 
from '@/services/violationsApi';

// Lấy danh sách
const violations = await fetchViolationsManagement({
  verification_status: 'unverified',
  plate: '59A'
});

// Lấy chi tiết
const violation = await fetchViolationById(1);

// Tạo mới
const newViolation = await createViolation({
  video_job_id: 5,
  violation_type_code: 'RED_LIGHT',
  plate: '59A-12345',
  confidence: 0.95,
  verification_status: 'unverified',
  verified_source: 'ai'
});

// Cập nhật
const updated = await updateViolation(1, {
  verification_status: 'verified',
  verified_by: 1,
  verified_source: 'manual'
});

// Xóa
await deleteViolationItem(1);
```

---

## 📝 TODO - Cần Hoàn Thành

### Frontend Pages

- [ ] Tạo `/violations/management/create/page.tsx`
  - Form thêm mới với validation
  - Dropdown select cho video_job_id
  - Dropdown select cho violation_type_code
  - Toast notifications

- [ ] Tạo `/violations/management/edit/[id]/page.tsx`
  - Load dữ liệu hiện tại
  - Form chỉnh sửa
  - Cập nhật trạng thái xác minh
  - Toast notifications

### Enhancements

- [ ] Thêm filter theo loại vi phạm
- [ ] Thêm filter theo video job
- [ ] Thêm pagination controls
- [ ] Thêm modal xem ảnh bằng chứng
- [ ] Thêm bulk actions (xác minh nhiều vi phạm cùng lúc)

---

## 🎉 Kết Luận

Module Violations đã có:
- ✅ Backend CRUD hoàn chỉnh
- ✅ API client TypeScript
- ✅ Trang danh sách với filter và search
- ⏳ Cần tạo trang Create và Edit (copy pattern từ module Models/Violation Types)

Tất cả API đã sẵn sàng và có thể test qua Swagger UI tại http://localhost:8000/docs
