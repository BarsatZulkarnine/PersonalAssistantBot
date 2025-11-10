#!/usr/bin/env python3
"""
Memory & RAG CLI Tool - UPDATED

Command-line interface for inspecting memory and RAG systems.

Usage:
    # Memory commands
    python memory_cli.py --stats                    # Show all stats
    python memory_cli.py --list-facts               # List facts
    python memory_cli.py --list-convs               # List conversations
    python memory_cli.py --list-sessions            # List all sessions
    python memory_cli.py --session SESSION_ID       # View specific session
    python memory_cli.py --search "query"           # Search memory
    python memory_cli.py --test-isolation           # Test session isolation
    
    # RAG commands
    python memory_cli.py --rag-stats                # RAG statistics
    python memory_cli.py --rag-list                 # List documents
    python memory_cli.py --rag-search "query"       # Search documents
    python memory_cli.py --rag-index PATH           # Index document/directory
    
    # Maintenance
    python memory_cli.py --cleanup DAYS             # Clean old conversations
    python memory_cli.py --clear-test               # Clear test database
"""

import sys
import argparse
import asyncio
from pathlib import Path
from datetime import datetime, timedelta

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

# ✅ FIX: Import only what we need to avoid circular imports
# Don't import get_memory_manager at top level


# ============================================
# MEMORY COMMANDS
# ============================================

def show_all_stats(args):
    """Show comprehensive statistics"""
    store = SQLStore(args.db)
    
    # Overall stats
    stats = store.get_stats()
    
    print("\n" + "="*60)
    print("📊 MEMORY SYSTEM STATISTICS")
    print("="*60)
    print(f"Total Conversations: {stats['total_conversations']}")
    print(f"Total Facts:         {stats['total_facts']}")
    print(f"Total Tokens:        {stats['total_tokens']:,}")
    print(f"Estimated Cost:      ${stats['estimated_cost_usd']:.4f}")
    
    # Session stats
    sessions = store.get_all_sessions_for_user("default_user", limit=100)
    print(f"\nTotal Sessions:      {len(sessions)}")
    
    if sessions:
        print("\n📅 Recent Sessions:")
        for i, sess in enumerate(sessions[:5], 1):
            print(f"\n  {i}. {sess['session_id'][:40]}...")
            print(f"     Turns: {sess['turn_count']}")
            print(f"     Last: {sess['last_turn']}")
    
    # Facts by category
    print("\n📚 Facts by Category:")
    for category in FactCategory:
        facts = store.get_facts(category=category, limit=1000)
        if facts:
            print(f"  {category.value.upper()}: {len(facts)} facts")
    
    # RAG stats (if available)
    try:
        from modules.rag import get_indexer
        indexer = get_indexer()
        rag_stats = indexer.get_stats()
        
        print("\n" + "="*60)
        print("📄 RAG SYSTEM STATISTICS")
        print("="*60)
        print(f"Total Documents:     {rag_stats.total_documents}")
        print(f"Total Chunks:        {rag_stats.total_chunks}")
        print(f"Total Size:          {rag_stats.total_size_bytes / 1024 / 1024:.2f} MB")
        
        if rag_stats.documents_by_type:
            print("\nDocuments by Type:")
            for doc_type, count in rag_stats.documents_by_type.items():
                print(f"  {doc_type.upper()}: {count}")
        
        if rag_stats.last_indexed:
            print(f"\nLast Indexed:        {rag_stats.last_indexed}")
    except Exception as e:
        print(f"\n⚠️  RAG stats unavailable: {e}")
    
    print("="*60)

def list_sessions(args):
    """List all sessions"""
    store = SQLStore(args.db)
    sessions = store.get_all_sessions_for_user(args.user, limit=args.limit)
    
    if not sessions:
        print("📭 No sessions found")
        return
    
    print(f"\n📅 Sessions for {args.user} (showing {len(sessions)}):")
    print("="*80)
    
    for i, sess in enumerate(sessions, 1):
        print(f"\n{i}. {sess['session_id']}")
        print(f"   Turns: {sess['turn_count']}")
        print(f"   First: {sess['first_turn']}")
        print(f"   Last:  {sess['last_turn']}")
        print(f"   Tokens: {sess['total_tokens']}")
        print("-"*80)

