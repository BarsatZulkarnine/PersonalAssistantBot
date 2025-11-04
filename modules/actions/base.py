"""
Actions Module - Base Interface

Modular action system with categories.
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from dataclasses import dataclass
from enum import Enum

class ActionCategory(Enum):
    """Action categories for organization"""
    HOME_AUTOMATION = "home_automation"
    PRODUCTIVITY = "productivity"
    SYSTEM = "system"
    CONVERSATION = "conversation"

class SecurityLevel(Enum):
    """Security levels for actions"""
    SAFE = "safe"                  # No confirmation needed
    CONFIRM = "confirm"            # Requires user confirmation
    AUTH_REQUIRED = "auth"         # Requires authentication

@dataclass
class ActionResult:
    """Result of action execution"""
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None
    requires_confirmation: bool = False
    confirmation_prompt: Optional[str] = None

class Action(ABC):
    """
    Base class for all actions.
    
    Each action belongs to a category and can be easily added/removed.
    """
    
    def __init__(self):
        self.name = self.__class__.__name__
        self.category: ActionCategory = ActionCategory.CONVERSATION
        self.security_level: SecurityLevel = SecurityLevel.SAFE
        self.enabled: bool = True
        self.description: str = ""
    
    @abstractmethod
    def get_intents(self) -> List[str]:
        """
        Return list of phrases that trigger this action.
        
        Returns:
            List of intent patterns
        """
        pass
    
    @abstractmethod
    async def execute(self, prompt: str, params: Optional[Dict[str, Any]] = None) -> ActionResult:
        """
        Execute the action.
        
        Args:
            prompt: Original user prompt
            params: Optional extracted parameters
            
        Returns:
            ActionResult with success status and message
        """
        pass
    
    def matches(self, prompt: str) -> bool:
        """
        Check if prompt matches this action.
        
        Args:
            prompt: User prompt
            
        Returns:
            True if matches
        """
        prompt_lower = prompt.lower()
        for intent in self.get_intents():
            if intent.lower() in prompt_lower:
                return True
        return False
    
    def get_category(self) -> ActionCategory:
        """Get action category"""
        return self.category
    
    def requires_confirmation(self) -> bool:
        """Check if action requires user confirmation"""
        return self.security_level in [SecurityLevel.CONFIRM, SecurityLevel.AUTH_REQUIRED]
    
    async def validate(self, params: Optional[Dict[str, Any]] = None) -> bool:
        """
        Validate parameters before execution.
        Override for custom validation.
        
        Args:
            params: Parameters to validate
            
        Returns:
            True if valid
        """
        return True