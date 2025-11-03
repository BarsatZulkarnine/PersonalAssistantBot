# 🔄 Migration Guide: v1.0 → v2.0

This guide helps you migrate from the old architecture to the new plugin-based system.

---

## 📁 File Structure Changes

### New Files (Create These)

```bash
# Configuration
mkdir -p config
touch config/settings.yaml
touch config/actions.yaml

# Logs directory
mkdir -p logs

# Data directories (for future use)
mkdir -p data/rag data/cache scripts
```

### Files to Replace

| Old Location | New Location | Status |
|-------------|-------------|---------|
| `app/main.py` | `app/main.py` | ✅ Replace |
| `app/router.py` | `app/router.py` | ✅ Replace |
| `app/modules/actions.py` | `app/actions/` (multiple files) | ✅ Split into plugins |
| `app/modules/ai_core.py` | `app/actions/conversation.py` | ✅ Migrate |
| `app/modules/web_search.py` | `app/actions/web.py` | ✅ Migrate |
| `app/utils/speech.py` | `app/utils/speech.py` | ⚠️ Keep (minor updates) |

### New Files to Create

```bash
app/utils/config.py          # NEW: Config loader
app/utils/logger.py          # NEW: Logging system
app/actions/__init__.py      # NEW: Actions package
app/actions/base.py          # NEW: Base action class
app/actions/registry.py      # NEW: Action registry
app/actions/smart_home.py    # NEW: Smart home plugin
app/actions/system.py        # NEW: System actions plugin
app/actions/web.py           # NEW: Web search plugin
app/actions/conversation.py  # NEW: Conversation plugin
```

---

## 🔧 Step-by-Step Migration

### Step 1: Install Dependencies

```bash
pip install pyyaml aiofiles
```

### Step 2: Create Config Files

Copy the provided `settings.yaml` and `actions.yaml` to your `config/` directory.

### Step 3: Create Utils

1. Add `app/utils/config.py`
2. Add `app/utils/logger.py`
3. Update `app/utils/speech.py` (minor - just imports)

### Step 4: Create Action System

1. Create `app/actions/` directory
2. Add `base.py` (base action class)
3. Add `registry.py` (action registry)
4. Add `__init__.py`

### Step 5: Migrate Actions

Create these new action files:

1. `app/actions/smart_home.py` - Migrate light control from `actions.py`
2. `app/actions/system.py` - Migrate volume/app launching from `actions.py`
3. `app/actions/web.py` - Migrate from `web_search.py`
4. `app/actions/conversation.py` - Migrate from `ai_core.py`

### Step 6: Update Main Files

1. Replace `app/router.py` with new version
2. Replace `app/main.py` with new version

### Step 7: Remove Old Files

**⚠️ Backup first!**

```bash
# Backup old files
mkdir backup
cp -r app/modules backup/

# Remove old module files (after confirming migration works)
rm -rf app/modules/
```

---

## 🔍 Code Changes Comparison

### Old: Adding an Action

**Old way** (`actions.py`):
```python
async def perform_action(prompt: str) -> str:
    prompt = prompt.lower()
    
    if "turn on light" in prompt:
        return "Turning on the light 💡"
    elif "volume up" in prompt:
        os.system("pactl set-sink-volume @DEFAULT_SINK@ +10%")
        return "Volume increased 🔊"
    # ... more if/elif chains
```

**New way** (Create `app/actions/my_action.py`):
```python
from app.actions.base import Action, ActionResult, SecurityLevel

class MyAction(Action):
    def get_intents(self) -> List[str]:
        return ["turn on light", "lights on"]
    
    async def execute(self, prompt: str, params=None) -> ActionResult:
        return ActionResult(
            success=True,
            message="Turning on the light 💡"
        )
```

✅ **Auto-discovered, no routing code needed!**

---

### Old: Routing Logic

**Old way** (`router.py`):
```python
async def process_prompt(prompt: str) -> str:
    decision = await decide_action(prompt)
    
    if "web" in decision.lower():
        return await web_search(prompt)
    elif "action" in decision.lower():
        result = await perform_action(prompt)
        if "don't know" in result:
            return await ask_ai(prompt)
        return result
    else:
        return await ask_ai(prompt)
```

