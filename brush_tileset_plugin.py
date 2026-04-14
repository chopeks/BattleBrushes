#!/usr/bin/env python3
"""
Battle Brothers .brush reader/writer.

Binary format based on bbrusher by Adam Milazzo (public domain).
Can run standalone (pack/unpack CLI) or as a Tiled tileset-format plugin.
"""

import io
import math
import os
import struct
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

try:
    from PIL import Image as PILImage
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

try:
    import tiled
    # Verify this is actually Tiled's scripting API, not a stray module
    if not hasattr(tiled, 'Plugin'):
        raise ImportError('Not the Tiled scripting API')
    TILED_AVAILABLE = True
except (ImportError, AttributeError):
    TILED_AVAILABLE = False


# ── Constants ──────────────────────────────────────────────────────────────────

BRUSH_MAGIC = 0xBAADFAAD
DEFAULT_VERSION = 17
DEFAULT_L0 = 0xBF795EF4D3FE85C5
DEFAULT_FLAGS = 0x6400
DEFAULT_I0 = 1000
DEFAULT_F3 = 2.0

# Header flag byte defaults (b1–b12): indices 0,2,3,4,8 → 1, rest → 0
HEADER_FLAG_DEFAULTS = bytes([1, 0, 1, 1, 1, 0, 0, 0, 1, 0, 0, 0])

# Per-sprite b6–b9 defaults
SPRITE_B6_9_DEFAULTS = bytes([3, 4, 0, 0])


# ── Low-level helpers ──────────────────────────────────────────────────────────

def hash_name(name):
    """Hash a sprite name to uint64 (bbrusher convention)."""
    h = 0
    for c in name:
        h = (h * 65599 + ord(c)) & 0xFFFFFFFFFFFFFFFF
    return h


def _read_str(data, off):
    """Read uint16-length-prefixed UTF-8 string.  Returns (string, new_offset)."""
    n = struct.unpack_from('<H', data, off)[0]
    return data[off + 2:off + 2 + n].decode('utf-8'), off + 2 + n


def _write_str(f, s):
    """Write uint16-length-prefixed UTF-8 string to file-like *f*."""
    b = s.encode('utf-8')
    f.write(struct.pack('<H', len(b)))
    f.write(b)


def _po2(v):
    """Round *v* up to next power of two (minimum 1)."""
    v = max(int(v), 1) - 1
    v |= v >> 1
    v |= v >> 2
    v |= v >> 4
    v |= v >> 8
    v |= v >> 16
    return v + 1


# ── Data containers ───────────────────────────────────────────────────────────

class Frame:
    """One animation frame within a sprite."""
    __slots__ = ('name', 'u1', 'u2', 'v1', 'v2',
                 'edge_left', 'edge_right', 'edge_top', 'edge_bottom')

    def __init__(self):
        self.name = ''
        self.u1 = self.u2 = self.v1 = self.v2 = 0.0
        self.edge_left = self.edge_right = self.edge_top = self.edge_bottom = None

    def pixel_rect(self, img_w, img_h):
        """Return (x, y, w, h) in atlas pixels."""
        x1 = int(round(self.u1 * img_w))
        x2 = int(round(self.u2 * img_w))
        y1 = int(round(self.v1 * img_h))
        y2 = int(round(self.v2 * img_h))
        return x1, y1, x2 - x1, y2 - y1


class Sprite:
    """One sprite record (may contain multiple frames)."""
    __slots__ = ('id', 'hash', 'L0', 'width', 'height',
                 'offset_x', 'offset_y', 'flags',
                 'b1_5', 'rot_speed', 'b6_9',
                 'f1', 'f2', 'ic', 'f3',
                 'frames', 'b10_12')

    def __init__(self):
        self.id = ''
        self.hash = 0
        self.L0 = DEFAULT_L0
        self.width = self.height = 0
        self.offset_x = self.offset_y = 0
        self.flags = DEFAULT_FLAGS
        self.b1_5 = bytes(5)
        self.rot_speed = 0.0
        self.b6_9 = bytes(SPRITE_B6_9_DEFAULTS)
        self.f1 = self.f2 = 0.0
        self.ic = 0
        self.f3 = DEFAULT_F3
        self.frames = []
        self.b10_12 = bytes(3)


