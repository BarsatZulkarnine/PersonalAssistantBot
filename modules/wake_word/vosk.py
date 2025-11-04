# Module: modules/wake_word/vosk.py
from modules.wake_word.base import WakeWordDetector, WakeWordConfig
import vosk
import sounddevice as sd

class VoskWakeWord(WakeWordDetector):
    """
    Vosk-based wake word detection.
    """
    def __init__(self, config: WakeWordConfig):
        super().__init__(config)
        self.model = vosk.Model(config.vosk['model_path'])
        self.sensitivity = config.sensitivity
        self.sample_rate = config.sample_rate
        self.stream = None

    def start(self):
        self.is_listening = True
        self.stream = sd.InputStream(samplerate=self.sample_rate, channels=1, callback=self._callback_wrapper)
        self.stream.start()

    def stop(self):
        self.is_listening = False
        if self.stream:
            self.stream.stop()
            self.stream.close()
            self.stream = None

    def _callback_wrapper(self, indata, frames, time, status):
        if not self.is_listening:
            return
        # simple detection logic
        # TODO: add Vosk wake word detection here

    def wait_for_wake_word(self) -> bool:
        # blocking loop waiting for wake word
        return True  # placeholder

    def get_resource_usage(self) -> dict:
        return {"cpu_percent": 0, "memory_mb": 0}
