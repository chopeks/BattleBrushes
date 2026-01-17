#!/usr/bin/env python3
"""Quick test of the brush plugin functionality"""

import sys
import os
sys.path.insert(0, os.path.expanduser("~/.local/share/tiled/plugins"))

try:
    from brush_tileset_plugin import BrushTilesetFormat
    
    plugin = BrushTilesetFormat()
    
    # Test with example file
    test_file = "examples/original_packed_brush_example/brushes/terrain.brush"
    
    if os.path.exists(test_file):
        print(f"Testing plugin with: {test_file}")
        print(f"Supports file: {plugin.supportsFile(test_file)}")
        print(f"Name filter: {plugin.nameFilter()}")
        print(f"Short name: {plugin.shortName()}")
        print("✅ Plugin basic functionality works!")
    else:
        print(f"❌ Test file not found: {test_file}")
        print("Plugin installed but cannot test without brush files")
        
except Exception as e:
    print(f"❌ Plugin test failed: {e}")

