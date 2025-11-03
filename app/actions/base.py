from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from enum import IntEnum

class SecurityLevel(IntEnum):
    """Security levels for actions"""
    SAFE = 0           # No confirmation needed
    CONFIRM = 1        # Requires user confirmation
    AUTH_REQUIRED = 2  # Requires authentication

@dataclass
class ActionResult:
    """Result of an action execution"""
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None
    requires_confirmation: bool = False
    confirmation_prompt: Optional[str] = None

class Action(ABC):
    """
    Base class for all actions.
    Each action plugin must inherit from this class.
    """
    
    def __init__(self):
        self.name: str = self.__class__.__name__
        self.intents: List[str] = []
        self.security_level: SecurityLevel = SecurityLevel.SAFE
        self.enabled: bool = True
        self.description: str = ""
    
    @abstractmethod
    def get_intents(self) -> List[str]:
        """
        Return list of intent patterns this action handles.
        Examples: ["turn on light", "turn off light"]
        """
        pass
    
    @abstractmethod
    async def execute(self, prompt: str, params: Optional[Dict[str, Any]] = None) -> ActionResult:
        """
        Execute the action.
        
        Args:
            prompt: Original user prompt
            params: Extracted parameters from intent classifier
            
        Returns:
            ActionResult with success status and message
        """
        pass
    
    def get_security_level(self) -> SecurityLevel:
        """Get security level for this action"""
        return self.security_level
    
    def requires_confirmation(self) -> bool:
        """Check if action requires confirmation"""
        return self.security_level >= SecurityLevel.CONFIRM
    
    def is_enabled(self) -> bool:
        """Check if action is enabled"""
        return self.enabled
    
    def get_description(self) -> str:
        """Get action description"""
        return self.description
    
    def matches_intent(self, prompt: str) -> bool:
        """
        Check if prompt matches any of this action's intents.
        Override for custom matching logic.
        """
        prompt_lower = prompt.lower()
        for intent in self.get_intents():
            if intent.lower() in prompt_lower:
                return True
        return False
    
    async def validate(self, params: Optional[Dict[str, Any]] = None) -> bool:
        """
        Validate parameters before execution.
        Override for custom validation.
        """
        return True
    
    async def get_confirmation_prompt(self, params: Optional[Dict[str, Any]] = None) -> str:
        """
        Generate confirmation prompt for user.
        Override for custom confirmation messages.
        """
        return f"Are you sure you want to execute {self.name}?"

class ActionError(Exception):
    """Custom exception for action errors"""
    def __init__(self, message: str, action_name: str = None):
        self.message = message
        self.action_name = action_name
        super().__init__(self.message)