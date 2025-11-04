"""
Wake Word Detection Module - Base Interface

This module handles efficient wake word detection without consuming
unnecessary resources when idle.
"""

from abc import ABC, abstractmethod
from typing import Optional, Callable
from dataclasses import dataclass

@dataclass
class WakeWordConfig:
    """Configuration for wake word detection"""
    wake_word: str
    sensitivity: float = 0.5
    timeout: Optional[float] = None
    low_power_mode: bool = True
    sample_rate: int = 16000

class WakeWordDetector(ABC):
    """
    Base interface for wake word detection.
    
    Key Requirements:
    - Low resource usage when idle
    - Fast detection (< 500ms)
    - High accuracy
    - Easy to swap providers
    """
    
    def __init__(self, config: WakeWordConfig):
        self.config = config
        self.is_listening = False
        self._callback: Optional[Callable] = None
    
    @abstractmethod
    def start(self):
        """
        Start listening for wake word.
        Should be non-blocking and resource efficient.
        """
        pass
    
    @abstractmethod
    def stop(self):
        """Stop listening for wake word"""
        pass
    
    @abstractmethod
    def wait_for_wake_word(self) -> bool:
        """
        Wait for wake word detection (blocking).
        
        Returns:
            True if wake word detected, False if timeout
        """
        pass
    
    def set_callback(self, callback: Callable):
        """Set callback function to call when wake word detected"""
        self._callback = callback
    
    @abstractmethod
    def get_resource_usage(self) -> dict:
        """
        Get current resource usage stats.
        
        Returns:
            dict with cpu_percent, memory_mb, etc.
        """
        pass
    
    def __enter__(self):
        """Context manager support"""
        self.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager cleanup"""
        self.stop()