"""
Dynamic Module Loader

Loads and manages independent modules based on configuration.
"""

import importlib
from typing import Optional, Dict, Any
from pathlib import Path
import yaml

class ModuleLoader:
    """
    Loads modules dynamically based on configuration.
    Allows swapping implementations without code changes.
    """
    
    def __init__(self, config_dir: str = "config/modules"):
        self.config_dir = Path(config_dir)
        self.loaded_modules: Dict[str, Any] = {}
    
    def load_config(self, module_name: str) -> dict:
        """
        Load configuration for a module.
        
        Args:
            module_name: Name of module (e.g., 'stt', 'tts')
            
        Returns:
            Configuration dictionary
        """
        config_path = self.config_dir / f"{module_name}.yaml"
        
        if not config_path.exists():
            raise FileNotFoundError(f"Config not found: {config_path}")
        
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
    
    def load_module(self, module_type: str, provider: Optional[str] = None) -> Any:
        """
        Load a module dynamically.
        
        Args:
            module_type: Type of module ('stt', 'tts', 'intent', etc.)
            provider: Specific provider to load (or read from config)
            
        Returns:
            Instantiated module
            
        Example:
            stt = loader.load_module('stt')  # Loads Google STT
            stt = loader.load_module('stt', 'whisper')  # Loads Whisper
        """
        # Load config
        config = self.load_config(module_type)
        
        # Get provider from config if not specified
        if provider is None:
            provider = config.get('provider')
        
        if not provider:
            raise ValueError(f"No provider specified for {module_type}")
        
        # Build module path
        # modules.stt.google -> GoogleSTT
        module_path = f"modules.{module_type}.{provider}"
        class_name = self._get_class_name(provider, module_type)
        
        try:
            # Import module
            module = importlib.import_module(module_path)
            
            # Get class
            provider_class = getattr(module, class_name)
            
            # Instantiate with config
            instance = provider_class(config)
            
            # Cache
            cache_key = f"{module_type}:{provider}"
            self.loaded_modules[cache_key] = instance
            
            return instance
            
        except ImportError as e:
            raise ImportError(
                f"Failed to import {module_path}: {e}\n"
                f"Make sure {provider}.py exists in modules/{module_type}/"
            )
        except AttributeError as e:
            raise AttributeError(
                f"Class {class_name} not found in {module_path}: {e}"
            )
    
    def get_module(self, module_type: str, provider: Optional[str] = None) -> Optional[Any]:
        """
        Get cached module or load it.
        
        Args:
            module_type: Type of module
            provider: Optional provider name
            
        Returns:
            Module instance or None
        """
        if provider is None:
            config = self.load_config(module_type)
            provider = config.get('provider')
        
        cache_key = f"{module_type}:{provider}"
        
        if cache_key in self.loaded_modules:
            return self.loaded_modules[cache_key]
        
        return self.load_module(module_type, provider)
    
    def _get_class_name(self, provider: str, module_type: str) -> str:
        """
        Convert provider name to class name.
        
        Examples:
            'google' + 'stt' -> 'GoogleSTT'
            'gtts' + 'tts' -> 'GTTS'
            'simple_ai' + 'intent' -> 'SimpleAIIntent'
            'simple' + 'wake_word' -> 'SimpleWakeWord'
        """
        # Special cases
        if provider == 'gtts':
            return 'GTTS'
        
        # Convert snake_case to PascalCase
        parts = provider.split('_')
        class_name = ''.join(word.capitalize() for word in parts)
        
        # Add module type suffix
        if module_type == 'stt':
            class_name += 'STT'
        elif module_type == 'tts':
            if provider == 'openai_tts':
                return 'OpenAITTS'
            class_name += 'TTS' if not class_name.endswith('TTS') else ''
        elif module_type == 'intent':
            class_name += 'Intent'
        elif module_type == 'wake_word':
            class_name += 'WakeWord'
        
        return class_name
    
    def reload_module(self, module_type: str, provider: Optional[str] = None):
        """
        Reload a module (useful for config changes).
        
        Args:
            module_type: Type of module
            provider: Optional provider name
        """
        if provider is None:
            config = self.load_config(module_type)
            provider = config.get('provider')
        
        cache_key = f"{module_type}:{provider}"
        
        # Remove from cache
        if cache_key in self.loaded_modules:
            del self.loaded_modules[cache_key]
        
        # Reload
        return self.load_module(module_type, provider)
    
    def list_available_providers(self, module_type: str) -> list:
        """
        List available providers for a module type.
        
        Args:
            module_type: Type of module
            
        Returns:
            List of provider names
        """
        module_dir = Path(f"modules/{module_type}")
        
        if not module_dir.exists():
            return []
        
        providers = []
        for file in module_dir.glob("*.py"):
            if file.name not in ['__init__.py', 'base.py']:
                providers.append(file.stem)
        
        return providers

# Global instance
_loader = None

def get_module_loader() -> ModuleLoader:
    """Get global module loader instance"""
    global _loader
    if _loader is None:
        _loader = ModuleLoader()
    return _loader