"""
Conversation Service - UPDATED FOR CLIENT AWARENESS

Key changes:
- Accepts client_type parameter
- Passes client_type to actions
- Returns action_data in response
"""

import time
import uuid
from typing import Optional, Dict, Any
from datetime import datetime

from modules.intent.base import IntentType
from modules.actions.registry import ActionRegistry
from modules.memory.memory_manager import MemoryManager
from modules.rag.retriever import HybridRetriever
from utils.logger import get_logger, log_conversation

logger = get_logger('conversation_service')


class ConversationService:
    """Session-aware conversation service with client support"""
    
    def __init__(
        self,
        intent_detector,
        action_registry: ActionRegistry,
        memory_manager: Optional[MemoryManager] = None,
        rag_retriever: Optional[HybridRetriever] = None
    ):
        self.intent = intent_detector
        self.actions = action_registry
        self.memory = memory_manager
        self.rag = rag_retriever
        
        logger.info("ConversationService initialized (client-aware)")
    
    def _generate_session_id(self, user_id: str) -> str:
        """Generate unique session ID"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        short_uuid = str(uuid.uuid4())[:8]
        return f"{user_id}_{timestamp}_{short_uuid}"
    
    async def process_input(
        self,
        user_input: str,
        session_id: Optional[str] = None,
        user_id: str = "default_user",
        client_type: str = "server"  # ✅ NEW PARAMETER
    ) -> Dict[str, Any]:
        """
        Process user input with client awareness.
        
        Args:
            user_input: User's text input
            session_id: Session identifier
            user_id: User identifier
            client_type: Client type (server, raspberry_pi, web_ui)
        
        Returns:
            Response with action_data included
        """
        start_time = time.time()
        
        # Generate session ID if not provided
        if not session_id:
            session_id = self._generate_session_id(user_id)
            logger.info(f"Generated new session: {session_id}")
        
        try:
            logger.info(f"[{session_id}] Processing: {user_input[:50]}... (client={client_type})")
            
            # Step 1: Retrieve Memory Context
            memory_context = ""
            memory_results = []
            if self.memory:
                try:
                    logger.debug(f"[{session_id}] Retrieving memory context...")
                    
                    memory_results = await self.memory.retrieve_context(
                        query=user_input,
                        session_id=session_id,
                        user_id=user_id,
                        max_results=3,
                        include_recent=True
                    )
                    
                    if memory_results:
                        memory_context = self.memory.format_context_for_prompt(
                            memory_results,
                            max_length=500
                        )
                        logger.info(
                            f"[{session_id}] Retrieved {len(memory_results)} "
                            f"memory items from THIS session"
                        )
                except Exception as e:
                    logger.error(f"[{session_id}] Memory retrieval error: {e}")
            
            # Step 2: Search RAG Documents
            rag_context = ""
            rag_results = []
            if self.rag:
                try:
                    logger.debug(f"[{session_id}] Searching RAG documents...")
                    rag_results = await self.rag.retrieve(
                        query=user_input,
                        top_k=3
                    )
                    
                    if rag_results:
                        rag_context = self.rag.format_context(
                            rag_results,
                            max_length=800
                        )
                        logger.info(
                            f"[{session_id}] Retrieved {len(rag_results)} "
                            f"document chunks"
                        )
                except Exception as e:
                    logger.error(f"[{session_id}] RAG retrieval error: {e}")
            
            # Step 3: Detect Intent
            logger.debug(f"[{session_id}] Detecting intent...")
            intent_result = await self.intent.detect(user_input)
            intent_type = intent_result.intent_type
            
            logger.info(
                f"[{session_id}] Intent: {intent_type.value} "
                f"(confidence: {intent_result.confidence:.2f})"
            )
            
            # Step 4: Route Based on Intent
            response = ""
            action_executed = None
            action_data = None  # ✅ NEW: Store action data
            
            if intent_type == IntentType.ACTION:
                response, action_executed, action_data = await self._handle_action(
                    user_input, 
                    session_id,
                    client_type  # ✅ PASS CLIENT TYPE
                )
            
            elif intent_type == IntentType.WEB:
                response = await self._handle_web_search(
                    user_input, 
                    memory_context,
                    session_id
                )
            
            else:  # IntentType.AI
                response = await self._handle_conversation(
                    user_input,
                    memory_context,
                    rag_context,
                    session_id
                )
            
            duration_ms = (time.time() - start_time) * 1000
            
            # Step 5: Store in Memory
            memory_stored = False
            memory_category = None
            if self.memory:
                try:
                    logger.debug(f"[{session_id}] Storing conversation in memory...")
                    
                    classification = await self.memory.process_conversation(
                        user_input=user_input,
                        assistant_response=response,
                        session_id=session_id,
                        user_id=user_id,
                        intent_type=intent_type.value,
                        duration_ms=duration_ms,
                        prompt_tokens=0,
                        completion_tokens=0
                    )
                    
                    memory_stored = classification.should_store()
                    memory_category = classification.category.value
                    logger.info(
                        f"[{session_id}] Memory: {classification.category.value} "
                        f"(intent: {intent_type.value}, "
                        f"importance: {classification.importance_score:.2f})"
                    )
                except Exception as e:
                    logger.error(f"[{session_id}] Memory storage error: {e}")
            
            # Log conversation
            log_conversation(user_input, response)
            
            # ✅ RETURN ENHANCED RESULT
            result = {
                'response': response,
                'intent': intent_type.value,
                'confidence': intent_result.confidence,
                'action_executed': action_executed,
                'action_data': action_data,  # ✅ NEW: Action-specific data
                'memory_stored': memory_stored,
                'memory_category': memory_category,
                'rag_used': bool(rag_results),
                'duration_ms': duration_ms,
                'metadata': {
                    'session_id': session_id,
                    'user_id': user_id,
                    'client_type': client_type,  # ✅ NEW
                    'memory_results': len(memory_results),
                    'rag_results': len(rag_results)
                }
            }
            
            logger.info(f"[{session_id}] Processing complete ({duration_ms:.0f}ms)")
            return result
            
        except Exception as e:
            logger.error(f"[{session_id}] Error processing input: {e}", exc_info=True)
            
            error_response = "Sorry, I encountered an error processing your request."
            log_conversation(user_input, error_response)
            
            return {
                'response': error_response,
                'intent': 'error',
                'confidence': 0.0,
                'action_executed': None,
                'action_data': None,
                'memory_stored': False,
                'memory_category': None,
                'rag_used': False,
                'duration_ms': (time.time() - start_time) * 1000,
                'metadata': {
                    'session_id': session_id,
                    'user_id': user_id,
                    'client_type': client_type,
                    'error': str(e)
                }
            }
    
    async def _handle_action(
        self, 
        user_input: str,
        session_id: str,
        client_type: str  # ✅ NEW PARAMETER
    ) -> tuple[str, Optional[str], Optional[Dict]]:
        """
        Handle action execution with client awareness.
        
        Returns:
            (response_text, action_name, action_data)
        """
        logger.debug(f"[{session_id}] Finding action...")
        
        action = self.actions.find_action_for_prompt(user_input)
        
        if not action:
            logger.warning(f"[{session_id}] No matching action found")
            return ("I'm not sure how to do that.", None, None)
        
        logger.info(f"[{session_id}] Executing action: {action.name}")
        
        # ✅ PASS CLIENT TYPE TO ACTION
        params = {'client_type': client_type}
        result = await action.execute(user_input, params=params)
        
        if result.success:
            logger.info(f"[{session_id}] Action completed: {action.name}")
        else:
            logger.warning(f"[{session_id}] Action failed: {result.message}")
        
        # ✅ RETURN ACTION DATA
        return (result.message, action.name, result.data)
    
    async def _handle_web_search(
        self, 
        user_input: str,
        memory_context: str,
        session_id: str
    ) -> str:
        """Handle web search with memory context"""
        logger.debug(f"[{session_id}] Handling web search...")
        
        web_action = None
        for action in self.actions.get_all_actions().values():
            if action.name == "WebSearchAction":
                web_action = action
                break
        
        if web_action:
            params = {}
            if memory_context:
                params['memory_context'] = memory_context
                logger.info(
                    f"[{session_id}] Injecting memory context "
                    f"({len(memory_context)} chars)"
                )
            
            result = await web_action.execute(user_input, params=params)
            return result.message
        
        logger.warning(f"[{session_id}] Web search action not found")
        return "Web search not available."
    
    async def _handle_conversation(
        self,
        user_input: str,
        memory_context: str,
        rag_context: str,
        session_id: str
    ) -> str:
        """Handle general conversation"""
        logger.debug(f"[{session_id[:20]}...] Handling conversation...")
        
        conv_action = None
        for action in self.actions.get_all_actions().values():
            if action.name == "AIChatAction":
                conv_action = action
                break
        
        if not conv_action:
            logger.warning(f"[{session_id[:20]}...] AI chat action not found")
            return "I'm not sure how to respond to that."
        
        params = {}
        full_context = ""
        
        # ✅ FIX: Build context properly
        if memory_context:
            full_context += "=== CONVERSATION HISTORY ===\n"
            full_context += memory_context
            logger.info(f"[{session_id[:20]}...] Added memory context ({len(memory_context)} chars)")
        
        if rag_context:
            if full_context:
                full_context += "\n\n"
            full_context += "=== RELEVANT DOCUMENTS ===\n"
            full_context += rag_context
            logger.info(f"[{session_id[:20]}...] Added RAG context ({len(rag_context)} chars)")
        
        if full_context:
            params['memory_context'] = full_context
            logger.info(
                f"[{session_id[:20]}...] Using combined context "
                f"({len(full_context)} chars)"
            )
        else:
            logger.warning(f"[{session_id[:20]}...] NO CONTEXT AVAILABLE!")
        
        result = await conv_action.execute(user_input, params=params)
        return result.message
    
    def get_stats(self) -> Dict[str, Any]:
        """Get service statistics"""
        stats = {
            'actions_available': len(self.actions.list_actions()),
            'memory_enabled': self.memory is not None,
            'rag_enabled': self.rag is not None,
            'session_aware': True,
            'client_aware': True  # ✅ NEW
        }
        
        if self.memory:
            memory_stats = self.memory.get_stats()
            stats['memory'] = memory_stats
        
        if self.rag:
            from modules.rag import get_indexer
            try:
                indexer = get_indexer()
                rag_stats = indexer.get_stats()
                stats['rag'] = {
                    'total_documents': rag_stats.total_documents,
                    'total_chunks': rag_stats.total_chunks
                }
            except:
                pass
        
        return stats