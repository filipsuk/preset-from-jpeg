"""
parameters.py - Lightroom parameter definitions and bounds.

Defines all optimizable parameters with their bounds, defaults, and stage assignments.
"""

from typing import Dict, Any, List, Tuple
from dataclasses import dataclass


# Optimization stages in order
OPTIMIZATION_STAGES = ["tone_curve", "hsl", "calibration"]


# Stage to parameter mapping
STAGE_PARAMS: Dict[str, List[str]] = {
    "tone_curve": [
        "ToneCurvePV2012",
        "ToneCurvePV2012Red",
        "ToneCurvePV2012Green",
        "ToneCurvePV2012Blue",
    ],
    "hsl": [
        "HueAdjustmentRed",
        "HueAdjustmentOrange",
        "HueAdjustmentYellow",
        "HueAdjustmentGreen",
        "HueAdjustmentAqua",
        "HueAdjustmentBlue",
        "HueAdjustmentPurple",
        "HueAdjustmentMagenta",
        "SaturationAdjustmentRed",
        "SaturationAdjustmentOrange",
        "SaturationAdjustmentYellow",
        "SaturationAdjustmentGreen",
        "SaturationAdjustmentAqua",
        "SaturationAdjustmentBlue",
        "SaturationAdjustmentPurple",
        "SaturationAdjustmentMagenta",
        "LuminanceAdjustmentRed",
        "LuminanceAdjustmentOrange",
        "LuminanceAdjustmentYellow",
        "LuminanceAdjustmentGreen",
        "LuminanceAdjustmentAqua",
        "LuminanceAdjustmentBlue",
        "LuminanceAdjustmentPurple",
        "LuminanceAdjustmentMagenta",
    ],
    "calibration": [
        "ShadowTint",
        "RedHue",
        "RedSaturation",
        "GreenHue",
        "GreenSaturation",
        "BlueHue",
        "BlueSaturation",
    ],
}


# HSL parameter definitions
HSL_PARAMETERS: Dict[str, Dict[str, Any]] = {
    # Hue adjustments (-30 to +30, narrower than full range)
    "HueAdjustmentRed": {"bounds": (-30, 30), "default": 0, "stage": "hsl"},
    "HueAdjustmentOrange": {"bounds": (-30, 30), "default": 0, "stage": "hsl"},
    "HueAdjustmentYellow": {"bounds": (-30, 30), "default": 0, "stage": "hsl"},
    "HueAdjustmentGreen": {"bounds": (-30, 30), "default": 0, "stage": "hsl"},
    "HueAdjustmentAqua": {"bounds": (-30, 30), "default": 0, "stage": "hsl"},
    "HueAdjustmentBlue": {"bounds": (-30, 30), "default": 0, "stage": "hsl"},
    "HueAdjustmentPurple": {"bounds": (-30, 30), "default": 0, "stage": "hsl"},
    "HueAdjustmentMagenta": {"bounds": (-30, 30), "default": 0, "stage": "hsl"},
    # Saturation adjustments (-50 to +50)
    "SaturationAdjustmentRed": {"bounds": (-50, 50), "default": 0, "stage": "hsl"},
    "SaturationAdjustmentOrange": {"bounds": (-50, 50), "default": 0, "stage": "hsl"},
    "SaturationAdjustmentYellow": {"bounds": (-50, 50), "default": 0, "stage": "hsl"},
    "SaturationAdjustmentGreen": {"bounds": (-50, 50), "default": 0, "stage": "hsl"},
    "SaturationAdjustmentAqua": {"bounds": (-50, 50), "default": 0, "stage": "hsl"},
    "SaturationAdjustmentBlue": {"bounds": (-50, 50), "default": 0, "stage": "hsl"},
    "SaturationAdjustmentPurple": {"bounds": (-50, 50), "default": 0, "stage": "hsl"},
    "SaturationAdjustmentMagenta": {"bounds": (-50, 50), "default": 0, "stage": "hsl"},
    # Luminance adjustments (-50 to +50)
    "LuminanceAdjustmentRed": {"bounds": (-50, 50), "default": 0, "stage": "hsl"},
    "LuminanceAdjustmentOrange": {"bounds": (-50, 50), "default": 0, "stage": "hsl"},
    "LuminanceAdjustmentYellow": {"bounds": (-50, 50), "default": 0, "stage": "hsl"},
    "LuminanceAdjustmentGreen": {"bounds": (-50, 50), "default": 0, "stage": "hsl"},
    "LuminanceAdjustmentAqua": {"bounds": (-50, 50), "default": 0, "stage": "hsl"},
    "LuminanceAdjustmentBlue": {"bounds": (-50, 50), "default": 0, "stage": "hsl"},
    "LuminanceAdjustmentPurple": {"bounds": (-50, 50), "default": 0, "stage": "hsl"},
    "LuminanceAdjustmentMagenta": {"bounds": (-50, 50), "default": 0, "stage": "hsl"},
}


