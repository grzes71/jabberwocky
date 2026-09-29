#!/usr/bin/env python3
"""Extract and relocate CMC music data from SAP container.

Reads a SAP file (TYPE C), extracts the music data segment, relocates its
internal 16-bit instrument/pattern pointer table to the target address,
and outputs raw binary suitable for MADS 'ins' directive.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import struct
import sys
from typing import Dict, Tuple


def parse_sap_header(data: bytes) -> Tuple[Dict[str, str], int]:
    """Parse ASCII SAP header and return tags dictionary and binary offset."""
    if not data.startswith(b"SAP\r\n") and not data.startswith(b"SAP\n"):
        raise ValueError("Invalid SAP header: missing 'SAP' identifier at start.")

    pos = 0
    while pos < len(data) - 1:
        if data[pos:pos+2] == b"\xff\xff":
            break
        pos += 1

    if pos >= len(data) - 1:
        raise ValueError("Could not find binary payload (0xFFFF) in SAP file.")

    header_text = data[:pos].decode("ascii", errors="replace")
    tags: Dict[str, str] = {}
    for line in header_text.splitlines():
        line = line.strip()
        if not line or line == "SAP":
            continue
        parts = line.split(maxsplit=1)
        tag = parts[0].upper()
        val = parts[1] if len(parts) > 1 else ""
        tags[tag] = val

    return tags, pos


def extract_and_relocate(
    sap_path: Path,
    out_path: Path,
    target_addr: int = 0x9000,
) -> int:
    """Extract CMC music segment from SAP, relocate table, and save raw binary.

    Returns the number of bytes written.
    """
    data = sap_path.read_bytes()
    tags, payload_offset = parse_sap_header(data)

    sap_type = tags.get("TYPE", "").strip().upper()
    if sap_type != "C":
        raise ValueError(f"Expected SAP TYPE C, but found TYPE '{sap_type}'.")

    payload = data[payload_offset:]
    idx = 0
    segments = []
    while idx < len(payload):
        if idx + 2 <= len(payload) and payload[idx:idx+2] == b"\xff\xff":
            idx += 2
            continue
        if idx + 4 > len(payload):
            break
        start, end = struct.unpack("<HH", payload[idx:idx+4])
        idx += 4
        length = end - start + 1
        seg_bytes = payload[idx:idx+length]
        idx += length
        segments.append((start, end, length, seg_bytes))

    if not segments:
        raise ValueError("No segments found in SAP binary payload.")

    # Find the music segment (matching tags['MUSIC'] or start address >= 0x1000)
    music_tag_hex = tags.get("MUSIC", "8400")
    orig_base = int(music_tag_hex, 16)

    music_seg = None
    for start, end, length, seg_bytes in segments:
        if start == orig_base:
            music_seg = (start, end, length, bytearray(seg_bytes))
            break

    if music_seg is None:
        # Fallback: segment 0 if not player ($0500)
        for start, end, length, seg_bytes in segments:
            if start != 0x0500 and length > 500:
                music_seg = (start, end, length, bytearray(seg_bytes))
                orig_base = start
                break

    if music_seg is None:
        raise ValueError(f"Could not locate music segment with base ${orig_base:04X}.")

    orig_start, orig_end, orig_len, music_data = music_seg
    delta = target_addr - orig_base

    # Relocate CMC instrument/pattern pointer table:
    # 64 entries: low byte at offset $14..$53, high byte at offset $54..$93
    TABLE_OFFSET = 0x14
    NUM_ENTRIES = 64
    if len(music_data) < TABLE_OFFSET + 2 * NUM_ENTRIES:
        raise ValueError("Music segment is too short to contain CMC pointer table.")

    relocated_count = 0
    for i in range(NUM_ENTRIES):
        lo = music_data[TABLE_OFFSET + i]
        hi = music_data[TABLE_OFFSET + NUM_ENTRIES + i]
        if hi != 0xFF:
            orig_ptr = lo | (hi << 8)
            # Verify original pointer points within original segment
            if not (orig_base <= orig_ptr <= orig_end):
                raise ValueError(
                    f"Invalid CMC pointer at index {i}: ${orig_ptr:04X} outside ${orig_base:04X}-${orig_end:04X}"
                )
            addr = orig_ptr + delta
            if not (target_addr <= addr <= target_addr + orig_len):
                raise ValueError(
                    f"Relocated pointer out of bounds: entry {i} addr ${addr:04X} outside target range"
                )
            music_data[TABLE_OFFSET + i] = addr & 0xFF
            music_data[TABLE_OFFSET + NUM_ENTRIES + i] = (addr >> 8) & 0xFF
            relocated_count += 1

    if relocated_count == 0:
        raise ValueError("No active pointers found in CMC table; module appears empty or corrupted.")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(music_data)
    print(
        f"Extracted CMC music ({orig_len} bytes, orig ${orig_base:04X}-${orig_end:04X}) -> "
        f"relocated to ${target_addr:04X}-${target_addr + orig_len - 1:04X} "
        f"({relocated_count} pointers updated) -> '{out_path}'"
    )
    return len(music_data)


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract and relocate CMC music from SAP.")
    parser.add_argument("-i", "--input", type=Path, required=True, help="Input .sap file")
    parser.add_argument("-o", "--output", type=Path, required=True, help="Output .cmc binary")
    parser.add_argument(
        "-t", "--target-address",
        type=lambda x: int(x, 0),
        default=0x9000,
        help="Target base address (hex or dec, default 0x9000)",
    )
    args = parser.parse_args()

    try:
        extract_and_relocate(args.input, args.output, args.target_address)
    except Exception as exc:
        print(f"Error extracting SAP: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
