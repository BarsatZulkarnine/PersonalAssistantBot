#!/usr/bin/env python3
"""
WebSocket Test Client - COMPLETE WITH AUTO-RECONNECT

Features:
- Auto-reconnection with exponential backoff
- Event subscription management
- Chat via WebSocket
- Music control
- Heartbeat monitoring
- Event replay on reconnect

Usage:
    python websocket_test.py
    python websocket_test.py --server ws://192.168.1.100:8000/ws
"""

import asyncio
import websockets
import json
from datetime import datetime
import argparse
import sys
from typing import Optional, Set
from enum import Enum


class ConnectionState(Enum):
    """WebSocket connection states"""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"


class WebSocketTestClient:
    """
    Test client for WebSocket event bus with auto-reconnection.
    """
    
    def __init__(
        self,
        server_url: str = "ws://localhost:8000/ws",
        session_id: Optional[str] = None,
        user_id: str = "test_user",
        auto_reconnect: bool = True
    ):
        self.server_url = server_url
        self.user_id = user_id
        self.auto_reconnect = auto_reconnect
        
        # Generate session ID if not provided
        if not session_id:
            timestamp = datetime.now().strftime("%H%M%S")
            self.session_id = f"test_{timestamp}"
        else:
            self.session_id = session_id
        
        # Connection state
        self.ws: Optional[websockets.WebSocketClientProtocol] = None
        self.state = ConnectionState.DISCONNECTED
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = 10
        
        # Subscriptions
        self.subscribed_events: Set[str] = set()
        
        # Statistics
        self.messages_received = 0
        self.messages_sent = 0
        self.events_by_type = {}
        
        # Background tasks
        self.heartbeat_task: Optional[asyncio.Task] = None
        self.listen_task: Optional[asyncio.Task] = None
    
    def _build_url(self) -> str:
        """Build WebSocket URL with query parameters"""
        return f"{self.server_url}?session_id={self.session_id}&user_id={self.user_id}&client_type=test"
    
    async def connect(self):
        """Connect to WebSocket server"""
        if self.state in [ConnectionState.CONNECTING, ConnectionState.CONNECTED]:
            print(f"[WARN] Already {self.state.value}")
            return
        
        self.state = ConnectionState.CONNECTING
        url = self._build_url()
        
        try:
            print(f"\n[CONNECT] Connecting to {url}...")
            self.ws = await websockets.connect(url)
            self.state = ConnectionState.CONNECTED
            self.reconnect_attempts = 0
            
            print(f"[OK] Connected! Session: {self.session_id}")
            
            # Start background tasks
            self.heartbeat_task = asyncio.create_task(self._heartbeat_loop())
            
        except Exception as e:
            self.state = ConnectionState.DISCONNECTED
            print(f"[ERROR] Connection failed: {e}")
            
            if self.auto_reconnect:
                await self._reconnect()
            else:
                raise
    
    async def _reconnect(self):
        """Reconnect with exponential backoff"""
        if self.reconnect_attempts >= self.max_reconnect_attempts:
            print(f"[FAIL] Max reconnection attempts ({self.max_reconnect_attempts}) reached")
            return
        
        self.state = ConnectionState.RECONNECTING
        self.reconnect_attempts += 1
        
        # Exponential backoff: 2^n seconds (max 60s)
        delay = min(2 ** self.reconnect_attempts, 60)
        
        print(f"\n[RECONNECT] Attempt {self.reconnect_attempts}/{self.max_reconnect_attempts} in {delay}s...")
        await asyncio.sleep(delay)
        
        await self.connect()
    
    async def _heartbeat_loop(self):
        """Send periodic heartbeat pings"""
        while self.state == ConnectionState.CONNECTED:
            try:
                await self.send_message('ping', {})
                await asyncio.sleep(30)  # Ping every 30 seconds
            except:
                break
    
    async def disconnect(self):
        """Gracefully disconnect"""
        print("\n[DISCONNECT] Closing connection...")
        
        self.state = ConnectionState.DISCONNECTED
        
        # Cancel background tasks
        if self.heartbeat_task:
            self.heartbeat_task.cancel()
        if self.listen_task:
            self.listen_task.cancel()
        
        # Close WebSocket
        if self.ws:
            await self.ws.close()
            self.ws = None
        
        print("[OK] Disconnected")
    
    async def send_message(self, message_type: str, data: dict):
        """Send message to server"""
        if not self.ws or self.state != ConnectionState.CONNECTED:
            print("[ERROR] Not connected")
            return
        
        payload = {
            'type': message_type,
            **data
        }
        
        try:
            await self.ws.send(json.dumps(payload))
            self.messages_sent += 1
        except Exception as e:
            print(f"[ERROR] Send failed: {e}")
            if self.auto_reconnect:
                await self._reconnect()
    
    async def listen(self):
        """Listen for events from server"""
        print("\n[LISTEN] Listening for events...\n")
        
        try:
            async for message in self.ws:
                self.messages_received += 1
                data = json.loads(message)
                
                event_type = data.get('type')
                event_data = data.get('data', {})
                timestamp = data.get('timestamp', '')
                
                # Track event types
                if event_type:
                    self.events_by_type[event_type] = self.events_by_type.get(event_type, 0) + 1
                
                # Pretty print event
                self._print_event(event_type, event_data, timestamp)
        
        except websockets.exceptions.ConnectionClosed:
            print("\n[WARN] Connection closed by server")
            self.state = ConnectionState.DISCONNECTED
            
            if self.auto_reconnect:
                await self._reconnect()
                if self.state == ConnectionState.CONNECTED:
                    # Resubscribe to events
                    if self.subscribed_events:
                        await self.subscribe(list(self.subscribed_events))
                    # Continue listening
                    await self.listen()
        
        except Exception as e:
            print(f"\n[ERROR] Listen error: {e}")
            self.state = ConnectionState.DISCONNECTED
            
            if self.auto_reconnect:
                await self._reconnect()
    
    def _print_event(self, event_type: str, event_data: dict, timestamp: str):
        """Pretty print event"""
        time_str = timestamp[11:19] if len(timestamp) > 19 else timestamp
        
        # Color coding by event type
        if event_type == 'pong':
            return  # Skip heartbeat responses
        elif event_type in ['connected', 'subscribed', 'unsubscribed']:
            prefix = "✅"
        elif event_type == 'error':
            prefix = "❌"
        elif event_type.startswith('music_'):
            prefix = "🎵"
        elif event_type.startswith('memory_') or event_type == 'fact_learned':
            prefix = "🧠"
        elif event_type in ['message_received', 'chat_response']:
            prefix = "💬"
        else:
            prefix = "📡"
        
        print(f"{prefix} [{time_str}] {event_type}")
        
        if event_data:
            # Pretty print data
            for key, value in event_data.items():
                if isinstance(value, str) and len(value) > 60:
                    value = value[:60] + "..."
                print(f"     {key}: {value}")
        print()
    
    async def subscribe(self, events: list):
        """Subscribe to specific event types"""
        await self.send_message('subscribe', {'events': events})
        self.subscribed_events.update(events)
        print(f"[SUBSCRIBE] Requested: {', '.join(events)}")
    
    async def unsubscribe(self, events: list):
        """Unsubscribe from event types"""
        await self.send_message('unsubscribe', {'events': events})
        self.subscribed_events.difference_update(events)
        print(f"[UNSUBSCRIBE] Removed: {', '.join(events)}")
    
    async def chat(self, message: str):
        """Send chat message via WebSocket"""
        await self.send_message('chat', {'message': message})
        print(f"[CHAT] Sent: {message}")
    
    async def control_music(self, action: str, song_name: Optional[str] = None):
        """Control music playback"""
        data = {'action': action}
        if song_name:
            data['song_name'] = song_name
        
        await self.send_message('music_control', data)
        print(f"[MUSIC] {action}" + (f" ({song_name})" if song_name else ""))
    
    def print_stats(self):
        """Print client statistics"""
        print("\n" + "="*50)
        print("CLIENT STATISTICS")
        print("="*50)
        print(f"Session ID: {self.session_id}")
        print(f"Connection State: {self.state.value}")
        print(f"Messages Sent: {self.messages_sent}")
        print(f"Messages Received: {self.messages_received}")
        print(f"Subscribed Events: {len(self.subscribed_events)}")
        
        if self.events_by_type:
            print("\nEvents Received by Type:")
            for event_type, count in sorted(self.events_by_type.items()):
                print(f"  {event_type}: {count}")
        
        print("="*50 + "\n")


