"""
System Routes - Status & Health
"""

from fastapi import APIRouter, HTTPException

from api.models import SystemStatus
from api.dependencies import get_conversation_service, get_music_player
from utils.logger import get_logger

logger = get_logger('api.routes.system')

router = APIRouter(prefix="/api/system", tags=["system"])


# Event bus import
try:
    from core.event_bus import get_event_bus
    EVENT_BUS_AVAILABLE = True
except ImportError:
    EVENT_BUS_AVAILABLE = False


@router.get("/status", response_model=SystemStatus)
async def get_system_status():
    """Get system status"""
    service = get_conversation_service()
    
    try:
        stats = service.get_stats()
        
        return SystemStatus(
            status="active",
            features={
                "conversation": True,
                "memory": stats.get('memory_enabled', False),
                "rag": stats.get('rag_enabled', False),
                "event_bus": EVENT_BUS_AVAILABLE,
                "music_streaming": get_music_player() is not None,
                "session_isolation": True,
                "websocket": EVENT_BUS_AVAILABLE
            },
            stats={
                **stats,
                'event_bus': get_event_bus().get_stats() if EVENT_BUS_AVAILABLE else None
            }
        )
        
    except Exception as e:
        logger.error(f"Status error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/events/stats")
async def get_event_stats():
    """Get event bus statistics"""
    if not EVENT_BUS_AVAILABLE:
        return {"error": "Event bus not available"}
    
    from api.dependencies import get_active_sessions
    
    event_bus = get_event_bus()
    stats = event_bus.get_stats()
    
    # Add active session info
    sessions = get_active_sessions()
    stats['active_sessions'] = {
        sid: {
            'user_id': info['user_id'],
            'client_type': info['client_type'],
            'websocket_connected': info.get('websocket_connected', False),
            'created_at': info['created_at']
        }
        for sid, info in sessions.items()
    }
    
    return stats