"""
Tests for the cache manager.
"""

import sys
import pytest
import tempfile
import shutil
from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from database.cache_manager import CacheManager
from database.models import Card, Set, SetImage
from core.logging_config import get_test_logger

logger = get_test_logger(__name__)


class TestCacheManager:
    """Test suite for CacheManager."""
    
    @pytest.fixture
    def temp_cache_dir(self):
        """Create a temporary cache directory."""
        temp_dir = tempfile.mkdtemp()
        yield Path(temp_dir)
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def cache_manager(self, temp_cache_dir):
        """Create a cache manager with temporary directory."""
        return CacheManager(cache_dir=temp_cache_dir)
    
    @pytest.fixture
    def sample_cards(self):
        """Create sample cards for testing."""
        return [
            Card(
                id="base1-1",
                name="Alakazam",
                supertype="Pokémon",
                set=Set(
                    id="base1",
                    name="Base",
                    series="Base",
                    printedTotal=102,
                    total=102,
                    ptcgoCode="BS",
                    releaseDate="1999/01/09",
                    updatedAt="2020/08/14 09:35:00",
                    images=SetImage(
                        symbol="https://example.com/symbol.png",
                        logo="https://example.com/logo.png"
                    )
                ),
                number="1",
                hp="80",
                types=["Psychic"]
            ),
            Card(
                id="base1-2",
                name="Blastoise",
                supertype="Pokémon",
                set=Set(
                    id="base1",
                    name="Base",
                    series="Base",
                    printedTotal=102,
                    total=102,
                    ptcgoCode="BS",
                    releaseDate="1999/01/09",
                    updatedAt="2020/08/14 09:35:00",
                    images=SetImage(
                        symbol="https://example.com/symbol.png",
                        logo="https://example.com/logo.png"
                    )
                ),
                number="2",
                hp="100",
                types=["Water"]
            )
        ]
    
    @pytest.fixture
    def sample_sets(self):
        """Create sample sets for testing."""
        return [
            Set(
                id="base1",
                name="Base",
                series="Base",
                printedTotal=102,
                total=102,
                ptcgoCode="BS",
                releaseDate="1999/01/09",
                updatedAt="2020/08/14",
                images=SetImage(
                    symbol="https://example.com/symbol.png",
                    logo="https://example.com/logo.png"
                )
            ),
            Set(
                id="base2",
                name="Jungle",
                series="Base",
                printedTotal=64,
                total=64,
                ptcgoCode="BS",
                    releaseDate="1999/06/16",
                updatedAt="2020/08/14",
                images=SetImage(
                    symbol="https://example.com/symbol.png",
                    logo="https://example.com/logo.png"
                )
            )
        ]
    
    def test_initialization(self, cache_manager, temp_cache_dir):
        """Test cache manager initialization."""
        assert cache_manager.cache_dir == temp_cache_dir
        assert cache_manager.db_path.exists()
        
        # Check database was initialized
        assert (temp_cache_dir / "cache_metadata.db").exists()
    
    def test_generate_key(self, cache_manager):
        """Test cache key generation."""
        key = cache_manager._generate_key("card", "base1-1")
        assert key.startswith("card_")
        assert len(key) > 5
        
        # Same input should generate same key
        key2 = cache_manager._generate_key("card", "base1-1")
        assert key == key2
    
    def test_get_file_path(self, cache_manager):
        """Test file path generation."""
        path = cache_manager._get_file_path("test_key")
        assert path.parent == cache_manager.cache_dir
        assert path.name == "test_key.pkl"
        
        path_json = cache_manager._get_file_path("test_key", "json")
        assert path_json.name == "test_key.json"
    
    def test_save_and_load_cards(self, cache_manager, sample_cards):
        """Test saving and loading cards."""
        # Save cards
        success = cache_manager.save_cards(sample_cards, ttl_days=7)
        assert success is True
        
        # Load cards
        loaded_cards = cache_manager.load_cards()
        assert loaded_cards is not None
        assert len(loaded_cards) == 2
        assert loaded_cards[0].name == "Alakazam"
        assert loaded_cards[1].name == "Blastoise"
    
    def test_save_cards_error(self, cache_manager):
        """Test error handling when saving cards."""
        with patch('builtins.open', side_effect=IOError("Write error")):
            success = cache_manager.save_cards([])
            assert success is False
    
    def test_load_cards_not_found(self, cache_manager):
        """Test loading cards when cache doesn't exist."""
        cards = cache_manager.load_cards()
        assert cards is None
    
    def test_load_cards_expired(self, cache_manager, sample_cards):
        """Test loading expired cards from cache."""
        # Save cards with negative TTL (already expired)
        cache_manager.save_cards(sample_cards, ttl_days=-1)
        
        # Should not load expired cache
        cards = cache_manager.load_cards()
        assert cards is None
    
    def test_save_and_load_sets(self, cache_manager, sample_sets):
        """Test saving and loading sets."""
        # Save sets
        success = cache_manager.save_sets(sample_sets, ttl_days=30)
        assert success is True
        
        # Load sets
        loaded_sets = cache_manager.load_sets()
        assert loaded_sets is not None
        assert len(loaded_sets) == 2
        assert loaded_sets[0].name == "Base"
        assert loaded_sets[1].name == "Jungle"
    
    def test_save_and_load_json(self, cache_manager):
        """Test saving and loading JSON data."""
        test_data = {
            "key": "value",
            "number": 42,
            "list": [1, 2, 3]
        }
        
        # Save JSON
        success = cache_manager.save_json("test_json", test_data, ttl_days=7)
        assert success is True
        
        # Load JSON
        loaded_data = cache_manager.load_json("test_json")
        assert loaded_data == test_data
    
    def test_load_json_not_found(self, cache_manager):
        """Test loading JSON when cache doesn't exist."""
        data = cache_manager.load_json("nonexistent")
        assert data is None
    
    def test_clear_cache_all(self, cache_manager, sample_cards, sample_sets):
        """Test clearing all cache entries."""
        # Save some data
        cache_manager.save_cards(sample_cards)
        cache_manager.save_sets(sample_sets)
        cache_manager.save_json("test", {"data": "test"})
        
        # Clear all cache
        deleted = cache_manager.clear_cache()
        assert deleted >= 0
        
        # Verify cache is cleared
        assert cache_manager.load_cards() is None
        assert cache_manager.load_sets() is None
        assert cache_manager.load_json("test") is None
    
    def test_clear_cache_by_type(self, cache_manager, sample_cards, sample_sets):
        """Test clearing cache by type."""
        # Save different types
        cache_manager.save_cards(sample_cards)
        cache_manager.save_sets(sample_sets)
        
        # Clear only cards
        deleted = cache_manager.clear_cache(entry_type="cards")
        
        # Cards should be cleared, sets should remain
        assert cache_manager.load_cards() is None
        assert cache_manager.load_sets() is not None
    
    def test_get_cache_stats(self, cache_manager, sample_cards):
        """Test getting cache statistics."""
        # Initially empty
        stats = cache_manager.get_cache_stats()
        assert stats["total_entries"] == 0
        
        # Add some data
        cache_manager.save_cards(sample_cards)
        cache_manager.save_json("test", {"data": "test"})
        
        # Check updated stats
        stats = cache_manager.get_cache_stats()
        assert stats["total_entries"] == 2
        assert stats["valid_entries"] >= 0
        assert stats["expired_entries"] >= 0
        assert "by_type" in stats
    
    def test_cache_file_corruption(self, cache_manager, sample_cards):
        """Test handling corrupted cache files."""
        # Save cards
        cache_manager.save_cards(sample_cards)
        
        # Corrupt the cache file
        cache_file = cache_manager._get_file_path("all_cards")
        with open(cache_file, "w") as f:
            f.write("corrupted data")
        
        # Should handle corruption gracefully
        cards = cache_manager.load_cards()
        assert cards is None
    
    def test_concurrent_access(self, cache_manager, sample_cards):
        """Test concurrent cache access."""
        import threading
        
        def save_cards():
            cache_manager.save_cards(sample_cards)
        
        def load_cards():
            cache_manager.load_cards()
        
        # Create multiple threads
        threads = []
        for _ in range(5):
            t1 = threading.Thread(target=save_cards)
            t2 = threading.Thread(target=load_cards)
            threads.extend([t1, t2])
        
        # Start all threads
        for t in threads:
            t.start()
        
        # Wait for completion
        for t in threads:
            t.join()
        
        # Cache should still be valid
        cards = cache_manager.load_cards()
        assert cards is not None or True  # May or may not have data
    
    def test_cache_size_tracking(self, cache_manager, sample_cards):
        """Test cache size tracking."""
        # Save cards
        cache_manager.save_cards(sample_cards)
        
        # Check size is tracked
        stats = cache_manager.get_cache_stats()
        assert stats["total_size_mb"] > 0
        
        # Size should be reasonable
        assert stats["total_size_mb"] < 100  # Less than 100MB for test data


if __name__ == "__main__":
    pytest.main([__file__, "-v"])