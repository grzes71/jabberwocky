#!/usr/bin/env python3
"""MADS Memory Map Generator.

Parses MADS assembler listing (.lst) and/or label (.lab) files to analyze
memory allocations, detect segment overlaps, validate zero page usage, and
generate both machine-readable (JSON) and human-readable (TXT) memory maps.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import json
from pathlib import Path
import re
import sys
from typing import Dict, List, Optional, Set, Tuple

# Standard Atari OS Zero Page shadow registers and system variables ($0000 - $007F)
ATARI_OS_ZP_SYMBOLS: Set[str] = {
    "LINFLG", "NGFLAG", "FINE", "CYLON", "KEYFLG", "TMPCHR",
    "HOLD1", "LBUFF", "PLYCNT", "RTCLOK", "CRSINH", "SOUNDR",
    "MDAT", "STATUS", "CHKSUM", "BUFADR", "CKEY", "CASSFL",
    "DSTAT", "ATRACT", "DRKMSK", "COLRSH", "TMPTIM", "HOLD2",
    "DMASK", "TMPLBT", "ESCFLG", "TABMAP", "LOGCOL", "BOMBFL",
    "DINDEX", "BRKKEY", "POKMSK", "SHFLOK", "BOTSCR", "TXTROW",
    "TXTCOL", "TINDEX", "TXTSTD", "SUCCES", "RAMTOP", "LMARGN",
    "RMARGN", "ROWCRS", "COLCRS", "DINDEX", "DOSVEC", "DOSINI",
    "APPMHI", "HDWR", "PAL", "BOOT?", "SWPFLG",
}

# ANTIC Display list mode constants and known equates commonly mapped to low numbers
ANTIC_DL_CONSTANTS: Set[str] = {
    "DL_BLANK1", "DL_BLANK2", "DL_BLANK3", "DL_BLANK4",
    "DL_BLANK5", "DL_BLANK6", "DL_BLANK7", "DL_BLANK8",
    "DL_MODE_2", "DL_MODE_3", "DL_MODE_4", "DL_MODE_5",
    "DL_MODE_6", "DL_MODE_7", "DL_MODE_8", "DL_MODE_9",
    "DL_MODE_A", "DL_MODE_B", "DL_MODE_C", "DL_MODE_D",
    "DL_MODE_E", "DL_MODE_F", "DL_HSCROL", "DL_VSCROL",
    "DL_LMS", "DL_DLI", "DL_JMP", "DL_JVB",
}


@dataclass
class MemorySegment:
    """Represents a continuous memory segment or free gap."""

    name: str
    start_address: str  # Hex format e.g. "$3000"
    end_address: str    # Hex format e.g. "$35B8"
    size: int           # Size in bytes
    type: str           # "code", "data", "display_list", "vram", "vector", "zeropage", "free"

    @property
    def start(self) -> int:
        """Integer start address."""
        return int(self.start_address.replace("$", "").replace("0x", ""), 16)

    @property
    def end(self) -> int:
        """Integer end address (inclusive)."""
        return int(self.end_address.replace("$", "").replace("0x", ""), 16)


@dataclass
class ZeroPageVar:
    """Represents a variable in Atari Zero Page."""

    name: str
    address: str        # Hex format e.g. "$80"
    size: int           # Size in bytes
    description: str = ""

    @property
    def addr_int(self) -> int:
        """Integer address."""
        return int(self.address.replace("$", "").replace("0x", ""), 16)


def format_hex(value: int, digits: int = 4) -> str:
    """Format an integer as a 6502-style hex string (e.g. $3000 or $80)."""
    return f"${value:0{digits}X}"


def parse_labels_file(lab_path: Path) -> List[Tuple[int, str]]:
    """Parse a MADS label table file (.lab).

    Returns a list of (address, label_name) tuples.
    """
    labels: List[Tuple[int, str]] = []
    if not lab_path.exists():
        return labels

    with lab_path.open("r", encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("mads ") or line.startswith("Label table:"):
                continue

            # MADS .lab format: [bank] [hex_address] [label_name]
            # e.g.: "00\t3000\tSTART" or "3000 START"
            parts = line.split()
            if len(parts) >= 3:
                addr_hex = parts[1]
                name = parts[2]
            elif len(parts) == 2:
                addr_hex = parts[0]
                name = parts[1]
            else:
                continue

            try:
                addr = int(addr_hex, 16)
                labels.append((addr, name))
            except ValueError:
                continue

    return labels


def parse_listing_file(lst_path: Path) -> Tuple[List[Tuple[int, int]], List[Tuple[int, str]]]:
    """Parse a MADS listing file (.lst).

    Extracts assembled continuous block ranges (e.g. '3000-35B8>') and labels.
    Returns:
        (blocks, labels) where blocks are (start_addr, end_addr) tuples.
    """
    blocks: List[Tuple[int, int]] = []
    labels: List[Tuple[int, str]] = []
    if not lst_path.exists():
        return blocks, labels

    range_pattern = re.compile(r"([0-9A-Fa-f]{4})-([0-9A-Fa-f]{4})>")
    label_pattern = re.compile(r"^\s*\d+\s+([0-9A-Fa-f]{4})\s+([A-Za-z0-9_@]+)\s*$")
    equ_pattern = re.compile(r"^\s*\d+\s*=\s*([0-9A-Fa-f]{4})\s+([A-Za-z0-9_@]+)")

    with lst_path.open("r", encoding="utf-8", errors="replace") as f:
        for line in f:
            # Check for range header
            m_range = range_pattern.search(line)
            if m_range:
                start_addr = int(m_range.group(1), 16)
                end_addr = int(m_range.group(2), 16)
                blocks.append((start_addr, end_addr))

            # Check for labels
            m_lbl = label_pattern.search(line)
            if m_lbl:
                addr = int(m_lbl.group(1), 16)
                name = m_lbl.group(2)
                labels.append((addr, name))
            else:
                m_equ = equ_pattern.search(line)
                if m_equ:
                    addr = int(m_equ.group(1), 16)
                    name = m_equ.group(2)
                    labels.append((addr, name))

    return blocks, labels


def parse_zeropage_asm(zp_asm_path: Path) -> Dict[str, Tuple[int, int, str]]:
    """Parse zeropage.asm to extract user variable names, addresses, sizes, and comments."""
    zp_info: Dict[str, Tuple[int, int, str]] = {}
    if not zp_asm_path.exists():
        return zp_info

    pattern = re.compile(
        r"^\s*([A-Za-z0-9_]+)\s*=\s*\$([0-9A-Fa-f]{2,4})(?:\s*;\s*(.*))?$"
    )
    with zp_asm_path.open("r", encoding="utf-8", errors="replace") as f:
        for line in f:
            m = pattern.match(line)
            if m:
                name = m.group(1)
                addr = int(m.group(2), 16)
                comment = (m.group(3) or "").strip()
                size = 2 if "16-bit" in comment.lower() or "pointer" in comment.lower() else 1
                zp_info[name] = (addr, size, comment)

    return zp_info


def choose_best_segment_name(
    start_addr: int,
    end_addr: int,
    labels: List[Tuple[int, str]],
) -> Tuple[str, str]:
    """Select an informative name and type for a memory block."""
    if start_addr == 0x02E0 and end_addr == 0x02E1:
        return "RUNAD", "vector"
    if start_addr == 0x02E2 and end_addr == 0x02E3:
        return "INITAD", "vector"
    if 0x0200 <= start_addr <= 0x03FF:
        return f"VEC_{start_addr:04X}", "vector"

    # Match labels at start address
    candidates = [name for addr, name in labels if addr == start_addr]
    if not candidates:
        # Match labels within segment
        candidates = [name for addr, name in labels if start_addr <= addr <= end_addr]

    good_candidates = [
        c for c in candidates
        if not re.match(r"^\d+@", c) and not c.startswith("@")
    ]
    if not good_candidates:
        good_candidates = candidates

    chosen = good_candidates[0] if good_candidates else f"SEG_{start_addr:04X}"

    upper_name = chosen.upper()
    if "DLIST" in upper_name or "DL_" in upper_name:
        seg_type = "display_list"
        chosen_name = "DLIST" if "DLIST" in upper_name else chosen
    elif "VRAM" in upper_name or "SCREEN" in upper_name or "TITLE" in upper_name:
        seg_type = "data"
        chosen_name = "VRAM" if "VRAM" in upper_name else chosen
    elif "PM_" in upper_name or "PMG" in upper_name:
        seg_type = "data"
    elif "FONT" in upper_name or "CHAR" in upper_name:
        seg_type = "data"
    elif start_addr >= 0x0400:
        seg_type = "code"
        if "CODE" in upper_name or "START" in upper_name or "MAIN" in upper_name:
            chosen_name = "CODE"
    else:
        seg_type = "data"

    return chosen_name, seg_type


def infer_blocks_from_labels(
    labels: List[Tuple[int, str]],
    gap_threshold: int = 512,
) -> List[Tuple[int, int, str, str]]:
    """Infer continuous blocks from label addresses when no listing file is present.

    Handles explicit `_START`/`_END` pairs, and groups remaining consecutive labels.
    """
    ram_labels = [(addr, name) for addr, name in labels if 0x0100 <= addr < 0xD000]
    if not ram_labels:
        return []

    # 1. Search for explicit start/end pairs
    label_dict: Dict[str, int] = {name: addr for addr, name in ram_labels}
    blocks: List[Tuple[int, int, str, str]] = []
    claimed_addrs: Set[int] = set()

    for name, start_addr in list(label_dict.items()):
        base_name = None
        end_addr = None

        if name.endswith("_START") or name.endswith("_BEG"):
            base_name = name.rsplit("_", 1)[0]
            end_name = f"{base_name}_END"
            if end_name in label_dict:
                end_addr = label_dict[end_name]
        elif name.startswith("START_"):
            base_name = name[6:]
            end_name = f"END_{base_name}"
            if end_name in label_dict:
                end_addr = label_dict[end_name]

        if base_name and end_addr is not None:
            seg_type = "code" if "CODE" in base_name.upper() else "data"
            blocks.append((start_addr, end_addr, base_name, seg_type))
            for a, _ in ram_labels:
                if start_addr <= a <= end_addr:
                    claimed_addrs.add(a)

    # 2. Group remaining unclaimed labels
    unclaimed = [(addr, name) for addr, name in ram_labels if addr not in claimed_addrs]
    if unclaimed:
        sorted_labels = sorted(unclaimed, key=lambda x: x[0])
        current_cluster: List[Tuple[int, str]] = []

        for addr, name in sorted_labels:
            if not current_cluster:
                current_cluster.append((addr, name))
                continue

            prev_addr = current_cluster[-1][0]
            prev_name = current_cluster[-1][1]
            is_prev_end = prev_name.endswith("_END") or prev_name.startswith("END_")
            is_new_start = name.endswith("_START") or name.startswith("START_") or name.endswith("_ADDR")

            if (addr - prev_addr <= gap_threshold) and not is_prev_end and not is_new_start:
                current_cluster.append((addr, name))
            else:
                c_start = current_cluster[0][0]
                c_end = current_cluster[-1][0]
                c_name, c_type = choose_best_segment_name(c_start, c_end, current_cluster)
                blocks.append((c_start, c_end, c_name, c_type))
                current_cluster = [(addr, name)]

        if current_cluster:
            c_start = current_cluster[0][0]
            c_end = current_cluster[-1][0]
            c_name, c_type = choose_best_segment_name(c_start, c_end, current_cluster)
            blocks.append((c_start, c_end, c_name, c_type))

    # Sort blocks by start address
    blocks.sort(key=lambda b: b[0])
    return blocks


def extract_zero_page_vars(
    labels: List[Tuple[int, str]],
    zp_asm_path: Optional[Path] = None,
) -> Tuple[List[ZeroPageVar], List[str]]:
    """Extract and validate zero page variables ($0000 - $00FF).

    Returns:
        (valid_zp_vars, violation_errors)
    """
    violations: List[str] = []
    zp_map: Dict[str, Tuple[int, int, str]] = {}

    if zp_asm_path and zp_asm_path.exists():
        zp_map.update(parse_zeropage_asm(zp_asm_path))

    for addr, name in labels:
        if addr < 0x0080:
            if name in ATARI_OS_ZP_SYMBOLS or name in ANTIC_DL_CONSTANTS:
                continue
            if name.startswith("STATE_") or name.startswith("DL_") or name.startswith("SPRITE_"):
                continue

            is_user_var = (
                name in zp_map
                or name.startswith("ZP_")
                or name.startswith("PTR_")
                or name.startswith("VAR_")
                or name.startswith("USER_")
                or name.startswith("MY_")
                or (not name.isupper() and not name.isdigit())
            )
            if is_user_var:
                violations.append(
                    f"Zero page violation: User variable '{name}' mapped to "
                    f"${addr:02X} in reserved OS Zero Page ($0000-$007F)."
                )
        elif 0x0080 <= addr <= 0x00FF:
            if (
                name.startswith("SPRITE_COL")
                or name.startswith("COLOR_")
                or name.startswith("STATE_")
                or name.startswith("DL_")
                or name in ANTIC_DL_CONSTANTS
            ):
                continue
            if name not in zp_map:
                size = 2 if name.startswith("PTR_") else 1
                zp_map[name] = (addr, size, "User Zero Page Variable")

    zp_vars: List[ZeroPageVar] = []
    sorted_items = sorted(zp_map.items(), key=lambda x: x[1][0])
    for i, (name, (addr, size, desc)) in enumerate(sorted_items):
        if i + 1 < len(sorted_items):
            next_addr = sorted_items[i + 1][1][0]
            if next_addr > addr and next_addr - addr < 4:
                size = next_addr - addr
        zp_vars.append(ZeroPageVar(
            name=name,
            address=format_hex(addr, 2),
            size=size,
            description=desc,
        ))

    return zp_vars, violations


def check_segment_overlaps(segments: List[MemorySegment]) -> List[str]:
    """Check for overlaps between used memory segments."""
    errors: List[str] = []
    used = [s for s in segments if s.type not in ("free", "zeropage")]
    sorted_segs = sorted(used, key=lambda s: s.start)

    for i in range(len(sorted_segs)):
        for j in range(i + 1, len(sorted_segs)):
            s1 = sorted_segs[i]
            s2 = sorted_segs[j]
            if s1.start <= s2.end and s2.start <= s1.end:
                errors.append(
                    f"Memory segment overlap detected: Segment '{s1.name}' "
                    f"({s1.start_address}-{s1.end_address}) overlaps with "
                    f"'{s2.name}' ({s2.start_address}-{s2.end_address})."
                )
    return errors


def check_memory_boundaries(
    segments: List[MemorySegment],
    ram_limit: int = 0xBFFF,
) -> List[str]:
    """Validate that memory segments do not exceed the OS ROM boundary ($BFFF)."""
    errors: List[str] = []
    for s in segments:
        if s.type in ("free", "zeropage", "vector"):
            continue
        if s.end > ram_limit:
            errors.append(
                f"Memory boundary violation: Segment '{s.name}' ends at "
                f"{s.end_address}, exceeding user RAM limit of {format_hex(ram_limit)} "
                f"(OS ROM / Hardware registers boundary)."
            )
        if s.start < 0x0080:
            errors.append(
                f"Zero page violation: Segment '{s.name}' starts at "
                f"{s.start_address}, which is in the OS Zero Page ($0000-$007F)."
            )
    return errors


def compute_memory_map(
    used_segments: List[MemorySegment],
    ram_base: int = 0x0800,
    ram_limit: int = 0xBFFF,
) -> List[MemorySegment]:
    """Compute the complete memory map including free space gaps."""
    all_segments: List[MemorySegment] = []

    vectors = [s for s in used_segments if s.type == "vector"]
    ram_segs = [s for s in used_segments if s.type != "vector"]
    ram_segs.sort(key=lambda s: s.start)

    all_segments.extend(vectors)

    if not ram_segs:
        gap_size = ram_limit - ram_base + 1
        all_segments.append(MemorySegment(
            name="FREE_SPACE",
            start_address=format_hex(ram_base),
            end_address=format_hex(ram_limit),
            size=gap_size,
            type="free",
        ))
        return all_segments

    first_seg = ram_segs[0]
    if first_seg.start > ram_base:
        gap_size = first_seg.start - ram_base
        all_segments.append(MemorySegment(
            name="FREE_SPACE",
            start_address=format_hex(ram_base),
            end_address=format_hex(first_seg.start - 1),
            size=gap_size,
            type="free",
        ))

    for i, seg in enumerate(ram_segs):
        all_segments.append(seg)
        if i + 1 < len(ram_segs):
            next_seg = ram_segs[i + 1]
            if next_seg.start > seg.end + 1:
                gap_start = seg.end + 1
                gap_end = next_seg.start - 1
                gap_size = gap_end - gap_start + 1
                all_segments.append(MemorySegment(
                    name="FREE_SPACE",
                    start_address=format_hex(gap_start),
                    end_address=format_hex(gap_end),
                    size=gap_size,
                    type="free",
                ))

    last_seg = ram_segs[-1]
    if last_seg.end < ram_limit:
        gap_start = last_seg.end + 1
        gap_end = ram_limit
        gap_size = gap_end - gap_start + 1
        all_segments.append(MemorySegment(
            name="FREE_SPACE",
            start_address=format_hex(gap_start),
            end_address=format_hex(gap_end),
            size=gap_size,
            type="free",
        ))

    return all_segments


def generate_ascii_table(
    all_segments: List[MemorySegment],
    zp_vars: List[ZeroPageVar],
    ram_base: int = 0x0800,
    ram_limit: int = 0xBFFF,
) -> str:
    """Generate human-readable ASCII summary table for docs/memory_map.txt."""
    lines: List[str] = []
    separator = "=" * 80
    thin_sep = "-" * 80

    lines.append(separator)
    lines.append("ATARI 8-BIT MEMORY MAP (XL/XE)")
    lines.append("Single Source of Truth (SSOT) — Built for Jabberwocky")
    lines.append(separator)
    lines.append("")

    # Section 1: Zero Page
    lines.append(thin_sep)
    lines.append("1. ZERO PAGE USAGE ($80 - $FF: User Application Space)")
    lines.append(thin_sep)
    lines.append(f"{'Address':<8} {'Size':<6} {'Variable Name':<20} {'Description'}")
    lines.append(thin_sep)

    zp_used_bytes = 0
    max_zp_addr = 0x007F
    for v in zp_vars:
        lines.append(f"{v.address:<8} {v.size:<6} {v.name:<20} {v.description}")
        zp_used_bytes += v.size
        end_var = v.addr_int + v.size - 1
        if end_var > max_zp_addr:
            max_zp_addr = end_var

    free_zp_start = max_zp_addr + 1
    free_zp_end = 0x00FF
    free_zp_size = max(0, free_zp_end - free_zp_start + 1)
    lines.append(thin_sep)
    lines.append(
        f"[ FREE ZERO PAGE: {format_hex(free_zp_start, 2)} - {format_hex(free_zp_end, 2)} "
        f"({free_zp_size} bytes free / 128 bytes total) ]"
    )
    lines.append("")

    # Section 2: Vectors
    vectors = [s for s in all_segments if s.type == "vector"]
    if vectors:
        lines.append(thin_sep)
        lines.append("2. SYSTEM VECTORS ($0200 - $03FF)")
        lines.append(thin_sep)
        lines.append(f"{'Start - End':<15} {'Size (B)':>8}   {'Segment / Name':<20} {'Type'}")
        lines.append(thin_sep)
        for vec in vectors:
            range_str = f"{vec.start_address} - {vec.end_address}"
            lines.append(
                f"{range_str:<15} {vec.size:>8}   {vec.name:<20} {vec.type}"
            )
        lines.append("")

    # Section 3: User RAM
    lines.append(thin_sep)
    lines.append(f"3. USER RAM MAP ({format_hex(ram_base)} - {format_hex(ram_limit)})")
    lines.append(thin_sep)
    lines.append(f"{'Start - End':<15} {'Size (B)':>8}   {'Segment / Name':<20} {'Type'}")
    lines.append(thin_sep)

    total_used_ram = 0
    total_free_ram = 0
    ram_segments = [s for s in all_segments if s.type != "vector"]

    for seg in ram_segments:
        if seg.type == "free":
            total_free_ram += seg.size
            lines.append(
                f"[ FREE SPACE: {seg.start_address} - {seg.end_address} ({seg.size} bytes) ]"
            )
        else:
            total_used_ram += seg.size
            range_str = f"{seg.start_address} - {seg.end_address}"
            lines.append(
                f"{range_str:<15} {seg.size:>8}   {seg.name:<20} {seg.type}"
            )

    total_window = ram_limit - ram_base + 1
    free_percentage = (total_free_ram / total_window * 100) if total_window > 0 else 0

    lines.append(separator)
    lines.append(f"Total RAM Used:  {total_used_ram:>6} bytes")
    lines.append(f"Total Free RAM:  {total_free_ram:>6} bytes ({free_percentage:.1f}% free headroom)")
    lines.append(f"RAM Boundaries:  {format_hex(ram_base)} - {format_hex(ram_limit)} ({total_window} bytes total)")
    lines.append(separator)
    lines.append("Status: VALIDATION PASSED (No overlaps detected, ZP boundary respected)")
    lines.append(separator)

    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate memory map and validate segment boundaries from MADS output."
    )
    parser.add_argument(
        "-i", "--input",
        required=True,
        help="Path to MADS output file (.lab or .lst)",
    )
    parser.add_argument(
        "--listing",
        default=None,
        help="Optional path to listing file (.lst). Auto-detected if alongside .lab",
    )
    parser.add_argument(
        "--out-text",
        default="docs/memory_map.txt",
        help="Output path for human-readable summary (default: docs/memory_map.txt)",
    )
    parser.add_argument(
        "--out-json",
        default="docs/memory_map.json",
        help="Output path for machine-readable JSON (default: docs/memory_map.json)",
    )
    parser.add_argument(
        "--base",
        type=lambda x: int(x, 0),
        default=0x0800,
        help="User RAM base address (default: 0x0800)",
    )
    parser.add_argument(
        "--limit",
        type=lambda x: int(x, 0),
        default=0xBFFF,
        help="User RAM limit address before OS ROM boundary (default: 0xBFFF)",
    )
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"Error: input file not found: {input_path}", file=sys.stderr)
        return 1

    lst_path: Optional[Path] = None
    lab_path: Optional[Path] = None

    if input_path.suffix.lower() == ".lst":
        lst_path = input_path
        candidate_lab = input_path.with_suffix(".lab")
        if candidate_lab.exists():
            lab_path = candidate_lab
    elif input_path.suffix.lower() == ".lab":
        lab_path = input_path
        if args.listing:
            lst_path = Path(args.listing)
        else:
            candidate_lst = input_path.with_suffix(".lst")
            if candidate_lst.exists():
                lst_path = candidate_lst
    else:
        lab_path = input_path

    labels: List[Tuple[int, str]] = []
    blocks: List[Tuple[int, int]] = []

    if lab_path and lab_path.exists():
        labels.extend(parse_labels_file(lab_path))

    if lst_path and lst_path.exists():
        lst_blocks, lst_labels = parse_listing_file(lst_path)
        blocks.extend(lst_blocks)
        existing_names = {name for _, name in labels}
        for addr, name in lst_labels:
            if name not in existing_names:
                labels.append((addr, name))

    zp_asm_candidates = [
        Path("zeropage.asm"),
        input_path.parent / "zeropage.asm",
        input_path.parent.parent / "zeropage.asm",
    ]
    zp_asm_path = next((p for p in zp_asm_candidates if p.exists()), None)

    # 1. Zero page extraction & validation
    zp_vars, zp_violations = extract_zero_page_vars(labels, zp_asm_path)
    if zp_violations:
        for err in zp_violations:
            print(f"ERROR: {err}", file=sys.stderr)
        return 1

    # 2. Build used segments
    used_segments: List[MemorySegment] = []
    if blocks:
        for start_addr, end_addr in blocks:
            name, seg_type = choose_best_segment_name(start_addr, end_addr, labels)
            size = end_addr - start_addr + 1
            used_segments.append(MemorySegment(
                name=name,
                start_address=format_hex(start_addr),
                end_address=format_hex(end_addr),
                size=size,
                type=seg_type,
            ))
    else:
        inferred = infer_blocks_from_labels(labels)
        for start_addr, end_addr, name, seg_type in inferred:
            size = end_addr - start_addr + 1
            used_segments.append(MemorySegment(
                name=name,
                start_address=format_hex(start_addr),
                end_address=format_hex(end_addr),
                size=size,
                type=seg_type,
            ))

    # 3. Validation: Overlaps & Boundaries
    overlap_errors = check_segment_overlaps(used_segments)
    if overlap_errors:
        for err in overlap_errors:
            print(f"ERROR: {err}", file=sys.stderr)
        return 1

    boundary_errors = check_memory_boundaries(used_segments, ram_limit=args.limit)
    if boundary_errors:
        for err in boundary_errors:
            print(f"ERROR: {err}", file=sys.stderr)
        return 1

    # 4. Compute full map with gaps
    all_segments = compute_memory_map(
        used_segments,
        ram_base=args.base,
        ram_limit=args.limit,
    )

    out_text_path = Path(args.out_text)
    out_json_path = Path(args.out_json)
    out_text_path.parent.mkdir(parents=True, exist_ok=True)
    out_json_path.parent.mkdir(parents=True, exist_ok=True)

    # 5. Write docs/memory_map.json
    json_data = [asdict(seg) for seg in all_segments]
    with out_json_path.open("w", encoding="utf-8") as f:
        json.dump(json_data, f, indent=2)

    # 6. Write docs/memory_map.txt
    text_content = generate_ascii_table(
        all_segments,
        zp_vars,
        ram_base=args.base,
        ram_limit=args.limit,
    )
    with out_text_path.open("w", encoding="utf-8") as f:
        f.write(text_content)

    print(f"Memory map successfully generated:")
    print(f"  - Text summary: {out_text_path}")
    print(f"  - JSON data:    {out_json_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
