# Requirements Document

## Introduction

Hệ thống phát hiện đèn giao thông (Traffic Light Detection System) cho phép người dùng chọn vùng quan tâm (ROI - Region of Interest) trên video realtime, sau đó chạy mô hình YOLO chuyên biệt để phát hiện trạng thái đèn giao thông (xanh/đỏ/vàng) trong vùng đó. Hệ thống được thiết kế để chạy nhẹ, độc lập với luồng phát hiện phương tiện chính, và cung cấp feedback realtime cho người dùng thông qua giao diện web.

## Glossary

- **ROI (Region of Interest)**: Vùng hình chữ nhật được người dùng chọn trên video để phát hiện đèn giao thông
- **TL System**: Traffic Light Detection System - hệ thống phát hiện đèn giao thông
- **YOLO TL Model**: Mô hình YOLO chuyên biệt cho phát hiện đèn giao thông với 2 class (0: green, 1: red)
- **ByteTrack**: Thuật toán tracking nhẹ để làm mượt kết quả detection theo thời gian
- **WebSocket**: Giao thức truyền thông hai chiều realtime giữa frontend và backend
- **Normalized Coordinates**: Tọa độ được chuẩn hóa trong khoảng [0, 1] để độc lập với resolution
- **Backend**: Python FastAPI server xử lý video và chạy YOLO models
- **Frontend**: Next.js React application hiển thị video và UI controls
- **Canvas Overlay**: Lớp SVG/Canvas đặt trên video để vẽ ROI selection
- **Detection Worker**: Luồng xử lý độc lập chạy YOLO TL detection trên ROI

## Requirements

### Requirement 1

**User Story:** Là người dùng, tôi muốn chọn vùng ROI đèn giao thông trên video bằng cách vẽ hình chữ nhật, để hệ thống biết vùng nào cần phát hiện đèn.

#### Acceptance Criteria

1. WHEN người dùng nhấn nút "Select ROI" THEN TL System SHALL kích hoạt chế độ vẽ ROI trên video canvas
2. WHEN người dùng click và kéo chuột trên video THEN TL System SHALL hiển thị hình chữ nhật preview với viền màu và nền trong suốt
3. WHEN người dùng thả chuột THEN TL System SHALL lưu tọa độ ROI dưới dạng normalized coordinates (x, y, width, height trong khoảng 0-1)
4. WHEN ROI được chọn THEN TL System SHALL hiển thị overlay hình chữ nhật cố định trên video với label "Traffic Light ROI"
5. WHEN người dùng chọn ROI mới THEN TL System SHALL thay thế ROI cũ bằng ROI mới

### Requirement 2

**User Story:** Là người dùng, tôi muốn khởi động detection đèn giao thông trên vùng ROI đã chọn, để hệ thống bắt đầu phân tích trạng thái đèn.

#### Acceptance Criteria

1. WHEN người dùng nhấn "Save ROI & Start TL Detection" với ROI hợp lệ THEN TL System SHALL gửi ROI normalized coordinates đến Backend qua API POST /traffic-light/roi
2. WHEN Backend nhận ROI request THEN Backend SHALL chuyển đổi normalized coordinates thành pixel coordinates dựa trên video resolution
3. WHEN Backend xử lý ROI THEN Backend SHALL khởi động Detection Worker riêng biệt cho camera tương ứng
4. WHEN Detection Worker khởi động THEN Backend SHALL gửi response xác nhận thành công với status "ok"
5. WHEN khởi động thất bại THEN Backend SHALL trả về error message cụ thể

### Requirement 3

**User Story:** Là hệ thống backend, tôi cần chạy YOLO TL detection trên vùng ROI với tần suất thấp (~0.75s/lần) để tiết kiệm tài nguyên GPU/CPU.

#### Acceptance Criteria

1. WHEN Detection Worker chạy THEN Backend SHALL crop vùng ROI từ frame video mới nhất mỗi 0.75 giây
2. WHEN frame ROI được crop THEN Backend SHALL resize ROI về kích thước input của YOLO TL model
3. WHEN YOLO TL inference hoàn tất THEN Backend SHALL phân loại kết quả: class 0 → GREEN, class 1 → RED, không detect → YELLOW
4. WHEN có kết quả detection THEN Backend SHALL áp dụng ByteTrack hoặc temporal smoothing để làm mượt state transitions
5. WHEN state được xác định THEN Backend SHALL broadcast kết quả qua WebSocket với format JSON chứa state, confidence, timestamp, và frame ROI (base64 JPEG)

### Requirement 4

**User Story:** Là người dùng, tôi muốn xem video vùng ROI và trạng thái đèn giao thông realtime trong panel riêng, để theo dõi kết quả detection.

#### Acceptance Criteria

