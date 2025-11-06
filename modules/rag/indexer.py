"""
Document Indexer - Process and Store Documents

Handles document loading, chunking, and indexing for RAG retrieval.
"""

import sqlite3
from pathlib import Path
from typing import Optional, List
from datetime import datetime

from modules.rag.base import Document, DocumentChunk, IndexStats
from modules.rag.loaders import get_loader_registry
from modules.rag.chunker import get_chunker
from utils.logger import get_logger

logger = get_logger('rag.indexer')

class DocumentIndexer:
    """
    Indexes documents for RAG retrieval.
    
    Process:
    1. Load document (PDF/DOCX/TXT)
    2. Chunk text
    3. Store in SQL
    4. Generate embeddings (via vector store)
    """
    
    def __init__(self, db_path: str = "data/rag_documents.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        self.conn: Optional[sqlite3.Connection] = None
        self.loader_registry = get_loader_registry()
        self.chunker = get_chunker()
        
        self._initialize_db()
        
        logger.info(f"DocumentIndexer initialized (db={self.db_path})")
    
    def _get_connection(self) -> sqlite3.Connection:
        """Get database connection"""
        if self.conn is None:
            self.conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
            self.conn.row_factory = sqlite3.Row
        return self.conn
    
    def _initialize_db(self):
        """Create database schema"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Documents table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_path TEXT NOT NULL UNIQUE,
                file_name TEXT NOT NULL,
                file_type TEXT NOT NULL,
                title TEXT,
                content TEXT NOT NULL,
                metadata TEXT,
                
                user_id TEXT DEFAULT 'default_user',
                tags TEXT,
                
                indexed_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                file_size_bytes INTEGER,
                num_chunks INTEGER DEFAULT 0,
                
                deleted_at DATETIME NULL
            )
        """)
        
        # Indexes for documents
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_docs_user 
            ON documents(user_id, indexed_at DESC)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_docs_type 
            ON documents(file_type, indexed_at DESC)
        """)
        
        # Chunks table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS document_chunks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                document_id INTEGER NOT NULL,
                content TEXT NOT NULL,
                chunk_index INTEGER NOT NULL,
                
                start_char INTEGER,
                end_char INTEGER,
                
                metadata TEXT,
                embedding_id TEXT,
                
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                
                FOREIGN KEY (document_id) REFERENCES documents(id),
                UNIQUE(document_id, chunk_index)
            )
        """)
        
        # Indexes for chunks
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_chunks_doc 
            ON document_chunks(document_id, chunk_index)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_chunks_embedding 
            ON document_chunks(embedding_id)
        """)
        
        # FTS5 for document search
        cursor.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS documents_fts USING fts5(
                title,
                content,
                content='documents',
                content_rowid='id'
            )
        """)
        
        # Triggers for FTS
        cursor.execute("""
            CREATE TRIGGER IF NOT EXISTS documents_fts_insert 
            AFTER INSERT ON documents BEGIN
                INSERT INTO documents_fts(rowid, title, content) 
                VALUES (new.id, new.title, new.content);
            END
        """)
        
        cursor.execute("""
            CREATE TRIGGER IF NOT EXISTS documents_fts_delete 
            AFTER DELETE ON documents BEGIN
                DELETE FROM documents_fts WHERE rowid = old.id;
            END
        """)
        
        cursor.execute("""
            CREATE TRIGGER IF NOT EXISTS documents_fts_update 
            AFTER UPDATE ON documents BEGIN
                UPDATE documents_fts 
                SET title = new.title, content = new.content 
                WHERE rowid = new.id;
            END
        """)
        
        conn.commit()
        logger.info("✅ Database schema initialized")
    
    def index_document(
        self,
        file_path: str,
        user_id: str = "default_user",
        tags: Optional[List[str]] = None
    ) -> Document:
        """
        Index a document.
        
        Args:
            file_path: Path to document
            user_id: User ID
            tags: Optional tags
            
        Returns:
            Document object with ID
        """
        path = Path(file_path)
        
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        # Check if already indexed
        existing = self._get_document_by_path(str(path.absolute()))
        if existing:
            logger.info(f"Document already indexed: {path.name} (id={existing.id})")
            return existing
        
        # Load document
        logger.info(f"Loading document: {path.name}")
        document = self.loader_registry.load_document(str(path))
        
        # Set user info
        document.user_id = user_id
        document.tags = tags or []
        document.indexed_at = datetime.now()
        
        # Chunk the document
        logger.info(f"Chunking document...")
        chunks = self.chunker.chunk(document.content)
        document.num_chunks = len(chunks)
        
        logger.info(f"Created {len(chunks)} chunks")
        
        # Store document in SQL
        doc_id = self._store_document(document)
        document.id = doc_id
        
        # Store chunks
        for i, chunk_text in enumerate(chunks):
            chunk = DocumentChunk(
                document_id=doc_id,
                content=chunk_text,
                chunk_index=i,
                created_at=datetime.now()
            )
            self._store_chunk(chunk)
        
        logger.info(f"✅ Indexed document: {path.name} (id={doc_id}, chunks={len(chunks)})")
        
        return document
    
    def index_directory(
        self,
        directory: str,
        recursive: bool = True,
        user_id: str = "default_user"
    ) -> List[Document]:
        """
        Index all documents in a directory.
        
        Args:
            directory: Directory path
            recursive: Search subdirectories
            user_id: User ID
            
        Returns:
            List of indexed documents
        """
        dir_path = Path(directory)
        
        if not dir_path.exists():
            raise FileNotFoundError(f"Directory not found: {directory}")
        
        logger.info(f"Indexing directory: {directory} (recursive={recursive})")
        
        # Get all supported files
        pattern = "**/*" if recursive else "*"
        all_files = list(dir_path.glob(pattern))
        
        supported_exts = self.loader_registry.get_supported_extensions()
        files_to_index = [
            f for f in all_files 
            if f.is_file() and f.suffix.lower() in supported_exts
        ]
        
        logger.info(f"Found {len(files_to_index)} documents to index")
        
        indexed_docs = []
        for file_path in files_to_index:
            try:
                doc = self.index_document(str(file_path), user_id=user_id)
                indexed_docs.append(doc)
            except Exception as e:
                logger.error(f"Failed to index {file_path}: {e}")
        
        logger.info(f"✅ Indexed {len(indexed_docs)} documents from {directory}")
        
        return indexed_docs
    
    def _store_document(self, document: Document) -> int:
        """Store document in database"""
        import json
        
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO documents (
                file_path, file_name, file_type, title, content,
                metadata, user_id, tags, indexed_at, file_size_bytes, num_chunks
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            document.file_path,
            document.file_name,
            document.file_type.value,
            document.title,
            document.content,
            json.dumps(document.metadata),
            document.user_id,
            json.dumps(document.tags),
            document.indexed_at,
            document.file_size_bytes,
            document.num_chunks
        ))
        
        conn.commit()
        return cursor.lastrowid
    
    def _store_chunk(self, chunk: DocumentChunk) -> int:
        """Store document chunk"""
        import json
        
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO document_chunks (
                document_id, content, chunk_index, start_char, end_char,
                metadata, embedding_id, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            chunk.document_id,
            chunk.content,
            chunk.chunk_index,
            chunk.start_char,
            chunk.end_char,
            json.dumps(chunk.metadata) if chunk.metadata else None,
            chunk.embedding_id,
            chunk.created_at
        ))
        
        conn.commit()
        return cursor.lastrowid
    
    def _get_document_by_path(self, file_path: str) -> Optional[Document]:
        """Check if document already indexed"""
        import json
        
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM documents 
            WHERE file_path = ? AND deleted_at IS NULL
        """, (file_path,))
        
        row = cursor.fetchone()
        if not row:
            return None
        
        doc = Document(
            id=row['id'],
            file_path=row['file_path'],
            file_name=row['file_name'],
            file_type=row['file_type'],
            title=row['title'],
            content=row['content'],
            metadata=json.loads(row['metadata']) if row['metadata'] else {},
            user_id=row['user_id'],
            tags=json.loads(row['tags']) if row['tags'] else [],
            indexed_at=datetime.fromisoformat(row['indexed_at']) if row['indexed_at'] else None,
            file_size_bytes=row['file_size_bytes'],
            num_chunks=row['num_chunks']
        )
        
        return doc
    
    def get_stats(self) -> IndexStats:
        """Get indexing statistics"""
        import json
        
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Total documents
        cursor.execute("SELECT COUNT(*) as count FROM documents WHERE deleted_at IS NULL")
        total_docs = cursor.fetchone()['count']
        
        # Total chunks
        cursor.execute("""
            SELECT COUNT(*) as count FROM document_chunks c
            JOIN documents d ON c.document_id = d.id
            WHERE d.deleted_at IS NULL
        """)
        total_chunks = cursor.fetchone()['count']
        
        # Total size
        cursor.execute("""
            SELECT SUM(file_size_bytes) as total FROM documents 
            WHERE deleted_at IS NULL
        """)
        total_size = cursor.fetchone()['total'] or 0
        
        # By type
        cursor.execute("""
            SELECT file_type, COUNT(*) as count FROM documents 
            WHERE deleted_at IS NULL
            GROUP BY file_type
        """)
        by_type = {row['file_type']: row['count'] for row in cursor.fetchall()}
        
        # Last indexed
        cursor.execute("""
            SELECT MAX(indexed_at) as last FROM documents 
            WHERE deleted_at IS NULL
        """)
        last_indexed = cursor.fetchone()['last']
        
        return IndexStats(
            total_documents=total_docs,
            total_chunks=total_chunks,
            total_size_bytes=total_size,
            documents_by_type=by_type,
            last_indexed=datetime.fromisoformat(last_indexed) if last_indexed else None
        )
    
    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
            self.conn = None


# Global instance

_indexer = None

def get_indexer() -> DocumentIndexer:
    """Get or create global indexer"""
    global _indexer
    if _indexer is None:
        _indexer = DocumentIndexer()
    return _indexer