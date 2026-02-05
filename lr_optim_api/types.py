"""Typed data structures for lr_optim_api."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal


@dataclass(frozen=True, slots=True)
class Rectangle:
    """Pixel rectangle relative to the window origin (top-left)."""

    x: int
    y: int
    width: int
    height: int

    @property
    def right(self) -> int:
        return self.x + self.width

    @property
    def bottom(self) -> int:
        return self.y + self.height

    @property
    def pil_box(self) -> tuple[int, int, int, int]:
        """Return (left, upper, right, lower) for ``PIL.Image.crop``."""
        return (self.x, self.y, self.right, self.bottom)

    def to_dict(self) -> dict[str, int]:
        return {"x": self.x, "y": self.y, "width": self.width, "height": self.height}

    @classmethod
    def from_dict(cls, d: dict[str, int]) -> Rectangle:
        return cls(x=d["x"], y=d["y"], width=d["width"], height=d["height"])


@dataclass(frozen=True, slots=True)
class WindowInfo:
    """Metadata returned by the Quartz window enumeration."""

    window_id: int
    owner_name: str
    title: str
    x: int
    y: int
    width: int
    height: int


@dataclass(slots=True)
class Calibration:
    """Persisted crop rectangles for Reference View."""

    window_id: int
    window_width: int
    window_height: int
    reference_rect: Rectangle
    current_rect: Rectangle

    def to_dict(self) -> dict:
        return {
            "window_id": self.window_id,
            "window_width": self.window_width,
            "window_height": self.window_height,
            "reference_rect": self.reference_rect.to_dict(),
            "current_rect": self.current_rect.to_dict(),
        }

    @classmethod
    def from_dict(cls, d: dict) -> Calibration:
        return cls(
            window_id=d["window_id"],
            window_width=d["window_width"],
            window_height=d["window_height"],
            reference_rect=Rectangle.from_dict(d["reference_rect"]),
            current_rect=Rectangle.from_dict(d["current_rect"]),
        )


MidiMode = Literal["cc", "nrpn"]


@dataclass(frozen=True, slots=True)
class ParamMapping:
    """How a single Develop parameter is addressed over MIDI.

    * For CC mode  → ``control`` is the CC number (0-127), value 7-bit.
    * For NRPN mode → ``control`` is the NRPN number (0-16383), value 14-bit.
    """

    mode: MidiMode
    control: int
    lr_min: float          # Lightroom minimum (e.g. -100)
    lr_max: float          # Lightroom maximum (e.g. +100)
    lr_default: float = 0  # Lightroom default / centre
    lr_command: str = ""   # MIDI2LR command_string (e.g. "Exposure")

    @property
    def midi_max(self) -> int:
        """Maximum MIDI value for this parameter's mode."""
        return 16383 if self.mode == "nrpn" else 127

    def norm_to_midi(self, value_norm: float) -> int:
        """Convert a normalised ``[0..1]`` value to the MIDI integer range."""
        clamped = max(0.0, min(1.0, value_norm))
        return round(clamped * self.midi_max)

    def lr_to_norm(self, lr_value: float) -> float:
        """Convert a Lightroom-unit value to normalised ``[0..1]``."""
        span = self.lr_max - self.lr_min
        if span == 0:
            return 0.5
        return (lr_value - self.lr_min) / span
