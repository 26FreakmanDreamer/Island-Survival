"""Assemble Crooked Witch potion artwork into review-only sheets and previews."""

from __future__ import annotations

import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "assets/generated/contact_sheets"
SETS = {
    "actor": ("crooked_witch_potion", "crooked_witch_potion_v1", 4),
    "projectile": ("crooked_witch_potion_projectile", "crooked_witch_potion_projectile_v1", 3),
    "break": ("crooked_witch_potion_break", "crooked_witch_potion_break_v1", 4),
    "pool": ("crooked_witch_poison_pool", "crooked_witch_poison_pool_v1", 4),
}
FRAMES: dict[str, list[Image.Image]] = {}
SCENE_SIZE = (940, 480)


def font(size: int) -> ImageFont.ImageFont:
    for name in ("C:/Windows/Fonts/segoeui.ttf", "C:/Windows/Fonts/arial.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            pass
    return ImageFont.load_default()


def load() -> None:
    for key, (directory, stem, count) in SETS.items():
        paths = [BASE / directory / f"{stem}_{i:02d}.png" for i in range(count)]
        frames = [Image.open(path).convert("RGBA") for path in paths]
        if any(frame.size != (1254, 1254) for frame in frames):
            raise ValueError(f"Unexpected canvas size: {key}")
        for path, frame in zip(paths, frames):
            bounds = frame.getchannel("A").point(lambda p: 255 if p >= 64 else 0).getbbox()
            if bounds is None:
                raise ValueError(f"Empty artwork: {path}")
            corners = [frame.getpixel(point)[3] for point in ((0, 0), (1253, 0), (0, 1253), (1253, 1253))]
            if any(alpha >= 64 for alpha in corners):
                raise ValueError(f"Visible canvas corner: {path}, alpha={corners}")
            if any(corners):
                print(f"  faint corner alpha: {corners}")
            print(f"{path.name}: {bounds}")
        FRAMES[key] = frames


def checker(size: tuple[int, int], tile: int = 18) -> Image.Image:
    result = Image.new("RGB", size, (45, 47, 56))
    draw = ImageDraw.Draw(result)
    for y in range(0, size[1], tile):
        for x in range(0, size[0], tile):
            if (x // tile + y // tile) % 2:
                draw.rectangle((x, y, x + tile - 1, y + tile - 1), fill=(62, 65, 76))
    return result


def sheet(key: str) -> Image.Image:
    directory, stem, count = SETS[key]
    size, gap, top, bottom = 288, 12, 50, 42
    result = Image.new("RGB", (gap + count * (size + gap), top + size + bottom), (25, 27, 35))
    draw = ImageDraw.Draw(result)
    title = {"actor": "POTION CAST", "projectile": "POTION PROJECTILE", "break": "BOTTLE BREAK", "pool": "POISON POOL"}[key]
    draw.text((gap, 12), f"Crooked Witch | {title} | v1", font=font(23), fill=(244, 242, 230))
    for i, frame in enumerate(FRAMES[key]):
        x = gap + i * (size + gap)
        board = checker((size, size))
        preview = frame.resize((size, size), Image.Resampling.LANCZOS)
        board.paste(preview, (0, 0), preview)
        result.paste(board, (x, top))
        draw.text((x + 5, top + size + 9), f"{i:02d}", font=font(20), fill=(225, 232, 240))
    out = BASE / directory / f"{stem}_sheet.png"
    result.save(out)
    print(out)
    return result


def save_gif(path: Path, frames: list[Image.Image], durations_ms: list[int]) -> None:
    rgb = [frame.convert("RGB") for frame in frames]
    rgb[0].save(path, save_all=True, append_images=rgb[1:], duration=durations_ms, loop=0, optimize=False)
    with Image.open(path) as saved:
        if saved.n_frames != len(frames):
            raise ValueError(f"Incorrect GIF frame count: {path}")
    print(path)


def simple_preview(key: str) -> None:
    _, stem, _ = SETS[key]
    seq = {
        "actor": [0, 1, 2, 3],
        "projectile": [0, 1, 2, 1],
        "break": [0, 1, 2, 3],
        "pool": [0, 1, 2, 1, 2, 3],
    }[key]
    duration = {
        "actor": [150, 150, 150, 200],
        "projectile": [130, 130, 130, 130],
        "break": [90, 90, 110, 150],
        "pool": [150, 220, 220, 220, 220, 180],
    }[key]
    out_frames = []
    for idx in seq:
        source = FRAMES[key][idx]
        board = checker((360, 360), 20)
        rendered = source.resize((360, 360), Image.Resampling.LANCZOS)
        board.paste(rendered, (0, 0), rendered)
        out_frames.append(board)
    save_gif(BASE / SETS[key][0] / f"{stem}_preview.gif", out_frames, duration)


def cropped(key: str, idx: int, *, width: int | None = None, height: int | None = None) -> Image.Image:
    frame = FRAMES[key][idx]
    bbox = frame.getchannel("A").point(lambda p: 255 if p >= 16 else 0).getbbox()
    assert bbox is not None
    frame = frame.crop(bbox)
    if width is not None:
        height = round(frame.height * width / frame.width)
    elif height is not None:
        width = round(frame.width * height / frame.height)
    else:
        raise ValueError("Specify width or height")
    assert width is not None and height is not None
    return frame.resize((width, height), Image.Resampling.LANCZOS)


def layer(scene: Image.Image, sprite: Image.Image, center_x: int, bottom_y: int) -> None:
    scene.paste(sprite, (round(center_x - sprite.width / 2), bottom_y - sprite.height), sprite)


def scene(branch: str, step: int) -> Image.Image:
    board = Image.new("RGB", SCENE_SIZE, (27, 31, 44))
    d = ImageDraw.Draw(board)
    # Lines are review guides only. They are not part of the transparent source art.
    if branch == "platform_miss":
        actor_ground, target_ground = 386, 449
        d.rectangle((0, actor_ground, 407, 405), fill=(91, 99, 111))
        d.line((407, target_ground, 940, target_ground), fill=(91, 99, 111), width=14)
    else:
        actor_ground = target_ground = 430
        d.line((0, target_ground, 940, target_ground), fill=(91, 99, 111), width=14)
    if branch == "direct_hit":
        d.rounded_rectangle((775, 272, 845, 428), radius=25, outline=(157, 167, 181), width=3)
        d.text((773, 245), "TARGET", font=font(16), fill=(176, 183, 198))

    actor_idx = min(step, 3)
    actor = FRAMES["actor"][actor_idx].resize((326, 326), Image.Resampling.LANCZOS)
    board.paste(actor, (8, actor_ground - 313), actor)

    paths = {
        "platform_miss": [(353, 139), (448, 170), (547, 202), (665, 284), (820, 440)],
        "ground_miss": [(353, 183), (449, 297), (563, 363), (692, 363), (820, 420)],
        "direct_hit": [(353, 183), (452, 257), (566, 315), (688, 337), (804, 358)],
    }
    if 2 <= step <= 6:
        x, y = paths[branch][step - 2]
        bottle = cropped("projectile", (step - 2) % 3, height=72)
        layer(board, bottle, x, y)
    if 7 <= step <= 10:
        break_fx = cropped("break", step - 7, width=(104, 150, 190, 128)[step - 7])
        impact_y = target_ground if branch != "direct_hit" else 390
        layer(board, break_fx, 820, impact_y + 4)
    if branch != "direct_hit" and 11 <= step <= 14:
        pool = cropped("pool", (0, 1, 2, 3)[step - 11], width=230)
        layer(board, pool, 820, target_ground + 4)
    d = ImageDraw.Draw(board)
    label = {"platform_miss": "PLATFORM MISS", "ground_miss": "GROUND MISS", "direct_hit": "DIRECT HIT"}[branch]
    d.text((20, 14), label, font=font(22), fill=(243, 238, 214))
    status = "CAST" if step < 2 else "RELEASE / FLIGHT" if step <= 6 else "BOTTLE BREAK" if step <= 10 else "POISON POOL" if branch != "direct_hit" else "NO POOL"
    d.text((20, 44), status, font=font(15), fill=(196, 211, 224))
    return board


def branch_previews() -> None:
    out_dir = BASE / "crooked_witch_potion"
    rows = []
    for branch in ("platform_miss", "ground_miss", "direct_hit"):
        count = 15 if branch != "direct_hit" else 12
        frames = [scene(branch, i) for i in range(count)]
        save_gif(out_dir / f"crooked_witch_potion_v1_{branch}_preview.gif", frames, [125] * count)
        sample_indices = (2, 5, 8, 12) if branch != "direct_hit" else (2, 5, 8, 11)
        rows.append([frames[i].resize((470, 240), Image.Resampling.LANCZOS) for i in sample_indices])
    gap, heading, cell_w, cell_h = 12, 47, 470, 240
    board = Image.new("RGB", (gap + 4 * (cell_w + gap), heading + 3 * (cell_h + gap)), (22, 25, 35))
    d = ImageDraw.Draw(board)
    d.text((gap, 9), "CROOKED WITCH POTION | CAST / FLIGHT / BREAK / RESULT", font=font(24), fill=(243, 242, 230))
    for row_idx, row in enumerate(rows):
        for col_idx, sample in enumerate(row):
            board.paste(sample, (gap + col_idx * (cell_w + gap), heading + row_idx * (cell_h + gap)))
    out = out_dir / "crooked_witch_potion_v1_branch_storyboard.png"
    board.save(out)
    print(out)


def manifests() -> None:
    definitions = {
        "actor": {
            "base": "../crooked_witch_base/crooked_witch_base_v4_02.png",
            "frame_durations_s": [0.15, 0.15, 0.15, 0.20],
            "release_frame": 2,
            "action": "staff windup, far hand opens, staff flicks and releases conjured bottle, return",
            "fx": ["../crooked_witch_potion_projectile", "../crooked_witch_potion_break", "../crooked_witch_poison_pool"],
        },
        "projectile": {
            "preview_cycle_frames": [0, 1, 2, 1],
            "suggested_cycle_s": 0.52,
            "action": "sealed bottle travels with gentle rotation and luminous liquid",
        },
        "break": {
            "preview_frame_durations_s": [0.09, 0.09, 0.11, 0.15],
            "action": "bottle cracks, glass shatters, poison splashes, fragments fade",
        },
        "pool": {
            "entry_frame": 0,
            "loop_frames": [1, 2],
            "exit_frame": 3,
            "lifetime_s": None,
            "action": "shallow bubbling poison puddle appears only after miss, landing, or path end",
        },
    }
    for key, detail in definitions.items():
        directory, stem, count = SETS[key]
        manifest = {
            "status": "pending_user_review",
            "runtime_integrated": False,
            "frames": [f"{stem}_{i:02d}.png" for i in range(count)],
            "sheet": f"{stem}_sheet.png",
            "preview": f"{stem}_preview.gif",
            **detail,
        }
        path = BASE / directory / f"{stem}_manifest.json"
        path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(path)
    branch_path = BASE / "crooked_witch_potion" / "crooked_witch_potion_v1_branches.json"
    branch_path.write_text(json.dumps({
        "status": "pending_user_review",
        "runtime_integrated": False,
        "platform_miss": "gravity arc, bottle shatters on ground/platform, pool appears",
        "ground_miss": "low horizontal travel, bottle shatters at path end, pool appears",
        "direct_hit": "bottle shatters on target, direct-hit status applies, no pool",
        "preview_only": "scene guides and target placeholder are not source art or runtime integration",
        "storyboard": "crooked_witch_potion_v1_branch_storyboard.png",
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    load()
    for key in SETS:
        sheet(key)
        simple_preview(key)
    branch_previews()
    manifests()


if __name__ == "__main__":
    main()
