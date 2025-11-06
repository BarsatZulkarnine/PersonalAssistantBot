"""
Memory Vector Store - ChromaDB Integration

Handles semantic search using embeddings for factual information.
"""

import os
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime

try:
    import chromadb
    from chromadb.config import Settings
    CHROMADB_AVAILABLE = True
except ImportError:
    CHROMADB_AVAILABLE = False

from modules.memory.base import VectorStore, RetrievalResult
from utils.logger import get_logger

logger = get_logger('memory.vector_store')

class ChromaVectorStore(VectorStore):
    """
    ChromaDB implementation for vector storage.
    
    Stores embeddings of factual information for semantic search.
    """
    
    def __init__(self, persist_directory: str = "data/chromadb"):
        if not CHROMADB_AVAILABLE:
            raise ImportError(
                "ChromaDB not installed. Install with: pip install chromadb"
            )
        
        self.persist_directory = Path(persist_directory)
        self.persist_directory.mkdir(parents=True, exist_ok=True)
        
        self.client: Optional[chromadb.ClientAPI] = None
        self.collection = None
        self.collection_name = "memory_facts"
        
        logger.info(f"ChromaVectorStore initialized (path={persist_directory})")
    
    def initialize(self):
        """Initialize ChromaDB client and collection"""
        try:
            # Create persistent client
            self.client = chromadb.PersistentClient(
                path=str(self.persist_directory),
                settings=Settings(
                    anonymized_telemetry=False,
                    allow_reset=True
                )
            )
            
            # Get or create collection
            self.collection = self.client.get_or_create_collection(
                name=self.collection_name,
                metadata={"description": "Memory facts with semantic search"}
            )
            
            count = self.collection.count()
            logger.info(f"✅ ChromaDB initialized ({count} embeddings)")
            
        except Exception as e:
            logger.error(f"Failed to initialize ChromaDB: {e}")
            raise
    
    def add_embedding(
        self,
        fact_id: int,
        content: str,
        metadata: Dict[str, Any]
    ) -> str:
        """
        Add content to vector store.
        
        Args:
            fact_id: ID from SQL database
            content: Text to embed
            metadata: Additional metadata
            
        Returns:
            Embedding ID (string)
        """
        if not self.collection:
            raise RuntimeError("Vector store not initialized")
        
        # Generate embedding ID
        embedding_id = f"fact_{fact_id}"
        
        # Prepare metadata (ChromaDB requires string values)
        chroma_metadata = {
            "fact_id": str(fact_id),
            "user_id": str(metadata.get("user_id", "default_user")),
            "category": str(metadata.get("category", "unknown")),
            "importance": str(metadata.get("importance", 0.5)),
            "created_at": metadata.get("created_at", datetime.now().isoformat())
        }
        
        # Add to collection (ChromaDB auto-generates embeddings)
        try:
            self.collection.add(
                ids=[embedding_id],
                documents=[content],
                metadatas=[chroma_metadata]
            )
            
            logger.debug(f"Added embedding {embedding_id}: {content[:50]}...")
            return embedding_id
            
        except Exception as e:
            logger.error(f"Failed to add embedding: {e}")
            raise
    
    def search(
        self,
        query: str,
        user_id: str = "default_user",
        limit: int = 5,
        min_similarity: float = 0.0
    ) -> List[RetrievalResult]:
        """
        Search by semantic similarity.
        
        Args:
            query: Search query
            user_id: Filter by user
            limit: Max results
            min_similarity: Minimum similarity threshold (0-1)
            
        Returns:
            List of RetrievalResult objects
        """
        if not self.collection:
            raise RuntimeError("Vector store not initialized")
        
        try:
            # Query with metadata filter
            results = self.collection.query(
                query_texts=[query],
                n_results=limit,
                where={"user_id": user_id}
            )
            
            # Parse results
            retrieval_results = []
            
            if results['ids'] and len(results['ids'][0]) > 0:
                for i in range(len(results['ids'][0])):
                    # Calculate similarity (ChromaDB returns distances)
                    distance = results['distances'][0][i] if results['distances'] else 1.0
                    similarity = 1.0 - min(distance, 1.0)  # Convert distance to similarity
                    
                    # Skip if below threshold
                    if similarity < min_similarity:
                        continue
                    
                    metadata = results['metadatas'][0][i]
                    
                    retrieval_results.append(RetrievalResult(
                        content=results['documents'][0][i],
                        relevance_score=similarity,
                        fact_id=int(metadata.get('fact_id', 0)),
                        category=metadata.get('category'),
                        importance=float(metadata.get('importance', 0.5)),
                        created_at=datetime.fromisoformat(metadata['created_at']) if 'created_at' in metadata else None,
                        source='vector'
                    ))
            
            logger.debug(f"Vector search found {len(retrieval_results)} results for: {query}")
            return retrieval_results
            
        except Exception as e:
            logger.error(f"Vector search error: {e}")
            return []
    
    def delete(self, embedding_id: str):
        """Delete an embedding"""
        if not self.collection:
            raise RuntimeError("Vector store not initialized")
        
        try:
            self.collection.delete(ids=[embedding_id])
            logger.debug(f"Deleted embedding {embedding_id}")
        except Exception as e:
            logger.error(f"Failed to delete embedding: {e}")
    
    def update(
        self,
        embedding_id: str,
        content: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Update an embedding"""
        if not self.collection:
            raise RuntimeError("Vector store not initialized")
        
        try:
            update_data = {"ids": [embedding_id]}
            
            if content:
                update_data["documents"] = [content]
            
            if metadata:
                # Convert metadata to strings
                chroma_metadata = {
                    k: str(v) for k, v in metadata.items()
                }
                update_data["metadatas"] = [chroma_metadata]
            
            self.collection.update(**update_data)
            logger.debug(f"Updated embedding {embedding_id}")
            
        except Exception as e:
            logger.error(f"Failed to update embedding: {e}")
    
    def get_by_id(self, embedding_id: str) -> Optional[Dict[str, Any]]:
        """Get embedding by ID"""
        if not self.collection:
            raise RuntimeError("Vector store not initialized")
        
        try:
            results = self.collection.get(ids=[embedding_id])
            
            if results['ids']:
                return {
                    'id': results['ids'][0],
                    'content': results['documents'][0],
                    'metadata': results['metadatas'][0]
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get embedding: {e}")
            return None
    
    def count(self) -> int:
        """Get total number of embeddings"""
        if not self.collection:
            return 0
        
        try:
            return self.collection.count()
        except Exception as e:
            logger.error(f"Failed to count embeddings: {e}")
            return 0
    
    def reset(self):
        """Reset the collection (delete all embeddings)"""
        if not self.client:
            raise RuntimeError("Vector store not initialized")
        
        try:
            self.client.delete_collection(self.collection_name)
            self.collection = self.client.create_collection(
                name=self.collection_name,
                metadata={"description": "Memory facts with semantic search"}
            )
            logger.warning("⚠️  Collection reset - all embeddings deleted")
            
        except Exception as e:
            logger.error(f"Failed to reset collection: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get vector store statistics"""
        if not self.collection:
            return {"error": "Not initialized"}
        
        try:
            count = self.collection.count()
            
            return {
                "total_embeddings": count,
                "collection_name": self.collection_name,
                "persist_directory": str(self.persist_directory)
            }
            
        except Exception as e:
            logger.error(f"Failed to get stats: {e}")
            return {"error": str(e)}


# Convenience function

_vector_store_instance = None

def get_vector_store() -> ChromaVectorStore:
    """Get or create global vector store instance"""
    global _vector_store_instance
    if _vector_store_instance is None:
        _vector_store_instance = ChromaVectorStore()
        _vector_store_instance.initialize()
    return _vector_store_instance