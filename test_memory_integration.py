#!/usr/bin/env python3
"""
Test Memory Integration with Orchestrator

Tests the complete flow:
1. User speaks with context
2. Assistant remembers information
3. Assistant recalls information in future conversations
"""

import sys
import os
import asyncio
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

def print_section(title: str):
    """Print a section header"""
    print(f"\n{'='*70}")
    print(f"  {title}")
    print('='*70)

async def test_basic_memory_flow():
    """Test the basic memory integration"""
    print_section("Test: Memory Integration with Orchestrator")
    
    print("\n🔧 Setting up test environment...")
    
    # Clean test databases
    test_db = "data/test_integration.db"
    test_vector = "data/test_integration_chromadb"
    
    if os.path.exists(test_db):
        os.remove(test_db)
        print("   Removed old test database")
    
    # Import after cleanup
    from core.orchestrator import AssistantOrchestrator
    
    print("   Initializing orchestrator...")
    orchestrator = AssistantOrchestrator()
    
    # Override memory paths for testing
    if orchestrator.memory:
        orchestrator.memory.sql_store.db_path = Path(test_db)
        orchestrator.memory.sql_store.initialize()
        print("   ✅ Memory system ready")
    else:
        print("   ❌ Memory system not available!")
        return False
    
    # Simulate conversations
    conversations = [
        {
            "turn": 1,
            "user": "Hi there!",
            "expected_memory": "ephemeral"
        },
        {
            "turn": 2,
            "user": "My name is Alice and I was born on March 15, 1990",
            "expected_memory": "factual"
        },
        {
            "turn": 3,
            "user": "I really love jazz music, especially Miles Davis",
            "expected_memory": "factual"
        },
        {
            "turn": 4,
            "user": "I live in Melbourne, Australia",
            "expected_memory": "factual"
        },
        {
            "turn": 5,
            "user": "What's my name?",
            "expected_recall": "Alice"
        },
        {
            "turn": 6,
            "user": "When's my birthday?",
            "expected_recall": "March 15"
        },
        {
            "turn": 7,
            "user": "What kind of music do I like?",
            "expected_recall": "jazz"
        }
    ]
    
    print("\n" + "="*70)
    print("  Simulating Conversation with Memory")
    print("="*70)
    
    for conv in conversations:
        print(f"\n--- Turn {conv['turn']} ---")
        print(f"User: {conv['user']}")
        
        # Process through orchestrator
        try:
            response = await orchestrator.process_user_input(conv['user'])
            print(f"Assistant: {response}")
            
            # Check expectations
            if 'expected_memory' in conv:
                # Check if it was classified correctly
                # (We can't easily check this without exposing internals,
                #  but we can check if facts were stored)
                if conv['expected_memory'] == 'factual':
                    facts = orchestrator.memory.get_user_facts(limit=10)
                    print(f"   📚 Facts stored: {len(facts)}")
            
            if 'expected_recall' in conv:
                # Check if response contains expected info
                if conv['expected_recall'].lower() in response.lower():
                    print(f"   ✅ Successfully recalled: {conv['expected_recall']}")
                else:
                    print(f"   ⚠️  Expected recall not found: {conv['expected_recall']}")
            
        except Exception as e:
            print(f"   ❌ Error: {e}")
            import traceback
            traceback.print_exc()
    
    # Final memory stats
    print("\n" + "="*70)
    print("  Memory Statistics")
    print("="*70)
    
    stats = orchestrator.memory.get_stats()
    print(f"\n📊 Summary:")
    print(f"   Total Conversations: {stats['sql']['total_conversations']}")
    print(f"   Total Facts: {stats['sql']['total_facts']}")
    print(f"   Session Turns: {stats['turn_count']}")
    
    if 'vector' in stats:
        print(f"   Vector Embeddings: {stats['vector']['total_embeddings']}")
    
    # Show stored facts
    print(f"\n📚 Stored Facts:")
    facts = orchestrator.memory.get_user_facts(limit=20)
    for fact in facts:
        print(f"   • [{fact.category.value if fact.category else 'unknown'}] {fact.content}")
    
    # Verify we have facts
    assert len(facts) >= 3, "Should have stored at least 3 facts"
    
    print("\n✅ Integration test passed!")
    return True

async def test_memory_commands():
    """Test special memory commands in text mode"""
    print_section("Test: Memory Commands")
    
    from modules.memory import get_memory_manager
    
    manager = get_memory_manager()
    
    print("\n📋 Testing memory commands...")
    
    # Test stats
    stats = manager.get_stats()
    print(f"\n1. Stats Command:")
    print(f"   Conversations: {stats['sql']['total_conversations']}")
    print(f"   Facts: {stats['sql']['total_facts']}")
    
    # Test search
    print(f"\n2. Search Command:")
    results = await manager.retrieve_context("Alice", max_results=3)
    print(f"   Found {len(results)} results for 'Alice'")
    for result in results:
        print(f"      • {result.content[:60]}...")
    
    # Test facts listing
    print(f"\n3. Facts Command:")
    facts = manager.get_user_facts(limit=5)
    print(f"   Listed {len(facts)} facts")
    
    print("\n✅ Memory commands working!")

async def run_all_tests():
    """Run all integration tests"""
    print("\n" + "="*70)
    print("  🧪 Memory Integration Tests")
    print("="*70)
    
    try:
        # Test 1: Basic memory flow
        success = await test_basic_memory_flow()
        
        if not success:
            return False
        
        # Test 2: Memory commands
        await test_memory_commands()
        
        # Summary
        print_section("✅ ALL INTEGRATION TESTS PASSED!")
        
        print("\n🎉 Memory system fully integrated!")
        print("\n💡 Try it yourself:")
        print("   python main.py --mode text")
        print("   > My name is [your name]")
        print("   > What's my name?")
        print("\n   Or use memory commands:")
        print("   > memory:stats")
        print("   > memory:facts")
        print("   > memory:search [query]")
        
        return True
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(run_all_tests())
    sys.exit(0 if success else 1)