"""
Music Player System

Handles local music playback and streaming.
"""

import os
import random
from pathlib import Path
from typing import List, Optional, Dict
from enum import Enum
import pygame
from utils.logger import get_logger
import threading
import time


logger = get_logger('music.player')

class PlaybackState(Enum):
    STOPPED = "stopped"
    PLAYING = "playing"
    PAUSED = "paused"

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
        self.source = "local"  # local or youtube
    
    def __str__(self):
        return self.name
    
    def __repr__(self):
        return f"Song({self.name})"

class MusicPlayer:
    """
    Music player with local and streaming support.
    
    Features:
    - Play local music files
    - Queue management
    - Shuffle and repeat
    - Volume control
    - Playlist support
    """
    
    def __init__(self, config: dict):
        self.config = config
        
        # Initialize pygame mixer
        if not pygame.mixer.get_init():
            pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
        
        # State
        self.state = PlaybackState.STOPPED
        self.current_song: Optional[Song] = None
        self.queue: List[Song] = []
        self.history: List[Song] = []
        self.volume = config.get('playback', {}).get('volume', 0.7)
        self.shuffle_enabled = config.get('playback', {}).get('shuffle', False)
        self.repeat_mode = RepeatMode(config.get('playback', {}).get('repeat', 'none'))
        
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
        
        pygame.mixer.music.set_volume(self.volume)
        
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
            # Expand user path
            dir_path = Path(directory).expanduser()
            
            if not dir_path.exists():
                logger.warning(f"Directory not found: {directory}")
                continue
            
            # Scan for music files
            for ext in formats:
                for file_path in dir_path.rglob(f"*.{ext}"):
                    song = Song(str(file_path))
                    self.library.append(song)
        
        logger.info(f"Found {len(self.library)} songs")

    def _monitor_playback(self):
        """Monitor the song and update state when it finishes."""
        while pygame.mixer.music.get_busy():
            time.sleep(0.5)
        self.state = PlaybackState.STOPPED
    
    
    def play(self, query: Optional[str] = None) -> str:
        """
        Play music.

        Args:
            query: Song name, artist, or None for random

        Returns:
            Status message
        """
        # --- Find song ---
        if query:
            song = self._find_song(query)

            # If not found locally and YouTube is enabled
            if not song and self.youtube and self.youtube.available:
                print(f"[MUSIC] Not found locally, searching YouTube...")
                file_path = self.youtube.search_and_download(query)
                if file_path:
                    song = Song(file_path)
                    song.source = "youtube"
                else:
                    return f"Could not find '{query}' locally or on YouTube"
            elif not song:
                return f"Could not find '{query}' in library"

            self.current_song = song
        else:
            # Play from queue or random from library
            if self.queue:
                self.current_song = self.queue.pop(0)
            elif self.library:
                self.current_song = random.choice(self.library)
            else:
                return "No songs available"

    # --- Playback thread ---
        def _playback_thread(song_path: str):
            try:
                pygame.mixer.music.load(song_path)
                pygame.mixer.music.set_volume(self.volume)
                pygame.mixer.music.play()
                self.state = PlaybackState.PLAYING

                print(f"[DEBUG] Playback thread started: {song_path}")
                while pygame.mixer.music.get_busy():
                    time.sleep(0.1)  # keep thread alive while song is playing

                self.state = PlaybackState.STOPPED
                print(f"[DEBUG] Playback finished: {song_path}")
            except Exception as e:
                logger.error(f"Playback error in thread: {e}")
                self.state = PlaybackState.STOPPED

        # Start playback in a daemon thread
        threading.Thread(target=_playback_thread, args=(self.current_song.path,), daemon=True).start()

        source_label = "YouTube" if self.current_song.source == "youtube" else "Library"
        logger.info(f"Playing ({source_label}): {self.current_song.name}")
        print(f"[MUSIC] Playing from {source_label}: {self.current_song.name}")

        return f"Now playing {self.current_song.name}"

    
    def pause(self) -> str:
        """Pause playback"""
        if self.state == PlaybackState.PLAYING:
            pygame.mixer.music.pause()
            self.state = PlaybackState.PAUSED
            logger.info("Paused")
            return "Music paused"
        return "Nothing is playing"
    
    def resume(self) -> str:
        """Resume playback"""
        if self.state == PlaybackState.PAUSED:
            pygame.mixer.music.unpause()
            self.state = PlaybackState.PLAYING
            logger.info("Resumed")
            return "Music resumed"
        return "Nothing to resume"
    
    def stop(self) -> str:
        """Stop playback"""
        pygame.mixer.music.stop()
        self.state = PlaybackState.STOPPED
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
            # Play random from library
            return self.play()
        else:
            return "No more songs"
    
    def previous(self) -> str:
        """Go to previous song"""
        if self.history:
            song = self.history.pop()
            self.current_song = song
            
            pygame.mixer.music.load(song.path)
            pygame.mixer.music.play()
            self.state = PlaybackState.PLAYING
            
            return f"Playing previous: {song.name}"
        return "No previous song"
    
    def set_volume(self, volume: float) -> str:
        """Set volume (0.0 to 1.0)"""
        self.volume = max(0.0, min(1.0, volume))
        pygame.mixer.music.set_volume(self.volume)
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
            'library_size': len(self.library)
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
        return self.state == PlaybackState.PLAYING and pygame.mixer.music.get_busy()