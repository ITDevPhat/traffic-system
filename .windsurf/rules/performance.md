---
trigger: manual
---

# performance optimization rules

## gpu optimization
- always enable fp16
- pin YOLO weights to GPU memory
- preallocate tracker buffers
- prefer torch.cuda.Stream for concurrent kernel ops
- if TensorRT available → build engine on startup

## cpu optimization
- offload frame read to threadpool
- minimize OpenCV resize/convert calls
- use cv2.cuda when possible

## async / threading
- use queue.Queue(maxsize=10) between threads
- never block on put() without timeout
- handle graceful shutdown on WS close

## frame encode
- turbojpeg if available
- encode_width: 960px default
- quality: 60
- send metadata JSON in WS
