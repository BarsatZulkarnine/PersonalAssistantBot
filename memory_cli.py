#!/usr/bin/env python3
"""
Memory CLI Tool

Quick command-line interface for inspecting and managing the memory database.

Usage:
    python memory_cli.py --init              # Initialize database
    python memory_cli.py --stats             # Show statistics
    python memory_cli.py --list-facts        # List all facts
    python memory_cli.py --list-convs        # List conversations
    python memory_cli.py --search "query"    # Search facts
    python memory_cli.py --clear-test        # Clear test database
"""

import sys
import argparse
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from modules.memory import SQLStore, FactCategory

def init_database(args):
    """Initialize the database"""
    print("🔧 Initializing database...")
    store = SQLStore(args.db)
    store.initialize()
    print("✅ Database initialized successfully!")
    print(f"📁 Location: {args.db}")

def show_stats(args):
    """Show database statistics"""
    store = SQLStore(args.db)
    stats = store.get_stats()
    
    print("\n📊 Database Statistics")
    print("=" * 50)
    print(f"Total Conversations: {stats['total_conversations']}")
    print(f"Total Facts:         {stats['total_facts']}")
    print(f"Total Tokens:        {stats['total_tokens']:,}")
    print(f"Estimated Cost:      ${stats['estimated_cost_usd']:.4f}")
    print("=" * 50)

def list_facts(args):
    """List all facts"""
    store = SQLStore(args.db)
    facts = store.get_facts(limit=args.limit)
    
    if not facts:
        print("📭 No facts found")
        return
    
    print(f"\n📚 Facts (showing {len(facts)}):")
    print("=" * 80)
    
    for fact in facts:
        print(f"\n[ID: {fact.id}] [{fact.category.value if fact.category else 'none'}] "
              f"[Importance: {fact.importance_score:.2f}]")
        print(f"Content: {fact.content}")
        if fact.conversation_id:
            print(f"From conversation: {fact.conversation_id}")
        print(f"Created: {fact.created_at}")
        print("-" * 80)

def list_conversations(args):
    """List conversations"""
    store = SQLStore(args.db)
    convs = store.get_conversations(limit=args.limit)
    
    if not convs:
        print("📭 No conversations found")
        return
    
    print(f"\n💬 Conversations (showing {len(convs)}):")
    print("=" * 80)
    
    for conv in convs:
        print(f"\n[ID: {conv.id}] [Turn: {conv.turn_no}] [{conv.intent_type or 'unknown'}]")
        print(f"User:      {conv.user_input[:100]}...")
        print(f"Assistant: {conv.assistant_response[:100]}...")
        print(f"Tokens: {conv.prompt_tokens + conv.completion_tokens}")
        print(f"Time: {conv.timestamp}")
        print("-" * 80)

def search_facts(args):
    """Search facts using FTS"""
    if not args.query:
        print("❌ No query provided. Use --search 'your query'")
        return
    
    store = SQLStore(args.db)
    results = store.search_facts(args.query, limit=args.limit)
    
    if not results:
        print(f"📭 No results found for: {args.query}")
        return
    
    print(f"\n🔍 Search Results for: '{args.query}'")
    print("=" * 80)
    
    for i, result in enumerate(results, 1):
        print(f"\n{i}. [Score: {result.relevance_score:.2f}] "
              f"[Importance: {result.importance:.2f}]")
        print(f"   {result.content}")
        if result.created_at:
            print(f"   Created: {result.created_at}")
        print("-" * 80)

def clear_test_db(args):
    """Clear test database"""
    import os
    
    test_db = "data/test_memory.db"
    if os.path.exists(test_db):
        os.remove(test_db)
        print(f"🗑️  Removed test database: {test_db}")
    else:
        print("ℹ️  No test database found")

def list_facts_by_category(args):
    """List facts by category"""
    store = SQLStore(args.db)
    
    print("\n📋 Facts by Category:")
    print("=" * 80)
    
    for category in FactCategory:
        facts = store.get_facts(category=category, limit=100)
        if facts:
            print(f"\n{category.value.upper()} ({len(facts)} facts):")
            for fact in facts:
                print(f"  • {fact.content[:70]}...")

def dump_database(args):
    """Dump entire database structure"""
    store = SQLStore(args.db)
    
    print("\n🗄️  Database Dump")
    print("=" * 80)
    
    # Stats
    stats = store.get_stats()
    print(f"\nStatistics:")
    print(f"  Conversations: {stats['total_conversations']}")
    print(f"  Facts: {stats['total_facts']}")
    print(f"  Tokens: {stats['total_tokens']:,}")
    
    # Recent conversations
    print(f"\n💬 Recent Conversations (last 5):")
    convs = store.get_conversations(limit=5)
    for conv in convs:
        print(f"  [{conv.id}] {conv.user_input[:60]}...")
    
    # Facts by category
    print(f"\n📚 Facts by Category:")
    for category in FactCategory:
        facts = store.get_facts(category=category, limit=100)
        if facts:
            print(f"  {category.value}: {len(facts)}")

def main():
    parser = argparse.ArgumentParser(
        description="Memory Database CLI Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        '--db',
        default='data/memory.db',
        help='Database path (default: data/memory.db)'
    )
    
    parser.add_argument(
        '--limit',
        type=int,
        default=10,
        help='Limit results (default: 10)'
    )
    
    # Commands
    parser.add_argument('--init', action='store_true', help='Initialize database')
    parser.add_argument('--stats', action='store_true', help='Show statistics')
    parser.add_argument('--list-facts', action='store_true', help='List facts')
    parser.add_argument('--list-convs', action='store_true', help='List conversations')
    parser.add_argument('--search', type=str, metavar='QUERY', help='Search facts')
    parser.add_argument('--by-category', action='store_true', help='List facts by category')
    parser.add_argument('--dump', action='store_true', help='Dump database structure')
    parser.add_argument('--clear-test', action='store_true', help='Clear test database')
    
    args = parser.parse_args()
    
    # Execute command
    if args.init:
        init_database(args)
    elif args.stats:
        show_stats(args)
    elif args.list_facts:
        list_facts(args)
    elif args.list_convs:
        list_conversations(args)
    elif args.search:
        args.query = args.search
        search_facts(args)
    elif args.by_category:
        list_facts_by_category(args)
    elif args.dump:
        dump_database(args)
    elif args.clear_test:
        clear_test_db(args)
    else:
        parser.print_help()
        print("\n💡 Examples:")
        print("  python memory_cli.py --init")
        print("  python memory_cli.py --stats")
        print("  python memory_cli.py --list-facts --limit 5")
        print("  python memory_cli.py --search 'birthday'")
        print("  python memory_cli.py --dump")

if __name__ == "__main__":
    main()