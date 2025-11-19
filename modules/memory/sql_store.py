"""
Memory System - SQLite Storage

Handles all SQL operations with proper indexing, FTS5, and provenance tracking.
"""

import sqlite3
import hashlib
import json
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime

from modules.memory.base import (
    MemoryStore, Conversation, Fact, Action, Preference,
    FactCategory, RetrievalResult
)
from utils.logger import get_logger

logger = get_logger('memory.sql_store')

class SQLStore(MemoryStore):
    """SQLite storage implementation with FTS5 and full provenance"""
    
    def __init__(self, db_path: str = "data/memory.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn: Optional[sqlite3.Connection] = None
        logger.info(f"SQLStore initialized (path={self.db_path})")
    
    def _get_connection(self) -> sqlite3.Connection:
        """Get database connection"""
        if self.conn is None:
            self.conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
            self.conn.row_factory = sqlite3.Row
            # Enable foreign keys
            self.conn.execute("PRAGMA foreign_keys = ON")
        return self.conn
    
    def initialize(self):
        """Create all tables and indexes"""
        logger.info("Initializing database schema...")
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # 1. Conversations table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                user_id TEXT DEFAULT 'default_user',
                turn_no INTEGER NOT NULL,
                user_input TEXT NOT NULL,
                assistant_response TEXT NOT NULL,
                intent_type TEXT,
                duration_ms REAL,
                prompt_tokens INTEGER DEFAULT 0,
                completion_tokens INTEGER DEFAULT 0,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                deleted_at DATETIME NULL,
                purged_at DATETIME NULL,
                
                UNIQUE(session_id, turn_no)
            )
        """)
        
        # Indexes for conversations
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_conv_session_time 
            ON conversations(session_id, timestamp DESC)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_conv_user 
            ON conversations(user_id, timestamp DESC)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_conv_deleted 
            ON conversations(deleted_at) WHERE deleted_at IS NULL
        """)
        
        # 2. Facts table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS facts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL DEFAULT 'default_user',
                content TEXT NOT NULL,
                content_hash TEXT NOT NULL,
                category TEXT,
                importance_score REAL DEFAULT 0.5,
                
                conversation_id INTEGER,
                message_id TEXT,
                source_doc_id TEXT,
                source_span TEXT,
                
                embedding_id TEXT,
                
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                deleted_at DATETIME NULL,
                purged_at DATETIME NULL,
                
                FOREIGN KEY (conversation_id) REFERENCES conversations(id),
                UNIQUE(user_id, content_hash)
            )
        """)
        
        # Indexes for facts
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_facts_user 
            ON facts(user_id, importance_score DESC)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_facts_category 
            ON facts(category, created_at DESC)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_facts_conversation 
            ON facts(conversation_id)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_facts_hash 
            ON facts(content_hash)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_facts_deleted 
            ON facts(deleted_at) WHERE deleted_at IS NULL
        """)
        
        # 3. FTS5 table for facts
        cursor.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS facts_fts USING fts5(
                content,
                content='facts',
                content_rowid='id'
            )
        """)
        
        # Triggers to keep FTS in sync
        cursor.execute("""
            CREATE TRIGGER IF NOT EXISTS facts_fts_insert 
            AFTER INSERT ON facts BEGIN
                INSERT INTO facts_fts(rowid, content) VALUES (new.id, new.content);
            END
        """)
        cursor.execute("""
            CREATE TRIGGER IF NOT EXISTS facts_fts_delete 
            AFTER DELETE ON facts BEGIN
                DELETE FROM facts_fts WHERE rowid = old.id;
            END
        """)
        cursor.execute("""
            CREATE TRIGGER IF NOT EXISTS facts_fts_update 
            AFTER UPDATE ON facts BEGIN
                UPDATE facts_fts SET content = new.content WHERE rowid = new.id;
            END
        """)
        
        # 4. Preferences table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS preferences (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL DEFAULT 'default_user',
                key TEXT NOT NULL,
                value TEXT NOT NULL,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                
                UNIQUE(user_id, key)
            )
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_pref_user ON preferences(user_id)
        """)
        
        # 5. Actions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS actions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL DEFAULT 'default_user',
                conversation_id INTEGER,
                action_name TEXT NOT NULL,
                params TEXT,
                result TEXT,
                success BOOLEAN,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                
                FOREIGN KEY (conversation_id) REFERENCES conversations(id)
            )
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_actions_user 
            ON actions(user_id, timestamp DESC)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_actions_name 
            ON actions(action_name, timestamp DESC)
        """)
        
        # 6. Memory metadata table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS memory_metadata (
                key TEXT PRIMARY KEY,
                value TEXT,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Initialize metadata
        cursor.execute("""
            INSERT OR IGNORE INTO memory_metadata (key, value) VALUES 
                ('total_embeddings', '0'),
                ('total_cost_usd', '0.0'),
                ('last_consolidation', NULL)
        """)
        
        conn.commit()
        logger.info("Database schema initialized successfully")
    
    def store_conversation(self, conversation: Conversation) -> int:
        """Store a conversation and return its ID"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO conversations (
                session_id, user_id, turn_no, user_input, assistant_response,
                intent_type, duration_ms, prompt_tokens, completion_tokens, timestamp
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            conversation.session_id,
            conversation.user_id,
            conversation.turn_no,
            conversation.user_input,
            conversation.assistant_response,
            conversation.intent_type,
            conversation.duration_ms,
            conversation.prompt_tokens,
            conversation.completion_tokens,
            conversation.timestamp or datetime.now()
        ))
        
        conn.commit()
        conv_id = cursor.lastrowid
        
        logger.debug(f"Stored conversation {conv_id}")
        return conv_id
    
    def store_fact(self, fact: Fact) -> int:
        """Store a fact with deduplication"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Generate content hash if not provided
        if not fact.content_hash:
            fact.content_hash = self._hash_content(fact.content)
        
        # Check for existing fact (deduplication)
        cursor.execute("""
            SELECT id FROM facts 
            WHERE user_id = ? AND content_hash = ? AND deleted_at IS NULL
        """, (fact.user_id, fact.content_hash))
        
        existing = cursor.fetchone()
        if existing:
            logger.debug(f"Fact already exists (id={existing['id']}), skipping duplicate")
            return existing['id']
        
        # Insert new fact
        cursor.execute("""
            INSERT INTO facts (
                user_id, content, content_hash, category, importance_score,
                conversation_id, message_id, source_doc_id, source_span,
                embedding_id, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            fact.user_id,
            fact.content,
            fact.content_hash,
            fact.category.value if fact.category else None,
            fact.importance_score,
            fact.conversation_id,
            fact.message_id,
            fact.source_doc_id,
            json.dumps(fact.source_span) if fact.source_span else None,
            fact.embedding_id,
            fact.created_at or datetime.now(),
            fact.updated_at or datetime.now()
        ))
        
        conn.commit()
        fact_id = cursor.lastrowid
        
        logger.debug(f"Stored fact {fact_id}: {fact.content[:50]}...")
        return fact_id
    
    def get_session_turn_count(self, session_id: str) -> int:
        """
        Get current turn count for a session.
        
        Args:
            session_id: Session identifier
            
        Returns:
            Number of turns in this session
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT COUNT(*) as count FROM conversations WHERE session_id = ?",
            (session_id,)
        )
        
        return cursor.fetchone()['count']

    def search_conversations(
        self,
        query: str,
        user_id: str,
        session_id: str,
        limit: int = 5
    ) -> List[RetrievalResult]:
        """Search conversations in a specific session using FTS."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Clean query for FTS
        cleaned_query = self._clean_fts_query(query)
        if not cleaned_query:
            return []
        
        # Search in conversations (session-filtered)
        cursor.execute("""
            SELECT 
                c.id,
                c.user_input,
                c.assistant_response,
                c.session_id,
                c.timestamp
            FROM conversations c
            WHERE (c.user_input LIKE ? OR c.assistant_response LIKE ?)
                AND c.user_id = ?
                AND c.session_id = ?
                AND c.deleted_at IS NULL
            ORDER BY c.timestamp DESC
            LIMIT ?
        """, (f'%{query}%', f'%{query}%', user_id, session_id, limit))
        
        results = []
        for row in cursor.fetchall():
            results.append(RetrievalResult(
                content=f"User: {row['user_input']}\nAssistant: {row['assistant_response']}",
                relevance_score=0.7,
                conversation_id=row['id'],
                session_id=row['session_id'],
                created_at=datetime.fromisoformat(row['timestamp']) if row['timestamp'] else None,
                importance=0.5,
                source='sql_conversation'
            ))
        
        return results

    def delete_old_conversations(
        self,
        cutoff_date: datetime,
        keep_factual: bool = True
    ) -> int:
        """
        Delete old conversations.
        
        ✅ NEW: Cleanup old ephemeral conversations
        
        Args:
            cutoff_date: Delete conversations before this date
            keep_factual: Keep conversations that have associated facts
            
        Returns:
            Number of deleted conversations
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        if keep_factual:
            # Delete only ephemeral/conversational (no associated facts)
            cursor.execute("""
                DELETE FROM conversations
                WHERE timestamp < ?
                    AND deleted_at IS NULL
                    AND id NOT IN (
                        SELECT DISTINCT conversation_id 
                        FROM facts
                        WHERE conversation_id IS NOT NULL
                    )
            """, (cutoff_date,))
        else:
            # Delete all old conversations
            cursor.execute("""
                DELETE FROM conversations
                WHERE timestamp < ?
                    AND deleted_at IS NULL
            """, (cutoff_date,))
        
        deleted = cursor.rowcount
        conn.commit()
        
        logger.info(f"Deleted {deleted} old conversations")
        return deleted

    def get_recent_conversations_from_session(
        self,
        session_id: str,
        user_id: str = "default_user",
        limit: int = 3
    ) -> List[RetrievalResult]:
        """
        Get recent conversations from a specific session.
        
        ✅ FIXED: Returns RetrievalResult with created_at
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                id,
                user_input,
                assistant_response,
                session_id,
                timestamp as created_at
            FROM conversations
            WHERE session_id = ?
                AND user_id = ?
                AND deleted_at IS NULL
            ORDER BY timestamp DESC
            LIMIT ?
        """, (session_id, user_id, limit))
        
        results = []
        for row in cursor.fetchall():
            results.append(RetrievalResult(
                content=f"User: {row['user_input']}\nAssistant: {row['assistant_response']}",
                relevance_score=0.8,
                conversation_id=row['id'],
                session_id=row['session_id'],
                created_at=datetime.fromisoformat(row['created_at']) if row['created_at'] else None,
                source='recent'
            ))
        
        logger.debug(f"[{session_id[:20]}...] Retrieved {len(results)} recent conversations")
        return results

    def get_all_sessions_for_user(
        self,
        user_id: str = "default_user",
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Get all sessions for a user.
        
        ✅ NEW: Session management helper
        
        Args:
            user_id: User identifier
            limit: Max sessions to return
            
        Returns:
            List of session info dicts
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                session_id,
                COUNT(*) as turn_count,
                MIN(timestamp) as first_turn,
                MAX(timestamp) as last_turn,
                SUM(prompt_tokens + completion_tokens) as total_tokens
            FROM conversations
            WHERE user_id = ?
                AND deleted_at IS NULL
            GROUP BY session_id
            ORDER BY MAX(timestamp) DESC
            LIMIT ?
        """, (user_id, limit))
        
        sessions = []
        for row in cursor.fetchall():
            sessions.append({
                'session_id': row[0],
                'turn_count': row[1],
                'first_turn': row[2],
                'last_turn': row[3],
                'total_tokens': row[4] or 0
            })
        
        return sessions
    
    def get_conversations(
        self,
        user_id: str = "default_user",
        session_id: Optional[str] = None,
        limit: int = 10
    ) -> List[Conversation]:
        """Retrieve conversations"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        query = """
            SELECT * FROM conversations 
            WHERE user_id = ? AND deleted_at IS NULL
        """
        params = [user_id]
        
        if session_id:
            query += " AND session_id = ?"
            params.append(session_id)
        
        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        conversations = []
        for row in rows:
            conversations.append(self._row_to_conversation(row))
        
        logger.debug(f"Retrieved {len(conversations)} conversations")
        return conversations
    
    def get_facts(
        self,
        user_id: str = "default_user",
        category: Optional[FactCategory] = None,
        limit: int = 10
    ) -> List[Fact]:
        """Retrieve facts"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        query = """
            SELECT * FROM facts 
            WHERE user_id = ? AND deleted_at IS NULL
        """
        params = [user_id]
        
        if category:
            query += " AND category = ?"
            params.append(category.value)
        
        query += " ORDER BY importance_score DESC, created_at DESC LIMIT ?"
        params.append(limit)
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        facts = []
        for row in rows:
            facts.append(self._row_to_fact(row))
        
        logger.debug(f"Retrieved {len(facts)} facts")
        return facts
    
    def search_facts(
        self,
        query: str,
        user_id: str = "default_user",
        limit: int = 5
    ) -> List[RetrievalResult]:
        """
        Search facts using FTS5.
        
        ✅ UPDATED: Now includes session_id (None for facts = shared)
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cleaned_query = self._clean_fts_query(query)
        if not cleaned_query:
            return []
        
        cursor.execute("""
            SELECT 
                f.*,
                bm25(facts_fts) as bm25_score,
                julianday('now') - julianday(f.created_at) as days_old
            FROM facts f
            JOIN facts_fts ON f.id = facts_fts.rowid
            WHERE facts_fts MATCH ?
            AND f.deleted_at IS NULL
            AND f.user_id = ?
            ORDER BY 
                bm25_score DESC,
                f.importance_score DESC,
                days_old ASC
            LIMIT ?
        """, (cleaned_query, user_id, limit))
        
        rows = cursor.fetchall()
        
        results = []
        for row in rows:
            results.append(RetrievalResult(
                content=row['content'],
                relevance_score=abs(row['bm25_score']) if row['bm25_score'] else 0.0,
                fact_id=row['id'],
                conversation_id=row['conversation_id'],
                session_id=None,  # ✅ Facts are session-agnostic (shared)
                category=row['category'],
                importance=row['importance_score'],
                created_at=datetime.fromisoformat(row['created_at']) if row['created_at'] else None,
                source='fts'
            ))
        
        logger.debug(f"FTS search found {len(results)} results for: {query}")
        return results

    def get_fact_by_id(self, fact_id: int) -> Optional[Fact]:
        """Get a specific fact by ID"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM facts WHERE id = ?", (fact_id,))
        row = cursor.fetchone()
        
        if row:
            return self._row_to_fact(row)
        return None
    
    def update_fact_embedding(self, fact_id: int, embedding_id: str):
        """Update the embedding_id for a fact"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE facts 
            SET embedding_id = ?, updated_at = CURRENT_TIMESTAMP 
            WHERE id = ?
        """, (embedding_id, fact_id))
        
        conn.commit()
        logger.debug(f"Updated embedding for fact {fact_id}")
    
    def soft_delete_fact(self, fact_id: int):
        """Soft delete a fact"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE facts 
            SET deleted_at = CURRENT_TIMESTAMP 
            WHERE id = ?
        """, (fact_id,))
        
        conn.commit()
        logger.info(f"Soft deleted fact {fact_id}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get database statistics"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) as count FROM conversations WHERE deleted_at IS NULL")
        conv_count = cursor.fetchone()['count']
        
        cursor.execute("SELECT COUNT(*) as count FROM facts WHERE deleted_at IS NULL")
        fact_count = cursor.fetchone()['count']
        
        cursor.execute("SELECT SUM(prompt_tokens + completion_tokens) as total FROM conversations")
        total_tokens = cursor.fetchone()['total'] or 0
        
        return {
            'total_conversations': conv_count,
            'total_facts': fact_count,
            'total_tokens': total_tokens,
            'estimated_cost_usd': total_tokens * 0.000001  # Rough estimate
        }
    
    # Helper methods
    
    def _hash_content(self, content: str) -> str:
        """Generate SHA256 hash of content for deduplication"""
        normalized = content.lower().strip()
        return hashlib.sha256(normalized.encode()).hexdigest()

    def _clean_fts_query(self, query: str) -> str:
        """Clean and escape FTS5 query string"""
        import re
        
        # If query is empty or just whitespace, return empty
        if not query or not query.strip():
            return ""
        
        # Remove or replace problematic characters
        # FTS5 special chars: + - ( ) " * AND OR NOT NEAR
        query = re.sub(r'[+\-!?.,;:\'"`(){}[\]<>|/\\&^%$#@=]', ' ', query)
        
        # Normalize whitespace
        query = ' '.join(query.split())
        
        # If query is empty after cleaning, return empty
        if not query:
            return ""
        
        # Split into terms
        terms = query.split()
        
        # Filter out FTS5 reserved words and short terms
        fts5_reserved = {'and', 'or', 'not', 'near'}
        valid_terms = [
            term for term in terms 
            if term.lower() not in fts5_reserved and len(term) > 1
        ]
        
        # If no valid terms, return empty
        if not valid_terms:
            return ""
        
        # Add fuzzy matching for longer terms only
        cleaned_terms = []
        for term in valid_terms:
            if len(term) > 2:  # Only add wildcard for terms with 3+ chars
                cleaned_terms.append(f'{term}*')
            else:
                cleaned_terms.append(term)
        
        # Join with OR for better matching
        return ' OR '.join(cleaned_terms)
    def _row_to_conversation(self, row: sqlite3.Row) -> Conversation:
        """Convert DB row to Conversation object"""
        return Conversation(
            id=row['id'],
            session_id=row['session_id'],
            user_id=row['user_id'],
            turn_no=row['turn_no'],
            user_input=row['user_input'],
            assistant_response=row['assistant_response'],
            intent_type=row['intent_type'],
            duration_ms=row['duration_ms'],
            prompt_tokens=row['prompt_tokens'],
            completion_tokens=row['completion_tokens'],
            timestamp=datetime.fromisoformat(row['timestamp']) if row['timestamp'] else None,
            deleted_at=datetime.fromisoformat(row['deleted_at']) if row['deleted_at'] else None,
            purged_at=datetime.fromisoformat(row['purged_at']) if row['purged_at'] else None
        )
    
    def _row_to_fact(self, row: sqlite3.Row) -> Fact:
        """Convert DB row to Fact object"""
        return Fact(
            id=row['id'],
            user_id=row['user_id'],
            content=row['content'],
            content_hash=row['content_hash'],
            category=FactCategory(row['category']) if row['category'] else None,
            importance_score=row['importance_score'],
            conversation_id=row['conversation_id'],
            message_id=row['message_id'],
            source_doc_id=row['source_doc_id'],
            source_span=json.loads(row['source_span']) if row['source_span'] else None,
            embedding_id=row['embedding_id'],
            created_at=datetime.fromisoformat(row['created_at']) if row['created_at'] else None,
            updated_at=datetime.fromisoformat(row['updated_at']) if row['updated_at'] else None,
            deleted_at=datetime.fromisoformat(row['deleted_at']) if row['deleted_at'] else None,
            purged_at=datetime.fromisoformat(row['purged_at']) if row['purged_at'] else None
        )
    
    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
            self.conn = None
            logger.info("Database connection closed")
    
    def __del__(self):
        """Cleanup on deletion"""
        self.close()


# Convenience functions

def get_sql_store() -> SQLStore:
    """Get or create global SQL store instance"""
    global _sql_store
    if '_sql_store' not in globals():
        _sql_store = SQLStore()
        _sql_store.initialize()
    return _sql_store