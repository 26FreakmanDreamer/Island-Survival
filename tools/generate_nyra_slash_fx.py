"""Draw a separate six-frame slash trail for Nyra and preview it over the sprites."""

from __future__ import annotations

import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter


ROOT = Path(__file__).resolve().parents[1]
FRAMES = ROOT / "assets/generated/staged/nyra/nyra_slash_v11_final"
FX_DIR = ROOT / "assets/generated/staged/nyra/nyra_slash_fx_v3"
COMBINED_DIR = ROOT / "assets/generated/staged/nyra/nyra_slash_fx_v3_combined"
SIZE = 384
SCALE = 4


def point(x: float, y: float) -> tuple[int, int]:
    return round(x * SCALE), round(y * SCALE)


def curve(start, control, end, steps=32):
    result = []
    for i in range(steps + 1):
        t = i / steps
        u = 1 - t
        result.append(
            (
                u * u * start[0] + 2 * u * t * control[0] + t * t * end[0],
                u * u * start[1] + 2 * u * t * control[1] + t * t * end[1],
            )
        )
    return result


def stroke(image, path, color, width):
    ImageDraw.Draw(image).line(
        [point(*p) for p in path], fill=color, width=round(width * SCALE), joint="curve"
    )


def ribbon(image, path, widths, color):
    left = []
    right = []
    for i, (x, y) in enumerate(path):
        previous = path[max(i - 1, 0)]
        following = path[min(i + 1, len(path) - 1)]
        dx, dy = following[0] - previous[0], following[1] - previous[1]
        length = math.hypot(dx, dy) or 1
        nx, ny = -dy / length, dx / length
        t = i / (len(path) - 1)
        width = widths[0] + (widths[1] - widths[0]) * t
        left.append(point(x + nx * width / 2, y + ny * width / 2))
        right.append(point(x - nx * width / 2, y - ny * width / 2))
    ImageDraw.Draw(image).polygon(left + right[::-1], fill=color)


def triangle(image, points, color):
    ImageDraw.Draw(image).polygon([point(*p) for p in points], fill=color)


def draw_frame(index: int) -> Image.Image:
    canvas = Image.new("RGBA", (SIZE * SCALE, SIZE * SCALE))
    if index in (0, 1, 5):
        return canvas.resize((SIZE, SIZE), Image.Resampling.LANCZOS)
    if index == 4:
        # A lingering afterimage: identical geometry and position to frame 03.
        effect = draw_frame(3)
        effect.putalpha(effect.getchannel("A").point(lambda alpha: round(alpha * 0.39)))
        return effect

    glow = Image.new("RGBA", canvas.size)
    fill = Image.new("RGBA", canvas.size)
    edges = Image.new("RGBA", canvas.size)
    core = Image.new("RGBA", canvas.size)

    if index == 2:
        # Early V is light and closes beyond this frame's shortened blade tip.
        upper = curve((240, 202), (273, 198), (305, 224))
        lower = curve((239, 247), (274, 247), (305, 224))
        ImageDraw.Draw(fill).polygon(
            [point(*p) for p in upper] + [point(*p) for p in lower[::-1]],
            fill=(47, 168, 246, 22),
        )
        for path in (upper, lower):
            stroke(glow, path, (22, 165, 255, 72), 11)
            stroke(edges, path, (45, 184, 255, 145), 3.1)
            stroke(core, path[7:-5], (212, 246, 255, 124), 1.1)
    elif index == 3:
        # Bright converging edges enclose the horizontal blade. Their meeting
        # point is 29 px to the right of the actual sword tip at about x=336.
        upper = curve((237, 184), (292, 178), (365, 218))
        lower = curve((235, 260), (296, 257), (365, 218))
        inner_upper = curve((246, 194), (304, 195), (359, 217))
        inner_lower = curve((247, 247), (305, 242), (359, 220))
        ImageDraw.Draw(fill).polygon(
            [point(*p) for p in upper] + [point(*p) for p in lower[::-1]],
            fill=(47, 168, 246, 43),
        )
        ribbon(fill, upper, (14, 1), (72, 203, 255, 66))
        ribbon(fill, lower, (13, 1), (53, 189, 252, 65))
        for path in (upper, lower):
            stroke(glow, path, (22, 165, 255, 147), 17)
            stroke(edges, path, (32, 180, 255, 235), 5.8)
            stroke(core, path[5:-3], (220, 249, 255, 233), 2.0)
        stroke(edges, inner_upper, (120, 221, 255, 107), 2.0)
        stroke(edges, inner_lower, (119, 221, 255, 99), 2.0)
        triangle(core, [(360, 214), (373, 218), (360, 222)], (223, 250, 255, 212))
        for x, y, radius in [(369, 215, 1.4), (343, 192, 1.1), (354, 239, 1.0)]:
            cx, cy = point(x, y)
            r = round(radius * SCALE)
            ImageDraw.Draw(core).ellipse((cx-r, cy-r, cx+r, cy+r), fill=(219, 247, 255, 190))
    canvas = Image.alpha_composite(canvas, glow.filter(ImageFilter.GaussianBlur(6 * SCALE)))
    canvas = Image.alpha_composite(canvas, fill)
    canvas = Image.alpha_composite(canvas, edges)
    canvas = Image.alpha_composite(canvas, core)
    return canvas.resize((SIZE, SIZE), Image.Resampling.LANCZOS)


def main() -> None:
    FX_DIR.mkdir(parents=True, exist_ok=True)
    COMBINED_DIR.mkdir(parents=True, exist_ok=True)
    for index in range(6):
        source_name = f"nyra_slash_{index:02d}.png"
        output_name = f"nyra_slash_fx_{index:02d}.png"
        frame = Image.open(FRAMES / source_name).convert("RGBA")
        effect = draw_frame(index)
        effect.save(FX_DIR / output_name)
        Image.alpha_composite(frame, effect).save(COMBINED_DIR / output_name)
    print(FX_DIR)
    print(COMBINED_DIR)


if __name__ == "__main__":
    main()
