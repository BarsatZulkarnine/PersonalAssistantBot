"""
Music Player System - WITH AUTO-PAUSE FOR WAKE WORD

Automatically pauses music when "hey pi" is detected and resumes after response
"""

import os
import random
import threading
import time
from pathlib import Path
from typing import List, Optional, Dict
from enum import Enum
import pygame
from utils.logger import get_logger

logger = get_logger('music.player')

class PlaybackState(Enum):
    STOPPED = "stopped"
    PLAYING = "playing"
    PAUSED = "paused"
    AUTO_PAUSED = "auto_paused"  # NEW: Auto-paused for voice interaction

class RepeatMode(Enum):
    NONE = "none"
    ONE = "one"
    ALL = "all"

class Song:
    """Represents a song"""
    def __init__(self, path: str):
        self.path = path
        self.filename = os.path.basename(path)
        self.name = os.path.splitext(self.filename)[0]
        self.directory = os.path.dirname(path)
        self.source = "local"
    
    def __str__(self):
        return self.name
    
    def __repr__(self):
        return f"Song({self.name})"
    
    def get_safe_name(self) -> str:
        """Get ASCII-safe name for logging"""
        safe = self.name
        replacements = {
            '\u2012': '-', '\u2013': '-', '\u2014': '--',
            '\u2018': "'", '\u2019': "'", '\u201c': '"', '\u201d': '"'
        }
        for old, new in replacements.items():
            safe = safe.replace(old, new)
        return safe

