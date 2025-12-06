# Requirements Document - Red Light Violation Logic Fix

## Introduction

This specification addresses a critical bug in the red-light violation detection system. The current implementation incorrectly flags vehicles as violators when they are merely touching or near the stopline during a red light, rather than only flagging vehicles that actively cross the stopline after the light turns red.

## Glossary

- **System**: The traffic violation detection system
- **Vehicle**: Any tracked object (car, bus, truck, bike) detected by YOLO
- **Stopline**: A straight line defined by two points (x1, y1) → (x2, y2) marking the legal stopping position
- **Bbox**: Bounding box coordinates [x1, y1, x2, y2] of a detected vehicle
- **Penetration**: The amount a vehicle's bbox extends beyond the stopline
- **Track ID**: Unique identifier for a tracked vehicle across frames
- **Light State**: Current traffic light status (RED, GREEN, YELLOW)

## Requirements

### Requirement 1: Correct Violation Detection Rule

**User Story:** As a traffic enforcement officer, I want the system to only flag vehicles that cross the stopline during a red light, so that I can issue accurate violations.

#### Acceptance Criteria

1. WHEN the light state is RED AND a vehicle's bbox penetrates the stopline by >= 50% of its width, THEN the System SHALL mark that vehicle as a violation
2. WHEN the light state is GREEN or YELLOW, THEN the System SHALL NOT mark any vehicle as a violation regardless of position
3. WHEN a vehicle's bbox penetration is < 50% of its width, THEN the System SHALL NOT mark it as a violation even if the light is RED
4. WHEN calculating penetration, the System SHALL use the vehicle's bbox bottom edge (y_max) compared to stopline Y coordinate
5. WHEN a vehicle is already marked as violated, the System SHALL NOT mark it again for the same red light cycle

### Requirement 2: Penetration Calculation

**User Story:** As a system developer, I want accurate penetration calculation, so that violation detection is consistent and fair.

#### Acceptance Criteria

1. WHEN calculating penetration depth, the System SHALL compute: depth = bbox_bottom_y - stopline_y
2. WHEN normalizing penetration, the System SHALL compute: penetration_ratio = depth / bbox_width
3. WHEN bbox_bottom_y <= stopline_y, the System SHALL set penetration_ratio = 0
4. WHEN penetration_ratio >= 0.5, the System SHALL flag as violation
5. WHEN stopline is defined by two points, the System SHALL use the average Y coordinate: stopline_y = (y1 + y2) / 2

### Requirement 3: Violation Data Output

**User Story:** As a frontend developer, I want structured violation data, so that I can display violations accurately to users.

#### Acceptance Criteria

1. WHEN a violation is detected, the System SHALL output a violation object containing track_id, bbox, violation_type, and penetration_ratio
2. WHEN sending violation data to frontend, the System SHALL include timestamp of violation
3. WHEN a vehicle is marked as violated, the System SHALL maintain violation status until light changes to non-RED
4. WHEN light changes from RED to GREEN/YELLOW, the System SHALL reset all violation flags
5. WHEN outputting violations, the System SHALL use format: {"track_id": int, "bbox": [x1,y1,x2,y2], "violation_type": "RED_LIGHT", "penetration_ratio": float, "timestamp": str}

### Requirement 4: Remove Old Logic

**User Story:** As a system maintainer, I want clean, simple violation logic, so that the codebase is maintainable.

#### Acceptance Criteria

1. WHEN implementing new logic, the System SHALL remove all BEFORE/AFTER/ON_LINE position tracking
2. WHEN implementing new logic, the System SHALL remove temporal "at_red_start" state tracking
3. WHEN implementing new logic, the System SHALL remove polygon ROI intersection checks for stopline
4. WHEN implementing new logic, the System SHALL use only: stopline_y, bbox coordinates, light state, and penetration ratio
5. WHEN a vehicle leaves the frame, the System SHALL clean up its violation state

### Requirement 5: Performance and Accuracy

**User Story:** As a system operator, I want fast and accurate violation detection, so that the system can handle real-time traffic monitoring.

#### Acceptance Criteria

1. WHEN processing each frame, the System SHALL compute violations in < 10ms per frame
2. WHEN multiple vehicles are present, the System SHALL process all vehicles independently
3. WHEN a vehicle bbox is invalid (x1 >= x2 or y1 >= y2), the System SHALL skip that vehicle and log a warning
4. WHEN stopline coordinates are invalid, the System SHALL log an error and disable violation detection
5. WHEN light state is UNKNOWN, the System SHALL treat it as GREEN (no violations)
