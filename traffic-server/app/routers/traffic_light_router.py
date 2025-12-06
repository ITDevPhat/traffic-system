"""
Traffic Light ROI Detection Router
Handles ROI-based traffic light detection with dedicated workers
"""
from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect, Query
from pydantic import BaseModel, Field, field_validator, model_validator
from typing import Optional
from typing import Literal, Optional
from datetime import datetime
import logging
import json

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/traffic-light",
    tags=["Traffic Light ROI Detection"],
)


# =========================================================
# Pydantic Models
# =========================================================

class ROI(BaseModel):
    """Normalized ROI coordinates [0, 1]"""
    x: float = Field(..., ge=0, le=1, description="Left edge (normalized)")
    y: float = Field(..., ge=0, le=1, description="Top edge (normalized)")
    width: float = Field(..., ge=0.02, le=1, description="Width (normalized, min 2%)")
    height: float = Field(..., ge=0.02, le=1, description="Height (normalized, min 2%)")
    
    @field_validator('width', 'height')
    @classmethod
    def check_minimum_size(cls, v, info):
        if v < 0.02:
            raise ValueError(f"{info.field_name} too small (minimum 2% of frame)")
        return v


class ROIPixel(BaseModel):
    """Pixel-based ROI coordinates"""
    x1: int = Field(..., description="Top-left X")
    y1: int = Field(..., description="Top-left Y")
    x2: int = Field(..., description="Bottom-right X")
    y2: int = Field(..., description="Bottom-right Y")


class ROIRequest(BaseModel):
    """Request to start TL detection"""
    camera_id: str = Field(..., min_length=1, description="Camera identifier")
    roi: Optional[ROI] = Field(None, description="Region of interest (normalized)")
    roi_pixel: Optional[ROIPixel] = Field(None, description="Region of interest (pixels)")
    frame_width: Optional[int] = Field(None, description="Frame width for pixel to normalized conversion")
    frame_height: Optional[int] = Field(None, description="Frame height for pixel to normalized conversion")
    
    @field_validator('camera_id')
    @classmethod
    def validate_camera_id(cls, v):
        # Sanitize camera_id to prevent path traversal
        if '..' in v or '/' in v or '\\' in v:
            raise ValueError("Invalid camera_id: contains illegal characters")
        return v
    
    @model_validator(mode='after')
    def check_roi_provided(self):
        if not self.roi and not self.roi_pixel:
            raise ValueError("Either 'roi' or 'roi_pixel' must be provided")
        return self


class StopRequest(BaseModel):
    """Request to stop TL detection"""
    camera_id: str = Field(..., min_length=1, description="Camera identifier")
    
    @field_validator('camera_id')
    @classmethod
    def validate_camera_id(cls, v):
        # Sanitize camera_id to prevent path traversal
        if '..' in v or '/' in v or '\\' in v:
            raise ValueError("Invalid camera_id: contains illegal characters")
        return v


class TLState(BaseModel):
    """Traffic light state"""
    state: Literal['GREEN', 'RED', 'YELLOW', 'UNKNOWN']
    confidence: float = Field(..., ge=0, le=1)
    timestamp: datetime
    frame_base64: Optional[str] = None


class WSMessage(BaseModel):
    """WebSocket message"""
    type: Literal['state_update', 'error', 'info']
    state: Optional[Literal['GREEN', 'RED', 'YELLOW', 'UNKNOWN']] = None
    confidence: Optional[float] = None
    timestamp: Optional[str] = None
    frame: Optional[str] = None
    error: Optional[str] = None
    info: Optional[str] = None


# =========================================================
# API Endpoints
# =========================================================

# In-memory storage for ROI configurations (shared with traffic_light_ws.py)
roi_storage = {}

def clear_roi(camera_id: str) -> None:
    """Clear ROI for a specific camera"""
    if camera_id in roi_storage:
        del roi_storage[camera_id]
        logger.info(f"🗑️ Cleared ROI for camera {camera_id}")


