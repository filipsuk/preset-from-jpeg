# RAW-to-JPEG Color Science Emulator

A Python CLI tool that reverse-engineers camera JPEG color processing into Lightroom presets. Given DNG + JPEG image pairs from your camera, it optimizes Lightroom-style parameters to minimize perceptual color difference and outputs a `.xmp` preset file.

## Features

- **Perceptual Color Matching**: Uses CIEDE2000 Delta E for accurate perceptual color difference measurement
- **Staged Optimization**: Optimizes tone curves, then HSL, then camera calibration for best results
- **Lightroom Compatible**: Generates `.xmp` presets that import directly into Lightroom Classic 14.5+
- **Camera White Balance**: Locks to camera's recorded white balance to match in-camera JPEGs

## Requirements

- Python 3.11+
- DNG + JPEG pairs from your camera (same filename, e.g., `IMG_001.dng` + `IMG_001.jpg`)

## Installation

```bash
# Clone the repository
git clone <repository-url>
cd preset-from-jpeg

# Install dependencies
pip install -r requirements.txt

# Or install in development mode
pip install -e .
```

## Quick Start

1. Place your DNG + JPEG pairs in a directory (e.g., `./data/input/`)
2. Run the emulator:

```bash
python color_emulator.py -i ./data/input -o ./output -t 60 -v
```

3. Import the generated preset (`./output/color_emulator_preset.xmp`) into Lightroom

## Usage

```bash
python color_emulator.py [OPTIONS]

Required:
  -i, --input PATH      Input directory with DNG+JPEG pairs

Options:
  -o, --output PATH     Output directory (default: ./output)
  -c, --config PATH     Config file (default: config.yaml)
  -t, --time MINUTES    Max optimization time (default: 60)
  --target-delta-e N    Target Delta E threshold (default: 3.0)
  --curve-points N      Tone curve control points (default: 5)
  --rgb-curve-points N  RGB curve control points (default: 3)
  -v, --verbose         Enable debug logging
```

## Examples

```bash
# Basic usage with 30 minute optimization
python color_emulator.py -i ./photos -o ./preset -t 30

# Verbose output with custom Delta E target
python color_emulator.py -i ./raw_jpgs -o ./output --target-delta-e 2.5 -v

# Quick test run (10 minutes)
python color_emulator.py -i ./data/input -o ./output -t 10 -v
```

## Output Files

After running, you'll find in the output directory:

- `color_emulator_preset.xmp` - The Lightroom preset
- `optimization_history.json` - Optimization metrics and history
- `optimized_params.json` - Raw parameter values
- `test_renders/` - Side-by-side comparison images
  - `*_emulated.jpg` - Rendered with optimized parameters
  - `*_reference.jpg` - Original camera JPEG

## Configuration

Edit `config.yaml` to customize:

```yaml
# Optimization
max_time_minutes: 60      # Total max runtime
target_delta_e: 3.0       # "Good enough" threshold

# Curves
curve_points: 5           # Main tone curve points
rgb_curve_points: 3       # RGB channel curve points

# Rendering
render_size: 1024         # Size during optimization
final_render_size: 2048   # Size for test renders
```

## How It Works

1. **Load Dataset**: Pairs DNG files with matching JPEGs
2. **Staged Optimization**:
   - Stage 1: Optimize tone curves (brightness, contrast)
   - Stage 2: Optimize HSL adjustments (color-specific tuning)
   - Stage 3: Optimize camera calibration (primary colors)
3. **Loss Function**: CIEDE2000 Delta E measures perceptual color difference
4. **Output**: Generate `.xmp` preset with optimized parameters

## Understanding Delta E

- **ΔE < 1**: Not perceptible by human eyes
- **ΔE 1-2**: Perceptible through close observation
- **ΔE 2-10**: Perceptible at a glance
- **ΔE > 10**: Colors are more different than similar

The tool targets ΔE < 5 by default, which produces visually similar results.

## Testing

```bash
# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_loss.py -v

# Verify installation
python test_setup.py
```

## Technical Details

### Rendering Engine
Uses `rawpy` (LibRaw wrapper) for DNG processing. Note that this doesn't match Lightroom's internal engine exactly, so some fine-tuning may be needed.

### Optimized Parameters

**Tone Curves:**
- Main tone curve (ToneCurvePV2012)
- RGB channel curves (Red, Green, Blue)

**HSL Adjustments:**
- Hue, Saturation, Luminance for 8 color ranges
- Red, Orange, Yellow, Green, Aqua, Blue, Purple, Magenta

**Camera Calibration:**
- Shadow Tint
- Red/Green/Blue Hue and Saturation primaries

## Limitations

- rawpy rendering differs from Lightroom's internal engine
- No local adjustments (masks, gradients)
- No sharpening or noise reduction
- Best results with consistent lighting across image pairs

## Importing into Lightroom

1. Open Lightroom Classic
2. Go to **File > Import Develop Profiles & Presets**
3. Select the `.xmp` file
4. Apply the preset to your photos

Or manually copy to:
- **macOS**: `~/Library/Application Support/Adobe/CameraRaw/Settings/`
- **Windows**: `%APPDATA%\Adobe\CameraRaw\Settings\`

## License

MIT License

## Acknowledgments

- [rawpy](https://github.com/letmaik/rawpy) - RAW image processing
- [scikit-image](https://scikit-image.org/) - CIEDE2000 implementation
- [SciPy](https://scipy.org/) - Differential evolution optimizer
