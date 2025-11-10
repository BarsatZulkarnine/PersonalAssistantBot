"""
FastAPI Main Application - FIXED & MAINTAINABLE

Clean structure with:
- Single WebSocket endpoint
- Proper service initialization
- Event bus integration
- Clear separation of concerns

Run with: uvicorn api.main:app --reload --port 8000
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, FileResponse
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import asyncio
import json
from datetime import datetime

# Core imports
from core.services.conversation_service import ConversationService
from modules.memory.base import FactCategory
from utils.logger import get_logger

# Event bus imports
try:
    from core.event_bus import (
        get_event_bus, emit_event, emit_music_event, emit_memory_event,
        EventType, Event
    )
    EVENT_BUS_AVAILABLE = True
except ImportError:
    EVENT_BUS_AVAILABLE = False
    print("[WARN] Event bus not available - WebSocket features disabled")

logger = get_logger('api.main')

# ============================================
# FASTAPI APP SETUP
# ============================================

app = FastAPI(
    title="Voice Assistant API",
    description="AI Voice Assistant with Memory, RAG, and Real-time Events",
    version="3.1.0"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================
# GLOBAL STATE
# ============================================

# Services
conversation_service: Optional[ConversationService] = None

# ============================================
# STARTUP & SHUTDOWN
# ============================================

@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    global conversation_service
    
    try:
        logger.info("Starting API service...")
        
        from core.module_loader import get_module_loader
        from modules.actions.registry import get_action_registry
        from modules.memory import get_memory_manager
        from modules.rag import get_retriever
        
        # Load modules
        loader = get_module_loader()
        
        intent = loader.load_module('intent')
        logger.info(f"Intent: {intent.__class__.__name__}")
        
        actions = get_action_registry()
        logger.info(f"Actions: {len(actions.list_actions())} loaded")
        
        # Optional modules
        try:
            memory = get_memory_manager()
            logger.info("Memory system initialized")
        except Exception as e:
            logger.warning(f"Memory disabled: {e}")
            memory = None
        
        try:
            rag = get_retriever()
            logger.info("RAG system initialized")
        except Exception as e:
            logger.warning(f"RAG disabled: {e}")
            rag = None
        
        # Initialize conversation service
        conversation_service = ConversationService(
            intent_detector=intent,
            action_registry=actions,
            memory_manager=memory,
            rag_retriever=rag
        )
        
        logger.info("✅ API service ready")
        print("[OK] API service initialized")
        print(f"[OK] Event Bus: {'Enabled' if EVENT_BUS_AVAILABLE else 'Disabled'}")
        
    except Exception as e:
        logger.error(f"Startup failed: {e}", exc_info=True)
        raise


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("Shutting down API service...")


# ============================================
# REQUEST/RESPONSE MODELS
# ============================================

class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    user_id: str = "default_user"
    client_type: str = "server"  # server, raspberry_pi, web_ui


class ChatResponse(BaseModel):
    response: str
    intent: str
    confidence: float
    action_executed: Optional[str] = None
    action_data: Optional[Dict[str, Any]] = None
    memory_stored: bool = False
    memory_category: Optional[str] = None
    rag_used: bool = False
    duration_ms: float
    session_id: str
    metadata: Dict[str, Any]


class ConversationItem(BaseModel):
    id: int
    session_id: str
    turn_no: int
    user_input: str
    assistant_response: str
    intent_type: Optional[str]
    timestamp: str


class FactItem(BaseModel):
    id: int
    content: str
    category: Optional[str]
    importance_score: float
    created_at: str


class SystemStatus(BaseModel):
    status: str
    features: Dict[str, bool]
    stats: Dict[str, Any]


# ============================================
# CHAT ENDPOINTS
# ============================================

@app.post("/api/chat", response_model=ChatResponse)
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
    if not conversation_service:
        raise HTTPException(status_code=503, detail="Service not ready")
    
    try:
        # Process message
        result = await conversation_service.process_input(
            user_input=request.message,
            session_id=request.session_id,
            user_id=request.user_id,
            client_type=request.client_type
        )
        
        # Emit events if event bus available
        if EVENT_BUS_AVAILABLE:
            await _emit_chat_events(request, result)
        
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
        raise HTTPException(status_code=500, detail=str(e))


async def _emit_chat_events(request: ChatRequest, result: Dict[str, Any]):
    """Helper: Emit events after chat processing"""
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


@app.post("/api/chat/stream")
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
    if not conversation_service:
        raise HTTPException(status_code=503, detail="Service not ready")
    
    async def generate():
        try:
            # Process message
            result = await conversation_service.process_input(
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
            
            yield f"data: {json.dumps({'word': '', 'done': True})}\n\n"
            
        except Exception as e:
            logger.error(f"Stream error: {e}")
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
    
    return StreamingResponse(generate(), media_type="text/event-stream")


# ============================================
# MEMORY ENDPOINTS
# ============================================

@app.get("/api/conversations", response_model=List[ConversationItem])
async def get_conversations(
    limit: int = 50,
    session_id: Optional[str] = None,
    user_id: str = "default_user"
):
    """Get conversation history"""
    if not conversation_service or not conversation_service.memory:
        return []
    
    try:
        conversations = conversation_service.memory.get_conversation_history(
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


@app.get("/api/memory/facts", response_model=List[FactItem])
async def get_facts(
    limit: int = 20,
    category: Optional[str] = None,
    user_id: str = "default_user"
):
    """Get stored facts"""
    if not conversation_service or not conversation_service.memory:
        return []
    
    try:
        fact_category = FactCategory[category.upper()] if category else None
        
        facts = conversation_service.memory.get_user_facts(
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


@app.get("/api/memory/stats")
async def get_memory_stats():
    """Get memory statistics"""
    if not conversation_service or not conversation_service.memory:
        return {"error": "Memory system not available"}
    
    try:
        stats = conversation_service.memory.get_stats()
        return stats
    except Exception as e:
        logger.error(f"Get memory stats error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# MUSIC ENDPOINTS
# ============================================

@app.get("/api/music/stream/{song_name}")
async def stream_music(song_name: str):
    """
    Stream local music file to client.
    
    Usage: Pi/UI requests this URL for playback
    """
    if not conversation_service:
        raise HTTPException(status_code=503, detail="Service not ready")
    
    try:
        # Find music action
        music_action = None
        for action in conversation_service.actions.get_all_actions().values():
            if action.name == "MusicAction" and hasattr(action, 'player'):
                music_action = action
                break
        
        if not music_action or not music_action.player:
            raise HTTPException(status_code=503, detail="Music player not available")
        
        # Find song
        song = music_action.player._find_song(song_name)
        
        if not song:
            raise HTTPException(status_code=404, detail="Song not found")
        
        # Stream file
        file_path = Path(song.path)
        
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="File not found")
        
        return FileResponse(
            path=str(file_path),
            media_type="audio/mpeg",
            filename=file_path.name
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Music streaming error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/music/status")
async def get_music_status():
    """Get current music player status"""
    if not conversation_service:
        return {"error": "Service not ready"}
    
    try:
        for action in conversation_service.actions.get_all_actions().values():
            if action.name == "MusicAction" and hasattr(action, 'player'):
                status = action.player.get_status()
                return status
        
        return {"status": "not_available"}
        
    except Exception as e:
        logger.error(f"Music status error: {e}")
        return {"error": str(e)}


# ============================================
# WEBSOCKET ENDPOINT
# ============================================

@app.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    session_id: Optional[str] = None,
    user_id: str = "default_user",
    client_type: str = "unknown"
):
    """
    WebSocket for real-time events.
    
    Usage:
    ```javascript
    const ws = new WebSocket('ws://localhost:8000/ws?session_id=abc&user_id=user1');
    
    ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        console.log('Event:', data.type, data.data);
    };
    ```
    """
    if not EVENT_BUS_AVAILABLE:
        await websocket.close(code=1011, reason="Event bus not available")
        return
    
    if not conversation_service:
        await websocket.close(code=1011, reason="Service not ready")
        return
    
    event_bus = get_event_bus()
    
    # Generate session_id if not provided
    if not session_id:
        import uuid
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        short_uuid = str(uuid.uuid4())[:8]
        session_id = f"{user_id}_{timestamp}_{short_uuid}"
    
    try:
        # Connect to event bus
        await event_bus.connect(
            websocket=websocket,
            session_id=session_id,
            user_id=user_id,
            client_type=client_type
        )
        
        logger.info(f"WebSocket connected: {session_id[:20]}...")
        
        # Listen for messages
        while True:
            try:
                data = await websocket.receive_text()
                message = json.loads(data)
                
                msg_type = message.get('type')
                
                if msg_type == 'ping':
                    # Heartbeat
                    await websocket.send_text(json.dumps({
                        'type': 'pong',
                        'timestamp': datetime.now().isoformat()
                    }))
                
                elif msg_type == 'subscribe':
                    # Subscribe to event types
                    event_types = message.get('events', [])
                    event_enum = {EventType[e] for e in event_types if e in EventType.__members__}
                    event_bus.subscribe(session_id, event_enum)
                    
                    await websocket.send_text(json.dumps({
                        'type': 'subscribed',
                        'events': event_types
                    }))
                
                elif msg_type == 'unsubscribe':
                    # Unsubscribe
                    event_types = message.get('events', [])
                    event_enum = {EventType[e] for e in event_types if e in EventType.__members__}
                    event_bus.unsubscribe(session_id, event_enum)
                
                elif msg_type == 'chat':
                    # Chat via WebSocket
                    user_message = message.get('message')
                    
                    if user_message:
                        result = await conversation_service.process_input(
                            user_input=user_message,
                            session_id=session_id,
                            user_id=user_id,
                            client_type=client_type
                        )
                        
                        # Send response via WebSocket
                        await websocket.send_text(json.dumps({
                            'type': 'chat_response',
                            'response': result['response'],
                            'action_data': result.get('action_data')
                        }))
                        
                        # Emit events
                        await _emit_chat_events(
                            ChatRequest(
                                message=user_message,
                                session_id=session_id,
                                user_id=user_id,
                                client_type=client_type
                            ),
                            result
                        )
                
                else:
                    await websocket.send_text(json.dumps({
                        'type': 'error',
                        'message': f'Unknown message type: {msg_type}'
                    }))
            
            except json.JSONDecodeError:
                await websocket.send_text(json.dumps({
                    'type': 'error',
                    'message': 'Invalid JSON'
                }))
    
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected: {session_id[:20]}...")
        event_bus.disconnect(websocket)
    
    except Exception as e:
        logger.error(f"WebSocket error: {e}", exc_info=True)
        event_bus.disconnect(websocket)


@app.get("/api/events/stats")
async def get_event_stats():
    """Get event bus statistics"""
    if not EVENT_BUS_AVAILABLE:
        return {"error": "Event bus not available"}
    
    event_bus = get_event_bus()
    return event_bus.get_stats()


# ============================================
# SYSTEM ENDPOINTS
# ============================================

@app.get("/api/system/status", response_model=SystemStatus)
async def get_system_status():
    """Get system status"""
    if not conversation_service:
        raise HTTPException(status_code=503, detail="System not ready")
    
    try:
        stats = conversation_service.get_stats()
        
        return SystemStatus(
            status="active",
            features={
                "conversation": True,
                "memory": stats.get('memory_enabled', False),
                "rag": stats.get('rag_enabled', False),
                "event_bus": EVENT_BUS_AVAILABLE,
                "music_streaming": True,
                "session_isolation": True
            },
            stats=stats
        )
        
    except Exception as e:
        logger.error(f"Status error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health_check():
    """Health check"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service_ready": conversation_service is not None,
        "event_bus": EVENT_BUS_AVAILABLE
    }


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "name": "Voice Assistant API",
        "version": "3.1.0",
        "features": [
            "Multi-client chat",
            "Session isolation",
            "Memory & RAG",
            "Music streaming",
            "Real-time events (WebSocket)" if EVENT_BUS_AVAILABLE else "WebSocket unavailable"
        ],
        "docs": "/docs",
        "health": "/health"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)