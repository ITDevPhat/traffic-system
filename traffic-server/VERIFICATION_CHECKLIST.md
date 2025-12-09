# Traffic Light Violation - Verification Checklist

## Pre-Test Setup
- [ ] Ensure traffic-server is running
- [ ] Have video3.mp4 ready for cam01
- [ ] Clear any old logs

## Test Steps

### 1. Start Traffic Server
```bash
cd traffic-server
python -m uvicorn app.main:app --reload --port 8000
```

### 2. Load Video and Trigger Violation
- Open frontend
- Connect to camera cam01
- Load video3.mp4
- Play until red light violation occurs

### 3. Check Logs - Expected Behavior

#### ✅ Should See:
```
🚨 RED LIGHT VIOLATION — camera=cam01, track=315, type=RED_LIGHT_RUN
🚨 1 violations detected for camera cam01
[TL-PLATE] cam=cam01, track=315, plate=None, conf=None, violation=RED_LIGHT_RUN
[TL-VIOLATION-DB] ✅ Saved: camera=cam01, type=RED_LIGHT_RUN, frame=XXX, plate=None, bbox=(...)
```

#### ❌ Should NOT See:
```
1 validation error for TrafficLightViolationIn
plate
  Input should be a valid string [type=string_type, input_value={'text': None, 'conf': None}, input_type=dict]

⚠️ Send error: Object of type datetime is not JSON serializable
```

### 4. Check Frontend

#### ✅ Should See:
- [ ] Violation detected and highlighted
- [ ] Red bounding box around violating vehicle
- [ ] Violation label displayed
- [ ] Track ID visible
- [ ] Plate field shows "None" or empty (if OCR not available)

#### ❌ Should NOT See:
- [ ] Missing violation highlight
- [ ] WebSocket connection errors
- [ ] Blank or frozen video

### 5. Check Database (Optional)
```sql
SELECT violation_id, camera_name, violation_type_code, plate, timestamp 
FROM violations 
WHERE violation_type_code LIKE '%RED_LIGHT%' 
ORDER BY timestamp DESC 
LIMIT 5;
```

Expected:
- [ ] New violation record exists
- [ ] `plate` field is NULL or string (not dict/JSON)
- [ ] `evidence_img` contains URLs to saved images

## Common Issues

### If OCR Service Not Available
**Expected**: Log shows `[PLATE-OCR] OCR service not available, skipping plate recognition`
**Result**: Violation still saved with `plate=None` ✅

### If DB Connection Fails
**Expected**: Log shows `[TL-VIOLATION-DB] ⚠️ Failed to persist violation (non-blocking)`
**Result**: Frontend still receives violation via WebSocket ✅

### If Validation Error Still Occurs
**Check**:
1. Verify `traffic_light_ws.py` has the latest changes
2. Restart traffic-server
3. Check Python version compatibility
4. Review full stack trace in logs

## Success Criteria
- [x] No ValidationError in logs
- [x] WebSocket sends violation packets
- [x] Frontend displays violations correctly
- [x] DB persists violations (when available)
- [x] System handles OCR unavailability gracefully
- [x] System handles DB errors gracefully
