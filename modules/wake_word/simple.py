"""
Simple Wake Word Detection

Uses Google Speech Recognition for wake word detection.
Not as efficient as Porcupine/Vosk but works out of the box.
"""

import speech_recognition as sr
from modules.wake_word.base import WakeWordDetector, WakeWordConfig
from utils.logger import get_logger
import time

logger = get_logger('wake_word.simple')

class SimpleWakeWord(WakeWordDetector):
    """
    Simple wake word detector using Google STT.
    
    Pros: Works immediately, no extra setup
    Cons: Requires internet, uses more resources
    """
    
    def __init__(self, config: dict):
        # Build config
        wake_config = WakeWordConfig(
            wake_word=config.get('wake_word', 'hey pi'),
            sensitivity=config.get('sensitivity', 0.5),
            timeout=config.get('timeout'),
            low_power_mode=config.get('low_power_mode', True),
            sample_rate=config.get('sample_rate', 16000)
        )
        
        super().__init__(wake_config)
        
        self.recognizer = sr.Recognizer()
        self.recognizer.energy_threshold = 300
        self.recognizer.dynamic_energy_threshold = True
        self.recognizer.pause_threshold = 0.8
        
        logger.info(f"Simple wake word initialized (word='{self.config.wake_word}')")
        print(f"🎤 Wake word detector ready (say '{self.config.wake_word}')")
    
    def start(self):
        """Start listening"""
        self.is_listening = True
        logger.debug("Wake word detector started")
    
    def stop(self):
        """Stop listening"""
        self.is_listening = False
        logger.debug("Wake word detector stopped")
    
    def wait_for_wake_word(self) -> bool:
        """
        Wait for wake word detection (blocking).
        
        Returns:
            True if detected, False if timeout
        """
        logger.debug(f"Listening for '{self.config.wake_word}'...")
        print(f"👂 Listening for '{self.config.wake_word}'...")
        
        with sr.Microphone() as source:
            # Quick ambient noise adjustment
            self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
            
            while self.is_listening:
                try:
                    # Listen for short phrases (wake word should be short)
                    audio = self.recognizer.listen(
                        source,
                        timeout=None,  # Wait indefinitely
                        phrase_time_limit=3  # Max 3 seconds per phrase
                    )
                    
                    # Recognize
                    text = self.recognizer.recognize_google(audio).lower()
                    logger.debug(f"Heard: {text}")
                    
                    # Check for wake word (fuzzy match)
                    wake_words = [
                        self.config.wake_word.lower(),
                        self.config.wake_word.replace(" ", "").lower(),
                        # Common mishearings
                        "hey pie", "hay pi", "hey pee", "hey p"
                    ]
                    
                    if any(wake in text for wake in wake_words):
                        logger.info(f"Wake word detected: '{text}'")
                        print(f"Wake word detected!")
                        return True
                    
                except sr.WaitTimeoutError:
                    continue
                except sr.UnknownValueError:
                    continue
                except sr.RequestError as e:
                    logger.error(f"Speech recognition error: {e}")
                    time.sleep(1)
                    continue
                except Exception as e:
                    logger.error(f"Wake word error: {e}")
                    time.sleep(1)
                    continue
        
        return False
    
    def get_resource_usage(self) -> dict:
        """Get resource usage (basic info)"""
        return {
            'cpu_percent': 0,  # Would need psutil
            'memory_mb': 0,
            'active': self.is_listening
        }