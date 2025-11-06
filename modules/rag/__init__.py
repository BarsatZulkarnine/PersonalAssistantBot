"""
RAG System - Retrieval Augmented Generation

Allows the assistant to search and understand your personal documents.
"""

from modules.rag.base import (
    Document,
    DocumentChunk,
    DocumentType,
    ChunkStrategy,
    RAGResult,
    IndexStats,
    DocumentLoader,
    TextChunker,
    DocumentStore,
    RAGRetriever
)

from modules.rag.loaders import get_loader_registry, LoaderRegistry
from modules.rag.chunker import get_chunker, SmartChunker
from modules.rag.indexer import get_indexer, DocumentIndexer
from modules.rag.retriever import get_retriever, HybridRetriever

__all__ = [
    # Base types
    'Document',
    'DocumentChunk',
    'DocumentType',
    'ChunkStrategy',
    'RAGResult',
    'IndexStats',
    
    # Interfaces
    'DocumentLoader',
    'TextChunker',
    'DocumentStore',
    'RAGRetriever',
    
    # Implementations
    'LoaderRegistry',
    'get_loader_registry',
    'SmartChunker',
    'get_chunker',
    'DocumentIndexer',
    'get_indexer',
    'HybridRetriever',
    'get_retriever'
]