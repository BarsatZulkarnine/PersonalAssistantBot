"""
FastAPI Main Application

Run with: uvicorn api.main:app --reload --port 8000
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import asyncio
import json
from datetime import datetime

from core.orchestrator import AssistantOrchestrator
from modules.memory.base import FactCategory
from utils.logger import get_logger

logger = get_logger('api.main')

# Initialize FastAPI app
app = FastAPI(
    title="Voice Assistant API",
    description="AI Voice Assistant with Memory and RAG",
    version="3.0.0"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],  # React/Vite dev servers
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize orchestrator
orchestrator: Optional[AssistantOrchestrator] = None

@app.on_event("startup")
async def startup_event():
    """Initialize orchestrator on startup"""
    global orchestrator
    logger.info("Starting FastAPI application...")
    orchestrator = AssistantOrchestrator()
    logger.info("✅ Orchestrator initialized")

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("Shutting down FastAPI application...")

# ============================================
# REQUEST/RESPONSE MODELS
# ============================================

class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    user_id: str = "default_user"

class ChatResponse(BaseModel):
    response: str
    intent_type: str
    duration_ms: float
    session_id: str
    turn_no: int
    used_memory: bool = False
    used_rag: bool = False

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

class ActionItem(BaseModel):
    id: int
    action_name: str
    params: Optional[Dict[str, Any]]
    result: str
    success: bool
    timestamp: str

class SystemStatus(BaseModel):
    status: str
    uptime_seconds: float
    modules: Dict[str, bool]
    current_activity: str
    memory_stats: Dict[str, Any]

class DocumentItem(BaseModel):
    id: int
    file_name: str
    file_type: str
    num_chunks: int
    indexed_at: str

# ============================================
# CHAT ENDPOINTS
# ============================================

@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Send a message and get response
    
    Example:
    ```
    POST /api/chat
    {
        "message": "What's the weather like?",
        "session_id": "abc123"
    }
    ```
    """
    if not orchestrator:
        raise HTTPException(status_code=503, detail="Orchestrator not initialized")
    
    try:
        start_time = datetime.now()
        
        # Process message
        response = await orchestrator.process_user_input(request.message)
        
        duration_ms = (datetime.now() - start_time).total_seconds() * 1000
        
        # Get session info
        session_id = orchestrator.memory.session_id if orchestrator.memory else "no-session"
        turn_no = orchestrator.memory.turn_counter if orchestrator.memory else 0
        
        return ChatResponse(
            response=response,
            intent_type="unknown",  # TODO: Extract from context
            duration_ms=duration_ms,
            session_id=session_id,
            turn_no=turn_no,
            used_memory=orchestrator.memory is not None,
            used_rag=orchestrator.rag is not None
        )
        
    except Exception as e:
        logger.error(f"Chat error: {e}", exc_info=True)
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
    if not orchestrator:
        raise HTTPException(status_code=503, detail="Orchestrator not initialized")
    
    async def generate():
        try:
            # Process message
            response = await orchestrator.process_user_input(request.message)
            
            # Stream response word by word
            words = response.split()
            for word in words:
                yield f"data: {json.dumps({'word': word, 'done': False})}\n\n"
                await asyncio.sleep(0.05)  # Simulate streaming
            
            yield f"data: {json.dumps({'word': '', 'done': True})}\n\n"
            
        except Exception as e:
            logger.error(f"Stream error: {e}")
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
    
    return StreamingResponse(generate(), media_type="text/event-stream")

