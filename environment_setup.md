# Environment Setup Guide for macOS

This guide will help you set up a Python development environment on your Mac for the Color Emulator project. Follow each step in order.

---

## Step 1: Install Homebrew (Package Manager)

Homebrew makes it easy to install software on macOS. Open **Terminal** (search for "Terminal" in Spotlight) and paste:

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

After installation, follow the on-screen instructions to add Homebrew to your PATH. Usually:

```bash
echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> ~/.zprofile
eval "$(/opt/homebrew/bin/brew shellenv)"
```

Verify it works:
```bash
brew --version
```

---

## Step 2: Install Python 3.11+ via Homebrew

macOS comes with Python, but it's better to install a fresh version:

```bash
brew install python@3.11
```

Verify:
```bash
python3 --version
# Should show Python 3.11.x or higher
```

---

## Step 3: Create a Project Directory

Choose where you want the project to live:

```bash
# Create project directory (adjust path as desired)
mkdir -p ~/Projects/color-emulator
cd ~/Projects/color-emulator
```

---

## Step 4: Create a Virtual Environment

A virtual environment keeps project dependencies isolated:

```bash
# Create virtual environment
python3 -m venv venv

# Activate it (you'll need to do this each time you work on the project)
source venv/bin/activate
```

Your terminal prompt should now show `(venv)` at the beginning.

**Important**: Always activate the venv before working on the project:
```bash
cd ~/Projects/color-emulator
source venv/bin/activate
```

---

## Step 5: Upgrade pip

```bash
pip install --upgrade pip
```

---

## Step 6: Install Required System Libraries

Some Python packages need system libraries. Install them via Homebrew:

```bash
# Required for rawpy (LibRaw)
brew install libraw

# Required for image processing
brew install libjpeg libpng
```

---

## Step 7: Create requirements.txt

Create a file called `requirements.txt` in your project directory with this content:

```
# Core
numpy>=1.24.0
scipy>=1.10.0

# Image processing
rawpy>=0.18.0
Pillow>=10.0.0
scikit-image>=0.21.0

# Utilities
PyYAML>=6.0
tqdm>=4.65.0

# Development
pytest>=7.0.0
```

You can create this file by running:
```bash
cat > requirements.txt << 'EOF'
# Core
numpy>=1.24.0
scipy>=1.10.0

# Image processing
rawpy>=0.18.0
Pillow>=10.0.0
scikit-image>=0.21.0

# Utilities
PyYAML>=6.0
tqdm>=4.65.0

# Development
pytest>=7.0.0
EOF
```

---

## Step 8: Install Python Dependencies

```bash
pip install -r requirements.txt
```

This may take a few minutes. If you see errors about rawpy, try:
```bash
pip install --no-cache-dir rawpy
```

---

## Step 9: Verify Installation

Create a quick test script to verify everything works:

```bash
cat > test_setup.py << 'EOF'
#!/usr/bin/env python3
"""Verify all dependencies are installed correctly."""

def test_imports():
    print("Testing imports...")
    
    import numpy as np
    print(f"  ✓ numpy {np.__version__}")
    
    import scipy
    print(f"  ✓ scipy {scipy.__version__}")
    
    import rawpy
    print(f"  ✓ rawpy {rawpy.__version__}")
    
    from PIL import Image
    import PIL
    print(f"  ✓ Pillow {PIL.__version__}")
    
    import skimage
    print(f"  ✓ scikit-image {skimage.__version__}")
    
    from skimage.color import deltaE_ciede2000
    print("  ✓ deltaE_ciede2000 available")
    
    import yaml
    print(f"  ✓ PyYAML {yaml.__version__}")
    
    print("\n✅ All dependencies installed correctly!")

if __name__ == "__main__":
    test_imports()
EOF

python test_setup.py
```

You should see checkmarks for all packages.

---

## Step 10: Prepare Test Data Directory

Create the directory structure for your DNG+JPEG pairs:

```bash
mkdir -p data/input
mkdir -p output
```

Place your 10 DNG+JPEG pairs in `data/input/` with matching names:
```
data/input/
├── IMG_001.dng
├── IMG_001.jpg
├── IMG_002.dng
├── IMG_002.jpg
...
```

---

## Step 11: Set Up for the AI Agent

When giving the project to the AI coding agent (like Claude):

1. **Share these files with the agent:**
   - `poc_project_plan.md` (the technical specification)
   - `agent_prompt.md` (the implementation instructions)

2. **Tell the agent the project path:**
   ```
   Project directory: ~/Projects/color-emulator
   Virtual environment is already set up and activated.
   ```

3. **The agent should create all files in the project directory.**

---

## Quick Reference: Common Commands

```bash
# Navigate to project
cd ~/Projects/color-emulator

# Activate virtual environment
source venv/bin/activate

# Deactivate virtual environment (when done)
deactivate

# Install new package
pip install package-name

# Run the tool (after implementation)
python color_emulator.py --input ./data/input --output ./output --time 60

# Run tests
pytest tests/

# Check installed packages
pip list
```

---

## Troubleshooting

### "command not found: python3"
Run: `brew install python@3.11`

### "No module named 'rawpy'"
Make sure venv is activated (`source venv/bin/activate`), then: `pip install rawpy`

### rawpy fails to install
```bash
brew install libraw
pip install --no-cache-dir rawpy
```

### Permission errors
Don't use `sudo` with pip when in a virtual environment. If you see permission errors, make sure your venv is activated.

### "externally-managed-environment" error
You're trying to install packages outside the virtual environment. Activate it first:
```bash
source venv/bin/activate
```

---

## For Linux Server (Optional)

If you later want to run this on a Linux server:

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install python3.11 python3.11-venv python3-pip libraw-dev libjpeg-dev libpng-dev

# Create venv and install
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

---

## Summary

After completing this guide, you will have:

1. ✅ Python 3.11+ installed via Homebrew
2. ✅ A virtual environment at `~/Projects/color-emulator/venv`
3. ✅ All required Python packages installed
4. ✅ Directory structure ready for the AI agent

The AI agent can now implement the code, and you can run it using the commands in the Quick Reference section.