def view_session(args):
    """View specific session details"""
    if not args.session_id:
        print("❌ Please provide --session-id")
        return
    
    store = SQLStore(args.db)
    
    # Get conversations
    convs = store.get_conversations(
        user_id=args.user,
        session_id=args.session_id,
        limit=1000
    )
    
    if not convs:
        print(f"📭 No conversations found for session: {args.session_id}")
        return
    
    print(f"\n💬 Session: {args.session_id}")
    print("="*80)
    print(f"Total turns: {len(convs)}")
    print(f"First turn: {convs[-1].timestamp}")
    print(f"Last turn:  {convs[0].timestamp}")
    print("="*80)
    
    for i, conv in enumerate(reversed(convs), 1):
        print(f"\n[Turn {i}] [{conv.intent_type or 'unknown'}]")
        print(f"User:      {conv.user_input}")
        print(f"Assistant: {conv.assistant_response}")
        print(f"Time:      {conv.timestamp}")
        print("-"*80)

def list_facts(args):
    """List all facts"""
    store = SQLStore(args.db)
    
    if args.category:
        try:
            category = FactCategory[args.category.upper()]
            facts = store.get_facts(category=category, limit=args.limit)
        except KeyError:
            print(f"❌ Invalid category: {args.category}")
            print(f"Valid categories: {', '.join(c.value for c in FactCategory)}")
            return
    else:
        facts = store.get_facts(limit=args.limit)
    
    if not facts:
        print("📭 No facts found")
        return
    
    print(f"\n📚 Facts (showing {len(facts)}):")
    print("="*80)
    
    for fact in facts:
        print(f"\n[ID: {fact.id}] [{fact.category.value if fact.category else 'none'}]")
        print(f"Content: {fact.content}")
        print(f"Importance: {fact.importance_score:.2f}")
        if fact.conversation_id:
            print(f"From conversation: {fact.conversation_id}")
        print(f"Created: {fact.created_at}")
        print("-"*80)

def search_memory(args):
    """Search memory using async"""
    if not args.query:
        print("❌ Please provide --search QUERY")
        return
    
    async def do_search():
        memory = get_memory_manager()
        
        # Use default session for search
        session_id = "cli_search_session"
        
        results = await memory.retrieve_context(
            query=args.query,
            session_id=session_id,
            user_id=args.user,
            max_results=args.limit,
            include_recent=False,  # Don't include recent (we're searching)
            include_facts=True
        )
        
        if not results:
            print(f"📭 No results found for: {args.query}")
            return
        
        print(f"\n🔍 Search Results for: '{args.query}'")
        print("="*80)
        
        for i, result in enumerate(results, 1):
            source = "FACT" if result.session_id is None else "SESSION"
            print(f"\n{i}. [{source}] [Score: {result.relevance_score:.2f}]")
            print(f"   {result.content[:200]}...")
            if result.session_id:
                print(f"   Session: {result.session_id[:40]}...")
            print("-"*80)
    
    asyncio.run(do_search())

def test_isolation(args):
    """Test session isolation"""
    async def do_test():
        memory = get_memory_manager()
        
        print("\n🧪 Testing Session Isolation...")
        print("="*60)
        
        # Create two sessions
        sess1 = MemoryManager.generate_session_id("testuser", "desktop")
        sess2 = MemoryManager.generate_session_id("testuser", "pi")
        
        print(f"\nSession 1: {sess1[:40]}...")
        print(f"Session 2: {sess2[:40]}...")
        
        # Store in session 1
        print("\n1. Storing in Session 1: 'I like pizza'")
        await memory.process_conversation(
            user_input="I like pizza",
            assistant_response="Pizza is delicious!",
            session_id=sess1,
            user_id="testuser",
            intent_type="AI"
        )
        
        # Store in session 2
        print("2. Storing in Session 2: 'Turn on lights'")
        await memory.process_conversation(
            user_input="Turn on lights",
            assistant_response="Lights on!",
            session_id=sess2,
            user_id="testuser",
            intent_type="ACTION"
        )
        
        # Search from session 1
        print("\n3. Searching from Session 1 for 'pizza':")
        results1 = await memory.retrieve_context(
            query="pizza",
            session_id=sess1,
            user_id="testuser",
            max_results=5
        )
        print(f"   Found {len(results1)} results")
        for r in results1:
            source = "FACT" if r.session_id is None else "SESSION"
            print(f"   - [{source}] {r.content[:60]}...")
        
        # Search from session 2
        print("\n4. Searching from Session 2 for 'lights':")
        results2 = await memory.retrieve_context(
            query="lights",
            session_id=sess2,
            user_id="testuser",
            max_results=5
        )
        print(f"   Found {len(results2)} results")
        for r in results2:
            source = "FACT" if r.session_id is None else "SESSION"
            print(f"   - [{source}] {r.content[:60]}...")
        
        # Cross-session search
        print("\n5. Session 1 searching for 'lights' (should NOT find Session 2):")
        cross_results = await memory.retrieve_context(
            query="lights",
            session_id=sess1,
            user_id="testuser",
            max_results=5
        )
        print(f"   Found {len(cross_results)} results")
        for r in cross_results:
            source = "FACT" if r.session_id is None else "SESSION"
            print(f"   - [{source}] {r.content[:60]}...")
        
        print("\n✅ Test complete!")
    
    asyncio.run(do_test())