# ============================================
# INTERACTIVE TEST MODES
# ============================================

async def interactive_mode(client: WebSocketTestClient):
    """Interactive command mode"""
    print("""
╔════════════════════════════════════════╗
║   Interactive WebSocket Test Client    ║
╚════════════════════════════════════════╝

Commands:
  chat <message>           - Send chat message
  subscribe <events>       - Subscribe to events (comma-separated)
  unsubscribe <events>     - Unsubscribe from events
  music play <name>        - Play music
  music pause/resume/stop  - Control music
  stats                    - Show statistics
  reconnect                - Force reconnection
  quit/exit                - Exit
    """)
    
    # Start listening in background
    client.listen_task = asyncio.create_task(client.listen())
    
    try:
        while True:
            try:
                command = await asyncio.get_event_loop().run_in_executor(
                    None, input, "\n> "
                )
                
                command = command.strip()
                if not command:
                    continue
                
                parts = command.split(None, 1)
                cmd = parts[0].lower()
                
                if cmd in ['quit', 'exit']:
                    break
                
                elif cmd == 'chat':
                    if len(parts) > 1:
                        await client.chat(parts[1])
                    else:
                        print("Usage: chat <message>")
                
                elif cmd == 'subscribe':
                    if len(parts) > 1:
                        events = [e.strip() for e in parts[1].split(',')]
                        await client.subscribe(events)
                    else:
                        print("Usage: subscribe <event1>,<event2>,...")
                
                elif cmd == 'unsubscribe':
                    if len(parts) > 1:
                        events = [e.strip() for e in parts[1].split(',')]
                        await client.unsubscribe(events)
                    else:
                        print("Usage: unsubscribe <event1>,<event2>,...")
                
                elif cmd == 'music':
                    if len(parts) > 1:
                        music_parts = parts[1].split(None, 1)
                        action = music_parts[0].lower()
                        song_name = music_parts[1] if len(music_parts) > 1 else None
                        await client.control_music(action, song_name)
                    else:
                        print("Usage: music <play|pause|resume|stop> [song_name]")
                
                elif cmd == 'stats':
                    client.print_stats()
                
                elif cmd == 'reconnect':
                    await client.disconnect()
                    await client.connect()
                
                else:
                    print(f"Unknown command: {cmd}")
            
            except EOFError:
                break
    
    finally:
        if client.listen_task:
            client.listen_task.cancel()


