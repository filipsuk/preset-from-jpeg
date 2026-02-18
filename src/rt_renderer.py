"""
rt_renderer.py - RAW to RGB rendering using RawTherapee CLI.

Uses RawTherapee for more accurate Lightroom-like rendering.
"""

import logging
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Dict, Optional, Tuple, Union

import numpy as np
from PIL import Image

logger = logging.getLogger(__name__)

# Path to RawTherapee CLI
RT_CLI = "/usr/local/bin/rawtherapee-cli"

# Default DCP profile path (Ricoh GR II Adobe Standard)
DEFAULT_DCP = "/Users/filipsuk/Development/preset-from-jpeg/data/profiles/Pentax Ricoh GR II Adobe Standard.dcp"


def create_pp3_profile(params: Dict[str, Any], dcp_path: Optional[str] = None) -> str:
    """
    Create a RawTherapee .pp3 profile from parameters.

    Args:
        params: Dictionary of parameters including tone curves, HSL, etc.
        dcp_path: Optional path to DCP profile file

    Returns:
        String content of the .pp3 profile
    """
    # Extract tone curve points
    tone_curve = params.get("ToneCurvePV2012", [[0, 0], [1, 1]])

    # Convert tone curve to RawTherapee format
    # RT format: CurveType;x1;y1;x2;y2;...
    # CurveType 1 = custom curve
    curve_points = []
    for point in tone_curve:
        curve_points.extend([str(point[0]), str(point[1])])
    curve_str = "1;" + ";".join(curve_points) + ";"

    # Extract exposure/brightness adjustment
    # We'll map our brightness to RT's exposure compensation
    exposure = params.get("Exposure", 0.0)

    # Vignetting correction
    vignette_amount = params.get("VignetteAmount", 0)
    vignette_radius = params.get("VignetteRadius", 50)
    vignette_strength = params.get("VignetteStrength", 1)

    # Extract HSL adjustments
    hue_red = params.get("HueAdjustmentRed", 0)
    hue_orange = params.get("HueAdjustmentOrange", 0)
    hue_yellow = params.get("HueAdjustmentYellow", 0)
    hue_green = params.get("HueAdjustmentGreen", 0)
    hue_aqua = params.get("HueAdjustmentAqua", 0)
    hue_blue = params.get("HueAdjustmentBlue", 0)
    hue_purple = params.get("HueAdjustmentPurple", 0)
    hue_magenta = params.get("HueAdjustmentMagenta", 0)

    sat_red = params.get("SaturationAdjustmentRed", 0)
    sat_orange = params.get("SaturationAdjustmentOrange", 0)
    sat_yellow = params.get("SaturationAdjustmentYellow", 0)
    sat_green = params.get("SaturationAdjustmentGreen", 0)
    sat_aqua = params.get("SaturationAdjustmentAqua", 0)
    sat_blue = params.get("SaturationAdjustmentBlue", 0)
    sat_purple = params.get("SaturationAdjustmentPurple", 0)
    sat_magenta = params.get("SaturationAdjustmentMagenta", 0)

    lum_red = params.get("LuminanceAdjustmentRed", 0)
    lum_orange = params.get("LuminanceAdjustmentOrange", 0)
    lum_yellow = params.get("LuminanceAdjustmentYellow", 0)
    lum_green = params.get("LuminanceAdjustmentGreen", 0)
    lum_aqua = params.get("LuminanceAdjustmentAqua", 0)
    lum_blue = params.get("LuminanceAdjustmentBlue", 0)
    lum_purple = params.get("LuminanceAdjustmentPurple", 0)
    lum_magenta = params.get("LuminanceAdjustmentMagenta", 0)

    # Color management settings - use full DCP features for Lightroom compatibility
    if dcp_path and Path(dcp_path).exists():
        color_mgmt = f"""[Color Management]
InputProfile={dcp_path}
ToneCurve=true
ApplyLookTable=true
ApplyBaselineExposureOffset=true
ApplyHueSatMap=true
DCPIlluminant=0"""
    else:
        color_mgmt = """[Color Management]
ToneCurve=true
ApplyLookTable=true
ApplyBaselineExposureOffset=true
ApplyHueSatMap=true"""

    profile = f"""[Version]
AppVersion=5.12
Version=349

[General]
ColorLabel=0

[Exposure]
Auto=false
Compensation={exposure}
CurveMode=Standard
Curve={curve_str}

[HLRecovery]
Enabled=true
Method=Coloropp

{color_mgmt}

[HSV Equalizer]
Enabled=true
HCurve=1;0;{hue_red/360};0.166;{hue_orange/360};0.333;{hue_yellow/360};0.5;{hue_green/360};0.666;{hue_aqua/360};0.833;{hue_blue/360};1;{hue_purple/360};
SCurve=1;0;{sat_red/100 + 0.5};0.166;{sat_orange/100 + 0.5};0.333;{sat_yellow/100 + 0.5};0.5;{sat_green/100 + 0.5};0.666;{sat_aqua/100 + 0.5};0.833;{sat_blue/100 + 0.5};1;{sat_purple/100 + 0.5};
VCurve=1;0;{lum_red/100 + 0.5};0.166;{lum_orange/100 + 0.5};0.333;{lum_yellow/100 + 0.5};0.5;{lum_green/100 + 0.5};0.666;{lum_aqua/100 + 0.5};0.833;{lum_blue/100 + 0.5};1;{lum_purple/100 + 0.5};

[Vignetting Correction]
Amount={vignette_amount}
Radius={vignette_radius}
Strength={vignette_strength}
CenterX=0
CenterY=0

[RAW]
CA=true

[RAW Bayer]
Method=rcd
"""
    return profile


