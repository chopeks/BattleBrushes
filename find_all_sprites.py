#!/usr/bin/env python3
"""
Find all sprites in a .brush file to understand the exact record structure
"""
import struct
import sys

def find_all_sprites(filename):
    with open(filename, 'rb') as f:
        data = f.read()
    
    print(f"File size: {len(data)} bytes")
    
    # Skip header (we know it ends at offset 57)
    header_end = 57
    print(f"Searching for sprites starting from offset {header_end}")
    
    sprites = []
    
    # Search for all potential sprite IDs
    for offset in range(header_end, len(data) - 2):
        id_len = struct.unpack('<H', data[offset:offset+2])[0]
        
        # Reasonable sprite ID length
        if 3 <= id_len <= 50:
            if offset + 2 + id_len <= len(data):
                try:
                    sprite_id = data[offset+2:offset+2+id_len].decode('ascii')
                    if sprite_id.isascii() and all(c.isprintable() for c in sprite_id):
                        # This looks like a valid sprite
                        sprites.append((offset, id_len, sprite_id))
                        print(f"Sprite at 0x{offset:02X} ({offset}): len={id_len}, id='{sprite_id}'")
                except UnicodeDecodeError:
                    continue
    
    print(f"\nFound {len(sprites)} sprites:")
    
    # Calculate distances between sprites
    for i in range(len(sprites) - 1):
        current_offset, current_len, current_id = sprites[i]
        next_offset, next_len, next_id = sprites[i + 1]
        
        distance = next_offset - current_offset
        print(f"  {current_id} -> {next_id}: {distance} bytes apart")
        
        # Try to find where the current sprite actually ends
        sprite_start = current_offset + 2 + current_len  # After ID
        
        # Look for the source path in this sprite
        search_start = sprite_start + 8  # After blob
        found_path = False
        
        for search_offset in range(search_start, next_offset):
            # Look for null-terminated string that could be a path
            for end_offset in range(search_offset, min(search_offset + 100, next_offset)):
                if end_offset < len(data) and data[end_offset] == 0:
                    try:
                        potential_path = data[search_offset:end_offset].decode('ascii')
                        if ('\\' in potential_path or '/' in potential_path) and '.png' in potential_path:
                            print(f"    Path found at 0x{search_offset:02X}: '{potential_path}' (ends at 0x{end_offset:02X})")
                            # After path + null + 8 bytes of floats = expected end
                            expected_end = end_offset + 1 + 8
                            gap = next_offset - expected_end
                            print(f"    Expected sprite end: 0x{expected_end:02X}, actual next sprite: 0x{next_offset:02X}, gap: {gap} bytes")
                            found_path = True
                            break
                    except UnicodeDecodeError:
                        continue
                if found_path:
                    break
            if found_path:
                break

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python3 find_all_sprites.py <brush_file>")
        sys.exit(1)
    
    find_all_sprites(sys.argv[1])