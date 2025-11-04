"""
Speech-to-Text Module - Base Interface

Handles recording and transcribing user speech with configurable duration.
"""

from abc import ABC, abstractmethod
from typing import Optional
from dataclasses import dataclass

@dataclass
class STTConfig:
    """Configuration for speech-to-text"""
    timeout: float = 5.0              # Max wait for speech start
    phrase_time_limit: float = 15.0   # Max recording duration
    pause_threshold: float = 0.8      # Silence to end recording
    energy_threshold: int = 300       # Voice detection threshold
    language: str = "en-US"

@dataclass
class STTResult:
    """Result of speech recognition"""
    text: str
    confidence: float = 1.0
    language: Optional[str] = None
    duration: float = 0.0
    
    def is_empty(self) -> bool:
        """Check if no text recognized"""
        return not self.text or self.text.strip() == ""

class STTProvider(ABC):
    """
    Base interface for Speech-to-Text providers.
    
    Key Features:
    - Configurable recording duration
    - Adjustable silence detection
    - Provider-agnostic interface
    """
    
    def __init__(self, config: STTConfig):
        self.config = config
        self.is_recording = False
    
    @abstractmethod
    def listen(self) -> STTResult:
        """
        Listen to microphone and transcribe speech.
        
        Behavior:
        - Waits up to `timeout` seconds for speech to start
        - Records for up to `phrase_time_limit` seconds
        - Stops recording after `pause_threshold` seconds of silence
        
        Returns:
            STTResult with transcribed text
        """
        pass
    
    @abstractmethod
    def transcribe_audio(self, audio_data: bytes) -> STTResult:
        """
        Transcribe audio data directly.
        
        Args:
            audio_data: Raw audio bytes
            
        Returns:
            STTResult with transcribed text
        """
        pass
    
    @abstractmethod
    def adjust_for_ambient_noise(self, duration: float = 1.0):
        """
        Calibrate for ambient noise.
        Should be called before listening in noisy environment.
        
        Args:
            duration: Seconds to sample ambient noise
        """
        pass
    
    def set_energy_threshold(self, threshold: int):
        """Manually set voice detection threshold"""
        self.config.energy_threshold = threshold
    
    def set_recording_duration(self, duration: float):
        """Set maximum recording duration"""
        self.config.phrase_time_limit = duration
    
    def set_pause_threshold(self, threshold: float):
        """Set silence duration before stopping"""
        self.config.pause_threshold = threshold