import speech_recognition as sr
from gtts import gTTS
import tempfile
import pygame
import os
import time

recognizer = sr.Recognizer()

def listen_to_user() -> str:
    with sr.Microphone() as source:
        print("🎧 Listening...")
        audio = recognizer.listen(source, timeout=5, phrase_time_limit=10)
    try:
        return recognizer.recognize_google(audio)
    except sr.UnknownValueError:
        print("❌ Didn’t catch that.")
        return ""
    except sr.RequestError as e:
        print(f"Speech API error: {e}")
        return ""

def speak(text: str):
    # Use temp directory and a unique filename
    temp_dir = tempfile.gettempdir()
    temp_file = os.path.join(temp_dir, f"assistant_speech_{int(time.time()*1000)}.mp3")
    
    # Generate TTS audio
    tts = gTTS(text=text, lang="en")
    tts.save(temp_file)

    # Play using pygame
    pygame.mixer.init()
    pygame.mixer.music.load(temp_file)
    pygame.mixer.music.play()
    while pygame.mixer.music.get_busy():
        pygame.time.Clock().tick(10)
    pygame.mixer.quit()

    # Optional: delete after playing
    try:
        os.remove(temp_file)
    except:
        pass

async def wait_for_hotword():
    import speech_recognition as sr
    recognizer = sr.Recognizer()
    with sr.Microphone() as source:
        print("👂 Waiting for 'Hey Pi'...")
        while True:
            try:
                audio = recognizer.listen(source, timeout=None)
                text = recognizer.recognize_google(audio).lower()
                if "hey pi" in text:
                    print("✅ Hotword detected!")
                    return
            except sr.UnknownValueError:
                continue
