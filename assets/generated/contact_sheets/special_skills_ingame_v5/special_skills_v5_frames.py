"""Draw and export the four special skills as six transparent PNGs each.

All PNGs are 320 x 340, with the caster's feet at (160, 278).
Draw back to front: actor, Shield, Purity, Fury, Tonic.
"""

import argparse
import math
import random
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter

from fury_unbound_v5_preview import FRAME_COUNT, LEFT, TOP, RIGHT, BOTTOM, render_rising_embers


OUTPUT = Path(__file__).resolve().parent
CANVAS_SIZE = (320, 340)
FEET = (160, 278)
SUPERSAMPLE = 3
SHIELD = (-109, -261, 106, 44)
PURITY = (-78, -202, 78, -9)
FURY = (-66, -66, 66, 20)
TONIC = (-70, -221, 70, 16)


def size_of(bounds):
    left, top, right, bottom = bounds
    return right - left, bottom - top


def location(bounds):
    return FEET[0] + bounds[0], FEET[1] + bounds[1]


def clamp(value):
    return max(0, min(1, value))


def smooth(value):
    value = clamp(value)
    return value * value * (3 - 2 * value)


def gaussian(value, center, spread):
    return math.exp(-.5 * ((value - center) / spread) ** 2)


def soft_span(value, start, end, ramp):
    return smooth((value - start) / ramp) * smooth((end - value) / ramp)


def mix(colors):
    """Composite translucent glow and reflections at a single pixel."""
    rgb = [0.0, 0.0, 0.0]
    alpha = 0.0
    for color, opacity in colors:
        weight = clamp(opacity / 255)
        alpha = weight + alpha * (1 - weight)
        for channel in range(3):
            rgb[channel] = color[channel] * weight + rgb[channel] * (1 - weight)
    if alpha < .010:
        return 0, 0, 0, 0
    return (*[round(channel / alpha) for channel in rgb], round(255 * alpha))


def draw_shield(frame):
    left, top, right, bottom = SHIELD
    phase = math.tau * frame / FRAME_COUNT
    sheen = 3.94 + .10 * math.sin(phase)
    glow = .86 + .14 * math.cos(phase)
    pixels = []
    for y in range(top, bottom):
        for x in range(left, right):
            nx, ny = (x + .5 - (-2.0)) / 92.0, (y + .5 - (-110.0)) / 135.0
            radius = math.hypot(nx, ny)
            angle = math.atan2(ny, nx) % math.tau
            inside = smooth((1.012 - radius) / .027)
            fringe = smooth((radius - .735) / .22)
            crescent = gaussian(angle, sheen, .30)
            backlight = gaussian(angle, 1.17, .44)
            highlight = soft_span(angle, 3.61, 4.41, .16) * (.91 + .09 * math.sin(phase))
            secondary = soft_span(angle, 5.11, 5.76, .19)
            inner_radius = .892 + .014 * math.sin((angle - 3.67) * 5)
            reflection = gaussian(radius, inner_radius, .014) * soft_span(angle, 3.68, 4.30, .18)
            travel = ((angle - (3.89 + .12 * math.sin(phase)) + math.pi) % math.tau) - math.pi
            fleck = gaussian(travel, 0, .031) * gaussian(radius, 1.002, .024)
            pixels.append(mix([
                ((248, 164, 43), (46 * glow + 22 * crescent) * gaussian(radius, 1.013, .041)),
                ((236, 148, 29), inside * fringe * (32 + 39 * crescent + 13 * backlight)),
                ((255, 202, 90), inside * gaussian(radius, .944, .030) * (27 + 64 * crescent + 27 * backlight)),
                ((128, 66, 19), (69 - 25 * crescent) * gaussian(radius, 1.008, .013)),
                ((255, 186, 55), (156 + 37 * backlight) * gaussian(radius, .991, .012)),
                ((255, 232, 145), (119 + 110 * highlight + 55 * secondary + 25 * backlight)
                 * gaussian(radius, 1.002, .0084)),
                ((255, 245, 208), 95 * reflection + 61 * secondary * gaussian(radius, .939, .009)),
                ((255, 253, 220), 125 * fleck),
            ]))
    image = Image.new("RGBA", size_of(SHIELD))
    image.putdata(pixels)
    return image


