#!/usr/bin/env python3
"""
Analyze .brush file structure to understand sprite record format
"""
import struct
import sys

def analyze_sprite_record(data, sprite_start):
    """Analyze a single sprite record structure"""
    print(f"\nAnalyzing sprite record starting at 0x{sprite_start:02X}:")
    
    offset = sprite_start
    
    # ID length and ID
    id_len = struct.unpack('<H', data[offset:offset+2])[0]
    offset += 2
    sprite_id = data[offset:offset+id_len].decode('ascii')
    offset += id_len
    print(f"  ID: '{sprite_id}' (length: {id_len})")
    
    # 8-byte blob
    blob = data[offset:offset+8]
    blob_hex = ' '.join(f'{b:02x}' for b in blob)
    print(f"  8-byte blob: {blob_hex}")
    offset += 8
    
    # Position/size data
    print(f"  Position data starts at 0x{offset:02X}:")
    
    # Try to parse as the expected structure
    if offset + 20 <= len(data):
        # Format: width(2), height(2), offsetX(2), offsetY(2), flags(2), avgColor(4) = 14 bytes
        width, height, offset_x, offset_y, flags, avg_color = struct.unpack('<hhhhHI', data[offset:offset+14])
        print(f"    width: {width}, height: {height}")
        print(f"    offset: ({offset_x}, {offset_y})")
        print(f"    flags: 0x{flags:04X}")
        print(f"    avg_color: 0x{avg_color:08X}")
        
        # Show remaining bytes in this section
        remaining_pos = data[offset+14:offset+24]
        remaining_hex = ' '.join(f'{b:02x}' for b in remaining_pos)
        print(f"    remaining position data: {remaining_hex}")
    
    # Look for source path by examining the hex dump
    # From hex dump, I can see "terrain\socket_earth.png" starts at 0x79
    print(f"  Looking for actual source path in hex dump...")
    
    # Search for the pattern that looks like a path
    for search_start in range(offset, min(offset + 50, len(data))):
        # Look for null-terminated strings that could be paths
        for i in range(search_start, min(search_start + 100, len(data))):
            if data[i] == 0:  # Found potential null terminator
                potential_path = data[search_start:i]
                try:
                    path_str = potential_path.decode('ascii')
                    if '\\' in path_str or '/' in path_str or path_str.endswith('.png'):
                        print(f"    Found path at 0x{search_start:02X}: '{path_str}' (ends at 0x{i:02X})")
                        
                        # Show trailing data (floats)
                        trail_start = i + 1
                        if trail_start + 8 <= len(data):
                            float1, float2 = struct.unpack('<ff', data[trail_start:trail_start+8])
                            print(f"    Trailing floats: {float1}, {float2}")
                            
                            next_sprite = trail_start + 8
                            print(f"    Next sprite should start at 0x{next_sprite:02X}")
                            print(f"    Total sprite record size: {next_sprite - sprite_start} bytes")
                            
                            # Show what's actually at next sprite position
                            if next_sprite + 2 <= len(data):
                                next_id_len = struct.unpack('<H', data[next_sprite:next_sprite+2])[0]
                                print(f"    Next sprite ID length: {next_id_len}")
                                if 3 <= next_id_len <= 50 and next_sprite + 2 + next_id_len <= len(data):
                                    next_id = data[next_sprite+2:next_sprite+2+next_id_len].decode('ascii', errors='replace')
                                    print(f"    Next sprite ID: '{next_id}'")
                        return
                except UnicodeDecodeError:
                    continue
                break
    
    # Show hex dump of this record
    record_end = min(sprite_start + 150, len(data))
    print(f"\nHex dump of record (0x{sprite_start:02X}-0x{record_end:02X}):")
    for i in range(sprite_start, record_end, 16):
        hex_part = ' '.join(f'{data[j]:02x}' for j in range(i, min(i+16, record_end)))
        ascii_part = ''.join(chr(data[j]) if 32 <= data[j] <= 126 else '.' for j in range(i, min(i+16, record_end)))
        print(f"  {i:08x}  {hex_part:<48} |{ascii_part}|")

def analyze_brush(filename):
    with open(filename, 'rb') as f:
        data = f.read()
    
    print(f"File size: {len(data)} bytes")
    
    # Parse header
    offset = 0
    
    # Magic
    magic = struct.unpack('<I', data[offset:offset+4])[0]
    print(f"Magic: 0x{magic:08X}")
    offset += 4
    
    # Version
    version = struct.unpack('<H', data[offset:offset+2])[0]
    print(f"Version: {version}")
    offset += 2
    
    # Sheet path
    sheet_len = struct.unpack('<H', data[offset:offset+2])[0]
    offset += 2
    sheet_path = data[offset:offset+sheet_len].decode('ascii')
    print(f"Sheet path: '{sheet_path}' (length: {sheet_len})")
    offset += sheet_len + 1  # +1 for null terminator
    
    print(f"After header: offset = {offset} (0x{offset:02X})")
    
    # Category header - skip it for now
    category_start = offset
    print(f"Category header starts at 0x{category_start:02X}")
    
    # Try to find first sprite by looking for reasonable sprite ID lengths
    for test_offset in range(category_start, min(category_start + 200, len(data) - 2), 1):
        if test_offset + 2 > len(data):
            break
            
        id_len = struct.unpack('<H', data[test_offset:test_offset+2])[0]
        
        # Reasonable sprite ID length is 3-50 characters
        if 3 <= id_len <= 50:
            if test_offset + 2 + id_len <= len(data):
                try:
                    sprite_id = data[test_offset+2:test_offset+2+id_len].decode('ascii')
                    if sprite_id.isascii() and all(c.isprintable() for c in sprite_id):
                        print(f"Found potential sprite at 0x{test_offset:02X}: id_len={id_len}, id='{sprite_id}'")
                        print(f"Category header size: {test_offset - category_start} bytes")
                        
                        # Analyze the sprite record structure
                        analyze_sprite_record(data, test_offset)
                        
                        return test_offset - category_start
                except UnicodeDecodeError:
                    continue
    
    print("Could not find sprite records")
    return None

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python3 brush_analyzer.py <brush_file>")
        sys.exit(1)
    
    analyze_brush(sys.argv[1])