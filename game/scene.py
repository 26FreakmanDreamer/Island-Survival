"""Arena scene: tick order, debug controls, projectiles and rendering."""

from __future__ import annotations

import pygame

from .debug import DebugOverlay, DebugPanel
from .dummy import Dummy
from .fighter import FighterState
from .hud import HUD
from .input import InputState
from .lina import Lina
from .particles import ParticleSystem
from .projectile import QWave
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
        self.projectiles: list[QWave] = []
        self.status_demo_index = 0
        self.time_scales = [0.25, 0.5, 1.0, 2.0]
        self.time_scale_index = 2
        self.time_scale = 1.0
        self.stage: Stage
        self.lina: Lina
        self.dummy: Dummy
        self.particles = ParticleSystem()
        self.rebuild()

    # --- lifecycle ----------------------------------------------------------
    def rebuild(self) -> None:
        self.stage = Stage(self.store.debug["stage"])
        self.lina = Lina(self.store, self.stage)
        self.dummy = Dummy(self.store, self.stage)
        self.projectiles = []
        self.particles = ParticleSystem()
        self.debug_hitboxes = []
        self.hitstop = 0.0
        self.tick_count = 0
        self.sim_time = 0.0
        self.last_hit = None
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

    def reload_data(self) -> bool:
        if not self.store.reload():
            return False
        self.rebuild()
        return True

    def reset(self) -> None:
        self.lina.reset()
        self.dummy.reset()
        self.projectiles = []
        self.particles = ParticleSystem()
        self.debug_hitboxes = []
        self.hitstop = 0.0
        self.tick_count = 0
        self.sim_time = 0.0
        self.last_hit = None
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
        self.dummy.update(dt, self)
        self.lina.update(dt, self.input, self.dummy, self)

        if self.hitstop > 0.0:
            return

        for projectile in self.projectiles:
            projectile.update(dt, self)
        self.projectiles = [projectile for projectile in self.projectiles if projectile.alive]
        self.particles.update(dt)

        if self.lina.flame_time > 0.0:
            self.particles.emit_flame(self.lina.x, self.lina.y)
        if self.dummy.statuses.has("burn"):
            self.particles.emit_flame(self.dummy.x, self.dummy.y - 90.0)

    def spawn_projectile_from_event(self, attacker, attack: dict, event: dict) -> None:
        lane_name = event.get("lane", "mid")
        lane_y = self.stage.lane_y(lane_name, attacker.y)
        direction = attacker.facing
        bonus = attacker.current_flame_bonus()
        base = attacker.atk * float(event.get("damage_mult", attack.get("damage_mult", 1.0)))
        damage = base * (1.0 + bonus)
        flame = attacker.flame_time > 0.0
        projectile = QWave(
            owner=attacker,
            target=self.dummy,
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
            dps = self.dummy.max_hp * float(self.store.stats["combat"]["poison_dps_pct"])
        self.dummy.statuses.add(kind, 3.0, source="debug", value=value, dps=dps)

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
            self.dummy.invincible = not self.dummy.invincible
        elif key == pygame.K_F8:
            self.dummy.reset()
        elif key == pygame.K_F9:
            self.reset()
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
        elif key == pygame.K_LEFT:
            self.dummy.x -= 20.0
        elif key == pygame.K_RIGHT:
            self.dummy.x += 20.0
        elif key == pygame.K_PAGEUP:
            self.dummy.hp = min(self.dummy.max_hp, self.dummy.hp + 100.0)
            if self.dummy.state == FighterState.KO:
                self.dummy.state = FighterState.IDLE
        elif key == pygame.K_PAGEDOWN:
            self.dummy.hp = max(0.0, self.dummy.hp - 100.0)
            if self.dummy.hp <= 0.0:
                self.dummy.state = FighterState.KO

    # --- rendering ----------------------------------------------------------
    def draw(self, surface: pygame.Surface) -> None:
        self.stage.draw(surface)
        self.dummy.draw(surface)
        for projectile in self.projectiles:
            projectile.draw(surface)
        self.particles.draw(surface)
        self.lina.draw(surface)
        self.hud.draw(surface, self)
        if self.show_overlay:
            self.overlay.draw(surface, self)
        if self.show_panel:
            self.panel.draw(surface, self)
