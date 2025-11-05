"""
OpenAI Text-to-Speech Implementation
"""

import os
import tempfile
import time
from pathlib import Path
from typing import List, Optional
import pygame
from openai import OpenAI

from modules.tts.base import TTSProvider, TTSConfig, VoiceProfile
from utils.logger import get_logger
from dotenv import load_dotenv

logger = get_logger('tts.openai')


class OpenAITTS(TTSProvider):
    """OpenAI TTS implementation (gpt-4o-mini-tts)"""

    def __init__(self, config: dict):
        # Ensure environment variables are loaded
        load_dotenv()
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

        # Get OpenAI settings
        openai_config = config.get('openai_tts', {})
        self.model = openai_config.get('model', 'gpt-4o-mini-tts')
        self.voice_name = openai_config.get('voice', 'alloy')

        # Get API key from config or environment
        api_key = openai_config.get('api_key') or os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OpenAI API key not found in config or environment variables")

        self.client = OpenAI(api_key=api_key)

        # Initialize pygame mixer
        if not pygame.mixer.get_init():
            pygame.mixer.init()

        logger.info(f"OpenAI TTS initialized (model={self.model}, voice={self.voice_name})")

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
            logger.error(f"OpenAI TTS speak error: {e}")
            self.is_speaking = False
            return False

    def speak_async(self, text: str, voice: Optional[VoiceProfile] = None):
        """Speak asynchronously"""
        import threading
        thread = threading.Thread(target=self.speak, args=(text, voice))
        thread.daemon = True
        thread.start()

    def stream_speak(self, text: str, voice: Optional[VoiceProfile] = None) -> bool:
        """Speak text sentence-by-sentence"""
        try:
            self.is_speaking = True

            import re
            sentences = re.split(r'(?<=[.!?])\s+', text)
            sentences = [s.strip() for s in sentences if s.strip()]

            if not sentences:
                return False

            logger.debug(f"Streaming {len(sentences)} sentences (OpenAI)")
            print(f"🔊 OpenAI TTS: Streaming {len(sentences)} sentences")

            for i, sentence in enumerate(sentences):
                print(f"   📢 Sentence {i+1}/{len(sentences)}: {sentence[:50]}...")
                temp_file = self._generate_audio(sentence, voice or self.config.voice)
                if temp_file:
                    self._play_audio(temp_file)
                    self._cleanup_file(temp_file)

            self.is_speaking = False
            return True

        except Exception as e:
            logger.error(f"OpenAI stream speak error: {e}")
            self.is_speaking = False
            return False

    def _generate_audio(self, text: str, voice: VoiceProfile) -> Optional[str]:
        """Generate audio from OpenAI TTS"""
        try:
            temp_file = self.temp_dir / f"tts_{int(time.time()*1000)}.mp3"

            response = self.client.audio.speech.create(
                model=self.model,
                voice=self.voice_name,
                input=text
            )

            with open(temp_file, "wb") as f:
                f.write(response.read())

            return str(temp_file)

        except Exception as e:
            logger.error(f"OpenAI TTS audio generation error: {e}")
            return None

    def _play_audio(self, file_path: str):
        """Play audio file"""
        try:
            pygame.mixer.music.load(file_path)
            pygame.mixer.music.set_volume(self.config.voice.volume)
            pygame.mixer.music.play()

            max_wait = 60
            start = time.time()

            while pygame.mixer.music.get_busy():
                if time.time() - start > max_wait:
                    logger.warning("Playback timeout, stopping")
                    pygame.mixer.music.stop()
                    break
                pygame.time.Clock().tick(10)

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
        """List available OpenAI voices"""
        return ["alloy", "verse", "shimmer", "coral", "sage"]

    def set_voice(self, voice_name: str):
        """Set OpenAI voice"""
        self.voice_name = voice_name
        logger.info(f"Voice set to: {voice_name}")

    def __del__(self):
        """Cleanup temp files"""
        try:
            if self.temp_dir.exists():
                for file in self.temp_dir.glob("*.mp3"):
                    try:
                        file.unlink()
                    except:
                        pass
        except:
            pass