def draw_purity(frame):
    left, top, right, bottom = PURITY
    phase = math.tau * frame / FRAME_COUNT
    pixels = []
    for y in range(top, bottom):
        py = y + .5
        height = clamp((py + 186) / 164)
        vertical_fade = soft_span(py, -190, -17, 28)
        wall = 56 + 5.8 * math.sin(math.pi * height)
        for x in range(left, right):
            side = -1 if x < 0 else 1
            edge = wall - abs(x + .5)
            front = smooth((edge + 3) / 5) * smooth((edge + 6) / 12) * smooth((20 - edge) / 9)
            light = .76 + .24 * math.sin(phase - py * .046 + side * .54)
            line = gaussian(edge, 0, .90)
            reflection = gaussian(edge, 4.8 + 1.7 * math.sin(phase + py * .029), 1.1)
            flow = .35 + .65 * (.5 + .5 * math.sin(py * .135 + phase + side)) ** 3
            pixels.append(mix([
                ((62, 161, 218), vertical_fade * gaussian(edge, -.4, 4.7) * 58),
                ((136, 213, 249), vertical_fade * front * (54 + 22 * light)),
                ((187, 239, 255), vertical_fade * front * gaussian(edge, 8.0, 4.3) * 34 * flow),
                ((161, 231, 253), vertical_fade * line * (118 + 30 * light)),
                ((223, 249, 255), vertical_fade * reflection * (67 + 28 * flow)),
            ]))
    image = Image.new("RGBA", size_of(PURITY))
    image.putdata(pixels)
    return image


class Brush:
    """Supersampled drawing for particles, crosses, and the healing ring."""

    def __init__(self, bounds):
        self.left, self.top = bounds[:2]
        self.size = size_of(bounds)
        self.image = Image.new("RGBA", tuple(length * SUPERSAMPLE for length in self.size))
        self.ink = ImageDraw.Draw(self.image)

    def point(self, xy):
        x, y = xy
        return round((x - self.left) * SUPERSAMPLE), round((y - self.top) * SUPERSAMPLE)

    @staticmethod
    def color(rgb, alpha):
        return (*rgb, round(max(0, min(255, alpha))))

    def polygon(self, points, rgb, alpha):
        self.ink.polygon([self.point(p) for p in points], fill=self.color(rgb, alpha))

    def line(self, points, rgb, alpha, width):
        self.ink.line(
            [self.point(p) for p in points],
            fill=self.color(rgb, alpha),
            width=max(1, round(width * SUPERSAMPLE)),
            joint="curve",
        )

    def gem(self, x, y, width, height, rgb, alpha):
        self.polygon([(x, y - height), (x + width, y), (x, y + height), (x - width, y)], rgb, alpha)

    def dot(self, x, y, radius, rgb, alpha):
        self.ink.ellipse(
            (self.point((x - radius, y - radius)), self.point((x + radius, y + radius))),
            fill=self.color(rgb, alpha),
        )

    def finish(self, color, strength, near, far):
        ink = self.image.resize(self.size, Image.Resampling.LANCZOS)
        alpha = ink.getchannel("A")
        near_radius, near_opacity = near
        far_radius, far_opacity = far
        bloom = ImageChops.add(
            alpha.filter(ImageFilter.GaussianBlur(near_radius)).point(
                lambda value: int(value * strength * near_opacity)
            ),
            alpha.filter(ImageFilter.GaussianBlur(far_radius)).point(
                lambda value: int(value * strength * far_opacity)
            ),
        )
        base = Image.new("RGBA", self.size, color)
        base.putalpha(bloom)
        base.alpha_composite(ink)
        return base


