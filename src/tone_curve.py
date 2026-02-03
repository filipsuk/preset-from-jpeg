"""
tone_curve.py - Tone curve application and fitting.

Implements Lightroom-style tone curves using interpolation.
"""

import logging
from typing import List, Tuple, Union

import numpy as np
from scipy.interpolate import PchipInterpolator

logger = logging.getLogger(__name__)


def apply_tone_curve(
    img: np.ndarray,
    curve_points: List[Tuple[float, float]],
) -> np.ndarray:
    """
    Apply a tone curve to an image using monotonic cubic interpolation.

    Args:
        img: Image array (can be single channel or RGB, float32 0-1 range)
        curve_points: List of (input, output) control points, normalized 0-1

    Returns:
        Image with tone curve applied
    """
    if len(curve_points) < 2:
        logger.warning("Curve needs at least 2 points, returning unchanged image")
        return img

    # Extract inputs and outputs
    inputs = np.array([p[0] for p in curve_points])
    outputs = np.array([p[1] for p in curve_points])

    # Sort by input value
    sort_idx = np.argsort(inputs)
    inputs = inputs[sort_idx]
    outputs = outputs[sort_idx]

    # Ensure endpoints at 0 and 1 if not present
    if inputs[0] > 0:
        inputs = np.concatenate([[0], inputs])
        outputs = np.concatenate([[0], outputs])
    if inputs[-1] < 1:
        inputs = np.concatenate([inputs, [1]])
        outputs = np.concatenate([outputs, [1]])

    # Create monotonic interpolator (PCHIP preserves monotonicity)
    # This is important for tone curves to avoid inversions
    try:
        interpolator = PchipInterpolator(inputs, outputs, extrapolate=True)
    except ValueError as e:
        logger.warning(f"Interpolation error: {e}, using linear fallback")
        # Fallback to linear interpolation
        result = np.interp(img, inputs, outputs)
        return np.clip(result, 0.0, 1.0).astype(np.float32)

    # Apply curve
    result = interpolator(img)

    return np.clip(result, 0.0, 1.0).astype(np.float32)


def apply_rgb_curves(
    rgb: np.ndarray,
    red_curve: List[Tuple[float, float]],
    green_curve: List[Tuple[float, float]],
    blue_curve: List[Tuple[float, float]],
) -> np.ndarray:
    """
    Apply individual tone curves to R, G, B channels.

    Args:
        rgb: RGB image (H, W, 3), float32 0-1
        red_curve: Red channel curve points
        green_curve: Green channel curve points
        blue_curve: Blue channel curve points

    Returns:
        RGB image with curves applied
    """
    result = rgb.copy()

    if red_curve:
        result[:, :, 0] = apply_tone_curve(result[:, :, 0], red_curve)

    if green_curve:
        result[:, :, 1] = apply_tone_curve(result[:, :, 1], green_curve)

    if blue_curve:
        result[:, :, 2] = apply_tone_curve(result[:, :, 2], blue_curve)

    return result


def create_linear_curve(num_points: int) -> List[Tuple[float, float]]:
    """
    Create a linear (identity) tone curve.

    Args:
        num_points: Number of control points

    Returns:
        List of (input, output) points forming a linear curve
    """
    if num_points < 2:
        num_points = 2

    return [(i / (num_points - 1), i / (num_points - 1)) for i in range(num_points)]


def create_contrast_curve(
    num_points: int,
    contrast: float = 0.0,
) -> List[Tuple[float, float]]:
    """
    Create an S-curve for contrast adjustment.

    Args:
        num_points: Number of control points
        contrast: Contrast amount (-1 to 1), 0 = linear

    Returns:
        List of (input, output) points
    """
    if num_points < 2:
        num_points = 2

    contrast = np.clip(contrast, -1.0, 1.0)

    points = []
    for i in range(num_points):
        x = i / (num_points - 1)
        # Apply S-curve transformation
        if contrast >= 0:
            # Increase contrast
            y = 0.5 + (x - 0.5) * (1 + contrast * 2)
        else:
            # Decrease contrast
            y = 0.5 + (x - 0.5) * (1 + contrast)

        y = np.clip(y, 0.0, 1.0)
        points.append((x, y))

    return points


