"""
REST API Interface - FIXED

HTTP API for external systems to interact with the assistant.
No I/O wrappers needed - uses ConversationService directly.
"""

import sys
from pathlib import Path
from typing import Optional
from datetime import datetime

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# FastAPI imports
try:
    from fastapi import FastAPI, HTTPException
    from fastapi.middleware.cors import CORSMiddleware
    from pydantic import BaseModel
    import uvicorn
    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False
    print("FastAPI not installed. Install with: pip install fastapi uvicorn")

from core.services.conversation_service import ConversationService
from core.module_loader import get_module_loader
from modules.memory import get_memory_manager
from modules.rag import get_retriever
from utils.logger import get_logger

logger = get_logger('interfaces.api')

# ===== Data Models =====

class ChatRequest(BaseModel):
    """Chat request model"""
    message: str
    session_id: Optional[str] = None
    user_id: str = "default_user"


class ChatResponse(BaseModel):
    """Chat response model"""
    response: str
    intent: str
    confidence: float
    action_executed: Optional[str] = None
    memory_stored: bool
    memory_category: Optional[str] = None
    rag_used: bool
    duration_ms: float
    timestamp: str


class StatsResponse(BaseModel):
    """System stats response"""
    actions_available: int
    memory_enabled: bool
    rag_enabled: bool
    memory_stats: Optional[dict] = None
    rag_stats: Optional[dict] = None


class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    service_ready: bool
    timestamp: str


# ===== API Setup =====

if FASTAPI_AVAILABLE:
    app = FastAPI(
        title="Voice Assistant API",
        description="REST API for the Voice Assistant",
        version="3.0.0"
    )
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure appropriately for production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Global service instance
    conversation_service: Optional[ConversationService] = None
    
    
    # ===== Startup/Shutdown =====
    
    @app.on_event("startup")
    async def startup_event():
        """Initialize service on startup"""
        global conversation_service
        
        try:
            logger.info("Initializing API service...")
            
            # Load modules
            loader = get_module_loader()
            
            # Load intent detector
            intent = loader.load_module('intent')
            logger.info(f"Intent: {intent.__class__.__name__}")
            
            # Load actions
            from modules.actions.registry import get_action_registry
            actions = get_action_registry()
            logger.info(f"Actions: {len(actions.list_actions())} loaded")
            
            # Load memory (optional)
            try:
                memory = get_memory_manager()
                logger.info("Memory system initialized")
            except Exception as e:
                logger.warning(f"Memory disabled: {e}")
                memory = None
            
            # Load RAG (optional)
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
            
            logger.info("API service ready!")
            print("[OK] API service initialized and ready")
            
        except Exception as e:
            logger.error(f"Startup failed: {e}", exc_info=True)
            raise
    
    
    @app.on_event("shutdown")
    async def shutdown_event():
        """Cleanup on shutdown"""
        logger.info("Shutting down API service...")
    
    
    # ===== API Endpoints =====
    
    @app.get("/", response_model=HealthResponse)
    async def root():
        """Root endpoint - health check"""
        return HealthResponse(
            status="ok",
            service_ready=conversation_service is not None,
            timestamp=datetime.now().isoformat()
        )
    
    
    @app.get("/health", response_model=HealthResponse)
    async def health_check():
        """Health check endpoint"""
        if conversation_service is None:
            raise HTTPException(status_code=503, detail="Service not ready")
        
        return HealthResponse(
            status="healthy",
            service_ready=True,
            timestamp=datetime.now().isoformat()
        )
    
    
    @app.post("/chat", response_model=ChatResponse)
    async def chat(request: ChatRequest):
        """
        Chat endpoint - main conversation interface.
        
        Example:
            POST /chat
            {
                "message": "What's the weather like?",
                "session_id": "abc123",
                "user_id": "user1"
            }
        """
        if conversation_service is None:
            raise HTTPException(status_code=503, detail="Service not ready")
        
        try:
            # Process via service
            result = await conversation_service.process_input(
                user_input=request.message,
                session_id=request.session_id,
                user_id=request.user_id
            )
            
            # Return response
            return ChatResponse(
                response=result['response'],
                intent=result['intent'],
                confidence=result['confidence'],
                action_executed=result['action_executed'],
                memory_stored=result['memory_stored'],
                memory_category=result['memory_category'],
                rag_used=result['rag_used'],
                duration_ms=result['duration_ms'],
                timestamp=datetime.now().isoformat()
            )
            
        except Exception as e:
            logger.error(f"Chat error: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=str(e))
    
    
    @app.get("/stats", response_model=StatsResponse)
    async def get_stats():
        """
        Get system statistics.
        
        Example:
            GET /stats
        """
        if conversation_service is None:
            raise HTTPException(status_code=503, detail="Service not ready")
        
        try:
            stats = conversation_service.get_stats()
            
            return StatsResponse(
                actions_available=stats['actions_available'],
                memory_enabled=stats['memory_enabled'],
                rag_enabled=stats['rag_enabled'],
                memory_stats=stats.get('memory'),
                rag_stats=stats.get('rag')
            )
            
        except Exception as e:
            logger.error(f"Stats error: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=str(e))
    
    
    # ===== Main Function =====
    
    def main():
        """Run API server - NOT ASYNC"""
        print("""
    ╔════════════════════════════════════════╗
    ║   Voice Assistant - API Interface      ║
    ║   REST API Server                      ║
    ╚════════════════════════════════════════╝
        """)
        
        print("Starting API server...")
        print("API will be available at: http://localhost:8000")
        print("Docs available at: http://localhost:8000/docs")
        print("Press Ctrl+C to stop\n")
        
        try:
            # uvicorn.run is blocking and manages its own event loop
            uvicorn.run(
                app,
                host="0.0.0.0",
                port=8000,
                log_level="info"
            )
        except KeyboardInterrupt:
            print("\n\n👋 Shutting down API server...")


else:
    # FastAPI not available
    def main():
        print("❌ FastAPI not installed!")
        print("Install with: pip install fastapi uvicorn")
        print("Then run: python -m interfaces.api.server")
        sys.exit(1)


if __name__ == "__main__":
    main()