@app.get("/api/conversations", response_model=List[ConversationItem])
async def get_conversations(
    limit: int = 50,
    session_id: Optional[str] = None,
    user_id: str = "default_user"
):
    """
    Get conversation history
    
    Example:
    ```
    GET /api/conversations?limit=20&session_id=abc123
    ```
    """
    if not orchestrator or not orchestrator.memory:
        return []
    
    try:
        conversations = orchestrator.memory.get_conversation_history(
            session_id=session_id,
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

# ============================================
# MEMORY ENDPOINTS
# ============================================

@app.get("/api/memory/facts", response_model=List[FactItem])
async def get_facts(
    limit: int = 20,
    category: Optional[str] = None,
    user_id: str = "default_user"
):
    """
    Get stored facts
    
    Example:
    ```
    GET /api/memory/facts?limit=10&category=personal
    ```
    """
    if not orchestrator or not orchestrator.memory:
        return []
    
    try:
        fact_category = FactCategory[category.upper()] if category else None
        
        facts = orchestrator.memory.get_user_facts(
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

@app.get("/api/memory/search")
async def search_memory(
    q: str,
    limit: int = 5,
    user_id: str = "default_user"
):
    """
    Search memory by query
    
    Example:
    ```
    GET /api/memory/search?q=birthday&limit=5
    ```
    """
    if not orchestrator or not orchestrator.memory:
        return {"results": []}
    
    try:
        results = await orchestrator.memory.retrieve_context(
            query=q,
            user_id=user_id,
            max_results=limit,
            include_recent=True
        )
        
        return {
            "results": [
                {
                    "content": r.content,
                    "relevance_score": r.relevance_score,
                    "fact_id": r.fact_id,
                    "conversation_id": r.conversation_id,
                    "source": r.source
                }
                for r in results
            ]
        }
        
    except Exception as e:
        logger.error(f"Search memory error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/memory/stats")
async def get_memory_stats():
    """
    Get memory statistics
    
    Example:
    ```
    GET /api/memory/stats
    ```
    """
    if not orchestrator or not orchestrator.memory:
        return {
            "error": "Memory system not available"
        }
    
    try:
        stats = orchestrator.memory.get_stats()
        return stats
        
    except Exception as e:
        logger.error(f"Get memory stats error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ============================================
# ACTION ENDPOINTS
# ============================================

@app.get("/api/actions/list")
async def list_actions():
    """
    Get list of available actions
    
    Example:
    ```
    GET /api/actions/list
    ```
    """
    if not orchestrator or not orchestrator.actions:
        return {"actions": []}
    
    try:
        actions = orchestrator.actions.get_all_actions()
        
        return {
            "actions": [
                {
                    "name": action.name,
                    "category": action.category.value,
                    "enabled": action.enabled,
                    "description": action.description,
                    "security_level": action.security_level.value
                }
                for action in actions.values()
            ]
        }
        
    except Exception as e:
        logger.error(f"List actions error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/actions/execute")
async def execute_action(
    action_name: str,
    prompt: str,
    params: Optional[Dict[str, Any]] = None
):
    """
    Execute an action manually
    
    Example:
    ```
    POST /api/actions/execute
    {
        "action_name": "MusicAction",
        "prompt": "play jazz",
        "params": {}
    }
    ```
    """
    if not orchestrator or not orchestrator.actions:
        raise HTTPException(status_code=503, detail="Actions not available")
    
    try:
        result = await orchestrator.actions.execute_action(
            action_name=action_name,
            prompt=prompt,
            params=params
        )
        
        return {
            "success": result.success,
            "message": result.message,
            "data": result.data
        }
        
    except Exception as e:
        logger.error(f"Execute action error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ============================================
# SYSTEM MONITORING ENDPOINTS
# ============================================

@app.get("/api/system/status", response_model=SystemStatus)
async def get_system_status():
    """
    Get system status
    
    Example:
    ```
    GET /api/system/status
    ```
    """
    if not orchestrator:
        raise HTTPException(status_code=503, detail="System not ready")
    
    try:
        status = orchestrator.get_status()
        
        # Get memory stats
        memory_stats = {}
        if orchestrator.memory:
            memory_stats = orchestrator.memory.get_stats()
        
        return SystemStatus(
            status="active",
            uptime_seconds=0,  # TODO: Track uptime
            modules={
                "wake_word": status.get('wake_word', False),
                "stt": status.get('stt', False),
                "tts": status.get('tts', False),
                "intent": status.get('intent', False),
                "actions": status.get('actions', 0) > 0,
                "memory": status.get('memory', False),
                "rag": status.get('rag', False)
            },
            current_activity="idle",  # TODO: Track current activity
            memory_stats=memory_stats
        )
        
    except Exception as e:
        logger.error(f"Get system status error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/analytics/intents")
async def get_intent_analytics(period: str = "7d"):
    """
    Get intent breakdown analytics
    
    Example:
    ```
    GET /api/analytics/intents?period=7d
    ```
    """
    # TODO: Implement intent analytics
    return {
        "intents": {
            "AI": 65,
            "Web": 20,
            "Action": 15
        },
        "period": period
    }

@app.get("/api/music/status")
async def get_music_status():
    """
    Get music player status
    
    Example:
    ```
    GET /api/music/status
    ```
    """
    if not orchestrator:
        return {"error": "System not ready"}
    
    try:
        # Find music action
        if orchestrator.actions:
            for action in orchestrator.actions.get_all_actions().values():
                if action.name == "MusicAction" and hasattr(action, 'player'):
                    status = action.player.get_status()
                    return status
        
        return {"status": "not_available"}
        
    except Exception as e:
        logger.error(f"Get music status error: {e}")
        return {"error": str(e)}

# ============================================
# RAG/DOCUMENT ENDPOINTS
# ============================================

@app.get("/api/documents", response_model=List[DocumentItem])
async def get_documents(limit: int = 20):
    """
    Get indexed documents
    
    Example:
    ```
    GET /api/documents?limit=10
    ```
    """
    if not orchestrator or not orchestrator.rag:
        return []
    
    try:
        from modules.rag import get_indexer
        indexer = get_indexer()
        
        stats = indexer.get_stats()
        
        # TODO: Implement actual document listing
        # For now, return stats
        return []
        
    except Exception as e:
        logger.error(f"Get documents error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/documents/search")
async def search_documents(q: str, limit: int = 5):
    """
    Search documents
    
    Example:
    ```
    GET /api/documents/search?q=project+deadline&limit=5
    ```
    """
    if not orchestrator or not orchestrator.rag:
        return {"results": []}
    
    try:
        results = await orchestrator.rag.retrieve(
            query=q,
            top_k=limit
        )
        
        return {
            "results": [
                {
                    "content": r.content,
                    "document_name": r.document_name,
                    "relevance_score": r.relevance_score,
                    "chunk_index": r.chunk_index
                }
                for r in results
            ]
        }
        
    except Exception as e:
        logger.error(f"Search documents error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ============================================
# WEBSOCKET ENDPOINT
# ============================================

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except:
                pass

manager = ConnectionManager()

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket for real-time updates
    
    Example messages:
    - System status updates
    - New messages
    - Action executions
    - Memory updates
    """
    await manager.connect(websocket)
    
    try:
        while True:
            data = await websocket.receive_text()
            
            # Parse message
            try:
                message = json.loads(data)
                msg_type = message.get("type")
                
                if msg_type == "ping":
                    await websocket.send_json({"type": "pong"})
                
                elif msg_type == "chat":
                    # Process chat message
                    response = await orchestrator.process_user_input(message.get("message", ""))
                    await websocket.send_json({
                        "type": "chat_response",
                        "response": response
                    })
                
                else:
                    await websocket.send_json({
                        "type": "error",
                        "message": f"Unknown message type: {msg_type}"
                    })
                    
            except json.JSONDecodeError:
                await websocket.send_json({
                    "type": "error",
                    "message": "Invalid JSON"
                })
                
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        logger.info("WebSocket disconnected")

# ============================================
# HEALTH CHECK
# ============================================

@app.get("/health")
async def health_check():
    """
    Health check endpoint
    
    Example:
    ```
    GET /health
    ```
    """
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "orchestrator_ready": orchestrator is not None
    }

@app.get("/")
async def root():
    """Root endpoint with API info"""
    return {
        "name": "Voice Assistant API",
        "version": "3.0.0",
        "docs": "/docs",
        "health": "/health"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)