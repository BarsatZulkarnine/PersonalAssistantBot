# 🏗️ Voice Assistant - Refactored Modular Architecture

## 🎯 Design Philosophy

**True Modularity**: Every component is independent and swappable without touching other code.

### Core Principles

1. **Independence** - Modules don't depend on each other's implementation
2. **Swappability** - Change providers via config, not code
3. **Clear Interfaces** - Each module has a well-defined interface
4. **Configuration-Driven** - Behavior controlled by YAML files
5. **Category-Based** - Actions organized by purpose

---

## 📐 Architecture Overview

```
┌─────────────────────────────────────────────────────┐
│                   Orchestrator                       │
│          (Coordinates all modules)                   │
└──────────────┬──────────────────────────────────────┘
               │
     ┌─────────┴─────────┐
     │   Module Loader    │  ← Loads modules dynamically
     └─────────┬──────────┘     based on config
               │
    ┌──────────┴──────────┐
    │                     │
┌───▼────┐  ┌───▼────┐  ┌▼──────┐  ┌─▼────┐  ┌─▼─────┐
│ Wake   │  │  STT   │  │  TTS  │  │Intent│  │Actions│
│ Word   │  │        │  │       │  │      │  │       │
└───┬────┘  └───┬────┘  └┬──────┘  └─┬────┘  └─┬─────┘
    │           │         │           │         │
┌───▼────┐  ┌───▼────┐  ┌▼──────┐  ┌─▼────┐  ┌─▼─────┐
│Vosk/   │  │Google/ │  │gTTS/  │  │Simple│  │ Home  │
│Porcupine│  │Whisper│  │Eleven │  │ AI   │  │ Auto  │
└────────┘  └────────┘  └───────┘  └──────┘  └───────┘
  (Choose)    (Choose)    (Choose)  (Choose)  (Categories)
```

---

## 📂 New File Structure

```
assistant/
├── config/                         # All configuration
│   ├── settings.yaml              # Global settings
│   └── modules/                   # Module configs
│       ├── wake_word.yaml         # Wake word settings
│       ├── stt.yaml               # STT settings
│       ├── tts.yaml               # TTS settings
│       ├── intent.yaml            # Intent detection
│       └── actions.yaml           # Actions config
│
├── modules/                        # Independent modules
│   ├── wake_word/                 # 🎤 Wake word detection
│   │   ├── base.py               # Interface
│   │   ├── vosk.py               # Vosk implementation
│   │   └── porcupine.py          # Porcupine implementation
│   │
│   ├── stt/                       # 🎧 Speech-to-Text
│   │   ├── base.py               # Interface
│   │   ├── google.py             # Google STT
│   │   ├── whisper.py            # Whisper (local)
│   │   └── azure.py              # Azure STT
│   │
│   ├── tts/                       # 🔊 Text-to-Speech
│   │   ├── base.py               # Interface
│   │   ├── gtts.py               # Google TTS
│   │   ├── elevenlabs.py         # ElevenLabs
│   │   └── piper.py              # Piper (local)
│   │
│   ├── intent/                    # 🎯 Intent Detection
│   │   ├── base.py               # Interface
│   │   ├── simple_ai.py          # Simple (AI/Web/Action)
│   │   └── advanced.py           # Advanced (with params)
│   │
│   ├── actions/                   # ⚡ Actions
│   │   ├── base.py               # Base action class
│   │   ├── registry.py           # Action registry
│   │   │
│   │   ├── home_automation/      # 🏠 Smart home
│   │   │   ├── lights.py
│   │   │   └── thermostat.py
│   │   │
│   │   ├── productivity/         # 📝 Productivity
│   │   │   ├── email.py
│   │   │   ├── todo.py
│   │   │   └── calendar.py
│   │   │
│   │   ├── system/               # 💻 System control
│   │   │   ├── volume.py
│   │   │   └── apps.py
│   │   │
│   │   └── conversation/         # 💬 Chat
│   │       └── ai_chat.py
│   │
│   ├── rag/                       # 🧠 RAG system
│   │   ├── vector_store.py
│   │   ├── retriever.py
│   │   └── indexer.py
│   │
│   └── security/                  # 🔒 Security
│       ├── confirmation.py
│       └── permissions.py
│
├── core/                          # Core coordination
│   ├── orchestrator.py           # Main coordinator
│   ├── module_loader.py          # Dynamic loading
│   └── pipeline.py               # Request pipeline
│
├── utils/                         # Utilities
│   ├── config.py                 # Config management
│   └── logger.py                 # Logging
│
├── data/                          # Data storage
├── logs/                          # Log files
├── main.py                       # Entry point
└── requirements.txt
```