# Camera calibration parameter definitions
CALIBRATION_PARAMETERS: Dict[str, Dict[str, Any]] = {
    "ShadowTint": {"bounds": (-100, 100), "default": 0, "stage": "calibration"},
    "RedHue": {"bounds": (-100, 100), "default": 0, "stage": "calibration"},
    "RedSaturation": {"bounds": (-100, 100), "default": 0, "stage": "calibration"},
    "GreenHue": {"bounds": (-100, 100), "default": 0, "stage": "calibration"},
    "GreenSaturation": {"bounds": (-100, 100), "default": 0, "stage": "calibration"},
    "BlueHue": {"bounds": (-100, 100), "default": 0, "stage": "calibration"},
    "BlueSaturation": {"bounds": (-100, 100), "default": 0, "stage": "calibration"},
}


def get_curve_parameters(curve_points: int = 5, rgb_curve_points: int = 3) -> Dict[str, Dict[str, Any]]:
    """
    Generate curve parameter definitions based on config.

    Args:
        curve_points: Number of points for main tone curve (from config)
        rgb_curve_points: Number of points for RGB channel curves (from config)

    Returns:
        Dictionary of curve parameter definitions
    """
    return {
        "ToneCurvePV2012": {
            "type": "point_curve",
            "points": curve_points,
            "bounds": (0.0, 1.0),
            "default": "linear",
            "stage": "tone_curve",
        },
        "ToneCurvePV2012Red": {
            "type": "point_curve",
            "points": rgb_curve_points,
            "bounds": (0.0, 1.0),
            "default": "linear",
            "stage": "tone_curve",
        },
        "ToneCurvePV2012Green": {
            "type": "point_curve",
            "points": rgb_curve_points,
            "bounds": (0.0, 1.0),
            "default": "linear",
            "stage": "tone_curve",
        },
        "ToneCurvePV2012Blue": {
            "type": "point_curve",
            "points": rgb_curve_points,
            "bounds": (0.0, 1.0),
            "default": "linear",
            "stage": "tone_curve",
        },
    }


def generate_linear_curve(num_points: int) -> List[Tuple[float, float]]:
    """
    Generate a linear (identity) curve with evenly spaced points.

    Args:
        num_points: Number of control points

    Returns:
        List of (input, output) tuples normalized 0-1
    """
    if num_points < 2:
        num_points = 2
    return [(i / (num_points - 1), i / (num_points - 1)) for i in range(num_points)]


def get_default_params(curve_points: int = 5, rgb_curve_points: int = 3) -> Dict[str, Any]:
    """
    Get default parameter values.

    Args:
        curve_points: Number of points for main tone curve
        rgb_curve_points: Number of points for RGB channel curves

    Returns:
        Dictionary of parameter names to default values
    """
    params = {}

    # Add curve defaults
    params["ToneCurvePV2012"] = generate_linear_curve(curve_points)
    params["ToneCurvePV2012Red"] = generate_linear_curve(rgb_curve_points)
    params["ToneCurvePV2012Green"] = generate_linear_curve(rgb_curve_points)
    params["ToneCurvePV2012Blue"] = generate_linear_curve(rgb_curve_points)

    # Add HSL defaults
    for name, info in HSL_PARAMETERS.items():
        params[name] = info["default"]

    # Add calibration defaults
    for name, info in CALIBRATION_PARAMETERS.items():
        params[name] = info["default"]

    return params


def get_bounds(curve_points: int = 5, rgb_curve_points: int = 3) -> Dict[str, Tuple[float, float]]:
    """
    Get parameter bounds for optimization.

    For curve parameters, this returns bounds for flattened curve arrays.

    Args:
        curve_points: Number of points for main tone curve
        rgb_curve_points: Number of points for RGB channel curves

    Returns:
        Dictionary of parameter names to (min, max) bounds
    """
    bounds = {}

    # Curve bounds (for each point's output value, inputs are fixed)
    curve_params = get_curve_parameters(curve_points, rgb_curve_points)
    for name, info in curve_params.items():
        bounds[name] = info["bounds"]

    # HSL bounds
    for name, info in HSL_PARAMETERS.items():
        bounds[name] = info["bounds"]

    # Calibration bounds
    for name, info in CALIBRATION_PARAMETERS.items():
        bounds[name] = info["bounds"]

    return bounds


