"""
FastAPI Main Application - REFACTORED & CLEAN

Now organized with separate route modules for maintainability.

Run with: uvicorn api.main:app --reload --port 8000
"""

import sys
from pathlib import Path
from datetime import datetime

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Import dependencies
from api import dependencies
from utils.logger import get_logger

# Import route modules
from api.routes import chat, music, memory, rag, system, sessions
from api.websocket import handler as websocket_handler

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
# STARTUP & SHUTDOWN
# ============================================

@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    try:
        logger.info("Starting API service...")
        
        from core.module_loader import get_module_loader
        from modules.actions.registry import get_action_registry
        from modules.memory import get_memory_manager
        from modules.rag import get_retriever
        from core.services.conversation_service import ConversationService
        
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
        
        # Initialize conversation service (store in dependencies)
        dependencies.conversation_service = ConversationService(
            intent_detector=intent,
            action_registry=actions,
            memory_manager=memory,
            rag_retriever=rag
        )
        
        logger.info("✅ API service ready")
        print("[OK] API service initialized")
        print(f"[OK] Event Bus: {'Enabled' if websocket_handler.EVENT_BUS_AVAILABLE else 'Disabled'}")
        
    except Exception as e:
        logger.error(f"Startup failed: {e}", exc_info=True)
        raise


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("Shutting down API service...")
    
    # Send shutdown event
    if websocket_handler.EVENT_BUS_AVAILABLE:
        from core.event_bus import emit_event, EventType
        await emit_event(
            event_type=EventType.STATUS_UPDATE,
            data={'status': 'shutting_down'}
        )


# ============================================
# REGISTER ROUTES
# ============================================

# Chat routes
app.include_router(chat.router)

# Music routes
app.include_router(music.router)

# Memory routes
app.include_router(memory.router)

# RAG routes
app.include_router(rag.router)

# System routes
app.include_router(system.router)

# Session routes
app.include_router(sessions.router)

# WebSocket endpoint
app.add_api_websocket_route("/ws", websocket_handler.websocket_endpoint)


# ============================================
# ROOT ENDPOINTS
# ============================================

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "name": "Voice Assistant API",
        "version": "4.0.0",
        "status": "ready" if dependencies.conversation_service else "starting",
        "features": [
            "Multi-client chat",
            "Session isolation",
            "Memory & RAG",
            "Music streaming & control",
            "Document upload",
            "Real-time events (WebSocket)" if websocket_handler.EVENT_BUS_AVAILABLE else "WebSocket unavailable",
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


@app.get("/health")
async def health_check():
    """Health check"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service_ready": dependencies.conversation_service is not None,
        "event_bus": websocket_handler.EVENT_BUS_AVAILABLE,
        "active_sessions": len(dependencies.active_sessions)
    }


# ============================================
# MAIN
# ============================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)