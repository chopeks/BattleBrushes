#!/bin/bash

# Tiled Brush Plugin Compilation Script
# This script builds just the brush plugin using Tiled's QBS build system

set -e  # Exit on any error

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TILED_DIR="$SCRIPT_DIR/tiled"

echo "=== Tiled Brush Plugin Builder ==="
echo "Script directory: $SCRIPT_DIR"
echo "Tiled directory: $TILED_DIR"

# Check if we have QBS
if ! command -v qbs &> /dev/null; then
    echo "ERROR: QBS build system not found. Please install qbs."
    echo "On Ubuntu/Debian: sudo apt install qbs qt5-qmake qtbase5-dev"
    exit 1
fi

# Check if Qt5 is available
if ! command -v qmake &> /dev/null; then
    echo "ERROR: Qt5 not found. Please install Qt5 development packages."
    echo "On Ubuntu/Debian: sudo apt install qtbase5-dev qtbase5-dev-tools"
    exit 1
fi

# Navigate to Tiled directory
cd "$TILED_DIR"

echo ""
echo "=== Setting up QBS build ==="

# Set up build directory
BUILD_DIR="build-brush"
mkdir -p "$BUILD_DIR"
cd "$BUILD_DIR"

echo "Build directory: $(pwd)"

# Configure QBS project
echo "Configuring QBS project..."
qbs setup-toolchains --detect
qbs setup-qt auto qt5
qbs config defaultProfile qt5

# Build just the brush plugin
echo ""
echo "=== Building brush plugin ==="

# Build the brush plugin specifically
qbs build --file ../tiled.qbs --products brush profile:qt5

if [ $? -eq 0 ]; then
    echo ""
    echo "=== Build successful! ==="
    
    # Find the built plugin
    PLUGIN_PATH=$(find . -name "*brush*" -name "*.so" -o -name "*.dll" -o -name "*.dylib" 2>/dev/null | head -1)
    
    if [ -n "$PLUGIN_PATH" ]; then
        echo "Plugin built at: $PLUGIN_PATH"
        
        # Copy to a convenient location
        cp "$PLUGIN_PATH" "$SCRIPT_DIR/brush_plugin$(echo $PLUGIN_PATH | sed 's/.*\(\.[^.]*\)$/\1/')"
        echo "Plugin copied to: $SCRIPT_DIR/brush_plugin$(echo $PLUGIN_PATH | sed 's/.*\(\.[^.]*\)$/\1/')"
    else
        echo "Plugin built, but could not locate output file."
    fi
    
    echo ""
    echo "To use the plugin:"
    echo "1. Copy the plugin file to your Tiled plugins directory"
    echo "2. Restart Tiled"
    echo "3. The brush format should appear in File -> Open and Export As dialogs"
    
else
    echo ""
    echo "=== Build failed ==="
    echo "Check the error messages above for details."
    exit 1
fi