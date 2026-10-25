"""Build GIF approval previews for the Bat side-view wing cycle.

The four shared wing frames (00, 00->01 transition, 01, 02) drive both ``idle``
(slow ping-pong) and ``fly`` (fast loop).  GIFs are review artifacts only;
nothing is copied into ``assets/frames``.
"""

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


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--frames",
        default="assets/generated/staged/bat/side_final/keyposes",
    )
    parser.add_argument(
        "--out-dir",
        default="assets/generated/contact_sheets/bat_v1",
    )
    parser.add_argument("--runtime", type=int, default=192)
    parser.add_argument("--scale", type=int, default=4)
    parser.add_argument("--idle-ms", type=int, default=220)
    parser.add_argument("--fly-ms", type=int, default=100)
    parser.add_argument("--tag", default="v1")
    args = parser.parse_args()

    frames_dir = _resolve(args.frames)
    out_dir = _resolve(args.out_dir)
    paths = [
        frames_dir / "side_wing_00.png",
        frames_dir / "side_wing_00_01.png",
        frames_dir / "side_wing_01.png",
        frames_dir / "side_wing_02.png",
    ]
    missing = [str(path) for path in paths if not path.exists()]
    if missing:
        print(f"ERROR missing wing frames: {missing}")
        return 1

    source = [_frame(path, args.runtime, args.scale) for path in paths]
    mirrored = [frame.transpose(Image.FLIP_LEFT_RIGHT) for frame in source]

    idle_order = [0, 1, 2, 3, 2, 1]
    fly_order = [0, 1, 2, 3]
    idle_frames = [source[index] for index in idle_order]
    idle_mirror = [mirrored[index] for index in idle_order]
    fly_frames = [source[index] for index in fly_order]
    fly_mirror = [mirrored[index] for index in fly_order]

    tag = args.tag
    _save_gif(
        idle_frames,
        [args.idle_ms] * len(idle_frames),
        out_dir / f"bat_side_wing_idle_{tag}.gif",
    )
    _save_gif(
        fly_frames,
        [args.fly_ms] * len(fly_frames),
        out_dir / f"bat_side_wing_fly_{tag}.gif",
    )
    _save_gif(
        idle_mirror,
        [args.idle_ms] * len(idle_mirror),
        out_dir / f"bat_side_wing_idle_mirror_{tag}.gif",
    )
    _save_gif(
        fly_mirror,
        [args.fly_ms] * len(fly_mirror),
        out_dir / f"bat_side_wing_fly_mirror_{tag}.gif",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
