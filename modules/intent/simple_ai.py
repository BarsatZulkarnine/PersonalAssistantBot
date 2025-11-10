"""
Simple AI Intent Detector - UPDATED

Now uses AI provider abstraction instead of direct OpenAI calls.
"""

from modules.intent.base import IntentDetector, IntentResult, IntentType
from core.ai.integration import get_ai_provider
from core.ai import AIMessage
from utils.logger import get_logger

logger = get_logger('intent.simple_ai')

class SimpleAiIntent(IntentDetector):
    """
    Simple AI-based intent detection using AI provider.
    
    Asks AI to classify into: AI, Web, or Action
    """
    
    def __init__(self, config: dict):
        super().__init__(config)
        
        simple_config = config.get('simple_ai', {})
        self.temperature = simple_config.get('temperature', 0.3)
        self.categories = simple_config.get('categories', ['AI', 'Web', 'Action'])
        
        # Get AI provider (initialized in orchestrator)
        self.ai_provider = get_ai_provider()
        
        logger.info(
            f"Simple AI Intent initialized "
            f"(provider={self.ai_provider.config.provider_name}, "
            f"model={self.ai_provider.config.model})"
        )
    
    async def detect(self, text: str) -> IntentResult:
        """
        Detect intent using AI provider.
        
        Returns one of: AI, Web, Action
        """
        try:
            system_prompt = """You are an intent classifier. 

Classify the user's input into ONE of these categories:

1. **AI** - General conversation, questions, explanations, jokes, opinions
   Examples: "Tell me a joke", "How are you?", "Explain quantum physics"

2. **Web** - Web search, current information, real-time data, facts that change
   Examples: "What's the weather?", "Who won the game?", "Search for Python tutorials"

3. **Action** - Execute a system action, control devices, open apps, trigger workflows
   Examples: 
   - "Turn on lights", "Set volume to 50", "Open Chrome"
   - "Play music", "Play [song name]"
   - "Test n8n", "Test webhook", "Send email", "Add to calendar"
   - "Take note", "Create task", "Slack the team"
   - "Trigger workflow", "Run automation"

CRITICAL RULES:
- ANY command with "test", "trigger", "run", "execute" + "n8n/webhook/workflow" → Action
- ANY command with "send", "create", "add", "log" + service name → Action
- ANY music control (play/pause/stop/next) → Action
- ONLY philosophical/explanatory questions about these topics → AI

Reply with ONLY ONE WORD: AI, Web, or Action

Nothing else. Just the category."""

            # Use AI provider's chat method
            messages = [
                AIMessage(role="system", content=system_prompt),
                AIMessage(role="user", content=f"Classify: {text}")
            ]
            
            response = await self.ai_provider.chat(
                messages=messages,
                temperature=self.temperature,
                max_tokens=10
            )
            
            result_text = response.content.strip().upper()
            
            # Parse result
            if "WEB" in result_text:
                intent_type = IntentType.WEB
            elif "ACTION" in result_text:
                intent_type = IntentType.ACTION
            else:
                intent_type = IntentType.AI
            
            logger.debug(f"Intent: {intent_type.value} for '{text}' (reasoning: {result_text})")
            
            return IntentResult(
                intent_type=intent_type,
                confidence=0.9,
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