async def automated_tests(client: WebSocketTestClient):
    """Run automated test suite"""
    print("""
╔════════════════════════════════════════╗
║   Automated WebSocket Tests            ║
╚════════════════════════════════════════╝
    """)
    
    # Start listening in background
    client.listen_task = asyncio.create_task(client.listen())
    
    try:
        # Test 1: Heartbeat
        print("\n[TEST 1] Testing heartbeat...")
        await client.send_message('ping', {})
        await asyncio.sleep(1)
        
        # Test 2: Subscriptions
        print("\n[TEST 2] Testing event subscriptions...")
        await client.subscribe(['MUSIC_PLAYING', 'MUSIC_PAUSED', 'FACT_LEARNED'])
        await asyncio.sleep(1)
        
        # Test 3: Chat
        print("\n[TEST 3] Testing chat...")
        await client.chat("What is 2+2?")
        await asyncio.sleep(3)
        
        await client.chat("Tell me a joke")
        await asyncio.sleep(3)
        
        # Test 4: Music control (if available)
        print("\n[TEST 4] Testing music control...")
        await client.control_music('play', 'jazz')
        await asyncio.sleep(2)
        
        await client.control_music('pause')
        await asyncio.sleep(1)
        
        # Test 5: Unsubscribe
        print("\n[TEST 5] Testing unsubscribe...")
        await client.unsubscribe(['MUSIC_PAUSED'])
        await asyncio.sleep(1)
        
        # Test 6: Reconnection (optional)
        print("\n[TEST 6] Testing reconnection...")
        print("Disconnecting in 3 seconds...")
        await asyncio.sleep(3)
        
        await client.disconnect()
        await asyncio.sleep(2)
        
        print("Reconnecting...")
        await client.connect()
        await asyncio.sleep(2)
        
        # Show stats
        print("\n[TESTS COMPLETE]")
        client.print_stats()
        
        print("\nContinuing to listen for events...")
        print("Press Ctrl+C to exit\n")
        
        # Keep listening
        await client.listen_task
    
    except asyncio.CancelledError:
        pass


# ============================================
# MAIN
# ============================================

async def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="WebSocket Test Client")
    parser.add_argument(
        '--server',
        default="ws://localhost:8000/ws",
        help="WebSocket server URL"
    )
    parser.add_argument(
        '--session-id',
        help="Session ID (auto-generated if not provided)"
    )
    parser.add_argument(
        '--user-id',
        default="test_user",
        help="User ID"
    )
    parser.add_argument(
        '--mode',
        choices=['interactive', 'auto'],
        default='interactive',
        help="Test mode"
    )
    parser.add_argument(
        '--no-reconnect',
        action='store_true',
        help="Disable auto-reconnection"
    )
    
    args = parser.parse_args()
    
    # Create client
    client = WebSocketTestClient(
        server_url=args.server,
        session_id=args.session_id,
        user_id=args.user_id,
        auto_reconnect=not args.no_reconnect
    )
    
    try:
        # Connect
        await client.connect()
        
        # Run mode
        if args.mode == 'interactive':
            await interactive_mode(client)
        else:
            await automated_tests(client)
    
    except KeyboardInterrupt:
        print("\n\n⏹️  Interrupted by user")
    
    except Exception as e:
        print(f"\n❌ Error: {e}")
    
    finally:
        await client.disconnect()
        client.print_stats()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
        sys.exit(0)