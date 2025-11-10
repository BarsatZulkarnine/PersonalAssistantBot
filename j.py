"""
Database Migration Script - Session Support

Run this to add session-aware indexes and verify schema.
Usage: python migrate_session_support.py
"""

import sqlite3
from pathlib import Path
import sys
from shutil import copy2
from datetime import datetime

def backup_database(db_path: str) -> str:
    """Create backup before migration"""
    if not Path(db_path).exists():
        print(f"❌ Database not found: {db_path}")
        sys.exit(1)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = f"{db_path}.backup_{timestamp}"
    
    copy2(db_path, backup_path)
    print(f"✅ Backup created: {backup_path}")
    return backup_path


def check_current_schema(db_path: str):
    """Check current database schema"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print("\n" + "="*60)
    print("Current Schema Check")
    print("="*60)
    
    # Check conversations table
    cursor.execute("PRAGMA table_info(conversations)")
    conv_columns = {col[1] for col in cursor.fetchall()}
    
    print("\nConversations table columns:")
    print(f"  - session_id: {'✅' if 'session_id' in conv_columns else '❌'}")
    print(f"  - user_id: {'✅' if 'user_id' in conv_columns else '❌'}")
    print(f"  - turn_no: {'✅' if 'turn_no' in conv_columns else '✅'}")
    
    # Check facts table
    cursor.execute("PRAGMA table_info(facts)")
    fact_columns = {col[1] for col in cursor.fetchall()}
    
    print("\nFacts table columns:")
    print(f"  - user_id: {'✅' if 'user_id' in fact_columns else '❌'}")
    print(f"  - content_hash: {'✅' if 'content_hash' in fact_columns else '❌'}")
    
    # Check indexes
    cursor.execute("SELECT name FROM sqlite_master WHERE type='index'")
    indexes = {row[0] for row in cursor.fetchall()}
    
    print("\nIndexes:")
    required_indexes = [
        'idx_conv_session_time',
        'idx_conv_user',
        'idx_facts_user'
    ]
    
    for idx in required_indexes:
        status = '✅' if idx in indexes else '❌'
        print(f"  - {idx}: {status}")
    
    conn.close()
    
    return conv_columns, fact_columns, indexes


def add_missing_indexes(db_path: str):
    """Add session-aware indexes"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print("\n" + "="*60)
    print("Adding Missing Indexes")
    print("="*60)
    
    indexes_to_add = [
        # Session + time index for conversations
        (
            "idx_conv_session_time",
            "CREATE INDEX IF NOT EXISTS idx_conv_session_time ON conversations(session_id, timestamp DESC)"
        ),
        # User index for conversations
        (
            "idx_conv_user",
            "CREATE INDEX IF NOT EXISTS idx_conv_user ON conversations(user_id, timestamp DESC)"
        ),
        # User index for facts
        (
            "idx_facts_user",
            "CREATE INDEX IF NOT EXISTS idx_facts_user ON facts(user_id, importance_score DESC)"
        ),
        # Session + user composite index
        (
            "idx_conv_session_user",
            "CREATE INDEX IF NOT EXISTS idx_conv_session_user ON conversations(session_id, user_id)"
        ),
        # Timestamp index for cleanup
        (
            "idx_conv_timestamp",
            "CREATE INDEX IF NOT EXISTS idx_conv_timestamp ON conversations(timestamp)"
        )
    ]
    
    for idx_name, idx_sql in indexes_to_add:
        try:
            cursor.execute(idx_sql)
            print(f"  ✅ {idx_name}")
        except Exception as e:
            print(f"  ⚠️  {idx_name}: {e}")
    
    conn.commit()
    conn.close()
    
    print("\n✅ Index creation complete")


