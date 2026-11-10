"""Render headless in-game approval screenshots for the shared special skills."""

from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pygame

from game.combat import resolve_hit
from game.config import FIXED_DT, SCREEN_H, SCREEN_W, JsonStore
from game.scene import ArenaScene

OUT = ROOT / "assets" / "generated" / "contact_sheets" / "special_skills_ingame_v1"


def main() -> int:
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
    store = JsonStore()
    if not store.last_ok:
        print("CONFIG ERROR", store.last_error)
        return 1
    scene = ArenaScene(store)
    scene.enemy_count_override = 1
    OUT.mkdir(parents=True, exist_ok=True)
    for stale in OUT.glob("*.png"):
        stale.unlink()

    def setup(hp: float | None = None) -> None:
        scene.set_character("lina")
        scene.set_enemy("dummy")
        scene.reset()
        player = scene.player
        dummy = scene.enemy
        dummy.ai_enabled = False
        player.x = 320.0
        player.y = 620.0
        player.facing = 1
        dummy.x = 560.0
        dummy.y = 620.0
        dummy.facing = -1
        if hp is not None:
            player.hp = hp

    def tick(count: int) -> None:
        for _ in range(count):
            scene.tick(FIXED_DT)

    def press(slot: int) -> None:
        scene.input.buffer.press(f"special_{slot}")

    def save(name: str) -> None:
        scene.draw(screen)
        path = OUT / name
        pygame.image.save(screen, str(path))
        print(path)

    attack = {"duration": 0.1, "hitstun": 0.2, "hitstop": 0.0}
    event = {"damage": 20.0, "knockback": 0.0, "t": 0.0}

    # Sacred Shield: cast, persistent aura, and a blocked hit.
    setup()
    press(1)
    tick(3)
    save("01_shield_cast.png")
    tick(18)
    save("02_shield_aura.png")
    resolve_hit(scene, scene.enemy, scene.player, attack, event)
    tick(4)
    save("03_shield_block.png")

    # Purity Seal: cast after poison/slow, then the persistent aura.
    setup(hp=60.0)
    scene.player.statuses.add_poison("preview", 3.0, 1.0)
    scene.player.statuses.add_slow(0.5, 3.0)
    press(2)
    tick(3)
    save("04_purity_cast.png")
    tick(18)
    save("05_purity_aura.png")

    # Fury Unbound: cast, aura, then a doubled punch on the dummy.
    setup()
    press(3)
    tick(3)
    save("06_fury_cast.png")
    tick(18)
    save("07_fury_aura.png")
    scene.player.x = scene.enemy.x - 80.0
    scene.player.facing = 1
    scene.player.start_attack("punch_l", scene, scene.enemy)
    tick(12)
    save("08_fury_hit.png")

    # Vitality Tonic: cast at low HP.
    setup(hp=35.0)
    press(4)
    tick(3)
    save("09_heal_cast.png")

    # Full-HP denial message above the player.
    setup(hp=100.0)
    press(4)
    tick(1)
    save("10_full_hp_message.png")

    # HUD row with everything used.
    setup(hp=10.0)
    for slot in (1, 2, 3, 4):
        press(slot)
        tick(1)
    save("11_hud_active.png")
    tick(310)
    save("12_hud_all_used.png")

    # F2 panel with the full special-skill names.
    scene.show_panel = True
    save("13_f2_panel.png")
    scene.show_panel = False

    pygame.quit()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
