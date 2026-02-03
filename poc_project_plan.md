# RAW-to-JPEG Color Science Emulator: PoC Implementation Plan

## Executive Summary

This document provides a complete, implementation-ready plan for building a Proof of Concept that reverse-engineers camera JPEG color science into Lightroom presets. The PoC will accept 10 DNG+JPEG pairs from a Ricoh GR II and output an optimized `.xmp` preset file.

---

## 1. Technical Decisions Summary

| Decision | Choice | Rationale |
|----------|--------|-----------|
| RAW Rendering | `rawpy` (LibRaw wrapper) | Free, cross-platform, Python-native. Adobe DNG SDK requires C++ compilation and has licensing complexity. rawpy supports DNG natively. |
| Loss Function | **CIEDE2000 (Delta E)** in LAB space | Industry-standard perceptual color difference metric. Available via `skimage.color.deltaE_ciede2000`. |
| Optimizer | **Differential Evolution** (primary) | Global optimizer, avoids local minima in non-convex space. ~30-60 min runtime acceptable. |
| Optimization Strategy | **Staged** (Tone → HSL → Calibration) | Reduces search space per stage; tone affects everything downstream. |
| Output Format | `.xmp` preset file | Native Lightroom Classic format, works with LrC 7.3+ and Camera Raw. |
| Platform | macOS (Apple Silicon compatible), Linux-ready | Python-only dependencies ensure portability. |

---

## 2. Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                        CLI Entry Point                              │
│                      (color_emulator.py)                            │
└─────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     Orchestrator Module                             │
│  - Load DNG/JPEG pairs                                              │
│  - Run staged optimization                                          │
│  - Generate final XMP                                               │
└─────────────────────────────────────────────────────────────────────┘
          │                     │                     │
          ▼                     ▼                     ▼
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│  RAW Renderer   │  │  Loss Calculator │  │  XMP Generator  │
│  (rawpy-based)  │  │  (CIEDE2000)     │  │                 │
└─────────────────┘  └─────────────────┘  └─────────────────┘
          │                     │                     │
          ▼                     ▼                     ▼
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│ Parameter Model │  │  Image Utils    │  │  Config/Logging │
│ (LR params)     │  │  (resize, LAB)  │  │                 │
└─────────────────┘  └─────────────────┘  └─────────────────┘
```

---

## 3. File Structure

```
color-emulator/
├── README.md
├── requirements.txt
├── config.yaml                    # User-configurable settings
├── color_emulator.py              # CLI entry point
├── src/
│   ├── __init__.py
│   ├── orchestrator.py            # Main optimization loop
│   ├── renderer.py                # RAW → RGB rendering via rawpy
│   ├── parameters.py              # Lightroom parameter definitions & bounds
│   ├── loss.py                    # CIEDE2000 loss computation
│   ├── optimizer.py               # SciPy optimizer wrapper
│   ├── xmp_generator.py           # Generate .xmp preset files
│   ├── image_utils.py             # Image loading, resizing, color space
│   └── tone_curve.py              # Tone curve application & fitting
├── data/
│   └── input/                     # Place DNG+JPEG pairs here
├── output/
│   ├── preset.xmp                 # Final optimized preset
│   └── test_renders/              # Rendered test images
└── tests/
    ├── test_loss.py
    ├── test_renderer.py
    └── test_xmp.py
```

---

## 4. Module Specifications

### 4.1 `parameters.py` — Lightroom Parameter Model

Defines all optimizable parameters with bounds and defaults. Curve points are configurable via config.yaml.

```python
# Parameter groups and their optimization order
OPTIMIZATION_STAGES = [
    "tone_curve",      # Stage 1: Tone/Exposure via curves
    "hsl",             # Stage 2: Color shifts
    "calibration"      # Stage 3: Sensor-level color
]

def get_curve_parameters(curve_points: int = 5, rgb_curve_points: int = 3) -> dict:
    """
    Generate curve parameter definitions based on config.
    
    Args:
        curve_points: Number of points for main tone curve (from config)
        rgb_curve_points: Number of points for RGB channel curves (from config)
    """
    return {
        # Stage 1: Tone Curve (Point Curve - configurable control points)
        # Each point has (input, output) from 0-255, normalized to 0-1
        "ToneCurvePV2012": {
            "type": "point_curve",
            "points": curve_points,  # Configurable via config.yaml
            "bounds": (0.0, 1.0),
            "default": "linear"
        },
        
        # RGB Channel Curves (for color/WB correction without touching WB slider)
        "ToneCurvePV2012Red": { 
            "type": "point_curve", 
            "points": rgb_curve_points,  # Configurable via config.yaml
            "bounds": (0.0, 1.0) 
        },
        "ToneCurvePV2012Green": { 
            "type": "point_curve", 
            "points": rgb_curve_points, 
            "bounds": (0.0, 1.0) 
        },
        "ToneCurvePV2012Blue": { 
            "type": "point_curve", 
            "points": rgb_curve_points, 
            "bounds": (0.0, 1.0) 
        },
    }

