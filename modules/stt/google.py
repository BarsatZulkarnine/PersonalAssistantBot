"""
Google Speech-to-Text Implementation
"""

import speech_recognition as sr
from modules.stt.base import STTProvider, STTConfig, STTResult
from utils.logger import get_logger
import time

logger = get_logger('stt.google')

class GoogleSTT(STTProvider):
    """Google Speech Recognition implementation"""
    
    def __init__(self, config: dict):
        # Extract recording config
        recording_config = config.get('recording', {})
        
        stt_config = STTConfig(
            timeout=recording_config.get('timeout', 5.0),
            phrase_time_limit=recording_config.get('phrase_time_limit', 15.0),
            pause_threshold=recording_config.get('pause_threshold', 0.8),
            energy_threshold=recording_config.get('energy_threshold', 300),
            language=config.get('language', 'en-US')
        )
        
        super().__init__(stt_config)
        
        self.recognizer = sr.Recognizer()
        self.recognizer.pause_threshold = self.config.pause_threshold
        self.recognizer.energy_threshold = self.config.energy_threshold
        
        # Dynamic energy adjustment
        if recording_config.get('dynamic_energy', True):
            self.recognizer.dynamic_energy_threshold = True
        
        logger.info(f"Google STT initialized (timeout={self.config.timeout}s, max_duration={self.config.phrase_time_limit}s)")
    
    def listen(self) -> STTResult:
        """Listen and transcribe"""
        self.is_recording = True
        start_time = time.time()
        
        try:
            with sr.Microphone() as source:
                logger.debug(f"Listening (timeout={self.config.timeout}s, max={self.config.phrase_time_limit}s)...")
                
                audio = self.recognizer.listen(
                    source,
                    timeout=self.config.timeout,
                    phrase_time_limit=self.config.phrase_time_limit
                )
                
                duration = time.time() - start_time
                logger.debug(f"Recording complete ({duration:.1f}s)")
                
                # Transcribe
                text = self.recognizer.recognize_google(audio, language=self.config.language)
                
                return STTResult(
                    text=text,
                    confidence=1.0,  # Google doesn't provide confidence
                    language=self.config.language,
                    duration=duration
                )
                
        except sr.WaitTimeoutError:
            logger.debug("Timeout waiting for speech")
            return STTResult(text="", duration=time.time() - start_time)
        
        except sr.UnknownValueError:
            logger.debug("Could not understand audio")
            return STTResult(text="", duration=time.time() - start_time)
        
        except sr.RequestError as e:
            logger.error(f"Speech recognition error: {e}")
            return STTResult(text="", duration=time.time() - start_time)
        
        finally:
            self.is_recording = False
    
    def transcribe_audio(self, audio_data: bytes) -> STTResult:
        """Transcribe audio bytes"""
        try:
            # Convert bytes to AudioData
            audio = sr.AudioData(audio_data, 16000, 2)
            text = self.recognizer.recognize_google(audio, language=self.config.language)
            
            return STTResult(
                text=text,
                confidence=1.0,
                language=self.config.language
            )
            
        except Exception as e:
            logger.error(f"Transcription error: {e}")
            return STTResult(text="")
    
    def adjust_for_ambient_noise(self, duration: float = 1.0):
        """Calibrate for ambient noise"""
        logger.info(f"Adjusting for ambient noise ({duration}s)...")
        
        try:
            with sr.Microphone() as source:
                self.recognizer.adjust_for_ambient_noise(source, duration=duration)
            
            logger.info(f"Energy threshold adjusted to {self.recognizer.energy_threshold}")
            
        except Exception as e:
            logger.error(f"Noise adjustment failed: {e}")