def cleanup_old(args):
    """Clean up old conversations"""
    store = SQLStore(args.db)
    
    days = args.days if hasattr(args, 'days') else 7
    cutoff = datetime.now() - timedelta(days=days)
    
    print(f"\n🗑️  Cleaning conversations older than {cutoff}")
    print("="*60)
    
    deleted = store.delete_old_conversations(cutoff_date=cutoff, keep_factual=True)
    
    print(f"Deleted {deleted} old conversations")
    print("✅ Cleanup complete!")


# ============================================
# RAG COMMANDS
# ============================================

def rag_stats(args):
    """Show RAG statistics"""
    try:
        indexer = get_indexer()
        stats = indexer.get_stats()
        
        print("\n" + "="*60)
        print("📄 RAG SYSTEM STATISTICS")
        print("="*60)
        print(f"Total Documents:     {stats.total_documents}")
        print(f"Total Chunks:        {stats.total_chunks}")
        print(f"Total Size:          {stats.total_size_bytes / 1024 / 1024:.2f} MB")
        
        if stats.documents_by_type:
            print("\nDocuments by Type:")
            for doc_type, count in stats.documents_by_type.items():
                print(f"  {doc_type.upper()}: {count}")
        
        if stats.last_indexed:
            print(f"\nLast Indexed:        {stats.last_indexed}")
        
        print("="*60)
    except Exception as e:
        print(f"❌ RAG stats error: {e}")

