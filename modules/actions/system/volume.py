"""
System Volume Control Action
"""

import os
import platform
from typing import List, Optional, Dict, Any
from modules.actions.base import Action, ActionResult, ActionCategory, SecurityLevel
from utils.logger import get_logger

logger = get_logger('actions.system.volume')

class VolumeAction(Action):
    """Control system volume"""
    
    def __init__(self):
        super().__init__()
        self.category = ActionCategory.SYSTEM
        self.security_level = SecurityLevel.SAFE
        self.description = "Control system volume"
        self.system = platform.system()
        self.step = 10  # Volume step percentage
        
        logger.info(f"Volume action initialized (system={self.system})")
    
    def get_intents(self) -> List[str]:
        return [
            "volume up",
            "volume down",
            "increase volume",
            "decrease volume",
            "turn up volume",
            "turn down volume",
            "louder",
            "quieter"
        ]
    
    async def execute(self, prompt: str, params: Optional[Dict[str, Any]] = None) -> ActionResult:
        prompt_lower = prompt.lower()
        
        # Determine direction
        if any(word in prompt_lower for word in ["up", "increase", "louder", "turn up"]):
            direction = "up"
        elif any(word in prompt_lower for word in ["down", "decrease", "quieter", "turn down"]):
            direction = "down"
        else:
            return ActionResult(
                success=False,
                message="I'm not sure if you want volume up or down."
            )
        
        logger.info(f"Volume {direction} requested (system={self.system})")
        print(f"🔊 VOLUME ACTION: Turning volume {direction} on {self.system}")
        
        try:
            if self.system == "Linux":
                return await self._linux_volume(direction)
            elif self.system == "Darwin":  # macOS
                return await self._macos_volume(direction)
            elif self.system == "Windows":
                return await self._windows_volume(direction)
            else:
                return ActionResult(
                    success=False,
                    message=f"Volume control not supported on {self.system}"
                )
                
        except Exception as e:
            logger.error(f"Volume control error: {e}")
            return ActionResult(
                success=False,
                message=f"Failed to control volume: {str(e)}"
            )
    
    async def _linux_volume(self, direction: str) -> ActionResult:
        """Linux volume control"""
        operator = "+" if direction == "up" else "-"
        cmd = f"pactl set-sink-volume @DEFAULT_SINK@ {operator}{self.step}%"
        
        print(f"🐧 LINUX: Executing: {cmd}")
        os.system(cmd)
        
        return ActionResult(
            success=True,
            message=f"Volume {'increased' if direction == 'up' else 'decreased'} 🔊"
        )
    
    async def _macos_volume(self, direction: str) -> ActionResult:
        """macOS volume control"""
        operator = "+" if direction == "up" else "-"
        cmd = f"osascript -e 'set volume output volume (output volume of (get volume settings) {operator} {self.step})'"
        
        print(f"🍎 MACOS: Executing: {cmd}")
        os.system(cmd)
        
        return ActionResult(
            success=True,
            message=f"Volume {'increased' if direction == 'up' else 'decreased'} 🔊"
        )
    
    async def _windows_volume(self, direction: str) -> ActionResult:
        """Windows volume control"""
        try:
            # Try using pycaw for Windows
            from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
            from comtypes import CLSCTX_ALL
            from ctypes import cast, POINTER
            
            print(f"🪟 WINDOWS: Using pycaw library")
            
            devices = AudioUtilities.GetSpeakers()
            interface = devices.Activate(
                IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
            volume = cast(interface, POINTER(IAudioEndpointVolume))
            
            current = volume.GetMasterVolumeLevelScalar()
            step = self.step / 100.0
            
            if direction == "up":
                new_volume = min(1.0, current + step)
            else:
                new_volume = max(0.0, current - step)
            
            volume.SetMasterVolumeLevelScalar(new_volume, None)
            
            print(f"🪟 WINDOWS: Volume changed from {current:.0%} to {new_volume:.0%}")
            
            return ActionResult(
                success=True,
                message=f"Volume {'increased' if direction == 'up' else 'decreased'} 🔊"
            )
            
        except ImportError:
            logger.warning("pycaw not installed, volume control unavailable on Windows")
            print("⚠️  WINDOWS: pycaw library not installed!")
            print("   Install with: pip install pycaw")
            
            return ActionResult(
                success=False,
                message="Volume control requires pycaw library. Install with: pip install pycaw"
            )
        except Exception as e:
            logger.error(f"Windows volume error: {e}")
            print(f"❌ WINDOWS volume error: {e}")
            
            return ActionResult(
                success=False,
                message=f"Windows volume control failed: {str(e)}"
            )