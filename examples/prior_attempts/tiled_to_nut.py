#!/usr/bin/env python3
"""
Convert a Tiled JSON map (hex) + tileset JSON into a Squirrel tactical template (.nut).

MVP assumptions:
- Base terrain is taken from the layer named "height 0" (fallback).
- Elevation is computed as the maximum N where layer name == "height N" has a non-zero gid at (x,y).
- Terrain variants recognized by tileset image names: grass_01 -> grass1, grass_02 -> grass2, earth_01 -> earth1.
- Unknown tiles default to grass1.

Usage:
  python tools/tiled_to_nut.py tileset/testmap.json tileset/Terrain.json \
    --name tactical.hills_mvp \
    --out templates/tactical/locations/tactical_hills_mvp.nut

Notes:
- This writes a self-contained .nut file; the engine does not parse JSON at runtime.
"""
from __future__ import annotations
import argparse
import json
import os
import sys
import xml.etree.ElementTree as ET


def load_json(path: str):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def basename_noext(p: str) -> str:
    return os.path.splitext(os.path.basename(p))[0]


def id_to_key(id_str: str) -> str | None:
    s = id_str.lower()
    if s.startswith('tile_'):
        s = s[5:]
    if s.startswith('socket_'):
        return None
    s = s.replace('swamp_green', 'swampgreen')
    s = s.replace('swamp_forest', 'swampforest')
    base, num = s, ''
    if '_' in s:
        parts = s.rsplit('_', 1)
        if len(parts) == 2 and parts[1].isdigit():
            base, num = parts[0], parts[1]
    key = f"{base}{int(num)}" if num else base
    fam = key
    for prefix in (
        'grass', 'earth', 'snow', 'desert', 'tundra', 'autumn', 'moss', 'forest',
        'stone', 'steppe', 'swamp', 'swampgreen', 'swampforest', 'legend_cave',
        'legend_desert', 'desert7_oasis', 'road',
    ):
        if fam.startswith(prefix):
            return key
    return None


def build_metadata_map(meta_xml_path: str | None) -> dict[str, str]:
    """Return a map from image basename -> canonical tile key using metadata.xml.
    Keys are lowercase basenames (e.g., 'grass_01'). Values like 'grass1'.
    """
    if not meta_xml_path or not os.path.isfile(meta_xml_path):
        return {}
    try:
        tree = ET.parse(meta_xml_path)
        root = tree.getroot()
    except Exception:
        return {}
    mapping: dict[str, str] = {}
    for spr in root.findall('.//sprite'):
        img = spr.attrib.get('img', '')
        sid = spr.attrib.get('id', '')
        if not img or not sid:
            continue
        base = basename_noext(img).lower().replace('\\', '/').split('/')[-1]
        key = id_to_key(sid)
        if key:
            mapping[base] = key
    return mapping


def classify_tile_name(img_path: str, meta_map: dict[str, str] | None = None) -> str | None:
    """Map a tileset image filename to an internal tactical tile key used by MapGen.

    Strategy: parse the basename, normalize prefixes and underscores, and build
    keys like 'grass1', 'earth2', 'snow3', 'desert7', 'tundra4', 'autumn3',
    'moss2', 'forest1', 'stone1', 'steppe5', 'swamp1', 'swampgreen2', 'swampforest3'.

    Returns None for sockets/unsupported placeholders so caller can decide.
    """
    name = basename_noext(img_path).lower().replace('\\', '/').split('/')[-1]
    # strip common prefixes
    if name.startswith('tile_'):
        name = name[5:]
    # ignore sockets and roads here (not terrain base)
    if name.startswith('socket_'):
        return None
    # Try filename-based classification first (more authoritative than metadata)
    # Normalize special composites
    name = name.replace('swamp_green', 'swampgreen')
    name = name.replace('swamp_forest', 'swampforest')

    # If ends with _<number>, split
    base, num = name, ''
    if '_' in name:
        parts = name.rsplit('_', 1)
        if len(parts) == 2 and parts[1].isdigit():
            base, num = parts[0], parts[1]
    # Accept already-formed names like 'desert7_oasis'
    if num:
        key = f"{base}{int(num)}"
    else:
        key = base

    # Final whitelist of known families; otherwise return None to skip
    fam = key
    for prefix in (
        'grass', 'earth', 'snow', 'desert', 'tundra', 'autumn', 'moss', 'forest',
        'stone', 'steppe', 'swamp', 'swampgreen', 'swampforest', 'legend_cave',
        'legend_desert', 'desert7_oasis', 'road',
    ):
        if fam.startswith(prefix):
            return key
    # Fallback to metadata-derived key if available
    if meta_map and name in meta_map:
        return meta_map[name]
    return None


def build_gid_to_img(tileset_json: dict, firstgid: int) -> dict[int, str]:
    gid_to_img: dict[int, str] = {}
    for t in tileset_json.get('tiles', []):
        tid = t.get('id')
        img = t.get('image')
        if isinstance(tid, int) and img:
            gid = firstgid + tid
            gid_to_img[gid] = img
    return gid_to_img


