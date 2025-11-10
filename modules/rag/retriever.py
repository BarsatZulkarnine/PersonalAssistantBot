"""
RAG Retriever - Search and Retrieve Document Chunks

Combines SQL FTS and vector search for optimal retrieval.
"""

import sqlite3
import json
from typing import List, Optional, Dict, Any
from pathlib import Path

from modules.rag.base import RAGRetriever, RAGResult
from modules.memory.vector_store import ChromaVectorStore, CHROMADB_AVAILABLE
from utils.logger import get_logger

logger = get_logger('rag.retriever')

class HybridRetriever(RAGRetriever):
    """
    Hybrid retrieval combining:
    1. SQL FTS (keyword matching)
    2. Vector search (semantic similarity)
    3. Ranking and deduplication
    """
    
    def __init__(
        self,
        db_path: str = "data/rag_documents.db",
        vector_path: str = "data/rag_chromadb"
    ):
        self.db_path = Path(db_path)
        self.conn: Optional[sqlite3.Connection] = None
        
        # Vector store for semantic search
        self.vector_store: Optional[ChromaVectorStore] = None
        if CHROMADB_AVAILABLE:
            self.vector_store = ChromaVectorStore(vector_path)
            try:
                self.vector_store.initialize()
                # Use different collection for RAG
                self.vector_store.collection_name = "rag_documents"
                self.vector_store.collection = self.vector_store.client.get_or_create_collection(
                    name="rag_documents",
                    metadata={"description": "RAG document chunks"}
                )
                logger.info("Vector store ready for RAG")
            except Exception as e:
                logger.warning(f"Vector store initialization failed: {e}")
                self.vector_store = None
        
        logger.info(f"HybridRetriever initialized (vector={'enabled' if self.vector_store else 'disabled'})")
    
    def _get_connection(self) -> sqlite3.Connection:
        """Get database connection"""
        if self.conn is None:
            self.conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
            self.conn.row_factory = sqlite3.Row
        return self.conn
    
    async def retrieve(
        self,
        query: str,
        top_k: int = 5,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[RAGResult]:
        """
        Retrieve relevant document chunks.
        
        Args:
            query: Search query
            top_k: Number of results
            filters: Optional filters (user_id, file_type, etc.)
            
        Returns:
            List of RAGResult objects
        """
        all_results = []
        
        # 1. FTS keyword search
        fts_results = self._fts_search(query, limit=top_k * 2)
        all_results.extend(fts_results)
        
        # 2. Vector semantic search (if available)
        if self.vector_store:
            vector_results = self._vector_search(query, limit=top_k)
            all_results.extend(vector_results)
        
        # 3. Deduplicate and rank
        final_results = self._deduplicate_and_rank(all_results, top_k)
        
        logger.info(f"Retrieved {len(final_results)} results for: {query}")
        
        return final_results
    
    def _clean_fts_query(self, query: str) -> str:
        """Clean query for FTS search"""
        if not query or not query.strip():
            return ""  # Return empty string to skip FTS search
            
        import re
        # Remove special characters that could cause FTS syntax errors
        query = re.sub(r'[!?.,;:\'"`(){}[\]<>|/\\&^%$#@]', ' ', query)
        # Normalize whitespace
        query = ' '.join(query.split())
        
        # Add fuzzy matching for non-empty queries
        terms = query.split()
        cleaned_terms = []
        for term in terms:
            if len(term) > 2:  # Only add fuzzy matching for longer terms
                cleaned_terms.append(f'{term}*')
            else:
                cleaned_terms.append(term)
        
        if not cleaned_terms:
            return ""  # Return empty if no valid terms
            
        return ' OR '.join(cleaned_terms)

    def _fts_search(self, query: str, limit: int = 10) -> List[RAGResult]:
        """Search using SQL FTS5"""
        try:
            # Clean and prepare query
            cleaned_query = self._clean_fts_query(query)
            if not cleaned_query:
                logger.debug("Empty query - skipping FTS search")
                return []  # Skip FTS search for empty queries
                
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Search document chunks via FTS
            cursor.execute("""
                SELECT 
                    c.id as chunk_id,
                    c.content,
                    c.chunk_index,
                    c.document_id,
                    d.file_name,
                    d.file_path,
                    d.title,
                    bm25(documents_fts) as score
                FROM document_chunks c
                JOIN documents d ON c.document_id = d.id
                JOIN documents_fts ON d.id = documents_fts.rowid
                WHERE documents_fts MATCH ? AND d.deleted_at IS NULL
                ORDER BY score DESC
                LIMIT ?
            """, (cleaned_query, limit))
            
            results = []
            for row in cursor.fetchall():
                results.append(RAGResult(
                    content=row['content'],
                    document_id=row['document_id'],
                    document_name=row['file_name'],
                    chunk_index=row['chunk_index'],
                    relevance_score=abs(row['score']) if row['score'] else 0.0,
                    source_path=row['file_path'],
                    metadata={'source': 'fts', 'title': row['title']}
                ))
            
            logger.debug(f"FTS found {len(results)} results")
            return results
            
        except Exception as e:
            logger.error(f"FTS search error: {e}")
            return []
    
    def _vector_search(self, query: str, limit: int = 5) -> List[RAGResult]:
        """Search using vector similarity"""
        if not self.vector_store:
            return []
        
        try:
            # Search vector store
            vector_results = self.vector_store.search(
                query=query,
                user_id="default_user",  # Can filter by user
                limit=limit,
                min_similarity=0.3
            )
            
            # Convert to RAGResult
            results = []
            for vr in vector_results:
                # Get chunk details from SQL
                chunk_info = self._get_chunk_info(vr.fact_id)
                
                if chunk_info:
                    results.append(RAGResult(
                        content=chunk_info['content'],
                        document_id=chunk_info['document_id'],
                        document_name=chunk_info['file_name'],
                        chunk_index=chunk_info['chunk_index'],
                        relevance_score=vr.relevance_score,
                        source_path=chunk_info['file_path'],
                        metadata={'source': 'vector', 'title': chunk_info['title']}
                    ))
            
            logger.debug(f"Vector search found {len(results)} results")
            return results
            
        except Exception as e:
            logger.error(f"Vector search error: {e}")
            return []
    
    def _get_chunk_info(self, chunk_id: int) -> Optional[Dict]:
        """Get chunk information from SQL"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT 
                    c.content,
                    c.chunk_index,
                    c.document_id,
                    d.file_name,
                    d.file_path,
                    d.title
                FROM document_chunks c
                JOIN documents d ON c.document_id = d.id
                WHERE c.id = ?
            """, (chunk_id,))
            
            row = cursor.fetchone()
            if row:
                return dict(row)
            return None
            
        except Exception as e:
            logger.error(f"Failed to get chunk info: {e}")
            return None
    
    def _deduplicate_and_rank(
        self,
        results: List[RAGResult],
        top_k: int
    ) -> List[RAGResult]:
        """Deduplicate and rank results"""
        
        # Deduplicate by content
        seen_content = set()
        unique_results = []
        
        for result in results:
            content_key = result.content[:100].lower().strip()
            
            if content_key not in seen_content:
                seen_content.add(content_key)
                unique_results.append(result)
        
        # Sort by relevance score
        ranked_results = sorted(
            unique_results,
            key=lambda r: r.relevance_score,
            reverse=True
        )
        
        return ranked_results[:top_k]
    
    def format_context(
        self,
        results: List[RAGResult],
        max_length: int = 1000
    ) -> str:
        """
        Format results for AI prompt.
        
        Args:
            results: Retrieved results
            max_length: Max character length
            
        Returns:
            Formatted context string
        """
        if not results:
            return ""
        
        context_lines = ["Relevant information from documents:"]
        total_length = len(context_lines[0])
        
        for i, result in enumerate(results, 1):
            # Format: "[Document: filename] content..."
            line = f"\n[{i}. {result.document_name}] {result.content[:200]}..."
            
            if total_length + len(line) > max_length:
                break
            
            context_lines.append(line)
            total_length += len(line)
        
        return "".join(context_lines)
    
    def close(self):
        """Close connections"""
        if self.conn:
            self.conn.close()
            self.conn = None


# Global instance

_retriever = None

def get_retriever() -> HybridRetriever:
    """Get or create global retriever"""
    global _retriever
    if _retriever is None:
        _retriever = HybridRetriever()
    return _retriever