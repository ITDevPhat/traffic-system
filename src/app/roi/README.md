# Advanced ROI Editor

Giao diện chỉnh sửa ROI (Region of Interest) nâng cao cho hệ thống giám sát giao thông.

## Tính năng

### 15 Loại ROI
- **Detection Zone**: Vùng phát hiện phương tiện
- **Lane Types**: Lane Car, Lane Bike, Lane Bus, Lane Truck
- **Forbidden Area**: Vùng cấm
- **Direction Zones**: Wrong Direction, Direction Zone
- **Lines**: Stopline, Solid Line, Dashed Line
- **Crosswalk**: Vạch sang đường
- **Traffic Light**: Vị trí đèn giao thông
- **Entry/Exit**: Vehicle Entry, Vehicle Exit

### Chức năng chính

#### 1. Vẽ ROI
- **Polygon**: Click để thêm điểm, double-click hoặc click điểm đầu để đóng
- **Line**: Click 2 điểm (tự động hoàn thành)
- **Rectangle**: Click 2 góc (tự động hoàn thành)
- **Snap Circle**: Hiển thị khi gần điểm đầu tiên (< 12px)

#### 2. Quản lý ROI
- **Add**: Tạo ROI mới với drawing mode
- **Edit**: Chỉnh sửa thông tin ROI
- **Delete**: Xóa ROI (có confirm dialog)
- **Clone**: Nhân bản ROI với suffix "_copy"
- **Select**: Click vào ROI trên canvas để chọn

#### 3. Metadata
- **Direction Zone/Wrong Direction**: Cấu hình heading range (0-360°)
- **Lane Types**: Chọn allowed vehicle classes (car, bus, truck, motorbike)
- **Traffic Light**: Thêm description

#### 4. Import/Export
- **Export JSON**: Download ROI config dưới dạng JSON
- **Import JSON**: Upload và load ROI config từ file JSON
- **JSON Preview**: Xem JSON của ROI đang chọn

#### 5. ROI Legend
- Hiển thị 15 loại ROI với màu sắc
- Filter theo loại (click để filter)
- Hover để highlight tất cả ROI cùng loại
- Toggle show/hide (lưu vào localStorage)

#### 6. Keyboard Shortcuts
- **Escape**: Cancel drawing
- **Enter**: Finish drawing (nếu hợp lệ)
- **Delete**: Xóa ROI đang chọn

## Cấu trúc Components

```
src/
├── types/
│   └── roi.ts                    # TypeScript types & constants
├── utils/
│   └── roiShape.ts              # Shape conversion utilities
├── store/
│   └── useRoiStore.ts           # Zustand store
├── services/
│   └── roiService.ts            # Backend API integration
├── components/
│   ├── ROIOverlay.tsx           # Canvas rendering
│   ├── ROIEditorPanel.tsx       # Editor panel
│   ├── ROIDrawingControls.tsx  # Drawing controls
│   └── ROILegend.tsx            # Legend component
└── app/
    └── roi/
        └── page.tsx             # Main page
```

## API Format

### Backend Request (Save)
```json
{
  "camera_id": "CAM_Q7_01",
  "items": [
    {
      "id": "uuid",
      "roi_type": "stopline",
      "name": "Stopline 1",
      "coordinates": [[100, 200], [500, 200]],
      "color": "#FF0000",
      "metadata": {},
      "created_at": "2025-11-13T...",
      "updated_at": "2025-11-13T..."
    }
  ]
}
```

### Backend Response (Load)
```json
{
  "items": [
    {
      "id": "uuid",
      "roi_type": "lane_car",
      "name": "Lane Car 1",
      "coordinates": [[50, 100], [200, 100], [200, 300], [50, 300]],
      "color": "#4CAF50",
      "metadata": {
        "allowed_classes": ["car", "bus"]
      }
    }
  ]
}
```

## Validation Rules

- **Name**: Tối thiểu 3 ký tự
- **Line**: Đúng 2 điểm
- **Rectangle**: Đúng 2 điểm (sẽ convert thành 4)
- **Polygon**: Tối thiểu 3 điểm
- **Heading**: 0-360 degrees

## Color Mapping

Mỗi loại ROI có màu mặc định:
- Detection Zone: Cyan (#00FFFF)
- Lane Car: Green (#4CAF50)
- Stopline: Red (#FF0000)
- Traffic Light: White (#FFFFFF)
- ... (xem ROI_COLORS trong roi.ts)

## Usage

1. Chọn camera từ dropdown
2. Click "Start Drawing" để vẽ ROI mới
3. Vẽ ROI trên canvas theo hướng dẫn
4. Click "Finish" hoặc Enter để hoàn thành
5. Click "Save ROIs" để lưu vào backend

## Notes

- Không thay đổi backend code (traffic-server/)
- JSON format tương thích 100% với backend hiện tại
- Sử dụng Zustand cho state management
- Sử dụng React Bootstrap cho UI components
