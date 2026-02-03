# AI Agent Implementation Prompt

## Context

You are implementing a Proof of Concept for a **RAW-to-JPEG Color Science Emulator** — a Python CLI tool that reverse-engineers camera JPEG color processing into Lightroom presets.

The complete technical specification is in the attached `poc_project_plan.md` file. Read it thoroughly before starting.

---

## Your Mission

Build a working Python CLI tool that:

1. **Accepts** 10 DNG + JPEG image pairs as input
2. **Optimizes** Lightroom-style parameters (tone curves, HSL, camera calibration) to minimize perceptual color difference
3. **Outputs** a `.xmp` preset file that can be imported into Lightroom Classic 14.5

---

## Implementation Order

Follow this exact sequence:

### Step 1: Project Scaffolding
Create the complete directory structure:
```
color-emulator/
├── README.md
├── requirements.txt
├── setup.py
├── config.yaml
├── color_emulator.py
├── src/
│   ├── __init__.py
│   ├── orchestrator.py
│   ├── renderer.py
│   ├── parameters.py
│   ├── loss.py
│   ├── optimizer.py
│   ├── xmp_generator.py
│   ├── image_utils.py
│   └── tone_curve.py
├── data/
│   └── input/
├── output/
└── tests/
    ├── __init__.py
    ├── test_loss.py
    ├── test_renderer.py
    └── test_xmp.py
```

### Step 2: Core Modules (in order)
1. `src/parameters.py` — Define all Lightroom parameters with bounds
2. `src/image_utils.py` — JPEG loading, resizing, colorspace conversion
3. `src/loss.py` — CIEDE2000 perceptual loss using scikit-image
4. `src/tone_curve.py` — Tone curve application (interpolation)
5. `src/renderer.py` — RAW rendering via rawpy with parameter application
6. `src/optimizer.py` — Staged differential evolution optimizer
7. `src/xmp_generator.py` — Generate valid Lightroom .xmp presets
8. `src/orchestrator.py` — Main coordination logic
9. `color_emulator.py` — CLI entry point

### Step 3: Testing & Polish
1. Write unit tests as specified
2. Create README.md with usage instructions
3. Ensure CLI has helpful error messages and progress logging

---

## Critical Technical Requirements

### Rendering (renderer.py)
- Use `rawpy` library for DNG processing
- Lock `use_camera_wb=True` to match in-camera JPEG white balance
- Apply parameters in order: tone curves → HSL → calibration
- Resize images to 1024px max dimension during optimization for speed

### Loss Function (loss.py)
- Use `skimage.color.deltaE_ciede2000` for perceptual color difference
- Convert RGB to LAB before comparison
- Return mean Delta E as primary loss metric
- Include optional luminance weighting (emphasize midtones)

### Optimization (optimizer.py)
- Use `scipy.optimize.differential_evolution` as primary optimizer
- Implement **staged optimization**: tone_curve → hsl → calibration
- Enable `polish=True` for L-BFGS-B refinement at end
- Respect `max_time_minutes` from config (default 60 min)
- Log progress to console

### XMP Generation (xmp_generator.py)
- Generate valid XML that Lightroom Classic 14.5 can import
- Include `ProcessVersion="15.4"` and `CameraProfile="Adobe Standard"`
- Format tone curves as comma-separated point lists
- Generate unique UUID for each preset

### Configuration (config.yaml)
- `curve_points`: Number of main tone curve control points (configurable)
- `rgb_curve_points`: Number of RGB channel curve points (configurable)
- All settings in config.yaml should be respected by the code

---

## Code Quality Requirements

1. **Type hints** on all function signatures
2. **Docstrings** for all public functions
3. **Logging** via Python's `logging` module (not print statements)
4. **Error handling** with helpful messages
5. **No hardcoded paths** — use config and CLI arguments

---

## What NOT To Do

- Do NOT attempt to use Adobe DNG SDK (use rawpy instead)
- Do NOT implement parallel/multiprocess image rendering (keep it simple)
- Do NOT add a GUI
- Do NOT implement features marked as "Future Enhancements" in the plan
- Do NOT use external services or APIs

---

## Testing Your Implementation

After implementation, verify:

```bash
# Install in development mode
pip install -e .

# Run with test data (user will provide DNG+JPEG pairs)
python color_emulator.py \
  --input ./data/input \
  --output ./output \
  --time 10 \
  --verbose

# Check outputs
ls ./output/color_emulator_preset.xmp
ls ./output/test_renders/
```

---

## Deliverables Checklist

- [ ] All source files created per directory structure
- [ ] `requirements.txt` with pinned versions
- [ ] `setup.py` for `pip install -e .`
- [ ] `config.yaml` with all documented options
- [ ] `README.md` with usage instructions
- [ ] Unit tests pass
- [ ] CLI runs without errors on valid input
- [ ] Generated .xmp is valid XML
- [ ] Test renders are saved to output directory

---

## Reference: Key Libraries

```python
# RAW processing
import rawpy

# Image processing
import numpy as np
from PIL import Image
from skimage.color import rgb2lab, deltaE_ciede2000
from skimage.transform import resize

# Optimization
from scipy.optimize import differential_evolution

# Utilities
import yaml
import logging
from pathlib import Path
```

---

## Begin Implementation

Start with Step 1 (project scaffolding), then proceed through each module in the specified order. After completing each module, verify it works in isolation before moving to the next.

Good luck!
