from __future__ import annotations
from pathlib import Path
from typing import List, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
from functools import lru_cache
from datetime import datetime
from PIL import Image
import json
import random
import os
import gc
import numpy as np
import cv2

from database.cache_manager import CacheManager

from synthgen.config import SynthConfig
from synthgen.generator import SynthGenerator
from synthgen.utils import setup_cv2_threads, setup_logger
from synthgen.augmentation import per_card
from synthgen.random_cards import RandomCardSampler  # your fast sampler

logger = setup_logger("pokemon-synth")

# ---------- Path anchoring (relative to THIS file) ----------
SCRIPT_DIR = Path(__file__).resolve().parent

def find_project_root(marker: str = "ai-backend") -> Path:
    """
    Walk up from this file until we find a folder named `marker`.
    Fallback to SCRIPT_DIR if not found.
    """
    for p in (SCRIPT_DIR,) + tuple(SCRIPT_DIR.parents):
        if (p / marker).is_dir():
            return p
    return SCRIPT_DIR  # sensible fallback

PROJ_ROOT = find_project_root()
logger.info(f"Project root: {PROJ_ROOT}")

CACHE_DIR       = PROJ_ROOT / "ai-backend" / "src" / "cache"
DATA_ROOT       = PROJ_ROOT / "database" / "data"
IMG_DB          = PROJ_ROOT / "ai-backend" / "src" / "image_database"
BACKGROUND_DIR  = PROJ_ROOT / "ai-backend" / "src" / "backgrounds"
OUT_DIR         = PROJ_ROOT / "ai-backend" / "dataset_generation"

IMAGE_OUTPUT_DIR = OUT_DIR / "images"
JSON_OUTPUT_DIR  = OUT_DIR / "annotations"

# ---------- helpers ----------
def ensure_images_downloaded(cache: CacheManager, cards: List, img_db: Path) -> None:
    img_db.mkdir(parents=True, exist_ok=True)
    cache.parallel_download_images(cards, img_db)

def load_card_images_parallel(cache: CacheManager, cards: List, img_db: Path, max_workers: int = 8):
    """Threaded I/O to load PIL RGBA; returns list[Image.Image]."""
    def _load(c):
        im = cache.get_card_image(c, img_db)
        return im.convert("RGBA") if im is not None else None
    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        imgs = list(ex.map(_load, cards))
    return [im for im in imgs if im is not None]

@lru_cache(maxsize=64)  # small, RAM-safe background cache
def _load_bg_cached(path_str: str) -> Image.Image:
    return Image.open(path_str).convert("RGB")

def _pil_list_to_numpy_rgba(images: List[Image.Image]) -> List[np.ndarray]:
    """Convert once per shard; free PILs after to save RAM."""
    arrs = [np.array(im, dtype=np.uint8) for im in images]  # RGBA
    return arrs

def _render_one(
    index: int,
    name: str,
    cfg: SynthConfig,
    card_images_rgba_np: List[np.ndarray],   # pre-converted NumPy RGBA (shared)
    background_paths: List[Path],            # file paths only
    image_out_dir: Path,
    json_out_dir: Path,
    seed: int | None = None,
) -> Tuple[str, int]:
    """
    Render a single sample (same semantics as your original):
      - choose a random background
      - call gen.generate_scene with the provided batch
      - save PNG and JSON with the same names/paths
    """
    rng = random.Random((seed or 0) ^ index)
    gen = SynthGenerator(cfg, per_card, rng=rng)

    bg_path = rng.choice(background_paths)
    bg = _load_bg_cached(str(bg_path))  # LRU-cached PIL.Image

    coco, scene_np, _ = gen.generate_scene(
        background_img=bg,
        card_images_rgba=card_images_rgba_np,  # already NumPy → no per-call conversion
        scene_id=index,
        scene_name=name
    )

    # Save image and JSON (same filenames as before)
    Image.fromarray(scene_np).save(image_out_dir / name)
    with open(json_out_dir / f"{name[:-4]}.json", "w", encoding="utf-8") as f:
        json.dump(coco, f)
    return (name, len(coco["annotations"]))

# ---------- main ----------
def main():
    # Keep OpenCV from oversubscribing when we also use Python threads
    setup_cv2_threads(num_threads=1, use_opencl=False)

    logger.info("Init cache...")
    cache = CacheManager(CACHE_DIR)

    # card/sets metadata (adjust to your layout)
    cards, sets = cache.read_data_folder(DATA_ROOT)
    cache.save_cards(cards); cache.save_sets(sets)

    ensure_images_downloaded(cache, cards, IMG_DB)
    cache.build_phash_index(IMG_DB)  # optional pHash index

    cfg = SynthConfig()
    sampler = RandomCardSampler(
        sets=sets,
        cache=cache,
        half_life_days=365,
        floor=0.05
    )

    IMAGE_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    JSON_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    logger.info(f"Image output directory: {IMAGE_OUTPUT_DIR.absolute()}")
    logger.info(f"JSON output directory:  {JSON_OUTPUT_DIR.absolute()}")

    background_paths = list(BACKGROUND_DIR.glob("*.png")) + \
                       list(BACKGROUND_DIR.glob("*.jpg")) + \
                       list(BACKGROUND_DIR.glob("*.jpeg"))
    if not background_paths:
        raise RuntimeError("No background images found in backgrounds/")
    logger.info(f"Found {len(background_paths)} background files")

    # Tune workers: start modest; increase if RAM allows
    WORKERS = min(max((os.cpu_count() or 4) // 2, 4), 8)  # e.g., 4–8

    total_shards = 50
    per_shard_images = 100
    batch_size_cards = 1500

    for j in range(total_shards):
        # 1) Sample cards for this shard (same logic as your code)
        random_cards = sampler.sample_cards(batch_size_cards)

        # 2) Load the images for this batch (parallelized I/O) as PIL
        #    Keep max_workers moderate to limit concurrent decode memory.
        pil_batch = load_card_images_parallel(cache, random_cards, IMG_DB, max_workers=8)
        if not pil_batch:
            raise RuntimeError("No card images found in image_database/")

        # 3) Convert ONCE to NumPy and free PIL to avoid per-render duplication
        card_images_np = _pil_list_to_numpy_rgba(pil_batch)
        pil_batch.clear()
        del pil_batch
        gc.collect()

        # 4) Render per-shard images in parallel (same filenames/JSON structure)
        jobs = []
        with ThreadPoolExecutor(max_workers=WORKERS) as pool:
            for i in range(per_shard_images):
                index = j * per_shard_images + i
                name = f"img_{index:04d}.png"
                jobs.append(pool.submit(
                    _render_one,
                    index, name, cfg, card_images_np, background_paths,
                    IMAGE_OUTPUT_DIR, JSON_OUTPUT_DIR,
                    seed=12345  # set or remove for reproducibility
                ))

            # optional: gather results (for logging)
            ann_total = 0
            for fut in as_completed(jobs):
                nm, anns = fut.result()
                ann_total += anns
        logger.info(f"[shard {j}] wrote {per_shard_images} images, total anns: {ann_total}")

        # 5) Free the NumPy batch before the next shard to keep RAM bounded
        card_images_np.clear()
        del card_images_np
        gc.collect()

if __name__ == "__main__":
    main()
