"""
Text-to-Speech Module - Base Interface

Handles converting text to speech with customizable voices and settings.
"""

from abc import ABC, abstractmethod
from typing import Optional, List
from dataclasses import dataclass
from enum import Enum

class VoiceGender(Enum):
    MALE = "male"
    FEMALE = "female"
    NEUTRAL = "neutral"

@dataclass
class VoiceProfile:
    """Voice configuration"""
    name: Optional[str] = None
    gender: VoiceGender = VoiceGender.NEUTRAL
    language: str = "en"
    speed: float = 1.0
    pitch: float = 1.0
    volume: float = 1.0

@dataclass
class TTSConfig:
    """Configuration for text-to-speech"""
    voice: VoiceProfile
    streaming_enabled: bool = True
    chunk_size: str = "sentence"  # sentence, word, character

class TTSProvider(ABC):
    """
    Base interface for Text-to-Speech providers.
    
    Key Features:
    - Customizable voices
    - Streaming support
    - Provider-agnostic
    """
    
    def __init__(self, config: TTSConfig):
        self.config = config
        self.is_speaking = False
        self.available_voices: List[str] = []
    
    @abstractmethod
    def speak(self, text: str, voice: Optional[VoiceProfile] = None) -> bool:
        """
        Speak text (blocking).
        
        Args:
            text: Text to speak
            voice: Optional voice override
            
        Returns:
            True if successful
        """
        pass
    
    @abstractmethod
    def speak_async(self, text: str, voice: Optional[VoiceProfile] = None):
        """
        Speak text (non-blocking).
        
        Args:
            text: Text to speak
            voice: Optional voice override
        """
        pass
    
    @abstractmethod
    def stream_speak(self, text: str, voice: Optional[VoiceProfile] = None) -> bool:
        """
        Speak text with streaming (sentence-by-sentence).
        
        Args:
            text: Text to speak
            voice: Optional voice override
            
        Returns:
            True if successful
        """
        pass
    
    @abstractmethod
    def stop(self):
        """Stop current speech"""
        pass
    
    @abstractmethod
    def list_voices(self) -> List[str]:
        """
        List available voices for this provider.
        
        Returns:
            List of voice names/IDs
        """
        pass
    
    @abstractmethod
    def set_voice(self, voice_name: str):
        """
        Set the voice by name.
        
        Args:
            voice_name: Name or ID of voice
        """
        pass
    
    def set_speed(self, speed: float):
        """Set speech speed (1.0 = normal)"""
        self.config.voice.speed = speed
    
    def set_pitch(self, pitch: float):
        """Set speech pitch (1.0 = normal)"""
        self.config.voice.pitch = pitch
    
    def set_volume(self, volume: float):
        """Set volume (0.0 to 1.0)"""
        self.config.voice.volume = max(0.0, min(1.0, volume))