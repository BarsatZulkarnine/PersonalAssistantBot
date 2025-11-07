# RAG System Architecture

## 📚 Overview

RAG (Retrieval Augmented Generation) lets your assistant **search and understand your personal documents**. Instead of just relying on built-in knowledge, it can reference your PDFs, Word docs, notes, and more.

**Key Features:**
- 📄 **Multi-Format Support**: PDF, DOCX, TXT, Markdown, HTML
- 🔪 **Smart Chunking**: Preserves context across splits
- 🔍 **Hybrid Search**: Keyword + Semantic retrieval
- 💾 **Local & Private**: All data stays on your machine
- 💰 **Cost-Effective**: One-time indexing cost, free retrieval

---

## 🏗️ Architecture Diagram

```
Document Upload
    ↓
[1] Load Document
    ├─ PDF → PyPDF2
    ├─ DOCX → python-docx
    ├─ TXT/MD → built-in
    └─ HTML → BeautifulSoup
    ↓
[2] Chunk Text
    ├─ Sentence boundaries
    ├─ 500 words per chunk
    ├─ 50 words overlap
    └─ Preserve context
    ↓
[3] Store in SQL
    ├─ documents table (metadata)
    ├─ document_chunks table
    └─ documents_fts (FTS5 index)
    ↓
[4] Generate Embeddings
    └─ ChromaDB (local model)
    
When user asks question:
    ↓
[5] Hybrid Retrieval
    ├─ FTS5 keyword search (SQL)
    └─ Vector semantic search
    ↓
[6] Rank & Format
    ↓
[7] Inject into AI Prompt
```

---

## 📊 Memory vs RAG - Key Differences

| Feature | Memory | RAG |
|---------|--------|-----|
| **Purpose** | Remember conversations | Search documents |
| **Input** | What you SAY | What you UPLOAD |
| **Content** | Personal facts, preferences | Documents, files, notes |
| **Updates** | Continuous (every chat) | Manual (index when needed) |
| **Storage** | Conversations + facts | Documents + chunks |
| **Retrieval** | Recent + relevant memories | Relevant document chunks |
| **Use Case** | "What's my name?" | "What does my report say about X?" |

### When to Use What?

**Use MEMORY for:**
- ✓ Personal information ("My birthday is...")
- ✓ Preferences ("I like jazz")
- ✓ Conversation history
- ✓ Things you TOLD the assistant

**Use RAG for:**
- ✓ Document content ("What's in my report?")
- ✓ Reference materials
- ✓ Knowledge bases
- ✓ Things in your FILES

**Both work together!**
```
User: "Based on my notes, what music do I like?"
Memory: "User prefers jazz" (from conversation)
RAG: "Meeting notes: Alice loves classical and jazz" (from document)
AI: Combines both sources for complete answer
```

---

## 🔪 Chunking Strategy

### Why Chunk Documents?

Documents are often too long for AI context windows. We split them into **manageable chunks** while **preserving context**.

### Chunking Approaches

#### 1. Fixed Size (Simple)
```
Split every 500 words → chunks
Problem: May split mid-sentence
```

#### 2. Sentence-Based (Smart) ✅ **WE USE THIS**
```
Split at sentence boundaries
Keep chunks ~500 words
Add 50-word overlap between chunks
Benefit: Preserves context, natural boundaries
```

#### 3. Paragraph-Based
```
Split at paragraph breaks
Benefit: Keeps related content together
Problem: Uneven chunk sizes
```

### Our Implementation

```python
chunker = SmartChunker(
    chunk_size=500,     # Target words per chunk
    overlap=50,         # Words shared between chunks
    strategy=SENTENCE   # Respect sentence boundaries
)

chunks = chunker.chunk(document_text)
```

**Example:**
```
Document: "This is sentence one. This is sentence two. This is sentence three..."

Chunk 1: "This is sentence one. This is sentence two. This is sentence three."
         (500 words)

Chunk 2: "This is sentence three. This is sentence four. This is sentence five."
         (Starts with last 50 words from Chunk 1)
         
Overlap ensures context isn't lost at boundaries!
```

