"""
Event Bus System

Provides real-time communication between server and clients via WebSocket.
"""

from core.event_bus.bus import (
    EventBus,
    Event,
    EventType,
    get_event_bus,
    emit_event,
    emit_music_event,
    emit_memory_event
)

__all__ = [
    'EventBus',
    'Event',
    'EventType',
    'get_event_bus',
    'emit_event',
    'emit_music_event',
    'emit_memory_event'
]