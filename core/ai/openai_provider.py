"""
OpenAI Provider Implementation
"""

import os
from typing import List, Optional, AsyncIterator
from openai import AsyncOpenAI

from core.ai.base import (
    AIProvider, AIProviderConfig, AIMessage, AIResponse,
    AIModelCapability, AIProviderFactory
)
from utils.logger import get_logger

logger = get_logger('ai.openai')


class OpenAIProvider(AIProvider):
    """OpenAI API provider (GPT-4, GPT-4o-mini, etc.)"""
    
    def __init__(self, config: AIProviderConfig):
        super().__init__(config)
        
        self.capabilities = [
            AIModelCapability.TEXT_COMPLETION,
            AIModelCapability.CHAT,
            AIModelCapability.FUNCTION_CALLING,
            AIModelCapability.STREAMING,
            AIModelCapability.EMBEDDINGS,
            AIModelCapability.VISION
        ]
        
        # Initialize OpenAI client
        api_key = config.api_key or os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OpenAI API key required (set OPENAI_API_KEY)")
        
        self.client = AsyncOpenAI(
            api_key=api_key,
            base_url=config.base_url,
            timeout=config.timeout
        )
        
        logger.info(f"OpenAI provider initialized (model={config.model})")
    
    async def complete(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> AIResponse:
        """Simple completion"""
        messages = []
        
        if system_prompt:
            messages.append(AIMessage(role="system", content=system_prompt))
        
        messages.append(AIMessage(role="user", content=prompt))
        
        return await self.chat(messages, temperature, max_tokens, **kwargs)
    
    async def chat(
        self,
        messages: List[AIMessage],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> AIResponse:
        """Multi-turn chat"""
        # Convert to OpenAI format
        openai_messages = [
            {"role": msg.role, "content": msg.content}
            for msg in messages
        ]
        
        response = await self.client.chat.completions.create(
            model=self.config.model,
            messages=openai_messages,
            temperature=temperature or self.config.temperature,
            max_tokens=max_tokens or self.config.max_tokens,
            **kwargs
        )
        
        choice = response.choices[0]
        
        return AIResponse(
            content=choice.message.content,
            model=response.model,
            usage={
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens
            },
            finish_reason=choice.finish_reason
        )
    
    async def stream_chat(
        self,
        messages: List[AIMessage],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> AsyncIterator[str]:
        """Stream chat response"""
        openai_messages = [
            {"role": msg.role, "content": msg.content}
            for msg in messages
        ]
        
        stream = await self.client.chat.completions.create(
            model=self.config.model,
            messages=openai_messages,
            temperature=temperature or self.config.temperature,
            max_tokens=max_tokens or self.config.max_tokens,
            stream=True,
            **kwargs
        )
        
        async for chunk in stream:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content
    
    async def embed(self, text: str) -> List[float]:
        """Generate embeddings"""
        response = await self.client.embeddings.create(
            model="text-embedding-3-small",
            input=text
        )
        return response.data[0].embedding
    
    def get_model_info(self) -> dict:
        """Get model information"""
        model_info = {
            "gpt-4o": {"context": 128000, "cost_per_1m_tokens": 2.50},
            "gpt-4o-mini": {"context": 128000, "cost_per_1m_tokens": 0.15},
            "gpt-3.5-turbo": {"context": 16385, "cost_per_1m_tokens": 0.50}
        }
        
        return {
            "model": self.config.model,
            "provider": "openai",
            **model_info.get(self.config.model, {"context": 4096})
        }


# Register provider
AIProviderFactory.register("openai", OpenAIProvider)