"""
Event Bus System - Real-Time Communication

Allows multiple clients to receive real-time updates:
- Music playback events
- Memory updates
- System status changes
- Chat messages
"""

import asyncio
import json
from typing import Dict, Set, Optional, Any
from datetime import datetime
from dataclasses import dataclass, asdict
from enum import Enum
from fastapi import WebSocket
from utils.logger import get_logger

logger = get_logger('event_bus')


class EventType(Enum):
    """Types of events"""
    # Chat events
    MESSAGE_RECEIVED = "message_received"
    MESSAGE_SENT = "message_sent"
    TYPING = "typing"
    
    # Music events
    MUSIC_PLAYING = "music_playing"
    MUSIC_PAUSED = "music_paused"
    MUSIC_STOPPED = "music_stopped"
    MUSIC_NEXT = "music_next"
    MUSIC_VOLUME_CHANGED = "music_volume_changed"
    
    # Memory events
    MEMORY_STORED = "memory_stored"
    FACT_LEARNED = "fact_learned"
    
    # System events
    CLIENT_CONNECTED = "client_connected"
    CLIENT_DISCONNECTED = "client_disconnected"
    STATUS_UPDATE = "status_update"
    ERROR = "error"


@dataclass
class Event:
    """Event data structure"""
    type: EventType
    data: Dict[str, Any]
    session_id: Optional[str] = None
    user_id: str = "default_user"
    timestamp: str = ""
    
    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON"""
        return {
            'type': self.type.value,
            'data': self.data,
            'session_id': self.session_id,
            'user_id': self.user_id,
            'timestamp': self.timestamp
        }
    
    def to_json(self) -> str:
        """Convert to JSON string"""
        return json.dumps(self.to_dict())


class EventBus:
    """
    Central event bus for real-time communication.
    
    Features:
    - Pub/Sub pattern
    - Session-aware routing
    - Broadcast to all or specific sessions
    - Event filtering
    """
    
    def __init__(self):
        # Active connections: {session_id: Set[WebSocket]}
        self.connections: Dict[str, Set[WebSocket]] = {}
        
        # Connection metadata: {websocket: {session_id, user_id, client_type}}
        self.connection_metadata: Dict[WebSocket, Dict[str, str]] = {}
        
        # Event subscriptions: {session_id: Set[EventType]}
        self.subscriptions: Dict[str, Set[EventType]] = {}
        
        logger.info("EventBus initialized")
    
    # ============================================
    # CONNECTION MANAGEMENT
    # ============================================
    
    async def connect(
        self,
        websocket: WebSocket,
        session_id: str,
        user_id: str = "default_user",
        client_type: str = "unknown"
    ):
        """Register new WebSocket connection"""
        await websocket.accept()
        
        # Add to connections
        if session_id not in self.connections:
            self.connections[session_id] = set()
        
        self.connections[session_id].add(websocket)
        
        # Store metadata
        self.connection_metadata[websocket] = {
            'session_id': session_id,
            'user_id': user_id,
            'client_type': client_type,
            'connected_at': datetime.now().isoformat()
        }
        
        # Initialize subscriptions (subscribe to all by default)
        if session_id not in self.subscriptions:
            self.subscriptions[session_id] = set(EventType)
        
        logger.info(
            f"Client connected: session={session_id[:20]}..., "
            f"client={client_type}"
        )
        
        # Send welcome message
        await self.send_to_connection(
            websocket,
            Event(
                type=EventType.CLIENT_CONNECTED,
                data={
                    'message': 'Connected to event bus',
                    'session_id': session_id,
                    'subscriptions': [e.value for e in self.subscriptions[session_id]]
                },
                session_id=session_id,
                user_id=user_id
            )
        )
        
        # Broadcast to others
        await self.broadcast_to_session(
            session_id,
            Event(
                type=EventType.STATUS_UPDATE,
                data={'clients_connected': len(self.connections[session_id])},
                session_id=session_id,
                user_id=user_id
            ),
            exclude={websocket}
        )
    
    def disconnect(self, websocket: WebSocket):
        """Remove WebSocket connection"""
        metadata = self.connection_metadata.get(websocket)
        
        if not metadata:
            return
        
        session_id = metadata['session_id']
        
        # Remove from connections
        if session_id in self.connections:
            self.connections[session_id].discard(websocket)
            
            # Clean up empty sessions
            if not self.connections[session_id]:
                del self.connections[session_id]
                if session_id in self.subscriptions:
                    del self.subscriptions[session_id]
        
        # Remove metadata
        del self.connection_metadata[websocket]
        
        logger.info(f"Client disconnected: session={session_id[:20]}...")
    
    # ============================================
    # EVENT PUBLISHING
    # ============================================
    
    async def publish(self, event: Event):
        """
        Publish event to appropriate subscribers.
        
        Args:
            event: Event to publish
        """
        try:
            # Route based on session_id
            if event.session_id:
                # Send to specific session
                await self.broadcast_to_session(event.session_id, event)
            else:
                # Broadcast to all
                await self.broadcast_to_all(event)
        
        except Exception as e:
            logger.error(f"Publish error: {e}")
    
    async def broadcast_to_all(self, event: Event):
        """Broadcast event to ALL connected clients"""
        dead_connections = set()
        
        for session_id, websockets in self.connections.items():
            for ws in websockets:
                try:
                    # Check if subscribed
                    if event.type in self.subscriptions.get(session_id, set()):
                        await ws.send_text(event.to_json())
                
                except Exception as e:
                    logger.error(f"Send error: {e}")
                    dead_connections.add(ws)
        
        # Clean up dead connections
        for ws in dead_connections:
            self.disconnect(ws)
    
    async def broadcast_to_session(
        self,
        session_id: str,
        event: Event,
        exclude: Optional[Set[WebSocket]] = None
    ):
        """
        Broadcast event to specific session.
        
        Args:
            session_id: Target session
            event: Event to send
            exclude: WebSockets to exclude
        """
        if session_id not in self.connections:
            return
        
        exclude = exclude or set()
        dead_connections = set()
        
        for ws in self.connections[session_id]:
            if ws in exclude:
                continue
            
            try:
                # Check subscription
                if event.type in self.subscriptions.get(session_id, set()):
                    await ws.send_text(event.to_json())
            
            except Exception as e:
                logger.error(f"Send error: {e}")
                dead_connections.add(ws)
        
        # Clean up
        for ws in dead_connections:
            self.disconnect(ws)
    
    async def send_to_connection(self, websocket: WebSocket, event: Event):
        """Send event to specific connection"""
        try:
            await websocket.send_text(event.to_json())
        except Exception as e:
            logger.error(f"Send error: {e}")
            self.disconnect(websocket)
    
    # ============================================
    # SUBSCRIPTION MANAGEMENT
    # ============================================
    
    def subscribe(
        self,
        session_id: str,
        event_types: Set[EventType]
    ):
        """Subscribe to specific event types"""
        if session_id not in self.subscriptions:
            self.subscriptions[session_id] = set()
        
        self.subscriptions[session_id].update(event_types)
        
        logger.info(
            f"Session {session_id[:20]}... subscribed to "
            f"{len(event_types)} event types"
        )
    
    def unsubscribe(
        self,
        session_id: str,
        event_types: Set[EventType]
    ):
        """Unsubscribe from event types"""
        if session_id in self.subscriptions:
            self.subscriptions[session_id] -= event_types
    
    # ============================================
    # STATUS & MONITORING
    # ============================================
    
    def get_stats(self) -> Dict[str, Any]:
        """Get event bus statistics"""
        total_connections = sum(len(ws_set) for ws_set in self.connections.values())
        
        return {
            'total_sessions': len(self.connections),
            'total_connections': total_connections,
            'sessions': {
                session_id: {
                    'connections': len(websockets),
                    'subscriptions': len(self.subscriptions.get(session_id, set()))
                }
                for session_id, websockets in self.connections.items()
            }
        }
    
    def is_session_connected(self, session_id: str) -> bool:
        """Check if session has any active connections"""
        return session_id in self.connections and len(self.connections[session_id]) > 0


# ============================================
# GLOBAL INSTANCE
# ============================================

_event_bus: Optional[EventBus] = None


def get_event_bus() -> EventBus:
    """Get global event bus instance"""
    global _event_bus
    if _event_bus is None:
        _event_bus = EventBus()
    return _event_bus


# ============================================
# CONVENIENCE FUNCTIONS
# ============================================

async def emit_event(
    event_type: EventType,
    data: Dict[str, Any],
    session_id: Optional[str] = None,
    user_id: str = "default_user"
):
    """Convenience function to emit an event"""
    event = Event(
        type=event_type,
        data=data,
        session_id=session_id,
        user_id=user_id
    )
    
    bus = get_event_bus()
    await bus.publish(event)


async def emit_music_event(
    action: str,
    song_name: Optional[str] = None,
    session_id: Optional[str] = None
):
    """Emit music-related event"""
    event_type_map = {
        'play': EventType.MUSIC_PLAYING,
        'pause': EventType.MUSIC_PAUSED,
        'stop': EventType.MUSIC_STOPPED,
        'next': EventType.MUSIC_NEXT
    }
    
    event_type = event_type_map.get(action, EventType.STATUS_UPDATE)
    
    await emit_event(
        event_type=event_type,
        data={'action': action, 'song': song_name},
        session_id=session_id
    )


async def emit_memory_event(
    fact_content: str,
    category: str,
    session_id: Optional[str] = None
):
    """Emit memory storage event"""
    await emit_event(
        event_type=EventType.FACT_LEARNED,
        data={'content': fact_content, 'category': category},
        session_id=session_id
    )