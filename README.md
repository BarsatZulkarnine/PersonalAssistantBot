# 🎙️ Modular Voice Assistant

A fully modular, extensible voice assistant with intelligent memory, document search (RAG), and n8n workflow integration.

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

---

## ✨ Key Features

### 🧠 **Intelligent Memory System**
- Remembers personal information, preferences, and past conversations
- Hybrid SQL + Vector storage for semantic recall
- Automatic classification of important information
- **Cost**: ~$1/month for 1000 conversations

### 📚 **Document Search (RAG)**
- Search your personal documents (PDF, DOCX, TXT, Markdown, HTML)
- Semantic understanding of document content
- Completely local and private
- Smart chunking preserves context

### 🔗 **n8n Workflow Integration**
- Connect to 100+ services (Gmail, Slack, GitHub, etc.)
- Visual workflow editor
- No code required
- Self-hosted and private

### 🎤 **Modular Architecture**
- Swap any component without code changes
- Choose your providers via config files
- Easy to extend with new actions
- Clean separation of concerns

---

## 🚀 Quick Start

### 1. Installation

```bash
# Clone repository
git clone https://github.com/yourusername/voice-assistant.git
cd voice-assistant

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configuration

```bash
# Copy environment template
cp .env.example .env

# Add your OpenAI API key (required)
echo "OPENAI_API_KEY=sk-your-key-here" >> .env
```

### 3. Run

```bash
# Voice mode (voice input + voice output)
python main.py --mode voice

# Text mode (text input + text output)
python main.py --mode text

# Mixed modes
python main.py --input voice --output text  # Voice input, text output
python main.py --input text --output voice  # Text input, voice output
```

---

## 📋 What's Included

### Core Modules

| Module | Purpose | Swappable Providers |
|--------|---------|-------------------|
| **Wake Word** | Detect activation phrase | Simple (Google), Vosk, Porcupine |
| **STT** | Speech-to-Text | Google ✅, Whisper, Azure |
| **TTS** | Text-to-Speech | gTTS, OpenAI ✅, ElevenLabs, Piper |
| **Intent** | Classify user requests | Simple AI ✅, Advanced |
| **Actions** | Execute commands | See Actions below |
| **Memory** | Remember conversations | SQL + ChromaDB ✅ |
| **RAG** | Search documents | Hybrid retrieval ✅ |

✅ = Currently active (see `config/modules/`)

### Actions by Category

**🏠 Home Automation** (via n8n)
- Smart lights, thermostats, locks
- Integrates with Home Assistant

**📝 Productivity** (via n8n)
- Email (Gmail, Outlook)
- Calendar (Google, Outlook)
- Notes (Joplin, Notion)
- Tasks (Todoist, ClickUp, Asana)
- Slack/Discord notifications
- GitHub issues

**💻 System Control** (local)
- Volume control
- Launch applications

**🎵 Entertainment** (local)
- Music playback with YouTube support
- Auto-pause for voice commands

**💬 Conversation** (local)
- AI chat with memory context
- Web search (Brave API)

---

## 🎯 Usage Examples

### Basic Conversation
```
You: "Hey Pi"
Assistant: "Yes?"
You: "My name is Alice and I live in Melbourne"
Assistant: "Nice to meet you, Alice!"

[Later...]
You: "Hey Pi"
Assistant: "Yes?"
You: "What's my name?"
Assistant: "Your name is Alice!"
```

### Document Search
```
You: "Hey Pi"
Assistant: "Yes?"
You: "What does my Python guide say about decorators?"
Assistant: "Based on your Python guide, decorators allow you to..."
```

### n8n Workflows
```
You: "Hey Pi"
Assistant: "Yes?"
You: "Send an email to John about the meeting"
Assistant: "Email sent to john@example.com"
```

### Music Control
```
You: "Hey Pi, play some jazz"
Assistant: "Now playing: Take Five by Dave Brubeck"

