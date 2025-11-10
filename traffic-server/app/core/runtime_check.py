"""Runtime environment diagnostic checks."""
import os
import sys
import site
import logging

logger = logging.getLogger(__name__)

def check_runtime_environment():
    """Check and log runtime environment details."""
    logger.info("\n=== 🔍 RUNTIME ENVIRONMENT INFO ===")
    logger.info("🐍 Python exe: %s", sys.executable)
    logger.info("📦 sys.path[0]: %s", sys.path[0])

    # Add TensorRT DLL path to PATH early
    for p in site.getsitepackages():
        if "site-packages" in p:
            trt_dll_dir = os.path.join(p, "tensorrt")
            if os.path.isdir(trt_dll_dir):
                os.add_dll_directory(trt_dll_dir)  # Windows 10+
                os.environ["PATH"] = trt_dll_dir + os.pathsep + os.environ["PATH"]
                logger.info("✅ Added TensorRT DLL dir to PATH: %s", trt_dll_dir)
                break

    try:
        import tensorrt as trt
        logger.info("🧪 TensorRT import OK, version: %s", trt.__version__)
    except Exception as e:
        logger.error("❌ TensorRT import failed: %s: %s", type(e).__name__, e)

    try:
        import onnxruntime as ort
        logger.info("🔎 onnxruntime.__version__: %s", ort.__version__)
        logger.info("🔎 onnxruntime.__file__   : %s", ort.__file__)
        logger.info("🔎 Providers              : %s", ort.get_available_providers())
        logger.info("🔎 Device                 : %s", ort.get_device())
    except Exception as e:
        logger.error("❌ ORT import failed: %s: %s", type(e).__name__, e)
    logger.info("===================================\n")