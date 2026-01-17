# Battle Brothers .brush Import/Export – Implementation Guide

This guide describes how to implement native `.brush` import/export (including atlas packing) and integrate it into a Tiled‑based workflow or a fork of Tiled, without external tools.

## Overview

- Goal: Read/write Battle Brothers `.brush` files (spritesheet descriptor + per‑sprite metadata) and pack/unpack the associated PNG atlas natively.
- Deliverables:
  - Exporter: Tileset → atlas PNG + `.brush` (descriptor).
  - Importer: `.brush` + atlas PNG → Tileset (image collection or atlas).
  - UI integration: Import/Export commands (Tiled plugin) or native formats (Tiled fork).

## Workflows

### Export (Tileset → .brush)

- Source: Tiled image‑collection tileset (individual PNGs) or an atlas tileset (rects into a sheet).
- Output: Packed atlas PNG and `.brush` that preserve per‑sprite `id`, rects, flags (F), average color (IC), and pivots/edges.

### Import (.brush → Tileset)

- Source: `.brush` file plus its atlas PNG.
- Output: Tiled tileset (image‑collection by cropping into separate PNGs, or a single atlas tileset with rects).

## .brush Format (Observed)

- Endianness: Little‑endian throughout.
- Magic: `0xBAADFAAD` (bytes `AD FA AD BA`).
- Version: `uint16` (vanilla = `17`).
- Header:
  - `sheetPathLen` (`uint16`), followed by ASCII `sheetPath` (e.g., `gfx/terrain.png`), then NUL terminator `0x00`.
  - Category‑level flags/ints (commonly referred to as `b1/b6/b9/b11/i0`) that vary by brush type (`terrain`, `detail`, `object`, `entity`). Preserve and round‑trip; set sensible defaults by category.
- Per‑sprite record (repeated):
  - `idLen` (`uint16`), ASCII `id`, no terminator.
  - 8‑byte opaque blob (appears like a hash/checksum/seed). Preserve if present; generate a stable value for new sprites.
  - Position/size/offsets block (ints/floats) including rect `x,y,w,h`, edges or offsets, a 16‑bit flags field `F`, and a 32‑bit ARGB `ic` average color.
  - NUL‑terminated ASCII `srcPath` (relative path like `terrain\socket_earth.png`).
  - Two `float32` near the tail (category‑dependent pivots/edges; keep order matched to vanilla).
- Count: Some files carry an explicit sprite count near the header block; others stream records to EOF. Prefer writing an explicit count for safety.

## Data Model (Tileset Properties)

- Tileset‑level:
  - `sheetPath` (string): `gfx/...png` path expected by the engine.
  - `brushVersion` (int): default `17`.
  - `brushCategory` (enum): `terrain|detail|object|entity` (selects header defaults and per‑record field ordering).

- Tile‑level:
  - `spriteId` (or `id`) (string): unique sprite identifier.
  - `srcPath` (string): relative PNG path (vanilla uses backslashes). For round‑trip.
  - `flagsF` (`uint16` little‑endian): sort key (see Flags policy).
  - `ic` (`uint32` ARGB): average color.
  - `rect` (ints): `x,y,w,h` in atlas.
  - `pivots`/`edges` (floats/shorts): category‑specific LR/TB or offsets; preserve order.
  - (Optional) `layerRole` (enum): maps to canonical `F` (body, armor, helmet, hair, beard‑top, upgrade‑front/back, injury, blood, etc.).

## Native Export (.brush Write)

1. Validate inputs:
   - Require `sheetPath` and `spriteId` for each tile; ensure rects are available (directly or after packing).
2. Write header:
   - Magic, version.
   - `sheetPathLen` + `sheetPath` + NUL.
   - Category header flags/ints copied from the matching vanilla profile (by `brushCategory`).
   - (Optional) Explicit sprite count, atlas width/height.
3. For each sprite (sorted deterministically by `spriteId`):
   - `idLen` + `id`.
   - 8‑byte opaque blob (preserve or write stable hash of `id|srcPath|rect`).
   - Rect/offsets/edges in the exact integer/float order for the category.
   - `F` (`uint16` LE), `ic` (`uint32` ARGB).
   - NUL‑terminated `srcPath` (backslashes).
   - Two trailing `float32` (pivots/edges) in the observed category order.

## Atlas Packing (Native)

1. Decode each source PNG to RGBA pixel buffers.
2. Pack rects using a skyline or max‑rects algorithm (optionally with padding, PO2 sizing).
3. Compose atlas RGBA buffer.
4. Encode PNG:
   - `IHDR` (32‑bit RGBA, no interlace), `IDAT` (zlib/deflate; a simple implementation with unfiltered scanlines is acceptable), `IEND`.
   - Include `CRC32` per chunk and `Adler32` for zlib stream.
5. Update tiles with final rects and write `.brush` referencing the atlas.

### Unpacking (Optional)

1. Decode atlas PNG to RGBA.
2. Crop each rect to a per‑sprite PNG.
3. Emit image‑collection tileset and store per‑tile metadata from `.brush`.

## Native Import (.brush Read)

1. Parse magic/version; read `sheetPath`.
2. Read and store category header flags/ints (tileset props).
3. Iterate sprite records:
   - Read `id`, 8‑byte blob, rect/edges/offsets, `F`, `ic`, `srcPath`, pivots.
   - For image‑collection: crop atlas into individual PNGs and attach properties.
   - For atlas tileset: create atlas tiles with rects and attach properties.

