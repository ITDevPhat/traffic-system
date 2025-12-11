from ultralytics import YOLO

model = YOLO("yolo_vehicle_11s.pt")

model.export(
    format="onnx",
    opset=11,
    simplify=True,
    imgsz=640,  # Match current ONNX model dimensions
    dynamic=False
)
