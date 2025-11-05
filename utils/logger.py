"""
Logging System - FIXED FOR UNICODE + CONVERSATION LOGGING

Key changes:
1. UTF-8 encoding for file handlers
2. Error handling for console output on Windows
3. Sanitizes problematic characters before logging
4. FIXED: Conversation logging now works properly
"""

import logging
import sys
import codecs
from pathlib import Path
from logging.handlers import RotatingFileHandler
from datetime import datetime

# Fix Windows console encoding for emojis
if sys.platform == 'win32':
    try:
        sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
        sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')
    except:
        pass  # If it fails, continue anyway

class SafeFormatter(logging.Formatter):
    """Formatter that handles unicode errors gracefully"""
    
    def format(self, record):
        try:
            return super().format(record)
        except UnicodeEncodeError:
            # Fallback: ASCII-safe version
            record.msg = str(record.msg).encode('ascii', 'replace').decode('ascii')
            return super().format(record)

class LoggerManager:
    """Manages all loggers with Unicode support"""
    
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
        
        # Setup conversation logger (separate file)
        conv_log = log_dir / f"conversations_{datetime.now().strftime('%Y%m%d')}.log"
        self._setup_conversation_logger(str(conv_log))
    
    def _setup_logger(
        self,
        name: str,
        log_file: str,
        level: str,
        max_size: int,
        backup_count: int,
        simple_format: bool = False
    ):
        """Setup individual logger with UTF-8 support"""
        logger = logging.getLogger(name)
        logger.setLevel(getattr(logging, level.upper()))
        logger.handlers = []  # Clear existing
        logger.propagate = False  # Don't propagate to root
        
        # Format
        if simple_format:
            formatter = SafeFormatter(
                '%(asctime)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
        else:
            formatter = SafeFormatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
        
        # Console handler with error handling
        try:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setFormatter(formatter)
            console_handler.setLevel(logging.WARNING)
            logger.addHandler(console_handler)
        except Exception as e:
            print(f"Warning: Console logging disabled ({e})")
        
        # File handler with UTF-8 encoding
        try:
            file_handler = RotatingFileHandler(
                log_file,
                maxBytes=max_size,
                backupCount=backup_count,
                encoding='utf-8'  # KEY FIX: UTF-8 encoding
            )
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
        except Exception as e:
            print(f"Warning: File logging failed ({e})")
        
        self._loggers[name] = logger
    
    def _setup_conversation_logger(self, log_file: str):
        """Setup dedicated conversation logger"""
        logger = logging.getLogger('conversations')
        logger.setLevel(logging.INFO)
        logger.handlers = []  # Clear existing
        logger.propagate = False  # Don't propagate to root
        
        # Simple format for conversations
        formatter = SafeFormatter(
            '%(asctime)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # File handler only (no console spam)
        try:
            file_handler = RotatingFileHandler(
                log_file,
                maxBytes=10 * 1024 * 1024,  # 10MB
                backupCount=30,  # Keep 30 days
                encoding='utf-8'
            )
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
            print(f"[OK] Conversation logging to: {log_file}")
        except Exception as e:
            print(f"[FAIL] Conversation logging failed: {e}")
        
        self._loggers['conversations'] = logger
    
    def get_logger(self, name: str = 'assistant') -> logging.Logger:
        """Get logger instance"""
        full_name = f'assistant.{name}' if name != 'assistant' else name
        
        if full_name not in self._loggers:
            logger = logging.getLogger(full_name)
            logger.setLevel(logging.DEBUG)
            logger.propagate = False
            
            # Use parent's handlers if available
            if name != 'assistant':
                parent_logger = self._loggers.get('assistant')
                if parent_logger and parent_logger.handlers:
                    for handler in parent_logger.handlers:
                        logger.addHandler(handler)
            
            self._loggers[full_name] = logger
        
        return self._loggers[full_name]
    
    def log_conversation(self, user_input: str, assistant_response: str):
        """
        Log conversation exchange to dedicated conversation log.
        
        Args:
            user_input: What the user said
            assistant_response: What the assistant responded
        """
        try:
            conv_logger = logging.getLogger('conversations')
            
            # Sanitize unicode characters for safety
            user_safe = self._sanitize_text(user_input)
            response_safe = self._sanitize_text(assistant_response)
            
            # Log the exchange
            conv_logger.info(f"USER: {user_safe}")
            conv_logger.info(f"ASSISTANT: {response_safe}")
            conv_logger.info("=" * 80)
            
            # Force flush to ensure it's written
            for handler in conv_logger.handlers:
                if hasattr(handler, 'flush'):
                    handler.flush()
                    
        except Exception as e:
            print(f"[WARN] Failed to log conversation: {e}")
    
    def _sanitize_text(self, text: str) -> str:
        """Replace problematic unicode characters"""
        # Replace common problematic characters
        replacements = {
            '\u2012': '-',  # Figure dash
            '\u2013': '-',  # En dash
            '\u2014': '--', # Em dash
            '\u2015': '--', # Horizontal bar
            '\u2018': "'",  # Left single quote
            '\u2019': "'",  # Right single quote
            '\u201c': '"',  # Left double quote
            '\u201d': '"',  # Right double quote
        }
        
        for old, new in replacements.items():
            text = text.replace(old, new)
        
        return text

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
    """
    Log conversation - convenience function.
    
    Args:
        user_input: What the user said
        assistant_response: What the assistant responded
    """
    global _logger_manager
    if _logger_manager is None:
        _logger_manager = LoggerManager()
    _logger_manager.log_conversation(user_input, assistant_response)