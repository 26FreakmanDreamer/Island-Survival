"""Build review-only lightning ignition frames, sheets, and previews.

The generated sparks introduce the existing v1 flash and bolt.  Source alpha is
retained; the sequence never uses an opacity ramp or a crossfade.
"""

from __future__ import annotations

import hashlib
import json
import math
import shutil
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "assets/generated/contact_sheets/crooked_witch_lightning_fx"
STEM = "crooked_witch_lightning_fx_v2"
CANVAS = (1400, 1400)
PIVOT = (300, 700)
INTRO_EDGES = (44, 86, 130)
DURATIONS = (60, 60, 60, 80, 100, 100)
STAGES = (
    "ignition spark", "gathering arcs", "compressed discharge",
    "staff-tip flash", "flash and full bolt", "fading bolt",
)
BACKGROUND = (31, 28, 43)
FOREGROUND = (239, 234, 246)
WORLD_BOUNDS = (280, -460, 2400, 1470)


def font(size: int) -> ImageFont.ImageFont:
    for path in ("C:/Windows/Fonts/segoeui.ttf", "C:/Windows/Fonts/arial.ttf"):
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            pass
    return ImageFont.load_default()


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def open_rgba(path: Path) -> Image.Image:
    with Image.open(path) as source:
        return source.convert("RGBA")


def check_frame(frame: Image.Image, name: str) -> None:
    if frame.size != CANVAS or frame.mode != "RGBA":
        raise ValueError(f"Unexpected FX canvas or color mode: {name}")
    alpha = frame.getchannel("A")
    bounds = alpha.getbbox()
    if bounds is None:
        raise ValueError(f"Empty FX frame: {name}")
    if bounds[0] <= 0 or bounds[1] <= 0 or bounds[2] >= CANVAS[0] or bounds[3] >= CANVAS[1]:
        raise ValueError(f"FX touches a canvas edge: {name}, {bounds}")
    if alpha.getextrema()[0] != 0:
        raise ValueError(f"FX has no fully transparent pixels: {name}")


