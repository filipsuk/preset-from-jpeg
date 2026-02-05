"""CLI calibration workflow for Reference View crop rectangles.

Run with::

    python -m lr_optim_api.calibrate
"""

from __future__ import annotations

import sys
import textwrap

from .capture import capture_lightroom_window, find_lightroom_window
from .config import DEFAULT_CONFIG_PATH, save_calibration
from .types import Calibration, Rectangle


def _ask_rect(label: str) -> Rectangle:
    print(f"\n--- {label} ---")
    print("Enter pixel coordinates relative to the window top-left corner.")
    try:
        x = int(input("  x (left edge): "))
        y = int(input("  y (top edge):  "))
        w = int(input("  width:         "))
        h = int(input("  height:        "))
    except (ValueError, EOFError) as exc:
        raise SystemExit(f"Invalid input: {exc}") from exc

    if w <= 0 or h <= 0:
        raise SystemExit("Width and height must be positive.")
    return Rectangle(x=x, y=y, width=w, height=h)


def _preview_crop(window_id: int, rect: Rectangle, label: str) -> None:
    try:
        img = capture_lightroom_window(window_id)
        cropped = img.crop(rect.pil_box)
        path = f"/tmp/lr_optim_api_{label}.png"
        cropped.save(path)
        print(f"  Preview saved to {path}")
    except Exception as exc:  # noqa: BLE001
        print(f"  (could not save preview: {exc})")


def main() -> None:
    print(
        textwrap.dedent("""\
        ╔══════════════════════════════════════════════╗
        ║  lr_optim_api — Reference View Calibration   ║
        ╚══════════════════════════════════════════════╝

        Prerequisites:
          • Lightroom Classic must be running and visible.
          • Develop module with Reference View enabled (Shift+R).
          • The window must stay at the same size/position after calibration.
        """)
    )

    print("Step 1: Locating Lightroom Classic window …")
    try:
        win = find_lightroom_window()
    except LookupError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc

    print(f"  Window ID : {win.window_id}")
    print(f"  Owner     : {win.owner_name}")
    print(f"  Bounds    : ({win.x}, {win.y}) {win.width}×{win.height}")

    print("\nStep 2: Define the REFERENCE preview rectangle.")
    ref_rect = _ask_rect("Reference preview (left side)")
    _preview_crop(win.window_id, ref_rect, "reference")

    print("\nStep 3: Define the CURRENT/EDITED preview rectangle.")
    cur_rect = _ask_rect("Current preview (right side)")
    _preview_crop(win.window_id, cur_rect, "current")

    cal = Calibration(
        window_id=win.window_id,
        window_width=win.width,
        window_height=win.height,
        reference_rect=ref_rect,
        current_rect=cur_rect,
    )

    path = save_calibration(cal)
    print(f"\nCalibration saved to {path}")
    print("Re-run this script any time the window layout changes.")


if __name__ == "__main__":
    main()
