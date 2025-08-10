from __future__ import annotations
import argparse
from pathlib import Path
from typing import Optional, List
import json
import numpy as np
from PIL import Image
import cv2
import albumentations as A

from .config import SynthConfig
from .generator import SynthGenerator
from .utils import setup_cv2_threads, setup_logger

def _default_per_card() -> A.Compose:
    # Minimal, replace with your own `augmentation.per_card`
    return A.Compose([
        A.Rotate(limit=5, border_mode=cv2.BORDER_CONSTANT, value=(30, 30, 30), mask_value=0, p=0.8),
        A.RandomBrightnessContrast(0.05, 0.05, p=0.6),
        A.GaussianBlur(ksize=(3, 3), sigmaX=0.6, p=0.3),
    ])

def load_rgba_images(folder: Path, limit: Optional[int] = None) -> List[Image.Image]:
    exts = {".png", ".webp"}
    paths = [p for p in folder.rglob("*") if p.suffix.lower() in exts]
    if limit:
        paths = paths[:limit]
    imgs = []
    for p in paths:
        try:
            im = Image.open(p).convert("RGBA")
            imgs.append(im)
        except Exception:
            pass
    return imgs

def main():
    ap = argparse.ArgumentParser(description="Synthetic scene generator")
    ap.add_argument("--cards-dir", type=Path, required=True, help="Folder with RGBA card images")
    ap.add_argument("--background", type=Path, default=None, help="Optional background image")
    ap.add_argument("--out", type=Path, required=True, help="Output folder")
    ap.add_argument("--num", type=int, default=1, help="Number of scenes to generate")
    ap.add_argument("--limit-cards", type=int, default=None, help="Only load first N cards")
    ap.add_argument("--seed", type=int, default=None)
    ap.add_argument("--show", action="store_true", help="Show images instead of saving")
    args = ap.parse_args()

    logger = setup_logger("synthgen")
    setup_cv2_threads()

    rng = None
    if args.seed is not None:
        import random
        rng = random.Random(args.seed)

    cfg = SynthConfig()
    per_card = _default_per_card()  # Replace with your project's augmentation if desired
    gen = SynthGenerator(cfg, per_card, rng=rng)

    args.out.mkdir(parents=True, exist_ok=True)
    cards = load_rgba_images(args.cards_dir, limit=args.limit_cards)
    if not cards:
        raise SystemExit("No RGBA cards found in --cards-dir")

    bg = Image.open(args.background).convert("RGB") if args.background and args.background.exists() else None

    for i in range(1, args.num + 1):
        name = f"synthetic_{i:06d}.png"
        coco, canvas_np, _ = gen.generate_scene(bg, cards, scene_id=i, scene_name=name)
        if args.show:
            import matplotlib.pyplot as plt
            fig, ax = plt.subplots(figsize=(10, 6))
            ax.imshow(canvas_np); ax.axis("off")
            ax.set_title(name)
            plt.show()
        else:
            out_img = args.out / name
            out_json = args.out / f"{out_img.stem}.json"
            Image.fromarray(canvas_np).save(out_img)
            with open(out_json, "w", encoding="utf-8") as f:
                json.dump(coco, f)
            logger.info(f"Wrote {out_img} and {out_json}")

if __name__ == "__main__":
    main()
