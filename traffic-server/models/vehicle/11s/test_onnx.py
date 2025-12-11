import onnx
m = onnx.load("yolo_vehicle_11s_old.onnx")
print("IR_VERSION:", m.ir_version)
print("OPSET:", m.opset_import[0].version)
