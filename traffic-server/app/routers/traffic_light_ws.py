"""
Traffic Light Detection WebSocket Router
Separate pipeline for traffic light violation detection
"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, HTTPException
from app.services.realtime_binary_stream import (
    BinaryAnnotStream,
    DEFAULT_REALTIME_MODEL_PATH,
)
import json
import logging
import asyncio

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/traffic-light",
    tags=["Traffic Light Detection"],
)


@router.websocket("/realtime")
async def ws_traffic_light_realtime(
    websocket: WebSocket,
    source: str = Query("0", description="Video source"),
    conf: float = Query(0.5, description="Confidence threshold"),
    fps: int = Query(30, description="Target FPS"),
    imgsz: int = Query(640, description="YOLO inference size"),
    quality: int = Query(60, description="JPEG quality"),
    encode_width: int = Query(960, description="Encode width"),
    model_path: str = Query(DEFAULT_REALTIME_MODEL_PATH, description="Model path"),
    enable_traffic_light: bool = Query(True, description="Enable traffic light detection"),
    enable_violation: bool = Query(True, description="Enable violation detection"),
):
    """
    Traffic Light Detection WebSocket - Separate pipeline
    
    Features:
    - Traffic light detection (red/yellow/green)
    - Violation detection (running red light)
    - ROI support for stoplines
    - Real-time streaming
    """
    logger.info(f"🚦 Traffic Light WS connection from: {websocket.client}")
    logger.info(f"📹 Source: {source}, TL: {enable_traffic_light}, Violation: {enable_violation}")
    
    await websocket.accept()
    logger.info("✅ WebSocket accepted")
    
    stream = None
    
    try:
        # Initialize stream with traffic light enabled
        stream = BinaryAnnotStream(
            source=source,
            conf=conf,
            imgsz=imgsz,
            target_fps=fps,
            jpeg_quality=quality,
            encode_width=encode_width,
            model_path=model_path,
            enable_yolo=True,
            enable_tracking=True,
            enable_bbox_drawing=True,
            enable_roi=True,
            enable_roi_drawing=True,
            # Traffic light specific settings would go here
            # For now, use same stream but can be extended
        )
        
        stream.start()
        
        # Send info packet
        info = stream.info_packet()
        info['traffic_light_enabled'] = enable_traffic_light
        info['violation_enabled'] = enable_violation
        await websocket.send_text(json.dumps(info))
        logger.info(f"📤 Sent info: {info}")
        
        # Stream loop
        async def send_frames():
            """Send frames with traffic light data"""
            frame_count = 0
            consecutive_errors = 0
            max_consecutive_errors = 3
            
            while True:
                # Check connection
                if websocket.client_state.name == 'DISCONNECTED':
                    logger.info("🔌 WebSocket disconnected")
                    break
                
                if stream and stream.stop_ev.is_set():
                    logger.info("🛑 Stream stopped")
                    break
                
                try:
                    header, jpeg_bytes = stream.next_frame()
                    
                    if header is None or jpeg_bytes is None:
                        await asyncio.sleep(0.001)
                        continue
                    
                    if websocket.client_state.name == 'DISCONNECTED':
                        break
                    
                    try:
                        # Send header with traffic light data
                        await asyncio.wait_for(
                            websocket.send_text(json.dumps(header)),
                            timeout=1.0
                        )
                        
                        # Send JPEG
                        await asyncio.wait_for(
                            websocket.send_bytes(jpeg_bytes),
                            timeout=1.0
                        )
                        
                        frame_count += 1
                        consecutive_errors = 0
                        
                    except asyncio.TimeoutError:
                        logger.warning(f"⏱️ Send timeout at frame {frame_count}")
                        consecutive_errors += 1
                        if consecutive_errors >= max_consecutive_errors:
                            logger.error(f"❌ Too many timeouts - stopping")
                            break
                            
                except Exception as send_error:
                    error_str = str(send_error)
                    if "disconnect" in error_str.lower() or "closed" in error_str.lower():
                        logger.info(f"🔌 Client disconnected: {send_error}")
                        break
                    else:
                        logger.warning(f"⚠️ Send error: {send_error}")
                        consecutive_errors += 1
                        if consecutive_errors >= max_consecutive_errors:
                            logger.error(f"❌ Too many errors - stopping")
                            break
                        await asyncio.sleep(0.01)
            
            logger.info(f"✅ send_frames() ended after {frame_count} frames")
        
        async def receive_commands():
            """Receive commands from client"""
            disconnected = False
            while not disconnected:
                try:
                    if websocket.client_state.name == 'DISCONNECTED':
                        disconnected = True
                        break
                    
                    message = await asyncio.wait_for(websocket.receive(), timeout=0.1)
                    
                    if 'text' in message:
                        data = message['text']
                        cmd = json.loads(data)
                        
                        # Handle traffic light specific commands
                        if cmd.get('command') == 'set_roi':
                            rois_payload = cmd.get('rois')
                            if isinstance(rois_payload, list):
                                rois_payload = {
                                    f"roi_{idx + 1}": item for idx, item in enumerate(rois_payload)
                                }
                            if stream:
                                count = stream.set_roi_polygons(rois_payload)
                                logger.info(f"🗺️ ROI polygons updated ({count})")
                                await websocket.send_text(json.dumps({
                                    "type": "roi_ack",
                                    "count": count
                                }))
                        elif cmd.get('command') == 'clear_roi':
                            if stream:
                                stream.clear_roi_polygons()
                                logger.info("🧹 ROI cleared")
                                await websocket.send_text(json.dumps({
                                    "type": "roi_cleared"
                                }))
                
                except asyncio.TimeoutError:
                    continue
                except WebSocketDisconnect:
                    disconnected = True
                    break
                except Exception as e:
                    error_str = str(e)
                    if "disconnect" in error_str.lower():
                        disconnected = True
                        break
                    logger.warning(f"Command receive error: {e}")
                    await asyncio.sleep(0.01)
        
        # Run both tasks
        send_task = asyncio.create_task(send_frames())
        recv_task = asyncio.create_task(receive_commands())
        
        done, pending = await asyncio.wait(
            {send_task, recv_task},
            return_when=asyncio.FIRST_COMPLETED
        )
        
        # Cancel pending tasks
        for task in pending:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        
        # Check exceptions
        for task in done:
            try:
                task.result()
            except Exception as e:
                logger.warning(f"Task exception: {e}")
        
        logger.info("✅ Stream ended normally")
    
    except WebSocketDisconnect as e:
        logger.info(f"❌ Client disconnected: {e}")
    
    except Exception as e:
        logger.error(f"❌ Error: {e}", exc_info=True)
        try:
            await websocket.send_text(json.dumps({
                "type": "error",
                "message": str(e)
            }))
        except:
            pass
    
    finally:
        # Force stop stream
        if stream:
            logger.info("🧹 Force stopping stream...")
            import time
            start_time = time.time()
            
            try:
                stream.stop()
                stream.close()
                
                elapsed = time.time() - start_time
                if elapsed > 2.0:
                    logger.warning(f"⚠️ Stream cleanup took {elapsed:.2f}s")
                else:
                    logger.info(f"✅ Stream stopped in {elapsed:.2f}s")
            except Exception as e:
                logger.error(f"❌ Stream cleanup error: {e}")
        
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
