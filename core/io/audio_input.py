"""
Audio Input Abstraction

Abstract interface for all input sources (microphone, keyboard, websocket, etc.)
"""

from abc import ABC, abstractmethod
from typing import Optional
from dataclasses import dataclass

@dataclass
class InputCapabilities:
    """Describes what an input source can do"""
    supports_wake_word: bool = False
    supports_streaming: bool = False
    requires_network: bool = False
    latency_ms: int = 0
    input_type: str = "unknown"  # 'audio', 'text', 'network'

@dataclass
class AudioInputResult:
    """Result from input source"""
    text: str
    confidence: float = 1.0
    duration_ms: float = 0.0
    source: str = "unknown"
    
    def is_empty(self) -> bool:
        """Check if no input received"""
        return not self.text or self.text.strip() == ""

class AudioInput(ABC):
    """
    Abstract interface for audio/text input.
    
    Can be implemented by:
    - Microphone (via STT)
    - Keyboard (text input)
    - WebSocket (network audio/text)
    - File (pre-recorded audio)
    - Robot sensors
    """
    
    @abstractmethod
    def listen(self) -> AudioInputResult:
        """
        Listen for input and return text.
        
        Returns:
            AudioInputResult with transcribed/typed text
        """
        pass
    
    @abstractmethod
    def get_capabilities(self) -> InputCapabilities:
        """
        Get capabilities of this input source.
        
        Returns:
            InputCapabilities describing what this source can do
        """
        pass
    
    def is_available(self) -> bool:
        """
        Check if input source is available.
        
        Returns:
            True if ready to use
        """
        return True
