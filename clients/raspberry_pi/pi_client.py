#!/usr/bin/env python3
"""
Raspberry Pi Voice Client - COMPLETE IMPLEMENTATION

Features:
- Voice input/output
- Music playback (YouTube + local streams)
- Session management
- Auto-reconnect
- Error handling

Installation:
    sudo apt-get update
    sudo apt-get install python3-pip portaudio19-dev mpv
    pip3 install requests SpeechRecognition gTTS pygame yt-dlp
"""

import requests
import speech_recognition as sr
from gtts import gTTS
import pygame
import os
import time
import sys
import subprocess
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime
import uuid
import json

class PiVoiceClient:
    """Raspberry Pi voice client with full music support"""
    
    def __init__(
        self,
        server_url: str = "http://192.168.1.100:8000",
        device_name: str = "raspberry_pi",
        user_id: str = "user1"
    ):
        self.server_url = server_url
        self.device_name = device_name
        self.user_id = user_id
        self.session_id = self._generate_session_id()
        
        # Audio setup
        self.recognizer = sr.Recognizer()
        self.recognizer.energy_threshold = 300
        self.recognizer.dynamic_energy_threshold = True
        self.recognizer.pause_threshold = 0.8
        
        pygame.mixer.init()
        
        # Music player state
        self.music_process: Optional[subprocess.Popen] = None
        self.current_song = None
        
        # Connection status
        self.connected = False
        
        print(f"╔════════════════════════════════════════╗")
        print(f"║   Raspberry Pi Voice Client            ║")
        print(f"╚════════════════════════════════════════╝")
        print(f"Server: {self.server_url}")
        print(f"Device: {self.device_name}")
        print(f"Session: {self.session_id[:30]}...")
        print()
        
        self._check_connection()
    
    def _generate_session_id(self) -> str:
        """Generate unique session ID"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        short_uuid = str(uuid.uuid4())[:8]
        return f"{self.user_id}_{self.device_name}_{timestamp}_{short_uuid}"
    
    def _check_connection(self):
        """Check server connection"""
        try:
            response = requests.get(f"{self.server_url}/health", timeout=5)
            if response.status_code == 200:
                self.connected = True
                print("✅ Connected to server")
                return True
        except Exception as e:
            print(f"❌ Cannot connect to server: {e}")
            print(f"   Make sure server is running at {self.server_url}")
            self.connected = False
            return False
    
    # ============================================
    # AUDIO INPUT/OUTPUT
    # ============================================
    
    def listen(self, timeout: int = 5) -> str:
        """Capture audio from microphone"""
        print("[🎤] Listening...")
        
        try:
            with sr.Microphone() as source:
                # Quick ambient noise adjustment
                self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
                
                # Listen
                audio = self.recognizer.listen(
                    source,
                    timeout=timeout,
                    phrase_time_limit=15
                )
            
            # Transcribe
            text = self.recognizer.recognize_google(audio)
            print(f"[👂] Heard: {text}")
            return text
        
        except sr.WaitTimeoutError:
            return ""
        except sr.UnknownValueError:
            return ""
        except Exception as e:
            print(f"[❌] Listen error: {e}")
            return ""
    
    def speak(self, text: str):
        """Speak text via TTS"""
        print(f"[🔊] Speaking: {text[:50]}...")
        
        try:
            # Stop music if playing
            was_playing = self._pause_music()
            
            # Generate TTS
            tts = gTTS(text=text, lang='en')
            temp_file = "/tmp/pi_tts.mp3"
            tts.save(temp_file)
            
            # Play
            pygame.mixer.music.load(temp_file)
            pygame.mixer.music.play()
            
            while pygame.mixer.music.get_busy():
                pygame.time.Clock().tick(10)
            
            # Cleanup
            try:
                os.remove(temp_file)
            except:
                pass
            
            # Resume music if it was playing
            if was_playing:
                self._resume_music()
        
        except Exception as e:
            print(f"[❌] Speak error: {e}")
    
    # ============================================
    # SERVER COMMUNICATION
    # ============================================
    
    def chat(self, message: str) -> Dict[str, Any]:
        """Send message to server"""
        if not self.connected:
            self._check_connection()
        
        if not self.connected:
            return {
                "response": "Sorry, I can't reach the server.",
                "error": True
            }
        
        try:
            response = requests.post(
                f"{self.server_url}/api/chat",
                json={
                    "message": message,
                    "session_id": self.session_id,
                    "user_id": self.user_id,
                    "client_type": "raspberry_pi"  # Important!
                },
                timeout=30
            )
            
            response.raise_for_status()
            data = response.json()
            
            return {
                "response": data["response"],
                "action_data": data.get("action_data"),
                "intent": data.get("intent"),
                "error": False
            }
        
        except requests.exceptions.Timeout:
            return {
                "response": "Sorry, the request timed out.",
                "error": True
            }
        except requests.exceptions.ConnectionError:
            self.connected = False
            return {
                "response": "Sorry, I lost connection to the server.",
                "error": True
            }
        except Exception as e:
            print(f"[❌] Server error: {e}")
            return {
                "response": "Sorry, something went wrong.",
                "error": True
            }
    
    # ============================================
    # MUSIC PLAYBACK
    # ============================================
    
    def handle_music_action(self, action_data: Dict[str, Any]):
        """Handle music action from server"""
        if not action_data:
            return
        
        action = action_data.get('action')
        
        if action == 'play_music':
            music_info = action_data.get('music')
            self._play_music(music_info)
        
        elif action == 'pause_music':
            self._pause_music()
        
        elif action == 'resume_music':
            self._resume_music()
        
        elif action == 'stop_music':
            self._stop_music()
        
        elif action == 'next_song':
            self._stop_music()
            print("[🎵] Skipped to next song")
        
        elif action == 'previous_song':
            self._stop_music()
            print("[🎵] Playing previous song")
    
    def _play_music(self, music_info: Dict[str, Any]):
        """Play music on Pi"""
        if not music_info:
            return
        
        music_type = music_info.get('type')
        name = music_info.get('name', 'Unknown')
        
        print(f"[🎵] Playing: {name}")
        self.current_song = name
        
        # Stop current playback
        self._stop_music()
        
        try:
            if music_type == 'youtube':
                # Stream YouTube
                video_id = music_info.get('video_id')
                url = f"https://www.youtube.com/watch?v={video_id}"
                
                print(f"[🎵] Streaming from YouTube...")
                
                # Use mpv for YouTube (no video)
                self.music_process = subprocess.Popen(
                    ['mpv', '--no-video', '--really-quiet', url],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
            
            elif music_type == 'local':
                # Stream from server
                stream_url = music_info.get('stream_url')
                
                if stream_url.startswith('/'):
                    # Relative URL, prepend server
                    stream_url = f"{self.server_url}{stream_url}"
                
                print(f"[🎵] Streaming from server...")
                
                # Use mpv for streaming
                self.music_process = subprocess.Popen(
                    ['mpv', '--really-quiet', stream_url],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
            
            print(f"[✅] Now playing: {name}")
        
        except FileNotFoundError:
            print("[❌] mpv not installed. Install with: sudo apt-get install mpv")
        except Exception as e:
            print(f"[❌] Music playback error: {e}")
    
    def _pause_music(self) -> bool:
        """Pause music, return True if was playing"""
        if self.music_process and self.music_process.poll() is None:
            # Music is playing
            try:
                # Send SIGSTOP (pause)
                self.music_process.send_signal(19)  # SIGSTOP
                print("[⏸️] Music paused")
                return True
            except:
                pass
        return False
    
    def _resume_music(self):
        """Resume music"""
        if self.music_process and self.music_process.poll() is None:
            try:
                # Send SIGCONT (resume)
                self.music_process.send_signal(18)  # SIGCONT
                print("[▶️] Music resumed")
            except:
                pass
    
    def _stop_music(self):
        """Stop music"""
        if self.music_process:
            try:
                self.music_process.terminate()
                self.music_process.wait(timeout=2)
            except:
                try:
                    self.music_process.kill()
                except:
                    pass
            self.music_process = None
            self.current_song = None
    
    # ============================================
    # MAIN LOOP
    # ============================================
    
    def run(self):
        """Main voice assistant loop"""
        print("\n[🚀] Voice assistant started!")
        print("[INFO] Say 'hey pi' to activate\n")
        
        # Initial connection check
        if not self.connected:
            print("[WAIT] Waiting for server connection...")
            while not self._check_connection():
                time.sleep(5)
            print("[OK] Connected!\n")
        
        wake_words = ["hey pi", "hey pie", "hay pi"]
        
        while True:
            try:
                # Listen for wake word
                user_input = self.listen(timeout=None)  # Infinite wait
                
                if not user_input:
                    continue
                
                # Check for wake word
                if not any(wake in user_input.lower() for wake in wake_words):
                    continue
                
                print("[✅] Wake word detected!")
                
                # Acknowledge
                self.speak("Yes?")
                
                # Listen for command
                command = self.listen(timeout=5)
                
                if not command:
                    self.speak("I didn't hear anything.")
                    continue
                
                print(f"[💬] Command: {command}")
                
                # Send to server
                result = self.chat(command)
                
                # Handle response
                if result.get('error'):
                    self.speak(result['response'])
                    continue
                
                # Handle action data (e.g., music)
                action_data = result.get('action_data')
                if action_data:
                    self.handle_music_action(action_data)
                
                # Speak response
                response = result['response']
                self.speak(response)
            
            except KeyboardInterrupt:
                print("\n\n[👋] Shutting down...")
                self._stop_music()
                break
            
            except Exception as e:
                print(f"[❌] Error: {e}")
                time.sleep(1)
    
    def run_test_mode(self):
        """Test mode without wake word (for debugging)"""
        print("\n[🧪] TEST MODE - No wake word required\n")
        
        while True:
            try:
                command = input("You: ").strip()
                
                if not command:
                    continue
                
                if command.lower() in ['exit', 'quit']:
                    break
                
                # Send to server
                result = self.chat(command)
                
                # Handle action data
                action_data = result.get('action_data')
                if action_data:
                    self.handle_music_action(action_data)
                
                # Print response
                print(f"Assistant: {result['response']}\n")
            
            except KeyboardInterrupt:
                print("\n[👋] Exiting test mode...")
                self._stop_music()
                break


# ============================================
# MAIN
# ============================================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Raspberry Pi Voice Client")
    parser.add_argument('--server', default="http://192.168.1.100:8000", help="Server URL")
    parser.add_argument('--test', action='store_true', help="Run in test mode (no wake word)")
    args = parser.parse_args()
    
    client = PiVoiceClient(server_url=args.server)
    
    if args.test:
        client.run_test_mode()
    else:
        client.run()