from typing import List, Dict, Any, Optional
from app.actions.base import Action, ActionResult, SecurityLevel
from app.utils.config import config
from app.utils.logger import get_logger

logger = get_logger('smart_home')

class SmartHomeAction(Action):
    """Smart home control actions (lights, etc.)"""
    
    def __init__(self):
        super().__init__()
        self.description = "Control smart home devices like lights"
        self.security_level = SecurityLevel.SAFE
        
        # Load from config
        action_config = config.get_actions('smart_home')
        if action_config:
            self.enabled = action_config.get('enabled', True)
    
    def get_intents(self) -> List[str]:
        """Intent patterns for smart home control"""
        return [
            "turn on light",
            "turn off light",
            "toggle light",
            "turn on the light",
            "turn off the light",
            "lights on",
            "lights off"
        ]
    
    async def execute(self, prompt: str, params: Optional[Dict[str, Any]] = None) -> ActionResult:
        """Execute smart home action"""
        prompt_lower = prompt.lower()
        
        try:
            if "on" in prompt_lower:
                # TODO: Integrate with actual smart home API (Hue, HomeAssistant, etc.)
                logger.info("💡 Turning light ON")
                return ActionResult(
                    success=True,
                    message="Turning on the light 💡",
                    data={"state": "on"}
                )
            
            elif "off" in prompt_lower:
                logger.info("💡 Turning light OFF")
                return ActionResult(
                    success=True,
                    message="Turning off the light 💡",
                    data={"state": "off"}
                )
            
            else:
                return ActionResult(
                    success=False,
                    message="I'm not sure what to do with the lights."
                )
                
        except Exception as e:
            logger.error(f"Smart home error: {e}")
            return ActionResult(
                success=False,
                message=f"Failed to control light: {str(e)}"
            )