from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Tuple

Tile = Tuple[int, int]

@dataclass
class GridConfig:
    tile_dimensions: List[Tile] = field(default_factory=lambda: [
        (80, 120), (120, 180), (160, 240), (240, 360),
        (320, 480), (400, 600), (480, 720), (560, 840), (640, 840)
    ])
    step_ratios: List[float] = field(default_factory=lambda: [0.75, 1.0, 1.5, 2.0])

@dataclass
class PlacementConfig:
    max_overlap_frac_new: float = 0.15   # at most 15% of new card may overlap others
    placement_retries: int = 6
    visibility_keep_frac: float = 0.60   # keep if >=60% remains visible

@dataclass
class ScaleConfig:
    big_card_prob: float = 0.45
    big_card_range: Tuple[float, float] = (1.0, 1.2)
    scale_range: Tuple[float, float] = (0.7, 1.0)
    center_bias: float = 0.65

@dataclass
class PolyConfig:
    mode: str = "quad"  # "quad" or "full"
    erode_px: int = 1

@dataclass
class SceneConfig:
    width: int = 1280
    height: int = 720
    drop_prob: float = 0.10
    min_inbounds_frac: float = 0.60
    min_visible_frac: float = 0.25
    rect_w: int = 320
    rect_h: int = 448
    perspective_delta_frac: float = 0.08  # mild global perspective

@dataclass
class SynthConfig:
    scene: SceneConfig = SceneConfig()
    grid: GridConfig = GridConfig()
    placement: PlacementConfig = PlacementConfig()
    scale: ScaleConfig = ScaleConfig()
    poly: PolyConfig = PolyConfig()
