"""
YouTube Music Downloader - SIMPLIFIED & FIXED

No fake streaming - just reliable downloads with proper filename handling
"""

import os
import sys
import re
from pathlib import Path
from typing import Optional
from utils.logger import get_logger

logger = get_logger('music.youtube')

class YouTubeStreamer:
    """
    YouTube music downloader with smart caching.
    
    Requires: pip install yt-dlp
    """
    
    def __init__(self, config: dict):
        self.config = config
        self.cache_dir = Path(config.get('youtube', {}).get('download_dir', 'data/music_cache'))
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Check if yt-dlp is available
        try:
            import yt_dlp
            self.yt_dlp = yt_dlp
            self.available = True
            logger.info("[OK] YouTube downloader initialized")
        except ImportError:
            logger.warning("[WARN] yt-dlp not installed, YouTube disabled")
            print("[WARN] YouTube: Install with: pip install yt-dlp")
            self.available = False
    
    def _sanitize_filename(self, filename: str) -> str:
        """
        Sanitize filename to match yt-dlp's sanitization.
        
        This ensures our cache lookup matches what yt-dlp actually saves.
        """
        # Remove invalid characters
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            filename = filename.replace(char, '')
        
        # Replace unicode chars
        replacements = {
            '\u2012': '-', '\u2013': '-', '\u2014': '-',
            '\u2018': "'", '\u2019': "'", 
            '\u201c': '"', '\u201d': '"',
            '\u2026': '...',
        }
        for old, new in replacements.items():
            filename = filename.replace(old, new)
        
        # Remove multiple spaces
        filename = re.sub(r'\s+', ' ', filename)
        
        # Strip whitespace
        filename = filename.strip()
        
        # Limit length
        if len(filename) > 200:
            filename = filename[:200]
        
        return filename
    
    def _find_in_cache(self, query: str) -> Optional[Path]:
        """
        Search for matching file in cache.
        
        Uses fuzzy matching to handle variations in titles.
        """
        try:
            from difflib import SequenceMatcher
            
            query_lower = query.lower()
            query_words = set(query_lower.split())
            
            best_match = None
            best_score = 0.0
            
            for file in self.cache_dir.glob('*.mp3'):
                filename_lower = file.stem.lower()
                filename_words = set(filename_lower.split())
                
                # Calculate similarity
                string_sim = SequenceMatcher(None, query_lower, filename_lower).ratio()
                
                # Word overlap
                if query_words and filename_words:
                    word_overlap = len(query_words & filename_words) / len(query_words | query_words)
                else:
                    word_overlap = 0.0
                
                score = (string_sim * 0.5) + (word_overlap * 0.5)
                
                if score > best_score:
                    best_score = score
                    best_match = file
            
            # Require at least 60% match
            if best_match and best_score >= 0.6:
                logger.info(f"Cache hit: {best_match.name} (score={best_score:.2f})")
                return best_match
            
            logger.debug(f"No cache match for '{query}' (best score={best_score:.2f})")
            return None
            
        except Exception as e:
            logger.error(f"Cache search error: {e}")
            return None
    
    def search_and_download(self, query: str, max_wait: int = 120) -> Optional[str]:
        """
        Search and download from YouTube.
        
        Args:
            query: Song name or search query
            max_wait: Maximum seconds to wait for download
            
        Returns:
            Path to downloaded file or None
        """
        if not self.available:
            logger.error("YouTube not available")
            return None
        
        try:
            # Ensure query is a string
            if isinstance(query, bytes):
                query = query.decode('utf-8')
            
            # Check cache first
            cached_file = self._find_in_cache(query)
            if cached_file and cached_file.exists():
                print(f"[YOUTUBE] ✓ Found in cache: {cached_file.name}")
                return str(cached_file)
            
            print(f"[YOUTUBE] 🔍 Searching: {query}")
            
            # Set up output template - let yt-dlp sanitize the title
            output_template = str(self.cache_dir / '%(title)s.%(ext)s')
            
            class QuietLogger:
                def debug(self, msg): pass
                def info(self, msg): pass
                def warning(self, msg): pass
                def error(self, msg):
                    logger.error(f"yt-dlp: {msg}")
            
            ydl_opts = {
                'format': 'bestaudio/best',
                'outtmpl': output_template,
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }],
                'quiet': True,
                'no_warnings': True,
                'noplaylist': True,
                'no_color': True,
                'noprogress': False,  # Show progress
                'logger': QuietLogger(),
                'nocheckcertificate': True,
            }
            
            search_query = f"ytsearch1:{query}"
            
            # Get list of files before download
            files_before = set(self.cache_dir.glob('*.mp3'))
            
            print(f"[YOUTUBE] ⬇️  Downloading...")
            
            # Download
            with self.yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(search_query, download=True)
            
            # Find the new file
            files_after = set(self.cache_dir.glob('*.mp3'))
            new_files = files_after - files_before
            
            if new_files:
                downloaded_file = list(new_files)[0]
                print(f"[YOUTUBE] ✓ Downloaded: {downloaded_file.name}")
                logger.info(f"Downloaded: {downloaded_file.name}")
                return str(downloaded_file)
            
            # Fallback: find most recent file
            mp3_files = list(self.cache_dir.glob('*.mp3'))
            if mp3_files:
                most_recent = max(mp3_files, key=lambda p: p.stat().st_mtime)
                
                # Check if it's recent enough (within last minute)
                import time
                if time.time() - most_recent.stat().st_mtime < 60:
                    print(f"[YOUTUBE] ✓ Found recent file: {most_recent.name}")
                    return str(most_recent)
            
            logger.warning("Download succeeded but file not found")
            return None
            
        except Exception as e:
            logger.error(f"Download error: {e}")
            print(f"[YOUTUBE] ✗ Download failed: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return None
    
    def get_stream_and_download(self, query: str):
        """
        Legacy method for compatibility.
        Now just does a simple download.
        """
        # Just download - no fake streaming
        file_path = self.search_and_download(query)
        
        if file_path:
            # Return file path twice (old API expected URL, cache_path)
            return file_path, file_path
        return None, None
    
    def stream_url(self, query: str) -> Optional[str]:
        """Legacy method - downloads and returns path"""
        return self.search_and_download(query)
    
    def clean_cache(self, max_size_mb: int = 500):
        """Clean cache if it exceeds size limit"""
        try:
            total_size = sum(f.stat().st_size for f in self.cache_dir.glob('*') if f.is_file())
            total_size_mb = total_size / (1024 * 1024)
            
            if total_size_mb > max_size_mb:
                logger.info(f"Cleaning cache ({total_size_mb:.1f}MB)")
                
                files = sorted(self.cache_dir.glob('*'), key=lambda f: f.stat().st_mtime)
                
                while total_size_mb > max_size_mb * 0.8 and files:
                    file = files.pop(0)
                    size = file.stat().st_size / (1024 * 1024)
                    file.unlink()
                    total_size_mb -= size
                    logger.info(f"Removed: {file.name}")
                    
        except Exception as e:
            logger.error(f"Cache cleanup error: {e}")
    
    def clear_cache(self):
        """Clear entire cache"""
        try:
            count = 0
            for file in self.cache_dir.glob('*.mp3'):
                file.unlink()
                count += 1
            logger.info(f"Cleared {count} files from cache")
            print(f"[YOUTUBE] Cleared {count} cached songs")
        except Exception as e:
            logger.error(f"Cache clear error: {e}")