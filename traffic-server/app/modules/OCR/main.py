"""
FastAPI Main Application
Chạy server: uvicorn main:app --reload --host 0.0.0.0 --port 8000
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Import router từ module OCR
try:
    from router import router as ocr_router
except ImportError:
    # Nếu import từ thư mục cha
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent))
    from router import router as ocr_router

# Tạo FastAPI app
app = FastAPI(
    title="OCR License Plate Recognition API",
    description="API nhận dạng biển số xe Việt Nam sử dụng YOLO v10",
    version="2.0.0"
)

# Thêm CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include OCR router
app.include_router(ocr_router)

# Root endpoint
@app.get("/")
async def root():
    return {
        "message": "OCR License Plate Recognition API",
        "version": "2.0.0",
        "docs": "/docs",
        "ocr_endpoints": "/ocr"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

