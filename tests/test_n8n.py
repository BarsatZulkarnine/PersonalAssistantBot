#!/usr/bin/env python3
"""
Test n8n Integration

Quick test script to verify n8n webhooks are working.
"""

import sys
import os
import asyncio
import requests
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from modules.actions.productivity.n8n_webhook import N8nWebhookAction
from dotenv import load_dotenv

load_dotenv()

def print_section(title: str):
    """Print section header"""
    print(f"\n{'='*70}")
    print(f"  {title}")
    print('='*70)

def test_n8n_availability():
    """Test if n8n is running"""
    print_section("Test 1: n8n Server Availability")
    
    base_url = os.getenv("N8N_BASE_URL", "http://localhost:5678")
    
    print(f"\n🔍 Checking n8n at: {base_url}")
    
    try:
        response = requests.get(f"{base_url}/healthz", timeout=5)
        
        if response.status_code == 200:
            print("✅ n8n is running!")
            return True
        else:
            print(f"⚠️  n8n responded with status: {response.status_code}")
            return False
    
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to n8n")
        print(f"   Make sure n8n is running: npx n8n")
        print(f"   Or: docker run -it --rm -p 5678:5678 n8nio/n8n")
        return False
    
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

async def test_action_initialization():
    """Test if action initializes correctly"""
    print_section("Test 2: Action Initialization")
    
    print("\n🔧 Initializing N8nWebhookAction...")
    
    try:
        action = N8nWebhookAction()
        
        print(f"✅ Action initialized")
        print(f"   Enabled: {action.enabled}")
        print(f"   Category: {action.category.value}")
        print(f"   Security: {action.security_level.value}")
        
        # Show available workflows
        workflows = action.get_available_workflows()
        print(f"\n📋 Available workflows ({len(workflows)}):")
        for workflow in workflows:
            config = action.get_workflow_info(workflow)
            print(f"   • {workflow}: {config.get('description', 'No description')}")
        
        return True
    
    except Exception as e:
        print(f"❌ Failed to initialize: {e}")
        return False

async def test_webhook_direct():
    """Test webhook directly (bypass action)"""
    print_section("Test 3: Direct Webhook Test")
    
    base_url = os.getenv("N8N_BASE_URL", "http://localhost:5678")
    
    # Use the test webhook path
    webhook_path = "/webhook-test/ac0a62b1-2305-4176-a743-a1c7a96a541a"
    webhook_url = f"{base_url}{webhook_path}"
    
    print(f"\n🔗 Testing webhook: {webhook_url}")
    
    payload = {
        "user_input": "Test from voice assistant",
        "test": True,
        "timestamp": "2025-01-15T10:30:00Z",
        "source": "voice_assistant_test_script"
    }
    
    try:
        print("📤 Sending test payload...")
        response = requests.post(
            webhook_url,
            json=payload,
            timeout=10
        )
        
        print(f"✅ Webhook responded: {response.status_code}")
        
        try:
            data = response.json()
            print(f"📄 Response (JSON):")
            import json
            print(f"   {json.dumps(data, indent=2)}")
        except:
            print(f"📄 Response (text):")
            print(f"   {response.text[:200]}")
        
        return True
    
    except requests.exceptions.Timeout:
        print("❌ Webhook timeout (>10s)")
        print("   Check if n8n workflow is active")
        return False
    
    except requests.exceptions.ConnectionError:
        print("❌ Connection error")
        print("   Make sure n8n is running at:", base_url)
        return False
    
    except Exception as e:
        print(f"❌ Webhook error: {e}")
        return False

