"""
AI Chat Action - WITH MEMORY CONTEXT INJECTION

General conversation with AI, now with memory context!
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
    """General AI conversation with memory context support"""
    
    def __init__(self):
        super().__init__()
        self.category = ActionCategory.CONVERSATION
        self.security_level = SecurityLevel.SAFE
        self.description = "General conversation and questions with memory"
        self.client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        
        # NEW: Store memory context for this request
        self.current_context = ""
        
        logger.info("AI chat action initialized (with memory support)")
    
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
        print(f"[AI CHAT] Processing '{prompt}'")
        
        # NEW: Extract memory context from params if provided
        memory_context = ""
        if params and 'memory_context' in params:
            memory_context = params['memory_context']
            logger.info(f"Using memory context ({len(memory_context)} chars)")
            print(f"[AI CHAT] Injecting memory context")
        
        try:
            # Build system prompt with optional memory context
            system_content = self._build_system_prompt(memory_context)
            
            response = await self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_content},
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
                data={"type": "conversation", "used_memory": bool(memory_context)}
            )
            
        except Exception as e:
            logger.error(f"AI chat error: {e}")
            print(f"❌ AI CHAT ERROR: {e}")
            
            return ActionResult(
                success=False,
                message="Sorry, I encountered an error."
            )
    
    def _build_system_prompt(self, memory_context: str = "") -> str:
        """
        Build system prompt with optional memory context.
        
        Args:
            memory_context: Retrieved memory context
            
        Returns:
            System prompt string
        """
        base_prompt = """You are a helpful and friendly AI assistant. 
Answer questions clearly and concisely. 
Be conversational but informative."""
        
        # NEW: Inject memory context if available
        if memory_context:
            base_prompt += f"""

{memory_context}

Use the above information to provide personalized, contextual responses. 
Reference past conversations naturally when relevant.
If the user asks about something in memory, answer based on what you know."""
        
        return base_prompt