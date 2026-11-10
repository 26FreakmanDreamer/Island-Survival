"""Arena scene: tick order, debug controls, projectiles and rendering."""

from __future__ import annotations

import math
import random

import pygame

from .combat import attack_damage
from .config import ASSETS_DIR, FIXED_DT, SCREEN_W
from .debug import DebugOverlay, DebugPanel
from .fighter import Fighter, FighterState
from .fx import (
    BiteArcFx,
    FxEffect,
    PhantomBindBackFx,
    PhantomBindFrontFx,
    PoisonSplashFx,
    Q_WAVE_DRAW_OFFSET_Y,
    RingBurstFx,
    SilkCastFx,
    SpriteStripFx,
    WebImpactFx,
)
from .hud import HUD
from .input import InputState
from .particles import ParticleSystem, draw_knock_up_vortex
from .projectile import (
    AimedProjectile,
    AxeThrow,
    CreepyBullet,
    CreepyDownBullet,
    CreepyHomingBullet,
    EiraIceShardProjectile,
    EiraSnowballProjectile,
    QWave,
    ShadowBindProjectile,
    ShadowFlashProjectile,
    ShadowKunaiProjectile,
    ShurikenProjectile,
    SonicWave,
    SwordWave,
    WitchLightningProjectile,
    WitchPotionProjectile,
)
from .roster import create_fighter
from .stage import Stage
from .slash_fx import SlashEffect
from .special_skills import SpecialSkills

DEBUG_KEYS = {
    pygame.K_F1,
    pygame.K_F2,
    pygame.K_F5,
    pygame.K_F6,
    pygame.K_F7,
    pygame.K_F8,
    pygame.K_F9,
    pygame.K_F10,
    pygame.K_F11,
    pygame.K_F12,
    pygame.K_v,
    pygame.K_c,
    pygame.K_x,
    pygame.K_z,
    pygame.K_b,
    pygame.K_LEFTBRACKET,
    pygame.K_RIGHTBRACKET,
    pygame.K_LEFT,
    pygame.K_RIGHT,
    pygame.K_PAGEUP,
    pygame.K_PAGEDOWN,
}

SKILL_KEYS = {
    pygame.K_v: 0,
    pygame.K_c: 1,
    pygame.K_x: 2,
    pygame.K_z: 3,
}

_FREEZE_SHELL_CACHE: dict[tuple[str, float], pygame.Surface | None] = {}
_FREEZE_FOOT_CACHE: dict[tuple[str, float], pygame.Surface | None] = {}


def _freeze_asset(name: str, cache: dict) -> pygame.Surface | None:
    path = ASSETS_DIR / "frames" / "status" / "fx" / name
    try:
        mtime = path.stat().st_mtime
    except OSError:
        return None
    key = (str(path), mtime)
    if key in cache:
        cached = cache[key]
        return cached.copy() if cached is not None else None
    try:
        image = pygame.image.load(str(path)).convert_alpha()
    except (OSError, pygame.error):
        cache[key] = None
        return None
    cache[key] = image
    return image.copy()


