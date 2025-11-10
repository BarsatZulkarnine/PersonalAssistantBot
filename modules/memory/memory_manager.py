"""
Memory Manager - Main Orchestrator

Coordinates classification, storage, and retrieval of memories.
This is the primary interface for the voice assistant.
"""

import uuid
from typing import Optional, List, Dict, Any
from datetime import datetime

from modules.memory.base import (
    Conversation, Fact, MemoryCategory, FactCategory,
    MemoryClassification, RetrievalResult
)
from modules.memory.sql_store import SQLStore
from modules.memory.classifier import AIMemoryClassifier
from modules.memory.vector_store import ChromaVectorStore, CHROMADB_AVAILABLE
from utils.logger import get_logger

logger = get_logger('memory.manager')

class MemoryManager:
    """
    Main memory orchestrator.
    
    Handles the complete flow:
    1. Classify conversation worth
    2. Store in SQL (always for CONVERSATIONAL+)
    3. Store in vector DB (only for FACTUAL)
    4. Retrieve relevant context when needed
    """
    
    def __init__(
        self,
        db_path: str = "data/memory.db",
        vector_path: str = "data/chromadb"
    ):
        # Initialize components
        self.sql_store = SQLStore(db_path)
        self.sql_store.initialize()
        
        self.classifier = AIMemoryClassifier()
        
        # Vector store (optional)
        self.vector_store: Optional[ChromaVectorStore] = None
        if CHROMADB_AVAILABLE:
            self.vector_store = ChromaVectorStore(vector_path)
            self.vector_store.initialize()
            logger.info("Vector store enabled")
        else:
            logger.warning("⚠️  Vector store disabled (ChromaDB not installed)")
        
        # Current session
        self.session_id = str(uuid.uuid4())
        self.turn_counter = 0
        
        logger.info("Memory manager initialized")
    
    async def process_conversation(
        self,
        user_input: str,
        assistant_response: str,
        intent_type: Optional[str] = None,
        duration_ms: float = 0.0,
        prompt_tokens: int = 0,
        completion_tokens: int = 0
    ) -> MemoryClassification:
        """
        Process a conversation turn.
        
        This is the main entry point - call this after each user interaction.
        
        Args:
            user_input: What the user said
            assistant_response: What the assistant replied
            intent_type: Optional intent (AI, Web, Action)
            duration_ms: How long it took to process
            prompt_tokens: Tokens used in prompt
            completion_tokens: Tokens used in completion
            
        Returns:
            MemoryClassification showing what was stored
        """
        try:
            self.turn_counter += 1
            
            # Step 1: Classify
            logger.debug(f"Classifying turn {self.turn_counter}...")
            classification = await self.classifier.classify(
                user_input,
                assistant_response,
                intent_type
            )
            
            # Step 2: Handle based on category
            if classification.category == MemoryCategory.EPHEMERAL:
                logger.debug("Ephemeral conversation - not storing")
                return classification
            
            # Step 3: Store conversation in SQL
            conversation = Conversation(
                session_id=self.session_id,
                turn_no=self.turn_counter,
                user_input=user_input,
                assistant_response=assistant_response,
                intent_type=intent_type,
                duration_ms=duration_ms,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                timestamp=datetime.now()
            )
            
            conv_id = self.sql_store.store_conversation(conversation)
            logger.info(f"Stored conversation {conv_id} as {classification.category.value}")
            
            # Step 4: If FACTUAL, extract and store facts
            if classification.category == MemoryCategory.FACTUAL:
                await self._store_facts(
                    classification,
                    conv_id,
                    user_input,
                    assistant_response
                )
            
            return classification
            
        except Exception as e:
            logger.error(f"Error processing conversation: {e}", exc_info=True)
            raise
    
    async def _store_facts(
        self,
        classification: MemoryClassification,
        conversation_id: int,
        user_input: str,
        assistant_response: str
    ):
        """Store extracted facts from a FACTUAL conversation"""
        # CRITICAL FIX: Always use the full user input as the fact
        # This preserves context and makes retrieval work
        # The classifier's extracted_facts are just hints, not the actual content to store
        
        # Build a complete, searchable fact from user input
        fact_text = user_input
        
        # If there are extracted facts, create a more structured fact
        if classification.extracted_facts:
            # Combine user input with extracted facts for better context
            extracted = ", ".join(classification.extracted_facts)
            # Keep the original user input as it has the most context
            fact_text = user_input
        
        # Create single fact from user input
        fact = Fact(
            content=fact_text,  # Full user sentence, not just keywords
            category=classification.fact_category or FactCategory.CONTEXT,
            importance_score=classification.importance_score,
            conversation_id=conversation_id,
            message_id=f"msg_{conversation_id}_{self.turn_counter}"
        )
            
            # Store in SQL
        fact_id = self.sql_store.store_fact(fact)
        logger.info(f"Stored fact {fact_id}: {fact_text[:50]}...")
            
            # Store in vector DB if available
        if self.vector_store:
            try:
                embedding_id = self.vector_store.add_embedding(
                    fact_id=fact_id,
                    content=fact_text,
                    metadata={
                        "user_id": "default_user",
                        "category": fact.category.value if fact.category else "unknown",
                        "importance": fact.importance_score,
                        "created_at": datetime.now().isoformat()
                    }
                )
                
                # Update SQL with embedding reference
                self.sql_store.update_fact_embedding(fact_id, embedding_id)
                logger.debug(f"Added embedding {embedding_id}")
                
            except Exception as e:
                logger.error(f"Failed to add embedding: {e}")
    
    async def retrieve_context(
        self,
        query: str,
        user_id: str = "default_user",
        max_results: int = 5,
        include_recent: bool = True
    ) -> List[RetrievalResult]:
        """
        Retrieve relevant context for a query.
        
        Uses hybrid retrieval:
        1. FTS keyword search (SQL)
        2. Semantic search (Vector)
        3. Recent conversations (SQL)
        
        Args:
            query: Search query
            user_id: User to search for
            max_results: Maximum results to return
            include_recent: Include recent conversations
            
        Returns:
            List of relevant facts/conversations
        """
        try:
            all_results = []
            
            # 1. FTS keyword search
            logger.debug("Searching SQL FTS...")
            fts_results = self.sql_store.search_facts(query, user_id, limit=max_results)
            all_results.extend(fts_results)
            
            # 2. Vector semantic search (if available)
            if self.vector_store:
                logger.debug("Searching vector store...")
                vector_results = self.vector_store.search(
                    query,
                    user_id=user_id,
                    limit=max_results,
                    min_similarity=0.3  # Threshold
                )
                all_results.extend(vector_results)
            
            # 3. Recent conversations (if requested)
            if include_recent:
                logger.debug("Getting recent conversations...")
                recent_convs = self.sql_store.get_conversations(
                    user_id=user_id,
                    session_id=self.session_id,
                    limit=3
                )
                
                for conv in recent_convs:
                    all_results.append(RetrievalResult(
                        content=f"User: {conv.user_input}\nAssistant: {conv.assistant_response}",
                        relevance_score=0.5,  # Medium relevance for recency
                        conversation_id=conv.id,
                        source='recent'
                    ))
            
            # Deduplicate and rank
            results = self._deduplicate_and_rank(all_results, max_results)
            
            logger.info(f"Retrieved {len(results)} relevant results for: {query}")
            return results
            
        except Exception as e:
            logger.error(f"Context retrieval error: {e}", exc_info=True)
            return []
    
    def _deduplicate_and_rank(
        self,
        results: List[RetrievalResult],
        max_results: int
    ) -> List[RetrievalResult]:
        """
        Deduplicate and rank results by relevance.
        
        Ranking factors:
        - Relevance score (from FTS or vector)
        - Importance score
        - Recency
        """
        # Deduplicate by content
        seen_content = set()
        unique_results = []
        
        for result in results:
            # Create a simple hash of content
            content_key = result.content[:100].lower().strip()
            
            if content_key not in seen_content:
                seen_content.add(content_key)
                unique_results.append(result)
        
        # Sort by composite score
        def calculate_score(r: RetrievalResult) -> float:
            relevance = r.relevance_score
            importance = r.importance if r.importance else 0.5
            
            # Boost recent items slightly
            recency_boost = 0.1 if r.source == 'recent' else 0.0
            
            return (relevance * 0.6) + (importance * 0.3) + recency_boost
        
        ranked_results = sorted(
            unique_results,
            key=calculate_score,
            reverse=True
        )
        
        return ranked_results[:max_results]
    
    def get_conversation_history(
        self,
        session_id: Optional[str] = None,
        limit: int = 10
    ) -> List[Conversation]:
        """Get conversation history"""
        sid = session_id or self.session_id
        return self.sql_store.get_conversations(session_id=sid, limit=limit)
    
    def get_user_facts(
        self,
        user_id: str = "default_user",
        category: Optional[FactCategory] = None,
        limit: int = 20
    ) -> List[Fact]:
        """Get user's stored facts"""
        return self.sql_store.get_facts(user_id=user_id, category=category, limit=limit)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get memory system statistics"""
        sql_stats = self.sql_store.get_stats()
        
        stats = {
            "sql": sql_stats,
            "session_id": self.session_id,
            "turn_count": self.turn_counter
        }
        
        if self.vector_store:
            stats["vector"] = self.vector_store.get_stats()
        
        return stats
    
    def start_new_session(self):
        """Start a new conversation session"""
        self.session_id = str(uuid.uuid4())
        self.turn_counter = 0
        logger.info(f"Started new session: {self.session_id}")
    
    def format_context_for_prompt(
        self,
        results: List[RetrievalResult],
        max_length: int = 500
    ) -> str:
        """
        Format retrieved context for AI prompt injection.
        
        Args:
            results: Retrieved results
            max_length: Maximum character length
            
        Returns:
            Formatted context string
        """
        if not results:
            return ""
        
        context_lines = ["Relevant information from memory:"]
        total_length = len(context_lines[0])
        
        for result in results:
            line = f"- {result.content}"
            
            # Check length
            if total_length + len(line) > max_length:
                break
            
            context_lines.append(line)
            total_length += len(line)
        
        return "\n".join(context_lines)


# Global instance

_memory_manager = None

def get_memory_manager() -> MemoryManager:
    """Get or create global memory manager"""
    global _memory_manager
    if _memory_manager is None:
        _memory_manager = MemoryManager()
    return _memory_manager