---

## 🔌 Module System

### How Modules Work

Each module:
1. **Has an interface** (base.py) - Defines contract
2. **Has implementations** - Different providers
3. **Has config** - In `config/modules/`
4. **Is loaded dynamically** - By ModuleLoader

### Switching Providers

**Change STT from Google to Whisper:**

Edit `config/modules/stt.yaml`:
```yaml
provider: "whisper"  # Changed from "google"
```

That's it! No code changes needed.

---

## 🎤 Module 1: Wake Word Detection

### Purpose
Efficiently detect wake word without consuming resources.

### Interface
```python
class WakeWordDetector(ABC):
    def start()  # Start listening
    def stop()   # Stop listening
    def wait_for_wake_word() -> bool  # Block until detected
    def get_resource_usage() -> dict  # Check CPU/memory
```

### Implementations
- **Vosk** - Offline, accurate, medium resources
- **Porcupine** - Very efficient, customizable wake words

### Configuration
```yaml
# config/modules/wake_word.yaml
provider: "vosk"
wake_word: "hey pi"
sensitivity: 0.5
low_power_mode: true
```

---

## 🎧 Module 2: Speech-to-Text

### Purpose
Record and transcribe user speech with configurable duration.

### Interface
```python
class STTProvider(ABC):
    def listen() -> STTResult  # Record and transcribe
    def set_recording_duration(float)  # Adjust max duration
    def set_pause_threshold(float)  # Silence detection
    def adjust_for_ambient_noise()  # Calibrate
```

### Implementations
- **Google** - Cloud-based, accurate, requires internet
- **Whisper** - Local, very accurate, requires GPU
- **Azure** - Cloud-based, enterprise features

### Configuration
```yaml
# config/modules/stt.yaml
provider: "google"
recording:
  timeout: 5              # Max wait for speech
  phrase_time_limit: 15   # Max recording duration
  pause_threshold: 0.8    # Silence to stop
  energy_threshold: 300   # Voice detection
language: "en-US"
```

---

## 🔊 Module 3: Text-to-Speech

### Purpose
Convert text to speech with customizable voices.

### Interface
```python
class TTSProvider(ABC):
    def speak(text) -> bool  # Blocking speech
    def speak_async(text)    # Non-blocking
    def stream_speak(text)   # Sentence-by-sentence
    def list_voices() -> List[str]  # Available voices
    def set_voice(name)      # Change voice
```

### Implementations
- **gTTS** - Free, decent quality, cloud
- **ElevenLabs** - Premium, best quality, paid
- **Piper** - Local, fast, offline

### Configuration
```yaml
# config/modules/tts.yaml
provider: "gtts"
language: "en"
speed: 1.0
streaming:
  enabled: true
voice:
  gender: "neutral"
```

---

## 🎯 Module 4: Intent Detection

### Purpose
Classify user input into categories: AI, Web, or Action.

### Interface
```python
class IntentDetector(ABC):
    async def detect(text) -> IntentResult
    # Returns: IntentType (AI, WEB, ACTION)
```

### Implementations
- **Simple AI** - Uses GPT to classify into 3 categories
- **Advanced** - Extracts parameters, multi-intent

### Configuration
```yaml
# config/modules/intent.yaml
provider: "simple_ai"
simple_ai:
  model: "gpt-4o-mini"
  temperature: 0.3
  categories:
    - "AI"      # Conversation
    - "Web"     # Search
    - "Action"  # Execute
```

---

## ⚡ Module 5: Actions

### Purpose
Execute user commands, organized by category.

### Categories

#### 🏠 Home Automation
- Lights, thermostat, locks, etc.
- Integrates with Hue, Home Assistant, MQTT

#### 📝 Productivity  
- Email, todo, calendar
- Requires confirmation for sensitive actions

#### 💻 System
- Volume, apps, window management
- Cross-platform support

#### 💬 Conversation
- General AI chat
- Fallback for unmatched intents

### Adding New Action

Create `modules/actions/<category>/<action>.py`:

```python
from modules.actions.base import Action, ActionResult, ActionCategory

class MyAction(Action):
    def __init__(self):
        super().__init__()
        self.category = ActionCategory.HOME_AUTOMATION
    
    def get_intents(self):
        return ["my trigger phrase"]
    
    async def execute(self, prompt, params=None):
        # Your code here
        return ActionResult(success=True, message="Done!")
```

