@echo off
REM =====================================================
REM Setup và Activate Conda Environment LVTN
REM Tối ưu cho >30 FPS với ONNX/TensorRT
REM =====================================================

echo.
echo ========================================
echo   Traffic Detection System - LVTN
echo   Performance Optimized Setup
echo ========================================
echo.

REM Activate conda environment
call conda activate LVTN
if %errorlevel% neq 0 (
    echo [ERROR] Failed to activate conda environment 'LVTN'
    echo Please create it first:
    echo   conda create -n LVTN python=3.10
    pause
    exit /b 1
)

echo [OK] Conda environment 'LVTN' activated
echo.

REM Set performance environment variables
echo Setting performance optimization flags...

REM CUDA Optimizations
set CUDA_LAUNCH_BLOCKING=0
set CUDA_DEVICE_MAX_CONNECTIONS=32

REM PyTorch Optimizations
set PYTORCH_CUDA_ALLOC_CONF=max_split_size_mb:512
set TORCH_CUDNN_V8_API_ENABLED=1

REM OpenMP Optimizations (prevent conflicts)
set KMP_DUPLICATE_LIB_OK=TRUE
set OMP_NUM_THREADS=4

REM TensorRT Optimizations
set TENSORRT_MIN_MEMORY_MB=256
set TENSORRT_WORKSPACE_SIZE=2147483648

REM ONNX Runtime Optimizations
set ORT_TENSORRT_ENGINE_CACHE_ENABLE=1
set ORT_TENSORRT_FP16_ENABLE=1

echo [OK] Performance flags set
echo.

REM Display GPU info
echo Checking GPU status...
python -c "import torch; print(f'CUDA Available: {torch.cuda.is_available()}'); print(f'GPU: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else \"None\"}'); print(f'CUDA Version: {torch.version.cuda}')"
echo.

echo ========================================
echo   Environment Ready!
echo   Run: uvicorn app.main:app --host 0.0.0.0 --port 8000
echo ========================================
echo.

REM Keep window open
cmd /k