## Flags (F) Policy

- `F` is a `uint16` little‑endian sort key. Printed as big‑endian hex (e.g., `64FF`), it is actually `0xFF64` in bytes.
- Vanilla conventions:
  - High byte `0x64`: character group.
  - Low byte: sublayer (body `0xFF`, armor `0xFE`, helmet `0xF0`, head `0xF6`, hair `0xF2`, beard‑top `0xFA`, upgrade‑front `0xEF`, upgrade‑back `0xFD`, arrows `0xFB`, injuries `0xF1/0xF3/0xF5`, blood `0x20`, head cut off `0x01`).
- Guidance:
  - Keep high byte `0x64` for actor layers; assign unique low‑byte values for simultaneous overlays.
  - Never stack multiple visible layers with identical `F` in the same screen region (risk of unstable order/batching).
  - Prefer canonical values for vanilla roles; for extra mod layers, reserve an unused low‑byte subrange within `0x64xx`.

## Vanilla‑Specific Fields Often Missed (Handle Carefully)

- **Explicit counts and atlas size** in header:
  - Vanilla includes fields that match sprite count and common atlas dimensions (1024/2048/etc.). Always write the correct count and actual atlas width/height.
- **Category header flags (b1/b6/b9/b11/i0)**:
  - Differ per brush type and influence draw/batch buckets. Copy from the closest vanilla brush category; avoid hardcoding terrain flags on entity brushes (and vice versa).
- **Per‑sprite 8‑byte blob** (hash/seed):
  - Preserve on round‑trip; for new sprites, write a stable, non‑zero value (e.g., hash of `id|src|rect`).
- **Edges/pivots ordering**:
  - Short LR/TB and two trailing float32 must match vanilla order per category. Do not drop or reorder.
- **IC (average color)**:
  - Compute per sprite and write ARGB. Avoid zeros or copy‑pasting; engines may use this for mip/LUT/batching hints.
- **Path normalization**:
  - Use backslashes `\` in `srcPath`, ASCII only, and include a NUL terminator.
- **Endianness of F**:
  - Store as LE `uint16`. Do not write the byte sequence corresponding to printed hex.

## Validation & Linting

- Header:
  - Sprite count matches records written; atlas `W×H` reflects actual PNG.
  - Category flags match expected profile for brush type.
- Flags:
  - Warn on overlapping concurrent sprites sharing the same `F`.
  - Warn on non‑`0x64xx` actor layers (unless explicitly intended).
- IC:
  - Warn on zero `ic` unless the sprite is truly empty/transparent.
- Strings:
  - ASCII only; `srcPath` uses backslashes; all strings with required NUL terminators.
- Blob:
  - Non‑zero and stable across builds unless inputs change.

## Integration Options

- **Tiled plugin (JS)**:
  - Add actions: “Import .brush (native)”, “Export .brush (native)”, “Export .brush (native, pack atlas)”.
  - Vendor a small PNG codec and a bin‑packer as plain JS in the Scripts folder.

- **Tiled fork (C++)**:
  - Implement a `TilesetFormat` for `.brush` (read/write).
  - Use `QImage/QPainter` (or similar) for atlas composition and pixel IO.
  - Add menus for import/export.

## PNG Codec & Packer

- Decoder/Encoder (JS):
  - Vendor a lightweight PNG library (e.g., UPNG.js) or implement minimal RGBA32 codec.
  - Ensure `CRC32` (chunks) and `Adler32` (zlib) are correct.
- Packer:
  - Skyline or max‑rects; sort by height for good packing.
  - Support padding and optional power‑of‑two sheets.
- Licensing:
  - Place third‑party code under `vendor/` with licenses; mention in README.

## Performance & Limits

- Target atlas sizes of 1024/2048/4096 (configurable); paginate if needed (v2).
- JS PNG encode/decode is slower than native but acceptable for hundreds/thousands of sprites.

## Roadmap

1) **v1 – Descriptor‑only export**
   - Write `.brush` from an existing atlas tileset or a tileset with known rects.

2) **v2 – Native pack/unpack**
   - Pack individual PNGs into an atlas and write `.brush`.
   - Import `.brush`, crop atlas into individual PNGs.

3) **v3 – Quality of life**
   - Multi‑atlas support.
   - `layerRole → F` mapping UI with reserved subrange management.
   - Extended defaults per brush category.

---

### Appendix: Practical Defaults per Category

- **terrain/detail**:
  - Header flags: copy from vanilla `terrain.brush` / `detail.brush`.
  - Per‑sprite field order: rects → edges/offsets → `F` → `ic` → `srcPath` → float pivots.

- **object/entity**:
  - Header flags: copy from vanilla `object_0.brush` / `entity_0.brush`.
  - Per‑sprite order similar; ensure the 8‑byte blob is preserved and floats are in the observed order.

### Appendix: Flags (F) Cheatsheet (character layers)

- Body: `0x64FF`
- Armor: `0x64FE`
- Helmet: `0x64F0`
- Head: `0x64F6`
- Hair: `0x64F2`
- Beard top: `0x64FA`
- Upgrade (front): `0x64EF`
- Upgrade (back): `0x64FD`
- Arrows: `0x64FB`
- Injuries: `0x64F1/0x64F3/0x64F5`
- Head blood: `0x6420`
- Head cut off: `0x6401`

