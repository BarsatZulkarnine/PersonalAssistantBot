"""
Memory System - Base Interfaces

FIXED: Added session_id to RetrievalResult for session isolation.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from enum import Enum
from datetime import datetime

class MemoryCategory(Enum):
    """Categories for memory classification"""
    EPHEMERAL = "ephemeral"        # Don't store
    CONVERSATIONAL = "conversational"  # SQL only
    FACTUAL = "factual"            # SQL + Vector

class FactCategory(Enum):
    """Categories for facts"""
    PERSONAL = "personal"          # Birthday, location, etc.
    PREFERENCE = "preference"      # Likes, dislikes
    KNOWLEDGE = "knowledge"        # Learned information
    CONTEXT = "context"            # Conversation context
    OPINION = "opinion"            # User opinions

class IntentType(Enum):
    """Intent types (from existing system)"""
    AI = "AI"
    WEB = "Web"
    ACTION = "Action"

@dataclass
class Conversation:
    """Represents a conversation turn"""
    id: Optional[int] = None
    session_id: str = ""
    user_id: str = "default_user"
    turn_no: int = 0
    user_input: str = ""
    assistant_response: str = ""
    intent_type: Optional[str] = None
    duration_ms: float = 0.0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    timestamp: Optional[datetime] = None
    deleted_at: Optional[datetime] = None
    purged_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage"""
        return {
            'id': self.id,
            'session_id': self.session_id,
            'user_id': self.user_id,
            'turn_no': self.turn_no,
            'user_input': self.user_input,
            'assistant_response': self.assistant_response,
            'intent_type': self.intent_type,
            'duration_ms': self.duration_ms,
            'prompt_tokens': self.prompt_tokens,
            'completion_tokens': self.completion_tokens,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'deleted_at': self.deleted_at.isoformat() if self.deleted_at else None,
            'purged_at': self.purged_at.isoformat() if self.purged_at else None
        }

@dataclass
class Fact:
    """Represents an important piece of information"""
    id: Optional[int] = None
    user_id: str = "default_user"
    content: str = ""
    content_hash: str = ""
    category: Optional[FactCategory] = None
    importance_score: float = 0.5
    
    # Provenance
    conversation_id: Optional[int] = None
    message_id: Optional[str] = None
    source_doc_id: Optional[str] = None
    source_span: Optional[Dict[str, int]] = None
    
    # Vector DB reference
    embedding_id: Optional[str] = None
    
    # Lifecycle
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    deleted_at: Optional[datetime] = None
    purged_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'content': self.content,
            'content_hash': self.content_hash,
            'category': self.category.value if self.category else None,
            'importance_score': self.importance_score,
            'conversation_id': self.conversation_id,
            'message_id': self.message_id,
            'source_doc_id': self.source_doc_id,
            'source_span': str(self.source_span) if self.source_span else None,
            'embedding_id': self.embedding_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'deleted_at': self.deleted_at.isoformat() if self.deleted_at else None,
            'purged_at': self.purged_at.isoformat() if self.purged_at else None
        }

@dataclass
class MemoryClassification:
    """Result of memory classification"""
    category: MemoryCategory
    importance_score: float
    fact_category: Optional[FactCategory] = None
    extracted_facts: List[str] = field(default_factory=list)
    reasoning: str = ""
    
    def should_store(self) -> bool:
        """Check if this should be stored"""
        return self.category != MemoryCategory.EPHEMERAL
    
    def should_embed(self) -> bool:
        """Check if this should go to vector DB"""
        return self.category == MemoryCategory.FACTUAL

@dataclass
class RetrievalResult:
    """
    Result of memory retrieval.
    
    ✅ FIXED: Added session_id for session isolation
    """
    content: str
    relevance_score: float
    fact_id: Optional[int] = None
    conversation_id: Optional[int] = None
    session_id: Optional[str] = None  # ✅ NEW: Session tracking
    category: Optional[str] = None
    importance: float = 0.5
    created_at: Optional[datetime] = None
    source: str = "unknown"  # 'sql', 'vector', 'hybrid', 'recent'
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'content': self.content,
            'relevance_score': self.relevance_score,
            'fact_id': self.fact_id,
            'conversation_id': self.conversation_id,
            'session_id': self.session_id,  # ✅ NEW
            'category': self.category,
            'importance': self.importance,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'source': self.source
        }

@dataclass
class Action:
    """Represents an action execution"""
    id: Optional[int] = None
    user_id: str = "default_user"
    conversation_id: Optional[int] = None
    action_name: str = ""
    params: Optional[Dict[str, Any]] = None
    result: str = ""
    success: bool = False
    timestamp: Optional[datetime] = None

@dataclass
class Preference:
    """User preference/setting"""
    id: Optional[int] = None
    user_id: str = "default_user"
    key: str = ""
    value: str = ""
    updated_at: Optional[datetime] = None

# Abstract Interfaces

class MemoryStore(ABC):
    """Base interface for memory storage"""
    
    @abstractmethod
    def initialize(self):
        """Initialize storage (create tables, etc.)"""
        pass
    
    @abstractmethod
    def store_conversation(self, conversation: Conversation) -> int:
        """Store a conversation and return its ID"""
        pass
    
    @abstractmethod
    def store_fact(self, fact: Fact) -> int:
        """Store a fact and return its ID"""
        pass
    
    @abstractmethod
    def get_conversations(
        self, 
        user_id: str = "default_user",
        session_id: Optional[str] = None,
        limit: int = 10
    ) -> List[Conversation]:
        """Retrieve conversations"""
        pass
    
    @abstractmethod
    def get_facts(
        self,
        user_id: str = "default_user",
        category: Optional[FactCategory] = None,
        limit: int = 10
    ) -> List[Fact]:
        """Retrieve facts"""
        pass
    
    @abstractmethod
    def search_facts(
        self,
        query: str,
        user_id: str = "default_user",
        limit: int = 5
    ) -> List[RetrievalResult]:
        """Search facts using FTS5"""
        pass

class VectorStore(ABC):
    """Base interface for vector storage"""
    
    @abstractmethod
    def initialize(self):
        """Initialize vector store"""
        pass
    
    @abstractmethod
    def add_embedding(
        self,
        fact_id: int,
        content: str,
        metadata: Dict[str, Any]
    ) -> str:
        """Add content to vector store, return embedding ID"""
        pass
    
    @abstractmethod
    def search(
        self,
        query: str,
        user_id: str = "default_user",
        limit: int = 5,
        min_similarity: float = 0.0
    ) -> List[RetrievalResult]:
        """Search by semantic similarity"""
        pass
    
    @abstractmethod
    def delete(self, embedding_id: str):
        """Delete an embedding"""
        pass

class MemoryClassifier(ABC):
    """Base interface for memory classification"""
    
    @abstractmethod
    async def classify(
        self,
        user_input: str,
        assistant_response: str,
        intent_type: Optional[str] = None
    ) -> MemoryClassification:
        """Classify a conversation's memory worth"""
        pass