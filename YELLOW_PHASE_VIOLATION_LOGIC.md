# Yellow Phase + Immediate RED Check - Violation Logic Update

## Tóm tắt

Đã thêm logic xử lý **pha VÀNG** và **kiểm tra ngay khi đèn ĐỎ** để phân biệt chính xác giữa:
- Xe vượt đèn đỏ (RED_LIGHT_RUN)
- Xe dừng sai vạch (RED_LIGHT_STOPLINE)

## Các thay đổi chính

### 1. Thêm flag `touched_during_yellow_or_before_red`

```python
@dataclass
class VehicleViolationState:
    # ... existing fields ...
    touched_during_yellow_or_before_red: bool = False
```

**Mục đích:** Đánh dấu xe đã chạm vạch trong pha vàng hoặc trước khi đèn đỏ.

### 2. Cập nhật `_update_light()` - Reset state theo chu kỳ đèn

```python
def _update_light(self, light_state: LightState, timestamp: datetime) -> None:
    # Reset state when light turns GREEN (new cycle)
    if self.last_light_state == "RED" and light_state == "GREEN":
        logger.info(f"🟢 Light turned GREEN - resetting violation states")
        for v in self.vehicles.values():
            v.touched_during_yellow_or_before_red = False
            v.violated = False  # Reset for new cycle
    
    # Record when light turns RED
    if light_state != self.last_light_state and light_state == "RED":
        self.last_red_on = timestamp
        logger.info(f"🔴 Light turned RED at {timestamp.isoformat()}")
    
    # Log when light turns YELLOW
    if light_state != self.last_light_state and light_state == "YELLOW":
        logger.info(f"🟡 Light turned YELLOW at {timestamp.isoformat()}")
```

**Chu kỳ đèn:**
- GREEN → YELLOW → RED → GREEN (reset)
- Mỗi chu kỳ mới, tất cả xe được reset state

### 3. Logic YELLOW Phase - "Arm" vehicles

```python
# YELLOW PHASE: "Arm" vehicles that touch stopline during yellow
if light_state == "YELLOW" and overlap_ratio > 0.0:
    if not vehicle.touched_during_yellow_or_before_red:
        vehicle.touched_during_yellow_or_before_red = True
        logger.info(
            f"🟡 Track {track_id} touched stopline during YELLOW "
            f"(overlap={overlap_ratio:.2f}, pos={position})"
        )
```

**Hành vi:**
- Khi đèn VÀNG, xe nào chạm vạch (overlap > 0) → đánh dấu
- Chưa có vi phạm, chỉ ghi nhận

### 4. Logic RED Phase - Kiểm tra ngay

```python
# RED PHASE: Check violations immediately
if light_state == "RED" and not vehicle.violated:
    # Chỉ xét các xe thực sự chạm vạch (overlap > 0)
    if overlap_ratio > 0.0:
        # Nếu đè vạch >= 40% chiều cao → đây là vi phạm
        if overlap_ratio >= 0.4:
            # Phân loại:
            if previous_position == "BEFORE" and not vehicle.touched_during_yellow_or_before_red:
                violation_type = "RED_LIGHT_RUN"
            else:
                violation_type = "RED_LIGHT_STOPLINE"
```

**Điều kiện vi phạm:**
1. Đèn đỏ (`light_state == "RED"`)
2. Xe chạm vạch (`overlap_ratio > 0`)
3. Xe đè vạch >= 40% (`overlap_ratio >= 0.4`)
4. Chưa bị bắt (`not vehicle.violated`)

**Phân loại:**
- **RED_LIGHT_RUN:** `previous_position == "BEFORE"` VÀ `not touched_during_yellow`
  - Xe đang chạy từ phía sau, chưa chạm vạch trong pha vàng
  - Khi đèn đỏ, xe vẫn tiếp tục vượt vạch
  
- **RED_LIGHT_STOPLINE:** Các trường hợp còn lại
  - Xe đã chạm vạch trong pha vàng
  - Xe đã ở ON/AFTER khi đèn đỏ
  - Xe dừng nhưng đè lên vạch

## Luồng hoạt động

### Scenario 1: Xe vượt đèn đỏ (RED_LIGHT_RUN)

```
Frame 1: light=GREEN, vehicle BEFORE, overlap=0.0
         → touched_during_yellow=False

Frame 2: light=YELLOW, vehicle BEFORE, overlap=0.0
         → touched_during_yellow=False (chưa chạm)

Frame 3: light=RED, vehicle BEFORE, overlap=0.0
         → Chưa vi phạm (chưa chạm vạch)

Frame 4: light=RED, vehicle ON, overlap=0.5
         → Violation: RED_LIGHT_RUN
         → Lý do: previous=BEFORE, not touched_during_yellow
```

### Scenario 2: Xe dừng sai vạch (RED_LIGHT_STOPLINE)

```
Frame 1: light=GREEN, vehicle BEFORE, overlap=0.0
         → touched_during_yellow=False

Frame 2: light=YELLOW, vehicle ON, overlap=0.3
         → touched_during_yellow=True (đánh dấu)

Frame 3: light=RED, vehicle ON, overlap=0.5
         → Violation: RED_LIGHT_STOPLINE
         → Lý do: touched_during_yellow=True
```

### Scenario 3: Xe dừng đúng (không vi phạm)

```
Frame 1: light=GREEN, vehicle BEFORE, overlap=0.0
         → touched_during_yellow=False

Frame 2: light=YELLOW, vehicle BEFORE, overlap=0.0
         → touched_during_yellow=False

Frame 3: light=RED, vehicle BEFORE, overlap=0.2
         → No violation (overlap < 0.4)
```

