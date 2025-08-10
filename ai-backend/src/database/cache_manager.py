import sys
import json
import sqlite3
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Tuple
from contextlib import contextmanager
from PIL import Image
import requests
from io import BytesIO
import os
from typing import Callable, Any, Optional
import requests 
from concurrent.futures import ThreadPoolExecutor, as_completed

# Add parent directory to path for core imports
sys.path.insert(0, str(Path(__file__).parent.parent))
from core.logging_config import setup_logger
from .config import Config
from .models import Card, Set

import imagehash

logger = setup_logger(__name__)


class CacheManager:
    """SQLite-backed cache manager for Pokemon TCG cards and sets."""

    def __init__(self, cache_dir: Optional[Path] = None):
        self.cache_dir = cache_dir or Config.CACHE_DIR
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        self.db_path = self.cache_dir / "cache.db"
        print(f"Absolute path: {self.db_path.absolute()}")
        self._init_database()
        logger.info(f"Cache manager initialized with database: {self.db_path}")

    def _init_database(self):
        with self._get_db() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS cards (
                    id TEXT PRIMARY KEY,
                    name TEXT,
                    set_id TEXT,
                    data TEXT NOT NULL,
                    created_at TIMESTAMP
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_cards_name ON cards(name)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_cards_set_id ON cards(set_id)")

            conn.execute("""
                CREATE TABLE IF NOT EXISTS sets (
                    id TEXT PRIMARY KEY,
                    name TEXT,
                    data TEXT NOT NULL,
                    created_at TIMESTAMP
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_sets_name ON sets(name)")
            self._ensure_phash_schema(conn) 
            conn.commit()

    @contextmanager
    def _get_db(self):
        conn = sqlite3.connect(self.db_path)
        try:
            yield conn
        finally:
            conn.close()

    def save_cards(self, cards: List[Card]) -> bool:
        try:
            with self._get_db() as conn:
                conn.execute("DELETE FROM cards")
                now = datetime.now()
                for card in cards:
                    conn.execute("""
                        INSERT INTO cards (id, name, set_id, data, created_at)
                        VALUES (?, ?, ?, ?, ?)
                    """, (
                        card.id,
                        card.name.lower(),
                        card.set.id,
                        card.json(),
                        now
                    ))
                conn.commit()
            logger.info(f"Saved {len(cards)} cards to SQLite")
            return True
        except Exception as e:
            logger.error(f"Failed to save cards: {e}")
            return False

    def save_sets(self, sets: List[Set]) -> bool:
        try:
            with self._get_db() as conn:
                conn.execute("DELETE FROM sets")
                now = datetime.now()
                for s in sets:
                    conn.execute("""
                        INSERT INTO sets (id, name, data, created_at)
                        VALUES (?, ?, ?, ?)
                    """, (
                        s.id,
                        s.name.lower(),
                        s.json(),
                        now
                    ))
                conn.commit()
            logger.info(f"Saved {len(sets)} sets to SQLite")
            return True
        except Exception as e:
            logger.error(f"Failed to save sets: {e}")
            return False

    def load_cards(self) -> Optional[List[Card]]:
        try:
            with self._get_db() as conn:
                cursor = conn.execute("SELECT data FROM cards")
                return [Card.parse_raw(row[0]) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Failed to load cards: {e}")
            return None

    def load_sets(self, sort_lambda: Callable[[Set], Any] = lambda x: x.name) -> Optional[List[Set]]:
        try:
            with self._get_db() as conn:
                cursor = conn.execute("SELECT data FROM sets")
                sets = [Set.parse_raw(row[0]) for row in cursor.fetchall()]
                sets.sort(key=sort_lambda)
                return sets
        except Exception as e:
            logger.error(f"Failed to load sets: {e}")
            return None

    def search_cards(self, query: str, sort_lambda: Callable[[Card], Any] = lambda x: x.name) -> List[Card]:
        try:
            with self._get_db() as conn:
                cursor = conn.execute(
                    "SELECT data FROM cards WHERE name LIKE ?",
                    (f"%{query.lower()}%",)
                )
                cards = [Card.parse_raw(row[0]) for row in cursor.fetchall()]
                cards.sort(key=sort_lambda)
                return cards
        except Exception as e:
            logger.error(f"Failed to search cards: {e}")
            return []

    def search_cards_by_id(self, card_id: str, sort_lambda: Callable[[Card], Any] = lambda x: x.name) -> List[Card]:
        try:
            with self._get_db() as conn:
                cursor = conn.execute("SELECT data FROM cards WHERE id = ?", (card_id,))
                cards = [Card.parse_raw(row[0]) for row in cursor.fetchall()]
                cards.sort(key=sort_lambda)
                return cards
        except Exception as e:
            logger.error(f"Failed to search cards by id: {e}")
            return []

    def search_cards_by_set(self, set_id: str, sort_lambda: Callable[[Card], Any] = lambda x: x.name) -> List[Card]:
        try:
            with self._get_db() as conn:
                cursor = conn.execute("SELECT data FROM cards WHERE set_id = ?", (set_id,))
                cards = [Card.parse_raw(row[0]) for row in cursor.fetchall()]
                cards.sort(key=sort_lambda)
                return cards
        except Exception as e:
            logger.error(f"Failed to search cards by set: {e}")
            return []

    def search_sets(self, query: str, sort_lambda: Callable[[Set], Any] = lambda x: x.name) -> List[Set]:
        try:
            with self._get_db() as conn:
                cursor = conn.execute(
                    "SELECT data FROM sets WHERE name LIKE ?",
                    (f"%{query.lower()}%",)
                )

                sets = [Set.parse_raw(row[0]) for row in cursor.fetchall()]
                sets.sort(key=sort_lambda)
                return sets
        except Exception as e:
            logger.error(f"Failed to search sets: {e}")
            return []

    def _read_cards(self, folder_path: Path, sets: List[Set]) -> List[Card]:
        cards = []
        for set_json in folder_path.glob("*.json"):
            with open(set_json, "r") as f:
                data = json.load(f)
            for card in data:
                set_obj = next((s for s in sets if s.id == set_json.stem), None)
                if not set_obj:
                    logger.warning(f"Set {set_json.name} not found")
                    continue
                card["set"] = set_obj
                cards.append(Card(**card))
        return cards

    def _read_sets(self, folder_path: Path) -> List[Set]:
        all_sets = []
        for set_json in folder_path.glob("*.json"):
            with open(set_json, "r") as f:
                data = json.load(f)
                all_sets.extend([Set(**s) for s in data])
        return all_sets

    def read_data_folder(self, folder_path: Path) -> Tuple[List[Card], List[Set]]:
        logger.info(f"Reading data from absolute path: {folder_path.absolute()}")
        cards_folder = folder_path / "cards" / "en"
        sets_folder = folder_path / "sets"
        sets = self._read_sets(sets_folder)
        cards = self._read_cards(cards_folder, sets)
        return cards, sets

    def get_card_image(self, card: Card, output_folder: Path) -> Image.Image | None:
        #check if the image is already in the database
        if os.path.exists(f"{output_folder}/{card.set.id}/{card.id}.png"):
            return Image.open(f"{output_folder}/{card.set.id}/{card.id}.png")

        # download the image from the url
        url = card.images.large if card.images else None
        if not url:
            logger.error(f"No image url found for card {card.id}")
            return None
        logger.info(f"Downloading image from {url}")
        response = requests.get(url)
        image = Image.open(BytesIO(response.content))
        #save the image to the output folder
        if not os.path.exists(f"{output_folder}/{card.set.id}"):
            os.makedirs(f"{output_folder}/{card.set.id}")
        image.save(f"{output_folder}/{card.set.id}/{card.id}.png")
        return image

    def parallel_download_images(self, cards: List[Card], output_folder: Path, max_workers: int = 16):
        def download_missing_cards(cards: List[Card], output_folder: Path):
            # check if the output folder exists and already has the same number of files as cards
            absolute_output_folder = output_folder.absolute()
            logger.info(f"Absolute output folder: {absolute_output_folder}")
            if not os.path.exists(output_folder):
                os.makedirs(output_folder)
            else:
                if len(os.listdir(output_folder)) >= len(cards):
                    logger.info(f"Output folder {output_folder} already has {len(os.listdir(output_folder))} images")
                    return

            missing_cards = []
            for card in cards:
                if not os.path.exists(os.path.join(output_folder, card.set.id, f"{card.id}.png")):
                    missing_cards.append(card)
            logger.info(f"Missing cards: {len(missing_cards)}")

            # download the missing cards
            for card in missing_cards:
                logger.debug(f"Downloading card {card.set.id}/{card.id}")
                self.get_card_image(card, output_folder)  


        session = requests.Session()
        session.headers.update({"User-Agent": "pokemon-mask-fetcher/1.0"})
        count_cards = len(cards)
        logger.info(f"Downloading {count_cards} images in parallel")
        #check if the output folder exists and already has the same number of files as cards
        # cards are in subfolders of the output folder
        folders = [f for f in os.listdir(output_folder) if os.path.isdir(os.path.join(output_folder, f))]
        count_files = sum([len(os.listdir(os.path.join(output_folder, f))) for f in folders])

        if os.path.exists(output_folder):
            if count_files == count_cards:
                logger.info(f"Output folder {output_folder} already has {count_cards} images")
                return
            elif count_cards-count_files < 100:
                logger.info(f"Output folder {output_folder} already has {count_files} images, downloading missing cards...")
                download_missing_cards(cards, output_folder)
                return

        def download_image(card):
            """Download large image for one card, save as {card.id}.png"""
            url = card.images.large
            if not url:
                logger.warning(f"No URL for {card.id}")
                return
            try:
                with session.get(url, timeout=10, stream=True) as resp:
                    resp.raise_for_status()
                    if not os.path.exists(os.path.join(output_folder, card.set.id)):
                        os.makedirs(os.path.join(output_folder, card.set.id))
                    path = os.path.join(output_folder, card.set.id , f"{card.id}.png")
                    with open(path, "wb") as f:
                        for chunk in resp.iter_content(1024 * 8):
                            if chunk:
                                f.write(chunk)
                logger.debug(f"Saved {card.id} → {path}")
            except Exception as e:
                logger.error(f"Failed {card.id}: {e}")

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(download_image, c): c for c in cards}

            for future in as_completed(futures):
                card = futures[future]
                try:
                    future.result()
                except Exception as e:
                    logger.error(f"Download thread error for {card.id}: {e}")

        # once you’re done, close the session
        session.close()
        download_missing_cards(cards, output_folder)

    # ---- pHash helpers ----------------------------------------------------------

    # --- add inside CacheManager -----------------------------------------------

    @staticmethod
    def _to_sqlite_i64(u64: int) -> int:
        """Map unsigned 64-bit -> signed 64-bit (two's complement) for SQLite."""
        return u64 if u64 < (1 << 63) else u64 - (1 << 64)

    @staticmethod
    def _from_sqlite_i64(signed: int) -> int:
        """Map signed 64-bit from SQLite back to unsigned 64-bit."""
        return signed & ((1 << 64) - 1)

    @staticmethod
    def _hamming64(a: int, b: int) -> int:
        """Hamming distance on 64-bit domain."""
        return ((a ^ b) & ((1 << 64) - 1)).bit_count()

    @staticmethod
    def _phash64(img: Image.Image) -> int:
        """64-bit perceptual hash (fast + compact)."""
        h = imagehash.phash(img, hash_size=8)   # 8x8 DCT -> 64 bits
        return int(str(h), 16)                  # ImageHash -> int via hex

    @staticmethod
    def _bands64(h: int) -> tuple[int, ...]:
        """Split 64-bit hash into eight 8-bit bands (for LSH)."""
        return tuple((h >> (8 * i)) & 0xFF for i in range(8))  # band0 = LSB

    @staticmethod
    def _hamming(a: int, b: int) -> int:
        """Hamming distance between two 64-bit ints."""
        return (a ^ b).bit_count()

    def _ensure_phash_schema(self, conn: sqlite3.Connection) -> None:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS phashes (
                card_id  TEXT PRIMARY KEY,
                set_id   TEXT,
                path     TEXT NOT NULL,
                phash    INTEGER NOT NULL,
                band0 INTEGER, band1 INTEGER, band2 INTEGER, band3 INTEGER,
                band4 INTEGER, band5 INTEGER, band6 INTEGER, band7 INTEGER,
                mtime_ns INTEGER,         
                file_size INTEGER,        
                created_at TIMESTAMP
            )
        """)
        # add missing columns if table pre-existed
        cols = {r[1] for r in conn.execute("PRAGMA table_info(phashes)")}
        if "mtime_ns" not in cols:
            conn.execute("ALTER TABLE phashes ADD COLUMN mtime_ns INTEGER")
        if "file_size" not in cols:
            conn.execute("ALTER TABLE phashes ADD COLUMN file_size INTEGER")
        for i in range(8):
            conn.execute(f"CREATE INDEX IF NOT EXISTS idx_phashes_band{i} ON phashes(band{i})")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_phashes_set ON phashes(set_id)")
        conn.commit()


    # --- replace your upsert_phash with a version that can reuse an open conn ---
    def upsert_phash(self, card_id: str, set_id: str, path: Path | str, conn: sqlite3.Connection | None = None) -> None:
        p = Path(path)
        with Image.open(p) as im:
            im = im.convert("RGB")
            h_u64 = self._phash64(im)               # 0..2^64-1
        bands = self._bands64(h_u64)
        h_i64 = self._to_sqlite_i64(h_u64)          # signed for SQLite

        owns_conn = conn is None
        if owns_conn:
            with self._get_db() as conn:
                self._ensure_phash_schema(conn)
                conn.execute("""
                    INSERT INTO phashes (card_id, set_id, path, phash,
                                        band0,band1,band2,band3,band4,band5,band6,band7, created_at)
                    VALUES (?, ?, ?, ?, ?,?,?,?,?,?,?,?, ?)
                    ON CONFLICT(card_id) DO UPDATE SET
                    set_id=excluded.set_id, path=excluded.path, phash=excluded.phash,
                    band0=excluded.band0, band1=excluded.band1, band2=excluded.band2, band3=excluded.band3,
                    band4=excluded.band4, band5=excluded.band5, band6=excluded.band6, band7=excluded.band7,
                    created_at=excluded.created_at
                """, (card_id, set_id, str(p), h_i64, *bands, datetime.now()))
                conn.commit()
        else:
            conn.execute("""
                INSERT INTO phashes (card_id, set_id, path, phash,
                                    band0,band1,band2,band3,band4,band5,band6,band7, created_at)
                VALUES (?, ?, ?, ?, ?,?,?,?,?,?,?,?, ?)
                ON CONFLICT(card_id) DO UPDATE SET
                set_id=excluded.set_id, path=excluded.path, phash=excluded.phash,
                band0=excluded.band0, band1=excluded.band1, band2=excluded.band2, band3=excluded.band3,
                band4=excluded.band4, band5=excluded.band5, band6=excluded.band6, band7=excluded.band7,
                created_at=excluded.created_at
            """, (card_id, set_id, str(p), h_i64, *bands, datetime.now()))



    # --- replace your build_phash_index with a single-connection, batched version ---
    def build_phash_index(self, images_root: Path, batch_size: int = 500,
                        skip_unchanged: bool = True, remove_stale: bool = False) -> None:
        """
        Incremental pHash indexing:
        - Skips files whose (mtime,size) match the DB.
        - Only re-hashes new/changed files.
        - Optionally removes DB rows for files no longer on disk.
        """
        images_root = Path(images_root)
        logger.info(f"Building pHash index for {images_root}")

        with self._get_db() as conn:
            self._ensure_phash_schema(conn)
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=NORMAL")
            conn.execute("PRAGMA temp_store=MEMORY")

            # Load existing fingerprints once.
            existing: dict[str, tuple[str, str, int, int]] = {}
            for cid, sid, path, mtime_ns, fsize in conn.execute(
                "SELECT card_id, set_id, path, mtime_ns, file_size FROM phashes"
            ):
                existing[cid] = (sid, path, mtime_ns or -1, fsize or -1)

            # Optional: collect current ids to detect stale rows.
            current_ids = set()

            sql = """
                INSERT INTO phashes (
                    card_id, set_id, path, phash,
                    band0,band1,band2,band3,band4,band5,band6,band7,
                    mtime_ns, file_size, created_at
                )
                VALUES (?, ?, ?, ?, ?,?,?,?,?,?,?,?, ?, ?, ?)
                ON CONFLICT(card_id) DO UPDATE SET
                    set_id=excluded.set_id, path=excluded.path, phash=excluded.phash,
                    band0=excluded.band0, band1=excluded.band1, band2=excluded.band2, band3=excluded.band3,
                    band4=excluded.band4, band5=excluded.band5, band6=excluded.band6, band7=excluded.band7,
                    mtime_ns=excluded.mtime_ns, file_size=excluded.file_size,
                    created_at=excluded.created_at
            """

            batch = []
            now = datetime.now()
            total, skipped, updated = 0, 0, 0

            for set_dir in images_root.iterdir():
                if not set_dir.is_dir():
                    continue
                for img_path in set_dir.glob("*.png"):
                    card_id = img_path.stem
                    set_id  = set_dir.name
                    current_ids.add(card_id)

                    st = img_path.stat()
                    cur_fp = (st.st_mtime_ns, st.st_size)

                    if skip_unchanged and (card_id in existing):
                        _, ex_path, ex_mtime, ex_size = existing[card_id]
                        if ex_path == str(img_path) and ex_mtime == cur_fp[0] and ex_size == cur_fp[1]:
                            skipped += 1
                            continue  # up-to-date

                    # (Re)hash only when needed
                    try:
                        with Image.open(img_path) as im:
                            h_u64 = self._phash64(im.convert("RGB"))
                        h_i64 = self._to_sqlite_i64(h_u64)
                        bands = self._bands64(h_u64)
                    except Exception as e:
                        logger.error(f"pHash index failed for {img_path}: {e}")
                        continue

                    batch.append((card_id, set_id, str(img_path), h_i64, *bands, cur_fp[0], cur_fp[1], now))
                    total += 1
                    if card_id in existing:
                        updated += 1

                    if len(batch) >= batch_size:
                        conn.executemany(sql, batch); batch.clear()

            if batch:
                conn.executemany(sql, batch)

            # Remove rows for files that disappeared (optional)
            if remove_stale:
                stale = [cid for cid in existing.keys() if cid not in current_ids]
                if stale:
                    for i in range(0, len(stale), 1000):
                        chunk = stale[i:i+1000]
                        qmarks = ",".join("?" for _ in chunk)
                        conn.execute(f"DELETE FROM phashes WHERE card_id IN ({qmarks})", chunk)
                    logger.info(f"Removed {len(stale)} stale phash rows")

            conn.commit()

        logger.info(f"pHash index complete. Rehashed {total} images "
                    f"(skipped {skipped} up-to-date, updated {updated}).")



    def phash_lookup(self,
                    img_or_path: Image.Image | str | Path,
                    max_distance: int = 8,
                    set_filter: Optional[str] = None,
                    min_band_matches: int = 1,
                    limit: int = 20):
        # 1) query hash
        if isinstance(img_or_path, (str, Path)):
            with Image.open(img_or_path) as im:
                qh = self._phash64(im.convert("RGB"))
        elif isinstance(img_or_path, Image.Image):
            qh = self._phash64(img_or_path.convert("RGB"))
        else:
            raise TypeError("img_or_path must be PIL.Image or path")

        qb = self._bands64(qh)

        # 2) shortlist by bands
        where = " OR ".join([f"band{i}=?" for i in range(8)])
        params = list(qb)
        if set_filter:
            where = f"({where}) AND set_id=?"
            params.append(set_filter)

        with self._get_db() as conn:
            # Build SQL once
            band_eq = " OR ".join([f"band{i}=?" for i in range(8)])
            sql = (
                "SELECT card_id, set_id, path, phash, "
                "( (band0=?)+(band1=?)+(band2=?)+(band3=?)+(band4=?)+(band5=?)+(band6=?)+(band7=?) ) AS band_matches "
                "FROM phashes WHERE (" + band_eq + ")"
            )
            params = [*qb, *qb]  # 8 for SELECT scoring + 8 for WHERE shortlist
            if set_filter:
                sql += " AND set_id=?"
                params.append(set_filter)

            rows = conn.execute(sql, params).fetchall()


        # 3) refine by true Hamming
        out = []
        for card_id, set_id, path, ph_signed, matches in rows:
            if matches < min_band_matches:
                continue
            ph_u64 = self._from_sqlite_i64(int(ph_signed))
            d = self._hamming64(qh, ph_u64)
            if d <= max_distance:
                out.append({"card_id": card_id, "set_id": set_id, "path": path,
                            "distance": d, "band_matches": matches})

        out.sort(key=lambda x: (x["distance"], -x["band_matches"]))
        return out[:limit]

