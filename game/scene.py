"""Arena scene: tick order, debug controls, projectiles and rendering."""

from __future__ import annotations

import pygame

from .debug import DebugOverlay, DebugPanel
from .dummy import Dummy
from .fighter import Fighter, FighterState
from .hud import HUD
from .input import InputState
from .lina import Lina
from .particles import ParticleSystem
from .projectile import AxeThrow, QWave
from .stage import Stage
from .warrior import Warrior

ENEMY_MODES = ("warrior", "dummy")

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
    pygame.K_b,
    pygame.K_LEFT,
    pygame.K_RIGHT,
    pygame.K_PAGEUP,
    pygame.K_PAGEDOWN,
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
        self.enemy_mode = str(store.debug.get("enemy", {}).get("default_mode", "warrior"))
        if self.enemy_mode not in ENEMY_MODES:
            self.enemy_mode = "warrior"
        self.match_over: str | None = None
        self.stage: Stage
        self.lina: Lina
        self.enemy: Fighter
        self.particles = ParticleSystem()
        self.rebuild()

    # --- lifecycle ----------------------------------------------------------
    def rebuild(self) -> None:
        self.stage = Stage(self.store.debug["stage"])
        self.lina = Lina(self.store, self.stage)
        self.enemy = self._create_enemy()
        self.projectiles = []
        self.particles = ParticleSystem()
        self.debug_hitboxes = []
        self.hitstop = 0.0
        self.tick_count = 0
        self.sim_time = 0.0
        self.last_hit = None
        self.match_over = None
        self.status_demo_index = 0
        self.input.buffer.max_age = float(self.store.stats["combat"]["input_buffer"])
        self.input.clear()

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

    def _create_enemy(self) -> Fighter:
        if self.enemy_mode == "dummy":
            return Dummy(self.store, self.stage)
        return Warrior(self.store, self.stage)

    def set_enemy_mode(self, mode: str) -> bool:
        if mode not in ENEMY_MODES or mode == self.enemy_mode:
            return False
        self.enemy_mode = mode
        self.lina.cancel_attack()
        self.enemy = self._create_enemy()
        self.projectiles = []
        self.hitstop = 0.0
        self.last_hit = None
        self.debug_hitboxes = []
        self.match_over = None
        return True

    def opponent_of(self, fighter):
        if fighter is self.lina:
            return self.enemy
        if fighter is self.enemy:
            return self.lina
        return None

    def reload_data(self) -> bool:
        if not self.store.reload():
            return False
        self.rebuild()
        return True

    def reset(self) -> None:
        self.lina.reset()
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
        self.lina.update(dt, self.input, self.enemy, self)
        self.enemy.update(dt, self)
        self._separate_fighters()
        self._check_match_end()

        if self.hitstop > 0.0:
            return

        for projectile in self.projectiles:
            projectile.update(dt, self)
        self.projectiles = [projectile for projectile in self.projectiles if projectile.alive]
        self.particles.update(dt)

        if self.lina.flame_time > 0.0:
            self.particles.emit_flame(self.lina.x, self.lina.y)
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

    def _separate_fighters(self) -> None:
        """Keep the Warrior's center from crossing Lina's center.

        There is no fighter-vs-fighter physics elsewhere; without this the AI
        can walk through Lina, flip facing every few pixels and stack sprites.
        """
        if self.enemy_mode != "warrior":
            return
        if self.lina.hp <= 0.0 or self.enemy.hp <= 0.0:
            return
        lina_body = self.stage.body_rect(self.lina)
        enemy_body = self.stage.body_rect(self.enemy)
        if not lina_body.colliderect(enemy_body):
            return

        min_dist = self.lina.stage_half_width + self.enemy.stage_half_width
        dx = self.enemy.x - self.lina.x
        if abs(dx) >= min_dist:
            return
        if abs(dx) < 0.01:
            side = self.enemy.facing
        else:
            side = 1 if dx > 0.0 else -1
        # Prefer a side where the Warrior can actually stand; otherwise the
        # block resolver would fling him to the far edge of a block.
        if not self._can_stand(self.enemy, self.lina.x + side * min_dist):
            other = -side
            if self._can_stand(self.enemy, self.lina.x + other * min_dist):
                side = other
        target_x = self.lina.x + side * min_dist
        self.stage.move_x(self.enemy, target_x - self.enemy.x)
        # If a wall or block stopped the Warrior, push Lina to the free side
        # instead of leaving the bodies stacked.
        if abs(self.enemy.x - self.lina.x) < min_dist:
            lina_target = self.enemy.x - side * min_dist
            self.stage.move_x(self.lina, lina_target - self.lina.x)

    def _check_match_end(self) -> None:
        if self.enemy_mode != "warrior" or self.match_over is not None:
            return
        if self.enemy.hp <= 0.0:
            self.match_over = "WIN"
        elif self.lina.hp <= 0.0:
            self.match_over = "LOSE"

    def spawn_projectile_from_event(self, attacker, attack: dict, event: dict) -> None:
        lane_name = event.get("lane", "mid")
        lane_y = self.stage.lane_y(lane_name, attacker.y)
        direction = attacker.facing
        bonus = attacker.current_flame_bonus()
        if "damage" in event:
            damage = float(event["damage"]) * (1.0 + bonus)
        else:
            base = attacker.atk * float(event.get("damage_mult", attack.get("damage_mult", 1.0)))
            damage = base * (1.0 + bonus)
        flame = getattr(attacker, "flame_time", 0.0) > 0.0
        target = self.opponent_of(attacker)

        if event.get("id") == "axe_throw":
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
            dps = self.lina.burn_dps
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
            self.set_enemy_mode("dummy" if self.enemy_mode == "warrior" else "warrior")
        elif key == pygame.K_F8:
            if self.enemy_mode == "warrior":
                self.enemy.ai_enabled = not self.enemy.ai_enabled
            else:
                self.enemy.invincible = not self.enemy.invincible
        elif key == pygame.K_F9:
            self.reset()
        elif key == pygame.K_b:
            self.stage.toggle_blocks()
        elif key == pygame.K_F10:
            self.lina.energy = self.lina.max_energy
            self.lina.e_cd = 0.0
            self.lina.start_transform()
        elif key == pygame.K_F11:
            self._cycle_status_demo()
        elif key == pygame.K_F12:
            if self.lina.hp > 10.0:
                self.lina.take_hit(10.0, 0.0, 0.2, -1)
            else:
                self.lina.take_hit(999.0, 0.0, 0.2, -1)
            self._check_match_end()
        elif key == pygame.K_v:
            if self.enemy_mode == "warrior":
                self.enemy.force_attack(self, self.lina, "axe_slash")
        elif key == pygame.K_c:
            if self.enemy_mode == "warrior":
                self.enemy.force_attack(self, self.lina, "dash")
        elif key == pygame.K_x:
            if self.enemy_mode == "warrior":
                self.enemy.force_attack(self, self.lina, "axe_throw")
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
            if self.lina.hp > 0.0:
                self.match_over = None
        elif key == pygame.K_PAGEDOWN:
            self.enemy.hp = max(0.0, self.enemy.hp - 100.0)
            if self.enemy.hp <= 0.0:
                self.enemy.state = FighterState.KO
                if self.enemy.anim is not None:
                    self.enemy.anim.set_clip("ko", reset=True)
            self._check_match_end()

    # --- rendering ----------------------------------------------------------
    def draw(self, surface: pygame.Surface) -> None:
        self.stage.draw(surface)
        self.enemy.draw(surface)
        for projectile in self.projectiles:
            projectile.draw(surface)
        self.particles.draw(surface)
        self.lina.draw(surface)
        self.hud.draw(surface, self)
        if self.show_overlay:
            self.overlay.draw(surface, self)
        if self.show_panel:
            self.panel.draw(surface, self)
