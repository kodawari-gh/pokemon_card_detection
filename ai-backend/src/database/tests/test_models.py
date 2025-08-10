"""
Tests for database models.
"""

import sys
import pytest
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from database.models import (
    Card, Set, Attack, Ability,
    CardImage, SetImage, SearchResult
)
from core.logging_config import get_test_logger

logger = get_test_logger(__name__)


class TestCardModel:
    """Test suite for Card model."""
    
    @pytest.fixture
    def card_data(self):
        """Sample card data."""
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
            },
            "attacks": [{
                "name": "Confuse Ray",
                "cost": ["Psychic", "Psychic", "Psychic"],
                "convertedEnergyCost": 3,
                "damage": "30",
                "text": "Flip a coin. If heads, the Defending Pokémon is now Confused."
            }],
            "weaknesses": [{
                "type": "Psychic",
                "value": "×2"
            }],
            "retreatCost": ["Colorless", "Colorless", "Colorless"],
            "convertedRetreatCost": 3
        }
    
    def test_card_creation(self, card_data):
        """Test creating a card from data."""
        card = Card(**card_data)
        
        assert card.id == "base1-1"
        assert card.name == "Alakazam"
        assert card.supertype == "Pokémon"
        assert "Stage 2" in card.subtypes
        assert card.hp == "80"
        assert "Psychic" in card.types
        assert card.evolves_from == "Kadabra"
        assert card.set.id == "base1"
        assert card.number == "1"
        assert card.artist == "Ken Sugimori"
        assert card.rarity == "Rare Holo"
    
    def test_card_full_name(self, card_data):
        """Test card full name property."""
        card = Card(**card_data)
        assert card.full_name == "Alakazam (base1 1)"
    
    def test_card_image_urls(self, card_data):
        """Test card image URL properties."""
        card = Card(**card_data)
        assert card.image_url == "https://example.com/large.png"
        assert card.small_image_url == "https://example.com/small.png"
    
    def test_card_without_images(self):
        """Test card without images."""
        card = Card(
            id="test-1",
            name="Test Card",
            supertype="Pokémon",
            set=Set(
                id="test",
                name="Test",
                series="Test",
                printedTotal=10,
                total=10,
                ptcgoCode="BS",
                releaseDate="1999/01/09",
                updatedAt="2020/08/14 09:35:00",
                images=SetImage(
                    symbol="https://example.com/symbol.png",
                    logo="https://example.com/logo.png"
                )
            ),
            number="1"
        )
        assert card.image_url is None
        assert card.small_image_url is None
    
    def test_card_attacks(self, card_data):
        """Test card attacks."""
        card = Card(**card_data)
        assert len(card.attacks) == 1
        
        attack = card.attacks[0]
        assert attack.name == "Confuse Ray"
        assert len(attack.cost) == 3
        assert attack.damage == "30"
    
    def test_card_weaknesses(self, card_data):
        """Test card weaknesses."""
        card = Card(**card_data)
        assert len(card.weaknesses) == 1
        
        weakness = card.weaknesses[0]
        assert weakness.type == "Psychic"
        assert weakness.value == "×2"
    
    def test_card_minimal_data(self):
        """Test card with minimal required data."""
        card = Card(
            id="test-1",
            name="Test",
            supertype="Pokémon",
            set=Set(
                id="test",
                name="Test",
                series="Test",
                printedTotal=10,
                total=10,
                ptcgoCode="BS",
                releaseDate="1999/01/09",
                updatedAt="2020/08/14 09:35:00",
                images=SetImage(
                    symbol="https://example.com/symbol.png",
                    logo="https://example.com/logo.png"
                )
            ),
            number="1"
        )
        
        assert card.id == "test-1"
        assert card.name == "Test"
        assert len(card.types) == 0
        assert len(card.attacks) == 0
        assert card.hp is None


class TestSetModel:
    """Test suite for Set model."""
    
    @pytest.fixture
    def set_data(self):
        """Sample set data."""
        return {
            "id": "base1",
            "name": "Base",
            "series": "Base",
            "printedTotal": 102,
            "total": 102,
            "legalities": {
                "unlimited": "Legal",
                "expanded": "Legal"
            },
            "ptcgoCode": "BS",
            "releaseDate": "1999/01/09",
            "updatedAt": "2020/08/14 09:35:00",
            "images": {
                "symbol": "https://example.com/symbol.png",
                "logo": "https://example.com/logo.png"
            }
        }
    
    def test_set_creation(self, set_data):
        """Test creating a set from data."""
        set_obj = Set(**set_data)
        
        assert set_obj.id == "base1"
        assert set_obj.name == "Base"
        assert set_obj.series == "Base"
        assert set_obj.printedTotal == 102
        assert set_obj.total == 102
        assert set_obj.ptcgo_code == "BS"
        assert set_obj.release_date == "1999/01/09"
    
    def test_set_release_datetime(self, set_data):
        """Test set release datetime property."""
        set_obj = Set(**set_data)
        release_dt = set_obj.release_datetime
        
        assert isinstance(release_dt, datetime)
        assert release_dt.year == 1999
        assert release_dt.month == 1
        assert release_dt.day == 9
    
    def test_set_image_urls(self, set_data):
        """Test set image URL properties."""
        set_obj = Set(**set_data)
        assert set_obj.symbol_url == "https://example.com/symbol.png"
        assert set_obj.logo_url == "https://example.com/logo.png"

    
    def test_set_legalities(self, set_data):
        """Test set legalities."""
        set_obj = Set(**set_data)
        assert set_obj.legalities is not None
        assert set_obj.legalities.unlimited == "Legal"
        assert set_obj.legalities.expanded == "Legal"


