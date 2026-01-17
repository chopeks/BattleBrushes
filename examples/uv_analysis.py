#!/usr/bin/env python3
import struct

def hex_to_float(hex_str):
    """Convert little-endian hex string to float"""
    # Remove any spaces and convert to bytes
    hex_bytes = bytes.fromhex(hex_str.replace(" ", ""))
    # Unpack as little-endian float
    return struct.unpack('<f', hex_bytes)[0]

# socket_earth UV coordinates (WORKING)
print("socket_earth (WORKING):")
socket_u0 = hex_to_float("00 00 00 3a")
socket_v0 = hex_to_float("00 00 b5 3d") 
socket_u1 = hex_to_float("00 c0 30 3f")
socket_v1 = hex_to_float("00 c0 49 3f")
print(f"  u0={socket_u0}, v0={socket_v0}, u1={socket_u1}, v1={socket_v1}")
print(f"  Pixels: left={int(socket_u0*2048)}, top={int(socket_v0*1024)}, right={int(socket_u1*2048)}, bottom={int(socket_v1*1024)}")

# zone_range_overlay UV coordinates (BROKEN)
print("\nzone_range_overlay (BROKEN):")
zone_u0 = hex_to_float("00 a0 34 3f")
zone_v0 = hex_to_float("00 e0 49 3f")
zone_u1 = hex_to_float("00 40 64 3f") 
zone_v1 = hex_to_float("00 c0 7f 3f")
print(f"  u0={zone_u0}, v0={zone_v0}, u1={zone_u1}, v1={zone_v1}")
print(f"  Pixels: left={int(zone_u0*2048)}, top={int(zone_v0*1024)}, right={int(zone_u1*2048)}, bottom={int(zone_v1*1024)}")

# Check if these are in valid UV range
print(f"\nValidity check:")
print(f"socket_earth valid UV: u0={0<=socket_u0<=1}, v0={0<=socket_v0<=1}, u1={0<=socket_u1<=1}, v1={0<=socket_v1<=1}")
print(f"zone_range valid UV: u0={0<=zone_u0<=1}, v0={0<=zone_v0<=1}, u1={0<=zone_u1<=1}, v1={0<=zone_v1<=1}")