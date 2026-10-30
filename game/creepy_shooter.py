"""Creepy Shooter: platform sniper with a straight shot, lock-on bolt, back-roll and jump shot."""

from __future__ import annotations

import math

import pygame

from .combat import AttackRuntime
from .config import ASSETS_DIR
from .fighter import Fighter, FighterState

_LOCK_SPRITE_CACHE: dict[tuple[str, float], pygame.Surface | None] = {}


def _lock_sprite(index: int) -> pygame.Surface | None:
    path = (
        ASSETS_DIR / "frames" / "creepy_shooter" / "fx"
        / f"creepy_lock_{index:02d}.png"
    )
    try:
        mtime = path.stat().st_mtime
    except OSError:
        return None
    key = (str(path), mtime)
    if key not in _LOCK_SPRITE_CACHE:
        try:
            _LOCK_SPRITE_CACHE[key] = pygame.image.load(str(path)).convert_alpha()
        except pygame.error:
            _LOCK_SPRITE_CACHE[key] = None
    return _LOCK_SPRITE_CACHE[key]


class CreepyShooter(Fighter):
    show_health_bar = True

    def __init__(self, store, stage, entry, anim) -> None:
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
        self.walk_speed = float(cfg["move"]["walk"])
        self.jump_v = float(cfg["move"]["jump_v"])
        self.set_attack_stats(cfg)
        self.shot_cd_max = float(cfg["cooldowns"]["shot"])
        self.homing_cd_max = float(cfg["cooldowns"]["homing"])
        self.roll_cd_max = float(cfg["cooldowns"]["roll"])
        self.jump_cd_max = float(cfg["cooldowns"]["jump"])
        ai = cfg["ai"]
        self.near_range = float(ai["near_range"])
        self.far_range = float(ai["far_range"])
        self.level_tolerance = float(ai["level_tolerance"])
        self.decision_interval = float(ai["decision_interval"])
        self.roll_distance = float(ai["roll_distance"])
        self.roll_time = float(ai["roll_time"])
        self.platform_reach = float(ai["platform_reach"])
        self.jump_heights = [float(value) for value in ai["jump_heights"]]
        self.ai_enabled = True
        self.decision_cd = 0.0
        self.lock_target = None
        self.roll_dir = -1
        self.jump_plan = None
        self.jump_phase = 0
        self.jump_elapsed = 0.0
        self.jump_timeout = 0.0
        self.jump_start_y = 0.0
        self.jump_target_y = 0.0
        self.jump_target_x = 0.0
        self.jump_t_fall = 0.0
        self.jump_vx = 0.0
        self.reset()

    # --- update -------------------------------------------------------------
    def update(self, dt: float, scene) -> None:
        self.update_common(dt)
        self.shot_cd = max(0.0, self.shot_cd - dt)
        self.homing_cd = max(0.0, self.homing_cd - dt)
        self.roll_cd = max(0.0, self.roll_cd - dt)
        self.jump_cd = max(0.0, self.jump_cd - dt)
        self.decision_cd = max(0.0, self.decision_cd - dt)

        if self.state == FighterState.KO:
            self.vx = 0.0
            self.anim.update(dt)
            self.stage.move_fighter(self, dt)
            self._sync_ko_frame()
            return

        if self.state == FighterState.HURT:
            self.vx = 0.0
            self.anim.update(dt)
            self.stage.move_fighter(self, dt)
            if self.hitstun <= 0.0 and self.hp > 0.0 and self.on_ground:
                self.state = FighterState.IDLE
                self.anim.set_clip("idle")
            return

        if self.state == FighterState.ATTACK:
            self._update_attack(dt, scene)
            return

        if self.statuses.control_locked():
            self.vx = 0.0
            self.set_air_or_idle_anim()
            self.anim.update(dt)
            self.stage.move_fighter(self, dt)
            return

        if not self.on_ground:
            self._airborne_step(dt, scene)
            return

        target = scene.player
        if self.ai_enabled and scene.match_over is None and target.hp > 0.0:
            self._think(scene, target)
        else:
            self._hold()
        if self.state == FighterState.ATTACK:
            return
        self.anim.update(dt)
        self.stage.move_fighter(self, dt)

    def _airborne_step(self, dt: float, scene) -> None:
        self.set_air_or_idle_anim()
        self.anim.update(dt)
        self.stage.move_fighter(self, dt)
        if self.on_ground:
            self.vx = 0.0
            self.state = FighterState.IDLE
            self.anim.set_clip("idle")

    def _sync_ko_frame(self) -> None:
        if self.anim is not None and self.on_ground:
            self.anim.set_frame(1)

    def _hold(self) -> None:
        self.vx = 0.0
        if self.on_ground:
            self.state = FighterState.IDLE
            self.anim.set_clip("idle")

    # --- AI -----------------------------------------------------------------
    def _think(self, scene, target) -> None:
        if self.decision_cd > 0.0:
            return
        self.decision_cd = self.decision_interval
        dx = target.x - self.x
        if abs(dx) > 8.0:
            self.facing = 1 if dx > 0.0 else -1
        on_platform = self.stage.platform_top_at(self.x, self.y) is not None
        if on_platform:
            self._platform_think(scene, target)
        else:
            self._ground_think(scene, target)

    def _platform_think(self, scene, target) -> None:
        distance = abs(target.x - self.x)
        can_hit = self._can_hit_horizontally(scene, target)
        if distance <= self.near_range and self.roll_cd <= 0.0:
            self.start_attack("creepy_roll_shot", scene, target)
            return
        if not can_hit:
            if self.homing_cd <= 0.0:
                self.start_attack("creepy_homing_shot", scene, target)
                return
            self._hold()
            return
        if self.shot_cd <= 0.0:
            self.start_attack("creepy_shot", scene, target)
            return
        if self.homing_cd <= 0.0 and distance >= self.far_range:
            self.start_attack("creepy_homing_shot", scene, target)
            return
        self._hold()

    def _ground_think(self, scene, target) -> None:
        distance = abs(target.x - self.x)
        if distance <= self.near_range and self.roll_cd <= 0.0:
            self.start_attack("creepy_roll_shot", scene, target)
            return
        plan = self._jump_plan(scene)
        if plan is None:
            self._ground_attack(scene, target)
            return
        can_hit = self._can_hit_horizontally(scene, target)
        if can_hit and self.shot_cd <= 0.0:
            self.start_attack("creepy_shot", scene, target)
            return
        if not can_hit and self.homing_cd <= 0.0:
            self.start_attack("creepy_homing_shot", scene, target)
            return
        takeoff = plan["takeoff_x"]
        if abs(self.x - takeoff) > 6.0:
            direction = 1 if takeoff > self.x else -1
            self.facing = direction
            if self._blocked_ahead(scene):
                self._start_hop()
                return
            self.vx = direction * self.walk_speed
            self.state = FighterState.WALK
            self.anim.set_clip("walk")
            return
        if self.jump_cd <= 0.0:
            self.start_attack("creepy_jump_shot", scene, target)
            return
        self._ground_attack(scene, target)

    def _ground_attack(self, scene, target) -> None:
        if self._can_hit_horizontally(scene, target):
            if self.shot_cd <= 0.0:
                self.start_attack("creepy_shot", scene, target)
                return
        elif self.homing_cd <= 0.0:
            self.start_attack("creepy_homing_shot", scene, target)
            return
        self._hold()

    def _can_hit_horizontally(self, scene, target) -> bool:
        if abs(self.y - target.y) > self.level_tolerance:
            return False
        muzzle_x = self.x + self.facing * 48.0
        muzzle_y = self.y - 120.0
        chest_y = target.y - target.hurtbox_dims[1] * 0.5
        return not scene.stage.segment_hits_blocks(
            muzzle_x, muzzle_y, target.x, chest_y
        )

    def _blocked_ahead(self, scene) -> bool:
        probe_y = self.y - 30.0
        reach = self.stage_half_width + 20.0
        return scene.stage.segment_hits_blocks(
            self.x, probe_y, self.x + self.facing * reach, probe_y
        )

    def _start_hop(self) -> None:
        if not self.on_ground:
            return
        # A deliberate leap that clears a 90px ground barrier, not a small hop.
        self.vy = -self.jump_v * 1.15
        self.on_ground = False
        self.vx = self.facing * self.walk_speed * 2.0
        self.state = FighterState.AIR
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
        if attack_id == "creepy_shot":
            self.shot_cd = self.shot_cd_max
        elif attack_id == "creepy_homing_shot":
            self.homing_cd = self.homing_cd_max
            self.lock_target = target
        elif attack_id == "creepy_roll_shot":
            self.roll_cd = self.roll_cd_max
            self._begin_roll(scene)
        elif attack_id == "creepy_jump_shot":
            self.jump_cd = self.jump_cd_max
            self._begin_jump(scene)

    def _begin_roll(self, scene) -> None:
        self.roll_dir = -self.facing

    def _roll_step(self, dt: float, runtime, scene) -> None:
        if 0.15 <= runtime.time < 0.43:
            step = (self.roll_distance / self.roll_time) * dt
            self.stage.move_x(self, self.roll_dir * step)
            # The roll is not clamped to the platform: crossing the edge drops
            # the shooter. Gravity then runs for the rest of the attack.
            if (
                self.on_ground
                and self.y < scene.stage.ground_y - 1.0
                and scene.stage.platform_top_at(self.x, self.y) is None
            ):
                self.on_ground = False
                self.vy = 0.0
        self.vx = 0.0
        if not self.on_ground:
            self.stage.move_fighter(self, dt)

    def _jump_plan(self, scene) -> dict | None:
        """Nearest platform + a takeoff point outside its footprint."""
        low, high = scene.stage.walls
        half = self.stage_half_width
        best = None
        for rect in scene.stage.platforms:
            top = float(rect.top)
            if top not in self.jump_heights:
                continue
            if top > self.y - 80.0:
                continue
            candidates = []
            for side in (-1, 1):
                if side < 0:
                    takeoff = rect.left - (half + 6.0)
                    target = rect.left + half + 10.0
                else:
                    takeoff = rect.right + (half + 6.0)
                    target = rect.right - half - 10.0
                if not (low + half <= takeoff <= high - half):
                    continue
                body = pygame.Rect(
                    round(takeoff - half),
                    round(self.y - self.hurtbox_dims[1]),
                    round(half * 2),
                    round(self.hurtbox_dims[1]),
                )
                if scene.stage.blocks_enabled and any(
                    self.y > block.top + 1 and body.colliderect(block)
                    for block in scene.stage.blocks
                ):
                    continue
                candidates.append((abs(self.x - takeoff), takeoff, target))
            if not candidates:
                continue
            distance, takeoff, target = min(candidates)
            if best is None or distance < best["distance"]:
                best = {
                    "distance": distance,
                    "takeoff_x": takeoff,
                    "target_x": target,
                    "top": top,
                }
        return best

    def _begin_jump(self, scene) -> bool:
        plan = self._jump_plan(scene)
        if plan is None:
            return False
        self.jump_plan = plan
        self.jump_phase = 1
        self.jump_elapsed = 0.0
        self.jump_timeout = 1.6
        self.jump_start_y = self.y
        self.jump_target_y = float(plan["top"])
        self.jump_target_x = float(plan["target_x"])
        rise = max(1.0, self.jump_start_y - self.jump_target_y)
        overshoot = 80.0
        self.vy = -math.sqrt(2.0 * self.gravity * (rise + overshoot))
        self.vx = 0.0
        self.on_ground = False
        self.facing = 1 if self.jump_target_x >= self.x else -1
        disc = max(0.0, self.vy * self.vy - 2.0 * self.gravity * rise)
        self.jump_t_fall = (-self.vy + math.sqrt(disc)) / self.gravity
        self.jump_vx = 0.0
        return True

    def _jump_step(self, dt: float, scene) -> None:
        self.jump_elapsed += dt
        self.jump_timeout -= dt
        if self.jump_phase == 1:
            self.vx = 0.0
            if self.y <= self.jump_target_y - 1.0:
                self.jump_phase = 2
                remaining = max(0.08, self.jump_t_fall - self.jump_elapsed)
                self.jump_vx = max(
                    -300.0,
                    min(300.0, (self.jump_target_x - self.x) / remaining),
                )
        if self.jump_phase == 2:
            self.vx = self.jump_vx
        self.stage.move_fighter(self, dt)
        if self.on_ground and self.jump_phase > 0:
            self.jump_phase = 0
            self.vx = 0.0
        if self.jump_timeout <= 0.0 and self.jump_phase > 0:
            self.jump_phase = 0
            self.vx = 0.0

    def _update_attack(self, dt: float, scene) -> None:
        runtime = self.attack_runtime
        if runtime is None:
            self.state = FighterState.IDLE
            self.anim.set_clip("idle")
            return
        if self.attack_id == "creepy_roll_shot":
            self._roll_step(dt, runtime, scene)
        elif self.attack_id == "creepy_jump_shot":
            self._jump_step(dt, scene)
        else:
            self.vx = 0.0
            self.stage.move_fighter(self, dt)
        runtime.update(dt)
        self.anim.update(dt)
        if runtime.finished:
            self.state = FighterState.IDLE
            self.attack_runtime = None
            self.attack_id = None
            self.lock_target = None
            self.jump_phase = 0
            self.vx = 0.0
            if self.on_ground:
                self.anim.set_clip("idle")
            else:
                self.set_air_or_idle_anim()

    def force_attack(self, scene, target, attack_id: str = "creepy_shot") -> bool:
        if self.hp <= 0.0 or self.state in (FighterState.KO, FighterState.HURT):
            return False
        if attack_id not in self.store.attacks:
            return False
        if attack_id == "creepy_jump_shot":
            if not self.on_ground:
                return False
            plan = self._jump_plan(scene)
            if plan is None or abs(self.x - plan["takeoff_x"]) > 10.0:
                return False
        self.shot_cd = 0.0
        self.homing_cd = 0.0
        self.roll_cd = 0.0
        self.jump_cd = 0.0
        self.start_attack(attack_id, scene, target)
        return True

    def skill_remaining(self, attack_id: str) -> float:
        return {
            "creepy_shot": self.shot_cd,
            "creepy_homing_shot": self.homing_cd,
            "creepy_roll_shot": self.roll_cd,
            "creepy_jump_shot": self.jump_cd,
        }.get(attack_id, 0.0)

    # --- lock marker --------------------------------------------------------
    def lock_marker_progress(self) -> float | None:
        if self.attack_id != "creepy_homing_shot" or self.attack_runtime is None:
            return None
        if self.attack_runtime.time >= 1.0:
            return None
        if self.lock_target is None or self.lock_target.hp <= 0.0:
            return None
        return min(1.0, self.attack_runtime.time / 1.0)

    def draw_lock_marker(self, surface: pygame.Surface) -> None:
        if self.lock_marker_progress() is None:
            return
        elapsed = float(self.attack_runtime.time)
        # User-drawn 3-frame reticle: large / small (red dot) / large.
        index = 0 if elapsed < 0.3 else (1 if elapsed < 0.7 else 2)
        sprite = _lock_sprite(index)
        if sprite is None:
            return
        target = self.lock_target
        x = float(target.x)
        y = float(target.y - target.hurtbox_dims[1] * 0.5)
        surface.blit(sprite, sprite.get_rect(center=(round(x), round(y))))

    # --- reset --------------------------------------------------------------
    def reset(self) -> None:
        self.reset_common(self.spawn[0], self.spawn[1], -1)
        self.shot_cd = 0.0
        self.homing_cd = 0.0
        self.roll_cd = 0.0
        self.jump_cd = 0.0
        self.decision_cd = 0.0
        self.lock_target = None
        self.jump_plan = None
        self.jump_phase = 0
        self.jump_elapsed = 0.0
        self.jump_timeout = 0.0
        self.jump_vx = 0.0
        if self.anim is not None:
            self.anim.set_clip("idle")
