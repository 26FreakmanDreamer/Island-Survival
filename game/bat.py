"""Bat: free-flying enemy with a dive attack and a returning sonic wave."""

from __future__ import annotations

import math
import random

import pygame

from .combat import AttackRuntime
from .fighter import Fighter, FighterState

DIVE_SPEED = 520.0
DIVE_MOVE_FROM = 0.05
DIVE_MOVE_UNTIL = 0.30


class Bat(Fighter):
    """Side-view flier.

    Flight is kinematic: gravity is never applied outside KO, and the
    altitude is clamped to the arena's flight band. Blocks are real
    obstacles, so the body stops on a block top while descending and the
    sonic wave bounces off block rectangles.
    """

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
        self.walk_speed = float(cfg["move"]["walk"])

        dive_events = [
            event
            for event in self.store.attacks.get("bat_dive", {}).get("events", [])
            if event.get("type") == "hitbox"
        ]
        self.dive_box = (
            tuple(dive_events[0]["box"])
            if dive_events
            else (0.0, -70.0, 90.0, 70.0)
        )

        flight = cfg["flight"]
        self.flight_min_height = float(flight["min_height"])
        self.flight_max_height = float(flight["max_height"])
        self.preferred_height = float(flight["preferred_height"])
        self.vertical_speed = float(flight["vertical_speed"])
        self.bob = float(flight["bob"])
        self.bob_rate = float(flight["bob_rate"])

        ai = cfg["ai"]
        self.dive_range = float(ai["dive_range"])
        self.sonic_min_range = float(ai["sonic_min_range"])
        self.sonic_range = float(ai["sonic_range"])
        self.standoff = float(ai["standoff"])
        self.decision_interval = float(ai["decision_interval"])
        self.group_skill_gaps = {
            str(key): float(value)
            for key, value in ai.get("group_skill_gaps", {}).items()
        }
        self.opening_delay = float(ai.get("opening_delay", 0.0))
        flight = ai.get("flight_cycle", {})
        self.free_flight = float(flight.get("free_flight", 5.0))
        self.flight_low_stay = float(flight.get("low_stay", 2.0))
        self.flight_high_min = float(flight.get("high_height_min", 400.0))
        self.flight_high_max = float(flight.get("high_height_max", 600.0))
        self.flight_low_height = float(flight.get("low_height", 70.0))
        self.flight_high_count = int(flight.get("high_flights", 3))
        self.flight_low_count = int(flight.get("low_flights", 2))
        self.flight_stagger = float(flight.get("stagger", 1.0))

        self.dive_cd_max = float(cfg["cooldowns"]["dive"])
        self.sonic_cd_max = float(cfg["cooldowns"]["sonic"])
        self.dive_cd = 0.0
        self.sonic_cd = 0.0
        self.decision_cd = 0.0
        self.opening_cd = 0.0
        self.flight_side: str | None = None
        self.flight_target_height = self.flight_low_height
        self.flight_remaining = 0.0
        self.flight_bag: list[str] = []
        self.low_stay_remaining = 0.0
        self.free_target_x = 0.0
        self.free_target_timer = 0.0
        self.bob_phase = 0.0
        self.dive_dir = (-1.0, 0.0)
        self.flying = True
        self.mode = "fly"
        self.ai_enabled = True
        self.attack_runtime: AttackRuntime | None = None
        self.attack_id: str | None = None
        self.reset()

    # --- public state -------------------------------------------------------
    @property
    def hover_height(self) -> float:
        """Altitude above the ground; F2 displays this for any mode enemy."""
        return max(0.0, self.stage.ground_y - self.y)

    @property
    def flight_min_y(self) -> float:
        return self.stage.ground_y - self.flight_max_height

    @property
    def flight_max_y(self) -> float:
        return self.stage.ground_y - self.flight_min_height

    # --- update -------------------------------------------------------------
    def update(self, dt: float, scene) -> None:
        self.update_common(dt)
        self.dive_cd = max(0.0, self.dive_cd - dt)
        self.sonic_cd = max(0.0, self.sonic_cd - dt)
        self.decision_cd = max(0.0, self.decision_cd - dt)
        self.opening_cd = max(0.0, self.opening_cd - dt)
        self._update_flight_cycle(dt, scene)

        if self.state == FighterState.KO:
            self.vx = 0.0
            self.anim.update(dt)
            self.stage.move_fighter(self, dt)
            self._sync_ko_frame()
            return

        if self.state == FighterState.HURT:
            self.vx = 0.0
            self.anim.update(dt)
            self._move_flying(dt, scene)
            if self.hitstun <= 0.0 and self.hp > 0.0:
                self.mode = "fly"
                self.state = FighterState.IDLE
                self.anim.set_clip("fly")
            return

        if self.state == FighterState.ATTACK:
            self._update_attack(dt, scene)
            return

        if self.statuses.control_locked():
            self.vx = 0.0
            self.vy = 0.0
            self.mode = "fly"
            self.state = FighterState.AIR
            if self.statuses.has("stun"):
                self.anim.set_clip("stun")
                self.anim.set_frame(0)
            else:
                self.anim.set_clip("fly")
            self.anim.update(dt)
            if self.statuses.has("stun"):
                self.anim.set_frame(0)
            self._move_flying(dt, scene)
            return

        if self.ai_enabled and scene.match_over is None and scene.player.hp > 0.0:
            self._think(dt, scene, scene.player)
        else:
            self._hold(dt)
        self._move_flying(dt, scene)

    def _sync_ko_frame(self) -> None:
        """Hold the airborne KO frame until the bat actually lands."""
        if self.anim is None:
            return
        self.anim.set_frame(0 if not self.on_ground else 1)

    def _move_flying(self, dt: float, scene) -> None:
        total_vx = self.vx + self.kb_vx
        self.stage.move_x(self, total_vx * dt)

        previous_y = self.y
        self.y += self.vy * dt
        if self.y < self.flight_min_y:
            self.y = self.flight_min_y
            if self.vy < 0.0:
                self.vy = 0.0
        elif self.y > self.flight_max_y:
            self.y = self.flight_max_y
            if self.vy > 0.0:
                self.vy = 0.0

        if self.vy > 0.0 and scene.stage.blocks_enabled:
            half = self.hurtbox_width * 0.5
            for block in scene.stage.blocks:
                if self.x + half <= block.left or self.x - half >= block.right:
                    continue
                if previous_y <= block.top and self.y > block.top:
                    self.y = float(block.top)
                    self.vy = 0.0
                    break

        # Full AABB: a rising flyer stops against the underside too.
        if self.vy < 0.0 and scene.stage.blocks_enabled:
            half = self.hurtbox_width * 0.5
            height = self.hurtbox_dims[1]
            previous_top = previous_y - height
            current_top = self.y - height
            for block in scene.stage.blocks:
                if previous_top < block.bottom or current_top >= block.bottom:
                    continue
                if self.x + half <= block.left or self.x - half >= block.right:
                    continue
                self.y = float(block.bottom + height)
                self.vy = 0.0
                break

        self.on_ground = False

    def _make_flight_bag(self) -> list[str]:
        bag = ["high"] * self.flight_high_count
        bag += ["low"] * self.flight_low_count
        random.shuffle(bag)
        return bag

    def _next_flight_side(self) -> str:
        if not self.flight_bag:
            self.flight_bag = self._make_flight_bag()
        return self.flight_bag.pop(0)

    def _pick_free_target(self) -> None:
        half = self.hurtbox_width * 0.5
        low, high = self.stage.walls
        margin = half + 20.0
        self.free_target_x = random.uniform(low + margin, high - margin)
        self.free_target_timer = random.uniform(0.9, 1.4)

    def _enter_flight_side(self, side: str) -> None:
        self.flight_side = side
        if side == "high":
            self.flight_target_height = random.uniform(
                self.flight_high_min, self.flight_high_max
            )
        else:
            self.flight_target_height = self.flight_low_height
        self._pick_free_target()

    def _update_flight_cycle(self, dt: float, scene) -> None:
        """Five random free flights: three high, two low; low flights stay 2s."""
        if not self.ai_enabled or scene.match_over is not None:
            return
        if self.state == FighterState.KO:
            return
        if self.low_stay_remaining > 0.0:
            self.low_stay_remaining = max(0.0, self.low_stay_remaining - dt)
            if self.low_stay_remaining <= 0.0:
                self._enter_flight_side(self._next_flight_side())
                self.flight_remaining = self.free_flight
            return
        self.flight_remaining = max(0.0, self.flight_remaining - dt)
        if self.flight_remaining <= 0.0:
            if self.flight_side == "low":
                self.low_stay_remaining = self.flight_low_stay
            else:
                self._enter_flight_side(self._next_flight_side())
                self.flight_remaining = self.free_flight

    # --- AI -----------------------------------------------------------------
    def _think(self, dt: float, scene, target) -> None:
        dx = target.x - self.x
        if abs(dx) > 8.0:
            self.facing = 1 if dx > 0.0 else -1
        distance = abs(dx)
        self.bob_phase += dt

        if self.decision_cd <= 0.0 and self.opening_cd <= 0.0:
            sonic_ready = (
                self.flight_side == "high"
                and self.sonic_cd <= 0.0
                and self.sonic_min_range <= distance <= self.sonic_range
            )
            dive_ready = (
                self.dive_cd <= 0.0
                and distance <= self.dive_range
                and self._dive_can_reach(target)
            )
            sonic_available = sonic_ready and not self.group_skill_recent(
                scene,
                "bat_sonic",
                self.group_skill_gaps.get("bat_sonic", 0.0),
            )
            dive_available = dive_ready and not self.group_skill_recent(
                scene,
                "bat_dive",
                self.group_skill_gaps.get("bat_dive", 0.0),
            )
            # Randomness belongs to the sonic only. The dive is deterministic:
            # it fires whenever it is ready and its hitbox can actually reach
            # the player from the Bat's current altitude.
            if sonic_available and random.random() < 0.5:
                self.decision_cd = self.decision_interval
                self.start_attack("bat_sonic", scene, target)
                return
            if dive_available:
                self.decision_cd = self.decision_interval
                self.start_attack("bat_dive", scene, target)
                return
            if sonic_available or dive_available:
                # The sonic random gate skipped this decision; retry shortly.
                self.decision_cd = self.decision_interval

        self.free_target_timer = max(0.0, self.free_target_timer - dt)
        if (
            self.free_target_timer <= 0.0
            or abs(self.x - self.free_target_x) <= 18.0
        ):
            self._pick_free_target()
        target_x = self.free_target_x
        offset = self.flight_target_height + math.sin(
            self.bob_phase * self.bob_rate
        ) * self.bob
        offset = max(
            self.flight_min_height,
            min(self.flight_max_height, offset),
        )
        target_y = self.stage.ground_y - offset
        slow = self.statuses.slow_factor()

        self.vx = 0.0
        self.vy = 0.0
        if abs(target_x - self.x) > 6.0:
            self.vx = math.copysign(
                self.walk_speed * slow, target_x - self.x
            )
        if abs(target_y - self.y) > 4.0:
            self.vy = math.copysign(
                self.vertical_speed * slow, target_y - self.y
            )

        self.mode = "fly"
        self.state = FighterState.AIR
        moving = abs(self.vx) > 1.0 or abs(self.vy) > 1.0
        self.anim.set_clip("fly" if moving else "idle")
        self.anim.update(dt)

    def _dive_can_reach(self, target) -> bool:
        """Whether the dive hitbox can actually reach the target from here.

        The dive locks its direction at attack start, moves for 0.25s and
        keeps its hitbox in front of the body. Sampling that path prevents
        high-altitude Bats from diving into empty air.
        """
        if target is None or target.hp <= 0.0:
            return False
        aim_x = target.x
        aim_y = target.y - target.hurtbox_dims[1] * 0.5
        dx = aim_x - self.x
        dy = aim_y - self.y
        length = math.hypot(dx, dy)
        if length < 1e-6:
            return False
        ux = dx / length
        uy = dy / length
        bx, by, bw, bh = self.dive_box
        reach = DIVE_SPEED * (DIVE_MOVE_UNTIL - DIVE_MOVE_FROM)
        target_box = target.hurtbox()
        for step in range(1, 6):
            distance = reach * step / 5.0
            px = self.x + ux * distance
            py = self.y + uy * distance
            if self.facing >= 0:
                left = px + bx
            else:
                left = px - bx - bw
            top = py + by
            probe = pygame.Rect(
                round(left),
                round(top),
                round(bw),
                round(bh),
            )
            if probe.colliderect(target_box):
                return True
        return False

    def _hold(self, dt: float) -> None:
        self.vx = 0.0
        self.vy = 0.0
        self.mode = "fly"
        self.state = FighterState.AIR
        self.anim.set_clip("idle")
        self.anim.update(dt)

    # --- actions ------------------------------------------------------------
    def start_attack(self, attack_id: str, scene, target) -> None:
        if target is not None and abs(target.x - self.x) > 8.0:
            self.facing = 1 if target.x > self.x else -1
        self.attack_id = attack_id
        self.state = FighterState.ATTACK
        self.vx = 0.0
        self.vy = 0.0
        self.anim.set_clip(attack_id, reset=True)
        data = self.store.attacks[attack_id]
        self.attack_runtime = AttackRuntime(self, attack_id, data, target, scene)
        if attack_id == "bat_dive":
            self.dive_cd = self.dive_cd_max
            self._lock_dive_direction(target)
        elif attack_id == "bat_sonic":
            self.sonic_cd = self.sonic_cd_max
        self.note_attack_started(scene, attack_id)

    def _lock_dive_direction(self, target) -> None:
        """Aim the dive once at attack start; it does not home."""
        if target is None:
            self.dive_dir = (float(self.facing), 0.0)
            return
        aim_x = target.x
        aim_y = target.y - target.hurtbox_dims[1] * 0.5
        dx = aim_x - self.x
        dy = aim_y - self.y
        length = math.hypot(dx, dy)
        if length < 1e-6:
            self.dive_dir = (float(self.facing), 0.0)
        else:
            self.dive_dir = (dx / length, dy / length)

    def _update_attack(self, dt: float, scene) -> None:
        runtime = self.attack_runtime
        if runtime is None:
            self.state = FighterState.IDLE
            self.mode = "fly"
            self.anim.set_clip("fly")
            return

        if self.attack_id == "bat_dive":
            t = runtime.time
            if DIVE_MOVE_FROM <= t <= DIVE_MOVE_UNTIL:
                self.vx = self.dive_dir[0] * DIVE_SPEED
                self.vy = self.dive_dir[1] * DIVE_SPEED
            else:
                self.vx = 0.0
                self.vy = 0.0
            self._move_flying(dt, scene)
        else:
            self.vx = 0.0
            self.vy = 0.0

        runtime.update(dt)
        self.anim.update(dt)
        if runtime.finished:
            self.state = FighterState.IDLE
            self.mode = "fly"
            self.attack_runtime = None
            self.attack_id = None
            self.vx = 0.0
            self.vy = 0.0
            self.anim.set_clip("fly")

    def force_attack(self, scene, target, attack_id: str = "bat_dive") -> bool:
        if self.hp <= 0.0 or self.state in (FighterState.KO, FighterState.HURT):
            return False
        if attack_id not in self.store.attacks:
            return False
        self.dive_cd = 0.0
        self.sonic_cd = 0.0
        self.start_attack(attack_id, scene, target)
        return True

    def skill_remaining(self, attack_id: str) -> float:
        return {
            "bat_dive": self.dive_cd,
            "bat_sonic": self.sonic_cd,
        }.get(attack_id, 0.0)

    def on_projectile_hit(self, projectile) -> None:
        target = projectile.target
        if target is None or target.hp <= 0.0:
            return
        if getattr(projectile, "status", None) == "stun":
            target.statuses.add(
                "stun",
                float(projectile.status_duration),
                source="bat_sonic",
            )

    # --- reset --------------------------------------------------------------
    def reset(self) -> None:
        x, y = self.spawn
        self.reset_common(x, y, -1)
        # Only the sonic gets a random opening cooldown; the dive is
        # deterministic and is additionally gated by _dive_can_reach.
        self.dive_cd = 0.0
        self.sonic_cd = random.uniform(0.0, min(2.5, self.sonic_cd_max))
        self.decision_cd = 0.0
        self.opening_cd = self.opening_delay
        self.flight_bag = self._make_flight_bag()
        self._enter_flight_side(self._next_flight_side())
        self.flight_remaining = self.free_flight
        self.low_stay_remaining = 0.0
        self.bob_phase = 0.0
        self.cruise_height = self.preferred_height
        self.dive_dir = (-1.0, 0.0)
        self.flying = True
        self.mode = "fly"
        self.on_ground = False
        self.ai_enabled = True
        self.attack_runtime = None
        self.attack_id = None
        if self.anim is not None:
            self.anim.set_clip("fly", reset=True)
