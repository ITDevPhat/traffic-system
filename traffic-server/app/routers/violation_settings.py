"""
Violation Settings API Router
API endpoints for managing violation detection settings
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any
import logging

from ..core.violation_config import (
    ENABLE_VIOLATIONS, 
    VIOLATION_RULES, 
    VIOLATION_SETTINGS,
    get_violation_status
)

logger = logging.getLogger(__name__)

router = APIRouter()

class ViolationStatusResponse(BaseModel):
    """Response model for violation status"""
    enabled: bool
    message: str
    rules: Dict[str, Any]
    settings: Dict[str, Any]

@router.get("/violation-status", response_model=ViolationStatusResponse)
async def get_violation_status_endpoint():
    """
    Get current violation detection status
    
    Returns:
        Current violation detection configuration and status
    """
    try:
        status = get_violation_status()
        
        return ViolationStatusResponse(
            enabled=status["enabled"],
            message=status["message"],
            rules=status["rules"],
            settings=status["settings"]
        )
        
    except Exception as e:
        logger.error(f"Error getting violation status: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get violation status: {str(e)}")

@router.get("/violation-info")
async def get_violation_info():
    """
    Get detailed violation detection information
    
    Returns:
        Detailed information about violation detection system
    """
    try:
        status = get_violation_status()
        
        return {
            "status": "success",
            "violation_detection": {
                "enabled": status["enabled"],
                "message": status["message"],
                "available_rules": list(status["rules"].keys()),
                "enabled_rules": [k for k, v in status["rules"].items() if v],
                "disabled_rules": [k for k, v in status["rules"].items() if not v],
                "settings": status["settings"]
            },
            "note": "Violation detection is currently disabled while traffic rules are being developed. This ensures no false positives during testing phase."
        }
        
    except Exception as e:
        logger.error(f"Error getting violation info: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get violation info: {str(e)}")

@router.post("/violation-status/toggle")
async def toggle_violation_detection():
    """
    Toggle violation detection on/off (for development/testing)
    
    Note: This is a temporary endpoint for development.
    In production, violation rules should be configured through proper config files.
    """
    try:
        # This would require modifying the config file or using environment variables
        # For now, just return current status
        status = get_violation_status()
        
        return {
            "status": "info",
            "message": "Violation detection toggle is controlled by configuration file",
            "current_status": status["enabled"],
            "note": "To enable violations, set ENABLE_VIOLATIONS = True in app/core/violation_config.py",
            "recommendation": "Implement proper traffic rules before enabling violation detection"
        }
        
    except Exception as e:
        logger.error(f"Error toggling violation detection: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to toggle violation detection: {str(e)}")