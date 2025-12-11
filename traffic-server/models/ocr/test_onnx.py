import onnx
from ultralytics import YOLO

pt_model_path = "yolo_ocr_chars_v10n.pt"
onnx_export_path = "yolo_ocr_chars_v10n.onnx"   # đúng tên Ultralytics export

print("🔄 Exporting model to ONNX opset=11...")
model = YOLO(pt_model_path)
model.export(format="onnx", opset=11)
print(f"✅ Export hoàn tất: {onnx_export_path}")

print("\n🔍 Đang kiểm tra file ONNX...")
onnx_model = onnx.load(onnx_export_path)
graph = onnx_model.graph

ir_version = onnx_model.ir_version
opset_imports = {imp.domain: imp.version for imp in onnx_model.opset_import}

print("\n===== THÔNG TIN MODEL ONNX =====")
print(f"📌 File: {onnx_export_path}")
print(f"📌 IR Version: {ir_version}")
print(f"📌 Opset Imports: {opset_imports}")

main_opset = opset_imports.get("", None)
if main_opset == 11:
    print("🎉 File ONNX đúng OPSET=11")
else:
    print(f"⚠️ Opset={main_opset}, KHÔNG PHẢI 11!")

print("\n===== Một số ops trong graph =====")
for node in graph.node[:10]:
    print(f"- {node.op_type}")

print("\n🔚 Kiểm tra hoàn tất.")