class Brush:
    """In-memory representation of a complete .brush file."""
    __slots__ = ('version', 'img_name', 'img_width', 'img_height',
                 'header_flags', 'b13_14', 'i0', 'sprites')

    def __init__(self):
        self.version = DEFAULT_VERSION
        self.img_name = ''
        self.img_width = self.img_height = 0
        self.header_flags = bytearray(HEADER_FLAG_DEFAULTS)
        self.b13_14 = bytes(2)
        self.i0 = DEFAULT_I0
        self.sprites = []


# ── Binary reader ──────────────────────────────────────────────────────────────

def read_brush(data):
    """Parse raw bytes into a *Brush*.  Raises *ValueError* on bad data."""
    if len(data) < 32:
        raise ValueError('File too small to be a valid .brush file')

    o = 0
    magic = struct.unpack_from('<I', data, o)[0]; o += 4
    if magic != BRUSH_MAGIC:
        raise ValueError(f'Invalid magic: 0x{magic:08X}')

    b = Brush()
    b.version = struct.unpack_from('<H', data, o)[0]; o += 2
    b.img_name, o = _read_str(data, o)
    b.img_width, b.img_height = struct.unpack_from('<HH', data, o); o += 4
    b.header_flags = bytearray(data[o:o + 12]); o += 12

    count = struct.unpack_from('<i', data, o)[0]; o += 4
    b.b13_14 = bytes(data[o:o + 2]); o += 2
    b.i0 = struct.unpack_from('<I', data, o)[0]; o += 4

    for _ in range(count):
        s = Sprite()
        s.hash = struct.unpack_from('<Q', data, o)[0]; o += 8
        s.id, o = _read_str(data, o)
        s.L0 = struct.unpack_from('<Q', data, o)[0]; o += 8
        s.width, s.height = struct.unpack_from('<ii', data, o); o += 8
        s.offset_x, s.offset_y = struct.unpack_from('<hh', data, o); o += 4
        s.flags = struct.unpack_from('<I', data, o)[0]; o += 4
        s.b1_5 = bytes(data[o:o + 5]); o += 5
        s.rot_speed = struct.unpack_from('<f', data, o)[0]; o += 4
        s.b6_9 = bytes(data[o:o + 4]); o += 4
        s.f1, s.f2 = struct.unpack_from('<ff', data, o); o += 8
        s.ic = struct.unpack_from('<I', data, o)[0]; o += 4
        s.f3 = struct.unpack_from('<f', data, o)[0]; o += 4

        fc = struct.unpack_from('<H', data, o)[0]; o += 2
        for _ in range(fc):
            fr = Frame()
            fr.name, o = _read_str(data, o)
            fr.u1, fr.u2, fr.v1, fr.v2 = struct.unpack_from('<ffff', data, o); o += 16
            fr.edge_left, fr.edge_right, fr.edge_top, fr.edge_bottom = \
                struct.unpack_from('<ffff', data, o); o += 16
            s.frames.append(fr)

        s.b10_12 = bytes(data[o:o + 3]); o += 3
        b.sprites.append(s)

    return b


# ── Binary writer ──────────────────────────────────────────────────────────────

