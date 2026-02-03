"""
renderer.py - RAW to RGB rendering using rawpy/LibRaw.

IMPORTANT: This renderer does NOT match Lightroom's internal engine exactly.
The optimizer finds parameters that work best within rawpy's rendering,
which should translate reasonably (but not perfectly) to Lightroom.
"""

import logging
from pathlib import Path
from typing import Any, Dict, Tuple, Union

import numpy as np
import rawpy

from .image_utils import rgb_to_hsl, hsl_to_rgb, resize_array
from .tone_curve import apply_tone_curve, apply_rgb_curves

logger = logging.getLogger(__name__)


# HSL color ranges (hue angles)
HSL_COLOR_RANGES = {
    "Red": (345, 15),      # Wraps around 0
    "Orange": (15, 45),
    "Yellow": (45, 75),
    "Green": (75, 165),
    "Aqua": (165, 195),
    "Blue": (195, 255),
    "Purple": (255, 285),
    "Magenta": (285, 345),
}


class RawRenderer:
    """
    RAW image renderer using rawpy (LibRaw wrapper).

    Applies Lightroom-style parameters to rendered images.
    """

    def __init__(self, use_camera_wb: bool = True):
        """
        Initialize renderer.

        Args:
            use_camera_wb: If True, use camera's recorded white balance.
                          We lock this to True to match in-camera JPEG WB.
        """
        self.use_camera_wb = use_camera_wb
        self._cache: Dict[str, np.ndarray] = {}

    def render(
        self,
        dng_path: Union[str, Path],
        params: Dict[str, Any],
        target_size: Tuple[int, int] = (1024, 1024),
        use_cache: bool = True,
    ) -> np.ndarray:
        """
        Render a DNG file with the given Lightroom-style parameters.

        Args:
            dng_path: Path to DNG file
            params: Dictionary of Lightroom parameters
            target_size: Max dimension for output (for speed)
            use_cache: Whether to cache the base render

        Returns:
            RGB image as numpy array (float32, 0-1 range)
        """
        dng_path = str(dng_path)

        # Get base render (cached if possible)
        if use_cache and dng_path in self._cache:
            rgb = self._cache[dng_path].copy()
        else:
            rgb = self._render_base(dng_path)
            if use_cache:
                self._cache[dng_path] = rgb.copy()

        # Apply our parameter pipeline
        rgb = self._apply_parameters(rgb, params)

        # Resize for speed
        max_dim = max(target_size)
        rgb = resize_array(rgb, max_dim)

        return rgb

    def _render_base(self, dng_path: str) -> np.ndarray:
        """
        Render base image from DNG without parameter adjustments.

        Args:
            dng_path: Path to DNG file

        Returns:
            Linear RGB image (float32, 0-1 range)
        """
        logger.debug(f"Rendering base image: {Path(dng_path).name}")

        with rawpy.imread(dng_path) as raw:
            # Base demosaic with camera white balance
            rgb = raw.postprocess(
                use_camera_wb=self.use_camera_wb,
                use_auto_wb=False,
                output_color=rawpy.ColorSpace.sRGB,
                output_bps=16,
                no_auto_bright=True,
                gamma=(1, 1),  # Linear output, we apply curves ourselves
                demosaic_algorithm=rawpy.DemosaicAlgorithm.AHD,
            )

        # Convert to float 0-1
        rgb = rgb.astype(np.float32) / 65535.0

        return rgb

    def _apply_parameters(self, rgb: np.ndarray, params: Dict[str, Any]) -> np.ndarray:
        """
        Apply Lightroom-equivalent transformations.

        Order: tone curves -> HSL -> calibration

        Args:
            rgb: Linear RGB image (float32, 0-1)
            params: Parameter dictionary

        Returns:
            Processed RGB image
        """
        # 1. Apply main tone curve (if present)
        if "ToneCurvePV2012" in params and params["ToneCurvePV2012"]:
            rgb = apply_tone_curve(rgb, params["ToneCurvePV2012"])

        # 2. Apply RGB channel curves (for WB-like adjustments)
        red_curve = params.get("ToneCurvePV2012Red")
        green_curve = params.get("ToneCurvePV2012Green")
        blue_curve = params.get("ToneCurvePV2012Blue")

        if red_curve or green_curve or blue_curve:
            rgb = apply_rgb_curves(
                rgb,
                red_curve or [],
                green_curve or [],
                blue_curve or [],
            )

        # 3. Apply HSL adjustments
        rgb = self._apply_hsl(rgb, params)

        # 4. Apply camera calibration
        rgb = self._apply_calibration(rgb, params)

        # Ensure valid range
        return np.clip(rgb, 0.0, 1.0).astype(np.float32)

    def _apply_hsl(self, rgb: np.ndarray, params: Dict[str, Any]) -> np.ndarray:
        """
        Apply HSL adjustments per color channel.

        Args:
            rgb: RGB image (float32, 0-1)
            params: Parameter dictionary containing HSL adjustments

        Returns:
            Adjusted RGB image
        """
        # Check if any HSL params are non-zero
        hsl_colors = ["Red", "Orange", "Yellow", "Green", "Aqua", "Blue", "Purple", "Magenta"]
        has_hsl_adjustments = False

        for color in hsl_colors:
            for adj_type in ["Hue", "Saturation", "Luminance"]:
                key = f"{adj_type}Adjustment{color}"
                if params.get(key, 0) != 0:
                    has_hsl_adjustments = True
                    break
            if has_hsl_adjustments:
                break

        if not has_hsl_adjustments:
            return rgb

        # Convert to HSL
        hsl = rgb_to_hsl(rgb)
        h, s, l = hsl[:, :, 0], hsl[:, :, 1], hsl[:, :, 2]

        # Apply adjustments for each color range
        for color in hsl_colors:
            hue_adj = params.get(f"HueAdjustment{color}", 0) / 100.0 * 30  # Scale to degrees
            sat_adj = params.get(f"SaturationAdjustment{color}", 0) / 100.0
            lum_adj = params.get(f"LuminanceAdjustment{color}", 0) / 100.0

            if hue_adj == 0 and sat_adj == 0 and lum_adj == 0:
                continue

            # Create mask for this color range
            mask = self._get_color_mask(h, color)

            if mask.sum() == 0:
                continue

            # Apply hue shift
            if hue_adj != 0:
                h[mask] = (h[mask] + hue_adj) % 360

            # Apply saturation adjustment
            if sat_adj != 0:
                s[mask] = np.clip(s[mask] * (1 + sat_adj), 0, 1)

            # Apply luminance adjustment
            if lum_adj != 0:
                l[mask] = np.clip(l[mask] + lum_adj * 0.5, 0, 1)

        # Reconstruct HSL and convert back to RGB
        hsl = np.stack([h, s, l], axis=-1)
        return hsl_to_rgb(hsl)

    def _get_color_mask(self, hue: np.ndarray, color: str) -> np.ndarray:
        """
        Create a soft mask for a color range.

        Args:
            hue: Hue channel (0-360)
            color: Color name

        Returns:
            Mask array (0-1)
        """
        hue_range = HSL_COLOR_RANGES.get(color)
        if not hue_range:
            return np.zeros_like(hue, dtype=bool)

        start, end = hue_range

        if start > end:  # Wraps around (e.g., Red)
            mask = (hue >= start) | (hue < end)
        else:
            mask = (hue >= start) & (hue < end)

        return mask

    def _apply_calibration(self, rgb: np.ndarray, params: Dict[str, Any]) -> np.ndarray:
        """
        Apply camera calibration primary shifts.

        These affect the underlying color response.

        Args:
            rgb: RGB image (float32, 0-1)
            params: Parameter dictionary

        Returns:
            Calibrated RGB image
        """
        # Check if any calibration params are non-zero
        shadow_tint = params.get("ShadowTint", 0)
        red_hue = params.get("RedHue", 0)
        red_sat = params.get("RedSaturation", 0)
        green_hue = params.get("GreenHue", 0)
        green_sat = params.get("GreenSaturation", 0)
        blue_hue = params.get("BlueHue", 0)
        blue_sat = params.get("BlueSaturation", 0)

        if all(v == 0 for v in [shadow_tint, red_hue, red_sat, green_hue, green_sat, blue_hue, blue_sat]):
            return rgb

        rgb = rgb.copy()

        # Shadow tint: add green/magenta to shadows
        if shadow_tint != 0:
            shadow_mask = (1 - np.mean(rgb, axis=2, keepdims=True)) ** 2
            tint_amount = shadow_tint / 100.0 * 0.1
            rgb[:, :, 1] = np.clip(rgb[:, :, 1] + tint_amount * shadow_mask[:, :, 0], 0, 1)

        # Red primary adjustments
        if red_hue != 0 or red_sat != 0:
            # Create red mask
            red_mask = rgb[:, :, 0] - np.maximum(rgb[:, :, 1], rgb[:, :, 2])
            red_mask = np.clip(red_mask, 0, 1)

            if red_hue != 0:
                # Shift red towards orange or magenta
                hue_shift = red_hue / 100.0 * 0.2
                rgb[:, :, 1] = np.clip(rgb[:, :, 1] + hue_shift * red_mask * rgb[:, :, 0], 0, 1)

            if red_sat != 0:
                sat_mult = 1 + red_sat / 100.0
                avg = (rgb[:, :, 1] + rgb[:, :, 2]) / 2
                rgb[:, :, 0] = np.clip(avg + (rgb[:, :, 0] - avg) * sat_mult, 0, 1)

        # Green primary adjustments
        if green_hue != 0 or green_sat != 0:
            green_mask = rgb[:, :, 1] - np.maximum(rgb[:, :, 0], rgb[:, :, 2])
            green_mask = np.clip(green_mask, 0, 1)

            if green_hue != 0:
                hue_shift = green_hue / 100.0 * 0.2
                rgb[:, :, 2] = np.clip(rgb[:, :, 2] + hue_shift * green_mask * rgb[:, :, 1], 0, 1)

            if green_sat != 0:
                sat_mult = 1 + green_sat / 100.0
                avg = (rgb[:, :, 0] + rgb[:, :, 2]) / 2
                rgb[:, :, 1] = np.clip(avg + (rgb[:, :, 1] - avg) * sat_mult, 0, 1)

        # Blue primary adjustments
        if blue_hue != 0 or blue_sat != 0:
            blue_mask = rgb[:, :, 2] - np.maximum(rgb[:, :, 0], rgb[:, :, 1])
            blue_mask = np.clip(blue_mask, 0, 1)

            if blue_hue != 0:
                hue_shift = blue_hue / 100.0 * 0.2
                rgb[:, :, 0] = np.clip(rgb[:, :, 0] + hue_shift * blue_mask * rgb[:, :, 2], 0, 1)

            if blue_sat != 0:
                sat_mult = 1 + blue_sat / 100.0
                avg = (rgb[:, :, 0] + rgb[:, :, 1]) / 2
                rgb[:, :, 2] = np.clip(avg + (rgb[:, :, 2] - avg) * sat_mult, 0, 1)

        return np.clip(rgb, 0.0, 1.0).astype(np.float32)

    def clear_cache(self) -> None:
        """Clear the render cache."""
        self._cache.clear()
        logger.debug("Render cache cleared")

    def preload(self, dng_paths: list) -> None:
        """
        Preload base renders into cache.

        Args:
            dng_paths: List of DNG file paths
        """
        for path in dng_paths:
            path = str(path)
            if path not in self._cache:
                self._cache[path] = self._render_base(path)
                logger.debug(f"Preloaded: {Path(path).name}")
