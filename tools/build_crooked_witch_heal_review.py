"""Render review-only heal v5 + FX v2, using unchanged source artwork."""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "assets/generated/contact_sheets"
HEAL, FX, FLY = (BASE / f"crooked_witch_{name}" for name in ("heal", "heal_fx", "fly"))
STEM = "crooked_witch_heal_v5_fx_v2"
SEQUENCE = ROOT / "tmp" / f"{STEM}_frames"
STEP_MS = 50
BG = (30, 28, 43)
FLOAT_OFFSET = (280, 0)
HELD_OFFSET = (-11, -2)
HELD_ANGLE = -4.0
PROP_CENTER = (757.5, 1137.2)


def font(size: int) -> ImageFont.ImageFont:
    return ImageFont.truetype("C:/Windows/Fonts/segoeui.ttf", size)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def visible_bounds(image: Image.Image) -> tuple[int, int, int, int]:
    bounds = image.getchannel("A").point(lambda a: 255 if a >= 16 else 0).getbbox()
    if bounds is None:
        raise ValueError("Empty source image")
    return bounds


def mix(a: tuple, b: tuple, t: float) -> tuple[float, float]:
    t = (1 - math.cos(math.pi * t)) / 2
    return tuple(a[i] + (b[i] - a[i]) * t for i in range(2))


