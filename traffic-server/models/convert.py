"""
=========================================================
🚀 YOLO Model Conversion Pipeline: .pt → .onnx → .engine
=========================================================
Tự động tìm tất cả model .pt trong thư mục hiện tại,
xuất sang TensorRT FP16 (.engine) để tăng tốc suy luận.
"""

import torch
from ultralytics import YOLO
import os

# --- Đường dẫn model nguồn (.pt) ---
model_path = r"D:\ITDevPhat\Python\LVTN\traffic-system\traffic-server\models\yolo_ocr_chars_v10n.pt"

# --- Thư mục đích để lưu file .engine ---
export_dir = os.path.dirname(model_path)  # cùng thư mục models

# --- Load YOLOv10 model ---
print("🔄 Đang load model YOLOv10...")
model = YOLO(model_path)

# --- Xuất sang TensorRT (FP16) ---
print("⚙️  Bắt đầu xuất sang TensorRT (.engine)...")
engine_path = os.path.join(export_dir, "yolo_ocr_chars_v10n.engine")

model.export(
    format="engine",    # TensorRT
    half=True,          # FP16 precision
    device=0,           # GPU 0
    imgsz=640,          # kích thước input (phù hợp với training)
    project=export_dir, # thư mục xuất
    name="trt_export"   # tạo subfolder riêng để gọn gàng
)

print("✅ Xuất TensorRT thành công!")
print(f"📦 File .engine nằm tại: {export_dir}")
