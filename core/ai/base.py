"""
AI Provider Abstraction - Base Interface

Allows swapping between OpenAI, Ollama, LLaMA, Claude, etc. without code changes.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, AsyncIterator
from enum import Enum

class AIModelCapability(Enum):
    """What can this model do?"""
    TEXT_COMPLETION = "text_completion"
    CHAT = "chat"
    FUNCTION_CALLING = "function_calling"
    STREAMING = "streaming"
    EMBEDDINGS = "embeddings"
    VISION = "vision"

@dataclass
class AIMessage:
    """Single message in conversation"""
    role: str  # "system", "user", "assistant"
    content: str
    name: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class AIResponse:
    """Response from AI provider"""
    content: str
    model: str
    usage: Dict[str, int] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    finish_reason: Optional[str] = None

@dataclass
class AIProviderConfig:
    """Configuration for AI provider"""
    provider_name: str
    model: str
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    temperature: float = 0.7
    max_tokens: int = 500
    timeout: int = 30
    extra_params: Dict[str, Any] = field(default_factory=dict)

class AIProvider(ABC):
    """Abstract interface for AI providers"""
    
    def __init__(self, config: AIProviderConfig):
        self.config = config
        self.capabilities: List[AIModelCapability] = []
    
    @abstractmethod
    async def complete(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> AIResponse:
        """Simple completion (one-shot prompt)"""
        pass
    
    @abstractmethod
    async def chat(
        self,
        messages: List[AIMessage],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> AIResponse:
        """Multi-turn chat completion"""
        pass
    
    @abstractmethod
    async def stream_chat(
        self,
        messages: List[AIMessage],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> AsyncIterator[str]:
        """Stream chat response token-by-token"""
        pass
    
    async def embed(self, text: str) -> List[float]:
        """Generate embedding vector for text"""
        raise NotImplementedError(f"{self.config.provider_name} doesn't support embeddings")
    
    def supports(self, capability: AIModelCapability) -> bool:
        """Check if provider supports a capability"""
        return capability in self.capabilities
    
    @abstractmethod
    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the model"""
        pass
    
    def estimate_tokens(self, text: str) -> int:
        """Rough token estimate (override for accurate counting)"""
        return len(text) // 4


class AIProviderFactory:
    """Factory for creating AI providers"""
    
    _providers: Dict[str, type] = {}
    
    @classmethod
    def register(cls, name: str, provider_class: type):
        """Register a provider implementation"""
        cls._providers[name] = provider_class
    
    @classmethod
    def create(
        cls,
        provider_name: str,
        model: str,
        **kwargs
    ) -> AIProvider:
        """Create AI provider instance"""
        if provider_name not in cls._providers:
            available = ", ".join(cls._providers.keys())
            raise ValueError(
                f"Provider '{provider_name}' not found. "
                f"Available: {available}"
            )
        
        config = AIProviderConfig(
            provider_name=provider_name,
            model=model,
            **kwargs
        )
        
        provider_class = cls._providers[provider_name]
        return provider_class(config)
    
    @classmethod
    def list_providers(cls) -> List[str]:
        """List all registered providers"""
        return list(cls._providers.keys())


# Global default provider
_default_provider: Optional[AIProvider] = None

def set_default_provider(provider: AIProvider):
    """Set global default AI provider"""
    global _default_provider
    _default_provider = provider

def get_default_provider() -> AIProvider:
    """Get global default AI provider"""
    global _default_provider
    if _default_provider is None:
        raise RuntimeError(
            "No default AI provider set. Call set_default_provider() first."
        )
    return _default_provider

async def ai_complete(prompt: str, **kwargs) -> str:
    """Convenience function using default provider"""
    response = await get_default_provider().complete(prompt, **kwargs)
    return response.content

async def ai_chat(messages: List[AIMessage], **kwargs) -> str:
    """Convenience function for chat using default provider"""
    response = await get_default_provider().chat(messages, **kwargs)
    return response.content