# lr_optim_api

Python API layer for controlling Adobe Lightroom Classic Develop adjustments via
MIDI2LR and capturing Reference View previews via macOS Quartz screenshots.

Designed as a building block for an automated optimisation loop.

## Prerequisites

- macOS (Quartz Window Services is macOS-only)
- Adobe Lightroom Classic, Develop module, Reference View enabled (Shift+R)
- MIDI2LR installed and running
- Screen Recording permission granted for your terminal / Python process

## Installation

```bash
pip install -e ".[dev]"
```

## Quick start

### 1. Configure MIDI2LR

This package creates a **virtual MIDI port** (no IAC Driver needed). On launch,
a port named `"LR Control"` appears automatically.

1. Start your Python script (this creates the port).
2. In MIDI2LR, click **"Rescan MIDI devices"** — `LR Control` will appear.
3. Send an NRPN message from Python — a row appears in MIDI2LR.
4. Assign each row to a Lightroom Develop parameter in the **"LR Command"** dropdown.
5. Click **"Save"** in MIDI2LR to persist the profile.

The NRPN numbers must match the `control` field in `DEFAULT_MAPPINGS`
(starting at 128). MIDI2LR treats NRPN numbers >= 128 as 14-bit absolute
(0-16383), which maps linearly to the full Lightroom parameter range.

**Important**: In MIDI2LR **Settings**, uncheck **"Enable Pickup Mode"**.
Pickup mode requires the MIDI value to cross the current slider position
before responding, which prevents programmatic absolute control.

### 3. Calibrate crop regions

```bash
python -m lr_optim_api.calibrate
```

Follow the prompts to define the reference and current preview rectangles.
Calibration is saved to `~/.config/lr_optim_api/config.json`.

### 4. Use the API

```python
from lr_optim_api import LightroomBridge

bridge = LightroomBridge()   # creates virtual port "LR Control"

bridge.set("HSL_RED_HUE", 0.52)     # normalised 0..1
bridge.set("HSL_RED_SAT", 0.12)
bridge.wait_settle(150)

ref_img, cur_img = bridge.get_previews()
# your optimiser computes loss(ref_img, cur_img)
```

### Low-level usage

```python
from lr_optim_api.midi2lr import open_midi_out, send_nrpn

port = open_midi_out("LR Control")   # virtual=True by default
send_nrpn(port, channel=0, nrpn_number=138, value_0_16383=8192)  # Hue Red → 0
```

## Running tests

```bash
pytest
```

## Package structure

```
lr_optim_api/
  __init__.py      LightroomBridge high-level facade
  types.py         Rectangle, WindowInfo, Calibration, ParamMapping
  config.py        JSON config persistence (~/.config/lr_optim_api/)
  midi2lr.py       MIDI CC / NRPN messaging + default parameter mappings
  capture.py       Quartz window capture + Reference View cropping
  calibrate.py     CLI calibration workflow
  __main__.py      python -m lr_optim_api.calibrate entry point
tests/
  test_types.py    Rectangle math, ParamMapping normalisation
  test_midi.py     MIDI message building, NRPN 4-message sequence
  test_config.py   Config serialisation round-trips
```

## External documentation

MIDI2LR wiki – MIDI Controller Setup:
https://github.com/rsjaffe/MIDI2LR/wiki/MIDI-Controller-Setup

MIDI2LR website (general info, releases):
https://rsjaffe.github.io/MIDI2LR/

Apple: IAC Driver setup in Audio MIDI Setup:
https://support.apple.com/guide/audio-midi-setup/transfer-midi-information-between-apps-ams1013/mac

Apple: CGWindowListCreateImage (Quartz Window Services):
https://developer.apple.com/documentation/coregraphics/cgwindowlistcreateimage%28_%3A_%3A_%3A_%3A%29

Apple: Quartz Window Services overview:
https://developer.apple.com/documentation/coregraphics/quartz-window-services

Mido docs: RtMidi backend:
https://mido.readthedocs.io/en/latest/backends/rtmidi.html

python-rtmidi docs:
https://spotlightkid.github.io/python-rtmidi/rtmidi.html
