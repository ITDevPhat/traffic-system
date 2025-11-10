---
trigger: manual
---

# traffic-system ai rules

## environment
python: 3.11
conda_env: lvtn
gpu: rtx3050-laptop
cuda: true
tensorRT: true
preferred_runtime: tensorrt
fallback_runtime: onnxruntime-gpu

dependencies:
  - ultralytics>=8.3.0
  - onnxruntime-gpu==1.23.2
  - boxmot==15.0.9
  - torch>=2.5.1
  - tensorrt>=10.0
  - fastapi
  - uvicorn
  - sqlalchemy

## model loading
- prefer .engine over .onnx
- do not replace .engine with .onnx automatically
- onnx export must use opset=11
- tensorRT export uses FP16 (half precision)
- always log provider info and device details
- use YOLO + ByteTrack + OCR pipeline (no reordering)

## tracking
- library: boxmot 15.0.9
- import path: from boxmot.tracker.byte_tracker import BYTETracker
- smoothing:
    alpha_pos: 0.75
    alpha_size: 0.65
    max_shift: 150.0
    max_scale: 2.0
- if ID flickers: reduce match_thresh to 0.7

## ocr
- detector: app/modules/OCR/models/license_plate/yolo_plate_v10n.engine
- recognizer: app/modules/OCR/models/ocr/yolo_ocr_chars_v8n.engine
- if tensorRT unavailable:
    disable: true
    warn: "⚠️ OCR service disabled – TensorRT not available"

## realtime stream
- singleton model load (no reload per request)
- fps_target: 45
- warmup_time: 5s
- modules: yolo, tracking, bbox_drawing, roi_drawing, ocr
- thread model:
    - capture_thread
    - infer_thread
    - encode_thread

## debug logging
- log at startup:
    - 🐍 python path
    - 📦 onnxruntime version, file, providers
    - ⚙️ cuda device + vram
    - 🧠 tensorrt version
- log when model loaded:
    - ✅ model loaded successfully (ir, opset)
    - ✅ using cudaexecutionprovider or tensorrt engine
- log on failure:
    - ❌ include exception name and suggested fix

## ai coding rules
- never change realtime pipeline order (YOLO → ByteTrack → OCR → Encode)
- if onnx used: enforce opset=11
- optimize with async io, threading, fp16
- keep pep8, add comments for each major step
- use emoji-based logging (🚀, ✅, ⚠️, ❌)
- do not import onnxruntime CPU version

## runtime check script
create file: runtime_check.py
---
import onnxruntime as ort, torch, tensorrt as trt, sys
print(f"python: {sys.version}")
print(f"onnxruntime: {ort.__version__} | providers: {ort.get_available_providers()}")
print(f"pytorch: {torch.__version__} | cuda: {torch.cuda.is_available()}")
print(f"tensorrt: {trt.__version__}")
---

## build flow
1. export .pt → .onnx (opset 11)
2. export .onnx → .engine (fp16)
3. validate inference (1 batch)
4. deploy model to models/vehicle/<version>/