# Static parameters (not dependent on config)
STATIC_PARAMETERS = {
    # Stage 2: HSL Adjustments (-100 to +100)
    "HueAdjustmentRed": { "bounds": (-30, 30), "default": 0 },
    "HueAdjustmentOrange": { "bounds": (-30, 30), "default": 0 },
    "HueAdjustmentYellow": { "bounds": (-30, 30), "default": 0 },
    "HueAdjustmentGreen": { "bounds": (-30, 30), "default": 0 },
    "HueAdjustmentAqua": { "bounds": (-30, 30), "default": 0 },
    "HueAdjustmentBlue": { "bounds": (-30, 30), "default": 0 },
    "HueAdjustmentPurple": { "bounds": (-30, 30), "default": 0 },
    "HueAdjustmentMagenta": { "bounds": (-30, 30), "default": 0 },
    
    "SaturationAdjustmentRed": { "bounds": (-50, 50), "default": 0 },
    "SaturationAdjustmentOrange": { "bounds": (-50, 50), "default": 0 },
    "SaturationAdjustmentYellow": { "bounds": (-50, 50), "default": 0 },
    "SaturationAdjustmentGreen": { "bounds": (-50, 50), "default": 0 },
    "SaturationAdjustmentAqua": { "bounds": (-50, 50), "default": 0 },
    "SaturationAdjustmentBlue": { "bounds": (-50, 50), "default": 0 },
    "SaturationAdjustmentPurple": { "bounds": (-50, 50), "default": 0 },
    "SaturationAdjustmentMagenta": { "bounds": (-50, 50), "default": 0 },
    
    "LuminanceAdjustmentRed": { "bounds": (-50, 50), "default": 0 },
    "LuminanceAdjustmentOrange": { "bounds": (-50, 50), "default": 0 },
    "LuminanceAdjustmentYellow": { "bounds": (-50, 50), "default": 0 },
    "LuminanceAdjustmentGreen": { "bounds": (-50, 50), "default": 0 },
    "LuminanceAdjustmentAqua": { "bounds": (-50, 50), "default": 0 },
    "LuminanceAdjustmentBlue": { "bounds": (-50, 50), "default": 0 },
    "LuminanceAdjustmentPurple": { "bounds": (-50, 50), "default": 0 },
    "LuminanceAdjustmentMagenta": { "bounds": (-50, 50), "default": 0 },
    
    # Stage 3: Camera Calibration (-100 to +100)
    "ShadowTint": { "bounds": (-100, 100), "default": 0 },
    "RedHue": { "bounds": (-100, 100), "default": 0 },
    "RedSaturation": { "bounds": (-100, 100), "default": 0 },
    "GreenHue": { "bounds": (-100, 100), "default": 0 },
    "GreenSaturation": { "bounds": (-100, 100), "default": 0 },
    "BlueHue": { "bounds": (-100, 100), "default": 0 },
    "BlueSaturation": { "bounds": (-100, 100), "default": 0 },
}

# Parameter count calculation (with default config values):
# Stage 1 (Tone): 5*2 (main) + 3*3*2 (RGB) = 28 params
# Stage 2 (HSL): 8*3 = 24 params
# Stage 3 (Calibration): 7 params
# Total: 59 parameters (varies with curve_points config)
```

**Implementation Notes:**
- Point curves are flattened to 1D arrays for optimization
- RGB curves handle "white balance equivalent" adjustments
- Bounds are intentionally constrained to prevent extreme values
- `curve_points` and `rgb_curve_points` are read from config.yaml


### 4.2 `renderer.py` — RAW Rendering Engine

**Critical Design Decision:** Since we cannot use Adobe DNG SDK headlessly in Python, we use `rawpy` (LibRaw) for rendering. This creates a **known parity gap** between our renders and Lightroom's internal engine.

**Mitigation Strategy:**
1. Focus on **relative** color differences, not absolute matching
2. Use consistent rendering settings
3. Document this limitation clearly

```python
"""
renderer.py - RAW to RGB rendering using rawpy/LibRaw

IMPORTANT: This renderer does NOT match Lightroom's internal engine exactly.
The optimizer finds parameters that work best within rawpy's rendering,
which should translate reasonably (but not perfectly) to Lightroom.
"""

import rawpy
import numpy as np
from typing import Dict, Any, Tuple
from .tone_curve import apply_tone_curve
from .parameters import PARAMETERS

