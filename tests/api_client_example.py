"""
API Client Examples - Testing the REST API Interface

Run the API server first:
    python main.py --interface api

Then run these examples:
    python api_client_example.py
"""

import requests
import json
from typing import Optional


class AssistantAPIClient:
    """Python client for Voice Assistant API"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        """
        Initialize API client.
        
        Args:
            base_url: Base URL of the API server
        """
        self.base_url = base_url
        self.session_id: Optional[str] = None
    
    def health_check(self) -> dict:
        """
        Check if API is healthy.
        
        Returns:
            Health status dictionary
        """
        response = requests.get(f"{self.base_url}/health")
        response.raise_for_status()
        return response.json()
    
    def chat(
        self, 
        message: str, 
        user_id: str = "default_user",
        session_id: Optional[str] = None
    ) -> dict:
        """
        Send a chat message.
        
        Args:
            message: Message to send
            user_id: User identifier
            session_id: Session identifier (optional)
        
        Returns:
            Response dictionary
        """
        # Use stored session_id if not provided
        if session_id is None:
            session_id = self.session_id
        
        payload = {
            "message": message,
            "user_id": user_id,
            "session_id": session_id
        }
        
        response = requests.post(
            f"{self.base_url}/chat",
            json=payload
        )
        response.raise_for_status()
        
        data = response.json()
        
        # Store session_id for next request
        if 'session_id' in data.get('metadata', {}):
            self.session_id = data['metadata']['session_id']
        
        return data
    
    def get_stats(self) -> dict:
        """
        Get system statistics.
        
        Returns:
            Stats dictionary
        """
        response = requests.get(f"{self.base_url}/stats")
        response.raise_for_status()
        return response.json()


# ===== Example Usage =====

def example_health_check():
    """Example: Health check"""
    print("\n" + "="*60)
    print("Example 1: Health Check")
    print("="*60)
    
    client = AssistantAPIClient()
    
    try:
        health = client.health_check()
        print(f"✅ API Status: {health['status']}")
        print(f"   Service Ready: {health['service_ready']}")
        print(f"   Timestamp: {health['timestamp']}")
    except Exception as e:
        print(f"❌ Health check failed: {e}")


def example_simple_chat():
    """Example: Simple chat"""
    print("\n" + "="*60)
    print("Example 2: Simple Chat")
    print("="*60)
    
    client = AssistantAPIClient()
    
    messages = [
        "Hello!",
        "What's 2 + 2?",
        "Tell me a joke"
    ]
    
    for msg in messages:
        print(f"\nUser: {msg}")
        
        try:
            response = client.chat(msg)
            
            print(f"Assistant: {response['response']}")
            print(f"  Intent: {response['intent']}")
            print(f"  Confidence: {response['confidence']:.2f}")
            print(f"  Duration: {response['duration_ms']:.0f}ms")
            print(f"  Memory Stored: {response['memory_stored']} ({response['memory_category']})")
            
        except Exception as e:
            print(f"❌ Error: {e}")


def example_web_search():
    """Example: Web search"""
    print("\n" + "="*60)
    print("Example 3: Web Search")
    print("="*60)
    
    client = AssistantAPIClient()
    
    query = "What's the weather in Tokyo?"
    print(f"\nUser: {query}")
    
    try:
        response = client.chat(query)
        
        print(f"Assistant: {response['response']}")
        print(f"  Intent: {response['intent']}")
        print(f"  RAG Used: {response['rag_used']}")
        
    except Exception as e:
        print(f"❌ Error: {e}")


def example_memory_context():
    """Example: Using memory context"""
    print("\n" + "="*60)
    print("Example 4: Memory Context")
    print("="*60)
    
    client = AssistantAPIClient()
    
    # First, tell the assistant something
    print("\nUser: My name is Alice")
    try:
        response = client.chat("My name is Alice", user_id="alice123")
        print(f"Assistant: {response['response']}")
        print(f"  Memory Stored: {response['memory_stored']}")
        print(f"  Category: {response['memory_category']}")
    except Exception as e:
        print(f"❌ Error: {e}")
        return
    
    # Then ask about it
    print("\nUser: What's my name?")
    try:
        response = client.chat("What's my name?", user_id="alice123")
        print(f"Assistant: {response['response']}")
        print(f"  Used Memory: {response['memory_stored']}")
    except Exception as e:
        print(f"❌ Error: {e}")


def example_stats():
    """Example: Get statistics"""
    print("\n" + "="*60)
    print("Example 5: System Statistics")
    print("="*60)
    
    client = AssistantAPIClient()
    
    try:
        stats = client.get_stats()
        
        print(f"\n📊 System Stats:")
        print(f"  Actions Available: {stats['actions_available']}")
        print(f"  Memory Enabled: {stats['memory_enabled']}")
        print(f"  RAG Enabled: {stats['rag_enabled']}")
        
        if stats.get('memory_stats'):
            mem = stats['memory_stats']['sql']
            print(f"\n  Memory:")
            print(f"    Conversations: {mem['total_conversations']}")
            print(f"    Facts: {mem['total_facts']}")
            print(f"    Tokens: {mem['total_tokens']:,}")
        
        if stats.get('rag_stats'):
            rag = stats['rag_stats']
            print(f"\n  RAG:")
            print(f"    Documents: {rag['total_documents']}")
            print(f"    Chunks: {rag['total_chunks']}")
        
    except Exception as e:
        print(f"❌ Error: {e}")


def example_action_execution():
    """Example: Execute action"""
    print("\n" + "="*60)
    print("Example 6: Action Execution")
    print("="*60)
    
    client = AssistantAPIClient()
    
    # Try a system action
    print("\nUser: volume up")
    try:
        response = client.chat("volume up")
        
        print(f"Assistant: {response['response']}")
        print(f"  Intent: {response['intent']}")
        print(f"  Action Executed: {response['action_executed']}")
        
    except Exception as e:
        print(f"❌ Error: {e}")


def example_batch_requests():
    """Example: Multiple parallel requests"""
    print("\n" + "="*60)
    print("Example 7: Batch Requests")
    print("="*60)
    
    from concurrent.futures import ThreadPoolExecutor
    import time
    
    client = AssistantAPIClient()
    
    messages = [
        "What's 2+2?",
        "What's 3+3?",
        "What's 4+4?",
        "What's 5+5?"
    ]
    
    def send_message(msg):
        """Helper to send message"""
        try:
            return client.chat(msg)
        except Exception as e:
            return {"error": str(e)}
    
    print(f"\nSending {len(messages)} requests in parallel...")
    
    start = time.time()
    
    with ThreadPoolExecutor(max_workers=4) as executor:
        results = list(executor.map(send_message, messages))
    
    duration = time.time() - start
    
    print(f"\nCompleted in {duration:.2f}s")
    
    for i, (msg, result) in enumerate(zip(messages, results), 1):
        if 'error' in result:
            print(f"\n{i}. {msg}")
            print(f"   ❌ Error: {result['error']}")
        else:
            print(f"\n{i}. {msg}")
            print(f"   ✅ {result['response']}")
            print(f"   Duration: {result['duration_ms']:.0f}ms")


def example_curl_commands():
    """Example: cURL command equivalents"""
    print("\n" + "="*60)
    print("Example 8: cURL Commands")
    print("="*60)
    
    base_url = "http://localhost:8000"
    
    print("\nEquivalent cURL commands:")
    
    print("\n# Health Check")
    print(f"curl {base_url}/health")
    
    print("\n# Simple Chat")
    print(f"curl -X POST {base_url}/chat \\")
    print(f'  -H "Content-Type: application/json" \\')
    print(f"  -d '{{\"message\": \"Hello!\"}}'")
    
    print("\n# Chat with User ID")
    print(f"curl -X POST {base_url}/chat \\")
    print(f'  -H "Content-Type: application/json" \\')
    print(f"  -d '{{\"message\": \"My name is Alice\", \"user_id\": \"alice123\"}}'")
    
    print("\n# Get Stats")
    print(f"curl {base_url}/stats")
    
    print("\n# Pretty Print JSON (with jq)")
    print(f"curl {base_url}/stats | jq")


def run_all_examples():
    """Run all examples"""
    print("""
