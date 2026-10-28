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
    CLIMB = 8


CLIMB_SPEED = 160.0
# The back-view climb frames were staged at the same canvas/pivot as the
# standing frames, but the pose reads smaller in game. Scale both climb frames
# uniformly around the feet pivot so the head matches the standing sprite.
CLIMB_DRAW_SCALE = 1.2  # Lina default; Nyra overrides this per character.



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
        entry: dict | None = None,
    ) -> None:
        self.stage = stage
        self.anim = anim
        self.entry = entry or {}
        self.name = self.entry.get("name", type(self).__name__)
        self.skill_slots = list(self.entry.get("skill_slots", []))
        self.basic_atk = 0.0
        self.extra_atk = 0.0
        self.atk = 0.0
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
        self.knock_up_gravity = gravity
        self.on_ground = True
        self.climbing = False
        self.climb_ladder = None
        # Suppress an immediate re-grab after a deliberate exit (jump-off,
        # attack, hit). Cleared on landing or when the climb keys are released.
        self.climb_suppressed = False
        self.climb_anim_dir = None
        self.pre_climb_facing = None
        self.climb_draw_scale = CLIMB_DRAW_SCALE
        self.max_hp = float(max_hp)
        self.hp = float(max_hp)
        self.state = FighterState.IDLE
        self.state_time = 0.0
        self.hitstun = 0.0
        self.flash = 0.0
        self.invincible = False
        # Nyra's marks live on the target so every enemy has its own stack.
        self.marks = 0
        self.mark_burst_time = 0.0
        self.mark_burst_damage = 0.0
        self.statuses = StatusSet()
        self.attack_runtime = None
        self.attack_id = None

    def set_attack_stats(self, cfg: dict) -> None:
        """Copy the data-driven attack values used by the damage formula."""
        self.basic_atk = float(cfg.get("basic_atk", 0.0))
        self.extra_atk = float(cfg.get("extra_atk", 0.0))
        self.atk = self.basic_atk + self.extra_atk

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
        self.mark_burst_time = max(0.0, self.mark_burst_time - dt)
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
        self._stop_climb()
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
            self.vy = 0.0
            self.marks = 0
            self.mark_burst_time = 0.0
            self.mark_burst_damage = 0.0
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
        self._stop_climb()
        self.hp = max(0.0, self.hp - amount)
        self.flash = max(self.flash, 0.05)
        if self.hp <= 0.0:
            self.state = FighterState.KO
            self.kb_vx = 0.0
            self.kb_time = 0.0
            self.vy = 0.0
            self.marks = 0
            self.mark_burst_time = 0.0
            self.mark_burst_damage = 0.0
            if self.anim is not None:
                self.anim.set_clip("ko", reset=True)

    # --- hooks used by combat ----------------------------------------------
    def current_flame_bonus(self) -> float:
        return 0.0

    def on_hit_success(self, attack: dict, target, bonus: float) -> None:
        return

    def on_projectile_hit(self, projectile) -> None:
        return

    def force_skill(self, scene, target, slot: int) -> bool:
        """Trigger one of the enemy's four data-defined skill slots.

        ``slot`` is zero-based (V/C/X/Z -> 0/1/2/3). ``None`` slots and
        classes without ``force_attack`` are safe no-ops.
        """
        if slot < 0 or slot >= len(self.skill_slots):
            return False
        attack_id = self.skill_slots[slot]
        if not attack_id:
            return False
        force = getattr(self, "force_attack", None)
        if force is None:
            return False
        return bool(force(scene, target, attack_id))

    def skill_remaining(self, attack_id: str) -> float:
        """Cooldown remaining for the debug panel; overridden by enemies."""
        return 0.0

    def set_air_or_idle_anim(self) -> None:
        """Show jump frames while airborne and idle frames on the ground."""
        if self.anim is None:
            return
        if not self.on_ground:
            self.state = FighterState.AIR
            self.anim.set_clip("jump")
            self.anim.set_frame(0 if self.vy < 0.0 else 1)
        else:
            self.state = FighterState.IDLE
            self.anim.set_clip("idle")

    # --- climbing (player characters only) ----------------------------------
    def _climb_clip_available(self) -> bool:
        """True when the active variant has a climb clip."""
        if self.anim is None:
            return False
        table = (
            self.anim.flame_clips
            if self.anim.variant == "flame"
            else self.anim.default_clips
        )
        return "climb" in table

    def try_start_climb(self, input_state, scene) -> bool:
        """Grab a nearby ladder when W/S is held. Returns True while climbing."""
        if self.climbing:
            return True
        up = input_state.is_held("climb_up")
        down = input_state.is_held("climb_down")
        if self.climb_suppressed:
            if self.on_ground or not (up or down):
                self.climb_suppressed = False
            else:
                return False
        if up == down:
            return False
        ladder = scene.stage.ladder_for(self)
        if ladder is None:
            return False
        if up and self.y <= ladder.top_y + 1.0:
            # At the top W must keep its normal jump behaviour.
            return False
        if down and self.y >= ladder.bottom_y - 1.0:
            return False
        has_climb = self._climb_clip_available()
        if has_climb:
            # Back-view climb art is drawn unflipped; restore on exit.
            self.pre_climb_facing = self.facing
            self.facing = 1
        else:
            self.pre_climb_facing = None
        self.climb_anim_dir = 1 if down else 0
        self.x = float(ladder.rect.centerx)
        self.y = min(max(self.y, ladder.top_y), ladder.bottom_y)
        self.climbing = True
        self.climb_ladder = ladder
        self.vx = 0.0
        self.vy = 0.0
        self.on_ground = False
        self.state = FighterState.CLIMB
        if self.anim is not None:
            if has_climb:
                self.anim.set_clip("climb", reset=True)
                self.anim.set_frame(1 if down else 0)
            else:
                self.anim.set_clip("idle")
        return True

    def _update_climb(self, dt: float, input_state, scene) -> None:
        ladder = self.climb_ladder
        if ladder is None:
            self._stop_climb()
            return
        if self.statuses.control_locked() or self.hitstun > 0.0:
            self._stop_climb()
            self.on_ground = False
            self.state = FighterState.AIR
            return
        if any(
            input_state.buffer.has(action)
            for action in ("punch", "kick", "q", "e")
        ):
            self._stop_climb()
            self.on_ground = False
            self.state = FighterState.AIR
            return
        if input_state.is_held("climb_jump"):
            # Space is the only jump-off key; W keeps climbing.
            self._stop_climb()
            self.vy = -self.jump_v
            self.on_ground = False
            self.state = FighterState.AIR
            if self.anim is not None:
                self.anim.set_clip("jump")
            return

        up = input_state.is_held("climb_up")
        down = input_state.is_held("climb_down")
        moving = False
        if up and not down:
            self.y -= CLIMB_SPEED * dt
            moving = True
            if self.y <= ladder.top_y:
                self.y = float(ladder.top_y)
                self._finish_climb_top(scene)
                return
        elif down and not up:
            self.y += CLIMB_SPEED * dt
            moving = True
            if self.y >= ladder.bottom_y:
                self.y = float(ladder.bottom_y)
                self._finish_climb_bottom()
                return

        self.vx = 0.0
        self.vy = 0.0
        self.on_ground = False
        self.state = FighterState.CLIMB
        if self.anim is not None:
            if self._climb_clip_available():
                if self.anim.clip_name != "climb":
                    direction = 1 if down else 0
                    self.anim.set_clip("climb", reset=True)
                    self.anim.set_frame(direction)
                    self.climb_anim_dir = direction
                elif moving:
                    direction = 1 if down else 0
                    if self.climb_anim_dir != direction:
                        self.anim.set_clip("climb", reset=True)
                        self.anim.set_frame(direction)
                        self.climb_anim_dir = direction
                    self.anim.update(dt)
            else:
                # Staged fallback: Nyra/flame keep the old placeholders until
                # their own climb clips are approved.
                self.anim.set_clip("walk" if moving else "idle")
                if moving:
                    self.anim.update(dt)

    def _finish_climb_top(self, scene) -> None:
        ladder = self.climb_ladder
        if ladder is None:
            self._stop_climb()
            return
        on_platform = False
        if scene.stage.blocks_enabled:
            half = self.stage_half_width
            for block in scene.stage.blocks:
                if abs(block.top - ladder.top_y) > 1.0:
                    continue
                if block.left - half <= self.x <= block.right + half:
                    on_platform = True
                    break
        if on_platform:
            self._stop_climb()
            self.on_ground = True
            self.state = FighterState.IDLE
            if self.anim is not None:
                self.anim.set_clip("idle")
        else:
            # Blocks off or no platform at the top: hold the ladder top.
            self.y = float(ladder.top_y)
            self.on_ground = False
            self.state = FighterState.CLIMB
            if self.anim is not None:
                self.anim.set_clip("idle")

    def _finish_climb_bottom(self) -> None:
        ladder = self.climb_ladder
        if ladder is None:
            self._stop_climb()
            return
        self.y = float(ladder.bottom_y)
        self._stop_climb()
        self.on_ground = self.y >= self.stage.ground_y - 0.5
        if self.on_ground:
            self.state = FighterState.IDLE
            if self.anim is not None:
                self.anim.set_clip("idle")
        else:
            self.state = FighterState.AIR

    def _stop_climb(self) -> None:
        self.climbing = False
        self.climb_ladder = None
        self.climb_suppressed = True
        if self.pre_climb_facing is not None:
            self.facing = self.pre_climb_facing
        self.pre_climb_facing = None
        self.climb_anim_dir = None

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
        self._stop_climb()
        self.hitstun = 0.0
        self.flash = 0.0
        self.marks = 0
        self.mark_burst_time = 0.0
        self.mark_burst_damage = 0.0
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

    def draw(
        self,
        surface: pygame.Surface,
        tint: tuple[int, int, int] | None = None,
    ) -> None:
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
                scale = (
                    self.climb_draw_scale
                    if self.climbing and self.anim.clip_name == "climb"
                    else 1.0
                )
                self.anim.draw(
                    surface, self.x, self.y, self.facing, tint=tint, scale=scale
                )
        if self.flash > 0.0:
            pygame.draw.rect(surface, (255, 255, 255), self.hurtbox(), 2)
        if self.show_health_bar:
            self.draw_health_bar(surface)
