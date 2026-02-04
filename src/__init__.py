"""
Color Emulator - RAW-to-JPEG color science emulation package.

Reverse-engineers camera JPEG color processing into Lightroom presets.
Uses RawTherapee CLI for rendering with DCP profile support.
"""

from .rt_renderer import RawTherapeeRenderer, get_default_rt_params
from .loss import PerceptualLoss
from .xmp_generator import XMPGenerator
from .image_utils import load_jpeg, save_image
from .tone_curve import apply_tone_curve

__version__ = "0.1.0"

__all__ = [
    "RawTherapeeRenderer",
    "get_default_rt_params",
    "PerceptualLoss",
    "XMPGenerator",
    "load_jpeg",
    "save_image",
    "apply_tone_curve",
]
