"""Build separated Veno web-spit animation layers and review previews."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "assets" / "generated" / "contact_sheets"
SPIDER_SRC = ROOT / "assets" / "frames" / "veno" / "veno_web"
FRAME_SIZE = (640, 320)
FRAMES = 6
POSES = (0, 1, 2, 2, 1, 0)
DURATIONS = (140, 100, 90, 90, 100, 180)
MOUTH = ((263, 259), (267, 260), (269, 267), (269, 267), (267, 260), (263, 259))


def web_image(path: Path) -> Image.Image:
    image = Image.open(path).convert("RGBA")
    alpha = image.getchannel("A")
    bounds = alpha.point(lambda value: 255 if value > 20 else 0).getbbox()
    if bounds is None:
        raise ValueError("Generated web has no visible pixels")
    return image.crop(bounds)


def add_web(web: Image.Image, source: Image.Image, index: int) -> None:
    if index == 0:
        return
    draw = ImageDraw.Draw(web)
    ox, oy = MOUTH[index]
    if index == 1:
        draw.ellipse((ox + 3, oy - 7, ox + 14, oy + 4), fill=(193, 255, 136, 230))
        draw.ellipse((ox + 6, oy - 5, ox + 11, oy), fill=(255, 255, 240, 255))
        draw.line((ox + 2, oy, ox + 7, oy - 2), fill=(212, 255, 208, 220), width=2)
        return

    centers = {2: (318, 251), 3: (391, 241), 4: (477, 229), 5: (557, 216)}
    sizes = {2: (40, 30), 3: (75, 68), 4: (105, 98), 5: (130, 122)}
    cx, cy = centers[index]
    width, height = sizes[index]

    # The sticky launch thread is tied to the mouth only during release.
    if index <= 4:
        end_x = cx - width // 2 + 5
        strength = {2: 205, 3: 145, 4: 80}[index]
        draw.line((ox + 6, oy - 1, end_x, cy), fill=(30, 74, 27, strength), width=5)
        draw.line((ox + 6, oy - 2, end_x, cy - 1), fill=(212, 255, 191, strength), width=2)
        draw.line((ox + 7, oy + 2, end_x - 3, cy + 6), fill=(158, 248, 124, strength // 2), width=1)

    # A few fading silk droplets make the travel direction readable.
    if index >= 3:
        trail_alpha = {3: 135, 4: 105, 5: 70}[index]
        for distance, offset, radius in ((24, 3, 2), (47, -4, 2), (65, 5, 1)):
            tx = cx - width // 2 - distance
            if tx > ox + 20:
                draw.ellipse(
                    (tx - radius, cy + offset - radius, tx + radius, cy + offset + radius),
                    fill=(198, 255, 170, trail_alpha),
                )

    scaled = source.resize((width, height), Image.Resampling.LANCZOS)
    web.alpha_composite(scaled, (cx - width // 2, cy - height // 2))


def checkerboard(size: tuple[int, int], cell: int = 16) -> Image.Image:
    board = Image.new("RGB", size, (72, 74, 83))
    draw = ImageDraw.Draw(board)
    for y in range(0, size[1], cell):
        for x in range(0, size[0], cell):
            if (x // cell + y // cell) % 2:
                draw.rectangle((x, y, x + cell - 1, y + cell - 1), fill=(87, 89, 99))
    return board


def contact_sheet(frames: list[Image.Image], title: str, labels: bool) -> Image.Image:
    margin, gap, header, footer = 12, 12, 34, 26 if labels else 0
    fw, fh = FRAME_SIZE
    sheet = Image.new(
        "RGB", (margin * 2 + fw * 3 + gap * 2, header + margin * 2 + (fh + footer) * 2 + gap),
        (25, 27, 35),
    )
    draw = ImageDraw.Draw(sheet)
    draw.text((margin, 11), title, fill=(237, 239, 245))
    for index, frame in enumerate(frames):
        x = margin + index % 3 * (fw + gap)
        y = header + margin + index // 3 * (fh + footer + gap)
        board = checkerboard(FRAME_SIZE)
        board.paste(frame, (0, 0), frame)
        sheet.paste(board, (x, y))
        if labels:
            draw.text((x + 4, y + fh + 5), f"{index:02d}    {DURATIONS[index]} ms", fill=(207, 212, 221))
    return sheet


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--web-source", type=Path, default=OUT / "veno_web_spit_v2_web_master.png"
    )
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    frames_dir = OUT / "veno_web_spit_v2_frames"
    frames_dir.mkdir(exist_ok=True)
    source = web_image(args.web_source)
    source.save(OUT / "veno_web_spit_v2_web_master.png")

    spiders: list[Image.Image] = []
    webs: list[Image.Image] = []
    combined: list[Image.Image] = []
    for index in range(FRAMES):
        spider = Image.new("RGBA", FRAME_SIZE)
        pose = Image.open(SPIDER_SRC / f"veno_web_{POSES[index]:02d}.png").convert("RGBA")
        spider.alpha_composite(pose, (0, 0))
        web = Image.new("RGBA", FRAME_SIZE)
        add_web(web, source, index)
        frame = spider.copy()
        frame.alpha_composite(web)
        for layer, image in (("spider", spider), ("web", web), ("combined", frame)):
            image.save(frames_dir / f"veno_web_spit_{layer}_{index:02d}.png")
        spiders.append(spider)
        webs.append(web)
        combined.append(frame)

    for layer, frames in (("spider", spiders), ("web", webs)):
        atlas = Image.new("RGBA", (FRAME_SIZE[0] * 3, FRAME_SIZE[1] * 2))
        for index, frame in enumerate(frames):
            atlas.alpha_composite(frame, (index % 3 * FRAME_SIZE[0], index // 3 * FRAME_SIZE[1]))
        atlas.save(OUT / f"veno_web_spit_v2_{layer}_sheet.png")
        contact_sheet(frames, f"Veno web spit / {layer} layer - 6 frames", True).save(
            OUT / f"veno_web_spit_v2_{layer}_preview.png"
        )

    contact_sheet(combined, "Veno web spit / combined preview - 6 frames", True).save(
        OUT / "veno_web_spit_v2_combined_preview.png"
    )
    gif_frames = []
    for frame in combined:
        board = checkerboard(FRAME_SIZE)
        board.paste(frame, (0, 0), frame)
        gif_frames.append(board)
    gif_frames[0].save(
        OUT / "veno_web_spit_v2_combined_preview.gif",
        save_all=True,
        append_images=gif_frames[1:],
        duration=DURATIONS,
        loop=0,
        optimize=False,
        disposal=2,
    )
    (OUT / "veno_web_spit_v2_manifest.json").write_text(
        json.dumps(
            {
                "frame_size": list(FRAME_SIZE),
                "layout": {"columns": 3, "rows": 2},
                "frame_order": "left-to-right, top-to-bottom",
                "durations_ms": list(DURATIONS),
                "pivot": [160, 308],
                "spider_source_poses": list(POSES),
                "layers": ["spider", "web"],
            },
            indent=2,
        ) + "\n",
        encoding="utf-8",
    )
    print(f"Saved {FRAMES} separate spider/web frame pairs, atlases, and combined previews to {OUT}")


if __name__ == "__main__":
    main()
