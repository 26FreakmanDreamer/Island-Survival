"""Render headless in-game approval screenshots for the Shadow Ninja fight."""

from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pygame

from game.config import FIXED_DT, SCREEN_H, SCREEN_W, JsonStore
from game.scene import ArenaScene

OUT = ROOT / "assets" / "generated" / "contact_sheets" / "shadow_ninja_ingame_v1"


def main() -> int:
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
    store = JsonStore()
    if not store.last_ok:
        print("CONFIG ERROR", store.last_error)
        return 1
    scene = ArenaScene(store)
    scene.enemy_count_override = 1
    scene.set_character("lina")
    scene.set_enemy("shadow_ninja")
    scene.stage.set_blocks_enabled(True)
    OUT.mkdir(parents=True, exist_ok=True)
    for stale in OUT.glob("*.png"):
        stale.unlink()

    def place(ex: float, px: float, py: float = 620.0):
        scene.reset()
        ninja = scene.enemy
        ninja.ai_enabled = False
        ninja.x = float(ex)
        ninja.y = 620.0
        ninja.on_ground = True
        ninja.vy = 0.0
        ninja.facing = 1 if px > ex else -1
        player = scene.player
        player.x = float(px)
        player.y = float(py)
        player.on_ground = True
        player.vy = 0.0
        player.hp = player.max_hp
        player.statuses.clear()
        player.shadow_marks = 0
        player.shadow_mark_burst_time = 0.0
        return ninja, player

    def tick_until(predicate, limit: int = 360) -> None:
        for _ in range(limit):
            scene.tick(FIXED_DT)
            if predicate():
                return

    def save(name: str) -> None:
        scene.draw(screen)
        path = OUT / name
        pygame.image.save(screen, str(path))
        print(path)

    def time_at(seconds: float):
        ninja = scene.enemy
        return (
            lambda: ninja.attack_runtime is not None
            and ninja.attack_runtime.time >= seconds
        )

    save("01_startup.png")

    ninja, player = place(450.0, 400.0)
    ninja.force_attack(scene, player, "shadow_kunai_slash")
    tick_until(time_at(0.18))
    save("02_slash.png")

    ninja, player = place(400.0, 900.0)
    ninja.force_attack(scene, player, "shadow_kunai_throw")
    tick_until(
        lambda: bool(scene.projectiles)
        and scene.projectiles[0].x >= 560.0,
        limit=80,
    )
    save("03_throw_low.png")

    ninja, player = place(400.0, 900.0)
    saved_blocks = scene.stage.blocks
    saved_barriers = scene.stage.barriers
    test_barrier = pygame.Rect(600, 560, 90, 60)
    scene.stage.blocks = [test_barrier]
    scene.stage.barriers = [test_barrier]
    ninja.force_attack(scene, player, "shadow_kunai_throw")
    tick_until(
        lambda: bool(scene.projectiles)
        and scene.projectiles[0].x >= 585.0,
        limit=80,
    )
    save("04_throw_blocked.png")
    scene.stage.blocks = saved_blocks
    scene.stage.barriers = saved_barriers

    ninja, player = place(400.0, 900.0)
    ninja.force_attack(scene, player, "shadow_dash")
    tick_until(time_at(0.25))
    save("05_dash.png")

    ninja, player = place(450.0, 400.0)
    ninja._add_shadow_mark(scene, player)
    save("06_marks_1.png")
    ninja._add_shadow_mark(scene, player)
    save("07_marks_2.png")
    ninja._add_shadow_mark(scene, player)
    save("08_marks_3.png")
    ninja._add_shadow_mark(scene, player)
    scene.tick(FIXED_DT)
    save("09_mark_burst.png")

    ninja, player = place(450.0, 400.0)
    ninja.statuses.add("stun", 1.0, source="preview")
    scene.tick(FIXED_DT)
    save("10_stun.png")

    scene.reset()
    scene.enemy.ai_enabled = False
    save("11_idle.png")

    scene.show_overlay = True
    scene.show_panel = False
    save("12_f1_overlay.png")

    scene.show_overlay = False
    scene.show_panel = True
    save("13_f2_panel.png")
    scene.show_panel = False

    scene.set_enemy("shadow_ninja")
    scene.reset()
    scene.enemy.ai_enabled = False
    save("14_stage.png")

    print("DONE", OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
