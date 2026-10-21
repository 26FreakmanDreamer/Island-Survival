"""Arena scene: tick order, debug controls, projectiles and rendering."""

from __future__ import annotations

import pygame

from .combat import attack_damage
from .config import FIXED_DT
from .debug import DebugOverlay, DebugPanel
from .fighter import Fighter, FighterState
from .hud import HUD
from .input import InputState
from .particles import ParticleSystem, draw_knock_up_vortex
from .projectile import AxeThrow, QWave
from .roster import create_fighter
from .stage import Stage

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
        self.particles = ParticleSystem()
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

    def _rebuild_fighters(self) -> None:
        blocks_enabled = self.stage.blocks_enabled
        self.player = create_fighter(self.character_spec, self.store, self.stage)
        self.enemy = create_fighter(self.enemy_spec, self.store, self.stage)
        self.stage.blocks_enabled = blocks_enabled
        self.projectiles = []
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

    def _force_ai_off(self) -> None:
        if hasattr(self.enemy, "ai_enabled"):
            self.enemy.ai_enabled = False

    def rebuild(self) -> None:
        self.stage = Stage(self.store.debug["stage"])
        self._resolve_ids()
        self._rebuild_fighters()
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
        self._force_ai_off()
        return True

    def set_enemy(self, enemy_id: str) -> bool:
        enemies = self.store.roster.get("enemies", {})
        if enemy_id not in enemies or enemy_id == self.enemy_id:
            return False
        self.enemy_id = enemy_id
        self.enemy_spec = enemies[enemy_id]
        self._rebuild_fighters()
        self._force_ai_off()
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
            return self.enemy
        if fighter is self.enemy:
            return self.player
        return None

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
        self.enemy.reset()
        self.projectiles = []
        self.particles = ParticleSystem()
        self.debug_hitboxes = []
        self.hitstop = 0.0
        self.tick_count = 0
        self.sim_time = 0.0
        self.last_hit = None
        self.match_over = None
        self.input.clear()

    # --- simulation ---------------------------------------------------------
    def tick(self, dt: float) -> None:
        self.tick_count += 1
        self.sim_time += dt

        if self.hitstop > 0.0:
            self.hitstop = max(0.0, self.hitstop - dt)
            return

        self.debug_hitboxes.clear()
        self.input.update(dt)
        self.player.update(dt, self.input, self.enemy, self)
        self.enemy.update(dt, self)
        self._separate_fighters(dt)
        self._check_match_end()

        if self.hitstop > 0.0:
            return

        for projectile in self.projectiles:
            projectile.update(dt, self)
        self.projectiles = [projectile for projectile in self.projectiles if projectile.alive]
        self._check_match_end()
        self.particles.update(dt)

        if getattr(self.player, "flame_time", 0.0) > 0.0:
            self.particles.emit_flame(self.player.x, self.player.y)
        if self.enemy.statuses.has("burn"):
            self.particles.emit_flame(self.enemy.x, self.enemy.y - 90.0)

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
        """Keep the enemy's center from crossing the player's center."""
        if not self.enemy_spec.get("separates", False):
            return
        if self.player.hp <= 0.0 or self.enemy.hp <= 0.0:
            return
        player_body = self.stage.body_rect(self.player)
        enemy_body = self.stage.body_rect(self.enemy)
        if not player_body.colliderect(enemy_body):
            return

        min_dist = self.player.stage_half_width + self.enemy.stage_half_width
        dx = self.enemy.x - self.player.x
        if abs(dx) >= min_dist:
            return
        if abs(dx) < 0.01:
            side = self.enemy.facing
        else:
            side = 1 if dx > 0.0 else -1
        # The enemy yields first, but only on his current side. Flipping to
        # the other side of the player would teleport him across the block
        # that blocked the first target. If his side is blocked, push the
        # player away instead. Both pushes are capped so a deep overlap
        # slides apart over a few ticks instead of teleporting.
        max_step = float(
            self.store.stats["combat"].get("separation_speed", 600.0)
        ) * dt
        target_x = self.player.x + side * min_dist
        if self._can_stand(self.enemy, self.enemy.x) and self._can_stand(
            self.enemy, target_x
        ):
            self._step_x(self.enemy, target_x, max_step)
        if abs(self.enemy.x - self.player.x) < min_dist:
            player_target = self.enemy.x - side * min_dist
            if self._can_stand(self.player, self.player.x) and self._can_stand(
                self.player, player_target
            ):
                self._step_x(self.player, player_target, max_step)

    def _step_x(self, fighter, target_x: float, max_step: float) -> None:
        """Move toward a target without crossing into a block in one tick."""
        delta = target_x - fighter.x
        if abs(delta) > max_step:
            delta = max_step if delta > 0.0 else -max_step
        if delta and self._can_stand(fighter, fighter.x + delta):
            self.stage.move_x(fighter, delta)

    def _check_match_end(self) -> None:
        if not self.enemy_spec.get("decides_match", False) or self.match_over is not None:
            return
        if self.enemy.hp <= 0.0:
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
        if projectile_kind == "axe":
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
            )
        self.projectiles.append(projectile)

    # --- debug --------------------------------------------------------------
    def cycle_time_scale(self) -> None:
        if not self.time_scales:
            return
        self.time_scale_index = (self.time_scale_index + 1) % len(self.time_scales)
        self.time_scale = float(self.time_scales[self.time_scale_index])

    def _cycle_status_demo(self) -> None:
        statuses = [
            "burn", "poison", "stun", "freeze", "slow",
            "super_armor", "damage_reduction",
        ]
        kind = statuses[self.status_demo_index % len(statuses)]
        self.status_demo_index += 1
        value = {"slow": 0.5, "damage_reduction": 0.2}.get(kind, 0.0)
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
            if hasattr(self.enemy, "ai_enabled"):
                self.enemy.ai_enabled = not self.enemy.ai_enabled
            elif hasattr(self.enemy, "invincible"):
                self.enemy.invincible = not self.enemy.invincible
        elif key == pygame.K_F9:
            self.reset()
        elif key == pygame.K_b:
            self.stage.toggle_blocks()
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
        for fighter in (self.enemy, self.player):
            effect = fighter.statuses.get("knock_up")
            progress = self.knock_up_effect_progress(fighter)
            if effect is None or progress is None:
                continue
            elapsed = max(0.0, effect.total - effect.remaining)
            draw_knock_up_vortex(
                surface, fighter.x, fighter.y, progress, elapsed * spin, cfg
            )

    def draw(self, surface: pygame.Surface) -> None:
        self.stage.draw(surface)
        self._draw_knock_up_effects(surface)
        self.enemy.draw(surface)
        for projectile in self.projectiles:
            projectile.draw(surface)
        self.particles.draw(surface)
        self.player.draw(surface)
        self.hud.draw(surface, self)
        if self.show_overlay:
            self.overlay.draw(surface, self)
        if self.show_panel:
            self.panel.draw(surface, self)
