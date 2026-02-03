#!/usr/bin/env python3
"""
color_emulator.py - CLI entry point for RAW-to-JPEG color science emulator.

Reverse-engineers camera JPEG color science into Lightroom presets.
"""

import argparse
import logging
import sys
from pathlib import Path

import yaml

from src.orchestrator import ColorEmulator


def setup_logging(verbose: bool = False) -> None:
    """
    Configure logging.

    Args:
        verbose: Enable debug logging if True
    """
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)-8s | %(message)s",
        datefmt="%H:%M:%S",
    )


def load_config(config_path: Path) -> dict:
    """
    Load configuration from YAML file.

    Args:
        config_path: Path to config file

    Returns:
        Configuration dictionary
    """
    if config_path.exists():
        with open(config_path) as f:
            return yaml.safe_load(f) or {}
    return {}


def main() -> int:
    """
    Main entry point.

    Returns:
        Exit code (0 for success, non-zero for error)
    """
    parser = argparse.ArgumentParser(
        description="Reverse-engineer camera JPEG color science into Lightroom presets",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s -i ./data/input -o ./output
  %(prog)s -i ./photos -o ./output -t 30 -v
  %(prog)s -i ./raw_jpgs -o ./presets --target-delta-e 2.5

For more information, see the README.md file.
        """,
    )

    parser.add_argument(
        "-i", "--input",
        required=True,
        type=Path,
        help="Input directory containing DNG+JPEG pairs (e.g., IMG_001.dng + IMG_001.jpg)",
    )
    parser.add_argument(
        "-o", "--output",
        type=Path,
        default=Path("./output"),
        help="Output directory for preset and test renders (default: ./output)",
    )
    parser.add_argument(
        "-c", "--config",
        type=Path,
        default=Path("config.yaml"),
        help="Path to configuration file (default: config.yaml)",
    )
    parser.add_argument(
        "-t", "--time",
        type=int,
        default=None,
        help="Maximum optimization time in minutes (default: from config or 60)",
    )
    parser.add_argument(
        "--target-delta-e",
        type=float,
        default=None,
        help="Target Delta E threshold for 'good enough' match (default: from config or 3.0)",
    )
    parser.add_argument(
        "--curve-points",
        type=int,
        default=None,
        help="Number of tone curve control points (default: from config or 5)",
    )
    parser.add_argument(
        "--rgb-curve-points",
        type=int,
        default=None,
        help="Number of RGB curve control points (default: from config or 3)",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose (debug) logging",
    )

    args = parser.parse_args()

    # Setup logging
    setup_logging(args.verbose)
    logger = logging.getLogger(__name__)

    # Load config
    config = load_config(args.config)
    logger.debug(f"Loaded config from: {args.config}")

    # Override config with CLI arguments
    if args.time is not None:
        config["max_time_minutes"] = args.time
    if args.target_delta_e is not None:
        config["target_delta_e"] = args.target_delta_e
    if args.curve_points is not None:
        config["curve_points"] = args.curve_points
    if args.rgb_curve_points is not None:
        config["rgb_curve_points"] = args.rgb_curve_points

    # Set defaults if not in config
    config.setdefault("max_time_minutes", 60)
    config.setdefault("target_delta_e", 3.0)
    config.setdefault("curve_points", 5)
    config.setdefault("rgb_curve_points", 3)
    config.setdefault("render_size", 1024)
    config.setdefault("final_render_size", 2048)
    config.setdefault("use_camera_wb", True)
    config.setdefault("luminance_weight", True)
    config.setdefault("population_size", 15)
    config.setdefault("tolerance", 0.01)
    config.setdefault("preset_name", "ColorEmulator")

    # Validate input directory
    if not args.input.exists():
        logger.error(f"Input directory not found: {args.input}")
        return 1

    if not args.input.is_dir():
        logger.error(f"Input path is not a directory: {args.input}")
        return 1

    # Create output directory
    args.output.mkdir(parents=True, exist_ok=True)

    # Run emulator
    try:
        logger.info("Initializing Color Emulator...")
        emulator = ColorEmulator(config)

        logger.info(f"Loading dataset from: {args.input}")
        num_pairs = emulator.load_dataset(args.input)

        if num_pairs == 0:
            logger.error("No image pairs found. Ensure DNG and JPEG files have matching names.")
            return 1

        xmp_path = emulator.run(args.output)

        # Print success message
        print()
        print("=" * 60)
        print("SUCCESS!")
        print("=" * 60)
        print(f"Preset saved to: {xmp_path}")
        print(f"Test renders saved to: {args.output / 'test_renders'}")
        print()
        print("To use in Lightroom Classic:")
        print(f"  1. Copy '{xmp_path}' to your Lightroom presets folder")
        print("  2. Or use File > Import Develop Profiles & Presets")
        print("=" * 60)

        return 0

    except FileNotFoundError as e:
        logger.error(f"File not found: {e}")
        return 1
    except ValueError as e:
        logger.error(f"Invalid input: {e}")
        return 1
    except KeyboardInterrupt:
        logger.warning("Interrupted by user")
        return 130
    except Exception as e:
        logger.exception(f"Optimization failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
