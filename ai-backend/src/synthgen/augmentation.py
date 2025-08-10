import albumentations as A
import numpy as np
import inspect
from albumentations.core.transforms_interface import ImageOnlyTransform

def _make_noise(p=0.3):
    """Version-proof Gaussian noise (avoids var_limit warnings)."""
    if hasattr(A, "GaussNoise"):
        try:
            sig = inspect.signature(A.GaussNoise.__init__)
            if "var_limit" in sig.parameters:
                return A.GaussNoise(var_limit=(10.0, 40.0), p=p)
            else:
                return A.GaussNoise(p=p)
        except Exception:
            return A.GaussNoise(p=p)

    # Fallback custom noise if GaussNoise missing
    class _LiteGaussianNoise(ImageOnlyTransform):
        def __init__(self, sigma=(10.0, 40.0), always_apply=False, p=0.3):
            super().__init__(always_apply, p); self.sigma = sigma
        def get_params_dependent_on_targets(self, params):
            s = np.random.uniform(*self.sigma)
            return {"_noise": np.random.normal(0.0, s, size=params["image"].shape).astype(np.float32)}
        @property
        def targets_as_params(self): return ["image"]
        def apply(self, img, _noise=None, **kwargs):
            if img.dtype != np.float32: img = img.astype(np.float32)
            out = img + _noise; np.clip(out, 0, 255, out); return out.astype(np.uint8)
    return _LiteGaussianNoise(p=p)

per_card = A.Compose([
    # Small geometry only (you already scale outside)
    A.Affine(
        scale=(0.97, 1.05),            # ~±5% at most
        rotate=(-7, 7),                # small tilt
        shear=(-3, 3),                 # tiny perspective-ish effect
        translate_percent={"x": (-0.02, 0.02), "y": (-0.02, 0.02)},
        fit_output=True,
        p=1.0
    ),

    # One mild color/tone change
    A.OneOf([
        A.ColorJitter(brightness=0.08, contrast=0.08, saturation=0.08, hue=0.01, p=1.0),
        A.RandomBrightnessContrast(brightness_limit=0.08, contrast_limit=0.08, p=1.0),
        A.HueSaturationValue(hue_shift_limit=2, sat_shift_limit=8, val_shift_limit=8, p=1.0),
    ], p=0.6),

    # Very light blur/sharpen (rare)
    A.OneOf([
        A.GaussianBlur(blur_limit=(3, 3), p=1.0),
        A.MotionBlur(blur_limit=3, p=1.0),
        A.Sharpen(alpha=(0.05, 0.12), lightness=(0.95, 1.05), p=1.0),
    ], p=0.15),

    # Subtle sensor noise (rare)
    A.OneOf([
        _make_noise(p=1.0),  # version-safe Gaussian noise
        A.ISONoise(color_shift=(0.005, 0.02), intensity=(0.05, 0.15), p=1.0),
        A.MultiplicativeNoise(multiplier=(0.95, 1.05), per_channel=False, p=1.0),
    ], p=0.20),

    # Occasional local contrast enhancement
    A.CLAHE(clip_limit=(2, 3), p=0.05),
])
