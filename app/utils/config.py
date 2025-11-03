import os
import yaml
from pathlib import Path
from typing import Any, Dict

class Config:
    """Centralized configuration manager"""
    
    _instance = None
    _config: Dict[str, Any] = {}
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Config, cls).__new__(cls)
            cls._instance._load_config()
        return cls._instance
    
    def _load_config(self):
        """Load configuration from YAML files"""
        config_dir = Path(__file__).parent.parent.parent / "config"
        
        # Load settings
        settings_path = config_dir / "settings.yaml"
        if settings_path.exists():
            with open(settings_path, 'r') as f:
                self._config['settings'] = yaml.safe_load(f)
        else:
            print(f"⚠️  Warning: {settings_path} not found, using defaults")
            self._config['settings'] = self._default_settings()
        
        # Load actions config
        actions_path = config_dir / "actions.yaml"
        if actions_path.exists():
            with open(actions_path, 'r') as f:
                self._config['actions'] = yaml.safe_load(f)
        else:
            print(f"⚠️  Warning: {actions_path} not found, using defaults")
            self._config['actions'] = self._default_actions()
    
    def _default_settings(self) -> Dict[str, Any]:
        """Default settings if config file missing"""
        return {
            'app': {'name': 'Voice Assistant', 'debug': True},
            'speech': {'hotword': 'hey pi', 'listen_timeout': 5, 'phrase_time_limit': 10},
            'tts': {'provider': 'gtts', 'language': 'en', 'streaming': False},
            'ai': {'provider': 'openai', 'model': 'gpt-4o-mini', 'temperature': 0.7},
            'logging': {'level': 'INFO', 'file': 'logs/assistant.log'}
        }
    
    def _default_actions(self) -> Dict[str, Any]:
        """Default actions if config file missing"""
        return {
            'smart_home': {'enabled': True},
            'system': {'enabled': True},
            'web': {'enabled': True},
            'conversation': {'enabled': True}
        }
    
    def get(self, path: str, default: Any = None) -> Any:
        """
        Get config value using dot notation
        Example: config.get('speech.hotword') -> 'hey pi'
        """
        keys = path.split('.')
        value = self._config
        
        try:
            for key in keys:
                value = value[key]
            return value
        except (KeyError, TypeError):
            return default
    
    def get_settings(self, key: str = None) -> Any:
        """Get settings config"""
        if key:
            return self.get(f'settings.{key}')
        return self._config.get('settings', {})
    
    def get_actions(self, key: str = None) -> Any:
        """Get actions config"""
        if key:
            return self.get(f'actions.{key}')
        return self._config.get('actions', {})
    
    def reload(self):
        """Reload configuration from files"""
        self._config = {}
        self._load_config()

# Singleton instance
config = Config()