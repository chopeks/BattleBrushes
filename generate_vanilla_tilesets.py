#!/usr/bin/env python3
"""
Prompt for a Battle Brothers install directory and generate Tiled tilesets
for all vanilla .brush files.
"""

from __future__ import annotations

import argparse
import sys
import zipfile
from pathlib import Path

from brush_to_tileset import create_tsx_tileset, extract_sprites_from_atlas, parse_brush_file


def _prompt_install_dir() -> Path:
    raw = input("Battle Brothers install directory: ").strip()
    return Path(raw).expanduser()


def _normalize_data_dir(install_dir: Path) -> Path | None:
    if (install_dir / "data").is_dir():
        return install_dir / "data"
    if (install_dir / "brushes").is_dir() and (install_dir / "gfx").is_dir():
        return install_dir
    return None


def _extract_data_archive(archive_path: Path, extract_root: Path) -> None:
    extract_root.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive_path) as zf:
        members = [
            m
            for m in zf.namelist()
            if m.startswith("brushes/") or m.startswith("gfx/")
        ]
        for member in members:
            zf.extract(member, extract_root)


def _resolve_data_sources(install_dir: Path, extract_dir: Path) -> tuple[Path, Path]:
    data_dir = _normalize_data_dir(install_dir)
    if data_dir:
        brushes_dir = data_dir / "brushes"
        gfx_dir = data_dir / "gfx"
        if brushes_dir.is_dir() and gfx_dir.is_dir():
            return data_dir, brushes_dir

    data_dir = install_dir / "data" if (install_dir / "data").is_dir() else install_dir
    archive_path = data_dir / "data_001.dat"
    if not archive_path.is_file():
        raise FileNotFoundError("Could not locate data/brushes or data_001.dat")

    extract_root = extract_dir
    if not (extract_root / "brushes").is_dir() or not (extract_root / "gfx").is_dir():
        _extract_data_archive(archive_path, extract_root)

    return extract_root, extract_root / "brushes"


def _sheet_path_to_atlas(data_dir: Path, sheet_path: str) -> Path:
    normalized = sheet_path.replace("\\", "/")
    parts = [p for p in normalized.split("/") if p]
    return data_dir.joinpath(*parts)


def convert_brushes(brushes_dir: Path, data_dir: Path, out_dir: Path, force: bool) -> int:
    count = 0
    brush_paths = sorted(brushes_dir.rglob("*.brush"))
    for brush_path in brush_paths:
        rel = brush_path.relative_to(brushes_dir).with_suffix("")
        out_base = out_dir / rel
        out_base.mkdir(parents=True, exist_ok=True)
        out_tsx = out_base / f"{brush_path.stem}.tsx"

        if out_tsx.exists() and not force:
            print(f"Skipping {brush_path.name}: output exists")
            continue

        header, sprites = parse_brush_file(str(brush_path))
        atlas_path = _sheet_path_to_atlas(data_dir, header["sheet_path"])
        if not atlas_path.exists():
            print(f"Skipping {brush_path.name}: atlas not found at {atlas_path}")
            continue

        sprites_dir = out_base / "sprites"
        extract_sprites_from_atlas(str(atlas_path), sprites, str(sprites_dir))
        create_tsx_tileset(header, sprites, str(out_tsx), str(sprites_dir))
        count += 1

    return count


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate Tiled tilesets for vanilla Battle Brothers brushes"
    )
    parser.add_argument(
        "--install-dir",
        help="Battle Brothers install directory (contains data/)",
    )
    parser.add_argument(
        "--out-dir",
        default="out/vanilla_tilesets",
        help="Output directory for generated tilesets",
    )
    parser.add_argument(
        "--extract-dir",
        default="out/bb_extracted",
        help="Where to extract data_001.dat (if needed)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing tilesets",
    )
    args = parser.parse_args()

    install_dir = Path(args.install_dir).expanduser() if args.install_dir else _prompt_install_dir()
    install_dir = install_dir.resolve()
    if not install_dir.exists():
        print(f"Install directory not found: {install_dir}", file=sys.stderr)
        return 1

    out_dir = Path(args.out_dir).expanduser().resolve()
    extract_dir = Path(args.extract_dir).expanduser().resolve()

    try:
        data_dir, brushes_dir = _resolve_data_sources(install_dir, extract_dir)
    except Exception as exc:
        print(f"Failed to locate game data: {exc}", file=sys.stderr)
        return 1

    out_dir.mkdir(parents=True, exist_ok=True)
    count = convert_brushes(brushes_dir, data_dir, out_dir, args.force)
    print(f"Generated {count} tilesets in {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
