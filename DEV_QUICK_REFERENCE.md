# 🚀 Developer Quick Reference

Quick cheatsheet for common development tasks.

---

## 🆕 Adding a New Action

### 1. Create Action File

Create `app/actions/my_new_action.py`:

```python
from typing import List, Dict, Any, Optional
from app.actions.base import Action, ActionResult, SecurityLevel
from app.utils.logger import get_logger

logger = get_logger('my_action')

class MyNewAction(Action):
    def __init__(self):
        super().__init__()
        self.description = "What this action does"
        self.security_level = SecurityLevel.SAFE
        # or SecurityLevel.CONFIRM for sensitive actions
        # or SecurityLevel.AUTH_REQUIRED for very sensitive
    
    def get_intents(self) -> List[str]:
        """Phrases that trigger this action"""
        return [
            "do something",
            "perform action",
            "my trigger phrase"
        ]
    
    async def execute(
        self, 
        prompt: str, 
        params: Optional[Dict[str, Any]] = None
    ) -> ActionResult:
        """Execute the action"""
        try:
            # Your action logic here
            logger.info("Executing my action")
            
            # Do stuff...
            result = "Something happened!"
            
            return ActionResult(
                success=True,
                message=result,
                data={"key": "value"}  # Optional extra data
            )
            
        except Exception as e:
            logger.error(f"Action failed: {e}")
            return ActionResult(
                success=False,
                message=f"Failed: {str(e)}"
            )
```

### 2. That's It!

The action is **automatically discovered** and registered. No need to modify any other files!

### 3. Test It

```bash
python -m app.main
```

Say: "Hey Pi" → "do something"

---

## 🔧 Configuration

### Access Config Values

```python
from app.utils.config import config

# Get with dot notation
value = config.get('settings.speech.hotword')

# Get with default
timeout = config.get('settings.speech.timeout', 5)

# Get entire section
ai_config = config.get_settings('ai')
```

### Add New Config

Edit `config/settings.yaml`:

```yaml
my_feature:
  enabled: true
  api_key: "secret"
  timeout: 30
```

Access:
```python
enabled = config.get('settings.my_feature.enabled')
```

---

## 📝 Logging

### Get Logger

```python
from app.utils.logger import get_logger

logger = get_logger('my_module')
```

### Log Messages

```python
# Different levels
logger.debug("Detailed info for debugging")
logger.info("General information")
logger.warning("Warning message")
logger.error("Error occurred")
logger.critical("Critical failure")

# With exception details
try:
    something()
except Exception as e:
    logger.error(f"Failed: {e}", exc_info=True)
```

### Log Conversations

```python
from app.utils.logger import log_conversation

log_conversation(user_input, assistant_response)
```

---

## 🎬 Action Results

### Simple Success

```python
return ActionResult(
    success=True,
    message="Action completed successfully!"
)
```

### With Data

```python
return ActionResult(
    success=True,
    message="Found 3 items",
    data={
        "items": [1, 2, 3],
        "count": 3
    }
)
```

### Failure

```python
return ActionResult(
    success=False,
    message="Action failed because..."
)
```

### Requires Confirmation

```python
return ActionResult(
    success=False,
    message="Draft prepared",
    requires_confirmation=True,
    confirmation_prompt="Send email to John about meeting?"
)
```

---

## 🔒 Security Levels

```python
from app.actions.base import SecurityLevel

class MyAction(Action):
    def __init__(self):
        super().__init__()
        # Choose one:
        self.security_level = SecurityLevel.SAFE           # No confirmation
        self.security_level = SecurityLevel.CONFIRM        # Ask user first
        self.security_level = SecurityLevel.AUTH_REQUIRED  # Need authentication
```

### Custom Confirmation

```python
async def get_confirmation_prompt(self, params=None) -> str:
    return f"Are you sure you want to delete {params['file']}?"
```

---

## 🧪 Testing Actions Manually

### From Python Console

```python
import asyncio
from app.actions.registry import action_registry

# Get action
action = action_registry.get_action("MyNewAction")

# Execute
result = asyncio.run(action.execute("test prompt"))

print(result.success)
print(result.message)
```

### From CLI

```bash
# Run assistant
python -m app.main

# Say hotword
"Hey Pi"

# Test your action
"do something"
```

---

## 🐛 Debugging

### Check Logs

```bash
# Real-time logs
tail -f logs/assistant.log

# Conversation history
tail -f logs/conversations_*.log

# Search logs
grep "ERROR" logs/assistant.log
```

### Enable Debug Mode

Edit `config/settings.yaml`:

```yaml
app:
  debug: true

logging:
  level: "DEBUG"
```

### Common Issues

**Action not found:**
- Check file is in `app/actions/`
- Check class inherits from `Action`
- Check `enabled = True` in config