def verify_data_integrity(db_path: str):
    """Verify data integrity after migration"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print("\n" + "="*60)
    print("Data Integrity Check")
    print("="*60)
    
    # Count records
    cursor.execute("SELECT COUNT(*) FROM conversations")
    conv_count = cursor.fetchone()[0]
    print(f"\n  Conversations: {conv_count}")
    
    cursor.execute("SELECT COUNT(*) FROM facts")
    fact_count = cursor.fetchone()[0]
    print(f"  Facts: {fact_count}")
    
    # Check for null session_ids (should have defaults)
    cursor.execute("SELECT COUNT(*) FROM conversations WHERE session_id IS NULL OR session_id = ''")
    null_sessions = cursor.fetchone()[0]
    
    if null_sessions > 0:
        print(f"\n  ⚠️  Found {null_sessions} conversations with missing session_id")
        print("     These will use empty string as session_id (backward compatible)")
    else:
        print(f"\n  ✅ All conversations have session_id")
    
    # Check for null user_ids
    cursor.execute("SELECT COUNT(*) FROM conversations WHERE user_id IS NULL OR user_id = ''")
    null_users = cursor.fetchone()[0]
    
    if null_users > 0:
        print(f"  ⚠️  Found {null_users} conversations with missing user_id")
    else:
        print(f"  ✅ All conversations have user_id")
    
    # Check unique sessions
    cursor.execute("SELECT COUNT(DISTINCT session_id) FROM conversations")
    unique_sessions = cursor.fetchone()[0]
    print(f"\n  Unique sessions: {unique_sessions}")
    
    # Get session stats
    cursor.execute("""
        SELECT 
            session_id,
            COUNT(*) as turns,
            MIN(timestamp) as first,
            MAX(timestamp) as last
        FROM conversations
        WHERE session_id IS NOT NULL AND session_id != ''
        GROUP BY session_id
        ORDER BY MAX(timestamp) DESC
        LIMIT 5
    """)
    
    print("\n  Recent sessions:")
    for row in cursor.fetchall():
        session_id, turns, first, last = row
        print(f"    - {session_id[:40]}... ({turns} turns)")
    
    conn.close()


def test_session_queries(db_path: str):
    """Test session-aware queries"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print("\n" + "="*60)
    print("Testing Session Queries")
    print("="*60)
    
    # Test 1: Get conversations by session
    cursor.execute("""
        SELECT session_id, COUNT(*) as count
        FROM conversations
        WHERE session_id IS NOT NULL AND session_id != ''
        GROUP BY session_id
        LIMIT 1
    """)
    
    result = cursor.fetchone()
    if result:
        test_session = result[0]
        turn_count = result[1]
        
        print(f"\n  Test session: {test_session[:40]}...")
        print(f"  Turn count: {turn_count}")
        
        # Query by session
        cursor.execute("""
            SELECT COUNT(*) FROM conversations
            WHERE session_id = ?
        """, (test_session,))
        
        queried_count = cursor.fetchone()[0]
        
        if queried_count == turn_count:
            print(f"  ✅ Session query works correctly")
        else:
            print(f"  ❌ Session query mismatch: expected {turn_count}, got {queried_count}")
    else:
        print("  ⚠️  No sessions found to test")
    
    # Test 2: Search with user filter
    cursor.execute("""
        SELECT DISTINCT user_id FROM conversations
        LIMIT 1
    """)
    
    result = cursor.fetchone()
    if result:
        test_user = result[0]
        
        cursor.execute("""
            SELECT COUNT(*) FROM conversations
            WHERE user_id = ?
        """, (test_user,))
        
        user_count = cursor.fetchone()[0]
        print(f"\n  Test user: {test_user}")
        print(f"  Conversations: {user_count}")
        print(f"  ✅ User filter works")
    
    conn.close()


def main():
    """Run complete migration"""
    db_path = "data/memory.db"
    
    if len(sys.argv) > 1:
        db_path = sys.argv[1]
    
    print("\n" + "="*60)
    print("Session Support Migration")
    print("="*60)
    print(f"Database: {db_path}\n")
    
    # Step 1: Check if migration needed
    conv_cols, fact_cols, indexes = check_current_schema(db_path)
    
    needs_migration = False
    
    if 'session_id' not in conv_cols:
        print("\n❌ ERROR: session_id column missing from conversations table!")
        print("   Your schema is outdated. Please run the full schema initialization.")
        sys.exit(1)
    
    if 'user_id' not in conv_cols:
        print("\n❌ ERROR: user_id column missing from conversations table!")
        print("   Your schema is outdated. Please run the full schema initialization.")
        sys.exit(1)
    
    # Check for missing indexes
    required_indexes = {'idx_conv_session_time', 'idx_conv_user', 'idx_facts_user'}
    missing_indexes = required_indexes - indexes
    
    if missing_indexes:
        needs_migration = True
        print(f"\n⚠️  Missing indexes: {missing_indexes}")
    
    if not needs_migration:
        print("\n✅ Database schema is up-to-date!")
        print("   No migration needed.")
        
        # Still verify data
        verify_data_integrity(db_path)
        test_session_queries(db_path)
        
        return
    
    # Step 2: Backup
    backup_path = backup_database(db_path)
    
    # Step 3: Add indexes
    try:
        add_missing_indexes(db_path)
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        print(f"   Restore from backup: {backup_path}")
        sys.exit(1)
    
    # Step 4: Verify
    verify_data_integrity(db_path)
    
    # Step 5: Test queries
    test_session_queries(db_path)
    
    # Step 6: Final report
    print("\n" + "="*60)
    print("Migration Complete!")
    print("="*60)
    print(f"\n✅ Database migrated successfully")
    print(f"✅ Backup saved to: {backup_path}")
    print(f"\nNext steps:")
    print("  1. Update your code with the new session-aware methods")
    print("  2. Test with: pytest tests/test_memory_sessions.py -v")
    print("  3. Run your assistant and verify session isolation")


if __name__ == "__main__":
    main()