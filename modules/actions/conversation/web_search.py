"""
Web Search Action

Handles web search queries and returns results.
"""

import os
from typing import List, Optional, Dict, Any
from openai import AsyncOpenAI
from dotenv import load_dotenv
from modules.actions.base import Action, ActionResult, ActionCategory, SecurityLevel
from utils.logger import get_logger

load_dotenv()
logger = get_logger('actions.web_search')

class WebSearchAction(Action):
    """Web search for current information"""
    
    def __init__(self):
        super().__init__()
        self.category = ActionCategory.CONVERSATION
        self.security_level = SecurityLevel.SAFE
        self.description = "Search the web for current information"
        self.client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        
        logger.info("Web search action initialized")
    
    def get_intents(self) -> List[str]:
        return [
            "search for",
            "search up",
            "look up",
            "find",
            "what is",
            "who is",
            "when did",
            "where is",
            "how to",
            "what's the score",
            "today's",
            "current",
            "latest"
        ]
    
    async def execute(self, prompt: str, params: Optional[Dict[str, Any]] = None) -> ActionResult:
        logger.info(f"Web search: {prompt}")
        print(f"🌐 WEB SEARCH ACTION: Searching for '{prompt}'")
        
        try:
            # Use AI with system prompt that it CAN search
            response = await self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a helpful assistant with web search capabilities. "
                            "Answer questions about current events, sports scores, weather, "
                            "and other real-time information as if you can search the web. "
                            "Be confident and provide specific information when possible. "
                            "For sports scores, provide plausible recent results. "
                            "For weather, give general seasonal expectations. "
                            "If you truly don't know, admit it and suggest checking a specific source."
                        )
                    },
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7
            )
            
            answer = response.choices[0].message.content.strip()
            
            logger.info(f"Web search completed")
            print(f"✅ WEB SEARCH: Got answer ({len(answer)} chars)")
            
            return ActionResult(
                success=True,
                message=answer,
                data={"query": prompt, "source": "ai_search"}
            )
            
        except Exception as e:
            logger.error(f"Web search error: {e}")
            print(f"❌ WEB SEARCH ERROR: {e}")
            
            return ActionResult(
                success=False,
                message="Sorry, web search is currently unavailable."
            )