# Summary

## Changes Implemented
- Tracked per-track violation snapshots (first entry and best view) and plate OCR results inside `RedLightViolationEngine`, and exposed them in violation details.
- Added an OCR helper `recognize_plate_from_crop` that reuses the existing OCR engine to return `(plate_text, plate_conf)` from a BGR crop.
- Integrated license plate OCR into the traffic-light WebSocket pipeline so violations and detections carry plate text/confidence derived from recorded snapshots.

## API & Payload Notes
- `RedLightViolationEngine.update` now accepts an optional `frame_index` to align snapshots with incoming frames.
- WebSocket `/api/traffic-light/realtime` payloads:
  - Each detection may include `plate` (`{text, conf}`) plus `plate_text` and `plate_conf` mirrors when OCR runs.
  - `header["violations"]` entries include snapshot metadata (`first_in_region_frame`, `first_in_region_bbox`, `best_view_frame`, `best_view_bbox`) and OCR results (`plate_text`, `plate_conf`).
- OCR helper usage: `recognize_plate_from_crop(crop_bgr)` returns a tuple `(text | None, confidence | None)` and skips gracefully when OCR is unavailable or the crop is empty.
