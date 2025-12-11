from ultralytics import YOLO

model = YOLO("yolo_vehicle_11s.pt")

model.export(
    format="onnx",
    opset=11,
    simplify=True,
    imgsz=320,  # sẽ thay theo lựa chọn của bạn
    dynamic=False
)
