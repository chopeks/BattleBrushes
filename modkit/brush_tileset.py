#!/usr/bin/env python3
"""
Battle Brothers .brush <-> Tiled tileset wrapper using bbrusher.exe

Features:
- unpack: Run bbrusher unpack on a .brush and generate a Tiled collection-of-images tileset JSON.
- gen-tileset: Generate a Tiled tileset JSON from an existing unpacked directory (sprites.xml/metadata.xml + PNGs).
- pack: Run bbrusher pack to produce a .brush from an input directory (expects sprites.xml).

Note: This script shells out to tools/modkit/bin/bbrusher.exe by default. Override with --bbrusher.

Examples:
- Unpack and create tileset
  python tools/modkit/brush_tileset.py unpack \
    --brush assets/terrain.brush \
    --outDir build/terrain \
    --gfxPath assets \
    --tilesetOut build/terrain/Terrain.json \
    --tilesetName Terrain

- Generate tileset only (directory already unpacked)
  python tools/modkit/brush_tileset.py gen-tileset \
    --dir build/terrain \
    --tilesetOut build/terrain/Terrain.json \
    --tilesetName Terrain

- Pack
  python tools/modkit/brush_tileset.py pack \
    --brush assets/terrain.brush \
    --dir build/terrain \
    --gfxPath assets
"""
from __future__ import annotations
import argparse
import json
import os
import subprocess
import sys
import xml.etree.ElementTree as ET


REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
DEFAULT_BBRUSHER = os.path.join(REPO_ROOT, 'tools', 'modkit', 'bin', 'bbrusher.exe')


def run(cmd: list[str], cwd: str | None = None):
    try:
        subprocess.check_call(cmd, cwd=cwd)
    except FileNotFoundError:
        print(f"ERROR: Command not found: {cmd[0]}", file=sys.stderr)
        sys.exit(1)
    except subprocess.CalledProcessError as e:
        print(f"ERROR: Command failed ({e.returncode}): {' '.join(cmd)}", file=sys.stderr)
        sys.exit(e.returncode)


def ensure_dir(path: str):
    if path and not os.path.isdir(path):
        os.makedirs(path, exist_ok=True)


def png_dimensions(path: str) -> tuple[int, int] | None:
    """Return (width, height) of a PNG without external deps. None if not PNG."""
    try:
        with open(path, 'rb') as f:
            sig = f.read(8)
            if sig != b'\x89PNG\r\n\x1a\n':
                return None
            # IHDR chunk: length(4) 'IHDR'(4) width(4) height(4)
            _len = f.read(4)
            chunk = f.read(4)
            if chunk != b'IHDR':
                return None
            w = int.from_bytes(f.read(4), 'big')
            h = int.from_bytes(f.read(4), 'big')
            return (w, h)
    except Exception:
        return None


def id_to_key(id_str: str) -> str | None:
    s = (id_str or '').lower()
    if s.startswith('tile_'):
        s = s[5:]
    if s.startswith('socket_'):
        return None
    s = s.replace('swamp_green', 'swampgreen').replace('swamp_forest', 'swampforest')
    base, num = s, ''
    if '_' in s:
        parts = s.rsplit('_', 1)
        if len(parts) == 2 and parts[1].isdigit():
            base, num = parts[0], parts[1]
    key = f"{base}{int(num)}" if num else base
    families = (
        'grass', 'earth', 'snow', 'desert', 'tundra', 'autumn', 'moss', 'forest',
        'stone', 'steppe', 'swamp', 'swampgreen', 'swampforest', 'legend_cave',
        'legend_desert', 'desert7_oasis', 'road'
    )
    return key if any(key.startswith(p) for p in families) else None


def load_sprites_xml(dir_path: str) -> list[dict]:
    """Parse sprites.xml or metadata.xml from unpacked dir.
    Return list of {id, img} entries as they appear.
    """
    for name in ('sprites.xml', 'metadata.xml'):
        p = os.path.join(dir_path, name)
        if os.path.isfile(p):
            tree = ET.parse(p)
            root = tree.getroot()
            nodes = root.findall('.//sprite')
            out = []
            for s in nodes:
                sid = s.attrib.get('id')
                img = s.attrib.get('img')
                if not img:
                    continue
                out.append({'id': sid, 'img': img})
            if out:
                return out
    raise FileNotFoundError('No sprites.xml/metadata.xml found in ' + dir_path)


