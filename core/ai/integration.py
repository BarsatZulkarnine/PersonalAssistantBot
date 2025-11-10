"""
AI Provider Integration Helper

Initializes AI provider from config and provides easy setup.
"""

import os
from pathlib import Path
import yaml
from typing import Optional

from core.ai import (
    AIProviderFactory,
    set_default_provider,
    get_default_provider,
    AIProvider
)
from utils.logger import get_logger

logger = get_logger('ai.integration')


def load_ai_config() -> dict:
    """Load AI configuration from config file"""
    config_path = Path("config/modules/ai.yaml")
    
    if not config_path.exists():
        logger.warning(f"AI config not found: {config_path}, using defaults")
        return {
            'provider': 'openai',
            'openai': {
                'model': 'gpt-4o-mini',
                'temperature': 0.7,
                'max_tokens': 500
            }
        }
    
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f) or {}
    
    return config


def initialize_ai_provider(provider_name: Optional[str] = None) -> AIProvider:
    """
    Initialize AI provider from config.
    
    Args:
        provider_name: Override provider from config
        
    Returns:
        AIProvider instance
    """
    config = load_ai_config()
    
    # Use override or config
    provider_name = provider_name or config.get('provider', 'openai')
    provider_config = config.get(provider_name, {})
    
    if not provider_config:
        raise ValueError(f"No configuration found for provider '{provider_name}'")
    
    # Extract settings
    model = provider_config.get('model')
    if not model:
        raise ValueError(f"No model specified for provider '{provider_name}'")
    
    # Create provider
    logger.info(f"Initializing AI provider: {provider_name}/{model}")
    
    provider = AIProviderFactory.create(
        provider_name=provider_name,
        model=model,
        api_key=provider_config.get('api_key'),
        base_url=provider_config.get('base_url'),
        temperature=provider_config.get('temperature', 0.7),
        max_tokens=provider_config.get('max_tokens', 500),
        timeout=provider_config.get('timeout', 30)
    )
    
    # Set as default
    set_default_provider(provider)
    
    logger.info(f"✓ AI provider ready: {provider_name}/{model}")
    print(f"[OK] AI Provider: {provider_name} ({model})")
    
    return provider


def get_ai_provider() -> AIProvider:
    """
    Get current AI provider (initializes if needed).
    
    Returns:
        AIProvider instance
    """
    try:
        return get_default_provider()
    except RuntimeError:
        # Not initialized yet
        return initialize_ai_provider()


# Convenience exports for backward compatibility
__all__ = [
    'initialize_ai_provider',
    'get_ai_provider',
    'load_ai_config'
]