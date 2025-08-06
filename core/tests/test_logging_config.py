"""
Tests for logging configuration.
"""

import sys
import logging
import tempfile
import shutil
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import pytest
from core.logging_config import (
    setup_logger,
    get_test_logger,
    get_frontend_logger,
    get_database_logger,
    get_ai_backend_logger
)


class TestLoggingConfig:
    """Test suite for logging configuration."""
    
    @pytest.fixture
    def temp_log_dir(self):
        """Create a temporary log directory."""
        temp_dir = tempfile.mkdtemp()
        yield Path(temp_dir)
        shutil.rmtree(temp_dir)
    
    def test_setup_logger_basic(self):
        """Test basic logger setup."""
        logger = setup_logger("test_logger")
        
        assert logger is not None
        assert logger.name == "test_logger"
        assert logger.level == logging.INFO
        assert len(logger.handlers) > 0
    
    def test_setup_logger_with_level(self):
        """Test logger setup with custom level."""
        logger = setup_logger("debug_logger", level=logging.DEBUG)
        
        assert logger.level == logging.DEBUG
    
    def test_setup_logger_console_only(self, temp_log_dir):
        """Test logger with console output only."""
        logger = setup_logger(
            "console_logger",
            log_dir=str(temp_log_dir),
            console_output=True,
            file_output=False
        )
        
        # Should have only console handler
        console_handlers = [
            h for h in logger.handlers 
            if isinstance(h, logging.StreamHandler) and 
            not isinstance(h, logging.FileHandler)
        ]
        assert len(console_handlers) > 0
    
    def test_setup_logger_file_only(self, temp_log_dir):
        """Test logger with file output only."""
        logger = setup_logger(
            "file_logger",
            log_dir=str(temp_log_dir),
            console_output=False,
            file_output=True
        )
        
        # Should have file handler
        file_handlers = [
            h for h in logger.handlers 
            if hasattr(h, 'baseFilename')
        ]
        assert len(file_handlers) > 0
        
        # Check log file was created
        log_files = list(temp_log_dir.glob("*.log"))
        assert len(log_files) > 0
    
    def test_setup_logger_rotation(self, temp_log_dir):
        """Test logger with file rotation settings."""
        logger = setup_logger(
            "rotation_logger",
            log_dir=str(temp_log_dir),
            max_bytes=1024,
            backup_count=3
        )
        
        # Write enough data to trigger rotation
        for i in range(100):
            logger.info(f"Test message {i}" * 50)
        
        # Should have created log files
        log_files = list(temp_log_dir.glob("*.log*"))
        assert len(log_files) > 0
    
    def test_get_test_logger(self):
        """Test getting a test logger."""
        logger = get_test_logger("test_module")
        
        assert logger is not None
        assert logger.name == "test_module"
        assert logger.level == logging.DEBUG
    
    def test_get_frontend_logger(self):
        """Test getting frontend logger."""
        logger = get_frontend_logger()
        
        assert logger is not None
        assert logger.name == "frontend"
        assert logger.level == logging.INFO
    
    def test_get_database_logger(self):
        """Test getting database logger."""
        logger = get_database_logger()
        
        assert logger is not None
        assert logger.name == "database"
        assert logger.level == logging.INFO
    
    def test_get_ai_backend_logger(self):
        """Test getting AI backend logger."""
        logger = get_ai_backend_logger()
        
        assert logger is not None
        assert logger.name == "ai_backend"
        assert logger.level == logging.INFO
    
    def test_logger_singleton(self):
        """Test that loggers are singletons."""
        logger1 = setup_logger("singleton_test")
        logger2 = setup_logger("singleton_test")
        
        assert logger1 is logger2
    
    def test_logger_formatting(self, temp_log_dir):
        """Test logger message formatting."""
        logger = setup_logger(
            "format_test",
            log_dir=str(temp_log_dir),
            file_output=True
        )
        
        logger.info("Test message")
        logger.error("Error message")
        
        # Check log file content
        log_files = list(temp_log_dir.glob("*.log"))
        assert len(log_files) > 0
        
        with open(log_files[0], 'r') as f:
            content = f.read()
            assert "Test message" in content
            assert "Error message" in content
            assert "format_test" in content
            assert "INFO" in content
            assert "ERROR" in content
    
    def test_logger_with_exception(self, temp_log_dir):
        """Test logging exceptions."""
        logger = setup_logger(
            "exception_test",
            log_dir=str(temp_log_dir),
            file_output=True
        )
        
        try:
            raise ValueError("Test exception")
        except ValueError:
            logger.exception("Caught exception")
        
        # Check log file contains traceback
        log_files = list(temp_log_dir.glob("*.log"))
        assert len(log_files) > 0
        
        with open(log_files[0], 'r') as f:
            content = f.read()
            assert "Test exception" in content
            assert "Traceback" in content or "ValueError" in content
    
    def test_log_levels(self):
        """Test different log levels."""
        logger = setup_logger("level_test", level=logging.DEBUG)
        
        # These should all work without error
        logger.debug("Debug message")
        logger.info("Info message")
        logger.warning("Warning message")
        logger.error("Error message")
        logger.critical("Critical message")
    
    def test_log_dir_creation(self, temp_log_dir):
        """Test automatic log directory creation."""
        non_existent_dir = temp_log_dir / "new_logs"
        assert not non_existent_dir.exists()
        
        logger = setup_logger(
            "dir_test",
            log_dir=str(non_existent_dir),
            file_output=True
        )
        
        assert non_existent_dir.exists()
        assert non_existent_dir.is_dir()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])