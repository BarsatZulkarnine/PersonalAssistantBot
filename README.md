# 🎤 Voice Assistant v2.0

A modular, extensible voice-activated AI assistant with hotword detection, plugin-based actions, and intelligent routing.

## 🏗️ Architecture

```
assistant/
├── app/
│   ├── main.py                  # Entry point & main loop
│   ├── router.py                # Request routing & orchestration
│   │
│   ├── actions/                 # Plugin-based action system
│   │   ├── __init__.py
│   │   ├── base.py             # Base Action class
│   │   ├── registry.py         # Action auto-discovery
│   │   ├── smart_home.py       # Smart home control
│   │   ├── system.py           # System actions (volume, apps)
│   │   ├── web.py              # Web search
│   │   └── conversation.py     # General AI chat
│   │
│   └── utils/
│       ├── config.py           # Centralized configuration
│       ├── logger.py           # Structured logging
│       └── speech.py           # STT, TTS, hotword detection
│
├── config/
│   ├── settings.yaml           # App settings
│   └── actions.yaml            # Action configurations
│
├── scripts/                    # Pre-written automation scripts
│   ├── email_sender.py
│   └── todo_manager.py
│
├── data/
│   ├── rag/                    # Personal knowledge base
│   └── cache/                  # Response cache
│
├── logs/                       # Application logs
│   ├── assistant.log
│   └── conversations_*.log
│
├── Dockerfile
├── requirements.txt
└── README.md
```

## 🚀 Tech Stack

- **Speech Recognition**: Google Speech Recognition
- **Text-to-Speech**: gTTS (modular, supports multiple providers)
- **AI/LLM**: OpenAI GPT-4o-mini
- **Action System**: Plugin-based with auto-discovery
- **Configuration**: YAML-based
- **Logging**: Python logging with rotation

## ✅ Implementation Checklist

### **Phase 1: Foundation ✅ COMPLETED**

#### Core Systems
- [x] **Centralized Configuration System**
  - [x] YAML-based settings (`config/settings.yaml`)
  - [x] Action configurations (`config/actions.yaml`)
  - [x] Config loader with dot notation access
  - [x] Environment variable support

- [x] **Structured Logging System**
  - [x] Multiple log levels (DEBUG, INFO, WARNING, ERROR)
  - [x] File rotation (size-based)
  - [x] Separate conversation logs
  - [x] Console + file output
  - [x] Contextual loggers per module

- [x] **Error Handling**
  - [x] Graceful error recovery in main loop
  - [x] Action-level error handling
  - [x] Custom ActionError exception
  - [x] Detailed error logging

#### Action Plugin System
- [x] **Base Action Architecture**
  - [x] Abstract base class (`Action`)
  - [x] Security levels (SAFE, CONFIRM, AUTH_REQUIRED)
  - [x] ActionResult data structure
  - [x] Intent matching system
  - [x] Validation framework

- [x] **Action Registry**
  - [x] Auto-discovery of action plugins
  - [x] Action registration system
  - [x] Intent-based routing
  - [x] Action execution with error handling

- [x] **Migrated Existing Actions**
  - [x] SmartHomeAction (light control)
  - [x] SystemAction (volume, app launching)
  - [x] WebSearchAction (web queries)
  - [x] ConversationAction (general chat)

---

### **Phase 2: Speech Enhancements** 🚧 IN PROGRESS

#### Speech Input (STT)
- [x] Basic speech recognition (Google STT)
- [x] Hotword detection ("Hey Pi")
- [ ] **Improvements Needed:**
  - [ ] Better error handling for network failures
  - [ ] Adjustable timeout via config
  - [ ] Alternative STT (Whisper for offline)
  - [ ] Background noise filtering
  - [ ] Multi-language support

#### Speech Output (TTS)
- [x] Basic TTS (gTTS)
- [ ] **Streaming TTS** ⚡ HIGH PRIORITY
  - [ ] Sentence-by-sentence playback
  - [ ] Queue system for smooth transitions
  - [ ] Reduce latency for long responses
  - [ ] Handle interruptions gracefully

- [ ] **Pluggable TTS Providers**
  - [ ] TTS provider interface
  - [ ] Refactor gTTS as provider
  - [ ] ElevenLabs integration (premium voices)
  - [ ] Piper TTS (offline/local)
  - [ ] Azure/Google Cloud TTS
  - [ ] Voice selection via config

- [ ] **TTS Improvements**
  - [ ] Better temp file management
  - [ ] Voice speed/pitch controls
  - [ ] Emotion/tone support
  - [ ] Caching for common phrases

---

### **Phase 3: Intent & Intelligence** 🔮 PLANNED

#### Intent Classification
- [ ] **Improved Intent Classifier**
  - [ ] Structured output (JSON intent + params)
  - [ ] Parameter extraction from prompts
  - [ ] Confidence scoring
  - [ ] Multi-intent handling
  - [ ] Context-aware classification

- [ ] **Intent Examples:**
  ```
  "Send email to John about meeting"
  → Intent: send_email
  → Params: {recipient: "John", subject: "meeting"}
  ```

#### Confirmation System
- [ ] **User Confirmation Flow**
  - [ ] Confirmation prompts for sensitive actions
  - [ ] Read-back before execution (emails, etc.)
  - [ ] Voice confirmation ("yes"/"no")
  - [ ] Timeout handling
  - [ ] Confirmation history

---

### **Phase 4: Productivity Features** 📝 PLANNED

