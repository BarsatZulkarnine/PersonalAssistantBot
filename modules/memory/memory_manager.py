"""
Memory Manager - Session-Aware Implementation

Handles multi-device, multi-user conversation isolation.
Each device/conversation maintains its own session.
"""

import uuid
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta

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
    Session-aware memory orchestrator.
    
    Key features:
    - Multi-device support (Desktop, Raspberry Pi, etc.)
    - Session isolation (conversations don't mix)
    - Shared facts (cross-session factual knowledge)
    - Multi-user support
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
            logger.warning("Vector store disabled (ChromaDB not installed)")
        
        logger.info("Memory manager initialized (session-aware)")
    
    @staticmethod
    def generate_session_id(
        user_id: str,
        device_name: Optional[str] = None
    ) -> str:
        """
        Generate unique session ID.
        
        Format: {user_id}_{device}_{timestamp}_{uuid}
        Example: user1_desktop_20241110_143022_a1b2c3d4
        
        Args:
            user_id: User identifier
            device_name: Optional device name (desktop, pi, mobile)
            
        Returns:
            Unique session ID
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        short_uuid = str(uuid.uuid4())[:8]
        
        if device_name:
            return f"{user_id}_{device_name}_{timestamp}_{short_uuid}"
        else:
            return f"{user_id}_{timestamp}_{short_uuid}"
    
    async def process_conversation(
        self,
        user_input: str,
        assistant_response: str,
        session_id: str,                    # ✅ REQUIRED
        user_id: str = "default_user",      # ✅ REQUIRED
        intent_type: Optional[str] = None,
        duration_ms: float = 0.0,
        prompt_tokens: int = 0,
        completion_tokens: int = 0
    ) -> MemoryClassification:
        """
        Process a conversation turn with session tracking.
        
        ✅ CHANGED: session_id and user_id are now required
        ✅ NEW: Stores session context for isolation
        
        Args:
            user_input: What the user said
            assistant_response: What the assistant replied
            session_id: Session identifier (device/conversation)
            user_id: User identifier
            intent_type: Optional intent (AI, Web, Action)
            duration_ms: Processing time
            prompt_tokens: Token usage
            completion_tokens: Token usage
            
        Returns:
            MemoryClassification showing what was stored
            
        Example:
            # Desktop session
            await memory.process_conversation(
                user_input="What's the weather?",
                assistant_response="15°C and sunny",
                session_id="user1_desktop_20241110_143022_a1b2c3d4",
                user_id="user1"
            )
            
            # Raspberry Pi session (same time, different session)
            await memory.process_conversation(
                user_input="Turn on lights",
                assistant_response="Lights on",
                session_id="user1_pi_20241110_143023_x9y8z7w6",
                user_id="user1"
            )
        """
        try:
            # Step 1: Classify
            logger.debug(f"[{session_id[:20]}...] Classifying conversation...")
            classification = await self.classifier.classify(
                user_input,
                assistant_response,
                intent_type
            )
            
            # Step 2: Handle based on category
            if classification.category == MemoryCategory.EPHEMERAL:
                logger.debug(f"[{session_id[:20]}...] Ephemeral - not storing")
                return classification
            
            # Step 3: Get turn number for this session
            turn_no = self.sql_store.get_session_turn_count(session_id) + 1
            
            # Step 4: Store conversation in SQL with session info
            conversation = Conversation(
                session_id=session_id,      # ✅ Session tracking
                user_id=user_id,            # ✅ User tracking
                turn_no=turn_no,
                user_input=user_input,
                assistant_response=assistant_response,
                intent_type=intent_type,
                duration_ms=duration_ms,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                timestamp=datetime.now()
            )
            
            conv_id = self.sql_store.store_conversation(conversation)
            logger.info(
                f"[{session_id[:20]}...] Stored conversation {conv_id} "
                f"as {classification.category.value} (turn {turn_no})"
            )
            
            # Step 5: If FACTUAL, extract and store facts (cross-session)
            if classification.category == MemoryCategory.FACTUAL:
                await self._store_facts(
                    classification,
                    conv_id,
                    user_id,
                    user_input,
                    assistant_response
                )
            
            return classification
            
        except Exception as e:
            logger.error(
                f"[{session_id[:20]}...] Error processing conversation: {e}",
                exc_info=True
            )
            raise
    
    async def _store_facts(
        self,
        classification: MemoryClassification,
        conversation_id: int,
        user_id: str,
        user_input: str,
        assistant_response: str
    ):
        """
        Store extracted facts (cross-session).
        
        ✅ FIXED: Store extracted facts, not full conversation
        """
        
        # ✅ FIX: Use extracted facts if available
        if classification.extracted_facts:
            facts_to_store = classification.extracted_facts
        else:
            # Fallback: use user input if no extraction
            facts_to_store = [user_input]
        
        # Store each extracted fact separately
        for fact_text in facts_to_store:
            fact = Fact(
                content=fact_text,  # ✅ FIXED: Use extracted fact
                user_id=user_id,
                category=classification.fact_category or FactCategory.CONTEXT,
                importance_score=classification.importance_score,
                conversation_id=conversation_id,
                message_id=f"msg_{conversation_id}"
            )
            
            # Store in SQL
            fact_id = self.sql_store.store_fact(fact)
            logger.info(f"Stored fact {fact_id}: {fact_text[:50]}... (shared)")
            
            # Store in vector DB if available
            if self.vector_store:
                try:
                    embedding_id = self.vector_store.add_embedding(
                        fact_id=fact_id,
                        content=fact_text,  # ✅ FIXED: Embed the fact
                        metadata={
                            "user_id": user_id,
                            "category": fact.category.value if fact.category else "unknown",
                            "importance": fact.importance_score,
                            "created_at": datetime.now().isoformat(),
                            "is_fact": True
                        }
                    )
                    
                    self.sql_store.update_fact_embedding(fact_id, embedding_id)
                    logger.debug(f"Added embedding {embedding_id} for fact")
                    
                except Exception as e:
                    logger.error(f"Failed to add embedding: {e}")
    
    async def retrieve_context(
        self,
        query: str,
        session_id: str,
        user_id: str = "default_user",
        max_results: int = 5,
        include_recent: bool = True,
        include_facts: bool = True
    ) -> List[RetrievalResult]:
        """
        Retrieve relevant context with SESSION ISOLATION.
        
        ✅ FIXED: Proper session filtering
        ✅ FIXED: Better logging for debugging
        
        Returns:
            - Recent conversations FROM THIS SESSION
            - Conversation search FROM THIS SESSION
            - Facts SHARED ACROSS SESSIONS
        """
        try:
            all_results = []
            
            logger.debug(
                f"[{session_id[:20]}...] Retrieving context for: '{query}'\n"
                f"  - user_id: {user_id}\n"
                f"  - include_recent: {include_recent}\n"
                f"  - include_facts: {include_facts}"
            )
            
            # ============================================
            # 1. RECENT CONVERSATIONS (SESSION-FILTERED)
            # ============================================
            if include_recent:
                logger.debug(f"[{session_id[:20]}...] → Getting recent conversations (THIS session only)")
                
                recent_results = self.sql_store.get_recent_conversations_from_session(
                    session_id=session_id,
                    user_id=user_id,
                    limit=3
                )
                
                all_results.extend(recent_results)
                
                logger.info(
                    f"[{session_id[:20]}...] ✓ Found {len(recent_results)} recent from THIS session"
                )
                
                # Debug log each recent conversation
                for i, r in enumerate(recent_results, 1):
                    logger.debug(f"  Recent {i}: {r.content[:100]}...")
            
            # ============================================
            # 2. CONVERSATION SEARCH (SESSION-FILTERED)
            # ============================================
            logger.debug(f"[{session_id[:20]}...] → Searching conversations (THIS session only)")
            
            search_results = self.sql_store.search_conversations(
                query=query,
                user_id=user_id,
                session_id=session_id,  # ✅ CRITICAL: Session filter
                limit=max_results // 2
            )
            
            all_results.extend(search_results)
            
            logger.info(
                f"[{session_id[:20]}...] ✓ Found {len(search_results)} conversation matches from THIS session"
            )
            
            # Debug log each search result
            for i, r in enumerate(search_results, 1):
                logger.debug(f"  Search {i}: {r.content[:100]}...")
            
            # ============================================
            # 3. SHARED FACTS (CROSS-SESSION)
            # ============================================
            if include_facts:
                logger.debug(f"[{session_id[:20]}...] → Searching shared facts (cross-session)")
                
                # FTS search for facts
                fact_fts_results = self.sql_store.search_facts(
                    query=query,
                    user_id=user_id,
                    limit=max_results // 2
                )
                all_results.extend(fact_fts_results)
                
                logger.info(
                    f"[{session_id[:20]}...] ✓ Found {len(fact_fts_results)} fact matches (FTS)"
                )
                
                # Vector search for facts (if available)
                if self.vector_store:
                    fact_vector_results = self.vector_store.search(
                        query=query,
                        user_id=user_id,
                        limit=max_results // 2,
                        min_similarity=0.3,
                        filter_facts_only=True
                    )
                    all_results.extend(fact_vector_results)
                    
                    logger.info(
                        f"[{session_id[:20]}...] ✓ Found {len(fact_vector_results)} fact matches (vector)"
                    )
            
            # ============================================
            # 4. DEDUPLICATE AND RANK
            # ============================================
            results = self._deduplicate_and_rank(all_results, max_results)
            
            # ✅ COUNT BY SOURCE
            session_count = sum(1 for r in results if r.session_id == session_id)
            fact_count = sum(1 for r in results if r.session_id is None)
            
            logger.info(
                f"[{session_id[:20]}...] ═══ FINAL RESULTS ═══\n"
                f"  Total: {len(results)}\n"
                f"  From THIS session: {session_count}\n"
                f"  Shared facts: {fact_count}"
            )
            
            # Debug log final results
            for i, r in enumerate(results, 1):
                source_label = "SESSION" if r.session_id == session_id else "FACT"
                logger.debug(
                    f"  Result {i} [{source_label}]: {r.content[:80]}... "
                    f"(score={r.relevance_score:.2f})"
                )
            
            return results
            
        except Exception as e:
            logger.error(
                f"[{session_id[:20]}...] ❌ Context retrieval error: {e}",
                exc_info=True
            )
            return []
        
    def _deduplicate_and_rank(
        self,
        results: List[RetrievalResult],
        max_results: int
    ) -> List[RetrievalResult]:
        """
        Deduplicate and rank results by relevance.
        
        ✅ FIXED: Better deduplication logic
        """
        seen_content = set()
        unique_results = []
        
        for result in results:
            # Use first 100 chars as dedup key
            content_key = result.content[:100].lower().strip()
            
            if content_key not in seen_content:
                seen_content.add(content_key)
                unique_results.append(result)
        
        # Calculate combined score
        def calculate_score(r: RetrievalResult) -> float:
            relevance = r.relevance_score
            importance = r.importance if r.importance else 0.5
            
            # Boost recent session conversations
            recency_boost = 0.2 if r.source == 'recent' else 0.0
            
            # Boost facts slightly (they're important)
            fact_boost = 0.1 if r.session_id is None else 0.0
            
            return (relevance * 0.5) + (importance * 0.3) + recency_boost + fact_boost
        
        # Sort by score
        ranked_results = sorted(
            unique_results,
            key=calculate_score,
            reverse=True
        )
        
        return ranked_results[:max_results]
    def get_conversation_history(
        self,
        session_id: str,
        user_id: str = "default_user",
        limit: int = 10
    ) -> List[Conversation]:
        """
        Get conversation history for a specific session.
        
        ✅ CHANGED: Requires session_id
        """
        return self.sql_store.get_conversations(
            user_id=user_id,
            session_id=session_id,
            limit=limit
        )
    
    def get_user_facts(
        self,
        user_id: str = "default_user",
        category: Optional[FactCategory] = None,
        limit: int = 20
    ) -> List[Fact]:
        """Get user's stored facts (cross-session)"""
        return self.sql_store.get_facts(
            user_id=user_id,
            category=category,
            limit=limit
        )
    
    def get_session_stats(
        self,
        session_id: str,
        user_id: str = "default_user"
    ) -> Dict[str, Any]:
        """Get statistics for a specific session"""
        convs = self.sql_store.get_conversations(
            user_id=user_id,
            session_id=session_id,
            limit=1000  # Get all
        )
        
        return {
            "session_id": session_id,
            "user_id": user_id,
            "total_turns": len(convs),
            "first_turn": convs[-1].timestamp if convs else None,
            "last_turn": convs[0].timestamp if convs else None,
            "total_tokens": sum(
                c.prompt_tokens + c.completion_tokens
                for c in convs
            )
        }
    
    def get_stats(self) -> Dict[str, Any]:
        """Get overall memory system statistics"""
        sql_stats = self.sql_store.get_stats()
        
        stats = {
            "sql": sql_stats,
            "session_aware": True  # ✅ Flag
        }
        
        if self.vector_store:
            stats["vector"] = self.vector_store.get_stats()
        
        return stats
    
    async def cleanup_old_sessions(
        self,
        days_old: int = 7,
        keep_facts: bool = True
    ):
        """
        Clean up old ephemeral conversations.
        
        ✅ NEW: Removes old session data to keep DB lean
        
        Args:
            days_old: Delete conversations older than this
            keep_facts: Keep factual memories (recommended)
        """
        cutoff = datetime.now() - timedelta(days=days_old)
        
        logger.info(f"Cleaning up conversations older than {cutoff}")
        
        # Delete old ephemeral/conversational memories
        deleted = self.sql_store.delete_old_conversations(
            cutoff_date=cutoff,
            keep_factual=keep_facts
        )
        
        logger.info(f"Deleted {deleted} old conversation turns")
        return deleted
    
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
            # Add source indicator
            source_tag = ""
            if result.session_id:
                source_tag = "(this conversation) "
            elif result.source == 'fact':
                source_tag = "(remembered fact) "
            
            line = f"- {source_tag}{result.content}"
            
            if total_length + len(line) > max_length:
                break
            
            context_lines.append(line)
            total_length += len(line)
        
        return "\n".join(context_lines)


# Global instance (still useful for backward compatibility)
_memory_manager = None

def get_memory_manager() -> MemoryManager:
    """Get or create global memory manager"""
    global _memory_manager
    if _memory_manager is None:
        _memory_manager = MemoryManager()
    return _memory_manager