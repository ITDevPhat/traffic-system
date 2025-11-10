"""
=========================================================
🚀 YOLO Model Conversion Pipeline: .pt → .onnx (FP32)
=========================================================
Tự động xuất model YOLO sang ONNX chuẩn để dùng với ONNXRuntime.
Hỗ trợ FP32, opset=11 (tương thích mọi bản onnxruntime).
"""

from ultralytics import YOLO
import os

# --- Đường dẫn model nguồn (.pt) ---
model_path = r"D:\ITDevPhat\Python\LVTN\traffic-system\traffic-server\models\vehicle\11s\yolo_vehicle_11s.pt"

# --- Thư mục đích để lưu file .onnx ---
export_dir = os.path.dirname(model_path)

print("🔄 Đang load model YOLOv11s...")
model = YOLO(model_path)

# --- Xuất sang ONNX (FP32, opset 11) ---
print("⚙️  Đang export sang ONNX FP32 (opset=11)...")
export_path = os.path.join(export_dir, "yolo_vehicle_11s.onnx")

model.export(
    format="onnx",   # ONNX format
    opset=11,        # IR <= 11 cho onnxruntime 1.23.2
    half=False,      # DÙNG FP32 để tránh lỗi tensor(float16)
    imgsz=640,       # input size
)

print("✅ Xuất ONNX thành công!")
print(f"📦 File lưu tại: {export_path}")
