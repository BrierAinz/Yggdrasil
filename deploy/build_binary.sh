#!/bin/bash
# Build Lilith Agent standalone binary
set -e

echo "Building Lilith Agent binary..."

# Install PyInstaller if needed
pip install pyinstaller 2>/dev/null || true

# Build
cd "$(dirname "$0")/.."
pyinstaller --onefile --name lilith \
    --add-data "LILITH_README.md:." \
    --add-data "LILITH_ROADMAP.md:." \
    --add-data "LILITH_TOOLS.md:." \
    --exclude-module tkinter \
    --exclude-module matplotlib \
    --exclude-module numpy \
    --exclude-module pandas \
    --strip \
    lilith_agent.py

echo ""
echo "Binary: dist/lilith"
echo "Size: $(du -sh dist/lilith | cut -f1)"
echo ""
echo "Install: cp dist/lilith ~/.local/bin/"
