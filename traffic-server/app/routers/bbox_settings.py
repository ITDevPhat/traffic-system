from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


class BBoxSettingsUpdate(BaseModel):
    thickness: Optional[int] = None
    font_scale: Optional[float] = None
    font_thickness: Optional[int] = None
    label_padding: Optional[int] = None
    violation_thickness: Optional[int] = None


@router.get("/bbox-settings")
async def get_bbox_settings():
    """Get current bounding box drawing settings"""
    try:
        from app.core.performance_config import BBOX_SETTINGS
        return {
            "status": "success",
            "settings": BBOX_SETTINGS
        }
    except Exception as e:
        logger.error(f"Error getting bbox settings: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/bbox-settings")
async def update_bbox_settings(settings: BBoxSettingsUpdate):
    """Update bounding box drawing settings dynamically"""
    try:
        from app.core import performance_config
        
        updated_fields = []
        
        if settings.thickness is not None:
            if 1 <= settings.thickness <= 10:
                performance_config.BBOX_SETTINGS["thickness"] = settings.thickness
                updated_fields.append(f"thickness={settings.thickness}")
            else:
                raise HTTPException(status_code=400, detail="Thickness must be between 1 and 10")
        
        if settings.font_scale is not None:
            if 0.1 <= settings.font_scale <= 2.0:
                performance_config.BBOX_SETTINGS["font_scale"] = settings.font_scale
                updated_fields.append(f"font_scale={settings.font_scale}")
            else:
                raise HTTPException(status_code=400, detail="Font scale must be between 0.1 and 2.0")
        
        if settings.font_thickness is not None:
            if 1 <= settings.font_thickness <= 5:
                performance_config.BBOX_SETTINGS["font_thickness"] = settings.font_thickness
                updated_fields.append(f"font_thickness={settings.font_thickness}")
            else:
                raise HTTPException(status_code=400, detail="Font thickness must be between 1 and 5")
        
        if settings.label_padding is not None:
            if 0 <= settings.label_padding <= 20:
                performance_config.BBOX_SETTINGS["label_padding"] = settings.label_padding
                updated_fields.append(f"label_padding={settings.label_padding}")
            else:
                raise HTTPException(status_code=400, detail="Label padding must be between 0 and 20")
        
        if settings.violation_thickness is not None:
            if 1 <= settings.violation_thickness <= 10:
                performance_config.BBOX_SETTINGS["violation_thickness"] = settings.violation_thickness
                updated_fields.append(f"violation_thickness={settings.violation_thickness}")
            else:
                raise HTTPException(status_code=400, detail="Violation thickness must be between 1 and 10")
        
        if not updated_fields:
            raise HTTPException(status_code=400, detail="No valid settings provided")
        
        logger.info(f"✅ BBox settings updated: {', '.join(updated_fields)}")
        
        return {
            "status": "success",
            "message": f"Updated: {', '.join(updated_fields)}",
            "settings": performance_config.BBOX_SETTINGS
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating bbox settings: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/bbox-settings/reset")
async def reset_bbox_settings():
    """Reset bounding box settings to defaults"""
    try:
        from app.core import performance_config
        
        # Reset to defaults
        performance_config.BBOX_SETTINGS.update({
            "thickness": 2,
            "font_scale": 0.6,
            "font_thickness": 1,
            "label_padding": 5,
            "violation_thickness": 2,
        })
        
        logger.info("✅ BBox settings reset to defaults")
        
        return {
            "status": "success",
            "message": "BBox settings reset to defaults",
            "settings": performance_config.BBOX_SETTINGS
        }
        
    except Exception as e:
        logger.error(f"Error resetting bbox settings: {e}")
        raise HTTPException(status_code=500, detail=str(e))