"""
Configuration management for the Pokemon TCG database module.
"""

import os
import sys
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

# Add parent directory to path for core imports
sys.path.insert(0, str(Path(__file__).parent.parent))
from core.logging_config import setup_logger

logger = setup_logger(__name__)

# Load environment variables
load_dotenv()

class Config:
    """Configuration class for database module."""
    
    # API Configuration
    API_KEY: Optional[str] = os.getenv("POKEMON_TCG_API_KEY")
    API_BASE_URL: str = os.getenv("API_BASE_URL", "https://api.pokemontcg.io/v2")
    API_TIMEOUT: int = int(os.getenv("API_TIMEOUT", "30"))
    MAX_RETRIES: int = int(os.getenv("MAX_RETRIES", "3"))
    RATE_LIMIT_DELAY: float = float(os.getenv("RATE_LIMIT_DELAY", "0.5"))
    
    # Database Configuration
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///pokemon_cards.db")
    CACHE_DIR: Path = Path(os.getenv("CACHE_DIR", "cache"))
    
    # Ensure cache directory exists
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    
    @classmethod
    def validate(cls) -> bool:
        """
        Validate configuration.
        
        Returns:
            bool: True if configuration is valid
        """
        if not cls.API_KEY:
            logger.warning(
                "No API key configured. Rate limits will be restrictive. "
                "Get your API key from https://dev.pokemontcg.io/"
            )
            return True  # API key is optional but recommended
        
        if not cls.API_BASE_URL:
            logger.error("API_BASE_URL is required")
            return False
        
        return True
    
    @classmethod
    def get_headers(cls) -> dict:
        """
        Get API request headers.
        
        Returns:
            dict: Headers for API requests
        """
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        
        if cls.API_KEY:
            headers["X-Api-Key"] = cls.API_KEY
        
        return headers