1. WHEN Frontend kết nối WebSocket /ws/traffic-light?camera_id=X THEN TL System SHALL thiết lập kênh truyền dữ liệu realtime
2. WHEN Backend gửi message qua WebSocket THEN Frontend SHALL parse JSON payload chứa state, confidence, timestamp, và frame (base64)
3. WHEN Frontend nhận frame ROI THEN TL System SHALL hiển thị ảnh trong panel "Traffic Light ROI" với kích thước phù hợp
4. WHEN Frontend nhận state GREEN THEN TL System SHALL hiển thị text "GREEN" với màu xanh lá (#10b981)
5. WHEN Frontend nhận state RED THEN TL System SHALL hiển thị text "RED" với màu đỏ (#ef4444)
6. WHEN Frontend nhận state YELLOW THEN TL System SHALL hiển thị text "YELLOW" với màu vàng (#f59e0b)
7. WHEN không có detection THEN TL System SHALL hiển thị "UNKNOWN" với màu xám (#6b7280)

### Requirement 5

**User Story:** Là người dùng, tôi muốn dừng detection đèn giao thông, để giải phóng tài nguyên khi không cần thiết.

#### Acceptance Criteria

1. WHEN người dùng nhấn "Stop TL Detection" THEN Frontend SHALL gửi POST request đến /traffic-light/stop với camera_id
2. WHEN Backend nhận stop request THEN Backend SHALL dừng Detection Worker tương ứng với camera_id
3. WHEN Worker dừng THEN Backend SHALL giải phóng tài nguyên (memory, GPU) được sử dụng bởi worker đó
4. WHEN stop thành công THEN Frontend SHALL đóng WebSocket connection
5. WHEN WebSocket đóng THEN Frontend SHALL xóa preview frame ROI và reset state về "UNKNOWN"

### Requirement 6

**User Story:** Là hệ thống, tôi cần đảm bảo TL detection chạy độc lập với vehicle detection chính, để không ảnh hưởng hiệu năng tổng thể.

#### Acceptance Criteria

1. WHEN TL Detection Worker khởi động THEN Backend SHALL tạo thread hoặc async task riêng biệt không block main detection loop
2. WHEN TL Worker chạy THEN Backend SHALL sử dụng YOLO TL model riêng (nano hoặc ONNX optimized) không chia sẻ với vehicle detection
3. WHEN cả hai detection cùng chạy THEN Backend SHALL đảm bảo TL detection không làm giảm FPS của vehicle detection xuống dưới 80% baseline
4. WHEN GPU memory đầy THEN Backend SHALL ưu tiên vehicle detection và fallback TL detection sang CPU nếu cần
5. WHEN có nhiều camera THEN Backend SHALL giới hạn tối đa 2 TL Workers đồng thời mỗi camera

### Requirement 7

**User Story:** Là developer, tôi muốn có API endpoints rõ ràng để quản lý TL detection lifecycle, để dễ dàng tích hợp và debug.

#### Acceptance Criteria

1. WHEN gọi POST /traffic-light/roi với body {camera_id, roi: {x, y, width, height}} THEN Backend SHALL validate ROI coordinates trong khoảng [0, 1]
2. WHEN ROI validation thất bại THEN Backend SHALL trả về HTTP 400 với error message cụ thể
3. WHEN gọi POST /traffic-light/stop với body {camera_id} THEN Backend SHALL dừng worker và trả về HTTP 200 với status "stopped"
4. WHEN gọi GET /ws/traffic-light?camera_id=X THEN Backend SHALL upgrade connection thành WebSocket và bắt đầu streaming
5. WHEN WebSocket connection bị ngắt THEN Backend SHALL tự động cleanup worker sau 5 giây timeout

### Requirement 8

**User Story:** Là người dùng, tôi muốn UI panel TL detection được bố trí hợp lý và responsive, để dễ dàng theo dõi trên nhiều kích thước màn hình.

#### Acceptance Criteria

1. WHEN trang detection load THEN TL System SHALL hiển thị panel "Traffic Light ROI" ở vị trí bên dưới hoặc bên phải video chính
2. WHEN panel hiển thị THEN TL System SHALL chứa: preview image ROI, state label với màu tương ứng, và các button controls
3. WHEN màn hình nhỏ hơn 768px THEN TL System SHALL chuyển panel xuống dưới video (vertical layout)
4. WHEN màn hình lớn hơn 768px THEN TL System SHALL hiển thị panel bên phải video (horizontal layout)
5. WHEN không có ROI được chọn THEN TL System SHALL hiển thị placeholder text "No ROI selected" trong preview area

### Requirement 9

**User Story:** Là người dùng, tôi muốn thấy feedback rõ ràng khi thao tác với hệ thống, để biết các hành động của mình có thành công hay không.

#### Acceptance Criteria

1. WHEN người dùng chọn ROI thành công THEN TL System SHALL hiển thị toast notification "ROI selected"
2. WHEN detection bắt đầu THEN TL System SHALL hiển thị toast "Traffic light detection started"
3. WHEN detection dừng THEN TL System SHALL hiển thị toast "Traffic light detection stopped"
4. WHEN có lỗi từ backend THEN TL System SHALL hiển thị toast error với message cụ thể từ server
5. WHEN WebSocket mất kết nối THEN TL System SHALL hiển thị toast warning "Connection lost, retrying..."

### Requirement 10

**User Story:** Là hệ thống, tôi cần xử lý các edge cases và error conditions một cách graceful, để đảm bảo stability.

#### Acceptance Criteria

1. WHEN người dùng chọn ROI quá nhỏ (< 20x20 pixels) THEN TL System SHALL hiển thị warning "ROI too small, please select larger area"
2. WHEN YOLO TL model chưa được load THEN Backend SHALL tự động load model khi nhận ROI request lần đầu
3. WHEN video stream bị gián đoạn THEN Detection Worker SHALL pause và resume khi stream trở lại
4. WHEN Backend quá tải (CPU > 90%) THEN Backend SHALL tự động giảm TL detection frequency xuống 1.5s/lần
5. WHEN có exception trong Detection Worker THEN Backend SHALL log error, gửi error message qua WebSocket, và dừng worker gracefully
