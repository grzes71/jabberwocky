from __future__ import annotations

import os
from pathlib import Path
from typing import List, Tuple
import numpy as np
from PIL import Image

from sprite_studio.models import Frame

SUPPORTED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".bmp"}
MAX_DIMENSION = 8192


class ImageImportError(Exception):
    """Raised when image loading, slicing, or conversion fails."""
    pass


def compute_slice_ranges(total: int, count: int) -> List[Tuple[int, int]]:
    """
    Compute start and end coordinates for dividing `total` into `count` parts.
    Remainder pixels are distributed evenly across the first slices so that
    no dimension difference exceeds 1 pixel, no pixel is skipped or duplicated.
    """
    if count < 1:
        raise ImageImportError("Frame count must be at least 1.")
    if count > total:
        raise ImageImportError(f"Frame count ({count}) cannot exceed image dimension ({total} px).")

    base = total // count
    rem = total % count
    ranges = []
    current = 0
    for i in range(count):
        size = base + (1 if i < rem else 0)
        ranges.append((current, current + size))
        current += size
    return ranges


def load_image(path: Path | str) -> Image.Image:
    """
    Load and validate an image file (PNG, JPG/JPEG, BMP).
    """
    p = Path(path)
    if not p.exists():
        raise ImageImportError(f"File not found: {p}")
    if not p.is_file():
        raise ImageImportError(f"Path is not a regular file: {p}")
    if p.suffix.lower() not in SUPPORTED_EXTENSIONS:
        raise ImageImportError(
            f"Unsupported file format '{p.suffix}'. Supported formats: {', '.join(sorted(SUPPORTED_EXTENSIONS))}"
        )

    try:
        img = Image.open(p)
        img.load()  # Force reading entire file to detect corruption early
    except Exception as e:
        raise ImageImportError(f"Failed to read/decode image file: {e}")

    w, h = img.size
    if w <= 0 or h <= 0:
        raise ImageImportError(f"Invalid image dimensions: {w}x{h}")
    if w > MAX_DIMENSION or h > MAX_DIMENSION:
        raise ImageImportError(
            f"Image dimension ({w}x{h}) exceeds maximum supported size ({MAX_DIMENSION}x{MAX_DIMENSION})."
        )

    return img


def slice_image(image: Image.Image, frame_count: int, direction: str) -> List[Image.Image]:
    """
    Slice an image into `frame_count` frames either horizontally or vertically.
    """
    if frame_count < 1:
        raise ImageImportError("Frame count must be at least 1.")

    w, h = image.size
    dir_norm = direction.strip().lower()

    if dir_norm in ("horizontal", "h"):
        ranges = compute_slice_ranges(w, frame_count)
        return [image.crop((x0, 0, x1, h)) for (x0, x1) in ranges]
    elif dir_norm in ("vertical", "v"):
        ranges = compute_slice_ranges(h, frame_count)
        return [image.crop((0, y0, w, y1)) for (y0, y1) in ranges]
    else:
        raise ImageImportError(f"Invalid slice direction '{direction}'. Must be 'horizontal' or 'vertical'.")


def prepare_rgb_image(image: Image.Image) -> Image.Image:
    """
    Convert image to RGB. If alpha transparency exists, composite over a black background.
    """
    if image.mode in ("RGBA", "LA") or (image.mode == "P" and "transparency" in image.info):
        rgba = image.convert("RGBA")
        bg = Image.new("RGBA", rgba.size, (0, 0, 0, 255))
        return Image.alpha_composite(bg, rgba).convert("RGB")
    elif image.mode == "L":
        return image.convert("RGB")
    else:
        return image.convert("RGB")


