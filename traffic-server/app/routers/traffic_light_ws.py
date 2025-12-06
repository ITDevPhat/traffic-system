"""
Traffic Light Detection WebSocket Router
Consumes from Traffic Light Worker (no separate pipeline)
"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, HTTPException
import json
import logging
import asyncio
import base64
import cv2
import numpy as np
from typing import Optional

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/traffic-light",
    tags=["Traffic Light Detection"],
)


def encode_roi_frame(roi_frame: Optional[np.ndarray], quality: int = 80) -> Optional[str]:
    """Encode ROI frame to base64 JPEG"""
    if roi_frame is None or roi_frame.size == 0:
        return None
    
    try:
        _, buffer = cv2.imencode('.jpg', roi_frame, [cv2.IMWRITE_JPEG_QUALITY, quality])
        return base64.b64encode(buffer).decode('utf-8')
    except Exception as e:
        logger.error(f"Failed to encode ROI frame: {e}")
        return None


@router.websocket("/realtime")
async def ws_traffic_light_realtime(
    websocket: WebSocket,
    camera_id: str = Query(..., description="Camera ID"),
):
    """
    Traffic Light Detection WebSocket - Consumes from TL Worker
    
    This endpoint streams traffic light detection results from the
    dedicated TL worker. It does NOT create a separate pipeline.
    
    Features:
    - Traffic light state (RED/GREEN/YELLOW)
    - Confidence scores
    - ROI frame (base64 JPEG)
    - Red light violations
    - Frame index synchronization
    """
    from app.services.traffic_light_manager import worker_manager
    
    logger.info(f"🚦 Traffic Light WS connection for camera: {camera_id}")
    
    await websocket.accept()
    logger.info("✅ WebSocket accepted")
    
    try:
        # Get worker for this camera
        worker = worker_manager.get_worker(camera_id)
        
        if not worker:
            # No active worker - send error
            error_msg = {
                "type": "error",
                "error": "no_worker",
                "message": f"No traffic light worker found for camera: {camera_id}. Please start detection first via POST /api/traffic-light/roi",
                "camera_id": camera_id
            }
            await websocket.send_json(error_msg)
            logger.warning(f"⚠️ No worker for camera: {camera_id}")
            await websocket.close()
            return
        
        # Send connection confirmation
        await websocket.send_json({
            "type": "info",
            "message": "Traffic light detection WebSocket connected",
            "camera_id": camera_id
        })
        
        logger.info(f"✅ Streaming from TL worker for camera: {camera_id}")
        
        # Stream loop
        frame_count = 0
        last_state = None
        
        while True:
            # Check connection
            if websocket.client_state.name == 'DISCONNECTED':
                logger.info("🔌 WebSocket disconnected")
                break
            
            # Get latest state from worker
            state = worker.get_latest_state()
            
            if state is None:
                # No state yet, wait
                await asyncio.sleep(0.1)
                continue
            
            # Only send if state changed or every 10 frames
            if last_state is None or state.frame_index != last_state.frame_index:
                # Encode ROI frame to base64
                roi_frame_b64 = encode_roi_frame(state.roi_frame, quality=80)
                
                # Build message
                message = {
                    "type": "traffic_light_update",
                    "camera_id": state.camera_id,
                    "frame_index": state.frame_index,
                    "traffic_light": {
                        "state": state.state,
                        "confidence": state.confidence if state.confidence is not None else 0.0
                    },
                    "roi_frame": roi_frame_b64,
                    "violations": state.violations,
                    "timestamp": state.timestamp.isoformat()
                }
                
                # Send message
                try:
                    await asyncio.wait_for(
                        websocket.send_json(message),
                        timeout=1.0
                    )
                    
                    frame_count += 1
                    last_state = state
                    
                    if frame_count % 50 == 0:
                        logger.info(
                            f"🚦 Sent TL update #{frame_count}: state={state.state}, "
                            f"violations={len(state.violations)}"
                        )
                    
                except asyncio.TimeoutError:
                    logger.warning(f"⏱️ Send timeout at frame {frame_count}")
                    break
                except Exception as e:
                    error_str = str(e)
                    if "disconnect" in error_str.lower() or "closed" in error_str.lower():
                        logger.info(f"🔌 Client disconnected: {e}")
                        break
                    else:
                        logger.error(f"❌ Send error: {e}")
                        break
            
            # Small delay to avoid busy loop
            await asyncio.sleep(0.05)
        
        logger.info(f"✅ Stream ended after {frame_count} updates")
    
    except WebSocketDisconnect as e:
        logger.info(f"❌ Client disconnected: {e}")
    
    except Exception as e:
        logger.error(f"❌ Error: {e}", exc_info=True)
        try:
            await websocket.send_json({
                "type": "error",
                "message": str(e)
            })
        except:
            pass
    
    finally:
        # Close WebSocket
        try:
            await websocket.close()
        except:
            pass
        
        logger.info("✅ Traffic Light WebSocket handler complete")


@router.get("/health")
async def traffic_light_health():
    """Health check for traffic light detection"""
    return {
        "status": "healthy",
        "service": "traffic_light_detection",
        "features": [
            "Traffic light detection",
            "Violation detection",
            "ROI support",
            "Real-time streaming"
        ]
    }
