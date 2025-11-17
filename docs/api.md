# Voice Assistant API Documentation

A comprehensive REST API and WebSocket server for a multi-modal AI voice assistant with memory, RAG, music playback, and real-time event streaming.

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Getting Started](#getting-started)
- [Authentication](#authentication)
- [Core Concepts](#core-concepts)
- [REST API Endpoints](#rest-api-endpoints)
- [WebSocket API](#websocket-api)
- [Event System](#event-system)
- [Error Handling](#error-handling)
- [Examples](#examples)
- [Deployment](#deployment)

---

## Overview

The Voice Assistant API provides a comprehensive interface for building conversational AI applications with support for:

- **Multi-client chat** with session isolation
- **Long-term memory** (facts and conversation history)
- **RAG (Retrieval Augmented Generation)** for document-based Q&A
- **Music playback** with streaming capabilities
- **Real-time events** via WebSocket
- **Session management** for multiple concurrent users

### Key Features

- ✅ RESTful API for all core functions
- ✅ WebSocket for real-time bidirectional communication
- ✅ Session-based conversation tracking
- ✅ Memory persistence across sessions
- ✅ Document upload and semantic search
- ✅ Music library management and streaming
- ✅ Event bus for real-time notifications
- ✅ Auto-reconnect support
- ✅ Comprehensive error handling

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      Client Applications                     │
│  (Web UI, Mobile App, Raspberry Pi, CLI Tools)              │
└────────────┬─────────────────────────────────┬──────────────┘
             │                                 │
             │ REST API                        │ WebSocket
             │                                 │
┌────────────▼─────────────────────────────────▼──────────────┐
│                     FastAPI Server                           │
│  ┌──────────────────────────────────────────────────────┐   │
│  │              API Routes Layer                         │   │
│  │  • chat.py    • music.py   • memory.py               │   │
│  │  • rag.py     • system.py  • sessions.py             │   │
│  └──────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────┐   │
│  │            WebSocket Handler                          │   │
│  │  • Real-time events  • Auto-reconnect                │   │
│  └──────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────┐   │
│  │            Conversation Service                       │   │
│  │  • Intent Detection  • Action Execution              │   │
│  │  • Memory Integration  • RAG Integration             │   │
│  └──────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────┘
             │                                 │
    ┌────────▼────────┐              ┌────────▼────────┐
    │  Memory System  │              │   RAG System    │
    │  (SQLite)       │              │  (Vector Store) │
    └─────────────────┘              └─────────────────┘
```

### Technology Stack

- **Framework**: FastAPI 
- **WebSocket**: Native FastAPI WebSocket support
- **Memory**: SQLite with custom ORM
- **RAG**: Vector embeddings with semantic search
- **Music**: Local file streaming + YouTube integration
- **Events**: Custom event bus with pub/sub

---

## Getting Started

### Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/voice-assistant.git
cd voice-assistant

# Install dependencies
pip install -r requirements.txt

# Start the server
uvicorn api.main:app --reload --port 8000
```

### Quick Test

```bash
# Health check
curl http://localhost:8000/health

# Send a chat message
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Hello, how are you?",
    "user_id": "test_user",
    "client_type": "web"
  }'
```

### Environment Variables

```bash
# Optional configuration
export LOG_LEVEL=INFO
export MUSIC_LIBRARY_PATH=/path/to/music
export MEMORY_DB_PATH=data/memory.db
export RAG_INDEX_PATH=data/rag_index
```

---

## Authentication

Currently, the API uses a simple user identification system:

- `user_id`: String identifier for the user (default: "default_user")
- `session_id`: Optional session identifier (auto-generated if not provided)
- `client_type`: Descriptor of the client (e.g., "web", "mobile", "raspberry_pi")

**Note**: This is suitable for development and trusted environments. For production, implement proper authentication (JWT, OAuth, API keys) before the endpoint layer.

---

## Core Concepts

### Sessions

Each conversation is isolated by a unique `session_id`. Sessions are:

- **Auto-generated** if not provided (format: `{user_id}_{timestamp}_{uuid}`)
- **Persistent** across reconnections
- **Isolated** from other sessions
- **Trackable** via the `/api/sessions` endpoint

### Memory System

The assistant maintains two types of memory:

1. **Conversation History**: Complete chat logs with intent and action tracking
2. **User Facts**: Extracted knowledge organized by category (preferences, personal info, etc.)

Memory is stored per `user_id` and accessible across all sessions.

### RAG (Retrieval Augmented Generation)

Upload documents to create a searchable knowledge base:

- Supports: PDF, TXT, MD, DOCX
- Automatically chunks and indexes content
- Semantic search retrieves relevant context
- Integrates transparently into conversations

### Event System

Real-time events are broadcast via WebSocket:

- `MESSAGE_RECEIVED`: New chat messages
- `MUSIC_PLAY`, `MUSIC_PAUSE`, etc.: Music control events
- `MEMORY_STORED`: New facts extracted
- `STATUS_UPDATE`: System status changes
- `ERROR`: Error notifications

---

## REST API Endpoints

### Base URL

```
http://localhost:8000
```

### Chat Endpoints

#### POST `/api/chat`

Send a message and receive a response.

**Request Body:**
```json
{
  "message": "Play some jazz music",
  "session_id": "user1_20250116_abc123",  // optional
  "user_id": "user1",                      // default: "default_user"
  "client_type": "web"                     // default: "server"
}
```

**Response:**
```json
{
  "response": "Playing jazz music from the library.",
  "intent": "play_music",
  "confidence": 0.95,
  "action_executed": "MusicAction",
  "action_data": {
    "action": "play_music",
    "music": {
      "name": "Miles Davis - Kind of Blue",
      "type": "local"
    }
  },
  "memory_stored": false,
  "memory_category": null,
  "rag_used": false,
  "duration_ms": 234.5,
  "session_id": "user1_20250116_abc123",
  "metadata": {
    "session_id": "user1_20250116_abc123",
    "user_id": "user1",
    "client_type": "web",
    "timestamp": "2025-01-16T10:30:00"
  }
}
```

#### POST `/api/chat/stream`

Stream response word-by-word using Server-Sent Events (SSE).

**Request Body:** Same as `/api/chat`

**Response Stream:**
```
data: {"word": "I", "done": false}

data: {"word": "can", "done": false}

data: {"word": "help", "done": false}

data: {"word": "", "done": true, "metadata": {...}}
```

---

### Music Endpoints

#### POST `/api/music/control`

Control music playback.

**Request Body:**
```json
{
  "action": "play",           // play, pause, resume, stop, next, previous
  "song_name": "Kind of Blue" // required for 'play'
}
```

**Response:**
```json
{
  "success": true,
  "message": "Playing: Miles Davis - Kind of Blue",
  "status": {
    "state": "playing",
    "current_song": "Miles Davis - Kind of Blue",
    "volume": 0.8,
    "shuffle": false,
    "repeat": "none",
    "queue_length": 5,
    "library_size": 42
  }
}
```

#### GET `/api/music/status`

Get current music player status.

**Response:**
```json
{
  "state": "playing",
  "current_song": "Miles Davis - Kind of Blue",
  "volume": 0.8,
  "shuffle": false,
  "repeat": "none",
  "queue_length": 5,
  "library_size": 42
}
```

#### GET `/api/music/library`

List all available songs.

**Response:**
```json
{
  "total": 42,
  "songs": [
    {
      "name": "Miles Davis - Kind of Blue",
      "type": "local",
      "artist": "Miles Davis",
      "album": "Kind of Blue",
      "duration": 540
    }
  ]
}
```

#### GET `/api/music/stream/{song_name}`

Stream a music file for playback.

**Response:** Binary audio stream (audio/mpeg)

**Note:** Only works for local files. YouTube links are played directly by the client.

---

### Memory Endpoints

#### GET `/api/conversations`

Get conversation history.

**Query Parameters:**
- `limit`: Number of conversations (default: 50)
- `session_id`: Filter by session (optional)
- `user_id`: Filter by user (default: "default_user")

**Response:**
```json
[
  {
    "id": 1,
    "session_id": "user1_20250116_abc123",
    "turn_no": 1,
    "user_input": "Play jazz music",
    "assistant_response": "Playing jazz from library",
    "intent_type": "play_music",
    "timestamp": "2025-01-16T10:30:00"
  }
]
```

#### GET `/api/memory/facts`

Get stored user facts.

**Query Parameters:**
- `limit`: Number of facts (default: 20)
- `category`: Filter by category (optional: personal, preferences, context, other)
- `user_id`: Filter by user (default: "default_user")

**Response:**
```json
[
  {
    "id": 1,
    "content": "User enjoys jazz music, particularly Miles Davis",
    "category": "preferences",
    "importance_score": 0.8,
    "created_at": "2025-01-16T10:30:00"
  }
]
```

#### DELETE `/api/memory/facts/{fact_id}`

Delete a specific fact.

**Query Parameters:**
- `user_id`: User identifier (default: "default_user")

**Response:**
```json
{
  "success": true,
  "message": "Fact 1 deleted"
}
```

#### GET `/api/memory/stats`

Get memory system statistics.

**Response:**
```json
{
  "total_facts": 15,
  "facts_by_category": {
    "personal": 5,
    "preferences": 8,
    "context": 2
  },
  "total_conversations": 42,
  "oldest_conversation": "2025-01-10T08:00:00",
  "newest_conversation": "2025-01-16T10:30:00"
}
```

---

### RAG Endpoints

#### POST `/api/rag/upload`

Upload a document for indexing.

**Form Data:**
- `file`: Document file (PDF, TXT, MD, DOCX)
- `user_id`: User identifier (default: "default_user")

**Response:**
```json
{
  "success": true,
  "filename": "manual.pdf",
  "chunks": 42,
  "message": "Document indexed successfully (42 chunks)"
}
```

#### GET `/api/rag/stats`

Get RAG system statistics.

**Response:**
```json
{
  "total_documents": 5,
  "total_chunks": 210,
  "average_chunk_size": 512
}
```

---

### Session Endpoints

#### GET `/api/sessions`

Get list of active sessions.

**Response:**
```json
{
  "total": 3,
  "sessions": {
    "user1_20250116_abc123": {
      "user_id": "user1",
      "client_type": "web",
      "created_at": "2025-01-16T10:00:00",
      "last_activity": "2025-01-16T10:30:00",
      "websocket_connected": true
    }
  }
}
```

#### DELETE `/api/sessions/{session_id}`

Close a specific session.

**Response:**
```json
{
  "success": true,
  "message": "Session user1_20250116_abc123 closed"
}
```

---

### System Endpoints

#### GET `/health`

Health check endpoint.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2025-01-16T10:30:00",
  "service_ready": true,
  "event_bus": true,
  "active_sessions": 3
}
```

#### GET `/api/system/status`

Get detailed system status.

**Response:**
```json
{
  "status": "active",
  "features": {
    "conversation": true,
    "memory": true,
    "rag": true,
    "event_bus": true,
    "music_streaming": true,
    "session_isolation": true,
    "websocket": true
  },
  "stats": {
    "memory_enabled": true,
    "rag_enabled": true,
    "total_sessions": 3,
    "memory": {
      "total_facts": 15,
      "total_conversations": 42
    },
    "rag": {
      "total_documents": 5,
      "total_chunks": 210
    }
  }
}
```

#### GET `/api/system/events/stats`

Get event bus statistics.

**Response:**
```json
{
  "total_events_emitted": 156,
  "events_by_type": {
    "MESSAGE_RECEIVED": 42,
    "MUSIC_PLAY": 8,
    "MEMORY_STORED": 5
  },
  "active_connections": 3,
  "active_sessions": {
    "user1_20250116_abc123": {
      "user_id": "user1",
      "client_type": "web",
      "websocket_connected": true,
      "created_at": "2025-01-16T10:00:00"
    }
  }
}
```

---

## WebSocket API

### Connection

**Endpoint:** `ws://localhost:8000/ws`

**Query Parameters:**
- `session_id`: Session identifier (optional, auto-generated if not provided)
- `user_id`: User identifier (default: "default_user")
- `client_type`: Client type (default: "unknown")

**Example:**
```javascript
const ws = new WebSocket(
  'ws://localhost:8000/ws?user_id=user1&client_type=web'
);
```

### Connection Lifecycle

1. **Connect**: Client establishes WebSocket connection
2. **Welcome**: Server sends connection confirmation
3. **Subscribe**: Client subscribes to event types
4. **Events**: Server broadcasts events
5. **Disconnect**: Clean disconnection with reconnect support

### Welcome Message

Upon connection, the server sends:

```json
{
  "type": "connected",
  "session_id": "user1_20250116_abc123",
  "user_id": "user1",
  "timestamp": "2025-01-16T10:30:00",
  "features": {
    "chat": true,
    "events": true,
    "music": true,
    "memory": true,
    "rag": true
  }
}
```

### Client → Server Messages

#### Ping

Keep connection alive.

```json
{
  "type": "ping"
}
```

**Response:**
```json
{
  "type": "pong",
  "timestamp": "2025-01-16T10:30:00"
}
```

#### Subscribe to Events

```json
{
  "type": "subscribe",
  "events": ["MESSAGE_RECEIVED", "MUSIC_PLAY", "MEMORY_STORED"]
}
```

**Response:**
```json
{
  "type": "subscribed",
  "events": ["MESSAGE_RECEIVED", "MUSIC_PLAY", "MEMORY_STORED"],
  "timestamp": "2025-01-16T10:30:00"
}
```

#### Unsubscribe from Events

```json
{
  "type": "unsubscribe",
  "events": ["MUSIC_PLAY"]
}
```

#### Send Chat Message

```json
{
  "type": "chat",
  "message": "Play some jazz music"
}
```

**Response:**
```json
{
  "type": "chat_response",
  "response": "Playing jazz music from the library.",
  "intent": "play_music",
  "action_data": { ... },
  "timestamp": "2025-01-16T10:30:00"
}
```

#### Music Control

```json
{
  "type": "music_control",
  "action": "play",
  "song_name": "Kind of Blue"
}
```

### Server → Client Events

#### Event Structure

All events follow this structure:

```json
{
  "type": "event",
  "event_type": "MESSAGE_RECEIVED",
  "data": { ... },
  "session_id": "user1_20250116_abc123",
  "user_id": "user1",
  "timestamp": "2025-01-16T10:30:00",
  "event_id": "evt_abc123"
}
```

#### Event Types

**MESSAGE_RECEIVED**
```json
{
  "event_type": "MESSAGE_RECEIVED",
  "data": {
    "message": "Play jazz music",
    "response": "Playing jazz from library",
    "intent": "play_music"
  }
}
```

**MUSIC_PLAY / MUSIC_PAUSE / MUSIC_STOP**
```json
{
  "event_type": "MUSIC_PLAY",
  "data": {
    "action": "play",
    "song_name": "Miles Davis - Kind of Blue"
  }
}
```

**MEMORY_STORED**
```json
{
  "event_type": "MEMORY_STORED",
  "data": {
    "fact_content": "User enjoys jazz music",
    "category": "preferences"
  }
}
```

**STATUS_UPDATE**
```json
{
  "event_type": "STATUS_UPDATE",
  "data": {
    "status": "ready",
    "features": { ... }
  }
}
```

**ERROR**
```json
{
  "event_type": "ERROR",
  "data": {
    "error": "Music player not available",
    "endpoint": "/api/music/control"
  }
}
```

**CLIENT_CONNECTED / CLIENT_DISCONNECTED**
```json
{
  "event_type": "CLIENT_CONNECTED",
  "data": {
    "session_id": "user2_20250116_def456",
    "client_type": "mobile"
  }
}
```

---

## Event System

### Event Bus Architecture

The event bus enables real-time communication between the server and all connected clients:

```
┌─────────────┐
│   Server    │
│   Events    │
└──────┬──────┘
       │
       ├──────────────┬──────────────┬──────────────┐
       │              │              │              │
  ┌────▼────┐   ┌────▼────┐   ┌────▼────┐   ┌────▼────┐
  │ Client1 │   │ Client2 │   │ Client3 │   │ Client4 │
  │  (Web)  │   │ (Mobile)│   │  (RPi)  │   │  (CLI)  │
  └─────────┘   └─────────┘   └─────────┘   └─────────┘
```

### Event Types

```python
class EventType(Enum):
    MESSAGE_RECEIVED = "message_received"
    MUSIC_PLAY = "music_play"
    MUSIC_PAUSE = "music_pause"
    MUSIC_STOP = "music_stop"
    MUSIC_NEXT = "music_next"
    MUSIC_PREVIOUS = "music_previous"
    MEMORY_STORED = "memory_stored"
    STATUS_UPDATE = "status_update"
    ERROR = "error"
    CLIENT_CONNECTED = "client_connected"
    CLIENT_DISCONNECTED = "client_disconnected"
```

### Subscription Management

Clients can selectively subscribe to event types:

```javascript
// Subscribe to specific events
ws.send(JSON.stringify({
  type: 'subscribe',
  events: ['MESSAGE_RECEIVED', 'MUSIC_PLAY']
}));

// Unsubscribe when no longer needed
ws.send(JSON.stringify({
  type: 'unsubscribe',
  events: ['MUSIC_PLAY']
}));
```

### Session Isolation

Events are scoped by `session_id`:

- Each session receives only its own events
- Global events (e.g., `STATUS_UPDATE`) are broadcast to all
- Cross-session events require explicit routing

---

## Error Handling

### HTTP Error Codes

- `400 Bad Request`: Invalid request parameters
- `404 Not Found`: Resource not found
- `500 Internal Server Error`: Server error
- `503 Service Unavailable`: Service not ready or disabled

### Error Response Format

```json
{
  "detail": "Music player not available"
}
```

### WebSocket Errors

```json
{
  "type": "error",
  "message": "Invalid message format",
  "timestamp": "2025-01-16T10:30:00"
}
```

### Common Error Scenarios

1. **Service Not Ready**: API called before initialization completes
   ```json
   {"detail": "Service not ready"}
   ```

2. **Feature Disabled**: Memory/RAG/Music not configured
   ```json
   {"detail": "Memory system not available"}
   ```

3. **Invalid Session**: Session ID not found
   ```json
   {"detail": "Session not found"}
   ```

4. **WebSocket Disconnection**: Network interruption
   - Client should implement auto-reconnect logic
   - Server maintains event history for replay

---

## Examples

### Python Client

```python
import requests
import json

BASE_URL = "http://localhost:8000"

# Send chat message
response = requests.post(
    f"{BASE_URL}/api/chat",
    json={
        "message": "What's the weather like?",
        "user_id": "alice",
        "client_type": "python_script"
    }
)
result = response.json()
print(f"Response: {result['response']}")
print(f"Intent: {result['intent']}")

# Get memory facts
facts = requests.get(
    f"{BASE_URL}/api/memory/facts",
    params={"user_id": "alice", "limit": 10}
).json()
print(f"Facts: {len(facts)}")

# Upload document
with open("manual.pdf", "rb") as f:
    files = {"file": ("manual.pdf", f, "application/pdf")}
    upload = requests.post(
        f"{BASE_URL}/api/rag/upload",
        files=files
    ).json()
print(f"Uploaded: {upload['chunks']} chunks")
```

### JavaScript/Node.js Client

```javascript
const BASE_URL = 'http://localhost:8000';

// Send chat message
async function chat(message) {
  const response = await fetch(`${BASE_URL}/api/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      message: message,
      user_id: 'bob',
      client_type: 'web'
    })
  });
  return await response.json();
}

// WebSocket connection
const ws = new WebSocket(
  `ws://localhost:8000/ws?user_id=bob&client_type=web`
);

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('Received:', data);
  
  if (data.type === 'connected') {
    // Subscribe to events
    ws.send(JSON.stringify({
      type: 'subscribe',
      events: ['MESSAGE_RECEIVED', 'MUSIC_PLAY']
    }));
  }
};

// Send message via WebSocket
ws.send(JSON.stringify({
  type: 'chat',
  message: 'Tell me a joke'
}));
```

### cURL Examples

```bash
# Health check
curl http://localhost:8000/health

# Chat
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello", "user_id": "test"}'

# Play music
curl -X POST http://localhost:8000/api/music/control \
  -H "Content-Type: application/json" \
  -d '{"action": "play", "song_name": "jazz"}'

# Get conversations
curl "http://localhost:8000/api/conversations?user_id=test&limit=10"

# Upload document
curl -X POST http://localhost:8000/api/rag/upload \
  -F "file=@document.pdf" \
  -F "user_id=test"

# System status
curl http://localhost:8000/api/system/status
```

### React Component Example

```jsx
import React, { useState, useEffect, useRef } from 'react';

function VoiceAssistant() {
  const [messages, setMessages] = useState([]);
  const [connected, setConnected] = useState(false);
  const ws = useRef(null);

  useEffect(() => {
    // Connect to WebSocket
    ws.current = new WebSocket(
      'ws://localhost:8000/ws?user_id=user1&client_type=web'
    );

    ws.current.onopen = () => {
      setConnected(true);
      // Subscribe to events
      ws.current.send(JSON.stringify({
        type: 'subscribe',
        events: ['MESSAGE_RECEIVED', 'MUSIC_PLAY']
      }));
    };

    ws.current.onmessage = (event) => {
      const data = JSON.parse(event.data);
      
      if (data.type === 'chat_response') {
        setMessages(prev => [...prev, {
          role: 'assistant',
          content: data.response
        }]);
      }
      
      if (data.type === 'event' && data.event_type === 'MUSIC_PLAY') {
        console.log('Now playing:', data.data.song_name);
      }
    };

    ws.current.onclose = () => {
      setConnected(false);
      // Implement reconnection logic here
    };

    return () => ws.current.close();
  }, []);

  const sendMessage = (text) => {
    setMessages(prev => [...prev, { role: 'user', content: text }]);
    
    ws.current.send(JSON.stringify({
      type: 'chat',
      message: text
    }));
  };

  return (
    <div>
      <div>Status: {connected ? 'Connected' : 'Disconnected'}</div>
      <div>
        {messages.map((msg, i) => (
          <div key={i}>
            <strong>{msg.role}:</strong> {msg.content}
          </div>
        ))}
      </div>
      <input 
        type="text" 
        onKeyPress={(e) => {
          if (e.key === 'Enter') {
            sendMessage(e.target.value);
            e.target.value = '';
          }
        }}
      />
    </div>
  );
}
```

---

## Deployment

### Production Checklist

- [ ] Configure proper authentication (JWT/OAuth)
- [ ] Set up HTTPS/WSS with valid certificates
- [ ] Configure CORS for specific origins
- [ ] Set up rate limiting
- [ ] Configure logging and monitoring
- [ ] Set up database backups
- [ ] Configure environment variables
- [ ] Test auto-reconnect logic
- [ ] Implement health checks
- [ ] Set up load balancing (if needed)

### Docker Deployment

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

```bash
# Build image
docker build -t voice-assistant-api .

# Run container
docker run -p 8000:8000 \
  -v $(pwd)/data:/app/data \
  -e LOG_LEVEL=INFO \
  voice-assistant-api
```

### Production Server

```bash
# Using Gunicorn with Uvicorn workers
gunicorn api.main:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000 \
  --access-logfile - \
  --error-logfile -
```

### Nginx Reverse Proxy

```nginx
server {
    listen 80;
    server_name api.yourdomain.com;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location /ws {
        proxy_pass http://localhost:8000/ws;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_read_timeout 86400;
    }
}
```

---

## Rate Limiting

Consider implementing rate limiting for production:

```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@app.post("/api/chat")
@limiter.limit("30/minute")
async def chat(request: Request, chat_request: ChatRequest):
    # ... existing code
```

---

## Monitoring

### Prometheus Metrics

```python
from prometheus_client import Counter, Histogram, Gauge

chat_requests = Counter('chat_requests_total', 'Total chat requests')
response_time = Histogram('response_time_seconds', 'Response time')
active_sessions = Gauge('active_sessions', 'Active sessions')
```

### Health Endpoint

The `/health` endpoint provides basic health status. For production, consider:

- Database connectivity check
- External service health
- Resource usage metrics
- Disk space monitoring

---

## Performance Considerations

### Response Times

Typical response times by operation:

- **Simple chat**: 100-300ms
- **Memory retrieval**: 50-150ms
- **RAG search**: 200-500ms
- **Music control**: 50-100ms
- **WebSocket ping**: <10ms

### Optimization Tips

1. **Use WebSocket for real-time updates** instead of polling
2. **Batch API calls** when possible
3. **Cache frequently accessed data** on the client side
4. **Use streaming endpoints** for long responses
5. **Implement connection pooling** for database access

### Scaling

For high-traffic deployments:

- **Horizontal scaling**: Run multiple API instances behind a load balancer
- **Session affinity**: Route WebSocket connections to the same instance
- **Redis for state**: Share session state across instances
- **Separate workers**: Offload heavy tasks (RAG indexing) to background workers

---

## Security Best Practices

### Authentication

Implement proper authentication before production:

```python
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security = HTTPBearer()

async def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    # Verify JWT token
    if not is_valid_token(token):
        raise HTTPException(status_code=401, detail="Invalid token")
    return decode_token(token)

@app.post("/api/chat")
async def chat(request: ChatRequest, user = Depends(verify_token)):
    # User is now authenticated
    pass
```

### Input Validation

All inputs are validated using Pydantic models, but consider:

- **SQL injection**: Use parameterized queries (already implemented)
- **XSS protection**: Sanitize user inputs before display
- **File upload limits**: Restrict file size and types
- **Rate limiting**: Prevent abuse and DDoS

### CORS Configuration

For production, restrict allowed origins:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://yourdomain.com",
        "https://app.yourdomain.com"
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["*"],
)
```

### WebSocket Security

```python
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    
    # Verify authentication token
    token = websocket.query_params.get('token')
    if not is_valid_token(token):
        await websocket.send_text(json.dumps({
            'type': 'error',
            'message': 'Authentication required'
        }))
        await websocket.close(code=1008)
        return
```

---

## Troubleshooting

### Common Issues

#### 1. WebSocket Connection Failed

**Symptoms**: `WebSocket connection failed` or immediate disconnection

**Solutions**:
- Check if server is running: `curl http://localhost:8000/health`
- Verify WebSocket URL format: `ws://` (not `wss://` for local dev)
- Check firewall rules
- Verify event bus is available (check `/health` response)

#### 2. Service Not Ready (503 Error)

**Symptoms**: All endpoints return `503 Service Unavailable`

**Solutions**:
- Wait for startup to complete (check logs)
- Verify all dependencies are installed
- Check database connectivity
- Restart the server

#### 3. Memory/RAG Not Available

**Symptoms**: Endpoints return "Memory/RAG system not available"

**Solutions**:
- Check if feature is enabled in config
- Verify database paths exist and are writable
- Check initialization logs for errors
- Ensure required dependencies are installed

#### 4. Music Player Issues

**Symptoms**: Music control returns errors

**Solutions**:
- Verify music library path is configured
- Check if MusicAction is loaded (see `/api/system/status`)
- Ensure music files exist and are accessible
- Check file permissions

#### 5. Session ID Conflicts

**Symptoms**: Unexpected session behavior or data mixing

**Solutions**:
- Ensure unique session IDs per client
- Don't reuse session IDs across different users
- Clear old sessions periodically via `/api/sessions/{session_id}`

### Debug Mode

Enable detailed logging:

```bash
export LOG_LEVEL=DEBUG
uvicorn api.main:app --reload --port 8000
```

Check logs at: `logs/voice_assistant.log`

### Testing WebSocket Connection

```bash
# Install websocat
brew install websocat  # macOS
# or apt-get install websocat (Linux)

# Test connection
websocat "ws://localhost:8000/ws?user_id=test&client_type=cli"

# Send ping
{"type": "ping"}

# Expected response
{"type": "pong", "timestamp": "..."}
```

---

## SDKs and Client Libraries

### Official SDKs

Currently, the API uses standard HTTP/WebSocket protocols. Community SDKs:

- **Python**: Use `requests` and `websocket-client`
- **JavaScript**: Use `fetch` and native `WebSocket`
- **TypeScript**: Type definitions available at `@types/voice-assistant-api` (community)

### Creating Custom Clients

Minimum requirements for a functional client:

1. **HTTP Client**: For REST API calls
2. **WebSocket Client**: For real-time events
3. **JSON Support**: For message serialization
4. **Reconnection Logic**: Handle network interruptions

Example minimal client:

```python
import requests
import websocket
import json
import time

class VoiceAssistantClient:
    def __init__(self, base_url, user_id, client_type):
        self.base_url = base_url
        self.user_id = user_id
        self.client_type = client_type
        self.ws = None
        self.session_id = None
    
    def connect(self):
        """Connect WebSocket"""
        ws_url = f"{self.base_url.replace('http', 'ws')}/ws"
        ws_url += f"?user_id={self.user_id}&client_type={self.client_type}"
        
        self.ws = websocket.create_connection(ws_url)
        
        # Receive welcome message
        welcome = json.loads(self.ws.recv())
        self.session_id = welcome['session_id']
        return welcome
    
    def chat(self, message):
        """Send chat message via REST"""
        response = requests.post(
            f"{self.base_url}/api/chat",
            json={
                "message": message,
                "user_id": self.user_id,
                "client_type": self.client_type,
                "session_id": self.session_id
            }
        )
        return response.json()
    
    def subscribe(self, events):
        """Subscribe to events"""
        self.ws.send(json.dumps({
            "type": "subscribe",
            "events": events
        }))
        return json.loads(self.ws.recv())
    
    def listen(self):
        """Listen for events"""
        while True:
            try:
                message = self.ws.recv()
                yield json.loads(message)
            except Exception as e:
                print(f"Error: {e}")
                break

# Usage
client = VoiceAssistantClient(
    "http://localhost:8000",
    "user1",
    "python_client"
)

client.connect()
client.subscribe(["MESSAGE_RECEIVED", "MUSIC_PLAY"])

# Send message
result = client.chat("Hello!")
print(result['response'])

# Listen for events
for event in client.listen():
    print(f"Event: {event['event_type']}")
```

---

## Testing

### Unit Tests

```bash
# Run tests
pytest tests/

# With coverage
pytest --cov=api tests/
```

### Integration Tests

```bash
# Start test server
uvicorn api.main:app --port 8001 &

# Run integration tests
pytest tests/integration/

# Cleanup
pkill -f "uvicorn api.main"
```

### Load Testing

Use tools like `locust` or `k6` for load testing:

```python
# locustfile.py
from locust import HttpUser, task, between

class VoiceAssistantUser(HttpUser):
    wait_time = between(1, 3)
    
    @task
    def chat(self):
        self.client.post("/api/chat", json={
            "message": "Hello",
            "user_id": f"user_{self.client.user_id}",
            "client_type": "load_test"
        })
    
    @task
    def status(self):
        self.client.get("/api/system/status")
```

```bash
# Run load test
locust -f locustfile.py --host http://localhost:8000
```

### Manual Testing

Use the interactive API docs:

```
http://localhost:8000/docs
```

This provides a Swagger UI for testing all endpoints.

---

## FAQ

### General Questions

**Q: Can I use this API without WebSocket?**  
A: Yes! All core functionality is available via REST API. WebSocket is optional for real-time events.

**Q: How many concurrent connections are supported?**  
A: Depends on your server resources. A single instance can handle hundreds of connections. Scale horizontally for more.

**Q: Is the API stateless?**  
A: Mostly. Conversation state is stored in the database. WebSocket connections maintain some state for event routing.

**Q: Can I run multiple API instances?**  
A: Yes, but you'll need shared storage (Redis) for session state and event bus coordination.

### Technical Questions

**Q: Why is my WebSocket disconnecting?**  
A: Check network timeouts, implement ping/pong keepalive, and handle reconnection on the client side.

**Q: How do I handle large file uploads?**  
A: Use streaming uploads or increase request size limits in your server configuration.

**Q: Can I use this with mobile apps?**  
A: Yes! The API works with any HTTP/WebSocket client. Consider using native WebSocket libraries for mobile.

**Q: How is data isolated between users?**  
A: All data is scoped by `user_id`. Sessions provide additional isolation within a user's context.

**Q: What happens if the server restarts?**  
A: Memory and RAG data persist in databases. Active WebSocket connections need to reconnect.

### Feature Questions

**Q: Can I add custom intent types?**  
A: Yes, extend the intent detection module and register new action handlers.

**Q: How do I add more music sources?**  
A: Extend the `MusicPlayer` class with new source adapters (Spotify, Apple Music, etc.).

**Q: Can I use my own LLM for intent detection?**  
A: Yes, implement the `IntentDetector` interface with your preferred model.

**Q: Is there support for multiple languages?**  
A: The core supports any language your LLM can handle. Add language-specific processing as needed.

---


### Development Setup

```bash
# Clone repo
git clone https://github.com/yourusername/voice-assistant.git
cd voice-assistant

# Create virtual environment
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows

# Install dev dependencies
pip install -r requirements-dev.txt

# Run tests
pytest

# Start dev server
uvicorn api.main:app --reload
```

### Code Style

- Follow PEP 8
- Use type hints
- Write docstrings for all functions
- Add tests for new features

---

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) file for details.

---

## Support

## THERE IS NO SUPPORT

---

## Acknowledgments

Built with:
- [FastAPI](https://fastapi.tiangolo.com/) - Modern web framework
- [Pydantic](https://pydantic-docs.helpmanual.io/) - Data validation
- [SQLAlchemy](https://www.sqlalchemy.org/) - Database ORM
- [Uvicorn](https://www.uvicorn.org/) - ASGI server



