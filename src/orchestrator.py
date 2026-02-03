"""
orchestrator.py - Main orchestration logic for the color emulator.

Coordinates loading images, running optimization, and generating output.
"""

import json
import logging
import shutil
from pathlib import Path
from typing import Any, Dict, List, Tuple, Union

import numpy as np

from .image_utils import load_jpeg, save_image, resize_to_match
from .loss import PerceptualLoss
from .optimizer import StagedOptimizer
from .parameters import get_default_params, OPTIMIZATION_STAGES
from .renderer import RawRenderer
from .xmp_generator import XMPGenerator

logger = logging.getLogger(__name__)


class ColorEmulator:
    """
    Main orchestrator for the RAW-to-JPEG color science emulator.

    Coordinates:
    - Loading DNG/JPEG pairs
    - Running staged optimization
    - Generating XMP preset output
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the color emulator.

        Args:
            config: Configuration dictionary
        """
        self.config = config

        # Initialize components
        self.renderer = RawRenderer(use_camera_wb=config.get("use_camera_wb", True))
        self.loss_fn = PerceptualLoss(
            target_delta_e=config.get("target_delta_e", 3.0),
            use_luminance_weight=config.get("luminance_weight", True),
        )
        self.optimizer = StagedOptimizer(
            max_time_minutes=config.get("max_time_minutes", 60),
            population_size=config.get("population_size", 15),
            tolerance=config.get("tolerance", 0.01),
        )
        self.xmp_gen = XMPGenerator(
            preset_name=config.get("preset_name", "ColorEmulator")
        )

        # Curve configuration
        self.curve_points = config.get("curve_points", 5)
        self.rgb_curve_points = config.get("rgb_curve_points", 3)

        # Render sizes
        self.render_size = config.get("render_size", 1024)
        self.final_render_size = config.get("final_render_size", 2048)

        # Image data
        self.dng_paths: List[str] = []
        self.jpeg_paths: List[str] = []
        self.reference_images: List[np.ndarray] = []

        # Optimization state
        self._eval_count = 0

    def load_dataset(self, input_dir: Union[str, Path]) -> int:
        """
        Load DNG+JPEG pairs from input directory.

        Expected naming: IMG_001.dng + IMG_001.jpg (case-insensitive)

        Args:
            input_dir: Directory containing image pairs

        Returns:
            Number of pairs loaded
        """
        input_path = Path(input_dir)
        if not input_path.exists():
            raise FileNotFoundError(f"Input directory not found: {input_path}")

        # Find all DNG files (case-insensitive)
        dng_files = sorted(
            list(input_path.glob("*.dng")) + list(input_path.glob("*.DNG"))
        )

        loaded = 0
        for dng_path in dng_files:
            # Find matching JPEG
            base_name = dng_path.stem
            jpeg_candidates = [
                input_path / f"{base_name}.jpg",
                input_path / f"{base_name}.JPG",
                input_path / f"{base_name}.jpeg",
                input_path / f"{base_name}.JPEG",
            ]

            jpeg_path = None
            for candidate in jpeg_candidates:
                if candidate.exists():
                    jpeg_path = candidate
                    break

            if jpeg_path:
                self.dng_paths.append(str(dng_path))
                self.jpeg_paths.append(str(jpeg_path))

                # Pre-load and resize reference JPEG
                ref_img = load_jpeg(str(jpeg_path), max_size=self.render_size)
                self.reference_images.append(ref_img)

                logger.info(f"Loaded pair: {dng_path.name} + {jpeg_path.name}")
                loaded += 1
            else:
                logger.warning(f"No matching JPEG for {dng_path.name}")

        logger.info(f"Loaded {loaded} image pairs")

        if loaded == 0:
            raise ValueError(f"No valid DNG+JPEG pairs found in {input_dir}")

        # Preload DNG base renders
        logger.info("Preloading DNG renders...")
        self.renderer.preload(self.dng_paths)

        return loaded

    def _objective(self, params: Dict[str, Any]) -> float:
        """
        Compute total loss over all image pairs.

        This is the function being minimized by the optimizer.

        Args:
            params: Parameter dictionary

        Returns:
            Loss value (lower is better)
        """
        self._eval_count += 1
        rendered_images = []

        for dng_path, ref_img in zip(self.dng_paths, self.reference_images):
            rendered = self.renderer.render(
                dng_path, params, target_size=(self.render_size, self.render_size)
            )

            # Ensure same size as reference
            if rendered.shape[:2] != ref_img.shape[:2]:
                rendered = resize_to_match(rendered, ref_img.shape[:2])

            rendered_images.append(rendered)

        total_loss, metrics = self.loss_fn.compute_batch(
            rendered_images, self.reference_images
        )

        if self._eval_count % 50 == 0:
            logger.debug(
                f"Eval {self._eval_count}: loss={total_loss:.4f}, "
                f"mean_dE={metrics['mean_delta_e']:.2f}"
            )

        return total_loss

    def run(self, output_dir: Union[str, Path]) -> str:
        """
        Run the full optimization pipeline.

        Args:
            output_dir: Directory to save outputs

        Returns:
            Path to generated .xmp preset
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        logger.info("="*60)
        logger.info("Starting Color Emulation Optimization")
        logger.info("="*60)
        logger.info(f"Dataset: {len(self.dng_paths)} image pairs")
        logger.info(f"Max time: {self.config.get('max_time_minutes', 60)} minutes")
        logger.info(f"Target Delta E: {self.config.get('target_delta_e', 3.0)}")

        # Get initial parameters
        initial_params = get_default_params(self.curve_points, self.rgb_curve_points)

        # Compute initial loss
        initial_loss = self._objective(initial_params)
        logger.info(f"Initial loss: {initial_loss:.4f}")

        # Reset eval counter for optimization
        self._eval_count = 0

        # Run staged optimization
        best_params, history = self.optimizer.optimize(
            objective_fn=self._objective,
            initial_params=initial_params,
            curve_points=self.curve_points,
            rgb_curve_points=self.rgb_curve_points,
            stages=OPTIMIZATION_STAGES,
        )

        # Compute final loss
        final_loss = self._objective(best_params)
        logger.info(f"Final loss: {final_loss:.4f}")
        logger.info(f"Improvement: {initial_loss - final_loss:.4f} ({(1 - final_loss/initial_loss)*100:.1f}%)")

        # Generate XMP preset
        xmp_path = output_path / "color_emulator_preset.xmp"
        self.xmp_gen.generate(best_params, str(xmp_path))

        # Validate XMP
        if self.xmp_gen.validate_xmp(xmp_path):
            logger.info("XMP validation: PASSED")
        else:
            logger.warning("XMP validation: FAILED")

        # Save optimization history
        history["initial_loss"] = initial_loss
        history["final_loss"] = final_loss
        history["improvement"] = initial_loss - final_loss
        history["improvement_pct"] = (1 - final_loss / initial_loss) * 100

        history_path = output_path / "optimization_history.json"
        with open(history_path, "w") as f:
            json.dump(history, f, indent=2, default=str)
        logger.info(f"History saved: {history_path}")

        # Save optimized parameters
        params_path = output_path / "optimized_params.json"
        self._save_params(best_params, params_path)

        # Render test images with final parameters
        self._render_test_images(best_params, output_path)

        return str(xmp_path)

    def _render_test_images(
        self,
        params: Dict[str, Any],
        output_dir: Path,
    ) -> None:
        """
        Render test images with optimized parameters.

        Args:
            params: Optimized parameters
            output_dir: Output directory
        """
        test_render_dir = output_dir / "test_renders"
        test_render_dir.mkdir(exist_ok=True)

        logger.info("Rendering test images...")

        for i, (dng_path, jpeg_path) in enumerate(zip(self.dng_paths, self.jpeg_paths)):
            # Render with optimized parameters
            rendered = self.renderer.render(
                dng_path, params, target_size=(self.final_render_size, self.final_render_size)
            )

            base_name = Path(dng_path).stem

            # Save emulated image
            emulated_path = test_render_dir / f"{base_name}_emulated.jpg"
            save_image(rendered, emulated_path)

            # Copy reference for comparison
            ref_path = test_render_dir / f"{base_name}_reference.jpg"
            shutil.copy(jpeg_path, ref_path)

            logger.debug(f"Saved test render: {base_name}")

        logger.info(f"Test renders saved to: {test_render_dir}")

    def _save_params(
        self,
        params: Dict[str, Any],
        output_path: Path,
    ) -> None:
        """
        Save optimized parameters to JSON file.

        Args:
            params: Parameter dictionary
            output_path: Output file path
        """
        # Convert curve tuples to lists for JSON serialization
        serializable = {}
        for key, value in params.items():
            if isinstance(value, list) and value and isinstance(value[0], tuple):
                serializable[key] = [[p[0], p[1]] for p in value]
            else:
                serializable[key] = value

        with open(output_path, "w") as f:
            json.dump(serializable, f, indent=2)

        logger.debug(f"Parameters saved: {output_path}")

    def get_metrics(self, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Compute detailed metrics for current or given parameters.

        Args:
            params: Parameters to evaluate (uses defaults if None)

        Returns:
            Dictionary of metrics
        """
        if params is None:
            params = get_default_params(self.curve_points, self.rgb_curve_points)

        rendered_images = []
        for dng_path, ref_img in zip(self.dng_paths, self.reference_images):
            rendered = self.renderer.render(
                dng_path, params, target_size=(self.render_size, self.render_size)
            )
            if rendered.shape[:2] != ref_img.shape[:2]:
                rendered = resize_to_match(rendered, ref_img.shape[:2])
            rendered_images.append(rendered)

        _, metrics = self.loss_fn.compute_batch(rendered_images, self.reference_images)
        return metrics
