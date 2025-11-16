"""
Memory Routes - Conversation & Fact Management
"""

from typing import Optional, List
from fastapi import APIRouter, HTTPException

from api.models import ConversationItem, FactItem
from api.dependencies import get_conversation_service
from modules.memory.base import FactCategory
from utils.logger import get_logger

logger = get_logger('api.routes.memory')

router = APIRouter(prefix="/api", tags=["memory"])


# Event bus import
try:
    from core.event_bus import emit_event, EventType
    EVENT_BUS_AVAILABLE = True
except ImportError:
    EVENT_BUS_AVAILABLE = False


@router.get("/conversations", response_model=List[ConversationItem])
async def get_conversations(
    limit: int = 50,
    session_id: Optional[str] = None,
    user_id: str = "default_user"
):
    """Get conversation history"""
    service = get_conversation_service()
    
    if not service.memory:
        return []
    
    try:
        conversations = service.memory.get_conversation_history(
            session_id=session_id,
            user_id=user_id,
            limit=limit
        )
        
        return [
            ConversationItem(
                id=conv.id,
                session_id=conv.session_id,
                turn_no=conv.turn_no,
                user_input=conv.user_input,
                assistant_response=conv.assistant_response,
                intent_type=conv.intent_type,
                timestamp=conv.timestamp.isoformat() if conv.timestamp else ""
            )
            for conv in conversations
        ]
        
    except Exception as e:
        logger.error(f"Get conversations error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/memory/facts", response_model=List[FactItem])
async def get_facts(
    limit: int = 20,
    category: Optional[str] = None,
    user_id: str = "default_user"
):
    """Get stored facts"""
    service = get_conversation_service()
    
    if not service.memory:
        return []
    
    try:
        fact_category = FactCategory[category.upper()] if category else None
        
        facts = service.memory.get_user_facts(
            user_id=user_id,
            category=fact_category,
            limit=limit
        )
        
        return [
            FactItem(
                id=fact.id,
                content=fact.content,
                category=fact.category.value if fact.category else None,
                importance_score=fact.importance_score,
                created_at=fact.created_at.isoformat() if fact.created_at else ""
            )
            for fact in facts
        ]
        
    except Exception as e:
        logger.error(f"Get facts error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/memory/facts/{fact_id}")
async def delete_fact(fact_id: int, user_id: str = "default_user"):
    """Delete a specific fact"""
    service = get_conversation_service()
    
    if not service.memory:
        raise HTTPException(
            status_code=503,
            detail="Memory system not available"
        )
    
    try:
        # Delete from SQL
        service.memory.sql_storage.delete_fact(fact_id)
        
        # Emit event
        if EVENT_BUS_AVAILABLE:
            await emit_event(
                event_type=EventType.STATUS_UPDATE,
                data={'action': 'fact_deleted', 'fact_id': fact_id},
                user_id=user_id
            )
        
        return {
            "success": True,
            "message": f"Fact {fact_id} deleted"
        }
        
    except Exception as e:
        logger.error(f"Delete fact error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/memory/stats")
async def get_memory_stats():
    """Get memory statistics"""
    service = get_conversation_service()
    
    if not service.memory:
        return {"error": "Memory system not available"}
    
    try:
        stats = service.memory.get_stats()
        return stats
    except Exception as e:
        logger.error(f"Get memory stats error: {e}")
        raise HTTPException(status_code=500, detail=str(e))