# lr_optim_api

Python API layer for controlling Adobe Lightroom Classic Develop adjustments via
MIDI2LR and capturing Reference View previews via macOS Quartz screenshots.

Designed as a building block for an automated optimisation loop.

## Prerequisites

- macOS (Quartz Window Services is macOS-only)
- Adobe Lightroom Classic, Develop module, Reference View enabled (Shift+R)
- MIDI2LR installed and running, listening on a macOS IAC virtual MIDI port
- IAC Driver enabled in Audio MIDI Setup
- Screen Recording permission granted for your terminal / Python process

## Installation

```bash
pip install -e ".[dev]"
```

## Quick start

### 1. Set up IAC Driver

Open **Audio MIDI Setup** → **Window → Show MIDI Studio** → double-click
**IAC Driver** → tick **Device is online**. Note the bus name (default:
`IAC Driver Bus 1`).

### 2. Configure MIDI2LR

Launch MIDI2LR. In its mapping UI, assign each MIDI control (CC or NRPN
number) to a Lightroom Develop parameter. The NRPN numbers you assign must
match the `control` field in `DEFAULT_MAPPINGS` (or your own saved config).

### 3. Calibrate crop regions

```bash
python -m lr_optim_api.calibrate
```

Follow the prompts to define the reference and current preview rectangles.
Calibration is saved to `~/.config/lr_optim_api/config.json`.

### 4. Use the API

```python
from lr_optim_api import LightroomBridge

bridge = LightroomBridge(
    midi_port_name="IAC Driver Bus 1",
    midi_channel=0,
    config_path="~/.config/lr_optim_api/config.json",
)

bridge.set("HSL_RED_HUE", 0.52)     # normalised 0..1
bridge.set("HSL_RED_SAT", 0.12)
bridge.wait_settle(150)

ref_img, cur_img = bridge.get_previews()
# your optimiser computes loss(ref_img, cur_img)
```

### Low-level usage

```python
from lr_optim_api.midi2lr import open_midi_out, send_cc, send_nrpn

port = open_midi_out("IAC Driver Bus 1")
send_cc(port, channel=0, control=7, value_0_127=64)
send_nrpn(port, channel=0, nrpn_number=300, value_0_16383=8192)
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
