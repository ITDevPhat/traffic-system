# Tính Năng Upload Hình Ảnh Vi Phạm

## Mô tả
Đã thêm khả năng upload hình ảnh cho biển số xe, địa điểm vi phạm và hình ảnh bằng chứng trong trang chi tiết vi phạm.

## Tính năng mới

### 1. Upload ảnh biển số xe
- **Vị trí**: Bên cạnh thông tin biển số xe
- **Kích thước**: 120x60px (tỷ lệ biển số thực tế)
- **Chức năng**: Click vào khung ảnh hoặc nút "📷 Upload" để chọn file
- **Hiển thị**: Ảnh biển số nhỏ gọn, dễ nhận dạng

### 2. Upload ảnh địa điểm vi phạm
- **Vị trí**: Bên cạnh thông tin địa điểm
- **Kích thước**: 120x80px (ảnh phong cảnh nhỏ)
- **Chức năng**: Click vào khung ảnh hoặc nút "📍 Upload" để chọn file
- **Hiển thị**: Ảnh địa điểm để tham khảo vị trí vi phạm

### 3. Upload ảnh bằng chứng vi phạm
- **Vị trí**: Phần video bằng chứng ở dưới cùng
- **Kích thước**: Full width, tối đa 700px chiều cao
- **Chức năng**: 
  - Nút "📤 Upload Ảnh Mới" trên header
  - Click vào vùng trống nếu chưa có ảnh
- **Hiển thị**: Ảnh bằng chứng lớn với bounding box overlay

## API Backend

### Endpoint upload hình ảnh
```
POST /api/violations/{violation_id}/upload-image
```

**Parameters:**
- `file`: File hình ảnh (multipart/form-data)
- `image_type`: Loại ảnh ('plate', 'location', 'evidence')

**Response:**
```json
{
  "ok": true,
  "message": "Đã upload plate thành công",
  "url": "/uploads/violations/24/plate_abc123.jpg",
  "filename": "plate_abc123.jpg"
}
```

### Validation
- **File type**: Chỉ chấp nhận hình ảnh (image/*)
- **File size**: Tối đa 5MB
- **Supported formats**: JPG, PNG, GIF, BMP, WEBP

## Cấu trúc thư mục uploads
```
traffic-server/
├── uploads/
│   └── violations/
│       └── {violation_id}/
│           ├── plate_{uuid}.jpg      # Ảnh biển số
│           ├── location_{uuid}.jpg   # Ảnh địa điểm  
│           └── evidence_{uuid}.jpg   # Ảnh bằng chứng
```

## Cách sử dụng

### 1. Setup thư mục uploads
```bash
cd traffic-server
python setup_uploads.py
```

### 2. Khởi động server
```bash
# Backend
cd traffic-server
python -m uvicorn app.main:app --reload --port 8000

# Frontend  
npm run dev
```

### 3. Upload hình ảnh
1. Truy cập trang chi tiết vi phạm: `http://localhost:3000/violations/management/24`
2. Nhấn nút "✏️ Chỉnh sửa"
3. Upload hình ảnh:
   - **Biển số**: Click vào khung ảnh bên cạnh biển số hoặc nút "📷 Upload"
   - **Địa điểm**: Click vào khung ảnh bên cạnh địa điểm hoặc nút "📍 Upload"
   - **Bằng chứng**: Click nút "📤 Upload Ảnh Mới" hoặc click vào vùng trống
4. Chọn file hình ảnh từ máy tính
5. Nhấn "💾 Lưu" để lưu thay đổi

## Giao diện

### Chế độ xem (không chỉnh sửa)
- Hiển thị các ảnh đã upload
- Ảnh biển số và địa điểm nhỏ gọn bên cạnh thông tin
- Ảnh bằng chứng lớn ở dưới với bounding box

### Chế độ chỉnh sửa
- Khung ảnh có thể click để upload
- Nút upload rõ ràng với icon phù hợp
- Loading spinner khi đang upload
- Toast notification khi upload thành công/thất bại

### Trạng thái upload
- **Đang upload**: Hiển thị spinner, disable nút
- **Thành công**: Toast xanh, cập nhật ảnh ngay lập tức
- **Thất bại**: Toast đỏ với thông báo lỗi

## Tính năng nổi bật

### UX/UI tối ưu
- **Drag & drop**: Click để chọn file, trực quan
- **Preview ngay lập tức**: Ảnh hiển thị ngay sau khi upload
- **Responsive**: Hoạt động tốt trên mọi thiết bị
- **Loading states**: Feedback rõ ràng cho người dùng

### Bảo mật
- **File validation**: Kiểm tra loại file và kích thước
- **Unique filename**: Tránh conflict với UUID
- **Path traversal protection**: An toàn với đường dẫn file

### Performance
- **Lazy loading**: Chỉ load ảnh khi cần
- **Optimized size**: Ảnh nhỏ cho biển số và địa điểm
- **Caching**: Browser cache cho ảnh đã tải

## Lưu ý kỹ thuật

### Frontend
- Sử dụng `useRef` để control file input
- State management cho từng loại ảnh
- Error handling đầy đủ
- TypeScript interfaces rõ ràng

### Backend
- FastAPI với UploadFile
- Static file serving cho uploads
- Database update cho evidence image
- Proper error responses

### File Management
- Tự động tạo thư mục theo violation_id
- UUID để tránh trùng tên file
- Cleanup cũ khi upload mới (có thể thêm sau)

## Mở rộng tương lai
- **Image compression**: Tự động nén ảnh khi upload
- **Multiple formats**: Hỗ trợ thêm định dạng ảnh
- **Batch upload**: Upload nhiều ảnh cùng lúc
- **Image editing**: Crop, rotate ảnh trước khi lưu
- **Thumbnail generation**: Tạo thumbnail tự động