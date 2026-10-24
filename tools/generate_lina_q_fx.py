"""Build Lina Q sprite-projectile frames and approval previews from textures.

Normal uses the supplied teal glass-ball texture only (no procedural ball and no
code-drawn trail). Flame uses the Seedream pixel-art fire orb plus a short trail.
This tool never copies anything into ``assets/frames``. It writes candidates and
contact sheets under ``assets/generated/contact_sheets/``; the approved frames
are copied to the runtime directory after review.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "assets" / "generated" / "contact_sheets" / "lina_q_fx_v1"
FRAME_COUNT = 1
FRAME_SIZE = 96
ANCHOR = (64, 48)
ORB_DIAMETERS = {"normal": 26, "flame": 32}
PIXEL_BLOCK = 2
DURATIONS = [0.06] * FRAME_COUNT

FLAME_PALETTE = {
    "trail": (255, 170, 90),
    "trail_alt": (255, 90, 40),
    "ring": (255, 220, 140),
    "spark": (255, 245, 200),
}

TEAL_PALETTE = {
    "trail": (80, 230, 225),
    "trail_alt": (35, 165, 175),
    "ring": (220, 250, 248),
    "spark": (245, 255, 253),
}


def _font(size: int):
    try:
        return ImageFont.truetype("arial.ttf", size)
    except Exception:  # noqa: BLE001
        return ImageFont.load_default()


def _checkerboard(size: tuple[int, int], tile: int = 8) -> Image.Image:
    board = Image.new("RGB", size, (62, 64, 74))
    draw = ImageDraw.Draw(board)
    for y in range(0, size[1], tile):
        for x in range(0, size[0], tile):
            if (x // tile + y // tile) % 2:
                draw.rectangle(
                    [x, y, x + tile - 1, y + tile - 1], fill=(82, 84, 96)
                )
    return board


def _corner_luminance(rgb: Image.Image) -> float:
    width, height = rgb.size
    points = (
        (0, 0), (width - 1, 0), (0, height - 1), (width - 1, height - 1),
        (width // 2, 0), (width // 2, height - 1),
        (0, height // 2), (width - 1, height // 2),
    )
    values = []
    pixels = rgb.load()
    for x, y in points:
        r, g, b = pixels[x, y]
        values.append((r + g + b) / 3.0)
    return sum(values) / len(values)


def _connected_mask(
    rgb: Image.Image, near_black: bool, corner_luminance: float
) -> Image.Image:
    """Mask of background-coloured pixels connected to the image border."""
    width, height = rgb.size
    mask = Image.new("L", (width, height), 0)
    source = rgb.load()
    target = mask.load()
    dark_limit = max(8, int(corner_luminance + 10))
    for y in range(height):
        for x in range(width):
            r, g, b = source[x, y]
            if near_black:
                if max(r, g, b) <= dark_limit:
                    target[x, y] = 255
            else:
                if min(r, g, b) >= 185 and max(r, g, b) - min(r, g, b) <= 45:
                    target[x, y] = 255
    corners = (
        (0, 0), (width - 1, 0), (0, height - 1), (width - 1, height - 1),
        (width // 2, 0), (width // 2, height - 1),
        (0, height // 2), (width - 1, height // 2),
    )
    for seed in corners:
        if mask.getpixel(seed) == 255:
            ImageDraw.floodfill(mask, seed, 128, thresh=0)
    return mask


def key_background(image: Image.Image) -> Image.Image:
    """Turn a black (or fallback white/checker) render into a clean RGBA glow."""
    rgba = image.convert("RGBA")
    alpha = rgba.getchannel("A")
    if alpha.getextrema()[0] < 250:
        # The generator already returned transparency; just trim the halo.
        return rgba

    rgb = rgba.convert("RGB")
    corner_luminance = _corner_luminance(rgb)
    if 110.0 < corner_luminance < 185.0:
        raise ValueError(
            "Ambiguous background luminance "
            f"({corner_luminance:.0f}); regenerate on pure black"
        )
    near_black = corner_luminance <= 110.0
    mask = _connected_mask(
        rgb, near_black=near_black, corner_luminance=corner_luminance
    )
    mask_pixels = mask.load()
    rgb_pixels = rgb.load()
    result = Image.new("RGBA", rgba.size, (0, 0, 0, 0))
    out = result.load()
    width, height = rgba.size
    for y in range(height):
        for x in range(width):
            r, g, b = rgb_pixels[x, y]
            if mask_pixels[x, y] == 128:
                continue
            value = max(r, g, b)
            if near_black:
                if value <= 6:
                    continue
                alpha_value = min(255, round(value * 255 / 235))
                # Unpremultiply so the glow keeps its hue instead of going grey.
                scale = 255.0 / max(1, value)
                nr = min(255, round(r * scale))
                ng = min(255, round(g * scale))
                nb = min(255, round(b * scale))
            else:
                if min(r, g, b) >= 240 and max(r, g, b) - min(r, g, b) <= 12:
                    continue
                alpha_value = 255
                nr, ng, nb = r, g, b
            out[x, y] = (nr, ng, nb, alpha_value)
    alpha = result.getchannel("A").filter(ImageFilter.GaussianBlur(0.5))
    result.putalpha(alpha)
    return result


def _crop_to_alpha(image: Image.Image) -> Image.Image:
    bounds = image.getchannel("A").point(
        lambda value: 255 if value > 8 else 0
    ).getbbox()
    if bounds is None:
        raise ValueError("Source image has no visible pixels after keying")
    return image.crop(bounds)


def normalize_orb(
    image: Image.Image, orb_diameter: int = ORB_DIAMETERS["normal"]
) -> Image.Image:
    """Crop the orb and center its full glow on the runtime anchor."""
    cropped = _crop_to_alpha(image)
    scale = orb_diameter / max(1.0, float(max(cropped.width, cropped.height)))
    target_size = (
        max(1, round(cropped.width * scale)),
        max(1, round(cropped.height * scale)),
    )
    scaled = cropped.resize(target_size, Image.Resampling.LANCZOS)
    canvas = Image.new("RGBA", (FRAME_SIZE, FRAME_SIZE), (0, 0, 0, 0))
    paste_x = round(ANCHOR[0] - scaled.width * 0.5)
    paste_y = round(ANCHOR[1] - scaled.height * 0.5)
    canvas.alpha_composite(scaled, (paste_x, paste_y))
    return canvas


def compose_frame(
    orb: Image.Image, index: int, palette: dict, count: int = FRAME_COUNT
) -> Image.Image:
    """One static pixel-art frame; ``index`` is kept for future frame counts."""
    frame = Image.new("RGBA", (FRAME_SIZE, FRAME_SIZE), (0, 0, 0, 0))
    frame.alpha_composite(orb, (0, 0))
    draw = ImageDraw.Draw(frame)
    for trail_index in range(4):
        distance = 20.0 + trail_index * 7.0
        size = max(2.0, 5.0 - trail_index * 1.0)
        alpha = max(28, 140 - trail_index * 30)
        color = palette["trail"] if trail_index % 2 == 0 else palette["trail_alt"]
        cx = ANCHOR[0] - distance
        cy = ANCHOR[1] + (trail_index % 2) * 2.0 - 1.0
        draw.rectangle(
            (cx - size * 0.5, cy - size * 0.5, cx + size * 0.5, cy + size * 0.5),
            fill=(*color, alpha),
        )
    # Enforce a visible pixel grid matching the character's pixel-art style.
    logical = frame.resize(
        (FRAME_SIZE // PIXEL_BLOCK, FRAME_SIZE // PIXEL_BLOCK),
        Image.Resampling.NEAREST,
    )
    return logical.resize((FRAME_SIZE, FRAME_SIZE), Image.Resampling.NEAREST)


def build_variant(source: Path, variant: str, out_dir: Path) -> dict:
    orb_diameter = ORB_DIAMETERS[variant]
    raw = Image.open(source)
    keyed = key_background(raw)
    orb = normalize_orb(keyed, orb_diameter)
    frame_dir = out_dir / variant
    frame_dir.mkdir(parents=True, exist_ok=True)
    frames = []
    palette = TEAL_PALETTE if variant == "normal" else FLAME_PALETTE
    for index in range(FRAME_COUNT):
        # Pixelate the supplied texture to match the character art and add a
        # short trail; the normal form has no procedural ball.
        frame = compose_frame(orb, index, palette)
        path = frame_dir / f"q_wave_{index:02d}.png"
        frame.save(path)
        frames.append(frame)
    return {
        "source": str(source),
        "variant": variant,
        "frames_dir": str(frame_dir),
        "frames": [f"q_wave_{index:02d}.png" for index in range(FRAME_COUNT)],
        "durations": DURATIONS,
        "frame_size": [FRAME_SIZE, FRAME_SIZE],
        "anchor": list(ANCHOR),
        "orb_diameter": orb_diameter,
        "trail": True,
    }


def write_preview(out_dir: Path, entries: list[dict]) -> None:
    cell = FRAME_SIZE
    zoom = 2
    pad = 16
    header = 34
    label_height = 22
    rows = len(entries)
    width = max(720, pad + (cell + pad) + (cell * zoom + pad))
    height = header + rows * (cell * zoom + label_height + pad) + pad
    sheet = Image.new("RGB", (width, height), (25, 27, 35))
    draw = ImageDraw.Draw(sheet)
    title_font = _font(20)
    label_font = _font(13)
    draw.text(
        (pad, 8), "Lina Q projectile - review",
        fill=(238, 238, 246), font=title_font,
    )

    for row, entry in enumerate(entries):
        y = header + row * (cell * zoom + label_height + pad)
        frame = Image.open(
            Path(entry["frames_dir"]) / entry["frames"][0]
        ).convert("RGBA")
        board = _checkerboard((cell, cell))
        board.paste(frame, (0, 0), frame)
        overlay = ImageDraw.Draw(board)
        overlay.line([(0, ANCHOR[1]), (cell, ANCHOR[1])], fill=(255, 210, 80), width=1)
        overlay.line([(ANCHOR[0], 0), (ANCHOR[0], cell)], fill=(120, 220, 255), width=1)

        native_panel = Image.new("RGB", (cell * zoom, cell * zoom), (25, 27, 35))
        native_panel.paste(board, ((cell * zoom - cell) // 2, (cell * zoom - cell) // 2))
        sheet.paste(native_panel, (pad, y))

        zoom_board = _checkerboard((cell, cell))
        zoom_board.paste(frame, (0, 0), frame)
        zoom_board = zoom_board.resize(
            (cell * zoom, cell * zoom), Image.Resampling.NEAREST
        )
        sheet.paste(zoom_board, (pad + cell * zoom + pad, y))
        draw.text((pad + 4, y + 4), "1x", fill=(210, 214, 224), font=label_font)
        draw.text(
            (pad + cell * zoom + pad + 4, y + 4), "2x",
            fill=(210, 214, 224), font=label_font,
        )

        draw.text(
            (pad, y + cell * zoom + 4),
            f"{entry['variant']}   orb={entry['orb_diameter']}px   "
            f"anchor={entry['anchor']}   {Path(entry['source']).name}",
            fill=(225, 225, 235), font=label_font,
        )
    sheet.save(out_dir / "lina_q_fx_v1.png")
    print(out_dir / "lina_q_fx_v1.png")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--normal", type=Path, required=True)
    parser.add_argument("--flame", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, default=OUT)
    args = parser.parse_args()

    args.out_dir.mkdir(parents=True, exist_ok=True)
    entries = []
    for variant, source in (("normal", args.normal), ("flame", args.flame)):
        if not source.exists():
            print(f"ERROR missing {variant} source: {source}")
            return 1
        entries.append(build_variant(source, variant, args.out_dir))
    write_preview(args.out_dir, entries)
    manifest = {
        "tool": "generate_lina_q_fx.py",
        "frame_count": FRAME_COUNT,
        "frame_size": [FRAME_SIZE, FRAME_SIZE],
        "anchor": list(ANCHOR),
        "orb_diameters": ORB_DIAMETERS,
        "variants": entries,
    }
    (args.out_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