def flatten_params(params: Dict[str, Any], curve_points: int = 5, rgb_curve_points: int = 3) -> List[float]:
    """
    Flatten parameters dictionary to a 1D array for optimization.

    Curve parameters are flattened to just their output values (inputs are fixed).

    Args:
        params: Parameter dictionary
        curve_points: Number of points for main tone curve
        rgb_curve_points: Number of points for RGB channel curves

    Returns:
        Flattened parameter array
    """
    flat = []

    # Flatten curves (only output values, inputs are fixed)
    for curve_name in ["ToneCurvePV2012", "ToneCurvePV2012Red", "ToneCurvePV2012Green", "ToneCurvePV2012Blue"]:
        if curve_name in params:
            curve = params[curve_name]
            for _, output in curve:
                flat.append(output)

    # Flatten HSL
    for name in STAGE_PARAMS["hsl"]:
        if name in params:
            flat.append(float(params[name]))

    # Flatten calibration
    for name in STAGE_PARAMS["calibration"]:
        if name in params:
            flat.append(float(params[name]))

    return flat


def unflatten_params(
    flat: List[float], curve_points: int = 5, rgb_curve_points: int = 3
) -> Dict[str, Any]:
    """
    Convert flattened parameter array back to dictionary.

    Args:
        flat: Flattened parameter array
        curve_points: Number of points for main tone curve
        rgb_curve_points: Number of points for RGB channel curves

    Returns:
        Parameter dictionary
    """
    params = {}
    idx = 0

    # Unflatten main tone curve
    main_curve = []
    for i in range(curve_points):
        input_val = i / (curve_points - 1) if curve_points > 1 else 0.0
        output_val = flat[idx]
        main_curve.append((input_val, output_val))
        idx += 1
    params["ToneCurvePV2012"] = main_curve

    # Unflatten RGB curves
    for curve_name in ["ToneCurvePV2012Red", "ToneCurvePV2012Green", "ToneCurvePV2012Blue"]:
        curve = []
        for i in range(rgb_curve_points):
            input_val = i / (rgb_curve_points - 1) if rgb_curve_points > 1 else 0.0
            output_val = flat[idx]
            curve.append((input_val, output_val))
            idx += 1
        params[curve_name] = curve

    # Unflatten HSL
    for name in STAGE_PARAMS["hsl"]:
        params[name] = flat[idx]
        idx += 1

    # Unflatten calibration
    for name in STAGE_PARAMS["calibration"]:
        params[name] = flat[idx]
        idx += 1

    return params


def get_stage_param_names(stage: str) -> List[str]:
    """
    Get parameter names for a specific optimization stage.

    Args:
        stage: Stage name ('tone_curve', 'hsl', or 'calibration')

    Returns:
        List of parameter names for that stage
    """
    return STAGE_PARAMS.get(stage, [])


def get_stage_bounds(
    stage: str, curve_points: int = 5, rgb_curve_points: int = 3
) -> List[Tuple[float, float]]:
    """
    Get bounds for parameters in a specific stage as a list.

    For tone curves, we constrain bounds to ensure monotonically increasing curves:
    - First point (shadows): 0.0 to 0.4
    - Middle points: interpolated ranges
    - Last point (highlights): 0.6 to 1.0

    Args:
        stage: Stage name
        curve_points: Number of points for main tone curve
        rgb_curve_points: Number of points for RGB channel curves (0 to disable)

    Returns:
        List of (min, max) bounds for each parameter in the stage
    """
    bounds_list = []

    if stage == "tone_curve":
        # Main curve bounds - constrained to keep curve roughly monotonic
        # Each point has a range that ensures it stays in order
        for i in range(curve_points):
            # Calculate position along curve (0 to 1)
            pos = i / (curve_points - 1) if curve_points > 1 else 0.5
            # Allow +/- 0.3 deviation from linear, but constrained to valid range
            min_val = max(0.0, pos - 0.3)
            max_val = min(1.0, pos + 0.3)
            bounds_list.append((min_val, max_val))

        # RGB curve bounds (only if enabled) - same constraints
        if rgb_curve_points > 0:
            for _ in range(3):  # R, G, B
                for i in range(rgb_curve_points):
                    pos = i / (rgb_curve_points - 1) if rgb_curve_points > 1 else 0.5
                    min_val = max(0.0, pos - 0.3)
                    max_val = min(1.0, pos + 0.3)
                    bounds_list.append((min_val, max_val))

    elif stage == "hsl":
        for name in STAGE_PARAMS["hsl"]:
            bounds_list.append(HSL_PARAMETERS[name]["bounds"])
    elif stage == "calibration":
        for name in STAGE_PARAMS["calibration"]:
            bounds_list.append(CALIBRATION_PARAMETERS[name]["bounds"])

    return bounds_list


