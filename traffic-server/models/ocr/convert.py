from ultralytics import YOLO

model = YOLO("yolo_ocr_chars_v10n.pt")
model.export(format="onnx", opset=11)
