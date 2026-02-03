# RAW-to-JPEG Color Science Emulator

## Project Overview

This project implements a Python CLI tool that reverse-engineers camera JPEG color processing into Lightroom presets. It accepts DNG + JPEG image pairs as input and optimizes Lightroom-style parameters to minimize perceptual color difference, outputting a `.xmp` preset file.

## Key Documentation

- `agent_prompt.md` - Implementation instructions and deliverables checklist
- `poc_project_plan.md` - Complete technical specification
- `environment_setup.md` - Environment setup guide (primarily for macOS)

## Project Structure

```
color-emulator/
├── README.md
├── requirements.txt
├── setup.py
├── config.yaml
├── color_emulator.py          # CLI entry point
├── src/
│   ├── __init__.py
│   ├── orchestrator.py        # Main optimization loop
│   ├── renderer.py            # RAW → RGB rendering via rawpy
│   ├── parameters.py          # Lightroom parameter definitions & bounds
│   ├── loss.py                # CIEDE2000 loss computation
│   ├── optimizer.py           # SciPy optimizer wrapper
│   ├── xmp_generator.py       # Generate .xmp preset files
│   ├── image_utils.py         # Image loading, resizing, color space
│   └── tone_curve.py          # Tone curve application & fitting
├── data/
│   └── input/                 # Place DNG+JPEG pairs here
├── output/
│   └── test_renders/          # Rendered test images
└── tests/
    ├── __init__.py
    ├── test_loss.py
    ├── test_renderer.py
    └── test_xmp.py
```

## Implementation Order

Modules should be implemented in this order:
1. `src/parameters.py` - Define all Lightroom parameters with bounds
2. `src/image_utils.py` - JPEG loading, resizing, colorspace conversion
3. `src/loss.py` - CIEDE2000 perceptual loss using scikit-image
4. `src/tone_curve.py` - Tone curve application (interpolation)
5. `src/renderer.py` - RAW rendering via rawpy with parameter application
6. `src/optimizer.py` - Staged differential evolution optimizer
7. `src/xmp_generator.py` - Generate valid Lightroom .xmp presets
8. `src/orchestrator.py` - Main coordination logic
9. `color_emulator.py` - CLI entry point

## Key Technical Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| RAW Rendering | `rawpy` (LibRaw wrapper) | Free, cross-platform, Python-native |
| Loss Function | CIEDE2000 (Delta E) in LAB space | Industry-standard perceptual metric |
| Optimizer | Differential Evolution | Global optimizer, avoids local minima |
| Optimization Strategy | Staged (Tone → HSL → Calibration) | Reduces search space per stage |
| Output Format | `.xmp` preset file | Native Lightroom Classic format |

## Running the Tool

```bash
# Install in development mode
pip install -e .

# Run with test data
python color_emulator.py \
  --input ./data/input \
  --output ./output \
  --time 60 \
  --verbose
```

## Configuration

Main configuration via `config.yaml`:
- `curve_points`: Number of main tone curve control points
- `rgb_curve_points`: Number of RGB channel curve points
- `max_time_minutes`: Maximum optimization time
- `target_delta_e`: "Good enough" threshold for Delta E

## Testing

```bash
# Run all tests
pytest tests/

# Run specific test file
pytest tests/test_loss.py -v
```

## What NOT to Do

- Do NOT use Adobe DNG SDK (use rawpy instead)
- Do NOT implement parallel/multiprocess image rendering
- Do NOT add a GUI
- Do NOT implement features marked as "Future Enhancements"
- Do NOT use external services or APIs

## Success Criteria

| Metric | Target |
|--------|--------|
| Completes without error | CLI exits 0 |
| Runtime | < 60 min |
| Final mean ΔE | < 5.0 |
| XMP imports into LrC 14.5 | Yes |

## Environment Setup Status

### Linux (Completed)
All dependencies have been installed and verified:
- Python 3.11.14
- numpy 2.4.2
- scipy 1.17.0
- rawpy 0.26.0
- Pillow 12.1.0
- scikit-image 0.26.0
- PyYAML 6.0.1
- tqdm 4.67.3
- pytest 9.0.2

Run `python3 test_setup.py` to verify installation.

### macOS Setup (TODO for later)

On macOS, follow these steps:

1. **Install Homebrew** (if not already installed):
   ```bash
   /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
   ```

2. **Install Python 3.11+**:
   ```bash
   brew install python@3.11
   ```

3. **Install system libraries for rawpy**:
   ```bash
   brew install libraw libjpeg libpng
   ```

4. **Create and activate virtual environment**:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

5. **Install dependencies**:
   ```bash
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

6. **Verify installation**:
   ```bash
   python test_setup.py
   ```

See `environment_setup.md` for detailed macOS setup instructions.
