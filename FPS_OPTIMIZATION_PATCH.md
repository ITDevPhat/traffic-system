# FPS Optimization Patch - Traffic Light Detection

## 🔍 Problem Identified
- **Current FPS**: 6.5 FPS (very low)
- **Expected FPS**: 45 FPS
- **Root Cause**: Mismatch between frontend and backend FPS settings

## 🚀 Changes Applied

### 1. Frontend Settings Sync (traffic-light/page.jsx)
```diff
- target_fps: 45,      // Frontend wanted 45 FPS
- veh_detect_hz: 25,   // But detection only 25 FPS!
+ target_fps: 30,      // Synced with backend FIXED_DETECT_INTERVAL
+ veh_detect_hz: 30,   // Synced with target_fps for consistency
```

### 2. Backend Default Values (realtime_binary_stream.py)
```diff
- veh_detect_hz: int = 25,
+ veh_detect_hz: int = 30,
```

### 3. WebSocket Query Default (realtime_ws_binary.py)
```diff
- veh_detect_hz: int = Query(25, description="Vehicle detect frequency for keyframes (Hz)"),
+ veh_detect_hz: int = Query(30, description="Vehicle detect frequency for keyframes (Hz)"),
```

### 4. Performance Optimizations

#### A. Traffic Light Update Frequency
```diff
- tl_update_interval = 0.25  # Update TL every 250ms
+ tl_update_interval = 0.2   # Update TL every 200ms (5 FPS)
```

#### B. UI Update Throttling
```diff
- }, 200); // Update UI every 200ms
+ }, 300); // Update UI every 300ms (reduce React re-renders)
```

#### C. Log Entry Limits
```diff
- const trimmed = merged.slice(0, 200);
+ const trimmed = merged.slice(0, 100); // Reduced for better performance

- setViolations((prev) => [...newViolationEntries, ...prev].slice(0, 20));
+ setViolations((prev) => [...newViolationEntries, ...prev].slice(0, 10));
```

#### D. Canvas Rendering Optimization
- Pre-filter violation detections to reduce iterations
- Set canvas styles once for all violations instead of per violation
- Reduced redundant style changes

#### E. Performance Monitoring
```diff
- if self.frame_idx % 150 == 1:  # Every ~5 seconds at 30fps
+ if self.frame_idx % 90 == 1:   # Every ~3 seconds (more frequent monitoring)
```

## 📊 Expected Results

### Before Patch:
- **Frontend**: target_fps=45, veh_detect_hz=25
- **Backend**: FIXED_DETECT_INTERVAL=0.033 (30 FPS)
- **Actual FPS**: 6.5 FPS (severe bottleneck)

### After Patch:
- **Frontend**: target_fps=30, veh_detect_hz=30
- **Backend**: FIXED_DETECT_INTERVAL=0.033 (30 FPS)
- **Expected FPS**: ~30 FPS (consistent performance)

## 🎯 Performance Benefits

1. **Consistent FPS**: All components now target 30 FPS
2. **Reduced CPU Load**: Less frequent UI updates and optimized rendering
3. **Better Memory Usage**: Smaller log buffers
4. **Smoother Experience**: Eliminated FPS mismatch bottlenecks
5. **RTX 3050 Optimized**: Settings tuned for RTX 3050 4GB VRAM

## 🔧 Technical Notes

- **Why 30 FPS instead of 45 FPS?**
  - RTX 3050 with YOLO11s + ByteTrack + Violation Detection is more stable at 30 FPS
  - Avoids GPU memory pressure and thermal throttling
  - Provides consistent performance without frame drops

- **Backend FIXED_DETECT_INTERVAL remains 0.033s**
  - This ensures stable 30 FPS detection pipeline
  - Prevents adaptive throttling oscillations
  - Optimized for RTX 3050 hardware capabilities

## 🚀 Next Steps

1. **Test the patch**: Restart both frontend and backend
2. **Monitor FPS**: Should see ~30 FPS consistently
3. **Fine-tune if needed**: Can adjust veh_detect_hz between 25-35 based on performance
4. **GPU monitoring**: Watch GPU utilization and temperature

## 📝 Rollback Instructions

If performance degrades, revert these files:
- `src/app/(admin)/detection/traffic-light/page.jsx`
- `traffic-server/app/services/realtime_binary_stream.py`
- `traffic-server/app/routers/realtime_ws_binary.py`
- `traffic-server/app/routers/traffic_light_ws.py`

---
**Patch Applied**: December 11, 2025
**Target Performance**: 30 FPS stable (RTX 3050 optimized)