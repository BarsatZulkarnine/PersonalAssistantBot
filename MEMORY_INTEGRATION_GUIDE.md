# Memory System Integration Guide

## 🎉 Integration Complete!

Your voice assistant now has **intelligent memory**! It can:
- ✅ Remember personal information (name, birthday, location)
- ✅ Recall preferences (music taste, likes/dislikes)
- ✅ Use context from past conversations
- ✅ Learn from interactions
- ✅ Search memories semantically

---

## 📁 Files to Update

Replace these files in your project:

### 1. **core/orchestrator.py** ✅
- **What changed**: Added memory retrieval before processing, memory storage after response
- **Key additions**:
  - `self.memory = get_memory_manager()` in `__init__`
  - Memory context retrieval in `process_user_input()`
  - Memory storage after generating response
  - Special memory commands in text mode

### 2. **modules/actions/conversation/ai_chat.py** ✅
- **What changed**: Now accepts memory context via params
- **Key additions**:
  - `memory_context` parameter support
  - Context injection into system prompt
  - Personalized responses based on memory

### 3. **New Test**: test_memory_integration.py ✅
- Tests the complete flow with real conversations
- Verifies memory storage and retrieval
- Simulates multi-turn dialogue with recall

---

## 🧪 Testing the Integration

### Step 1: Run Integration Tests

```bash
python test_memory_integration.py
```

Expected output:
```
============================================================
  Test: Memory Integration with Orchestrator
============================================================

🔧 Setting up test environment...
   Removed old test database
   Initializing orchestrator...
   ✅ Memory system ready

============================================================
  Simulating Conversation with Memory
============================================================

--- Turn 1 ---
User: Hi there!
[MEMORY] Storing conversation...
[MEMORY] Stored as ephemeral
Assistant: Hello! How can I help you?

--- Turn 2 ---
User: My name is Alice and I was born on March 15, 1990
[MEMORY] Retrieving context...
[MEMORY] Found 0 relevant memories
[MEMORY] Storing conversation...
[MEMORY] Stored as factual
   📚 Facts stored: 1
Assistant: Nice to meet you, Alice!

--- Turn 5 ---
User: What's my name?
[MEMORY] Retrieving context...
[MEMORY] Found 2 relevant memories
[AI CHAT] Injecting memory context
Assistant: Your name is Alice!
   ✅ Successfully recalled: Alice

✅ Integration test passed!
```

### Step 2: Test with Real Assistant

#### Text Mode (Easiest)
```bash
python main.py --mode text
```

Try these:
```
> My name is Alice
> I live in Melbourne
> I love jazz music
> What's my name?              # Should recall "Alice"
> Where do I live?             # Should recall "Melbourne"  
> What music do I like?        # Should recall "jazz"
```

#### Memory Commands
```
> memory:stats      # Show statistics
> memory:facts      # List all facts
> memory:search Alice  # Search for "Alice"
```

#### Voice Mode (Full Experience)
```bash
python main.py --mode voice
```

Say the wake word, then:
- "My birthday is March 15"
- (later) "When is my birthday?"
- Should recall it!

---

## 🔍 How It Works

### The Flow

```
User Input
    ↓
[1] Retrieve Memory Context
    ↓ (relevant facts)
[2] Detect Intent
    ↓
[3] Generate Response (with context!)
    ↓
[4] Store Conversation
    ↓ (classify → store)
Response to User
```

### Example Trace

```
User: "What's my birthday?"

[MEMORY] Retrieving context for: "What's my birthday?"
[MEMORY] FTS Search: Found "User's birthday is March 15, 1990"
[MEMORY] Vector Search: Found similar memories
[MEMORY] Ranked 2 results, relevance: 0.85

[AI] System prompt with context:
    "You are a helpful assistant.
     
     Relevant information from memory:
     - User's birthday is March 15, 1990
     
     Use this to provide personalized responses."

[AI] Generated: "Your birthday is March 15, 1990!"

[MEMORY] Storing conversation as CONVERSATIONAL
```

---

## 🎛️ Configuration

### Memory Settings

Located in your memory manager initialization:

```python
# Default locations
db_path = "data/memory.db"           # SQLite database
vector_path = "data/chromadb"        # Vector embeddings
```

### Retrieval Settings

In `memory_manager.py`:

```python
# Adjust these parameters
await manager.retrieve_context(
    query=user_input,
    max_results=5,        # How many memories to retrieve
    include_recent=True   # Include recent conversation turns
)

# Format for prompt
context = manager.format_context_for_prompt(
    results,
    max_length=500       # Max characters for context
)
```

### Classification Thresholds

In `classifier.py`:

```python
# Importance scoring
- EPHEMERAL: 0.0
- CONVERSATIONAL: 0.1-0.4
- FACTUAL: 0.5-1.0
  - 0.5-0.6: Minor preferences
  - 0.7-0.8: Important preferences
  - 0.9-1.0: Critical personal info
```

---

## 📊 Memory Commands (Text Mode)

When in text mode, you can use these special commands:

### `memory:stats`
Shows memory statistics:
```
📊 Memory Stats:
  Conversations: 15
  Facts: 8
  Tokens: 1,234
  Cost: $0.0012
  Embeddings: 8
```

### `memory:facts`
Lists all stored facts:
```
📚 User Facts (8):
  • [personal] User's name is Alice
  • [personal] User's birthday is March 15, 1990
  • [preference] User prefers jazz music
  • [personal] User lives in Melbourne
```

