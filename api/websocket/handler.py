"""
WebSocket Handler - Real-time Event Communication

Handles WebSocket connections with auto-reconnect support.
"""

import json
import uuid
from datetime import datetime

from fastapi import WebSocket, WebSocketDisconnect

from api.dependencies import (
    get_conversation_service,
    get_music_player,
    get_active_sessions
)
from api.routes.chat import emit_chat_events
from api.models import ChatRequest
from utils.logger import get_logger

logger = get_logger('api.websocket')


# ============================================
# EVENT BUS SETUP
# ============================================

try:
    from core.event_bus import (
        get_event_bus, emit_event, emit_music_event,
        EventType
    )
    EVENT_BUS_AVAILABLE = True
except ImportError:
    EVENT_BUS_AVAILABLE = False
    logger.warning("Event bus not available - WebSocket disabled")


# ============================================
# WEBSOCKET ENDPOINT
# ============================================

async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket for real-time events with reconnection support.
    
    Query parameters (all optional):
    - session_id: Session identifier
    - user_id: User identifier (default: "default_user")
    - client_type: Client type (default: "unknown")
    """
    
    # CRITICAL: Accept connection FIRST
    await websocket.accept()
    
    # THEN get query parameters
    try:
        query_params = dict(websocket.query_params)
        session_id = query_params.get('session_id')
        user_id = query_params.get('user_id', 'default_user')
        client_type = query_params.get('client_type', 'unknown')
    except Exception as e:
        await websocket.send_text(json.dumps({
            'type': 'error',
            'message': f'Invalid parameters: {e}'
        }))
        await websocket.close()
        return
    
    # Check if services available
    if not EVENT_BUS_AVAILABLE:
        await websocket.send_text(json.dumps({
            'type': 'error',
            'message': 'Event bus not available'
        }))
        await websocket.close(code=1011)
        return
    
    service = None
    try:
        service = get_conversation_service()
    except:
        await websocket.send_text(json.dumps({
            'type': 'error',
            'message': 'Service not ready'
        }))
        await websocket.close(code=1011)
        return
    
    event_bus = get_event_bus()
    sessions = get_active_sessions()
    
    # Generate session_id if not provided
    if not session_id:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        short_uuid = str(uuid.uuid4())[:8]
        session_id = f"{user_id}_{timestamp}_{short_uuid}"
    
    try:
        # Register connection
        if session_id not in event_bus.connections:
            event_bus.connections[session_id] = set()
        event_bus.connections[session_id].add(websocket)
        
        # Store metadata
        event_bus.connection_metadata[websocket] = {
            'session_id': session_id,
            'user_id': user_id,
            'client_type': client_type,
            'connected_at': datetime.now().isoformat()
        }
        
        # Initialize subscriptions
        if session_id not in event_bus.subscriptions:
            event_bus.subscriptions[session_id] = set(EventType)
        
        logger.info(f"WebSocket connected: session={session_id[:20]}..., client={client_type}")
        
        # Track session
        if session_id not in sessions:
            sessions[session_id] = {
                'user_id': user_id,
                'client_type': client_type,
                'created_at': datetime.now().isoformat(),
                'websocket_connected': True
            }
        else:
            sessions[session_id]['websocket_connected'] = True
        
        # Send welcome message
        music_player = get_music_player()
        await websocket.send_text(json.dumps({
            'type': 'connected',
            'session_id': session_id,
            'user_id': user_id,
            'timestamp': datetime.now().isoformat(),
            'features': {
                'chat': True,
                'events': True,
                'music': music_player is not None,
                'memory': service.memory is not None,
                'rag': service.rag is not None
            }
        }))
        
        # Listen for messages
        await handle_websocket_messages(
            websocket,
            session_id,
            user_id,
            client_type,
            event_bus,
            service
        )
        
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected: {session_id[:20]}...")
        event_bus.disconnect(websocket)
        
        if session_id in sessions:
            sessions[session_id]['websocket_connected'] = False
            sessions[session_id]['last_disconnected'] = datetime.now().isoformat()
    
    except Exception as e:
        logger.error(f"WebSocket error: {e}", exc_info=True)
        event_bus.disconnect(websocket)
        
        try:
            await emit_event(
                event_type=EventType.ERROR,
                data={'error': str(e)},
                session_id=session_id
            )
        except:
            pass


async def handle_websocket_messages(
    websocket: WebSocket,
    session_id: str,
    user_id: str,
    client_type: str,
    event_bus,
    service
):
    """Handle incoming WebSocket messages"""
    
    while True:
        try:
            data = await websocket.receive_text()
            message = json.loads(data)
            
            msg_type = message.get('type')
            
            if msg_type == 'ping':
                await websocket.send_text(json.dumps({
                    'type': 'pong',
                    'timestamp': datetime.now().isoformat()
                }))
            
            elif msg_type == 'subscribe':
                event_types = message.get('events', [])
                event_enum = {EventType[e] for e in event_types if e in EventType.__members__}
                event_bus.subscribe(session_id, event_enum)
                
                await websocket.send_text(json.dumps({
                    'type': 'subscribed',
                    'events': event_types,
                    'timestamp': datetime.now().isoformat()
                }))
            
            elif msg_type == 'unsubscribe':
                event_types = message.get('events', [])
                event_enum = {EventType[e] for e in event_types if e in EventType.__members__}
                event_bus.unsubscribe(session_id, event_enum)
                
                await websocket.send_text(json.dumps({
                    'type': 'unsubscribed',
                    'events': event_types,
                    'timestamp': datetime.now().isoformat()
                }))
            
            elif msg_type == 'chat':
                user_message = message.get('message')
                
                if user_message:
                    result = await service.process_input(
                        user_input=user_message,
                        session_id=session_id,
                        user_id=user_id,
                        client_type=client_type
                    )
                    
                    await websocket.send_text(json.dumps({
                        'type': 'chat_response',
                        'response': result['response'],
                        'intent': result['intent'],
                        'action_data': result.get('action_data'),
                        'timestamp': datetime.now().isoformat()
                    }))
                    
                    await emit_chat_events(
                        ChatRequest(
                            message=user_message,
                            session_id=session_id,
                            user_id=user_id,
                            client_type=client_type
                        ),
                        result
                    )
            
            elif msg_type == 'music_control':
                await handle_music_control(message, websocket, session_id)
            
            else:
                await websocket.send_text(json.dumps({
                    'type': 'error',
                    'message': f'Unknown message type: {msg_type}',
                    'timestamp': datetime.now().isoformat()
                }))
        
        except json.JSONDecodeError:
            await websocket.send_text(json.dumps({
                'type': 'error',
                'message': 'Invalid JSON',
                'timestamp': datetime.now().isoformat()
            }))


async def handle_music_control(message: dict, websocket: WebSocket, session_id: str):
    """Handle music control via WebSocket"""
    action = message.get('action')
    song_name = message.get('song_name')
    
    player = get_music_player()
    if not player:
        await websocket.send_text(json.dumps({
            'type': 'error',
            'message': 'Music player not available'
        }))
        return
    
    try:
        if action == 'play' and song_name:
            song = player._find_song(song_name)
            if song:
                player.play(song)
                await emit_music_event('play', song.name, session_id)
        elif action == 'pause':
            player.pause()
            await emit_music_event('pause', None, session_id)
        elif action == 'resume':
            player.resume()
            await emit_music_event('play', None, session_id)
        elif action == 'stop':
            player.stop()
            await emit_music_event('stop', None, session_id)
    except Exception as e:
        logger.error(f"Music control error: {e}")