def core_anchor(image: Image.Image) -> tuple[float, float]:
    """Find the alpha-weighted near-white core within the central half.

    Keeping the search central excludes the scattered end sparks.  A strong
    whiteness weighting selects the luminous nucleus rather than purple glow.
    """
    pixels = image.load()
    width, height = image.size
    x0, x1 = int(width * 0.25), max(1, math.ceil(width * 0.75))
    y0, y1 = int(height * 0.25), max(1, math.ceil(height * 0.75))
    stride = max(1, max(width, height) // 900)
    total = x_total = y_total = 0.0
    for y in range(y0, y1, stride):
        for x in range(x0, x1, stride):
            r, g, b, alpha = pixels[x, y]
            white = min(r, g, b)
            if alpha < 128 or white < 205:
                continue
            weight = alpha * (white - 180) ** 4
            total += weight
            x_total += x * weight
            y_total += y * weight
    if total == 0:
        raise ValueError("Generated source has no opaque near-white central core")
    return x_total / total, y_total / total


def intro_frame(path: Path, edge: int) -> tuple[Image.Image, dict]:
    source = open_rgba(path)
    alpha = source.getchannel("A")
    visible_bounds = alpha.point(lambda value: 255 if value >= 8 else 0).getbbox()
    if visible_bounds is None or alpha.getextrema()[0] != 0:
        raise ValueError(f"Source must contain artwork on true transparency: {path}")
    # Faint remote alpha specks should not shrink the visible spark.  This mask
    # chooses crop coordinates only; the cropped source alpha remains unchanged.
    bounds = (
        max(0, visible_bounds[0] - 8), max(0, visible_bounds[1] - 8),
        min(source.width, visible_bounds[2] + 8), min(source.height, visible_bounds[3] + 8),
    )
    cropped = source.crop(bounds)
    anchor = core_anchor(cropped)
    scale = edge / max(cropped.size)
    size = tuple(max(1, round(length * scale)) for length in cropped.size)
    resized = cropped.resize(size, Image.Resampling.LANCZOS)
    scaled_anchor = (anchor[0] * size[0] / cropped.width, anchor[1] * size[1] / cropped.height)
    position = (round(PIVOT[0] - scaled_anchor[0]), round(PIVOT[1] - scaled_anchor[1]))
    frame = Image.new("RGBA", CANVAS)
    # Paste without a mask: using source alpha as a mask would multiply it twice.
    frame.paste(resized, position)
    check_frame(frame, path.name)
    return frame, {
        "source": str(path),
        "source_sha256": sha256(path),
        "source_alpha_bbox": list(bounds),
        "crop_visible_alpha_threshold": 8,
        "crop_margin_px": 8,
        "core_in_cropped_source": [round(value, 4) for value in anchor],
        "placed_core": [round(position[i] + scaled_anchor[i], 4) for i in range(2)],
        "resized_size": list(size),
        "max_edge_px": edge,
        "alpha": "native generated alpha, resampling only; no opacity ramp",
    }


def checker(size: tuple[int, int], tile: int = 16) -> Image.Image:
    board = Image.new("RGBA", size, (44, 42, 54, 255))
    draw = ImageDraw.Draw(board)
    for y in range(0, size[1], tile):
        for x in range(0, size[0], tile):
            if (x // tile + y // tile) % 2:
                draw.rectangle((x, y, x + tile - 1, y + tile - 1), fill=(57, 54, 68, 255))
    return board


def scene_image(actor: Image.Image, tip: tuple[int, int], fx: Image.Image | None,
                direction: str, stage: str, size: tuple[int, int] = (600, 600)) -> Image.Image:
    """Use one shared world crop/scale for every actor and direction."""
    board = Image.new("RGBA", size, (*BACKGROUND, 255))
    left, top, right, bottom = WORLD_BOUNDS
    scale = min((size[0] - 20) / (right - left), (size[1] - 78) / (bottom - top))
    offset = (10 - left * scale, 64 - top * scale)
    actor_size = tuple(round(value * scale) for value in actor.size)
    rendered_actor = actor.resize(actor_size, Image.Resampling.LANCZOS)
    board.alpha_composite(rendered_actor, (round(offset[0]), round(offset[1])))
    if fx is not None:
        effect_size = tuple(round(value * scale) for value in CANVAS)
        rendered_fx = fx.resize(effect_size, Image.Resampling.LANCZOS)
        effect_position = (
            round(offset[0] + (tip[0] - PIVOT[0]) * scale),
            round(offset[1] + (tip[1] - PIVOT[1]) * scale),
        )
        board.alpha_composite(rendered_fx, effect_position)
    draw = ImageDraw.Draw(board)
    draw.text((14, 10), f"{direction.upper()} | LIGHTNING v2", font=font(21), fill=FOREGROUND)
    draw.text((14, 38), stage, font=font(17), fill=(198, 185, 222))
    return board.convert("RGB")


def detail_image(actor: Image.Image, tip: tuple[int, int], fx: Image.Image,
                 size: int = 340) -> Image.Image:
    """Show every tip detail at the same native 1:1 source scale."""
    half = size // 2
    board = checker((size, size))
    actor_crop = actor.crop((tip[0] - half, tip[1] - half, tip[0] - half + size, tip[1] - half + size))
    fx_crop = fx.crop((PIVOT[0] - half, PIVOT[1] - half, PIVOT[0] - half + size, PIVOT[1] - half + size))
    board.alpha_composite(actor_crop)
    board.alpha_composite(fx_crop)
    return board.convert("RGB")


def contact_sheet(directions: dict, frames: dict[str, list[Image.Image]], actors: dict) -> Path:
    width, height, gap, heading = 360, 408, 12, 76
    board = Image.new("RGB", (gap + 6 * (width + gap), heading + 3 * (height + gap)), BACKGROUND)
    draw = ImageDraw.Draw(board)
    draw.text((gap, 9), "CROOKED WITCH LIGHTNING v2 | 3 generated intro frames + unchanged v1", font=font(27), fill=FOREGROUND)
    draw.text((gap, 44), "00-02: crystal-tip detail at 1:1  |  03-05: shared full-view scale  |  no fade-in", font=font(20), fill=(201, 188, 220))
    for row, (direction, info) in enumerate(directions.items()):
        actor, tip = actors[direction], tuple(info["crystal_tip_on_actor"])
        for index, fx in enumerate(frames[direction]):
            x, y = gap + index * (width + gap), heading + row * (height + gap)
            if index < 3:
                cell = detail_image(actor, tip, fx, width)
            else:
                cell = scene_image(actor, tip, fx, direction, STAGES[index], (width, width))
            board.paste(cell, (x, y))
            draw.text((x + 5, y + width + 5), f"{direction} {index:02d} | {DURATIONS[index]} ms", font=font(18), fill=FOREGROUND)
            draw.text((x + 5, y + width + 28), STAGES[index], font=font(16), fill=(192, 178, 216))
    path = OUT / f"{STEM}_sheet.png"
    board.save(path)
    return path


def intro_sheet(directions: dict, frames: dict[str, list[Image.Image]]) -> Path:
    size, gap, heading, label = 256, 12, 74, 42
    board = Image.new("RGB", (gap + 4 * (size + gap), heading + 3 * (size + label + gap)), BACKGROUND)
    draw = ImageDraw.Draw(board)
    draw.text((gap, 10), "LIGHTNING v2 | FX ONLY | NATIVE 1:1 TIP CROP", font=font(25), fill=FOREGROUND)
    draw.text((gap, 43), "Fixed pivot and crop; all artwork shown without alpha fading", font=font(19), fill=(201, 188, 220))
    for row, direction in enumerate(directions):
        for index in range(4):
            x, y = gap + index * (size + gap), heading + row * (size + label + gap)
            half = size // 2
            crop = frames[direction][index].crop((PIVOT[0] - half, PIVOT[1] - half, PIVOT[0] + half, PIVOT[1] + half))
            cell = checker((size, size))
            cell.alpha_composite(crop)
            board.paste(cell.convert("RGB"), (x, y))
            draw.text((x + 5, y + size + 6), f"{direction} {index:02d} | {DURATIONS[index]} ms", font=font(17), fill=FOREGROUND)
    path = OUT / f"{STEM}_intro_sheet.png"
    board.save(path)
    return path


def save_preview(path: Path, images: list[Image.Image], durations: list[int]) -> None:
    images[0].save(path, save_all=True, append_images=images[1:], duration=durations,
                   loop=0, optimize=False, disposal=2)
    with Image.open(path) as result:
        if result.size != (1800, 600) or result.n_frames != len(images):
            raise ValueError(f"Unexpected preview dimensions/frame count: {path}")
        actual = []
        for index in range(result.n_frames):
            result.seek(index)
            actual.append(result.info.get("duration"))
        if actual != durations:
            raise ValueError(f"Preview timing changed: {actual} != {durations}")


def previews(directions: dict, frames: dict[str, list[Image.Image]], actors: dict) -> list[Path]:
    sequence: list[int | None] = [None, 0, 1, 2, 3, 4, 5, None]
    images = []
    for index in sequence:
        board = Image.new("RGB", (1800, 600), BACKGROUND)
        for column, (direction, info) in enumerate(directions.items()):
            step = "actor-only pause" if index is None else f"{index:02d} | {STAGES[index]} | {DURATIONS[index]} ms"
            cell = scene_image(actors[direction], tuple(info["crystal_tip_on_actor"]),
                               None if index is None else frames[direction][index], direction, step)
            board.paste(cell, (column * 600, 0))
        images.append(board)
    full_speed = OUT / f"{STEM}_preview.gif"
    timings = [300, *DURATIONS, 400]
    save_preview(full_speed, images, timings)
    slow_images = []
    for frame in images:
        slow = frame.copy()
        ImageDraw.Draw(slow).text((14, 574), "SLOW REVIEW: 3x duration", font=font(18), fill=(255, 213, 144))
        slow_images.append(slow)
    slow_path = OUT / f"{STEM}_slow_preview.gif"
    save_preview(slow_path, slow_images, [duration * 3 for duration in timings])
    return [full_speed, slow_path]


def main() -> None:
    sources = [OUT / f"{STEM}_intro_{index:02d}_source.png" for index in range(3)]
    missing = [str(path) for path in sources if not path.is_file()]
    if missing:
        raise FileNotFoundError("Generate all three intro sources first:\n" + "\n".join(missing))
    old_paths = sorted(OUT.glob("crooked_witch_lightning_fx_v1_*"))
    old_hashes = {path: sha256(path) for path in old_paths if path.is_file()}
    old_manifest = json.loads((OUT / "crooked_witch_lightning_fx_v1_sheet.json").read_text(encoding="utf-8"))
    directions = old_manifest["directions"]
    generated = [intro_frame(path, edge) for path, edge in zip(sources, INTRO_EDGES)]
    frames: dict[str, list[Image.Image]] = {}
    actors: dict[str, Image.Image] = {}
    result_directions = {}
    for direction, info in directions.items():
        angle = info["angle_degrees"]
        introductions = [frame.copy() if angle == 0 else frame.rotate(angle, Image.Resampling.BICUBIC, center=PIVOT)
                         for frame, _ in generated]
        frame_paths = []
        direction_frames = introductions[:]
        for index, frame in enumerate(introductions):
            path = OUT / f"{STEM}_{direction}_{index:02d}.png"
            check_frame(frame, path.name)
            frame.save(path)
            frame_paths.append(str(path))
        for old_index, original in enumerate(info["frames"]):
            original_path = Path(original)
            path = OUT / f"{STEM}_{direction}_{old_index + 3:02d}.png"
            shutil.copyfile(original_path, path)
            if sha256(path) != old_hashes[original_path]:
                raise ValueError(f"Original FX frame was altered: {path}")
            frame = open_rgba(path)
            check_frame(frame, path.name)
            direction_frames.append(frame)
            frame_paths.append(str(path))
        frames[direction] = direction_frames
        actors[direction] = open_rgba(Path(info["release_actor"]))
        result_directions[direction] = {
            **info,
            "frames": frame_paths,
            "source_mapping": [
                {"frame": index, "source": str(sources[index]), "rotation_degrees": angle}
                for index in range(3)
            ] + [
                {"frame": index + 3, "source": original, "unchanged_copy": True}
                for index, original in enumerate(info["frames"])
            ],
        }
    sheet_path = contact_sheet(directions, frames, actors)
    intro_sheet_path = intro_sheet(directions, frames)
    preview_paths = previews(directions, frames, actors)
    manifest = {
        "title": "Crooked Witch lightning VFX v2 / generated ignition introduction",
        "status": "pending_user_review",
        "runtime_integrated": False,
        "transparent_canvas": list(CANVAS),
        "effect_pivot": list(PIVOT),
        "stages": list(STAGES),
        "duration_ms": list(DURATIONS),
        "fade_in": False,
        "crossfade": False,
        "fade_out": "unchanged v1 fading-bolt frame",
        "intro_processing": [detail for _, detail in generated],
        "directions": result_directions,
        "sheet": str(sheet_path),
        "intro_sheet": str(intro_sheet_path),
        "preview": str(preview_paths[0]),
        "slow_preview": str(preview_paths[1]),
        "preview_pause_ms": [300, 400],
        "preview_actor_scale": "one common scale and world crop for all directions; no per-direction normalization",
        "preserved_v1_sha256": {path.name: digest for path, digest in old_hashes.items()},
    }
    manifest_path = OUT / f"{STEM}_sheet.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    for path, digest in old_hashes.items():
        if sha256(path) != digest:
            raise ValueError(f"v1 asset changed during build: {path}")
    for path in [sheet_path, intro_sheet_path, *preview_paths, manifest_path]:
        print(path)
    print(f"Verified 18 transparent frames, full/slow timing, and {len(old_hashes)} unchanged v1 assets.")


if __name__ == "__main__":
    main()
