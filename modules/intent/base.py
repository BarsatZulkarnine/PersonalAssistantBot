"""
Intent Detection Module - Base Interface

Simple intent classification: AI, Web, or Action
"""

from abc import ABC, abstractmethod
from typing import Optional
from dataclasses import dataclass
from enum import Enum

class IntentType(Enum):
    """Simple intent categories"""
    AI = "AI"          # General conversation/questions
    WEB = "Web"        # Web search/current information
    ACTION = "Action"  # Execute an action

@dataclass
class IntentResult:
    """Result of intent detection"""
    intent_type: IntentType
    confidence: float
    original_text: str
    reasoning: Optional[str] = None
    
    def is_confident(self, threshold: float = 0.7) -> bool:
        """Check if confidence exceeds threshold"""
        return self.confidence >= threshold

class IntentDetector(ABC):
    """
    Base interface for intent detection.
    
    Returns one of three categories:
    - AI: General conversation, questions, chat
    - Web: Web search, current info, facts
    - Action: Execute system/home/productivity action
    """
    
    def __init__(self, config: dict):
        self.config = config
    
    @abstractmethod
    async def detect(self, text: str) -> IntentResult:
        """
        Detect intent from user text.
        
        Args:
            text: User's spoken/typed input
            
        Returns:
            IntentResult with classification
        """
        pass
    
    def get_intent_examples(self) -> dict:
        """
        Get example phrases for each intent type.
        Useful for debugging and understanding classifications.
        
        Returns:
            Dict mapping IntentType to example phrases
        """
        return {
            IntentType.AI: [
                "Tell me a joke",
                "What do you think about AI?",
                "How are you today?",
                "Explain quantum physics"
            ],
            IntentType.WEB: [
                "What's the weather today?",
                "Who won the game last night?",
                "Search for Python tutorials",
                "What's the population of Tokyo?"
            ],
            IntentType.ACTION: [
                "Turn on the lights",
                "Set volume to 50",
                "Open Chrome",
                "Send an email to John"
            ]
        }