"""
optimizer.py - Staged optimization using scipy.optimize.differential_evolution.

Implements a staged optimization strategy: tone_curve -> hsl -> calibration.
"""

import logging
import time
from typing import Any, Callable, Dict, List, Tuple

import numpy as np
from scipy.optimize import differential_evolution

from .parameters import (
    OPTIMIZATION_STAGES,
    get_stage_bounds,
    get_stage_defaults,
    update_params_from_stage,
    get_stage_values_from_params,
)

logger = logging.getLogger(__name__)


class StagedOptimizer:
    """
    Staged optimization using differential evolution.

    Optimizes parameters in stages to reduce search space complexity:
    1. tone_curve: Tone curves affect overall brightness/contrast
    2. hsl: HSL adjustments for color-specific tuning
    3. calibration: Camera calibration for primary color shifts
    """

    def __init__(
        self,
        max_time_minutes: int = 60,
        population_size: int = 15,
        tolerance: float = 0.01,
        seed: int = 42,
    ):
        """
        Initialize staged optimizer.

        Args:
            max_time_minutes: Maximum total runtime
            population_size: DE population multiplier (actual = param_count * multiplier)
            tolerance: Convergence tolerance
            seed: Random seed for reproducibility
        """
        self.max_time_minutes = max_time_minutes
        self.population_size = population_size
        self.tolerance = tolerance
        self.seed = seed

        # Time budget per stage (rough allocation)
        self.stage_time_ratios = {
            "tone_curve": 0.4,    # 40% - most important
            "hsl": 0.35,          # 35% - many parameters
            "calibration": 0.25,  # 25% - fewer parameters
        }

        # Iteration tracking
        self._iteration_count = 0
        self._best_loss = float("inf")
        self._start_time = None

    def optimize(
        self,
        objective_fn: Callable[[Dict[str, Any]], float],
        initial_params: Dict[str, Any],
        curve_points: int = 5,
        rgb_curve_points: int = 3,
        stages: List[str] = None,
    ) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """
        Run staged optimization.

        Args:
            objective_fn: Function that takes params dict, returns loss
            initial_params: Starting parameter values
            curve_points: Number of main tone curve points
            rgb_curve_points: Number of RGB curve points
            stages: List of stage names in order (default: all stages)

        Returns:
            best_params: Optimized parameters
            history: Optimization history and metrics
        """
        if stages is None:
            stages = OPTIMIZATION_STAGES

        current_params = initial_params.copy()
        history = {"stages": [], "total_time": 0, "total_iterations": 0}
        self._start_time = time.time()
        total_budget = self.max_time_minutes * 60

        for stage in stages:
            stage_start = time.time()
            elapsed = stage_start - self._start_time
            remaining = total_budget - elapsed

            if remaining <= 0:
                logger.warning("Time budget exhausted, skipping remaining stages")
                break

            # Calculate time budget for this stage
            time_ratio = self.stage_time_ratios.get(stage, 0.33)
            stage_budget = min(remaining, total_budget * time_ratio)

            logger.info(f"{'='*50}")
            logger.info(f"Starting Stage: {stage.upper()}")
            logger.info(f"Time budget: {stage_budget/60:.1f} minutes")

            # Get bounds and defaults for this stage
            bounds = get_stage_bounds(stage, curve_points, rgb_curve_points)
            defaults = get_stage_values_from_params(current_params, stage, curve_points, rgb_curve_points)

            if not bounds:
                logger.warning(f"No parameters for stage {stage}, skipping")
                continue

            num_params = len(bounds)
            logger.info(f"Optimizing {num_params} parameters")

            # Create objective wrapper for this stage
            def stage_objective(x: np.ndarray) -> float:
                test_params = update_params_from_stage(
                    current_params, stage, x.tolist(), curve_points, rgb_curve_points
                )
                return objective_fn(test_params)

            # Reset iteration tracking
            self._iteration_count = 0
            self._best_loss = float("inf")

            # Run differential evolution
            try:
                result = differential_evolution(
                    stage_objective,
                    bounds=bounds,
                    x0=defaults,
                    maxiter=500,
                    tol=self.tolerance,
                    seed=self.seed,
                    workers=1,
                    disp=False,
                    polish=True,
                    callback=lambda xk, convergence: self._callback(xk, convergence, stage, stage_budget, stage_start),
                    updating="deferred",
                    mutation=(0.5, 1.0),
                    recombination=0.7,
                )

                # Update current params with optimized values
                current_params = update_params_from_stage(
                    current_params, stage, result.x.tolist(), curve_points, rgb_curve_points
                )

                stage_time = time.time() - stage_start

                stage_history = {
                    "stage": stage,
                    "final_loss": float(result.fun),
                    "iterations": result.nit,
                    "function_evals": result.nfev,
                    "time_seconds": stage_time,
                    "success": result.success,
                    "message": result.message,
                }
                history["stages"].append(stage_history)
                history["total_iterations"] += result.nit

                logger.info(f"Stage {stage} complete:")
                logger.info(f"  Loss: {result.fun:.4f}")
                logger.info(f"  Iterations: {result.nit}")
                logger.info(f"  Time: {stage_time/60:.1f} min")

            except Exception as e:
                logger.error(f"Optimization error in stage {stage}: {e}")
                stage_history = {
                    "stage": stage,
                    "error": str(e),
                    "time_seconds": time.time() - stage_start,
                }
                history["stages"].append(stage_history)

        history["total_time"] = time.time() - self._start_time
        logger.info(f"{'='*50}")
        logger.info(f"Optimization complete")
        logger.info(f"Total time: {history['total_time']/60:.1f} minutes")

        return current_params, history

    def _callback(
        self,
        xk: np.ndarray,
        convergence: float,
        stage: str,
        time_budget: float,
        start_time: float,
    ) -> bool:
        """
        Callback for progress logging and time budget enforcement.

        Args:
            xk: Current solution vector
            convergence: Convergence value (0-1)
            stage: Current stage name
            time_budget: Time budget for this stage in seconds
            start_time: Stage start time

        Returns:
            True to stop optimization, False to continue
        """
        self._iteration_count += 1
        elapsed = time.time() - start_time

        # Log progress every 10 iterations
        if self._iteration_count % 10 == 0:
            logger.info(
                f"  [{stage}] Iter {self._iteration_count}: "
                f"convergence={convergence:.4f}, "
                f"elapsed={elapsed/60:.1f}min"
            )

        # Check time budget
        if elapsed > time_budget:
            logger.info(f"  [{stage}] Time budget exhausted, stopping early")
            return True

        return False


