"""Send MIDI CC / NRPN messages to MIDI2LR via an IAC virtual port."""

from __future__ import annotations

from typing import Any

import mido

from .types import ParamMapping

MidiOut = Any


def list_output_ports() -> list[str]:
    """Return names of all available MIDI output ports."""
    return mido.get_output_names()


def open_midi_out(port_name: str) -> MidiOut:
    """Open a named MIDI output port (e.g. ``"IAC Driver Bus 1"``)."""
    return mido.open_output(port_name)


def send_cc(
    midi_out: MidiOut,
    channel: int,
    control: int,
    value_0_127: int,
) -> None:
    """Send a single MIDI Control-Change message (7-bit)."""
    msg = mido.Message(
        "control_change",
        channel=channel,
        control=control,
        value=max(0, min(127, value_0_127)),
    )
    midi_out.send(msg)


def send_nrpn(
    midi_out: MidiOut,
    channel: int,
    nrpn_number: int,
    value_0_16383: int,
) -> None:
    """Send an NRPN parameter as a 4-message CC sequence.

    CC 99 = NRPN number MSB
    CC 98 = NRPN number LSB
    CC  6 = data-entry MSB
    CC 38 = data-entry LSB
    """
    nrpn_msb = (nrpn_number >> 7) & 0x7F
    nrpn_lsb = nrpn_number & 0x7F
    val = max(0, min(16383, value_0_16383))
    val_msb = (val >> 7) & 0x7F
    val_lsb = val & 0x7F

    for cc, v in [(99, nrpn_msb), (98, nrpn_lsb), (6, val_msb), (38, val_lsb)]:
        midi_out.send(
            mido.Message("control_change", channel=channel, control=cc, value=v)
        )


def set_param(
    midi_out: MidiOut,
    channel: int,
    mapping: ParamMapping,
    value_norm: float,
) -> None:
    """Set a Develop parameter using a normalised ``[0..1]`` value."""
    midi_value = mapping.norm_to_midi(value_norm)

    if mapping.mode == "nrpn":
        send_nrpn(midi_out, channel, mapping.control, midi_value)
    else:
        send_cc(midi_out, channel, mapping.control, midi_value)


DEFAULT_MAPPINGS: dict[str, ParamMapping] = {
    "TEMP": ParamMapping(mode="nrpn", control=0, lr_min=2000, lr_max=50000, lr_default=5500),
    "TINT": ParamMapping(mode="nrpn", control=1, lr_min=-150, lr_max=150, lr_default=0),
    "EXPOSURE": ParamMapping(mode="nrpn", control=2, lr_min=-5, lr_max=5, lr_default=0),
    "CONTRAST": ParamMapping(mode="nrpn", control=3, lr_min=-100, lr_max=100, lr_default=0),
    "HIGHLIGHTS": ParamMapping(mode="nrpn", control=4, lr_min=-100, lr_max=100, lr_default=0),
    "SHADOWS": ParamMapping(mode="nrpn", control=5, lr_min=-100, lr_max=100, lr_default=0),
    "WHITES": ParamMapping(mode="nrpn", control=6, lr_min=-100, lr_max=100, lr_default=0),
    "BLACKS": ParamMapping(mode="nrpn", control=7, lr_min=-100, lr_max=100, lr_default=0),
    "VIBRANCE": ParamMapping(mode="nrpn", control=8, lr_min=-100, lr_max=100, lr_default=0),
    "SATURATION": ParamMapping(mode="nrpn", control=9, lr_min=-100, lr_max=100, lr_default=0),
    "HSL_RED_HUE": ParamMapping(mode="nrpn", control=10, lr_min=-100, lr_max=100, lr_default=0),
    "HSL_ORANGE_HUE": ParamMapping(mode="nrpn", control=11, lr_min=-100, lr_max=100, lr_default=0),
    "HSL_YELLOW_HUE": ParamMapping(mode="nrpn", control=12, lr_min=-100, lr_max=100, lr_default=0),
    "HSL_GREEN_HUE": ParamMapping(mode="nrpn", control=13, lr_min=-100, lr_max=100, lr_default=0),
    "HSL_AQUA_HUE": ParamMapping(mode="nrpn", control=14, lr_min=-100, lr_max=100, lr_default=0),
    "HSL_BLUE_HUE": ParamMapping(mode="nrpn", control=15, lr_min=-100, lr_max=100, lr_default=0),
    "HSL_PURPLE_HUE": ParamMapping(mode="nrpn", control=16, lr_min=-100, lr_max=100, lr_default=0),
    "HSL_MAGENTA_HUE": ParamMapping(mode="nrpn", control=17, lr_min=-100, lr_max=100, lr_default=0),
    "HSL_RED_SAT": ParamMapping(mode="nrpn", control=18, lr_min=-100, lr_max=100, lr_default=0),
    "HSL_ORANGE_SAT": ParamMapping(mode="nrpn", control=19, lr_min=-100, lr_max=100, lr_default=0),
    "HSL_YELLOW_SAT": ParamMapping(mode="nrpn", control=20, lr_min=-100, lr_max=100, lr_default=0),
    "HSL_GREEN_SAT": ParamMapping(mode="nrpn", control=21, lr_min=-100, lr_max=100, lr_default=0),
    "HSL_AQUA_SAT": ParamMapping(mode="nrpn", control=22, lr_min=-100, lr_max=100, lr_default=0),
    "HSL_BLUE_SAT": ParamMapping(mode="nrpn", control=23, lr_min=-100, lr_max=100, lr_default=0),
    "HSL_PURPLE_SAT": ParamMapping(mode="nrpn", control=24, lr_min=-100, lr_max=100, lr_default=0),
    "HSL_MAGENTA_SAT": ParamMapping(mode="nrpn", control=25, lr_min=-100, lr_max=100, lr_default=0),
    "HSL_RED_LUM": ParamMapping(mode="nrpn", control=26, lr_min=-100, lr_max=100, lr_default=0),
    "HSL_ORANGE_LUM": ParamMapping(mode="nrpn", control=27, lr_min=-100, lr_max=100, lr_default=0),
    "HSL_YELLOW_LUM": ParamMapping(mode="nrpn", control=28, lr_min=-100, lr_max=100, lr_default=0),
    "HSL_GREEN_LUM": ParamMapping(mode="nrpn", control=29, lr_min=-100, lr_max=100, lr_default=0),
    "HSL_AQUA_LUM": ParamMapping(mode="nrpn", control=30, lr_min=-100, lr_max=100, lr_default=0),
    "HSL_BLUE_LUM": ParamMapping(mode="nrpn", control=31, lr_min=-100, lr_max=100, lr_default=0),
    "HSL_PURPLE_LUM": ParamMapping(mode="nrpn", control=32, lr_min=-100, lr_max=100, lr_default=0),
    "HSL_MAGENTA_LUM": ParamMapping(mode="nrpn", control=33, lr_min=-100, lr_max=100, lr_default=0),
}
