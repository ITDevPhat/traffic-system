# WebSocket JSON Serialization - Quick Reference

## The Problem
When sending data over WebSocket with `json.dumps()`, Python cannot serialize certain types:
- `datetime` objects
- `Decimal` numbers
- SQLAlchemy ORM models
- UUID objects
- Custom classes

This causes: `TypeError: Object of type datetime is not JSON serializable`

## The Solution
Use FastAPI's `jsonable_encoder` before `json.dumps()`:

```python
from fastapi.encoders import jsonable_encoder
import json

# ❌ WRONG - Will fail with datetime
await websocket.send_text(json.dumps(data))

# ✅ CORRECT - Handles all types
safe_data = jsonable_encoder(data)
await websocket.send_text(json.dumps(safe_data))
```

## What jsonable_encoder Does

| Type | Converts To | Example |
|------|-------------|---------|
| `datetime` | ISO 8601 string | `"2025-12-09T16:42:13.492798"` |
| `Decimal` | float | `95.5` |
| `UUID` | string | `"550e8400-e29b-41d4-a716-446655440000"` |
| `Enum` | value | `"RED"` |
| Pydantic model | dict | `{"field": "value"}` |
| SQLAlchemy model | dict | `{"id": 1, "name": "test"}` |

## Applied in traffic_light_ws.py

All WebSocket sends now use `jsonable_encoder`:

1. **Info packet** (line 271)
2. **Frame headers** (line 592) - Contains violation timestamps
3. **ROI acknowledgments** (lines 652, 660)
4. **Error messages** (line 709)

## Alternative (Not Recommended)

Quick fix using `default=str`:
```python
json.dumps(data, default=str)
```

**Pros**: Simple, one-line change
**Cons**: Converts EVERYTHING to string, less type safety

## Best Practice

Always use `jsonable_encoder` for WebSocket/API responses containing:
- Database models
- Datetime fields
- Complex nested objects
- Pydantic schemas

This ensures consistent, predictable JSON output.
