"""
Cache management for Pokemon TCG data.
"""

import sys
import json
import pickle
import hashlib
from pathlib import Path
from datetime import datetime, timedelta
from typing import Any, Optional, List, Dict
import sqlite3
from contextlib import contextmanager

# Add parent directory to path for core imports
sys.path.insert(0, str(Path(__file__).parent.parent))
from core.logging_config import setup_logger

from .config import Config
from .models import Card, Set

logger = setup_logger(__name__)


class CacheManager:
    """Manager for caching Pokemon TCG data."""
    
    def __init__(self, cache_dir: Optional[Path] = None):
        """
        Initialize cache manager.
        
        Args:
            cache_dir: Directory for cache files
        """
        self.cache_dir = cache_dir or Config.CACHE_DIR
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize SQLite database for metadata
        self.db_path = self.cache_dir / "cache_metadata.db"
        self._init_database()
        
        logger.info(f"Cache manager initialized with directory: {self.cache_dir}")
    
    def _init_database(self):
        """Initialize the cache metadata database."""
        with self._get_db() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS cache_entries (
                    key TEXT PRIMARY KEY,
                    file_path TEXT NOT NULL,
                    created_at TIMESTAMP NOT NULL,
                    expires_at TIMESTAMP,
                    size_bytes INTEGER,
                    entry_type TEXT
                )
            """)
            conn.commit()
    
    @contextmanager
    def _get_db(self):
        """Get database connection context manager."""
        conn = sqlite3.connect(
            self.db_path,
            detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES
        )
        try:
            yield conn
        finally:
            conn.close()
    
    def _generate_key(self, prefix: str, identifier: str) -> str:
        """
        Generate a cache key.
        
        Args:
            prefix: Key prefix (e.g., 'card', 'set')
            identifier: Unique identifier
        
        Returns:
            str: Cache key
        """
        return f"{prefix}_{hashlib.md5(identifier.encode()).hexdigest()}"
    
    def _get_file_path(self, key: str, extension: str = "pkl") -> Path:
        """
        Get file path for a cache key.
        
        Args:
            key: Cache key
            extension: File extension
        
        Returns:
            Path: File path
        """
        return self.cache_dir / f"{key}.{extension}"
    
    def save_cards(self, cards: List[Card], ttl_days: int = 7) -> bool:
        """
        Save cards to cache.
        
        Args:
            cards: List of Card objects
            ttl_days: Time to live in days
        
        Returns:
            bool: Success status
        """
        try:
            key = "all_cards"
            file_path = self._get_file_path(key)
            
            # Serialize cards
            with open(file_path, "wb") as f:
                pickle.dump(cards, f)
            
            # Update metadata
            file_size = file_path.stat().st_size
            expires_at = datetime.now() + timedelta(days=ttl_days)
            
            with self._get_db() as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO cache_entries 
                    (key, file_path, created_at, expires_at, size_bytes, entry_type)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    key,
                    str(file_path),
                    datetime.now(),
                    expires_at,
                    file_size,
                    "cards"
                ))
                conn.commit()
            
            logger.info(f"Cached {len(cards)} cards (size: {file_size / 1024:.1f} KB)")
            return True
        except Exception as e:
            logger.error(f"Failed to cache cards: {e}")
            return False
    
    def load_cards(self) -> Optional[List[Card]]:
        """
        Load cards from cache.
        
        Returns:
            List of Card objects or None if not cached/expired
        """
        try:
            key = "all_cards"
            
            # Check if cache exists and is valid
            with self._get_db() as conn:
                cursor = conn.execute("""
                    SELECT file_path, expires_at FROM cache_entries
                    WHERE key = ? AND (expires_at IS NULL OR expires_at > ?)
                """, (key, datetime.now()))
                row = cursor.fetchone()
            
            if not row:
                logger.info("No valid cache found for cards")
                return None
            
            file_path = Path(row[0])
            if not file_path.exists():
                logger.warning(f"Cache file not found: {file_path}")
                return None
            
            # Load cards
            with open(file_path, "rb") as f:
                cards = pickle.load(f)
            
            logger.info(f"Loaded {len(cards)} cards from cache")
            return cards
        except Exception as e:
            logger.error(f"Failed to load cards from cache: {e}")
            return None
    
    def save_sets(self, sets: List[Set], ttl_days: int = 30) -> bool:
        """
        Save sets to cache.
        
        Args:
            sets: List of Set objects
            ttl_days: Time to live in days
        
        Returns:
            bool: Success status
        """
        try:
            key = "all_sets"
            file_path = self._get_file_path(key)
            
            # Serialize sets
            with open(file_path, "wb") as f:
                pickle.dump(sets, f)
            
            # Update metadata
            file_size = file_path.stat().st_size
            expires_at = datetime.now() + timedelta(days=ttl_days)
            
            with self._get_db() as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO cache_entries 
                    (key, file_path, created_at, expires_at, size_bytes, entry_type)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    key,
                    str(file_path),
                    datetime.now(),
                    expires_at,
                    file_size,
                    "sets"
                ))
                conn.commit()
            
            logger.info(f"Cached {len(sets)} sets (size: {file_size / 1024:.1f} KB)")
            return True
        except Exception as e:
            logger.error(f"Failed to cache sets: {e}")
            return False
    
    def load_sets(self) -> Optional[List[Set]]:
        """
        Load sets from cache.
        
        Returns:
            List of Set objects or None if not cached/expired
        """
        try:
            key = "all_sets"
            
            # Check if cache exists and is valid
            with self._get_db() as conn:
                cursor = conn.execute("""
                    SELECT file_path, expires_at FROM cache_entries
                    WHERE key = ? AND (expires_at IS NULL OR expires_at > ?)
                """, (key, datetime.now()))
                row = cursor.fetchone()
            
            if not row:
                logger.info("No valid cache found for sets")
                return None
            
            file_path = Path(row[0])
            if not file_path.exists():
                logger.warning(f"Cache file not found: {file_path}")
                return None
            
            # Load sets
            with open(file_path, "rb") as f:
                sets = pickle.load(f)
            
            logger.info(f"Loaded {len(sets)} sets from cache")
            return sets
        except Exception as e:
            logger.error(f"Failed to load sets from cache: {e}")
            return None
    
    def save_json(self, key: str, data: Dict[str, Any], ttl_days: int = 7) -> bool:
        """
        Save JSON data to cache.
        
        Args:
            key: Cache key
            data: Data to cache
            ttl_days: Time to live in days
        
        Returns:
            bool: Success status
        """
        try:
            file_path = self._get_file_path(key, "json")
            
            with open(file_path, "w") as f:
                json.dump(data, f, indent=2)
            
            # Update metadata
            file_size = file_path.stat().st_size
            expires_at = datetime.now() + timedelta(days=ttl_days)
            
            with self._get_db() as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO cache_entries 
                    (key, file_path, created_at, expires_at, size_bytes, entry_type)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    key,
                    str(file_path),
                    datetime.now(),
                    expires_at,
                    file_size,
                    "json"
                ))
                conn.commit()
            
            logger.debug(f"Cached JSON data with key: {key}")
            return True
        except Exception as e:
            logger.error(f"Failed to cache JSON data: {e}")
            return False
    
    def load_json(self, key: str) -> Optional[Dict[str, Any]]:
        """
        Load JSON data from cache.
        
        Args:
            key: Cache key
        
        Returns:
            Cached data or None if not found/expired
        """
        try:
            # Check if cache exists and is valid
            with self._get_db() as conn:
                cursor = conn.execute("""
                    SELECT file_path, expires_at FROM cache_entries
                    WHERE key = ? AND (expires_at IS NULL OR expires_at > ?)
                """, (key, datetime.now()))
                row = cursor.fetchone()
            
            if not row:
                return None
            
            file_path = Path(row[0])
            if not file_path.exists():
                return None
            
            with open(file_path, "r") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load JSON from cache: {e}")
            return None
    
    def clear_cache(self, entry_type: Optional[str] = None) -> int:
        """
        Clear cache entries.
        
        Args:
            entry_type: Type of entries to clear (None for all)
        
        Returns:
            int: Number of entries cleared
        """
        try:
            with self._get_db() as conn:
                if entry_type:
                    cursor = conn.execute(
                        "SELECT file_path FROM cache_entries WHERE entry_type = ?",
                        (entry_type,)
                    )
                else:
                    cursor = conn.execute("SELECT file_path FROM cache_entries")
                
                files = cursor.fetchall()
                
                # Delete files
                deleted = 0
                for (file_path,) in files:
                    path = Path(file_path)
                    if path.exists():
                        path.unlink()
                        deleted += 1
                
                # Clear database entries
                if entry_type:
                    conn.execute("DELETE FROM cache_entries WHERE entry_type = ?", (entry_type,))
                else:
                    conn.execute("DELETE FROM cache_entries")
                conn.commit()
            
            logger.info(f"Cleared {deleted} cache entries")
            return deleted
        except Exception as e:
            logger.error(f"Failed to clear cache: {e}")
            return 0
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.
        
        Returns:
            dict: Cache statistics
        """
        try:
            with self._get_db() as conn:
                cursor = conn.execute("""
                    SELECT 
                        COUNT(*) as total_entries,
                        SUM(size_bytes) as total_size,
                        COUNT(CASE WHEN expires_at > ? THEN 1 END) as valid_entries,
                        COUNT(CASE WHEN expires_at <= ? THEN 1 END) as expired_entries
                    FROM cache_entries
                """, (datetime.now(), datetime.now()))
                row = cursor.fetchone()
                
                stats = {
                    "total_entries": row[0] or 0,
                    "total_size_mb": (row[1] or 0) / (1024 * 1024),
                    "valid_entries": row[2] or 0,
                    "expired_entries": row[3] or 0,
                    "cache_directory": str(self.cache_dir),
                }
                
                # Get breakdown by type
                cursor = conn.execute("""
                    SELECT entry_type, COUNT(*), SUM(size_bytes)
                    FROM cache_entries
                    GROUP BY entry_type
                """)
                
                stats["by_type"] = {
                    row[0]: {
                        "count": row[1],
                        "size_mb": row[2] / (1024 * 1024) if row[2] else 0
                    }
                    for row in cursor.fetchall()
                }
                
                return stats
        except Exception as e:
            logger.error(f"Failed to get cache stats: {e}")
            return {}