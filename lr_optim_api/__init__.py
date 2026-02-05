"""lr_optim_api — Python API for controlling Lightroom Classic via MIDI2LR."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from PIL import Image

from .capture import (
    capture_lightroom_window,
    extract_reference_and_current,
    find_lightroom_window,
    wait_after_adjustment,
)
from .config import (
    DEFAULT_CONFIG_PATH,
    load_calibration,
    load_config,
    load_mappings,
)
from .midi2lr import DEFAULT_MAPPINGS, MidiOut, open_midi_out, set_param
from .types import Calibration, ParamMapping, Rectangle, WindowInfo

__all__ = [
    "LightroomBridge",
    "Calibration",
    "ParamMapping",
    "Rectangle",
    "WindowInfo",
]


class LightroomBridge:
    """High-level facade consumed by the optimiser loop.

    Usage::

        bridge = LightroomBridge(midi_port_name="IAC Driver Bus 1")
        bridge.set("EXPOSURE", 0.52)
        bridge.wait_settle(150)
        ref, cur = bridge.get_previews()
    """

    def __init__(
        self,
        midi_port_name: str = "IAC Driver Bus 1",
        midi_channel: int = 0,
        config_path: str | Path = DEFAULT_CONFIG_PATH,
    ) -> None:
        self._channel = midi_channel
        self._config_path = Path(config_path).expanduser()

        self._calibration = load_calibration(self._config_path)
        saved_mappings = load_mappings(self._config_path)
        self._mappings: dict[str, ParamMapping] = {**DEFAULT_MAPPINGS, **saved_mappings}

        self._midi_out: MidiOut = open_midi_out(midi_port_name)

        if self._calibration is not None:
            self._window_id: int | None = self._calibration.window_id
        else:
            self._window_id = None

    def set(self, key: str, value_norm: float) -> None:
        mapping = self._mappings.get(key)
        if mapping is None:
            raise KeyError(
                f"Unknown parameter key '{key}'.  "
                f"Available: {sorted(self._mappings)}"
            )
        set_param(self._midi_out, self._channel, mapping, value_norm)

    def wait_settle(self, ms: int = 150) -> None:
        wait_after_adjustment(ms)

    def get_previews(self) -> tuple[Image.Image, Image.Image]:
        cal = self._require_calibration()
        wid = self._require_window_id()
        img = capture_lightroom_window(wid)
        return extract_reference_and_current(img, cal)

    def get_reference_preview(self) -> Image.Image:
        ref, _ = self.get_previews()
        return ref

    def get_current_preview(self) -> Image.Image:
        _, cur = self.get_previews()
        return cur

    def refresh_window(self) -> WindowInfo:
        win = find_lightroom_window()
        self._window_id = win.window_id
        return win

    def close(self) -> None:
        if self._midi_out is not None:
            self._midi_out.close()
            self._midi_out = None  # type: ignore[assignment]

    def __enter__(self) -> LightroomBridge:
        return self

    def __exit__(self, *_: Any) -> None:
        self.close()

    def _require_calibration(self) -> Calibration:
        if self._calibration is None:
            raise RuntimeError(
                "No calibration found.  Run:  python -m lr_optim_api.calibrate"
            )
        return self._calibration

    def _require_window_id(self) -> int:
        if self._window_id is None:
            win = self.refresh_window()
            return win.window_id
        return self._window_id
