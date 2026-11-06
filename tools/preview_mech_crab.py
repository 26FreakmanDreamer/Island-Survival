"""Render headless in-game approval screenshots for the Mech-Crab fight."""

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

OUT = ROOT / "assets" / "generated" / "contact_sheets" / "mech_crab_ingame_v1"


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
    scene.set_enemy("mech_crab")
    scene.stage.set_blocks_enabled(True)
    OUT.mkdir(parents=True, exist_ok=True)
    for stale in OUT.glob("*.png"):
        stale.unlink()

    def place(ex: float, px: float, py: float = 620.0):
        scene.reset()
        crab = scene.enemy
        crab.ai_enabled = False
        crab.x = float(ex)
        crab.y = 620.0
        crab.on_ground = True
        crab.vy = 0.0
        player = scene.player
        player.x = float(px)
        player.y = float(py)
        player.on_ground = True
        player.vy = 0.0
        player.hp = 100.0
        player.statuses.clear()
        return crab, player

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
        crab = scene.enemy
        return (
            lambda: crab.attack_runtime is not None
            and crab.attack_runtime.time >= seconds
        )

    save("01_startup.png")

    crab, player = place(600, 900)
    crab.force_attack(scene, player, "mech_laser")
    tick_until(time_at(0.85))
    save("02_laser_warning.png")
    tick_until(time_at(2.15))
    save("03_laser_active.png")

    crab, player = place(300, 900)
    crab.force_attack(scene, player, "mech_laser")
    tick_until(time_at(1.15))
    save("04_laser_blocked.png")

    crab, player = place(600, 800)
    crab.force_attack(scene, player, "mech_charge")
    tick_until(time_at(0.70))
    save("05_charge_warning.png")
    tick_until(time_at(1.25))
    save("06_charge_active.png")

    crab, player = place(600, 700)
    crab.force_attack(scene, player, "mech_claw_slam")
    tick_until(time_at(0.42))
    save("07_claw_growth.png")
    tick_until(time_at(0.53))
    save("08_claw_swing.png")
    tick_until(time_at(0.60))
    save("09_claw_impact.png")

    crab, player = place(600, 900)
    crab.force_attack(scene, player, "mech_leap_slam")
    tick_until(time_at(0.12))
    save("10_leap_lock_00.png")
    tick_until(time_at(0.30))
    save("10_leap_lock_01.png")
    tick_until(time_at(0.60))
    save("10_leap_lock_02.png")
    tick_until(time_at(1.10))
    save("11_leap_flight.png")
    tick_until(time_at(1.50))
    save("12_leap_landing.png")

    crab, player = place(600, 900)
    crab.force_attack(scene, player, "mech_laser")
    tick_until(time_at(2.15))
    scene.show_overlay = True
    scene.show_panel = False
    save("13_f1_overlay.png")

    scene.show_overlay = False
    scene.show_panel = True
    save("14_f2_panel.png")
    scene.show_panel = False

    scene.set_enemy("mech_crab")
    scene.reset()
    scene.enemy.ai_enabled = False
    save("15_stage_variant.png")

    print("DONE", OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
