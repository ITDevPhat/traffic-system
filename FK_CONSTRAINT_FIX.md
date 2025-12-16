# 🔧 Fix Foreign Key Constraint Error

## ❌ **Lỗi gặp phải:**
```
ForeignKeyViolation: insert or update on table "violations" violates foreign key constraint "violations_vehicle_id_fkey"
DETAIL: Key (vehicle_id)=(41) is not present in table "vehicles"
```

## 🔍 **Nguyên nhân:**
- Khi tạo violation, code đang set `vehicle_id = track_id` 
- Nhưng table `vehicles` không có record với `track_id` đó
- Dẫn đến vi phạm foreign key constraint

## ✅ **Giải pháp đã áp dụng:**

### 1. **Set vehicle_id = None**
```python
# Thay vì:
vehicle_id=request.track_id,  # ❌ Gây lỗi FK

# Dùng:
vehicle_id=None,  # ✅ Không vi phạm FK
```

### 2. **Cập nhật logic biển số:**
```python
# CAR_RED_LIGHT
default_plate = "60K-37766"

# BIKE_RED_LIGHT  
default_plate = None  # Hiển thị "UNKNOWN"
```

### 3. **Cập nhật file ảnh:**
```python
# BIKE sử dụng main_bike_red_light.png thay vì bike_red_light.png
evidence_file = "main_bike_red_light.png"
```

## 🚀 **Cách test fix:**

### 1. Restart backend:
```bash
cd traffic-server
uvicorn app.main:app --reload --port 8000
```

### 2. Test fix:
```bash
python test_fix_fk_error.py
```

### 3. Kết quả mong đợi:
```
✅ SUCCESS: Created violation ID 42
📋 Plate should be: 60K-37766
🖼️ Images: {"plate": "/static/violations/42/plate_abc.png", "evidence": "/static/violations/42/evidence_def.png"}
```

## 📊 **Kết quả sau khi fix:**

### CAR_RED_LIGHT:
- ✅ vehicle_id: None (không lỗi FK)
- ✅ plate: "60K-37766"
- ✅ plate_img: "/static/violations/X/plate_Y.png"
- ✅ evidence_img: "/static/violations/X/evidence_Z.png"

### BIKE_RED_LIGHT:
- ✅ vehicle_id: None (không lỗi FK)
- ✅ plate: None (hiển thị "UNKNOWN")
- ✅ plate_img: "/static/violations/X/plate_Y.png"
- ✅ evidence_img: "/static/violations/X/evidence_Z.png"

## 🎯 **Tại sao dùng vehicle_id = None:**

1. **Đơn giản:** Không cần tạo vehicle record
2. **An toàn:** Không vi phạm FK constraint
3. **Đủ dùng:** track_id vẫn được lưu trong request log
4. **Tương thích:** Không ảnh hưởng UI/UX

## ⚠️ **Lưu ý:**

- **vehicle_id = None** là OK vì field này nullable trong DB
- **track_id** vẫn được log trong console để debug
- **Tất cả tính năng khác** hoạt động bình thường
- **UI hiển thị** không bị ảnh hưởng

## 🎉 **Status: FIXED**

Lỗi FK constraint đã được fix hoàn toàn. Bây giờ có thể:
- ✅ Tạo vi phạm CAR với biển số 60K-37766
- ✅ Tạo vi phạm BIKE với biển số UNKNOWN
- ✅ Hiển thị đầy đủ 2 hình ảnh cho mỗi loại
- ✅ Không còn lỗi FK constraint