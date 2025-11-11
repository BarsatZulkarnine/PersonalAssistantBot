"""
Music Action - REFACTORED FOR CLIENT-AWARENESS

Now supports:
- Server playback (CLI mode)
- Client playback (API mode - returns stream info)
- YouTube streaming
- Local file streaming
"""

import yaml
from pathlib import Path
from typing import List, Optional, Dict, Any
from modules.actions.base import Action, ActionResult, ActionCategory, SecurityLevel
from modules.music.player import MusicPlayer
from utils.logger import get_logger

logger = get_logger('actions.music')

class MusicAction(Action):
    """Client-aware music playback control"""
    
    def __init__(self):
        super().__init__()
        self.category = ActionCategory.ENTERTAINMENT
        self.security_level = SecurityLevel.SAFE
        self.description = "Play and control music"
        
        # Load config
        config = self._load_config()
        
        # Initialize player (still needed for server playback)
        try:
            self.player = MusicPlayer(config)
            self.enabled = True
            logger.info("[OK] Music action initialized (client-aware)")
        except Exception as e:
            logger.error(f"[FAIL] Music player init failed: {e}")
            self.player = None
            self.enabled = False
    
    def _load_config(self) -> dict:
        """Load music config"""
        config_path = Path("config/modules/music.yaml")
        
        if config_path.exists():
            with open(config_path, 'r') as f:
                return yaml.safe_load(f) or {}
        
        return {
            'music': {
                'directories': ['~/Music'],
                'formats': ['mp3', 'wav']
            },
            'playback': {
                'volume': 0.7,
                'shuffle': False
            }
        }
    
    def get_intents(self) -> List[str]:
        return [
            "play",
            "play music",
            "play song",
            "pause",
            "resume",
            "stop",
            "next",
            "previous",
            "volume up",
            "volume down",
            "what's playing"
        ]
    
    def matches(self, prompt: str) -> bool:
        """Custom matching for music commands"""
        prompt_lower = prompt.lower()
        
        # Priority: Check if it starts with "play"
        if prompt_lower.startswith("play ") and len(prompt_lower) > 5:
            if not any(word in prompt_lower for word in ["play with", "play around", "play a game"]):
                return True
        
        # Standard intent matching
        for intent in self.get_intents():
            if intent in prompt_lower:
                return True
        
        return False
    
    async def execute(self, prompt: str, params: Optional[Dict[str, Any]] = None) -> ActionResult:
        if not self.player:
            return ActionResult(
                success=False,
                message="Music player not available"
            )
        
        # Extract client type
        client_type = params.get('client_type', 'server') if params else 'server'
        
        prompt_lower = prompt.lower()
        
        print(f"[MUSIC] Command: {prompt} (client={client_type})")
        
        try:
            # ============================================
            # PLAY COMMANDS
            # ============================================
            if any(cmd in prompt_lower for cmd in ["play music", "start music"]):
                return await self._handle_play(None, client_type)
            
            elif prompt_lower.startswith("play "):
                query = prompt[5:].strip()
                return await self._handle_play(query, client_type)
            
            # ============================================
            # CONTROL COMMANDS
            # ============================================
            elif "pause" in prompt_lower:
                return self._handle_pause(client_type)
            
            elif "resume" in prompt_lower or "continue" in prompt_lower:
                return self._handle_resume(client_type)
            
            elif "stop" in prompt_lower:
                return self._handle_stop(client_type)
            
            elif "next" in prompt_lower or "skip" in prompt_lower:
                return self._handle_next(client_type)
            
            elif "previous" in prompt_lower or "back" in prompt_lower:
                return self._handle_previous(client_type)
            
            # ============================================
            # VOLUME COMMANDS
            # ============================================
            elif "louder" in prompt_lower or ("volume" in prompt_lower and "up" in prompt_lower):
                return self._handle_volume_up(client_type)
            
            elif "quieter" in prompt_lower or ("volume" in prompt_lower and "down" in prompt_lower):
                return self._handle_volume_down(client_type)
            
            # ============================================
            # STATUS COMMANDS
            # ============================================
            elif "what's playing" in prompt_lower or "current song" in prompt_lower:
                return self._handle_status(client_type)
            
            else:
                return ActionResult(
                    success=False,
                    message="I didn't understand that music command"
                )
                
        except Exception as e:
            logger.error(f"Music command error: {e}")
            return ActionResult(
                success=False,
                message=f"Music error: {str(e)}"
            )
    
    # ============================================
    # COMMAND HANDLERS
    # ============================================
    
    async def _handle_play(self, query: Optional[str], client_type: str) -> ActionResult:
        """Handle play command"""
        
        # Get song info
        if query:
            song_info = self._get_song_info(query)
        else:
            song_info = self._get_random_song_info()
        
        if not song_info:
            return ActionResult(
                success=False,
                message=f"Could not find '{query}'" if query else "No songs available"
            )
        
        # CLIENT-AWARE LOGIC
        if client_type == "server":
            # Play on server (current behavior)
            result = self.player.play(query)
            return ActionResult(
                success=True,
                message=result
            )
        
        else:
            # Return playback info for client
            return ActionResult(
                success=True,
                message=f"Now playing {song_info['name']}",
                data={
                    'action': 'play_music',
                    'music': song_info
                }
            )
    
    def _handle_pause(self, client_type: str) -> ActionResult:
        """Handle pause command"""
        if client_type == "server":
            result = self.player.pause()
            return ActionResult(success=True, message=result)
        else:
            return ActionResult(
                success=True,
                message="Music paused",
                data={'action': 'pause_music'}
            )
    
    def _handle_resume(self, client_type: str) -> ActionResult:
        """Handle resume command"""
        if client_type == "server":
            result = self.player.resume()
            return ActionResult(success=True, message=result)
        else:
            return ActionResult(
                success=True,
                message="Music resumed",
                data={'action': 'resume_music'}
            )
    
    def _handle_stop(self, client_type: str) -> ActionResult:
        """Handle stop command"""
        if client_type == "server":
            result = self.player.stop()
            return ActionResult(success=True, message=result)
        else:
            return ActionResult(
                success=True,
                message="Music stopped",
                data={'action': 'stop_music'}
            )
    
    def _handle_next(self, client_type: str) -> ActionResult:
        """Handle next command"""
        if client_type == "server":
            result = self.player.next()
            return ActionResult(success=True, message=result)
        else:
            return ActionResult(
                success=True,
                message="Skipped to next song",
                data={'action': 'next_song'}
            )
    
    def _handle_previous(self, client_type: str) -> ActionResult:
        """Handle previous command"""
        if client_type == "server":
            result = self.player.previous()
            return ActionResult(success=True, message=result)
        else:
            return ActionResult(
                success=True,
                message="Playing previous song",
                data={'action': 'previous_song'}
            )
    
    def _handle_volume_up(self, client_type: str) -> ActionResult:
        """Handle volume up"""
        if client_type == "server":
            result = self.player.volume_up()
            return ActionResult(success=True, message=result)
        else:
            return ActionResult(
                success=True,
                message="Volume increased",
                data={'action': 'volume_change', 'direction': 'up'}
            )
    
    def _handle_volume_down(self, client_type: str) -> ActionResult:
        """Handle volume down"""
        if client_type == "server":
            result = self.player.volume_down()
            return ActionResult(success=True, message=result)
        else:
            return ActionResult(
                success=True,
                message="Volume decreased",
                data={'action': 'volume_change', 'direction': 'down'}
            )
    
    def _handle_status(self, client_type: str) -> ActionResult:
        """Handle status request"""
        status = self.player.get_status()
        
        if status['current_song']:
            message = f"Playing: {status['current_song']}"
        else:
            message = "Nothing is playing"
        
        return ActionResult(
            success=True,
            message=message,
            data={'status': status}
        )
    
    # ============================================
    # SONG INFO HELPERS
    # ============================================
    
    def _get_song_info(self, query: str) -> Optional[Dict[str, Any]]:
        """Get song information for playback"""
        
        # Check local library first
        song = self.player._find_song(query)
        
        if song:
            return {
                'type': 'local',
                'name': song.name,
                'path': song.path,
                'stream_url': f"/api/music/stream/{song.name}",
                'source': 'local'
            }
        
        # Try YouTube - FIXED: Use search_and_download instead of _get_video_info
        if self.player.youtube and self.player.youtube.available:
            try:
                # Download from YouTube and get the file path
                cache_path = self.player.youtube.search_and_download(query)
                
                if cache_path:
                    # Extract filename from path
                    from pathlib import Path
                    filename = Path(cache_path).stem
                    
                    return {
                        'type': 'youtube',
                        'name': filename,
                        'path': cache_path,
                        'stream_url': f"/api/music/stream/{filename}",
                        'source': 'youtube'
                    }
            except Exception as e:
                logger.error(f"YouTube download error: {e}")
        
        return None
    
    def _get_random_song_info(self) -> Optional[Dict[str, Any]]:
        """Get random song info"""
        if not self.player.library:
            return None
        
        import random
        song = random.choice(self.player.library)
        
        return {
            'type': 'local',
            'name': song.name,
            'path': song.path,
            'stream_url': f"/api/music/stream/{song.name}",
            'source': 'local'
        }