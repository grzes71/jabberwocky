#!/usr/bin/env python3
"""Convert images to Atari ANTIC Mode F binary data using atari-image-converter."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from converter.pipeline import convert_image
from converter.types import (
    ConversionConfig,
    DitherMethod,
    PaletteMethod,
    QuantizerMethod,
    ResizeMethod,
)
from converter.exporters.xex_export import _pack_1bpp


def main() -> int:
    parser = argparse.ArgumentParser(description="Convert image to ANTIC Mode F screen binary")
    parser.add_argument("-i", "--input", required=True, help="Input image file")
    parser.add_argument("-o", "--output", required=True, help="Output binary file (.bin)")
    parser.add_argument("--width", type=int, default=320, help="Output width (default: 320)")
    parser.add_argument("--height", type=int, default=175, help="Output height (default: 175)")
    parser.add_argument("--mode", default="F", choices=["F"], help="ANTIC mode (default: F)")
    parser.add_argument(
        "--dither",
        default="none",
        choices=[d.value for d in DitherMethod],
        help="Dithering algorithm (default: none)",
    )
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"Error: input file not found: {input_path}", file=sys.stderr)
        return 1

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    config = ConversionConfig(
        width=args.width,
        height=args.height,
        colors=2,
        palette=PaletteMethod.POPULARITY,
        dither=DitherMethod(args.dither),
        quantizer=QuantizerMethod.NEAREST,
        resize=ResizeMethod.LANCZOS,
    )

    result = convert_image(input_path, config)
    vram_data = _pack_1bpp(result.indexed, width=args.width, height=args.height, pad_4kb=True)
    output_path.write_bytes(vram_data)

    print(f"Converted {input_path} -> {output_path} ({len(vram_data)} bytes, ANTIC Mode {args.mode})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
