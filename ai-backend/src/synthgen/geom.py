from __future__ import annotations
import cv2
import numpy as np
from functools import lru_cache
from typing import Optional

def order_quad_tl_tr_br_bl(pts: np.ndarray) -> np.ndarray:
    pts = pts.astype(np.float32)
    s = pts.sum(axis=1)
    d = np.diff(pts, axis=1)
    tl = pts[np.argmin(s)]
    br = pts[np.argmax(s)]
    tr = pts[np.argmin(d)]
    bl = pts[np.argmax(d)]
    return np.stack([tl, tr, br, bl], axis=0)

def rectify_card_from_poly(image_rgb: np.ndarray,
                           poly_xy: np.ndarray,
                           out_size: tuple[int, int]) -> np.ndarray:
    if poly_xy.shape[0] != 4:
        rect = cv2.minAreaRect(poly_xy.astype(np.float32).reshape(-1, 1, 2))
        poly_xy = cv2.boxPoints(rect).astype(np.float32)
    src = order_quad_tl_tr_br_bl(poly_xy)
    w, h = out_size
    dst = np.array([[0, 0], [w - 1, 0], [w - 1, h - 1], [0, h - 1]], dtype=np.float32)
    M = cv2.getPerspectiveTransform(src, dst)
    return cv2.warpPerspective(image_rgb, M, (w, h), flags=cv2.INTER_LINEAR)
import numpy as np, cv2

def _order_quad_tl_tr_br_bl(pts: np.ndarray) -> np.ndarray:
    pts = pts.astype(np.float32)
    s = pts.sum(axis=1); d = np.diff(pts, axis=1)
    tl = pts[np.argmin(s)]; br = pts[np.argmax(s)]
    tr = pts[np.argmin(d)]; bl = pts[np.argmax(d)]
    return np.stack([tl, tr, br, bl], axis=0)

def _quad_from_poly(poly_xy: np.ndarray) -> np.ndarray:
    """Try to approximate to 4 points; fallback to minAreaRect."""
    cnt = poly_xy.astype(np.float32).reshape(-1, 1, 2)
    peri = cv2.arcLength(cnt, True)
    # sweep epsilon from gentle to stronger until we get 4 points
    for eps in np.linspace(0.01, 0.08, 8):
        approx = cv2.approxPolyDP(cnt, eps * peri, True)
        if len(approx) == 4 and cv2.isContourConvex(approx):
            return approx.reshape(-1, 2).astype(np.float32)
    rect = cv2.minAreaRect(cnt)
    return cv2.boxPoints(rect).astype(np.float32)

def _poly_fill_fraction(poly_xy: np.ndarray) -> float:
    """Area(poly) / area(minAreaRect). 1.0 = tight; lower = lots of background included."""
    cnt = poly_xy.astype(np.float32).reshape(-1, 1, 2)
    a_poly = max(cv2.contourArea(cnt), 1.0)
    (_, _), (w, h), _ = cv2.minAreaRect(cnt)
    a_rect = max(w * h, 1.0)
    return float(a_poly / a_rect)

def _inset_quad(quad: np.ndarray, frac: float) -> np.ndarray:
    """Move each corner toward centroid by 'frac' of its distance."""
    c = quad.mean(axis=0, keepdims=True)
    return (c + (quad - c) * (1.0 - float(frac))).astype(np.float32)

def rectify_card_from_poly_quadwise(
    image_rgb: np.ndarray,
    poly_xy: np.ndarray,
    out_size: tuple[int, int] = (320, 448),
    base_inset: float = 0.012,     # ~1.2% inward inset
    inset_range: tuple[float,float] = (0.008, 0.035)  # adapt based on fill
) -> np.ndarray:
    """
    Robust rectifier: fit a quad to the polygon, inset slightly (adaptive),
    then warp to out_size. No expansion to aspect; no morphology.
    """
    # 1) quad fit
    quad = _quad_from_poly(poly_xy)
    quad = _order_quad_tl_tr_br_bl(quad)

    # 2) adaptive inset based on how 'loose' the mask is
    fill = _poly_fill_fraction(poly_xy)  # ~0.6..1.0
    lo, hi = inset_range
    # loose mask (fill~0.6) -> ~hi inset, tight mask (fill~1.0) -> ~lo inset
    inset = np.interp(np.clip(fill, 0.55, 1.00), [0.55, 1.00], [hi, lo])
    inset = max(lo, min(hi, max(base_inset, inset)))

    quad_in = _inset_quad(quad, inset)

    # 3) projective warp
    Wout, Hout = out_size
    dst = np.array([[0, 0], [Wout-1, 0], [Wout-1, Hout-1], [0, Hout-1]], dtype=np.float32)
    M = cv2.getPerspectiveTransform(quad_in, dst)
    return cv2.warpPerspective(image_rgb, M, (Wout, Hout), flags=cv2.INTER_LINEAR)


@lru_cache(maxsize=1)
def _kernel(erode_px: int) -> np.ndarray:
    k = max(1, int(erode_px))
    return cv2.getStructuringElement(cv2.MORPH_RECT, (k, k))

def mask_to_poly(mask_clip: np.ndarray,
                 px: int, py: int,
                 poly_mode: str,
                 erode_px: int) -> Optional[np.ndarray]:
    binm = (mask_clip > 127).astype(np.uint8) * 255
    if erode_px > 0:
        binm = cv2.erode(binm, _kernel(erode_px), iterations=1)
    cnts, _ = cv2.findContours(binm, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not cnts:
        return None
    cnt = max(cnts, key=cv2.contourArea)
    if cnt.shape[0] < 3:
        return None

    if poly_mode == "quad":
        peri = cv2.arcLength(cnt, True)
        approx = cv2.approxPolyDP(cnt, 0.02 * peri, True)
        if approx.shape[0] != 4:
            rect = cv2.minAreaRect(cnt)
            approx = cv2.boxPoints(rect).astype(np.int32).reshape(-1, 1, 2)
        poly = approx.reshape(-1, 2)
    else:
        poly = cnt.reshape(-1, 2)

    poly = poly.astype(np.float32)
    poly[:, 0] += float(px)
    poly[:, 1] += float(py)
    return poly