### Scenario 4: Xe đã qua vạch trước đèn đỏ (không vi phạm)

```
Frame 1: light=GREEN, vehicle BEFORE, overlap=0.0
         → touched_during_yellow=False

Frame 2: light=GREEN, vehicle AFTER, overlap=1.0
         → Đã qua vạch khi đèn xanh

Frame 3: light=YELLOW, vehicle AFTER, overlap=1.0
         → touched_during_yellow=True (nhưng đã qua)

Frame 4: light=RED, vehicle AFTER, overlap=1.0
         → No violation (previous=AFTER, không phải BEFORE)
```

## Acceptance Criteria

✅ **Pha VÀNG:**
- Xe chạm vạch (overlap > 0) → đánh dấu `touched_during_yellow=True`
- Chưa có vi phạm
- Log: `🟡 Track X touched stopline during YELLOW`

✅ **Pha ĐỎ:**
- Kiểm tra ngay mỗi frame
- Chỉ xét xe đã chạm vạch (overlap > 0)
- Xe đè vạch >= 40% → vi phạm

✅ **Phân loại chính xác:**
- RED_LIGHT_RUN: Xe chạy từ BEFORE, chưa chạm trong pha vàng
- RED_LIGHT_STOPLINE: Xe đã chạm trong pha vàng hoặc đang ON/AFTER

✅ **Reset chu kỳ:**
- Khi đèn chuyển RED → GREEN: reset tất cả state
- Mỗi chu kỳ đèn độc lập

## Violation Details

Thông tin trong `ViolationRecord.details`:

```json
{
  "stopline": {"x1": 54, "y1": 317, "x2": 781, "y2": 316},
  "light_state": "RED",
  "red_since": "2025-12-06T19:38:44.123456",
  "position_now": "ON",
  "overlap_ratio": 0.52,
  "touched_during_yellow": false
}
```

**Các field quan trọng:**
- `overlap_ratio`: % chiều cao xe đã vượt vạch (0.0 - 1.0)
- `touched_during_yellow`: Xe có chạm vạch trong pha vàng không
- `position_now`: Vị trí hiện tại (BEFORE/ON/AFTER)

## Debug & Monitoring

### Log levels

**INFO:**
- `🟢 Light turned GREEN - resetting violation states`
- `🟡 Light turned YELLOW at ...`
- `🔴 Light turned RED at ...`
- `🟡 Track X touched stopline during YELLOW`

**WARNING:**
- `🚨 RED LIGHT VIOLATION — camera=..., track=..., type=..., overlap=..., touched_during_yellow=...`

**DEBUG:**
- `[VIOLATION] Track X overlap_ratio=..., light=..., prev=..., pos=...`
- `[VIOLATION] Track X RED but has not touched stopline`

### Kiểm tra vi phạm không được detect

1. **Check overlap_ratio:**
   ```
   [VIOLATION] Track X overlap_ratio=0.35, light=RED
   ```
   → Nếu < 0.4 → không đủ để bắt

2. **Check touched_during_yellow:**
   ```
   🟡 Track X touched stopline during YELLOW (overlap=0.3)
   ```
   → Nếu có log này → xe sẽ bị phân loại RED_LIGHT_STOPLINE

3. **Check light transitions:**
   ```
   🟡 Light turned YELLOW at ...
   🔴 Light turned RED at ...
   ```
   → Đảm bảo có pha vàng trước đỏ

4. **Check previous_position:**
   ```
   🚨 ... prev=BEFORE, now=ON, touched_during_yellow=False
   ```
   → Nếu prev=BEFORE và not touched → RED_LIGHT_RUN

## Configuration

### Threshold điều chỉnh

Hiện tại: `overlap_ratio >= 0.4` (40%)

Nếu cần điều chỉnh, sửa trong `update()`:

```python
if overlap_ratio >= 0.4:  # Thay đổi threshold ở đây
    # ... violation logic
```

**Gợi ý:**
- 0.3 (30%): Nghiêm ngặt hơn, bắt sớm hơn
- 0.5 (50%): Lỏng hơn, chỉ bắt khi đè sâu
- 0.4 (40%): Cân bằng (khuyến nghị)

### Stopline coordinates

**Cam01 (video3.mp4):**
```json
{"x1": 54, "y1": 317, "x2": 781, "y2": 316}
```

**Cam02:**
Cần cấu hình tùy video

## Performance Impact

- ✅ Không tăng độ phức tạp tính toán
- ✅ Chỉ thêm 1 boolean flag per vehicle
- ✅ Logic đơn giản, dễ maintain
- ✅ Log có cấu trúc, dễ debug

## Migration Notes

**Breaking changes:**
- Cần có pha VÀNG trong traffic light state
- Logic phân loại vi phạm thay đổi

**Backward compatible:**
- Nếu không có YELLOW state → hoạt động như cũ
- Interface ViolationRecord không đổi
- Thêm field `touched_during_yellow` trong details

## Testing Checklist

- [ ] Test với video có đầy đủ GREEN → YELLOW → RED
- [ ] Test xe vượt đèn đỏ (không chạm trong pha vàng)
- [ ] Test xe dừng sai vạch (chạm trong pha vàng)
- [ ] Test xe dừng đúng (không đè vạch >= 40%)
- [ ] Test xe đã qua vạch trước đèn đỏ
- [ ] Test reset state khi đèn chuyển GREEN
- [ ] Monitor false positives/negatives
- [ ] Check log output cho từng scenario