def rag_list(args):
    """List RAG documents"""
    try:
        indexer = get_indexer()
        conn = indexer._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, file_name, file_type, title, num_chunks, 
                   file_size_bytes, indexed_at
            FROM documents
            WHERE deleted_at IS NULL
            ORDER BY indexed_at DESC
            LIMIT ?
        """, (args.limit,))
        
        docs = cursor.fetchall()
        
        if not docs:
            print("📭 No documents found")
            return
        
        print(f"\n📄 Documents (showing {len(docs)}):")
        print("="*80)
        
        for doc in docs:
            print(f"\n[ID: {doc['id']}] {doc['file_name']}")
            print(f"  Type: {doc['file_type'].upper()}")
            print(f"  Title: {doc['title']}")
            print(f"  Chunks: {doc['num_chunks']}")
            print(f"  Size: {doc['file_size_bytes'] / 1024:.1f} KB")
            print(f"  Indexed: {doc['indexed_at']}")
            print("-"*80)
    except Exception as e:
        print(f"❌ RAG list error: {e}")

def rag_search(args):
    """Search RAG documents"""
    if not args.query:
        print("❌ Please provide --rag-search QUERY")
        return
    
    async def do_search():
        try:
            retriever = get_retriever()
            results = await retriever.retrieve(
                query=args.query,
                top_k=args.limit
            )
            
            if not results:
                print(f"📭 No documents found for: {args.query}")
                return
            
            print(f"\n🔍 Document Search Results for: '{args.query}'")
            print("="*80)
            
            for i, result in enumerate(results, 1):
                print(f"\n{i}. {result.document_name} [Score: {result.relevance_score:.2f}]")
                print(f"   Chunk {result.chunk_index}")
                print(f"   {result.content[:200]}...")
                print(f"   Path: {result.source_path}")
                print("-"*80)
        except Exception as e:
            print(f"❌ RAG search error: {e}")
    
    asyncio.run(do_search())

def rag_index(args):
    """Index document or directory"""
    if not args.path:
        print("❌ Please provide --rag-index PATH")
        return
    
    try:
        indexer = get_indexer()
        path = Path(args.path)
        
        if not path.exists():
            print(f"❌ Path not found: {args.path}")
            return
        
        print(f"\n📥 Indexing: {args.path}")
        print("="*60)
        
        if path.is_file():
            # Index single file
            doc = indexer.index_document(str(path), user_id=args.user)
            print(f"✅ Indexed: {doc.file_name}")
            print(f"   Chunks: {doc.num_chunks}")
        
        elif path.is_dir():
            # Index directory
            docs = indexer.index_directory(
                str(path),
                recursive=args.recursive,
                user_id=args.user
            )
            print(f"✅ Indexed {len(docs)} documents")
            for doc in docs:
                print(f"   - {doc.file_name} ({doc.num_chunks} chunks)")
        
        print("="*60)
    except Exception as e:
        print(f"❌ Indexing error: {e}")


# ============================================
# MAIN
# ============================================

def main():
    parser = argparse.ArgumentParser(
        description="Memory & RAG CLI Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    # Global options
    parser.add_argument('--db', default='data/memory.db', help='Database path')
    parser.add_argument('--user', default='default_user', help='User ID')
    parser.add_argument('--limit', type=int, default=10, help='Result limit')
    
    # Memory commands
    parser.add_argument('--stats', action='store_true', help='Show all statistics')
    parser.add_argument('--list-facts', action='store_true', help='List facts')
    parser.add_argument('--list-convs', action='store_true', help='List conversations')
    parser.add_argument('--list-sessions', action='store_true', help='List sessions')
    parser.add_argument('--session-id', type=str, help='View specific session')
    parser.add_argument('--category', type=str, help='Filter by category')
    parser.add_argument('--search', type=str, metavar='QUERY', help='Search memory')
    parser.add_argument('--test-isolation', action='store_true', help='Test session isolation')
    parser.add_argument('--cleanup', type=int, metavar='DAYS', help='Clean old conversations')
    
    # RAG commands
    parser.add_argument('--rag-stats', action='store_true', help='RAG statistics')
    parser.add_argument('--rag-list', action='store_true', help='List documents')
    parser.add_argument('--rag-search', type=str, metavar='QUERY', help='Search documents')
    parser.add_argument('--rag-index', type=str, metavar='PATH', help='Index document/directory')
    parser.add_argument('--recursive', action='store_true', help='Recursive directory indexing')
    parser.add_argument('--path', type=str, help='Path for indexing')
    
    # Maintenance
    parser.add_argument('--clear-test', action='store_true', help='Clear test database')
    
    args = parser.parse_args()
    
    # Handle --rag-index special case
    if args.rag_index:
        args.path = args.rag_index
        rag_index(args)
        return
    
    # Execute commands
    if args.stats:
        show_all_stats(args)
    elif args.list_sessions:
        list_sessions(args)
    elif args.session_id:
        view_session(args)
    elif args.list_facts:
        list_facts(args)
    elif args.list_convs:
        # Legacy support
        view_session(args)
    elif args.search:
        args.query = args.search
        search_memory(args)
    elif args.test_isolation:
        test_isolation(args)
    elif args.cleanup:
        args.days = args.cleanup
        cleanup_old(args)
    elif args.rag_stats:
        rag_stats(args)
    elif args.rag_list:
        rag_list(args)
    elif args.rag_search:
        args.query = args.rag_search
        rag_search(args)
    elif args.clear_test:
        import os
        if os.path.exists("data/test_memory.db"):
            os.remove("data/test_memory.db")
            print("🗑️  Removed test database")
    else:
        parser.print_help()
        print("\n💡 Examples:")
        print("  python memory_cli.py --stats")
        print("  python memory_cli.py --list-sessions")
        print("  python memory_cli.py --session-id SESSION_ID")
        print("  python memory_cli.py --search 'birthday'")
        print("  python memory_cli.py --test-isolation")
        print("  python memory_cli.py --rag-stats")
        print("  python memory_cli.py --rag-index documents/")
        print("  python memory_cli.py --rag-search 'AI models'")

if __name__ == "__main__":
    main()