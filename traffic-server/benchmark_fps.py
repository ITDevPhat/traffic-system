"""
Benchmark script để test FPS của hệ thống
Kiểm tra performance với các model format: .engine, .onnx, .pt
"""

import sys
import os
import time
import cv2
import torch
import numpy as np
from pathlib import Path

# Add app to path
sys.path.append(str(Path(__file__).parent / "app"))

from app.utils.model_loader import load_yolo_model, get_model_info
from app.core.performance_config import setup_cuda_optimizations, INFERENCE_SETTINGS

# Setup CUDA
setup_cuda_optimizations()

def benchmark_model(model_path: str, test_video: str = None, num_frames: int = 100):
    """
    Benchmark một model với video test
    
    Args:
        model_path: Đường dẫn đến model
        test_video: Đường dẫn video test (nếu None, dùng dummy frames)
        num_frames: Số frames để test
    """
    print("\n" + "="*60)
    print(f"📊 BENCHMARK: {os.path.basename(model_path)}")
    print("="*60)
    
    # Load model
    try:
        print("📦 Loading model...")
        start = time.time()
        model = load_yolo_model(
            model_path,
            device=INFERENCE_SETTINGS["device"],
            imgsz=INFERENCE_SETTINGS["imgsz"],
            half=INFERENCE_SETTINGS["half"],
            verbose=False
        )
        load_time = time.time() - start
        print(f"✅ Model loaded in {load_time:.2f}s")
    except Exception as e:
        print(f"❌ Failed to load model: {e}")
        return None
    
    # Get model info
    model_info = get_model_info(model_path)
    print(f"📂 Model type: {model_info['type']}")
    print(f"💾 Model size: {model_info['size_mb']:.1f} MB")
    
    # Prepare test frames
    if test_video and os.path.exists(test_video):
        print(f"📹 Using test video: {test_video}")
        cap = cv2.VideoCapture(test_video)
        frames = []
        for _ in range(num_frames):
            ret, frame = cap.read()
            if not ret:
                cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                ret, frame = cap.read()
            if ret:
                frames.append(frame)
        cap.release()
    else:
        print(f"🎨 Using dummy frames (640x640)")
        frames = [np.random.randint(0, 255, (640, 640, 3), dtype=np.uint8) for _ in range(num_frames)]
    
    print(f"🎬 Testing with {len(frames)} frames...")
    
    # Warm up (first inference is slow)
    print("🔥 Warming up...")
    for _ in range(5):
        _ = model.predict(
            frames[0],
            conf=INFERENCE_SETTINGS["conf"],
            device=INFERENCE_SETTINGS["device"],
            half=INFERENCE_SETTINGS["half"],
            verbose=False
        )
    
    # Benchmark
    print("⚡ Running benchmark...")
    inference_times = []
    
    start_time = time.time()
    
    for i, frame in enumerate(frames):
        frame_start = time.time()
        
        results = model.predict(
            frame,
            conf=INFERENCE_SETTINGS["conf"],
            device=INFERENCE_SETTINGS["device"],
            half=INFERENCE_SETTINGS["half"],
            verbose=False
        )
        
        frame_time = time.time() - frame_start
        inference_times.append(frame_time)
        
        if (i + 1) % 10 == 0:
            avg_fps = (i + 1) / (time.time() - start_time)
            print(f"  Frame {i+1}/{len(frames)} | FPS: {avg_fps:.1f}")
    
    total_time = time.time() - start_time
    
    # Statistics
    avg_inference = np.mean(inference_times) * 1000  # ms
    min_inference = np.min(inference_times) * 1000
    max_inference = np.max(inference_times) * 1000
    std_inference = np.std(inference_times) * 1000
    
    avg_fps = len(frames) / total_time
    
    # Results
    print("\n" + "-"*60)
    print("📈 RESULTS:")
    print("-"*60)
    print(f"🎯 Average FPS: {avg_fps:.1f} FPS")
    print(f"⚡ Average Inference: {avg_inference:.1f} ms")
    print(f"📊 Min Inference: {min_inference:.1f} ms")
    print(f"📊 Max Inference: {max_inference:.1f} ms")
    print(f"📊 Std Inference: {std_inference:.1f} ms")
    print(f"⏱️  Total Time: {total_time:.2f}s")
    
    # Check if target met
    target_fps = 30
    if avg_fps >= target_fps:
        print(f"✅ TARGET MET: {avg_fps:.1f} FPS >= {target_fps} FPS")
    else:
        print(f"⚠️  TARGET MISSED: {avg_fps:.1f} FPS < {target_fps} FPS")
    
    print("="*60 + "\n")
    
    return {
        "model_type": model_info['type'],
        "model_size_mb": model_info['size_mb'],
        "avg_fps": avg_fps,
        "avg_inference_ms": avg_inference,
        "min_inference_ms": min_inference,
        "max_inference_ms": max_inference,
        "std_inference_ms": std_inference,
        "total_time": total_time,
        "target_met": avg_fps >= target_fps
    }


