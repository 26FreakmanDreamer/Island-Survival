"""Build a labeled grid contact sheet from a small JSON manifest.

The existing ``contact_sheet.py`` handles one action in one row.  Bat approval
needs a matrix (candidates by pose, plus reference/mirror cells), so this tool
takes an explicit manifest:

{
  "title": "Bat key poses - v1",
  "columns": 6,
  "cell": 320,
  "pivot": [160, 224],
  "rows": [
    [
      {"path": "assets/generated/staged/bat/reference/base_320.png",
       "label": "canonical / base", "duration": ""},
      {"path": "assets/generated/staged/bat/keyposes/wing_00_a.png",
       "label": "wing_00 A", "duration": "0.22"}
    ],
    [null, {"path": "...", "label": "wing_00 B"}]
  ]
}

Cells may be null to leave a gap.  Missing files are drawn as red MISSING
cells so an incomplete batch is obvious in review.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

PAD = 12
LABEL_H = 44
TITLE_H = 34


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
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--out", default="")
    parser.add_argument("--cell", type=int, default=0)
    parser.add_argument("--pivot-x", type=int, default=-1)
    parser.add_argument("--pivot-y", type=int, default=-1)
    parser.add_argument("--title", default="")
    args = parser.parse_args()

    manifest_path = _resolve(args.manifest)
    if not manifest_path.exists():
        print(f"ERROR manifest not found: {manifest_path}")
        return 1
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    rows = manifest.get("rows") or []
    if not rows:
        print("ERROR manifest has no rows")
        return 1

    cell = args.cell or int(manifest.get("cell", 320))
    cell = max(1, cell)
    pivot = manifest.get("pivot", [160, 224])
    pivot_x = args.pivot_x if args.pivot_x >= 0 else int(pivot[0])
    pivot_y = args.pivot_y if args.pivot_y >= 0 else int(pivot[1])
    columns = int(manifest.get("columns") or max(len(row) for row in rows))
    title = args.title or manifest.get("title") or "contact sheet"
    out_text = args.out or manifest.get("out") or ""
    if not out_text:
        print("ERROR provide --out or a manifest 'out' path")
        return 1
    out_path = _resolve(out_text)

    width = PAD + columns * (cell + PAD)
    row_height = cell + LABEL_H + PAD
    height = TITLE_H + len(rows) * row_height + PAD
    sheet = Image.new("RGB", (width, height), (26, 28, 36))
    draw = ImageDraw.Draw(sheet)
    title_font = _font(20)
    label_font = _font(14)
    draw.text((PAD, 8), title, fill=(238, 238, 246), font=title_font)

    for row_index, row in enumerate(rows):
        for column_index in range(columns):
            cell_x = PAD + column_index * (cell + PAD)
            cell_y = TITLE_H + row_index * row_height
            item = row[column_index] if column_index < len(row) else None
            if item is None:
                draw.rectangle(
                    [cell_x, cell_y, cell_x + cell - 1, cell_y + cell - 1],
                    fill=(34, 36, 44),
                    outline=(54, 56, 68),
                )
                continue

            path = _resolve(str(item.get("path", "")))
            label = str(item.get("label") or path.name or "-")
            duration = str(item.get("duration") or "")
            if duration:
                label = f"{label}  {duration}s"
            cell_pivot = item.get("pivot") or [pivot_x, pivot_y]
            cell_pivot_x = int(cell_pivot[0])
            cell_pivot_y = int(cell_pivot[1])

            if not path.exists():
                draw.rectangle(
                    [cell_x, cell_y, cell_x + cell - 1, cell_y + cell - 1],
                    fill=(90, 30, 38),
                    outline=(200, 70, 80),
                )
                draw.text(
                    (cell_x + 8, cell_y + 8),
                    f"MISSING {path.name}",
                    fill=(255, 220, 220),
                    font=label_font,
                )
                draw.text(
                    (cell_x + 4, cell_y + cell + 8),
                    label,
                    fill=(255, 150, 150),
                    font=label_font,
                )
                continue

            frame = Image.open(path).convert("RGBA")
            if frame.size != (cell, cell):
                frame = frame.resize((cell, cell), Image.LANCZOS)
            board = _checkerboard((cell, cell))
            board.paste(frame, (0, 0), frame)

            overlay = ImageDraw.Draw(board)
            overlay.line(
                [(0, cell_pivot_y), (cell, cell_pivot_y)],
                fill=(255, 210, 80),
                width=1,
            )
            overlay.line(
                [(cell_pivot_x, 0), (cell_pivot_x, cell)],
                fill=(120, 220, 255),
                width=1,
            )
            overlay.line(
                [(cell_pivot_x - 8, cell_pivot_y), (cell_pivot_x + 8, cell_pivot_y)],
                fill=(255, 70, 70),
                width=2,
            )
            overlay.line(
                [(cell_pivot_x, cell_pivot_y - 8), (cell_pivot_x, cell_pivot_y + 8)],
                fill=(255, 70, 70),
                width=2,
            )
            sheet.paste(board, (cell_x, cell_y))
            draw.text(
                (cell_x + 4, cell_y + cell + 8),
                label,
                fill=(235, 235, 245),
                font=label_font,
            )

    out_path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out_path)
    print(out_path.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
