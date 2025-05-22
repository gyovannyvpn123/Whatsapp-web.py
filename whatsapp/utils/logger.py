"""
Logging setup for WhatsApp Web library.
"""

import os
import logging
from logging.handlers import RotatingFileHandler
from typing import Optional

# Global logging configuration flag
_logging_configured = False

def setup_logging(
    level: int = logging.INFO,
    log_dir: Optional[str] = None,
    max_size: int = 10 * 1024 * 1024,  # 10 MB
    backup_count: int = 3
) -> None:
    """
    Configure logging for the WhatsApp Web library
    
    Args:
        level: Logging level
        log_dir: Directory to store log files (None for no file logging)
        max_size: Maximum size of log files before rotation
        backup_count: Number of backup log files to keep
    """
    global _logging_configured
    
    if _logging_configured:
        return
        
    # Create root logger
    root_logger = logging.getLogger("whatsapp")
    root_logger.setLevel(level)
    
    # Create console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    
    # Create formatter
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    console_handler.setFormatter(formatter)
    
    # Add console handler to root logger
    root_logger.addHandler(console_handler)
    
    # Add file handler if log_dir is specified
    if log_dir:
        os.makedirs(log_dir, exist_ok=True)
        log_path = os.path.join(log_dir, "whatsapp.log")
        
        file_handler = RotatingFileHandler(
            log_path,
            maxBytes=max_size,
            backupCount=backup_count
        )
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        
        root_logger.addHandler(file_handler)
    
    _logging_configured = True

def get_logger(name: str, level: Optional[int] = None) -> logging.Logger:
    """
    Get a logger for a specific component
    
    Args:
        name: Logger name (component name)
        level: Optional specific logging level
        
    Returns:
        Logger: Configured logger
    """
    if not _logging_configured:
        setup_logging()
        
    logger = logging.getLogger(f"whatsapp.{name}")
    
    if level is not None:
        logger.setLevel(level)
        
    return logger