class RawRenderer:
    def __init__(self, use_camera_wb: bool = True):
        """
        Initialize renderer.
        
        Args:
            use_camera_wb: If True, use camera's recorded white balance.
                          We lock this to True to match in-camera JPEG WB.
        """
        self.use_camera_wb = use_camera_wb
    
    def render(
        self, 
        dng_path: str, 
        params: Dict[str, Any],
        target_size: Tuple[int, int] = (1024, 1024)
    ) -> np.ndarray:
        """
        Render a DNG file with the given Lightroom-style parameters.
        
        Args:
            dng_path: Path to DNG file
            params: Dictionary of Lightroom parameters
            target_size: Max dimension for output (for speed)
        
        Returns:
            RGB image as numpy array (float32, 0-1 range)
        """
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
        
        # Apply our parameter pipeline
        rgb = self._apply_parameters(rgb, params)
        
        # Resize for speed
        rgb = self._resize(rgb, target_size)
        
        return rgb
    
    def _apply_parameters(self, rgb: np.ndarray, params: Dict) -> np.ndarray:
        """Apply Lightroom-equivalent transformations."""
        
        # 1. Apply main tone curve
        if "ToneCurvePV2012" in params:
            rgb = apply_tone_curve(rgb, params["ToneCurvePV2012"])
        
        # 2. Apply RGB channel curves (for WB-like adjustments)
        if "ToneCurvePV2012Red" in params:
            rgb[:, :, 0] = apply_tone_curve(
                rgb[:, :, 0], params["ToneCurvePV2012Red"]
            )
        if "ToneCurvePV2012Green" in params:
            rgb[:, :, 1] = apply_tone_curve(
                rgb[:, :, 1], params["ToneCurvePV2012Green"]
            )
        if "ToneCurvePV2012Blue" in params:
            rgb[:, :, 2] = apply_tone_curve(
                rgb[:, :, 2], params["ToneCurvePV2012Blue"]
            )
        
        # 3. Apply HSL adjustments
        rgb = self._apply_hsl(rgb, params)
        
        # 4. Apply camera calibration
        rgb = self._apply_calibration(rgb, params)
        
        # Ensure valid range
        return np.clip(rgb, 0.0, 1.0)
    
    def _apply_hsl(self, rgb: np.ndarray, params: Dict) -> np.ndarray:
        """Apply HSL adjustments per color channel."""
        # Convert to HSL, apply shifts, convert back
        # Implementation uses vectorized numpy operations
        # ... (detailed implementation in full code)
        return rgb
    
    def _apply_calibration(self, rgb: np.ndarray, params: Dict) -> np.ndarray:
        """Apply camera calibration primary shifts."""
        # These affect the underlying color matrix
        # Simplified approximation: adjust RGB primaries
        # ... (detailed implementation in full code)
        return rgb
    
    def _resize(self, rgb: np.ndarray, max_size: Tuple[int, int]) -> np.ndarray:
        """Resize image maintaining aspect ratio."""
        from skimage.transform import resize
        h, w = rgb.shape[:2]
        scale = min(max_size[0] / h, max_size[1] / w)
        if scale < 1:
            new_h, new_w = int(h * scale), int(w * scale)
            rgb = resize(rgb, (new_h, new_w), anti_aliasing=True)
        return rgb
```


### 4.3 `loss.py` — Perceptual Loss Function

```python
"""
loss.py - CIEDE2000-based perceptual loss computation
"""

import numpy as np
from skimage.color import rgb2lab, deltaE_ciede2000
from typing import List, Tuple

