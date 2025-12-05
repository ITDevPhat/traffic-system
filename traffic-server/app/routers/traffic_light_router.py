"""
Traffic Light ROI Detection Router
Handles ROI-based traffic light detection with dedicated workers
"""
from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect, Query
from pydantic import BaseModel, Field, field_validator
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


class ROIRequest(BaseModel):
    """Request to start TL detection"""
    camera_id: str = Field(..., min_length=1, description="Camera identifier")
    roi: ROI = Field(..., description="Region of interest for traffic light")
    
    @field_validator('camera_id')
    @classmethod
    def validate_camera_id(cls, v):
        # Sanitize camera_id to prevent path traversal
        if '..' in v or '/' in v or '\\' in v:
            raise ValueError("Invalid camera_id: contains illegal characters")
        return v


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

@router.post("/roi")
async def set_roi(request: ROIRequest):
    """
    Start traffic light detection on specified ROI
    
    Args:
        request: ROI configuration with camera_id and normalized coordinates
        
    Returns:
        Success response with worker_id
        
    Raises:
        HTTPException: 400 for validation errors, 500 for server errors
    """
    try:
        # TODO: Implement worker creation in task 3
        # For now, return a placeholder response
        logger.info(f"ROI request received for camera {request.camera_id}: {request.roi}")
        
        # Validate ROI coordinates are within bounds
        if request.roi.x < 0 or request.roi.x > 1:
            raise HTTPException(
                status_code=400,
                detail={"error": "ROI validation failed", "field": "roi.x", "message": "x must be in [0, 1]"}
            )
        if request.roi.y < 0 or request.roi.y > 1:
            raise HTTPException(
                status_code=400,
                detail={"error": "ROI validation failed", "field": "roi.y", "message": "y must be in [0, 1]"}
            )
        if request.roi.width < 0.02 or request.roi.width > 1:
            raise HTTPException(
                status_code=400,
                detail={"error": "ROI validation failed", "field": "roi.width", "message": "width must be in [0.02, 1]"}
            )
        if request.roi.height < 0.02 or request.roi.height > 1:
            raise HTTPException(
                status_code=400,
                detail={"error": "ROI validation failed", "field": "roi.height", "message": "height must be in [0.02, 1]"}
            )
        
        # Check if ROI extends beyond frame
        if request.roi.x + request.roi.width > 1.0:
            raise HTTPException(
                status_code=400,
                detail={"error": "ROI validation failed", "field": "roi", "message": "ROI extends beyond frame width"}
            )
        if request.roi.y + request.roi.height > 1.0:
            raise HTTPException(
                status_code=400,
                detail={"error": "ROI validation failed", "field": "roi", "message": "ROI extends beyond frame height"}
            )
        
        return {
            "status": "ok",
            "worker_id": f"{request.camera_id}_tl_worker",
            "message": "Traffic light detection started"
        }
        
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail={"error": "Validation error", "message": str(e)}
        )
    except Exception as e:
        logger.error(f"Error starting TL detection: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={"error": "Internal server error", "message": str(e)}
        )


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
