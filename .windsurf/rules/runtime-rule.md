---
trigger: manual
---

# runtime and inference rules

## environment
python: 3.11
cuda: true
tensorrt: true
onnxruntime-gpu: 1.23.2
torch: 2.5.1
ultralytics: 8.3.0
boxmot: 15.0.9

## device setup
device_preference: cuda:0
precision: fp16
batch_size: 1
warmup_seconds: 5
max_fps: 60

## model hierarchy
priority: engine > onnx > pt
yolo_version: 11s
onnx_opset: 11
tracking_engine: bytetrack
ocr_engine: yolo_v10n + yolo_v8n

## fallback logic
if engine fails -> try onnx
if onnx fails -> fallback pt
if all fail -> log ❌ and stop inference thread

## logging
startup_logs:
  - cuda info
  - torch version
  - onnxruntime version
  - tensorrt version
  - active providers

error_logs:
  - print model path
  - print fix suggestions
  - print environment diagnostic summary

