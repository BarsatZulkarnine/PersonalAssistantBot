"""
AI Chat Action

General conversation with AI.
"""

import os
from typing import List, Optional, Dict, Any
from openai import AsyncOpenAI
from dotenv import load_dotenv
from modules.actions.base import Action, ActionResult, ActionCategory, SecurityLevel
from utils.logger import get_logger

load_dotenv()
logger = get_logger('actions.ai_chat')

class AIChatAction(Action):
    """General AI conversation"""
    
    def __init__(self):
        super().__init__()
        self.category = ActionCategory.CONVERSATION
        self.security_level = SecurityLevel.SAFE
        self.description = "General conversation and questions"
        self.client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        
        logger.info("AI chat action initialized")
    
    def get_intents(self) -> List[str]:
        # Catch-all intents
        return [
            "tell me",
            "what do you think",
            "explain",
            "how are you",
            "hello",
            "hi",
            "hey"
        ]
    
    def matches(self, prompt: str) -> bool:
        """
        This is a fallback action, so it matches anything
        that doesn't match other actions.
        """
        return True  # Always matches (fallback)
    
    async def execute(self, prompt: str, params: Optional[Dict[str, Any]] = None) -> ActionResult:
        logger.info(f"AI chat: {prompt}")
        print(f"AI CHAT ACTION: Processing '{prompt}'")
        
        try:
            response = await self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a helpful and friendly AI assistant. "
                            "Answer questions clearly and concisely. "
                            "Be conversational but informative."
                        )
                    },
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=150
            )
            
            answer = response.choices[0].message.content.strip()
            
            logger.info(f"AI chat completed")
            print(f"✅ AI CHAT: Generated response ({len(answer)} chars)")
            
            return ActionResult(
                success=True,
                message=answer,
                data={"type": "conversation"}
            )
            
        except Exception as e:
            logger.error(f"AI chat error: {e}")
            print(f"❌ AI CHAT ERROR: {e}")
            
            return ActionResult(
                success=False,
                message="Sorry, I encountered an error."
            )