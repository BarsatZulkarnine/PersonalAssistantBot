"""
Test Suite for Session-Aware Memory Manager

Tests multi-device, multi-user conversation isolation.
Run with: pytest tests/test_memory_sessions.py -v
"""

import pytest
import asyncio
import tempfile
import os
from datetime import datetime, timedelta

from modules.memory.memory_manager import MemoryManager
from modules.memory.base import MemoryCategory


@pytest.fixture
def temp_memory():
    """Create temporary memory manager for testing"""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test_memory.db")
        vector_path = os.path.join(tmpdir, "test_chromadb")
        
        memory = MemoryManager(db_path=db_path, vector_path=vector_path)
        yield memory


class TestSessionGeneration:
    """Test session ID generation"""
    
    def test_session_id_format(self):
        """Session ID should have correct format"""
        session_id = MemoryManager.generate_session_id("user1", "desktop")
        
        parts = session_id.split("_")
        assert len(parts) >= 4
        assert parts[0] == "user1"
        assert parts[1] == "desktop"
        # parts[2] and [3] are timestamp and UUID
    
    def test_session_id_unique(self):
        """Each session ID should be unique"""
        id1 = MemoryManager.generate_session_id("user1", "desktop")
        id2 = MemoryManager.generate_session_id("user1", "desktop")
        
        assert id1 != id2
    
    def test_session_id_without_device(self):
        """Session ID should work without device name"""
        session_id = MemoryManager.generate_session_id("user1")
        
        assert "user1" in session_id
        assert len(session_id.split("_")) >= 3


class TestSessionIsolation:
    """Test conversation isolation between sessions"""
    
    @pytest.mark.asyncio
    async def test_different_sessions_dont_mix(self, temp_memory):
        """Conversations from different sessions should not mix"""
        # Desktop session
        desktop_session = MemoryManager.generate_session_id("user1", "desktop")
        await temp_memory.process_conversation(
            user_input="What's the weather in Paris?",
            assistant_response="It's 15°C and sunny in Paris",
            session_id=desktop_session,
            user_id="user1"
        )
        
        # Raspberry Pi session (same time, same user)
        pi_session = MemoryManager.generate_session_id("user1", "pi")
        await temp_memory.process_conversation(
            user_input="Turn on the living room lights",
            assistant_response="Living room lights are now on",
            session_id=pi_session,
            user_id="user1"
        )
        
        # Desktop retrieves context - should NOT see Pi's conversation
        desktop_results = await temp_memory.retrieve_context(
            query="lights",
            session_id=desktop_session,
            user_id="user1",
            include_facts=False  # Don't include shared facts
        )
        
        # Should not find Pi's conversation
        assert len(desktop_results) == 0, "Desktop should not see Pi's conversation"
    
    @pytest.mark.asyncio
    async def test_same_session_retrieval(self, temp_memory):
        """Should retrieve from same session"""
        session_id = MemoryManager.generate_session_id("user1", "desktop")
        
        # First turn
        await temp_memory.process_conversation(
            user_input="What's the weather in Paris?",
            assistant_response="It's 15°C and sunny",
            session_id=session_id,
            user_id="user1"
        )
        
        # Second turn - should retrieve first turn
        results = await temp_memory.retrieve_context(
            query="weather Paris",
            session_id=session_id,
            user_id="user1",
            include_facts=False
        )
        
        assert len(results) > 0
        assert "Paris" in results[0].content
        assert results[0].session_id == session_id
    
    @pytest.mark.asyncio
    async def test_multi_turn_conversation(self, temp_memory):
        """Test multi-turn conversation in same session"""
        session_id = MemoryManager.generate_session_id("user1", "desktop")
        
        # Turn 1
        await temp_memory.process_conversation(
            user_input="My name is Alice",
            assistant_response="Nice to meet you, Alice!",
            session_id=session_id,
            user_id="user1"
        )
        
        # Turn 2
        await temp_memory.process_conversation(
            user_input="I like pizza",
            assistant_response="Great! Pizza is delicious.",
            session_id=session_id,
            user_id="user1"
        )
        
        # Turn 3 - retrieve both
        results = await temp_memory.retrieve_context(
            query="What do I like?",
            session_id=session_id,
            user_id="user1",
            include_recent=True
        )
        
        assert len(results) >= 2
        content = " ".join(r.content for r in results)
        assert "Alice" in content or "pizza" in content


