"""
API client for interacting with the Pokemon TCG API.
"""

import sys
import time
import json
import zipfile
import os
from pathlib import Path
from typing import List, Optional, Dict, Any
import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

# Add parent directory to path for core imports
sys.path.insert(0, str(Path(__file__).parent.parent))
from core.logging_config import setup_logger

from .config import Config
from .models import Card, Set, SearchResult
from .cache_manager import CacheManager

logger = setup_logger(__name__)


class PokemonTCGClient:
    """Client for Pokemon TCG API interactions."""
    
    def __init__(self):
        """Initialize the API client."""
        if not Config.validate():
            raise ValueError("Invalid configuration")
        
        self.base_url = Config.API_BASE_URL
        self.headers = Config.get_headers()
        self.timeout = Config.API_TIMEOUT
        self.rate_limit_delay = Config.RATE_LIMIT_DELAY
        
        # Set up session with retry strategy
        self.session = requests.Session()
        retry_strategy = Retry(
            total=Config.MAX_RETRIES,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        self.session.headers.update(self.headers)
        
        logger.info("Pokemon TCG API client initialized")
    
    def _make_request(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Make a request to the API.
        
        Args:
            endpoint: API endpoint
            params: Query parameters
        
        Returns:
            dict: API response data
        
        Raises:
            requests.RequestException: If request fails
        """
        url = f"{self.base_url}/{endpoint}"
        
        try:
            logger.debug(f"Making request to {url} with params: {params}")
            
            # Apply rate limiting
            time.sleep(self.rate_limit_delay)

            response = self.session.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"API request failed: {e}")
            raise
    
    def get_card(self, card_id: str) -> Optional[Card]:
        """
        Get a specific card by ID.
        
        Args:
            card_id: Card ID
        
        Returns:
            Card object or None if not found
        """
        try:
            data = self._make_request(f"cards/{card_id}")
            if data and "data" in data:
                return Card(**data["data"])
            return None
        except Exception as e:
            logger.error(f"Failed to get card {card_id}: {e}")
            return None
    
    def search_cards(
        self,
        query: Optional[str] = None,
        page: int = 1,
        page_size: int = 250,
        order_by: Optional[str] = None,
        **kwargs
    ) -> SearchResult:
        """
        Search for cards.
        
        Args:
            query: Search query string
            page: Page number
            page_size: Number of results per page
            order_by: Field to order results by
            **kwargs: Additional search parameters
        
        Returns:
            SearchResult containing cards
        """
        params = {
            "page": page,
            "pageSize": min(page_size, 250),  # API max is 250
        }
        
        if query:
            params["q"] = query
        
        if order_by:
            params["orderBy"] = order_by
        
        params.update(kwargs)
        
        try:
            data = self._make_request("cards", params)
            cards = [Card(**card_data) for card_data in data.get("data", [])]
            
            return SearchResult(
                data=cards,
                page=data.get("page", page),
                page_size=data.get("pageSize", page_size),
                count=data.get("count", len(cards)),
                total_count=data.get("totalCount", 0),
            )
        except Exception as e:
            logger.error(f"Failed to search cards: {e}")
            raise e
    
    def get_set(self, set_id: str) -> Optional[Set]:
        """
        Get a specific set by ID.
        
        Args:
            set_id: Set ID
        
        Returns:
            Set object or None if not found
        """
        try:
            data = self._make_request(f"sets/{set_id}")
            if data and "data" in data:
                return Set(**data["data"])
            return None
        except Exception as e:
            logger.error(f"Failed to get set {set_id}: {e}")
            return None
    
    def get_all_sets(self) -> List[Set]:
        """
        Get all sets from the API.
        
        Returns:
            List of Set objects
        """
        try:
            data = self._make_request("sets")
            sets = [Set(**set_data) for set_data in data.get("data", [])]
            logger.info(f"Retrieved {len(sets)} sets")
            return sets
        except Exception as e:
            logger.error(f"Failed to get sets: {e}")
            return []
    
    def get_types(self) -> List[str]:
        """
        Get all card types.
        
        Returns:
            List of type names
        """
        try:
            data = self._make_request("types")
            return data.get("data", [])
        except Exception as e:
            logger.error(f"Failed to get types: {e}")
            return []
    
    def get_subtypes(self) -> List[str]:
        """
        Get all card subtypes.
        
        Returns:
            List of subtype names
        """
        try:
            data = self._make_request("subtypes")
            return data.get("data", [])
        except Exception as e:
            logger.error(f"Failed to get subtypes: {e}")
            return []
    
    def get_supertypes(self) -> List[str]:
        """
        Get all card supertypes.
        
        Returns:
            List of supertype names
        """
        try:
            data = self._make_request("supertypes")
            return data.get("data", [])
        except Exception as e:
            logger.error(f"Failed to get supertypes: {e}")
            return []
    
    def get_rarities(self) -> List[str]:
        """
        Get all card rarities.
        
        Returns:
            List of rarity names
        """
        try:
            data = self._make_request("rarities")
            return data.get("data", [])
        except Exception as e:
            logger.error(f"Failed to get rarities: {e}")
            return []