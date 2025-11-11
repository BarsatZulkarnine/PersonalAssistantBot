"""
Music Player System - FIXED VERSION

Improvements:
1. Fuzzy matching for typos/word order
2. Better YouTube integration
3. Proper cache handling
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

# Use rapidfuzz for better fuzzy matching
try:
    from rapidfuzz import fuzz, process
    RAPIDFUZZ_AVAILABLE = True
except ImportError:
    from difflib import SequenceMatcher
    RAPIDFUZZ_AVAILABLE = False

logger = get_logger('music.player')

class PlaybackState(Enum):
    STOPPED = "stopped"
    PLAYING = "playing"
    PAUSED = "paused"
    AUTO_PAUSED = "auto_paused"

class RepeatMode(Enum):
    NONE = "none"
    ONE = "one"
    ALL = "all"

class Song:
    """Represents a song"""
    def __init__(self, path: str, source: str = "local"):
        self.path = path
        self.filename = os.path.basename(path)
        self.name = os.path.splitext(self.filename)[0]
        self.directory = os.path.dirname(path)
        self.source = source
    
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
    """Music player with fuzzy matching and YouTube integration"""
    
    def __init__(self, config: dict):
        self.config = config
        
        # Initialize pygame mixer
        if not pygame.mixer.get_init():
            pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=2048)
        
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
        
        # Auto-pause settings
        self.auto_pause_enabled = config.get('playback', {}).get('auto_pause', True)
        self.was_playing_before_pause = False
        
        # Threading
        self.playback_thread: Optional[threading.Thread] = None
        self.stop_flag = threading.Event()
        
        # YouTube streamer - MUST initialize BEFORE library scan
        self.youtube = None
        try:
            if config.get('youtube', {}).get('enabled', True):
                from modules.music.youtube import YouTubeStreamer
                self.youtube = YouTubeStreamer(config)
                if self.youtube.available:
                    logger.info("YouTube integration enabled")
        except Exception as e:
            logger.warning(f"YouTube unavailable: {e}")
            self.youtube = None
        
        # Music library (scans both local + YouTube cache)
        self.library: List[Song] = []
        self._scan_library()
        
        # Verify youtube attribute exists
        assert hasattr(self, 'youtube'), "YouTube attribute not set!"
        
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
                    song = Song(str(file_path), source="local")
                    self.library.append(song)
        
        # Also scan YouTube cache
        if self.youtube and hasattr(self.youtube, 'cache_dir'):
            cache_dir = self.youtube.cache_dir
            if cache_dir.exists():
                for file_path in cache_dir.glob("*.mp3"):
                    song = Song(str(file_path), source="youtube_cache")
                    self.library.append(song)
        
        logger.info(f"Found {len(self.library)} songs")
    
    def _similarity(self, a: str, b: str) -> float:
        """Calculate similarity between two strings (0.0 to 1.0)"""
        if RAPIDFUZZ_AVAILABLE:
            # Use token_sort_ratio for better word order handling
            return fuzz.token_sort_ratio(a, b) / 100.0
        else:
            return SequenceMatcher(None, a.lower(), b.lower()).ratio()
    
    def _normalize_query(self, query: str) -> str:
        """Normalize query for better matching"""
        # Remove common words and punctuation
        common_words = {'the', 'a', 'an', 'by', 'ft', 'feat', 'featuring', '-'}
        words = query.lower().split()
        words = [w.strip('.,!?;:()[]{}') for w in words if w.lower() not in common_words]
        return ' '.join(words)
    
    def _find_song(self, query: str, threshold: float = 0.65) -> Optional[Song]:
        """
        Find song using advanced fuzzy matching with rapidfuzz.
        
        Tries multiple strategies:
        1. Exact match (case-insensitive)
        2. Fuzzy match with typo tolerance
        3. Partial word match
        
        Args:
            query: Search query (can have typos, different word order)
            threshold: Minimum similarity score (0.0 to 1.0)
            
        Returns:
            Best matching song or None
        """
        if not self.library:
            return None
        
        query_lower = query.lower().strip()
        
        # Strategy 1: Exact match (case-insensitive)
        for song in self.library:
            if query_lower == song.name.lower():
                logger.info(f"✓ Exact match: '{song.name}'")
                return song
        
        # Strategy 2: Use rapidfuzz if available (best for typos)
        if RAPIDFUZZ_AVAILABLE:
            # Create list of song names with original casing for display
            song_names = [song.name for song in self.library]
            
            # Try multiple scorers for best results
            scorers = [
                (fuzz.token_sort_ratio, "token_sort"),  # Best for word order + typos
                (fuzz.partial_ratio, "partial"),         # Good for partial matches
                (fuzz.ratio, "ratio")                    # Standard fuzzy match
            ]
            
            best_overall = None
            best_overall_score = 0
            
            for scorer, scorer_name in scorers:
                result = process.extractOne(
                    query_lower,
                    song_names,
                    scorer=scorer,
                    score_cutoff=threshold * 100
                )
                
                if result:
                    matched_name, score, index = result
                    
                    if score > best_overall_score:
                        best_overall = (self.library[index], score / 100.0, scorer_name)
                        best_overall_score = score
            
            if best_overall:
                song, score, scorer_name = best_overall
                logger.info(f"✓ Fuzzy match: '{song.name}' (score={score:.2f}, method={scorer_name})")
                return song
            
            logger.warning(f"✗ No match for '{query}' (tried fuzzy matching)")
            return None
        
        # Fallback: Manual fuzzy matching if rapidfuzz not available
        return self._find_song_manual(query_lower, threshold)
    
    def _find_song_manual(self, query_lower: str, threshold: float) -> Optional[Song]:
        """Manual fuzzy matching fallback (when rapidfuzz not available)"""
        query_norm = self._normalize_query(query_lower)
        query_words = set(query_norm.split())
        
        best_match = None
        best_score = 0.0
        
        logger.debug(f"Manual search for: '{query_lower}' (normalized: '{query_norm}')")
        
        for song in self.library:
            song_norm = self._normalize_query(song.name.lower())
            song_words = set(song_norm.split())
            
            # Calculate multiple similarity metrics
            
            # 1. Overall string similarity
            overall_sim = self._similarity(query_norm, song_norm)
            
            # 2. Word overlap (Jaccard similarity)
            if query_words and song_words:
                word_overlap = len(query_words & song_words) / len(query_words | song_words)
            else:
                word_overlap = 0.0
            
            # 3. Check if ALL query words are in song (better for short queries)
            all_query_words_in_song = all(qw in song_norm for qw in query_words) if query_words else False
            all_words_bonus = 0.3 if all_query_words_in_song else 0.0
            
            # 4. Substring match bonus
            substring_bonus = 0.2 if query_norm in song_norm or song_norm in query_norm else 0.0
            
            # Combined score (weighted average)
            score = (overall_sim * 0.3) + (word_overlap * 0.3) + all_words_bonus + substring_bonus
            
            # Debug logging for close matches
            if score > 0.4:
                logger.debug(f"  '{song.name}' -> score={score:.2f}")
            
            if score > best_score:
                best_score = score
                best_match = song
        
        if best_match and best_score >= threshold:
            logger.info(f"✓ Manual match: '{best_match.name}' (score={best_score:.2f})")
            return best_match
        
        logger.warning(f"✗ No manual match for '{query_lower}' (best score={best_score:.2f})")
        return None
    
    def _playback_worker(self, song: Song):
        """Background worker for music playback"""
        try:
            logger.info(f"Loading song: {song.name}")
            
            # Check if file exists and is ready
            if not os.path.exists(song.path):
                logger.error(f"File not found: {song.path}")
                self.state = PlaybackState.STOPPED
                return
            
            # Wait a bit if file is very small (might still be downloading)
            file_size = os.path.getsize(song.path)
            if file_size < 10000:  # Less than 10KB
                logger.info("File seems incomplete, waiting...")
                time.sleep(2)
            
            # Load as Sound object
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
            # First try local/cache with fuzzy matching
            song = self._find_song(query, threshold=0.6)
            
            # Try YouTube if not found locally
            if not song and use_youtube and self.youtube and self.youtube.available:
                print(f"[MUSIC] Not found locally, searching YouTube...")
                
                # Download from YouTube (blocking to ensure file is ready)
                cache_path = self.youtube.search_and_download(query)
                
                if cache_path and os.path.exists(cache_path):
                    song = Song(cache_path, source="youtube")
                    # Add to library for future fuzzy matching
                    self.library.append(song)
                    logger.info(f"Downloaded from YouTube: {song.name}")
                else:
                    return f"Could not find or download '{query}'"
            elif not song:
                return f"Could not find '{query}' (tried fuzzy matching)"
            
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
        
        source_label = {
            "local": "Library",
            "youtube": "YouTube",
            "youtube_cache": "Cache"
        }.get(self.current_song.source, "Unknown")
        
        logger.info(f"Started playback ({source_label}): {self.current_song.name}")
        
        return f"Now playing {self.current_song.name}"
    
    # AUTO-PAUSE METHODS
    def auto_pause(self) -> bool:
        """Auto-pause music (called when wake word detected)"""
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
        """Auto-resume music (called after assistant response)"""
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
    
    def rescan_library(self):
        """Rescan library (useful after YouTube downloads)"""
        self.library.clear()
        self._scan_library()
        logger.info(f"Rescanned library: {len(self.library)} songs")
    
    def is_playing(self) -> bool:
        """Check if music is currently playing"""
        return self.state == PlaybackState.PLAYING and self.music_channel.get_busy()