def get_stage_defaults(
    stage: str, curve_points: int = 5, rgb_curve_points: int = 3
) -> List[float]:
    """
    Get default values for parameters in a specific stage as a list.

    Args:
        stage: Stage name
        curve_points: Number of points for main tone curve
        rgb_curve_points: Number of points for RGB channel curves (0 to disable)

    Returns:
        List of default values for each parameter in the stage
    """
    defaults = []

    if stage == "tone_curve":
        # Main curve defaults (linear)
        for i in range(curve_points):
            defaults.append(i / (curve_points - 1) if curve_points > 1 else 0.0)
        # RGB curve defaults (linear, only if enabled)
        if rgb_curve_points > 0:
            for _ in range(3):  # R, G, B
                for i in range(rgb_curve_points):
                    defaults.append(i / (rgb_curve_points - 1) if rgb_curve_points > 1 else 0.0)
    elif stage == "hsl":
        for name in STAGE_PARAMS["hsl"]:
            defaults.append(float(HSL_PARAMETERS[name]["default"]))
    elif stage == "calibration":
        for name in STAGE_PARAMS["calibration"]:
            defaults.append(float(CALIBRATION_PARAMETERS[name]["default"]))

    return defaults


def update_params_from_stage(
    params: Dict[str, Any],
    stage: str,
    stage_values: List[float],
    curve_points: int = 5,
    rgb_curve_points: int = 3,
) -> Dict[str, Any]:
    """
    Update parameters dictionary with optimized values from a stage.

    Args:
        params: Current parameters dictionary
        stage: Stage name
        stage_values: Optimized values for this stage
        curve_points: Number of points for main tone curve
        rgb_curve_points: Number of points for RGB channel curves (0 to disable)

    Returns:
        Updated parameters dictionary
    """
    params = params.copy()
    idx = 0

    if stage == "tone_curve":
        # Update main tone curve
        main_curve = []
        for i in range(curve_points):
            input_val = i / (curve_points - 1) if curve_points > 1 else 0.0
            output_val = stage_values[idx]
            main_curve.append((input_val, output_val))
            idx += 1
        params["ToneCurvePV2012"] = main_curve

        # Update RGB curves (only if enabled)
        if rgb_curve_points > 0:
            for curve_name in ["ToneCurvePV2012Red", "ToneCurvePV2012Green", "ToneCurvePV2012Blue"]:
                curve = []
                for i in range(rgb_curve_points):
                    input_val = i / (rgb_curve_points - 1) if rgb_curve_points > 1 else 0.0
                    output_val = stage_values[idx]
                    curve.append((input_val, output_val))
                    idx += 1
                params[curve_name] = curve

    elif stage == "hsl":
        for name in STAGE_PARAMS["hsl"]:
            params[name] = stage_values[idx]
            idx += 1

    elif stage == "calibration":
        for name in STAGE_PARAMS["calibration"]:
            params[name] = stage_values[idx]
            idx += 1

    return params


def get_stage_values_from_params(
    params: Dict[str, Any],
    stage: str,
    curve_points: int = 5,
    rgb_curve_points: int = 3,
) -> List[float]:
    """
    Extract values for a specific stage from parameters dictionary.

    Args:
        params: Parameters dictionary
        stage: Stage name
        curve_points: Number of points for main tone curve
        rgb_curve_points: Number of points for RGB channel curves (0 to disable)

    Returns:
        List of values for the stage
    """
    values = []

    if stage == "tone_curve":
        # Extract main curve outputs (use defaults if not present or wrong size)
        if "ToneCurvePV2012" in params and len(params["ToneCurvePV2012"]) == curve_points:
            for _, output in params["ToneCurvePV2012"]:
                values.append(output)
        else:
            # Use linear defaults
            for i in range(curve_points):
                values.append(i / (curve_points - 1) if curve_points > 1 else 0.0)

        # Extract RGB curve outputs (only if enabled)
        if rgb_curve_points > 0:
            for curve_name in ["ToneCurvePV2012Red", "ToneCurvePV2012Green", "ToneCurvePV2012Blue"]:
                if curve_name in params and len(params[curve_name]) == rgb_curve_points:
                    for _, output in params[curve_name]:
                        values.append(output)
                else:
                    # Use linear defaults
                    for i in range(rgb_curve_points):
                        values.append(i / (rgb_curve_points - 1) if rgb_curve_points > 1 else 0.0)

    elif stage == "hsl":
        for name in STAGE_PARAMS["hsl"]:
            values.append(float(params.get(name, HSL_PARAMETERS[name]["default"])))

    elif stage == "calibration":
        for name in STAGE_PARAMS["calibration"]:
            values.append(float(params.get(name, CALIBRATION_PARAMETERS[name]["default"])))

    return values
