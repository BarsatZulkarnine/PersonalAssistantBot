"""
Audio Output Abstraction

Abstract interface for all output sinks (speaker, console, websocket, etc.)
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass

@dataclass
class OutputCapabilities:
    """Describes what an output sink can do"""
    supports_audio: bool = False
    supports_streaming: bool = False
    requires_network: bool = False
    output_type: str = "unknown"  # 'audio', 'text', 'network'

class AudioOutput(ABC):
    """
    Abstract interface for audio/text output.
    
    Can be implemented by:
    - Speaker (via TTS)
    - Console (text print)
    - WebSocket (network audio/text)
    - File (save to file)
    - Robot actuators
    """
    
    @abstractmethod
    def output(self, text: str) -> bool:
        """
        Output text (speak or display).
        
        Args:
            text: Text to output
            
        Returns:
            True if successful
        """
        pass
    
    @abstractmethod
    def get_capabilities(self) -> OutputCapabilities:
        """
        Get capabilities of this output sink.
        
        Returns:
            OutputCapabilities describing what this sink can do
        """
        pass
    
    def is_available(self) -> bool:
        """
        Check if output sink is available.
        
        Returns:
            True if ready to use
        """
        return True
