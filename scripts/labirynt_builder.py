#!/usr/bin/env python3
"""Labirynt Builder for Atari 8-bit Jabberwocky Project.

Compiles world/project.yaml and world/objects.yaml into MOS 6502 MADS assembly
data structures in gen/world_data.asm.
Pre-renders 440-byte screen tile buffers and builds Structure-of-Arrays (SoA)
tables for screens, labyrinths, and object properties.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import sys
from typing import Dict, List, Tuple

# Zapewnienie dostępu do pakietu labirynt_studio niezależnie od cwd
_root = Path(__file__).resolve().parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

from labirynt_studio.model.packing import unpack_xy, SCREEN_WIDTH_CHARS, SCREEN_HEIGHT_CHARS
from labirynt_studio.io.objects_loader import ObjectsLibrary
from labirynt_studio.io.project_io import load_project_from_yaml
from labirynt_studio.model.models import Project, Screen, ObjectDefinition

SCREEN_VRAM_SIZE = SCREEN_WIDTH_CHARS * SCREEN_HEIGHT_CHARS  # 40 * 11 = 440 bytes


def bake_screen_vram(screen: Screen, objects_lib: ObjectsLibrary) -> bytearray:
    """Pre-renders a 440-byte VRAM character matrix for a given screen."""
    vram = bytearray(SCREEN_VRAM_SIZE)  # filled with 0 (empty background)

    for inst in screen.objects:
        obj_def = objects_lib.get_by_code(inst.code)
        if not obj_def:
            continue

        w = obj_def.size.width
        h = obj_def.size.height
        tiles = obj_def.tiles

        tile_idx = 0
        for dy in range(h):
            target_y = inst.y + dy
            if target_y >= SCREEN_HEIGHT_CHARS:
                break
            for dx in range(w):
                target_x = inst.x + dx
                if target_x >= SCREEN_WIDTH_CHARS:
                    break
                if tile_idx < len(tiles):
                    offset = target_y * SCREEN_WIDTH_CHARS + target_x
                    vram[offset] = tiles[tile_idx] & 0xFF
                tile_idx += 1

    return vram


def bake_screen_blocking(screen: Screen, objects_lib: ObjectsLibrary) -> bytearray:
    """Pre-renders a 440-byte blocking matrix for a given screen.
    Only solid tiles of objects with blocking: true are marked as 1.
    Empty/transparent tiles (tile == 0) and non-blocking objects remain 0.
    """
    blocking = bytearray(SCREEN_VRAM_SIZE)

    for inst in screen.objects:
        obj_def = objects_lib.get_by_code(inst.code)
        if not obj_def or not obj_def.flags.blocking:
            continue

        w = obj_def.size.width
        h = obj_def.size.height
        tiles = obj_def.tiles

        tile_idx = 0
        for dy in range(h):
            target_y = inst.y + dy
            if target_y >= SCREEN_HEIGHT_CHARS:
                break
            for dx in range(w):
                target_x = inst.x + dx
                if target_x >= SCREEN_WIDTH_CHARS:
                    break
                if tile_idx < len(tiles):
                    tile = tiles[tile_idx] & 0xFF
                    if tile != 0:
                        offset = target_y * SCREEN_WIDTH_CHARS + target_x
                        blocking[offset] = 1
                tile_idx += 1

    return blocking


def format_vram_dta(vram: bytearray) -> List[str]:
    """Formats 440 bytes of VRAM into 11 lines of 40-byte MADS dta statements."""
    lines: List[str] = []
    for row in range(SCREEN_HEIGHT_CHARS):
        start = row * SCREEN_WIDTH_CHARS
        row_bytes = vram[start:start + SCREEN_WIDTH_CHARS]
        byte_strs = [f"${b:02X}" for b in row_bytes]
        lines.append("    dta " + ", ".join(byte_strs))
    return lines


def load_colors(colors_path: Optional[Path]) -> Dict[str, int]:
    """Loads Atari decimal color values from colors.yaml."""
    defaults: Dict[str, int] = {
        "BACKGROUND": 0,
        "PF0": 20,
        "PF1": 24,
        "PF2": 194,
        "PF3_INV": 130,
    }
    if not colors_path or not colors_path.exists():
        return defaults

    try:
        import yaml
        with open(colors_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        if isinstance(data, dict):
            source = data.get("palette") if isinstance(data.get("palette"), dict) else data
            res: Dict[str, int] = {}
            for k, def_v in defaults.items():
                if k in source and isinstance(source[k], dict) and "atari" in source[k]:
                    res[k] = int(source[k]["atari"]) & 0xFF
                elif k in source and isinstance(source[k], int):
                    res[k] = int(source[k]) & 0xFF
                else:
                    res[k] = def_v
            return res
    except Exception:
        pass
    return defaults


def generate_world_asm(
    project: Project,
    objects_lib: ObjectsLibrary,
    colors: Optional[Dict[str, int]] = None,
) -> str:
    """Generates complete MADS assembly code for world data."""
    if colors is None:
        colors = load_colors(Path("world/colors.yaml"))

    asm: List[str] = []

    asm.append("; ==============================================================================")
    asm.append("; AUTO-GENERATED WORLD DATA FOR JABBERWOCKY (Atari 8-bit)")
    asm.append("; Generated by scripts/labirynt_builder.py — DO NOT EDIT MANUALLY")
    asm.append("; ==============================================================================")
    asm.append("")

    # Action Playfield Palette from colors.yaml
    asm.append("; ------------------------------------------------------------------------------")
    asm.append("; ACTION PLAYFIELD PALETTE (compiled from world/colors.yaml)")
    asm.append("; ------------------------------------------------------------------------------")
    asm.append(f"world_color_bk      dta {colors.get('BACKGROUND', 0)}")
    asm.append(f"world_color_pf0     dta {colors.get('PF0', 20)}")
    asm.append(f"world_color_pf1     dta {colors.get('PF1', 24)}")
    asm.append(f"world_color_pf2     dta {colors.get('PF2', 194)}")
    asm.append(f"world_color_pf3     dta {colors.get('PF3_INV', 130)}")
    asm.append("")

    # Equates
    screens_count = len(project.screens)
    labs_count = len(project.labyrinths)
    asm.append(f"WORLD_SCREENS_COUNT     = {screens_count}")
    asm.append(f"WORLD_LABYRINTHS_COUNT  = {labs_count}")
    asm.append(f"WORLD_SCREEN_VRAM_SIZE  = {SCREEN_VRAM_SIZE}")
    asm.append("")

    # Map screen ID to index
    screen_id_to_idx: Dict[str, int] = {s.id: idx for idx, s in enumerate(project.screens)}

    # 1. Screen VRAM Buffers and Object Lists
    asm.append("; ------------------------------------------------------------------------------")
    asm.append("; SCREEN BUFFERS & OBJECT INSTANCE DATA")
    asm.append("; ------------------------------------------------------------------------------")
    for idx, screen in enumerate(project.screens):
        vram = bake_screen_vram(screen, objects_lib)
        blocking = bake_screen_blocking(screen, objects_lib)
        safe_id = screen.id.replace("-", "_").replace(" ", "_")

        asm.append(f"; --- Screen {idx}: {screen.id} ---")
        asm.append(f"screen_{safe_id}_vram")
        asm.extend(format_vram_dta(vram))
        asm.append("")

        asm.append(f"screen_{safe_id}_blocking")
        asm.extend(format_vram_dta(blocking))
        asm.append("")

        asm.append(f"screen_{safe_id}_obj_count")
        asm.append(f"    dta {len(screen.objects)}")

        asm.append(f"screen_{safe_id}_codes")
        if screen.objects:
            codes_str = ", ".join(f"${inst.code:02X}" for inst in screen.objects)
            asm.append(f"    dta {codes_str}")
        else:
            asm.append("    dta 0")

        asm.append(f"screen_{safe_id}_coords")
        if screen.objects:
            coords_str = ", ".join(f"${inst.packed_xy:02X}" for inst in screen.objects)
            asm.append(f"    dta {coords_str}")
        else:
            asm.append("    dta 0")
        asm.append("")

    # 2. Screens Index Tables (SoA)
    asm.append("; ------------------------------------------------------------------------------")
    asm.append("; SCREENS INDEX TABLES (Structure-of-Arrays)")
    asm.append("; ------------------------------------------------------------------------------")
    if project.screens:
        vram_labels = [f"screen_{s.id.replace('-', '_').replace(' ', '_')}_vram" for s in project.screens]
        blocking_labels = [f"screen_{s.id.replace('-', '_').replace(' ', '_')}_blocking" for s in project.screens]
        codes_labels = [f"screen_{s.id.replace('-', '_').replace(' ', '_')}_codes" for s in project.screens]
        coords_labels = [f"screen_{s.id.replace('-', '_').replace(' ', '_')}_coords" for s in project.screens]
        counts = [f"{len(s.objects)}" for s in project.screens]

        asm.append("screens_vram_lo")
        asm.append("    dta " + ", ".join(f"<{lbl}" for lbl in vram_labels))
        asm.append("screens_vram_hi")
        asm.append("    dta " + ", ".join(f">{lbl}" for lbl in vram_labels))

        asm.append("screens_blocking_lo")
        asm.append("    dta " + ", ".join(f"<{lbl}" for lbl in blocking_labels))
        asm.append("screens_blocking_hi")
        asm.append("    dta " + ", ".join(f">{lbl}" for lbl in blocking_labels))

        asm.append("screens_obj_count")
        asm.append("    dta " + ", ".join(counts))

        asm.append("screens_codes_lo")
        asm.append("    dta " + ", ".join(f"<{lbl}" for lbl in codes_labels))
        asm.append("screens_codes_hi")
        asm.append("    dta " + ", ".join(f">{lbl}" for lbl in codes_labels))

        asm.append("screens_coords_lo")
        asm.append("    dta " + ", ".join(f"<{lbl}" for lbl in coords_labels))
        asm.append("screens_coords_hi")
        asm.append("    dta " + ", ".join(f">{lbl}" for lbl in coords_labels))
    else:
        asm.append("screens_vram_lo      dta 0")
        asm.append("screens_vram_hi      dta 0")
        asm.append("screens_blocking_lo  dta 0")
        asm.append("screens_blocking_hi  dta 0")
        asm.append("screens_obj_count    dta 0")
        asm.append("screens_codes_lo     dta 0")
        asm.append("screens_codes_hi     dta 0")
        asm.append("screens_coords_lo    dta 0")
        asm.append("screens_coords_hi    dta 0")
    asm.append("")

    # 3. Labyrinths Data
    asm.append("; ------------------------------------------------------------------------------")
    asm.append("; LABYRINTH DATA & INDEX TABLES")
    asm.append("; ------------------------------------------------------------------------------")
    lab_screen_labels: List[str] = []
    lab_counts: List[str] = []

    for idx, lab in enumerate(project.labyrinths):
        safe_lab_id = lab.id.replace("-", "_").replace(" ", "_")
        lbl = f"lab_{safe_lab_id}_screens"
        lab_screen_labels.append(lbl)
        lab_counts.append(str(len(lab.screens)))

        asm.append(f"; --- Labyrinth {idx}: {lab.id} ({lab.name}) ---")
        asm.append(f"{lbl}")
        if lab.screens:
            indices = [str(screen_id_to_idx.get(sid, 0)) for sid in lab.screens]
            asm.append("    dta " + ", ".join(indices))
        else:
            asm.append("    dta 0")
        asm.append("")

    if project.labyrinths:
        asm.append("labyrinths_screen_count")
        asm.append("    dta " + ", ".join(lab_counts))
        asm.append("labyrinths_screens_lo")
        asm.append("    dta " + ", ".join(f"<{lbl}" for lbl in lab_screen_labels))
        asm.append("labyrinths_screens_hi")
        asm.append("    dta " + ", ".join(f">{lbl}" for lbl in lab_screen_labels))
    else:
        asm.append("labyrinths_screen_count dta 0")
        asm.append("labyrinths_screens_lo   dta 0")
        asm.append("labyrinths_screens_hi   dta 0")
    asm.append("")

    # 4. Object Metadata Tables (size, flags for collision/interaction)
    # Scan max code used or up to 256
    used_codes = {inst.code for s in project.screens for inst in s.objects}
    max_code = max(used_codes) if used_codes else 0
    table_size = max(256, max_code + 1)

    widths = []
    heights = []
    flags = []

    for code in range(table_size):
        obj = objects_lib.get_by_code(code)
        if obj:
            widths.append(f"${obj.size.width:02X}")
            heights.append(f"${obj.size.height:02X}")
            # Bit 0: blocking, Bit 1: interactive, Bit 2: secret
            fl_val = (1 if obj.flags.blocking else 0) | \
                     (2 if obj.flags.interactive else 0) | \
                     (4 if obj.flags.secret else 0)
            flags.append(f"${fl_val:02X}")
        else:
            widths.append("$00")
            heights.append("$00")
            flags.append("$00")

    asm.append("; ------------------------------------------------------------------------------")
    asm.append("; OBJECT DEFINITIONS TABLE (indexed by code 0..255)")
    asm.append("; ------------------------------------------------------------------------------")
    asm.append("obj_type_width")
    for i in range(0, table_size, 16):
        asm.append("    dta " + ", ".join(widths[i:i+16]))
    asm.append("")

    asm.append("obj_type_height")
    for i in range(0, table_size, 16):
        asm.append("    dta " + ", ".join(heights[i:i+16]))
    asm.append("")

    asm.append("obj_type_flags")
    for i in range(0, table_size, 16):
        asm.append("    dta " + ", ".join(flags[i:i+16]))
    asm.append("")

    return "\n".join(asm)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Labirynt Builder: Compile world/project.yaml into MADS assembly"
    )
    parser.add_argument(
        "--project",
        type=str,
        default="world/project.yaml",
        help="Path to project.yaml (default: world/project.yaml)"
    )
    parser.add_argument(
        "--objects",
        type=str,
        default="world/objects.yaml",
        help="Path to objects.yaml (default: world/objects.yaml)"
    )
    parser.add_argument(
        "--colors",
        type=str,
        default=None,
        help="Path to colors.yaml (default: from project.resources.colors or world/colors.yaml)"
    )
    parser.add_argument(
        "--output",
        type=str,
        default="gen/world_data.asm",
        help="Output ASM path (default: gen/world_data.asm)"
    )

    args = parser.parse_args()

    project_path = Path(args.project)
    objects_path = Path(args.objects)
    output_path = Path(args.output)

    if not project_path.exists():
        print(f"Error: Project file not found: {project_path}", file=sys.stderr)
        return 1
    if not objects_path.exists():
        print(f"Error: Objects file not found: {objects_path}", file=sys.stderr)
        return 1

    print(f"Loading project from {project_path}...")
    project, err = load_project_from_yaml(project_path)
    if err or not project:
        print(f"Error loading project: {err}", file=sys.stderr)
        return 1

    colors_path = Path(args.colors) if args.colors else (project_path.parent / project.resources.colors if project.resources and project.resources.colors else Path("world/colors.yaml"))
    if not colors_path.exists():
        colors_path = Path("world/colors.yaml")

    print(f"Loading colors from {colors_path}...")
    colors = load_colors(colors_path)

    print(f"Loading objects from {objects_path}...")
    objects_lib = ObjectsLibrary()
    if not objects_lib.load(objects_path):
        print(f"Error loading objects from {objects_path}", file=sys.stderr)
        return 1

    print(f"Compiling {len(project.screens)} screens and {len(project.labyrinths)} labyrinths...")
    asm_content = generate_world_asm(project, objects_lib, colors)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(asm_content)

    print(f"Successfully generated {output_path} ({len(asm_content)} chars).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
