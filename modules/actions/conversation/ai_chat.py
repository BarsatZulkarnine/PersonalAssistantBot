"""
AI Chat and Web Search Actions - UPDATED

Now use AI provider abstraction.
"""

# ============================================
# AI CHAT ACTION
# ============================================

from typing import List, Optional, Dict, Any
from modules.actions.base import Action, ActionResult, ActionCategory, SecurityLevel
from core.ai.integration import get_ai_provider
from core.ai import AIMessage
from utils.logger import get_logger

logger_chat = get_logger('actions.ai_chat')

class AIChatAction(Action):
    """General AI conversation with memory context support"""
    
    def __init__(self):
        super().__init__()
        self.category = ActionCategory.CONVERSATION
        self.security_level = SecurityLevel.SAFE
        self.description = "General conversation and questions with memory"
        
        # Get AI provider
        self.ai_provider = get_ai_provider()
        
        logger_chat.info(
            f"AI chat action initialized "
            f"(provider={self.ai_provider.config.provider_name}, "
            f"model={self.ai_provider.config.model})"
        )
    
    def get_intents(self) -> List[str]:
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
        """This is a fallback action"""
        return True
    
    async def execute(self, prompt: str, params: Optional[Dict[str, Any]] = None) -> ActionResult:
        logger_chat.info(f"AI chat: {prompt}")
        print(f"[AI CHAT] Processing '{prompt}'")
        
        # Extract memory context
        memory_context = ""
        if params and 'memory_context' in params:
            memory_context = params['memory_context']
            logger_chat.info(f"Using memory context ({len(memory_context)} chars)")
            print(f"[AI CHAT] Injecting memory context")
        
        try:
            # Build system prompt with memory context
            system_content = self._build_system_prompt(memory_context)
            
            # Use AI provider
            messages = [
                AIMessage(role="system", content=system_content),
                AIMessage(role="user", content=prompt)
            ]
            
            response = await self.ai_provider.chat(
                messages=messages,
                temperature=0.7,
                max_tokens=150
            )
            
            answer = response.content.strip()
            
            logger_chat.info(f"AI chat completed")
            print(f"AI CHAT: Generated response ({len(answer)} chars)")
            
            return ActionResult(
                success=True,
                message=answer,
                data={"type": "conversation", "used_memory": bool(memory_context)}
            )
            
        except Exception as e:
            logger_chat.error(f"AI chat error: {e}")
            print(f"❌ AI CHAT ERROR: {e}")
            
            return ActionResult(
                success=False,
                message="Sorry, I encountered an error."
            )
    
    def _build_system_prompt(self, memory_context: str = "") -> str:
        """Build system prompt with optional memory context"""
        base_prompt = """You are a helpful and friendly AI assistant. 
    Answer questions clearly and concisely. 
    Be conversational but informative.

    IMPORTANT: If the user asks about previous conversations or things they told you,
    check the conversation history below and reference it in your response."""
        
        if memory_context:
            base_prompt += f"""

    {memory_context}

    USE THE ABOVE INFORMATION to provide personalized, contextual responses. 
    When the user asks "what was my last question" or similar, refer to the conversation history above.
    Reference past conversations naturally when relevant."""
        else:
            base_prompt += """

    Note: No previous conversation history is available for this session yet."""
        
        return base_prompt