def timeline() -> list[dict]:
    frames: list[dict] = []

    def add(stage: str, actor: str, position: tuple, prop: float | None = None,
            fx: int | None = None, pulse: int | None = None) -> None:
        frames.append(dict(stage=stage, actor=actor, position=list(position),
                           prop_float_progress=prop, fx=fx, pulse=pulse))

    start, center = (70, 206), (470, 115)
    for _ in range(6):
        add("Ready", "fly5", start)
    for index in (0, 1):
        for _ in range(4):
            add("Take off", f"fly{index}", start)
    for i in range(24):
        add("Fly to center", f"fly{2 + (i // 4) % 2}", mix(start, center, (i + 1) / 24))
    for index in range(3):
        for tick in range(4):
            add(("Release staff", "Open hands", "Prepare healing")[index],
                f"heal{index}", center, (tick + 1) / 4 if index == 0 else 1.0)
    for tick in range(100):
        add("Heal", f"heal{3 + (tick // 4) % 2}", center, 1.0, tick % 20, tick // 20 + 1)
    for tick in range(8):
        add("Staff returns", "heal3" if tick < 4 else "heal2", center, 1 - (tick + 1) / 8)
    for _ in range(4):
        add("Regrip staff", "heal5", center)
    for tick in range(24):
        add("Fly back", f"fly{3 - (tick // 4) % 2}", mix(center, start, (tick + 1) / 24))
    for index in (4, 5):
        for _ in range(4):
            add("Land", f"fly{index}", start)
    for _ in range(10):
        add("Complete", "fly5", start)
    assert len(frames) == 204
    assert [f["fx"] for f in frames if f["fx"] is not None] == list(range(20)) * 5
    return frames


class Renderer:
    def __init__(self, sprites: dict[str, Image.Image], size: tuple, scale: float, detail=False):
        self.sprites, self.size, self.scale, self.detail = sprites, size, scale, detail
        self.cache: dict[tuple, Image.Image] = {}

    def sprite(self, name: str, progress: float | None = None) -> Image.Image:
        key = (name, progress)
        if key not in self.cache:
            image = self.sprites[name]
            if name == "prop":
                image = image.rotate(HELD_ANGLE * (1 - progress), Image.Resampling.BICUBIC,
                                     center=PROP_CENTER)
            self.cache[key] = image.resize(tuple(round(n * self.scale) for n in image.size),
                                           Image.Resampling.LANCZOS)
        return self.cache[key]

    def render(self, event: dict, index: int, total: int) -> Image.Image:
        board = Image.new("RGBA", self.size, (*BG, 255))
        origin = (110, 100) if self.detail else event["position"]

        def place(name: str, offset=(0, 0), progress=None) -> None:
            image = self.sprite(name, progress)
            pos = tuple(round(origin[i] + offset[i] * self.scale) for i in range(2))
            bounds = visible_bounds(image)
            actual = tuple(bounds[i] + pos[i % 2] for i in range(4))
            if actual[0] < 0 or actual[1] < 88 or actual[2] > self.size[0] or actual[3] > self.size[1] - 20:
                raise ValueError(f"Clipped visible art: {name} / {event['stage']} / {actual}")
            board.alpha_composite(image, pos)

        place(event["actor"])
        progress = event["prop_float_progress"]
        if progress is not None:
            offset = tuple(HELD_OFFSET[i] + (FLOAT_OFFSET[i] - HELD_OFFSET[i]) * progress for i in range(2))
            place("prop", offset, progress)
        if event["fx"] is not None:
            place(f"fx{event['fx']}")
        draw = ImageDraw.Draw(board)
        draw.text((24, 14), "CROOKED WITCH | HEAL v5 + FX v2", font=font(25), fill=(242, 235, 247))
        stage = event["stage"] + (f" | pulse {event['pulse']} / 5" if event["pulse"] else "")
        draw.text((24, 50), stage, font=font(22), fill=(123, 215, 155))
        draw.text((self.size[0] - 142, 51), f"{index * .05:05.2f}s / {total * .05:.2f}s", font=font(16), fill=(197, 190, 208))
        draw.line((24, self.size[1] - 12, self.size[0] - 24, self.size[1] - 12), fill=(64, 57, 79), width=3)
        end = 24 + round((self.size[0] - 48) * (index + 1) / total)
        draw.line((24, self.size[1] - 12, end, self.size[1] - 12), fill=(107, 192, 143), width=3)
        return board.convert("RGB")


def save_gif(path: Path, frames: list[Image.Image]) -> None:
    frames[0].save(path, save_all=True, append_images=frames[1:], duration=STEP_MS,
                   loop=0, disposal=2, optimize=False)
    with Image.open(path) as result:
        assert result.n_frames == len(frames) and result.size == frames[0].size
        durations = []
        for index in range(result.n_frames):
            result.seek(index)
            durations.append(result.info["duration"])
        assert durations == [STEP_MS] * len(frames), durations


def storyboard(path: Path, images: list[Image.Image], labels: list[str]) -> None:
    cell = (400, 300)
    board = Image.new("RGB", (1200, 4 * cell[1]), BG)
    draw = ImageDraw.Draw(board)
    for index, (image, label) in enumerate(zip(images, labels)):
        x, y = index % 3 * cell[0], index // 3 * cell[1]
        thumb = image.copy()
        thumb.thumbnail((400, 267), Image.Resampling.LANCZOS)
        board.paste(thumb, (x, y))
        draw.text((x + 8, y + 271), label, font=font(16), fill=(235, 226, 244))
    board.save(path)


def main() -> None:
    actor_manifest = json.loads((HEAL / "crooked_witch_heal_v5_manifest.json").read_text(encoding="utf-8"))
    fx_manifest = json.loads((FX / "crooked_witch_heal_fx_v2_manifest.json").read_text(encoding="utf-8"))
    assert fx_manifest["frame_duration_ms"] == STEP_MS and len(fx_manifest["frames"]) == 20
    assert fx_manifest["actor_canvas_offset"] == [0, 0]
    paths = {f"heal{i}": HEAL / name for i, name in enumerate(actor_manifest["source_frames"])}
    paths.update({f"fly{i}": FLY / f"crooked_witch_fly_v3_{i:02d}.png" for i in range(6)})
    paths.update({f"fx{i}": FX / name for i, name in enumerate(fx_manifest["frames"])})
    paths["prop"] = HEAL / actor_manifest["detached_staff_prop"]
    originals = {p: digest(p) for directory in (HEAL, FX, FLY) for p in directory.iterdir()
                 if p.is_file() and not p.name.startswith((STEM, "crooked_witch_heal_fx_v2"))}
    sprites = {}
    for key, path in paths.items():
        with Image.open(path) as source:
            image = source.convert("RGBA")
        assert image.size == (1254, 1254) and image.getchannel("A").getextrema()[0] == 0
        visible_bounds(image)
        sprites[key] = image
    assert paths["heal5"].read_bytes() == paths["fly3"].read_bytes(), "Regrip/flight seam differs"
    events = timeline()
    render = Renderer(sprites, (1200, 800), .43)
    samples = [0, 20, 37, 39, 45, 50, 67, 107, 147, 157, 175, 203]
    palette_board = Image.new("RGB", (1200, 800 * 3))
    for row, sample in enumerate((0, 67, 147)):
        palette_board.paste(render.render(events[sample], sample, len(events)), (0, row * 800))
    palette = palette_board.quantize(colors=256, method=Image.Quantize.MEDIANCUT)
    SEQUENCE.mkdir(parents=True, exist_ok=True)
    frames, selected = [], {}
    for index, event in enumerate(events):
        frame = render.render(event, index, len(events))
        frame.save(SEQUENCE / f"frame_{index:04d}.png")
        frames.append(frame.quantize(palette=palette, dither=Image.Dither.NONE))
        if index in samples:
            selected[index] = frame
    main_path = HEAL / f"{STEM}_complete_preview.gif"
    save_gif(main_path, frames)
    del frames
    storyboard(HEAL / f"{STEM}_complete_storyboard.png", [selected[i] for i in samples],
               [f"{i * .05:.2f}s | {events[i]['stage']}" for i in samples])
    selected[67].save(HEAL / f"{STEM}_complete_poster.png")
    detail_events = events[38:162]
    detail_renderer = Renderer(sprites, (1000, 760), .5, detail=True)
    detail_frames, detail_selected = [], []
    detail_samples = [0, 4, 8, 12, 20, 29, 49, 69, 89, 109, 117, 123]
    for index, event in enumerate(detail_events):
        frame = detail_renderer.render(event, index, len(detail_events))
        detail_frames.append(frame.quantize(palette=palette, dither=Image.Dither.NONE))
        if index in detail_samples:
            detail_selected.append(frame)
    cast_path = HEAL / f"{STEM}_cast_preview.gif"
    save_gif(cast_path, detail_frames)
    storyboard(HEAL / f"{STEM}_cast_storyboard.png", detail_selected,
               [f"{i * .05:.2f}s | {detail_events[i]['stage']}" for i in detail_samples])
    assert all(digest(p) == value for p, value in originals.items()), "Existing asset changed"
    phases = []
    for index, event in enumerate(events):
        if not phases or phases[-1]["stage"] != event["stage"]:
            phases.append(dict(stage=event["stage"], start_ms=index * STEP_MS, duration_ms=0))
        phases[-1]["duration_ms"] += STEP_MS
    manifest = dict(status="pending_effect_review", actor_status="v5 group user-approved",
                    runtime_integrated=False, step_ms=STEP_MS, complete_duration_ms=10200,
                    cast_duration_ms=6200, heal_hold_ms=5000, pulse_count=5, fx_frames_per_cycle=20,
                    main_size=[1200, 800], main_uniform_scale=.43, detail_size=[1000, 760], detail_uniform_scale=.5,
                    floating_prop_offset=FLOAT_OFFSET, held_prop_offset=HELD_OFFSET,
                    held_prop_rotation_degrees=HELD_ANGLE, prop_rotation_center=PROP_CENTER,
                    alignment="one native canvas origin; identical scale for actor, prop and FX; translation-only actor travel",
                    source_files={key: str(path) for key, path in paths.items()},
                    source_sha256={key: digest(path) for key, path in paths.items()},
                    complete_preview=str(main_path), cast_preview=str(cast_path), png_sequence=str(SEQUENCE),
                    mp4_target=str(HEAL / f"{STEM}_complete_preview.mp4"), phases=phases,
                    timeline=[dict(frame=i, time_ms=i * STEP_MS, **e) for i, e in enumerate(events)],
                    preserved_old_sha256={str(p): value for p, value in originals.items()})
    manifest_path = HEAL / f"{STEM}_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"complete_preview": str(main_path), "cast_preview": str(cast_path),
                      "manifest": str(manifest_path), "sequence_frames": len(events),
                      "old_assets_verified": len(originals), "duration_ms": 10200}, indent=2))


if __name__ == "__main__":
    main()
