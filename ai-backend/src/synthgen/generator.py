from __future__ import annotations
import random
from typing import List, Tuple, Optional, Dict, Any
import numpy as np
import cv2
from PIL import Image
import albumentations as A

from .config import SynthConfig
from .canvas import make_canvas_from_image_np
from .geom import mask_to_poly, rectify_card_from_poly
from .utils import center_biased_uniform

class SynthGenerator:
    """
    Reusable synthetic scene generator. Thread-safe if called with separate instances.
    """
    def __init__(self,
                 cfg: SynthConfig,
                 per_card_aug: A.Compose,
                 rng: random.Random | None = None):
        self.cfg = cfg
        self.per_card = per_card_aug
        self.rng = rng or random

    @staticmethod
    def pil_rgba_to_numpy_rgba(images: List[Image.Image]) -> List[np.ndarray]:
        return [np.array(im.convert("RGBA")) for im in images]

    def _paste_with_clip_np(self,
                            canvas_rgb: np.ndarray,
                            src_rgb: np.ndarray,
                            mask_u8: np.ndarray,
                            px: int, py: int,
                            occ: Optional[np.ndarray] = None,
                            card_id: Optional[int] = None,
                            commit: bool = True) -> Tuple[bool, int, int, Optional[np.ndarray]]:
        Hc, Wc = canvas_rgb.shape[:2]
        total_pos = int((mask_u8 > 0).sum())
        if total_pos == 0:
            return False, px, py, None

        h, w = mask_u8.shape
        x0, y0, x1, y1 = px, py, px + w, py + h
        ix0, iy0 = max(0, x0), max(0, y0)
        ix1, iy1 = min(Wc, x1), min(Hc, y1)
        if ix1 <= ix0 or iy1 <= iy0:
            return False, px, py, None

        cfgs = self.cfg.scene
        plc = self.cfg.placement

        sx0, sy0 = ix0 - x0, iy0 - y0
        sx1, sy1 = sx0 + (ix1 - ix0), sy0 + (iy1 - iy0)

        src_crop  = src_rgb[sy0:sy1, sx0:sx1]
        mask_crop = mask_u8[sy0:sy1, sx0:sx1]
        mpos = (mask_crop > 0)

        inbounds_ratio = mpos.sum() / float(total_pos)
        if inbounds_ratio < cfgs.min_inbounds_frac:
            return False, px, py, None

        vis = mpos.sum() / float(mask_crop.size)
        if vis < cfgs.min_visible_frac:
            return False, px, py, None

        if occ is not None:
            occ_roi = occ[iy0:iy1, ix0:ix1]
            overlap = (mpos & (occ_roi > 0)).sum() / max(1, mpos.sum())
            if overlap > plc.max_overlap_frac_new:
                return False, px, py, None

        if not commit:
            return True, ix0, iy0, mask_crop

        dst_roi = canvas_rgb[iy0:iy1, ix0:ix1]
        alpha = (mask_crop.astype(np.float32) / 255.0)[..., None]
        blended = src_crop.astype(np.float32) * alpha + dst_roi.astype(np.float32) * (1.0 - alpha)
        canvas_rgb[iy0:iy1, ix0:ix1] = blended.astype(np.uint8)

        if occ is not None and card_id is not None:
            occ_roi = occ[iy0:iy1, ix0:ix1]
            occ_roi[mpos] = int(card_id)

        return True, ix0, iy0, mask_crop

    def _generate_warped_image(self,
                               card_rgba_list: List[np.ndarray],
                               canvas_rgb: np.ndarray,
                               x: int, y: int,
                               tile_w: int, tile_h: int,
                               occ: np.ndarray,
                               card_id: int) -> Optional[Tuple[np.ndarray, int, int]]:
        sc = self.cfg.scale
        sconf = self.cfg.scene

        rgba = self.rng.choice(card_rgba_list)  # HxWx4 uint8
        rgb  = rgba[..., :3]
        a    = rgba[..., 3]

        # resize to tile
        base_rgb = cv2.resize(rgb, (tile_w, tile_h), interpolation=cv2.INTER_LINEAR)
        base_a   = cv2.resize(a,   (tile_w, tile_h), interpolation=cv2.INTER_NEAREST)

        # scale with big-card bias
        s = self.rng.uniform(*sc.big_card_range) if self.rng.random() < sc.big_card_prob else self.rng.uniform(*sc.scale_range)
        new_w = max(1, int(tile_w * s)); new_h = max(1, int(tile_h * s))
        base_rgb = cv2.resize(base_rgb, (new_w, new_h), interpolation=cv2.INTER_LINEAR)
        base_a   = cv2.resize(base_a,   (new_w, new_h), interpolation=cv2.INTER_NEAREST)

        # pad to avoid crop during rotate
        h0, w0 = base_a.shape
        diag = int(np.ceil(np.hypot(w0, h0) * 1.1))
        pad_x = (diag - w0) // 2; pad_y = (diag - h0) // 2
        arr_p = cv2.copyMakeBorder(base_rgb, pad_y, pad_y, pad_x, pad_x, cv2.BORDER_CONSTANT, value=[30, 30, 30])
        msk_p = cv2.copyMakeBorder(base_a,   pad_y, pad_y, pad_x, pad_x, cv2.BORDER_CONSTANT, value=0)

        # Albumentations on (image, mask)
        aug = self.per_card(image=arr_p, mask=msk_p)
        warped_img  = aug["image"]   # RGB uint8
        warped_mask = aug["mask"]    # (H,W) uint8

        # center-biased jitter
        s2 = self.rng.uniform(*sc.big_card_range) if self.rng.random() < sc.big_card_prob else self.rng.uniform(*sc.scale_range)
        jitter = 10 + int(10 * s2)

        plc = self.cfg.placement
        width, height = self.cfg.scene.width, self.cfg.scene.height

        for _ in range(plc.placement_retries):
            px = center_biased_uniform(max(-w0, x - jitter), min(width,  x + jitter), sc.center_bias, self.rng)
            py = center_biased_uniform(max(-h0, y - jitter), min(height, y + jitter), sc.center_bias, self.rng)
            ok, ix, iy, mask_clip = self._paste_with_clip_np(
                canvas_rgb, warped_img, warped_mask, px, py,
                occ=occ, card_id=card_id, commit=True
            )
            if ok:
                return mask_clip, ix, iy
        return None

    def generate_scene(self,
                       background_img: Image.Image | None,
                       card_images_rgba: List[Image.Image] | List[np.ndarray],
                       scene_id: int = 1,
                       scene_name: str = "scene.png",
                       tile_w: Optional[int] = None,
                       tile_h: Optional[int] = None,
                       step_x: Optional[int] = None,
                       step_y: Optional[int] = None) -> Tuple[Dict[str, Any], np.ndarray, np.ndarray]:
        """
        Returns (coco_dict, scene_img_np, pre_warp_canvas_np)
        """
        cfg = self.cfg
        W, H = cfg.scene.width, cfg.scene.height

        # convert PIL->np if needed
        if len(card_images_rgba) > 0 and isinstance(card_images_rgba[0], Image.Image):
            cards_np = self.pil_rgba_to_numpy_rgba(card_images_rgba)  # List[np.ndarray]
        else:
            cards_np = card_images_rgba  # type: ignore

        # tile & steps
        if tile_w is None or tile_h is None:
            tile_w, tile_h = self.rng.choice(cfg.grid.tile_dimensions)
        if step_x is None:
            step_x = int(tile_w * self.rng.choice(cfg.grid.step_ratios))
        if step_y is None:
            step_y = int(tile_h * self.rng.choice(cfg.grid.step_ratios))

        canvas_rgb = make_canvas_from_image_np(background_img, W, H)
        occ = np.zeros((H, W), dtype=np.int32)

        coco = {
            "images": [{"id": scene_id, "width": W, "height": H, "file_name": scene_name}],
            "annotations": [],
            "categories": [{"id": 1, "name": "card"}],
        }
        image_id = scene_id
        ann_id = 1

        raw_anns, raw_polys, placed = [], [], []
        # grid sweep
        for y0 in range(0, H, step_y):
            for x0 in range(0, W, step_x):
                if self.rng.random() < cfg.scene.drop_prob:
                    continue
                out = self._generate_warped_image(cards_np, canvas_rgb, x0, y0, tile_w, tile_h, occ=occ, card_id=ann_id)
                if out is None:
                    continue
                mask_clip, px, py = out
                poly = mask_to_poly(mask_clip, px, py, cfg.poly.mode, cfg.poly.erode_px)
                if poly is None:
                    continue

                x, y, w, h = cv2.boundingRect(poly.astype(np.int32))
                area = float(cv2.contourArea(poly.astype(np.float32)))
                ann = {
                    "id": ann_id, "image_id": image_id, "category_id": 1,
                    "bbox": [int(x), int(y), int(w), int(h)],
                    "area": area, "segmentation": [poly.reshape(-1).tolist()], "iscrowd": 0
                }
                raw_anns.append(ann)
                raw_polys.append(poly)
                placed.append({"card_id": ann_id, "ix": px, "iy": py, "mask": mask_clip.copy()})
                ann_id += 1

        # visibility pruning
        keep_idx = []
        vis_keep = self.cfg.placement.visibility_keep_frac
        for i, info in enumerate(placed):
            m = info["mask"] > 0
            iy, ix = info["iy"], info["ix"]
            h, w = m.shape
            roi = occ[iy:iy+h, ix:ix+w]
            total = m.sum()
            if total == 0:
                continue
            visible = (m & (roi == info["card_id"])).sum()
            if visible / float(total) >= vis_keep:
                keep_idx.append(i)

        raw_anns  = [raw_anns[i]  for i in keep_idx]
        raw_polys = [raw_polys[i] for i in keep_idx]

        # mild global perspective
        src = np.float32([[0, 0], [W, 0], [W, H], [0, H]])
        delta = cfg.scene.perspective_delta_frac * min(W, H)
        dst = src + np.random.uniform(-delta, delta, src.shape).astype(np.float32)
        M = cv2.getPerspectiveTransform(src, dst)

        canvas_np = cv2.warpPerspective(
            canvas_rgb, M, (W, H),
            flags=cv2.INTER_LINEAR,
            borderMode=cv2.BORDER_CONSTANT, borderValue=(30, 30, 30)
        )

        warped_anns = []
        for ann, poly in zip(raw_anns, raw_polys):
            pts = poly.reshape(1, -1, 2).astype(np.float32)
            pts_w = cv2.perspectiveTransform(pts, M)[0]
            xw, yw, ww, hw = cv2.boundingRect(pts_w.astype(np.int32))
            new_ann = dict(ann)
            new_ann["segmentation"] = [pts_w.reshape(-1).tolist()]
            new_ann["bbox"] = [int(xw), int(yw), int(ww), int(hw)]
            new_ann["area"] = float(cv2.contourArea(pts_w.astype(np.float32)))
            warped_anns.append(new_ann)

        coco["annotations"] = warped_anns
        return coco, canvas_np, canvas_rgb.copy()

    # convenience export so callers don’t need to import geom.rectify
    def rectify_crop(self, image_rgb: np.ndarray, poly_xy: np.ndarray,
                     out_size: tuple[int, int]) -> np.ndarray:
        return rectify_card_from_poly(image_rgb, poly_xy, out_size)
