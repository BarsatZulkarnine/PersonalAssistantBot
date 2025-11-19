#!/usr/bin/env python3
"""
Memory System Debug Test

Tests to identify why memory context isn't being retrieved.
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from modules.memory import get_memory_manager
from modules.intent.base import IntentType
from utils.logger import get_logger
from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv(), override=False)
logger = get_logger('memory_debug')


async def test_memory_storage():
    """Test 1: Can we store conversations?"""
    print("\n=== TEST 1: Memory Storage ===")
    
    memory = get_memory_manager()
    
    # Store a conversation
    session_id = "test_session_123"
    user_id = "test_user"
    
    classification = await memory.process_conversation(
        user_input="what is life?",
        assistant_response="Life is a complex concept...",
        session_id=session_id,
        user_id=user_id,
        intent_type=IntentType.AI.value,
        duration_ms=100,
        prompt_tokens=10,
        completion_tokens=20
    )
    
    print(f"✓ Stored conversation: category={classification.category.value}, "
          f"importance={classification.importance_score:.2f}")
    
    # Check if it was stored
    stats = memory.get_stats()
    print(f"✓ Total conversations: {stats['sql']['total_conversations']}")
    
    return session_id, user_id


async def test_memory_retrieval(session_id: str, user_id: str):
    """Test 2: Can we retrieve stored conversations?"""
    print("\n=== TEST 2: Memory Retrieval ===")
    
    memory = get_memory_manager()
    
    # Try to retrieve the conversation we just stored
    results = await memory.retrieve_context(
        query="what was my last question?",
        session_id=session_id,
        user_id=user_id,
        max_results=5,
        include_recent=True
    )
    
    print(f"✓ Retrieved {len(results)} memory items")
    
    if results:
        for i, result in enumerate(results, 1):
            print(f"\n  Memory {i}:")
            print(f"    Type: {result.type if hasattr(result, 'type') else 'conversation'}")
            print(f"    Content: {result.content[:100]}...")
            print(f"    Score: {result.score:.3f}")
            print(f"    Source: {result.source}")
            print(f"    Timestamp: {result.timestamp}")
    else:
        print("  ⚠️ NO RESULTS FOUND!")
    
    return results


async def test_context_formatting(results):
    """Test 3: Can we format context properly?"""
    print("\n=== TEST 3: Context Formatting ===")
    
    if not results:
        print("  ⚠️ No results to format")
        return None
    
    memory = get_memory_manager()
    
    context = memory.format_context_for_prompt(results, max_length=500)
    
    print(f"✓ Formatted context ({len(context)} chars):")
    print(f"\n{context}\n")
    
    return context


async def test_sql_direct():
    """Test 4: Check SQL store directly"""
    print("\n=== TEST 4: SQL Store Direct Query ===")
    
    from modules.memory import get_sql_store
    
    sql_store = get_sql_store()
    
    # Get recent conversations
    conversations = await sql_store.get_recent_conversations(limit=5)
    
    print(f"✓ Found {len(conversations)} recent conversations:")
    
    for conv in conversations:
        print(f"\n  Session: {conv.session_id}")
        print(f"  User: {conv.user_input[:50]}...")
        print(f"  Assistant: {conv.assistant_response[:50]}...")
        print(f"  Timestamp: {conv.timestamp}")


async def test_vector_search():
    """Test 5: Check vector store search"""
    print("\n=== TEST 5: Vector Store Search ===")
    
    from modules.memory import get_vector_store
    
    vector_store = get_vector_store()
    
    # Search for similar conversations
    results = await vector_store.search(
        query="what was my question",
        top_k=3
    )
    
    print(f"✓ Vector search returned {len(results)} results:")
    
    for i, result in enumerate(results, 1):
        print(f"\n  Result {i}:")
        print(f"    Content: {result.content[:80]}...")
        print(f"    Score: {result.score:.3f}")
        print(f"    Metadata: {result.metadata}")


async def test_full_pipeline():
    """Test 6: Full pipeline simulation"""
    print("\n=== TEST 6: Full Pipeline Simulation ===")
    
    memory = get_memory_manager()
    
    session_id = "pipeline_test_456"
    user_id = "test_user"
    
    # Step 1: Store first conversation
    print("\n1. Storing first conversation...")
    await memory.process_conversation(
        user_input="My favorite color is blue",
        assistant_response="I'll remember that your favorite color is blue!",
        session_id=session_id,
        user_id=user_id,
        intent_type=IntentType.AI.value,
        duration_ms=100,
        prompt_tokens=10,
        completion_tokens=15
    )
    
    # Step 2: Store second conversation
    print("2. Storing second conversation...")
    await memory.process_conversation(
        user_input="what is life?",
        assistant_response="Life is complex...",
        session_id=session_id,
        user_id=user_id,
        intent_type=IntentType.AI.value,
        duration_ms=100,
        prompt_tokens=10,
        completion_tokens=20
    )
    
    # Step 3: Try to retrieve context
    print("3. Retrieving context...")
    results = await memory.retrieve_context(
        query="what was my last question?",
        session_id=session_id,
        user_id=user_id,
        max_results=5,
        include_recent=True
    )
    
    print(f"\n✓ Retrieved {len(results)} items for 'what was my last question?'")
    
    if results:
        context = memory.format_context_for_prompt(results, max_length=500)
        print(f"\n✓ Context would be injected ({len(context)} chars):")
        print(context)
    else:
        print("\n⚠️ NO CONTEXT RETRIEVED - THIS IS THE PROBLEM!")


async def main():
    """Run all tests"""
    print("=" * 60)
    print("Memory System Debug Tests")
    print("=" * 60)
    
    try:
        # Test storage
        session_id, user_id = await test_memory_storage()
        
        # Wait a moment for async operations
        await asyncio.sleep(0.5)
        
        # Test retrieval
        results = await test_memory_retrieval(session_id, user_id)
        
        # Test formatting
        await test_context_formatting(results)
        
        # Test SQL directly
        await test_sql_direct()
        
        # Test vector search
        await test_vector_search()
        
        # Test full pipeline
        await test_full_pipeline()
        
        print("\n" + "=" * 60)
        print("DIAGNOSIS:")
        print("=" * 60)
        
        if not results:
            print("❌ PROBLEM IDENTIFIED: retrieve_context() returns empty results")
            print("\nPossible causes:")
            print("1. Session ID mismatch")
            print("2. Vector search not finding similar content")
            print("3. Filtering logic too strict")
            print("4. Async timing issue")
        else:
            print("✓ Memory retrieval working correctly")
        
    except Exception as e:
        print(f"\n💥 TEST FAILED: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())