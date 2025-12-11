import onnxruntime as ort
sess = ort.InferenceSession("yolo_vehicle_11s_old.onnx", providers=["CUDAExecutionProvider"])
print(sess.get_providers())
print("Loaded OK on CUDA")
import onnxruntime as ort

sess = ort.InferenceSession("yolo_vehicle_11s_old.onnx", providers=["CUDAExecutionProvider"])

providers = sess.get_providers()
print("Providers:", providers)

if "CUDAExecutionProvider" in providers:
    print("GPU OK")
else:
    print("GPU NOT WORKING")