[Music auto-pauses when you say "Hey Pi"]
You: "Hey Pi, what's the weather?"
Assistant: "It's 22°C and sunny..."
[Music auto-resumes after response]
```

---

## 📚 Documentation

### Getting Started
- **[Installation Guide](docs/INSTALLATION.md)** - Detailed setup instructions
- **[Configuration Guide](docs/CONFIGURATION.md)** - Configure all modules
- **[Quick Start Examples](docs/QUICK_START.md)** - Common usage patterns

### Core Systems
- **[Memory System](docs/MEMORY_SYSTEM.md)** - How intelligent memory works
- **[RAG System](docs/RAG_SYSTEM.md)** - Document search explained
- **[n8n Integration](docs/N8N_INTEGRATION.md)** - Connect external services

### Module Documentation
- **[Wake Word Detection](docs/modules/WAKE_WORD.md)** - Activation phrase detection
- **[Speech-to-Text](docs/modules/STT.md)** - Voice recognition
- **[Text-to-Speech](docs/modules/TTS.md)** - Voice synthesis
- **[Intent Detection](docs/modules/INTENT.md)** - Understanding requests
- **[Actions System](docs/modules/ACTIONS.md)** - Extensible commands

### Development
- **[Architecture Overview](docs/ARCHITECTURE.md)** - System design
- **[Adding Actions](docs/dev/ADDING_ACTIONS.md)** - Create custom commands
- **[Adding Providers](docs/dev/ADDING_PROVIDERS.md)** - New STT/TTS providers
- **[API Reference](docs/dev/API_REFERENCE.md)** - Code documentation

### Deployment
- **[Raspberry Pi Setup](docs/deployment/RASPBERRY_PI.md)** - Deploy on Pi
- **[Docker Deployment](docs/deployment/DOCKER.md)** - Container deployment
- **[Headless Mode](docs/deployment/HEADLESS.md)** - Run without display

### Troubleshooting
- **[Common Issues](docs/TROUBLESHOOTING.md)** - Solutions to common problems
- **[FAQ](docs/FAQ.md)** - Frequently asked questions

---

## 🎨 Configuration Examples

### Switch to Whisper STT
```yaml
# config/modules/stt.yaml
provider: "whisper"
whisper:
  model_size: "base"
  device: "cuda"  # or "cpu"
```

### Use ElevenLabs TTS
```yaml
# config/modules/tts.yaml
provider: "elevenlabs"
elevenlabs:
  api_key: "your_key"
  voice_id: "specific_voice"
```

### Enable More Actions
```yaml
# config/modules/actions.yaml
productivity:
  n8n:
    enabled: true
    
entertainment:
  music:
    enabled: true
```

---

## 💰 Cost Breakdown

| Component | Provider | Cost |
|-----------|----------|------|
| **STT** | Google (free tier) | $0/month |
| **TTS** | OpenAI | ~$2/month |
| **AI Chat** | OpenAI (gpt-4o-mini) | ~$1/month |
| **Memory Classification** | OpenAI | ~$1/month |
| **Memory Storage** | Local (SQLite + ChromaDB) | $0 |
| **RAG** | Local (embeddings) | $0 |
| **n8n** | Self-hosted | $0 |
| **Web Search** | Brave API (free tier) | $0/month |
| **Total** | | **~$4/month** |

*Based on moderate usage (1000 conversations/month)*

---

## 🛠️ Technology Stack

- **Python 3.10+** - Core language
- **OpenAI API** - AI processing
- **SpeechRecognition** - Voice input
- **pygame** - Audio playback
- **SQLite** - Structured data storage
- **ChromaDB** - Vector embeddings
- **n8n** - Workflow automation
- **yt-dlp** - YouTube music support

---

## 📊 System Requirements

### Minimum
- Python 3.10+
- 2GB RAM
- Microphone (for voice input)
- Speaker (for voice output)
- Internet connection

### Recommended
- Python 3.11+
- 4GB RAM
- USB microphone (better quality)
- Dedicated speaker/headphones
- Fast internet connection

### Optional
- NVIDIA GPU (for Whisper STT)
- Raspberry Pi 4 (for deployment)

---

## 🤝 Contributing

Contributions are welcome! Please read our [Contributing Guide](docs/CONTRIBUTING.md) first.

### Areas for Contribution
- New action implementations
- Additional STT/TTS providers
- Improved wake word detection
- Documentation improvements
- Bug fixes and testing

---

## 📝 License

MIT License - See [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- OpenAI for GPT models and TTS
- Google for Speech Recognition
- ChromaDB for vector storage
- n8n for workflow automation
- All open-source contributors

---

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/yourusername/voice-assistant/issues)
- **Discussions**: [GitHub Discussions](https://github.com/yourusername/voice-assistant/discussions)
- **Documentation**: [docs/](docs/)

---

## 🗺️ Roadmap

- [x] Modular architecture
- [x] Memory system with RAG
- [x] n8n integration
- [x] Music playback with YouTube
- [ ] Multi-user support
- [ ] Mobile app
- [ ] Voice training/customization
- [ ] Plugin marketplace
- [ ] Cloud sync (optional)

---

**Built with ❤️ for voice-first interaction**