"""
Configuration Management

Centralized config loading for the modular system.
"""

import yaml
from pathlib import Path
from typing import Any, Dict, Optional

class ConfigManager:
    """Manages all configuration files"""
    
    def __init__(self, config_root: str = "config"):
        self.config_root = Path(config_root)
        self.global_config: Dict[str, Any] = {}
        self.module_configs: Dict[str, Dict] = {}
    
    def load_global_config(self) -> dict:
        """Load global settings"""
        settings_path = self.config_root / "settings.yaml"
        
        if settings_path.exists():
            with open(settings_path, 'r') as f:
                self.global_config = yaml.safe_load(f) or {}
        else:
            self.global_config = self._default_global_config()
        
        return self.global_config
    
    def load_module_config(self, module_name: str) -> dict:
        """Load configuration for a specific module"""
        config_path = self.config_root / "modules" / f"{module_name}.yaml"
        
        if not config_path.exists():
            raise FileNotFoundError(f"Module config not found: {config_path}")
        
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f) or {}
        
        self.module_configs[module_name] = config
        return config
    
    def get(self, path: str, default: Any = None) -> Any:
        """
        Get config value using dot notation.
        
        Examples:
            config.get('app.name')
            config.get('modules.stt.provider')
        """
        keys = path.split('.')
        value = self.global_config
        
        try:
            for key in keys:
                value = value[key]
            return value
        except (KeyError, TypeError):
            return default
    
    def _default_global_config(self) -> dict:
        """Default global configuration"""
        return {
            'app': {
                'name': 'Voice Assistant',
                'version': '3.0.0',
                'debug': False
            },
            'logging': {
                'level': 'INFO',
                'file': 'logs/assistant.log'
            }
        }

# Global instance
_config_manager = None

def get_config_manager() -> ConfigManager:
    """Get global config manager"""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
    return _config_manager

def load_global_config() -> dict:
    """Convenience function to load global config"""
    return get_config_manager().load_global_config()