---

## 📂 File Format Support

### Text Files (Built-in)
```python
TextLoader
├─ .txt  ✅ Plain text
├─ .md   ✅ Markdown
└─ Fast, no dependencies
```

### PDF Files
```python
PDFLoader (PyPDF2)
├─ Extracts text from all pages
├─ Preserves page numbers
├─ Handles metadata (author, title)
└─ pip install PyPDF2
```

### Word Documents
```python
DOCXLoader (python-docx)
├─ Extracts paragraphs
├─ Preserves structure
├─ Handles tables (basic)
└─ pip install python-docx
```

### HTML Files
```python
HTMLLoader (BeautifulSoup)
├─ Strips scripts/styles
├─ Extracts clean text
├─ Preserves structure
└─ pip install beautifulsoup4
```

### Adding New Formats

Create a loader:
```python
class CustomLoader(DocumentLoader):
    def can_load(self, file_path: str) -> bool:
        return Path(file_path).suffix == '.custom'
    
    def load(self, file_path: str) -> Document:
        # Your logic here
        return Document(...)
```

Register it:
```python
loader_registry.loaders.append(CustomLoader())
```

---

## 🗄️ Storage Schema

### SQL Tables

#### `documents`
Stores document metadata:
```sql
CREATE TABLE documents (
    id INTEGER PRIMARY KEY,
    file_path TEXT UNIQUE,
    file_name TEXT,
    file_type TEXT,           -- pdf, docx, txt, etc.
    title TEXT,
    content TEXT,             -- Full text
    metadata TEXT,            -- JSON (author, pages, etc.)
    
    user_id TEXT,
    tags TEXT,                -- JSON array
    
    indexed_at DATETIME,
    file_size_bytes INTEGER,
    num_chunks INTEGER,
    
    deleted_at DATETIME
);
```

#### `document_chunks`
Stores individual chunks:
```sql
CREATE TABLE document_chunks (
    id INTEGER PRIMARY KEY,
    document_id INTEGER,
    content TEXT,
    chunk_index INTEGER,
    
    start_char INTEGER,       -- Position in original
    end_char INTEGER,
    
    metadata TEXT,
    embedding_id TEXT,        -- Links to ChromaDB
    
    created_at DATETIME,
    
    FOREIGN KEY (document_id) REFERENCES documents(id),
    UNIQUE(document_id, chunk_index)
);
```

#### `documents_fts`
FTS5 search index:
```sql
CREATE VIRTUAL TABLE documents_fts USING fts5(
    title,
    content,
    content='documents',
    content_rowid='id'
);
```

### ChromaDB Collection

#### Collection: `rag_documents`
Stores chunk embeddings:
```python
{
    "ids": ["chunk_123"],
    "documents": ["Content of chunk 123..."],
    "embeddings": [[0.1, 0.2, ...]],
    "metadatas": [{
        "document_id": 42,
        "chunk_index": 5,
        "file_name": "report.pdf",
        "file_type": "pdf"
    }]
}
```

---

## 🔍 Retrieval Process

### 1. FTS Keyword Search
```python
# User query: "machine learning algorithms"
# SQL FTS5:
SELECT chunks.* FROM document_chunks chunks
JOIN documents_fts fts ON chunks.document_id = fts.rowid
WHERE fts MATCH 'machine learning algorithms'
ORDER BY bm25(documents_fts) DESC

# Finds: Chunks with exact keywords
# Score: BM25 relevance (higher = better match)
```

### 2. Vector Semantic Search
```python
# Same query: "machine learning algorithms"
# Vector search:
vector_store.search("machine learning algorithms")

# Finds: Semantically similar chunks
# Example matches:
# - "neural networks and deep learning"
# - "AI model training techniques"
# - "supervised learning methods"

# Even without exact keywords!
```