def extract_layers(map_json: dict) -> tuple[list[dict], list[tuple[int, list[int]]]]:
    """Return (layers, height_layers_by_level).
    height_layers_by_level is a list of (level, data[]) sorted ascending by level.
    """
    layers = map_json.get('layers', [])
    height_layers: list[tuple[int, list[int]]] = []
    for layer in layers:
        name = layer.get('name', '')
        if not isinstance(name, str):
            continue
        if name.startswith('height'):
            # Accept forms: "height", "height N", "heightN"
            level = 0
            parts = name.split()
            if len(parts) >= 2 and parts[0] == 'height':
                try:
                    level = int(parts[1])
                except Exception:
                    level = 0
            else:
                # Try strip prefix
                try:
                    level = int(name.replace('height', '').strip())
                except Exception:
                    level = 0
            data = layer.get('data')
            if isinstance(data, list):
                height_layers.append((level, data))
    height_layers.sort(key=lambda x: x[0])
    return layers, height_layers


def to_grid(data: list[int], width: int, height: int) -> list[list[int]]:
    return [data[y*width:(y+1)*width] for y in range(height)]


def compute_height_grid(height_layers: list[tuple[int, list[int]]], width: int, height: int) -> list[list[int]]:
    grid = [[0 for _ in range(width)] for _ in range(height)]
    for level, data in height_layers:
        if not data:
            continue
        layer_grid = to_grid(data, width, height)
        for y in range(height):
            row = layer_grid[y]
            for x in range(width):
                gid = row[x]
                if gid and level > grid[y][x]:
                    grid[y][x] = level
    return grid


def compute_terrain_index_grid_from_gid_grid(gid_grid: list[list[int]], width: int, height: int, gid_to_img: dict[int, str], meta_map: dict[str, str] | None = None):
    """Build (grid, keys): grid[y][x] is small int code; keys[index] -> tile key string.

    Code 0 means no tile. Indexing starts at 1 for the first discovered key.
    """
    # Discover keys in order of appearance for deterministic indices
    keys: list[str] = [None]  # index 0 is placeholder
    key_to_index: dict[str, int] = {}
    grid = [[0 for _ in range(width)] for _ in range(height)]
    for y in range(height):
        for x in range(width):
            gid = gid_grid[y][x]
            if gid == 0:
                continue
            img = gid_to_img.get(gid, '')
            key = classify_tile_name(img, meta_map) if img else None
            if key is None:
                # Fallback for present but unclassified tiles: default to grass1
                key = 'grass1'
            idx = key_to_index.get(key)
            if idx is None:
                keys.append(key)
                idx = len(keys) - 1
                key_to_index[key] = idx
            grid[y][x] = idx
    return grid, keys


def compute_terrain_gid_grid(width: int, height: int, height_layers: list[tuple[int, list[int]]], base_layer_data: list[int] | None) -> list[list[int]]:
    """Choose a representative terrain GID per cell.
    Preference: topmost height layer (highest level) with non-zero GID.
    Fallback: base layer data (typically 'height 0').
    """
    gid_grid = [[0 for _ in range(width)] for _ in range(height)]
    # Check height layers descending by level
    for level, data in sorted(height_layers, key=lambda x: x[0], reverse=True):
        if not data:
            continue
        layer = to_grid(data, width, height)
        for y in range(height):
            for x in range(width):
                if gid_grid[y][x] == 0 and layer[y][x] != 0:
                    gid_grid[y][x] = layer[y][x]
    # Fallback to base layer where still zero
    if base_layer_data:
        base_grid = to_grid(base_layer_data, width, height)
        for y in range(height):
            for x in range(width):
                if gid_grid[y][x] == 0:
                    gid_grid[y][x] = base_grid[y][x]
    return gid_grid


