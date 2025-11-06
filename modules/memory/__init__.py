"""
Memory System Module

Hybrid SQL + Vector storage for intelligent conversation memory.
"""

from modules.memory.base import (
    # Enums
    MemoryCategory,
    FactCategory,
    
    # Data classes
    Conversation,
    Fact,
    Action,
    Preference,
    MemoryClassification,
    RetrievalResult,
    
    # Interfaces
    MemoryStore,
    VectorStore,
    MemoryClassifier
)

from modules.memory.sql_store import SQLStore, get_sql_store
from modules.memory.classifier import AIMemoryClassifier, get_classifier
from modules.memory.vector_store import ChromaVectorStore, get_vector_store
from modules.memory.memory_manager import MemoryManager, get_memory_manager

__all__ = [
    # Enums
    'MemoryCategory',
    'FactCategory',
    
    # Data classes
    'Conversation',
    'Fact',
    'Action',
    'Preference',
    'MemoryClassification',
    'RetrievalResult',
    
    # Interfaces
    'MemoryStore',
    'VectorStore',
    'MemoryClassifier',
    
    # Implementations
    'SQLStore',
    'get_sql_store',
    'AIMemoryClassifier',
    'get_classifier',
    'ChromaVectorStore',
    'get_vector_store',
    'MemoryManager',
    'get_memory_manager'
]