# Battle Brothers .brush Binary Format Analysis

## What We Know For Certain

### File Header Structure (bytes 0-29)
```
0x00-0x03: Magic bytes "0xBAADFAAD" (little-endian)
0x04-0x05: Version (17 = 0x0011)
0x06-0x07: Sheet path length (N)
0x08-0x08+N: Sheet path string (null-terminated)
0x??: Category string (null-terminated) 
0x??: Unknown header bytes (b1, b6, b9, b11, i0)
0x??: Sprite count (16-bit)
```

### Sprite Entry Structure (Paired Entries)
Each sprite has TWO entries in the file:

#### Entry 1: Sprite Metadata (ID Record)
```
- 48 bytes total
- Contains: sprite ID, dimensions (width/height), 8-byte blob, edge/offset data
```

#### Entry 2: Path Record  
```
- Variable length
- Contains: file path string, UV coordinates (4 floats), additional data
```

### UV Coordinate Format
- 4 consecutive little-endian IEEE-754 floats: u0, v0, u1, v1
- Normalized coordinates (0.0 to 1.0 range)
- Located after null-terminated path string with 4-byte alignment

### Atlas Dimensions
- Actual atlas: 2048x1024 pixels (terrain.png)
- Pixel coordinates = UV * atlas_dimensions

## What We're Confident About

### Working Sprites (Complete Coordinates)
- socket_earth: left=181, top=707, right=360, bottom=806 ✓
- tile_inside: left=1061, top=441, right=1230, bottom=550 ✓  
- tile_road: left=1437, top=795, right=1606, bottom=904 ✓
- zone_of_control_overlay: left=1239, top=559, right=1408, bottom=668 ✓

### Problematic Sprites (Missing top/left)
- zone_range_overlay: left=800, **MISSING TOP**, right=969, bottom=109
- zone_target_overlay: left=1000, **MISSING TOP**, right=1169, bottom=109

## CRITICAL DISCOVERY

**We found the issue!** Our UV coordinate parsing is reading from wrong offsets.

### Raw Binary Analysis Results:
- **socket_earth UV coordinates** (hex at 0x90-0x9f): 
  - Raw: `00 00 00 3a 00 00 b5 3d 00 c0 30 3f 00 c0 49 3f`
  - Floats: u0=0.00048828125, v0=0.08837890625, u1=0.6904296875, v1=0.7880859375
  - **Correct pixels: left=1, top=90, right=1414, bottom=807**

- **zone_range_overlay UV coordinates** (hex at 0x2d4-0x2e3):
  - Raw: `00 a0 34 3f 00 e0 49 3f 00 40 64 3f 00 c0 7f 3f`  
  - Floats: u0=0.70556640625, v0=0.78857421875, u1=0.8916015625, v1=0.9990234375
  - **Correct pixels: left=1445, top=807, right=1826, bottom=1023**

### Our Parser Output (WRONG):
- socket_earth: left=181, top=707 (completely different!)
- zone_range_overlay: left=800, MISSING TOP (also wrong!)

**Root cause: We're scanning for "valid-looking" UV coordinates instead of reading from the correct fixed offsets.**

2. **Header fields interpretation**
   - What do b1, b6, b9, b11, i0 actually represent?
   - Are atlas dimensions stored in header or derived from image?

3. **Binary padding/alignment**
   - Are we correctly handling 4-byte alignment after strings?
   - Are there additional padding bytes we're missing?

## Next Analysis Steps

1. **Raw binary comparison**: Compare working vs broken sprite entries byte-by-byte
2. **Hex dump analysis**: Account for every single byte in problematic sprite entries  
3. **Pattern identification**: Look for systematic differences between sprite types