def write_nut(out_path: str, name: str, width: int, height: int, terrain_grid: list[list[int]], height_grid: list[list[int]], terrain_keys: list[str]):
    out_dir = os.path.dirname(out_path)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
    with open(out_path, 'w', encoding='utf-8') as f:
        w = f.write
        obj_name = name.replace('.', '_')
        w('this.{name} <- this.inherit("scripts/mapgen/tactical_template", {{\n'.format(name=obj_name))
        w('\tm = {},\n')
        w('\tfunction init()\n\t{\n')
        w('\t\tthis.m.Name = "{name}";\n'.format(name=name))
        w('\t\tthis.m.MinX = {w};\n'.format(w=width))
        w('\t\tthis.m.MinY = {h};\n'.format(h=height))
        w('\t}\n\n')
        w('\tfunction fill( _rect, _properties, _pass = 1 )\n\t{\n')
        # Emit tile objects array indexed by code
        w('\t\tlocal Tiles = [ null')
        for i, key in enumerate(terrain_keys):
            if i == 0:
                continue
            w(', this.MapGen.get("tactical.tile.{k}")'.format(k=key))
        w(' ];\n')
        # Emit terrain map
        w('\t\tlocal terrainMap = [\n')
        for y in range(height):
            row = terrain_grid[y]
            w('\t\t\t[' + ', '.join(str(v) for v in row) + ']' + (',' if y < height-1 else '') + '\n')
        w('\t\t];\n')
        # Emit height map
        w('\t\tlocal heightMap = [\n')
        for y in range(height):
            row = height_grid[y]
            w('\t\t\t[' + ', '.join(str(v) for v in row) + ']' + (',' if y < height-1 else '') + '\n')
        w('\t\t];\n')
        # Fill loop
        w('\t\tfor (local y = 0; y < {h}; y = ++y)\n'.format(h=height))
        w('\t\t{\n')
        w('\t\t\tfor (local x = 0; x < {w}; x = ++x)\n'.format(w=width))
        w('\t\t\t{\n')
        w('\t\t\t\tlocal wx = _rect.X + x;\n')
        w('\t\t\t\tlocal wy = _rect.Y + y;\n')
        w('\t\t\t\tlocal tile = this.Tactical.getTileSquare(wx, wy);\n')
        w('\t\t\t\t// Set height first\n')
        w('\t\t\t\ttile.Level = heightMap[y][x];\n')
        w('\t\t\t\t// Stamp terrain\n')
        w('\t\t\t\tlocal code = terrainMap[y][x];\n')
        w('\t\t\t\tlocal rect = { X = wx, Y = wy, W = 1, H = 1, IsEmpty = false };\n')
        w('\t\t\t\tif (code != 0) Tiles[code].fill(rect, _properties);\n')
        w('\t\t\t}\n')
        w('\t\t}\n')
        w('\t\tthis.makeBordersImpassable(_rect);\n')
        w('\t}\n\n')
        w('});\n')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('map_json', help='Path to Tiled map JSON (.json/.tmj)')
    ap.add_argument('tileset_json', nargs='?', default=None, help='Path to Tiled tileset JSON (collection of images). If omitted, inferred from map tilesets[0].source with .json extension.')
    ap.add_argument('--name', default='tactical.hills_mvp', help='Squirrel template name (e.g., tactical.hills_mvp)')
    ap.add_argument('--out', default='templates/tactical/locations/tactical_hills_mvp.nut', help='Output .nut path')
    ap.add_argument('--metadata', default=os.path.join('tileset', 'metadata.xml'), help='Optional metadata.xml to improve tile classification')
    args = ap.parse_args()

    map_json = load_json(args.map_json)

    width = int(map_json.get('width', 0))
    height = int(map_json.get('height', 0))
    if width <= 0 or height <= 0:
        print('Map width/height missing or zero', file=sys.stderr)
        sys.exit(1)

    # Resolve tileset path and firstgid
    tilesets = map_json.get('tilesets', [])
    if not tilesets:
        print('No tilesets in map JSON', file=sys.stderr)
        sys.exit(1)
    ts = tilesets[0]
    firstgid = int(ts.get('firstgid', 1))

    tileset_path = args.tileset_json
    if not tileset_path:
        src = ts.get('source') or ''
        if src:
            base = os.path.basename(src)
            # Prefer a .json sibling if .tsx was referenced
            if base.lower().endswith('.tsx'):
                base = base[:-4] + '.json'
            tileset_path = os.path.join(os.path.dirname(args.map_json), base)
        else:
            tileset_path = os.path.join(os.path.dirname(args.map_json), 'Terrain.json')

    tileset_json = load_json(tileset_path)
    gid_to_img = build_gid_to_img(tileset_json, firstgid)
    meta_map = build_metadata_map(args.metadata)

    layers, height_layers = extract_layers(map_json)
    if not height_layers:
        print('No height layers found (expected layers named "height N")', file=sys.stderr)
        sys.exit(1)

    # Base terrain layer: pick layer named exactly 'height 0' if present; else first layer.
    base_layer_data = None
    for l in layers:
        if l.get('type') == 'tilelayer' and l.get('name') == 'height 0':
            base_layer_data = l.get('data')
            break
    if base_layer_data is None:
        base_layer_data = layers[0].get('data') if layers and layers[0].get('type') == 'tilelayer' else None
    if base_layer_data is None:
        print('Could not find a base terrain layer; aborting', file=sys.stderr)
        sys.exit(1)

    height_grid = compute_height_grid(height_layers, width, height)
    terrain_gid_grid = compute_terrain_gid_grid(width, height, height_layers, base_layer_data)
    terrain_grid, terrain_keys = compute_terrain_index_grid_from_gid_grid(terrain_gid_grid, width, height, gid_to_img, meta_map)

    out_path = args.out
    write_nut(out_path, args.name, width, height, terrain_grid, height_grid, terrain_keys)
    print(f'Wrote {out_path} with name={args.name} size={width}x{height}')


if __name__ == '__main__':
    main()