def convert_frame_to_binary(
    frame_image: Image.Image,
    target_width: int = 8,
    target_height: int = 24,
    threshold: float = 50.0,
    inverse: bool = False,
    fit_mode: str = "fit",
) -> List[str]:
    """
    Fit `frame_image` into a `target_width` x `target_height` grid, and compute cell average luminance:
        Y = 0.2126 * R + 0.7152 * G + 0.0722 * B  (0..1)
        brightness = Y * 100 (0..100)
    fit_mode:
        - "fit": preserve aspect ratio, center on canvas. Unused padding is seamless and always yields '0'.
        - "stretch": stretch to fill the entire target_width x target_height without any margins.
        - "crop": scale to cover target area and center-crop excess borders without empty margins.
    Cells with brightness >= threshold are set to '1' (or '0' if inverse=True).
    Returns list of binary strings of length `target_width`, with total count `target_height`.
    """
    if target_width != 8:
        raise ImageImportError(f"Target width must be 8, got {target_width}.")
    if not (1 <= target_height <= 255):
        raise ImageImportError(f"Target height must be between 1 and 255, got {target_height}.")
    if not (0.0 <= threshold <= 100.0):
        raise ImageImportError(f"Threshold must be between 0 and 100, got {threshold}.")

    src_rgb = prepare_rgb_image(frame_image)
    src_w, src_h = src_rgb.size
    if src_w <= 0 or src_h <= 0:
        raise ImageImportError(f"Frame has invalid dimensions: {src_w}x{src_h}")

    # Determine sub-sampling resolution per cell (S x S pixels per cell)
    s = max(32, min(512, max(src_w // target_width * 2, src_h // target_height * 2)))
    canvas_w = target_width * s
    canvas_h = target_height * s

    fit_norm = fit_mode.strip().lower()

    if fit_norm == "stretch":
        scaled_w = canvas_w
        scaled_h = canvas_h
        scaled_img = src_rgb.resize((scaled_w, scaled_h), Image.Resampling.LANCZOS)
        canvas = scaled_img
        mask_in_bounds = np.ones((target_height, target_width), dtype=bool)

    elif fit_norm == "crop":
        scale = max(canvas_w / src_w, canvas_h / src_h)
        scaled_w = max(1, int(round(src_w * scale)))
        scaled_h = max(1, int(round(src_h * scale)))
        scaled_img = src_rgb.resize((scaled_w, scaled_h), Image.Resampling.LANCZOS)
        cx = (scaled_w - canvas_w) // 2
        cy = (scaled_h - canvas_h) // 2
        canvas = scaled_img.crop((cx, cy, cx + canvas_w, cy + canvas_h))
        mask_in_bounds = np.ones((target_height, target_width), dtype=bool)

    else:  # "fit" (letterbox / keep aspect ratio)
        scale = min(canvas_w / src_w, canvas_h / src_h)
        scaled_w = max(1, int(round(src_w * scale)))
        scaled_h = max(1, int(round(src_h * scale)))

        if scaled_w >= src_w and scaled_h >= src_h and (scaled_w % src_w == 0) and (scaled_h % src_h == 0):
            resample_filter = Image.Resampling.NEAREST
        else:
            resample_filter = Image.Resampling.LANCZOS

        scaled_img = src_rgb.resize((scaled_w, scaled_h), resample_filter)

        # Detect corner background color to seamlessly blend padding
        corners = [
            src_rgb.getpixel((0, 0)),
            src_rgb.getpixel((src_w - 1, 0)),
            src_rgb.getpixel((0, src_h - 1)),
            src_rgb.getpixel((src_w - 1, src_h - 1)),
        ]
        avg_corner_lum = sum(0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2] for c in corners) / 4.0
        pad_color = (255, 255, 255) if avg_corner_lum >= 128 else (0, 0, 0)

        paste_x = (canvas_w - scaled_w) // 2
        paste_y = (canvas_h - scaled_h) // 2

        canvas = Image.new("RGB", (canvas_w, canvas_h), pad_color)
        canvas.paste(scaled_img, (paste_x, paste_y))

        # Mark which grid cells overlap with the actual image
        # Padding cells completely outside the image must always produce '0'
        mask_in_bounds = np.zeros((target_height, target_width), dtype=bool)
        for r in range(target_height):
            cell_y0 = r * s
            cell_y1 = (r + 1) * s
            if cell_y1 > paste_y and cell_y0 < paste_y + scaled_h:
                for c in range(target_width):
                    cell_x0 = c * s
                    cell_x1 = (c + 1) * s
                    if cell_x1 > paste_x and cell_x0 < paste_x + scaled_w:
                        mask_in_bounds[r, c] = True

    # Calculate luminance Y = 0.2126*R + 0.7152*G + 0.0722*B in [0, 1]
    arr = np.asarray(canvas, dtype=np.float32) / 255.0
    luminance = 0.2126 * arr[:, :, 0] + 0.7152 * arr[:, :, 1] + 0.0722 * arr[:, :, 2]
    brightness = luminance * 100.0

    # Reshape to (target_height, s, target_width, s) and compute cell averages
    reshaped = brightness.reshape(target_height, s, target_width, s)
    cell_avg = reshaped.mean(axis=(1, 3))  # shape: (target_height, target_width)

    # Binarize
    binary_grid: List[str] = []
    for r in range(target_height):
        row_chars = []
        for c in range(target_width):
            if not mask_in_bounds[r, c]:
                # Letterbox padding outside content is always empty '0'
                row_chars.append("0")
            else:
                if not inverse:
                    row_chars.append("1" if cell_avg[r, c] >= threshold else "0")
                else:
                    row_chars.append("0" if cell_avg[r, c] >= threshold else "1")
        binary_grid.append("".join(row_chars))

    return binary_grid


def import_raster_frames(
    path: Path | str,
    frame_count: int = 1,
    direction: str = "horizontal",
    target_height: int = 24,
    threshold: float = 50.0,
    inverse: bool = False,
    fit_mode: str = "fit",
) -> List[Frame]:
    """
    Full pipeline: load image, slice into N frames, fit and binarize each frame.
    Returns list of Frame objects with .pixels matching target_height.
    """
    img = load_image(path)
    slices = slice_image(img, frame_count, direction)

    frames: List[Frame] = []
    for s_img in slices:
        pixels = convert_frame_to_binary(
            frame_image=s_img,
            target_width=8,
            target_height=target_height,
            threshold=threshold,
            inverse=inverse,
            fit_mode=fit_mode,
        )
        frames.append(Frame(pixels=pixels))

    return frames