def write_brush(brush):
    """Serialize a *Brush* to bytes."""
    f = io.BytesIO()

    f.write(struct.pack('<I', BRUSH_MAGIC))
    f.write(struct.pack('<H', brush.version))
    _write_str(f, brush.img_name)
    f.write(struct.pack('<HH', brush.img_width, brush.img_height))
    f.write(bytes(brush.header_flags[:12]).ljust(12, b'\x00'))
    f.write(struct.pack('<i', len(brush.sprites)))
    f.write(bytes(brush.b13_14[:2]).ljust(2, b'\x00'))
    f.write(struct.pack('<I', brush.i0))

    for sp in brush.sprites:
        f.write(struct.pack('<Q', sp.hash))
        _write_str(f, sp.id)
        f.write(struct.pack('<Q', sp.L0))
        f.write(struct.pack('<ii', sp.width, sp.height))
        f.write(struct.pack('<hh', sp.offset_x, sp.offset_y))
        f.write(struct.pack('<I', sp.flags))
        f.write(bytes(sp.b1_5[:5]).ljust(5, b'\x00'))
        f.write(struct.pack('<f', sp.rot_speed))
        f.write(bytes(sp.b6_9[:4]).ljust(4, b'\x00'))
        f.write(struct.pack('<ff', sp.f1, sp.f2))
        f.write(struct.pack('<I', sp.ic))
        f.write(struct.pack('<f', sp.f3))
        f.write(struct.pack('<H', len(sp.frames)))
        for fr in sp.frames:
            _write_str(f, fr.name)
            f.write(struct.pack('<ffff', fr.u1, fr.u2, fr.v1, fr.v2))
            f.write(struct.pack('<ffff',
                                fr.edge_left, fr.edge_right,
                                fr.edge_top, fr.edge_bottom))
        f.write(bytes(sp.b10_12[:3]).ljust(3, b'\x00'))

    return f.getvalue()


# ── XML conversion (bbrusher metadata.xml compatibility) ──────────────────────

def brush_to_xml(brush):
    """Convert a *Brush* to a bbrusher-compatible *metadata.xml* ElementTree root."""
    root = ET.Element('brush')
    root.set('name', brush.img_name)
    root.set('version', str(brush.version))

    for i in range(12):
        if brush.header_flags[i] != HEADER_FLAG_DEFAULTS[i]:
            root.set(f'b{i + 1}', str(brush.header_flags[i]))
    for i in range(2):
        if brush.b13_14[i] != 0:
            root.set(f'b{i + 13}', str(brush.b13_14[i]))
    if brush.i0 != DEFAULT_I0:
        root.set('i0', str(brush.i0))

    for sp in brush.sprites:
        el = ET.SubElement(root, 'sprite')
        el.set('id', sp.id)

        if sp.hash != hash_name(sp.id):
            el.set('hash', f'{sp.hash:016X}')
        if sp.L0 != DEFAULT_L0:
            el.set('L0', f'{sp.L0:016X}')
        if sp.offset_x != 0:
            el.set('offsetX', str(sp.offset_x))
        if sp.offset_y != 0:
            el.set('offsetY', str(sp.offset_y))
        if sp.flags != DEFAULT_FLAGS:
            el.set('f', f'{sp.flags:X}')

        for i in range(5):
            if sp.b1_5[i] != 0:
                el.set(f'b{i + 1}', str(sp.b1_5[i]))
        if sp.rot_speed != 0:
            el.set('rotSpeed', str(sp.rot_speed))
        for i in range(4):
            if sp.b6_9[i] != SPRITE_B6_9_DEFAULTS[i]:
                el.set(f'b{i + 6}', str(sp.b6_9[i]))

        if sp.f1 != 0:
            el.set('f1', str(sp.f1))
            el.set('f2', str(sp.f2))
        ic_str = f'{sp.ic:08X}' if sp.ic != 0 else None
        if ic_str:
            el.set('ic', ic_str)
        if sp.f3 != DEFAULT_F3:
            el.set('f3', str(sp.f3))

        # Width/height: only emit when they differ from first frame's stored dims
        first_stored_w = first_stored_h = 0
        if sp.frames:
            fr0 = sp.frames[0]
            first_stored_w = int(round(fr0.u2 * brush.img_width)) - \
                             int(round(fr0.u1 * brush.img_width))
            first_stored_h = int(round(fr0.v2 * brush.img_height)) - \
                             int(round(fr0.v1 * brush.img_height))
        if first_stored_w != sp.width or first_stored_h != sp.height:
            el.set('width', str(sp.width))
            el.set('height', str(sp.height))

        multi = len(sp.frames) > 1
        for fr in sp.frames:
            target = ET.SubElement(el, 'frame') if multi else el
            target.set('img', fr.name)

            _, _, sw, sh = fr.pixel_rect(brush.img_width, brush.img_height)
            left_def = int(-(sw + 1) / 2)
            right_def = sw // 2
            top_def = int(-(sh + 1) / 2)
            bottom_def = sh // 2

            if fr.edge_left != left_def:
                target.set('left', str(fr.edge_left))
            if fr.edge_right != right_def:
                target.set('right', str(fr.edge_right))
            if fr.edge_top != top_def:
                target.set('top', str(fr.edge_top))
            if fr.edge_bottom != bottom_def:
                target.set('bottom', str(fr.edge_bottom))

        for i in range(3):
            if sp.b10_12[i] != 0:
                el.set(f'b{i + 10}', str(sp.b10_12[i]))

    return root


