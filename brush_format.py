#!/usr/bin/env python3
"""
Battle Brothers Brush Format Plugin for Tiled
Works with Tiled's Python plugin system

This plugin registers a new tileset format for Battle Brothers .brush files
"""

import struct
import os
import sys
from pathlib import Path

# Check if we're running in Tiled's Python environment
try:
    import tiled
    from tiled import *
    TILED_AVAILABLE = True
except ImportError:
    TILED_AVAILABLE = False
    print("Warning: Tiled Python API not available")

def log_message(msg):
    """Log message to Tiled or console"""
    if TILED_AVAILABLE and hasattr(tiled, 'log'):
        tiled.log(f"[Brush Plugin] {msg}")
    else:
        print(f"[Brush Plugin] {msg}")

class BrushTilesetFormat:
    """Battle Brothers Brush tileset format handler"""
    
    def __init__(self):
        self.error = ""
        log_message("Brush format handler initialized")
    
    def nameFilter(self):
        return "Battle Brothers brush files (*.brush)"
    
    def shortName(self):
        return "brush"
    
    def capabilities(self):
        # Indicate this format can read files
        if TILED_AVAILABLE and hasattr(tiled, 'FileFormat'):
            return tiled.FileFormat.Read
        return 1  # Read capability
    
    def supportsFile(self, fileName):
        """Check if this format supports the given file"""
        return fileName.lower().endswith('.brush')
    
    def errorString(self):
        return self.error
    
    def read(self, fileName):
        """Read a .brush file and return a Tileset"""
        log_message(f"Attempting to read: {fileName}")
        
        try:
            if not os.path.exists(fileName):
                self.error = f"File not found: {fileName}"
                return None
            
            # Parse the brush file
            with open(fileName, 'rb') as f:
                data = f.read()
            
            if len(data) < 16:
                self.error = "File too small to be a valid brush file"
                return None
            
            # Check magic bytes
            magic = struct.unpack('<I', data[0:4])[0]
            if magic != 0xBAADFAAD:
                self.error = f"Invalid brush file magic: 0x{magic:08X}"
                return None
            
            log_message("Valid brush file detected")
            
            # Create a simple tileset for now
            basename = os.path.splitext(os.path.basename(fileName))[0]
            
            if TILED_AVAILABLE:
                # Try to create tileset using Tiled API
                tileset = tiled.Tileset(basename, 32, 32)  # name, tileWidth, tileHeight
                tileset.setProperty("brushFile", fileName)
                tileset.setProperty("brushFormat", "terrain")  # default
                log_message(f"Created tileset: {basename}")
                return tileset
            else:
                # Fallback for testing
                log_message("Created mock tileset (Tiled API not available)")
                return None
                
        except Exception as e:
            self.error = f"Error reading brush file: {str(e)}"
            log_message(f"Error: {self.error}")
            return None

# Global format instance
brush_format = BrushTilesetFormat()

def register_format():
    """Register the brush format with Tiled"""
    if not TILED_AVAILABLE:
        log_message("Cannot register format - Tiled API not available")
        return
    
    try:
        # Try different registration methods
        if hasattr(tiled, 'registerTilesetFormat'):
            tiled.registerTilesetFormat(brush_format)
            log_message("Registered using registerTilesetFormat")
        elif hasattr(tiled, 'registerFormat'):
            tiled.registerFormat(brush_format)
            log_message("Registered using registerFormat")
        else:
            log_message("Error: No format registration method found")
            log_message(f"Available tiled attributes: {dir(tiled)}")
            
    except Exception as e:
        log_message(f"Registration error: {str(e)}")

# Auto-register when imported by Tiled
if TILED_AVAILABLE:
    register_format()
    log_message("Brush plugin loaded successfully")
else:
    log_message("Plugin loaded in standalone mode")

# For testing outside of Tiled
if __name__ == "__main__":
    # Test the plugin with a brush file
    if len(sys.argv) > 1:
        test_file = sys.argv[1]
        handler = BrushTilesetFormat()
        result = handler.read(test_file)
        print(f"Test result: {result}")
        if handler.error:
            print(f"Error: {handler.error}")
    else:
        print("Usage: python brush_format.py <brush_file>")