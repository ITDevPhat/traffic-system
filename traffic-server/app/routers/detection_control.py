"""
Detection Control API
REST endpoints for controlling video playback state (START/PAUSE/RESUME/STOP)
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/detection", tags=["Detection Control"])

# Global registry of active streams (keyed by session_id or camera_id)
# This will be populated by WebSocket handlers
active_streams: Dict[str, any] = {}


class PlaybackControlRequest(BaseModel):
    """Request to control playback"""
    session_id: str


class PlaybackStateResponse(BaseModel):
    """Response with current playback state"""
    session_id: str
    state: str  # STOPPED | RUNNING | PAUSED
    frame_idx: int
    message: str


@router.post("/start", response_model=PlaybackStateResponse)
async def start_playback(request: PlaybackControlRequest):
    """
    Start video playback from frame 0 or resume from current position
    
    Args:
        request: Control request with session_id
        
    Returns:
        Current playback state
        
    Raises:
        HTTPException: 404 if session not found
    """
    session_id = request.session_id
    stream = active_streams.get(session_id)
    
    if not stream:
        raise HTTPException(
            status_code=404,
            detail=f"No active stream found for session: {session_id}"
        )
    
    try:
        stream.start_playback()
        state = stream.get_state()
        frame_idx = stream.frame_idx
        
        logger.info(f"▶️  Started playback for session {session_id} at frame {frame_idx}")
        
        return PlaybackStateResponse(
            session_id=session_id,
            state=state,
            frame_idx=frame_idx,
            message=f"Playback started at frame {frame_idx}"
        )
    except Exception as e:
        logger.error(f"Error starting playback: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/pause", response_model=PlaybackStateResponse)
async def pause_playback(request: PlaybackControlRequest):
    """
    Pause video playback at current frame
    
    Args:
        request: Control request with session_id
        
    Returns:
        Current playback state
        
    Raises:
        HTTPException: 404 if session not found
    """
    session_id = request.session_id
    stream = active_streams.get(session_id)
    
    if not stream:
        raise HTTPException(
            status_code=404,
            detail=f"No active stream found for session: {session_id}"
        )
    
    try:
        stream.pause_playback()
        state = stream.get_state()
        frame_idx = stream.frame_idx
        
        logger.info(f"⏸️  Paused playback for session {session_id} at frame {frame_idx}")
        
        return PlaybackStateResponse(
            session_id=session_id,
            state=state,
            frame_idx=frame_idx,
            message=f"Playback paused at frame {frame_idx}"
        )
    except Exception as e:
        logger.error(f"Error pausing playback: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/resume", response_model=PlaybackStateResponse)
async def resume_playback(request: PlaybackControlRequest):
    """
    Resume video playback from current frame
    
    Args:
        request: Control request with session_id
        
    Returns:
        Current playback state
        
    Raises:
        HTTPException: 404 if session not found
    """
    session_id = request.session_id
    stream = active_streams.get(session_id)
    
    if not stream:
        raise HTTPException(
            status_code=404,
            detail=f"No active stream found for session: {session_id}"
        )
    
    try:
        stream.start_playback()  # start_playback handles both start and resume
        state = stream.get_state()
        frame_idx = stream.frame_idx
        
        logger.info(f"▶️  Resumed playback for session {session_id} from frame {frame_idx}")
        
        return PlaybackStateResponse(
            session_id=session_id,
            state=state,
            frame_idx=frame_idx,
            message=f"Playback resumed from frame {frame_idx}"
        )
    except Exception as e:
        logger.error(f"Error resuming playback: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/stop", response_model=PlaybackStateResponse)
async def stop_playback(request: PlaybackControlRequest):
    """
    Stop video playback completely
    
    Args:
        request: Control request with session_id
        
    Returns:
        Current playback state
        
    Raises:
        HTTPException: 404 if session not found
    """
    session_id = request.session_id
    stream = active_streams.get(session_id)
    
    if not stream:
        raise HTTPException(
            status_code=404,
            detail=f"No active stream found for session: {session_id}"
        )
    
    try:
        stream.stop_playback()
        state = stream.get_state()
        frame_idx = stream.frame_idx
        
        logger.info(f"🛑 Stopped playback for session {session_id}")
        
        return PlaybackStateResponse(
            session_id=session_id,
            state=state,
            frame_idx=frame_idx,
            message="Playback stopped"
        )
    except Exception as e:
        logger.error(f"Error stopping playback: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/state/{session_id}", response_model=PlaybackStateResponse)
async def get_playback_state(session_id: str):
    """
    Get current playback state
    
    Args:
        session_id: Session identifier
        
    Returns:
        Current playback state
        
    Raises:
        HTTPException: 404 if session not found
    """
    stream = active_streams.get(session_id)
    
    if not stream:
        raise HTTPException(
            status_code=404,
            detail=f"No active stream found for session: {session_id}"
        )
    
    try:
        state = stream.get_state()
        frame_idx = stream.frame_idx
        
        return PlaybackStateResponse(
            session_id=session_id,
            state=state,
            frame_idx=frame_idx,
            message=f"Current state: {state}"
        )
    except Exception as e:
        logger.error(f"Error getting playback state: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


def register_stream(session_id: str, stream):
    """
    Register a stream for control via REST API
    
    Args:
        session_id: Unique session identifier
        stream: BinaryAnnotStream instance
    """
    active_streams[session_id] = stream
    logger.info(f"📝 Registered stream for session: {session_id}")


def unregister_stream(session_id: str):
    """
    Unregister a stream when it's closed
    
    Args:
        session_id: Session identifier
    """
    if session_id in active_streams:
        del active_streams[session_id]
        logger.info(f"🗑️  Unregistered stream for session: {session_id}")
