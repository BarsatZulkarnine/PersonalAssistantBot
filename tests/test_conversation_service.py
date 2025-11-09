"""
Test ConversationService - Phase 1

Tests that business logic can be tested WITHOUT hardware.
This is the key benefit of extracting the service.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, MagicMock
from core.services.conversation_service import ConversationService
from modules.intent.base import IntentResult, IntentType
from modules.actions.base import ActionResult


class TestConversationService:
    """Test suite for ConversationService"""
    
    @pytest.fixture
    def mock_intent_detector(self):
        """Mock intent detector"""
        detector = Mock()
        detector.detect = AsyncMock()
        return detector
    
    @pytest.fixture
    def mock_action_registry(self):
        """Mock action registry"""
        registry = Mock()
        registry.find_action_for_prompt = Mock()
        registry.get_all_actions = Mock(return_value={})
        registry.list_actions = Mock(return_value=[])
        return registry
    
    @pytest.fixture
    def mock_memory_manager(self):
        """Mock memory manager"""
        memory = Mock()
        memory.retrieve_context = AsyncMock(return_value=[])
        memory.format_context_for_prompt = Mock(return_value="")
        memory.process_conversation = AsyncMock()
        return memory
    
    @pytest.fixture
    def mock_rag_retriever(self):
        """Mock RAG retriever"""
        rag = Mock()
        rag.retrieve = AsyncMock(return_value=[])
        rag.format_context = Mock(return_value="")
        return rag
    
    @pytest.fixture
    def service(self, mock_intent_detector, mock_action_registry, 
                mock_memory_manager, mock_rag_retriever):
        """Create service with mocked dependencies"""
        return ConversationService(
            intent_detector=mock_intent_detector,
            action_registry=mock_action_registry,
            memory_manager=mock_memory_manager,
            rag_retriever=mock_rag_retriever
        )
    
    @pytest.mark.asyncio
    async def test_process_input_basic(self, service, mock_intent_detector):
        """Test basic input processing"""
        # Setup
        mock_intent_detector.detect.return_value = IntentResult(
            intent_type=IntentType.AI,
            confidence=0.9,
            original_text="Hello",
            reasoning="Greeting"
        )
        
        # Mock AI chat action
        mock_action = Mock()
        mock_action.name = "AIChatAction"
        mock_action.execute = AsyncMock(return_value=ActionResult(
            success=True,
            message="Hi! How can I help you?"
        ))
        
        service.actions.get_all_actions.return_value = {
            'AIChatAction': mock_action
        }
        
        # Execute
        result = await service.process_input("Hello")
        
        # Assert
        assert result['response'] == "Hi! How can I help you?"
        assert result['intent'] == 'AI'
        assert result['confidence'] == 0.9
        assert result['action_executed'] is None
        assert isinstance(result['duration_ms'], float)
    
    @pytest.mark.asyncio
    async def test_process_input_action(self, service, mock_intent_detector, 
                                       mock_action_registry):
        """Test action execution"""
        # Setup
        mock_intent_detector.detect.return_value = IntentResult(
            intent_type=IntentType.ACTION,
            confidence=0.95,
            original_text="turn on lights",
            reasoning="Action detected"
        )
        
        # Mock action
        mock_action = Mock()
        mock_action.name = "LightAction"
        mock_action.execute = AsyncMock(return_value=ActionResult(
            success=True,
            message="Lights turned on"
        ))
        
        mock_action_registry.find_action_for_prompt.return_value = mock_action
        
        # Execute
        result = await service.process_input("turn on lights")
        
        # Assert
        assert result['response'] == "Lights turned on"
        assert result['intent'] == 'Action'
        assert result['action_executed'] == "LightAction"
    
    @pytest.mark.asyncio
    async def test_process_input_with_memory(self, service, mock_intent_detector,
                                            mock_memory_manager):
        """Test that memory is retrieved and stored"""
        # Setup
        mock_intent_detector.detect.return_value = IntentResult(
            intent_type=IntentType.AI,
            confidence=0.9,
            original_text="What's my name?",
            reasoning="Personal question"
        )
        
        # Mock memory retrieval
        from modules.memory.base import RetrievalResult
        mock_memory_manager.retrieve_context.return_value = [
            RetrievalResult(
                content="User's name is Alice",
                relevance_score=0.9,
                source='sql'
            )
        ]
        mock_memory_manager.format_context_for_prompt.return_value = \
            "Relevant information:\n- User's name is Alice"
        
        # Mock memory classification
        from modules.memory.base import MemoryClassification, MemoryCategory
        mock_memory_manager.process_conversation.return_value = \
            MemoryClassification(
                category=MemoryCategory.CONVERSATIONAL,
                importance_score=0.5,
                reasoning="Casual conversation"
            )
        
        # Mock AI action
        mock_action = Mock()
        mock_action.name = "AIChatAction"
        mock_action.execute = AsyncMock(return_value=ActionResult(
            success=True,
            message="Your name is Alice!"
        ))
        
        service.actions.get_all_actions.return_value = {
            'AIChatAction': mock_action
        }
        
        # Execute
        result = await service.process_input("What's my name?")
        
        # Assert
        assert result['memory_stored'] == True
        assert mock_memory_manager.retrieve_context.called
        assert mock_memory_manager.process_conversation.called
    
    @pytest.mark.asyncio
    async def test_process_input_error_handling(self, service, mock_intent_detector):
        """Test error handling"""
        # Setup - make intent detector fail
        mock_intent_detector.detect.side_effect = Exception("Intent detection failed")
        
        # Execute
        result = await service.process_input("test")
        
        # Assert
        assert result['intent'] == 'error'
        assert result['confidence'] == 0.0
        assert 'error' in result['response'].lower()
        assert 'error' in result['metadata']
    
    @pytest.mark.asyncio
    async def test_service_without_memory(self, mock_intent_detector, 
                                         mock_action_registry):
        """Test service works without memory system"""
        # Create service without memory
        service = ConversationService(
            intent_detector=mock_intent_detector,
            action_registry=mock_action_registry,
            memory_manager=None,
            rag_retriever=None
        )
        
        # Setup
        mock_intent_detector.detect.return_value = IntentResult(
            intent_type=IntentType.AI,
            confidence=0.9,
            original_text="Hello",
            reasoning="Greeting"
        )
        
        # Mock AI action
        mock_action = Mock()
        mock_action.name = "AIChatAction"
        mock_action.execute = AsyncMock(return_value=ActionResult(
            success=True,
            message="Hi!"
        ))
        
        service.actions.get_all_actions.return_value = {
            'AIChatAction': mock_action
        }
        
        # Execute
        result = await service.process_input("Hello")
        
        # Assert - should work fine
        assert result['response'] == "Hi!"
        assert result['memory_stored'] == False
        assert result['rag_used'] == False
    
    def test_get_stats(self, service):
        """Test stats retrieval"""
        stats = service.get_stats()
        
        assert 'actions_available' in stats
        assert 'memory_enabled' in stats
        assert 'rag_enabled' in stats
        assert stats['memory_enabled'] == True
        assert stats['rag_enabled'] == True


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v"])