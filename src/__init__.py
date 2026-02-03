"""
Color Emulator - RAW-to-JPEG color science emulation package.

Reverse-engineers camera JPEG color processing into Lightroom presets.
"""

from .orchestrator import ColorEmulator
from .renderer import RawRenderer
from .loss import PerceptualLoss
from .optimizer import StagedOptimizer
from .xmp_generator import XMPGenerator
from .parameters import get_default_params, get_bounds
from .image_utils import load_jpeg, save_image
from .tone_curve import apply_tone_curve

__version__ = "0.1.0"

__all__ = [
    "ColorEmulator",
    "RawRenderer",
    "PerceptualLoss",
    "StagedOptimizer",
    "XMPGenerator",
    "get_default_params",
    "get_bounds",
    "load_jpeg",
    "save_image",
    "apply_tone_curve",
]
