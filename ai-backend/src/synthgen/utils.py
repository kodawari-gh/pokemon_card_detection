from __future__ import annotations
import sys
from pathlib import Path
import logging
import cv2
import random

def setup_cv2_threads(num_threads: int = 16, use_opencl: bool = False) -> None:
    try:
        cv2.setNumThreads(int(num_threads))
        cv2.ocl.setUseOpenCL(bool(use_opencl))
    except Exception:
        pass

def setup_logger(name: str = "gen", level: int = logging.INFO) -> logging.Logger:
    try:
        # If your project provides a richer logger, prefer it:
        from core.logging_config import setup_logger as _setup
        return _setup(name)
    except Exception:
        logger = logging.getLogger(name)
        if not logger.handlers:
            handler = logging.StreamHandler(sys.stdout)
            fmt = "[%(levelname)s] %(name)s: %(message)s"
            handler.setFormatter(logging.Formatter(fmt))
            logger.addHandler(handler)
        logger.setLevel(level)
        return logger

def center_biased_uniform(low: int, high: int, bias: float, rng=random) -> int:
    if high <= low:
        return low
    t = rng.random()
    if bias != 0.5:
        k = 8 * abs(bias - 0.5) + 1
        t = (t**k + (1 - (1 - t)**k)) / 2
    return int(low + (high - low) * t)
