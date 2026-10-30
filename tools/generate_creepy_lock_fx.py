"""Generate the 3-frame circular lock-on reticle for Creepy Shooter's wind-up.

Frame timing is 0.30 / 0.40 / 0.30 seconds. Frame 2 (index 1) has a red
padlock center. Runtime copies are not written here; approval comes first.
"""

from __future__ import annotations

import argparse
import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "assets" / "generated" / "contact_sheets" / "creepy_lock_fx_v1"

VIOLET = (190, 120, 255, 255)
VIOLET_DARK = (58, 28, 92, 255)
VIOLET_RED = (220, 90, 210, 255)
DOT_COLORS = ((80, 230, 225, 255), (222, 58, 70, 255), (230, 255, 250, 255))
PAD_DARK = (28, 22, 38, 255)


def _circle_points(cx: int, cy: int, radius: int) -> list[tuple[int, int]]:
    points: list[tuple[int, int]] = []
    x = radius
    y = 0
    error = 1 - radius
    while x >= y:
        for px, py in (
            (x, y), (y, x), (-y, x), (-x, y),
            (-x, -y), (-y, -x), (y, -x), (x, -y),
        ):
            points.append((cx + px, cy + py))
        y += 1
        if error < 0:
            error += 2 * y + 1
        else:
            x -= 1
            error += 2 * (y - x) + 1
    return points


def _in_gap(dx: float, dy: float) -> bool:
    angle = math.degrees(math.atan2(dy, dx))
    return any(abs(((angle - target + 180.0) % 360.0) - 180.0) < 9.0
               for target in (0.0, 90.0, 180.0, -90.0))


def _draw_dot(d: ImageDraw.ImageDraw, cx: int, cy: int, radius: int, color) -> None:
    for dy in range(-radius - 1, radius + 2):
        for dx in range(-radius - 1, radius + 2):
            if dx * dx + dy * dy <= (radius + 1) * (radius + 1):
                d.point((cx + dx, cy + dy), fill=PAD_DARK)
    for dy in range(-radius, radius + 1):
        for dx in range(-radius, radius + 1):
            if dx * dx + dy * dy <= radius * radius:
                d.point((cx + dx, cy + dy), fill=color)


def lock_frame(index: int) -> Image.Image:
    im = Image.new("RGBA", (48, 48), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    cx, cy = 24, 24
    # Frame sizes: large, small, large.
    radius = (18, 14, 18)[index]
    ring = VIOLET_RED if index == 1 else VIOLET
    cross_color = VIOLET_RED if index == 1 else VIOLET
    dot_color = DOT_COLORS[index]
    arm_start, arm_end = (5, 10) if index != 1 else (4, 8)
    dot_radius = 3 if index != 1 else 2

    # Two-pixel circular ring with cardinal gaps.
    for r, color in ((radius, ring), (radius - 1, ring)):
        for x, y in _circle_points(cx, cy, r):
            dx, dy = x - cx, y - cy
            if _in_gap(dx, dy):
                continue
            d.rectangle([x, y, x + 1, y + 1], fill=color)
    # Outer dark edge for readability on any outfit.
    for x, y in _circle_points(cx, cy, radius + 1):
        dx, dy = x - cx, y - cy
        if _in_gap(dx, dy):
            continue
        d.rectangle([x, y, x, y], fill=VIOLET_DARK)

    # Four cardinal ticks.
    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        x0 = cx + dx * (radius + 2)
        y0 = cy + dy * (radius + 2)
        x1 = cx + dx * (radius + 5)
        y1 = cy + dy * (radius + 5)
        d.line([x0, y0, x1, y1], fill=ring, width=2)

    # Four separate cross arms (not touching the center dot).
    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        p0 = (cx + dx * arm_start, cy + dy * arm_start)
        p1 = (cx + dx * arm_end, cy + dy * arm_end)
        d.line([p0, p1], fill=PAD_DARK, width=4)
        d.line([p0, p1], fill=cross_color, width=2)
    # Circular center dot in a different color.
    _draw_dot(d, cx, cy, dot_radius, dot_color)
    return im


def _font(size: int):
    try:
        return ImageFont.truetype("arial.ttf", size)
    except Exception:  # noqa: BLE001
        return ImageFont.load_default()


def build_sheet(frames: list[Image.Image], out_dir: Path) -> None:
    pad = 20
    cell = 210
    width = pad + 3 * (cell + pad)
    height = 300
    sheet = Image.new("RGB", (width, height), (48, 50, 58))
    draw = ImageDraw.Draw(sheet)
    for y in range(0, height, 20):
        for x in range(0, width, 20):
            if (x // 20 + y // 20) % 2:
                draw.rectangle([x, y, x + 19, y + 19], fill=(66, 68, 78))
    title = _font(20)
    label = _font(14)
    draw.text(
        (pad, 10),
        "Creepy Shooter lock-on reticle - 3 frames (0.30 / 0.40 / 0.30s)",
        fill=(238, 238, 246), font=title,
    )
    timings = ("00  0.30s  large", "01  0.40s  small / dot RED", "02  0.30s  large")
    for i, frame in enumerate(frames):
        x = pad + i * (cell + pad)
        board = sheet.crop((x, 50, x + cell, 50 + cell)).convert("RGBA")
        large = frame.resize((frame.width * 4, frame.height * 4), Image.Resampling.NEAREST)
        board.alpha_composite(large, ((cell - large.width) // 2, (cell - large.height) // 2))
        sheet.paste(board.convert("RGB"), (x, 50))
        draw.rectangle([x, 50, x + cell, 50 + cell], outline=(120, 124, 140), width=1)
        draw.text((x + 4, 50 + cell + 6), f"{timings[i]}  @4x", fill=(225, 225, 235), font=label)
    sheet.save(out_dir / "creepy_lock_fx_v1.png")
    print(out_dir / "creepy_lock_fx_v1.png")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", type=Path, default=OUT)
    args = parser.parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)
    frames = [lock_frame(i) for i in range(3)]
    for i, frame in enumerate(frames):
        frame.save(args.out_dir / f"creepy_lock_{i:02d}.png")
    build_sheet(frames, args.out_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
