import os
from typing import List, Dict, Any, Optional
from openai import AsyncOpenAI
from dotenv import load_dotenv
from app.actions.base import Action, ActionResult, SecurityLevel
from app.utils.config import config
from app.utils.logger import get_logger

load_dotenv()
logger = get_logger('conversation')

class ConversationAction(Action):
    """General conversation and AI responses"""
    
    def __init__(self):
        super().__init__()
        self.description = "General conversation and questions"
        self.security_level = SecurityLevel.SAFE
        self.client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        
        # Load from config
        action_config = config.get_actions('conversation')
        if action_config:
            self.enabled = action_config.get('enabled', True)
    
    def get_intents(self) -> List[str]:
        """This is a catch-all action"""
        return ["*"]  # Matches everything
    
    def matches_intent(self, prompt: str) -> bool:
        """Always matches - this is the fallback action"""
        return True
    
    async def execute(self, prompt: str, params: Optional[Dict[str, Any]] = None) -> ActionResult:
        """Execute general conversation"""
        try:
            logger.info(f"💬 Conversing: {prompt}")
            
            response = await self.client.chat.completions.create(
                model=config.get('settings.ai.model', 'gpt-4o-mini'),
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a witty assistant. Answer questions normally, but always end your response "
                            "with a Cristiano Ronaldo reference or joke, even if the question is unrelated to football. "
                            "Keep answers short and playful."
                        )
                    },
                    {"role": "user", "content": prompt}
                ],
                temperature=config.get('settings.ai.temperature', 0.7),
                max_tokens=config.get('settings.ai.max_tokens', 500)
            )
            
            answer = response.choices[0].message.content.strip()
            logger.info(f"✅ Conversation completed")
            
            return ActionResult(
                success=True,
                message=answer,
                data={"type": "conversation"}
            )
            
        except Exception as e:
            logger.error(f"Conversation error: {e}")
            return ActionResult(
                success=False,
                message=f"Sorry, I encountered an error: {str(e)}"
            )