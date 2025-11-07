"""
n8n Webhook Action

Trigger n8n workflows via webhooks for external integrations.
"""

import os
import requests
from typing import List, Optional, Dict, Any
from dotenv import load_dotenv
from modules.actions.base import Action, ActionResult, ActionCategory, SecurityLevel
from utils.logger import get_logger

load_dotenv()
logger = get_logger('actions.n8n')

class N8nWebhookAction(Action):
    """
    Generic n8n webhook action.
    
    Routes voice commands to n8n workflows for external integrations.
    
    Setup:
    1. Create n8n workflow with webhook trigger
    2. Add webhook URL to config
    3. Map intents to workflows
    """
    
    def __init__(self):
        super().__init__()
        self.category = ActionCategory.PRODUCTIVITY
        self.security_level = SecurityLevel.CONFIRM  # Require confirmation for external actions
        self.description = "Trigger n8n workflows for external integrations"
        
        # Load n8n configuration
        self.base_url = os.getenv("N8N_BASE_URL", "http://localhost:5678")
        self.auth_token = os.getenv("N8N_AUTH_TOKEN")  # Optional
        
        # Load webhook mappings from config
        self.webhook_mappings = self._load_webhook_mappings()
        
        if self.webhook_mappings:
            workflow_names = list(self.webhook_mappings.keys())
            logger.info(f"[OK] n8n integration initialized ({len(self.webhook_mappings)} workflows): {workflow_names}")
            print(f"[N8N] Initialized with workflows: {workflow_names}")
        else:
            logger.warning("[WARN] No n8n webhooks configured")
            print("[N8N] Warning: No webhooks configured")
            self.enabled = False
    
    def _load_webhook_mappings(self) -> Dict[str, Dict[str, Any]]:
        """
        Load webhook mappings from environment or config.
        
        Format:
        {
            "test_n8n": {
                "webhook_path": "/webhook-test/ac0a62b1-2305-4176-a743-a1c7a96a541a",
                "description": "Test n8n connection",
                "confirmation": False
            },
            "send_email": {
                "webhook_path": "/webhook/abc123",
                "description": "Send email via Gmail",
                "confirmation": True
            }
        }
        """
        import json
        
        # Try to load from config file first
        from pathlib import Path
        config_path = Path("config/modules/n8n.yaml")
        if config_path.exists():
            import yaml
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
                return config.get('webhooks', {})
        
        # Fallback: Try to load from environment variable
        mappings_json = os.getenv("N8N_WEBHOOK_MAPPINGS")
        if mappings_json:
            try:
                return json.loads(mappings_json)
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse N8N_WEBHOOK_MAPPINGS: {e}")
        
        # Default mappings (examples) - using webhook_path instead of webhook_id
        return {
            "test_n8n": {
                "webhook_path": "/webhook-test",  # Simplified test webhook path
                "description": "Test n8n connection",
                "confirmation": False,
                "intents": [
                    "test n8n",
                    "test webhook",
                    "check n8n",
                    "n8n test",
                    "webhook test"
                ]
            },
            "send_email": {
                "webhook_path": os.getenv("N8N_EMAIL_WEBHOOK"),
                "description": "Send email",
                "confirmation": True,
                "intents": ["send email", "email"]
            },
            "add_calendar": {
                "webhook_path": os.getenv("N8N_CALENDAR_WEBHOOK"),
                "description": "Add calendar event",
                "confirmation": True,
                "intents": ["add to calendar", "schedule", "remind me"]
            },
            "create_note": {
                "webhook_path": os.getenv("N8N_NOTE_WEBHOOK"),
                "description": "Create note in Notion/Evernote",
                "confirmation": False,
                "intents": ["take note", "note", "remember"]
            },
            "slack_message": {
                "webhook_path": os.getenv("N8N_SLACK_WEBHOOK"),
                "description": "Send Slack message",
                "confirmation": True,
                "intents": ["slack", "message team"]
            },
            "github_issue": {
                "webhook_path": os.getenv("N8N_GITHUB_WEBHOOK"),
                "description": "Create GitHub issue",
                "confirmation": True,
                "intents": ["create issue", "github bug"]
            },
            "log_sheet": {
                "webhook_path": os.getenv("N8N_SHEETS_WEBHOOK"),
                "description": "Log to Google Sheets",
                "confirmation": False,
                "intents": ["log this", "add to spreadsheet"]
            }
        }
    
    def get_intents(self) -> List[str]:
        """Get all intents from webhook mappings"""
        intents = []
        
        for workflow_name, config in self.webhook_mappings.items():
            # Add custom intents if defined
            if "intents" in config:
                intents.extend(config["intents"])
            else:
                # Default: use workflow name
                intents.append(workflow_name.replace("_", " "))
        
        return intents
    
    def matches(self, prompt: str) -> bool:
        """Check if prompt matches any n8n workflow"""
        prompt_lower = prompt.lower()
        
        # Special case: If it contains "n8n" or "webhook", it should be handled by this action
        if "n8n" in prompt_lower or "webhook" in prompt_lower:
            return True
            
        # Check all webhook mappings
        for workflow_name, config in self.webhook_mappings.items():
            # Check custom intents
            if "intents" in config:
                for intent in config["intents"]:
                    # Use more exact matching
                    intent_lower = intent.lower()
                    if (intent_lower in prompt_lower and 
                        (len(intent_lower.split()) > 1 or  # Multi-word intent
                         prompt_lower.startswith(intent_lower + " ") or  # Start of prompt
                         prompt_lower.endswith(" " + intent_lower) or  # End of prompt
                         f" {intent_lower} " in prompt_lower)):  # Whole word match
                        return True
            
            # Check workflow name
            workflow_phrase = workflow_name.replace("_", " ").lower()
            if (workflow_phrase in prompt_lower and 
                (len(workflow_phrase.split()) > 1 or  # Multi-word name
                 prompt_lower.startswith(workflow_phrase + " ") or  # Start of prompt
                 prompt_lower.endswith(" " + workflow_phrase) or  # End of prompt
                 f" {workflow_phrase} " in prompt_lower)):  # Whole word match
                return True
        
        return False
    
    async def execute(self, prompt: str, params: Optional[Dict[str, Any]] = None) -> ActionResult:
        """
        Execute n8n workflow.
        
        Args:
            prompt: User's command
            params: Optional parameters including:
                - workflow_name: Specific workflow to trigger
                - memory_context: Memory context from assistant
                - user_id: User identifier
        """
        try:
            # Determine which workflow to trigger
            result = self._find_workflow(prompt)
            if result is None or result == (None, None):
                return ActionResult(
                    success=False,
                    message="No matching n8n workflow found"
                )
                
            workflow_name, workflow_config = result
            
            webhook_path = workflow_config.get("webhook_path")
            if not webhook_path:
                logger.error(f"No webhook_path for {workflow_name}")
                return ActionResult(
                    success=False,
                    message=f"n8n workflow '{workflow_name}' not configured"
                )
            
            logger.info(f"Triggering n8n workflow: {workflow_name}")
            print(f"[N8N] Triggering: {workflow_name}")
            
            # Build webhook URL
            webhook_url = f"{self.base_url}{webhook_path}"
            
            # Prepare payload
            payload = {
                "user_input": prompt,
                "workflow_name": workflow_name,
                "timestamp": self._get_timestamp()
            }
            
            # Add optional parameters
            if params:
                if "memory_context" in params:
                    payload["context"] = params["memory_context"]
                if "user_id" in params:
                    payload["user_id"] = params["user_id"]
                if "intent_type" in params:
                    payload["intent_type"] = params["intent_type"]
            
            # Make request to n8n
            response = await self._call_webhook(webhook_url, payload)
            
            if response.get("success"):
                message = response.get("message", f"Workflow '{workflow_name}' triggered successfully")
                logger.info(f"n8n success: {message}")
                print(f"[N8N] ✅ {message}")
                
                return ActionResult(
                    success=True,
                    message=message,
                    data=response
                )
            else:
                error = response.get("error", "Unknown error")
                logger.error(f"n8n failed: {error}")
                print(f"[N8N] ❌ {error}")
                
                return ActionResult(
                    success=False,
                    message=f"Workflow failed: {error}"
                )
        
        except Exception as e:
            logger.error(f"n8n execution error: {e}")
            print(f"[N8N] ❌ Error: {e}")
            
            return ActionResult(
                success=False,
                message=f"n8n error: {str(e)}"
            )
    
    def _find_workflow(self, prompt: str) -> tuple:
        """
        Find matching workflow for prompt.
        
        Returns:
            (workflow_name, workflow_config) or (None, None)
            
        Matching priority:
        1. Test workflow (if contains test/check + n8n/webhook)
        2. Exact intent matches
        3. Fuzzy matches with word boundaries
        4. Workflow name matches
        5. Fallback for general test requests
        """
        prompt_lower = prompt.lower()
        logger.debug(f"Finding workflow for: {prompt_lower}")
        logger.debug(f"Available mappings: {list(self.webhook_mappings.keys())}")
        
        # 1. Special case - Test workflow check
        test_phrases = ["test", "check"]
        webhook_phrases = ["n8n", "webhook"]
        if any(t in prompt_lower for t in test_phrases):
            if any(w in prompt_lower for w in webhook_phrases):
                test_config = self.webhook_mappings.get("test_n8n")
                if test_config:
                    logger.info(f"Found test workflow: {test_config}")
                    return ("test_n8n", test_config)
                else:
                    logger.debug("Test phrase found but no test_n8n config")

        # 2. Try exact intent matches
        for workflow_name, config in self.webhook_mappings.items():
            if "intents" in config:
                for intent in config["intents"]:
                    if intent.lower() == prompt_lower:
                        logger.debug(f"Found exact match: {workflow_name}")
                        return (workflow_name, config)
        
        # 3. Try fuzzy intent matches with word boundaries
        for workflow_name, config in self.webhook_mappings.items():
            if "intents" in config:
                for intent in config["intents"]:
                    intent_lower = intent.lower()
                    if (intent_lower in prompt_lower and 
                        (len(intent_lower.split()) > 1 or  # Multi-word intent
                         prompt_lower.startswith(intent_lower + " ") or  # Start of prompt
                         prompt_lower.endswith(" " + intent_lower) or  # End of prompt
                         f" {intent_lower} " in prompt_lower)):  # Whole word match
                        logger.debug(f"Found fuzzy match: {workflow_name} via intent: {intent_lower}")
                        return (workflow_name, config)
            
            # 4. Try workflow name match
            workflow_phrase = workflow_name.replace("_", " ").lower()
            if (workflow_phrase in prompt_lower and 
                (len(workflow_phrase.split()) > 1 or  # Multi-word name
                 prompt_lower.startswith(workflow_phrase + " ") or  # Start of prompt
                 prompt_lower.endswith(" " + workflow_phrase) or  # End of prompt
                 f" {workflow_phrase} " in prompt_lower)):  # Whole word match
                logger.debug(f"Found workflow name match: {workflow_name}")
                return (workflow_name, config)
        
        # 5. Special fallback for general test requests
        if any(t in prompt_lower for t in test_phrases) and any(w in prompt_lower for w in webhook_phrases):
            test_config = self.webhook_mappings.get("test_n8n")
            if test_config:
                logger.debug("Found test workflow via fallback")
                return ("test_n8n", test_config)
        
        logger.debug(f"No workflow found for: {prompt_lower}")
        return (None, None)
    
    async def _call_webhook(self, url: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Call n8n webhook.
        
        Args:
            url: Webhook URL
            payload: JSON payload
            
        Returns:
            Response from n8n
        """
        try:
            # Prepare headers
            headers = {"Content-Type": "application/json"}
            
            # Add auth token if configured
            if self.auth_token:
                headers["Authorization"] = f"Bearer {self.auth_token}"
            
            # Make POST request
            response = requests.post(
                url,
                json=payload,
                headers=headers,
                timeout=30
            )
            
            # Check status
            response.raise_for_status()
            
            # Parse response
            try:
                return response.json()
            except ValueError:
                # If response is not JSON, return success with text
                return {
                    "success": True,
                    "message": response.text or "Webhook triggered successfully"
                }
        
        except requests.exceptions.Timeout:
            logger.error("n8n webhook timeout")
            return {
                "success": False,
                "error": "Webhook request timed out"
            }
        
        except requests.exceptions.RequestException as e:
            logger.error(f"n8n webhook error: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def _get_timestamp(self) -> str:
        """Get current timestamp in ISO format"""
        from datetime import datetime
        return datetime.now().isoformat()
    
    def get_available_workflows(self) -> List[str]:
        """Get list of available workflow names"""
        return list(self.webhook_mappings.keys())
    
    def get_workflow_info(self, workflow_name: str) -> Optional[Dict[str, Any]]:
        """Get information about a specific workflow"""
        return self.webhook_mappings.get(workflow_name)
