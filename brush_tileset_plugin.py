#!/usr/bin/env python3
"""
Battle Brothers Brush Tileset Plugin for Tiled
This plugin provides import/export support for Battle Brothers .brush files

Installation:
1. Copy this file to your Tiled plugins directory
2. Restart Tiled
3. Use File -> Open to load .brush files
4. Use File -> Export As to save .brush files
"""

import struct
import os
import sys
from pathlib import Path

# Tiled Python API imports (these work with Tiled 1.8+)
try:
    import tiled
except ImportError:
    print("This script requires Tiled with Python plugin support")
    sys.exit(1)

class BrushTilesetFormat(tiled.Plugin):
    """Battle Brothers Brush format support for Tiled"""
    
    @classmethod
    def nameFilter(cls):
        return "Battle Brothers brush files (*.brush)"
    
    @classmethod
    def shortName(cls):
        return "brush"
    
    @classmethod
    def supportsFile(cls, fileName):
        return fileName.lower().endswith('.brush')
    
    def __init__(self):
        super().__init__()
        self.error_string = ""
    
    def errorString(self):
        return self.error_string
    
    def read(self, fileName):
        """Import .brush file as tileset"""
        try:
            return self._read_brush_file(fileName)
        except Exception as e:
            self.error_string = str(e)
            return None
    
    def write(self, tileset, fileName, options=None):
        """Export tileset as .brush file"""
        try:
            self._write_brush_file(tileset, fileName)
            return True
        except Exception as e:
            self.error_string = str(e)
            return False
    
    def _read_brush_file(self, fileName):
        """Parse .brush file and create tileset"""
        
        # Read and parse brush file
        with open(fileName, 'rb') as f:
            data = f.read()
        
        if len(data) < 16:
            raise ValueError("File too small to be a valid brush file")
        
        offset = 0
        
        # Parse header
        magic = struct.unpack('<I', data[offset:offset+4])[0]
        offset += 4
        
        if magic != 0xBAADFAAD:
            raise ValueError(f"Invalid brush file magic: 0x{magic:08X}")
        
        version = struct.unpack('<H', data[offset:offset+2])[0]
        offset += 2
        
        # Read sheet path
        sheet_path_len = struct.unpack('<H', data[offset:offset+2])[0]
        offset += 2
        
        sheet_path = data[offset:offset+sheet_path_len].decode('ascii')
        offset += sheet_path_len + 1  # +1 for null terminator
        
        # Skip category header (12 bytes)
        offset += 12
        
        # Create tileset
        tileset_name = os.path.splitext(os.path.basename(fileName))[0]
        tileset = tiled.Tileset(tileset_name, 32, 32)  # Default tile size
        
        # Set tileset properties
        tileset.setProperty("brushVersion", version)
        tileset.setProperty("sheetPath", sheet_path)
        tileset.setProperty("brushCategory", "terrain")  # Default
        
        # Parse sprites
        sprite_count = 0
        while offset < len(data) and sprite_count < 100:  # Safety limit
            if offset + 2 > len(data):
                break
            
            # Read sprite ID length
            id_len = struct.unpack('<H', data[offset:offset+2])[0]
            offset += 2
            
            if offset + id_len > len(data):
                break
            
            sprite_id = data[offset:offset+id_len].decode('ascii')
            offset += id_len
            
            # Skip 8-byte blob
            if offset + 8 > len(data):
                break
            offset += 8
            
            # Read rect data (22 bytes)
            if offset + 22 > len(data):
                break
            
            width, height, offset_x, offset_y, flags, ic = struct.unpack('<hhhhHI', data[offset:offset+16])
            left, right, top, bottom = struct.unpack('<hhhh', data[offset+16:offset+24])
            offset += 22
            
            # Read source path (null-terminated)
            src_path_start = offset
            while offset < len(data) and data[offset] != 0:
                offset += 1
            
            if offset >= len(data):
                break
            
            src_path = data[src_path_start:offset].decode('ascii')
            offset += 1  # Skip null terminator
            
            # Skip trailing floats (8 bytes)
            if offset + 8 <= len(data):
                offset += 8
            
            # Create tile (simplified - we'll create a placeholder)
            tile = tileset.addTile()
            
            # Set tile properties
            tile.setProperty("spriteId", sprite_id)
            tile.setProperty("srcPath", src_path)
            tile.setProperty("flagsF", flags)
            tile.setProperty("ic", f"0x{ic:08X}")
            
            if offset_x != 0:
                tile.setProperty("offsetX", offset_x)
            if offset_y != 0:
                tile.setProperty("offsetY", offset_y)
            
            sprite_count += 1
        
        tiled.log(f"Loaded {sprite_count} sprites from brush file")
        return tileset
    
    def _write_brush_file(self, tileset, fileName):
        """Write tileset as .brush file"""
        
        # This is a simplified writer - full implementation would pack atlas
        raise NotImplementedError("Brush writing not yet implemented in Python version")

# Register the plugin
tiled.tilesetFormat = BrushTilesetFormat()
