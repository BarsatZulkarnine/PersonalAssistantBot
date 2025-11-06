"""
RAG System - Base Interfaces

Defines core types and interfaces for document retrieval.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum
from pathlib import Path

class DocumentType(Enum):
    """Supported document types"""
    PDF = "pdf"
    DOCX = "docx"
    TXT = "txt"
    MARKDOWN = "md"
    HTML = "html"
    CODE = "code"

class ChunkStrategy(Enum):
    """Text chunking strategies"""
    FIXED_SIZE = "fixed"           # Fixed token count
    SENTENCE = "sentence"          # By sentence boundaries
    PARAGRAPH = "paragraph"        # By paragraph
    SEMANTIC = "semantic"          # Semantic similarity

@dataclass
class Document:
    """Represents a document"""
    id: Optional[int] = None
    file_path: str = ""
    file_name: str = ""
    file_type: DocumentType = DocumentType.TXT
    title: str = ""
    content: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # Tracking
    indexed_at: Optional[datetime] = None
    file_size_bytes: int = 0
    num_chunks: int = 0
    
    # User/organization
    user_id: str = "default_user"
    tags: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'id': self.id,
            'file_path': self.file_path,
            'file_name': self.file_name,
            'file_type': self.file_type.value,
            'title': self.title,
            'content': self.content[:500],  # Preview only
            'metadata': self.metadata,
            'indexed_at': self.indexed_at.isoformat() if self.indexed_at else None,
            'file_size_bytes': self.file_size_bytes,
            'num_chunks': self.num_chunks,
            'user_id': self.user_id,
            'tags': self.tags
        }

@dataclass
class DocumentChunk:
    """Represents a chunk of a document"""
    id: Optional[int] = None
    document_id: int = 0
    content: str = ""
    chunk_index: int = 0
    
    # Position in document
    start_char: int = 0
    end_char: int = 0
    
    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # Vector DB reference
    embedding_id: Optional[str] = None
    
    # Timestamps
    created_at: Optional[datetime] = None

@dataclass
class RAGResult:
    """Result from RAG retrieval"""
    content: str
    document_id: int
    document_name: str
    chunk_index: int
    relevance_score: float
    
    # Context
    metadata: Dict[str, Any] = field(default_factory=dict)
    source_path: str = ""
    
    # Position info
    start_char: int = 0
    end_char: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'content': self.content,
            'document_id': self.document_id,
            'document_name': self.document_name,
            'chunk_index': self.chunk_index,
            'relevance_score': self.relevance_score,
            'metadata': self.metadata,
            'source_path': self.source_path
        }

@dataclass
class IndexStats:
    """Statistics about the document index"""
    total_documents: int = 0
    total_chunks: int = 0
    total_size_bytes: int = 0
    documents_by_type: Dict[str, int] = field(default_factory=dict)
    last_indexed: Optional[datetime] = None

# Abstract Interfaces

class DocumentLoader(ABC):
    """Base interface for document loaders"""
    
    @abstractmethod
    def can_load(self, file_path: str) -> bool:
        """Check if this loader can handle the file"""
        pass
    
    @abstractmethod
    def load(self, file_path: str) -> Document:
        """Load a document from file"""
        pass

class TextChunker(ABC):
    """Base interface for text chunking"""
    
    @abstractmethod
    def chunk(self, text: str, chunk_size: int = 500) -> List[str]:
        """Split text into chunks"""
        pass

class DocumentStore(ABC):
    """Base interface for document storage"""
    
    @abstractmethod
    def store_document(self, document: Document) -> int:
        """Store a document and return its ID"""
        pass
    
    @abstractmethod
    def store_chunk(self, chunk: DocumentChunk) -> int:
        """Store a document chunk"""
        pass
    
    @abstractmethod
    def get_document(self, doc_id: int) -> Optional[Document]:
        """Get a document by ID"""
        pass
    
    @abstractmethod
    def get_chunks(self, doc_id: int) -> List[DocumentChunk]:
        """Get all chunks for a document"""
        pass
    
    @abstractmethod
    def search_documents(
        self, 
        query: str, 
        limit: int = 10
    ) -> List[Document]:
        """Search documents by text"""
        pass

class RAGRetriever(ABC):
    """Base interface for RAG retrieval"""
    
    @abstractmethod
    async def retrieve(
        self,
        query: str,
        top_k: int = 5,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[RAGResult]:
        """Retrieve relevant document chunks"""
        pass
    
    @abstractmethod
    def format_context(
        self,
        results: List[RAGResult],
        max_length: int = 1000
    ) -> str:
        """Format results for AI prompt"""
        pass