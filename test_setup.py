#!/usr/bin/env python3
"""Verify all dependencies are installed correctly."""

import sys


def test_imports():
    """Test that all required packages can be imported."""
    print("Testing imports...")
    errors = []

    try:
        import numpy as np
        print(f"  [OK] numpy {np.__version__}")
    except ImportError as e:
        errors.append(f"  [FAIL] numpy: {e}")

    try:
        import scipy
        print(f"  [OK] scipy {scipy.__version__}")
    except ImportError as e:
        errors.append(f"  [FAIL] scipy: {e}")

    try:
        import rawpy
        print(f"  [OK] rawpy {rawpy.__version__}")
    except ImportError as e:
        errors.append(f"  [FAIL] rawpy: {e}")

    try:
        from PIL import Image
        import PIL
        print(f"  [OK] Pillow {PIL.__version__}")
    except ImportError as e:
        errors.append(f"  [FAIL] Pillow: {e}")

    try:
        import skimage
        print(f"  [OK] scikit-image {skimage.__version__}")
    except ImportError as e:
        errors.append(f"  [FAIL] scikit-image: {e}")

    try:
        from skimage.color import deltaE_ciede2000
        print("  [OK] deltaE_ciede2000 available")
    except ImportError as e:
        errors.append(f"  [FAIL] deltaE_ciede2000: {e}")

    try:
        import yaml
        print(f"  [OK] PyYAML {yaml.__version__}")
    except ImportError as e:
        errors.append(f"  [FAIL] PyYAML: {e}")

    try:
        import tqdm
        print(f"  [OK] tqdm {tqdm.__version__}")
    except ImportError as e:
        errors.append(f"  [FAIL] tqdm: {e}")

    try:
        import pytest
        print(f"  [OK] pytest {pytest.__version__}")
    except ImportError as e:
        errors.append(f"  [FAIL] pytest: {e}")

    print()

    if errors:
        print("ERRORS:")
        for error in errors:
            print(error)
        print("\nSome dependencies are missing. Run: pip install -r requirements.txt")
        return False
    else:
        print("All dependencies installed correctly!")
        return True


if __name__ == "__main__":
    success = test_imports()
    sys.exit(0 if success else 1)
