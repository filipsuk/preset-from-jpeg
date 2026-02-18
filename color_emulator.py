#!/usr/bin/env python3
"""
color_emulator.py - CLI entry point for RAW-to-JPEG color science emulator.

Reverse-engineers camera JPEG color science into Lightroom-compatible presets
using RawTherapee as the rendering engine.
"""

import argparse
import json
import logging
import sys
from pathlib import Path

import numpy as np
from PIL import Image
from skimage.color import rgb2lab, deltaE_ciede2000

from src.rt_renderer import RawTherapeeRenderer, get_default_rt_params
from src.xmp_generator import XMPGenerator

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def load_image_pairs(input_dir: Path, max_images: int = None, resize: tuple = (256, 170)):
    """Load DNG + JPEG pairs from input directory."""
    pairs = []
    dng_files = sorted(list(input_dir.glob("*.DNG")) + list(input_dir.glob("*.dng")))

    for dng in dng_files:
        if max_images and len(pairs) >= max_images:
            break

        jpeg = None
        for ext in [".jpg", ".jpeg", ".JPG", ".JPEG"]:
            potential = dng.with_suffix(ext)
            if potential.exists():
                jpeg = potential
                break

        if jpeg:
            ref_img = Image.open(jpeg).convert("RGB")
            if resize:
                ref_img = ref_img.resize(resize, Image.Resampling.LANCZOS)
            ref = np.array(ref_img).astype(np.float32) / 255.0
            pairs.append({
                "dng": str(dng),
                "ref": ref,
                "ref_lab": rgb2lab(ref),
                "name": dng.stem,
            })
            logger.info(f"Loaded: {dng.stem}")

    return pairs


def evaluate(renderer, pairs, exposure, curve_y):
    """Evaluate parameters on image pairs, return average Delta E."""
    params = get_default_rt_params(curve_points=5)
    params["Exposure"] = exposure
    params["ToneCurvePV2012"] = [[i / 4.0, curve_y[i]] for i in range(5)]

    total_de = 0
    for pair in pairs:
        rgb = renderer.render(pair["dng"], params, target_size=(256, 256))

        if rgb.shape != pair["ref"].shape:
            rgb_pil = Image.fromarray((rgb * 255).astype(np.uint8))
            rgb_pil = rgb_pil.resize(
                (pair["ref"].shape[1], pair["ref"].shape[0]),
                Image.Resampling.LANCZOS
            )
            rgb = np.array(rgb_pil).astype(np.float32) / 255.0

        rgb_lab = rgb2lab(np.clip(rgb, 0, 1))
        delta_e = deltaE_ciede2000(pair["ref_lab"], rgb_lab)
        total_de += np.mean(delta_e)

    return total_de / len(pairs)


