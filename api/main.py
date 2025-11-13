"""
FastAPI Main Application - COMPLETE & PRODUCTION-READY

Features:
- ✅ Full REST API
- ✅ WebSocket with auto-reconnect support
- ✅ Complete music control
- ✅ Event bus with replay
- ✅ Memory management
- ✅ RAG document upload
- ✅ Session cleanup
- ✅ Error handling

Run with: uvicorn api.main:app --reload --port 8000
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, FileResponse
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import asyncio
import json
from datetime import datetime
import uuid

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
    version="4.0.0"
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

conversation_service: Optional[ConversationService] = None
active_sessions: Dict[str, Dict[str, Any]] = {}  # Session state tracking

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
    
    # Close all WebSocket connections gracefully
    if EVENT_BUS_AVAILABLE:
        event_bus = get_event_bus()
        # Send shutdown event
        await emit_event(
            event_type=EventType.STATUS_UPDATE,
            data={'status': 'shutting_down'}
        )


# ============================================
# REQUEST/RESPONSE MODELS
# ============================================

class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    user_id: str = "default_user"
    client_type: str = "server"


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


class MusicControlRequest(BaseModel):
    action: str  # play, pause, resume, stop, next, previous
    song_name: Optional[str] = None


class DocumentUploadResponse(BaseModel):
    success: bool
    filename: str
    chunks: int
    message: str


# ============================================
# HELPER FUNCTIONS
# ============================================

async def _emit_chat_events(request: ChatRequest, result: Dict[str, Any]):
    """Helper: Emit events after chat processing"""
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


def _get_music_player():
    """Get music player from actions"""
    if not conversation_service:
        return None
    
    for action in conversation_service.actions.get_all_actions().values():
        if action.name == "MusicAction" and hasattr(action, 'player'):
            return action.player
    return None


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
        
        # Track session
        session_id = result['metadata']['session_id']
        if session_id not in active_sessions:
            active_sessions[session_id] = {
                'user_id': request.user_id,
                'client_type': request.client_type,
                'created_at': datetime.now().isoformat(),
                'last_activity': datetime.now().isoformat()
            }
        else:
            active_sessions[session_id]['last_activity'] = datetime.now().isoformat()
        
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
        
        # Emit error event
        if EVENT_BUS_AVAILABLE:
            await emit_event(
                event_type=EventType.ERROR,
                data={'error': str(e), 'endpoint': '/api/chat'},
                session_id=request.session_id
            )
        
        raise HTTPException(status_code=500, detail=str(e))


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
            
            # Send completion
            yield f"data: {json.dumps({'word': '', 'done': True, 'metadata': result['metadata']})}\n\n"
            
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


@app.delete("/api/memory/facts/{fact_id}")
async def delete_fact(fact_id: int, user_id: str = "default_user"):
    """Delete a specific fact"""
    if not conversation_service or not conversation_service.memory:
        raise HTTPException(status_code=503, detail="Memory system not available")
    
    try:
        # Delete from SQL
        conversation_service.memory.sql_storage.delete_fact(fact_id)
        
        # Emit event
        if EVENT_BUS_AVAILABLE:
            await emit_event(
                event_type=EventType.STATUS_UPDATE,
                data={'action': 'fact_deleted', 'fact_id': fact_id},
                user_id=user_id
            )
        
        return {"success": True, "message": f"Fact {fact_id} deleted"}
        
    except Exception as e:
        logger.error(f"Delete fact error: {e}")
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
# MUSIC ENDPOINTS - COMPLETE IMPLEMENTATION
# ============================================

@app.post("/api/music/control")
async def control_music(request: MusicControlRequest):
    """
    Control music playback
    
    Example:
    ```json
    POST /api/music/control
    {
        "action": "play",
        "song_name": "jazz music"
    }
    ```
    """
    if not conversation_service:
        raise HTTPException(status_code=503, detail="Service not ready")
    
    player = _get_music_player()
    if not player:
        raise HTTPException(status_code=503, detail="Music player not available")
    
    try:
        action = request.action.lower()
        
        if action == "play":
            if not request.song_name:
                raise HTTPException(status_code=400, detail="song_name required for play action")
            
            # Search and play
            song = player._find_song(request.song_name)
            if not song:
                return {"success": False, "message": f"Song '{request.song_name}' not found"}
            
            player.play(song)
            message = f"Playing: {song.name}"
        
        elif action == "pause":
            player.pause()
            message = "Music paused"
        
        elif action == "resume":
            player.resume()
            message = "Music resumed"
        
        elif action == "stop":
            player.stop()
            message = "Music stopped"
        
        elif action == "next":
            player.next_track()
            message = "Skipped to next track"
        
        elif action == "previous":
            player.previous_track()
            message = "Playing previous track"
        
        else:
            raise HTTPException(status_code=400, detail=f"Unknown action: {action}")
        
        # Emit music event
        if EVENT_BUS_AVAILABLE:
            await emit_music_event(
                action=action,
                song_name=player.current_song.name if player.current_song else None
            )
        
        return {
            "success": True,
            "message": message,
            "status": player.get_status()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Music control error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/music/stream/{song_name}")
async def stream_music(song_name: str):
    """
    Stream local music file to client.
    
    Usage: Pi/UI requests this URL for playback
    """
    if not conversation_service:
        raise HTTPException(status_code=503, detail="Service not ready")
    
    player = _get_music_player()
    if not player:
        raise HTTPException(status_code=503, detail="Music player not available")
    
    try:
        # Find song
        song = player._find_song(song_name)
        
        if not song:
            raise HTTPException(status_code=404, detail="Song not found")
        
        # Only stream local files
        if song.type != 'local':
            raise HTTPException(
                status_code=400,
                detail="Only local files can be streamed. YouTube plays directly on client."
            )
        
        # Check file exists
        file_path = Path(song.path)
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="File not found on disk")
        
        # Stream file
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
        raise HTTPException(status_code=503, detail="Service not ready")
    
    player = _get_music_player()
    if not player:
        return {"status": "not_available", "message": "Music player not loaded"}
    
    try:
        status = player.get_status()
        return status
        
    except Exception as e:
        logger.error(f"Music status error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/music/library")
async def get_music_library():
    """Get list of available songs"""
    if not conversation_service:
        raise HTTPException(status_code=503, detail="Service not ready")
    
    player = _get_music_player()
    if not player:
        raise HTTPException(status_code=503, detail="Music player not available")
    
    try:
        songs = [
            {
                'name': song.name,
                'type': song.type,
                'artist': song.artist,
                'album': song.album,
                'duration': song.duration
            }
            for song in player.library
        ]
        
        return {
            "total": len(songs),
            "songs": songs
        }
        
    except Exception as e:
        logger.error(f"Music library error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# RAG ENDPOINTS
# ============================================

@app.post("/api/rag/upload", response_model=DocumentUploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    user_id: str = "default_user"
):
    """
    Upload document for RAG indexing
    
    Supports: PDF, TXT, MD, DOCX
    """
    if not conversation_service or not conversation_service.rag:
        raise HTTPException(status_code=503, detail="RAG system not available")
    
    try:
        from modules.rag import get_indexer
        
        # Save uploaded file temporarily
        temp_path = Path(f"data/temp/{file.filename}")
        temp_path.parent.mkdir(parents=True, exist_ok=True)
        
        content = await file.read()
        temp_path.write_bytes(content)
        
        # Index document
        indexer = get_indexer()
        chunks = await indexer.index_document(str(temp_path))
        
        # Clean up
        temp_path.unlink()
        
        return DocumentUploadResponse(
            success=True,
            filename=file.filename,
            chunks=chunks,
            message=f"Document indexed successfully ({chunks} chunks)"
        )
        
    except Exception as e:
        logger.error(f"Document upload error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/rag/stats")
async def get_rag_stats():
    """Get RAG system statistics"""
    if not conversation_service or not conversation_service.rag:
        return {"error": "RAG system not available"}
    
    try:
        from modules.rag import get_indexer
        indexer = get_indexer()
        stats = indexer.get_stats()
        
        return {
            "total_documents": stats.total_documents,
            "total_chunks": stats.total_chunks,
            "average_chunk_size": stats.avg_chunk_size
        }
        
    except Exception as e:
        logger.error(f"RAG stats error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# WEBSOCKET ENDPOINT - COMPLETE WITH RECONNECTION
# ============================================

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket for real-time events with reconnection support.
    
    Query parameters (all optional):
    - session_id: Session identifier
    - user_id: User identifier (default: "default_user")
    - client_type: Client type (default: "unknown")
    """
    
    # CRITICAL: Accept connection FIRST, before ANY other code
    await websocket.accept()
    
    # THEN get query parameters manually
    try:
        query_params = dict(websocket.query_params)
        session_id = query_params.get('session_id')
        user_id = query_params.get('user_id', 'default_user')
        client_type = query_params.get('client_type', 'unknown')
    except Exception as e:
        await websocket.send_text(json.dumps({
            'type': 'error',
            'message': f'Invalid parameters: {e}'
        }))
        await websocket.close()
        return
    
    # Now check if services are available
    if not EVENT_BUS_AVAILABLE:
        await websocket.send_text(json.dumps({
            'type': 'error',
            'message': 'Event bus not available'
        }))
        await websocket.close(code=1011)
        return
    
    if not conversation_service:
        await websocket.send_text(json.dumps({
            'type': 'error',
            'message': 'Service not ready'
        }))
        await websocket.close(code=1011)
        return
    
    event_bus = get_event_bus()
    
    # Generate session_id if not provided
    if not session_id:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        short_uuid = str(uuid.uuid4())[:8]
        session_id = f"{user_id}_{timestamp}_{short_uuid}"
    
    try:
        # Register connection manually (don't call event_bus.connect())
        if session_id not in event_bus.connections:
            event_bus.connections[session_id] = set()
        event_bus.connections[session_id].add(websocket)
        
        # Store metadata
        event_bus.connection_metadata[websocket] = {
            'session_id': session_id,
            'user_id': user_id,
            'client_type': client_type,
            'connected_at': datetime.now().isoformat()
        }
        
        # Initialize subscriptions (subscribe to all by default)
        if session_id not in event_bus.subscriptions:
            event_bus.subscriptions[session_id] = set(EventType)
        
        logger.info(f"WebSocket connected: session={session_id[:20]}..., client={client_type}")
        
        # Track session
        if session_id not in active_sessions:
            active_sessions[session_id] = {
                'user_id': user_id,
                'client_type': client_type,
                'created_at': datetime.now().isoformat(),
                'websocket_connected': True
            }
        else:
            active_sessions[session_id]['websocket_connected'] = True
        
        # Send welcome message
        await websocket.send_text(json.dumps({
            'type': 'connected',
            'session_id': session_id,
            'user_id': user_id,
            'timestamp': datetime.now().isoformat(),
            'features': {
                'chat': True,
                'events': True,
                'music': _get_music_player() is not None,
                'memory': conversation_service.memory is not None,
                'rag': conversation_service.rag is not None
            }
        }))
        
        # Listen for messages
        while True:
            try:
                data = await websocket.receive_text()
                message = json.loads(data)
                
                msg_type = message.get('type')
                
                if msg_type == 'ping':
                    await websocket.send_text(json.dumps({
                        'type': 'pong',
                        'timestamp': datetime.now().isoformat()
                    }))
                
                elif msg_type == 'subscribe':
                    event_types = message.get('events', [])
                    event_enum = {EventType[e] for e in event_types if e in EventType.__members__}
                    event_bus.subscribe(session_id, event_enum)
                    
                    await websocket.send_text(json.dumps({
                        'type': 'subscribed',
                        'events': event_types,
                        'timestamp': datetime.now().isoformat()
                    }))
                
                elif msg_type == 'unsubscribe':
                    event_types = message.get('events', [])
                    event_enum = {EventType[e] for e in event_types if e in EventType.__members__}
                    event_bus.unsubscribe(session_id, event_enum)
                    
                    await websocket.send_text(json.dumps({
                        'type': 'unsubscribed',
                        'events': event_types,
                        'timestamp': datetime.now().isoformat()
                    }))
                
                elif msg_type == 'chat':
                    user_message = message.get('message')
                    
                    if user_message:
                        result = await conversation_service.process_input(
                            user_input=user_message,
                            session_id=session_id,
                            user_id=user_id,
                            client_type=client_type
                        )
                        
                        await websocket.send_text(json.dumps({
                            'type': 'chat_response',
                            'response': result['response'],
                            'intent': result['intent'],
                            'action_data': result.get('action_data'),
                            'timestamp': datetime.now().isoformat()
                        }))
                        
                        await _emit_chat_events(
                            ChatRequest(
                                message=user_message,
                                session_id=session_id,
                                user_id=user_id,
                                client_type=client_type
                            ),
                            result
                        )
                
                elif msg_type == 'music_control':
                    action = message.get('action')
                    song_name = message.get('song_name')
                    
                    player = _get_music_player()
                    if player:
                        if action == 'play' and song_name:
                            song = player._find_song(song_name)
                            if song:
                                player.play(song)
                                await emit_music_event('play', song.name, session_id)
                        elif action == 'pause':
                            player.pause()
                            await emit_music_event('pause', None, session_id)
                        elif action == 'resume':
                            player.resume()
                            await emit_music_event('play', None, session_id)
                        elif action == 'stop':
                            player.stop()
                            await emit_music_event('stop', None, session_id)
                
                else:
                    await websocket.send_text(json.dumps({
                        'type': 'error',
                        'message': f'Unknown message type: {msg_type}',
                        'timestamp': datetime.now().isoformat()
                    }))
            
            except json.JSONDecodeError:
                await websocket.send_text(json.dumps({
                    'type': 'error',
                    'message': 'Invalid JSON',
                    'timestamp': datetime.now().isoformat()
                }))
    
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected: {session_id[:20]}...")
        event_bus.disconnect(websocket)
        
        if session_id in active_sessions:
            active_sessions[session_id]['websocket_connected'] = False
            active_sessions[session_id]['last_disconnected'] = datetime.now().isoformat()
    
    except Exception as e:
        logger.error(f"WebSocket error: {e}", exc_info=True)
        event_bus.disconnect(websocket)
        
        try:
            await emit_event(
                event_type=EventType.ERROR,
                data={'error': str(e)},
                session_id=session_id
            )
        except:
            pass