### 3. Hybrid Combination
```python
# Combine both approaches:
fts_results = fts_search(query)      # Keyword matches
vector_results = vector_search(query) # Semantic matches

# Merge and deduplicate
all_results = fts_results + vector_results
unique_results = deduplicate(all_results)

# Rank by composite score
ranked = sort_by_relevance(unique_results)

return ranked[:5]  # Top 5
```

---

## 📊 Indexing Process

### Step-by-Step

```
1. Load Document
   document = PDFLoader().load("report.pdf")
   → Document object with full text
   
2. Chunk Text
   chunks = chunker.chunk(document.content)
   → ["Chunk 1 text...", "Chunk 2 text...", ...]
   → With overlap for context
   
3. Store Document
   doc_id = sql_store.store_document(document)
   → Row in documents table
   
4. Store Chunks
   for i, chunk in enumerate(chunks):
       chunk_id = sql_store.store_chunk(DocumentChunk(
           document_id=doc_id,
           content=chunk,
           chunk_index=i
       ))
   → Rows in document_chunks table
   → Auto-indexed in FTS5
   
5. Generate Embeddings
   for chunk_id, chunk in chunks:
       embedding_id = vector_store.add_embedding(
           fact_id=chunk_id,
           content=chunk,
           metadata={...}
       )
       sql_store.update_chunk_embedding(chunk_id, embedding_id)
   → Embeddings in ChromaDB
   → Links back to SQL

✅ Document fully indexed!
```

### Batch Indexing

```python
indexer = get_indexer()

# Index entire directory
docs = indexer.index_directory(
    "~/Documents",
    recursive=True
)

# Progress:
# [1/50] report.pdf (5 chunks)
# [2/50] notes.txt (2 chunks)
# ...
# ✅ Indexed 50 documents, 237 chunks
```

---

## 💾 Example Data Flow

### Indexing a PDF

```
File: "Python_Guide.pdf" (20 pages, 10,000 words)
    ↓
[Load PDF]
    → Extracted text: "Python is a programming language..."
    ↓
[Chunk] (500 words/chunk with 50-word overlap)
    → Chunk 1: "Python is a programming language..."
    → Chunk 2: "...language features. Python has..."
    → ...
    → Chunk 20: "...advanced topics and best practices."
    ↓
[Store SQL]
    documents:
      id=42, file="Python_Guide.pdf", chunks=20
    
    document_chunks:
      id=101, doc_id=42, index=0, content="Python is..."
      id=102, doc_id=42, index=1, content="...features..."
      ...
    ↓
[Generate Embeddings]
    ChromaDB:
      chunk_101 → [0.1, 0.2, 0.3, ...]
      chunk_102 → [0.15, 0.25, 0.35, ...]
      ...
    ↓
✅ 1 document → 20 searchable chunks
```

### Searching the PDF

```
User: "How do I use decorators in Python?"
    ↓
[FTS Search]
    MATCH 'decorators python'
    → Found: chunk_115 (score: 0.85)
    ↓
[Vector Search]
    similarity("How do I use decorators?")
    → Found: chunk_115 (score: 0.92)
    →        chunk_118 (score: 0.78)
    ↓
[Combine & Rank]
    1. chunk_115 (avg: 0.88) "Decorators in Python..."
    2. chunk_118 (score: 0.78) "Advanced decorator patterns..."
    ↓
[Format Context]
    "Relevant information from documents:
     [1. Python_Guide.pdf] Decorators in Python allow you to..."
    ↓
[Inject into AI]
    System: {context above}
    User: How do I use decorators in Python?
    AI: Based on the Python guide, decorators are...
```

---

## 📈 Performance Metrics

| Operation | Time | Scalability |
|-----------|------|-------------|
| Index 1-page PDF | ~500ms | Linear with size |
| Index 100-page PDF | ~30s | Good |
| FTS Search | 5-20ms | <1000 docs: fast, >10k docs: slower |
| Vector Search | 50-200ms | <10k chunks: good, >100k: slower |
| Hybrid Retrieval | 100-300ms | Depends on corpus size |

**Recommendations:**
- **<1000 documents**: Excellent performance
- **1000-10000 documents**: Good performance
- **>10000 documents**: Consider chunking strategies or external vector DB

