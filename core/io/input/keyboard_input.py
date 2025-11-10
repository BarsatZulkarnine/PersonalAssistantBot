"""
Keyboard Input - Simple text input
"""

import time
from core.io.audio_input import AudioInput, AudioInputResult, InputCapabilities
from utils.logger import get_logger

logger = get_logger('io.keyboard_input')

class KeyboardInput(AudioInput):
    """Keyboard text input (no hardware needed)"""
    
    def __init__(self, prompt: str = "> "):
        """
        Initialize keyboard input.
        
        Args:
            prompt: Prompt to show user
        """
        self.prompt = prompt
        logger.info("KeyboardInput initialized")
    
    def listen(self) -> AudioInputResult:
        """Get text from keyboard"""
        start_time = time.time()
        
        try:
            text = input(self.prompt)
            duration_ms = (time.time() - start_time) * 1000
            
            return AudioInputResult(
                text=text,
                confidence=1.0,
                duration_ms=duration_ms,
                source='keyboard'
            )
            
        except EOFError:
            # Ctrl+D pressed
            return AudioInputResult(
                text="",
                confidence=0.0,
                duration_ms=(time.time() - start_time) * 1000,
                source='keyboard'
            )
        except Exception as e:
            logger.error(f"Keyboard input error: {e}")
            return AudioInputResult(
                text="",
                confidence=0.0,
                duration_ms=(time.time() - start_time) * 1000,
                source='keyboard'
            )
    
    def get_capabilities(self) -> InputCapabilities:
        """Get keyboard capabilities"""
        return InputCapabilities(
            supports_wake_word=False,
            supports_streaming=False,
            requires_network=False,
            latency_ms=0,
            input_type='text'
        )
    
    def is_available(self) -> bool:
        """Keyboard always available"""
        return True