class SimpleOptimizer:
    """
    Simpler single-stage optimizer for quick tests.
    """

    def __init__(
        self,
        max_iterations: int = 100,
        tolerance: float = 0.01,
        seed: int = 42,
    ):
        """
        Initialize simple optimizer.

        Args:
            max_iterations: Maximum number of iterations
            tolerance: Convergence tolerance
            seed: Random seed
        """
        self.max_iterations = max_iterations
        self.tolerance = tolerance
        self.seed = seed

    def optimize(
        self,
        objective_fn: Callable[[np.ndarray], float],
        bounds: List[Tuple[float, float]],
        x0: np.ndarray = None,
    ) -> Tuple[np.ndarray, float, Dict[str, Any]]:
        """
        Run optimization.

        Args:
            objective_fn: Objective function
            bounds: Parameter bounds
            x0: Initial guess

        Returns:
            best_x: Optimized parameters
            best_loss: Final loss
            info: Optimization info
        """
        result = differential_evolution(
            objective_fn,
            bounds=bounds,
            x0=x0,
            maxiter=self.max_iterations,
            tol=self.tolerance,
            seed=self.seed,
            workers=1,
            disp=False,
            polish=True,
        )

        info = {
            "iterations": result.nit,
            "function_evals": result.nfev,
            "success": result.success,
            "message": result.message,
        }

        return result.x, result.fun, info
