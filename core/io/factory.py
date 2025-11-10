"""
I/O Factory - Creates appropriate I/O implementations based on config
"""

from typing import Optional, Tuple
from core.io.audio_input import AudioInput
from core.io.audio_output import AudioOutput
from core.io.input.microphone_input import MicrophoneInput
from core.io.input.keyboard_input import KeyboardInput
from core.io.output.speaker_output import SpeakerOutput
from core.io.output.console_output import ConsoleOutput
from utils.logger import get_logger

logger = get_logger('io.factory')

class IOFactory:
    """
    Factory for creating I/O implementations.
    
    Handles auto-detection and fallback when hardware unavailable.
    """
    
    @staticmethod
    def create_input(
        mode: str,
        stt_provider = None,
        fallback: bool = True
    ) -> AudioInput:
        """
        Create audio input based on mode.
        
        Args:
            mode: 'auto', 'microphone', 'keyboard'
            stt_provider: STT provider for microphone
            fallback: Whether to fallback to keyboard if mic unavailable
            
        Returns:
            AudioInput implementation
        """
        logger.info(f"Creating input: mode={mode}, fallback={fallback}")
        
        if mode == 'auto':
            # Try microphone first
            if stt_provider:
                mic_input = MicrophoneInput(stt_provider)
                if mic_input.is_available():
                    logger.info("Auto-selected: MicrophoneInput")
                    return mic_input
            
            # Fallback to keyboard
            if fallback:
                logger.info("Microphone unavailable, falling back to keyboard")
                return KeyboardInput()
            else:
                raise RuntimeError("Microphone unavailable and fallback disabled")
        
        elif mode == 'microphone':
            if not stt_provider:
                raise ValueError("STT provider required for microphone mode")
            mic_input = MicrophoneInput(stt_provider)
            if not mic_input.is_available():
                if fallback:
                    logger.warning("Microphone unavailable, using keyboard")
                    return KeyboardInput()
                else:
                    raise RuntimeError("Microphone not available")
            return mic_input
        
        elif mode == 'keyboard':
            return KeyboardInput()
        
        else:
            raise ValueError(f"Unknown input mode: {mode}")
    
    @staticmethod
    def create_output(
        mode: str,
        tts_provider = None,
        fallback: bool = True
    ) -> AudioOutput:
        """
        Create audio output based on mode.
        
        Args:
            mode: 'auto', 'speaker', 'console'
            tts_provider: TTS provider for speaker
            fallback: Whether to fallback to console if speaker unavailable
            
        Returns:
            AudioOutput implementation
        """
        logger.info(f"Creating output: mode={mode}, fallback={fallback}")
        
        if mode == 'auto':
            # Try speaker first
            if tts_provider:
                speaker_output = SpeakerOutput(tts_provider)
                if speaker_output.is_available():
                    logger.info("Auto-selected: SpeakerOutput")
                    return speaker_output
            
            # Fallback to console
            if fallback:
                logger.info("Speaker unavailable, falling back to console")
                return ConsoleOutput()
            else:
                raise RuntimeError("Speaker unavailable and fallback disabled")
        
        elif mode == 'speaker':
            if not tts_provider:
                raise ValueError("TTS provider required for speaker mode")
            speaker_output = SpeakerOutput(tts_provider)
            if not speaker_output.is_available():
                if fallback:
                    logger.warning("Speaker unavailable, using console")
                    return ConsoleOutput()
                else:
                    raise RuntimeError("Speaker not available")
            return speaker_output
        
        elif mode == 'console':
            return ConsoleOutput()
        
        else:
            raise ValueError(f"Unknown output mode: {mode}")
    
    @staticmethod
    def create_io_pair(
        input_mode: str,
        output_mode: str,
        stt_provider = None,
        tts_provider = None,
        fallback: bool = True
    ) -> Tuple[AudioInput, AudioOutput]:
        """
        Create matching input/output pair.
        
        Args:
            input_mode: Input mode
            output_mode: Output mode
            stt_provider: STT provider
            tts_provider: TTS provider
            fallback: Enable fallback
            
        Returns:
            (AudioInput, AudioOutput) tuple
        """
        audio_input = IOFactory.create_input(input_mode, stt_provider, fallback)
        audio_output = IOFactory.create_output(output_mode, tts_provider, fallback)
        
        logger.info(
            f"Created I/O pair: "
            f"input={audio_input.__class__.__name__}, "
            f"output={audio_output.__class__.__name__}"
        )
        
        return audio_input, audio_output