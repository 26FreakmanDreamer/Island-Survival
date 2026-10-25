"""Build GIF approval previews for the Bat side-view action clips."""

from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageDraw


def _resolve(path_text: str) -> Path:
    path = Path(path_text)
    return path if path.is_absolute() else Path.cwd() / path


def _checkerboard(size: int, tile: int = 16) -> Image.Image:
    image = Image.new("RGB", (size, size), (62, 64, 74))
    draw = ImageDraw.Draw(image)
    for y in range(0, size, tile):
        for x in range(0, size, tile):
            if (x // tile + y // tile) % 2:
                draw.rectangle([x, y, x + tile - 1, y + tile - 1], fill=(82, 84, 96))
    return image


def _frame(path: Path, runtime: int, scale: int) -> Image.Image:
    image = Image.open(path).convert("RGBA")
    if image.size != (runtime, runtime):
        image = image.resize((runtime, runtime), Image.LANCZOS)
    board = _checkerboard(runtime)
    board.paste(image, (0, 0), image)
    return board.resize((runtime * scale, runtime * scale), Image.NEAREST)


def _save_gif(frames: list[Image.Image], durations: list[int], out: Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    frames[0].save(
        out,
        save_all=True,
        append_images=frames[1:],
        duration=durations,
        loop=0,
        disposal=2,
        optimize=True,
    )
    print(out.resolve())


CLIPS = {
    "bat_dive": (
        [
            "bat_dive/bat_dive_00.png",
            "bat_dive/bat_dive_01.png",
            "bat_dive/bat_dive_02.png",
        ],
        [120, 220, 410],
    ),
    "bat_sonic": (
        [
            "bat_sonic/bat_sonic_00.png",
            "bat_sonic/bat_sonic_01.png",
            "bat_sonic/bat_sonic_02.png",
        ],
        [100, 300, 250],
    ),
    "bat_hurt_stun_ko": (
        [
            "hurt/hurt_00.png",
            "stun/stun_00.png",
            "ko/ko_00.png",
            "ko/ko_01.png",
        ],
        [300, 700, 350, 350],
    ),
}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--root",
        default="assets/generated/staged/bat/side_final",
    )
    parser.add_argument(
        "--mirror-root",
        default="assets/generated/staged/bat/side_final_mirror",
    )
    parser.add_argument(
        "--out-dir",
        default="assets/generated/contact_sheets/bat_v1",
    )
    parser.add_argument("--runtime", type=int, default=192)
    parser.add_argument("--scale", type=int, default=4)
    parser.add_argument("--tag", default="v1")
    args = parser.parse_args()

    root = _resolve(args.root)
    mirror_root = _resolve(args.mirror_root)
    out_dir = _resolve(args.out_dir)

    for name, (paths, durations) in CLIPS.items():
        for base_root, suffix in ((root, ""), (mirror_root, "_mirror")):
            frames = []
            for rel in paths:
                path = base_root / rel
                if not path.exists():
                    print(f"ERROR missing frame: {path}")
                    return 1
                frames.append(_frame(path, args.runtime, args.scale))
            _save_gif(
                frames,
                durations,
                out_dir / f"bat_side_{name}{suffix}_{args.tag}.gif",
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
