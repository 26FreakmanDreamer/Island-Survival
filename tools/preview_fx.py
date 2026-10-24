"""Render offscreen in-game FX snapshots for review.

Run from the project root:

    .venv/Scripts/python.exe tools/preview_fx.py

By default the runtime frame directories are used (missing sprite frames fall
back to the procedural draws). Pass ``--lina-normal-dir``, ``--lina-flame-dir``
and/or ``--web-sprite`` to preview candidate assets before the approval copy.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pygame

from game import fx
from game.config import FIXED_DT, SCREEN_H, SCREEN_W, JsonStore
from game.scene import ArenaScene


OUT = ROOT / "assets" / "generated" / "contact_sheets" / "fx_ingame_preview_v1"


def override_assets(args) -> None:
    for key, directory in (
        ("normal", args.lina_normal_dir),
        ("flame", args.lina_flame_dir),
    ):
        if directory is None:
            continue
        current = fx.LINA_Q_SPECS[key]
        fx.LINA_Q_SPECS[key] = fx.StripSpec(
            directory=Path(directory),
            names=current.names,
            durations=current.durations,
            frame_size=current.frame_size,
            anchor=current.anchor,
            loop=current.loop,
        )
    if args.web_sprite is not None:
        fx.VENO_WEB_SPRITE_PATH = Path(args.web_sprite)


def save(surface: pygame.Surface, name: str) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    pygame.image.save(surface, str(OUT / f"{name}.png"))


def _tick_until(scene: ArenaScene, predicate, limit: int = 120) -> bool:
    for _ in range(limit):
        scene.tick(FIXED_DT)
        if predicate():
            return True
    return False


def lina_q_scene(
    scene: ArenaScene, surface: pygame.Surface, name: str, flame: bool
) -> None:
    scene.set_character("lina")
    scene.set_enemy("dummy")
    scene.reset()
    scene.player.flame_time = 5.0 if flame else 0.0
    if flame:
        scene.player.anim.set_variant("flame")
    scene.enemy.x = scene.player.x + 260.0
    scene.enemy.y = scene.stage.ground_y
    scene.enemy.on_ground = True
    scene.player.facing = 1
    scene.player.start_attack("q", scene, scene.enemy)
    if not _tick_until(scene, lambda: bool(scene.projectiles)):
        return
    scene.draw(surface)
    save(surface, f"{name}_cast")
    for index in range(3):
        for _ in range(3):
            scene.tick(FIXED_DT)
        scene.draw(surface)
        save(surface, f"{name}_flight_{index}")
    if _tick_until(scene, lambda: not scene.projectiles, limit=120):
        scene.draw(surface)
        save(surface, f"{name}_impact")

    # Left-facing mirror check (sprite flip + mirrored anchor).
    scene.reset()
    scene.player.flame_time = 5.0 if flame else 0.0
    if flame:
        scene.player.anim.set_variant("flame")
    scene.enemy.x = scene.player.x - 260.0
    scene.enemy.y = scene.stage.ground_y
    scene.enemy.on_ground = True
    scene.player.facing = -1
    scene.player.start_attack("q", scene, scene.enemy)
    if _tick_until(scene, lambda: bool(scene.projectiles)):
        for _ in range(6):
            scene.tick(FIXED_DT)
        scene.draw(surface)
        save(surface, f"{name}_left")


def veno_scene(
    scene: ArenaScene, surface: pygame.Surface, name: str, attack_id: str
) -> None:
    scene.set_character("lina")
    scene.set_enemy("veno")
    scene.reset()
    veno = scene.enemy
    player = scene.player
    veno.ai_enabled = False
    player.x = veno.x - 300.0
    player.y = scene.stage.ground_y
    player.on_ground = True
    veno.facing = -1
    veno.force_attack(scene, player, attack_id)
    if not _tick_until(scene, lambda: bool(scene.projectiles) or attack_id == "veno_bite"):
        return
    scene.draw(surface)
    save(surface, f"{name}_cast")
    for index in range(3):
        for _ in range(3):
            scene.tick(FIXED_DT)
        scene.draw(surface)
        save(surface, f"{name}_flight_{index}")
    impact_kind = {
        "veno_poison": "veno_poison_impact",
        "veno_web": "veno_web_impact",
        "veno_bite": "veno_bite_hit",
    }.get(attack_id, "")
    hit = _tick_until(
        scene,
        lambda: any(effect.kind == impact_kind for effect in scene.fx_effects),
        limit=120,
    )
    if hit:
        scene.draw(surface)
        save(surface, f"{name}_impact")


def veno_group_scene(scene: ArenaScene, surface: pygame.Surface) -> None:
    scene.set_character("lina")
    scene.set_enemy("veno")
    scene.reset()
    scene.draw(surface)
    save(surface, "veno_group_spawn")


def poison_status_scene(scene: ArenaScene, surface: pygame.Surface) -> None:
    scene.set_character("lina")
    scene.set_enemy("dummy")
    scene.reset()
    scene.enemy.x = scene.player.x + 260.0
    scene.enemy.y = scene.stage.ground_y
    scene.enemy.on_ground = True
    scene.player.statuses.add(
        "poison", 3.0, source="preview", dps=1.0
    )
    scene.sim_time = 0.0
    scene.draw(surface)
    save(surface, "poison_status_green")
    scene.sim_time = 0.18
    scene.draw(surface)
    save(surface, "poison_status_purple")
    scene.player.statuses.clear()


def hover_scene(scene: ArenaScene, surface: pygame.Surface) -> None:
    scene.set_character("lina")
    scene.set_enemy("veno")
    scene.reset()
    veno = scene.enemy
    veno.ai_enabled = False
    veno.mode = "hover"
    veno.on_ground = False
    veno.y = scene.stage.ground_y - 220.0
    veno.vy = 0.0
    veno.hover_phase = 0.7
    scene.draw(surface)
    save(surface, "veno_hover_silk")


def bite_scene(scene: ArenaScene, surface: pygame.Surface) -> None:
    scene.set_character("lina")
    scene.set_enemy("veno")
    scene.reset()
    veno = scene.enemy
    player = scene.player
    veno.ai_enabled = False
    player.x = veno.x - 80.0
    player.y = scene.stage.ground_y
    player.on_ground = True
    veno.facing = -1
    veno.force_attack(scene, player, "veno_bite")
    hit = _tick_until(
        scene,
        lambda: any(effect.kind == "veno_bite_hit" for effect in scene.fx_effects),
        limit=60,
    )
    if hit:
        scene.draw(surface)
        save(surface, "veno_bite_hit")


def main() -> int:
    global OUT
    parser = argparse.ArgumentParser()
    parser.add_argument("--lina-normal-dir", type=Path, default=None)
    parser.add_argument("--lina-flame-dir", type=Path, default=None)
    parser.add_argument("--web-sprite", type=Path, default=None)
    parser.add_argument("--out-dir", type=Path, default=OUT)
    args = parser.parse_args()
    OUT = args.out_dir

    pygame.init()
    pygame.display.set_mode((SCREEN_W, SCREEN_H))
    store = JsonStore()
    scene = ArenaScene(store)
    surface = pygame.Surface((SCREEN_W, SCREEN_H)).convert()
    override_assets(args)

    lina_q_scene(scene, surface, "lina_q_normal", flame=False)
    lina_q_scene(scene, surface, "lina_q_flame", flame=True)
    veno_scene(scene, surface, "veno_poison", "veno_poison")
    veno_scene(scene, surface, "veno_web", "veno_web")
    veno_group_scene(scene, surface)
    bite_scene(scene, surface)
    poison_status_scene(scene, surface)
    hover_scene(scene, surface)

    pygame.quit()
    print(OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
