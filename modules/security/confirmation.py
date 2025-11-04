"""
Security Module - Confirmation System

Handles user confirmations for sensitive actions.
"""

import yaml
from pathlib import Path
from typing import Optional
from utils.logger import get_logger

logger = get_logger('security.confirmation')

class ConfirmationManager:
    """Manages confirmation flows for sensitive actions"""
    
    def __init__(self):
        self.config = self._load_config()
        self.enabled = self.config.get('confirmation', {}).get('enabled', True)
        self.timeout = self.config.get('confirmation', {}).get('timeout', 30)
        self.required_actions = self.config.get('confirmation', {}).get('require_for', [])
        
        logger.info(f"Confirmation manager initialized (enabled={self.enabled})")
    
    def _load_config(self) -> dict:
        """Load security config"""
        config_path = Path("config/security.yaml")
        
        if not config_path.exists():
            logger.warning("security.yaml not found, using defaults")
            return self._default_config()
        
        with open(config_path, 'r') as f:
            return yaml.safe_load(f) or {}
    
    def _default_config(self) -> dict:
        """Default security config"""
        return {
            'confirmation': {
                'enabled': True,
                'timeout': 30,
                'require_for': ['send_email', 'delete_file', 'make_payment'],
                'method': 'voice'
            }
        }
    
    def requires_confirmation(self, action_name: str) -> bool:
        """
        Check if action requires confirmation.
        
        Args:
            action_name: Name of action to check
            
        Returns:
            True if confirmation needed
        """
        if not self.enabled:
            return False
        
        # Check if action in required list
        for required in self.required_actions:
            if required.lower() in action_name.lower():
                return True
        
        return False
    
    async def request_confirmation(
        self,
        action_name: str,
        prompt: str,
        details: Optional[dict] = None
    ) -> bool:
        """
        Request user confirmation for an action.
        
        Args:
            action_name: Name of action
            prompt: Confirmation prompt to speak
            details: Additional details to include
            
        Returns:
            True if confirmed, False if denied
        """
        if not self.enabled:
            return True
        
        logger.info(f"Requesting confirmation for: {action_name}")
        
        # TODO: Implement actual confirmation flow
        # For now, just return True
        logger.warning("Confirmation flow not implemented yet, auto-approving")
        return True
    
    def get_confirmation_prompt(
        self,
        action_name: str,
        details: Optional[dict] = None
    ) -> str:
        """
        Generate confirmation prompt.
        
        Args:
            action_name: Name of action
            details: Action details
            
        Returns:
            Confirmation prompt text
        """
        base_prompt = f"Are you sure you want to {action_name}?"
        
        if details:
            detail_text = ", ".join([f"{k}: {v}" for k, v in details.items()])
            base_prompt += f" ({detail_text})"
        
        base_prompt += " Say yes to confirm or no to cancel."
        
        return base_prompt

# Global instance
_confirmation_manager = None

def get_confirmation_manager() -> ConfirmationManager:
    """Get global confirmation manager"""
    global _confirmation_manager
    if _confirmation_manager is None:
        _confirmation_manager = ConfirmationManager()
    return _confirmation_manager