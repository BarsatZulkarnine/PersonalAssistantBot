"""
Chat Routes - Main Conversation Endpoints
"""

import asyncio
import json
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from api.models import ChatRequest, ChatResponse
from api.dependencies import (
    get_conversation_service,
    get_active_sessions
)
from utils.logger import get_logger

logger = get_logger('api.routes.chat')

router = APIRouter(prefix="/api", tags=["chat"])


# ============================================
# EVENT BUS HELPERS
# ============================================

try:
    from core.event_bus import (
        emit_event, emit_music_event, emit_memory_event,
        EventType
    )
    EVENT_BUS_AVAILABLE = True
except ImportError:
    EVENT_BUS_AVAILABLE = False


async def emit_chat_events(
    request: ChatRequest,
    result: dict
):
    """Emit events after chat processing"""
    if not EVENT_BUS_AVAILABLE:
        return
    
    try:
        # Chat event
        await emit_event(
            event_type=EventType.MESSAGE_RECEIVED,
            data={
                'message': request.message,
                'response': result['response'],
                'intent': result['intent']
            },
            session_id=request.session_id,
            user_id=request.user_id
        )
        
        # Music event
        if result.get('action_data'):
            action_data = result['action_data']
            action = action_data.get('action', '')
            
            if action == 'play_music':
                await emit_music_event(
                    action='play',
                    song_name=action_data.get('music', {}).get('name'),
                    session_id=request.session_id
                )
            elif action in ['pause_music', 'stop_music', 'next_song', 'previous_song']:
                await emit_music_event(
                    action=action.replace('_music', '').replace('_song', ''),
                    session_id=request.session_id
                )
        
        # Memory event
        if result.get('memory_stored'):
            await emit_memory_event(
                fact_content=request.message[:100],
                category=result.get('memory_category', 'unknown'),
                session_id=request.session_id
            )
    
    except Exception as e:
        logger.error(f"Event emission error: {e}")


# ============================================
# ROUTES
# ============================================

@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Main chat endpoint with event emission.
    
    Example:
    ```json
    POST /api/chat
    {
        "message": "play jazz music",
        "session_id": "user1_device_...",
        "user_id": "user1",
        "client_type": "raspberry_pi"
    }
    ```
    """
    service = get_conversation_service()
    sessions = get_active_sessions()
    
    try:
        # Process message
        result = await service.process_input(
            user_input=request.message,
            session_id=request.session_id,
            user_id=request.user_id,
            client_type=request.client_type
        )
        
        # Track session
        session_id = result['metadata']['session_id']
        if session_id not in sessions:
            sessions[session_id] = {
                'user_id': request.user_id,
                'client_type': request.client_type,
                'created_at': datetime.now().isoformat(),
                'last_activity': datetime.now().isoformat()
            }
        else:
            sessions[session_id]['last_activity'] = datetime.now().isoformat()
        
        # Emit events
        if EVENT_BUS_AVAILABLE:
            await emit_chat_events(request, result)
        
        # Return response
        return ChatResponse(
            response=result['response'],
            intent=result['intent'],
            confidence=result['confidence'],
            action_executed=result['action_executed'],
            action_data=result.get('action_data'),
            memory_stored=result['memory_stored'],
            memory_category=result['memory_category'],
            rag_used=result['rag_used'],
            duration_ms=result['duration_ms'],
            session_id=result['metadata']['session_id'],
            metadata=result['metadata']
        )
        
    except Exception as e:
        logger.error(f"Chat error: {e}", exc_info=True)
        
        # Emit error event
        if EVENT_BUS_AVAILABLE:
            await emit_event(
                event_type=EventType.ERROR,
                data={'error': str(e), 'endpoint': '/api/chat'},
                session_id=request.session_id
            )
        
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/chat/stream")
async def chat_stream(request: ChatRequest):
    """
    Stream chat response (Server-Sent Events)
    
    Example:
    ```
    POST /api/chat/stream
    {
        "message": "Tell me a story"
    }
    ```
    """
    service = get_conversation_service()
    
    async def generate():
        try:
            # Process message
            result = await service.process_input(
                user_input=request.message,
                session_id=request.session_id,
                user_id=request.user_id,
                client_type=request.client_type
            )
            
            response = result['response']
            
            # Stream response word by word
            words = response.split()
            for word in words:
                yield f"data: {json.dumps({'word': word, 'done': False})}\n\n"
                await asyncio.sleep(0.05)
            
            # Send completion
            yield f"data: {json.dumps({'word': '', 'done': True, 'metadata': result['metadata']})}\n\n"
            
        except Exception as e:
            logger.error(f"Stream error: {e}")
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
    
    return StreamingResponse(generate(), media_type="text/event-stream")