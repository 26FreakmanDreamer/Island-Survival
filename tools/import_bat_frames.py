"""Normalize Bat frames onto a fixed canvas using the body core as the anchor.

The standard ``import_frames.py`` aligns on the full silhouette bottom and the
alpha-weighted bottom band.  A bat's lowest pixels are often wing claws, not the
body, so that would make the body bob between wing poses.  This tool:

* calibrates one fixed scale from the approved base's body-core height;
* crops each generated frame to its alpha bbox and resizes by that fixed scale;
* aligns the body-core bottom to the pivot and the body-core center to pivot X;
* flags (never silently fixes) body-core height drift or canvas overflow.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageDraw


def _resolve(path_text: str) -> Path:
    path = Path(path_text)
    return path if path.is_absolute() else Path.cwd() / path


def _remove_white_background(
    image: Image.Image,
    threshold_min: int = 195,
    threshold_range: int = 35,
) -> Image.Image:
    """Remove a connected near-white/checkerboard background from an RGB render."""
    rgba = image.convert("RGBA")
    rgb = rgba.convert("RGB")
    width, height = rgb.size
    pixels = rgb.load()

    work = rgb.copy()
    work_pixels = work.load()
    sentinel = (255, 0, 255)
    corners = ((0, 0), (width - 1, 0), (0, height - 1), (width - 1, height - 1))
    for seed in corners:
        if work.getpixel(seed) != sentinel:
            ImageDraw.floodfill(work, seed, sentinel, thresh=45)

    mask = Image.new("L", (width, height), 0)
    mask_pixels = mask.load()
    for y in range(height):
        for x in range(width):
            r, g, b = pixels[x, y]
            if min(r, g, b) >= threshold_min and max(r, g, b) - min(r, g, b) <= threshold_range:
                mask_pixels[x, y] = 255
    for seed in corners:
        if mask.getpixel(seed) == 255:
            ImageDraw.floodfill(mask, seed, 128, thresh=0)

    alpha = rgba.getchannel("A")
    alpha_pixels = alpha.load()
    for y in range(height):
        for x in range(width):
            if mask_pixels[x, y] == 128 or work_pixels[x, y] == sentinel:
                alpha_pixels[x, y] = 0
    rgba.putalpha(alpha)
    return rgba


def _band_bbox(
    alpha: Image.Image,
    band_fraction: float,
    center_x: float | None = None,
) -> tuple[int, int, int, int] | None:
    """Alpha bbox of a vertical band around the body center.

    ``band_fraction`` is the band width as a fraction of the full alpha bbox
    width.  For the bat this band covers the head/body/feet while excluding the
    wing tips, so its height is a stable body-core metric across wing poses.
    """
    bbox = alpha.getbbox()
    if bbox is None:
        return None
    full_width = bbox[2] - bbox[0]
    if center_x is None:
        center_x = (bbox[0] + bbox[2]) / 2.0
    half = max(2, int(round(full_width * band_fraction / 2.0)))
    x0 = max(0, int(round(center_x - half)))
    x1 = min(alpha.width, int(round(center_x + half)))
    if x1 <= x0:
        return None
    band = alpha.crop((x0, 0, x1, alpha.height))
    band_bbox = band.getbbox()
    if band_bbox is None:
        return None
    return (x0 + band_bbox[0], band_bbox[1], x0 + band_bbox[2], band_bbox[3])


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--src", required=True, help="folder with generated PNG frames")
    parser.add_argument("--out", required=True, help="staged output folder")
    parser.add_argument(
        "--base",
        default="assets/generated/base/bat_front_base.png",
        help="approved Bat base used for the fixed scale",
    )
    parser.add_argument("--target-core-height", type=float, default=58.0)
    parser.add_argument("--canvas", type=int, default=320)
    parser.add_argument("--pivot-x", type=int, default=160)
    parser.add_argument("--pivot-y", type=int, default=198)
    parser.add_argument("--action", default="", help="prefix when --names is omitted")
    parser.add_argument("--names", default="", help="comma-separated output basenames")
    parser.add_argument("--order", default="", help="comma-separated source filenames")
    parser.add_argument("--expect", type=int, default=0)
    parser.add_argument("--core-band", type=float, default=0.30)
    parser.add_argument("--tolerance", type=float, default=0.06)
    parser.add_argument("--remove-bg", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    src = _resolve(args.src)
    out = _resolve(args.out)
    base_path = _resolve(args.base)
    if not src.exists():
        print(f"ERROR source folder not found: {src}")
        return 1
    if not base_path.exists():
        print(f"ERROR base image not found: {base_path}")
        return 1

    if args.order:
        files = [src / name.strip() for name in args.order.split(",") if name.strip()]
    else:
        files = sorted(src.glob("*.png"))
    if not files:
        print(f"ERROR no PNG frames in {src}")
        return 1
    if args.expect and len(files) != args.expect:
        print(f"WARN expected {args.expect} frames, found {len(files)}")

    if args.names:
        names = [name.strip() for name in args.names.split(",") if name.strip()]
        if len(names) != len(files):
            print(f"ERROR --names has {len(names)} entries for {len(files)} files")
            return 1
    else:
        if not args.action:
            print("ERROR provide --action or --names")
            return 1
        names = [f"{args.action}_{index:02d}" for index in range(len(files))]

    base = Image.open(base_path).convert("RGBA")
    base_alpha = base.getchannel("A").point(lambda value: 0 if value < 10 else value)
    base_bbox = base_alpha.getbbox()
    if base_bbox is None:
        print("ERROR base image has no opaque pixels")
        return 1
    base_core = _band_bbox(base_alpha, args.core_band)
    if base_core is None:
        print("ERROR base body core could not be measured")
        return 1
    base_core_height = base_core[3] - base_core[1]
    scale = args.target_core_height / base_core_height
    print(
        f"base bbox={base_bbox} core={base_core} core_h={base_core_height}"
        f" scale={scale:.5f}"
    )

    if not args.dry_run:
        out.mkdir(parents=True, exist_ok=True)
    flagged_dir = out / "_flagged"

    reject_count = 0
    fit_count = 0
    for index, path in enumerate(files):
        name = names[index]
        if not path.exists():
            print(f"MISSING {path}")
            continue
        image = Image.open(path).convert("RGBA")
        if args.remove_bg:
            image = _remove_white_background(image)
        alpha = image.getchannel("A").point(lambda value: 0 if value < 10 else value)
        image.putalpha(alpha)

        bbox = alpha.getbbox()
        if bbox is None:
            print(f"EMPTY {path.name}")
            continue
        cropped = image.crop(bbox)
        cropped_alpha = cropped.getchannel("A")
        core_raw = _band_bbox(
            cropped_alpha,
            args.core_band,
            center_x=cropped.width / 2.0,
        )
        if core_raw is None:
            print(f"EMPTY core {path.name}")
            continue
        core = tuple(int(round(value * scale)) for value in core_raw)
        new_size = (
            max(1, round(cropped.width * scale)),
            max(1, round(cropped.height * scale)),
        )
        resized = cropped.resize(new_size, Image.LANCZOS)

        core_height = core[3] - core[1]
        deviation = (core_height - args.target_core_height) / args.target_core_height
        core_center_x = (core[0] + core[2]) / 2.0
        left = args.pivot_x - round(core_center_x)
        top = args.pivot_y - round(core[3])

        overflow = (
            left < 0
            or top < 0
            or left + resized.width > args.canvas
            or top + resized.height > args.canvas
        )
        if overflow:
            fit_count += 1
            if not args.dry_run:
                flagged_dir.mkdir(parents=True, exist_ok=True)
                flagged_image = Image.new("RGBA", resized.size, (0, 0, 0, 0))
                flagged_image.alpha_composite(resized, (0, 0))
                flagged_image.save(flagged_dir / f"{name}.png")
            print(
                f"{index:02d} {path.name} bbox={bbox} core={core} h={core_height}"
                f" dev={deviation:+.1%} FIT left={left} top={top}"
                f" size={new_size[0]}x{new_size[1]} -> _flagged/{name}.png"
            )
            continue

        canvas = Image.new("RGBA", (args.canvas, args.canvas), (0, 0, 0, 0))
        canvas.alpha_composite(resized, (left, top))
        is_rejected = abs(deviation) > args.tolerance
        if is_rejected:
            reject_count += 1
        target = out / f"{name}.png"
        if not args.dry_run:
            canvas.save(target)
        print(
            f"{index:02d} {path.name} bbox={bbox} core={core} h={core_height}"
            f" dev={deviation:+.1%} left={left} top={top}"
            f" -> {target.name}{' REJECT' if is_rejected else ''}"
        )

    print(
        f"DONE files={len(files)} rejected={reject_count} fit={fit_count}"
        f" out={out} scale={scale:.5f}"
    )
    return 2 if (reject_count or fit_count) else 0


if __name__ == "__main__":
    raise SystemExit(main())
