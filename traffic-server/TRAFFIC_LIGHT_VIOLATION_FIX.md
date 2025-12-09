# Traffic Light Violation Fix - Complete Resolution

## Problems Fixed

### 1. ValidationError (FIXED)
WebSocket `/api/traffic-light/realtime` was throwing ValidationError when persisting violations to DB:
```
1 validation error for TrafficLightViolationIn
plate
  Input should be a valid string [type=string_type, input_value={'text': None, 'conf': None}, input_type=dict]
```

**Root Cause**: `plate_text` was extracted as dict but passed to Pydantic model expecting `Optional[str]`.

### 2. JSON Serialization Error (FIXED)
After fixing validation, WebSocket was failing with:
```
⚠️ Send error: Object of type datetime is not JSON serializable
```

**Root Cause**: `header` dict contained `datetime` objects (from `violation.timestamp`, `created_at`, etc.) that `json.dumps()` cannot serialize.

## Solutions Applied

### 1. Fixed Plate Extraction
```python
# Extract plate text from dict or use plate_text field
plate_data = matching_det.get("plate") if matching_det else None
if isinstance(plate_data, dict):
    plate_text = plate_data.get("text")
    plate_conf = plate_data.get("conf")
else:
    plate_text = matching_det.get("plate_text") if matching_det else None
    plate_conf = matching_det.get("plate_conf") if matching_det else None
```

### 2. Fixed Payload Construction
```python
plate=plate_text if plate_text else None,  # Must be string or None, not dict
confidence=plate_conf if plate_conf is not None else det_confidence,
```

### 3. Fixed JSON Serialization (CRITICAL)
Added `jsonable_encoder` from FastAPI to handle datetime and other non-JSON-serializable types:

```python
from fastapi.encoders import jsonable_encoder

# Before (BROKEN):
await websocket.send_text(json.dumps(header))

# After (FIXED):
safe_header = jsonable_encoder(header)  # Converts datetime → ISO string
await websocket.send_text(json.dumps(safe_header))
```

Applied to all WebSocket sends:
- Info packet (line 271)
- Frame headers with violations (line 592)
- ROI acknowledgments (lines 652, 660)
- Error messages (line 709)

### 4. Improved Error Handling
- DB persist errors are now non-blocking
- Added clear logging: `[TL-VIOLATION-DB] ✅ Saved` or `⚠️ Failed to persist`
- WebSocket send is in separate try/except, never blocked by DB errors

## Results
✅ No more ValidationError for `TrafficLightViolationIn.plate`
✅ No more "Object of type datetime is not JSON serializable" error
✅ WebSocket successfully sends violation packets to frontend
✅ Frontend receives violations with proper highlighting (red bbox + label)
✅ Plate can be None (when OCR not available) without breaking the flow
✅ DB persist errors don't block WebSocket communication

## Technical Details

### Why jsonable_encoder?
FastAPI's `jsonable_encoder` automatically converts:
- `datetime` → ISO 8601 string (`"2025-12-09T16:42:13.492798"`)
- `Decimal` → float
- SQLAlchemy models → dict
- UUID → string
- Enum → value
- Pydantic models → dict

This ensures all data sent over WebSocket is JSON-serializable.

### Alternative (Quick Fix)
If you don't want to use `jsonable_encoder`, you can use:
```python
json.dumps(header, default=str)
```
But this is less controlled - it converts ALL non-serializable types to string.

## Testing
See `VERIFICATION_CHECKLIST.md` for complete testing steps.
