# Implementation Tasks - Red Light Violation Backend Integration

## Summary

Integrate RedLightViolationEngine into backend pipeline to compute violations server-side and broadcast via WebSocket.

- [x] 1. Create ViolationManager
- [x] 2. Add stopline API endpoints
- [x] 3. Integrate violations into WebSocket stream
- [x] 4. Update frontend to use new API
- [ ] 5. Test end-to-end flow
- [ ] 6. Verify violations display correctly

## Completed Tasks

### 1. Create ViolationManager ✅
- Created `traffic-server/app/violations/violation_manager.py`
- Manages RedLightViolationEngine instances per camera
- Provides `set_stopline()` and `compute_violations()` methods
- _Requirements: 1.1, 2.1, 3.1_

### 2. Add Stopline API Endpoints ✅
- Added `POST /api/violations/stopline` endpoint
- Added `GET /api/violations/stopline/{camera_id}` endpoint
- Integrated with ViolationManager
- _Requirements: 3.2, 4.1_

### 3. Integrate Violations into WebSocket Stream ✅
- Modified `traffic_light_ws.py` to compute violations each frame
- Added violations to header before sending
- Format: `{"track_id": int, "bbox": [...], "penetration_ratio": float, "timestamp": str}`
- _Requirements: 3.1, 3.5_

### 4. Update Frontend API Call ✅
- Fixed stopline save format (flat instead of nested)
- Sends `{camera_id, x1, y1, x2, y2}` to backend
- _Requirements: 3.2_

## Testing Tasks

### 5. Test End-to-End Flow
**Steps:**
1. Start backend server
2. Open frontend traffic light page
3. Upload video3.mp4 (auto-loads stopline)
4. Start detection
5. Draw stopline if not auto-loaded
6. Click "Save" stopline button
7. Verify console logs show stopline saved
8. Wait for red light
9. Verify violations computed in backend logs
10. Verify violations sent via WebSocket

**Expected Results:**
- Backend logs: `✅ Stopline set for camera cam01`
- Backend logs: `🚨 X violations detected for camera cam01`
- Frontend console: Violations received in packet
- Frontend UI: Red bbox + "VI PHẠM" label on violating vehicles

### 6. Verify Violations Display Correctly
**Test Cases:**
1. **No penetration**: Vehicle stops before stopline → No violation
2. **< 50% penetration**: Vehicle slightly crosses → No violation
3. **>= 50% penetration**: Vehicle crosses halfway → Violation ✅
4. **Green light**: Vehicle crosses stopline → No violation
5. **Multiple vehicles**: All computed independently
6. **Violation reset**: Light changes GREEN → All violations reset

## Notes

- Frontend already has penetration-based logic (works independently)
- Backend violations are additional validation/logging
- Both frontend and backend use same penetration rule (>= 50%)
- Violations are computed per-frame, O(N) complexity