def optimize(renderer, pairs):
    """Optimize exposure and tone curve using grid search."""
    logger.info("="*60)
    logger.info("Starting optimization")
    logger.info("="*60)

    # Phase 1: Find best exposure
    linear_curve = [0.0, 0.25, 0.5, 0.75, 1.0]
    best_exp, best_de = 0.0, float("inf")

    logger.info("\n[Phase 1] Exposure search:")
    for exp in np.arange(-0.2, 0.4, 0.1):
        de = evaluate(renderer, pairs, exp, linear_curve)
        logger.info(f"  Exp={exp:+.1f}: ΔE={de:.2f}")
        if de < best_de:
            best_de, best_exp = de, exp

    # Phase 2: Test curve shapes
    logger.info(f"\n[Phase 2] Curve shape search:")
    curves = {
        "linear": [0.0, 0.25, 0.5, 0.75, 1.0],
        "slight_s": [0.02, 0.23, 0.5, 0.77, 0.98],
        "contrast+": [0.0, 0.20, 0.5, 0.80, 1.0],
    }

    best_curve = linear_curve
    for name, curve in curves.items():
        de = evaluate(renderer, pairs, best_exp, curve)
        logger.info(f"  {name}: ΔE={de:.2f}")
        if de < best_de:
            best_de, best_curve = de, curve

    # Phase 3: Fine-tune curve
    logger.info(f"\n[Phase 3] Fine-tuning curve:")
    best_curve = list(best_curve)
    for i in range(5):
        for delta in [-0.02, -0.01, 0.01, 0.02]:
            test_curve = best_curve.copy()
            test_curve[i] = np.clip(test_curve[i] + delta, 0, 1)
            de = evaluate(renderer, pairs, best_exp, test_curve)
            if de < best_de:
                best_de = de
                best_curve = test_curve
                logger.info(f"  Point {i} -> {test_curve[i]:.3f}: ΔE={de:.2f}")

    return best_exp, best_curve, best_de


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Reverse-engineer camera JPEG color science into Lightroom presets"
    )
    parser.add_argument("-i", "--input", required=True, type=Path,
                        help="Input directory with DNG+JPEG pairs")
    parser.add_argument("-o", "--output", type=Path, default=Path("output"),
                        help="Output directory (default: output)")
    parser.add_argument("-n", "--max-images", type=int, default=None,
                        help="Max images to use (default: all)")
    parser.add_argument("--dcp", type=Path,
                        default=Path("data/profiles/Pentax Ricoh GR II Adobe Standard.dcp"),
                        help="DCP profile path")
    parser.add_argument("-v", "--verbose", action="store_true",
                        help="Verbose output")

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Validate input
    if not args.input.exists():
        logger.error(f"Input directory not found: {args.input}")
        return 1

    # Setup DCP
    dcp_path = str(args.dcp) if args.dcp.exists() else None
    if dcp_path:
        logger.info(f"Using DCP profile: {args.dcp.name}")

    # Initialize renderer
    try:
        renderer = RawTherapeeRenderer(dcp_path=dcp_path)
    except RuntimeError as e:
        logger.error(f"Failed to initialize RawTherapee: {e}")
        logger.error("Make sure RawTherapee is installed: brew install --cask rawtherapee")
        return 1

    # Load images
    pairs = load_image_pairs(args.input, args.max_images)
    if not pairs:
        logger.error("No DNG+JPEG pairs found")
        return 1

    logger.info(f"Loaded {len(pairs)} image pairs")

    # Run optimization
    best_exp, best_curve, avg_de = optimize(renderer, pairs)

    # Final evaluation
    logger.info("\n" + "="*60)
    logger.info("FINAL RESULTS")
    logger.info("="*60)

    params = get_default_rt_params(curve_points=5)
    params["Exposure"] = best_exp
    params["ToneCurvePV2012"] = [[i / 4.0, best_curve[i]] for i in range(5)]

    results = {}
    logger.info("\nPer-image results:")
    for pair in pairs:
        rgb = renderer.render(pair["dng"], params, target_size=(256, 256))
        if rgb.shape != pair["ref"].shape:
            rgb_pil = Image.fromarray((rgb * 255).astype(np.uint8))
            rgb_pil = rgb_pil.resize((pair["ref"].shape[1], pair["ref"].shape[0]), Image.Resampling.LANCZOS)
            rgb = np.array(rgb_pil).astype(np.float32) / 255.0

        de = float(np.mean(deltaE_ciede2000(pair["ref_lab"], rgb2lab(np.clip(rgb, 0, 1)))))
        results[pair["name"]] = de
        status = "✓" if de < 5 else ("~" if de < 10 else "✗")
        logger.info(f"  {status} {pair['name']}: ΔE={de:.2f}")

    avg_de = sum(results.values()) / len(results)
    logger.info(f"\n  Average: {avg_de:.2f}")

    # Save outputs
    args.output.mkdir(parents=True, exist_ok=True)

    # Save JSON
    output_json = {
        "exposure": float(best_exp),
        "tone_curve": [[i / 4.0, float(best_curve[i])] for i in range(5)],
        "dcp_profile": str(args.dcp) if args.dcp.exists() else None,
        "average_delta_e": avg_de,
        "per_image": results,
    }
    json_path = args.output / "optimized_params.json"
    with open(json_path, "w") as f:
        json.dump(output_json, f, indent=2)

    # Save RawTherapee .pp3 profile
    curve_str = ";".join([f"{i/4};{best_curve[i]}" for i in range(5)]) + ";"
    pp3_content = f"""[Version]
AppVersion=5.12
Version=349

[Exposure]
Auto=false
Compensation={best_exp}
CurveMode=Standard
Curve=1;{curve_str}

[HLRecovery]
Enabled=true
Method=Coloropp

[Color Management]
InputProfile={args.dcp if args.dcp.exists() else '(camera)'}
ToneCurve=true
ApplyLookTable=true
ApplyBaselineExposureOffset=true
ApplyHueSatMap=true
DCPIlluminant=0

[RAW]
CA=true

[RAW Bayer]
Method=amaze
"""
    pp3_path = args.output / "optimized_preset.pp3"
    pp3_path.write_text(pp3_content)

    # Generate Lightroom XMP preset
    try:
        xmp_params = {
            "ToneCurvePV2012": [[int(p[0]*255), int(p[1]*255)] for p in params["ToneCurvePV2012"]],
        }
        generator = XMPGenerator()
        xmp_path = args.output / "color_emulator_preset.xmp"
        generator.generate(xmp_params, xmp_path)
        logger.info(f"\nSaved Lightroom XMP: {xmp_path}")
    except Exception as e:
        logger.warning(f"Could not generate XMP: {e}")

    logger.info(f"Saved RawTherapee profile: {pp3_path}")
    logger.info(f"Saved parameters: {json_path}")

    print()
    print("="*60)
    print("SUCCESS!")
    print("="*60)
    print(f"Average Delta E: {avg_de:.2f}")
    print(f"Output saved to: {args.output}")
    print("="*60)

    return 0


if __name__ == "__main__":
    sys.exit(main())
