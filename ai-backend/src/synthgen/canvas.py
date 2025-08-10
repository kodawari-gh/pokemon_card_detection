from __future__ import annotations
import cv2
import numpy as np
from PIL import Image

def make_canvas_from_image_np(bg_img: Image.Image | None, W: int, H: int) -> np.ndarray:
    if bg_img is None:
        return np.full((H, W, 3), 30, np.uint8)
    bg = bg_img.convert("RGB")
    w0, h0 = bg.size
    scale = max(W / w0, H / h0)
    new_w, new_h = int(np.ceil(w0 * scale)), int(np.ceil(h0 * scale))
    bg_np = cv2.cvtColor(np.array(bg), cv2.COLOR_RGB2BGR)
    bg_rs = cv2.resize(
        bg_np, (new_w, new_h),
        interpolation=cv2.INTER_AREA if scale < 1.0 else cv2.INTER_LINEAR
    )
    left = (new_w - W) // 2
    top = (new_h - H) // 2
    crop = bg_rs[top:top + H, left:left + W]
    return cv2.cvtColor(crop, cv2.COLOR_BGR2RGB)