**Import errors:**
- Check `app/actions/__init__.py` exists
- Check Python path is correct

**Intents not matching:**
- Check `get_intents()` returns list of strings
- Check strings match user input (case-insensitive)
- Check action is registered: Check logs for "✅ Registered action"

---

## 📦 Adding Dependencies

### 1. Install Package

```bash
pip install new-package
```

### 2. Add to requirements.txt

```txt
new-package==1.2.3
```

### 3. Use in Action

```python
import new_package

class MyAction(Action):
    async def execute(self, prompt, params=None):
        result = new_package.do_something()
        return ActionResult(success=True, message=result)
```

---

## 🔄 Action Registry API

```python
from app.actions.registry import action_registry

# Get action by name
action = action_registry.get_action("SmartHomeAction")

# Find action for prompt
action = action_registry.find_action_for_prompt("turn on light")

# List all actions
actions = action_registry.get_all_actions()  # Returns dict
action_names = action_registry.list_actions()  # Returns list of names

# Execute action
result = await action_registry.execute_action(
    "SmartHomeAction",
    prompt="turn on light",
    params={"room": "bedroom"}
)
```

---

## 🎨 Action Patterns

### Simple Command

```python
class PrintAction(Action):
    def get_intents(self):
        return ["print something"]
    
    async def execute(self, prompt, params=None):
        print("Printed!")
        return ActionResult(success=True, message="Printed to console")
```

### API Call

```python
class WeatherAction(Action):
    async def execute(self, prompt, params=None):
        import requests
        response = requests.get(f"https://api.weather.com/...")
        data = response.json()
        
        return ActionResult(
            success=True,
            message=f"Temperature is {data['temp']}°F",
            data=data
        )
```

### File Operation

```python
class FileAction(Action):
    async def execute(self, prompt, params=None):
        with open('data/file.txt', 'w') as f:
            f.write("content")
        
        return ActionResult(success=True, message="File saved")
```

### External Script

```python
class ScriptAction(Action):
    async def execute(self, prompt, params=None):
        import subprocess
        result = subprocess.run(
            ['python', 'scripts/my_script.py'],
            capture_output=True,
            text=True
        )
        
        return ActionResult(
            success=result.returncode == 0,
            message=result.stdout
        )
```

---

## 📊 Useful Commands

```bash
# Run assistant
python -m app.main

# Run with debug
DEBUG=true python -m app.main

# Check config is valid
python -c "from app.utils.config import config; print(config.get_settings())"

# List registered actions
python -c "from app.actions.registry import action_registry; print(action_registry.list_actions())"

# View logs
tail -f logs/assistant.log

# Clear logs
rm logs/*.log

# Run tests (when available)
pytest tests/
```

---

## 🎯 Common Tasks Checklist

### Adding Todo Action
- [ ] Create `app/actions/todo.py`
- [ ] Add intents: "add todo", "add task", etc.
- [ ] Implement JSON storage or database
- [ ] Add to `config/actions.yaml`
- [ ] Test with voice commands

### Adding Email Action
- [ ] Create `app/actions/email.py`
- [ ] Set security level to `CONFIRM`
- [ ] Implement draft generation
- [ ] Create `scripts/email_sender.py`
- [ ] Add SMTP config to `.env`
- [ ] Test confirmation flow

### Adding RAG System
- [ ] Create `app/rag/` directory
- [ ] Choose vector store (ChromaDB/FAISS)
- [ ] Create indexer for documents
- [ ] Create retriever for queries
- [ ] Create RAG action plugin
- [ ] Index your documents

---

## 🚨 Error Handling Template

```python
async def execute(self, prompt, params=None):
    try:
        # Your code here
        result = do_something()
        
        if not result:
            logger.warning("No result returned")
            return ActionResult(
                success=False,
                message="No results found"
            )
        
        return ActionResult(
            success=True,
            message="Success!"
        )
        
    except ValueError as e:
        logger.error(f"Invalid value: {e}")
        return ActionResult(
            success=False,
            message="Invalid input provided"
        )
        
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        return ActionResult(
            success=False,
            message=f"Error: {str(e)}"
        )
```

---

## 📚 Resources

- **Base Classes**: `app/actions/base.py`
- **Config System**: `app/utils/config.py`
- **Logging System**: `app/utils/logger.py`
- **Registry**: `app/actions/registry.py`
- **Examples**: `app/actions/*.py` (existing actions)

---

## 💡 Pro Tips

1. **Always use logger, never print()** for production code
2. **Return ActionResult** from all actions for consistency
3. **Use SecurityLevel.CONFIRM** for anything that modifies data
4. **Add type hints** for better IDE support
5. **Keep intents specific** to avoid conflicts
6. **Test actions individually** before integration
7. **Check logs** when debugging - they're your friend!

---

Happy coding! 🚀