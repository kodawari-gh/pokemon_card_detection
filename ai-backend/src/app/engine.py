import io
import os
import sys
import base64
import threading
from pathlib import Path
from typing import Any, Dict, List, Tuple

import cv2
import numpy as np
from PIL import Image
import torch
from ultralytics import YOLO

# --- repo paths (assumes this file is in <repo>/app/engine.py) ---
APP_DIR = Path(__file__).resolve().parent
BASE = (APP_DIR.parent).resolve()              # -> repo root (e.g., ai-backend/)
SRC = BASE / "src"                              # your src with synthgen + database
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

# --- your project imports ---
from synthgen.geom import rectify_card_from_poly_quadwise
from database.cache_manager import CacheManager  # your SQLite + pHash helpers


class InferenceEngine:
    """
    Loads YOLO seg, maintains pHash cache, and provides a process() API.
    Thread-safe predict via a simple lock (Ultralytics can be non-thread-safe).
    """
    def __init__(
        self,
        weights_path: Path,
        cache_dir: Path,
        img_db_dir: Path,
        rect_size: Tuple[int, int] = (448, 320),  # (H, W) to match portrait cards
        device: str | int | None = None,
        phash_max_distance: int = 10,
        phash_min_band_matches: int = 2,
    ) -> None:
        assert weights_path.is_file(), f"Missing weights: {weights_path}"
        self.rect_h, self.rect_w = rect_size
        self.phash_max_distance = phash_max_distance
        self.phash_min_band_matches = phash_min_band_matches

        # Choose device
        if device is None:
            device = "cuda:0" if torch.cuda.is_available() else "cpu"
        self.device = device

        # Model
        self.model = YOLO(str(weights_path))
        self._predict_lock = threading.Lock()

        # Cache + index
        self.cache = CacheManager(cache_dir)
        self.cache.build_phash_index(
            img_db_dir,
            skip_unchanged=True,
            remove_stale=False
        )

    def _pil_to_np(self, pil: Image.Image) -> np.ndarray:
        return np.array(pil.convert("RGB"))

    def _np_to_pil(self, arr: np.ndarray) -> Image.Image:
        if arr.dtype != np.uint8:
            arr = np.clip(arr, 0, 255).astype(np.uint8)
        return Image.fromarray(arr)

    def _draw_overlays(self, img_rgb: np.ndarray, polys: List[np.ndarray], labels: List[str]) -> np.ndarray:
        """
        Draw polygons and labels on image (RGB in, RGB out).
        """
        out = img_rgb.copy()
        for poly, text in zip(polys, labels):
            pts = poly.astype(np.int32).reshape((-1, 1, 2))
            cv2.polylines(out, [pts], isClosed=True, color=(0, 255, 0), thickness=2)
            cx = int(np.mean(poly[:, 0]))
            cy = int(np.mean(poly[:, 1]))
            cv2.putText(out, text, (max(0, cx - 10), max(0, cy - 10)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 50, 50), 2, cv2.LINE_AA)
        return out

    def _encode_png_b64(self, img_rgb: np.ndarray) -> str:
        bgr = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2BGR)
        ok, buf = cv2.imencode(".png", bgr)
        if not ok:
            raise RuntimeError("Failed to encode PNG")
        return base64.b64encode(buf.tobytes()).decode("ascii")

    def _extract_polys(self, yolo_result: Any) -> List[np.ndarray]:
        polys_xy: List[np.ndarray] = []
        if getattr(yolo_result, "masks", None) is not None and getattr(yolo_result.masks, "xy", None) is not None:
            for poly in yolo_result.masks.xy:
                if poly is None or len(poly) < 3:
                    continue
                polys_xy.append(np.asarray(poly, dtype=np.float32))
        elif getattr(yolo_result, "boxes", None) is not None and getattr(yolo_result.boxes, "xyxy", None) is not None:
            for (x1, y1, x2, y2) in yolo_result.boxes.xyxy.cpu().numpy():
                quad = np.array([[x1, y1], [x2, y1], [x2, y2], [x1, y2]], dtype=np.float32)
                polys_xy.append(quad)
        return polys_xy

    def _lookup_name(self, card_id: str | None) -> str | None:
        if not card_id:
            return None
        try:
            res = self.cache.search_cards_by_id(card_id)
            if not res:
                return None
            # handle both object-like and dict-like
            first = res[0]
            return getattr(first, "name", None) or first.get("name")
        except Exception:
            return None

    def process(
        self,
        image_bytes: bytes,
        *,
        conf: float = 0.25,
        iou: float = 0.5,
        base_inset: float = 0.012,
        inset_range: Tuple[float, float] = (0.008, 0.035),
        max_hits: int = 5,
        return_vis: bool = False,
    ) -> Dict[str, Any]:
        """
        Returns a dict ready to be serialized to JSON:
        {
          image_size: (H,W),
          num_detections: int,
          detections: [
            {
              polygon: [[x,y], ...],
              crop_size: (H,W),
              matches: [{set_id, card_id, distance, name}, ...]
            }, ...
          ],
          visualization_png_b64: Optional[str]
        }
        """
        pil = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        np_img = self._pil_to_np(pil)
        H, W = np_img.shape[:2]

        with self._predict_lock:
            res = self.model.predict(
                source=np_img,
                device=self.device,
                imgsz=640,
                conf=conf,
                iou=iou,
                save=False,
                verbose=False
            )[0]

        polys_xy = self._extract_polys(res)

        detections: List[Dict[str, Any]] = []
        label_texts: List[str] = []
        label_polys: List[np.ndarray] = []

        for poly in polys_xy:
            rect = rectify_card_from_poly_quadwise(
                np_img, poly,
                out_size=(self.rect_w, self.rect_h),
                base_inset=base_inset,
                inset_range=inset_range
            )
            crop_pil = self._np_to_pil(rect)
            hits = self.cache.phash_lookup(
                crop_pil,
                max_distance=self.phash_max_distance,
                min_band_matches=self.phash_min_band_matches,
                limit=max_hits
            )

            # attach human-readable name if available
            for h in hits:
                h["name"] = h.get("name") or self._lookup_name(h.get("card_id"))

            detections.append({
                "polygon": [[float(x), float(y)] for x, y in poly.tolist()],
                "crop_size": (int(rect.shape[0]), int(rect.shape[1])),
                "matches": [
                    {
                        "set_id": h.get("set_id"),
                        "card_id": h.get("card_id"),
                        "distance": int(h.get("distance", 0)),
                        "name": h.get("name") or None
                    }
                    for h in hits
                ]
            })

            top = detections[-1]["matches"][0] if detections[-1]["matches"] else None
            label = f"{top['set_id']}/{top['card_id']} d={top['distance']}" if top else "?"
            label_texts.append(label)
            label_polys.append(poly)

        out: Dict[str, Any] = {
            "image_size": (int(H), int(W)),
            "num_detections": len(detections),
            "detections": detections,
        }

        if return_vis:
            vis_rgb = self._draw_overlays(np_img, label_polys, label_texts)
            out["visualization_png_b64"] = self._encode_png_b64(vis_rgb)

        return out
