"""Capture the Lightroom Classic window and crop Reference View regions.

Requires macOS Screen Recording permission for the calling process.
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

from PIL import Image

from .types import Calibration, Rectangle, WindowInfo

if TYPE_CHECKING:
    pass

LR_OWNER_NAME = "Adobe Lightroom Classic"


def _import_quartz():  # noqa: ANN202
    """Lazy-import Quartz so the rest of the package stays importable on
    non-macOS platforms (useful for testing).
    """
    try:
        import Quartz  # type: ignore[import-untyped]
    except ImportError as exc:
        raise RuntimeError(
            "PyObjC Quartz bindings are required.  "
            "Install with: pip install pyobjc-framework-Quartz"
        ) from exc
    return Quartz


def find_lightroom_window() -> WindowInfo:
    """Locate the main Lightroom Classic window via Quartz Window Services."""
    Quartz = _import_quartz()

    window_list = Quartz.CGWindowListCopyWindowInfo(
        Quartz.kCGWindowListOptionOnScreenOnly | Quartz.kCGWindowListExcludeDesktopElements,
        Quartz.kCGNullWindowID,
    )

    for win in window_list:
        owner = win.get(Quartz.kCGWindowOwnerName, "")
        if LR_OWNER_NAME in owner:
            bounds = win[Quartz.kCGWindowBounds]
            return WindowInfo(
                window_id=int(win[Quartz.kCGWindowNumber]),
                owner_name=str(owner),
                title=str(win.get(Quartz.kCGWindowName, "")),
                x=int(bounds["X"]),
                y=int(bounds["Y"]),
                width=int(bounds["Width"]),
                height=int(bounds["Height"]),
            )

    raise LookupError(
        f"No on-screen window found for '{LR_OWNER_NAME}'.  "
        "Make sure Lightroom Classic is running and visible."
    )


def capture_lightroom_window(window_id: int) -> Image.Image:
    """Capture a single window by ID and return a PIL Image (in-memory)."""
    Quartz = _import_quartz()

    cg_image = Quartz.CGWindowListCreateImage(
        Quartz.CGRectNull,
        Quartz.kCGWindowListOptionIncludingWindow,
        window_id,
        Quartz.kCGWindowImageBoundsIgnoreFraming,
    )

    if cg_image is None:
        raise RuntimeError(
            f"CGWindowListCreateImage returned None for window {window_id}.  "
            "Check macOS Screen Recording permission for this process."
        )

    width = Quartz.CGImageGetWidth(cg_image)
    height = Quartz.CGImageGetHeight(cg_image)
    bytes_per_row = Quartz.CGImageGetBytesPerRow(cg_image)

    provider = Quartz.CGImageGetDataProvider(cg_image)
    raw_data = Quartz.CGDataProviderCopyData(provider)

    img = Image.frombuffer(
        "RGBA",
        (width, height),
        raw_data,
        "raw",
        "BGRA",
        bytes_per_row,
        1,
    )
    return img.convert("RGB")


def extract_reference_and_current(
    window_image: Image.Image,
    calibration: Calibration,
) -> tuple[Image.Image, Image.Image]:
    """Crop reference and current preview regions from a window screenshot."""
    ref = window_image.crop(calibration.reference_rect.pil_box)
    cur = window_image.crop(calibration.current_rect.pil_box)
    return ref, cur


def get_reference_preview(
    window_id: int, calibration: Calibration
) -> Image.Image:
    img = capture_lightroom_window(window_id)
    ref, _ = extract_reference_and_current(img, calibration)
    return ref


def get_current_preview(
    window_id: int, calibration: Calibration
) -> Image.Image:
    img = capture_lightroom_window(window_id)
    _, cur = extract_reference_and_current(img, calibration)
    return cur


def get_both_previews(
    window_id: int, calibration: Calibration
) -> tuple[Image.Image, Image.Image]:
    img = capture_lightroom_window(window_id)
    return extract_reference_and_current(img, calibration)


def wait_after_adjustment(ms: int = 150) -> None:
    """Sleep to let Lightroom settle after a parameter change."""
    time.sleep(ms / 1000.0)
