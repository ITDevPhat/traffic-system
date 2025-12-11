# Tính Năng Chỉnh Sửa Kết Quả OCR

## Mô tả
Đã thêm tính năng cho phép người dùng chỉnh sửa kết quả OCR sau khi phát hiện biển số và áp dụng lại lên UI.

## Tính năng mới

### 1. Chỉnh sửa text biển số
- Mỗi biển số phát hiện được hiển thị trong một input field có thể chỉnh sửa
- Người dùng có thể sửa trực tiếp text của biển số nếu OCR nhận dạng sai

### 2. Trạng thái thay đổi
- **Badge "Có thay đổi"**: Hiển thị khi có bất kỳ chỉnh sửa nào chưa được áp dụng
- **Highlight vàng**: Input field được highlight màu vàng khi đang có thay đổi chưa áp dụng
- **Highlight xanh**: Input field được highlight màu xanh sau khi thay đổi đã được áp dụng

### 3. Nút điều khiển
- **"✅ Áp dụng thay đổi"**: Áp dụng tất cả các chỉnh sửa lên kết quả và cập nhật UI
- **"↶ Hủy"**: Hủy bỏ tất cả các thay đổi chưa áp dụng

### 4. Hiển thị trực quan
- **Bounding box màu tím**: Biển số đã được chỉnh sửa sẽ có khung màu tím (magenta) và dày hơn
- **Icon ✏️**: Hiển thị trên bounding box và badge để đánh dấu biển số đã chỉnh sửa
- **Thông tin gốc**: Hiển thị text gốc bên dưới để so sánh

### 5. Cập nhật thống kê
- Số lượng "Biển số nhận dạng" được cập nhật tự động dựa trên kết quả sau chỉnh sửa
- Chỉ tính những biển số có text không rỗng và đạt ngưỡng tin cậy

## Cách sử dụng

1. **Upload ảnh** và nhấn "🔍 Nhận Diện Biển Số"
2. **Chỉnh sửa text** trong các input field nếu cần thiết
3. **Nhấn "✅ Áp dụng thay đổi"** để cập nhật kết quả
4. **Xem kết quả** được cập nhật trên ảnh với bounding box màu tím cho biển số đã chỉnh sửa

## Giao diện

### Trước khi chỉnh sửa:
- Bounding box xanh lá (tin cậy cao) hoặc cam (tin cậy thấp)
- Text hiển thị kết quả OCR gốc

### Trong quá trình chỉnh sửa:
- Badge "Có thay đổi" xuất hiện
- Input field highlight màu vàng
- Nút "Áp dụng thay đổi" và "Hủy" hiển thị

### Sau khi áp dụng:
- Bounding box màu tím cho biển số đã chỉnh sửa
- Icon ✏️ trên bounding box và badge
- Input field highlight màu xanh
- Hiển thị text gốc để so sánh

## Lợi ích
- **Tăng độ chính xác**: Cho phép sửa lỗi OCR thủ công
- **Trải nghiệm tốt**: Giao diện trực quan, dễ sử dụng
- **Theo dõi thay đổi**: Rõ ràng biết được biển số nào đã được chỉnh sửa
- **Linh hoạt**: Có thể hủy thay đổi hoặc áp dụng theo ý muốn