╔════════════════════════════════════════════════════════╗
║                                                        ║
║          Voice Assistant API - Client Examples         ║
║                                                        ║
╚════════════════════════════════════════════════════════╝

Make sure the API server is running:
    python main.py --interface api

Press Ctrl+C to stop.
    """)
    
    input("Press Enter to start examples...")
    
    try:
        example_health_check()
        example_simple_chat()
        example_web_search()
        example_memory_context()
        example_stats()
        example_action_execution()
        example_batch_requests()
        example_curl_commands()
        
        print("\n" + "="*60)
        print("✅ All examples completed!")
        print("="*60)
        
    except KeyboardInterrupt:
        print("\n\n👋 Examples stopped")
    except Exception as e:
        print(f"\n💥 Error running examples: {e}")


# ===== JavaScript Example =====

def print_javascript_example():
    """Print JavaScript client example"""
    js_code = """
// JavaScript API Client Example

class AssistantAPIClient {
    constructor(baseURL = 'http://localhost:8000') {
        this.baseURL = baseURL;
        this.sessionId = null;
    }
    
    async healthCheck() {
        const response = await fetch(`${this.baseURL}/health`);
        return await response.json();
    }
    
    async chat(message, userId = 'default_user', sessionId = null) {
        const response = await fetch(`${this.baseURL}/chat`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                message,
                user_id: userId,
                session_id: sessionId || this.sessionId
            })
        });
        
        const data = await response.json();
        if (data.metadata && data.metadata.session_id) {
            this.sessionId = data.metadata.session_id;
        }
        return data;
    }
    
    async getStats() {
        const response = await fetch(`${this.baseURL}/stats`);
        return await response.json();
    }
}

// Usage
const client = new AssistantAPIClient();

// Check health
const health = await client.healthCheck();
console.log('Status:', health.status);

// Send message
const response = await client.chat('Hello!');
console.log('Response:', response.response);
console.log('Intent:', response.intent);

// Get stats
const stats = await client.getStats();
console.log('Actions:', stats.actions_available);
"""
    
    print("\n" + "="*60)
    print("JavaScript Client Example")
    print("="*60)
    print(js_code)


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == '--js':
        print_javascript_example()
    else:
        run_all_examples()