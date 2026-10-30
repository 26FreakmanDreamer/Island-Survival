"""Generate Creepy Shooter's normal and homing projectile sprites.

The two bullets must read as different pixel-art objects: a cyan/white tracer
for the straight and downward shots, and a violet/cyan lock ring for the
homing shot. Runtime copies are not written here; the approved PNGs are
installed into ``assets/frames/creepy_shooter/fx/`` after review.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "assets" / "generated" / "contact_sheets" / "creepy_shooter_fx_v1"

CYAN = (80, 230, 225, 255)
CYAN_BRIGHT = (190, 255, 252, 255)
CYAN_DARK = (24, 92, 104, 220)
WHITE = (245, 255, 255, 255)
VIOLET = (190, 120, 255, 255)
VIOLET_DARK = (92, 52, 140, 230)


def normal_frame(index: int) -> Image.Image:
    """32x12 tracer pointing right; the runtime rotates it to the shot angle."""
    im = Image.new("RGBA", (32, 12), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    if index == 0:
        d.rectangle([0, 5, 6, 6], fill=CYAN_DARK)
        d.rectangle([4, 3, 30, 8], fill=CYAN_DARK)
        d.rectangle([6, 4, 29, 7], fill=CYAN)
        d.rectangle([14, 4, 27, 7], fill=CYAN_BRIGHT)
        d.rectangle([20, 4, 28, 7], fill=WHITE)
        d.rectangle([26, 5, 30, 6], fill=WHITE)
        d.point([16, 2], fill=CYAN_BRIGHT)
        d.point([22, 9], fill=CYAN)
    else:
        d.rectangle([0, 5, 8, 6], fill=CYAN_DARK)
        d.rectangle([6, 4, 30, 7], fill=CYAN_DARK)
        d.rectangle([8, 5, 28, 6], fill=CYAN)
        d.rectangle([14, 5, 26, 6], fill=CYAN_BRIGHT)
        d.rectangle([22, 4, 29, 7], fill=WHITE)
        d.rectangle([27, 5, 30, 6], fill=WHITE)
        d.point([12, 3], fill=CYAN)
        d.point([19, 8], fill=CYAN_BRIGHT)
    return im


def homing_frame(index: int) -> Image.Image:
    """40x24 violet homing bolt with cyan nose/core and lock-on brackets."""
    im = Image.new("RGBA", (40, 24), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    fin = (0, 1, 0)[index]
    # Split tail fins so the bolt reads as a projectile, not a ring.
    d.polygon([(2, 7 + fin), (10, 9), (10, 13), (2, 10 - fin)], fill=VIOLET_DARK)
    d.polygon([(2, 17 - fin), (10, 15), (10, 11), (2, 14 + fin)], fill=VIOLET_DARK)
    # Tapered violet body with a dark outline.
    body = [(7, 8), (29, 9), (37, 12), (29, 15), (7, 16)]
    d.polygon(body, fill=VIOLET)
    d.line(body + [body[0]], fill=VIOLET_DARK, width=1, joint="curve")
    # Bright cyan core and nose; frame 1 pulses wider.
    core_half = (1, 2, 1)[index]
    d.rectangle([12, 12 - core_half, 29, 12 + core_half], fill=CYAN_BRIGHT)
    d.rectangle([24, 11, 29, 13], fill=WHITE)
    nose = [(29, 9), (38, 12), (29, 15)]
    d.polygon(nose, fill=CYAN_BRIGHT)
    d.line(nose + [nose[0]], fill=VIOLET_DARK, width=1)
    # Four lock-on corner brackets; they pulse outward per frame.
    off = (3, 2, 4)[index]
    bracket = 5
    color = VIOLET if index != 1 else VIOLET_DARK
    d.line([(off, off + bracket), (off, off), (off + bracket, off)], fill=color, width=2)
    d.line([(39 - off - bracket, off), (39 - off, off), (39 - off, off + bracket)], fill=color, width=2)
    d.line([(off, 23 - off - bracket), (off, 23 - off), (off + bracket, 23 - off)], fill=color, width=2)
    d.line([(39 - off - bracket, 23 - off), (39 - off, 23 - off), (39 - off, 23 - off - bracket)], fill=color, width=2)
    # Small motion sparks.
    d.point([5, 4], fill=CYAN_BRIGHT)
    d.point([34, 20], fill=CYAN)
    return im


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
                draw.rectangle([x, y, x + tile - 1, y + tile - 1], fill=(82, 84, 96))
    return board


def build_sheet(normal: list[Image.Image], homing: list[Image.Image], out_dir: Path) -> None:
    pad = 20
    cell_w, cell_h = 210, 190
    columns = 4
    width = pad + columns * (cell_w + pad)
    height = 120 + 2 * (cell_h + pad) + 40
    sheet = _checkerboard((width, height))
    draw = ImageDraw.Draw(sheet)
    title = _font(20)
    label = _font(14)
    draw.text((pad, 10), "Creepy Shooter bullets - normal tracer vs homing bolt", fill=(238, 238, 246), font=title)

    def blit(frame: Image.Image, x: int, y: int, scale: int) -> None:
        large = frame.resize((frame.width * scale, frame.height * scale), Image.Resampling.NEAREST)
        board = sheet.crop((x, y, x + cell_w, y + cell_h)).convert("RGBA")
        board.alpha_composite(large, ((cell_w - large.width) // 2, (cell_h - large.height) // 2))
        sheet.paste(board.convert("RGB"), (x, y))
        draw.rectangle([x, y, x + cell_w, y + cell_h], outline=(120, 124, 140), width=1)

    def blit_row(frames: list[Image.Image], x: int, y: int) -> None:
        board = sheet.crop((x, y, x + cell_w, y + cell_h)).convert("RGBA")
        cursor = 12
        for frame in frames:
            board.alpha_composite(frame, (cursor, (cell_h - frame.height) // 2))
            cursor += frame.width + 10
        sheet.paste(board.convert("RGB"), (x, y))
        draw.rectangle([x, y, x + cell_w, y + cell_h], outline=(120, 124, 140), width=1)

    y0 = 50
    for i, frame in enumerate(normal):
        x = pad + i * (cell_w + pad)
        blit(frame, x, y0, 4)
        draw.text((x + 4, y0 + cell_h + 4), f"normal {i:02d}  32x12 @4x", fill=(225, 225, 235), font=label)
    x = pad + 2 * (cell_w + pad)
    blit_row(normal, x, y0)
    draw.text((x + 4, y0 + cell_h + 4), "normal 1x runtime size", fill=(225, 225, 235), font=label)

    y1 = y0 + cell_h + pad + 20
    for i, frame in enumerate(homing):
        x = pad + i * (cell_w + pad)
        blit(frame, x, y1, 4)
        draw.text((x + 4, y1 + cell_h + 4), f"homing {i:02d}  40x24 @4x", fill=(225, 225, 235), font=label)
    x = pad + 3 * (cell_w + pad)
    blit_row(homing, x, y1)
    draw.text((x + 4, y1 + cell_h + 4), "homing 1x runtime size", fill=(225, 225, 235), font=label)

    sheet.save(out_dir / "creepy_shooter_bullets_v1.png")
    print(out_dir / "creepy_shooter_bullets_v1.png")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", type=Path, default=OUT)
    args = parser.parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)

    normal = [normal_frame(0), normal_frame(1)]
    homing = [homing_frame(0), homing_frame(1), homing_frame(2)]
    for i, frame in enumerate(normal):
        frame.save(args.out_dir / f"creepy_bullet_{i:02d}.png")
    for i, frame in enumerate(homing):
        frame.save(args.out_dir / f"creepy_homing_bullet_{i:02d}.png")
    build_sheet(normal, homing, args.out_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
