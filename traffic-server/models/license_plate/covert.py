from ultralytics import YOLO

model = YOLO("yolo_plate_v10n.pt")
model.export(format="onnx", opset=11, dynamic=False)