def main():
    """Main benchmark function"""
    print("\n" + "="*60)
    print("🚀 TRAFFIC DETECTION SYSTEM - FPS BENCHMARK")
    print("="*60)
    print(f"🖥️  Device: {INFERENCE_SETTINGS['device']}")
    print(f"🔧 FP16: {INFERENCE_SETTINGS['half']}")
    print(f"📐 Input Size: {INFERENCE_SETTINGS['imgsz']}")
    print(f"🎯 Target FPS: 30")
    
    if torch.cuda.is_available():
        print(f"🎮 GPU: {torch.cuda.get_device_name(0)}")
        vram = torch.cuda.get_device_properties(0).total_memory / (1024**3)
        print(f"💾 VRAM: {vram:.1f} GB")
    else:
        print("⚠️  GPU not available - using CPU")
    
    # Find models
    models_dir = Path(__file__).parent / "models" / "vehicle" / "v10m"
    
    if not models_dir.exists():
        models_dir = Path(__file__).parent / "models" / "vehicle"
    
    # Test video
    videos_dir = Path(__file__).parent / "videos"
    test_video = None
    if videos_dir.exists():
        video_files = list(videos_dir.glob("*.mp4"))
        if video_files:
            test_video = str(video_files[0])
    
    # Find all model formats
    model_formats = [".engine", ".onnx", ".pt"]
    results = []
    
    for ext in model_formats:
        model_files = list(models_dir.glob(f"*{ext}"))
        if model_files:
            model_path = str(model_files[0])
            result = benchmark_model(model_path, test_video, num_frames=100)
            if result:
                results.append(result)
    
    # Summary
    if results:
        print("\n" + "="*60)
        print("📊 BENCHMARK SUMMARY")
        print("="*60)
        print(f"{'Format':<10} {'FPS':<10} {'Inference (ms)':<15} {'Target Met'}")
        print("-"*60)
        for r in results:
            status = "✅" if r['target_met'] else "❌"
            print(f"{r['model_type']:<10} {r['avg_fps']:<10.1f} {r['avg_inference_ms']:<15.1f} {status}")
        print("="*60)
        
        # Recommendation
        best = max(results, key=lambda x: x['avg_fps'])
        print(f"\n🏆 BEST: {best['model_type'].upper()} - {best['avg_fps']:.1f} FPS")
        
        if best['model_type'] == 'engine':
            print("✅ TensorRT engine is fastest (as expected)")
        elif best['model_type'] == 'onnx':
            print("💡 ONNX is best available. Consider converting to TensorRT for 2-3x speedup:")
            print("   python models/convert.py")
        else:
            print("⚠️  Using PyTorch .pt model. Convert to ONNX or TensorRT for better performance:")
            print("   python models/convert.py")
    else:
        print("\n❌ No models found to benchmark!")
        print(f"📂 Checked directory: {models_dir}")


if __name__ == "__main__":
    main()