async def test_action_execution():
    """Test action execution"""
    print_section("Test 4: Action Execution")
    
    action = N8nWebhookAction()
    
    if not action.enabled:
        print("⚠️  Action is disabled (no webhooks configured)")
        return False
    
    # Test prompts - including the test webhook
    test_prompts = [
        ("test n8n", "Should trigger test webhook"),
        ("check n8n", "Should trigger test webhook"),
        ("test webhook", "Should trigger test webhook"),
        ("send email to test@example.com", "Email workflow (if configured)"),
        ("add to calendar meeting tomorrow", "Calendar workflow (if configured)"),
    ]
    
    print("\n🧪 Testing prompts...")
    
    found_working = False
    
    for prompt, description in test_prompts:
        print(f"\n📝 Prompt: '{prompt}'")
        print(f"   ({description})")
        
        # Check if matches
        matches = action.matches(prompt)
        print(f"   Matches: {'✅ Yes' if matches else '❌ No'}")
        
        if matches:
            # Find workflow
            workflow_name, config = action._find_workflow(prompt)
            print(f"   Workflow: {workflow_name}")
            
            if config and config.get("webhook_path"):
                print(f"   Webhook: {config['webhook_path']}")
                
                # Try to execute (only for test_n8n to avoid spamming)
                if workflow_name == "test_n8n":
                    try:
                        print(f"   Executing...")
                        result = await action.execute(prompt)
                        if result.success:
                            print(f"   ✅ Success: {result.message}")
                            found_working = True
                        else:
                            print(f"   ⚠️  Failed: {result.message}")
                    except Exception as e:
                        print(f"   ❌ Error: {e}")
                else:
                    print(f"   ⏭️  Skipped (not test webhook)")
            else:
                print(f"   ⚠️  No webhook_path configured")
    
    return found_working

async def test_end_to_end():
    """Full end-to-end test"""
    print_section("Test 5: End-to-End Test (Test Webhook)")
    
    print("\n🔄 Full flow test with test webhook...")
    
    # Initialize action
    action = N8nWebhookAction()
    
    if not action.enabled:
        print("❌ Action disabled, skipping e2e test")
        return False
    
    # Test prompt for the test webhook
    test_prompt = "test n8n connection"
    
    print(f"\n1️⃣ User says: '{test_prompt}'")
    
    # Check if matches
    matches = action.matches(test_prompt)
    print(f"2️⃣ Action matches: {'✅ Yes' if matches else '❌ No'}")
    
    if not matches:
        print("   ⚠️  Test prompt doesn't match any intent")
        return False
    
    # Execute
    print(f"3️⃣ Executing action...")
    
    try:
        result = await action.execute(test_prompt, params={
            "test": True,
            "source": "end_to_end_test",
            "timestamp": "2025-01-15T10:30:00Z"
        })
        
        print(f"4️⃣ Result:")
        print(f"   Success: {'✅' if result.success else '❌'} {result.success}")
        print(f"   Message: {result.message}")
        
        if result.data:
            print(f"   Data: {result.data}")
        
        if result.success:
            print(f"\n✅ End-to-end test PASSED!")
            print(f"   Your n8n webhook is working correctly")
        else:
            print(f"\n⚠️  End-to-end test completed but workflow returned failure")
        
        return result.success
    
    except Exception as e:
        print(f"❌ Execution failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def run_all_tests():
    """Run all tests"""
    print("\n" + "="*70)
    print("  🧪 n8n Integration Tests")
    print("="*70)
    
    results = {}
    
    # Test 1: Server availability
    results['server'] = test_n8n_availability()
    
    # Test 2: Action initialization
    results['init'] = await test_action_initialization()
    
    # Test 3: Direct webhook (if server available)
    if results['server']:
        results['webhook'] = await test_webhook_direct()
    
    # Test 4: Action execution (if initialized)
    if results['init']:
        results['execution'] = await test_action_execution()
    
    # Test 5: End-to-end (if server available)
    if results['server'] and results['init']:
        results['e2e'] = await test_end_to_end()
    
    # Summary
    print_section("Summary")
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    print(f"\n✅ Passed: {passed}/{total}")
    
    for test, result in results.items():
        status = "✅" if result else "❌"
        print(f"   {status} {test}")
    
    if passed == total:
        print("\n🎉 All tests passed!")
        print("\n💡 Next steps:")
        print("   1. Create n8n workflow with webhook trigger")
        print("   2. Add webhook ID to .env")
        print("   3. Test with: python main.py --mode text")
        return True
    else:
        print("\n⚠️  Some tests failed")
        print("\n💡 Setup checklist:")
        print("   ☐ Start n8n: npx n8n (or Docker)")
        print("   ☐ Create workflow in n8n with webhook trigger")
        print("   ☐ Add webhook ID to .env: N8N_EMAIL_WEBHOOK=abc123")
        print("   ☐ Activate workflow in n8n")
        return False

if __name__ == "__main__":
    success = asyncio.run(run_all_tests())
    sys.exit(0 if success else 1)