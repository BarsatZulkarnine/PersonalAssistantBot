"""
YouTube Music Streamer - WINDOWS CONSOLE FIX

Key fix: Redirect yt-dlp output to avoid Windows console encoding errors
"""

import os
import sys
from pathlib import Path
from typing import Optional
from utils.logger import get_logger

logger = get_logger('music.youtube')

class YouTubeStreamer:
    """
    YouTube music streaming using yt-dlp.
    
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
            logger.info("[OK] YouTube streamer initialized")
        except ImportError:
            logger.warning("[WARN] yt-dlp not installed, YouTube disabled")
            print("[WARN] YouTube: Install with: pip install yt-dlp")
            self.available = False
    
    def search_and_download(self, query: str) -> Optional[str]:
        """
        Search YouTube and download audio.
        
        Args:
            query: Song name or search query
            
        Returns:
            Path to downloaded file or None
        """
        if not self.available:
            logger.error("YouTube not available")
            return None
        
        try:
            print(f"[YOUTUBE] Searching for: {query}")
            
            # Ensure query is a string
            if isinstance(query, bytes):
                query = query.decode('utf-8')
            
            # CRITICAL FIX: Create a custom logger that redirects yt-dlp output
            # This prevents Windows console encoding errors
            class QuietLogger:
                def debug(self, msg):
                    pass
                def info(self, msg):
                    pass
                def warning(self, msg):
                    pass
                def error(self, msg):
                    logger.error(f"yt-dlp: {msg}")
            
            # Download options with NOPROGRESS to avoid console issues
            ydl_opts = {
                'format': 'bestaudio/best',
                'outtmpl': str(self.cache_dir / '%(title)s.%(ext)s'),
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }],
                'quiet': True,
                'no_warnings': True,
                'noplaylist': True,
                'no_color': True,
                'extract_flat': False,
                'noprogress': True,  # KEY FIX: Disable progress display
                'logger': QuietLogger(),  # KEY FIX: Custom logger
                'nocheckcertificate': True,
            }
            
            # Search and download
            search_query = f"ytsearch1:{query}"
            
            # CRITICAL: Suppress stdout/stderr during download to avoid encoding issues
            if sys.platform == 'win32':
                # On Windows, redirect outputs to avoid console encoding errors
                old_stdout = sys.stdout
                old_stderr = sys.stderr
                try:
                    # Redirect to null
                    with open(os.devnull, 'w') as devnull:
                        sys.stdout = devnull
                        sys.stderr = devnull
                        
                        with self.yt_dlp.YoutubeDL(ydl_opts) as ydl:
                            info = ydl.extract_info(search_query, download=True)
                finally:
                    # Restore outputs
                    sys.stdout = old_stdout
                    sys.stderr = old_stderr
            else:
                # On Linux/Mac, no need for redirection
                with self.yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(search_query, download=True)
            
            if not info:
                logger.error("No search results")
                return None
            
            # Get first result
            if 'entries' in info:
                info = info['entries'][0]
            
            # Get title
            title = info.get('title', 'unknown')
            
            # Sanitize title for filename
            title = self._sanitize_filename(title)
            
            # Find the downloaded file (most recent .mp3 in cache)
            downloaded_files = list(self.cache_dir.glob('*.mp3'))
            if downloaded_files:
                # Get most recent file
                file_path = max(downloaded_files, key=lambda p: p.stat().st_mtime)
                
                print(f"[YOUTUBE] ✅ Downloaded: {file_path.name}")
                logger.info(f"Downloaded: {file_path.name}")
                return str(file_path)
            
            logger.error("Download completed but file not found")
            return None
            
        except Exception as e:
            logger.error(f"YouTube download error: {e}")
            print(f"[FAIL] YouTube error: {e}")
            
            # Detailed traceback
            import traceback
            logger.error(traceback.format_exc())
            
            return None
    
    def _sanitize_filename(self, filename: str) -> str:
        """
        Sanitize filename to remove problematic characters.
        
        Args:
            filename: Original filename
            
        Returns:
            Sanitized filename
        """
        # Remove or replace problematic characters
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            filename = filename.replace(char, '_')
        
        # Replace unicode dashes/quotes
        replacements = {
            '\u2012': '-', '\u2013': '-', '\u2014': '--',
            '\u2018': "'", '\u2019': "'", '\u201c': '"', '\u201d': '"'
        }
        for old, new in replacements.items():
            filename = filename.replace(old, new)
        
        # Limit length
        if len(filename) > 200:
            filename = filename[:200]
        
        return filename
    
    def stream_url(self, query: str) -> Optional[str]:
        """
        Get direct audio stream URL without downloading.
        
        Args:
            query: Song name or YouTube URL
            
        Returns:
            Stream URL or None
        """
        if not self.available:
            return None
        
        try:
            # Ensure string
            if isinstance(query, bytes):
                query = query.decode('utf-8')
            
            class QuietLogger:
                def debug(self, msg): pass
                def info(self, msg): pass
                def warning(self, msg): pass
                def error(self, msg):
                    logger.error(f"yt-dlp: {msg}")
            
            ydl_opts = {
                'format': 'bestaudio/best',
                'quiet': True,
                'no_warnings': True,
                'no_color': True,
                'noprogress': True,
                'logger': QuietLogger(),
            }
            
            search_query = f"ytsearch1:{query}"
            
            # Redirect outputs on Windows
            if sys.platform == 'win32':
                old_stdout = sys.stdout
                old_stderr = sys.stderr
                try:
                    with open(os.devnull, 'w') as devnull:
                        sys.stdout = devnull
                        sys.stderr = devnull
                        
                        with self.yt_dlp.YoutubeDL(ydl_opts) as ydl:
                            info = ydl.extract_info(search_query, download=False)
                finally:
                    sys.stdout = old_stdout
                    sys.stderr = old_stderr
            else:
                with self.yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(search_query, download=False)
            
            if not info:
                return None
            
            if 'entries' in info:
                info = info['entries'][0]
            
            url = info.get('url')
            title = info.get('title', 'unknown')
            
            print(f"[YOUTUBE] Found: {title}")
            logger.info(f"Found: {title}")
            
            return url
            
        except Exception as e:
            logger.error(f"YouTube stream error: {e}")
            return None
    
    def clean_cache(self, max_size_mb: int = 500):
        """Clean cache if it exceeds size limit"""
        try:
            total_size = sum(f.stat().st_size for f in self.cache_dir.glob('*') if f.is_file())
            total_size_mb = total_size / (1024 * 1024)
            
            if total_size_mb > max_size_mb:
                logger.info(f"Cleaning cache ({total_size_mb:.1f}MB)")
                
                # Delete oldest files
                files = sorted(self.cache_dir.glob('*'), key=lambda f: f.stat().st_mtime)
                
                while total_size_mb > max_size_mb * 0.8 and files:
                    file = files.pop(0)
                    size = file.stat().st_size / (1024 * 1024)
                    file.unlink()
                    total_size_mb -= size
                    
        except Exception as e:
            logger.error(f"Cache cleanup error: {e}")