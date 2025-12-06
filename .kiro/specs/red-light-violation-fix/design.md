# Design Document - Red Light Violation Backend Integration

## Overview

This design integrates the `RedLightViolationEngine` into the backend detection pipeline to compute violations server-side and broadcast them via WebSocket to the frontend.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Frontend (page.jsx)                       │
│  - Receives violations via WebSocket                         │
│  - Renders red bbox + "VI PHẠM" label                       │
└─────────────────────────────────────────────────────────────┘
                              ▲
                              │ WebSocket
                              │
┌─────────────────────────────────────────────────────────────┐
│              traffic_light_ws.py                             │
│  - Streams frames + header with violations                   │
│  - Calls violation_manager.compute_violations()              │
└─────────────────────────────────────────────────────────────┘
                              ▲
                              │
┌─────────────────────────────────────────────────────────────┐
│           ViolationManager (NEW)                             │
│  - Manages RedLightViolationEngine per camera               │
│  - Loads stopline from storage                               │
│  - Calls engine.update(tracks, light_state, timestamp)      │
└─────────────────────────────────────────────────────────────┘
                              ▲
                              │
┌─────────────────────────────────────────────────────────────┐
│         RedLightViolationEngine                              │
│  - Computes penetration ratio                                │
│  - Returns ViolationRecord list                              │
└─────────────────────────────────────────────────────────────┘
```

## Components and Interfaces

### 1. ViolationManager (NEW)

**Location:** `traffic-server/app/violations/violation_manager.py`

**Purpose:** Manage violation engines per camera

**Interface:**
```python
class ViolationManager:
    def __init__(self):
        self.engines: Dict[str, RedLightViolationEngine] = {}
        self.stoplines: Dict[str, Dict] = {}
    
    def set_stopline(self, camera_id: str, stopline: Dict) -> None:
        """Set or update stopline for camera"""
        
    def compute_violations(
        self, 
        camera_id: str, 
        tracks: List[Dict], 
        light_state: str,
        timestamp: datetime
    ) -> List[ViolationRecord]:
        """Compute violations for current frame"""
```

### 2. Stopline Storage (NEW)

**Location:** `traffic-server/app/violations/stopline_storage.py`

**Purpose:** Store stopline coordinates per camera

**Interface:**
```python
# In-memory storage
stoplines_storage: Dict[str, Dict[str, float]] = {}

def save_stopline(camera_id: str, stopline: Dict) -> None:
    """Save stopline coordinates"""
    
def get_stopline(camera_id: str) -> Optional[Dict]:
    """Get stopline for camera"""
```

### 3. Integration Points

#### A) traffic_light_router.py
- Add endpoint `/api/violations/stopline` to save stopline
- Store in `stoplines_storage`
- Notify `ViolationManager` to update engine

#### B) traffic_light_ws.py
- Import `ViolationManager`
- Call `compute_violations()` each frame
- Add violations to header before sending

#### C) Frontend (page.jsx)
- Read `violations` from packet header
- Render red bbox overlay for violated tracks

## Data Models

### Stopline Format
```python
{
    "x1": float,  # pixel coordinates
    "y1": float,
    "x2": float,
    "y2": float
}
```

### Track Format (from YOLO/ByteTrack)
```python
{
    "track_id": int,
    "bbox": [x1, y1, x2, y2],  # pixel coordinates
    "class_id": int,
    "class_name": str
}
```

### Violation Format (WebSocket)
```python
{
    "track_id": int,
    "bbox": [x1, y1, x2, y2],
    "penetration_ratio": float,
    "timestamp": str  # ISO format
}
```

## Error Handling

1. **No stopline configured**: Skip violation detection, log warning
2. **Invalid bbox**: Skip that track, continue with others
3. **Engine error**: Catch exception, log error, return empty violations list
4. **Light state unknown**: Treat as GREEN (no violations)

## Testing Strategy

### Unit Tests
- Test `ViolationManager.compute_violations()` with mock data
- Test stopline storage save/get operations
- Test coordinate scaling if needed

### Integration Tests
- Test full pipeline: tracks → violations → WebSocket → frontend
- Test stopline update flow
- Test violation reset when light changes to GREEN

## Performance Considerations

- **O(N) per frame** where N = number of tracks
- **Memory**: One engine per camera (lightweight)
- **No blocking**: All operations synchronous, fast (<1ms per frame)

## Migration Notes

- Frontend logic already updated (penetration-based)
- Backend engine ready (red_light_engine.py)
- Only need to wire components together
- No breaking changes to existing APIs