---

## 💰 Cost Analysis

### Indexing Costs

| Document | Chunks | Embedding Cost | One-Time |
|----------|--------|----------------|----------|
| 1-page PDF | ~2 | $0.0002 | Yes ✅ |
| 10-page PDF | ~20 | $0.002 | Yes ✅ |
| 100-page PDF | ~200 | $0.02 | Yes ✅ |
| 1000 PDFs (avg 10 pages) | ~20,000 | $2.00 | Yes ✅ |

**Note:** Using ChromaDB's local embeddings = **$0 cost!**

### Retrieval Costs

- FTS Search: **FREE** (local SQL)
- Vector Search: **FREE** (local ChromaDB)
- Context Formatting: **FREE** (local)

**Total per query: $0** 🎉

---

## 🔄 Memory + RAG Integration

### How They Work Together

```
User: "What music do I like according to my notes?"
    ↓
[Memory Retrieval]
    → "User prefers jazz music" (from past conversations)
    ↓
[RAG Retrieval]
    → "Meeting notes: Alice loves classical and jazz" (from document)
    ↓
[Combine Contexts]
    Memory: User prefers jazz music
    RAG: Meeting notes mention classical and jazz
    ↓
[AI Response]
    "Based on our conversations and your notes, you enjoy jazz music. 
     Your meeting notes also mention an interest in classical music."
    ↓
✅ Complete answer using both sources!
```

### Context Prioritization

```python
# In orchestrator:
memory_context = retrieve_memory(query)  # Recent, personal
rag_context = retrieve_documents(query)  # Reference materials

# Combine (memory first for recency)
full_context = f"""
{memory_context}

{rag_context}
"""

# AI sees both, prioritizes based on relevance
```

---

## 🎯 Best Practices

### ✅ DO
- Index documents before asking about them
- Use descriptive filenames
- Keep documents organized
- Update index when files change
- Use hybrid retrieval (FTS + Vector)

### ❌ DON'T
- Index huge files (>100MB) without chunking
- Expect instant indexing (it takes time)
- Forget to re-index after file changes
- Only use one retrieval method
- Store binary files (images, etc.)

---

## 🔧 Configuration

### Chunk Size Tuning

```python
# Smaller chunks (more precise)
chunker = SmartChunker(chunk_size=300)
# Pros: Precise matches
# Cons: May lose context

# Larger chunks (more context)
chunker = SmartChunker(chunk_size=800)
# Pros: More context per chunk
# Cons: Less precise, fewer chunks

# Default (balanced)
chunker = SmartChunker(chunk_size=500)  ✅
```

### Retrieval Tuning

```python
# More results (more context, slower)
results = retrieve(query, top_k=10)

# Fewer results (faster, less context)
results = retrieve(query, top_k=3)

# Default (balanced)
results = retrieve(query, top_k=5)  ✅
```

---

## 🔒 Privacy

**All data is local:**
- ✅ Documents: Stored on your machine
- ✅ Embeddings: Generated and stored locally (ChromaDB)
- ✅ Queries: Processed locally
- ❌ No data sent to external services (except OpenAI for AI responses)

---

## 📚 Use Cases

### 1. Personal Knowledge Base
```
Index: Your notes, journals, research
Query: "What did I learn about X last month?"
```

### 2. Work Documents
```
Index: Reports, meeting notes, project docs
Query: "What were the Q3 goals?"
```

### 3. Learning Materials
```
Index: Textbooks, tutorials, documentation
Query: "How do I implement a binary tree?"
```

### 4. Reference Library
```
Index: Manuals, guides, specifications
Query: "What's the API endpoint for user management?"
```

---

## 🚀 Next Steps

1. **Index your documents**: `python -c "from modules.rag import get_indexer; get_indexer().index_directory('~/Documents')"`
2. **Test retrieval**: `python test_rag_system.py`
3. **Use in assistant**: Already integrated! Just ask about your documents

---

**RAG transforms your assistant from a chatbot into a personal research assistant with access to all your documents.** 📚