class TestAttackModel:
    """Test suite for Attack model."""
    
    def test_attack_creation(self):
        """Test creating an attack."""
        attack = Attack(
            name="Thunder Shock",
            cost=["Lightning"],
            converted_energy_cost=1,
            damage="10",
            text="Flip a coin. If heads, the Defending Pokémon is now Paralyzed."
        )
        
        assert attack.name == "Thunder Shock"
        assert len(attack.cost) == 1
        assert attack.converted_energy_cost == 1
        assert attack.damage == "10"
    
    def test_attack_minimal(self):
        """Test attack with minimal data."""
        attack = Attack(name="Quick Attack")
        assert attack.name == "Quick Attack"
        assert len(attack.cost) == 0
        assert attack.damage == ""


class TestAbilityModel:
    """Test suite for Ability model."""
    
    def test_ability_creation(self):
        """Test creating an ability."""
        ability = Ability(
            name="Damage Swap",
            text="As often as you like during your turn...",
            type="Pokémon Power"
        )
        
        assert ability.name == "Damage Swap"
        assert ability.text.startswith("As often as")
        assert ability.type == "Pokémon Power"


class TestSearchResultModel:
    """Test suite for SearchResult model."""
    
    def test_search_result_creation(self):
        """Test creating a search result."""
        cards = [
            Card(id="1", name="Card1", supertype="Pokémon", set=Set(id="test", name="Test", series="Test", printedTotal=10, total=10, ptcgoCode="BS", releaseDate="1999/01/09", updatedAt="2020/08/14 09:35:00", images=SetImage(symbol="https://example.com/symbol.png", logo="https://example.com/logo.png")), number="1"),
            Card(id="2", name="Card2", supertype="Pokémon", set=Set(id="test", name="Test", series="Test", printedTotal=10, total=10, ptcgoCode="BS", releaseDate="1999/01/09", updatedAt="2020/08/14 09:35:00", images=SetImage(symbol="https://example.com/symbol.png", logo="https://example.com/logo.png")), number="2")
        ]
        
        result = SearchResult(
            data=cards,
            page=1,
            page_size=250,
            count=2,
            total_count=100
        )
        
        assert len(result.data) == 2
        assert result.page == 1
        assert result.page_size == 250
        assert result.count == 2
        assert result.total_count == 100
    
    def test_search_result_defaults(self):
        """Test search result with default values."""
        result = SearchResult(data=[])
        
        assert len(result.data) == 0
        assert result.page == 1
        assert result.page_size == 250
        assert result.count == 0
        assert result.total_count == 0


class TestCardImageModel:
    """Test suite for CardImage model."""
    
    def test_card_image_creation(self):
        """Test creating card images."""
        images = CardImage(
            small="https://example.com/small.png",
            large="https://example.com/large.png"
        )
        
        assert images.small == "https://example.com/small.png"
        assert images.large == "https://example.com/large.png"


class TestModelValidation:
    """Test model validation and edge cases."""
    
    def test_card_strip_whitespace(self):
        """Test that card fields strip whitespace."""
        card = Card(
            id="  test-1  ",
            name="  Test Card  ",
            supertype="  Pokémon  ",
            set=Set(id="test", name="Test", series="Test", printedTotal=10, total=10, ptcgoCode="BS", releaseDate="1999/01/09", updatedAt="2020/08/14 09:35:00", images=SetImage(symbol="https://example.com/symbol.png", logo="https://example.com/logo.png")),
            number="1"
        )
        
        assert card.id == "test-1"
        assert card.name == "Test Card"
        assert card.supertype == "Pokémon"
    
    def test_card_empty_lists(self):
        """Test card with empty list fields."""
        card = Card(
            id="test-1",
            name="Test",
            supertype="Pokémon",
            set=Set(id="test", name="Test", series="Test", printedTotal=10, total=10, ptcgoCode="BS", releaseDate="1999/01/09", updatedAt="2020/08/14 09:35:00", images=SetImage(symbol="https://example.com/symbol.png", logo="https://example.com/logo.png")),
            number="1",
            types=[],
            subtypes=[],
            attacks=[],
            abilities=[]
        )
        
        assert len(card.types) == 0
        assert len(card.subtypes) == 0
        assert len(card.attacks) == 0
        assert len(card.abilities) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])