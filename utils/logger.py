"""
Logging System

Centralized logging for all modules.
"""

import logging
import sys
import codecs
from pathlib import Path
from logging.handlers import RotatingFileHandler
from datetime import datetime

# Fix Windows console encoding for emojis
if sys.platform == 'win32':
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

class LoggerManager:
    """Manages all loggers"""
    
    _instance = None
    _loggers = {}
    _initialized = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(LoggerManager, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not self._initialized:
            self._setup_logging()
            self._initialized = True
    
    def _setup_logging(self):
        """Setup logging system"""
        # Create logs directory
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
        
        # Setup root logger
        self._setup_logger(
            'assistant',
            'logs/assistant.log',
            'INFO',
            10 * 1024 * 1024,  # 10MB
            5  # 5 backups
        )
        
        # Setup conversation logger
        conv_log = log_dir / f"conversations_{datetime.now().strftime('%Y%m%d')}.log"
        self._setup_logger(
            'conversations',
            str(conv_log),
            'INFO',
            10 * 1024 * 1024,
            5,
            simple_format=True
        )
    
    def _setup_logger(
        self,
        name: str,
        log_file: str,
        level: str,
        max_size: int,
        backup_count: int,
        simple_format: bool = False
    ):
        """Setup individual logger"""
        logger = logging.getLogger(name)
        logger.setLevel(getattr(logging, level.upper()))
        logger.handlers = []  # Clear existing
        
        # Format
        if simple_format:
            formatter = logging.Formatter(
                '%(asctime)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
        else:
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
        
        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        console_handler.setLevel(logging.WARNING)  # Only warnings and errors to console
        logger.addHandler(console_handler)
        
        # File handler with rotation
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=max_size,
            backupCount=backup_count
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        
        self._loggers[name] = logger
    
    def get_logger(self, name: str = 'assistant') -> logging.Logger:
        """Get logger instance"""
        # Create sub-logger
        full_name = f'assistant.{name}' if name != 'assistant' else name
        
        if full_name not in self._loggers:
            logger = logging.getLogger(full_name)
            logger.setLevel(logging.DEBUG)
            
            # Inherit handlers from parent if not root
            if name != 'assistant' and not logger.handlers:
                parent_logger = self._loggers.get('assistant')
                if parent_logger:
                    for handler in parent_logger.handlers:
                        logger.addHandler(handler)
            
            self._loggers[full_name] = logger
        
        return self._loggers[full_name]
    
    def log_conversation(self, user_input: str, assistant_response: str):
        """Log conversation exchange"""
        conv_logger = self.get_logger('conversations')
        conv_logger.info(f"USER: {user_input}")
        conv_logger.info(f"ASSISTANT: {assistant_response}")
        conv_logger.info("---")

# Global instance
_logger_manager = None

def get_logger(name: str = 'assistant') -> logging.Logger:
    """
    Get logger for a module.
    
    Args:
        name: Module name (e.g., 'stt.google', 'actions.lights')
        
    Returns:
        Logger instance
    """
    global _logger_manager
    if _logger_manager is None:
        _logger_manager = LoggerManager()
    return _logger_manager.get_logger(name)

def log_conversation(user_input: str, assistant_response: str):
    """Log conversation - convenience function"""
    global _logger_manager
    if _logger_manager is None:
        _logger_manager = LoggerManager()
    _logger_manager.log_conversation(user_input, assistant_response)