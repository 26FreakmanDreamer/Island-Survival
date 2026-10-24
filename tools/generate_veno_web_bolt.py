"""Crop the approved web_05 web into Veno's projectile/impact sprite.

No runtime copy happens here: the crop and previews go to
``assets/generated/contact_sheets/veno_web_fx_v1`` and are installed after review.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
SOURCE = (
    ROOT
    / "assets"
    / "generated"
    / "contact_sheets"
    / "veno_web_spit_v2_frames"
    / "veno_web_spit_web_05.png"
)
OUT = ROOT / "assets" / "generated" / "contact_sheets" / "veno_web_fx_v1"
CROP = (492, 155, 622, 278)
SOURCE_NAME = "veno_web_spit_web_05.png"


def _font(size: int):
    try:
        return ImageFont.truetype("arial.ttf", size)
    except Exception:  # noqa: BLE001
        return ImageFont.load_default()


def _checkerboard(size: tuple[int, int], tile: int = 12) -> Image.Image:
    board = Image.new("RGB", size, (62, 64, 74))
    draw = ImageDraw.Draw(board)
    for y in range(0, size[1], tile):
        for x in range(0, size[0], tile):
            if (x // tile + y // tile) % 2:
                draw.rectangle(
                    [x, y, x + tile - 1, y + tile - 1], fill=(82, 84, 96)
                )
    return board


def _trail(size: tuple[int, int]) -> Image.Image:
    """Preview-only silk trail; the runtime draws its own trail."""
    layer = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    cx, cy = size[0] // 2, size[1] // 2
    for offset in (0, 1):
        points = []
        for step in range(8):
            t = step / 7.0
            distance = 12.0 + 54.0 * t
            wobble = math.sin(t * 3.0 + offset * 1.7) * 2.5 * t
            points.append((cx - distance, cy + wobble + offset * 2.0))
        draw.line(
            points,
            fill=(90, 140, 80, 150) if offset == 0 else (225, 255, 205, 190),
            width=2 if offset == 0 else 1,
        )
    return layer


def build_preview(crop: Image.Image, out_dir: Path) -> None:
    cell = 180
    sizes = (34, 38, 96, 108)
    pad = 16
    width = pad + len(sizes) * (cell + pad)
    height = 300
    sheet = _checkerboard((width, height))
    draw = ImageDraw.Draw(sheet)
    title_font = _font(20)
    label_font = _font(14)
    draw.text(
        (pad, 10),
        "Veno web_05 crop - projectile / impact previews",
        fill=(238, 238, 246),
        font=title_font,
    )
    for index, size in enumerate(sizes):
        x = pad + index * (cell + pad)
        y = 48
        frame = crop.resize(
            (round(crop.width * size / crop.height), size),
            Image.Resampling.LANCZOS,
        )
        preview = Image.new("RGBA", (cell, cell), (0, 0, 0, 0))
        if size <= 40:
            preview.alpha_composite(_trail((cell, cell)))
        preview.alpha_composite(
            frame,
            ((cell - frame.width) // 2, (cell - frame.height) // 2),
        )
        board = sheet.crop((x, y, x + cell, y + cell)).convert("RGBA")
        board.alpha_composite(preview)
        sheet.paste(board.convert("RGB"), (x, y))
        draw.rectangle([x, y, x + cell, y + cell], outline=(120, 124, 140), width=1)
        draw.text(
            (x + 4, y + cell + 8),
            f"{size}px  trail={'yes' if size <= 40 else 'no'}",
            fill=(225, 225, 235),
            font=label_font,
        )
    sheet.save(out_dir / "veno_web_fx_v1.png")
    print(out_dir / "veno_web_fx_v1.png")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=SOURCE)
    parser.add_argument("--out-dir", type=Path, default=OUT)
    parser.add_argument("--crop", default="492,155,622,278")
    args = parser.parse_args()

    if args.source.name != SOURCE_NAME:
        print(
            f"ERROR source must be {SOURCE_NAME}, got {args.source.name}; "
            "do not use combined/spider frames"
        )
        return 1
    if not args.source.exists():
        print(f"ERROR missing source: {args.source}")
        return 1

    box = tuple(int(part) for part in args.crop.split(","))
    if len(box) != 4:
        print("ERROR --crop must be x0,y0,x1,y1")
        return 1

    args.out_dir.mkdir(parents=True, exist_ok=True)
    source = Image.open(args.source).convert("RGBA")
    crop = source.crop(box)
    if crop.width <= 0 or crop.height <= 0:
        print("ERROR empty crop")
        return 1
    crop_path = args.out_dir / "veno_web_05_web.png"
    crop.save(crop_path)
    build_preview(crop, args.out_dir)
    manifest = {
        "tool": "generate_veno_web_bolt.py",
        "source": str(args.source),
        "source_name": SOURCE_NAME,
        "crop_box": list(box),
        "crop_size": [crop.width, crop.height],
        "alpha_bbox": list(crop.getchannel("A").getbbox() or (0, 0, 0, 0)),
        "notes": "No thread, droplets, padding or recolor baked in.",
        "runtime_path": "assets/frames/veno/veno_web_fx/veno_web_05_web.png",
    }
    (args.out_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
