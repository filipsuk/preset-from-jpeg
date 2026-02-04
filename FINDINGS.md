# Color Emulation Findings

## Summary

This document summarizes the findings from experimenting with different RAW rendering approaches to match camera JPEG output.

## Goal

Match the color output of camera-generated JPEGs by finding optimal RAW processing parameters that minimize Delta E (CIEDE2000 perceptual color difference).

## Test Dataset

- **Camera**: Ricoh GR II
- **Images**: 5 DNG + JPEG pairs
- **Target**: Delta E < 5.0 (excellent), < 10.0 (good)

---

## Approach 1: rawpy (LibRaw)

### Initial Baseline (Linear Output)
- `gamma=(1, 1)` - Linear output
- `no_auto_bright=True`
- **Result**: Delta E ~36 (very poor - image too dark)

### Optimized Baseline
After testing various rawpy parameters:
- `gamma=(2.8, 7.75)` - Optimized gamma curve
- `bright=3.9` - Brightness multiplier
- `no_auto_bright=True`

**Results**:
| Image | Delta E |
|-------|---------|
| R0041010 | 14.27 |
| R0041011 | ~13 |
| R0041176 | ~15 |
| R0041177 | ~13 |
| R0041179 | ~19 |

**Conclusion**: rawpy baseline is far from camera JPEG. Requires significant tone curve optimization to get close.

---

## Approach 2: RawTherapee CLI

### Why RawTherapee?
- More sophisticated demosaicing algorithms
- Better color science
- Supports DCP (DNG Camera Profile) files
- CLI for batch processing

### Installation
```bash
brew install --cask --no-quarantine rawtherapee
# CLI available at: /usr/local/bin/rawtherapee-cli
```

### Default RawTherapee Output
- No profile, default settings
- **Result**: Delta E ~16

### With Exposure Compensation Only
- `Compensation=1.12` (optimized via grid search)
- **Result**: Delta E ~6-7 average

### With DCP Profile (Adobe Standard)

Using the camera's Adobe Standard DCP profile with specific settings:

```ini
[Color Management]
InputProfile=/path/to/Pentax Ricoh GR II Adobe Standard.dcp
ToneCurve=false              # Don't use DCP's tone curve
ApplyLookTable=false         # Don't use DCP's look table
ApplyBaselineExposureOffset=false  # Control exposure ourselves
ApplyHueSatMap=true          # USE the color corrections
DCPIlluminant=0
```

**Key Insight**: The DCP profile contains color correction matrices (HueSatMap) that improve color accuracy, but its tone curve and exposure offset are designed for Adobe's engine and make images too bright in RawTherapee.

**Results with DCP + Exposure=1.12**:
| Image | Delta E |
|-------|---------|
| R0041010 | 4.34 |
| R0041011 | 5.50 |
| R0041176 | 8.22 |
| R0041177 | 5.19 |
| R0041179 | 13.44 |
| **Average** | **7.34** |

---

## Current Best Configuration

### RawTherapee .pp3 Profile
```ini
[Version]
AppVersion=5.12
Version=349

[Exposure]
Auto=false
Compensation=1.12

[Color Management]
InputProfile=/path/to/Pentax Ricoh GR II Adobe Standard.dcp
ToneCurve=false
ApplyLookTable=false
ApplyBaselineExposureOffset=false
ApplyHueSatMap=true
DCPIlluminant=0

[RAW]
CA=true

[RAW Bayer]
Method=amaze
```

### Performance
- 4 out of 5 images below Delta E 9
- 3 out of 5 images below Delta E 6
- Average Delta E: 7.34

---

## Outlier Analysis

**R0041179** consistently has higher Delta E (~13-14) across all approaches:
- May have different lighting conditions
- May need per-image exposure adjustment
- Could benefit from additional HSL tuning

---

## Optimized Parameters (Current Best)

### Configuration: Full DCP + Optimized Curve

```ini
[Exposure]
Compensation=0.10
CurveMode=Standard
Curve=1;0;0.0;0.25;0.22;0.5;0.51;0.75;0.73;1;0.97;

[Color Management]
InputProfile=/path/to/Pentax Ricoh GR II Adobe Standard.dcp
ToneCurve=true
ApplyLookTable=true
ApplyBaselineExposureOffset=true
ApplyHueSatMap=true
DCPIlluminant=0
```

### Results
| Image | Delta E | Status |
|-------|---------|--------|
| R0041010 | 3.71 | ✓ Excellent |
| R0041011 | 3.68 | ✓ Excellent |
| R0041176 | 4.82 | ✓ Excellent |
| R0041177 | 3.09 | ✓ Excellent |
| R0041179 | 14.30 | ✗ Outlier |
| **Average** | **5.92** | |

**Summary**: 4 out of 5 images below ΔE 5 (excellent match). One outlier (R0041179) requires investigation.

---

## Outlier Analysis: R0041179

Extensive testing confirmed R0041179 is a **scene-specific outlier**:

| Adjustment | R0041010 ΔE | R0041179 ΔE |
|------------|-------------|-------------|
| Baseline (best) | 3.71 | 14.30 |
| Exposure -0.3 to +0.3 | 3.5-6.5 | 14.3-15.1 |
| WB 4500-6000K | 5.3-8.7 | 14.4-17.1 |
| Saturation ±10 | 3.7 | 14.3 |
| DCPIlluminant 0/1/2 | 3.5-5.4 | 14.3-14.7 |

**Conclusion**: No global parameter adjustment significantly improves R0041179. The image has fundamentally different color characteristics (stronger blue cast, B/G=1.389 vs ~1.2 for others) that cannot be matched with a single preset.

**Additional testing with HSL/RGB curves**:
| Adjustment | R0041010 ΔE | R0041179 ΔE |
|------------|-------------|-------------|
| Blue Sat 0.55 | 3.48 | 14.32 |
| Blue Lum 0.45 | 3.60 | 14.21 |
| RGB R+2% B-2% | 4.59 | 14.69 |

None significantly improved the outlier.

**Recommendation**: Accept ~14 ΔE for this outlier, or create per-image presets for difficult scenes.

---

## Summary

| Approach | Avg ΔE | Best Image | Worst Image |
|----------|--------|------------|-------------|
| rawpy linear | ~36 | - | - |
| rawpy optimized | ~15 | - | - |
| RawTherapee default | ~16 | - | - |
| RT + DCP (HueSatMap only) | 7.34 | 4.34 | 13.44 |
| **RT + Full DCP + curve** | **5.92** | **3.09** | **14.30** |

**Best configuration achieves ΔE < 5 for 4 out of 5 images.**

---

## Next Steps

1. ~~Optimize tone curve~~ ✓ Done
2. ~~Investigate R0041179~~ ✓ Done - confirmed as scene-specific outlier
3. **Generate Lightroom XMP preset** from optimized parameters
4. **Test with more images** to validate generalization
5. **Consider per-image adjustment** for outliers

---

## Technical Notes

### Delta E Interpretation
| Delta E | Perception |
|---------|------------|
| < 1 | Not perceptible |
| 1-2 | Perceptible through close observation |
| 2-10 | Perceptible at a glance |
| 11-49 | Colors are more similar than opposite |
| 100 | Colors are exactly opposite |

### File Locations
- DCP Profile: `data/profiles/Pentax Ricoh GR II Adobe Standard.dcp`
- RawTherapee CLI: `/usr/local/bin/rawtherapee-cli`
- Test images: `data/input/*.DNG` + `*.jpg`

### Dependencies
- RawTherapee 5.12
- Python packages: numpy, scipy, scikit-image, Pillow
