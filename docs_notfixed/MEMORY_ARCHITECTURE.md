# Memory System Architecture

## 🧠 Overview

The Memory System gives the voice assistant **long-term memory** across conversations. It remembers facts about you, your preferences, past conversations, and important context.

**Key Features:**
- 💾 **Hybrid Storage**: SQL (structured) + Vector DB (semantic)
- 🎯 **Smart Classification**: AI decides what's worth remembering
- 🔍 **Intelligent Retrieval**: Finds relevant memories for any query
- 💰 **Cost-Effective**: ~$1/month for 1000 conversations

---

## 🏗️ Architecture Diagram

```
User Input
    ↓
[1] Classify Memory Worth
    ├─ EPHEMERAL → Don't store
    ├─ CONVERSATIONAL → SQL only
    └─ FACTUAL → SQL + Vector
    ↓
[2] Store in SQL
    ├─ conversations table (all dialogue)
    ├─ facts table (important info)
    └─ facts_fts (FTS5 keyword index)
    ↓
[3] Store in Vector DB (if FACTUAL)
    └─ ChromaDB embeddings
    
When user asks something:
    ↓
[4] Hybrid Retrieval
    ├─ FTS5 keyword search (SQL)
    ├─ Vector semantic search
    └─ Recent conversations
    ↓
[5] Rank & Deduplicate
    ↓
[6] Inject into AI Prompt
```

---

## 📊 SQL vs Vector DB - When to Use What

### SQL Database (SQLite)

**What it stores:**
- ✅ ALL conversations (ephemeral, conversational, factual)
- ✅ Metadata (timestamps, user IDs, tokens)
- ✅ Provenance (which conversation created what)
- ✅ Structured queries (by date, user, category)

**Best for:**
- Exact matches ("What did I say yesterday?")
- Recent conversations
- Structured data (dates, counts, IDs)
- Fast keyword search (via FTS5)

**Example queries:**
```sql
-- Find conversations mentioning "birthday"
SELECT * FROM facts_fts WHERE facts_fts MATCH 'birthday';

-- Get last 10 conversations
SELECT * FROM conversations 
WHERE user_id = 'alice' 
ORDER BY timestamp DESC LIMIT 10;

-- Find all personal facts
SELECT * FROM facts 
WHERE category = 'personal' 
ORDER BY importance_score DESC;
```

**Why SQL?**
- FREE (local SQLite)
- FAST (indexed queries)
- RELIABLE (ACID transactions)
- QUERYABLE (powerful SQL)

---

### Vector Database (ChromaDB)

**What it stores:**
- ✅ Embeddings of FACTUAL information only
- ✅ Semantic meaning of content
- ✅ Allows "similar meaning" searches

**Best for:**
- Semantic queries ("Tell me about my preferences")
- Concept-based search ("What do I like?")
- When exact keywords don't match
- Finding related information

**Example queries:**
```python
# Semantic search
vector_store.search(
    query="What does the user enjoy?",
    # Finds: "User loves jazz music"
    # Even though "enjoy" != "love"
)

# Finds semantically similar facts
vector_store.search(
    query="User's age",
    # Finds: "User's birthday is March 15, 1990"
    # Even though "age" not in text
)
```

**Why Vector DB?**
- Understands MEANING, not just keywords
- Finds related concepts
- Language-agnostic (works across languages)
- Great for vague queries

---

## 🔀 Hybrid Retrieval: Best of Both Worlds

The system uses **both** SQL and Vector search simultaneously:

```python
async def retrieve_context(query: str):
    # 1. SQL FTS5 (fast keyword search)
    fts_results = sql_store.search_facts(query)
    # Finds: exact keyword matches
    
    # 2. Vector search (semantic similarity)
    vector_results = vector_store.search(query)
    # Finds: conceptually similar content
    
    # 3. Recent conversations
    recent = sql_store.get_conversations(limit=3)
    
    # 4. Combine, deduplicate, rank
    all_results = fts_results + vector_results + recent
    ranked = rank_by_relevance(all_results)
    
    return ranked[:5]  # Top 5 results
```

**Why Hybrid?**
- **SQL**: Fast, exact, structured
- **Vector**: Semantic, flexible, concept-based
- **Together**: Get the best of both!

---

## 🎯 Memory Classification

AI classifies every conversation into one of three tiers:

### Tier 1: EPHEMERAL (Don't Store)
**Criteria:**
- No learning value
- Temporary information
- Generic responses

**Examples:**
- ❌ "Hello" → "Hi there!"
- ❌ "What time is it?" → "It's 3:45 PM"
- ❌ "Play music" → "Playing now"
- ❌ "Thanks" → "You're welcome"