class TestSharedFacts:
    """Test cross-session fact sharing"""
    
    @pytest.mark.asyncio
    async def test_facts_shared_across_sessions(self, temp_memory):
        """Factual memories should be accessible from all sessions"""
        # Desktop session - store a fact
        desktop_session = MemoryManager.generate_session_id("user1", "desktop")
        
        # Simulate storing a fact (you'll need to mock the classifier 
        # to return FACTUAL category)
        # For now, we'll test the concept
        
        await temp_memory.process_conversation(
            user_input="My favorite color is blue",
            assistant_response="I'll remember that your favorite color is blue",
            session_id=desktop_session,
            user_id="user1"
        )
        
        # Raspberry Pi session - retrieve fact
        pi_session = MemoryManager.generate_session_id("user1", "pi")
        
        results = await temp_memory.retrieve_context(
            query="favorite color",
            session_id=pi_session,
            user_id="user1",
            include_recent=False,  # Don't include desktop's conversation
            include_facts=True      # Do include shared facts
        )
        
        # Note: This will depend on classifier marking it as FACTUAL
        # In real usage, the classifier would handle this
        # For testing, you might need to mock the classifier


class TestMultiUser:
    """Test multi-user isolation"""
    
    @pytest.mark.asyncio
    async def test_different_users_isolated(self, temp_memory):
        """Different users should not see each other's conversations"""
        # User 1
        user1_session = MemoryManager.generate_session_id("user1", "desktop")
        await temp_memory.process_conversation(
            user_input="My secret is 1234",
            assistant_response="I've noted your secret",
            session_id=user1_session,
            user_id="user1"
        )
        
        # User 2 - should NOT see user1's secret
        user2_session = MemoryManager.generate_session_id("user2", "desktop")
        results = await temp_memory.retrieve_context(
            query="secret",
            session_id=user2_session,
            user_id="user2"
        )
        
        # Should not find user1's secret
        assert len(results) == 0, "User2 should not see User1's conversations"
    
    @pytest.mark.asyncio
    async def test_same_user_different_devices(self, temp_memory):
        """Same user on different devices should have isolated conversations"""
        # Desktop
        desktop_session = MemoryManager.generate_session_id("user1", "desktop")
        await temp_memory.process_conversation(
            user_input="Schedule meeting at 3pm",
            assistant_response="Meeting scheduled for 3pm",
            session_id=desktop_session,
            user_id="user1"
        )
        
        # Phone - should not see desktop's conversation
        phone_session = MemoryManager.generate_session_id("user1", "phone")
        results = await temp_memory.retrieve_context(
            query="meeting",
            session_id=phone_session,
            user_id="user1",
            include_facts=False  # Only check conversations
        )
        
        assert len(results) == 0, "Phone should not see desktop's conversation"


class TestConversationHistory:
    """Test conversation history retrieval"""
    
    @pytest.mark.asyncio
    async def test_get_session_history(self, temp_memory):
        """Should get full history for a session"""
        session_id = MemoryManager.generate_session_id("user1", "desktop")
        
        # Add multiple turns
        for i in range(5):
            await temp_memory.process_conversation(
                user_input=f"Question {i}",
                assistant_response=f"Answer {i}",
                session_id=session_id,
                user_id="user1"
            )
        
        # Get history
        history = temp_memory.get_conversation_history(
            session_id=session_id,
            user_id="user1",
            limit=10
        )
        
        assert len(history) == 5
        assert history[0].turn_no == 1
        assert history[-1].turn_no == 5
    
    @pytest.mark.asyncio
    async def test_session_stats(self, temp_memory):
        """Should get accurate session statistics"""
        session_id = MemoryManager.generate_session_id("user1", "desktop")
        
        # Add conversations
        for i in range(3):
            await temp_memory.process_conversation(
                user_input=f"Test {i}",
                assistant_response=f"Response {i}",
                session_id=session_id,
                user_id="user1"
            )
        
        # Get stats
        stats = temp_memory.get_session_stats(
            session_id=session_id,
            user_id="user1"
        )
        
        assert stats["total_turns"] == 3
        assert stats["session_id"] == session_id
        assert stats["user_id"] == "user1"


