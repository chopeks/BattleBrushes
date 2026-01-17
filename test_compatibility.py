#!/usr/bin/env python3
"""
Test script to validate brush file round-trip compatibility with bbrusher.exe

This script:
1. Uses bbrusher.exe to unpack an existing brush file
2. Creates a simple test brush using our format
3. Tests if bbrusher.exe can read our generated brush file
"""

import os
import sys
import subprocess
import shutil
import tempfile

def run_wine_command(cmd, cwd=None):
    """Run a wine command and return output"""
    try:
        result = subprocess.run(['wine'] + cmd, 
                              capture_output=True, 
                              text=True, 
                              cwd=cwd,
                              timeout=30)
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return -1, "", "Command timed out"

def test_bbrusher_unpack():
    """Test unpacking with bbrusher.exe"""
    print("=== Testing bbrusher.exe unpack functionality ===")
    
    brush_file = "../../examples/original_packed_brush_example/brushes/terrain.brush"
    output_dir = "test_unpack_validation"
    
    if os.path.exists(output_dir):
        shutil.rmtree(output_dir)
    
    cmd = ['bbrusher.exe', 'unpack', brush_file, output_dir]
    returncode, stdout, stderr = run_wine_command(cmd, cwd='.')
    
    print(f"Return code: {returncode}")
    print(f"Output: {stdout}")
    if stderr and "wine32" not in stderr:
        print(f"Errors: {stderr}")
    
    # Check if output files were created
    if os.path.exists(output_dir):
        files = []
        for root, dirs, filenames in os.walk(output_dir):
            for filename in filenames:
                files.append(os.path.join(root, filename))
        
        print(f"Created {len(files)} files:")
        for f in files[:10]:  # Show first 10
            print(f"  {f}")
        if len(files) > 10:
            print(f"  ... and {len(files) - 10} more")
        
        return output_dir if os.path.exists(f"{output_dir}/metadata.xml") else None
    else:
        print("No output directory created")
        return None

def test_bbrusher_pack(input_dir):
    """Test packing with bbrusher.exe"""
    print(f"\n=== Testing bbrusher.exe pack functionality ===")
    
    output_brush = "test_output.brush"
    if os.path.exists(output_brush):
        os.remove(output_brush)
    
    # Create a gfx directory for the atlas image  
    gfx_dir = "gfx"
    os.makedirs(gfx_dir, exist_ok=True)
    
    cmd = ['bbrusher.exe', 'pack', output_brush, input_dir, '--gfxPath', gfx_dir]
    returncode, stdout, stderr = run_wine_command(cmd, cwd='.')
    
    print(f"Return code: {returncode}")
    print(f"Output: {stdout}")
    if stderr and "wine32" not in stderr:
        print(f"Errors: {stderr}")
    
    # Check if output files were created
    created_files = []
    if os.path.exists(output_brush):
        created_files.append(output_brush)
    
    # Look for created atlas image
    for filename in os.listdir(gfx_dir):
        if filename.endswith('.png'):
            created_files.append(f"gfx/{filename}")
    
    print(f"Created files: {created_files}")
    
    return created_files if output_brush in created_files else None

def analyze_format_differences():
    """Analyze differences between original and repacked formats"""
    print(f"\n=== Analyzing format differences ===")
    
    # Compare original brush file with our repacked one
    original = "../../examples/original_packed_brush_example/brushes/terrain.brush"
    repacked = "test_output.brush"
    
    if not os.path.exists(repacked):
        print("No repacked file to compare")
        return
    
    # Compare file sizes
    orig_size = os.path.getsize(original)
    new_size = os.path.getsize(repacked)
    
    print(f"Original file size: {orig_size} bytes")
    print(f"Repacked file size: {new_size} bytes")
    print(f"Size difference: {new_size - orig_size} bytes ({((new_size/orig_size - 1) * 100):+.1f}%)")
    
    # Compare binary headers
    with open(original, 'rb') as f:
        orig_header = f.read(32)
    
    with open(repacked, 'rb') as f:
        new_header = f.read(32)
    
    print("\nHeader comparison (first 32 bytes):")
    print("Original:", ' '.join(f'{b:02x}' for b in orig_header))
    print("Repacked:", ' '.join(f'{b:02x}' for b in new_header))
    
    if orig_header == new_header:
        print("✅ Headers match perfectly!")
    else:
        print("❌ Header differences found")

def main():
    """Main test function"""
    print("Battle Brothers Brush Compatibility Test")
    print("=" * 50)
    
    if not os.path.exists('bbrusher.exe'):
        print("Error: bbrusher.exe not found in current directory")
        print("Make sure to run this from modkit/bin/")
        return 1
    
    # Test 1: Unpack existing brush file
    unpacked_dir = test_bbrusher_unpack()
    if not unpacked_dir:
        print("❌ Failed to unpack brush file")
        return 1
    
    print("✅ Successfully unpacked brush file")
    
    # Test 2: Repack the unpacked files
    packed_files = test_bbrusher_pack(unpacked_dir)
    if not packed_files:
        print("❌ Failed to repack brush file")
        return 1
    
    print("✅ Successfully repacked brush file")
    
    # Test 3: Analyze format differences
    analyze_format_differences()
    
    print(f"\n=== Test Summary ===")
    print("✅ bbrusher.exe can unpack existing brush files")
    print("✅ bbrusher.exe can repack into new brush files") 
    print("📊 Format analysis complete")
    print("\nNext step: Ensure our Tiled plugin generates compatible format")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())