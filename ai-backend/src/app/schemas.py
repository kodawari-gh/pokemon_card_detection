from typing import List, Optional, Tuple
from pydantic import BaseModel, Field

Point = Tuple[float, float]

class Match(BaseModel):
    set_id: Optional[str] = None
    card_id: Optional[str] = None
    distance: int
    name: Optional[str] = None

class Detection(BaseModel):
    polygon: List[Point] = Field(..., description="Polygon in pixel coords (x,y)")
    crop_size: Tuple[int, int]  # (H, W)
    matches: List[Match] = []

class ProcessResponse(BaseModel):
    image_size: Tuple[int, int]  # (H, W)
    num_detections: int
    detections: List[Detection]
    visualization_png_b64: Optional[str] = None
