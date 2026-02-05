"""Send MIDI CC / NRPN messages to MIDI2LR via a virtual MIDI port."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from xml.etree.ElementTree import Element, SubElement, ElementTree, indent

import mido

from .types import ParamMapping

MidiOut = Any


def list_output_ports() -> list[str]:
    """Return names of all available MIDI output ports."""
    return mido.get_output_names()


def open_midi_out(port_name: str, *, virtual: bool = True) -> MidiOut:
    """Open a MIDI output port.

    When *virtual* is ``True`` (default), a new virtual port owned by this
    process is created.  MIDI2LR sees it as an input device after a rescan.
    This avoids IAC Driver echo/feedback loops.

    The port stays alive until ``.close()`` is called or the process exits.
    """
    return mido.open_output(port_name, virtual=virtual)


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


# NRPN numbers must be >= 128 for MIDI2LR to use 14-bit absolute mode.
# Numbers 0-127 are treated as 7-bit CC (relative in many configs).
DEFAULT_MAPPINGS: dict[str, ParamMapping] = {
    "TEMP": ParamMapping(mode="nrpn", control=128, lr_min=2000, lr_max=50000, lr_default=5500, lr_command="Temperature"),
    "TINT": ParamMapping(mode="nrpn", control=129, lr_min=-150, lr_max=150, lr_default=0, lr_command="Tint"),
    "EXPOSURE": ParamMapping(mode="nrpn", control=130, lr_min=-5, lr_max=5, lr_default=0, lr_command="Exposure"),
    "CONTRAST": ParamMapping(mode="nrpn", control=131, lr_min=-100, lr_max=100, lr_default=0, lr_command="Contrast"),
    "HIGHLIGHTS": ParamMapping(mode="nrpn", control=132, lr_min=-100, lr_max=100, lr_default=0, lr_command="Highlights"),
    "SHADOWS": ParamMapping(mode="nrpn", control=133, lr_min=-100, lr_max=100, lr_default=0, lr_command="Shadows"),
    "WHITES": ParamMapping(mode="nrpn", control=134, lr_min=-100, lr_max=100, lr_default=0, lr_command="Whites"),
    "BLACKS": ParamMapping(mode="nrpn", control=135, lr_min=-100, lr_max=100, lr_default=0, lr_command="Blacks"),
    "VIBRANCE": ParamMapping(mode="nrpn", control=136, lr_min=-100, lr_max=100, lr_default=0, lr_command="Vibrance"),
    "SATURATION": ParamMapping(mode="nrpn", control=137, lr_min=-100, lr_max=100, lr_default=0, lr_command="Saturation"),
    "HSL_RED_HUE": ParamMapping(mode="nrpn", control=138, lr_min=-100, lr_max=100, lr_default=0, lr_command="HueAdjustmentRed"),
    "HSL_ORANGE_HUE": ParamMapping(mode="nrpn", control=139, lr_min=-100, lr_max=100, lr_default=0, lr_command="HueAdjustmentOrange"),
    "HSL_YELLOW_HUE": ParamMapping(mode="nrpn", control=140, lr_min=-100, lr_max=100, lr_default=0, lr_command="HueAdjustmentYellow"),
    "HSL_GREEN_HUE": ParamMapping(mode="nrpn", control=141, lr_min=-100, lr_max=100, lr_default=0, lr_command="HueAdjustmentGreen"),
    "HSL_AQUA_HUE": ParamMapping(mode="nrpn", control=142, lr_min=-100, lr_max=100, lr_default=0, lr_command="HueAdjustmentAqua"),
    "HSL_BLUE_HUE": ParamMapping(mode="nrpn", control=143, lr_min=-100, lr_max=100, lr_default=0, lr_command="HueAdjustmentBlue"),
    "HSL_PURPLE_HUE": ParamMapping(mode="nrpn", control=144, lr_min=-100, lr_max=100, lr_default=0, lr_command="HueAdjustmentPurple"),
    "HSL_MAGENTA_HUE": ParamMapping(mode="nrpn", control=145, lr_min=-100, lr_max=100, lr_default=0, lr_command="HueAdjustmentMagenta"),
    "HSL_RED_SAT": ParamMapping(mode="nrpn", control=146, lr_min=-100, lr_max=100, lr_default=0, lr_command="SaturationAdjustmentRed"),
    "HSL_ORANGE_SAT": ParamMapping(mode="nrpn", control=147, lr_min=-100, lr_max=100, lr_default=0, lr_command="SaturationAdjustmentOrange"),
    "HSL_YELLOW_SAT": ParamMapping(mode="nrpn", control=148, lr_min=-100, lr_max=100, lr_default=0, lr_command="SaturationAdjustmentYellow"),
    "HSL_GREEN_SAT": ParamMapping(mode="nrpn", control=149, lr_min=-100, lr_max=100, lr_default=0, lr_command="SaturationAdjustmentGreen"),
    "HSL_AQUA_SAT": ParamMapping(mode="nrpn", control=150, lr_min=-100, lr_max=100, lr_default=0, lr_command="SaturationAdjustmentAqua"),
    "HSL_BLUE_SAT": ParamMapping(mode="nrpn", control=151, lr_min=-100, lr_max=100, lr_default=0, lr_command="SaturationAdjustmentBlue"),
    "HSL_PURPLE_SAT": ParamMapping(mode="nrpn", control=152, lr_min=-100, lr_max=100, lr_default=0, lr_command="SaturationAdjustmentPurple"),
    "HSL_MAGENTA_SAT": ParamMapping(mode="nrpn", control=153, lr_min=-100, lr_max=100, lr_default=0, lr_command="SaturationAdjustmentMagenta"),
    "HSL_RED_LUM": ParamMapping(mode="nrpn", control=154, lr_min=-100, lr_max=100, lr_default=0, lr_command="LuminanceAdjustmentRed"),
    "HSL_ORANGE_LUM": ParamMapping(mode="nrpn", control=155, lr_min=-100, lr_max=100, lr_default=0, lr_command="LuminanceAdjustmentOrange"),
    "HSL_YELLOW_LUM": ParamMapping(mode="nrpn", control=156, lr_min=-100, lr_max=100, lr_default=0, lr_command="LuminanceAdjustmentYellow"),
    "HSL_GREEN_LUM": ParamMapping(mode="nrpn", control=157, lr_min=-100, lr_max=100, lr_default=0, lr_command="LuminanceAdjustmentGreen"),
    "HSL_AQUA_LUM": ParamMapping(mode="nrpn", control=158, lr_min=-100, lr_max=100, lr_default=0, lr_command="LuminanceAdjustmentAqua"),
    "HSL_BLUE_LUM": ParamMapping(mode="nrpn", control=159, lr_min=-100, lr_max=100, lr_default=0, lr_command="LuminanceAdjustmentBlue"),
    "HSL_PURPLE_LUM": ParamMapping(mode="nrpn", control=160, lr_min=-100, lr_max=100, lr_default=0, lr_command="LuminanceAdjustmentPurple"),
    "HSL_MAGENTA_LUM": ParamMapping(mode="nrpn", control=161, lr_min=-100, lr_max=100, lr_default=0, lr_command="LuminanceAdjustmentMagenta"),
}


def generate_midi2lr_profile(
    mappings: dict[str, ParamMapping] | None = None,
    *,
    channel: int = 1,
) -> ElementTree:
    """Build a MIDI2LR profile XML tree from parameter mappings.

    *channel* is 1-indexed (matches MIDI2LR convention; mido uses 0-indexed).
    """
    if mappings is None:
        mappings = DEFAULT_MAPPINGS

    root = Element("settings")
    for mapping in mappings.values():
        if not mapping.lr_command:
            continue
        setting = SubElement(root, "setting")
        setting.set("channel", str(channel))
        setting.set("controller", str(mapping.control))
        setting.set("command_string", mapping.lr_command)

    indent(root, space="  ")
    tree = ElementTree(root)
    return tree


def write_midi2lr_profile(
    path: str | Path,
    mappings: dict[str, ParamMapping] | None = None,
    *,
    channel: int = 1,
) -> Path:
    """Generate and write a MIDI2LR profile XML to *path*."""
    p = Path(path)
    tree = generate_midi2lr_profile(mappings, channel=channel)
    tree.write(p, encoding="unicode", xml_declaration=True)
    # ElementTree.write with encoding="unicode" doesn't add a trailing newline
    with p.open("a") as f:
        f.write("\n")
    return p
