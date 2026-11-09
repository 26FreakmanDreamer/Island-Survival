"""Animate the existing healing ring and particles upward for artwork review."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "assets/generated/contact_sheets/crooked_witch_heal_fx"
ACTOR = ROOT / "assets/generated/contact_sheets/crooked_witch_heal/crooked_witch_heal_v2_02.png"
STEM = "crooked_witch_heal_fx_v2"
SIZE = (1254, 1254)
COUNT = 20
FRAME_MS = 50
ASCENT_PX = 348
HEAD_NECK_LIMIT_Y = 280


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def font(size: int) -> ImageFont.ImageFont:
    return ImageFont.truetype("C:/Windows/Fonts/segoeui.ttf", size)


def deepen(source: Image.Image, progress: float, ending: float) -> Image.Image:
    """Deepen green and increase density, keeping the small pale spark cores."""
    r, g, b, alpha = source.split()
    dark = Image.merge("RGBA", (
        r.point([round(v * (1 - 0.8 * progress) + 15 * progress) for v in range(256)]),
        g.point([round(v * (1 - 0.32 * progress) + 8 * progress) for v in range(256)]),
        b.point([round(v * (1 - 0.45 * progress) + 14 * progress) for v in range(256)]),
        alpha,
    ))
    pale = ImageChops.multiply(
        ImageChops.darker(r, b).point(lambda v: 255 if v >= 170 else 0),
        g.point(lambda v: 255 if v >= 245 else 0),
    )
    colored = Image.composite(source, dark, pale)
    gain = (0.50 + 0.60 * progress) * ending
    colored.putalpha(alpha.point([min(255, round(v * gain)) for v in range(256)]))
    return colored


def top_limit() -> Image.Image:
    # Particles disappear at the head/neck band instead of drifting above the hat.
    column = Image.new("L", (1, SIZE[1]))
    column.putdata([
        0 if y < HEAD_NECK_LIMIT_Y else min(255, round((y - HEAD_NECK_LIMIT_Y) * 255 / 28))
        for y in range(SIZE[1])
    ])
    return column.resize(SIZE)


def display(frame: Image.Image, actor: Image.Image | None, index: int) -> Image.Image:
    board = Image.new("RGBA", SIZE, (31, 29, 43, 255))
    if actor is not None:
        board.alpha_composite(actor)
    board.alpha_composite(frame)
    board = board.resize((480, 480), Image.Resampling.LANCZOS).convert("RGB")
    draw = ImageDraw.Draw(board)
    draw.text((12, 10), f"HEAL FX v2 | {index:02d} | {index * FRAME_MS} ms", font=font(18), fill=(242, 239, 245))
    return board


def main() -> None:
    original_paths = sorted(OUT.glob("crooked_witch_heal_fx_v1*"))
    hashes = {p.name: digest(p) for p in original_paths}
    sources = [Image.open(OUT / f"crooked_witch_heal_fx_v1_{i:02d}.png").convert("RGBA") for i in range(5)]
    if any(im.size != SIZE for im in sources):
        raise ValueError("All original healing effects must use the same 1254px canvas")
    ceiling = top_limit()
    frames, records = [], []
    for index in range(COUNT):
        progress = min(1.0, index / 17)
        eased = progress * progress * (3 - 2 * progress)
        ending = (0.65 if index == 18 else 0.25 if index == 19 else 1.0)
        source_index = min(4, int(progress * 5))
        dy = -round(ASCENT_PX * eased)
        colored = deepen(sources[source_index], progress, ending)
        frame = Image.new("RGBA", SIZE)
        frame.paste(colored, (0, dy))
        frame.putalpha(ImageChops.multiply(frame.getchannel("A"), ceiling))
        bounds = frame.getchannel("A").getbbox()
        if bounds is None or bounds[1] < HEAD_NECK_LIMIT_Y:
            raise ValueError(f"Healing particles rose beyond the head/neck ceiling: {index}")
        frame_path = OUT / f"{STEM}_{index:02d}.png"
        frame.save(frame_path)
        frames.append(frame)
        records.append({
            "frame": frame_path.name, "source_frame": source_index,
            "offset_y_px": dy, "ring_center_y_px": round(718.5 + dy, 1),
            "deepening_progress": round(progress, 4), "end_dissipation": ending,
            "visible_alpha_bbox": list(bounds),
        })

    actor = Image.open(ACTOR).convert("RGBA")
    samples = [0, 4, 8, 12, 16, 17, 18, 19]
    sheet = Image.new("RGB", (4 * 480, 2 * 510 + 65), (25, 24, 36))
    draw = ImageDraw.Draw(sheet)
    draw.text((14, 12), "HEAL FX v2 | DEEPENING GREEN / UPWARD TO HEAD-NECK / END DISSIPATION", font=font(26), fill=(243, 239, 247))
    for cell, index in enumerate(samples):
        x, y = cell % 4 * 480, 65 + cell // 4 * 510
        sheet.paste(display(frames[index], actor, index), (x, y))
        draw.text((x + 12, y + 484), f"ring y={records[index]['ring_center_y_px']:.0f} | {index * FRAME_MS} ms", font=font(18), fill=(199, 220, 204))
    sheet_path = OUT / f"{STEM}_sheet.png"
    sheet.save(sheet_path)
    for label, actor_layer in [("preview", actor), ("fx_only_preview", None)]:
        images = [display(frame, actor_layer, index) for index, frame in enumerate(frames)]
        path = OUT / f"{STEM}_{label}.gif"
        images[0].save(path, save_all=True, append_images=images[1:], duration=FRAME_MS, loop=0, optimize=False, disposal=2)
        with Image.open(path) as saved:
            if saved.n_frames != COUNT:
                raise ValueError("Unexpected preview frame count")
    manifest = {
        "version": "v2", "status": "pending_user_review", "runtime_integrated": False,
        "actor_version": "heal v5 group approved by user; original character frames unchanged",
        "canvas": list(SIZE), "frame_duration_ms": FRAME_MS, "cycle_duration_s": 1.0,
        "cycle_repeats": 5, "frames": [record["frame"] for record in records],
        "ring_center_x_px": 647, "ring_center_y_start_px": 718.5,
        "ring_center_y_peak_px": 370.5, "ascent_px": ASCENT_PX,
        "particle_head_neck_ceiling_y_px": HEAD_NECK_LIMIT_Y,
        "particle_ceiling_soft_edge_px": 28, "actor_canvas_offset": [0, 0],
        "color": "existing pale green deepens toward emerald while opacity/density increases; pale spark cores retained",
        "ending": "last 100ms dissipates at head/neck height before next pulse restarts",
        "processing": "existing v1 sprites animated by translation, color/density curves, and a head-neck particle ceiling; no actor redraw",
        "sheet": sheet_path.name, "preview": f"{STEM}_preview.gif",
        "fx_only_preview": f"{STEM}_fx_only_preview.gif", "per_frame": records,
        "preserved_original_sha256": hashes,
    }
    (OUT / f"{STEM}_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for name, original_hash in hashes.items():
        if digest(OUT / name) != original_hash:
            raise ValueError(f"Original source changed: {name}")
    print(f"Verified {COUNT} transparent frames, 1000ms per cycle, 348px ascent, ceiling y={HEAD_NECK_LIMIT_Y}.")
    print(sheet_path)


if __name__ == "__main__":
    main()
