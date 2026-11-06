"""Mech-Crab: front-facing mechanical boss with four telegraphed skills."""

from __future__ import annotations

import math

import pygame

from .combat import AttackRuntime, resolve_hit
from .config import ASSETS_DIR
from .fighter import Fighter, FighterState
from .fx import RingBurstFx

MECH_SKILLS = ("mech_laser", "mech_charge", "mech_claw_slam", "mech_leap_slam")

# Timings from the approved lock animation (0.22 / 0.18 / 0.42 s, 3 frames).
# The last frame holds through the leap flight instead of looping.
MECH_LOCK_FRAME_DURATIONS = (0.22, 0.18, 0.40)

_LOCK_SPRITE_CACHE: dict[tuple[str, float], pygame.Surface | None] = {}


def _lock_sprite(index: int) -> pygame.Surface | None:
    path = (
        ASSETS_DIR / "frames" / "mech_crab" / "fx"
        / f"mech_crab_lock_{index:02d}.png"
    )
    try:
        mtime = path.stat().st_mtime
    except OSError:
        return None
    key = (str(path), mtime)
    if key not in _LOCK_SPRITE_CACHE:
        try:
            _LOCK_SPRITE_CACHE[key] = pygame.image.load(
                str(path)
            ).convert_alpha()
        except pygame.error:
            _LOCK_SPRITE_CACHE[key] = None
    return _LOCK_SPRITE_CACHE[key]

# Measured from the approved front base: alpha bbox is 964x667, the glowing
# core ring is 94px wide and its center sits 464px above the feet. At body
# height 230 that is a 32.4px core, a 25.9px beam (0.8x) and a 160px offset.
MECH_CORE_OFFSET_Y = 160.0
MECH_CORE_DIAMETER = 32.4
MECH_LASER_WIDTH = 25.9
MECH_LASER_RANGE = 900.0
MECH_LASER_SPEED = math.pi / 2.0
MECH_LEAP_AOE = 100.0


class MechLaserBeam:
    """A rotating core laser with segment collision and one hit per target."""

    def __init__(
        self,
        owner,
        origin_x: float,
        origin_y: float,
        width: float,
        max_range: float,
        speed_rad: float,
    ) -> None:
        self.owner = owner
        self.origin_x = float(origin_x)
        self.origin_y = float(origin_y)
        self.width = float(width)
        self.max_range = float(max_range)
        self.speed_rad = float(speed_rad)
        self.angle = 0.0  # 0 is straight up; positive turns toward the right.
        self.time = 0.0
        self.alive = True
        self.blocked = False
        self.block_distance = self.max_range
        self.end_x = self.origin_x
        self.end_y = self.origin_y - self.max_range
        self.hit_ids: set[int] = set()
        self._refresh_end(None)

    def _direction(self) -> tuple[float, float]:
        return math.sin(self.angle), -math.cos(self.angle)

    def _refresh_end(self, scene) -> None:
        dx, dy = self._direction()
        full_x = self.origin_x + dx * self.max_range
        full_y = self.origin_y + dy * self.max_range
        self.end_x = full_x
        self.end_y = full_y
        self.blocked = False
        self.block_distance = self.max_range
        stage = getattr(scene, "stage", None) if scene is not None else None
        if stage is None or not stage.blocks_enabled:
            return
        best = self.max_range
        best_point = None
        for block in stage.blocks:
            hit = block.clipline(
                (self.origin_x, self.origin_y), (full_x, full_y)
            )
            if not hit:
                continue
            entry = hit[0]
            distance = math.hypot(
                entry[0] - self.origin_x, entry[1] - self.origin_y
            )
            if distance < best:
                best = distance
                best_point = entry
        if best_point is not None:
            self.blocked = True
            self.block_distance = best
            self.end_x = float(best_point[0])
            self.end_y = float(best_point[1])

    def update(self, dt: float, scene, target) -> None:
        self.time += dt
        if target is not None and target.hp > 0.0:
            aim_x = float(target.x)
            aim_y = float(target.y) - float(target.hurtbox_dims[1]) * 0.5
            desired = math.atan2(
                aim_x - self.origin_x, -(aim_y - self.origin_y)
            )
            delta = (desired - self.angle + math.pi) % math.tau - math.pi
            step = self.speed_rad * dt
            if abs(delta) <= step:
                self.angle = desired
            else:
                self.angle += math.copysign(step, delta)
        self._refresh_end(scene)

    def hits(self, target) -> bool:
        if target is None or target.hp <= 0.0 or id(target) in self.hit_ids:
            return False
        inflated = target.hurtbox().inflate(self.width, self.width)
        return bool(
            inflated.clipline(
                (self.origin_x, self.origin_y), (self.end_x, self.end_y)
            )
        )

    def draw(self, surface: pygame.Surface) -> None:
        if not self.alive:
            return
        ox, oy = round(self.origin_x), round(self.origin_y)
        ex, ey = round(self.end_x), round(self.end_y)
        width = max(2, int(round(self.width)))
        pygame.draw.line(
            surface, (110, 12, 18), (ox, oy), (ex, ey), max(3, int(width * 1.7))
        )
        pygame.draw.line(surface, (235, 45, 30), (ox, oy), (ex, ey), width)
        pygame.draw.line(
            surface, (255, 220, 150), (ox, oy), (ex, ey),
            max(2, int(width * 0.42)),
        )
        pygame.draw.circle(
            surface, (255, 90, 40), (ox, oy), max(3, int(width * 1.1))
        )
        pygame.draw.circle(
            surface, (255, 245, 210), (ox, oy), max(2, int(width * 0.45))
        )
        if self.blocked:
            pygame.draw.circle(
                surface, (255, 140, 70), (ex, ey), max(4, int(width * 0.8))
            )
            pygame.draw.circle(
                surface, (255, 230, 170), (ex, ey), max(2, int(width * 0.32))
            )
        for index in range(3):
            phase = self.time * 14.0 + index * 2.1
            sx = ex + math.cos(phase) * width * 0.95
            sy = ey + math.sin(phase) * width * 0.95
            pygame.draw.circle(
                surface, (255, 190, 90), (round(sx), round(sy)), 2
            )