#### Todo Management
- [ ] Todo action plugin
- [ ] Add tasks via voice
- [ ] View/list todos
- [ ] Mark complete
- [ ] Priority setting
- [ ] Due dates
- [ ] Integration with pre-written script

#### Email Management
- [ ] Email action plugin
- [ ] Draft generation
- [ ] Recipient extraction
- [ ] Confirmation flow
- [ ] Send via pre-written script
- [ ] Multiple recipients
- [ ] Attachment support

#### Calendar Integration
- [ ] Calendar action plugin
- [ ] Add events
- [ ] View schedule
- [ ] Set reminders
- [ ] Recurring events

---

### **Phase 5: RAG & Personal Knowledge** 🧠 PLANNED

#### RAG System
- [ ] **Vector Store Setup**
  - [ ] Choose vector DB (ChromaDB/FAISS)
  - [ ] Document indexer
  - [ ] Embedding generation
  - [ ] Retrieval system

- [ ] **Personal Knowledge Base**
  - [ ] Index personal documents
  - [ ] Query personal info
  - [ ] Context-aware responses
  - [ ] Update knowledge base
  - [ ] Privacy controls

#### Use Cases
- "What did I discuss with John last week?"
- "Show me notes from Q3 planning"
- "Remind me what I need to do for the project"

---

### **Phase 6: Smart Home Expansion** 🏠 PLANNED

#### Smart Home Integration
- [ ] **Actual API Integration**
  - [ ] Philips Hue
  - [ ] Home Assistant
  - [ ] MQTT support
  - [ ] Custom integrations

- [ ] **Enhanced Control**
  - [ ] Multiple lights/rooms
  - [ ] Brightness control
  - [ ] Color control
  - [ ] Scenes/routines
  - [ ] Temperature control
  - [ ] Security systems

---

### **Phase 7: Advanced Features** 🚀 PLANNED

#### Pre-written Scripts
- [ ] **Script System**
  - [ ] Script executor framework
  - [ ] Parameter passing
  - [ ] Output handling
  - [ ] Error handling

- [ ] **Scripts to Create**
  - [ ] Email sender
  - [ ] Todo manager
  - [ ] Calendar sync
  - [ ] File organizer
  - [ ] Backup utility

#### Performance
- [ ] Response caching
- [ ] Parallel action execution
- [ ] Model optimization (use cheaper models when possible)
- [ ] Request batching

#### Security
- [ ] API key encryption
- [ ] User authentication (multi-user)
- [ ] Audit logging
- [ ] Rate limiting
- [ ] Sandboxed script execution

---

### **Phase 8: Deployment & Polish** 🐳 PLANNED

#### Deployment
- [ ] Validate Dockerfile
- [ ] Docker Compose setup
- [ ] Environment variables
- [ ] Systemd service file
- [ ] Auto-start on boot
- [ ] Health check endpoints
- [ ] Update mechanism

#### User Experience
- [ ] Conversation context memory
- [ ] Multi-turn conversations
- [ ] Follow-up questions
- [ ] Better error messages
- [ ] User feedback collection
- [ ] Voice customization
- [ ] Wake word customization

---

## 📊 Progress Summary

| Phase | Status | Progress |
|-------|--------|----------|
| Phase 1: Foundation | ✅ Complete | 100% |
| Phase 2: Speech | 🚧 In Progress | 40% |
| Phase 3: Intent & Intelligence | 🔮 Planned | 0% |
| Phase 4: Productivity | 🔮 Planned | 0% |
| Phase 5: RAG | 🔮 Planned | 0% |
| Phase 6: Smart Home | 🔮 Planned | 0% |
| Phase 7: Advanced | 🔮 Planned | 0% |
| Phase 8: Deployment | 🔮 Planned | 0% |

**Overall Progress: ~15%**

---

## 🎯 Quick Start

### Installation

```bash
# Clone repository
git clone <repo-url>
cd assistant

# Install dependencies
pip install -r requirements.txt

# Setup environment
cp .env.example .env
# Add your OPENAI_API_KEY to .env

# Create config files
mkdir -p config logs data/rag data/cache scripts
```

### Configuration

Edit `config/settings.yaml` and `config/actions.yaml` to customize behavior.

### Run

```bash
python -m app.main
```

Say "Hey Pi" to activate, then speak your command!

---

## 🔧 Creating New Actions

```python
from app.actions.base import Action, ActionResult, SecurityLevel

class MyAction(Action):
    def __init__(self):
        super().__init__()
        self.description = "What this action does"
        self.security_level = SecurityLevel.SAFE
    
    def get_intents(self) -> List[str]:
        return ["my intent", "another intent"]
    
    async def execute(self, prompt: str, params=None) -> ActionResult:
        # Your action logic here
        return ActionResult(
            success=True,
            message="Action completed!"
        )
```

Save in `app/actions/my_action.py` - it will be auto-discovered!

---

## 📝 Logs

- **Main log**: `logs/assistant.log` (with rotation)
- **Conversations**: `logs/conversations_YYYYMMDD.log`

---

## 🤝 Contributing

1. Check the checklist above for features to implement
2. Create a new action plugin for new capabilities
3. Update configuration files as needed
4. Add tests (coming soon!)
5. Submit PR

---

## 📄 License

MIT

---

## 🎉 Next Steps

**Immediate priorities:**
1. ✅ Streaming TTS (sentence-by-sentence)
2. ✅ Improved intent classifier with parameters
3. ✅ Confirmation flow implementation
4. ✅ Todo & email actions

Let's build something awesome! 🚀