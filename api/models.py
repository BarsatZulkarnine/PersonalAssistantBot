"""
API Models - Request/Response Schemas

All Pydantic models for API validation.
"""

from typing import Optional, Dict, Any, List
from pydantic import BaseModel
from datetime import datetime


# ============================================
# CHAT MODELS
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


# ============================================
# MEMORY MODELS
# ============================================

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


# ============================================
# MUSIC MODELS
# ============================================

class MusicControlRequest(BaseModel):
    action: str  # play, pause, resume, stop, next, previous
    song_name: Optional[str] = None


class MusicStatusResponse(BaseModel):
    state: str
    current_song: Optional[str]
    volume: float
    shuffle: bool
    repeat: str
    queue_length: int
    library_size: int


# ============================================
# RAG MODELS
# ============================================

class DocumentUploadResponse(BaseModel):
    success: bool
    filename: str
    chunks: int
    message: str


# ============================================
# SYSTEM MODELS
# ============================================

class SystemStatus(BaseModel):
    status: str
    features: Dict[str, bool]
    stats: Dict[str, Any]


class HealthResponse(BaseModel):
    status: str
    timestamp: str
    service_ready: bool
    event_bus: bool
    active_sessions: int


# ============================================
# SESSION MODELS
# ============================================

class SessionInfo(BaseModel):
    session_id: str
    user_id: str
    client_type: str
    created_at: str
    last_activity: Optional[str] = None
    websocket_connected: bool = False