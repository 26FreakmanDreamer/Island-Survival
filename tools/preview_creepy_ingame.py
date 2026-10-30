"""Render approval screenshots of the Creepy Shooter fight headlessly."""

from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import pygame  # noqa: E402

from game.config import FIXED_DT, SCREEN_H, SCREEN_W, JsonStore  # noqa: E402
from game.fighter import FighterState  # noqa: E402
from game.scene import ArenaScene  # noqa: E402

OUT = ROOT / "assets" / "generated" / "contact_sheets" / "creepy_shooter_ingame_v1"


def main() -> int:
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
    store = JsonStore()
    scene = ArenaScene(store)
    scene.enemy_count_override = 1
    OUT.mkdir(parents=True, exist_ok=True)

    def save(name: str) -> None:
        scene.draw(screen)
        pygame.image.save(screen, str(OUT / name))
        print(OUT / name)

    def place(creepy_x: float, creepy_y: float, player_x: float, player_y: float) -> None:
        creepy = scene.enemy
        creepy.ai_enabled = False
        creepy.x = float(creepy_x)
        creepy.y = float(creepy_y)
        creepy.vx = 0.0
        creepy.vy = 0.0
        creepy.on_ground = True
        creepy.state = FighterState.IDLE
        player = scene.player
        player.x = float(player_x)
        player.y = float(player_y)
        player.vx = 0.0
        player.vy = 0.0
        player.on_ground = True
        player.hp = player.max_hp
        player.state = FighterState.IDLE

    scene.reset()
    save("01_startup.png")

    # Skill 1: straight bullet in flight.
    scene.reset()
    place(800, 220, 950, 220)
    scene.enemy.force_attack(scene, scene.player, "creepy_shot")
    for _ in range(13):
        scene.tick(FIXED_DT)
    save("02_creepy_shot.png")

    # Skill 2: 1s lock wind-up reticle on the player.
    scene.reset()
    place(800, 220, 900, 620)
    scene.enemy.force_attack(scene, scene.player, "creepy_homing_shot")
    for _ in range(30):
        scene.tick(FIXED_DT)
    save("03_lock_marker.png")

    # Skill 2: homing bolt in flight and impact.
    for _ in range(40):
        scene.tick(FIXED_DT)
    save("04_homing_bullet.png")
    for _ in range(80):
        scene.tick(FIXED_DT)
    save("05_homing_impact.png")

    # Skill 3: roll tuck and inverted frame.
    scene.reset()
    place(800, 220, 700, 220)
    scene.enemy.force_attack(scene, scene.player, "creepy_roll_shot")
    for _ in range(10):
        scene.tick(FIXED_DT)
    save("06_roll_tuck.png")
    for _ in range(8):
        scene.tick(FIXED_DT)
    save("07_roll_inverted.png")

    # Skill 4: jump shot from the far-right ground takeoff.
    scene.reset()
    place(1136, 620, 1100, 620)
    scene.enemy.force_attack(scene, scene.player, "creepy_jump_shot")
    for _ in range(8):
        scene.tick(FIXED_DT)
    save("08_jump_shot.png")

    # F1/F2 on the platform.
    scene.reset()
    place(800, 220, 950, 220)
    scene.show_overlay = True
    scene.show_panel = True
    save("09_overlay_panel.png")
    scene.show_overlay = False
    scene.show_panel = False
    print("DONE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