def draw_fury_at_feet(frame):
    brush = Brush(FURY)
    rng = random.Random(519)
    for index in range(41):
        center = (-25, 24, 0)[index % 3]
        start_x = center + rng.uniform(-14, 14)
        start_y = rng.uniform(-2, 7)
        start = rng.random()
        rise = rng.uniform(16, 50)
        size = rng.uniform(.65, 2.35)
        drift = rng.uniform(-10, 10)
        age = (start + frame / FRAME_COUNT) % 1
        x = start_x + drift * age
        y = start_y - rise * age
        opacity = math.sin(math.pi * age) ** .72
        dark = (150 + 11 * (index % 5), 32 + 7 * (index % 4), 27)
        red = (241, 80 + 9 * (index % 4), 38)
        gold = (255, 170 + 10 * (index % 5), 87)
        if index % 4 == 0:
            lean = (1 if drift > 0 else -1) * (1.4 + size)
            tail = 3.5 + size * 3.5
            brush.polygon(
                [(x + .35, y - 1), (x + size + 1, y + 2), (x - lean, y + tail), (x - size - .7, y + 3)],
                dark,
                236 * opacity,
            )
            brush.polygon(
                [(x, y), (x + size * .8, y + 2), (x - lean * .8, y + tail * .79), (x - size * .70, y + 2.5)],
                red,
                253 * opacity,
            )
            brush.polygon(
                [(x, y + .45), (x + size * .5, y + 2), (x - lean * .44, y + tail * .49),
                 (x - size * .31, y + 1.9)],
                gold,
                254 * opacity,
            )
            brush.gem(x, y + .95, max(.44, size * .24), 1.0, (255, 231, 155), 235 * opacity)
        else:
            brush.gem(x, y, size * 1.44 + .4, size * 1.64 + .4, dark, 221 * opacity)
            brush.gem(x, y - .15, size * .96, size * 1.10, red, 255 * opacity)
            brush.gem(x - .2, y - .42, size * .49, size * .66, gold, 249 * opacity)
    return brush.finish((255, 129, 63), 1, (2.05, .79), (4, .40))


TONIC_CROSSES = [
    ((-12, -29), (15, -47), (1, -84)),
    ((-17, -47), (10, -70), (-21, -108)),
    ((8, -65), (-23, -100), (11, -120), (-13, -149)),
    ((-24, -113), (11, -132), (-14, -160), (14, -178)),
    ((-7, -143), (-21, -169), (18, -188), (1, -202)),
    ((-18, -157), (4, -181), (-13, -195)),
]


def draw_tonic(frame):
    brush = Brush(TONIC)
    y = (0, -34, -74, -116, -159, -199)[frame]
    rx = (20, 29, 39, 48, 55, 60)[frame]
    ry = 4.3 + rx * .087
    mint, lime, pale, pine = (118, 252, 155), (173, 255, 190), (229, 255, 217), (20, 101, 57)
    strength = (1, .96, 1, 1, .93, .66)[frame]

    def arc(start, end):
        return [
            (math.cos(start + (end - start) * step / 60) * rx,
             y + math.sin(start + (end - start) * step / 60) * ry)
            for step in range(61)
        ]

    rear, front = arc(math.pi, math.tau), arc(0, math.pi)
    brush.line(rear, pine, 156 * strength, 3.2)
    brush.line(rear, mint, 155 * strength, 1.55)
    brush.line(front, pine, 189 * strength, 4.2)
    brush.line(front, mint, 240 * strength, 2.45)
    brush.line(arc(.22, 2.90), pale, 245 * strength, 1.1)

    rng = random.Random(311)
    for index in range(24):
        offset = rng.random()
        reach = rng.uniform(.26, 1)
        tail = rng.uniform(4, 24)
        size = rng.uniform(.55, 1.55)
        angle = math.tau * (offset + frame * .09)
        x = math.cos(angle) * rx * reach
        py = y + math.sin(angle) * ry + tail * (.22 + .65 * frame / 5) - 7
        fade = (.47 + .53 * math.sin(math.pi * (offset + frame * .21) % math.pi)) * strength
        brush.gem(x, py, size * .72, size * 1.22, mint, (160 + 12 * (index % 5)) * fade)
        if index % 4 == 0:
            brush.dot(x, py, .54, pale, 222 * fade)

    for index, (x, cy) in enumerate(TONIC_CROSSES[frame]):
        size = (2.6, 3.1, 3.55, 2.85)[(index + frame) % 4]
        opacity = (185 + ((index + frame * 2) % 4) * 18) * strength
        for span, width, color in ((size + .65, 1.23, pine), (size, .76, lime)):
            points = [
                (-width, -span), (width, -span), (width, -width), (span, -width),
                (span, width), (width, width), (width, span), (-width, span),
                (-width, width), (-span, width), (-span, -width), (-width, -width),
            ]
            brush.polygon([(x + dx, cy + dy) for dx, dy in points], color, opacity)
        brush.dot(x, cy, .45, pale, opacity)
    return brush.finish((123, 243, 161), .96, (2.4, .78), (5.4, .65))


