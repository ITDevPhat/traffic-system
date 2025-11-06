@echo off
REM =====================================================
REM Run Traffic Detection System - OPTIMIZED
REM Target: >30 FPS with ONNX/TensorRT
REM =====================================================

echo.
echo ========================================
echo   Starting OPTIMIZED Detection Server
echo   Target: 30+ FPS
echo ========================================
echo.

REM Activate conda environment
call conda activate LVTN
if %errorlevel% neq 0 (
    echo [ERROR] Failed to activate LVTN environment
    echo Run setup_lvtn_env.bat first
    pause
    exit /b 1
)

REM Performance environment variables
set CUDA_LAUNCH_BLOCKING=0
set PYTORCH_CUDA_ALLOC_CONF=max_split_size_mb:512
set KMP_DUPLICATE_LIB_OK=TRUE
set OMP_NUM_THREADS=4
set ORT_TENSORRT_ENGINE_CACHE_ENABLE=1
set ORT_TENSORRT_FP16_ENABLE=1

REM Navigate to app directory
cd app

echo [INFO] Starting FastAPI server with optimized settings...
echo [INFO] Using LVTN conda environment
echo [INFO] CUDA optimizations enabled
echo [INFO] TensorRT FP16 enabled
echo.

REM Run with optimized uvicorn settings
uvicorn main:app ^
    --host 0.0.0.0 ^
    --port 8000 ^
    --workers 1 ^
    --loop uvloop ^
    --log-level info ^
    --no-access-log

pause

