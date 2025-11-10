
#!/usr/bin/env python3
"""
WebSocket Test Client

Tests the event bus system.

Usage:
    python websocket_test_client.py
"""

import asyncio
import websockets
import json
from datetime import datetime

class WebSocketTestClient:
    """Test client for WebSocket event bus"""
    
    def __init__(self, server_url: str = "ws://localhost:8000/ws"):
        self.server_url = server_url
        self.session_id = f"test_{datetime.now().strftime('%H%M%S')}"
        self.ws = None
    
    async def connect(self):
        """Connect to WebSocket server"""
        url = f"{self.server_url}?session_id={self.session_id}&user_id=test_user&client_type=test"
        print(f"Connecting to {url}...")
        
        self.ws = await websockets.connect(url)
        print(f"✅ Connected! Session: {self.session_id}")
    
    async def listen(self):
        """Listen for events"""
        print("\n👂 Listening for events...\n")
        
        try:
            async for message in self.ws:
                data = json.loads(message)
                
                event_type = data.get('type')
                event_data = data.get('data', {})
                timestamp = data.get('timestamp', '')
                
                # Pretty print event
                print(f"[{timestamp[11:19]}] {event_type}")
                print(f"  Data: {json.dumps(event_data, indent=2)}")
                print()
        
        except websockets.exceptions.ConnectionClosed:
            print("❌ Connection closed")
    
    async def send_message(self, message_type: str, data: dict):
        """Send message to server"""
        payload = {
            'type': message_type,
            **data
        }
        
        await self.ws.send(json.dumps(payload))
        print(f"📤 Sent: {message_type}")
    
    async def test_chat(self):
        """Test chat via WebSocket"""
        print("\n🧪 Testing chat...")
        
        await self.send_message('chat', {
            'message': 'What is 2+2?'
        })
        
        await asyncio.sleep(2)
        
        await self.send_message('chat', {
            'message': 'play jazz music'
        })
        
        await asyncio.sleep(2)
    
    async def test_subscriptions(self):
        """Test subscription management"""
        print("\n🧪 Testing subscriptions...")
        
        # Subscribe to specific events
        await self.send_message('subscribe', {
            'events': ['MUSIC_PLAYING', 'MUSIC_PAUSED', 'FACT_LEARNED']
        })
        
        await asyncio.sleep(1)
        
        # Unsubscribe from some
        await self.send_message('unsubscribe', {
            'events': ['MUSIC_PAUSED']
        })
        
        await asyncio.sleep(1)
    
    async def test_heartbeat(self):
        """Test ping/pong"""
        print("\n🧪 Testing heartbeat...")
        
        for i in range(3):
            await self.send_message('ping', {})
            await asyncio.sleep(1)
    
    async def run_tests(self):
        """Run all tests"""
        await self.connect()
        
        # Start listening in background
        listen_task = asyncio.create_task(self.listen())
        
        # Give time for welcome message
        await asyncio.sleep(1)
        
        # Run tests
        await self.test_heartbeat()
        await self.test_subscriptions()
        await self.test_chat()
        
        # Keep listening
        print("\n👂 Continuing to listen for events...")
        print("   Press Ctrl+C to exit\n")
        
        try:
            await listen_task
        except asyncio.CancelledError:
            pass
    
    async def close(self):
        """Close connection"""
        if self.ws:
            await self.ws.close()
            print("👋 Disconnected")


async def main():
    """Main entry point"""
    print("""
╔════════════════════════════════════════╗
║   WebSocket Event Bus Test Client     ║
╚════════════════════════════════════════╝
    """)
    
    client = WebSocketTestClient()
    
    try:
        await client.run_tests()
    except KeyboardInterrupt:
        print("\n\n⏹️  Stopping...")
        await client.close()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())