"""
Simple AI Intent Detector

Returns one of three categories: AI, Web, Action
"""

import os
from openai import AsyncOpenAI
from dotenv import load_dotenv
from modules.intent.base import IntentDetector, IntentResult, IntentType
from utils.logger import get_logger

load_dotenv()
logger = get_logger('intent.simple_ai')

class SimpleAiIntent(IntentDetector):
    """
    Simple AI-based intent detection.
    
    Asks AI to classify into: AI, Web, or Action
    """
    
    def __init__(self, config: dict):
        super().__init__(config)
        
        simple_config = config.get('simple_ai', {})
        self.model = simple_config.get('model', 'gpt-4o-mini')
        self.temperature = simple_config.get('temperature', 0.3)
        self.categories = simple_config.get('categories', ['AI', 'Web', 'Action'])
        
        self.client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        
        logger.info(f"Simple AI Intent initialized (model={self.model})")
    
    async def detect(self, text: str) -> IntentResult:
        """
        Detect intent using AI.
        
        Returns one of: AI, Web, Action
        """
        try:
            system_prompt = f"""You are an intent classifier. 

Classify the user's input into ONE of these categories:

1. **AI** - General conversation, questions, explanations, jokes, opinions
   Examples: "Tell me a joke", "How are you?", "Explain quantum physics"

2. **Web** - Web search, current information, real-time data, facts that change
   Examples: "What's the weather?", "Who won the game?", "Search for Python tutorials"

3. **Action** - Execute a system action, control devices, open apps
   Examples: "Turn on lights", "Set volume to 50", "Open Chrome", "Send email"

Reply with ONLY ONE WORD: AI, Web, or Action

Nothing else. Just the category."""

            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Classify: {text}"}
                ],
                temperature=self.temperature,
                max_tokens=10
            )
            
            result_text = response.choices[0].message.content.strip().upper()
            
            # Parse result
            if "WEB" in result_text:
                intent_type = IntentType.WEB
            elif "ACTION" in result_text:
                intent_type = IntentType.ACTION
            else:
                intent_type = IntentType.AI
            
            logger.debug(f"Intent: {intent_type.value} for '{text}'")
            
            return IntentResult(
                intent_type=intent_type,
                confidence=0.9,  # High confidence for AI classification
                original_text=text,
                reasoning=result_text
            )
            
        except Exception as e:
            logger.error(f"Intent detection failed: {e}")
            # Fallback to AI/conversation
            return IntentResult(
                intent_type=IntentType.AI,
                confidence=0.5,
                original_text=text,
                reasoning="Error, defaulting to AI"
            )