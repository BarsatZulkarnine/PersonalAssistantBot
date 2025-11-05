"""
YouTube Music Streamer - Stream + Background Download

Streams immediately while downloading in background for caching
"""

import os
import sys
import threading
from pathlib import Path
from typing import Optional, Tuple
from utils.logger import get_logger

logger = get_logger('music.youtube')

class YouTubeStreamer:
    """
    YouTube music streaming with background caching.
    
    Requires: pip install yt-dlp
    """
    
    def __init__(self, config: dict):
        self.config = config
        self.cache_dir = Path(config.get('youtube', {}).get('download_dir', 'data/music_cache'))
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Track active downloads
        self.active_downloads = {}
        self.download_lock = threading.Lock()
        
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
    
    def get_stream_and_download(self, query: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Get stream URL immediately and start background download.
        
        Args:
            query: Song name or search query
            
        Returns:
            Tuple of (stream_url, expected_cache_path)
        """
        if not self.available:
            logger.error("YouTube not available")
            return None, None
        
        try:
            print(f"[YOUTUBE] Searching for: {query}")
            
            # Ensure query is a string
            if isinstance(query, bytes):
                query = query.decode('utf-8')
            
            # Check if already in cache
            cached_file = self._find_in_cache(query)
            if cached_file:
                print(f"[YOUTUBE] ✅ Found in cache: {cached_file.name}")
                return str(cached_file), str(cached_file)
            
            # Get video info (fast, no download)
            info = self._get_video_info(query)
            if not info:
                return None, None
            
            # Get stream URL
            stream_url = info.get('url')
            title = info.get('title', 'unknown')
            video_id = info.get('id', 'unknown')
            
            print(f"[YOUTUBE] 🎵 Streaming: {title}")
            logger.info(f"Streaming: {title}")
            
            # Calculate expected cache path
            sanitized_title = self._sanitize_filename(title)
            cache_path = self.cache_dir / f"{sanitized_title}.mp3"
            
            # Start background download
            self._start_background_download(query, video_id, title)
            
            return stream_url, str(cache_path)
            
        except Exception as e:
            logger.error(f"YouTube stream error: {e}")
            print(f"[FAIL] YouTube error: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return None, None
    
    def _get_video_info(self, query: str) -> Optional[dict]:
        """Get video info without downloading"""
        try:
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
                'nocheckcertificate': True,
            }
            
            search_query = f"ytsearch1:{query}"
            
            # Redirect outputs on Windows
            if sys.platform == 'win32':
                old_stdout = sys.stdout
                old_stderr = sys.stderr
                try:
                    with open(os.devnull, 'w', encoding='utf-8') as devnull:
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
            
            return info
            
        except Exception as e:
            logger.error(f"Info extraction error: {e}")
            return None
    
    def _start_background_download(self, query: str, video_id: str, title: str):
        """Start downloading in background thread"""
        with self.download_lock:
            # Check if already downloading
            if video_id in self.active_downloads:
                logger.info(f"Already downloading: {title}")
                return
            
            # Mark as downloading
            self.active_downloads[video_id] = True
        
        # Start download thread
        thread = threading.Thread(
            target=self._background_download_worker,
            args=(query, video_id, title),
            daemon=True
        )
        thread.start()
        print(f"[YOUTUBE] ⬇️  Downloading in background: {title}")
    
    def _background_download_worker(self, query: str, video_id: str, title: str):
        """Worker thread for background downloading"""
        try:
            class QuietLogger:
                def debug(self, msg): pass
                def info(self, msg): pass
                def warning(self, msg): pass
                def error(self, msg):
                    logger.error(f"yt-dlp: {msg}")
            
            sanitized_title = self._sanitize_filename(title)
            
            ydl_opts = {
                'format': 'bestaudio/best',
                'outtmpl': str(self.cache_dir / f'{sanitized_title}.%(ext)s'),
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }],
                'quiet': True,
                'no_warnings': True,
                'noplaylist': True,
                'no_color': True,
                'noprogress': True,
                'logger': QuietLogger(),
                'nocheckcertificate': True,
            }
            
            search_query = f"ytsearch1:{query}"
            
            # Download with output suppression
            if sys.platform == 'win32':
                old_stdout = sys.stdout
                old_stderr = sys.stderr
                try:
                    with open(os.devnull, 'w', encoding='utf-8') as devnull:
                        sys.stdout = devnull
                        sys.stderr = devnull
                        
                        with self.yt_dlp.YoutubeDL(ydl_opts) as ydl:
                            ydl.extract_info(search_query, download=True)
                finally:
                    sys.stdout = old_stdout
                    sys.stderr = old_stderr
            else:
                with self.yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.extract_info(search_query, download=True)
            
            print(f"[YOUTUBE] ✅ Cached: {sanitized_title}.mp3")
            logger.info(f"Background download complete: {sanitized_title}.mp3")
            
        except Exception as e:
            logger.error(f"Background download error: {e}")
            print(f"[YOUTUBE] ⚠️  Cache failed for: {title}")
        finally:
            # Remove from active downloads
            with self.download_lock:
                self.active_downloads.pop(video_id, None)
    
    def _find_in_cache(self, query: str) -> Optional[Path]:
        """Search for matching file in cache"""
        try:
            query_lower = query.lower()
            
            for file in self.cache_dir.glob('*.mp3'):
                # Simple matching: if query terms are in filename
                filename_lower = file.stem.lower()
                
                # Split query into words
                query_words = query_lower.split()
                
                # Check if most words match
                matches = sum(1 for word in query_words if word in filename_lower)
                
                # If >70% of words match, consider it a hit
                if len(query_words) > 0 and matches / len(query_words) > 0.7:
                    return file
            
            return None
            
        except Exception as e:
            logger.error(f"Cache search error: {e}")
            return None
    
    def _sanitize_filename(self, filename: str) -> str:
        """Sanitize filename to remove problematic characters"""
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            filename = filename.replace(char, '_')
        
        replacements = {
            '\u2012': '-', '\u2013': '-', '\u2014': '--',
            '\u2018': "'", '\u2019': "'", '\u201c': '"', '\u201d': '"'
        }
        for old, new in replacements.items():
            filename = filename.replace(old, new)
        
        if len(filename) > 200:
            filename = filename[:200]
        
        return filename
    
    def stream_url(self, query: str) -> Optional[str]:
        """Get stream URL only (legacy method for compatibility)"""
        stream_url, _ = self.get_stream_and_download(query)
        return stream_url
    
    def search_and_download(self, query: str) -> Optional[str]:
        """Download only (legacy method, blocks until complete)"""
        if not self.available:
            return None
        
        # Check cache first
        cached = self._find_in_cache(query)
        if cached:
            print(f"[YOUTUBE] ✅ Found in cache: {cached.name}")
            return str(cached)
        
        # Download synchronously (original behavior)
        try:
            print(f"[YOUTUBE] Downloading: {query}")
            
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
                'noprogress': True,
                'logger': QuietLogger(),
                'nocheckcertificate': True,
            }
            
            search_query = f"ytsearch1:{query}"
            
            if sys.platform == 'win32':
                old_stdout = sys.stdout
                old_stderr = sys.stderr
                try:
                    with open(os.devnull, 'w', encoding='utf-8') as devnull:
                        sys.stdout = devnull
                        sys.stderr = devnull
                        
                        with self.yt_dlp.YoutubeDL(ydl_opts) as ydl:
                            ydl.extract_info(search_query, download=True)
                finally:
                    sys.stdout = old_stdout
                    sys.stderr = old_stderr
            else:
                with self.yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.extract_info(search_query, download=True)
            
            # Find downloaded file
            downloaded_files = list(self.cache_dir.glob('*.mp3'))
            if downloaded_files:
                file_path = max(downloaded_files, key=lambda p: p.stat().st_mtime)
                print(f"[YOUTUBE] ✅ Downloaded: {file_path.name}")
                return str(file_path)
            
            return None
            
        except Exception as e:
            logger.error(f"Download error: {e}")
            return None
    
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
                    
        except Exception as e:
            logger.error(f"Cache cleanup error: {e}")