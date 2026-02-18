"""
loss.py - CIEDE2000-based perceptual loss computation.

Uses scikit-image's implementation of the CIEDE2000 color difference formula.
"""

import logging
from typing import Dict, List, Tuple

import numpy as np
from skimage.color import rgb2lab, deltaE_ciede2000
from skimage.transform import resize

logger = logging.getLogger(__name__)


class PerceptualLoss:
    """
    Perceptual loss calculator using CIEDE2000 Delta E metric.

    This is the industry-standard metric for measuring perceptual color difference.
    Delta E < 1: Not perceptible by human eyes
    Delta E 1-2: Perceptible through close observation
    Delta E 2-10: Perceptible at a glance
    Delta E > 10: Colors are more different than similar
    """

    def __init__(
        self,
        target_delta_e: float = 3.0,
        use_luminance_weight: bool = True,
    ):
        """
        Initialize loss calculator.

        Args:
            target_delta_e: "Good enough" threshold for Delta E
            use_luminance_weight: Weight errors more in midtones (where eye is sensitive)
        """
        self.target_delta_e = target_delta_e
        self.use_luminance_weight = use_luminance_weight

    def compute(
        self,
        rendered: np.ndarray,
        reference: np.ndarray,
    ) -> Tuple[float, Dict[str, float]]:
        """
        Compute perceptual difference between rendered and reference images.

        Args:
            rendered: Rendered image (float32, 0-1, RGB)
            reference: Reference JPEG (float32, 0-1, RGB)

        Returns:
            loss: Scalar loss value (lower is better)
            metrics: Dictionary with detailed metrics
        """
        # Ensure same size
        if rendered.shape != reference.shape:
            reference = resize(
                reference,
                rendered.shape[:2],
                anti_aliasing=True,
                preserve_range=True,
            ).astype(np.float32)

        # Clip to valid range
        rendered = np.clip(rendered, 0.0, 1.0)
        reference = np.clip(reference, 0.0, 1.0)

        # Convert to LAB
        rendered_lab = rgb2lab(rendered)
        reference_lab = rgb2lab(reference)

        # Compute per-pixel Delta E (CIEDE2000)
        delta_e = deltaE_ciede2000(reference_lab, rendered_lab)

        # Optional: weight by luminance (emphasize midtones)
        if self.use_luminance_weight:
            L = reference_lab[:, :, 0] / 100.0  # Normalize to 0-1
            # Bell curve weight: highest at L=0.5
            weight = np.exp(-((L - 0.5) ** 2) / 0.2)
            weight = weight / (weight.mean() + 1e-10)  # Normalize
            weighted_delta_e = delta_e * weight
        else:
            weighted_delta_e = delta_e

        # Aggregate metrics
        mean_delta_e = float(np.mean(weighted_delta_e))
        median_delta_e = float(np.median(delta_e))
        p95_delta_e = float(np.percentile(delta_e, 95))
        max_delta_e = float(np.max(delta_e))

        # Primary loss: mean weighted Delta E
        loss = mean_delta_e

        metrics = {
            "mean_delta_e": float(np.mean(delta_e)),  # Unweighted for reporting
            "weighted_mean_delta_e": mean_delta_e,
            "median_delta_e": median_delta_e,
            "p95_delta_e": p95_delta_e,
            "max_delta_e": max_delta_e,
            "below_threshold_pct": float((delta_e < self.target_delta_e).mean() * 100),
        }

        return loss, metrics

    def compute_batch(
        self,
        rendered_list: List[np.ndarray],
        reference_list: List[np.ndarray],
    ) -> Tuple[float, Dict[str, float]]:
        """
        Compute average loss over multiple image pairs.

        Args:
            rendered_list: List of rendered images
            reference_list: List of reference images

        Returns:
            total_loss: Average loss across all pairs
            aggregate_metrics: Aggregated metrics
        """
        if len(rendered_list) != len(reference_list):
            raise ValueError(
                f"Mismatched list lengths: {len(rendered_list)} rendered vs {len(reference_list)} reference"
            )

        if len(rendered_list) == 0:
            raise ValueError("Empty image lists provided")

        losses = []
        all_metrics = []

        for rendered, reference in zip(rendered_list, reference_list):
            loss, metrics = self.compute(rendered, reference)
            losses.append(loss)
            all_metrics.append(metrics)

        total_loss = float(np.mean(losses))

        aggregate_metrics = {
            "total_loss": total_loss,
            "per_image_losses": losses,
            "mean_delta_e": float(np.mean([m["mean_delta_e"] for m in all_metrics])),
            "median_delta_e": float(np.mean([m["median_delta_e"] for m in all_metrics])),
            "p95_delta_e": float(np.mean([m["p95_delta_e"] for m in all_metrics])),
            "worst_image_loss": float(max(losses)),
            "best_image_loss": float(min(losses)),
            "below_threshold_pct": float(np.mean([m["below_threshold_pct"] for m in all_metrics])),
        }

        return total_loss, aggregate_metrics


def compute_delta_e(
    img1: np.ndarray,
    img2: np.ndarray,
) -> np.ndarray:
    """
    Compute per-pixel Delta E between two images.

    Args:
        img1: First image (float32, 0-1, RGB)
        img2: Second image (float32, 0-1, RGB)

    Returns:
        Per-pixel Delta E values
    """
    img1 = np.clip(img1, 0.0, 1.0)
    img2 = np.clip(img2, 0.0, 1.0)

    lab1 = rgb2lab(img1)
    lab2 = rgb2lab(img2)

    return deltaE_ciede2000(lab1, lab2)


def quick_loss(
    rendered: np.ndarray,
    reference: np.ndarray,
) -> float:
    """
    Quick loss computation without detailed metrics.

    Useful for optimization inner loops.

    Args:
        rendered: Rendered image (float32, 0-1, RGB)
        reference: Reference image (float32, 0-1, RGB)

    Returns:
        Mean Delta E loss
    """
    # Ensure same size
    if rendered.shape != reference.shape:
        reference = resize(
            reference,
            rendered.shape[:2],
            anti_aliasing=True,
            preserve_range=True,
        ).astype(np.float32)

    rendered = np.clip(rendered, 0.0, 1.0)
    reference = np.clip(reference, 0.0, 1.0)

    rendered_lab = rgb2lab(rendered)
    reference_lab = rgb2lab(reference)

    delta_e = deltaE_ciede2000(reference_lab, rendered_lab)
    return float(np.mean(delta_e))