def tonic_mask():
    left, top, right, bottom = TONIC
    pixels = []
    for y in range(top, bottom):
        for x in range(left, right):
            px, py = x + .5, y + .5
            shell = (abs(px) / 114.5) ** 3.15 + (abs(py + 104) / 128) ** 3.15
            pixels.append(round(255 * (clamp((69 - abs(px)) / 5) * clamp((.67 - shell) / .085))))
    mask = Image.new("L", size_of(TONIC))
    mask.putdata(pixels)
    return mask


def frame_sequence(draw, bounds, mask=None):
    width, height = size_of(bounds)
    frames = []
    for index in range(FRAME_COUNT):
        image = draw(index)
        alpha = image.getchannel("A")
        if mask is not None:
            alpha = ImageChops.multiply(alpha, mask)
        alpha = alpha.point(lambda value: value if value >= 4 else 0)
        padded = Image.new("L", image.size)
        padded.paste(alpha.crop((3, 3, width - 3, height - 3)), (3, 3))
        image.putalpha(padded)
        frame = Image.new("RGBA", CANVAS_SIZE)
        frame.paste(image, location(bounds))
        frames.append(frame)
    return frames


def occupied_pixels(*sequences):
    occupied = Image.new("L", CANVAS_SIZE)
    for frames in sequences:
        for frame in frames:
            occupied = ImageChops.lighter(occupied, frame.getchannel("A"))
    return occupied.point(lambda alpha: 255 if alpha else 0)


def clear_area(bounds, *sequences):
    occupied = occupied_pixels(*sequences)
    feather = occupied.filter(ImageFilter.MaxFilter(3)).filter(ImageFilter.GaussianBlur(1.35))
    x, y = location(bounds)
    width, height = size_of(bounds)
    return ImageChops.invert(ImageChops.lighter(occupied, feather)).crop((x, y, x + width, y + height))


def build_frames():
    tonic = frame_sequence(draw_tonic, TONIC, tonic_mask())
    fury = frame_sequence(draw_fury_at_feet, FURY)
    shield = frame_sequence(draw_shield, SHIELD, clear_area(SHIELD, tonic, fury))
    purity = frame_sequence(draw_purity, PURITY, clear_area(PURITY, shield, tonic, fury))

    # Reuse the same upper particle layer as the V5 GIF.
    rising_bounds = (LEFT, TOP, RIGHT, BOTTOM)
    x, y = location(rising_bounds)
    width, height = size_of(rising_bounds)
    blocked = occupied_pixels(shield, purity, fury).crop((x, y, x + width, y + height))
    allowed = ImageChops.invert(blocked)
    for index, frame in enumerate(fury):
        frame.alpha_composite(render_rising_embers(index, allowed), (x, y))

    return {
        "sacred_shield": (4, shield),
        "purity_seal": (4, purity),
        "fury_unbound": (5, fury),
        "vitality_tonic": (3, tonic),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=OUTPUT, help="Folder for the four skill directories")
    args = parser.parse_args()
    for skill, (version, frames) in build_frames().items():
        folder = args.output / skill
        folder.mkdir(parents=True, exist_ok=True)
        for index, frame in enumerate(frames):
            frame.save(folder / f"{skill}_v{version}_{index:02}.png", optimize=True)
        print(f"{folder}: {len(frames)} frames")


if __name__ == "__main__":
    main()
