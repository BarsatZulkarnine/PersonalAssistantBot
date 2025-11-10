"""
n8n Webhook Action - IMPROVED ERROR HANDLING

Handles all response types including empty responses.
"""

import os
import yaml
import requests
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime
from dotenv import load_dotenv
from modules.actions.base import Action, ActionResult, ActionCategory, SecurityLevel
from utils.logger import get_logger

load_dotenv()
logger = get_logger('actions.n8n')

class N8nWebhookAction(Action):
    """
    Generic n8n webhook action with robust error handling.
    """
    
    def __init__(self):
        super().__init__()
        self.category = ActionCategory.PRODUCTIVITY
        self.security_level = SecurityLevel.SAFE
        self.description = "Trigger n8n workflows for external integrations"
        
        # Load configuration
        self.base_url = os.getenv("N8N_BASE_URL", "http://localhost:5678")
        self.auth_token = os.getenv("N8N_AUTH_TOKEN")
        
        # Load webhook mappings
        self.webhook_mappings = self._load_webhook_mappings()
        
        # Check if any webhooks are configured
        configured_count = sum(1 for config in self.webhook_mappings.values() 
                             if config.get("webhook_path"))
        
        if configured_count > 0:
            logger.info(f"[OK] n8n integration initialized with {configured_count} configured webhooks")
            print(f"[N8N] Initialized with {configured_count} configured webhooks")
            self.enabled = True
        else:
            logger.warning("[WARN] No n8n webhooks configured (all webhook_path are null)")
            print("[N8N] ⚠️  No webhooks configured - add webhook paths to config")
            self.enabled = False
    
    def _load_webhook_mappings(self) -> Dict[str, Dict[str, Any]]:
        """Load webhook mappings from config file"""
        config_path = Path("config/modules/n8n.yaml")
        
        if not config_path.exists():
            logger.warning(f"Config file not found: {config_path}")
            return self._get_default_mappings()
        
        try:
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
                webhooks = config.get('webhooks', {})
                
                # Load from environment variables if webhook_path is null
                for workflow_name, workflow_config in webhooks.items():
                    if workflow_config.get('webhook_path') is None:
                        env_var = f"N8N_{workflow_name.upper()}_WEBHOOK"
                        env_value = os.getenv(env_var)
                        if env_value:
                            workflow_config['webhook_path'] = env_value
                            logger.info(f"Loaded {workflow_name} from env: {env_var}")
                
                logger.info(f"Loaded {len(webhooks)} webhook mappings from config")
                return webhooks
                
        except Exception as e:
            logger.error(f"Failed to load n8n config: {e}")
            return self._get_default_mappings()
    
    def _get_default_mappings(self) -> Dict[str, Dict[str, Any]]:
        """Get default webhook mappings from environment"""
        return {
            "test_n8n": {
                "webhook_path": os.getenv("N8N_TEST_WEBHOOK", "/webhook/ac0a62b1-2305-4176-a743-a1c7a96a541a"),
                "description": "Test n8n connection",
                "confirmation": False,
                "intents": ["test n8n", "test webhook", "check n8n", "webhook test", "n8n test"]
            }
        }
    
    def get_intents(self) -> List[str]:
        """Get all intents from webhook mappings"""
        intents = []
        
        for workflow_name, config in self.webhook_mappings.items():
            # Skip if no webhook path configured
            if not config.get("webhook_path"):
                continue
                
            # Add custom intents
            if "intents" in config:
                intents.extend(config["intents"])
            else:
                # Default: use workflow name
                intents.append(workflow_name.replace("_", " "))
        
        return intents
    
    def matches(self, prompt: str) -> bool:
        """Check if prompt matches any n8n workflow"""
        prompt_lower = prompt.lower()
        
        # PRIORITY 1: Special case for test commands
        test_keywords = ["test", "check", "verify"]
        n8n_keywords = ["n8n", "webhook", "workflow"]
        
        if any(test in prompt_lower for test in test_keywords):
            if any(n8n in prompt_lower for n8n in n8n_keywords):
                logger.debug(f"Matched test workflow: {prompt_lower}")
                return True
        
        # PRIORITY 2: Check all webhook mappings
        for workflow_name, config in self.webhook_mappings.items():
            # Skip if no webhook path
            if not config.get("webhook_path"):
                continue
            
            # Check custom intents
            if "intents" in config:
                for intent in config["intents"]:
                    intent_lower = intent.lower()
                    # Exact match or word boundary match
                    if intent_lower == prompt_lower or f" {intent_lower} " in f" {prompt_lower} ":
                        logger.debug(f"Matched workflow '{workflow_name}' via intent '{intent}'")
                        return True
            
            # Check workflow name
            workflow_phrase = workflow_name.replace("_", " ").lower()
            if workflow_phrase in prompt_lower:
                logger.debug(f"Matched workflow name: {workflow_name}")
                return True
        
        return False
    
    async def execute(self, prompt: str, params: Optional[Dict[str, Any]] = None) -> ActionResult:
        """Execute n8n workflow"""
        try:
            # Find matching workflow
            workflow_name, workflow_config = self._find_workflow(prompt)
            
            if not workflow_name or not workflow_config:
                logger.warning(f"No workflow found for: {prompt}")
                return ActionResult(
                    success=False,
                    message="I couldn't find a matching n8n workflow for that command."
                )
            
            webhook_path = workflow_config.get("webhook_path")
            if not webhook_path:
                return ActionResult(
                    success=False,
                    message=f"Workflow '{workflow_name}' is not configured. Add webhook_path to config."
                )
            
            logger.info(f"Triggering n8n workflow: {workflow_name}")
            print(f"[N8N] 🚀 Triggering: {workflow_name}")
            
            # Build webhook URL
            webhook_url = f"{self.base_url}{webhook_path}"
            
            # Prepare payload
            payload = {
                "user_input": prompt,
                "workflow_name": workflow_name,
                "timestamp": datetime.now().isoformat()
            }
            
            # Add optional parameters
            if params:
                if "memory_context" in params:
                    payload["context"] = params["memory_context"]
                if "user_id" in params:
                    payload["user_id"] = params["user_id"]
            
            # Make request
            response = await self._call_webhook(webhook_url, payload)
            
            # Handle response
            return self._process_response(response, workflow_name)
        
        except Exception as e:
            logger.error(f"n8n execution error: {e}", exc_info=True)
            print(f"[N8N] ❌ Error: {e}")
            
            return ActionResult(
                success=False,
                message=f"n8n error: {str(e)}"
            )
    
    def _process_response(self, response: Dict[str, Any], workflow_name: str) -> ActionResult:
        """
        Process n8n webhook response with robust error handling.
        
        Handles:
        - Standard responses: {"success": true, "message": "..."}
        - Empty responses: {}
        - Non-JSON responses: "OK"
        - Error responses: {"success": false, "error": "..."}
        """
        # Case 1: Empty or None response
        if not response or response == {}:
            logger.warning(f"Empty response from workflow '{workflow_name}'")
            print(f"[N8N] ⚠️  Empty response - workflow may need 'Respond to Webhook' node")
            return ActionResult(
                success=True,  # Assume success if webhook was triggered
                message=f"Workflow '{workflow_name}' triggered (no response configured). "
                       f"Add 'Respond to Webhook' node to n8n workflow for confirmation."
            )
        
        # Case 2: Standard format with success field
        if "success" in response:
            success = response.get("success")
            message = response.get("message", "Workflow completed")
            
            if success:
                logger.info(f"n8n success: {message}")
                print(f"[N8N] ✅ {message}")
            else:
                error = response.get("error", "Unknown error")
                logger.error(f"n8n failed: {error}")
                print(f"[N8N] ❌ {error}")
            
            return ActionResult(
                success=success,
                message=message,
                data=response.get("data")
            )
        
        # Case 3: Non-standard response (has message but no success field)
        if "message" in response:
            message = response.get("message")
            logger.info(f"n8n response (non-standard): {message}")
            print(f"[N8N] ✅ {message}")
            return ActionResult(
                success=True,
                message=message,
                data=response
            )
        
        # Case 4: Plain text response
        if isinstance(response, str):
            logger.info(f"n8n text response: {response}")
            print(f"[N8N] ✅ {response}")
            return ActionResult(
                success=True,
                message=response
            )
        
        # Case 5: Unknown format - treat as success if we got here
        logger.warning(f"Unexpected response format: {response}")
        print(f"[N8N] ⚠️  Unexpected response format (but webhook triggered)")
        return ActionResult(
            success=True,
            message=f"Workflow '{workflow_name}' triggered. Response format: {str(response)[:100]}"
        )
    
    def _find_workflow(self, prompt: str) -> tuple:
        """Find matching workflow for prompt"""
        prompt_lower = prompt.lower()
        
        # Priority 1: Test workflow
        test_keywords = ["test", "check", "verify"]
        n8n_keywords = ["n8n", "webhook", "workflow"]
        
        if any(test in prompt_lower for test in test_keywords):
            if any(n8n in prompt_lower for n8n in n8n_keywords):
                test_config = self.webhook_mappings.get("test_n8n")
                if test_config and test_config.get("webhook_path"):
                    return ("test_n8n", test_config)
        
        # Priority 2: Exact intent matches
        for workflow_name, config in self.webhook_mappings.items():
            if not config.get("webhook_path"):
                continue
                
            if "intents" in config:
                for intent in config["intents"]:
                    if intent.lower() == prompt_lower:
                        return (workflow_name, config)
        
        # Priority 3: Partial matches
        for workflow_name, config in self.webhook_mappings.items():
            if not config.get("webhook_path"):
                continue
                
            if "intents" in config:
                for intent in config["intents"]:
                    intent_lower = intent.lower()
                    if intent_lower in prompt_lower or f" {intent_lower} " in f" {prompt_lower} ":
                        return (workflow_name, config)
            
            # Check workflow name
            workflow_phrase = workflow_name.replace("_", " ").lower()
            if workflow_phrase in prompt_lower:
                return (workflow_name, config)
        
        return (None, None)
    
    async def _call_webhook(self, url: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Call n8n webhook"""
        try:
            headers = {"Content-Type": "application/json"}
            
            if self.auth_token:
                headers["Authorization"] = f"Bearer {self.auth_token}"
            
            logger.debug(f"Calling webhook: {url}")
            logger.debug(f"Payload: {payload}")
            
            # Synchronous request
            response = requests.post(
                url,
                json=payload,
                headers=headers,
                timeout=30
            )
            
            # Log response details
            logger.debug(f"Response status: {response.status_code}")
            logger.debug(f"Response body: {response.text[:500]}")
            
            response.raise_for_status()
            
            # Try to parse JSON response
            try:
                return response.json()
            except ValueError:
                # Non-JSON response
                text = response.text.strip()
                if text:
                    return {"message": text}
                else:
                    # Empty response
                    return {}
        
        except requests.exceptions.Timeout:
            logger.error("Webhook timeout")
            return {
                "success": False,
                "error": "Webhook request timed out"
            }
        
        except requests.exceptions.RequestException as e:
            logger.error(f"Webhook request error: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_available_workflows(self) -> List[str]:
        """Get list of configured workflows"""
        return [name for name, config in self.webhook_mappings.items() 
                if config.get("webhook_path")]