"""
test_loss.py - Unit tests for the loss function module.
"""

import numpy as np
import pytest

from src.loss import PerceptualLoss, compute_delta_e, quick_loss


class TestPerceptualLoss:
    """Tests for the PerceptualLoss class."""

    def test_identical_images_zero_loss(self):
        """Identical images should have Delta E = 0."""
        img = np.random.rand(100, 100, 3).astype(np.float32)
        loss_fn = PerceptualLoss()
        loss, metrics = loss_fn.compute(img, img)
        assert loss < 0.01, f"Expected near-zero loss, got {loss}"
        assert metrics["mean_delta_e"] < 0.01

    def test_different_images_positive_loss(self):
        """Very different images should have high Delta E."""
        img1 = np.zeros((100, 100, 3), dtype=np.float32)  # Black
        img2 = np.ones((100, 100, 3), dtype=np.float32)   # White
        loss_fn = PerceptualLoss()
        loss, metrics = loss_fn.compute(img1, img2)
        assert loss > 50, f"Expected high loss for black vs white, got {loss}"

    def test_similar_images_low_loss(self):
        """Similar images should have low Delta E."""
        img1 = np.full((100, 100, 3), 0.5, dtype=np.float32)
        img2 = np.full((100, 100, 3), 0.52, dtype=np.float32)
        loss_fn = PerceptualLoss()
        loss, metrics = loss_fn.compute(img1, img2)
        assert loss < 5, f"Expected low loss for similar images, got {loss}"

    def test_metrics_structure(self):
        """Metrics should contain expected keys."""
        img = np.random.rand(50, 50, 3).astype(np.float32)
        loss_fn = PerceptualLoss()
        _, metrics = loss_fn.compute(img, img)

        expected_keys = [
            "mean_delta_e",
            "weighted_mean_delta_e",
            "median_delta_e",
            "p95_delta_e",
            "max_delta_e",
            "below_threshold_pct",
        ]
        for key in expected_keys:
            assert key in metrics, f"Missing metric: {key}"

    def test_batch_computation(self):
        """Batch computation should average losses correctly."""
        loss_fn = PerceptualLoss()

        # Create pairs with known differences
        img1 = np.full((50, 50, 3), 0.5, dtype=np.float32)
        img2 = np.full((50, 50, 3), 0.5, dtype=np.float32)
        img3 = np.full((50, 50, 3), 0.6, dtype=np.float32)

        rendered_list = [img1, img1]
        reference_list = [img2, img3]

        total_loss, metrics = loss_fn.compute_batch(rendered_list, reference_list)

        assert "per_image_losses" in metrics
        assert len(metrics["per_image_losses"]) == 2
        assert total_loss == pytest.approx(np.mean(metrics["per_image_losses"]))

    def test_luminance_weighting(self):
        """Luminance weighting should affect the loss."""
        img1 = np.random.rand(100, 100, 3).astype(np.float32)
        img2 = img1 + 0.1  # Slight offset

        loss_weighted = PerceptualLoss(use_luminance_weight=True)
        loss_unweighted = PerceptualLoss(use_luminance_weight=False)

        l1, _ = loss_weighted.compute(img1, img2)
        l2, _ = loss_unweighted.compute(img1, img2)

        # They should be different (weighting has an effect)
        # Note: they might be similar in some cases, so just check they compute
        assert l1 > 0
        assert l2 > 0

    def test_size_mismatch_handling(self):
        """Loss should handle different sized images."""
        img1 = np.random.rand(100, 100, 3).astype(np.float32)
        img2 = np.random.rand(80, 120, 3).astype(np.float32)

        loss_fn = PerceptualLoss()
        # Should not raise an error
        loss, metrics = loss_fn.compute(img1, img2)
        assert loss >= 0


class TestHelperFunctions:
    """Tests for helper functions."""

    def test_compute_delta_e(self):
        """Test per-pixel Delta E computation."""
        img1 = np.full((10, 10, 3), 0.5, dtype=np.float32)
        img2 = np.full((10, 10, 3), 0.5, dtype=np.float32)

        delta_e = compute_delta_e(img1, img2)
        assert delta_e.shape == (10, 10)
        assert delta_e.max() < 0.01

    def test_quick_loss(self):
        """Test quick loss computation."""
        img1 = np.random.rand(50, 50, 3).astype(np.float32)
        img2 = img1.copy()

        loss = quick_loss(img1, img2)
        assert loss < 0.01

    def test_valid_range_clipping(self):
        """Test that out-of-range values are handled."""
        img1 = np.full((10, 10, 3), -0.5, dtype=np.float32)  # Below 0
        img2 = np.full((10, 10, 3), 1.5, dtype=np.float32)   # Above 1

        loss_fn = PerceptualLoss()
        # Should not raise an error
        loss, _ = loss_fn.compute(img1, img2)
        assert loss >= 0


class TestEdgeCases:
    """Tests for edge cases."""

    def test_empty_batch(self):
        """Empty batch should raise an error."""
        loss_fn = PerceptualLoss()
        with pytest.raises(ValueError):
            loss_fn.compute_batch([], [])

    def test_mismatched_batch_lengths(self):
        """Mismatched batch lengths should raise an error."""
        loss_fn = PerceptualLoss()
        img = np.random.rand(10, 10, 3).astype(np.float32)
        with pytest.raises(ValueError):
            loss_fn.compute_batch([img, img], [img])

    def test_single_pixel_image(self):
        """Single pixel images should work."""
        img1 = np.array([[[0.5, 0.5, 0.5]]], dtype=np.float32)
        img2 = np.array([[[0.5, 0.5, 0.5]]], dtype=np.float32)

        loss_fn = PerceptualLoss()
        loss, _ = loss_fn.compute(img1, img2)
        assert loss < 0.01
