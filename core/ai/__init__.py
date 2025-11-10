"""
AI Provider System

Abstraction layer for AI models (OpenAI, Ollama, etc.)
"""

from core.ai.base import (
    AIProvider,
    AIProviderFactory,
    AIProviderConfig,
    AIMessage,
    AIResponse,
    AIModelCapability,
    set_default_provider,
    get_default_provider,
    ai_complete,
    ai_chat
)

# Import providers to register them
from core.ai.openai_provider import OpenAIProvider
from core.ai.ollama_provider import OllamaProvider

__all__ = [
    'AIProvider',
    'AIProviderFactory',
    'AIProviderConfig',
    'AIMessage',
    'AIResponse',
    'AIModelCapability',
    'set_default_provider',
    'get_default_provider',
    'ai_complete',
    'ai_chat',
    'OpenAIProvider',
    'OllamaProvider'
]