class RawTherapeeRenderer:
    """
    RAW image renderer using RawTherapee CLI.
    """

    def __init__(self, rt_cli_path: str = RT_CLI, dcp_path: Optional[str] = DEFAULT_DCP):
        """
        Initialize renderer.

        Args:
            rt_cli_path: Path to rawtherapee-cli executable
            dcp_path: Path to DCP profile file (optional)
        """
        self.rt_cli = rt_cli_path
        self.dcp_path = dcp_path if dcp_path and Path(dcp_path).exists() else None
        self._cache: Dict[str, np.ndarray] = {}
        self._verify_cli()

        if self.dcp_path:
            logger.info(f"Using DCP profile: {Path(self.dcp_path).name}")

    def _verify_cli(self):
        """Verify RawTherapee CLI is available."""
        try:
            result = subprocess.run(
                [self.rt_cli, "-v"],
                capture_output=True,
                text=True,
                timeout=10
            )
            # RT returns 255 for -v but that's fine
            logger.debug(f"RawTherapee CLI verified: {self.rt_cli}")
        except Exception as e:
            raise RuntimeError(f"RawTherapee CLI not available: {e}")

    def render(
        self,
        dng_path: Union[str, Path],
        params: Dict[str, Any],
        target_size: Tuple[int, int] = (1024, 1024),
        use_cache: bool = False,
    ) -> np.ndarray:
        """
        Render a DNG file with the given parameters.

        Args:
            dng_path: Path to DNG file
            params: Dictionary of parameters
            target_size: Max dimension for output (for speed)
            use_cache: Whether to cache renders (not used for RT)

        Returns:
            RGB image as numpy array (float32, 0-1 range)
        """
        dng_path = Path(dng_path)

        # Create temporary files for profile and output
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            pp3_path = tmpdir / "profile.pp3"
            out_path = tmpdir / "output.jpg"

            # Write profile
            profile_content = create_pp3_profile(params, self.dcp_path)
            pp3_path.write_text(profile_content)

            # Run RawTherapee CLI with optimized flags:
            # -q: Quick mode (skip loading profiles at startup)
            # -js1: 4:2:0 chroma subsampling (faster, minimal quality impact)
            cmd = [
                self.rt_cli,
                "-o", str(out_path),
                "-p", str(pp3_path),
                "-q",
                "-j95", "-js1",
                "-Y",
                "-c", str(dng_path)
            ]

            logger.debug(f"Running: {' '.join(cmd)}")

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=120
            )

            if not out_path.exists():
                logger.error(f"RT failed: {result.stderr}")
                raise RuntimeError(f"RawTherapee failed to render: {result.stderr}")

            # Load output image
            img = Image.open(out_path).convert("RGB")

            # Resize to target
            max_dim = max(target_size)
            ratio = max_dim / max(img.size)
            if ratio < 1:
                new_size = (int(img.width * ratio), int(img.height * ratio))
                img = img.resize(new_size, Image.Resampling.LANCZOS)

            # Convert to float array
            rgb = np.array(img).astype(np.float32) / 255.0

        return rgb

    def render_baseline(
        self,
        dng_path: Union[str, Path],
        target_size: Tuple[int, int] = (1024, 1024),
    ) -> np.ndarray:
        """
        Render with default/neutral settings for baseline comparison.

        Args:
            dng_path: Path to DNG file
            target_size: Max dimension for output

        Returns:
            RGB image as numpy array (float32, 0-1 range)
        """
        dng_path = Path(dng_path)

        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            out_path = tmpdir / "output.jpg"

            # Run RawTherapee CLI with default processing
            # -q: Quick mode (skip loading profiles at startup)
            # -js1: 4:2:0 chroma subsampling (faster)
            cmd = [
                self.rt_cli,
                "-o", str(out_path),
                "-d",  # Use default profile
                "-q",
                "-j95", "-js1",
                "-Y",
                "-c", str(dng_path)
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=120
            )

            if not out_path.exists():
                raise RuntimeError(f"RawTherapee failed: {result.stderr}")

            img = Image.open(out_path).convert("RGB")

            max_dim = max(target_size)
            ratio = max_dim / max(img.size)
            if ratio < 1:
                new_size = (int(img.width * ratio), int(img.height * ratio))
                img = img.resize(new_size, Image.Resampling.LANCZOS)

            rgb = np.array(img).astype(np.float32) / 255.0

        return rgb

    def clear_cache(self) -> None:
        """Clear the render cache."""
        self._cache.clear()


