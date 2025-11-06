"""
OCR Module - License Plate Recognition
Module con cho FastAPI để nhận dạng biển số xe

Note: Router is NOT auto-imported to avoid loading models on startup.
For integrated mode, use: from app.services.plate_ocr_service import get_ocr_service
For standalone mode, import router explicitly: from app.modules.OCR.router import router
"""

from .core import LicensePlateDetector, create_detector

# Import optimized version nếu có
try:
    from .core_optimized import LicensePlateDetectorOptimized, create_detector_optimized
    __all__ = ['LicensePlateDetector', 'create_detector', 'LicensePlateDetectorOptimized', 'create_detector_optimized']
except ImportError:
    __all__ = ['LicensePlateDetector', 'create_detector']

__version__ = '2.0.0'

# Router is available but not auto-imported (lazy loading)
def get_router():
    """Get OCR router (lazy loading for standalone mode)"""
    from .router import router
    return router

