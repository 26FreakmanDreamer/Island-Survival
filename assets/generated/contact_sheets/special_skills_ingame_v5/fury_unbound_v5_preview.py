"""Rebuild the six-frame Fury Unbound V5 preview from the adjacent V4 assets."""

import argparse
import json
import math
import random
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageSequence


HERE = Path(__file__).resolve().parent
SOURCE = HERE.parent / "special_skills_ingame_v4"
OUTPUT = HERE / "fury_unbound_v5_preview.gif"
FRAME_COUNT = 6
FEET_X, FEET_Y = 307, 361
LEFT, TOP, RIGHT, BOTTOM = -56, -232, 56, -51
WIDTH, HEIGHT = RIGHT - LEFT, BOTTOM - TOP
PREVIEW_RECT = (FEET_X + LEFT, FEET_Y + TOP, FEET_X + RIGHT, FEET_Y + BOTTOM)
SUPERSAMPLE = 3


def clamp(value: float) -> float:
    return max(0, min(1, value))


def reserved_pixels_mask() -> Image.Image:
    """Keep the new particles clear of the V4 shield, purity, and lower Fury frames."""
    manifest = json.loads((SOURCE / "special_skills_v4_manifest.json").read_text(encoding="utf-8"))
    blocked = Image.new("L", (WIDTH, HEIGHT))
    for skill in manifest["skills"][:3]:
        frame_width, frame_height = skill["frame_size_px"]
        x, y = skill["top_left_from_feet_px"]
        with Image.open(SOURCE / skill["atlas"]) as atlas:
            for frame in range(FRAME_COUNT):
                left = frame * frame_width
                alpha = atlas.crop((left, 0, left + frame_width, frame_height)).getchannel("A")
                placed = Image.new("L", blocked.size)
                placed.paste(alpha, (x - LEFT, y - TOP))
                blocked = ImageChops.lighter(blocked, placed)
    return blocked.point(lambda alpha: 0 if alpha else 255)


def render_rising_embers(frame: int, allowed: Image.Image) -> Image.Image:
    """Draw only the upper particle layer, from above the boots to head height."""
    canvas = Image.new("RGBA", (WIDTH * SUPERSAMPLE, HEIGHT * SUPERSAMPLE))
    draw = ImageDraw.Draw(canvas)

    def polygon(points, color, opacity):
        positions = [
            (round((x - LEFT) * SUPERSAMPLE), round((y - TOP) * SUPERSAMPLE))
            for x, y in points
        ]
        draw.polygon(positions, fill=(*color, round(max(0, min(255, opacity)))))

    def ember(x, y, width, height, color, opacity):
        polygon(
            [(x, y - height), (x + width, y), (x, y + height), (x - width, y)],
            color,
            opacity,
        )

    # Reset the seed for each frame so every ember follows the same path through the loop.
    rng = random.Random(4481)
    for side in (-1, 1):
        for index in range(8):
            offset = (index * .125 + rng.uniform(-.036, .035)) % 1
            drift = rng.uniform(-8, 7)
            size = rng.uniform(.73, 1.54)
            phase = rng.uniform(0, math.tau)
            age = (offset + frame / FRAME_COUNT) % 1
            y = -53 - 164 * age
            path_width = 22 + 9 * math.sin(math.pi * age) - 1.5 * age
            x = side * path_width + drift + 4.2 * math.sin(age * 5 + phase)
            opacity = clamp(age / .10) * clamp((1 - age) / .13)
            dark = (164 + 10 * (index % 4), 40 + 7 * (index % 3), 24)
            red = (241, 80 + 9 * (index % 4), 38)
            hot = (255, 196 + 8 * (index % 4), 103)
            if index % 3 == 0:
                tail = 4 + size * 3.1
                lean = 1.8 * math.sin(age * 6 + phase)
                polygon(
                    [(x + .2, y - 1), (x + size + .65, y + 1.6), (x - lean, y + tail),
                     (x - size - .55, y + 2.1)],
                    dark,
                    219 * opacity,
                )
                polygon(
                    [(x, y - .2), (x + size * .73, y + 1.6), (x - lean * .76, y + tail * .76),
                     (x - size * .62, y + 2)],
                    red,
                    247 * opacity,
                )
                polygon(
                    [(x, y + .15), (x + size * .38, y + 1.5),
                     (x - lean * .37, y + tail * .46), (x - size * .28, y + 1.6)],
                    hot,
                    248 * opacity,
                )
            else:
                ember(x, y, size * 1.33 + .35, size * 1.55 + .48, dark, 229 * opacity)
                ember(x, y - .17, size * .99, size * 1.13, red, 248 * opacity)
                ember(x - .17, y - .42, size * .49, size * .63, hot, 250 * opacity)

    # Small embers peel away near the head and fade out before the loop resets.
    for index, offset in enumerate((.08, .36, .68, .84)):
        age = (offset + frame / FRAME_COUNT) % 1
        opacity = math.sin(math.pi * age) ** .73
        side = -1 if index % 2 == 0 else 1
        x = side * (19 + 10 * age) + 4 * math.sin(index * 3 + age * 2)
        y = -174 - 37 * age + index * 1.1
        ember(x, y, 1.26 + (index % 2) * .36, 1.68, (172, 50, 26), 208 * opacity)
        ember(x - .12, y - .2, .83 + (index % 2) * .27, 1.10, (255, 120, 51), 248 * opacity)
        ember(x - .26, y - .39, .38, .64, (255, 213, 133), 240 * opacity)

    ink = canvas.resize((WIDTH, HEIGHT), Image.Resampling.LANCZOS)
    alpha = ink.getchannel("A")
    halo = ImageChops.add(
        alpha.filter(ImageFilter.GaussianBlur(1.85)).point(lambda a: int(.66 * a)),
        alpha.filter(ImageFilter.GaussianBlur(3.3)).point(lambda a: int(.42 * a)),
    )
    layer = Image.new("RGBA", ink.size, (252, 126, 52))
    layer.putalpha(halo)
    layer.alpha_composite(ink)
    fade = Image.new("L", ink.size)
    fade.putdata([
        round(255 * clamp((HEIGHT - 1 - y) / 8) * clamp((y - 1) / 5))
        for y in range(HEIGHT)
        for _ in range(WIDTH)
    ])
    alpha = ImageChops.multiply(layer.getchannel("A"), ImageChops.multiply(fade, allowed))
    layer.putalpha(alpha.point(lambda a: a if a >= 4 else 0))
    return layer


