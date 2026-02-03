"""
image_utils.py - Image loading, resizing, and colorspace conversion utilities.
"""

import logging
from pathlib import Path
from typing import Tuple, Union

import numpy as np
from PIL import Image
from skimage.color import rgb2lab, lab2rgb
from skimage.transform import resize

logger = logging.getLogger(__name__)


def load_jpeg(
    path: Union[str, Path],
    max_size: int = 1024,
) -> np.ndarray:
    """
    Load a JPEG image and optionally resize it.

    Args:
        path: Path to the JPEG file
        max_size: Maximum dimension (width or height). If 0, no resizing.

    Returns:
        RGB image as numpy array (float32, 0-1 range)
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Image not found: {path}")

    # Load image
    with Image.open(path) as img:
        # Convert to RGB if necessary
        if img.mode != "RGB":
            img = img.convert("RGB")

        # Resize if needed
        if max_size > 0:
            img = resize_pil_image(img, max_size)

        # Convert to numpy array
        rgb = np.array(img, dtype=np.float32) / 255.0

    logger.debug(f"Loaded {path.name}: shape={rgb.shape}")
    return rgb


def resize_pil_image(img: Image.Image, max_size: int) -> Image.Image:
    """
    Resize a PIL image maintaining aspect ratio.

    Args:
        img: PIL Image
        max_size: Maximum dimension

    Returns:
        Resized PIL Image
    """
    w, h = img.size
    if max(w, h) <= max_size:
        return img

    scale = max_size / max(w, h)
    new_w = int(w * scale)
    new_h = int(h * scale)

    return img.resize((new_w, new_h), Image.Resampling.LANCZOS)


def resize_array(
    img: np.ndarray,
    max_size: int = 1024,
) -> np.ndarray:
    """
    Resize a numpy image array maintaining aspect ratio.

    Args:
        img: Image array (H, W, C) in float32 0-1 range
        max_size: Maximum dimension

    Returns:
        Resized image array
    """
    h, w = img.shape[:2]
    if max(h, w) <= max_size:
        return img

    scale = max_size / max(h, w)
    new_h = int(h * scale)
    new_w = int(w * scale)

    resized = resize(img, (new_h, new_w), anti_aliasing=True, preserve_range=True)
    return resized.astype(np.float32)


def resize_to_match(
    img: np.ndarray,
    target_shape: Tuple[int, int],
) -> np.ndarray:
    """
    Resize an image to match a target shape.

    Args:
        img: Image array (H, W, C)
        target_shape: Target (H, W)

    Returns:
        Resized image array
    """
    if img.shape[:2] == target_shape:
        return img

    resized = resize(img, target_shape, anti_aliasing=True, preserve_range=True)
    return resized.astype(np.float32)


def rgb_to_lab(rgb: np.ndarray) -> np.ndarray:
    """
    Convert RGB image to LAB colorspace.

    Args:
        rgb: RGB image (float32, 0-1 range)

    Returns:
        LAB image
    """
    # Ensure valid range
    rgb = np.clip(rgb, 0.0, 1.0)
    return rgb2lab(rgb)


def lab_to_rgb(lab: np.ndarray) -> np.ndarray:
    """
    Convert LAB image to RGB colorspace.

    Args:
        lab: LAB image

    Returns:
        RGB image (float32, 0-1 range)
    """
    rgb = lab2rgb(lab)
    return np.clip(rgb, 0.0, 1.0).astype(np.float32)


def rgb_to_hsl(rgb: np.ndarray) -> np.ndarray:
    """
    Convert RGB image to HSL colorspace.

    Args:
        rgb: RGB image (float32, 0-1 range)

    Returns:
        HSL image where H is in [0, 360), S and L are in [0, 1]
    """
    rgb = np.clip(rgb, 0.0, 1.0)

    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]

    max_c = np.maximum(np.maximum(r, g), b)
    min_c = np.minimum(np.minimum(r, g), b)
    delta = max_c - min_c

    # Lightness
    l = (max_c + min_c) / 2.0

    # Saturation
    s = np.zeros_like(l)
    mask = delta > 0
    s[mask] = delta[mask] / (1 - np.abs(2 * l[mask] - 1) + 1e-10)
    s = np.clip(s, 0.0, 1.0)

    # Hue
    h = np.zeros_like(l)

    # Red is max
    mask_r = (max_c == r) & (delta > 0)
    h[mask_r] = 60 * (((g[mask_r] - b[mask_r]) / delta[mask_r]) % 6)

    # Green is max
    mask_g = (max_c == g) & (delta > 0)
    h[mask_g] = 60 * (((b[mask_g] - r[mask_g]) / delta[mask_g]) + 2)

    # Blue is max
    mask_b = (max_c == b) & (delta > 0)
    h[mask_b] = 60 * (((r[mask_b] - g[mask_b]) / delta[mask_b]) + 4)

    h = h % 360  # Ensure positive

    hsl = np.stack([h, s, l], axis=-1)
    return hsl.astype(np.float32)


def hsl_to_rgb(hsl: np.ndarray) -> np.ndarray:
    """
    Convert HSL image to RGB colorspace.

    Args:
        hsl: HSL image where H is in [0, 360), S and L are in [0, 1]

    Returns:
        RGB image (float32, 0-1 range)
    """
    h, s, l = hsl[..., 0], hsl[..., 1], hsl[..., 2]

    c = (1 - np.abs(2 * l - 1)) * s
    x = c * (1 - np.abs((h / 60) % 2 - 1))
    m = l - c / 2

    h_section = (h / 60).astype(np.int32) % 6

    rgb = np.zeros((*hsl.shape[:-1], 3), dtype=np.float32)

    # Section 0: R=C, G=X, B=0
    mask = h_section == 0
    rgb[mask, 0] = c[mask]
    rgb[mask, 1] = x[mask]

    # Section 1: R=X, G=C, B=0
    mask = h_section == 1
    rgb[mask, 0] = x[mask]
    rgb[mask, 1] = c[mask]

    # Section 2: R=0, G=C, B=X
    mask = h_section == 2
    rgb[mask, 1] = c[mask]
    rgb[mask, 2] = x[mask]

    # Section 3: R=0, G=X, B=C
    mask = h_section == 3
    rgb[mask, 1] = x[mask]
    rgb[mask, 2] = c[mask]

    # Section 4: R=X, G=0, B=C
    mask = h_section == 4
    rgb[mask, 0] = x[mask]
    rgb[mask, 2] = c[mask]

    # Section 5: R=C, G=0, B=X
    mask = h_section == 5
    rgb[mask, 0] = c[mask]
    rgb[mask, 2] = x[mask]

    rgb = rgb + m[..., np.newaxis]
    return np.clip(rgb, 0.0, 1.0).astype(np.float32)


def save_image(
    img: np.ndarray,
    path: Union[str, Path],
    quality: int = 95,
) -> None:
    """
    Save a numpy array as a JPEG image.

    Args:
        img: RGB image (float32, 0-1 range)
        path: Output path
        quality: JPEG quality (0-100)
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    # Convert to uint8
    img = np.clip(img * 255, 0, 255).astype(np.uint8)

    # Save
    pil_img = Image.fromarray(img, mode="RGB")
    pil_img.save(path, "JPEG", quality=quality)

    logger.debug(f"Saved image: {path}")


def ensure_float32(img: np.ndarray) -> np.ndarray:
    """
    Ensure image is float32 in 0-1 range.

    Args:
        img: Image array

    Returns:
        Float32 image in 0-1 range
    """
    if img.dtype == np.uint8:
        return img.astype(np.float32) / 255.0
    elif img.dtype == np.uint16:
        return img.astype(np.float32) / 65535.0
    elif img.dtype in [np.float32, np.float64]:
        if img.max() > 1.0:
            return (img / 255.0).astype(np.float32)
        return img.astype(np.float32)
    else:
        return img.astype(np.float32)
