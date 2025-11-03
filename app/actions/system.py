import os
import platform
import subprocess
from typing import List, Dict, Any, Optional
from app.actions.base import Action, ActionResult, SecurityLevel
from app.utils.config import config
from app.utils.logger import get_logger

logger = get_logger('system')

class SystemAction(Action):
    """System-level actions (volume, launching apps, etc.)"""
    
    def __init__(self):
        super().__init__()
        self.description = "System control: volume, launching apps"
        self.security_level = SecurityLevel.SAFE
        self.system = platform.system()
        
        # Load from config
        action_config = config.get_actions('system')
        if action_config:
            self.enabled = action_config.get('enabled', True)
            self.volume_step = action_config.get('volume', {}).get('step_percentage', 10)
            self.allowed_apps = action_config.get('launch_app', {}).get('allowed_apps', ['chrome'])
    
    def get_intents(self) -> List[str]:
        """Intent patterns for system actions"""
        return [
            "volume up",
            "volume down",
            "increase volume",
            "decrease volume",
            "open chrome",
            "launch chrome",
            "open firefox",
            "launch firefox",
            "open notepad",
            "start vscode"
        ]
    
    async def execute(self, prompt: str, params: Optional[Dict[str, Any]] = None) -> ActionResult:
        """Execute system action"""
        prompt_lower = prompt.lower()
        
        try:
            # Volume control
            if "volume" in prompt_lower:
                return await self._handle_volume(prompt_lower)
            
            # App launching
            elif any(word in prompt_lower for word in ["open", "launch", "start"]):
                return await self._handle_launch_app(prompt_lower)
            
            else:
                return ActionResult(
                    success=False,
                    message="I don't recognize that system command."
                )
                
        except Exception as e:
            logger.error(f"System action error: {e}")
            return ActionResult(
                success=False,
                message=f"System action failed: {str(e)}"
            )
    
    async def _handle_volume(self, prompt: str) -> ActionResult:
        """Handle volume control"""
        try:
            if "up" in prompt or "increase" in prompt:
                if self.system == "Linux":
                    os.system(f"pactl set-sink-volume @DEFAULT_SINK@ +{self.volume_step}%")
                elif self.system == "Darwin":  # macOS
                    os.system(f"osascript -e 'set volume output volume (output volume of (get volume settings) + {self.volume_step})'")
                elif self.system == "Windows":
                    # Windows volume control would need additional library
                    return ActionResult(success=False, message="Volume control not yet implemented for Windows")
                
                logger.info(f"🔊 Volume increased by {self.volume_step}%")
                return ActionResult(success=True, message=f"Volume increased 🔊")
            
            elif "down" in prompt or "decrease" in prompt:
                if self.system == "Linux":
                    os.system(f"pactl set-sink-volume @DEFAULT_SINK@ -{self.volume_step}%")
                elif self.system == "Darwin":
                    os.system(f"osascript -e 'set volume output volume (output volume of (get volume settings) - {self.volume_step})'")
                elif self.system == "Windows":
                    return ActionResult(success=False, message="Volume control not yet implemented for Windows")
                
                logger.info(f"🔉 Volume decreased by {self.volume_step}%")
                return ActionResult(success=True, message=f"Volume decreased 🔉")
            
        except Exception as e:
            logger.error(f"Volume control error: {e}")
            return ActionResult(success=False, message=f"Failed to control volume: {str(e)}")
    
    async def _handle_launch_app(self, prompt: str) -> ActionResult:
        """Handle app launching"""
        # Extract app name
        app_name = None
        for app in self.allowed_apps:
            if app.lower() in prompt:
                app_name = app
                break
        
        if not app_name:
            return ActionResult(
                success=False,
                message="I don't recognize that application."
            )
        
        try:
            if self.system == "Windows":
                if app_name == "chrome":
                    subprocess.Popen("start chrome", shell=True)
                elif app_name == "firefox":
                    subprocess.Popen("start firefox", shell=True)
                elif app_name == "notepad":
                    subprocess.Popen("notepad.exe")
            
            elif self.system == "Darwin":  # macOS
                if app_name == "chrome":
                    subprocess.Popen(["open", "-a", "Google Chrome"])
                elif app_name == "firefox":
                    subprocess.Popen(["open", "-a", "Firefox"])
                elif app_name == "vscode":
                    subprocess.Popen(["open", "-a", "Visual Studio Code"])
            
            elif self.system == "Linux":
                subprocess.Popen([app_name], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
            logger.info(f"🚀 Launched {app_name}")
            return ActionResult(
                success=True,
                message=f"Opening {app_name} 🌐",
                data={"app": app_name}
            )
            
        except Exception as e:
            logger.error(f"Failed to launch {app_name}: {e}")
            return ActionResult(
                success=False,
                message=f"Failed to open {app_name}: {str(e)}"
            )