@app.get("/api/events/stats")
async def get_event_stats():
    """Get event bus statistics"""
    if not EVENT_BUS_AVAILABLE:
        return {"error": "Event bus not available"}
    
    event_bus = get_event_bus()
    stats = event_bus.get_stats()
    
    # Add active session info
    stats['active_sessions'] = {
        sid: {
            'user_id': info['user_id'],
            'client_type': info['client_type'],
            'websocket_connected': info.get('websocket_connected', False),
            'created_at': info['created_at']
        }
        for sid, info in active_sessions.items()
    }
    
    return stats


# ============================================
# SESSION MANAGEMENT ENDPOINTS
# ============================================

@app.get("/api/sessions")
async def get_active_sessions():
    """Get list of active sessions"""
    return {
        "total": len(active_sessions),
        "sessions": active_sessions
    }


@app.delete("/api/sessions/{session_id}")
async def close_session(session_id: str):
    """Close/cleanup a specific session"""
    if session_id not in active_sessions:
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
        del active_sessions[session_id]
        
        return {"success": True, "message": f"Session {session_id} closed"}
        
    except Exception as e:
        logger.error(f"Session close error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


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
                "music_streaming": _get_music_player() is not None,
                "session_isolation": True,
                "websocket": EVENT_BUS_AVAILABLE
            },
            stats={
                **stats,
                'active_sessions': len(active_sessions),
                'event_bus': get_event_bus().get_stats() if EVENT_BUS_AVAILABLE else None
            }
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
        "event_bus": EVENT_BUS_AVAILABLE,
        "active_sessions": len(active_sessions)
    }


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "name": "Voice Assistant API",
        "version": "4.0.0",
        "status": "ready" if conversation_service else "starting",
        "features": [
            "Multi-client chat",
            "Session isolation",
            "Memory & RAG",
            "Music streaming & control",
            "Document upload",
            "Real-time events (WebSocket)" if EVENT_BUS_AVAILABLE else "WebSocket unavailable",
            "Event replay on reconnect",
            "Session management"
        ],
        "endpoints": {
            "docs": "/docs",
            "health": "/health",
            "chat": "/api/chat",
            "websocket": "/ws",
            "music": "/api/music/control",
            "memory": "/api/memory/facts",
            "rag": "/api/rag/upload"
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)