**Storage:** NONE  
**Cost:** $0

### Tier 2: CONVERSATIONAL (SQL Only)
**Criteria:**
- General dialogue
- No personal information
- Reference value only

**Examples:**
- ✓ "Tell me a joke" → "Why did the..."
- ✓ "Explain quantum physics" → "Quantum physics is..."
- ✓ "What's for dinner?" → "How about pasta?"

**Storage:** SQL conversations table  
**Cost:** ~$0.001/conversation

### Tier 3: FACTUAL (SQL + Vector)
**Criteria:**
- Personal information
- Preferences
- Important context
- Learning content

**Examples:**
- ✓✓ "My name is Alice" → Stores in both SQL + Vector
- ✓✓ "I live in Melbourne" → Stores in both
- ✓✓ "I prefer jazz music" → Stores in both
- ✓✓ "My birthday is March 15" → Stores in both

**Storage:** SQL facts table + ChromaDB embeddings  
**Cost:** ~$0.002/fact (one-time)

---

## 📊 Database Schema

### SQL Tables

#### `conversations`
Stores ALL dialogue (even ephemeral, for logging):
```sql
CREATE TABLE conversations (
    id INTEGER PRIMARY KEY,
    session_id TEXT,
    user_id TEXT,
    turn_no INTEGER,
    user_input TEXT,
    assistant_response TEXT,
    intent_type TEXT,
    duration_ms REAL,
    prompt_tokens INTEGER,
    completion_tokens INTEGER,
    timestamp DATETIME,
    deleted_at DATETIME
);

-- Indexes for fast retrieval
CREATE INDEX idx_conv_user ON conversations(user_id, timestamp DESC);
CREATE INDEX idx_conv_session ON conversations(session_id, turn_no);
```

#### `facts`
Stores FACTUAL information with full provenance:
```sql
CREATE TABLE facts (
    id INTEGER PRIMARY KEY,
    user_id TEXT,
    content TEXT,              -- Full sentence (not keywords!)
    content_hash TEXT,         -- SHA256 for deduplication
    category TEXT,             -- personal, preference, etc.
    importance_score REAL,     -- 0.0 to 1.0
    
    -- Provenance
    conversation_id INTEGER,   -- Which conversation created this
    message_id TEXT,
    source_doc_id TEXT,
    source_span TEXT,
    
    -- Vector reference
    embedding_id TEXT,         -- Links to ChromaDB
    
    -- Lifecycle
    created_at DATETIME,
    updated_at DATETIME,
    deleted_at DATETIME,
    
    FOREIGN KEY (conversation_id) REFERENCES conversations(id),
    UNIQUE(user_id, content_hash)  -- Prevent duplicates
);
```

#### `facts_fts`
FTS5 full-text search index (auto-synced):
```sql
CREATE VIRTUAL TABLE facts_fts USING fts5(
    content,
    content='facts',
    content_rowid='id'
);

-- Auto-maintained via triggers
```

### ChromaDB Collections

#### Collection: `memory_facts`
Stores embeddings of factual information:
```python
{
    "ids": ["fact_123"],
    "documents": ["User's birthday is March 15, 1990"],
    "embeddings": [[0.1, 0.2, ...]],  # Auto-generated
    "metadatas": [{
        "user_id": "alice",
        "fact_id": 123,  # Links back to SQL
        "category": "personal",
        "importance": 0.9,
        "created_at": "2025-01-01T00:00:00Z"
    }]
}
```

---

## 🔍 Retrieval Strategies

### 1. Keyword Search (SQL FTS5)
**When to use:** User query has specific keywords

```python
# User asks: "When is my birthday?"
# FTS5 finds: "User's birthday is March 15, 1990"
# Match: "birthday" keyword present
```

**Performance:** <5ms  
**Cost:** FREE

### 2. Semantic Search (Vector)
**When to use:** Conceptual or vague queries

```python
# User asks: "What do I enjoy?"
# Vector finds: "User loves jazz music"
# Match: "enjoy" ≈ "love" semantically
```

**Performance:** <50ms  
**Cost:** FREE (local embeddings)

### 3. Recency Boost
**When to use:** Context from recent conversation

```python
# User: "What did we just talk about?"
# Gets: Last 3-5 conversation turns
# Useful: Maintains conversation flow
```

### 4. Importance Ranking
**When to use:** Multiple results

```python
# Rank by:
score = (relevance * 0.6) + (importance * 0.3) + (recency * 0.1)

# Personal info (importance=0.9) ranks higher
# than casual preferences (importance=0.5)
```

---

## 💾 Data Flow Example

### Storing a Fact

