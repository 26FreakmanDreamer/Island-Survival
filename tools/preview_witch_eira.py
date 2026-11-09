"""Render headless in-game approval screenshots for Eira and the Crooked Witch."""

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
from game.fighter import FighterState
from game.scene import ArenaScene

OUT = ROOT / "assets" / "generated" / "contact_sheets" / "witch_eira_ingame_v1"


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

    # --- Eira ---------------------------------------------------------------
    scene.set_character("eira")
    scene.set_enemy("dummy")
    scene.reset()
    eira = scene.player
    dummy = scene.enemy
    dummy.ai_enabled = False

    def place_eira(px: float = 300.0, ex: float = 700.0, py: float = 620.0) -> None:
        scene.reset()
        eira = scene.player
        dummy = scene.enemy
        dummy.ai_enabled = False
        for fighter, x, y, facing in (
            (eira, px, py, 1 if ex >= px else -1),
            (dummy, ex, py, 1 if px >= ex else -1),
        ):
            fighter.x = float(x)
            fighter.y = float(y)
            fighter.facing = facing
            fighter.vx = 0.0
            fighter.vy = 0.0
            fighter.hitstun = 0.0
            fighter.hp = fighter.max_hp
            fighter.state = FighterState.IDLE
            fighter.on_ground = True
            fighter.invincible = False
            fighter.statuses.clear()
            fighter.eira_freeze = 0.0
        scene.hazards = []
        scene.projectiles = []
        scene.hitstop = 0.0
        scene.match_over = None
        scene.sim_time = 0.0

    place_eira()
    scene.draw(screen)
    save("eira_01_startup.png")

    place_eira()
    eira.start_attack("eira_snowball", scene, dummy)
    tick_until(lambda: eira.attack_runtime is not None and eira.attack_runtime.time >= 0.20)
    save("eira_02_snowball_release.png")
    tick_until(lambda: dummy.hp < dummy.max_hp, limit=80)
    save("eira_03_snowball_hit.png")

    place_eira(300.0, 380.0)
    eira.start_attack("eira_staff_strike", scene, dummy)
    tick_until(lambda: eira.attack_runtime is not None and eira.attack_runtime.time >= 0.25)
    save("eira_04_staff_strike.png")
    tick_until(lambda: eira.attack_runtime is not None and eira.attack_runtime.time >= 0.30)
    save("eira_04b_staff_strike_follow.png")

    place_eira()
    dummy.statuses.add("freeze", 2.0)
    eira.start_attack("eira_ice_shard", scene, dummy)
    tick_until(
        lambda: eira.attack_runtime is not None
        and eira.attack_runtime.time >= 0.16,
        limit=20,
    )
    save("eira_05a_ice_shard_charge.png")
    tick_until(
        lambda: eira.attack_runtime is not None
        and eira.attack_runtime.time >= 0.24,
        limit=20,
    )
    save("eira_05b_ice_shard_release.png")
    tick_until(lambda: dummy.hp < dummy.max_hp, limit=80)
    save("eira_05_ice_shard_frozen_hit.png")

    place_eira()
    eira._start_e(scene)
    tick_until(lambda: eira.e_targeting, limit=60)
    scene.mouse_x = 700.0
    save("eira_06_e_targeting.png")
    scene.input.buffer.press("punch")
    tick_until(lambda: eira.e_phase == "release", limit=20)
    tick_until(lambda: bool(scene.hazards), limit=20)
    tick_until(
        lambda: bool(scene.hazards) and scene.hazards[0].y > 300.0,
        limit=80,
    )
    save("eira_07_e_ball_spawn.png")
    tick_until(lambda: scene.hazards and getattr(scene.hazards[0], "landed", False), limit=120)
    save("eira_08_e_ground_contact.png")
    tick_until(
        lambda: scene.hazards and getattr(scene.hazards[0], "land_time", 0.0) > 0.3,
        limit=60,
    )
    save("eira_08a_e_ground_bounce.png")
    tick_until(
        lambda: scene.hazards and getattr(scene.hazards[0], "land_time", 0.0) > 0.6,
        limit=60,
    )
    save("eira_08b_e_ground_chunks.png")
    tick_until(
        lambda: scene.hazards and getattr(scene.hazards[0], "land_time", 0.0) > 2.7,
        limit=200,
    )
    save("eira_08c_e_ground_fade.png")
    place_eira()
    dummy.statuses.add("freeze", 2.0)
    scene.tick(FIXED_DT)
    save("eira_09_frozen_shell.png")

    scene.show_overlay = True
    save("eira_10_f1_overlay.png")
    scene.show_overlay = False
    scene.show_panel = True
    save("eira_11_f2_panel.png")
    scene.show_panel = False

    # --- Crooked Witch ------------------------------------------------------
    scene.set_character("lina")
    scene.set_enemy("crooked_witch")
    scene.reset()
    witch = scene.enemy
    player = scene.player

    def place_witch(
        wx: float = 900.0,
        wy: float = 220.0,
        px: float = 300.0,
        py: float = 620.0,
        lock_teleport: bool = True,
    ) -> None:
        scene.reset()
        witch = scene.enemy
        player = scene.player
        for fighter, x, y, facing in (
            (witch, wx, wy, 1 if px >= wx else -1),
            (player, px, py, 1 if wx >= px else -1),
        ):
            fighter.x = float(x)
            fighter.y = float(y)
            fighter.facing = facing
            fighter.vx = 0.0
            fighter.vy = 0.0
            fighter.hitstun = 0.0
            fighter.hp = fighter.max_hp
            fighter.state = FighterState.IDLE
            fighter.on_ground = True
            fighter.invincible = False
            fighter.statuses.clear()
        witch.phase = "normal"
        witch.phase_time = 0.0
        witch.teleport_cd = 999.0 if lock_teleport else 0.0
        witch.damage_timer = 0.0
        witch.teleport_pending = False
        witch.heal_used = False
        witch.attack_runtime = None
        witch.attack_id = None
        witch.no_hitbox = False
        witch.hidden = False
        witch.invincible = False
        witch.ignore_separation = False
        witch.ai_enabled = False
        scene.hazards = []
        scene.projectiles = []
        scene.hitstop = 0.0
        scene.match_over = None
        scene.sim_time = 0.0

    place_witch()
    scene.draw(screen)
    save("witch_01_startup.png")

    place_witch(lock_teleport=False)
    witch.take_hit(5.0, 0.0, 0.2, -1)
    tick_until(lambda: witch.phase == "teleport_out", limit=10)
    save("witch_02_teleport_out.png")
    tick_until(lambda: witch.phase == "teleport_in", limit=40)
    save("witch_03_teleport_in.png")

    place_witch(900.0, 620.0, 300.0, 620.0)
    witch.hp = 199.0
    tick_until(lambda: witch.phase == "heal_in", limit=10)
    save("witch_04_heal_fly.png")
    tick_until(lambda: witch.phase == "heal_cast", limit=120)
    tick_until(lambda: witch.heal_tick >= 2, limit=180)
    for _ in range(30):
        scene.tick(FIXED_DT)
    save("witch_05_heal_ticks.png")
    tick_until(lambda: witch.phase == "heal_out", limit=300)
    save("witch_06_heal_return.png")

    place_witch(900.0, 620.0, 300.0, 620.0)
    witch.force_attack(scene, player, "witch_lightning")
    tick_until(lambda: bool(scene.projectiles), limit=40)
    for _ in range(8):
        scene.tick(FIXED_DT)
    save("witch_07_lightning_forward.png")
    place_witch(900.0, 620.0, 700.0, 320.0)
    witch.force_attack(scene, player, "witch_lightning_up")
    tick_until(lambda: bool(scene.projectiles), limit=40)
    for _ in range(8):
        scene.tick(FIXED_DT)
    save("witch_08_lightning_up.png")
    place_witch(900.0, 620.0, 300.0, 620.0)

    class _FakeLightning:
        def __init__(self, target) -> None:
            self.target = target
            self.kind = "witch_lightning_forward"

    for _ in range(3):
        witch.on_projectile_hit(_FakeLightning(player))
    scene.tick(FIXED_DT)
    save("witch_09_vulnerable_stacks.png")

    place_witch(900.0, 620.0, 300.0, 620.0)
    witch.force_attack(scene, player, "witch_ice_spike")
    tick_until(lambda: bool(scene.hazards), limit=40)
    save("witch_10_ice_warning.png")
    tick_until(lambda: witch_player_frozen(scene), limit=140)
    for _ in range(8):
        scene.tick(FIXED_DT)
    save("witch_11_ice_spike.png")

    place_witch(900.0, 620.0, 300.0, 620.0)
    witch.force_attack(scene, player, "witch_potion")
    tick_until(lambda: player.hp < player.max_hp, limit=120)
    save("witch_12_potion_direct.png")
    place_witch(900.0, 220.0, 300.0, 620.0)
    witch.force_attack(scene, player, "witch_potion")
    tick_until(lambda: bool(scene.hazards), limit=180)
    save("witch_13_poison_zone.png")

    place_witch(900.0, 620.0, 700.0, 620.0)
    witch.force_attack(scene, player, "witch_fire_rain")
    tick_until(lambda: witch.phase == "fire_cast", limit=140)
    save("witch_14_fire_pulse.png")
    def fireball_on_screen() -> bool:
        return any(
            getattr(projectile, "kind", "") == "witch_fireball"
            and projectile.y > 60.0
            for projectile in scene.projectiles
        )

    tick_until(fireball_on_screen, limit=220)
    save("witch_15_fireballs.png")

    scene.show_overlay = True
    save("witch_16_f1_overlay.png")
    scene.show_overlay = False
    scene.show_panel = True
    save("witch_17_f2_panel.png")
    scene.show_panel = False

    print("DONE", OUT)
    return 0


def witch_player_frozen(scene) -> bool:
    return scene.player.statuses.has("freeze")


if __name__ == "__main__":
    raise SystemExit(main())