def xml_to_brush(root):
    """Convert a bbrusher *metadata.xml* root element to a *Brush*.

    Frame UV coords and edge defaults are left unset — they are filled in during
    atlas packing (see *pack_brush_from_dir*).
    """
    b = Brush()
    b.img_name = root.get('name', '')
    b.version = int(root.get('version', str(DEFAULT_VERSION)))

    hf = bytearray(HEADER_FLAG_DEFAULTS)
    for i in range(12):
        v = root.get(f'b{i + 1}')
        if v is not None:
            hf[i] = int(v)
    b.header_flags = hf

    b13 = bytearray(2)
    for i in range(2):
        v = root.get(f'b{i + 13}')
        if v is not None:
            b13[i] = int(v)
    b.b13_14 = bytes(b13)

    b.i0 = int(root.get('i0', str(DEFAULT_I0)))

    for sel in root.findall('sprite'):
        sp = Sprite()
        sp.id = sel.get('id', '')

        h = sel.get('hash')
        sp.hash = int(h, 16) if h else hash_name(sp.id)
        l0 = sel.get('L0')
        sp.L0 = int(l0, 16) if l0 else DEFAULT_L0

        sp.offset_x = int(sel.get('offsetX', '0'))
        sp.offset_y = int(sel.get('offsetY', '0'))

        fv = sel.get('f')
        sp.flags = int(fv, 16) if fv else DEFAULT_FLAGS

        b1 = bytearray(5)
        for i in range(5):
            v = sel.get(f'b{i + 1}')
            if v is not None:
                b1[i] = int(v)
        sp.b1_5 = bytes(b1)

        rs = sel.get('rotSpeed')
        sp.rot_speed = float(rs) if rs else 0.0

        b6 = bytearray(SPRITE_B6_9_DEFAULTS)
        for i in range(4):
            v = sel.get(f'b{i + 6}')
            if v is not None:
                b6[i] = int(v)
        sp.b6_9 = bytes(b6)

        sp.f1 = float(sel.get('f1', '0'))
        sp.f2 = float(sel.get('f2', '0'))
        icv = sel.get('ic')
        sp.ic = int(icv, 16) if icv else 0
        sp.f3 = float(sel.get('f3', str(DEFAULT_F3)))

        sp.width = int(sel.get('width', '0'))
        sp.height = int(sel.get('height', '0'))

        frame_els = sel.findall('frame')
        if not frame_els:
            frame_els = [sel]
        for fel in frame_els:
            fr = Frame()
            fr.name = fel.get('img', '')
            # Edges — read if present, otherwise left at 0 (set during packing)
            for attr, slot in [('left', 'edge_left'), ('right', 'edge_right'),
                               ('top', 'edge_top'), ('bottom', 'edge_bottom')]:
                v = fel.get(attr)
                if v is not None:
                    setattr(fr, slot, float(v))
            sp.frames.append(fr)

        b10 = bytearray(3)
        for i in range(3):
            v = sel.get(f'b{i + 10}')
            if v is not None:
                b10[i] = int(v)
        sp.b10_12 = bytes(b10)

        b.sprites.append(sp)

    return b