### `memory:search <query>`
Searches memories:
```
> memory:search birthday

🔍 Found 2 results:
  1. [0.92] User's birthday is March 15, 1990
  2. [0.45] User mentioned birthday plans
```

---

## 🐛 Troubleshooting

### Memory Not Working

**Check if memory initialized:**
```python
# Should see this on startup:
[OK] Memory: Hybrid SQL + Vector storage
```

If you see:
```
[WARN] Memory disabled: ...
```

Check:
1. ChromaDB installed: `pip install chromadb`
2. OpenAI API key in `.env`
3. No import errors in logs

### Context Not Being Used

**Check logs for:**
```
[MEMORY] Found 0 relevant memories
```

If always 0:
- No facts stored yet (say something factual first)
- FTS index might be empty
- Query too specific

**Check logs for:**
```
[AI CHAT] Injecting memory context
```

If missing:
- Context retrieval failed
- AI chat action not receiving params

### Classification Always EPHEMERAL

**Check:**
1. OpenAI API working
2. Classifier prompt in `classifier.py`
3. Test with obvious factual statements:
   - "My name is [name]"
   - "I live in [city]"
   - "I love [thing]"

### Assistant Doesn't Recall

**Possible causes:**
1. **Facts not stored**: Check `memory:facts` to verify
2. **Retrieval failing**: Check logs for `[MEMORY] Found X memories`
3. **Context not injected**: Check for `[AI CHAT] Injecting memory`
4. **AI ignoring context**: Try more explicit questions

**Debug:**
```bash
# Check what's stored
python memory_cli.py --list-facts

# Check search works
python memory_cli.py --search "user name"

# Check stats
python memory_cli.py --stats
```

---

## 💰 Cost Tracking

### Per Conversation

| Component | Cost |
|-----------|------|
| Classification | ~$0.001 |
| Embeddings (if FACTUAL) | $0.0001 |
| AI Response | ~$0.002 |
| **Total** | **~$0.003** |

### Monthly (1000 conversations)

- **Base**: ~$3/month
- **With memory**: ~$4/month
- **Extra cost**: Just $1/month! 💰

Track in real-time:
```bash
python memory_cli.py --stats
```

Shows:
- Total tokens used
- Estimated cost
- Number of embeddings

---

## 🎯 Next Steps

### 1. Test in Production

```bash
# Start with text mode
python main.py --mode text

# Test recall
> My favorite color is blue
> What's my favorite color?

# Check memory
> memory:facts
```

### 2. Try Voice Mode

```bash
python main.py --mode voice
```

Say wake word, then:
- Tell it personal info
- Ask it to recall later
- Should remember!

### 3. Monitor Performance

```bash
# Check memory stats regularly
python memory_cli.py --stats

# Review stored facts
python memory_cli.py --list-facts --limit 20

# Search for specific memories
python memory_cli.py --search "birthday"
```

### 4. Tune If Needed

**If too much stored:**
- Increase classification threshold in `classifier.py`
- Adjust importance scoring

**If not enough context:**
- Increase `max_results` in retrieval
- Increase `max_length` in prompt formatting
- Adjust `min_similarity` threshold

**If slow:**
- Reduce `max_results`
- Disable vector search temporarily
- Check database size

---

## 🚀 Advanced Usage

### Custom Memory Commands

Add to your own actions:

```python
from modules.memory import get_memory_manager

class CustomAction(Action):
    async def execute(self, prompt: str, params=None):
        memory = get_memory_manager()
        
        # Store something explicitly
        await memory.process_conversation(
            user_input=prompt,
            assistant_response="Noted!",
            intent_type="Action"
        )
        
        # Search memory
        results = await memory.retrieve_context("search query")
        
        # Get facts
        facts = memory.get_user_facts(limit=10)
```

### Direct Memory Access

```python
from modules.memory import get_memory_manager, Fact, FactCategory

manager = get_memory_manager()

# Store a fact manually
fact = Fact(
    content="User's favorite color is blue",
    category=FactCategory.PREFERENCE,
    importance_score=0.7
)
fact_id = manager.sql_store.store_fact(fact)

# Add to vector store
if manager.vector_store:
    manager.vector_store.add_embedding(
        fact_id=fact_id,
        content=fact.content,
        metadata={"category": "preference"}
    )
```

### Memory Reset

```bash
# Clear all memories
python memory_cli.py --clear-test

# Or in code:
manager.sql_store.reset()  # Careful!
manager.vector_store.reset()
```

---

## ✅ Verification Checklist

Before deploying:

- [ ] Integration tests pass
- [ ] Memory stores factual info
- [ ] Memory recalls info correctly
- [ ] Context injected into AI responses
- [ ] Memory commands work
- [ ] Stats show reasonable usage
- [ ] No errors in logs
- [ ] Cost is acceptable

---

## 🎉 You're Done!

Your assistant now has **intelligent memory**! It will:
- 🧠 Remember what you tell it
- 💭 Recall information when needed
- 🎯 Provide personalized responses
- 📈 Learn from every interaction

**Cost**: Just ~$1/month extra for 1000 conversations

Enjoy your memory-enhanced assistant! 🚀

---

**Questions?** Check:
- `modules/memory/README.md` - Architecture details
- `PHASE2_SETUP.md` - Classification guide
- `memory_cli.py --help` - CLI tool
- Logs in `logs/` directory