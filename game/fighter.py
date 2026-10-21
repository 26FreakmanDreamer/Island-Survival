"""Shared fighter state, physics-adjacent bookkeeping and hit reactions."""

from __future__ import annotations

from enum import IntEnum

import pygame

from .animation import AnimationPlayer
from .stage import Stage
from .status import StatusSet


class FighterState(IntEnum):
    IDLE = 0
    WALK = 1
    CROUCH = 2
    AIR = 3
    ATTACK = 4
    HURT = 5
    TRANSFORM = 6
    KO = 7


class Fighter:
    show_health_bar = False

    def __init__(
        self,
        x: float,
        y: float,
        facing: int,
        anim: AnimationPlayer | None,
        hurtbox_config: dict,
        max_hp: float,
        stage: Stage,
        gravity: float,
        knockback_decay: float,
        stage_body_width: float | None = None,
    ) -> None:
        self.stage = stage
        self.anim = anim
        self.hurtbox_config = hurtbox_config
        self.stage_half_width = (
            float(stage_body_width) * 0.5
            if stage_body_width is not None
            else float(hurtbox_config["standing"][0]) * 0.5
        )
        self.x = float(x)
        self.y = float(y)
        self.facing = 1 if facing >= 0 else -1
        self.vx = 0.0
        self.vy = 0.0
        self.kb_vx = 0.0
        self.kb_start = 0.0
        self.kb_time = 0.0
        self.kb_decay = max(0.01, knockback_decay)
        self.gravity = gravity
        self.on_ground = True
        self.max_hp = float(max_hp)
        self.hp = float(max_hp)
        self.state = FighterState.IDLE
        self.state_time = 0.0
        self.hitstun = 0.0
        self.flash = 0.0
        self.invincible = False
        self.statuses = StatusSet()
        self.attack_runtime = None
        self.attack_id = None

    # --- geometry -----------------------------------------------------------
    @property
    def hurtbox_dims(self) -> tuple[float, float]:
        key = "crouching" if self.state == FighterState.CROUCH else "standing"
        width, height = self.hurtbox_config[key]
        return float(width), float(height)

    @property
    def hurtbox_width(self) -> float:
        return self.hurtbox_dims[0]

    def hurtbox(self) -> pygame.Rect:
        width, height = self.hurtbox_dims
        return pygame.Rect(
            round(self.x - width * 0.5),
            round(self.y - height),
            round(width),
            round(height),
        )

    # --- timers -------------------------------------------------------------
    def update_common(self, dt: float) -> None:
        self.state_time += dt
        self.statuses.update(dt, self)
        self.flash = max(0.0, self.flash - dt)
        if self.hitstun > 0.0:
            self.hitstun = max(0.0, self.hitstun - dt)
        if self.kb_time > 0.0:
            self.kb_time = max(0.0, self.kb_time - dt)
            ratio = self.kb_time / self.kb_decay
            self.kb_vx = self.kb_start * ratio
        else:
            self.kb_vx = 0.0

    # --- reactions ----------------------------------------------------------
    def take_hit(
        self,
        damage: float,
        knockback: float,
        hitstun: float,
        direction: int,
        launch: float = 0.0,
    ) -> bool:
        if self.invincible or self.hp <= 0.0:
            return False
        self.hp = max(0.0, self.hp - damage)
        self.flash = 0.12
        self.hitstun = max(self.hitstun, hitstun)
        self.attack_runtime = None
        self.attack_id = None
        if self.hp <= 0.0:
            self.state = FighterState.KO
            self.hitstun = 0.0
            self.kb_vx = 0.0
            self.kb_time = 0.0
            if self.anim is not None:
                self.anim.set_clip("ko", reset=True)
            return True

        self.state = FighterState.HURT
        if self.anim is not None:
            self.anim.set_clip("hurt", reset=True)
        if launch > 0.0:
            self.vy = -launch
            self.on_ground = False
        if knockback:
            self.kb_start = knockback * (1 if direction >= 0 else -1)
            self.kb_vx = self.kb_start
            self.kb_time = self.kb_decay
        return True

    def apply_dot(self, amount: float) -> None:
        if self.invincible or self.hp <= 0.0:
            return
        self.hp = max(0.0, self.hp - amount)
        self.flash = max(self.flash, 0.05)
        if self.hp <= 0.0:
            self.state = FighterState.KO
            self.kb_vx = 0.0
            self.kb_time = 0.0
            if self.anim is not None:
                self.anim.set_clip("ko", reset=True)

    # --- hooks used by combat ----------------------------------------------
    def current_flame_bonus(self) -> float:
        return 0.0

    def on_hit_success(self, attack: dict, target, bonus: float) -> None:
        return

    def on_projectile_hit(self, projectile) -> None:
        return

    # --- reset --------------------------------------------------------------
    def reset_common(self, x: float, y: float, facing: int) -> None:
        self.x = float(x)
        self.y = float(y)
        self.facing = 1 if facing >= 0 else -1
        self.vx = 0.0
        self.vy = 0.0
        self.kb_vx = 0.0
        self.kb_start = 0.0
        self.kb_time = 0.0
        self.hp = self.max_hp
        self.state = FighterState.IDLE
        self.state_time = 0.0
        self.hitstun = 0.0
        self.flash = 0.0
        self.on_ground = True
        self.statuses.clear()
        self.attack_runtime = None
        self.attack_id = None

    def cancel_attack(self) -> None:
        """Drop the current attack; used when the scene swaps targets."""
        self.attack_runtime = None
        self.attack_id = None
        if self.state == FighterState.ATTACK:
            self.state = FighterState.IDLE
            if self.anim is not None:
                self.anim.set_clip("idle", reset=True)

    # --- rendering ----------------------------------------------------------
    def draw_health_bar(
        self,
        surface: pygame.Surface,
        width: int = 120,
        height: int = 10,
    ) -> None:
        bar_x = round(self.x - width * 0.5)
        bar_y = round(self.y - self.hurtbox_dims[1] - 30.0)
        pygame.draw.rect(surface, (20, 20, 20), (bar_x, bar_y, width, height))
        fill = max(0.0, min(1.0, self.hp / self.max_hp)) if self.max_hp else 0.0
        pygame.draw.rect(
            surface,
            (214, 70, 58),
            (bar_x + 1, bar_y + 1, round((width - 2) * fill), height - 2),
        )
        if self.invincible:
            pygame.draw.rect(surface, (120, 220, 255), (bar_x, bar_y, width, height), 1)

    def draw(self, surface: pygame.Surface) -> None:
        if self.anim is not None:
            flame = bool(getattr(self, "flame_time", 0.0) > 0.0)
            # In flame form, only dedicated flame art may be drawn. A normal
            # variant (e.g. an interrupted transform) draws its normal frames
            # untinted rather than disappearing; a flame-variant clip without
            # flame art is skipped.
            if (
                not flame
                or self.anim.variant == "normal"
                or self.anim.clip_name == "transform"
                or self.anim.current_is_flame_frame
            ):
                self.anim.draw(surface, self.x, self.y, self.facing)
        if self.flash > 0.0:
            pygame.draw.rect(surface, (255, 255, 255), self.hurtbox(), 2)
        if self.show_health_bar:
            self.draw_health_bar(surface)
