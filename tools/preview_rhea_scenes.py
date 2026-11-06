"""Render approval previews for Rhea's E phases and the enemy stage variants.

Headless, no Image/ changes. Writes PNGs and two contact sheets under
assets/generated/contact_sheets/rhea_scenes_v1/.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import pygame  # noqa: E402
from PIL import Image, ImageDraw, ImageFont  # noqa: E402

from game.config import FIXED_DT, SCREEN_H, SCREEN_W, JsonStore  # noqa: E402
from game.scene import ArenaScene  # noqa: E402

OUT = ROOT / "assets" / "generated" / "contact_sheets" / "rhea_scenes_v1"


def _font(size: int):
    try:
        return ImageFont.truetype("arial.ttf", size)
    except Exception:  # noqa: BLE001
        return ImageFont.load_default()


def make_sheet(items, columns: int, cell_w: int, out: Path, title: str) -> None:
    cell_h = round(cell_w * SCREEN_H / SCREEN_W)
    pad = 12
    label_h = 30
    title_h = 34
    rows = (len(items) + columns - 1) // columns
    sheet = Image.new(
        "RGB",
        (pad + columns * (cell_w + pad), title_h + rows * (cell_h + label_h + pad) + pad),
        (26, 28, 36),
    )
    draw = ImageDraw.Draw(sheet)
    draw.text((pad, 8), title, fill=(238, 238, 246), font=_font(20))
    for index, (path, label) in enumerate(items):
        column = index % columns
        row = index // columns
        x = pad + column * (cell_w + pad)
        y = title_h + row * (cell_h + label_h + pad)
        image = Image.open(path).convert("RGB").resize(
            (cell_w, cell_h), Image.LANCZOS
        )
        sheet.paste(image, (x, y))
        draw.text((x + 4, y + cell_h + 6), label, fill=(235, 235, 245), font=_font(14))
    out.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out)
    print(out)


def main() -> int:
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
    store = JsonStore()
    scene = ArenaScene(store)
    OUT.mkdir(parents=True, exist_ok=True)

    def save(name: str) -> Path:
        scene.draw(screen)
        path = OUT / name
        pygame.image.save(screen, str(path))
        print(path)
        return path

    def tick_until(predicate, limit: int = 240) -> int:
        ticks = 0
        while not predicate() and ticks < limit:
            scene.tick(FIXED_DT)
            ticks += 1
        return ticks

    # --- stage variants -----------------------------------------------------
    scene.enemy_count_override = None
    scene.set_character("lina")
    stage_shots = []
    for enemy_id, label in (
        ("warrior", "Warrior - symmetric"),
        ("bat", "Bat - empty stage, 5 bats"),
        ("veno", "Veno-Spider - empty stage, 3 spiders"),
        ("creepy_shooter", "Creepy Shooter - current layout"),
    ):
        scene.set_enemy("dummy")
        scene.set_enemy(enemy_id)
        scene.reset()
        scene.show_overlay = True
        scene.show_panel = False
        stage_shots.append((save(f"stage_{enemy_id}.png"), label))
    scene.show_overlay = False

    # --- Rhea E phases ------------------------------------------------------
    scene.set_character("rhea")
    scene.set_enemy("dummy")
    scene.reset()
    scene.stage.blocks_enabled = False
    player = scene.player
    enemy = scene.enemy
    enemy.ai_enabled = False
    player.x, player.y = 300.0, scene.stage.ground_y
    player.on_ground = True
    player.facing = 1
    enemy.x, enemy.y = 500.0, scene.stage.ground_y
    enemy.on_ground = True
    scene.show_overlay = True
    scene.show_panel = False
    scene.input.buffer.press("e")
    tick_until(lambda: player.e_phase == "out" and player.x >= 620.0, 60)
    e_out = save("e_01_outbound.png")
    tick_until(lambda: player.e_phase == "window")
    scene.show_panel = True
    e_window = save("e_02_window.png")
    scene.show_panel = False
    scene.input.buffer.press("e")
    tick_until(lambda: player.e_phase == "return", 30)
    tick_until(lambda: player.x <= 700.0 or player.e_phase != "return", 30)
    e_return = save("e_03_return.png")
    tick_until(lambda: player.e_phase is None, 240)
    e_ready = save("e_04_cooldown.png")

    make_sheet(
        stage_shots,
        2,
        640,
        OUT / "stage_variants_sheet.png",
        "Enemy stage variants - F1 collision overlay",
    )
    make_sheet(
        [
            (e_out, "E outbound 0.06-0.60s"),
            (e_window, "free-control window + HUD/F2"),
            (e_return, "manual return"),
            (e_ready, "cooldown started"),
        ],
        4,
        480,
        OUT / "rhea_e_phases_sheet.png",
        "Rhea E - outbound / window / return / cooldown",
    )
    print("DONE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
