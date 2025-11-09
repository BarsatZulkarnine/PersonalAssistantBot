"""
Conversation Service - Pure Business Logic

Extracted from orchestrator.py to separate business logic from I/O.
This service can be used by voice, CLI, API, or robot interfaces.

UPDATED: Web search now receives memory context and all interactions are stored.
"""

import time
from typing import Optional, Dict, Any
from datetime import datetime

from modules.intent.base import IntentType
from modules.actions.registry import ActionRegistry
from modules.memory.memory_manager import MemoryManager
from modules.rag.retriever import HybridRetriever
from utils.logger import get_logger, log_conversation

logger = get_logger('conversation_service')


class ConversationService:
    """
    Pure business logic for conversation processing.
    
    No I/O dependencies - returns data structures, doesn't do I/O.
    Can be tested without hardware.
    Reusable across all interfaces (voice, CLI, API, robot).
    
    FIXED: Web searches now use memory context and are stored in sessions.
    """
    
    def __init__(
        self,
        intent_detector,
        action_registry: ActionRegistry,
        memory_manager: Optional[MemoryManager] = None,
        rag_retriever: Optional[HybridRetriever] = None
    ):
        """
        Initialize service with dependencies.
        
        Args:
            intent_detector: Intent classification module
            action_registry: Action execution registry
            memory_manager: Optional memory system
            rag_retriever: Optional RAG document search
        """
        self.intent = intent_detector
        self.actions = action_registry
        self.memory = memory_manager
        self.rag = rag_retriever
        
        logger.info("ConversationService initialized")
    
    async def process_input(
        self,
        user_input: str,
        session_id: Optional[str] = None,
        user_id: str = "default_user"
    ) -> Dict[str, Any]:
        """
        Process user input through the full pipeline.
        
        Args:
            user_input: User's text input (from voice or keyboard)
            session_id: Optional session identifier
            user_id: User identifier for memory/personalization
        
        Returns:
            {
                'response': str,           # Response text to output
                'intent': str,             # Detected intent type
                'confidence': float,       # Intent confidence
                'action_executed': str,    # Action name if any
                'memory_stored': bool,     # Whether stored in memory
                'memory_category': str,    # Memory category (ephemeral/conversational/factual)
                'rag_used': bool,          # Whether RAG was used
                'duration_ms': float,      # Processing time
                'metadata': dict           # Additional data
            }
        """
        start_time = time.time()
        
        try:
            logger.info(f"Processing input: {user_input[:50]}...")
            
            # Step 1: Retrieve Memory Context
            memory_context = ""
            memory_results = []
            if self.memory:
                try:
                    logger.debug("Retrieving memory context...")
                    memory_results = await self.memory.retrieve_context(
                        query=user_input,
                        max_results=3,
                        include_recent=True
                    )
                    
                    if memory_results:
                        memory_context = self.memory.format_context_for_prompt(
                            memory_results,
                            max_length=500
                        )
                        logger.info(f"Retrieved {len(memory_results)} memory items")
                except Exception as e:
                    logger.error(f"Memory retrieval error: {e}")
            
            # Step 2: Search RAG Documents
            rag_context = ""
            rag_results = []
            if self.rag:
                try:
                    logger.debug("Searching RAG documents...")
                    rag_results = await self.rag.retrieve(
                        query=user_input,
                        top_k=3
                    )
                    
                    if rag_results:
                        rag_context = self.rag.format_context(
                            rag_results,
                            max_length=800
                        )
                        logger.info(f"Retrieved {len(rag_results)} document chunks")
                except Exception as e:
                    logger.error(f"RAG retrieval error: {e}")
            
            # Step 3: Detect Intent
            logger.debug("Detecting intent...")
            intent_result = await self.intent.detect(user_input)
            intent_type = intent_result.intent_type
            
            logger.info(
                f"Intent: {intent_type.value} "
                f"(confidence: {intent_result.confidence:.2f})"
            )
            
            # Step 4: Route Based on Intent (ALL get memory context now)
            response = ""
            action_executed = None
            
            if intent_type == IntentType.ACTION:
                response, action_executed = await self._handle_action(user_input)
            
            elif intent_type == IntentType.WEB:
                # FIXED: Pass memory_context to web search
                response = await self._handle_web_search(user_input, memory_context)
            
            else:  # IntentType.AI / Conversation
                response = await self._handle_conversation(
                    user_input,
                    memory_context,
                    rag_context
                )
            
            # Calculate processing time
            duration_ms = (time.time() - start_time) * 1000
            
            # Step 5: Store in Memory (FIXED: includes web searches)
            memory_stored = False
            memory_category = None  # ADDED: Track memory category
            if self.memory:
                try:
                    logger.debug("Storing conversation in memory...")
                    classification = await self.memory.process_conversation(
                        user_input=user_input,
                        assistant_response=response,
                        intent_type=intent_type.value,  # 'Web', 'Action', or 'AI'
                        duration_ms=duration_ms,
                        prompt_tokens=0,  # TODO: Track from AI calls
                        completion_tokens=0
                    )
                    
                    memory_stored = classification.should_store()
                    memory_category = classification.category.value  # ADDED: Capture category
                    logger.info(
                        f"Memory: {classification.category.value} "
                        f"(intent: {intent_type.value}, importance: {classification.importance_score:.2f})"
                    )
                except Exception as e:
                    logger.error(f"Memory storage error: {e}")
            
            # Log conversation (legacy logging)
            log_conversation(user_input, response)
            
            # Return structured result
            result = {
                'response': response,
                'intent': intent_type.value,
                'confidence': intent_result.confidence,
                'action_executed': action_executed,
                'memory_stored': memory_stored,
                'memory_category': memory_category,  # ADDED: Return category
                'rag_used': bool(rag_results),
                'duration_ms': duration_ms,
                'metadata': {
                    'memory_results': len(memory_results),
                    'rag_results': len(rag_results),
                    'session_id': session_id,
                    'user_id': user_id
                }
            }
            
            logger.info(f"Processing complete ({duration_ms:.0f}ms)")
            return result
            
        except Exception as e:
            logger.error(f"Error processing input: {e}", exc_info=True)
            
            # Return error result
            error_response = "Sorry, I encountered an error processing your request."
            log_conversation(user_input, error_response)
            
            return {
                'response': error_response,
                'intent': 'error',
                'confidence': 0.0,
                'action_executed': None,
                'memory_stored': False,
                'memory_category': None,  # ADDED
                'rag_used': False,
                'duration_ms': (time.time() - start_time) * 1000,
                'metadata': {
                    'error': str(e)
                }
            }
    
    async def _handle_action(self, user_input: str) -> tuple[str, Optional[str]]:
        """
        Handle action execution.
        
        Returns:
            (response_text, action_name)
        """
        logger.debug("Finding action...")
        
        # Find matching action
        action = self.actions.find_action_for_prompt(user_input)
        
        if not action:
            logger.warning("No matching action found")
            return ("I'm not sure how to do that.", None)
        
        # Execute action
        logger.info(f"Executing action: {action.name}")
        result = await action.execute(user_input)
        
        if result.success:
            logger.info(f"Action completed: {action.name}")
        else:
            logger.warning(f"Action failed: {result.message}")
        
        return (result.message, action.name)
    
    async def _handle_web_search(self, user_input: str, memory_context: str = "") -> str:
        """
        Handle web search request WITH MEMORY CONTEXT.
        
        FIXED: Now passes memory context to web search action.
        
        Args:
            user_input: User's search query
            memory_context: Retrieved memory context
            
        Returns:
            Search result message
        """
        logger.debug("Handling web search...")
        
        # Find web search action
        web_action = None
        for action in self.actions.get_all_actions().values():
            if action.name == "WebSearchAction":
                web_action = action
                break
        
        if web_action:
            # FIXED: Pass memory context via params
            params = {}
            if memory_context:
                params['memory_context'] = memory_context
                logger.info(f"Injecting memory context to web search ({len(memory_context)} chars)")
            
            result = await web_action.execute(user_input, params=params)
            return result.message
        
        logger.warning("Web search action not found")
        return "Web search not available."
    
    async def _handle_conversation(
        self,
        user_input: str,
        memory_context: str,
        rag_context: str
    ) -> str:
        """
        Handle general conversation with AI.
        
        Args:
            user_input: User's message
            memory_context: Context from memory
            rag_context: Context from documents
        
        Returns:
            AI response
        """
        logger.debug("Handling conversation...")
        
        # Find AI chat action
        conv_action = None
        for action in self.actions.get_all_actions().values():
            if action.name == "AIChatAction":
                conv_action = action
                break
        
        if not conv_action:
            logger.warning("AI chat action not found")
            return "I'm not sure how to respond to that."
        
        # Combine contexts
        params = {}
        full_context = ""
        
        if memory_context:
            full_context += memory_context
        
        if rag_context:
            if full_context:
                full_context += "\n\n"
            full_context += rag_context
        
        if full_context:
            params['memory_context'] = full_context
            logger.info(f"Using combined context ({len(full_context)} chars)")
        
        # Execute conversation
        result = await conv_action.execute(user_input, params=params)
        return result.message
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get service statistics.
        
        Returns:
            Dictionary of stats (memory, RAG, actions, etc.)
        """
        
        stats = {
            'actions_available': len(self.actions.list_actions()),
            'memory_enabled': self.memory is not None,
            'rag_enabled': self.rag is not None
        }
        
        # Memory stats
        if self.memory:
            memory_stats = self.memory.get_stats()
            stats['memory'] = memory_stats
        
        # RAG stats
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