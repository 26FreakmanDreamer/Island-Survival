"""Warrior: axe-wielding enemy with approach AI and startup super armor."""

from __future__ import annotations

import pygame

from .animation import AnimationPlayer
from .combat import AttackRuntime
from .config import CANONICAL_WARRIOR, WARRIOR_FRAMES_DIR
from .fighter import Fighter, FighterState


class Warrior(Fighter):
    name = "Warrior"
    show_health_bar = True

    def __init__(self, store, stage) -> None:
        cfg = store.stats["warrior"]
        combat_cfg = store.stats["combat"]
        anim = AnimationPlayer(
            store.animations["warrior_clips"],
            {},
            WARRIOR_FRAMES_DIR,
            CANONICAL_WARRIOR,
            store.animations["warrior_pivot"],
            frame_size=store.animations["warrior_frame_size"],
        )
        x, y = stage.warrior_spawn
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
        )

        self.store = store
        self.cfg = cfg
        self.atk = float(cfg["basic_atk"] + cfg["extra_atk"])
        self.walk_speed = float(cfg["move"]["walk"])
        self.jump_v = float(cfg["move"]["jump_v"])
        self.attack_range = float(cfg["ai"]["attack_range"])
        self.attack_cd_max = float(cfg["ai"]["attack_cooldown"])
        self.skill_cd_max = float(cfg["ai"]["skill_gap"])
        self.dash_range = float(cfg["ai"]["dash_range"])
        self.dash_cd_max = float(cfg["ai"]["dash_cooldown"])
        self.throw_min_range = float(cfg["ai"]["throw_min_range"])
        self.throw_range = float(cfg["ai"]["throw_range"])
        self.throw_cd_max = float(cfg["ai"]["throw_cooldown"])
        self.attack_cd = 0.0
        self.skill_cd = 0.0
        self.dash_cd = 0.0
        self.throw_cd = 0.0
        self.ai_enabled = True
        self.reset()

    # --- update -------------------------------------------------------------
    def update(self, dt: float, scene) -> None:
        self.update_common(dt)
        self.attack_cd = max(0.0, self.attack_cd - dt)
        self.skill_cd = max(0.0, self.skill_cd - dt)
        self.dash_cd = max(0.0, self.dash_cd - dt)
        self.throw_cd = max(0.0, self.throw_cd - dt)

        if self.state == FighterState.KO:
            self.vx = 0.0
            self.anim.update(dt)
            self.stage.move_fighter(self, dt)
            return

        if self.state == FighterState.HURT:
            self.vx = 0.0
            self.anim.update(dt)
            if self.hitstun <= 0.0 and self.hp > 0.0:
                self.state = FighterState.IDLE
                self.anim.set_clip("idle")
            self.stage.move_fighter(self, dt)
            return

        if self.state == FighterState.ATTACK:
            self._update_attack(dt)
            self.stage.move_fighter(self, dt)
            return

        if self.statuses.control_locked():
            self.vx = 0.0
            self.state = FighterState.IDLE
            self.anim.set_clip("idle")
            self.anim.update(dt)
            self.stage.move_fighter(self, dt)
            return

        target = scene.lina
        if (
            self.ai_enabled
            and scene.match_over is None
            and target.hp > 0.0
        ):
            self._think(dt, scene, target)
        elif not self.on_ground:
            self.state = FighterState.AIR
            self.anim.set_clip("jump")
            self.anim.set_frame(0 if self.vy < 0.0 else 1)
        else:
            self.vx = 0.0
            self.state = FighterState.IDLE
            self.anim.set_clip("idle")
            self.anim.update(dt)

        self.stage.move_fighter(self, dt)

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
            self.attack_cd = self.attack_cd_max
            self.skill_cd = self.skill_cd_max
            self.anim.set_clip("idle")

    # --- AI -----------------------------------------------------------------
    def _think(self, dt: float, scene, target) -> None:
        dx = target.x - self.x
        # Deadzone: while the bodies are nearly coincident, keep the current
        # facing instead of flipping every tick.
        if abs(dx) > 8.0:
            self.facing = 1 if dx > 0.0 else -1

        if not self.on_ground:
            self.state = FighterState.AIR
            self.anim.set_clip("jump")
            self.anim.set_frame(0 if self.vy < 0.0 else 1)
            self.vx = self.facing * self.walk_speed * self.statuses.slow_factor()
            return

        # A block between the actors must be handled before the range check. The
        # high-lane axe throw can cross a block; otherwise jump over it.
        blocked = self._block_ahead(scene)
        same_height = abs(target.y - self.y) <= 90.0
        distance = abs(dx)

        if blocked:
            if (
                self.skill_cd <= 0.0
                and same_height
                and self.throw_min_range <= distance <= self.throw_range
                and self.throw_cd <= 0.0
            ):
                self.start_attack("axe_throw", scene, target)
            else:
                self._start_jump()
            return

        if self.skill_cd <= 0.0:
            if same_height and distance <= self.attack_range and self.attack_cd <= 0.0:
                self.start_attack("axe_slash", scene, target)
                return
            if same_height and distance <= self.dash_range and self.dash_cd <= 0.0:
                self.start_attack("dash", scene, target)
                return
            if (
                same_height
                and self.throw_min_range <= distance <= self.throw_range
                and self.throw_cd <= 0.0
            ):
                self.start_attack("axe_throw", scene, target)
                return

        self.vx = self.facing * self.walk_speed * self.statuses.slow_factor()
        self.state = FighterState.WALK
        self.anim.set_clip("walk")
        self.anim.update(dt)

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
        self.attack_id = attack_id
        self.state = FighterState.ATTACK
        self.vx = 0.0
        self.anim.set_clip(attack_id, reset=True)
        data = self.store.attacks[attack_id]
        self.attack_runtime = AttackRuntime(self, attack_id, data, target, scene)
        if attack_id == "dash":
            self.dash_cd = self.dash_cd_max
        elif attack_id == "axe_throw":
            self.throw_cd = self.throw_cd_max

    def force_attack(self, scene, target, attack_id: str = "axe_slash") -> None:
        if self.hp <= 0.0 or self.state in (FighterState.KO, FighterState.HURT):
            return
        if not self.on_ground or attack_id not in self.store.attacks:
            return
        if target.x != self.x:
            self.facing = 1 if target.x > self.x else -1
        self.attack_cd = 0.0
        self.skill_cd = 0.0
        self.dash_cd = 0.0
        self.throw_cd = 0.0
        self.start_attack(attack_id, scene, target)

    # --- reactions ----------------------------------------------------------
    def take_hit(
        self,
        damage: float,
        knockback: float,
        hitstun: float,
        direction: int,
        launch: float = 0.0,
    ) -> bool:
        runtime = self.attack_runtime
        armored = (
            self.state == FighterState.ATTACK
            and runtime is not None
            and runtime.time < float(runtime.data.get("armor_until", 0.0))
            and not self.invincible
            and self.hp > 0.0
        )
        if not armored:
            return super().take_hit(damage, knockback, hitstun, direction, launch=launch)

        self.hp = max(0.0, self.hp - damage)
        self.flash = 0.12
        if self.hp <= 0.0:
            self.state = FighterState.KO
            self.hitstun = 0.0
            self.kb_vx = 0.0
            self.kb_time = 0.0
            self.attack_runtime = None
            self.attack_id = None
            self.anim.set_clip("ko", reset=True)
        return True

    # --- reset --------------------------------------------------------------
    def reset(self) -> None:
        x, y = self.stage.warrior_spawn
        self.reset_common(x, y, -1)
        self.attack_cd = 0.0
        self.skill_cd = 0.0
        self.dash_cd = 0.0
        self.throw_cd = 0.0
        self.ai_enabled = True
        self.anim.set_clip("idle", reset=True)
