"""
Ollama Provider Implementation (Local LLMs)
"""

import json
from typing import List, Optional, AsyncIterator
import httpx

from core.ai.base import (
    AIProvider, AIProviderConfig, AIMessage, AIResponse,
    AIModelCapability, AIProviderFactory
)
from utils.logger import get_logger

logger = get_logger('ai.ollama')


class OllamaProvider(AIProvider):
    """
    Ollama provider for local LLMs.
    
    Supports: Llama 3, Mistral, Phi, Gemma, etc.
    """
    
    def __init__(self, config: AIProviderConfig):
        super().__init__(config)
        
        self.capabilities = [
            AIModelCapability.TEXT_COMPLETION,
            AIModelCapability.CHAT,
            AIModelCapability.STREAMING,
            AIModelCapability.EMBEDDINGS
        ]
        
        # Ollama runs locally (default: http://localhost:11434)
        self.base_url = config.base_url or "http://localhost:11434"
        self.client = httpx.AsyncClient(base_url=self.base_url, timeout=config.timeout)
        
        logger.info(f"Ollama provider initialized (model={config.model}, url={self.base_url})")
    
    async def complete(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> AIResponse:
        """Simple completion"""
        # Build full prompt
        full_prompt = prompt
        if system_prompt:
            full_prompt = f"{system_prompt}\n\n{prompt}"
        
        try:
            response = await self.client.post(
                "/api/generate",
                json={
                    "model": self.config.model,
                    "prompt": full_prompt,
                    "stream": False,
                    "options": {
                        "temperature": temperature or self.config.temperature,
                        "num_predict": max_tokens or self.config.max_tokens
                    }
                }
            )
            
            response.raise_for_status()
            data = response.json()
            
            return AIResponse(
                content=data["response"],
                model=self.config.model,
                usage={
                    "prompt_tokens": data.get("prompt_eval_count", 0),
                    "completion_tokens": data.get("eval_count", 0),
                    "total_tokens": data.get("prompt_eval_count", 0) + data.get("eval_count", 0)
                },
                metadata={"eval_duration_ms": data.get("eval_duration", 0) / 1_000_000}
            )
        except httpx.ConnectError:
            raise ConnectionError(
                f"Cannot connect to Ollama at {self.base_url}. "
                f"Make sure Ollama is running: ollama serve"
            )
        except Exception as e:
            logger.error(f"Ollama completion error: {e}")
            raise
    
    async def chat(
        self,
        messages: List[AIMessage],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> AIResponse:
        """Multi-turn chat"""
        # Convert to Ollama format
        ollama_messages = [
            {"role": msg.role, "content": msg.content}
            for msg in messages
        ]
        
        try:
            response = await self.client.post(
                "/api/chat",
                json={
                    "model": self.config.model,
                    "messages": ollama_messages,
                    "stream": False,
                    "options": {
                        "temperature": temperature or self.config.temperature,
                        "num_predict": max_tokens or self.config.max_tokens
                    }
                }
            )
            
            response.raise_for_status()
            data = response.json()
            
            return AIResponse(
                content=data["message"]["content"],
                model=self.config.model,
                usage={
                    "prompt_tokens": data.get("prompt_eval_count", 0),
                    "completion_tokens": data.get("eval_count", 0),
                    "total_tokens": data.get("prompt_eval_count", 0) + data.get("eval_count", 0)
                },
                metadata={
                    "eval_duration_ms": data.get("eval_duration", 0) / 1_000_000,
                    "done": data.get("done", False)
                }
            )
        except httpx.ConnectError:
            raise ConnectionError(
                f"Cannot connect to Ollama at {self.base_url}. "
                f"Make sure Ollama is running: ollama serve"
            )
        except Exception as e:
            logger.error(f"Ollama chat error: {e}")
            raise
    
    async def stream_chat(
        self,
        messages: List[AIMessage],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> AsyncIterator[str]:
        """Stream chat response"""
        ollama_messages = [
            {"role": msg.role, "content": msg.content}
            for msg in messages
        ]
        
        try:
            async with self.client.stream(
                "POST",
                "/api/chat",
                json={
                    "model": self.config.model,
                    "messages": ollama_messages,
                    "stream": True,
                    "options": {
                        "temperature": temperature or self.config.temperature,
                        "num_predict": max_tokens or self.config.max_tokens
                    }
                }
            ) as response:
                async for line in response.aiter_lines():
                    if line:
                        data = json.loads(line)
                        if "message" in data:
                            content = data["message"].get("content", "")
                            if content:
                                yield content
        except httpx.ConnectError:
            raise ConnectionError(
                f"Cannot connect to Ollama at {self.base_url}. "
                f"Make sure Ollama is running: ollama serve"
            )
    
    async def embed(self, text: str) -> List[float]:
        """Generate embeddings"""
        try:
            response = await self.client.post(
                "/api/embeddings",
                json={
                    "model": self.config.model,
                    "prompt": text
                }
            )
            
            response.raise_for_status()
            data = response.json()
            return data["embedding"]
        except Exception as e:
            logger.error(f"Ollama embedding error: {e}")
            raise
    
    def get_model_info(self) -> dict:
        """Get model information"""
        return {
            "model": self.config.model,
            "provider": "ollama",
            "local": True,
            "base_url": self.base_url
        }
    
    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()


# Register provider
AIProviderFactory.register("ollama", OllamaProvider)