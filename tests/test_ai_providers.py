#!/usr/bin/env python3
"""
Test AI Provider Abstraction

Tests OpenAI and Ollama providers to verify abstraction works.
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from core.ai import (
    AIProviderFactory, 
    AIMessage,
    set_default_provider,
    ai_complete,
    ai_chat
)
from dotenv import load_dotenv

load_dotenv()


async def test_openai():
    """Test OpenAI provider"""
    print("\n" + "="*60)
    print("Testing OpenAI Provider")
    print("="*60)
    
    try:
        provider = AIProviderFactory.create(
            "openai",
            model="gpt-4o-mini"
        )
        
        print(f"✓ Provider created: {provider.config.model}")
        print(f"✓ Capabilities: {[c.value for c in provider.capabilities]}")
        
        # Test simple completion
        print("\n1. Testing simple completion...")
        response = await provider.complete("What is 2+2? Answer in one sentence.")
        print(f"   Prompt: What is 2+2?")
        print(f"   Response: {response.content}")
        print(f"   Tokens: {response.usage.get('total_tokens', 'N/A')}")
        
        # Test chat
        print("\n2. Testing chat...")
        messages = [
            AIMessage(role="system", content="You are a helpful math tutor."),
            AIMessage(role="user", content="What is 5*7?")
        ]
        response = await provider.chat(messages)
        print(f"   Response: {response.content}")
        
        # Test streaming
        print("\n3. Testing streaming...")
        print("   Response: ", end="", flush=True)
        messages = [
            AIMessage(role="user", content="Count from 1 to 5, one number per line.")
        ]
        async for chunk in provider.stream_chat(messages, max_tokens=50):
            print(chunk, end="", flush=True)
        print()
        
        print("\n✅ OpenAI provider: ALL TESTS PASSED")
        return True
        
    except Exception as e:
        print(f"\n❌ OpenAI provider failed: {e}")
        return False


async def test_ollama():
    """Test Ollama provider"""
    print("\n" + "="*60)
    print("Testing Ollama Provider (Local LLMs)")
    print("="*60)
    
    try:
        provider = AIProviderFactory.create(
            "ollama",
            model="llama3:8b",
            base_url="http://localhost:11434"
        )
        
        print(f"✓ Provider created: {provider.config.model}")
        print(f"✓ Base URL: {provider.base_url}")
        
        # Test simple completion
        print("\n1. Testing simple completion...")
        response = await provider.complete("What is 2+2? Answer in one sentence.")
        print(f"   Prompt: What is 2+2?")
        print(f"   Response: {response.content}")
        print(f"   Tokens: {response.usage.get('total_tokens', 'N/A')}")
        print(f"   Duration: {response.metadata.get('eval_duration_ms', 0):.0f}ms")
        
        # Test chat
        print("\n2. Testing chat...")
        messages = [
            AIMessage(role="system", content="You are a helpful assistant."),
            AIMessage(role="user", content="What is 5*7?")
        ]
        response = await provider.chat(messages)
        print(f"   Response: {response.content}")
        
        print("\n✅ Ollama provider: ALL TESTS PASSED")
        return True
        
    except ConnectionError as e:
        print(f"\n⚠️  Ollama not running: {e}")
        print("   Start Ollama with: ollama serve")
        print("   Then pull a model: ollama pull llama3:8b")
        return False
    except Exception as e:
        print(f"\n❌ Ollama provider failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_default_provider():
    """Test default provider and convenience functions"""
    print("\n" + "="*60)
    print("Testing Default Provider System")
    print("="*60)
    
    try:
        # Set default to OpenAI
        provider = AIProviderFactory.create("openai", model="gpt-4o-mini")
        set_default_provider(provider)
        print("✓ Set OpenAI as default provider")
        
        # Test convenience function
        print("\n1. Testing ai_complete()...")
        response = await ai_complete("What is the capital of France? One word only.")
        print(f"   Response: {response}")
        
        # Test ai_chat convenience
        print("\n2. Testing ai_chat()...")
        messages = [
            AIMessage(role="user", content="Say 'Hello World'")
        ]
        response = await ai_chat(messages)
        print(f"   Response: {response}")
        
        print("\n✅ Default provider: ALL TESTS PASSED")
        return True
        
    except Exception as e:
        print(f"\n❌ Default provider failed: {e}")
        return False


async def test_provider_switching():
    """Test switching between providers"""
    print("\n" + "="*60)
    print("Testing Provider Switching")
    print("="*60)
    
    try:
        # Create both providers
        openai = AIProviderFactory.create("openai", model="gpt-4o-mini")
        
        print("✓ Created OpenAI provider")
        
        # Same question to both
        question = "What is 10 divided by 2? Answer with just the number."
        
        print(f"\n1. Question: {question}")
        
        print("\n   OpenAI response:")
        response1 = await openai.complete(question)
        print(f"   → {response1.content}")
        
        # Try Ollama if available
        try:
            ollama = AIProviderFactory.create("ollama", model="llama3:8b")
            print("\n   Ollama response:")
            response2 = await ollama.complete(question)
            print(f"   → {response2.content}")
            print("\n✓ Both providers gave answers (content may differ)")
        except ConnectionError:
            print("\n   (Ollama not available - skipping comparison)")
        
        print("\n✅ Provider switching: TEST PASSED")
        return True
        
    except Exception as e:
        print(f"\n❌ Provider switching failed: {e}")
        return False


async def main():
    """Run all tests"""
    print("""
    ╔════════════════════════════════════════╗
    ║   AI Provider Abstraction Tests        ║
    ╚════════════════════════════════════════╝
    """)
    
    results = []
    
    # Test OpenAI (should always work if API key is set)
    results.append(("OpenAI", await test_openai()))
    
    # Test Ollama (may not be available)
    results.append(("Ollama", await test_ollama()))
    
    # Test default provider system
    results.append(("Default Provider", await test_default_provider()))
    
    # Test switching
    results.append(("Provider Switching", await test_provider_switching()))
    
    # Summary
    print("\n" + "="*60)
    print("Test Summary")
    print("="*60)
    
    for name, passed in results:
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{name:.<40} {status}")
    
    all_passed = all(passed for _, passed in results)
    
    print("\n" + "="*60)
    if all_passed:
        print("🎉 ALL TESTS PASSED!")
    else:
        print("⚠️  Some tests failed (see above)")
    print("="*60)
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\nTests interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n💥 Critical error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)