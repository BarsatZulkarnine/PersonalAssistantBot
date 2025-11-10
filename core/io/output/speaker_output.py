"""
Speaker Output - Wraps existing TTS module
"""

from modules.tts.base import TTSProvider
from core.io.audio_output import AudioOutput, OutputCapabilities
from utils.logger import get_logger

logger = get_logger('io.speaker_output')

class SpeakerOutput(AudioOutput):
    """Speaker output using existing TTS provider"""
    
    def __init__(self, tts_provider: TTSProvider):
        """
        Initialize with TTS provider.
        
        Args:
            tts_provider: Existing TTS module (gTTS, OpenAI, etc.)
        """
        self.tts = tts_provider
        logger.info(f"SpeakerOutput initialized with {tts_provider.__class__.__name__}")
    
    def output(self, text: str) -> bool:
        """Speak text via TTS"""
        try:
            # Use streaming if enabled
            if self.tts.config.streaming_enabled:
                self.tts.stream_speak(text)
            else:
                self.tts.speak(text)
            return True
            
        except Exception as e:
            logger.error(f"Speaker output error: {e}")
            return False
    
    def get_capabilities(self) -> OutputCapabilities:
        """Get speaker capabilities"""
        return OutputCapabilities(
            supports_audio=True,
            supports_streaming=self.tts.config.streaming_enabled,
            requires_network=False,  # gTTS/OpenAI generate locally
            output_type='audio'
        )
    
    def is_available(self) -> bool:
        """Check if speaker is available"""
        try:
            import pygame
            if not pygame.mixer.get_init():
                pygame.mixer.init()
            return True
        except Exception as e:
            logger.warning(f"Speaker not available: {e}")
            return False
