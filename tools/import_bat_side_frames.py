"""Normalize Bat side-view frames with a fixed scale and body anchor.

The approved side-view base (``assets/generated/base/bat_side_base.png``)
uses a horizontal body: the head is on the right, the feet/body bottom is the
lowest point, and the wings sweep up/back.  The body center sits forward of the
feet, so this tool:

* calibrates one fixed scale from the approved base's full alpha width;
* aligns the full silhouette bottom to the pivot Y (the feet/body bottom);
* aligns the feet center plus a fixed forward offset to the pivot X, which puts
  the hurtbox center on the body/head rather than on the feet;
* flags canvas overflow instead of shrinking or cropping the wings.
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


def _feet_center_x(cropped: Image.Image) -> float:
    """Alpha-weighted center of the bottom band (the feet/body bottom)."""
    alpha = cropped.getchannel("A")
    width, height = alpha.size
    band_height = max(4, int(height * 0.08))
    band = alpha.crop((0, height - band_height, width, height))
    pixels = band.load()
    total = 0
    weighted = 0
    for y in range(band_height):
        for x in range(width):
            value = pixels[x, y]
            if value > 32:
                total += value
                weighted += x * value
    if total == 0:
        return width * 0.5
    return weighted / total


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--src", required=True, help="folder with generated PNG frames")
    parser.add_argument("--out", required=True, help="staged output folder")
    parser.add_argument(
        "--base",
        default="assets/generated/base/bat_side_base.png",
        help="approved side-view Bat base",
    )
    parser.add_argument("--target-width", type=float, default=256.0)
    parser.add_argument("--canvas", type=int, default=384)
    parser.add_argument("--pivot-x", type=int, default=230)
    parser.add_argument("--pivot-y", type=int, default=285)
    parser.add_argument(
        "--body-forward-offset",
        type=float,
        default=33.0,
        help="source px from the feet center to the body/hurtbox center",
    )
    parser.add_argument("--action", default="", help="prefix when --names is omitted")
    parser.add_argument("--names", default="", help="comma-separated output basenames")
    parser.add_argument("--order", default="", help="comma-separated source filenames")
    parser.add_argument("--expect", type=int, default=0)
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
    base_width = base_bbox[2] - base_bbox[0]
    scale = args.target_width / base_width
    print(
        f"base bbox={base_bbox} width={base_width} target={args.target_width}"
        f" scale={scale:.5f}"
    )

    if not args.dry_run:
        out.mkdir(parents=True, exist_ok=True)
    flagged_dir = out / "_flagged"

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
        new_size = (
            max(1, round(cropped.width * scale)),
            max(1, round(cropped.height * scale)),
        )
        resized = cropped.resize(new_size, Image.LANCZOS)
        feet_x = _feet_center_x(resized)
        left = args.pivot_x - round(feet_x + args.body_forward_offset)
        top = args.pivot_y - resized.height

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
                f"{index:02d} {path.name} bbox={bbox} feet_x={feet_x:.0f}"
                f" size={new_size[0]}x{new_size[1]} FIT left={left} top={top}"
                f" -> _flagged/{name}.png"
            )
            continue

        canvas = Image.new("RGBA", (args.canvas, args.canvas), (0, 0, 0, 0))
        canvas.alpha_composite(resized, (left, top))
        target = out / f"{name}.png"
        if not args.dry_run:
            canvas.save(target)
        print(
            f"{index:02d} {path.name} bbox={bbox} feet_x={feet_x:.0f}"
            f" size={new_size[0]}x{new_size[1]} left={left} top={top}"
            f" -> {target.name}"
        )

    print(f"DONE files={len(files)} fit={fit_count} out={out} scale={scale:.5f}")
    return 2 if fit_count else 0


if __name__ == "__main__":
    raise SystemExit(main())
