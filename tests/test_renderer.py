"""
test_renderer.py - Unit tests for the renderer module.

Note: These tests focus on the parameter application logic.
Full rendering tests require actual DNG files.
"""

import numpy as np
import pytest

from src.renderer import RawRenderer, HSL_COLOR_RANGES
from src.image_utils import rgb_to_hsl, hsl_to_rgb
from src.tone_curve import apply_tone_curve, create_linear_curve


class TestRawRenderer:
    """Tests for the RawRenderer class."""

    def test_initialization(self):
        """Renderer should initialize with correct settings."""
        renderer = RawRenderer(use_camera_wb=True)
        assert renderer.use_camera_wb is True

        renderer = RawRenderer(use_camera_wb=False)
        assert renderer.use_camera_wb is False

    def test_cache_operations(self):
        """Cache operations should work correctly."""
        renderer = RawRenderer()
        assert len(renderer._cache) == 0

        renderer.clear_cache()
        assert len(renderer._cache) == 0


class TestParameterApplication:
    """Tests for parameter application functions."""

    def test_tone_curve_application(self):
        """Tone curve should modify image values."""
        img = np.full((10, 10, 3), 0.5, dtype=np.float32)

        # S-curve that boosts midtones
        curve = [(0, 0), (0.25, 0.2), (0.5, 0.6), (0.75, 0.8), (1, 1)]

        result = apply_tone_curve(img, curve)
        assert result.shape == img.shape
        # Midtones should be boosted
        assert result[0, 0, 0] > 0.5

    def test_linear_curve_no_change(self):
        """Linear curve should not modify values significantly."""
        img = np.random.rand(10, 10, 3).astype(np.float32)
        curve = create_linear_curve(5)

        result = apply_tone_curve(img, curve)
        np.testing.assert_allclose(result, img, atol=0.01)

    def test_hsl_conversion_roundtrip(self):
        """RGB -> HSL -> RGB should be identity (approximately)."""
        rgb = np.random.rand(10, 10, 3).astype(np.float32)
        hsl = rgb_to_hsl(rgb)
        rgb_back = hsl_to_rgb(hsl)

        np.testing.assert_allclose(rgb, rgb_back, atol=0.01)

    def test_hsl_red_detection(self):
        """Red colors should be detected in red hue range."""
        # Pure red
        rgb = np.array([[[1.0, 0.0, 0.0]]], dtype=np.float32)
        hsl = rgb_to_hsl(rgb)

        h = hsl[0, 0, 0]
        # Red hue is around 0 or 360
        assert h < 15 or h > 345

    def test_hsl_green_detection(self):
        """Green colors should be detected correctly."""
        rgb = np.array([[[0.0, 1.0, 0.0]]], dtype=np.float32)
        hsl = rgb_to_hsl(rgb)

        h = hsl[0, 0, 0]
        # Green hue is around 120
        assert 100 < h < 140

    def test_hsl_blue_detection(self):
        """Blue colors should be detected correctly."""
        rgb = np.array([[[0.0, 0.0, 1.0]]], dtype=np.float32)
        hsl = rgb_to_hsl(rgb)

        h = hsl[0, 0, 0]
        # Blue hue is around 240
        assert 220 < h < 260


class TestColorRanges:
    """Tests for HSL color range definitions."""

    def test_color_ranges_defined(self):
        """All expected color ranges should be defined."""
        expected_colors = [
            "Red", "Orange", "Yellow", "Green",
            "Aqua", "Blue", "Purple", "Magenta"
        ]
        for color in expected_colors:
            assert color in HSL_COLOR_RANGES, f"Missing color range: {color}"

    def test_color_ranges_valid(self):
        """Color ranges should have valid hue values."""
        for color, (start, end) in HSL_COLOR_RANGES.items():
            assert 0 <= start <= 360, f"Invalid start for {color}: {start}"
            assert 0 <= end <= 360, f"Invalid end for {color}: {end}"


class TestEdgeCases:
    """Tests for edge cases in rendering."""

    def test_empty_curve(self):
        """Empty curve should return unchanged image."""
        img = np.random.rand(10, 10, 3).astype(np.float32)
        result = apply_tone_curve(img, [])
        np.testing.assert_array_equal(result, img)

    def test_single_point_curve(self):
        """Single point curve should return unchanged image."""
        img = np.random.rand(10, 10, 3).astype(np.float32)
        result = apply_tone_curve(img, [(0.5, 0.5)])
        # Should return img unchanged (warning logged)
        assert result.shape == img.shape

    def test_out_of_range_values(self):
        """Out of range values should be clipped."""
        img = np.array([[[1.5, -0.5, 0.5]]], dtype=np.float32)
        curve = create_linear_curve(3)

        result = apply_tone_curve(img, curve)
        assert result.max() <= 1.0
        assert result.min() >= 0.0

    def test_grayscale_hsl_conversion(self):
        """Grayscale values should have zero saturation."""
        gray = np.full((5, 5, 3), 0.5, dtype=np.float32)
        hsl = rgb_to_hsl(gray)

        # Saturation should be very close to 0
        np.testing.assert_allclose(hsl[:, :, 1], 0, atol=0.01)

    def test_black_white_hsl(self):
        """Black and white should convert correctly."""
        # Black
        black = np.zeros((1, 1, 3), dtype=np.float32)
        hsl_black = rgb_to_hsl(black)
        assert hsl_black[0, 0, 2] == pytest.approx(0, abs=0.01)  # L=0

        # White
        white = np.ones((1, 1, 3), dtype=np.float32)
        hsl_white = rgb_to_hsl(white)
        assert hsl_white[0, 0, 2] == pytest.approx(1, abs=0.01)  # L=1
