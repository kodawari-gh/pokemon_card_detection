"""
Centralized logging configuration for the Pokemon Card Detection application.
Provides consistent logging format and handlers across all modules.
"""

import logging
import logging.handlers
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional


def setup_logger(
    name: str,
    level: int = logging.INFO,
    log_dir: Optional[str] = None,
    console_output: bool = True,
    file_output: bool = True,
    max_bytes: int = 10485760,  # 10MB
    backup_count: int = 5
) -> logging.Logger:
    """
    Configure and return a logger with both console and file handlers.
    
    Args:
        name: Logger name, typically __name__ of the calling module
        level: Logging level (default: INFO)
        log_dir: Directory for log files (default: logs/)
        console_output: Enable console output
        file_output: Enable file output
        max_bytes: Maximum size of log file before rotation
        backup_count: Number of backup files to keep
    
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # Prevent duplicate handlers
    if logger.handlers:
        return logger
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Console handler
    if console_output:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
    
    # File handler with rotation
    if file_output:
        if log_dir is None:
            log_dir = Path(__file__).parent.parent / 'logs'
        else:
            log_dir = Path(log_dir)
        
        log_dir.mkdir(parents=True, exist_ok=True)
        
        # Create log file name with timestamp
        log_file = log_dir / f"{name.replace('.', '_')}_{datetime.now().strftime('%Y%m%d')}.log"
        
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=max_bytes,
            backupCount=backup_count
        )
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger


def get_test_logger(name: str) -> logging.Logger:
    """
    Get a logger configured specifically for testing.
    
    Args:
        name: Logger name
    
    Returns:
        Logger configured for testing with DEBUG level
    """
    return setup_logger(
        name,
        level=logging.DEBUG,
        log_dir='test_logs',
        console_output=True,
        file_output=True
    )


# Module-specific logger configurations
def get_frontend_logger() -> logging.Logger:
    """Get logger for frontend module."""
    return setup_logger('frontend', level=logging.INFO)


def get_database_logger() -> logging.Logger:
    """Get logger for database module."""
    return setup_logger('database', level=logging.INFO)


def get_ai_backend_logger() -> logging.Logger:
    """Get logger for AI backend module."""
    return setup_logger('ai_backend', level=logging.INFO)