class PerceptualLoss:
    def __init__(
        self,
        target_delta_e: float = 3.0,
        use_luminance_weight: bool = True
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
        reference: np.ndarray
    ) -> Tuple[float, dict]:
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
            from skimage.transform import resize
            reference = resize(reference, rendered.shape[:2], anti_aliasing=True)
        
        # Convert to LAB
        rendered_lab = rgb2lab(rendered)
        reference_lab = rgb2lab(reference)
        
        # Compute per-pixel Delta E (CIEDE2000)
        delta_e = deltaE_ciede2000(reference_lab, rendered_lab)
        
        # Optional: weight by luminance (emphasize midtones)
        if self.use_luminance_weight:
            L = reference_lab[:, :, 0] / 100.0  # 0-1
            # Bell curve weight: highest at L=0.5
            weight = np.exp(-((L - 0.5) ** 2) / 0.2)
            weight = weight / weight.mean()  # Normalize
            delta_e = delta_e * weight
        
        # Aggregate metrics
        mean_delta_e = float(np.mean(delta_e))
        median_delta_e = float(np.median(delta_e))
        p95_delta_e = float(np.percentile(delta_e, 95))
        
        # Primary loss: mean Delta E
        loss = mean_delta_e
        
        metrics = {
            "mean_delta_e": mean_delta_e,
            "median_delta_e": median_delta_e,
            "p95_delta_e": p95_delta_e,
            "below_threshold_pct": float((delta_e < self.target_delta_e).mean() * 100)
        }
        
        return loss, metrics
    
    def compute_batch(
        self,
        rendered_list: List[np.ndarray],
        reference_list: List[np.ndarray]
    ) -> Tuple[float, dict]:
        """
        Compute average loss over multiple image pairs.
        
        Returns:
            total_loss: Average loss across all pairs
            aggregate_metrics: Aggregated metrics
        """
        losses = []
        all_metrics = []
        
        for rendered, reference in zip(rendered_list, reference_list):
            loss, metrics = self.compute(rendered, reference)
            losses.append(loss)
            all_metrics.append(metrics)
        
        total_loss = np.mean(losses)
        
        aggregate_metrics = {
            "total_loss": total_loss,
            "per_image_losses": losses,
            "mean_delta_e": np.mean([m["mean_delta_e"] for m in all_metrics]),
            "worst_image_loss": max(losses),
            "best_image_loss": min(losses),
        }
        
        return total_loss, aggregate_metrics
```


### 4.4 `optimizer.py` — Staged Optimization Engine

```python
"""
optimizer.py - Staged optimization using scipy.optimize.differential_evolution
"""

import numpy as np
from scipy.optimize import differential_evolution, minimize
from typing import Callable, Dict, List, Tuple, Any
import logging

logger = logging.getLogger(__name__)

class StagedOptimizer:
    def __init__(
        self,
        max_time_minutes: int = 60,
        population_size: int = 15,
        tolerance: float = 0.01,
        seed: int = 42
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
            "tone_curve": 0.4,    # 24 min - most important
            "hsl": 0.35,          # 21 min - many parameters
            "calibration": 0.25  # 15 min - fewer parameters
        }
    
    def optimize(
        self,
        objective_fn: Callable[[Dict], float],
        stages: List[str],
        initial_params: Dict[str, Any],
        param_bounds: Dict[str, Tuple[float, float]]
    ) -> Tuple[Dict[str, Any], Dict]:
        """
        Run staged optimization.
        
        Args:
            objective_fn: Function that takes params dict, returns loss
            stages: List of stage names in order
            initial_params: Starting parameter values
            param_bounds: Bounds for each parameter
        
        Returns:
            best_params: Optimized parameters
            history: Optimization history and metrics
        """
        import time
        
        current_params = initial_params.copy()
        history = {"stages": [], "total_time": 0}
        start_time = time.time()
        
        for stage in stages:
            stage_start = time.time()
            time_budget = self.max_time_minutes * 60 * self.stage_time_ratios.get(stage, 0.33)
            
            logger.info(f"=== Starting Stage: {stage} ===")
            logger.info(f"Time budget: {time_budget/60:.1f} minutes")
            
            # Get parameters for this stage
            stage_params = self._get_stage_params(stage, current_params)
            stage_bounds = [(param_bounds[p][0], param_bounds[p][1]) for p in stage_params.keys()]
            
            if not stage_params:
                logger.warning(f"No parameters for stage {stage}, skipping")
                continue
            
            # Create objective wrapper for this stage
            def stage_objective(x):
                test_params = current_params.copy()
                for i, (param_name, _) in enumerate(stage_params.items()):
                    test_params[param_name] = x[i]
                return objective_fn(test_params)
            
            # Initial guess
            x0 = list(stage_params.values())
            
            # Run differential evolution
            logger.info(f"Optimizing {len(stage_params)} parameters...")
            
            result = differential_evolution(
                stage_objective,
                bounds=stage_bounds,
                x0=x0,
                maxiter=1000,
                tol=self.tolerance,
                seed=self.seed,
                workers=1,  # Multiprocessing handled at image level
                disp=True,
                polish=True,  # L-BFGS-B polish at end
                callback=lambda xk, convergence: self._callback(xk, convergence, stage)
            )
            
            # Update current params with optimized values
            for i, (param_name, _) in enumerate(stage_params.items()):
                current_params[param_name] = result.x[i]
            
            stage_time = time.time() - stage_start
            
            stage_history = {
                "stage": stage,
                "final_loss": result.fun,
                "iterations": result.nit,
                "time_seconds": stage_time,
                "success": result.success
            }
            history["stages"].append(stage_history)
            
            logger.info(f"Stage {stage} complete: loss={result.fun:.4f}, time={stage_time/60:.1f}min")
        
        history["total_time"] = time.time() - start_time
        logger.info(f"Optimization complete. Total time: {history['total_time']/60:.1f} minutes")
        
        return current_params, history
    
    def _get_stage_params(self, stage: str, all_params: Dict) -> Dict:
        """Extract parameters belonging to a specific stage."""
        from .parameters import OPTIMIZATION_STAGES, STAGE_PARAMS
        return {k: v for k, v in all_params.items() if k in STAGE_PARAMS.get(stage, [])}
    
    def _callback(self, xk, convergence, stage):
        """Callback for progress logging."""
        logger.debug(f"[{stage}] Convergence: {convergence:.4f}")
        return False  # Continue optimization