**Auto-discovered!** No registration needed.

---

## 🔧 Configuration System

### Three Levels

1. **Global Settings** - `config/settings.yaml`
   - App name, version, debug mode
   - Logging configuration

2. **Module Configs** - `config/modules/*.yaml`
   - Each module has its own config
   - Provider selection
   - Module-specific settings

3. **Action Configs** - `config/modules/actions.yaml`
   - Which actions enabled
   - Category settings
   - Integration details

### Example: Switching Everything to Local

```yaml
# wake_word.yaml
provider: "vosk"  # Offline

# stt.yaml
provider: "whisper"  # Local

# tts.yaml
provider: "piper"  # Local

# intent.yaml
provider: "rule_based"  # No API calls
```

Now runs **completely offline**!

---

## 🚀 Getting Started

### 1. Install

```bash
pip install -r requirements.txt
```

### 2. Configure

Create config files in `config/modules/`:
- Copy templates from artifacts
- Edit provider selections
- Adjust settings

### 3. Run

```bash
python main.py
```

### 4. Test Module Loading

```bash
python -c "from core.module_loader import get_module_loader; loader = get_module_loader(); print(loader.list_available_providers('stt'))"
```

---

## 🎨 Customization Examples

### Example 1: Use Whisper for Better Accuracy

```yaml
# config/modules/stt.yaml
provider: "whisper"
whisper:
  model_size: "base"  # tiny, base, small, medium, large
  device: "cuda"      # or "cpu"
```

### Example 2: Premium Voice with ElevenLabs

```yaml
# config/modules/tts.yaml
provider: "elevenlabs"
elevenlabs:
  api_key: "your_key"
  voice_id: "specific_voice"
  stability: 0.5
```

### Example 3: Longer Recording Time

```yaml
# config/modules/stt.yaml
recording:
  phrase_time_limit: 30  # 30 seconds instead of 15
  pause_threshold: 1.5   # Wait longer for pauses
```

---

## 🔄 Migration from v3.0

### Changes Required

1. **Reorganize files** to new structure
2. **Create module configs** in `config/modules/`
3. **Update imports** to use new paths
4. **Test each module** independently

### Benefits

- ✅ Swap providers without code changes
- ✅ Test modules independently
- ✅ Clear separation of concerns
- ✅ Easy to add new implementations
- ✅ Configuration-driven behavior

---

## 📊 Module Status

| Module | Interface | Implementations | Config | Status |
|--------|-----------|----------------|--------|--------|
| Wake Word | ✅ | Vosk, Porcupine | ✅ | ⚠️ WIP |
| STT | ✅ | Google, Whisper | ✅ | ✅ Done |
| TTS | ✅ | gTTS, ElevenLabs, Piper | ✅ | ⚠️ WIP |
| Intent | ✅ | Simple AI, Advanced | ✅ | ✅ Done |
| Actions | ✅ | 4 categories | ✅ | ⚠️ WIP |

---

## 🎯 Next Steps

1. **Implement remaining providers**
   - Wake word detectors
   - TTS providers
   - Action categories

2. **Add RAG module**
   - Vector store
   - Retrieval
   - Indexing

3. **Add security module**
   - Confirmation flows
   - Permissions
   - Auth

4. **Test and optimize**
   - Resource usage
   - Latency
   - Accuracy

---

## 🤝 Contributing

### Adding a New Provider

1. Create `modules/<type>/<provider>.py`
2. Inherit from `<Type>Provider` base class
3. Implement required methods
4. Add config to `config/modules/<type>.yaml`
5. Test: `provider: "your_provider"`

### Adding a New Action

1. Create `modules/actions/<category>/<action>.py`
2. Inherit from `Action`
3. Set category
4. Implement `get_intents()` and `execute()`
5. Auto-discovered!

---

## 📚 Documentation

- **This README** - Architecture overview
- **Module READMEs** - In each module directory
- **Config Examples** - In `config/` directory
- **API Docs** - In `docs/` (coming soon)

---

## 🎉 Key Advantages

1. **True Modularity** - Each module is independent
2. **Easy Testing** - Test modules in isolation
3. **Configuration-Driven** - No code changes to switch providers
4. **Organized** - Actions by category
5. **Scalable** - Easy to add new implementations
6. **Clear** - Well-defined interfaces
7. **Flexible** - Mix and match providers

**This is a professional, maintainable architecture!** 🚀