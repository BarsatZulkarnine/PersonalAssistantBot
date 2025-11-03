import logging
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler
from datetime import datetime
from typing import Optional

class AssistantLogger:
    """Centralized logging system"""
    
    _instance = None
    _loggers = {}
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(AssistantLogger, cls).__new__(cls)
            cls._instance._setup_logging()
        return cls._instance
    
    def _setup_logging(self):
        """Setup logging configuration"""
        from app.utils.config import config
        
        # Create logs directory
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
        
        # Get config
        log_level = config.get('settings.logging.level', 'INFO')
        log_file = config.get('settings.logging.file', 'logs/assistant.log')
        max_size = config.get('settings.logging.max_size_mb', 10) * 1024 * 1024
        backup_count = config.get('settings.logging.backup_count', 5)
        
        # Setup root logger
        self._setup_logger(
            'assistant',
            log_file,
            log_level,
            max_size,
            backup_count
        )
        
        # Setup conversation logger if enabled
        if config.get('settings.logging.log_conversations', True):
            conv_log = log_dir / f"conversations_{datetime.now().strftime('%Y%m%d')}.log"
            self._setup_logger(
                'conversations',
                str(conv_log),
                'INFO',
                max_size,
                backup_count,
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
        logger.handlers = []  # Clear existing handlers
        
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
        return self._loggers.get(name, logging.getLogger(name))
    
    def log_conversation(self, user_input: str, assistant_response: str):
        """Log conversation exchange"""
        conv_logger = self.get_logger('conversations')
        conv_logger.info(f"USER: {user_input}")
        conv_logger.info(f"ASSISTANT: {assistant_response}")
        conv_logger.info("---")

# Singleton instance
logger_instance = AssistantLogger()

def get_logger(name: str = 'assistant') -> logging.Logger:
    """Get logger - convenience function"""
    return logger_instance.get_logger(name)

def log_conversation(user_input: str, assistant_response: str):
    """Log conversation - convenience function"""
    logger_instance.log_conversation(user_input, assistant_response)