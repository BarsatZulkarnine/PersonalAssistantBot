"""
Test Memory Recall

Run this to test if memory system properly recalls previous messages.
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.ai.integration import initialize_ai_provider
from modules.memory import get_memory_manager, MemoryManager

# maybe will fix this one day
from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv(), override=False)

async def test_memory_recall():
    """Test memory system with session isolation"""
    
    print("=" * 60)
    print("MEMORY RECALL TEST")
    print("=" * 60)
    
    # Initialize
    print("\n1. Initializing AI provider...")
    ai_provider = initialize_ai_provider()
    print(f"   ✓ Using: {ai_provider.config.provider_name}/{ai_provider.config.model}")
    
    print("\n2. Initializing memory manager...")
    memory = get_memory_manager()
    print("   ✓ Memory system ready")
    
    # Generate session IDs
    session1 = MemoryManager.generate_session_id("testuser", "desktop")
    session2 = MemoryManager.generate_session_id("testuser", "pi")
    
    print(f"\n3. Generated sessions:")
    print(f"   Session 1 (Desktop): {session1}")
    print(f"   Session 2 (Pi):      {session2}")
    
    # ============================================
    # TEST 1: Store conversations in Session 1
    # ============================================
    print("\n" + "=" * 60)
    print("TEST 1: Store conversations in Session 1 (Desktop)")
    print("=" * 60)
    
    conversations_s1 = [
        ("My name is Alice", "Nice to meet you, Alice!"),
        ("I live in Paris", "Paris is a beautiful city!"),
        ("What's my name?", "Your name is Alice.")
    ]
    
    for i, (user_input, assistant_response) in enumerate(conversations_s1, 1):
        print(f"\n  Turn {i}: '{user_input}'")
        
        result = await memory.process_conversation(
            user_input=user_input,
            assistant_response=assistant_response,
            session_id=session1,
            user_id="testuser",
            intent_type="AI"
        )
        
        print(f"    → Category: {result.category.value}")
        print(f"    → Importance: {result.importance_score:.2f}")
        if result.extracted_facts:
            print(f"    → Facts: {result.extracted_facts}")
    
    # ============================================
    # TEST 2: Store different conversations in Session 2
    # ============================================
    print("\n" + "=" * 60)
    print("TEST 2: Store DIFFERENT conversations in Session 2 (Pi)")
    print("=" * 60)
    
    conversations_s2 = [
        ("Turn on the lights", "Lights turned on!"),
        ("What's the temperature?", "It's 22°C"),
    ]
    
    for i, (user_input, assistant_response) in enumerate(conversations_s2, 1):
        print(f"\n  Turn {i}: '{user_input}'")
        
        result = await memory.process_conversation(
            user_input=user_input,
            assistant_response=assistant_response,
            session_id=session2,
            user_id="testuser",
            intent_type="AI"
        )
        
        print(f"    → Category: {result.category.value}")
        print(f"    → Importance: {result.importance_score:.2f}")
    
    # ============================================
    # TEST 3: Retrieve from Session 1
    # ============================================
    print("\n" + "=" * 60)
    print("TEST 3: Retrieve from Session 1 (should see Alice, Paris)")
    print("=" * 60)
    
    queries_s1 = [
        "What's my name?",
        "Where do I live?",
        "What did I say about lights?"  # Should NOT find (different session)
    ]
    
    for query in queries_s1:
        print(f"\n  Query: '{query}'")
        
        results = await memory.retrieve_context(
            query=query,
            session_id=session1,
            user_id="testuser",
            max_results=3,
            include_recent=True,
            include_facts=True
        )
        
        print(f"    → Found {len(results)} results:")
        for i, result in enumerate(results, 1):
            source = "SESSION" if result.session_id == session1 else "FACT"
            print(f"      {i}. [{source}] {result.content[:80]}...")
            print(f"         (score={result.relevance_score:.2f})")
    
    # ============================================
    # TEST 4: Retrieve from Session 2
    # ============================================
    print("\n" + "=" * 60)
    print("TEST 4: Retrieve from Session 2 (should see lights, temp)")
    print("=" * 60)
    
    queries_s2 = [
        "What did I say about lights?",
        "What's my name?"  # Should find FACT (Alice), but not SESSION conv
    ]
    
    for query in queries_s2:
        print(f"\n  Query: '{query}'")
        
        results = await memory.retrieve_context(
            query=query,
            session_id=session2,
            user_id="testuser",
            max_results=3,
            include_recent=True,
            include_facts=True
        )
        
        print(f"    → Found {len(results)} results:")
        for i, result in enumerate(results, 1):
            source = "SESSION" if result.session_id == session2 else "FACT"
            print(f"      {i}. [{source}] {result.content[:80]}...")
            print(f"         (score={result.relevance_score:.2f})")
    
    # ============================================
    # TEST 5: Stats
    # ============================================
    print("\n" + "=" * 60)
    print("TEST 5: Memory Stats")
    print("=" * 60)
    
    stats_s1 = memory.get_session_stats(session1, "testuser")
    stats_s2 = memory.get_session_stats(session2, "testuser")
    
    print(f"\nSession 1 (Desktop):")
    print(f"  Total turns: {stats_s1['total_turns']}")
    print(f"  First turn: {stats_s1['first_turn']}")
    
    print(f"\nSession 2 (Pi):")
    print(f"  Total turns: {stats_s2['total_turns']}")
    print(f"  First turn: {stats_s2['first_turn']}")
    
    overall_stats = memory.get_stats()
    print(f"\nOverall:")
    print(f"  Total conversations: {overall_stats['sql']['total_conversations']}")
    print(f"  Total facts: {overall_stats['sql']['total_facts']}")
    
    print("\n" + "=" * 60)
    print("TEST COMPLETE")
    print("=" * 60)
    
    # Expected results:
    print("\nEXPECTED RESULTS:")
    print("✓ Session 1 should recall: Alice, Paris")
    print("✓ Session 2 should recall: lights, temperature")
    print("✓ Both sessions should access shared FACTS (Alice, Paris)")
    print("✓ Session 1 should NOT see Session 2's lights conversation")
    print("✓ Session 2 should NOT see Session 1's Paris conversation")

if __name__ == "__main__":
    asyncio.run(test_memory_recall())