"""Normalize generated frames onto a 256x256 canvas with a fixed feet pivot.

The scale is calibrated once from the approved side-view base so that every
frame uses the same character scale. Frames whose pose makes them too wide or
too tall for the canvas are fitted and flagged instead of being silently
stretched.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter


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

    # Strategy 1: flood-fill the uniform background color from the corners.
    work = rgb.copy()
    work_pixels = work.load()
    sentinel = (255, 0, 255)
    corners = ((0, 0), (width - 1, 0), (0, height - 1), (width - 1, height - 1))
    for seed in corners:
        if work.getpixel(seed) != sentinel:
            ImageDraw.floodfill(work, seed, sentinel, thresh=45)

    # Strategy 2: a connected near-white mask catches checkerboard/white backdrops.
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
    """Alpha-weighted center of the bottom band (the boots/support foot)."""
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
    parser.add_argument("--action", required=True)
    parser.add_argument("--src", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--base", default="assets/generated/base/lina_side_base.png")
    parser.add_argument("--body-height", type=float, default=210.0)
    parser.add_argument("--canvas", type=int, default=256)
    parser.add_argument("--pivot-x", type=int, default=128)
    parser.add_argument("--pivot-y", type=int, default=244)
    parser.add_argument("--order", default="")
    parser.add_argument("--expect", type=int, default=0)
    parser.add_argument("--remove-bg", action="store_true")
    parser.add_argument("--pose-ref", default="")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    src = _resolve(args.src)
    out = _resolve(args.out)
    base_path = _resolve(args.base)
    pose_ref_dir = _resolve(args.pose_ref) if args.pose_ref else None
    if not src.exists():
        print(f"ERROR source folder not found: {src}")
        return 1
    if not base_path.exists():
        print(f"ERROR base image not found: {base_path}")
        return 1

    base = Image.open(base_path).convert("RGBA")
    base_bbox = base.getchannel("A").getbbox()
    if base_bbox is None:
        print("ERROR base image has no opaque pixels")
        return 1
    base_height = base_bbox[3] - base_bbox[1]
    scale = args.body_height / base_height
    print(f"base bbox={base_bbox} height={base_height} scale={scale:.5f}")

    if args.order:
        files = [src / name.strip() for name in args.order.split(",") if name.strip()]
    else:
        files = sorted(src.glob("*.png"))
    if not files:
        print(f"ERROR no PNG frames in {src}")
        return 1
    if args.expect and len(files) != args.expect:
        print(f"WARN expected {args.expect} frames, found {len(files)}")

    if not args.dry_run:
        out.mkdir(parents=True, exist_ok=True)

    for index, path in enumerate(files):
        if not path.exists():
            print(f"MISSING {path}")
            continue
        image = Image.open(path).convert("RGBA")
        if args.remove_bg:
            image = _remove_white_background(image)
        alpha = image.getchannel("A").point(lambda value: 0 if value < 10 else value)
        image.putalpha(alpha)

        target = out / f"{args.action}_{index:02d}.png"

        if pose_ref_dir is not None:
            ref_path = pose_ref_dir / path.name
            if ref_path.exists():
                ref = Image.open(ref_path).convert("RGBA")
                ref_bbox = ref.getchannel("A").getbbox()
                if ref_bbox is not None:
                    # Remove remaining near-white background outside the pose silhouette.
                    protection = (
                        ref.getchannel("A")
                        .point(lambda value: 255 if value > 32 else 0)
                        .filter(ImageFilter.MaxFilter(9))
                    )
                    rgb = image.convert("RGB")
                    rgb_pixels = rgb.load()
                    protect_pixels = protection.load()
                    alpha = image.getchannel("A")
                    alpha_pixels = alpha.load()
                    for y in range(image.height):
                        for x in range(image.width):
                            if protect_pixels[x, y] == 0:
                                r, g, b = rgb_pixels[x, y]
                                if min(r, g, b) >= 185 and max(r, g, b) - min(r, g, b) <= 40:
                                    alpha_pixels[x, y] = 0
                    image.putalpha(alpha)

                    ref_feet_x = _feet_center_x(ref.crop(ref_bbox))
                    new_size = (
                        max(1, round(image.width * scale)),
                        max(1, round(image.height * scale)),
                    )
                    resized = image.resize(new_size, Image.LANCZOS)
                    canvas = Image.new("RGBA", (args.canvas, args.canvas), (0, 0, 0, 0))
                    left = args.pivot_x - round(ref_feet_x * scale)
                    top = args.pivot_y - round(ref_bbox[3] * scale)
                    canvas.alpha_composite(resized, (left, top))
                    if not args.dry_run:
                        canvas.save(target)
                    print(
                        f"{index:02d} {path.name} pose_bbox={ref_bbox}"
                        f" feet_x={ref_feet_x:.0f} full={new_size[0]}x{new_size[1]}"
                        f" -> {target.name} (pose-ref)"
                    )
                    continue
            print(f"WARN pose ref missing for {path.name}; using source bbox")

        bbox = image.getchannel("A").getbbox()
        if bbox is None:
            print(f"EMPTY {path.name}")
            continue

        cropped = image.crop(bbox)
        feet_x = _feet_center_x(cropped)
        used_scale = scale
        warning = ""
        if cropped.width * scale > args.canvas * 0.98 or cropped.height * scale > args.pivot_y * 0.98:
            used_scale = min(
                scale,
                (args.canvas * 0.98) / cropped.width,
                (args.pivot_y * 0.98) / cropped.height,
            )
            warning = f" FIT {used_scale:.5f}"

        new_size = (
            max(1, round(cropped.width * used_scale)),
            max(1, round(cropped.height * used_scale)),
        )
        resized = cropped.resize(new_size, Image.LANCZOS)
        canvas = Image.new("RGBA", (args.canvas, args.canvas), (0, 0, 0, 0))
        left = args.pivot_x - round(feet_x * used_scale)
        top = args.pivot_y - new_size[1]
        canvas.alpha_composite(resized, (left, top))

        target = out / f"{args.action}_{index:02d}.png"
        if not args.dry_run:
            canvas.save(target)
        print(
            f"{index:02d} {path.name} bbox={bbox} feet_x={feet_x:.0f}"
            f" size={new_size[0]}x{new_size[1]} -> {target.name}{warning}"
        )

    print(f"DONE action={args.action} frames={len(files)} out={out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