def make_tiled_tileset_json(dir_path: str, tiles: list[dict], name: str, out_path: str):
    # Normalize and compute dimensions
    max_h = 0
    tile_entries = []
    for i, t in enumerate(tiles):
        img_rel = t['img'].replace('\\', '/')
        img_abs = os.path.join(dir_path, img_rel)
        dims = png_dimensions(img_abs)
        w = dims[0] if dims else None
        h = dims[1] if dims else None
        if h and h > max_h:
            max_h = h
        # Tiled tileset JSON entry
        entry = {'id': i, 'image': img_rel}
        if w and h:
            entry['imagewidth'] = w
            entry['imageheight'] = h
        # Add a derived property for engine mapping
        key = id_to_key(t.get('id') or os.path.splitext(os.path.basename(img_rel))[0])
        if key:
            entry['properties'] = [{
                'name': 'terrainKey', 'type': 'string', 'value': key
            }]
        tile_entries.append(entry)

    tileset = {
        'columns': 0,
        'grid': {'height': 1, 'orientation': 'orthogonal', 'width': 1},
        'margin': 0,
        'name': name,
        'objectalignment': 'topleft',
        'spacing': 0,
        'tilecount': len(tile_entries),
        'tiledversion': '1.11.2',
        # Use max_h as a hint for tileheight; not strictly required for image collections
        'tileheight': max_h or 1,
        'tiles': tile_entries,
    }

    ensure_dir(os.path.dirname(out_path))
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(tileset, f, indent=1)
    print(f'Wrote Tiled tileset: {out_path} ({len(tile_entries)} tiles)')


def cmd_unpack(args):
    bbrusher = args.bbrusher or DEFAULT_BBRUSHER
    if not os.path.isfile(bbrusher):
        print(f'ERROR: bbrusher.exe not found at {bbrusher}', file=sys.stderr)
        sys.exit(1)
    out_dir = args.outDir
    ensure_dir(out_dir) if out_dir else None
    cmd = [bbrusher, 'unpack']
    if args.gfxPath:
        cmd += ['--gfxPath', args.gfxPath]
    cmd += [args.brush]
    if out_dir:
        cmd += [out_dir]
    run(cmd)
    # Determine actual output dir
    if not out_dir:
        base = os.path.splitext(os.path.basename(args.brush))[0]
        out_dir = os.path.abspath(os.path.join(os.getcwd(), base))
    tiles = load_sprites_xml(out_dir)
    if args.tilesetOut:
        name = args.tilesetName or os.path.splitext(os.path.basename(args.brush))[0]
        make_tiled_tileset_json(out_dir, tiles, name, args.tilesetOut)


def cmd_gen_tileset(args):
    tiles = load_sprites_xml(args.dir)
    name = args.tilesetName or os.path.basename(os.path.abspath(args.dir))
    make_tiled_tileset_json(args.dir, tiles, name, args.tilesetOut)


def cmd_pack(args):
    bbrusher = args.bbrusher or DEFAULT_BBRUSHER
    if not os.path.isfile(bbrusher):
        print(f'ERROR: bbrusher.exe not found at {bbrusher}', file=sys.stderr)
        sys.exit(1)
    if not os.path.isdir(args.dir):
        print(f'ERROR: Input directory not found: {args.dir}', file=sys.stderr)
        sys.exit(1)
    # Validate presence of sprites.xml
    if not (os.path.isfile(os.path.join(args.dir, 'sprites.xml')) or os.path.isfile(os.path.join(args.dir, 'metadata.xml'))):
        print('WARNING: No sprites.xml/metadata.xml found in input directory. bbrusher pack may fail.')
    cmd = [bbrusher, 'pack']
    if args.gfxPath:
        cmd += ['--gfxPath', args.gfxPath]
    cmd += [args.brush, args.dir]
    run(cmd)


def main():
    ap = argparse.ArgumentParser(description='Battle Brothers .brush <-> Tiled tileset wrapper')
    sub = ap.add_subparsers(dest='cmd', required=True)

    ap.add_argument('--bbrusher', help='Path to bbrusher.exe (defaults to tools/modkit/bin/bbrusher.exe)')

    up = sub.add_parser('unpack', help='Unpack .brush and build Tiled tileset JSON')
    up.add_argument('--brush', required=True, help='Path to .brush file')
    up.add_argument('--outDir', help='Output directory for unpacked sprites (default: derived from brush name)')
    up.add_argument('--gfxPath', help='--gfxPath for bbrusher (sheet dir)')
    up.add_argument('--tilesetOut', help='Path to write Tiled tileset JSON (e.g., Terrain.json)')
    up.add_argument('--tilesetName', help='Tiled tileset name (default: brush basename)')
    up.set_defaults(func=cmd_unpack)

    gt = sub.add_parser('gen-tileset', help='Generate Tiled tileset JSON from an unpacked directory')
    gt.add_argument('--dir', required=True, help='Directory containing sprites.xml/metadata.xml and PNGs')
    gt.add_argument('--tilesetOut', required=True, help='Path to write Tiled tileset JSON')
    gt.add_argument('--tilesetName', help='Tiled tileset name')
    gt.set_defaults(func=cmd_gen_tileset)

    pk = sub.add_parser('pack', help='Pack a directory into a .brush using bbrusher')
    pk.add_argument('--brush', required=True, help='Output .brush path')
    pk.add_argument('--dir', required=True, help='Input directory containing PNGs and sprites.xml')
    pk.add_argument('--gfxPath', help='--gfxPath for bbrusher (sheet dir)')
    pk.set_defaults(func=cmd_pack)

    args = ap.parse_args()
    args.func(args)


if __name__ == '__main__':
    main()