class ArenaScene:
    def __init__(self, store) -> None:
        self.store = store
        self.input = InputState(float(store.stats["combat"]["input_buffer"]))
        self.hud = HUD()
        self.overlay = DebugOverlay()
        self.panel = DebugPanel()
        self.show_overlay = False
        self.show_panel = False
        self.fps = 0.0
        self.hitstop = 0.0
        self.tick_count = 0
        self.sim_time = 0.0
        self.last_hit: dict | None = None
        self.debug_hitboxes: list[pygame.Rect] = []
        self.projectiles: list = []
        # Persistent skill hazards (ice ball, ice spike warning, poison zone).
        self.hazards: list = []
        self.mouse_x = SCREEN_W * 0.5
        self._freeze_seen: set[int] = set()
        self.slash_effects: list[SlashEffect] = []
        self.fx_effects: list[FxEffect] = []
        self.status_demo_index = 0
        self.time_scales = [0.25, 0.5, 1.0, 2.0]
        self.time_scale_index = 2
        self.time_scale = 1.0
        self.lock_on = False
        defaults = store.debug.get("roster", {})
        characters = store.roster.get("characters", {})
        enemies = store.roster.get("enemies", {})
        self.character_id = str(
            defaults.get("default_character", next(iter(characters), ""))
        )
        self.enemy_id = str(defaults.get("default_enemy", next(iter(enemies), "")))
        self.character_spec: dict = {}
        self.enemy_spec: dict = {}
        self.match_over: str | None = None
        self.stage: Stage
        self.player: Fighter
        self.enemy: Fighter
        self.enemies: list[Fighter] = []
        # Smoke tests force a single Veno for isolated checks; the game uses
        # the roster's count (3 for Veno).
        self.enemy_count_override: int | None = None
        self.particles = ParticleSystem()
        self.special = SpecialSkills(store)
        self.rebuild()

    # --- lifecycle ----------------------------------------------------------
    def _resolve_ids(self) -> None:
        characters = self.store.roster.get("characters", {})
        enemies = self.store.roster.get("enemies", {})
        defaults = self.store.debug.get("roster", {})
        if self.character_id not in characters:
            self.character_id = str(
                defaults.get("default_character", next(iter(characters), ""))
            )
        if self.enemy_id not in enemies:
            self.enemy_id = str(
                defaults.get("default_enemy", next(iter(enemies), ""))
            )
        self.character_spec = characters[self.character_id]
        self.enemy_spec = enemies[self.enemy_id]

    def _enemy_count(self) -> int:
        if self.enemy_count_override is not None:
            return max(1, int(self.enemy_count_override))
        return max(1, int(self.enemy_spec.get("count", 1)))

    def _place_enemies(self) -> None:
        """Apply per-index spawn offsets, flying heights and ground/hover modes."""
        if not self.enemies:
            return
        spawn_key = str(self.enemy_spec.get("spawn", "veno_spawn"))
        base_x, base_y = self.stage.spawn(spawn_key)
        if self.enemy_count_override is not None:
            # Isolated smoke checks use the base spawn and stay on the ground.
            offsets: list = []
            modes: list = []
            heights: list = []
            jitter = 0.0
        else:
            offsets = list(self.enemy_spec.get("spawn_offsets", []))
            modes = list(self.enemy_spec.get("spawn_modes", []))
            heights = list(self.enemy_spec.get("spawn_heights", []))
            jitter = float(self.enemy_spec.get("spawn_jitter", 0.0))
        # Flying enemies always spawn airborne. This branch deliberately sits
        # outside the enemy_count_override suppression so isolated smoke
        # checks still get a flier rather than a grounded Bat.
        flying_spec = bool(self.enemy_spec.get("flying", False))
        low, high = self.stage.walls
        for index, enemy in enumerate(self.enemies):
            offset = float(offsets[index]) if index < len(offsets) else 0.0
            x = base_x + offset
            if jitter > 0.0:
                x += random.uniform(-jitter, jitter)
            is_flying = flying_spec or bool(getattr(enemy, "flying", False))
            half = (
                enemy.hurtbox_width * 0.5
                if is_flying
                else enemy.stage_half_width
            )
            enemy.x = max(low + half, min(high - half, x))
            enemy.y = base_y
            enemy.vx = 0.0
            enemy.vy = 0.0
            enemy.on_ground = True
            if hasattr(enemy, "mode"):
                enemy.mode = "ground"
            enemy.state = FighterState.IDLE
            if is_flying:
                enemy.on_ground = False
                enemy.vy = 0.0
                altitude = None
                if index < len(heights):
                    altitude = float(heights[index])
                    if hasattr(enemy, "flight_min_height"):
                        altitude = max(
                            float(enemy.flight_min_height),
                            min(float(enemy.flight_max_height), altitude),
                        )
                if altitude is not None:
                    enemy.y = self.stage.ground_y - altitude
                    if hasattr(enemy, "cruise_height"):
                        enemy.cruise_height = altitude
                elif hasattr(enemy, "cruise_height"):
                    enemy.cruise_height = max(
                        0.0, self.stage.ground_y - base_y
                    )
                if hasattr(enemy, "bob_phase"):
                    enemy.bob_phase = index * 1.1
                if hasattr(enemy, "mode"):
                    enemy.mode = "fly"
                enemy.state = FighterState.AIR
                if enemy.anim is not None:
                    enemy.anim.set_clip("fly")
            elif index < len(modes) and modes[index] == "hover" and hasattr(
                enemy, "hover_base"
            ):
                enemy.mode = "hover"
                enemy.on_ground = False
                enemy.y = self.stage.ground_y - float(enemy.hover_base)
                enemy.vy = 0.0
                enemy.hover_time = 0.0
                enemy.hover_phase = 0.0
                enemy.state = FighterState.AIR
                if enemy.anim is not None:
                    enemy.anim.set_clip("hover")
            elif enemy.anim is not None:
                enemy.anim.set_clip("idle")
            if hasattr(enemy, "flight_remaining") and hasattr(
                enemy, "flight_stagger"
            ):
                enemy.flight_remaining += index * enemy.flight_stagger

    def _pick_primary(self) -> None:
        living = [enemy for enemy in self.enemies if enemy.hp > 0.0]
        if living:
            self.enemy = min(living, key=lambda enemy: abs(enemy.x - self.player.x))
        elif self.enemies:
            self.enemy = self.enemies[0]

    def _rebuild_fighters(self) -> None:
        blocks_enabled = self.stage.blocks_enabled
        self.player = create_fighter(self.character_spec, self.store, self.stage)
        self.enemies = [
            create_fighter(self.enemy_spec, self.store, self.stage)
            for _ in range(self._enemy_count())
        ]
        self.enemy = self.enemies[0]
        self._place_enemies()
        self._pick_primary()
        self.stage.blocks_enabled = blocks_enabled
        self.projectiles = []
        self.hazards = []
        self._freeze_seen.clear()
        self.slash_effects = []
        self.fx_effects = []
        self.particles = ParticleSystem()
        self.debug_hitboxes = []
        self.hitstop = 0.0
        self.tick_count = 0
        self.sim_time = 0.0
        self.last_hit = None
        self.match_over = None
        self.status_demo_index = 0
        self.lock_on = False
        self.input.clear()
        self.special.message_time = 0.0
        self._force_ai_off()
        self._resolve_stage_overlaps()
        self._sync_enemy_stats_from_player()

    def _sync_enemy_stats_from_player(self) -> None:
        """Let enemies that mirror the player's stats copy them at battle start."""
        for enemy in self.enemies:
            sync = getattr(enemy, "sync_from_player", None)
            if sync is not None:
                sync(self.player, full_heal=True)

    def _resolve_stage_overlaps(self) -> None:
        """Push fighters out of solids after a rebuild or B re-enable."""
        fighters = [self.player, *self.enemies]
        for fighter in fighters:
            if fighter is not None:
                self.stage.resolve_overlap(fighter)

    def _force_ai_off(self) -> None:
        for enemy in self.enemies:
            if hasattr(enemy, "ai_enabled"):
                enemy.ai_enabled = False

    def _stage_config(self) -> dict:
        variant = self.enemy_spec.get("stage_variant")
        if variant:
            return self.store.debug["stage_variants"][variant]
        return self.store.debug["stage"]

    def rebuild(self) -> None:
        self._resolve_ids()
        self.stage = Stage(self._stage_config())
        self._rebuild_fighters()
        self.special.reset()
        self.input.buffer.max_age = float(self.store.stats["combat"]["input_buffer"])

        debug_cfg = self.store.debug.get("debug", {})
        self.time_scales = list(debug_cfg.get("time_scales", [0.25, 0.5, 1.0, 2.0]))
        start_scale = float(debug_cfg.get("start_time_scale", 1.0))
        if self.time_scales:
            self.time_scale_index = min(
                range(len(self.time_scales)),
                key=lambda index: abs(float(self.time_scales[index]) - start_scale),
            )
            self.time_scale = float(self.time_scales[self.time_scale_index])
        else:
            self.time_scales = [1.0]
            self.time_scale_index = 0
            self.time_scale = 1.0

    def set_character(self, character_id: str) -> bool:
        characters = self.store.roster.get("characters", {})
        if character_id not in characters or character_id == self.character_id:
            return False
        self.character_id = character_id
        self.character_spec = characters[character_id]
        self._rebuild_fighters()
        return True

    def set_enemy(self, enemy_id: str) -> bool:
        enemies = self.store.roster.get("enemies", {})
        if enemy_id not in enemies or enemy_id == self.enemy_id:
            return False
        self.enemy_id = enemy_id
        self.enemy_spec = enemies[enemy_id]
        blocks_enabled = self.stage.blocks_enabled
        self.stage = Stage(self._stage_config())
        self.stage.blocks_enabled = blocks_enabled
        self._rebuild_fighters()
        return True

    def cycle_character(self, step: int = 1) -> bool:
        ids = list(self.store.roster.get("characters", {}))
        if len(ids) <= 1 or self.character_id not in ids:
            return False
        index = ids.index(self.character_id)
        return self.set_character(ids[(index + step) % len(ids)])

    def cycle_enemy(self) -> bool:
        ids = list(self.store.roster.get("enemies", {}))
        if len(ids) <= 1 or self.enemy_id not in ids:
            return False
        index = ids.index(self.enemy_id)
        return self.set_enemy(ids[(index + 1) % len(ids)])

    def toggle_lock_on(self) -> bool:
        """Toggle attack lock-on; returns the new state."""
        self.lock_on = not self.lock_on
        return self.lock_on

    def face_target_if_locked(self, fighter, target) -> None:
        """At attack start, face the living enemy while lock-on is active."""
        if not self.lock_on or target is None or target.hp <= 0.0:
            return
        dx = target.x - fighter.x
        if abs(dx) > 8.0:
            fighter.facing = 1 if dx > 0.0 else -1

    def opponent_of(self, fighter):
        if fighter is self.player:
            living = [enemy for enemy in self.enemies if enemy.hp > 0.0]
            if not living:
                return None
            return min(living, key=lambda enemy: abs(enemy.x - fighter.x))
        if fighter in self.enemies:
            return self.player
        return None

    def targets_for(self, attacker) -> list:
        """Living targets for a melee hitbox or projectile."""
        if attacker is self.player:
            # The phantom form has no combat hitbox: player attacks and
            # projectiles pass through instead of being consumed.
            return [
                enemy
                for enemy in self.enemies
                if enemy.hp > 0.0
                and not getattr(enemy, "phantom_form", False)
                and not getattr(enemy, "no_hitbox", False)
                and not getattr(enemy, "hidden", False)
            ]
        if attacker in self.enemies:
            if (
                self.player.hp > 0.0
                and not getattr(self.player, "no_hitbox", False)
                and not getattr(self.player, "hidden", False)
            ):
                return [self.player]
            return []
        return []

    def reload_data(self) -> bool:
        if not self.store.reload():
            return False
        try:
            self.rebuild()
        except Exception as exc:  # noqa: BLE001 - reported in the debug panel
            self.store.last_error = f"{type(exc).__name__}: {exc}"
            self.store.last_ok = False
            return False
        return True

    def reset(self) -> None:
        self.player.reset()
        for enemy in self.enemies:
            enemy.reset()
        self._place_enemies()
        self._pick_primary()
        self._force_ai_off()
        self._resolve_stage_overlaps()
        self._sync_enemy_stats_from_player()
        self.projectiles = []
        self.hazards = []
        self._freeze_seen.clear()
        self.slash_effects = []
        self.fx_effects = []
        self.particles = ParticleSystem()
        self.debug_hitboxes = []
        self.hitstop = 0.0
        self.tick_count = 0
        self.sim_time = 0.0
        self.last_hit = None
        self.match_over = None
        self.input.clear()
        self.special.reset()

    # --- simulation ---------------------------------------------------------
    def tick(self, dt: float) -> None:
        self.tick_count += 1
        self.sim_time += dt

        if self.hitstop > 0.0:
            self.hitstop = max(0.0, self.hitstop - dt)
            return

        self.debug_hitboxes.clear()
        self.input.update(dt)
        self._update_slash_effects(dt)
        self._update_fx_effects(dt)
        self._pick_primary()
        self.special.update(dt, self)
        self.player.update(dt, self.input, self.enemy, self)
        for enemy in self.enemies:
            enemy.update(dt, self)
        self._separate_fighters(dt)
        self._separate_enemies(dt)
        self._check_match_end()
        self._flush_block_fx()

        if self.hitstop > 0.0:
            return

        for projectile in self.projectiles:
            projectile.update(dt, self)
        self.projectiles = [projectile for projectile in self.projectiles if projectile.alive]
        for hazard in self.hazards:
            hazard.update(dt, self)
        self.hazards = [hazard for hazard in self.hazards if hazard.alive]
        self._update_freeze_fx()
        self._flush_block_fx()
        self._check_match_end()
        self.particles.update(dt)

        if getattr(self.player, "flame_time", 0.0) > 0.0:
            self.particles.emit_flame(self.player.x, self.player.y)
        for enemy in self.enemies:
            if enemy.hp > 0.0 and enemy.statuses.has("burn"):
                self.particles.emit_flame(enemy.x, enemy.y - 90.0)
        if self.tick_count % 2 == 0:
            if self.player.statuses.has("poison") and self.player.hp > 0.0:
                self.particles.emit_poison(self.player.x, self.player.y)
            for enemy in self.enemies:
                if enemy.statuses.has("poison") and enemy.hp > 0.0:
                    self.particles.emit_poison(enemy.x, enemy.y)

    def _update_freeze_fx(self) -> None:
        """Spawn the thaw shatter when a fighter leaves the freeze state."""
        frozen: set[int] = set()
        for fighter in [self.player, *self.enemies]:
            if fighter.hp <= 0.0:
                continue
            is_frozen = fighter.statuses.has("freeze")
            if is_frozen:
                frozen.add(id(fighter))
            if id(fighter) in self._freeze_seen and not is_frozen:
                self._spawn_thaw_fx(fighter)
        self._freeze_seen = frozen

    def _spawn_thaw_fx(self, fighter) -> None:
        fx_dir = ASSETS_DIR / "frames" / "eira" / "fx"
        frames = [
            fx_dir / f"eira_e_release_v1_fx_frozen_hit_{index:02d}.png"
            for index in range(3)
        ]
        self.fx_effects.append(
            SpriteStripFx(
                frames, [0.05, 0.07, 0.10], fighter.x,
                fighter.y - fighter.hurtbox_dims[1] * 0.5,
                scale=0.55, kind="eira_thaw",
            )
        )

    def _can_stand(self, fighter, x: float) -> bool:
        half = fighter.stage_half_width
        low, high = self.stage.walls
        if x - half < low or x + half > high:
            return False
        _, height = fighter.hurtbox_dims
        body = pygame.Rect(
            round(x - half), round(fighter.y - height), round(half * 2), round(height)
        )
        if not self.stage.blocks_enabled:
            return True
        for block in self.stage.blocks:
            if fighter.y <= block.top + 1:
                continue
            if body.colliderect(block):
                return False
        return True

    def _separate_fighters(self, dt: float = FIXED_DT) -> None:
        """Keep each enemy's center from crossing the player's center."""
        runtime = getattr(self.player, "attack_runtime", None)
        if runtime is not None and runtime.data.get("pass_through_enemy"):
            return
        if self.player.hp <= 0.0:
            return
        # The enemy yields first, but only on its current side. Flipping to
        # the other side of the player would teleport it across the block
        # that blocked the first target. If its side is blocked, push the
        # player away instead. Both pushes are capped so a deep overlap
        # slides apart over a few ticks instead of teleporting.
        max_step = float(
            self.store.stats["combat"].get("separation_speed", 600.0)
        ) * dt
        for enemy in self.enemies:
            if enemy.hp <= 0.0 or not enemy.entry.get("separates", False):
                continue
            if getattr(enemy, "ignore_separation", False):
                continue
            if getattr(enemy, "no_hitbox", False) or getattr(enemy, "hidden", False):
                continue
            player_body = self.stage.body_rect(self.player)
            enemy_body = self.stage.body_rect(enemy)
            if not player_body.colliderect(enemy_body):
                continue

            min_dist = self.player.stage_half_width + enemy.stage_half_width
            dx = enemy.x - self.player.x
            if abs(dx) >= min_dist:
                continue
            if abs(dx) < 0.01:
                side = enemy.facing
            else:
                side = 1 if dx > 0.0 else -1
            target_x = self.player.x + side * min_dist
            if self._can_stand(enemy, enemy.x) and self._can_stand(
                enemy, target_x
            ):
                self._step_x(enemy, target_x, max_step)
            if abs(enemy.x - self.player.x) < min_dist:
                player_target = enemy.x - side * min_dist
                if self._can_stand(self.player, self.player.x) and self._can_stand(
                    self.player, player_target
                ):
                    self._step_x(self.player, player_target, max_step)

    def _separate_enemies(self, dt: float = FIXED_DT) -> None:
        """Keep same-altitude enemies from stacking on the same x."""
        max_step = float(
            self.store.stats["combat"].get("separation_speed", 600.0)
        ) * dt
        for index, first in enumerate(self.enemies):
            if first.hp <= 0.0 or getattr(first, "ignore_separation", False):
                continue
            if getattr(first, "no_hitbox", False) or getattr(first, "hidden", False):
                continue
            first_body = self.stage.body_rect(first)
            for second in self.enemies[index + 1:]:
                if second.hp <= 0.0 or getattr(
                    second, "ignore_separation", False
                ):
                    continue
                if getattr(second, "no_hitbox", False) or getattr(second, "hidden", False):
                    continue
                if not first_body.colliderect(self.stage.body_rect(second)):
                    continue
                min_dist = first.stage_half_width + second.stage_half_width
                dx = second.x - first.x
                if abs(dx) >= min_dist:
                    continue
                side = 1 if dx >= 0.0 else -1
                target_x = first.x + side * min_dist
                if self._can_stand(second, second.x) and self._can_stand(
                    second, target_x
                ):
                    self._step_x(second, target_x, max_step)

    def _step_x(self, fighter, target_x: float, max_step: float) -> None:
        """Move toward a target without crossing into a block in one tick."""
        delta = target_x - fighter.x
        if abs(delta) > max_step:
            delta = max_step if delta > 0.0 else -max_step
        if delta and self._can_stand(fighter, fighter.x + delta):
            self.stage.move_x(fighter, delta)

    def push_apart(self, a, b) -> None:
        """Resolve an overlap after a pass-through dash.

        The enemy yields first; if a wall or block prevents that, push the
        dasher back to the other side.
        """
        if a.hp <= 0.0 or b.hp <= 0.0:
            return
        if not self.stage.body_rect(a).colliderect(self.stage.body_rect(b)):
            return
        min_dist = a.stage_half_width + b.stage_half_width
        dx = b.x - a.x
        side = 1 if dx >= 0.0 else -1
        if abs(dx) < 0.01:
            side = -a.facing
        target_x = a.x + side * min_dist
        if self._can_stand(b, b.x) and self._can_stand(b, target_x):
            self.stage.move_x(b, target_x - b.x)
            return
        a_target = b.x - side * min_dist
        if self._can_stand(a, a.x) and self._can_stand(a, a_target):
            self.stage.move_x(a, a_target - a.x)

    def _update_slash_effects(self, dt: float) -> None:
        for effect in self.slash_effects:
            effect.update(dt)
        self.slash_effects = [effect for effect in self.slash_effects if effect.alive]

    def _update_fx_effects(self, dt: float) -> None:
        for effect in self.fx_effects:
            effect.update(dt)
        self.fx_effects = [effect for effect in self.fx_effects if effect.alive]
        if len(self.fx_effects) > 64:
            self.fx_effects = self.fx_effects[-64:]

    def spawn_special_block_fx(self, x: float, y: float) -> None:
        """Gold flash when Sacred Shield negates a hit."""
        self.fx_effects.append(
            RingBurstFx(
                x,
                y,
                (255, 215, 90),
                life=0.28,
                start_radius=14.0,
                end_radius=64.0,
                width=5,
                sparks=8,
                spark_color=(255, 250, 210),
                kind="special_block",
            )
        )
        self.particles.emit_burst(
            x, y, (255, 215, 90), count=10, speed=220.0
        )

    def _flush_block_fx(self) -> None:
        if self.player.blocked_hits <= 0:
            return
        self.player.blocked_hits = 0
        self.spawn_special_block_fx(self.player.x, self.player.y - 110.0)

    def spawn_projectile_cast_fx(self, projectile) -> None:
        """Emit the short muzzle/hand effect when a projectile is created."""
        visual_kind = getattr(projectile, "visual_kind", None)
        if visual_kind is None:
            return
        x = float(projectile.x)
        y = float(projectile.y)
        direction = getattr(projectile, "direction", 1)
        ux = float(getattr(projectile, "ux", float(direction)))
        uy = float(getattr(projectile, "uy", 0.0))

        if visual_kind == "lina_q":
            cast_y = y + Q_WAVE_DRAW_OFFSET_Y
            self.fx_effects.append(
                RingBurstFx(
                    x, cast_y, (60, 220, 215), life=0.14,
                    start_radius=6.0, end_radius=28.0, width=2,
                    sparks=4, kind="lina_q_cast",
                )
            )
            self.particles.emit_burst(
                x, cast_y, (150, 248, 242), 6, speed=150.0, life=(0.10, 0.20)
            )
        elif visual_kind == "lina_q_flame":
            cast_y = y + Q_WAVE_DRAW_OFFSET_Y
            self.fx_effects.append(
                RingBurstFx(
                    x, cast_y, (255, 150, 70), life=0.14,
                    start_radius=6.0, end_radius=28.0, width=2,
                    sparks=4, spark_color=(255, 220, 140),
                    kind="lina_q_flame_cast",
                )
            )
            self.particles.emit_embers(x, cast_y, 3)
        elif visual_kind == "veno_poison":
            self.particles.emit_mist(
                x + ux * 8.0, y + uy * 8.0,
                color=(55, 160, 75), count=5,
            )
            self.fx_effects.append(
                RingBurstFx(
                    x, y, (60, 170, 75), life=0.12,
                    start_radius=4.0, end_radius=18.0, width=2,
                    kind="veno_poison_cast",
                )
            )
        elif visual_kind == "veno_web":
            self.fx_effects.append(
                SilkCastFx(x, y, ux, uy, life=0.12)
            )
            self.particles.emit_burst(
                x + ux * 10.0, y + uy * 10.0, (220, 255, 200), 3,
                speed=90.0, life=(0.10, 0.18), gravity=90.0,
            )
        elif visual_kind == "rhea_shuriken":
            self.fx_effects.append(
                RingBurstFx(
                    x, y, (228, 236, 255), life=0.12,
                    start_radius=4.0, end_radius=20.0, width=2,
                    sparks=3, spark_color=(255, 248, 215),
                    kind="rhea_shuriken_cast",
                )
            )
            self.particles.emit_burst(
                x + ux * 8.0, y + uy * 8.0, (238, 242, 255), 4,
                speed=140.0, life=(0.08, 0.16),
            )
        elif visual_kind == "rhea_poison_shuriken":
            self.fx_effects.append(
                RingBurstFx(
                    x, y, (90, 205, 115), life=0.14,
                    start_radius=4.0, end_radius=22.0, width=2,
                    sparks=4, spark_color=(180, 115, 235),
                    kind="rhea_poison_shuriken_cast",
                )
            )
            self.particles.emit_mist(
                x + ux * 8.0, y + uy * 8.0, color=(65, 175, 85), count=5
            )
            self.particles.emit_burst(
                x + ux * 6.0, y + uy * 6.0, (160, 95, 220), 4,
                speed=120.0, life=(0.10, 0.18),
            )
        elif visual_kind == "eira_snowball":
            self.fx_effects.append(
                SpriteStripFx(
                    [ASSETS_DIR / "frames" / "eira" / "fx"
                     / "eira_snowball_v1_fx_release.png"],
                    [0.06], x, y, scale=0.5, kind="eira_snowball_cast",
                )
            )
            self.particles.emit_burst(
                x + ux * 8.0, y + uy * 8.0, (220, 245, 255), 4,
                speed=130.0, life=(0.08, 0.16),
            )
        elif visual_kind == "eira_ice_shard":
            self.fx_effects.append(
                SpriteStripFx(
                    [
                        ASSETS_DIR / "frames" / "eira" / "fx"
                        / f"eira_ice_shard_v1_fx_release_{index:02d}.png"
                        for index in range(2)
                    ],
                    [0.03, 0.03], x, y, scale=0.55, kind="eira_ice_shard_cast",
                )
            )
            self.particles.emit_burst(
                x + ux * 8.0, y + uy * 8.0, (180, 235, 255), 4,
                speed=140.0, life=(0.08, 0.16),
            )
        elif visual_kind in (
            "witch_lightning_forward",
            "witch_lightning_up",
            "witch_lightning_down",
        ):
            self.fx_effects.append(
                RingBurstFx(
                    x, y, (185, 120, 255), life=0.14,
                    start_radius=6.0, end_radius=30.0, width=2,
                    sparks=4, spark_color=(240, 220, 255),
                    kind="witch_lightning_cast",
                )
            )
            self.particles.emit_burst(
                x + ux * 8.0, y + uy * 8.0, (210, 165, 255), 5,
                speed=150.0, life=(0.08, 0.18),
            )
        elif visual_kind == "witch_potion":
            self.fx_effects.append(
                RingBurstFx(
                    x, y, (90, 200, 100), life=0.14,
                    start_radius=5.0, end_radius=24.0, width=2,
                    sparks=3, spark_color=(210, 255, 180),
                    kind="witch_potion_cast",
                )
            )
            self.particles.emit_mist(x, y, color=(70, 175, 85), count=4)
        elif visual_kind == "shadow_kunai":
            self.fx_effects.append(
                RingBurstFx(
                    x, y, (175, 105, 255), life=0.12,
                    start_radius=4.0, end_radius=22.0, width=2,
                    sparks=4, spark_color=(240, 220, 255),
                    kind="shadow_kunai_cast",
                )
            )
            self.particles.emit_burst(
                x + ux * 8.0, y + uy * 8.0, (205, 150, 255), 4,
                speed=140.0, life=(0.08, 0.16),
            )
        elif visual_kind == "shadow_phantom_bind":
            self.fx_effects.append(
                RingBurstFx(
                    x, y, (150, 80, 235), life=0.14,
                    start_radius=6.0, end_radius=26.0, width=2,
                    sparks=4, spark_color=(235, 215, 255),
                    kind="shadow_phantom_bind_cast",
                )
            )
            self.particles.emit_mist(x, y, color=(120, 70, 200), count=4)
        elif visual_kind == "shadow_phantom_flash":
            self.fx_effects.append(
                RingBurstFx(
                    x, y, (190, 120, 255), life=0.12,
                    start_radius=5.0, end_radius=22.0, width=2,
                    sparks=4, spark_color=(240, 220, 255),
                    kind="shadow_phantom_flash_cast",
                )
            )
            self.particles.emit_burst(
                x + ux * 8.0, y + uy * 8.0, (215, 170, 255), 4,
                speed=140.0, life=(0.08, 0.16),
            )
        elif visual_kind == "bat_sonic":
            self.fx_effects.append(
                RingBurstFx(
                    x, y, (210, 190, 255), life=0.14,
                    start_radius=6.0, end_radius=30.0, width=2,
                    sparks=4, spark_color=(245, 235, 255),
                    kind="bat_sonic_cast",
                )
            )
            self.particles.emit_burst(
                x + ux * 8.0, y + uy * 8.0, (235, 220, 255), 4,
                speed=120.0, life=(0.10, 0.18),
            )
        elif visual_kind in ("creepy_bullet", "creepy_down_bullet"):
            self.fx_effects.append(
                RingBurstFx(
                    x, y, (80, 230, 225), life=0.10,
                    start_radius=3.0, end_radius=16.0, width=2,
                    sparks=3, spark_color=(210, 255, 252),
                    kind="creepy_bullet_cast",
                )
            )
            self.particles.emit_burst(
                x + ux * 6.0, y + uy * 6.0, (170, 255, 250), 3,
                speed=130.0, life=(0.08, 0.16),
            )
        elif visual_kind == "creepy_homing_bullet":
            self.fx_effects.append(
                RingBurstFx(
                    x, y, (190, 120, 255), life=0.16,
                    start_radius=5.0, end_radius=26.0, width=2,
                    sparks=4, spark_color=(235, 220, 255),
                    kind="creepy_homing_cast",
                )
            )
            self.particles.emit_burst(
                x, y, (190, 120, 255), 5, speed=120.0,
                life=(0.10, 0.20),
            )

    def spawn_projectile_impact(self, projectile, target) -> None:
        """Emit the elemental hit effect at the same anchor as the hit particles."""
        visual_kind = getattr(projectile, "visual_kind", None)
        if visual_kind is None or target is None:
            return
        x = float(target.x)
        y = float(projectile.y)

        if visual_kind == "lina_q":
            self.fx_effects.append(
                RingBurstFx(
                    x, y, (60, 220, 215), life=0.18,
                    start_radius=8.0, end_radius=44.0, width=3,
                    sparks=6, kind="lina_q_impact",
                )
            )
            self.particles.emit_burst(
                x, y, (155, 250, 245), 12, speed=220.0
            )
        elif visual_kind == "lina_q_flame":
            self.fx_effects.append(
                RingBurstFx(
                    x, y, (255, 140, 70), life=0.18,
                    start_radius=8.0, end_radius=44.0, width=3,
                    sparks=6, spark_color=(255, 220, 140),
                    kind="lina_q_flame_impact",
                )
            )
            self.particles.emit_burst(
                x, y, (255, 160, 80), 10, speed=200.0
            )
            self.particles.emit_embers(x, y, 3)
        elif visual_kind == "veno_poison":
            self.fx_effects.append(PoisonSplashFx(x, y))
            self.fx_effects.append(
                RingBurstFx(
                    x, y, (60, 170, 75), life=0.20,
                    start_radius=6.0, end_radius=34.0, width=2,
                    kind="veno_poison_ring",
                )
            )
            self.particles.emit_burst(
                x, y, (75, 185, 90), 8, speed=170.0
            )
        elif visual_kind == "veno_web":
            self.fx_effects.append(WebImpactFx(x, y))
            self.fx_effects.append(
                RingBurstFx(
                    x, y, (235, 255, 220), life=0.16,
                    start_radius=10.0, end_radius=42.0, width=2,
                    sparks=3, spark_color=(255, 224, 90),
                    kind="veno_web_ring",
                )
            )
            self.particles.emit_burst(
                x, y, (255, 224, 90), 3, speed=120.0, life=(0.10, 0.20)
            )
        elif visual_kind == "rhea_shuriken":
            self.fx_effects.append(
                RingBurstFx(
                    x, y, (232, 240, 255), life=0.16,
                    start_radius=6.0, end_radius=30.0, width=2,
                    sparks=5, spark_color=(255, 240, 190),
                    kind="rhea_shuriken_impact",
                )
            )
            self.particles.emit_burst(
                x, y, (238, 242, 255), 9, speed=190.0
            )
        elif visual_kind == "rhea_poison_shuriken":
            self.fx_effects.append(PoisonSplashFx(x, y, kind="rhea_poison_impact"))
            self.fx_effects.append(
                RingBurstFx(
                    x, y, (90, 205, 115), life=0.20,
                    start_radius=6.0, end_radius=34.0, width=2,
                    sparks=4, spark_color=(180, 115, 235),
                    kind="rhea_poison_impact_ring",
                )
            )
            self.particles.emit_burst(
                x, y, (90, 200, 110), 8, speed=170.0
            )
            self.particles.emit_burst(
                x, y, (160, 95, 220), 5, speed=150.0
            )
        elif visual_kind == "eira_snowball":
            self.fx_effects.append(
                SpriteStripFx(
                    [
                        ASSETS_DIR / "frames" / "eira" / "fx"
                        / f"eira_snowball_v1_fx_impact_{index:02d}.png"
                        for index in range(4)
                    ],
                    [0.04, 0.05, 0.06, 0.07], x, y,
                    scale=0.5, kind="eira_snowball_impact",
                )
            )
            self.particles.emit_burst(x, y, (220, 245, 255), 8, speed=180.0)
        elif visual_kind == "eira_ice_shard":
            was_frozen = bool(getattr(projectile, "hit_target_was_frozen", False))
            prefix = (
                "eira_ice_shard_v1_fx_frozen_hit"
                if was_frozen
                else "eira_ice_shard_v1_fx_hit"
            )
            self.fx_effects.append(
                SpriteStripFx(
                    [
                        ASSETS_DIR / "frames" / "eira" / "fx"
                        / f"{prefix}_{index:02d}.png"
                        for index in range(4)
                    ],
                    [0.04, 0.05, 0.06, 0.07], x, y,
                    scale=0.55, kind="eira_ice_shard_impact",
                )
            )
            self.particles.emit_burst(x, y, (180, 235, 255), 7, speed=170.0)
        elif visual_kind in (
            "witch_lightning_forward",
            "witch_lightning_up",
            "witch_lightning_down",
        ):
            variant = visual_kind.rsplit("_", 1)[1]
            frames = [
                ASSETS_DIR / "frames" / "crooked_witch" / "fx"
                / f"crooked_witch_lightning_fx_v2_{variant}_{index:02d}.png"
                for index in range(6)
            ]
            self.fx_effects.append(
                SpriteStripFx(
                    frames, [0.06] * 6, x, y,
                    scale=0.35, kind="witch_lightning_impact_fx",
                )
            )
            self.fx_effects.append(
                RingBurstFx(
                    x, y, (185, 120, 255), life=0.18,
                    start_radius=8.0, end_radius=40.0, width=3,
                    sparks=6, spark_color=(240, 220, 255),
                    kind="witch_lightning_impact",
                )
            )
            self.particles.emit_burst(x, y, (205, 150, 255), 8, speed=190.0)
        elif visual_kind == "witch_potion":
            self.fx_effects.append(PoisonSplashFx(x, y, kind="witch_potion_impact"))
            self.fx_effects.append(
                RingBurstFx(
                    x, y, (80, 195, 95), life=0.20,
                    start_radius=6.0, end_radius=32.0, width=2,
                    sparks=4, spark_color=(210, 255, 180),
                    kind="witch_potion_impact_ring",
                )
            )
            self.particles.emit_burst(x, y, (90, 200, 110), 8, speed=170.0)
        elif visual_kind == "witch_fireball":
            self.fx_effects.append(
                RingBurstFx(
                    x, y, (255, 140, 60), life=0.18,
                    start_radius=8.0, end_radius=38.0, width=3,
                    sparks=5, spark_color=(255, 225, 150),
                    kind="witch_fireball_hit",
                )
            )
            self.particles.emit_embers(x, y, 4)
        elif visual_kind == "shadow_kunai":
            self.fx_effects.append(
                RingBurstFx(
                    x, y, (185, 110, 255), life=0.18,
                    start_radius=6.0, end_radius=34.0, width=2,
                    sparks=5, spark_color=(240, 220, 255),
                    kind="shadow_kunai_impact",
                )
            )
            self.particles.emit_burst(x, y, (205, 150, 255), 8, speed=180.0)
        elif visual_kind == "shadow_phantom_bind":
            self.fx_effects.append(
                RingBurstFx(
                    x, y, (150, 80, 235), life=0.20,
                    start_radius=8.0, end_radius=38.0, width=3,
                    sparks=5, spark_color=(235, 215, 255),
                    kind="shadow_phantom_bind_impact",
                )
            )
            self.fx_effects.append(PhantomBindBackFx(target, life=1.0))
            self.fx_effects.append(PhantomBindFrontFx(target, life=1.0))
            self.particles.emit_burst(x, y, (175, 110, 255), 8, speed=170.0)
        elif visual_kind == "shadow_phantom_flash":
            self.fx_effects.append(
                RingBurstFx(
                    x, y, (200, 140, 255), life=0.18,
                    start_radius=8.0, end_radius=40.0, width=3,
                    sparks=6, spark_color=(245, 225, 255),
                    kind="shadow_phantom_flash_impact",
                )
            )
            self.particles.emit_burst(x, y, (210, 160, 255), 9, speed=190.0)
        elif visual_kind == "bat_sonic":
            self.fx_effects.append(
                RingBurstFx(
                    x, y, (210, 190, 255), life=0.18,
                    start_radius=10.0, end_radius=44.0, width=3,
                    sparks=5, spark_color=(245, 235, 255),
                    kind="bat_sonic_impact",
                )
            )
            self.particles.emit_burst(
                x, y, (230, 215, 255), 8, speed=180.0,
            )
        elif visual_kind in ("creepy_bullet", "creepy_down_bullet"):
            self.fx_effects.append(
                RingBurstFx(
                    x, y, (80, 230, 225), life=0.16,
                    start_radius=6.0, end_radius=36.0, width=2,
                    sparks=5, spark_color=(220, 255, 252),
                    kind="creepy_bullet_impact",
                )
            )
            self.particles.emit_burst(x, y, (170, 255, 250), 8, speed=190.0)
        elif visual_kind == "creepy_homing_bullet":
            self.fx_effects.append(
                RingBurstFx(
                    x, y, (190, 120, 255), life=0.20,
                    start_radius=8.0, end_radius=42.0, width=3,
                    sparks=6, spark_color=(235, 220, 255),
                    kind="creepy_homing_impact",
                )
            )
            self.particles.emit_burst(x, y, (190, 120, 255), 10, speed=200.0)

    def spawn_hit_fx(self, kind: str, attacker, target, event: dict | None = None) -> None:
        """Visual-only hook for melee hit feedback; unknown kinds are ignored."""
        if target is None:
            return
        facing = 1 if attacker.facing >= 0 else -1
        x = float(target.x) - facing * float(target.hurtbox_width) * 0.5
        if kind == "veno_bite_hit":
            y = float(attacker.y) - 40.0
            self.fx_effects.append(BiteArcFx(x, y, facing, life=0.12))
            self.particles.emit_burst(
                x, y, (150, 240, 120), 3, speed=110.0,
                life=(0.08, 0.16), radius=(1.5, 3.0), gravity=160.0,
            )
        elif kind == "bat_dive_hit":
            y = float(attacker.y) - 50.0
            self.fx_effects.append(
                RingBurstFx(
                    x, y, (220, 190, 255), life=0.12,
                    start_radius=6.0, end_radius=28.0, width=2,
                    sparks=3, spark_color=(245, 235, 255),
                    kind="bat_dive_hit",
                )
            )
            self.particles.emit_burst(
                x, y, (235, 220, 255), 4, speed=140.0,
                life=(0.08, 0.16), gravity=120.0,
            )
        elif kind == "shadow_slash_hit":
            y = float(target.y) - float(target.hurtbox_dims[1]) * 0.5
            self.fx_effects.append(
                RingBurstFx(
                    x, y, (190, 115, 255), life=0.14,
                    start_radius=6.0, end_radius=30.0, width=2,
                    sparks=4, spark_color=(240, 220, 255),
                    kind="shadow_slash_hit",
                )
            )
            self.particles.emit_burst(
                x, y, (205, 150, 255), 6, speed=160.0,
                life=(0.08, 0.18), gravity=120.0,
            )
        elif kind == "shadow_dash_hit":
            y = float(target.y) - float(target.hurtbox_dims[1]) * 0.5
            self.fx_effects.append(
                RingBurstFx(
                    x, y, (170, 90, 255), life=0.18,
                    start_radius=10.0, end_radius=42.0, width=4,
                    sparks=6, spark_color=(240, 220, 255),
                    kind="shadow_dash_hit",
                )
            )
            self.particles.emit_burst(
                x, y, (195, 125, 255), 8, speed=190.0,
                life=(0.10, 0.22), gravity=180.0,
            )
        elif kind == "shadow_phantom_rend_hit":
            y = float(target.y) - float(target.hurtbox_dims[1]) * 0.5
            self.fx_effects.append(
                RingBurstFx(
                    x, y, (180, 100, 255), life=0.18,
                    start_radius=8.0, end_radius=46.0, width=4,
                    sparks=6, spark_color=(240, 220, 255),
                    kind="shadow_phantom_rend_hit",
                )
            )
            self.particles.emit_burst(
                x, y, (200, 130, 255), 8, speed=190.0,
                life=(0.10, 0.22), gravity=140.0,
            )
        elif kind == "shadow_phantom_flash_hit":
            y = float(target.y) - float(target.hurtbox_dims[1]) * 0.5
            self.fx_effects.append(
                RingBurstFx(
                    x, y, (205, 145, 255), life=0.16,
                    start_radius=6.0, end_radius=34.0, width=3,
                    sparks=5, spark_color=(245, 225, 255),
                    kind="shadow_phantom_flash_hit",
                )
            )
            self.particles.emit_burst(
                x, y, (215, 165, 255), 7, speed=170.0,
                life=(0.08, 0.18), gravity=120.0,
            )
        elif kind == "shadow_phantom_shark_hit":
            y = float(target.y) - 40.0
            self.fx_effects.append(
                RingBurstFx(
                    x, y, (150, 70, 240), life=0.22,
                    start_radius=12.0, end_radius=64.0, width=5,
                    sparks=8, spark_color=(235, 210, 255),
                    kind="shadow_phantom_shark_hit",
                )
            )
            self.particles.emit_burst(
                x, y, (180, 100, 255), 10, speed=220.0,
                life=(0.10, 0.24), gravity=240.0,
            )
        elif kind == "eira_staff_hit":
            y = float(target.y) - float(target.hurtbox_dims[1]) * 0.5
            self.fx_effects.append(
                RingBurstFx(
                    x, y, (170, 230, 255), life=0.14,
                    start_radius=6.0, end_radius=28.0, width=2,
                    sparks=4, spark_color=(235, 250, 255),
                    kind="eira_staff_hit",
                )
            )
            self.particles.emit_burst(
                x, y, (205, 240, 255), 5, speed=150.0,
                life=(0.08, 0.18), gravity=120.0,
            )
        elif kind == "mech_laser_hit":
            y = float(target.y) - float(target.hurtbox_dims[1]) * 0.5
            self.fx_effects.append(
                RingBurstFx(
                    x, y, (255, 90, 60), life=0.16,
                    start_radius=8.0, end_radius=34.0, width=3,
                    sparks=4, spark_color=(255, 220, 170),
                    kind="mech_laser_hit",
                )
            )
            self.particles.emit_burst(
                x, y, (255, 150, 90), 5, speed=150.0,
                life=(0.08, 0.18), gravity=120.0,
            )
        elif kind == "mech_charge_hit":
            y = float(target.y) - float(target.hurtbox_dims[1]) * 0.5
            self.fx_effects.append(
                RingBurstFx(
                    x, y, (240, 170, 80), life=0.18,
                    start_radius=10.0, end_radius=42.0, width=4,
                    sparks=5, spark_color=(255, 225, 170),
                    kind="mech_charge_hit",
                )
            )
            self.particles.emit_burst(
                x, y, (220, 180, 140), 7, speed=180.0,
                life=(0.10, 0.22), gravity=220.0,
            )
        elif kind == "mech_claw_hit":
            y = float(target.y) - float(target.hurtbox_dims[1]) * 0.5
            self.fx_effects.append(
                RingBurstFx(
                    x, y, (255, 120, 50), life=0.20,
                    start_radius=12.0, end_radius=52.0, width=5,
                    sparks=7, spark_color=(255, 230, 180),
                    kind="mech_claw_hit",
                )
            )
            self.particles.emit_burst(
                x, y, (235, 195, 145), 8, speed=200.0,
                life=(0.10, 0.24), gravity=260.0,
            )
        elif kind == "mech_leap_hit":
            y = float(target.y) - float(target.hurtbox_dims[1]) * 0.5
            self.fx_effects.append(
                RingBurstFx(
                    x, y, (255, 140, 60), life=0.24,
                    start_radius=16.0, end_radius=70.0, width=6,
                    sparks=10, spark_color=(255, 235, 190),
                    kind="mech_leap_hit",
                )
            )
            self.particles.emit_burst(
                x, y, (230, 195, 150), 11, speed=250.0,
                life=(0.12, 0.30), gravity=300.0,
            )

    def spawn_slash_effect(
        self,
        attacker,
        event: dict,
        cast_x: float | None = None,
        cast_y: float | None = None,
        cast_facing: int | None = None,
    ) -> None:
        x = float(cast_x if cast_x is not None else attacker.x)
        y = float(cast_y if cast_y is not None else attacker.y)
        facing = int(cast_facing if cast_facing is not None else attacker.facing)
        self.slash_effects.append(SlashEffect(x, y, facing, event))

    def _check_match_end(self) -> None:
        if not self.enemy_spec.get("decides_match", False) or self.match_over is not None:
            return
        if self.enemies and all(enemy.hp <= 0.0 for enemy in self.enemies):
            self.match_over = "WIN"
        elif self.player.hp <= 0.0:
            self.match_over = "LOSE"

    def spawn_projectile_from_event(self, attacker, attack: dict, event: dict) -> None:
        lane_name = event.get("lane", "mid")
        lane_y = self.stage.lane_y(lane_name, attacker.y)
        direction = attacker.facing
        bonus = attacker.current_flame_bonus()
        damage = attack_damage(attacker, attack, event) * (1.0 + bonus)
        flame = getattr(attacker, "flame_time", 0.0) > 0.0
        target = self.opponent_of(attacker)

        projectile_kind = event.get("projectile", "q_wave")
        if projectile_kind == "sword_wave":
            projectile = SwordWave(
                owner=attacker,
                target=target,
                x=attacker.x + direction * 44.0,
                y=lane_y,
                direction=direction,
                speed=float(event.get("speed", 900.0)),
                max_range=float(event.get("range", 560.0)),
                damage=damage,
                knockback=float(event.get("knockback", 0.0)),
                hitstun=float(attack.get("hitstun", self.store.stats["combat"]["hitstun"])),
                hitstop=float(attack.get("hitstop", self.store.stats["combat"]["hitstop"])),
                penetrates_blocks=bool(event.get("penetrates_blocks", False)),
            )
        elif projectile_kind in ("venom_glob", "web_bolt"):
            origin_height = float(event.get("origin_height", 100.0))
            origin_forward = float(event.get("origin_forward", 24.0))
            origin_x = attacker.x + direction * origin_forward
            origin_y = attacker.y - origin_height
            if target is not None:
                aim_x = target.x
                aim_y = target.y - target.hurtbox_dims[1] * 0.5
            else:
                aim_x = origin_x + direction * 320.0
                aim_y = origin_y
            distance = math.hypot(aim_x - origin_x, aim_y - origin_y)
            if distance < 1e-6:
                ux, uy = float(direction), 0.0
            else:
                ux = (aim_x - origin_x) / distance
                uy = (aim_y - origin_y) / distance
            speed = float(event.get("speed", 520.0))
            projectile = AimedProjectile(
                owner=attacker,
                target=target,
                x=origin_x,
                y=origin_y,
                vx=ux * speed,
                vy=uy * speed,
                max_range=float(event.get("range", 800.0)),
                damage=damage,
                knockback=float(event.get("knockback", 0.0)),
                hitstun=float(attack.get("hitstun", self.store.stats["combat"]["hitstun"])),
                hitstop=float(attack.get("hitstop", self.store.stats["combat"]["hitstop"])),
                kind=projectile_kind,
                radius=18.0 if projectile_kind == "venom_glob" else 30.0,
                status=event.get("status"),
                status_duration=float(event.get("status_duration", 0.0)),
                status_dps_pct=float(event.get("status_dps_pct", 0.0)),
                penetrates_blocks=bool(event.get("penetrates_blocks", False)),
            )
        elif projectile_kind in ("rhea_shuriken", "rhea_poison_shuriken"):
            projectile = ShurikenProjectile(
                owner=attacker,
                target=target,
                x=attacker.x + direction * float(event.get("origin_forward", 30.0)),
                y=lane_y,
                direction=direction,
                speed=float(event.get("speed", 850.0)),
                max_range=float(event.get("range", 700.0)),
                damage=damage,
                knockback=float(event.get("knockback", 0.0)),
                hitstun=float(
                    attack.get("hitstun", self.store.stats["combat"]["hitstun"])
                ),
                hitstop=float(
                    attack.get("hitstop", self.store.stats["combat"]["hitstop"])
                ),
                kind=projectile_kind,
                radius=float(
                    event.get("hitbox_radius", event.get("radius", 12.0))
                ),
                status=event.get("status"),
                status_duration=float(event.get("status_duration", 0.0)),
                status_dps_pct=float(event.get("status_dps_pct", 0.0)),
                extends_poison=bool(event.get("extends_poison", False)),
                bonus_target_max_hp_pct=float(
                    event.get("bonus_target_max_hp_pct", 0.0)
                ),
                bonus_vs_poison_max_hp_pct=float(
                    event.get("bonus_vs_poison_max_hp_pct", 0.0)
                ),
                bonus_vs_poison_source=event.get("bonus_vs_poison_source"),
                penetrates_blocks=bool(event.get("penetrates_blocks", False)),
            )
        elif projectile_kind in ("eira_snowball", "eira_ice_shard"):
            projectile_class = (
                EiraSnowballProjectile
                if projectile_kind == "eira_snowball"
                else EiraIceShardProjectile
            )
            spawn_y = lane_y
            if event.get("origin_height") is not None:
                spawn_y = attacker.y - float(event["origin_height"])
            projectile = projectile_class(
                owner=attacker,
                target=target,
                x=attacker.x + direction * float(event.get("origin_forward", 30.0)),
                y=spawn_y,
                direction=direction,
                speed=float(event.get("speed", 900.0)),
                max_range=float(event.get("range", 900.0)),
                damage=damage,
                knockback=float(event.get("knockback", 0.0)),
                hitstun=float(
                    attack.get("hitstun", self.store.stats["combat"]["hitstun"])
                ),
                hitstop=float(
                    attack.get("hitstop", self.store.stats["combat"]["hitstop"])
                ),
                radius=float(event.get("hitbox_radius", event.get("radius", 14.0))),
                penetrates_blocks=bool(event.get("penetrates_blocks", False)),
                pierces_targets=bool(
                    event.get(
                        "pierces_targets",
                        projectile_kind == "eira_ice_shard",
                    )
                ),
                freeze_gain=float(event.get("freeze_gain", 0.0)),
                bonus_vs_frozen_atk_mult=float(
                    event.get("bonus_vs_frozen_atk_mult", 0.0)
                ),
                bonus_vs_frozen_extra_mult=float(
                    event.get("bonus_vs_frozen_extra_mult", 0.0)
                ),
            )
        elif projectile_kind in (
            "witch_lightning_forward",
            "witch_lightning_up",
            "witch_lightning_down",
        ):
            variant = projectile_kind.rsplit("_", 1)[1]
            speed = float(event.get("speed", 1800.0))
            angle = math.radians(
                {"forward": 0.0, "up": 35.0, "down": -35.0}[variant]
            )
            vx = direction * speed * math.cos(angle)
            vy = -speed * math.sin(angle)
            projectile = WitchLightningProjectile(
                variant=variant,
                owner=attacker,
                target=target,
                x=attacker.x + direction * float(event.get("origin_forward", 40.0)),
                y=attacker.y - float(event.get("origin_height", 150.0)),
                vx=vx,
                vy=vy,
                max_range=float(event.get("range", 900.0)),
                damage=damage,
                knockback=float(event.get("knockback", 0.0)),
                hitstun=float(
                    attack.get("hitstun", self.store.stats["combat"]["hitstun"])
                ),
                hitstop=float(
                    attack.get("hitstop", self.store.stats["combat"]["hitstop"])
                ),
                radius=float(event.get("hitbox_radius", event.get("radius", 14.0))),
                penetrates_blocks=bool(event.get("penetrates_blocks", False)),
            )
        elif projectile_kind == "witch_potion":
            on_platform = (
                self.stage.platform_top_at(attacker.x, attacker.y) is not None
            )
            mode = "platform" if on_platform else "ground"
            potion_cfg = self.store.stats["crooked_witch"]["potion"]
            projectile = WitchPotionProjectile(
                owner=attacker,
                target=target,
                x=attacker.x + direction * float(event.get("origin_forward", 40.0)),
                y=attacker.y
                - float(event.get("origin_height", 160.0 if on_platform else 60.0)),
                direction=direction,
                mode=mode,
                speed=float(event.get("speed", 320.0 if on_platform else 420.0)),
                max_range=float(event.get("range", 700.0)),
                damage=damage,
                knockback=float(event.get("knockback", 0.0)),
                hitstun=float(
                    attack.get("hitstun", self.store.stats["combat"]["hitstun"])
                ),
                hitstop=float(
                    attack.get("hitstop", self.store.stats["combat"]["hitstop"])
                ),
                radius=float(event.get("hitbox_radius", event.get("radius", 12.0))),
                zone_config=dict(potion_cfg),
            )
        elif projectile_kind == "shadow_kunai":
            projectile = ShadowKunaiProjectile(
                owner=attacker,
                target=target,
                x=attacker.x + direction * float(event.get("origin_forward", 30.0)),
                y=lane_y,
                direction=direction,
                speed=float(event.get("speed", 900.0)),
                max_range=float(event.get("range", 900.0)),
                damage=damage,
                knockback=float(event.get("knockback", 0.0)),
                hitstun=float(
                    attack.get("hitstun", self.store.stats["combat"]["hitstun"])
                ),
                hitstop=float(
                    attack.get("hitstop", self.store.stats["combat"]["hitstop"])
                ),
                radius=float(
                    event.get("hitbox_radius", event.get("radius", 10.0))
                ),
                status=event.get("status"),
                status_duration=float(event.get("status_duration", 0.0)),
                penetrates_blocks=bool(event.get("penetrates_blocks", False)),
            )
            projectile.scene = self
        elif projectile_kind == "shadow_phantom_bind":
            projectile = ShadowBindProjectile(
                owner=attacker,
                target=target,
                x=attacker.x + direction * float(event.get("origin_forward", 30.0)),
                y=lane_y,
                direction=direction,
                speed=float(event.get("speed", 900.0)),
                max_range=float(event.get("range", 700.0)),
                damage=damage,
                knockback=float(event.get("knockback", 0.0)),
                hitstun=float(
                    attack.get("hitstun", self.store.stats["combat"]["hitstun"])
                ),
                hitstop=float(
                    attack.get("hitstop", self.store.stats["combat"]["hitstop"])
                ),
                radius=float(event.get("hitbox_radius", 20.0)),
                status=event.get("status"),
                status_duration=float(event.get("status_duration", 0.0)),
                penetrates_blocks=bool(event.get("penetrates_blocks", True)),
            )
        elif projectile_kind == "shadow_phantom_flash":
            projectile = ShadowFlashProjectile(
                owner=attacker,
                target=target,
                x=attacker.x + direction * float(event.get("origin_forward", 30.0)),
                y=lane_y,
                direction=direction,
                speed=float(event.get("speed", 900.0)),
                max_range=float(event.get("range", 420.0)),
                damage=damage,
                knockback=float(event.get("knockback", 0.0)),
                hitstun=float(
                    attack.get("hitstun", self.store.stats["combat"]["hitstun"])
                ),
                hitstop=float(
                    attack.get("hitstop", self.store.stats["combat"]["hitstop"])
                ),
                radius=float(event.get("hitbox_radius", 18.0)),
                penetrates_blocks=bool(event.get("penetrates_blocks", True)),
            )
        elif projectile_kind == "sonic_wave":
            origin_height = float(event.get("origin_height", 30.0))
            origin_forward = float(event.get("origin_forward", 46.0))
            origin_x = attacker.x + direction * origin_forward
            origin_y = attacker.y - origin_height
            if target is not None:
                aim_x = target.x
                aim_y = target.y - target.hurtbox_dims[1] * 0.5
            else:
                aim_x = origin_x + direction * 320.0
                aim_y = origin_y
            distance = math.hypot(aim_x - origin_x, aim_y - origin_y)
            if distance < 1e-6:
                ux, uy = float(direction), 0.0
            else:
                ux = (aim_x - origin_x) / distance
                uy = (aim_y - origin_y) / distance
            projectile = SonicWave(
                owner=attacker,
                target=target,
                x=origin_x,
                y=origin_y,
                ux=ux,
                uy=uy,
                speed=float(event.get("speed", 420.0)),
                max_range=float(event.get("range", 3000.0)),
                damage=damage,
                knockback=float(event.get("knockback", 0.0)),
                hitstun=float(
                    attack.get("hitstun", self.store.stats["combat"]["hitstun"])
                ),
                hitstop=float(
                    attack.get("hitstop", self.store.stats["combat"]["hitstop"])
                ),
                status=event.get("status"),
                status_duration=float(event.get("status_duration", 0.0)),
                radius=18.0,
                return_height=origin_height,
                hitbox_forward=float(event.get("hitbox_forward", 8.0)),
                hitbox_radius=float(event.get("hitbox_radius", 24.0)),
                penetrates_blocks=bool(event.get("penetrates_blocks", False)),
            )
        elif projectile_kind == "creepy_bullet":
            origin_height = float(event.get("origin_height", 143.0))
            origin_forward = float(event.get("origin_forward", 111.0))
            projectile = CreepyBullet(
                owner=attacker,
                target=target,
                x=attacker.x + direction * origin_forward,
                y=attacker.y - origin_height,
                direction=direction,
                speed=float(event.get("speed", 980.0)),
                max_range=float(event.get("range", 900.0)),
                damage=damage,
                knockback=float(event.get("knockback", 0.0)),
                hitstun=float(attack.get("hitstun", self.store.stats["combat"]["hitstun"])),
                hitstop=float(attack.get("hitstop", self.store.stats["combat"]["hitstop"])),
                radius=float(event.get("hitbox_radius", 9.0)),
                penetrates_blocks=bool(event.get("penetrates_blocks", False)),
            )
        elif projectile_kind == "creepy_homing_bullet":
            origin_height = float(event.get("origin_height", 120.0))
            origin_forward = float(event.get("origin_forward", 48.0))
            projectile = CreepyHomingBullet(
                owner=attacker,
                target=target,
                x=attacker.x + direction * origin_forward,
                y=attacker.y - origin_height,
                speed=float(event.get("speed", 520.0)),
                max_range=float(event.get("range", 3000.0)),
                lifetime=float(event.get("lifetime", 8.0)),
                damage=damage,
                knockback=float(event.get("knockback", 0.0)),
                hitstun=float(attack.get("hitstun", self.store.stats["combat"]["hitstun"])),
                hitstop=float(attack.get("hitstop", self.store.stats["combat"]["hitstop"])),
                radius=float(event.get("hitbox_radius", 14.0)),
            )
        elif projectile_kind == "creepy_down_bullet":
            origin_height = float(event.get("origin_height", 110.0))
            origin_forward = float(event.get("origin_forward", 24.0))
            origin_x = attacker.x + direction * origin_forward
            origin_y = attacker.y - origin_height
            ux, uy = 0.0, 1.0
            if target is not None:
                aim_x = target.x
                aim_y = target.y - target.hurtbox_dims[1] * 0.5
                dx = aim_x - origin_x
                dy = aim_y - origin_y
                if dy > 0.0 and abs(math.atan2(dx, dy)) <= math.pi / 4.0:
                    distance = math.hypot(dx, dy)
                    if distance > 1e-6:
                        ux, uy = dx / distance, dy / distance
            projectile = CreepyDownBullet(
                owner=attacker,
                target=target,
                x=origin_x,
                y=origin_y,
                ux=ux,
                uy=uy,
                speed=float(event.get("speed", 900.0)),
                max_range=float(event.get("range", 600.0)),
                damage=damage,
                knockback=float(event.get("knockback", 0.0)),
                hitstun=float(attack.get("hitstun", self.store.stats["combat"]["hitstun"])),
                hitstop=float(attack.get("hitstop", self.store.stats["combat"]["hitstop"])),
                radius=float(event.get("hitbox_radius", 12.0)),
            )
        elif projectile_kind == "axe":
            projectile = AxeThrow(
                owner=attacker,
                target=target,
                x=attacker.x + direction * 50.0,
                y=lane_y,
                direction=direction,
                speed=float(event.get("speed", 900.0)),
                max_range=float(event.get("range", 420.0)),
                damage=damage,
                knockback=float(event.get("knockback", 0.0)),
                hitstun=float(attack.get("hitstun", self.store.stats["combat"]["hitstun"])),
                hitstop=float(attack.get("hitstop", self.store.stats["combat"]["hitstop"])),
            )
        else:
            projectile = QWave(
                owner=attacker,
                target=target,
                x=attacker.x + direction * 50.0,
                y=lane_y,
                direction=direction,
                speed=float(event.get("speed", 700.0)),
                max_range=float(event.get("range", 520.0)),
                damage=damage,
                knockback=float(event.get("knockback", 0.0)),
                hitstun=float(attack.get("hitstun", self.store.stats["combat"]["hitstun"])),
                hitstop=float(attack.get("hitstop", self.store.stats["combat"]["hitstop"])),
                energy_gain=float(attack.get("energy_gain", 0.0)),
                flame=flame,
                flame_bonus=bonus,
                grant_energy=not flame,
                penetrates_blocks=bool(event.get("penetrates_blocks", False)),
            )
        self.projectiles.append(projectile)
        self.spawn_projectile_cast_fx(projectile)

    # --- debug --------------------------------------------------------------
    def cycle_time_scale(self) -> None:
        if not self.time_scales:
            return
        self.time_scale_index = (self.time_scale_index + 1) % len(self.time_scales)
        self.time_scale = float(self.time_scales[self.time_scale_index])

    def _cycle_status_demo(self) -> None:
        statuses = [
            "burn", "poison", "stun", "freeze", "slow",
            "super_armor", "damage_reduction", "vulnerable",
        ]
        kind = statuses[self.status_demo_index % len(statuses)]
        self.status_demo_index += 1
        value = {
            "slow": 0.5, "damage_reduction": 0.2, "vulnerable": 0.2,
        }.get(kind, 0.0)
        dps = 0.0
        if kind == "burn":
            dps = float(
                getattr(self.player, "burn_dps", self.store.stats["combat"]["burn_dps"])
            )
        elif kind == "poison":
            dps = self.enemy.max_hp * float(self.store.stats["combat"]["poison_dps_pct"])
        self.enemy.statuses.add(kind, 3.0, source="debug", value=value, dps=dps)

    def handle_debug_key(self, key: int) -> None:
        if key == pygame.K_F1:
            self.show_overlay = not self.show_overlay
        elif key == pygame.K_F2:
            self.show_panel = not self.show_panel
        elif key == pygame.K_F5:
            self.reload_data()
        elif key == pygame.K_F6:
            self.cycle_time_scale()
        elif key == pygame.K_F7:
            self.cycle_enemy()
        elif key == pygame.K_LEFTBRACKET:
            self.cycle_character(-1)
        elif key == pygame.K_RIGHTBRACKET:
            self.cycle_character(1)
        elif key == pygame.K_F8:
            ai_enemies = [
                enemy for enemy in self.enemies if hasattr(enemy, "ai_enabled")
            ]
            if ai_enemies:
                enabled = not ai_enemies[0].ai_enabled
                for enemy in ai_enemies:
                    enemy.ai_enabled = enabled
            elif hasattr(self.enemy, "invincible"):
                self.enemy.invincible = not self.enemy.invincible
        elif key == pygame.K_F9:
            self.reset()
        elif key == pygame.K_b:
            enabled = self.stage.toggle_blocks()
            if enabled:
                self._resolve_stage_overlaps()
        elif key == pygame.K_F10:
            if hasattr(self.player, "start_transform") and hasattr(self.player, "energy"):
                self.player.energy = self.player.max_energy
                self.player.e_cd = 0.0
                self.player.start_transform()
        elif key == pygame.K_F11:
            self._cycle_status_demo()
        elif key == pygame.K_F12:
            if self.player.hp > 10.0:
                self.player.take_hit(10.0, 0.0, 0.2, -1)
            else:
                self.player.take_hit(999.0, 0.0, 0.2, -1)
            self._check_match_end()
        elif key in SKILL_KEYS:
            self.enemy.force_skill(self, self.player, SKILL_KEYS[key])
        elif key == pygame.K_LEFT:
            self.stage.move_x(self.enemy, -20.0)
        elif key == pygame.K_RIGHT:
            self.stage.move_x(self.enemy, 20.0)
        elif key == pygame.K_PAGEUP:
            self.enemy.hp = min(self.enemy.max_hp, self.enemy.hp + 100.0)
            if self.enemy.state == FighterState.KO:
                self.enemy.state = FighterState.IDLE
                if self.enemy.anim is not None:
                    self.enemy.anim.set_clip("idle", reset=True)
            if self.player.hp > 0.0:
                self.match_over = None
        elif key == pygame.K_PAGEDOWN:
            self.enemy.hp = max(0.0, self.enemy.hp - 100.0)
            if self.enemy.hp <= 0.0:
                self.enemy.state = FighterState.KO
                if self.enemy.anim is not None:
                    self.enemy.anim.set_clip("ko", reset=True)
            self._check_match_end()

    # --- rendering ----------------------------------------------------------
    def knock_up_effect_progress(self, fighter) -> float | None:
        """Remaining knock_up ratio, or None when the effect is inactive."""
        effect = fighter.statuses.get("knock_up")
        if effect is None or effect.total <= 0.0:
            return None
        return max(0.0, min(1.0, effect.remaining / effect.total))

    def _draw_knock_up_effects(self, surface: pygame.Surface) -> None:
        cfg = self.store.stats["combat"].get("knock_up_fx", {})
        spin = float(cfg.get("spin", 6.0))
        for fighter in [*self.enemies, self.player]:
            effect = fighter.statuses.get("knock_up")
            progress = self.knock_up_effect_progress(fighter)
            if effect is None or progress is None:
                continue
            elapsed = max(0.0, effect.total - effect.remaining)
            draw_knock_up_vortex(
                surface, fighter.x, fighter.y, progress, elapsed * spin, cfg
            )

    def _poison_tint(self, fighter) -> tuple[int, int, int] | None:
        """Whole-body poison flash: green/purple every 0.18s."""
        if fighter.hp <= 0.0 or not fighter.statuses.has("poison"):
            return None
        phase = int(self.sim_time / 0.18) % 2
        return (70, 255, 110) if phase == 0 else (220, 100, 255)

    def _draw_status_fx(self, surface: pygame.Surface, fighter) -> None:
        if fighter.hp <= 0.0:
            return
        if fighter.statuses.has("stun"):
            head_y = fighter.y - fighter.hurtbox_dims[1] - 18.0
            for index in range(3):
                angle = self.sim_time * 4.0 + index * (math.tau / 3.0)
                x = fighter.x + math.cos(angle) * 16.0
                y = head_y + math.sin(angle) * 6.0
                pygame.draw.circle(surface, (255, 224, 90), (round(x), round(y)), 4)
                pygame.draw.circle(surface, (255, 250, 210), (round(x), round(y)), 2)
        if fighter.statuses.has("freeze"):
            self._draw_freeze_shell(surface, fighter)

    def _draw_freeze_shell(self, surface: pygame.Surface, fighter) -> None:
        width, height = fighter.hurtbox_dims
        shell = _freeze_asset("eira_freeze_shell.png", _FREEZE_SHELL_CACHE)
        if shell is not None:
            target_w = max(1, round(width * 1.65))
            target_h = max(1, round(height * 1.10))
            shell = pygame.transform.smoothscale(shell, (target_w, target_h))
            # The approved shell art is drawn at 58% opacity so the frozen
            # body stays readable underneath.
            shell.fill(
                (255, 255, 255, 150), special_flags=pygame.BLEND_RGBA_MULT
            )
            surface.blit(
                shell,
                (
                    round(fighter.x - target_w * 0.5),
                    round(fighter.y - target_h + 8.0),
                ),
            )
        else:
            pad = 8
            layer = pygame.Surface(
                (round(width) + pad * 2, round(height) + pad * 2),
                pygame.SRCALPHA,
            )
            rect = layer.get_rect()
            pygame.draw.ellipse(layer, (130, 205, 255, 58), rect)
            pygame.draw.ellipse(layer, (210, 245, 255, 150), rect, 2)
            surface.blit(
                layer,
                (
                    round(fighter.x - rect.width * 0.5),
                    round(fighter.y + 8.0 - rect.height),
                ),
            )
        foot = _freeze_asset("eira_freeze_foot_ice.png", _FREEZE_FOOT_CACHE)
        if foot is not None:
            foot_w = max(1, round(width * 1.8))
            foot_h = max(
                1, round(foot.get_height() * foot_w / max(1, foot.get_width()))
            )
            foot = pygame.transform.smoothscale(foot, (foot_w, foot_h))
            foot.fill(
                (255, 255, 255, 220), special_flags=pygame.BLEND_RGBA_MULT
            )
            surface.blit(
                foot,
                foot.get_rect(midbottom=(round(fighter.x), round(fighter.y + 4))),
            )
        else:
            for index in range(3):
                angle = self.sim_time * 2.5 + index * (math.tau / 3.0)
                fx = fighter.x + math.cos(angle) * width * 0.35
                fy = fighter.y - abs(math.sin(angle)) * 7.0
                pygame.draw.polygon(
                    surface, (205, 242, 255),
                    [
                        (round(fx), round(fy - 9)),
                        (round(fx - 3), round(fy)),
                        (round(fx + 3), round(fy)),
                    ],
                )

    def _draw_mark_fx(self, surface: pygame.Surface) -> None:
        # Marks are stored per target, so each enemy shows its own stack.
        if not hasattr(self.player, "mark_detonations"):
            return
        for enemy in self.enemies:
            if enemy.hp <= 0.0:
                continue
            marks = int(getattr(enemy, "marks", 0))
            burst = float(getattr(enemy, "mark_burst_time", 0.0))
            base_y = enemy.y - enemy.hurtbox_dims[1] - 70.0
            for index in range(3):
                x = enemy.x + (index - 1) * 16.0
                filled = index < marks
                color = (190, 225, 255) if filled else (90, 110, 135)
                points = [
                    (round(x), round(base_y - 6)),
                    (round(x + 6), round(base_y)),
                    (round(x), round(base_y + 6)),
                    (round(x - 6), round(base_y)),
                ]
                pygame.draw.polygon(surface, color, points)
                if filled:
                    pygame.draw.polygon(surface, (245, 252, 255), points, 1)
            if burst > 0.0:
                progress = max(0.0, min(1.0, 1.0 - burst / 0.4))
                radius = 10 + round(38 * progress)
                alpha = max(0, round(200 * (1.0 - progress)))
                ring = pygame.Surface(
                    (radius * 2 + 8, radius * 2 + 8), pygame.SRCALPHA
                )
                center = ring.get_width() // 2
                pygame.draw.circle(
                    ring, (200, 235, 255, alpha), (center, center), radius, 3
                )
                surface.blit(
                    ring, (round(enemy.x - center), round(base_y - center))
                )

    def _draw_shadow_mark_fx(self, surface: pygame.Surface) -> None:
        """Shadow Ninja's purple marks live on the player, not the enemy."""
        if not any(
            getattr(enemy, "is_shadow_ninja", False) for enemy in self.enemies
        ):
            return
        player = self.player
        if player.hp <= 0.0:
            return
        marks = int(getattr(player, "shadow_marks", 0))
        burst = float(getattr(player, "shadow_mark_burst_time", 0.0))
        base_y = player.y - player.hurtbox_dims[1] - 70.0
        for index in range(3):
            x = player.x + (index - 1) * 16.0
            filled = index < marks
            color = (190, 120, 255) if filled else (72, 52, 96)
            points = [
                (round(x), round(base_y - 6)),
                (round(x + 6), round(base_y)),
                (round(x), round(base_y + 6)),
                (round(x - 6), round(base_y)),
            ]
            pygame.draw.polygon(surface, color, points)
            if filled:
                pygame.draw.polygon(surface, (240, 220, 255), points, 1)
        if burst > 0.0:
            progress = max(0.0, min(1.0, 1.0 - burst / 0.4))
            radius = 10 + round(38 * progress)
            alpha = max(0, round(200 * (1.0 - progress)))
            ring = pygame.Surface(
                (radius * 2 + 8, radius * 2 + 8), pygame.SRCALPHA
            )
            center = ring.get_width() // 2
            pygame.draw.circle(
                ring, (190, 120, 255, alpha), (center, center), radius, 3
            )
            surface.blit(
                ring, (round(player.x - center), round(base_y - center))
            )

    def draw(self, surface: pygame.Surface) -> None:
        self.stage.draw(surface)
        self._draw_knock_up_effects(surface)
        for effect in self.fx_effects:
            if effect.alive and getattr(effect, "behind", False):
                effect.draw(surface)
        for hazard in self.hazards:
            if getattr(hazard, "behind", False):
                hazard.draw(surface)
        for enemy in self.enemies:
            enemy.draw(surface, tint=self._poison_tint(enemy))
            self._draw_status_fx(surface, enemy)
        for projectile in self.projectiles:
            if not getattr(projectile, "draw_front", False):
                projectile.draw(surface)
        self.particles.draw(surface)
        self.player.draw(surface, tint=self._poison_tint(self.player))
        for hazard in self.hazards:
            if not getattr(hazard, "behind", False):
                hazard.draw(surface)
        for projectile in self.projectiles:
            if getattr(projectile, "draw_front", False):
                projectile.draw(surface)
        for enemy in self.enemies:
            draw_lock = getattr(enemy, "draw_lock_marker", None)
            if draw_lock is not None:
                draw_lock(surface)
        for effect in self.slash_effects:
            effect.draw(surface)
        for effect in self.fx_effects:
            if effect.alive and not getattr(effect, "behind", False):
                effect.draw(surface)
        self._draw_status_fx(surface, self.player)
        self._draw_mark_fx(surface)
        self._draw_shadow_mark_fx(surface)
        self.hud.draw(surface, self)
        self.hud.draw_targeting_prompt(surface, self)
        if self.show_overlay:
            self.overlay.draw(surface, self)
        if self.show_panel:
            self.panel.draw(surface, self)