# ── Atlas packing ─────────────────────────────────────────────────────────────

def _pack_rects(sizes, spacing=1):
    """Shelf-pack a list of (w, h) tuples into a power-of-two atlas.

    Returns *(atlas_w, atlas_h, positions)* where *positions* is a list of
    *(x, y)* tuples in the same order as *sizes*.
    """
    if not sizes:
        return 1, 1, []

    total_area = sum((w + spacing) * (h + spacing) for w, h in sizes)
    atlas_w = _po2(int(math.sqrt(total_area)))
    atlas_h = _po2(total_area // max(atlas_w, 1))

    # Ensure atlas can fit the widest / tallest single rect
    atlas_w = max(atlas_w, _po2(max(w for w, _ in sizes)))
    atlas_h = max(atlas_h, _po2(max(h for _, h in sizes)))

    # Sort indices by height descending for better shelf utilisation
    order = sorted(range(len(sizes)), key=lambda i: -sizes[i][1])

    while True:
        positions = [None] * len(sizes)
        shelf_y = shelf_x = shelf_h = 0
        fit = True

        for idx in order:
            w, h = sizes[idx]
            if shelf_x + w > atlas_w:
                shelf_y += shelf_h + spacing
                shelf_x = 0
                shelf_h = 0
            if shelf_x + w > atlas_w or shelf_y + h > atlas_h:
                fit = False
                break
            positions[idx] = (shelf_x, shelf_y)
            shelf_x += w + spacing
            shelf_h = max(shelf_h, h)

        if fit:
            used_h = max(y + sizes[i][1] for i, (x, y) in enumerate(positions))
            atlas_h = _po2(used_h)
            return atlas_w, atlas_h, positions

        if atlas_w > atlas_h:
            atlas_h *= 2
        else:
            atlas_w *= 2


def _flip_blit(src, dst, dst_x, dst_y):
    """Paste *src* (PIL Image) into *dst* flipped vertically (BB atlas convention)."""
    flipped = src.transpose(PILImage.FLIP_TOP_BOTTOM)
    dst.paste(flipped, (dst_x, dst_y))


# ── High-level pack / unpack ──────────────────────────────────────────────────

def unpack_brush_to_dir(brush_path, out_dir, gfx_dir=None):
    """Unpack a .brush to individual PNGs + metadata.xml (bbrusher-compatible)."""
    if not PIL_AVAILABLE:
        raise RuntimeError('PIL/Pillow is required for unpacking')

    if gfx_dir is None:
        gfx_dir = str(Path(brush_path).resolve().parent.parent)

    with open(brush_path, 'rb') as fh:
        brush = read_brush(fh.read())

    atlas_path = os.path.join(gfx_dir, brush.img_name)
    atlas = PILImage.open(atlas_path).convert('RGBA')

    os.makedirs(out_dir, exist_ok=True)

    for sp in brush.sprites:
        for fr in sp.frames:
            x, y, w, h = fr.pixel_rect(brush.img_width, brush.img_height)
            cropped = atlas.crop((x, y, x + w, y + h))
            cropped = cropped.transpose(PILImage.FLIP_TOP_BOTTOM)

            frame_path = os.path.join(out_dir, fr.name)
            os.makedirs(os.path.dirname(frame_path), exist_ok=True)
            cropped.save(frame_path)
            print(fr.name)

    # Write metadata.xml
    xml_root = brush_to_xml(brush)
    tree = ET.ElementTree(xml_root)
    ET.indent(tree, space='  ')
    tree.write(os.path.join(out_dir, 'metadata.xml'),
               encoding='unicode', xml_declaration=True)

    print(f'Unpacked {len(brush.sprites)} sprites to {out_dir}')


def pack_brush_from_dir(brush_path, in_dir, gfx_dir=None):
    """Pack individual PNGs + metadata.xml into a .brush + atlas PNG."""
    if not PIL_AVAILABLE:
        raise RuntimeError('PIL/Pillow is required for packing')

    if gfx_dir is None:
        gfx_dir = str(Path(brush_path).resolve().parent.parent)

    tree = ET.parse(os.path.join(in_dir, 'metadata.xml'))
    brush = xml_to_brush(tree.getroot())

    # Load all frame images
    print('Loading images...')
    frame_images = {}
    for sp in brush.sprites:
        for fr in sp.frames:
            if fr.name not in frame_images:
                img_path = os.path.join(in_dir, fr.name)
                print(fr.name)
                frame_images[fr.name] = PILImage.open(img_path).convert('RGBA')

    # Fill in sprite dimensions from first frame where not explicitly set
    for sp in brush.sprites:
        if sp.width == 0 and sp.frames:
            img = frame_images[sp.frames[0].name]
            sp.width = img.width
            sp.height = img.height

    # Pack rectangles
    print('Packing rectangles...')
    frame_names = list(frame_images.keys())
    sizes = [(frame_images[n].width, frame_images[n].height) for n in frame_names]
    spacing = 1 if len(frame_names) > 1 else 0

    atlas_w, atlas_h, positions = _pack_rects(sizes, spacing)
    pos_by_name = dict(zip(frame_names, positions))

    # Set UVs and edge defaults on every frame
    for sp in brush.sprites:
        for fr in sp.frames:
            img = frame_images[fr.name]
            px, py = pos_by_name[fr.name]
            fr.u1 = px / atlas_w
            fr.u2 = (px + img.width) / atlas_w
            fr.v1 = py / atlas_h
            fr.v2 = (py + img.height) / atlas_h

            # Edge defaults (only set if still at zero from XML parse with no
            # explicit override — matches bbrusher behaviour)
            left_def = int(-(img.width + 1) / 2)
            right_def = img.width // 2
            top_def = int(-(img.height + 1) / 2)
            bottom_def = img.height // 2
            if fr.edge_left is None:
                fr.edge_left = float(left_def)
             if fr.edge_right is None:
                fr.edge_right = float(right_def)
             if fr.edge_top is None:
                fr.edge_top = float(top_def)
             if fr.edge_bottom is None:
                fr.edge_bottom = float(bottom_def)

    brush.img_width = atlas_w
    brush.img_height = atlas_h

    # Compose atlas
    print(f'Writing {brush.img_name} ({atlas_w}x{atlas_h})...')
    atlas = PILImage.new('RGBA', (atlas_w, atlas_h), (0, 0, 0, 0))
    for name, img in frame_images.items():
        px, py = pos_by_name[name]
        _flip_blit(img, atlas, px, py)

    # Save atlas PNG
    img_path = os.path.join(gfx_dir, brush.img_name)
    os.makedirs(os.path.dirname(img_path), exist_ok=True)
    atlas.save(img_path, 'PNG')

    # Write .brush
    with open(brush_path, 'wb') as fh:
        fh.write(write_brush(brush))

    print(f'Packed {len(brush.sprites)} sprites')


# ── Tiled plugin ──────────────────────────────────────────────────────────────

if TILED_AVAILABLE:
    class BrushTilesetFormat(tiled.Plugin):
        """Battle Brothers .brush format support for Tiled."""

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
            try:
                return self._read_brush_file(fileName)
            except Exception as e:
                self.error_string = str(e)
                return None

        def write(self, tileset, fileName, options=None):
            try:
                self._write_brush_file(tileset, fileName)
                return True
            except Exception as e:
                self.error_string = str(e)
                return False

        def _read_brush_file(self, fileName):
            with open(fileName, 'rb') as fh:
                brush = read_brush(fh.read())

            tileset_name = os.path.splitext(os.path.basename(fileName))[0]
            tileset = tiled.Tileset(tileset_name, 32, 32)

            tileset.setProperty('brushVersion', brush.version)
            tileset.setProperty('sheetPath', brush.img_name)
            tileset.setProperty('imgWidth', brush.img_width)
            tileset.setProperty('imgHeight', brush.img_height)
            tileset.setProperty('headerFlags', brush.header_flags.hex())
            tileset.setProperty('b13_14', brush.b13_14.hex())
            tileset.setProperty('i0', brush.i0)

            for sp in brush.sprites:
                tile = tileset.addTile()
                tile.setProperty('spriteId', sp.id)
                tile.setProperty('hash', f'{sp.hash:016X}')
                tile.setProperty('L0', f'{sp.L0:016X}')
                tile.setProperty('width', sp.width)
                tile.setProperty('height', sp.height)
                tile.setProperty('offsetX', sp.offset_x)
                tile.setProperty('offsetY', sp.offset_y)
                tile.setProperty('flags', f'{sp.flags:08X}')
                tile.setProperty('b1_5', sp.b1_5.hex())
                tile.setProperty('rotSpeed', sp.rot_speed)
                tile.setProperty('b6_9', sp.b6_9.hex())
                tile.setProperty('f1', sp.f1)
                tile.setProperty('f2', sp.f2)
                tile.setProperty('ic', f'{sp.ic:08X}')
                tile.setProperty('f3', sp.f3)
                tile.setProperty('b10_12', sp.b10_12.hex())

                # Store frames as indexed properties
                tile.setProperty('frameCount', len(sp.frames))
                for fi, fr in enumerate(sp.frames):
                    pfx = f'frame{fi}_'
                    tile.setProperty(pfx + 'name', fr.name)
                    tile.setProperty(pfx + 'u1', fr.u1)
                    tile.setProperty(pfx + 'u2', fr.u2)
                    tile.setProperty(pfx + 'v1', fr.v1)
                    tile.setProperty(pfx + 'v2', fr.v2)
                    tile.setProperty(pfx + 'edgeL', fr.edge_left)
                    tile.setProperty(pfx + 'edgeR', fr.edge_right)
                    tile.setProperty(pfx + 'edgeT', fr.edge_top)
                    tile.setProperty(pfx + 'edgeB', fr.edge_bottom)

            tiled.log(f'[Brush] Loaded {len(brush.sprites)} sprites from {fileName}')
            return tileset

        def _write_brush_file(self, tileset, fileName):
            brush = Brush()
            brush.version = int(tileset.property('brushVersion') or DEFAULT_VERSION)
            brush.img_name = tileset.property('sheetPath') or ''
            brush.img_width = int(tileset.property('imgWidth') or 0)
            brush.img_height = int(tileset.property('imgHeight') or 0)

            hf = tileset.property('headerFlags')
            brush.header_flags = bytearray.fromhex(hf) if hf else bytearray(HEADER_FLAG_DEFAULTS)
            b13 = tileset.property('b13_14')
            brush.b13_14 = bytes.fromhex(b13) if b13 else bytes(2)
            brush.i0 = int(tileset.property('i0') or DEFAULT_I0)

            for ti in range(tileset.tileCount()):
                tile = tileset.tileAt(ti)
                sp = Sprite()
                sp.id = tile.property('spriteId') or ''
                sp.hash = int(tile.property('hash') or '0', 16)
                sp.L0 = int(tile.property('L0') or f'{DEFAULT_L0:016X}', 16)
                sp.width = int(tile.property('width') or 0)
                sp.height = int(tile.property('height') or 0)
                sp.offset_x = int(tile.property('offsetX') or 0)
                sp.offset_y = int(tile.property('offsetY') or 0)
                sp.flags = int(tile.property('flags') or f'{DEFAULT_FLAGS:08X}', 16)
                b15 = tile.property('b1_5')
                sp.b1_5 = bytes.fromhex(b15) if b15 else bytes(5)
                sp.rot_speed = float(tile.property('rotSpeed') or 0)
                b69 = tile.property('b6_9')
                sp.b6_9 = bytes.fromhex(b69) if b69 else bytes(SPRITE_B6_9_DEFAULTS)
                sp.f1 = float(tile.property('f1') or 0)
                sp.f2 = float(tile.property('f2') or 0)
                sp.ic = int(tile.property('ic') or '0', 16)
                sp.f3 = float(tile.property('f3') or DEFAULT_F3)
                b1012 = tile.property('b10_12')
                sp.b10_12 = bytes.fromhex(b1012) if b1012 else bytes(3)

                fc = int(tile.property('frameCount') or 0)
                for fi in range(fc):
                    pfx = f'frame{fi}_'
                    fr = Frame()
                    fr.name = tile.property(pfx + 'name') or ''
                    fr.u1 = float(tile.property(pfx + 'u1') or 0)
                    fr.u2 = float(tile.property(pfx + 'u2') or 0)
                    fr.v1 = float(tile.property(pfx + 'v1') or 0)
                    fr.v2 = float(tile.property(pfx + 'v2') or 0)
                    fr.edge_left = float(tile.property(pfx + 'edgeL') or 0)
                    fr.edge_right = float(tile.property(pfx + 'edgeR') or 0)
                    fr.edge_top = float(tile.property(pfx + 'edgeT') or 0)
                    fr.edge_bottom = float(tile.property(pfx + 'edgeB') or 0)
                    sp.frames.append(fr)

                brush.sprites.append(sp)

            with open(fileName, 'wb') as fh:
                fh.write(write_brush(brush))

            tiled.log(f'[Brush] Wrote {len(brush.sprites)} sprites to {fileName}')

    tiled.tilesetFormat = BrushTilesetFormat()


# ── CLI ───────────────────────────────────────────────────────────────────────

def _print_usage():
    print("""Usage: brush_tileset_plugin.py unpack [options] <file.brush> [outputDir]
  Unpacks sprites from the atlas referenced by file.brush into individual
  PNGs plus a metadata.xml descriptor.

Usage: brush_tileset_plugin.py pack [options] <file.brush> <inputDir>
  Packs PNGs from inputDir (with metadata.xml) into a sprite atlas and
  writes the .brush descriptor.

Usage: brush_tileset_plugin.py roundtrip <file.brush>
  Read a .brush file and write it back, printing byte-level comparison.

Options:
  --gfxPath <directory>
    Directory where the atlas PNG is loaded from / written to.
    Defaults to the parent of the brush file's directory.""")


def main():
    args = sys.argv[1:]
    gfx_dir = None
    command = None
    positional = []

    i = 0
    while i < len(args):
        if args[i].lower() == '--gfxpath' and i + 1 < len(args):
            gfx_dir = args[i + 1]
            i += 2
        elif command is None:
            command = args[i].lower()
            i += 1
        else:
            positional.append(args[i])
            i += 1

    if command == 'unpack' and positional:
        brush_path = positional[0]
        out_dir = positional[1] if len(positional) > 1 else \
            Path(brush_path).stem
        unpack_brush_to_dir(brush_path, out_dir, gfx_dir)

    elif command == 'pack' and len(positional) >= 2:
        brush_path = positional[0]
        in_dir = positional[1]
        pack_brush_from_dir(brush_path, in_dir, gfx_dir)

    elif command == 'roundtrip' and positional:
        brush_path = positional[0]
        with open(brush_path, 'rb') as fh:
            original = fh.read()
        brush = read_brush(original)
        rewritten = write_brush(brush)

        if original == rewritten:
            print(f'Round-trip OK  ({len(original)} bytes)')
        else:
            print(f'MISMATCH  original={len(original)}  rewritten={len(rewritten)}')
            # Find first difference
            for j in range(min(len(original), len(rewritten))):
                if original[j] != rewritten[j]:
                    print(f'  First diff at byte 0x{j:04X}: '
                          f'orig=0x{original[j]:02X} new=0x{rewritten[j]:02X}')
                    # Show surrounding context
                    ctx = 16
                    start = max(0, j - ctx)
                    end = min(len(original), j + ctx)
                    print(f'  orig:    {original[start:end].hex(" ")}')
                    end2 = min(len(rewritten), j + ctx)
                    print(f'  new:     {rewritten[start:end2].hex(" ")}')
                    break
            sys.exit(1)

    else:
        _print_usage()
        sys.exit(1)


if __name__ == '__main__':
    main()