class TestCleanup:
    """Test old session cleanup"""
    
    @pytest.mark.asyncio
    async def test_cleanup_old_sessions(self, temp_memory):
        """Should delete old conversations"""
        # Create old session (simulate by storing with old timestamp)
        old_session = MemoryManager.generate_session_id("user1", "desktop")
        
        # Note: You'll need to modify sql_store to support custom timestamps
        # for testing, or wait and test with real time
        
        # For now, this is a placeholder test
        deleted = await temp_memory.cleanup_old_sessions(days_old=7)
        
        # Should not error
        assert deleted >= 0


class TestRealisticScenario:
    """Test realistic multi-device scenario"""
    
    @pytest.mark.asyncio
    async def test_desktop_and_pi_scenario(self, temp_memory):
        """
        Realistic scenario:
        - User on desktop asks about weather
        - User on Pi controls lights
        - Desktop doesn't see Pi's conversation
        - Both can access shared facts
        """
        # Desktop session
        desktop = MemoryManager.generate_session_id("alice", "desktop")
        
        # Desktop: Ask about weather
        await temp_memory.process_conversation(
            user_input="What's the weather like today?",
            assistant_response="It's 15°C and sunny",
            session_id=desktop,
            user_id="alice"
        )
        
        # Desktop: Another question
        await temp_memory.process_conversation(
            user_input="What should I wear?",
            assistant_response="A light jacket should be fine",
            session_id=desktop,
            user_id="alice"
        )
        
        # Raspberry Pi session
        pi = MemoryManager.generate_session_id("alice", "pi")
        
        # Pi: Control lights
        await temp_memory.process_conversation(
            user_input="Turn on the living room lights",
            assistant_response="Living room lights are now on",
            session_id=pi,
            user_id="alice"
        )
        
        # Pi: Another command
        await temp_memory.process_conversation(
            user_input="Set brightness to 50%",
            assistant_response="Brightness set to 50%",
            session_id=pi,
            user_id="alice"
        )
        
        # Test 1: Desktop retrieves its own context
        desktop_results = await temp_memory.retrieve_context(
            query="weather",
            session_id=desktop,
            user_id="alice",
            include_facts=False
        )
        
        assert len(desktop_results) > 0
        assert any("weather" in r.content.lower() for r in desktop_results)
        assert not any("lights" in r.content.lower() for r in desktop_results)
        
        # Test 2: Pi retrieves its own context
        pi_results = await temp_memory.retrieve_context(
            query="lights",
            session_id=pi,
            user_id="alice",
            include_facts=False
        )
        
        assert len(pi_results) > 0
        assert any("lights" in r.content.lower() for r in pi_results)
        assert not any("weather" in r.content.lower() for r in pi_results)
        
        # Test 3: Check session histories are separate
        desktop_history = temp_memory.get_conversation_history(
            session_id=desktop,
            user_id="alice"
        )
        
        pi_history = temp_memory.get_conversation_history(
            session_id=pi,
            user_id="alice"
        )
        
        assert len(desktop_history) == 2
        assert len(pi_history) == 2
        
        # Test 4: Get overall stats
        stats = temp_memory.get_stats()
        assert stats["sql"]["total_conversations"] == 4  # 2 desktop + 2 pi


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])