def build_preview(output: Path) -> None:
    allowed = reserved_pixels_mask()
    with Image.open(SOURCE / "fury_unbound_v4_preview.gif") as source:
        palette = source.copy()
        colors = palette.getpalette()
        source_frames = [frame.convert("RGB") for frame in ImageSequence.Iterator(source)]
        durations = [frame.info["duration"] for frame in ImageSequence.Iterator(source)]

    color_index = {
        tuple(colors[index:index + 3]): index // 3
        for index in range(0, len(colors), 3)
    }
    frames = []
    for index, base in enumerate(source_frames):
        painted = base.convert("RGBA")
        painted.alpha_composite(render_rising_embers(index, allowed), PREVIEW_RECT[:2])
        draft = painted.convert("RGB").quantize(palette=palette, dither=Image.Dither.NONE)
        approximation = base.quantize(palette=palette, dither=Image.Dither.NONE)

        # Compare equally quantized crops, then paste only changed particle pixels.
        # Re-index the preserved colors exactly so the lower effect stays pixel-identical.
        region = draft.convert("RGB").crop(PREVIEW_RECT)
        delta = ImageChops.difference(region, approximation.convert("RGB").crop(PREVIEW_RECT))
        red, green, blue = delta.split()
        changed = ImageChops.lighter(red, ImageChops.lighter(green, blue)).point(
            lambda value: 255 if value else 0
        )
        base.paste(region, PREVIEW_RECT[:2], changed)
        indexed = Image.new("P", base.size)
        indexed.putpalette(colors)
        indexed.putdata([color_index[pixel] for pixel in base.get_flattened_data()])
        frames.append(indexed)

    frames[0].save(
        output,
        save_all=True,
        append_images=frames[1:],
        duration=durations,
        loop=0,
        disposal=1,
        optimize=False,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=OUTPUT, help="Path for the generated GIF")
    args = parser.parse_args()
    build_preview(args.output)
    print(args.output.resolve())


if __name__ == "__main__":
    main()
