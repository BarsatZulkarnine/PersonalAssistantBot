"""
Music Player Action

Voice commands for music playback.
"""

import yaml
from pathlib import Path
from typing import List, Optional, Dict, Any
from modules.actions.base import Action, ActionResult, ActionCategory, SecurityLevel
from modules.music.player import MusicPlayer
from utils.logger import get_logger

logger = get_logger('actions.music')

class MusicAction(Action):
    """Music playback control"""
    
    def __init__(self):
        super().__init__()
        self.category = ActionCategory.SYSTEM  # or create ENTERTAINMENT category
        self.security_level = SecurityLevel.SAFE
        self.description = "Play and control music"
        
        # Load config
        config = self._load_config()
        
        # Initialize player
        try:
            self.player = MusicPlayer(config)
            self.enabled = True
            logger.info("[OK] Music action initialized")
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
            # Play commands - MUST BE FIRST for priority matching
            "play",
            "play music",
            "play song",
            "play ",  # Catches "play [anything]"
            "start music",
            
            # Control commands
            "pause",
            "pause music",
            "resume",
            "resume music",
            "stop music",
            "stop",
            
            # Navigation
            "next song",
            "next",
            "skip",
            "previous song",
            "previous",
            "back",
            
            # Queue
            "add to queue",
            "queue",
            "clear queue",
            
            # Settings
            "shuffle",
            "louder",
            "quieter",
            
            # Status
            "what's playing",
            "current song"
        ]
    
    def matches(self, prompt: str) -> bool:
        """Custom matching for music commands"""
        prompt_lower = prompt.lower()
        
        # Priority: Check if it starts with "play" (but not "play with", "play around")
        if prompt_lower.startswith("play ") and len(prompt_lower) > 5:
            # Check it's not something else
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
        
        prompt_lower = prompt.lower()
        
        print(f"[MUSIC] Command: {prompt}")
        
        try:
            # Play commands
            if any(cmd in prompt_lower for cmd in ["play music", "start music"]):
                result = self.player.play()
                return ActionResult(success=True, message=result)
            
            # Play specific song
            elif prompt_lower.startswith("play "):
                query = prompt[5:].strip()  # Remove "play "
                result = self.player.play(query)
                return ActionResult(success=True, message=result)
            
            # Pause
            elif "pause" in prompt_lower:
                result = self.player.pause()
                return ActionResult(success=True, message=result)
            
            # Resume
            elif "resume" in prompt_lower or "unpause" in prompt_lower or "continue" in prompt_lower:
                result = self.player.resume()
                return ActionResult(success=True, message=result)
            
            # Stop
            elif "stop" in prompt_lower:
                result = self.player.stop()
                return ActionResult(success=True, message=result)
            
            # Next
            elif "next" in prompt_lower or "skip" in prompt_lower:
                result = self.player.next()
                return ActionResult(success=True, message=result)
            
            # Previous
            elif "previous" in prompt_lower or "back" in prompt_lower:
                result = self.player.previous()
                return ActionResult(success=True, message=result)
            
            # Volume
            elif "louder" in prompt_lower or ("volume" in prompt_lower and "up" in prompt_lower):
                result = self.player.volume_up()
                return ActionResult(success=True, message=result)
            
            elif "quieter" in prompt_lower or ("volume" in prompt_lower and "down" in prompt_lower):
                result = self.player.volume_down()
                return ActionResult(success=True, message=result)
            
            # Shuffle
            elif "shuffle" in prompt_lower:
                result = self.player.toggle_shuffle()
                return ActionResult(success=True, message=result)
            
            # Queue
            elif "add to queue" in prompt_lower or "queue" in prompt_lower:
                query = prompt_lower.replace("add to queue", "").replace("queue", "").strip()
                if query:
                    result = self.player.add_to_queue(query)
                    return ActionResult(success=True, message=result)
                else:
                    return ActionResult(success=False, message="What should I add to queue?")
            
            elif "clear queue" in prompt_lower:
                result = self.player.clear_queue()
                return ActionResult(success=True, message=result)
            
            # Status
            elif "what's playing" in prompt_lower or "current song" in prompt_lower:
                status = self.player.get_status()
                if status['current_song']:
                    return ActionResult(
                        success=True,
                        message=f"Playing: {status['current_song']}"
                    )
                else:
                    return ActionResult(
                        success=True,
                        message="Nothing is playing"
                    )
            
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