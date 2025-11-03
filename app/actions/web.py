import os
from typing import List, Dict, Any, Optional
from openai import AsyncOpenAI
from dotenv import load_dotenv
from app.actions.base import Action, ActionResult, SecurityLevel
from app.utils.config import config
from app.utils.logger import get_logger

load_dotenv()
logger = get_logger('web')

class WebSearchAction(Action):
    """Web search and knowledge queries"""
    
    def __init__(self):
        super().__init__()
        self.description = "Search the web for information"
        self.security_level = SecurityLevel.SAFE
        self.client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        
        # Load from config
        action_config = config.get_actions('web')
        if action_config:
            self.enabled = action_config.get('enabled', True)
    
    def get_intents(self) -> List[str]:
        """Intent patterns for web search"""
        return [
            "search for",
            "look up",
            "what is",
            "who is",
            "when did",
            "where is",
            "how to",
            "find information about",
            "tell me about"
        ]
    
    async def execute(self, prompt: str, params: Optional[Dict[str, Any]] = None) -> ActionResult:
        """Execute web search"""
        try:
            logger.info(f"🌐 Searching for: {prompt}")
            
            # TODO: Replace with actual web search API (Brave, Serper, etc.)
            # For now, using OpenAI's knowledge
            response = await self.client.chat.completions.create(
                model=config.get('settings.ai.model', 'gpt-4o-mini'),
                messages=[{
                    "role": "user",
                    "content": f"Answer this query accurately and concisely: {prompt}"
                }],
                temperature=0
            )
            
            answer = response.choices[0].message.content.strip()
            logger.info(f"✅ Search completed")
            
            return ActionResult(
                success=True,
                message=answer,
                data={"query": prompt, "source": "openai"}
            )
            
        except Exception as e:
            logger.error(f"Web search error: {e}")
            return ActionResult(
                success=False,
                message=f"Failed to search: {str(e)}"
            )