```


### 4.5 `xmp_generator.py` — Lightroom Preset Generator

```python
"""
xmp_generator.py - Generate Lightroom Classic .xmp preset files
"""

from typing import Dict, Any, List
import xml.etree.ElementTree as ET
from datetime import datetime
import uuid

XMP_TEMPLATE = '''<?xpacket begin="" id="W5M0MpCehiHzreSzNTczkc9d"?>
<x:xmpmeta xmlns:x="adobe:ns:meta/" x:xmptk="Adobe XMP Core 7.0-c000 1.000000, 0000/00/00-00:00:00">
 <rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">
  <rdf:Description rdf:about=""
    xmlns:crs="http://ns.adobe.com/camera-raw-settings/1.0/"
    crs:PresetType="Normal"
    crs:Cluster=""
    crs:UUID="{uuid}"
    crs:SupportsAmount="False"
    crs:SupportsColor="True"
    crs:SupportsMonochrome="True"
    crs:SupportsHighDynamicRange="True"
    crs:SupportsNormalDynamicRange="True"
    crs:SupportsSceneReferred="True"
    crs:SupportsOutputReferred="True"
    crs:CameraModelRestriction=""
    crs:Copyright=""
    crs:ContactInfo=""
    crs:Version="15.4"
    crs:ProcessVersion="15.4"
    crs:ConvertToGrayscale="False"
    crs:CameraProfile="Adobe Standard"
{parameters}
   >
{tone_curves}
  </rdf:Description>
 </rdf:RDF>
</x:xmpmeta>
<?xpacket end="w"?>'''

class XMPGenerator:
    def __init__(self, preset_name: str = "ColorScienceEmulator"):
        self.preset_name = preset_name
    
    def generate(self, params: Dict[str, Any], output_path: str):
        """
        Generate a Lightroom .xmp preset file.
        
        Args:
            params: Optimized parameters dictionary
            output_path: Path to save the .xmp file
        """
        # Generate UUID
        preset_uuid = str(uuid.uuid4()).upper()
        
        # Format simple parameters
        param_lines = []
        for key, value in params.items():
            if not key.startswith("ToneCurve"):
                formatted = self._format_param(key, value)
                if formatted:
                    param_lines.append(f'    crs:{formatted}')
        
        # Format tone curves
        curve_sections = []
        for curve_name in ["ToneCurvePV2012", "ToneCurvePV2012Red", 
                          "ToneCurvePV2012Green", "ToneCurvePV2012Blue"]:
            if curve_name in params:
                curve_xml = self._format_tone_curve(curve_name, params[curve_name])
                curve_sections.append(curve_xml)
        
        # Assemble XMP
        xmp_content = XMP_TEMPLATE.format(
            uuid=preset_uuid,
            parameters="\n".join(param_lines),
            tone_curves="\n".join(curve_sections)
        )
        
        # Write file
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(xmp_content)
        
        return output_path
    
    def _format_param(self, key: str, value: Any) -> str:
        """Format a parameter for XMP."""
        if isinstance(value, bool):
            return f'{key}="{str(value).lower()}"'
        elif isinstance(value, float):
            # Round to reasonable precision
            if abs(value) < 0.01:
                value = 0
            return f'{key}="{value:+.0f}"' if value != 0 else f'{key}="0"'
        elif isinstance(value, int):
            return f'{key}="{value:+d}"' if value != 0 else f'{key}="0"'
        return None
    
    def _format_tone_curve(self, curve_name: str, points: List[tuple]) -> str:
        """Format a tone curve for XMP."""
        # Points are (input, output) pairs normalized 0-1, convert to 0-255
        scaled_points = [(int(p[0] * 255), int(p[1] * 255)) for p in points]
        point_str = ", ".join(f"{p[0]}, {p[1]}" for p in scaled_points)
        
        return f'''   <crs:{curve_name}>
    <rdf:Seq>
     <rdf:li>{point_str}</rdf:li>
    </rdf:Seq>
   </crs:{curve_name}>'''
```


### 4.6 `orchestrator.py` — Main Coordination Logic

```python
"""
orchestrator.py - Main orchestration logic
"""

