#!/bin/bash

# Battle Brothers Brush to Tiled Converter
# Uses the working bbrusher.exe tool to unpack, then converts to Tiled format

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

usage() {
    echo "Usage: $0 <input.brush> <output.tsx>"
    echo ""
    echo "Convert Battle Brothers .brush file to Tiled .tsx tileset format"
    echo ""
    echo "Example:"
    echo "  $0 terrain.brush terrain.tsx"
    echo ""
    echo "This will create:"
    echo "  - terrain.tsx (Tiled tileset file)"
    echo "  - terrain_sprites/ (directory with individual sprite images)"
    echo ""
    exit 1
}

if [ $# -ne 2 ]; then
    usage
fi

INPUT_BRUSH="$1"
OUTPUT_TSX="$2"

if [ ! -f "$INPUT_BRUSH" ]; then
    echo "Error: Input brush file not found: $INPUT_BRUSH"
    exit 1
fi

if ! command -v wine &> /dev/null; then
    echo "Error: Wine is required to run bbrusher.exe"
    echo "Install with: sudo apt install wine"
    exit 1
fi

BBRUSHER_PATH="$SCRIPT_DIR/modkit/bin/bbrusher.exe"
if [ ! -f "$BBRUSHER_PATH" ]; then
    echo "Error: bbrusher.exe not found at: $BBRUSHER_PATH"
    exit 1
fi

echo "=== Battle Brothers Brush to Tiled Converter ==="
echo "Input:  $INPUT_BRUSH"
echo "Output: $OUTPUT_TSX"
echo ""

# Create temporary directory for unpacking
TEMP_DIR=$(mktemp -d)
echo "Using temporary directory: $TEMP_DIR"

# Get absolute paths
INPUT_BRUSH=$(realpath "$INPUT_BRUSH")
OUTPUT_TSX=$(realpath "$OUTPUT_TSX")
OUTPUT_DIR=$(dirname "$OUTPUT_TSX")
OUTPUT_NAME=$(basename "$OUTPUT_TSX" .tsx)

cd "$TEMP_DIR"

echo "Step 1: Unpacking brush file with bbrusher.exe..."
if wine "$BBRUSHER_PATH" unpack "$INPUT_BRUSH" unpacked_brush 2>/dev/null; then
    echo "✅ Successfully unpacked brush file"
else
    echo "❌ Failed to unpack brush file"
    rm -rf "$TEMP_DIR"
    exit 1
fi

if [ ! -f "unpacked_brush/metadata.xml" ]; then
    echo "❌ No metadata.xml found in unpacked brush"
    rm -rf "$TEMP_DIR"
    exit 1
fi

echo "Step 2: Converting to Tiled format..."

# Create Python converter script for the unpacked data
cat > convert_to_tiled.py << 'EOF'
#!/usr/bin/env python3

import xml.etree.ElementTree as ET
import os
import sys
import shutil
from pathlib import Path

def convert_brush_to_tileset(metadata_path, output_tsx, sprites_base_dir):
    """Convert bbrusher metadata.xml to Tiled .tsx format"""
    
    # Parse the metadata.xml
    tree = ET.parse(metadata_path)
    brush = tree.getroot()
    
    print(f"Converting brush: {brush.get('name', 'Unknown')}")
    
    # Create new tileset
    tileset = ET.Element('tileset')
    tileset.set('version', '1.8')
    tileset.set('tiledversion', '1.8.0')
    tileset.set('name', os.path.splitext(os.path.basename(output_tsx))[0])
    tileset.set('tilewidth', '32')
    tileset.set('tileheight', '32')
    tileset.set('columns', '0')  # Image collection
    
    # Get all sprite elements
    sprites = brush.findall('sprite')
    tileset.set('tilecount', str(len(sprites)))
    
    print(f"Found {len(sprites)} sprites")
    
    # Add brush metadata as tileset properties
    properties = ET.SubElement(tileset, 'properties')
    
    for attr in ['version', 'b1', 'b6', 'b9', 'b11', 'i0']:
        if brush.get(attr):
            prop = ET.SubElement(properties, 'property')
            prop.set('name', f'brush{attr.capitalize()}')
            prop.set('type', 'int' if attr != 'name' else 'string')
            prop.set('value', brush.get(attr))
    
    if brush.get('name'):
        prop = ET.SubElement(properties, 'property')
        prop.set('name', 'sheetPath')
        prop.set('type', 'string')
        prop.set('value', brush.get('name'))
    
    # Create sprites directory
    output_dir = os.path.dirname(output_tsx)
    sprites_dir = os.path.join(output_dir, f"{os.path.splitext(os.path.basename(output_tsx))[0]}_sprites")
    os.makedirs(sprites_dir, exist_ok=True)
    
    # Convert each sprite
    for tile_id, sprite in enumerate(sprites):
        # Create tile element
        tile = ET.SubElement(tileset, 'tile')
        tile.set('id', str(tile_id))
        
        # Find the sprite image file
        img_path = sprite.get('img', '').replace('\\', '/')
        sprite_id = sprite.get('id', f'sprite_{tile_id}')
        
        # Look for the actual PNG file
        source_png = None
        for root, dirs, files in os.walk(sprites_base_dir):
            for file in files:
                if file == os.path.basename(img_path) or file == f"{sprite_id}.png":
                    source_png = os.path.join(root, file)
                    break
            if source_png:
                break
        
        if source_png and os.path.exists(source_png):
            # Copy sprite to output directory
            dest_png = os.path.join(sprites_dir, f"{sprite_id}.png")
            shutil.copy2(source_png, dest_png)
            
            # Add image reference
            image = ET.SubElement(tile, 'image')
            rel_path = os.path.relpath(dest_png, os.path.dirname(output_tsx))
            image.set('source', rel_path)
            
            # Get image dimensions
            try:
                from PIL import Image
                with Image.open(dest_png) as img:
                    image.set('width', str(img.width))
                    image.set('height', str(img.height))
            except ImportError:
                # Fallback if PIL not available
                image.set('width', '32')
                image.set('height', '32')
        else:
            print(f"Warning: Image not found for sprite {sprite_id}")
            continue
        
        # Add sprite properties
        tile_props = ET.SubElement(tile, 'properties')
        
        # Convert all sprite attributes to tile properties
        for attr, value in sprite.attrib.items():
            if attr == 'img':
                continue  # Already handled as image source
            
            prop = ET.SubElement(tile_props, 'property')
            prop.set('name', attr)
            
            # Determine property type
            if attr in ['b6', 'offsetX', 'offsetY', 'width', 'height']:
                prop.set('type', 'int')
            elif attr.startswith('ic') or attr in ['f']:
                prop.set('type', 'string')  # Keep hex values as strings
            else:
                prop.set('type', 'string')
            
            prop.set('value', value)
    
    # Write the .tsx file
    ET.indent(tileset, space="  ", level=0)
    tree = ET.ElementTree(tileset)
    tree.write(output_tsx, encoding='utf-8', xml_declaration=True)
    
    print(f"✅ Created Tiled tileset: {output_tsx}")
    print(f"✅ Sprite images in: {sprites_dir}")
    return True

if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Usage: convert_to_tiled.py <metadata.xml> <output.tsx> <sprites_base_dir>")
        sys.exit(1)
    
    metadata_path = sys.argv[1]
    output_tsx = sys.argv[2]
    sprites_base_dir = sys.argv[3]
    
    try:
        convert_brush_to_tileset(metadata_path, output_tsx, sprites_base_dir)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
EOF

# Run the conversion
python3 convert_to_tiled.py unpacked_brush/metadata.xml "$OUTPUT_TSX" unpacked_brush/

if [ $? -eq 0 ]; then
    echo ""
    echo "🎉 Conversion successful!"
    echo ""
    echo "Created files:"
    echo "  📄 $OUTPUT_TSX"
    echo "  📁 ${OUTPUT_NAME}_sprites/"
    echo ""
    echo "You can now open $OUTPUT_TSX in Tiled!"
    echo ""
    echo "To test:"
    echo "  tiled '$OUTPUT_TSX'"
else
    echo "❌ Conversion failed"
fi

# Cleanup
cd "$SCRIPT_DIR"
rm -rf "$TEMP_DIR"
echo "Cleaned up temporary files"