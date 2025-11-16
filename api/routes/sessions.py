"""
Session Routes - Session Management
"""

from fastapi import APIRouter, HTTPException

from api.dependencies import get_active_sessions
from utils.logger import get_logger

logger = get_logger('api.routes.sessions')

router = APIRouter(prefix="/api/sessions", tags=["sessions"])


# Event bus import
try:
    from core.event_bus import emit_event, EventType
    EVENT_BUS_AVAILABLE = True
except ImportError:
    EVENT_BUS_AVAILABLE = False


@router.get("")
async def get_active_sessions():
    """Get list of active sessions"""
    sessions = get_active_sessions()
    
    return {
        "total": len(sessions),
        "sessions": sessions
    }


@router.delete("/{session_id}")
async def close_session(session_id: str):
    """Close/cleanup a specific session"""
    sessions = get_active_sessions()
    
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    try:
        # Emit disconnect event
        if EVENT_BUS_AVAILABLE:
            await emit_event(
                event_type=EventType.CLIENT_DISCONNECTED,
                data={'reason': 'manual_close'},
                session_id=session_id
            )
        
        # Remove from active sessions
        del sessions[session_id]
        
        return {
            "success": True,
            "message": f"Session {session_id} closed"
        }
        
    except Exception as e:
        logger.error(f"Session close error: {e}")
        raise HTTPException(status_code=500, detail=str(e))