```
User: "My name is Alice and I was born on March 15, 1990"
    ↓
[1] Classify (OpenAI)
    → FACTUAL (importance: 0.9, category: PERSONAL)
    ↓
[2] Store in SQL
    INSERT INTO conversations (...)
    INSERT INTO facts (content="My name is Alice...")
    → fact_id = 42
    ↓
[3] Generate embedding (ChromaDB)
    → embedding_id = "fact_42"
    ↓
[4] Link back to SQL
    UPDATE facts SET embedding_id = "fact_42" WHERE id = 42
    ↓
✅ Stored in both SQL + Vector!
```

### Retrieving Context

```
User: "What's my name?"
    ↓
[1] FTS5 Search
    SELECT * FROM facts_fts WHERE facts_fts MATCH 'name'
    → Finds: "My name is Alice..."
    → Score: 0.85 (high keyword match)
    ↓
[2] Vector Search
    vector_store.search("What's my name?")
    → Finds: "My name is Alice..."
    → Score: 0.92 (high semantic match)
    ↓
[3] Combine & Deduplicate
    → 1 unique result (same fact from both sources)
    ↓
[4] Format for AI
    Context: "Relevant information from memory:
             - My name is Alice and I was born on March 15, 1990"
    ↓
[5] Inject into prompt
    System: You are a helpful assistant.
            {context}
    User: What's my name?
    ↓
AI: Your name is Alice! ✅
```

---

## 📈 Performance Characteristics

| Operation | Time | Database | Cost |
|-----------|------|----------|------|
| Classify | 200-500ms | OpenAI API | $0.001 |
| Store SQL | 2-5ms | SQLite | FREE |
| Store Vector | 50-100ms | ChromaDB | FREE |
| FTS Search | 5-10ms | SQLite | FREE |
| Vector Search | 50-100ms | ChromaDB | FREE |
| Format Context | 1-2ms | Local | FREE |

**Total per conversation:** ~300-700ms, ~$0.001

---

## 💰 Cost Breakdown

### Classification
- **API**: OpenAI GPT-4o-mini
- **Cost**: ~$0.001 per conversation
- **Frequency**: Every conversation

### Embeddings
- **API**: ChromaDB (local, free!)
- **Cost**: $0 (uses local sentence-transformers)
- **Frequency**: Only FACTUAL conversations (~30%)

### Storage
- **SQL**: SQLite (local, free!)
- **Vector**: ChromaDB (local, free!)
- **Cost**: $0

### Retrieval
- **All**: Local queries
- **Cost**: $0

**Monthly (1000 conversations):**
- Classification: $1.00
- Embeddings: $0.00
- Storage: $0.00
- Retrieval: $0.00
- **Total: ~$1/month** 🎉

---

## 🔒 Privacy & Data Control

### Soft Delete
```python
# Mark as deleted (reversible)
fact.deleted_at = datetime.now()
# Fact stays in DB but hidden from queries
```

### Hard Delete
```python
# Permanent removal
DELETE FROM facts WHERE id = 123;
vector_store.delete("fact_123");
```

### Export Data
```python
# Get all user data
data = {
    "conversations": get_conversations(user_id),
    "facts": get_facts(user_id),
    "preferences": get_preferences(user_id)
}
json.dump(data, file)
```

### Reset
```python
# Clear everything
sql_store.reset()
vector_store.reset()
```

---

## 🎯 Best Practices

### ✅ DO
- Store complete sentences, not keywords
- Use hybrid retrieval (FTS + Vector)
- Set appropriate importance scores
- Track provenance (conversation_id)
- Deduplicate via content hash

### ❌ DON'T
- Store just keywords ("Alice", "March 15")
- Only use one retrieval method
- Store ephemeral conversations in vector
- Lose track of where facts came from
- Create duplicate facts

---

## 🔧 Configuration

### Tune Classification
Adjust prompts in `classifier.py`:
```python
# Make stricter (fewer facts stored)
importance_threshold = 0.7  # Only store if >0.7

# Make looser (more facts stored)
importance_threshold = 0.3  # Store if >0.3
```

### Tune Retrieval
Adjust in `memory_manager.py`:
```python
retrieve_context(
    query=user_input,
    max_results=5,         # Fewer = faster, more = context
    include_recent=True    # Include recent conversations
)
```

### Tune Context Formatting
```python
format_context_for_prompt(
    results,
    max_length=500        # Adjust based on your model
)
```

---

## 📚 Further Reading

- `MEMORY_FIX_GUIDE.md` - Troubleshooting recall issues
- `test_memory_phase3.py` - End-to-end test examples
- `memory_cli.py` - CLI tool for inspection
- API docs in each module's docstrings

---

**The memory system gives your assistant true intelligence through persistent, searchable, context-aware storage.** 🧠