class MusicPlayer:
    """
    Music player with background playback and auto-pause support.
    
    Features:
    - Auto-pauses when wake word detected
    - Auto-resumes after assistant response
    - Won't be interrupted by TTS
    """
    
    def __init__(self, config: dict):
        self.config = config
        
        # Initialize pygame mixer with more channels
        if not pygame.mixer.get_init():
            pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=2048)
        
        # Reserve channel 0 for music (TTS will use music channel)
        pygame.mixer.set_num_channels(8)
        self.music_channel = pygame.mixer.Channel(0)
        
        # State
        self.state = PlaybackState.STOPPED
        self.current_song: Optional[Song] = None
        self.current_sound: Optional[pygame.mixer.Sound] = None
        self.queue: List[Song] = []
        self.history: List[Song] = []
        self.volume = config.get('playback', {}).get('volume', 0.7)
        self.shuffle_enabled = config.get('playback', {}).get('shuffle', False)
        self.repeat_mode = RepeatMode(config.get('playback', {}).get('repeat', 'none'))
        
        # NEW: Auto-pause settings
        self.auto_pause_enabled = config.get('playback', {}).get('auto_pause', True)
        self.was_playing_before_pause = False
        
        # Threading
        self.playback_thread: Optional[threading.Thread] = None
        self.stop_flag = threading.Event()
        
        # Music library
        self.library: List[Song] = []
        self._scan_library()
        
        # YouTube streamer
        self.youtube = None
        if config.get('youtube', {}).get('enabled', True):
            try:
                from modules.music.youtube import YouTubeStreamer
                self.youtube = YouTubeStreamer(config)
            except Exception as e:
                logger.warning(f"YouTube unavailable: {e}")
        
        logger.info(f"[OK] Music player initialized ({len(self.library)} songs)")
        print(f"[OK] Music player: {len(self.library)} songs in library")
        if self.youtube and self.youtube.available:
            print("[OK] Music player: YouTube streaming enabled")
    
    def _scan_library(self):
        """Scan directories for music files"""
        directories = self.config.get('music', {}).get('directories', [])
        formats = self.config.get('music', {}).get('formats', ['mp3', 'wav'])
        
        logger.info(f"Scanning {len(directories)} directories...")
        
        for directory in directories:
            dir_path = Path(directory).expanduser()
            
            if not dir_path.exists():
                logger.warning(f"Directory not found: {directory}")
                continue
            
            for ext in formats:
                for file_path in dir_path.rglob(f"*.{ext}"):
                    song = Song(str(file_path))
                    self.library.append(song)
        
        logger.info(f"Found {len(self.library)} songs")
    
    def _playback_worker(self, song: Song):
        """Background worker for music playback"""
        try:
            logger.info(f"Loading song: {song.name}")
            
            # Load as Sound object (not music)
            sound = pygame.mixer.Sound(song.path)
            self.current_sound = sound
            sound.set_volume(self.volume)
            
            # Play on dedicated channel
            self.music_channel.play(sound)
            self.state = PlaybackState.PLAYING
            
            logger.info(f"Playing in background: {song.name}")
            print(f"[MUSIC] ▶️  Now playing: {song.name}")
            
            # Wait for playback to finish
            while self.music_channel.get_busy() and not self.stop_flag.is_set():
                time.sleep(0.1)
            
            if not self.stop_flag.is_set():
                self.state = PlaybackState.STOPPED
                logger.info(f"Finished playing: {song.name}")
                
                # Auto-play next if queue exists
                if self.queue:
                    self.play()
            
        except Exception as e:
            logger.error(f"Playback error: {e}")
            self.state = PlaybackState.STOPPED
    
    def play(self, query: Optional[str] = None, use_youtube: bool = True) -> str:
        """
        Play music in background (non-blocking).
        
        Args:
            query: Song name, artist, or None for random
            use_youtube: Whether to search YouTube if not found locally
            
        Returns:
            Status message
        """
        # Stop current playback
        if self.state == PlaybackState.PLAYING:
            self.stop()
        
        # Find song
        if query:
            song = self._find_song(query)
            
            # Try YouTube if not found locally
            if not song and use_youtube and self.youtube and self.youtube.available:
                print(f"[MUSIC] Not found locally, searching YouTube...")
                
                # Use stream + background download
                stream_url, cache_path = self.youtube.get_stream_and_download(query)
                
                if stream_url:
                    # Check if it's a cached file or stream URL
                    if stream_url.startswith('http'):
                        print(f"[MUSIC] 🌐 Streaming from YouTube...")
                        # For now, we need the file downloaded
                        # TODO: Support direct URL streaming
                        print(f"[MUSIC] ⏳ Waiting for download...")
                        
                        # Wait a bit for download to complete
                        max_wait = 60  # 60 seconds max
                        waited = 0
                        while not os.path.exists(cache_path) and waited < max_wait:
                            time.sleep(1)
                            waited += 1
                        
                        if os.path.exists(cache_path):
                            song = Song(cache_path)
                            song.source = "youtube"
                        else:
                            return f"Download timed out for '{query}'"
                    else:
                        # Already cached
                        song = Song(stream_url)
                        song.source = "youtube"
                else:
                    return f"Could not find '{query}' locally or on YouTube"
            elif not song:
                return f"Could not find '{query}' in library"
            
            self.current_song = song
        else:
            # Play from queue or random
            if self.queue:
                self.current_song = self.queue.pop(0)
            elif self.library:
                self.current_song = random.choice(self.library)
            else:
                return "No songs available"
        
        # Start playback in background thread
        self.stop_flag.clear()
        self.playback_thread = threading.Thread(
            target=self._playback_worker,
            args=(self.current_song,),
            daemon=True
        )
        self.playback_thread.start()
        
        source_label = "YouTube" if self.current_song.source == "youtube" else "Library"
        logger.info(f"Started playback ({source_label}): {self.current_song.name}")
        
        return f"Now playing {self.current_song.name}"
    
    # NEW: Auto-pause methods for wake word detection
    def auto_pause(self) -> bool:
        """
        Auto-pause music (called when wake word detected).
        
        Returns:
            True if music was paused, False if nothing was playing
        """
        if not self.auto_pause_enabled:
            return False
        
        if self.state == PlaybackState.PLAYING:
            self.music_channel.pause()
            self.state = PlaybackState.AUTO_PAUSED
            self.was_playing_before_pause = True
            logger.info("Auto-paused for voice interaction")
            return True
        
        self.was_playing_before_pause = False
        return False
    
    def auto_resume(self) -> bool:
        """
        Auto-resume music (called after assistant response).
        
        Returns:
            True if music was resumed, False if nothing to resume
        """
        if not self.auto_pause_enabled:
            return False
        
        if self.state == PlaybackState.AUTO_PAUSED and self.was_playing_before_pause:
            self.music_channel.unpause()
            self.state = PlaybackState.PLAYING
            self.was_playing_before_pause = False
            logger.info("Auto-resumed after voice interaction")
            return True
        
        self.was_playing_before_pause = False
        return False
    
    def pause(self) -> str:
        """Pause playback (manual)"""
        if self.state == PlaybackState.PLAYING:
            self.music_channel.pause()
            self.state = PlaybackState.PAUSED
            logger.info("Paused")
            return "Music paused"
        return "Nothing is playing"
    
    def resume(self) -> str:
        """Resume playback (manual)"""
        if self.state in [PlaybackState.PAUSED, PlaybackState.AUTO_PAUSED]:
            self.music_channel.unpause()
            self.state = PlaybackState.PLAYING
            self.was_playing_before_pause = False
            logger.info("Resumed")
            return "Music resumed"
        return "Nothing to resume"
    
    def stop(self) -> str:
        """Stop playback"""
        self.stop_flag.set()
        self.music_channel.stop()
        self.state = PlaybackState.STOPPED
        self.was_playing_before_pause = False
        
        if self.current_song:
            logger.info(f"Stopped: {self.current_song.name}")
            return "Music stopped"
        return "Already stopped"
    
    def next(self) -> str:
        """Skip to next song"""
        if self.current_song:
            self.history.append(self.current_song)
        
        if self.queue:
            return self.play()
        elif self.library:
            return self.play()
        else:
            return "No more songs"
    
    def previous(self) -> str:
        """Go to previous song"""
        if self.history:
            song = self.history.pop()
            self.current_song = song
            
            # Use background playback
            self.stop_flag.clear()
            self.playback_thread = threading.Thread(
                target=self._playback_worker,
                args=(song,),
                daemon=True
            )
            self.playback_thread.start()
            
            return f"Playing previous: {song.name}"
        return "No previous song"
    
    def set_volume(self, volume: float) -> str:
        """Set volume (0.0 to 1.0)"""
        self.volume = max(0.0, min(1.0, volume))
        if self.current_sound:
            self.current_sound.set_volume(self.volume)
        logger.info(f"Volume set to {self.volume:.0%}")
        return f"Volume set to {self.volume:.0%}"
    
    def volume_up(self, step: float = 0.1) -> str:
        """Increase volume"""
        return self.set_volume(self.volume + step)
    
    def volume_down(self, step: float = 0.1) -> str:
        """Decrease volume"""
        return self.set_volume(self.volume - step)
    
    def toggle_shuffle(self) -> str:
        """Toggle shuffle mode"""
        self.shuffle_enabled = not self.shuffle_enabled
        logger.info(f"Shuffle: {self.shuffle_enabled}")
        return f"Shuffle {'enabled' if self.shuffle_enabled else 'disabled'}"
    
    def toggle_auto_pause(self) -> str:
        """Toggle auto-pause feature"""
        self.auto_pause_enabled = not self.auto_pause_enabled
        logger.info(f"Auto-pause: {self.auto_pause_enabled}")
        return f"Auto-pause {'enabled' if self.auto_pause_enabled else 'disabled'}"
    
    def add_to_queue(self, query: str) -> str:
        """Add song to queue"""
        song = self._find_song(query)
        if song:
            self.queue.append(song)
            logger.info(f"Added to queue: {song.name}")
            return f"Added {song.name} to queue"
        return f"Could not find '{query}'"
    
    def clear_queue(self) -> str:
        """Clear the queue"""
        count = len(self.queue)
        self.queue.clear()
        return f"Cleared {count} songs from queue"
    
    def get_status(self) -> Dict:
        """Get player status"""
        return {
            'state': self.state.value,
            'current_song': str(self.current_song) if self.current_song else None,
            'volume': self.volume,
            'shuffle': self.shuffle_enabled,
            'repeat': self.repeat_mode.value,
            'queue_length': len(self.queue),
            'library_size': len(self.library),
            'auto_pause': self.auto_pause_enabled
        }
    
    def _find_song(self, query: str) -> Optional[Song]:
        """Find song by name (fuzzy match)"""
        query_lower = query.lower()
        
        # Exact match
        for song in self.library:
            if query_lower == song.name.lower():
                return song
        
        # Partial match
        for song in self.library:
            if query_lower in song.name.lower():
                return song
        
        return None
    
    def is_playing(self) -> bool:
        """Check if music is currently playing"""
        return self.state == PlaybackState.PLAYING and self.music_channel.get_busy()