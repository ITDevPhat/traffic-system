# Red Light Violation Logic Update - Overlap-Based Detection

## Tóm tắt thay đổi

Đã cập nhật logic phát hiện vi phạm đèn đỏ từ position-based sang **overlap-based** detection, phù hợp với cả cam01 và cam02 (hướng xe chạy từ dưới lên trên).

## Các thay đổi chính

### 1. Thêm hàm `_stopline_overlap_ratio()`
```python
def _stopline_overlap_ratio(self, bbox: Tuple[float, float, float, float]) -> float:
    """
    Tính % chiều cao bbox đã vượt qua vạch dừng.
    
    Returns:
        - 0.0: chưa chạm vạch
        - 0.4: đầu xe vượt vạch 40% chiều cao
        - >=0.4: đè vạch đủ để bắt lỗi
    """
```

**Logic:**
- Hướng xe: dưới → trên (y giảm dần)
- Đầu xe = `y_top` (bbox[1])
- Vạch dừng = `line_y` (stopline_rect["y1"])
- Độ sâu vượt vạch: `depth = line_y - y_top`
- Overlap ratio: `depth / bbox_height`

### 2. Cập nhật `_position_vs_stopline()`
Đơn giản hóa logic cho hướng dưới → trên:
- `BEFORE`: `y > line_y` (dưới vạch)
- `ON`: `|y - line_y| < 10px` (trên vạch)
- `AFTER`: `y < line_y` (trên vạch)

### 3. Logic vi phạm mới (RULE duy nhất)

**Điều kiện vi phạm:**
```python
if (
    light_state == "RED"
    and overlap_ratio >= 0.4
    and not vehicle.violated
):
    # Phân loại:
    if previous_position == "BEFORE":
        violation_type = "RED_LIGHT_RUN"  # Vượt đèn đỏ
    else:
        violation_type = "RED_LIGHT_STOPLINE"  # Dừng sai vạch
```

**Loại bỏ:**
- ❌ `position_when_red` không còn dùng trong logic quyết định
- ❌ `touched` không còn dùng
- ❌ `_is_vehicle_stopped()` không còn cần
- ❌ `front_history` không còn cần

### 4. Phân loại vi phạm

#### RED_LIGHT_RUN (Vượt đèn đỏ)
- Xe từ `BEFORE` → `ON/AFTER` khi đèn đỏ
- Overlap >= 40%
- Ví dụ: Xe đang chạy, đèn đỏ, xe vẫn tiếp tục vượt vạch

#### RED_LIGHT_STOPLINE (Dừng sai vạch)
- Xe đã ở `ON/AFTER` khi đèn đỏ
- Overlap >= 40%
- Ví dụ: Xe dừng nhưng đè lên vạch dừng

### 5. Giảm log spam
- Chỉ log DEBUG khi `overlap_ratio > 0`
- Chỉ log INFO khi xe crossed và đèn đỏ
- Log WARNING khi phát hiện vi phạm

## Acceptance Criteria

✅ **Cam01 & Cam02 (cùng hướng dưới → trên):**

1. **Khi đèn đỏ:**
   - Xe đè vạch < 40% → KHÔNG bắt
   - Xe đè vạch >= 40%:
     - Từ BEFORE → RED_LIGHT_RUN
     - Đã ON/AFTER → RED_LIGHT_STOPLINE

2. **Không còn hiện tượng:**
   - ❌ Xe cũ đang đè vạch không bị bắt
   - ❌ Xe mới tới bị bắt bậy
   - ❌ Xe đã qua vạch trước khi đèn đỏ bị bắt sai

3. **Log sạch:**
   - Không spam mỗi frame
   - Chỉ log khi có vi phạm thực sự

## Test Cases

### Test 1: Xe vượt đèn đỏ
```
Frame 1: light=GREEN, vehicle BEFORE, overlap=0.0
Frame 2: light=RED, vehicle BEFORE, overlap=0.0
Frame 3: light=RED, vehicle ON, overlap=0.5
→ Violation: RED_LIGHT_RUN
```

### Test 2: Xe dừng sai vạch
```
Frame 1: light=GREEN, vehicle ON, overlap=0.6
Frame 2: light=RED, vehicle ON, overlap=0.6
→ Violation: RED_LIGHT_STOPLINE
```

### Test 3: Xe dừng đúng (không vi phạm)
```
Frame 1: light=GREEN, vehicle BEFORE, overlap=0.0
Frame 2: light=RED, vehicle BEFORE, overlap=0.0
Frame 3: light=RED, vehicle BEFORE, overlap=0.2 (< 40%)
→ No violation
```

### Test 4: Xe đã qua vạch trước đèn đỏ
```
Frame 1: light=GREEN, vehicle BEFORE, overlap=0.0
Frame 2: light=GREEN, vehicle AFTER, overlap=1.0
Frame 3: light=RED, vehicle AFTER, overlap=1.0
→ No violation (đã qua trước khi đèn đỏ)
```

## Stopline Configuration

### Cam01 (video3.mp4)
```json
{
  "x1": 54,
  "y1": 317,
  "x2": 781,
  "y2": 316
}
```

### Cam02
```json
{
  "x1": <tùy video>,
  "y1": <tùy video>,
  "x2": <tùy video>,
  "y2": <tùy video>
}
```

## Debug

Nếu vi phạm không được detect:

1. **Check overlap_ratio:**
   ```
   [VIOLATION] Track X overlap_ratio=0.35, light=RED
   ```
   → Nếu < 0.4 → không đủ để bắt

2. **Check light state:**
   ```
   🚦 Light turned RED at 2025-12-06T19:38:44
   ```
   → Đảm bảo đèn đỏ được nhận đúng

3. **Check stopline coordinates:**
   - Vạch ngang: `y1 ≈ y2`
   - Xe chạy từ dưới lên: `y_vehicle > y_stopline` ban đầu

4. **Check violation flag:**
   - Mỗi xe chỉ bị bắt 1 lần: `vehicle.violated = True`
   - Reset khi xe mất khỏi frame (5 giây)

## Migration Notes

**Breaking changes:**
- Logic vi phạm hoàn toàn mới
- `position_when_red` không còn ảnh hưởng đến quyết định
- Threshold mới: 40% overlap (có thể điều chỉnh)

**Backward compatible:**
- Interface `ViolationRecord` không đổi
- Interface `ViolationManager` không đổi
- Thêm field `overlap_ratio` trong `details`

## Performance

- ✅ Không tăng độ phức tạp tính toán
- ✅ Giảm log spam → giảm I/O
- ✅ Logic đơn giản hơn → dễ maintain
- ✅ Loại bỏ code không dùng → giảm memory

## Next Steps

1. Test với video thực tế (cam01 & cam02)
2. Điều chỉnh threshold nếu cần (hiện tại: 0.4 = 40%)
3. Monitor false positives/negatives
4. Update frontend để hiển thị `overlap_ratio` trong violation details
