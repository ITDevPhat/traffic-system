import onnxruntime as ort
so = ort.SessionOptions()
so.log_severity_level = 0
session = ort.InferenceSession("models/vehicle/11s/yolo_vehicle_11s.onnx", providers=["CUDAExecutionProvider","CPUExecutionProvider"], sess_options=so)
