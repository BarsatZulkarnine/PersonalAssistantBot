# Headless Mode - Raspberry Pi Deployment Guide

Run your voice assistant on Raspberry Pi without display/keyboard, accessible via API or remote control.

## Table of Contents
- [What is Headless Mode?](#what-is-headless-mode)
- [Hardware Requirements](#hardware-requirements)
- [Installation](#installation)
- [Configuration](#configuration)
- [Running Headless](#running-headless)
- [API Access](#api-access)
- [Auto-Start on Boot](#auto-start-on-boot)
- [Monitoring & Logs](#monitoring--logs)
- [Troubleshooting](#troubleshooting)

---

## What is Headless Mode?

Headless mode runs the assistant without:
- Display output
- Keyboard/mouse input
- Wake word detection (optional)
- TTS audio output (optional)

Perfect for:
- Raspberry Pi deployments
- Server/cloud hosting
- API integrations
- Home automation hubs
- IoT devices

---

## Hardware Requirements

### Minimum (API Only)
- Raspberry Pi 3B+ or newer
- 1GB RAM (2GB recommended)
- 8GB SD card
- Network connection (WiFi/Ethernet)

### Voice Capabilities (STT/TTS)
- USB microphone (for voice input)
- USB speaker/3.5mm audio (for voice output)
- Raspberry Pi 4 (2GB+ RAM recommended)

### Recommended Setup
- Raspberry Pi 4 (4GB RAM)
- 32GB SD card (for music cache, logs)
- USB microphone array (better voice detection)
- External USB sound card (better audio quality)
- Active cooling (fan/heatsink)

---

## Installation

### 1. Prepare Raspberry Pi

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Python 3.10+
sudo apt install python3 python3-pip python3-venv -y

# Install system dependencies
sudo apt install -y \
    portaudio19-dev \
    python3-pyaudio \
    ffmpeg \
    git \
    vim
```

### 2. Clone Repository

```bash
cd ~
git clone https://github.com/yourusername/voice-assistant.git
cd voice-assistant
```

### 3. Setup Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
```

### 4. Install Dependencies

```bash
pip install -r requirements.txt
```

### 5. Configure API Keys

```bash
# Copy example env file
cp .env.example .env

# Edit with your keys
nano .env
```

Add your API keys:
```env
OPENAI_API_KEY=sk-your-key-here
BRAVE_API_KEY=your-brave-key  # Optional for web search
```

---

## Configuration

### Headless Configuration File

Create `config/headless.yaml`:

```yaml
# Headless Mode Configuration
mode: headless

# Network Settings
network:
  host: 0.0.0.0  # Listen on all interfaces
  port: 5000
  allow_remote: true
  
# Modules (disable what you don't need)
modules:
  wake_word: false     # Disable wake word in headless
  stt: true           # Enable if using voice API
  tts: true           # Enable if using voice API
  intent: true        # Always needed
  actions: true       # Always needed
  
# Performance
performance:
  low_power_mode: true
  cache_enabled: true
  max_memory_mb: 512  # Limit for Raspberry Pi

# API Settings
api:
  enabled: true
  authentication: false  # Enable if exposing to internet
  rate_limit: 60  # Requests per minute
  
# Logging
logging:
  level: INFO
  console: false  # Disable console output
  file: true
  max_size_mb: 50
  
# Audio (for voice API)
audio:
  input_device: null   # Auto-detect microphone
  output_device: null  # Auto-detect speaker
  sample_rate: 16000
```

### Optimize for Raspberry Pi

Edit `config/modules/stt.yaml`:
```yaml
provider: "google"  # Lightweight, cloud-based

recording:
  timeout: 3
  phrase_time_limit: 10  # Shorter for faster response
  energy_threshold: 500  # Higher for noisy environments
```

Edit `config/modules/tts.yaml`:
```yaml
provider: "gtts"  # Lightweight

streaming:
  enabled: true
  chunk_size: "sentence"
```

Edit `config/modules/intent.yaml`:
```yaml
provider: "simple_ai"

simple_ai:
  model: "gpt-4o-mini"  # Faster, cheaper
  temperature: 0.3
```

---

## Running Headless

### Basic Headless Mode

```bash
# Start headless mode
python main.py --mode headless

# Or specify explicitly
python main.py --input text --output text --mode headless
```

### With Logging to File

```bash
# Run in background with logs
nohup python main.py --mode headless > /dev/null 2>&1 &

# Check if running
ps aux | grep python

# View logs
tail -f logs/assistant.log
```

### With systemd (Recommended)

Create service file:
```bash
sudo nano /etc/systemd/system/voice-assistant.service
```

Add:
```ini
[Unit]
Description=Voice Assistant - Headless Mode
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/voice-assistant
Environment="PATH=/home/pi/voice-assistant/venv/bin"
ExecStart=/home/pi/voice-assistant/venv/bin/python main.py --mode headless
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl daemon-reload
sudo systemctl enable voice-assistant
sudo systemctl start voice-assistant

# Check status
sudo systemctl status voice-assistant

# View logs
sudo journalctl -u voice-assistant -f
```

---

## API Access

### REST API Endpoints

The assistant exposes a REST API when running in headless mode.

#### Process Text Input
```bash
curl -X POST http://raspberry-pi-ip:5000/api/process \
  -H "Content-Type: application/json" \
  -d '{"text": "What is the weather today?"}'
```

Response:
```json
{
  "success": true,
  "response": "The current weather is...",
  "intent": "web",
  "processing_time_ms": 1234
}
```

#### Execute Action
```bash
curl -X POST http://raspberry-pi-ip:5000/api/action \
  -H "Content-Type: application/json" \
  -d '{"action": "play_music", "params": {"query": "jazz"}}'
```

#### Get Status
```bash
curl http://raspberry-pi-ip:5000/api/status
```

Response:
```json
{
  "status": "running",
  "uptime_seconds": 3600,
  "modules": {
    "stt": true,
    "tts": true,
    "intent": true,
    "actions": 4
  },
  "memory_usage_mb": 245,
  "cpu_percent": 12.5
}
```

### Python Client Example

```python
import requests

class VoiceAssistantClient:
    def __init__(self, host="http://192.168.1.100:5000"):
        self.host = host
    
    def process(self, text):
        response = requests.post(
            f"{self.host}/api/process",
            json={"text": text}
        )
        return response.json()
    
    def execute_action(self, action, params=None):
        response = requests.post(
            f"{self.host}/api/action",
            json={"action": action, "params": params or {}}
        )
        return response.json()
    
    def get_status(self):
        response = requests.get(f"{self.host}/api/status")
        return response.json()

# Usage
client = VoiceAssistantClient("http://192.168.1.50:5000")
result = client.process("Play some music")
print(result['response'])
```

### Home Assistant Integration

Add to `configuration.yaml`:
```yaml
rest_command:
  voice_assistant:
    url: http://192.168.1.50:5000/api/process
    method: POST
    content_type: "application/json"
    payload: '{"text": "{{ command }}"}'

automation:
  - alias: "Voice Assistant via HA"
    trigger:
      platform: event
      event_type: call_service
    action:
      service: rest_command.voice_assistant
      data:
        command: "{{ trigger.event.data.service_data.command }}"
```

---

## Auto-Start on Boot

### Method 1: systemd (Recommended)
Already covered above in "Running Headless" section.

### Method 2: cron
```bash
# Edit crontab
crontab -e

# Add line:
@reboot sleep 30 && cd /home/pi/voice-assistant && /home/pi/voice-assistant/venv/bin/python main.py --mode headless >> /home/pi/voice-assistant/logs/boot.log 2>&1
```

### Method 3: rc.local
```bash
sudo nano /etc/rc.local

# Add before 'exit 0':
su - pi -c "cd /home/pi/voice-assistant && /home/pi/voice-assistant/venv/bin/python main.py --mode headless &"
```

---

## Monitoring & Logs

### View Logs
```bash
# Real-time logs
tail -f logs/assistant.log

# Conversation logs
tail -f logs/conversations_$(date +%Y%m%d).log

# System logs (if using systemd)
sudo journalctl -u voice-assistant -f

# Last 100 lines
sudo journalctl -u voice-assistant -n 100
```

### Monitor Resources
```bash
# CPU and memory usage
htop

# Check disk space
df -h

# Check temperature (important for Pi!)
vcgencmd measure_temp
```

### Log Rotation
Logs auto-rotate at 10MB. Configure in `config/settings.yaml`:
```yaml
logging:
  max_size_mb: 10
  backup_count: 5  # Keep 5 old logs
```

---

## Troubleshooting

### Assistant Won't Start

Check logs:
```bash
sudo journalctl -u voice-assistant -n 50
```

Common issues:
- Missing API keys in `.env`
- Port 5000 already in use
- Virtual environment not activated

### High CPU Usage

Optimize configuration:
```yaml
# config/headless.yaml
performance:
  low_power_mode: true
  max_memory_mb: 512
```

### Audio Not Working

Check devices:
```bash
# List audio devices
arecord -l  # Microphones
aplay -l    # Speakers

# Test microphone
arecord -d 5 test.wav
aplay test.wav

# Set default device in config/modules/stt.yaml
recording:
  device_index: 1  # Your device number
```

### Can't Connect Remotely

Check firewall:
```bash
# Open port
sudo ufw allow 5000

# Check if listening
sudo netstat -tlnp | grep 5000
```

### Out of Memory

Reduce memory usage:
```yaml
# config/modules/music.yaml
youtube:
  cache_limit_mb: 200  # Lower cache limit

# config/settings.yaml
performance:
  max_memory_mb: 512
  cache_responses: false  # Disable caching
```

---

## Performance Tips

### 1. Use Lightweight Models
```yaml
# config/modules/intent.yaml
simple_ai:
  model: "gpt-4o-mini"  # Fastest
```

### 2. Disable Unused Features
```yaml
# config/modules/wake_word.yaml
enabled: false  # Don't need in headless

# config/modules/music.yaml
youtube:
  enabled: false  # If not using music
```

### 3. Optimize Audio Settings
```yaml
# config/modules/stt.yaml
recording:
  sample_rate: 16000  # Lower = less CPU
  phrase_time_limit: 10  # Shorter recordings
```

### 4. Add Swap (for low memory Pi)
```bash
# Create 2GB swap
sudo dd if=/dev/zero of=/swapfile bs=1M count=2048
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile

# Make permanent
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

### 5. Overclock (Carefully!)
```bash
sudo nano /boot/config.txt

# Add (Pi 4):
over_voltage=6
arm_freq=2000
```

---

## Security Considerations

### 1. Enable Authentication
```yaml
# config/headless.yaml
api:
  authentication: true
  api_key: "your-secret-key-here"
```

### 2. Use Firewall
```bash
# Only allow local network
sudo ufw allow from 192.168.1.0/24 to any port 5000
```

### 3. Run as Non-Root User
Never run as root! Use `pi` user or create dedicated user:
```bash
sudo useradd -m -s /bin/bash assistant
sudo su - assistant
```

### 4. Use HTTPS (Production)
Set up reverse proxy with nginx + Let's Encrypt.

---

## Advanced: Docker Deployment

Create `Dockerfile`:
```dockerfile
FROM python:3.10-slim

WORKDIR /app
COPY . /app

RUN apt-get update && apt-get install -y \
    portaudio19-dev \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

RUN pip install -r requirements.txt

CMD ["python", "main.py", "--mode", "headless"]
```

Build and run:
```bash
docker build -t voice-assistant .
docker run -d \
  --name assistant \
  -p 5000:5000 \
  -v $(pwd)/logs:/app/logs \
  -v $(pwd)/config:/app/config \
  --restart unless-stopped \
  voice-assistant
```

---

## Support

For issues or questions:
- GitHub Issues: [link]
- Documentation: [link]
- Discord: [link]

---

## License

MIT License - See LICENSE file for details.