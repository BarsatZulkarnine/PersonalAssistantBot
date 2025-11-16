"""
API Dependencies - Shared Resources

Provides dependency injection for FastAPI routes.
"""

from typing import Optional
from fastapi import HTTPException

from core.services.conversation_service import ConversationService
from modules.music.player import MusicPlayer
from utils.logger import get_logger

logger = get_logger('api.dependencies')

# ============================================
# GLOBAL STATE
# ============================================

conversation_service: Optional[ConversationService] = None
active_sessions: dict = {}


# ============================================
# DEPENDENCY FUNCTIONS
# ============================================

def get_conversation_service() -> ConversationService:
    """
    Get conversation service.
    
    Raises:
        HTTPException: If service not ready
    """
    if conversation_service is None:
        raise HTTPException(status_code=503, detail="Service not ready")
    return conversation_service


def get_music_player() -> Optional[MusicPlayer]:
    """
    Get music player from actions.
    
    Returns:
        MusicPlayer instance or None
    """
    if not conversation_service:
        return None
    
    for action in conversation_service.actions.get_all_actions().values():
        if action.name == "MusicAction" and hasattr(action, 'player'):
            return action.player
    
    return None


def require_music_player() -> MusicPlayer:
    """
    Get music player or raise error.
    
    Raises:
        HTTPException: If music player not available
    """
    player = get_music_player()
    if not player:
        raise HTTPException(
            status_code=503,
            detail="Music player not available"
        )
    return player


def get_active_sessions() -> dict:
    """Get active sessions dict"""
    return active_sessions