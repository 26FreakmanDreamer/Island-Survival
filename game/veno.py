"""Veno-Spider: ground bites, web-hover ranged pressure and poison."""

from __future__ import annotations

import math

import pygame

from .combat import AttackRuntime
from .fighter import Fighter, FighterState


class Veno(Fighter):
    show_health_bar = True

    def __init__(self, store, stage, entry: dict, anim) -> None:
        cfg = store.stats[entry["stats"]]
        combat_cfg = store.stats["combat"]
        x, y = stage.spawn(entry["spawn"])
        super().__init__(
            x=x,
            y=y,
            facing=-1,
            anim=anim,
            hurtbox_config=cfg["hurtbox"],
            max_hp=cfg["hp"],
            stage=stage,
            gravity=cfg["move"]["gravity"],
            knockback_decay=combat_cfg["knockback_decay"],
            stage_body_width=cfg.get("stage_body_width"),
            entry=entry,
        )

        self.store = store
        self.cfg = cfg
        self.spawn = (float(x), float(y))
        self.set_attack_stats(cfg)
        self.knock_up_gravity = float(
            combat_cfg.get("knock_up_gravity", self.gravity)
        )

        self.walk_speed = float(cfg["move"]["walk"])
        self.jump_v = float(cfg["move"]["jump_v"])
        self.bite_cd_max = float(cfg["cooldowns"]["bite"])
        self.poison_cd_max = float(cfg["cooldowns"]["poison"])
        self.web_cd_max = float(cfg["cooldowns"]["web"])

        hover = cfg["hover"]
        self.hover_base = float(hover["base"])
        self.hover_min = float(hover["min"])
        self.hover_max = float(hover["max"])
        self.hover_vertical_speed = float(hover["vertical_speed"])
        self.hover_descend_speed = float(hover["descend_speed"])
        self.hover_oscillation = float(hover["oscillation"])
        self.hover_rate = float(hover["oscillation_rate"])

        ai = cfg["ai"]
        self.bite_range = float(ai["bite_range"])
        self.close_range = float(ai["close_range"])
        self.ranged_range = float(ai["ranged_range"])
        self.decision_interval = float(ai["decision_interval"])
        self.hover_min_time = float(ai["hover_min_time"])

        self.bite_cd = 0.0
        self.poison_cd = 0.0
        self.web_cd = 0.0
        # Each spider is a distinct poison source: its own reapplications
        # extend, while poisons from other Venos stay independent.
        self.poison_source = f"veno_poison:{id(self)}"
        self.mode = "ground"
        self.ai_enabled = True
        self.hover_time = 0.0
        self.hover_phase = 0.0
        self.decision_cd = 0.0
        self.attack_runtime: AttackRuntime | None = None
        self.attack_id: str | None = None
        self.reset()

    # --- public state -------------------------------------------------------
    @property
    def hover_height(self) -> float:
        return max(0.0, self.stage.ground_y - self.y)

    def take_hit(
        self,
        damage: float,
        knockback: float,
        hitstun: float,
        direction: int,
        launch: float = 0.0,
    ) -> bool:
        hit = super().take_hit(damage, knockback, hitstun, direction, launch=launch)
        if hit and self.hp > 0.0 and not self.on_ground:
            self.mode = "descend"
        return hit

    # --- update -------------------------------------------------------------
    def update(self, dt: float, scene) -> None:
        self.update_common(dt)
        self.bite_cd = max(0.0, self.bite_cd - dt)
        self.poison_cd = max(0.0, self.poison_cd - dt)
        self.web_cd = max(0.0, self.web_cd - dt)
        self.decision_cd = max(0.0, self.decision_cd - dt)

        if self.state == FighterState.KO:
            self.vx = 0.0
            self.anim.update(dt)
            self.stage.move_fighter(self, dt)
            self._settle_mode_after_gravity(scene)
            return

        if self.state == FighterState.HURT:
            self.vx = 0.0
            self.anim.update(dt)
            self.stage.move_fighter(self, dt)
            if self.hitstun <= 0.0 and self.hp > 0.0:
                if self.on_ground:
                    self.mode = "ground"
                    self.state = FighterState.IDLE
                    self.anim.set_clip("idle")
                else:
                    self.mode = "descend"
            self._settle_mode_after_gravity(scene)
            return

        if self.state == FighterState.ATTACK:
            self._update_attack(dt)
            self._move(dt, scene)
            return

        if self.statuses.control_locked():
            self.vx = 0.0
            self.set_air_or_idle_anim()
            self.anim.update(dt)
            self.stage.move_fighter(self, dt)
            self._settle_mode_after_gravity(scene)
            return

        if not self.on_ground and self.mode == "ground":
            self.mode = "descend"

        target = scene.player
        if self.ai_enabled and scene.match_over is None and target.hp > 0.0:
            self._think(dt, scene, target)
        else:
            self._hold(dt)
        self._move(dt, scene)

    def _settle_mode_after_gravity(self, scene) -> None:
        if self.mode == "descend" and self.on_ground:
            self.mode = "ground"
            self.vy = 0.0
            self.state = FighterState.IDLE
            self.anim.set_clip("idle")

    def _move(self, dt: float, scene) -> None:
        if self.mode == "ground":
            self.stage.move_fighter(self, dt)
            return
        if not self.ai_enabled:
            self.vy = 0.0
            self.stage.move_fighter(self, dt, apply_gravity=False)
            return
        target_y = self._target_y(scene)
        self._hover_step(dt, scene, target_y)
        self._settle_mode_after_gravity(scene)

    def _target_y(self, scene) -> float:
        if self.mode == "ascend":
            return scene.stage.ground_y - self.hover_base
        if self.mode == "descend":
            return scene.stage.ground_y
        offset = self.hover_base + math.sin(
            self.hover_phase * self.hover_rate
        ) * self.hover_oscillation
        offset = max(self.hover_min, min(self.hover_max, offset))
        return scene.stage.ground_y - offset

    def _hover_step(self, dt: float, scene, target_y: float) -> None:
        delta = target_y - self.y
        speed = self.hover_descend_speed if delta > 0.0 else self.hover_vertical_speed
        if abs(delta) <= speed * dt:
            self.vy = delta / dt if dt > 0.0 else 0.0
        else:
            self.vy = speed if delta > 0.0 else -speed
        self.stage.move_fighter(self, dt, apply_gravity=False)
        if self.mode == "ascend" and self.y <= target_y + 1.0:
            self.mode = "hover"
            self.vy = 0.0
            self.hover_time = 0.0

    # --- AI -----------------------------------------------------------------
    def _think(self, dt: float, scene, target) -> None:
        dx = target.x - self.x
        if abs(dx) > 8.0:
            self.facing = 1 if dx > 0.0 else -1
        distance = abs(dx)

        if self.mode == "ground":
            if distance > self.bite_range and (self.poison_cd <= 0.0 or self.web_cd <= 0.0):
                self.mode = "ascend"
                self.on_ground = False
                self.vy = -self.hover_vertical_speed
                self.vx = 0.0
                self._set_hover_anim()
                self.anim.update(dt)
                return
            if distance <= self.bite_range and self.bite_cd <= 0.0:
                self.start_attack("veno_bite", scene, target)
                return
            if self._block_ahead(scene):
                if self.poison_cd <= 0.0 or self.web_cd <= 0.0:
                    self.mode = "ascend"
                    self.on_ground = False
                    self.vy = -self.hover_vertical_speed
                    self.vx = 0.0
                    self._set_hover_anim()
                    self.anim.update(dt)
                else:
                    self._start_jump()
                return
            self.vx = self.facing * self.walk_speed * self.statuses.slow_factor()
            self.state = FighterState.WALK
            self.anim.set_clip("walk")
            self.anim.update(dt)
            return

        if self.mode == "ascend":
            self.vx = 0.0
            self._set_hover_anim()
            self.anim.update(dt)
            return

        if self.mode == "hover":
            self.hover_time += dt
            self.hover_phase += dt
            self.vx = 0.0
            self._set_hover_anim()
            self.anim.update(dt)
            if distance <= self.close_range and self.hover_time >= self.hover_min_time:
                self.mode = "descend"
                self.vy = self.hover_descend_speed
                return
            if self.poison_cd <= 0.0 and distance <= self.ranged_range:
                self.start_attack("veno_poison", scene, target)
                return
            if self.web_cd <= 0.0 and distance <= self.ranged_range:
                self.start_attack("veno_web", scene, target)
                return
            if self.poison_cd > 0.0 and self.web_cd > 0.0 and self.hover_time >= 0.5:
                self.mode = "descend"
                self.vy = self.hover_descend_speed
                return
            if distance > self.ranged_range:
                self.vx = self.facing * 115.0 * self.statuses.slow_factor()
            return

        if self.mode == "descend":
            self.vx = (
                self.facing * 115.0 * self.statuses.slow_factor()
                if distance > self.bite_range
                else 0.0
            )
            self._set_hover_anim()
            self.anim.update(dt)

    def _hold(self, dt: float) -> None:
        self.vx = 0.0
        if self.mode == "ground":
            self.state = FighterState.IDLE
            self.anim.set_clip("idle")
            self.anim.update(dt)
        else:
            self.vy = 0.0
            self._set_hover_anim()
            self.anim.update(dt)

    def _set_hover_anim(self) -> None:
        self.state = FighterState.AIR
        self.anim.set_clip("hover")

    def _block_ahead(self, scene) -> bool:
        if not scene.stage.blocks_enabled:
            return False
        direction = self.facing
        height = self.hurtbox_dims[1]
        front = self.x + direction * (self.stage_half_width + 2.0)
        left = front if direction > 0 else front - 10.0
        probe = pygame.Rect(
            round(left),
            round(self.y - height + 2.0),
            10,
            max(1, round(height - 4.0)),
        )
        for block in scene.stage.blocks:
            if self.y <= block.top + 1:
                continue
            if probe.colliderect(block):
                return True
        return False

    def _start_jump(self) -> None:
        self.vy = -self.jump_v
        self.on_ground = False
        self.state = FighterState.AIR
        self.vx = self.facing * self.walk_speed * self.statuses.slow_factor()
        self.anim.set_clip("jump", reset=True)
        self.anim.set_frame(0)

    # --- actions ------------------------------------------------------------
    def start_attack(self, attack_id: str, scene, target) -> None:
        if target is not None and abs(target.x - self.x) > 8.0:
            self.facing = 1 if target.x > self.x else -1
        self.attack_id = attack_id
        self.state = FighterState.ATTACK
        self.vx = 0.0
        self.anim.set_clip(attack_id, reset=True)
        data = self.store.attacks[attack_id]
        self.attack_runtime = AttackRuntime(self, attack_id, data, target, scene)
        if attack_id == "veno_bite":
            self.bite_cd = self.bite_cd_max
        elif attack_id == "veno_poison":
            self.poison_cd = self.poison_cd_max
        elif attack_id == "veno_web":
            self.web_cd = self.web_cd_max

    def _update_attack(self, dt: float) -> None:
        self.vx = 0.0
        runtime = self.attack_runtime
        if runtime is None:
            self.state = FighterState.IDLE
            self.anim.set_clip("idle")
            return
        runtime.update(dt)
        self.anim.update(dt)
        if runtime.finished:
            self.state = FighterState.IDLE
            self.attack_runtime = None
            self.attack_id = None
            if self.mode == "ground":
                self.anim.set_clip("idle")
            else:
                self.anim.set_clip("hover")

    def force_attack(self, scene, target, attack_id: str = "veno_bite") -> bool:
        if self.hp <= 0.0 or self.state in (FighterState.KO, FighterState.HURT):
            return False
        if attack_id not in self.store.attacks:
            return False
        self.bite_cd = 0.0
        self.poison_cd = 0.0
        self.web_cd = 0.0
        self.start_attack(attack_id, scene, target)
        return True

    def skill_remaining(self, attack_id: str) -> float:
        return {
            "veno_bite": self.bite_cd,
            "veno_poison": self.poison_cd,
            "veno_web": self.web_cd,
        }.get(attack_id, 0.0)

    def on_projectile_hit(self, projectile) -> None:
        target = projectile.target
        if target is None or target.hp <= 0.0:
            return
        status = getattr(projectile, "status", None)
        if status == "poison":
            dps = target.max_hp * float(projectile.status_dps_pct)
            target.statuses.add(
                "poison",
                float(projectile.status_duration),
                source=self.poison_source,
                dps=dps,
            )
        elif status == "stun":
            target.statuses.add(
                "stun",
                float(projectile.status_duration),
                source="veno_web",
            )

    # --- rendering ----------------------------------------------------------
    def draw(
        self,
        surface: pygame.Surface,
        tint: tuple[int, int, int] | None = None,
    ) -> None:
        if self.hp > 0.0 and not self.on_ground and self.mode in ("ascend", "hover"):
            self._draw_hover_silk(surface)
        super().draw(surface, tint=tint)

    def _draw_hover_silk(self, surface: pygame.Surface) -> None:
        """Draw-only strand; sway uses the hover clock, never state/AI."""
        bottom_y = self.y - 37.5
        if bottom_y <= 1.0:
            return
        sway = math.sin(self.hover_phase * 2.0) * 4.0
        width = max(24, round(abs(sway) + 28))
        height = max(2, round(bottom_y))
        layer = pygame.Surface((width, height), pygame.SRCALPHA)
        center = width * 0.5

        points: list[tuple[int, int]] = []
        for step in range(13):
            t = step / 12.0
            u = 1.0 - t
            px = (
                u * u * (center + sway)
                + 2.0 * u * t * (center - sway * 0.5)
                + t * t * center
            )
            py = 2.0 * u * t * (bottom_y * 0.55) + t * t * bottom_y
            points.append((round(px), round(py)))

        pygame.draw.lines(layer, (60, 90, 60, 120), False, points, 3)
        pygame.draw.lines(layer, (170, 200, 170, 190), False, points, 2)
        pygame.draw.lines(layer, (245, 255, 245, 220), False, points, 1)
        pygame.draw.circle(
            layer, (210, 235, 210, 160),
            (round(center + sway), 2), 4,
        )
        pygame.draw.circle(
            layer, (220, 245, 220, 180),
            (round(center), round(bottom_y) - 4), 4, 1,
        )
        surface.blit(layer, (round(self.x - center), 0))

    # --- reset --------------------------------------------------------------
    def reset(self) -> None:
        x, y = self.spawn
        self.reset_common(x, y, -1)
        self.bite_cd = 0.0
        self.poison_cd = 0.0
        self.web_cd = 0.0
        self.mode = "ground"
        self.ai_enabled = True
        self.hover_time = 0.0
        self.hover_phase = 0.0
        self.decision_cd = 0.0
        self.attack_runtime = None
        self.attack_id = None
        if self.anim is not None:
            self.anim.set_clip("idle", reset=True)
