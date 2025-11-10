"""
Console Output - Simple text output
"""

from core.io.audio_output import AudioOutput, OutputCapabilities
from utils.logger import get_logger

logger = get_logger('io.console_output')

class ConsoleOutput(AudioOutput):
    """Console text output (no hardware needed)"""
    
    def __init__(self, prefix: str = "Assistant: "):
        """
        Initialize console output.
        
        Args:
            prefix: Prefix to show before output
        """
        self.prefix = prefix
        logger.info("ConsoleOutput initialized")
    
    def output(self, text: str) -> bool:
        """Print text to console"""
        try:
            print(f"\n{self.prefix}{text}\n")
            return True
            
        except Exception as e:
            logger.error(f"Console output error: {e}")
            return False
    
    def get_capabilities(self) -> OutputCapabilities:
        """Get console capabilities"""
        return OutputCapabilities(
            supports_audio=False,
            supports_streaming=False,
            requires_network=False,
            output_type='text'
        )
    
    def is_available(self) -> bool:
        """Console always available"""
        return True
