#!/usr/bin/env python3
"""
Test Memory Recall

Verifies that facts are stored with full context and can be recalled correctly.
"""

import sys
import os
import asyncio
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from modules.memory import get_memory_manager

async def test_fact_storage_and_recall():
    """Test that facts are stored with full sentences and can be recalled"""
    
    print("\n" + "="*70)
    print("  Testing Fact Storage & Recall")
    print("="*70)
    
    # Clean test database
    test_db = "data/test_recall.db"
    test_vector = "data/test_recall_chromadb"
    
    if os.path.exists(test_db):
        os.remove(test_db)
    
    from modules.memory.memory_manager import MemoryManager
    manager = MemoryManager(db_path=test_db, vector_path=test_vector)
    
    # Test conversations
    print("\n📝 Storing information...")
    
    # Conversation 1: Name and birthday
    print("\n1. User: My name is Alice and my birthday is March 15, 1990")
    classification = await manager.process_conversation(
        user_input="My name is Alice and my birthday is March 15, 1990",
        assistant_response="Nice to meet you, Alice! I'll remember your birthday.",
        intent_type="AI"
    )
    print(f"   Category: {classification.category.value}")
    print(f"   Importance: {classification.importance_score}")
    
    # Conversation 2: Location
    print("\n2. User: I live in Melbourne, Australia")
    classification = await manager.process_conversation(
        user_input="I live in Melbourne, Australia",
        assistant_response="Got it! Melbourne is a great city.",
        intent_type="AI"
    )
    print(f"   Category: {classification.category.value}")
    
    # Conversation 3: Preference
    print("\n3. User: I love jazz music, especially Miles Davis")
    classification = await manager.process_conversation(
        user_input="I love jazz music, especially Miles Davis",
        assistant_response="Jazz is wonderful! Miles Davis was a legend.",
        intent_type="AI"
    )
    print(f"   Category: {classification.category.value}")
    
    # Check what was stored
    print("\n" + "="*70)
    print("  Stored Facts")
    print("="*70)
    
    facts = manager.get_user_facts(limit=10)
    print(f"\nTotal facts stored: {len(facts)}")
    
    for fact in facts:
        print(f"\n  [{fact.category.value if fact.category else 'unknown'}] "
              f"[{fact.importance_score:.2f}]")
        print(f"  Content: {fact.content}")
    
    # Test retrieval with various queries
    print("\n" + "="*70)
    print("  Testing Retrieval")
    print("="*70)
    
    test_queries = [
        ("What's my name?", "Alice"),
        ("When is my birthday?", "March 15"),
        ("Where do I live?", "Melbourne"),
        ("What music do I like?", "jazz"),
        ("Tell me about myself", "Alice"),  # Should find multiple facts
    ]
    
    for query, expected_keyword in test_queries:
        print(f"\n🔍 Query: '{query}'")
        
        results = await manager.retrieve_context(
            query=query,
            max_results=5,
            include_recent=False  # Only search stored facts
        )
        
        if results:
            print(f"   Found {len(results)} results:")
            for i, result in enumerate(results, 1):
                print(f"      {i}. [{result.relevance_score:.2f}] {result.content[:80]}...")
            
            # Check if expected keyword is in results
            found = any(expected_keyword.lower() in r.content.lower() for r in results)
            if found:
                print(f"   ✅ Successfully found: '{expected_keyword}'")
            else:
                print(f"   ❌ Expected '{expected_keyword}' not found!")
                print(f"   ⚠️  This indicates a retrieval problem")
        else:
            print(f"   ❌ No results found!")
            print(f"   ⚠️  This indicates facts weren't stored properly")
    
    # Test FTS search directly
    print("\n" + "="*70)
    print("  Testing FTS Search")
    print("="*70)
    
    fts_queries = ["birthday", "Alice", "Melbourne", "jazz", "music"]
    
    for query in fts_queries:
        results = manager.sql_store.search_facts(query, limit=5)
        if results:
            print(f"\n✅ FTS '{query}': Found {len(results)} results")
            print(f"   Top: {results[0].content[:60]}...")
        else:
            print(f"\n❌ FTS '{query}': No results")
    
    # Final verdict
    print("\n" + "="*70)
    print("  Test Results")
    print("="*70)
    
    stats = manager.get_stats()
    print(f"\nFacts stored: {stats['sql']['total_facts']}")
    
    if stats['sql']['total_facts'] >= 3:
        print("✅ Facts are being stored")
    else:
        print("❌ Not enough facts stored")
    
    # Check if we can retrieve anything
    test_result = await manager.retrieve_context("Alice", max_results=1)
    if test_result:
        print("✅ Retrieval is working")
        print(f"   Sample: {test_result[0].content[:60]}...")
    else:
        print("❌ Retrieval is broken")
    
    print("\n" + "="*70)
    print("💡 To fix your existing database:")
    print("   python fix_existing_facts.py")
    print("="*70)

if __name__ == "__main__":
    asyncio.run(test_fact_storage_and_recall())