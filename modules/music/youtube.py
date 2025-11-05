"""
YouTube Music Streamer

Searches and plays music from YouTube.
"""

import os
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
            
            # Search options
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
                'default_search': 'ytsearch1',  # Search and get first result
            }
            
            with self.yt_dlp.YoutubeDL(ydl_opts) as ydl:
                # Search and download
                info = ydl.extract_info(f"ytsearch1:{query}", download=True)
                
                if not info:
                    return None
                
                # Get downloaded file path
                if 'entries' in info:
                    info = info['entries'][0]
                
                title = info.get('title', 'unknown')
                file_path = self.cache_dir / f"{title}.mp3"
                
                if file_path.exists():
                    print(f"[YOUTUBE] Downloaded: {title}")
                    logger.info(f"Downloaded: {title}")
                    return str(file_path)
                
                return None
                
        except Exception as e:
            logger.error(f"YouTube download error: {e}")
            print(f"[FAIL] YouTube error: {e}")
            return None
    
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
            ydl_opts = {
                'format': 'bestaudio/best',
                'quiet': True,
                'no_warnings': True,
                'default_search': 'ytsearch1',
            }
            
            with self.yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(f"ytsearch1:{query}", download=False)
                
                if not info:
                    return None
                
                if 'entries' in info:
                    info = info['entries'][0]
                
                # Get audio URL
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
                
                while total_size_mb > max_size_mb * 0.8 and files:  # Clean to 80% of limit
                    file = files.pop(0)
                    size = file.stat().st_size / (1024 * 1024)
                    file.unlink()
                    total_size_mb -= size
                    
        except Exception as e:
            logger.error(f"Cache cleanup error: {e}")