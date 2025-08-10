import os
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, File, UploadFile, HTTPException, Query
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware

from .schemas import ProcessResponse
from .engine import InferenceEngine, BASE, SRC

app = FastAPI(title="Card Seg/Rectify/pHash Server", version="1.0.0")

# CORS (relax as needed)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_headers=["*"],
    allow_methods=["*"],
)

# --- Config (env-overridable) ---
WEIGHTS = Path(os.getenv("WEIGHTS_PATH", str("models/yolo11m-seg-trained.pt")))
CACHE_DIR = Path(os.getenv("CACHE_DIR", str("cache")))
IMG_DB    = Path(os.getenv("IMG_DB_DIR", str("image_database")))
DEVICE    = os.getenv("DEVICE", None)  # e.g., "cuda:0" or "cpu"

# Global engine singleton
ENGINE: Optional[InferenceEngine] = None


@app.on_event("startup")
def _startup():
    global ENGINE
    try:
        ENGINE = InferenceEngine(
            weights_path=WEIGHTS,
            cache_dir=CACHE_DIR,
            img_db_dir=IMG_DB,
            rect_size=(448, 320),   # (H,W) portrait
            device=DEVICE,
            phash_max_distance=int(os.getenv("PHASH_MAX_DISTANCE", "10")),
            phash_min_band_matches=int(os.getenv("PHASH_MIN_BAND", "2")),
        )
    except AssertionError as e:
        raise
    except Exception as e:
        # surface a useful error message on startup
        raise RuntimeError(f"Failed to initialize engine: {e}") from e


@app.get("/health")
def health():
    ok = ENGINE is not None
    return {"ok": ok, "device": getattr(ENGINE, "device", None) if ok else None}


@app.post("/v1/process", response_model=ProcessResponse)
async def process_image(
    file: UploadFile = File(..., description="Image file"),
    conf: float = Query(0.25, ge=0.0, le=1.0),
    iou: float  = Query(0.50, ge=0.0, le=1.0),
    base_inset: float = Query(0.012, ge=0.0, le=0.25),
    inset_min: float = Query(0.008, ge=0.0, le=0.25),
    inset_max: float = Query(0.035, ge=0.0, le=0.25),
    max_hits: int = Query(5, ge=1, le=20),
    visualize: bool = Query(False, description="Return visualization PNG as base64"),
):
    if ENGINE is None:
        raise HTTPException(status_code=503, detail="Engine not ready")
    try:
        image_bytes = await file.read()
        data = ENGINE.process(
            image_bytes,
            conf=conf,
            iou=iou,
            base_inset=base_inset,
            inset_range=(inset_min, inset_max),
            max_hits=max_hits,
            return_vis=visualize,
        )
        return JSONResponse(content=data)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Processing failed: {e}")


# Optional: return just the visualization as an image stream (nice for quick checks)
@app.post("/v1/visualize")
async def visualize(
    file: UploadFile = File(...),
    conf: float = Query(0.25, ge=0.0, le=1.0),
    iou: float  = Query(0.50, ge=0.0, le=1.0),
    base_inset: float = Query(0.012, ge=0.0, le=0.25),
    inset_min: float = Query(0.008, ge=0.0, le=0.25),
    inset_max: float = Query(0.035, ge=0.0, le=0.25),
):
    if ENGINE is None:
        raise HTTPException(status_code=503, detail="Engine not ready")
    try:
        image_bytes = await file.read()
        data = ENGINE.process(
            image_bytes,
            conf=conf,
            iou=iou,
            base_inset=base_inset,
            inset_range=(inset_min, inset_max),
            max_hits=5,
            return_vis=True,
        )
        b64 = data.get("visualization_png_b64")
        if not b64:
            raise ValueError("No visualization generated")
        import base64, io
        raw = base64.b64decode(b64)
        return StreamingResponse(io.BytesIO(raw), media_type="image/png")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Visualization failed: {e}")
