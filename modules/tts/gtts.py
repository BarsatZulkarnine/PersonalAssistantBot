"""
Google Text-to-Speech Implementation
"""

import os
import tempfile
import time
from pathlib import Path
from gtts import gTTS as GoogleTTS
import pygame
from typing import List, Optional
from modules.tts.base import TTSProvider, TTSConfig, VoiceProfile
from utils.logger import get_logger

logger = get_logger('tts.gtts')

class GTTS(TTSProvider):
    """Google TTS implementation with streaming support"""
    
    def __init__(self, config: dict):
        # Build TTSConfig from dict
        voice_config = config.get('voice', {})
        voice = VoiceProfile(
            language=config.get('language', 'en'),
            speed=config.get('speed', 1.0),
            pitch=config.get('pitch', 1.0),
            volume=config.get('volume', 1.0)
        )
        
        streaming_config = config.get('streaming', {})
        tts_config = TTSConfig(
            voice=voice,
            streaming_enabled=streaming_config.get('enabled', True),
            chunk_size=streaming_config.get('chunk_size', 'sentence')
        )
        
        super().__init__(tts_config)
        
        self.temp_dir = Path(tempfile.gettempdir()) / "assistant_tts"
        self.temp_dir.mkdir(exist_ok=True)
        
        # gTTS specific settings
        self.tld = config.get('gtts', {}).get('tld', 'com')
        self.slow = config.get('gtts', {}).get('slow', False)
        
        # Initialize pygame
        if not pygame.mixer.get_init():
            pygame.mixer.init()
        
        logger.info(f"gTTS initialized (language={self.config.voice.language}, streaming={self.config.streaming_enabled})")
    
    def speak(self, text: str, voice: Optional[VoiceProfile] = None) -> bool:
        """Speak text (blocking)"""
        try:
            self.is_speaking = True
            
            voice_to_use = voice or self.config.voice
            temp_file = self._generate_audio(text, voice_to_use)
            
            if not temp_file:
                return False
            
            self._play_audio(temp_file)
            self._cleanup_file(temp_file)
            
            self.is_speaking = False
            return True
            
        except Exception as e:
            logger.error(f"gTTS speak error: {e}")
            self.is_speaking = False
            return False
    
    def speak_async(self, text: str, voice: Optional[VoiceProfile] = None):
        """Speak asynchronously"""
        import threading
        thread = threading.Thread(target=self.speak, args=(text, voice))
        thread.daemon = True
        thread.start()
    
    def stream_speak(self, text: str, voice: Optional[VoiceProfile] = None) -> bool:
        """Speak sentence-by-sentence"""
        try:
            self.is_speaking = True
            
            # Split into sentences
            import re
            sentences = re.split(r'(?<=[.!?])\s+', text)
            sentences = [s.strip() for s in sentences if s.strip()]
            
            if not sentences:
                return False
            
            logger.debug(f"Streaming {len(sentences)} sentences")
            print(f"🔊 GTTS: Streaming {len(sentences)} sentences")
            
            for i, sentence in enumerate(sentences):
                print(f"   📢 Sentence {i+1}/{len(sentences)}: {sentence[:50]}...")
                
                temp_file = self._generate_audio(sentence, voice or self.config.voice)
                if temp_file:
                    self._play_audio(temp_file)
                    self._cleanup_file(temp_file)
            
            self.is_speaking = False
            return True
            
        except Exception as e:
            logger.error(f"Stream speak error: {e}")
            self.is_speaking = False
            return False
    
    def _generate_audio(self, text: str, voice: VoiceProfile) -> Optional[str]:
        """Generate TTS audio file"""
        try:
            temp_file = self.temp_dir / f"tts_{int(time.time()*1000)}.mp3"
            
            tts = GoogleTTS(
                text=text,
                lang=voice.language,
                slow=self.slow,
                tld=self.tld
            )
            tts.save(str(temp_file))
            
            return str(temp_file)
            
        except Exception as e:
            logger.error(f"Audio generation error: {e}")
            return None
    
    def _play_audio(self, file_path: str):
        """Play audio file with timeout protection"""
        try:
            pygame.mixer.music.load(file_path)
            pygame.mixer.music.set_volume(self.config.voice.volume)
            pygame.mixer.music.play()
            
            # Wait with timeout
            max_wait = 60  # 60 seconds max
            start = time.time()
            
            while pygame.mixer.music.get_busy():
                if time.time() - start > max_wait:
                    logger.warning("Playback timeout, stopping")
                    pygame.mixer.music.stop()
                    break
                pygame.time.Clock().tick(10)
            
            # Unload to free resources
            pygame.mixer.music.unload()
                
        except Exception as e:
            logger.error(f"Audio playback error: {e}")
    
    def _cleanup_file(self, file_path: str):
        """Delete temporary file"""
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
        except Exception as e:
            logger.debug(f"Cleanup warning: {e}")
    
    def stop(self):
        """Stop playback"""
        try:
            if pygame.mixer.music.get_busy():
                pygame.mixer.music.stop()
                pygame.mixer.music.unload()
        except Exception as e:
            logger.error(f"Stop error: {e}")
    
    def list_voices(self) -> List[str]:
        """List available languages (gTTS uses language codes)"""
        # Common languages supported by gTTS
        return [
            'en', 'es', 'fr', 'de', 'it', 'pt', 'ru', 'ja', 'ko', 'zh',
            'ar', 'hi', 'nl', 'pl', 'tr', 'sv', 'da', 'fi', 'no'
        ]
    
    def set_voice(self, voice_name: str):
        """Set language (voice_name is language code)"""
        self.config.voice.language = voice_name
        logger.info(f"Voice set to: {voice_name}")
    
    def __del__(self):
        """Cleanup on destruction"""
        try:
            if self.temp_dir.exists():
                for file in self.temp_dir.glob("*.mp3"):
                    try:
                        file.unlink()
                    except:
                        pass
        except:
            pass