class MechCrab(Fighter):
    show_health_bar = True
    # Visual body height; keeps the HP bar and name label above the shell.
    health_bar_lift = 230.0

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
        self.set_attack_stats(cfg)
        self.walk_speed = float(cfg["move"]["walk"])
        self.jump_v = float(cfg["move"]["jump_v"])
        self.laser_cd_max = float(cfg["cooldowns"]["laser"])
        self.charge_cd_max = float(cfg["cooldowns"]["charge"])
        self.claw_cd_max = float(cfg["cooldowns"]["claw"])
        self.leap_cd_max = float(cfg["cooldowns"]["leap"])
        ai = cfg["ai"]
        self.laser_min_range = float(ai["laser_min_range"])
        self.laser_range = float(ai["laser_range"])
        self.charge_min_range = float(ai["charge_min_range"])
        self.charge_range = float(ai["charge_range"])
        self.claw_range = float(ai["claw_range"])
        self.leap_min_range = float(ai["leap_min_range"])
        self.leap_range = float(ai["leap_range"])
        self.level_tolerance = float(ai["level_tolerance"])
        self.decision_interval = float(ai["decision_interval"])
        self.skill_gap_max = float(ai.get("skill_gap", 1.0))
        self.ai_enabled = True
        self.decision_cd = 0.0
        self.skill_gap = 0.0
        self.ignore_separation = False
        self.laser_beam: MechLaserBeam | None = None
        self.laser_cast_x = 0.0
        self.laser_cast_y = 0.0
        self.laser_beam_started = False
        self.leap_target_x: float | None = None
        self.leap_target_y: float | None = None
        self.leap_start_x = 0.0
        self.leap_start_y = 0.0
        self.leap_launched = False
        self.leap_landed = False
        self.claw_fx_spawned = False
        self.charge_dust_timer = 0.0
        self.charge_direction = -1
        self.leap_landing_fx = False
        self.reset()

    # --- lifecycle ----------------------------------------------------------
    def _clear_armor(self) -> None:
        effect = self.statuses.effects.get("super_armor")
        if effect is not None and effect.source in MECH_SKILLS:
            self.statuses.effects.pop("super_armor", None)

    def _reset_attack_state(self) -> None:
        self.attack_runtime = None
        self.attack_id = None
        self.laser_beam = None
        self.laser_beam_started = False
        self.leap_target_x = None
        self.leap_target_y = None
        self.leap_launched = False
        self.leap_landed = False
        self.leap_landing_fx = False
        self.ignore_separation = False
        self.claw_fx_spawned = False
        self.charge_dust_timer = 0.0
        self.charge_direction = self.facing
        self._clear_armor()

    def reset(self) -> None:
        self.reset_common(self.spawn[0], self.spawn[1], -1)
        self.laser_cd = 0.0
        self.charge_cd = 0.0
        self.claw_cd = 0.0
        self.leap_cd = 0.0
        self.skill_gap = 0.0
        self.decision_cd = 0.0
        self._reset_attack_state()
        if self.anim is not None:
            self.anim.set_clip("idle")

    def cancel_attack(self) -> None:
        self._reset_attack_state()
        super().cancel_attack()

    def _finish_attack(self) -> None:
        self._reset_attack_state()
        self.skill_gap = self.skill_gap_max
        self.state = FighterState.IDLE
        self.vx = 0.0
        self.vy = 0.0
        if self.anim is not None:
            self.anim.set_clip("idle")

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
        if self.statuses.has("super_armor"):
            self.hp = max(0.0, self.hp - damage)
            self.flash = 0.12
            if self.hp <= 0.0:
                self.state = FighterState.KO
                self.hitstun = 0.0
                self.kb_vx = 0.0
                self.kb_time = 0.0
                self.vy = 0.0
                self._reset_attack_state()
                if self.anim is not None:
                    self.anim.set_clip("ko", reset=True)
            return True
        return super().take_hit(
            damage, knockback, hitstun, direction, launch=launch
        )

    def on_hit_success(self, attack: dict, target, bonus: float) -> None:
        if self.attack_id == "mech_claw_slam" and target.hp > 0.0:
            duration = float(self.store.attacks["mech_claw_slam"].get("stun", 1.5))
            target.statuses.add("stun", duration, source="mech_claw_slam")

    # --- update -------------------------------------------------------------
    def update(self, dt: float, scene) -> None:
        self.update_common(dt)
        self.laser_cd = max(0.0, self.laser_cd - dt)
        self.charge_cd = max(0.0, self.charge_cd - dt)
        self.claw_cd = max(0.0, self.claw_cd - dt)
        self.leap_cd = max(0.0, self.leap_cd - dt)
        self.skill_gap = max(0.0, self.skill_gap - dt)
        self.decision_cd = max(0.0, self.decision_cd - dt)

        if self.state == FighterState.KO:
            # DOT damage can KO without going through take_hit(), so clear
            # skill FX here as well as in the armored/KO paths.
            self._reset_attack_state()
            self.vx = 0.0
            if self.anim is not None:
                self.anim.update(dt)
            self.stage.move_fighter(self, dt)
            return

        if self.state == FighterState.HURT:
            self.vx = 0.0
            if self.anim is not None:
                self.anim.update(dt)
            self.stage.move_fighter(self, dt)
            if self.hitstun <= 0.0 and self.hp > 0.0 and self.on_ground:
                self.state = FighterState.IDLE
                if self.anim is not None:
                    self.anim.set_clip("idle")
            return

        if self.state == FighterState.ATTACK:
            self._update_attack(dt, scene)
            return

        if self.statuses.control_locked():
            self.vx = 0.0
            self.set_air_or_idle_anim()
            if self.anim is not None:
                self.anim.update(dt)
            self.stage.move_fighter(self, dt)
            return

        if not self.on_ground:
            self.set_air_or_idle_anim()
            if self.anim is not None:
                self.anim.update(dt)
            self.stage.move_fighter(self, dt)
            if self.on_ground:
                self.vx = 0.0
                self.state = FighterState.IDLE
                if self.anim is not None:
                    self.anim.set_clip("idle")
            return

        target = scene.player
        if self.ai_enabled and scene.match_over is None and target.hp > 0.0:
            self._think(scene, target)
        else:
            self._hold()
        if self.state == FighterState.ATTACK:
            return
        if self.anim is not None:
            self.anim.update(dt)
        self.stage.move_fighter(self, dt)

    def _hold(self) -> None:
        self.vx = 0.0
        if self.on_ground:
            self.state = FighterState.IDLE
            if self.anim is not None:
                self.anim.set_clip("idle")

    def _walk_or_hold(self, distance: float) -> None:
        if distance > self.claw_range * 0.9:
            self.state = FighterState.WALK
            self.vx = self.facing * self.walk_speed
            if self.anim is not None:
                self.anim.set_clip("walk")
        else:
            self._hold()

    # --- AI -----------------------------------------------------------------
    def _think(self, scene, target) -> None:
        if self.decision_cd > 0.0:
            return
        self.decision_cd = self.decision_interval
        dx = target.x - self.x
        if abs(dx) > 8.0:
            self.facing = 1 if dx > 0.0 else -1
        distance = abs(dx)
        same_level = abs(target.y - self.y) <= self.level_tolerance
        core_y = self.y - float(
            self.store.attacks["mech_laser"].get(
                "beam_origin_height", MECH_CORE_OFFSET_Y
            )
        )
        target_center_y = target.y - target.hurtbox_dims[1] * 0.5
        line_of_sight = not scene.stage.segment_hits_blocks(
            self.x, core_y, target.x, target_center_y
        )
        laser_angle = abs(
            math.atan2(target.x - self.x, -(target_center_y - core_y))
        )
        can_laser = (
            self.laser_cd <= 0.0
            and self.laser_min_range <= distance <= self.laser_range
            and line_of_sight
            and laser_angle <= math.radians(135.0)
        )
        if self.skill_gap > 0.0:
            self._walk_or_hold(distance)
            return
        if (
            not same_level
            and self.leap_cd <= 0.0
            and self.leap_min_range <= distance <= self.leap_range
        ):
            self.start_attack("mech_leap_slam", scene, target)
            return
        if distance <= self.claw_range and same_level and self.claw_cd <= 0.0:
            self.start_attack("mech_claw_slam", scene, target)
            return
        if (
            self.charge_min_range <= distance <= self.charge_range
            and same_level
            and self.charge_cd <= 0.0
        ):
            self.start_attack("mech_charge", scene, target)
            return
        if can_laser:
            self.start_attack("mech_laser", scene, target)
            return
        if (
            self.leap_cd <= 0.0
            and self.leap_min_range < distance <= self.leap_range
        ):
            self.start_attack("mech_leap_slam", scene, target)
            return
        self._walk_or_hold(distance)

    def _surface_below(self, x: float, feet_y: float) -> float:
        candidates = []
        for rect in self.stage.platforms:
            if (
                rect.left - self.stage.land_margin
                <= x
                <= rect.right + self.stage.land_margin
            ):
                if float(rect.top) >= float(feet_y) - 1.0:
                    candidates.append(float(rect.top))
        if candidates:
            return min(candidates)
        return float(self.stage.ground_y)

    def _begin_leap(self, target) -> None:
        if target is None:
            return
        walls = self.stage.walls
        half = self.stage_half_width
        target_x = max(
            float(walls[0]) + half, min(float(target.x), float(walls[1]) - half)
        )
        target_y = self._surface_below(target_x, target.y)
        for rect in self.stage.platforms:
            if (
                rect.left - self.stage.land_margin
                <= target_x
                <= rect.right + self.stage.land_margin
                and abs(float(rect.top) - target_y) <= 1.0
            ):
                target_x = max(
                    float(rect.left) + half,
                    min(target_x, float(rect.right) - half),
                )
                break
        self.leap_target_x = target_x
        self.leap_target_y = target_y
        self.leap_launched = False
        self.leap_landed = False

    # --- actions ------------------------------------------------------------
    def _set_cooldown(self, attack_id: str) -> None:
        if attack_id == "mech_laser":
            self.laser_cd = self.laser_cd_max
        elif attack_id == "mech_charge":
            self.charge_cd = self.charge_cd_max
        elif attack_id == "mech_claw_slam":
            self.claw_cd = self.claw_cd_max
        elif attack_id == "mech_leap_slam":
            self.leap_cd = self.leap_cd_max

    def start_attack(self, attack_id: str, scene, target) -> None:
        if attack_id not in self.store.attacks:
            return
        if target is None:
            target = scene.player
        if target is not None and abs(target.x - self.x) > 8.0:
            self.facing = 1 if target.x > self.x else -1
        self._reset_attack_state()
        self.attack_id = attack_id
        self.state = FighterState.ATTACK
        self.vx = 0.0
        self.vy = 0.0
        if self.anim is not None:
            self.anim.set_clip(attack_id, reset=True)
        data = self.store.attacks[attack_id]
        self.attack_runtime = AttackRuntime(self, attack_id, data, target, scene)
        self._set_cooldown(attack_id)
        self.charge_direction = self.facing
        armor = float(data.get("armor_until", data.get("duration", 0.0)))
        if armor > 0.0:
            self.statuses.add("super_armor", armor, source=attack_id)
        if attack_id == "mech_laser":
            self.laser_cast_x = self.x
            self.laser_cast_y = self.y
        elif attack_id == "mech_leap_slam":
            self._begin_leap(target)

    def force_attack(self, scene, target, attack_id: str) -> bool:
        if self.hp <= 0.0 or self.state in (
            FighterState.KO,
            FighterState.HURT,
            FighterState.ATTACK,
        ):
            return False
        if attack_id not in MECH_SKILLS or not self.on_ground:
            return False
        self.laser_cd = 0.0
        self.charge_cd = 0.0
        self.claw_cd = 0.0
        self.leap_cd = 0.0
        self.skill_gap = 0.0
        self.start_attack(attack_id, scene, target)
        return True

    def skill_remaining(self, attack_id: str) -> float:
        return {
            "mech_laser": self.laser_cd,
            "mech_charge": self.charge_cd,
            "mech_claw_slam": self.claw_cd,
            "mech_leap_slam": self.leap_cd,
        }.get(attack_id, 0.0)

    # --- attack phases ------------------------------------------------------
    def _update_attack(self, dt: float, scene) -> None:
        runtime = self.attack_runtime
        if runtime is None:
            self._finish_attack()
            return
        if self.anim is not None:
            self.anim.update(dt)
        runtime.update(dt)
        attack_id = self.attack_id
        data = runtime.data
        target = runtime.target if runtime.target is not None else scene.player
        if attack_id == "mech_laser":
            self._update_laser(dt, scene, runtime, data, target)
        elif attack_id == "mech_charge":
            self._update_charge(dt, scene, runtime)
        elif attack_id == "mech_claw_slam":
            self._update_claw(dt, scene, runtime, data)
        elif attack_id == "mech_leap_slam":
            self._update_leap(dt, scene, runtime, data)
        if runtime.finished:
            self._finish_attack()

    def _update_laser(self, dt, scene, runtime, data, target) -> None:
        warning = float(data.get("warning", 1.0))
        active = float(data.get("active", 1.5))
        self.x = self.laser_cast_x
        self.y = self.laser_cast_y
        self.vx = 0.0
        self.vy = 0.0
        if runtime.time >= warning and not self.laser_beam_started:
            self.laser_beam_started = True
            origin_y = self.y - float(
                data.get("beam_origin_height", MECH_CORE_OFFSET_Y)
            )
            self.laser_beam = MechLaserBeam(
                self,
                self.x,
                origin_y,
                float(data.get("beam_width", MECH_LASER_WIDTH)),
                float(data.get("beam_range", MECH_LASER_RANGE)),
                math.radians(float(data.get("beam_speed_deg", 90.0))),
            )
        if self.laser_beam is None:
            return
        if runtime.time >= warning + active:
            self.laser_beam.alive = False
            self.laser_beam = None
            return
        self.laser_beam.update(dt, scene, target)
        if (
            target is not None
            and target.hp > 0.0
            and self.laser_beam.hits(target)
        ):
            self.laser_beam.hit_ids.add(id(target))
            resolve_hit(
                scene,
                self,
                target,
                data,
                {"knockback": 0, "hit_fx": "mech_laser_hit"},
            )

    def _update_charge(self, dt, scene, runtime) -> None:
        self.vx = 0.0
        if (
            self.on_ground
            and self.y < self.stage.ground_y - 1.0
            and self.stage.platform_top_at(self.x, self.y) is None
        ):
            self.on_ground = False
            self.vy = 0.0
        if not self.on_ground:
            self.stage.move_fighter(self, dt)
        warning = float(runtime.data.get("warning", 1.0))
        active = float(runtime.data.get("active", 0.55))
        if warning <= runtime.time < warning + active:
            self.charge_dust_timer -= dt
            if self.charge_dust_timer <= 0.0:
                self.charge_dust_timer = 0.07
                dust_x = self.x - self.facing * 70.0
                dust_y = self.y - 8.0
                scene.particles.emit_burst(
                    dust_x,
                    dust_y,
                    (190, 175, 145),
                    3,
                    speed=90.0,
                    life=(0.10, 0.22),
                    radius=(2.0, 4.0),
                    gravity=180.0,
                )

    def _update_claw(self, dt, scene, runtime, data) -> None:
        warning = float(data.get("warning", 0.5))
        if runtime.time >= warning and not self.claw_fx_spawned:
            self.claw_fx_spawned = True
            impact_x = self.x + self.facing * 130.0
            impact_y = self.y - 8.0
            scene.fx_effects.append(
                RingBurstFx(
                    impact_x,
                    impact_y,
                    (255, 150, 70),
                    life=0.22,
                    start_radius=10.0,
                    end_radius=64.0,
                    width=4,
                    sparks=6,
                    spark_color=(255, 225, 170),
                    kind="mech_claw_impact",
                )
            )
            scene.particles.emit_burst(
                impact_x,
                impact_y,
                (230, 190, 140),
                6,
                speed=180.0,
                life=(0.10, 0.22),
                gravity=240.0,
            )

    def _update_leap(self, dt, scene, runtime, data) -> None:
        if self.leap_target_x is None or self.leap_target_y is None:
            return
        warning = float(data.get("warning", 1.5))
        active = float(data.get("active", 0.65))
        if runtime.time >= warning and not self.leap_launched:
            self.leap_launched = True
            self.leap_start_x = self.x
            self.leap_start_y = self.y
        if not self.leap_launched or self.leap_landed:
            return
        progress = (runtime.time - warning) / max(active, 1e-6)
        if progress < 1.0:
            p = max(0.0, progress)
            arc = float(data.get("arc_height", 180.0))
            self.x = self.leap_start_x + (
                self.leap_target_x - self.leap_start_x
            ) * p
            self.y = (
                self.leap_start_y
                + (self.leap_target_y - self.leap_start_y) * p
                - arc * math.sin(math.pi * p)
            )
            self.on_ground = False
            self.ignore_separation = True
            self.vx = 0.0
            self.vy = 0.0
            return
        self.x = self.leap_target_x
        self.y = self.leap_target_y
        self.on_ground = True
        self.ignore_separation = False
        self.leap_landed = True
        self._landing_aoe(scene, data)

    def _landing_aoe(self, scene, data) -> None:
        radius = float(data.get("aoe_radius", MECH_LEAP_AOE))
        center_x = float(self.leap_target_x)
        center_y = float(self.leap_target_y)
        scene.fx_effects.append(
            RingBurstFx(
                center_x,
                center_y - 6.0,
                (255, 150, 70),
                life=0.28,
                start_radius=18.0,
                end_radius=radius + 30.0,
                width=5,
                sparks=10,
                spark_color=(255, 225, 170),
                kind="mech_leap_impact",
            )
        )
        scene.particles.emit_burst(
            center_x,
            center_y - 10.0,
            (220, 190, 150),
            12,
            speed=240.0,
            life=(0.12, 0.30),
            gravity=320.0,
        )
        for target in scene.targets_for(self):
            if target.invincible or target.hp <= 0.0:
                continue
            box = target.hurtbox()
            closest_x = min(max(center_x, box.left), box.right)
            closest_y = min(max(center_y, box.top), box.bottom)
            if (
                math.hypot(closest_x - center_x, closest_y - center_y)
                <= radius
            ):
                resolve_hit(
                    scene,
                    self,
                    target,
                    data,
                    {"knockback": 180, "hit_fx": "mech_leap_hit"},
                )

    # --- markers and beam ---------------------------------------------------
    def draw_lock_marker(self, surface: pygame.Surface) -> None:
        if self.laser_beam is not None:
            self.laser_beam.draw(surface)
        if (
            self.attack_id == "mech_leap_slam"
            and self.attack_runtime is not None
            and self.leap_target_x is not None
            and self.leap_target_y is not None
            and not self.leap_landed
        ):
            elapsed = float(self.attack_runtime.time)
            index = 0
            while (
                index < len(MECH_LOCK_FRAME_DURATIONS) - 1
                and elapsed >= MECH_LOCK_FRAME_DURATIONS[index]
            ):
                elapsed -= MECH_LOCK_FRAME_DURATIONS[index]
                index += 1
            sprite = _lock_sprite(index)
            if sprite is not None:
                surface.blit(
                    sprite,
                    sprite.get_rect(
                        center=(
                            round(self.leap_target_x),
                            round(self.leap_target_y),
                        )
                    ),
                )
        if (
            self.attack_id == "mech_laser"
            and self.attack_runtime is not None
            and self.attack_runtime.time
            < float(self.store.attacks["mech_laser"].get("warning", 1.0))
        ):
            core_y = self.y - float(
                self.store.attacks["mech_laser"].get(
                    "beam_origin_height", MECH_CORE_OFFSET_Y
                )
            )
            pulse = 0.5 + 0.5 * math.sin(self.attack_runtime.time * 18.0)
            glow = int(18 + 10 * pulse)
            pygame.draw.circle(
                surface, (255, 80, 40), (int(self.x), int(core_y)), glow, 3
            )