import os
import logging
from pathlib import Path
from typing import List, Tuple, Dict
import numpy as np
from concurrent.futures import ProcessPoolExecutor
import json

from .renderer import RawRenderer
from .loss import PerceptualLoss
from .optimizer import StagedOptimizer
from .xmp_generator import XMPGenerator
from .parameters import PARAMETERS, OPTIMIZATION_STAGES, get_default_params, get_bounds
from .image_utils import load_jpeg, save_image

logger = logging.getLogger(__name__)

class ColorEmulator:
    def __init__(self, config: dict):
        """
        Initialize the color emulator.
        
        Args:
            config: Configuration dictionary
        """
        self.config = config
        self.renderer = RawRenderer(use_camera_wb=True)
        self.loss_fn = PerceptualLoss(
            target_delta_e=config.get("target_delta_e", 3.0),
            use_luminance_weight=config.get("luminance_weight", True)
        )
        self.optimizer = StagedOptimizer(
            max_time_minutes=config.get("max_time_minutes", 60),
            tolerance=config.get("tolerance", 0.01)
        )
        self.xmp_gen = XMPGenerator(
            preset_name=config.get("preset_name", "ColorEmulator")
        )
        
        # Image pairs
        self.dng_paths: List[str] = []
        self.jpeg_paths: List[str] = []
        self.reference_images: List[np.ndarray] = []
    
    def load_dataset(self, input_dir: str):
        """
        Load DNG+JPEG pairs from input directory.
        
        Expected naming: IMG_001.dng + IMG_001.jpg
        """
        input_path = Path(input_dir)
        
        # Find all DNG files
        dng_files = sorted(input_path.glob("*.dng")) + sorted(input_path.glob("*.DNG"))
        
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
                ref_img = load_jpeg(str(jpeg_path), max_size=1024)
                self.reference_images.append(ref_img)
                
                logger.info(f"Loaded pair: {dng_path.name} + {jpeg_path.name}")
            else:
                logger.warning(f"No matching JPEG for {dng_path.name}")
        
        logger.info(f"Loaded {len(self.dng_paths)} image pairs")
        
        if len(self.dng_paths) == 0:
            raise ValueError(f"No valid DNG+JPEG pairs found in {input_dir}")
    
    def _objective(self, params: Dict) -> float:
        """
        Compute total loss over all image pairs.
        
        This is the function being minimized by the optimizer.
        """
        rendered_images = []
        
        for dng_path in self.dng_paths:
            rendered = self.renderer.render(dng_path, params, target_size=(1024, 1024))
            rendered_images.append(rendered)
        
        total_loss, metrics = self.loss_fn.compute_batch(
            rendered_images, 
            self.reference_images
        )
        
        logger.debug(f"Loss: {total_loss:.4f} | Mean ΔE: {metrics['mean_delta_e']:.2f}")
        
        return total_loss
    
    def run(self, output_dir: str) -> str:
        """
        Run the full optimization pipeline.
        
        Args:
            output_dir: Directory to save outputs
        
        Returns:
            Path to generated .xmp preset
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        logger.info("Starting color emulation optimization...")
        logger.info(f"Dataset: {len(self.dng_paths)} image pairs")
        
        # Get initial parameters and bounds
        initial_params = get_default_params()
        param_bounds = get_bounds()
        
        # Run staged optimization
        best_params, history = self.optimizer.optimize(
            objective_fn=self._objective,
            stages=OPTIMIZATION_STAGES,
            initial_params=initial_params,
            param_bounds=param_bounds
        )
        
        # Generate XMP preset
        xmp_path = output_path / "color_emulator_preset.xmp"
        self.xmp_gen.generate(best_params, str(xmp_path))
        logger.info(f"Generated preset: {xmp_path}")
        
        # Save optimization history
        history_path = output_path / "optimization_history.json"
        with open(history_path, "w") as f:
            json.dump(history, f, indent=2, default=str)
        
        # Render test images with final parameters
        test_render_dir = output_path / "test_renders"
        test_render_dir.mkdir(exist_ok=True)
        
        for i, (dng_path, jpeg_path) in enumerate(zip(self.dng_paths, self.jpeg_paths)):
            rendered = self.renderer.render(dng_path, best_params, target_size=(2048, 2048))
            
            base_name = Path(dng_path).stem
            save_image(rendered, test_render_dir / f"{base_name}_emulated.jpg")
            
            # Copy reference for comparison
            import shutil
            shutil.copy(jpeg_path, test_render_dir / f"{base_name}_reference.jpg")
        
        logger.info(f"Test renders saved to: {test_render_dir}")
        
        # Final metrics
        final_loss = self._objective(best_params)
        logger.info(f"Final loss: {final_loss:.4f}")
        
        return str(xmp_path)
```


### 4.7 `color_emulator.py` — CLI Entry Point

```python
#!/usr/bin/env python3
"""
color_emulator.py - CLI entry point for RAW-to-JPEG color science emulator
"""

import argparse
import logging
import sys
from pathlib import Path
import yaml

from src.orchestrator import ColorEmulator

def setup_logging(verbose: bool = False):
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)-8s | %(message)s",
        datefmt="%H:%M:%S"
    )

def main():
    parser = argparse.ArgumentParser(
        description="Reverse-engineer camera JPEG color science into Lightroom presets"
    )
    parser.add_argument(
        "-i", "--input",
        required=True,
        help="Input directory containing DNG+JPEG pairs (e.g., IMG_001.dng + IMG_001.jpg)"
    )
    parser.add_argument(
        "-o", "--output",
        default="./output",
        help="Output directory for preset and test renders (default: ./output)"
    )
    parser.add_argument(
        "-c", "--config",
        default="config.yaml",
        help="Path to configuration file (default: config.yaml)"
    )
    parser.add_argument(
        "-t", "--time",
        type=int,
        default=60,
        help="Maximum optimization time in minutes (default: 60)"
    )
    parser.add_argument(
        "--target-delta-e",
        type=float,
        default=3.0,
        help="Target Delta E threshold for 'good enough' match (default: 3.0)"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )
    
    args = parser.parse_args()
    setup_logging(args.verbose)
    logger = logging.getLogger(__name__)
    
    # Load config
    config_path = Path(args.config)
    if config_path.exists():
        with open(config_path) as f:
            config = yaml.safe_load(f)
    else:
        config = {}
    
    # Override with CLI args
    config["max_time_minutes"] = args.time
    config["target_delta_e"] = args.target_delta_e
    
    # Validate input directory
    input_dir = Path(args.input)
    if not input_dir.exists():
        logger.error(f"Input directory not found: {input_dir}")
        sys.exit(1)
    
    # Run emulator
    try:
        emulator = ColorEmulator(config)
        emulator.load_dataset(str(input_dir))
        xmp_path = emulator.run(args.output)
        
        print(f"\n✅ Success! Preset saved to: {xmp_path}")
        print(f"   Test renders saved to: {Path(args.output) / 'test_renders'}")
        print(f"\nTo use in Lightroom Classic:")
        print(f"   1. Copy '{xmp_path}' to your Lightroom presets folder")
        print(f"   2. Or use File > Import Develop Profiles & Presets")
        
    except Exception as e:
        logger.exception(f"Optimization failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
```

---

## 5. Configuration File

```yaml
# config.yaml - Color Emulator Configuration

# Optimization settings
max_time_minutes: 60        # Total max runtime
tolerance: 0.01             # Convergence tolerance
population_size: 15         # Differential evolution population multiplier

# Loss function settings  
target_delta_e: 3.0         # "Good enough" threshold (ΔE < 3 is generally imperceptible)
luminance_weight: true      # Weight midtones more heavily

# Rendering settings
render_size: 1024           # Max dimension for optimization renders
final_render_size: 2048     # Max dimension for test renders
use_camera_wb: true         # Lock to camera white balance (match in-camera JPEG)

# Curve settings
curve_points: 5             # Number of control points for main tone curve (min 3, max 10)
rgb_curve_points: 3         # Number of control points for R/G/B channel curves (min 2, max 5)

# Output settings
preset_name: "ColorEmulator"

# Advanced: stage-specific settings
stages:
  tone_curve:
    time_ratio: 0.4
  hsl:
    time_ratio: 0.35
  calibration:
    time_ratio: 0.25
```

---

## 6. Dependencies

```
# requirements.txt

# Core
numpy>=1.24.0
scipy>=1.10.0

# Image processing
rawpy>=0.18.0
Pillow>=10.0.0
scikit-image>=0.21.0

# Color science
# (scikit-image includes deltaE_ciede2000)

# Utilities
PyYAML>=6.0
tqdm>=4.65.0

# Development
pytest>=7.0.0
```

---

## 7. Implementation Roadmap

### Phase 1: Foundation
| Task | Module | Acceptance Criteria |
|------|--------|---------------------|
| Project setup | - | `pip install -e .` works |
| Parameter model | `parameters.py` | All LR params defined with bounds, curve points configurable |
| Image utilities | `image_utils.py` | Load JPEG, resize, convert colorspace |
| Loss function | `loss.py` | CIEDE2000 computed correctly, matches skimage |

### Phase 2: Rendering
| Task | Module | Acceptance Criteria |
|------|--------|---------------------|
| Basic rawpy render | `renderer.py` | DNG → RGB without params |
| Tone curve application | `tone_curve.py` | Visual match to expected curve shape |
| HSL implementation | `renderer.py` | Color shifts work correctly |
| Calibration approximation | `renderer.py` | Primary shifts visible |

### Phase 3: Optimization
| Task | Module | Acceptance Criteria |
|------|--------|---------------------|
| Single-image objective | `orchestrator.py` | Loss decreases over iterations |
| Multi-image batch | `orchestrator.py` | Average loss over 10 images |
| Staged optimizer | `optimizer.py` | Completes all 3 stages |
| Convergence logging | `optimizer.py` | Progress visible in console |

### Phase 4: Output & Polish
| Task | Module | Acceptance Criteria |
|------|--------|---------------------|
| XMP generation | `xmp_generator.py` | Valid XMP, imports into LrC |
| Test render output | `orchestrator.py` | Side-by-side comparison possible |
| CLI polish | `color_emulator.py` | Helpful error messages, progress |
| Documentation | `README.md` | Clear usage instructions |

---

## 8. Testing Strategy

### Unit Tests
```python
# tests/test_loss.py
def test_identical_images_zero_loss():
    """Identical images should have Delta E = 0"""
    img = np.random.rand(100, 100, 3).astype(np.float32)
    loss_fn = PerceptualLoss()
    loss, _ = loss_fn.compute(img, img)
    assert loss < 0.01

def test_different_images_positive_loss():
    """Different images should have positive Delta E"""
    img1 = np.zeros((100, 100, 3), dtype=np.float32)
    img2 = np.ones((100, 100, 3), dtype=np.float32)
    loss_fn = PerceptualLoss()
    loss, _ = loss_fn.compute(img1, img2)
    assert loss > 10  # Very different

# tests/test_xmp.py
def test_xmp_generates_valid_file():
    """Generated XMP should be valid XML"""
    gen = XMPGenerator()
    params = {"HueAdjustmentRed": 10, "SaturationAdjustmentBlue": -5}
    gen.generate(params, "/tmp/test.xmp")
    
    import xml.etree.ElementTree as ET
    tree = ET.parse("/tmp/test.xmp")  # Should not raise
    assert tree.getroot() is not None
```

### Integration Test
```bash
# Run with sample data
python color_emulator.py \
  --input ./data/input \
  --output ./output \
  --time 10 \
  --verbose

# Verify outputs exist
ls ./output/color_emulator_preset.xmp
ls ./output/test_renders/
```

---

## 9. Known Limitations & Mitigations

| Limitation | Impact | Mitigation |
|------------|--------|------------|
| rawpy ≠ Lightroom rendering | Final preset may not match perfectly in LrC | Document clearly; user can fine-tune |
| No local tone mapping | Camera may apply local adjustments | Focus on global color; document as non-goal |
| Simplified calibration | Camera calibration is complex | Approximate with RGB primary shifts |
| No sharpening/NR | Structural differences remain | Document as out of scope |

---

## 10. Future Enhancements (Post-PoC)

1. **Lightroom CLI Integration**: If Adobe provides headless export, use it instead of rawpy
2. **DNG SDK Integration**: Build C++ bridge for exact Adobe rendering
3. **GPU Acceleration**: Use CuPy for faster image processing
4. **Bayesian Optimization**: More sample-efficient than DE for expensive evaluations
5. **Web UI**: Flask/Streamlit interface for non-CLI users
6. **Profile Generation**: Create `.dcp` camera profiles instead of/in addition to presets

---

## 11. Success Criteria for PoC

| Metric | Target | How to Verify |
|--------|--------|---------------|
| Completes without error | 100% | CLI exits 0 |
| Runtime | < 60 min | Wall clock on M4 Mac |
| Final mean ΔE | < 5.0 | Logged metrics |
| XMP imports into LrC 14.5 | Yes | Manual test |
| Visual similarity | Subjective | Side-by-side comparison |

---

## 12. How to Hand Off to Coding Agent

**Instructions for the coding agent:**

1. **Create the project structure** exactly as specified in Section 3
2. **Implement modules in order**: `parameters.py` → `image_utils.py` → `loss.py` → `tone_curve.py` → `renderer.py` → `optimizer.py` → `xmp_generator.py` → `orchestrator.py` → `color_emulator.py`
3. **Follow the interfaces** in Section 4 exactly
4. **Write tests** as specified in Section 8
5. **Document any deviations** from this plan

**Questions the agent should ask before starting:**
- None required; this plan is implementation-ready

**What NOT to do:**
- Do not attempt to use Adobe DNG SDK (too complex for PoC)
- Do not implement parallel image rendering (keep simple)
- Do not add a GUI
- Do not implement features marked as "Future Enhancements"

---

*Document Version: 1.0*  
*Created: February 2025*  
*Target: PoC Implementation*