def curve_to_lut(
    curve_points: List[Tuple[float, float]],
    lut_size: int = 256,
) -> np.ndarray:
    """
    Convert curve points to a lookup table for fast application.

    Args:
        curve_points: List of (input, output) control points
        lut_size: Size of the LUT

    Returns:
        Lookup table as numpy array
    """
    inputs = np.array([p[0] for p in curve_points])
    outputs = np.array([p[1] for p in curve_points])

    # Sort
    sort_idx = np.argsort(inputs)
    inputs = inputs[sort_idx]
    outputs = outputs[sort_idx]

    # Ensure endpoints
    if inputs[0] > 0:
        inputs = np.concatenate([[0], inputs])
        outputs = np.concatenate([[0], outputs])
    if inputs[-1] < 1:
        inputs = np.concatenate([inputs, [1]])
        outputs = np.concatenate([outputs, [1]])

    # Create interpolator
    interpolator = PchipInterpolator(inputs, outputs, extrapolate=True)

    # Generate LUT
    x = np.linspace(0, 1, lut_size)
    lut = interpolator(x)

    return np.clip(lut, 0.0, 1.0).astype(np.float32)


def apply_lut(
    img: np.ndarray,
    lut: np.ndarray,
) -> np.ndarray:
    """
    Apply a lookup table to an image.

    Args:
        img: Image array (float32, 0-1 range)
        lut: Lookup table (1D array, values 0-1)

    Returns:
        Image with LUT applied
    """
    lut_size = len(lut)
    indices = (img * (lut_size - 1)).astype(np.int32)
    indices = np.clip(indices, 0, lut_size - 1)
    return lut[indices]


def estimate_curve_from_images(
    source: np.ndarray,
    target: np.ndarray,
    num_points: int = 5,
    channel: int = None,
) -> List[Tuple[float, float]]:
    """
    Estimate a tone curve that maps source image to target image.

    This is a simple histogram-based approach.

    Args:
        source: Source image (float32, 0-1)
        target: Target image (float32, 0-1)
        num_points: Number of curve points to generate
        channel: If specified, only use this channel (0=R, 1=G, 2=B)

    Returns:
        Estimated curve points
    """
    # Flatten images
    if channel is not None and len(source.shape) == 3:
        source_flat = source[:, :, channel].flatten()
        target_flat = target[:, :, channel].flatten()
    else:
        source_flat = source.flatten()
        target_flat = target.flatten()

    # Sample points at different input levels
    points = []
    for i in range(num_points):
        input_val = i / (num_points - 1)

        # Find pixels near this input value in source
        tolerance = 0.1
        mask = np.abs(source_flat - input_val) < tolerance

        if mask.sum() > 0:
            # Average output for these pixels
            output_val = float(np.mean(target_flat[mask]))
        else:
            # No matching pixels, use linear
            output_val = input_val

        output_val = np.clip(output_val, 0.0, 1.0)
        points.append((input_val, output_val))

    return points


def blend_curves(
    curve1: List[Tuple[float, float]],
    curve2: List[Tuple[float, float]],
    weight: float = 0.5,
) -> List[Tuple[float, float]]:
    """
    Blend two curves together.

    Args:
        curve1: First curve
        curve2: Second curve
        weight: Blending weight (0 = curve1, 1 = curve2)

    Returns:
        Blended curve
    """
    # Resample both curves to same number of points
    num_points = max(len(curve1), len(curve2))

    # Create LUTs
    lut1 = curve_to_lut(curve1, num_points)
    lut2 = curve_to_lut(curve2, num_points)

    # Blend
    blended_lut = lut1 * (1 - weight) + lut2 * weight

    # Convert back to curve points
    points = []
    for i in range(num_points):
        x = i / (num_points - 1)
        y = float(blended_lut[i])
        points.append((x, y))

    return points
