"""
Microphone Input - Wraps existing STT module
"""

import time
from modules.stt.base import STTProvider
from core.io.audio_input import AudioInput, AudioInputResult, InputCapabilities
from utils.logger import get_logger

logger = get_logger('io.microphone_input')

class MicrophoneInput(AudioInput):
    """Microphone input using existing STT provider"""
    
    def __init__(self, stt_provider: STTProvider):
        """
        Initialize with STT provider.
        
        Args:
            stt_provider: Existing STT module (Google, Whisper, etc.)
        """
        self.stt = stt_provider
        logger.info(f"MicrophoneInput initialized with {stt_provider.__class__.__name__}")
    
    def listen(self) -> AudioInputResult:
        """Listen via microphone and transcribe"""
        start_time = time.time()
        
        try:
            # Use existing STT module
            result = self.stt.listen()
            duration_ms = (time.time() - start_time) * 1000
            
            return AudioInputResult(
                text=result.text,
                confidence=result.confidence,
                duration_ms=duration_ms,
                source='microphone'
            )
            
        except Exception as e:
            logger.error(f"Microphone input error: {e}")
            return AudioInputResult(
                text="",
                confidence=0.0,
                duration_ms=(time.time() - start_time) * 1000,
                source='microphone'
            )
    
    def get_capabilities(self) -> InputCapabilities:
        """Get microphone capabilities"""
        return InputCapabilities(
            supports_wake_word=True,
            supports_streaming=False,
            requires_network=True,  # Google STT needs internet
            latency_ms=500,
            input_type='audio'
        )
    
    def is_available(self) -> bool:
        """Check if microphone is available"""
        try:
            import speech_recognition as sr
            # Try to access microphone
            with sr.Microphone() as source:
                pass
            return True
        except Exception as e:
            logger.warning(f"Microphone not available: {e}")
            return False
