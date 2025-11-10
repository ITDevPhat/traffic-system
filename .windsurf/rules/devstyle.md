---
trigger: manual
---

# developer style rules

## code conventions
style: pep8
logging: emoji-prefixed
comment_language: vietnamese
docstring_language: english
import_style: explicit (no wildcard)

## structure
every service file must include:
  - init logs
  - device selection
  - fallback try/except
  - threaded start logs (🎬 Capture / 🎬 Infer / 🎬 Encode)
  - error handler with retry suggestion

## ai behavior
when writing code:
  - prefer diagnostic logging over silent failure
  - always explain GPU inference path in comments
  - never auto-convert .engine → .onnx
  - if editing realtime_binary_stream.py → keep capture/infer/encode intact
  - if exporting model → always use opset=11 for onnx
  - always write comments for performance tuning

## naming
variables_lowercase_with_underscore
classes_PascalCase
constants_UPPERCASE

## log format examples
✅ Model loaded successfully: {model_path} (device={device})
⚙️  Initialized BYTETracker (fps={fps}, buffer={buffer})
⚠️  OCR service disabled – TensorRT not available
❌ ONNX Runtime failed: {error}
🚀 Stream ready: {source}, {fps} FPS, {resolution}