**New way** (`router.py`):
```python
async def process_prompt(prompt: str) -> str:
    action = action_registry.find_action_for_prompt(prompt)
    
    if not action:
        action = action_registry.get_action("ConversationAction")
    
    result = await action_registry.execute_action(
        action.name, prompt
    )
    
    return result.message
```

✅ **Much simpler, no AI decision calls needed for routing!**

---

### Configuration

**Old way** (Hardcoded):
```python
hotword = "hey pi"
timeout = 5
model = "gpt-4o-mini"
```

**New way** (`config/settings.yaml`):
```yaml
speech:
  hotword: "hey pi"
  listen_timeout: 5

ai:
  model: "gpt-4o-mini"
```

Access in code:
```python
from app.utils.config import config

hotword = config.get('settings.speech.hotword')
```

✅ **Easy to change without touching code!**

---

### Logging

**Old way**:
```python
print("🎤 Listening...")
print(f"❌ Action failed: {e}")
```

**New way**:
```python
from app.utils.logger import get_logger

logger = get_logger('my_module')
logger.info("🎤 Listening...")
logger.error(f"❌ Action failed: {e}", exc_info=True)
```

✅ **Proper logging with levels, rotation, and file output!**

---

## ⚠️ Breaking Changes

### 1. Return Types

**Old**: Actions returned `str`
```python
return "Turning on the light 💡"
```

**New**: Actions return `ActionResult`
```python
return ActionResult(
    success=True,
    message="Turning on the light 💡"
)
```

### 2. Action Discovery

**Old**: Manually add to `actions.py` if/elif chain

**New**: Create new file in `app/actions/`, auto-discovered

### 3. Configuration

**Old**: Hardcoded values in code

**New**: Values in `config/settings.yaml` and `config/actions.yaml`

### 4. Module Paths

**Old**: `from app.modules.ai_core import ask_ai`

**New**: `from app.actions.registry import action_registry`

---

## ✅ Testing Your Migration

### 1. Basic Test

```bash
python -m app.main
```

Should see:
```
🚀 Starting Voice Assistant v2.0
📋 Loaded 4 actions
🎤 Say 'hey pi' to activate
```

### 2. Test Each Action

Say these commands:
- "Hey Pi" → "Turn on the light" ✅
- "Hey Pi" → "Volume up" ✅
- "Hey Pi" → "Search for Python tutorials" ✅
- "Hey Pi" → "Tell me a joke" ✅

### 3. Check Logs

```bash
tail -f logs/assistant.log
tail -f logs/conversations_*.log
```

Should see structured logs with timestamps and levels.

---

## 🆘 Troubleshooting

### Error: "No module named 'app.actions'"

**Fix**: Make sure you created `app/actions/__init__.py`

### Error: "No actions loaded"

**Fix**: Check that action files are in `app/actions/` and inherit from `Action`

### Error: "Config file not found"

**Fix**: Create `config/settings.yaml` and `config/actions.yaml`

### Actions not working

**Fix**: Check:
1. Action's `enabled` is `True` in config
2. Action's `get_intents()` matches your prompt
3. Check logs: `tail -f logs/assistant.log`

---

## 🎉 Benefits of Migration

✅ **Scalability**: Add new actions without modifying routing logic

✅ **Maintainability**: Each action is isolated and testable

✅ **Configuration**: Change behavior without code changes

✅ **Logging**: Proper structured logs for debugging

✅ **Error Handling**: Graceful failures, no more crashes

✅ **Security**: Built-in confirmation system for sensitive actions

✅ **Extensibility**: Easy to add RAG, email, todo, etc.

---

## 📚 Next Steps After Migration

1. ✅ Verify all actions work
2. ✅ Customize `config/settings.yaml` for your preferences
3. ✅ Test error scenarios (network failures, etc.)
4. ⏭️ Implement streaming TTS (Phase 2)
5. ⏭️ Add intent classifier (Phase 3)
6. ⏭️ Add new actions (todo, email, etc.)

---

## 🤔 Questions?

Check the README.md for the full feature checklist and architecture docs!