def get_default_rt_params(curve_points: int = 5) -> Dict[str, Any]:
    """
    Get default parameters for RawTherapee rendering.

    Args:
        curve_points: Number of tone curve control points

    Returns:
        Dictionary of default parameters
    """
    # Linear tone curve
    tone_curve = []
    for i in range(curve_points):
        x = i / (curve_points - 1) if curve_points > 1 else 0.5
        tone_curve.append([x, x])

    params = {
        "ToneCurvePV2012": tone_curve,
        "Exposure": 0.10,  # Optimized for full DCP mode
        "HueAdjustmentRed": 0,
        "HueAdjustmentOrange": 0,
        "HueAdjustmentYellow": 0,
        "HueAdjustmentGreen": 0,
        "HueAdjustmentAqua": 0,
        "HueAdjustmentBlue": 0,
        "HueAdjustmentPurple": 0,
        "HueAdjustmentMagenta": 0,
        "SaturationAdjustmentRed": 0,
        "SaturationAdjustmentOrange": 0,
        "SaturationAdjustmentYellow": 0,
        "SaturationAdjustmentGreen": 0,
        "SaturationAdjustmentAqua": 0,
        "SaturationAdjustmentBlue": 0,
        "SaturationAdjustmentPurple": 0,
        "SaturationAdjustmentMagenta": 0,
        "LuminanceAdjustmentRed": 0,
        "LuminanceAdjustmentOrange": 0,
        "LuminanceAdjustmentYellow": 0,
        "LuminanceAdjustmentGreen": 0,
        "LuminanceAdjustmentAqua": 0,
        "LuminanceAdjustmentBlue": 0,
        "LuminanceAdjustmentPurple": 0,
        "LuminanceAdjustmentMagenta": 0,
    }

    return params
