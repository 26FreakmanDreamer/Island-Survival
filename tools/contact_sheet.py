"""Build a labeled checkerboard contact sheet for frame approval."""

from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

CELL = 256
LABEL_H = 44
PAD = 12
TITLE_H = 34
PIVOT = (128, 244)


def _resolve(path_text: str) -> Path:
    path = Path(path_text)
    return path if path.is_absolute() else Path.cwd() / path


def _font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    try:
        return ImageFont.truetype("arial.ttf", size)
    except Exception:  # noqa: BLE001
        return ImageFont.load_default()


def _checkerboard(size: tuple[int, int], tile: int = 16) -> Image.Image:
    image = Image.new("RGB", size, (62, 64, 74))
    draw = ImageDraw.Draw(image)
    for y in range(0, size[1], tile):
        for x in range(0, size[0], tile):
            if (x // tile + y // tile) % 2:
                draw.rectangle([x, y, x + tile - 1, y + tile - 1], fill=(82, 84, 96))
    return image


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--action", required=True)
    parser.add_argument("--frames", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--durations", default="")
    parser.add_argument("--title", default="")
    args = parser.parse_args()

    frames_dir = _resolve(args.frames)
    out_path = _resolve(args.out)
    files = sorted(frames_dir.glob("*.png"))
    if not files:
        print(f"ERROR no frames in {frames_dir}")
        return 1

    durations = [item.strip() for item in args.durations.split(",") if item.strip()]
    title = args.title or f"{args.action} — {len(files)} frames"
    width = PAD + len(files) * (CELL + PAD)
    height = TITLE_H + CELL + LABEL_H + PAD * 2
    sheet = Image.new("RGB", (width, height), (26, 28, 36))
    draw = ImageDraw.Draw(sheet)
    title_font = _font(20)
    label_font = _font(14)
    draw.text((PAD, 8), title, fill=(238, 238, 246), font=title_font)

    for index, path in enumerate(files):
        frame = Image.open(path).convert("RGBA")
        if frame.size != (CELL, CELL):
            frame = frame.resize((CELL, CELL), Image.LANCZOS)
        cell_x = PAD + index * (CELL + PAD)
        cell_y = TITLE_H
        board = _checkerboard((CELL, CELL))
        board.paste(frame, (0, 0), frame)

        overlay = ImageDraw.Draw(board)
        overlay.line([(0, PIVOT[1]), (CELL, PIVOT[1])], fill=(255, 210, 80), width=1)
        overlay.line([(PIVOT[0], 0), (PIVOT[0], CELL)], fill=(120, 220, 255), width=1)
        overlay.line(
            [(PIVOT[0] - 8, PIVOT[1]), (PIVOT[0] + 8, PIVOT[1])],
            fill=(255, 70, 70), width=2,
        )
        overlay.line(
            [(PIVOT[0], PIVOT[1] - 8), (PIVOT[0], PIVOT[1] + 8)],
            fill=(255, 70, 70), width=2,
        )
        sheet.paste(board, (cell_x, cell_y))

        duration = durations[index] if index < len(durations) else "?"
        label = f"{index:02d}  {path.name}  {duration}s"
        draw.text((cell_x + 4, cell_y + CELL + 8), label, fill=(235, 235, 245), font=label_font)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out_path)
    print(out_path.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