@router.post("/roi")
async def set_roi(request: ROIRequest):
    """
    Start traffic light detection on specified ROI
    
    Args:
        request: ROI configuration with camera_id and coordinates (normalized or pixels)
        
    Returns:
        Success response with worker_id
        
    Raises:
        HTTPException: 400 for validation errors, 500 for server errors
    """
    from app.config.roi_config import save_traffic_light_roi
    
    try:
        roi_data = None
        roi_norm = None
        
        # Get frame dimensions from request or use defaults
        frame_width = request.frame_width or 1920
        frame_height = request.frame_height or 1080
        
        logger.info(f"📐 Using frame dimensions: {frame_width}x{frame_height}")
        
        # Convert roi_pixel to storage format AND normalized format
        if request.roi_pixel:
            logger.info(f"🚦 ROI pixel request for camera {request.camera_id}: {request.roi_pixel}")
            
            x1 = request.roi_pixel.x1
            y1 = request.roi_pixel.y1
            x2 = request.roi_pixel.x2
            y2 = request.roi_pixel.y2
            
            roi_data = {
                "type": "pixel",
                "x1": x1,
                "y1": y1,
                "x2": x2,
                "y2": y2
            }
            
            # Convert to normalized for worker
            roi_norm = {
                "x": x1 / frame_width,
                "y": y1 / frame_height,
                "width": (x2 - x1) / frame_width,
                "height": (y2 - y1) / frame_height
            }
            logger.info(f"🔄 Converted to normalized: {roi_norm}")
            
        elif request.roi:
            logger.info(f"🚦 ROI normalized request for camera {request.camera_id}: {request.roi}")
            
            # Validate ROI coordinates
            if request.roi.x + request.roi.width > 1.0:
                raise HTTPException(status_code=400, detail="ROI extends beyond frame width")
            if request.roi.y + request.roi.height > 1.0:
                raise HTTPException(status_code=400, detail="ROI extends beyond frame height")
            
            roi_data = {
                "type": "normalized",
                "x": request.roi.x,
                "y": request.roi.y,
                "width": request.roi.width,
                "height": request.roi.height
            }
            roi_norm = roi_data
        
        # Store ROI for this camera (for traffic_light_ws.py to use)
        roi_storage[request.camera_id] = roi_data
        logger.info(f"✅ ROI stored for camera {request.camera_id}: {roi_data}")
        logger.info(f"📦 Current roi_storage keys: {list(roi_storage.keys())}")
        
        # Also save to persistent storage for traffic_light.py worker
        if roi_norm:
            try:
                save_traffic_light_roi(request.camera_id, roi_norm)
                logger.info(f"💾 ROI saved to persistent storage for camera {request.camera_id}")
            except Exception as e:
                logger.warning(f"⚠️ Failed to save ROI to persistent storage: {e}")
        
        return {
            "ok": True,
            "status": "ok",
            "worker_id": f"{request.camera_id}_tl_worker",
            "message": "Traffic light ROI saved",
            "camera_id": request.camera_id,
            "roi": roi_data,
            "roi_normalized": roi_norm
        }
        
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail={"error": "Validation error", "message": str(e)})
    except Exception as e:
        logger.error(f"Error saving TL ROI: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail={"error": "Internal server error", "message": str(e)})


@router.get("/roi/{camera_id}")
async def get_roi(camera_id: str):
    """Get stored ROI for a camera"""
    from app.config.roi_config import get_traffic_light_roi

    roi = roi_storage.get(camera_id)
    
    # Fallback: Try loading from disk
    if not roi:
        saved_roi = get_traffic_light_roi(camera_id)
        if saved_roi:
            # Wrap in normalized format matched to roi_storage
            roi = {
                "type": "normalized",
                "x": saved_roi["x"],
                "y": saved_roi["y"],
                "width": saved_roi["width"],
                "height": saved_roi["height"]
            }
            # Cache it in memory
            roi_storage[camera_id] = roi
            logger.info(f"📂 Loaded ROI from file for {camera_id}")

    if not roi:
        raise HTTPException(status_code=404, detail=f"No ROI found for camera {camera_id}")
    return {"camera_id": camera_id, "roi": roi}


@router.post("/stop")
async def stop_detection(request: StopRequest):
    """
    Stop traffic light detection for camera
    
    Args:
        request: Stop request with camera_id
        
    Returns:
        Success response with status
        
    Raises:
        HTTPException: 404 if no active worker, 500 for server errors
    """
    try:
        # TODO: Implement worker stopping in task 3
        # For now, return a placeholder response
        logger.info(f"Stop request received for camera {request.camera_id}")
        
        return {
            "status": "stopped",
            "camera_id": request.camera_id,
            "message": "Traffic light detection stopped"
        }
        
    except KeyError:
        raise HTTPException(
            status_code=404,
            detail={"error": "No active worker", "message": f"No worker found for camera {request.camera_id}"}
        )
    except Exception as e:
        logger.error(f"Error stopping TL detection: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={"error": "Internal server error", "message": str(e)}
        )


@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    camera_id: str = Query(..., description="Camera identifier")
):
    """
    WebSocket endpoint for streaming TL detection results
    
    Implements WebSocket disconnect cleanup with 5s timeout:
    - Accepts connection and cancels any pending cleanup
    - Streams detection results from worker
    - On disconnect, schedules worker cleanup after 5s timeout
    - Cleanup is cancelled if client reconnects within timeout
    
    Args:
        websocket: WebSocket connection
        camera_id: Camera identifier
        
    Streams JSON messages with traffic light state updates
    """
    from app.services.traffic_light_manager import worker_manager
    
    logger.info(f"WebSocket connection request for camera: {camera_id}")
    
    await websocket.accept()
    logger.info(f"WebSocket accepted for camera: {camera_id}")
    
    # Cancel any pending disconnect cleanup (client reconnected)
    worker_manager.cancel_disconnect_cleanup(camera_id)
    
    try:
        # Get worker for this camera
        worker = worker_manager.get_worker(camera_id)
        
        if not worker:
            # No active worker - send error and close
            await websocket.send_json({
                "type": "error",
                "error": "No active worker for this camera. Please start detection first.",
                "camera_id": camera_id
            })
            await websocket.close()
            return
        
        # Send connection confirmation
        await websocket.send_json({
            "type": "info",
            "info": "Traffic light detection WebSocket connected",
            "camera_id": camera_id
        })
        
        # Stream detection results from worker
        async for message in worker.stream():
            try:
                await websocket.send_json(message)
            except WebSocketDisconnect:
                logger.info(f"Client disconnected during send: {camera_id}")
                break
            except Exception as e:
                logger.warning(f"Error sending message to client: {e}")
                break
                
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected: {camera_id}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}", exc_info=True)
        try:
            await websocket.send_json({
                "type": "error",
                "error": str(e)
            })
        except:
            pass
    finally:
        # Schedule worker cleanup after 5s timeout
        # This allows client to reconnect without stopping the worker
        logger.info(f"WebSocket cleanup for camera: {camera_id}")
        worker_manager.schedule_disconnect_cleanup(camera_id)
        
        try:
            await websocket.close()
        except:
            pass


@router.get("/health")
async def health_check():
    """Health check for traffic light ROI detection service"""
    return {
        "status": "healthy",
        "service": "traffic_light_roi_detection",
        "features": [
            "ROI-based traffic light detection",
            "Real-time state streaming",
            "Independent worker management"
        ]
    }
