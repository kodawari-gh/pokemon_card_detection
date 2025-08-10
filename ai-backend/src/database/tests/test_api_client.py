"""
Tests for the Pokemon TCG API client.
"""

import sys
import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import requests

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from database.api_client import PokemonTCGClient
from database.models import Card, Set, SearchResult
from core.logging_config import get_test_logger

logger = get_test_logger(__name__)


class TestPokemonTCGClient:
    """Test suite for PokemonTCGClient."""
    
    @pytest.fixture
    def client(self):
        """Create a client instance for testing."""
        with patch('database.config.Config.validate', return_value=True):
            return PokemonTCGClient()
    
    @pytest.fixture
    def mock_card_data(self):
        """Sample card data for testing."""
        return {
            "id": "base1-1",
            "name": "Alakazam",
            "supertype": "Pokémon",
            "subtypes": ["Stage 2"],
            "hp": "80",
            "types": ["Psychic"],
            "evolves_from": "Kadabra",
            "set": {
                "id": "base1",
                "name": "Base",
                "series": "Base",
                "printedTotal": 102,
                "total": 102,
                "ptcgoCode": "BS",
                "releaseDate": "1999/01/09",
                "updatedAt": "2020/08/14 09:35:00",
                "images": {
                    "symbol": "https://example.com/symbol.png",
                    "logo": "https://example.com/logo.png"
                }
            },
            "number": "1",
            "artist": "Ken Sugimori",
            "rarity": "Rare Holo",
            "images": {
                "small": "https://example.com/small.png",
                "large": "https://example.com/large.png"
            }
        }
    
    @pytest.fixture
    def mock_set_data(self):
        """Sample set data for testing."""
        return {
            "id": "base1",
            "name": "Base",
            "series": "Base",
            "printedTotal": 102,
            "total": 102,
            "releaseDate": "1999/01/09",
            "updatedAt": "2020/08/14 09:35:00",
            "images": {
                "symbol": "https://example.com/symbol.png",
                "logo": "https://example.com/logo.png"
            }
        }
    
    def test_client_initialization(self, client):
        """Test client initialization."""
        assert client is not None
        assert client.base_url is not None
        assert client.session is not None
        assert client.headers is not None
    
    def test_make_request_success(self, client):
        """Test successful API request."""
        mock_response = Mock()
        mock_response.json.return_value = {"data": "test"}
        mock_response.raise_for_status = Mock()
        
        with patch.object(client.session, 'get', return_value=mock_response):
            result = client._make_request("test")
            assert result == {"data": "test"}
            client.session.get.assert_called_once()
    
    def test_make_request_failure(self, client):
        """Test failed API request."""
        with patch.object(client.session, 'get', 
                         side_effect=requests.RequestException("API Error")):
            with pytest.raises(requests.RequestException):
                client._make_request("test")
    
    def test_get_card_success(self, client, mock_card_data):
        """Test successful card retrieval."""
        with patch.object(client, '_make_request', 
                         return_value={"data": mock_card_data}):
            card = client.get_card("base1-1")
            
            assert card is not None
            assert isinstance(card, Card)
            assert card.id == "base1-1"
            assert card.name == "Alakazam"
            assert card.hp == "80"
    
    def test_get_card_not_found(self, client):
        """Test card not found."""
        with patch.object(client, '_make_request', return_value={}):
            card = client.get_card("invalid-id")
            assert card is None
    
    def test_get_card_error(self, client):
        """Test card retrieval error."""
        with patch.object(client, '_make_request', 
                         side_effect=Exception("API Error")):
            card = client.get_card("base1-1")
            assert card is None
    
    def test_search_cards_success(self, client, mock_card_data):
        """Test successful card search."""
        search_response = {
            "data": [mock_card_data],
            "page": 1,
            "pageSize": 250,
            "count": 1,
            "totalCount": 1
        }
        
        with patch.object(client, '_make_request', return_value=search_response):
            result = client.search_cards(query="name:Alakazam")
            
            assert isinstance(result, SearchResult)
            assert len(result.data) == 1
            assert result.data[0].name == "Alakazam"
            assert result.total_count == 1
    
    def test_search_cards_empty(self, client):
        """Test empty card search results."""
        with patch.object(client, '_make_request', 
                         return_value={"data": []}):
            result = client.search_cards(query="nonexistent")
            
            assert isinstance(result, SearchResult)
            assert len(result.data) == 0
    
    def test_search_cards_with_pagination(self, client):
        """Test card search with pagination."""
        with patch.object(client, '_make_request', return_value={"data": []}) as mock_request:
            client.search_cards(page=2, page_size=100)

            # Get the actual call arguments
            call_args = mock_request.call_args
            assert call_args is not None
            # The first argument is the endpoint string, second is the params dict
            args, kwargs = call_args
            assert args[0] == "cards"  # endpoint
            assert args[1]["page"] == 2  # params
            assert args[1]["pageSize"] == 100  # params
    
    def test_get_set_success(self, client, mock_set_data):
        """Test successful set retrieval."""
        with patch.object(client, '_make_request', 
                         return_value={"data": mock_set_data}):
            set_obj = client.get_set("base1")
            
            assert set_obj is not None
            assert isinstance(set_obj, Set)
            assert set_obj.id == "base1"
            assert set_obj.name == "Base"
    
    def test_get_all_sets(self, client, mock_set_data):
        """Test retrieving all sets."""
        with patch.object(client, '_make_request', 
                         return_value={"data": [mock_set_data]}):
            sets = client.get_all_sets()
            
            assert len(sets) == 1
            assert sets[0].id == "base1"
    
    def test_get_types(self, client):
        """Test retrieving card types."""
        types_data = ["Fire", "Water", "Grass"]
        with patch.object(client, '_make_request', 
                         return_value={"data": types_data}):
            types = client.get_types()
            
            assert len(types) == 3
            assert "Fire" in types
    
    def test_get_subtypes(self, client):
        """Test retrieving card subtypes."""
        subtypes_data = ["Basic", "Stage 1", "Stage 2"]
        with patch.object(client, '_make_request', 
                         return_value={"data": subtypes_data}):
            subtypes = client.get_subtypes()
            
            assert len(subtypes) == 3
            assert "Basic" in subtypes
    
    def test_get_supertypes(self, client):
        """Test retrieving card supertypes."""
        supertypes_data = ["Pokémon", "Trainer", "Energy"]
        with patch.object(client, '_make_request', 
                         return_value={"data": supertypes_data}):
            supertypes = client.get_supertypes()
            
            assert len(supertypes) == 3
            assert "Pokémon" in supertypes
    
    def test_get_rarities(self, client):
        """Test retrieving card rarities."""
        rarities_data = ["Common", "Uncommon", "Rare"]
        with patch.object(client, '_make_request', 
                         return_value={"data": rarities_data}):
            rarities = client.get_rarities()
            
            assert len(rarities) == 3
            assert "Rare" in rarities
    
    def test_rate_limiting(self, client):
        """Test rate limiting delay."""
        with patch('database.api_client.time.sleep') as mock_sleep:
            with patch.object(client.session, 'get', return_value=MagicMock(json=lambda: {"data": []}, raise_for_status=MagicMock())):
                client.search_cards()
                mock_sleep.assert_called_with(client.rate_limit_delay)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])