"""Crooked Witch: teleporting F7 caster with a one-time heal and four skills."""

from __future__ import annotations

import random

import pygame

from .combat import AttackRuntime, attack_damage
from .config import ASSETS_DIR
from .fighter import Fighter, FighterState
from .fx import RingBurstFx, SpriteStripFx
from .hazards import IceSpikeHazard
from .projectile import WitchFireball

LIGHTNING_CLIPS = {
    "witch_lightning_forward": "lightning_forward",
    "witch_lightning_up": "lightning_up",
    "witch_lightning_down": "lightning_down",
}

_STAFF_CACHE: dict[tuple[str, float], pygame.Surface | None] = {}


def _staff_image() -> pygame.Surface | None:
    """Floating staff prop for the hands-open heal cast pose only."""
    path = (
        ASSETS_DIR / "frames" / "crooked_witch" / "fx"
        / "crooked_witch_heal_staff_prop_v1.png"
    )
    try:
        mtime = path.stat().st_mtime
    except OSError:
        return None
    scale = 0.15
    key = (str(path), mtime)
    if key in _STAFF_CACHE:
        cached = _STAFF_CACHE[key]
        return cached.copy() if cached is not None else None
    try:
        image = pygame.image.load(str(path)).convert_alpha()
    except (OSError, pygame.error):
        _STAFF_CACHE[key] = None
        return None
    image = pygame.transform.smoothscale(
        image,
        (
            max(1, round(image.get_width() * scale)),
            max(1, round(image.get_height() * scale)),
        ),
    )
    _STAFF_CACHE[key] = image
    return image.copy()


class CrookedWitch(Fighter):
    show_health_bar = True
    is_crooked_witch = True

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
        self.knock_up_gravity = float(
            combat_cfg.get("knock_up_gravity", self.gravity)
        )

        cooldowns = cfg["cooldowns"]
        self.lightning_cd_max = float(cooldowns["lightning"])
        self.ice_cd_max = float(cooldowns["ice_spike"])
        self.potion_cd_max = float(cooldowns["potion"])
        self.fire_cd_max = float(cooldowns["fire_rain"])
        self.teleport_cfg = dict(cfg.get("teleport", {}))
        self.heal_cfg = dict(cfg.get("heal", {}))
        self.lightning_cfg = dict(cfg.get("lightning", {}))
        self.ice_cfg = dict(cfg.get("ice_spike", {}))
        self.potion_cfg = dict(cfg.get("potion", {}))
        self.fire_cfg = dict(cfg.get("fire_rain", {}))
        ai = cfg.get("ai", {})
        self.decision_interval = float(ai.get("decision_interval", 0.2))
        self.skill_gap_max = float(ai.get("skill_gap", 0.6))
        self.fire_rain_min_range = float(ai.get("fire_rain_min_range", 180.0))
        self.opening_delay = float(ai.get("opening_delay", 0.5))

        self.phase = "normal"
        self.phase_time = 0.0
        self.teleport_cd = 0.0
        self.damage_timer = 0.0
        self.teleport_pending = False
        self.teleport_from = (x, y)
        self.teleport_to = (x, y)

        self.heal_used = False
        self.heal_time = 0.0
        self.heal_tick = 0
        self.heal_return_pos = (float(x), float(y))
        self.heal_start_pos = (float(x), float(y))

        self.fire_time = 0.0
        self.fire_spawned = 0
        self.fire_origin = (float(x), float(y))
        self.fire_intro_duration = 1.39

        self.lightning_cd = 0.0
        self.ice_cd = 0.0
        self.potion_cd = 0.0
        self.fire_cd = 0.0
        self.decision_cd = 0.0
        self.skill_gap = 0.0
        self.opening_cd = self.opening_delay
        # Skill 4 may not be the first numbered skill used in a battle.
        self.opened_skill = False

        self.attack_runtime: AttackRuntime | None = None
        self.attack_id: str | None = None
        self.ice_spike_spot: tuple[float, float] | None = None
        self.ice_spike_spawned = False

        self.no_hitbox = False
        self.hidden = False
        self.invincible = False
        self.ignore_separation = False
        self.ai_enabled = True
        self.reset()

    # --- helpers ------------------------------------------------------------
    def _clear_special_flags(self) -> None:
        self.no_hitbox = False
        self.hidden = False
        self.invincible = False
        self.ignore_separation = False

    def _set_special_flags(self) -> None:
        self.no_hitbox = True
        self.invincible = True
        self.ignore_separation = True

    def _center_target(self) -> tuple[float, float]:
        return (
            float(self.heal_cfg.get("center_x", 640.0)),
            float(self.stage.ground_y) - float(self.heal_cfg.get("center_altitude", 260.0)),
        )

    def _heal_fx(self, scene) -> None:
        from .config import ASSETS_DIR

        fx_dir = ASSETS_DIR / "frames" / "crooked_witch" / "fx"
        frames = [
            fx_dir / f"crooked_witch_heal_fx_v2_{index:02d}.png"
            for index in range(20)
        ]
        scene.fx_effects.append(
            SpriteStripFx(
                frames, [0.05] * 20, self.x, self.y - 110.0,
                scale=0.45, kind="crooked_witch_heal",
            )
        )
        scene.fx_effects.append(
            RingBurstFx(
                self.x, self.y - 90.0, (90, 220, 120), life=1.0,
                start_radius=24.0, end_radius=130.0, width=4,
                sparks=6, spark_color=(200, 255, 200),
                kind="crooked_witch_heal_ring",
            )
        )

    def _teleport_fx(self, scene, x: float, y: float, direction: str) -> None:
        from .config import ASSETS_DIR

        fx_dir = ASSETS_DIR / "frames" / "crooked_witch" / "fx"
        frames = [
            fx_dir / f"crooked_witch_teleport_fx_v1_{direction}_{index:02d}.png"
            for index in range(6)
        ]
        scene.fx_effects.append(
            SpriteStripFx(
                frames, [0.10] * 6, x, y,
                scale=0.25, behind=True, kind="crooked_witch_teleport",
            )
        )
        scene.fx_effects.append(
            RingBurstFx(
                x, y - 100.0, (190, 130, 255), life=0.7,
                start_radius=24.0, end_radius=120.0, width=4,
                sparks=6, spark_color=(245, 225, 255),
                kind="crooked_witch_teleport_ring",
            )
        )

    def _fire_pulse_fx(self, scene) -> None:
        from .config import ASSETS_DIR

        fx_dir = ASSETS_DIR / "frames" / "crooked_witch" / "fx"
        frames = [
            fx_dir / f"crooked_witch_fire_rain_v7_pulse_{index:02d}.png"
            for index in range(45)
        ]
        durations = [0.04] * 24 + [0.04] + [0.02] * 20
        scene.fx_effects.append(
            SpriteStripFx(
                frames, durations, self.x, self.y - 150.0,
                pivot=(256.0, 1216.0), scale=0.55,
                # Frames 30-44 are the final light pillar. Keep its height but
                # narrow it to slightly more than the staff head (~33px).
                x_scale=0.36, x_scale_from=30,
                kind="crooked_witch_fire_pulse",
            )
        )

    # --- update -------------------------------------------------------------
    def update(self, dt: float, scene) -> None:
        self.update_common(dt)
        self.lightning_cd = max(0.0, self.lightning_cd - dt)
        self.ice_cd = max(0.0, self.ice_cd - dt)
        self.potion_cd = max(0.0, self.potion_cd - dt)
        self.fire_cd = max(0.0, self.fire_cd - dt)
        self.teleport_cd = max(0.0, self.teleport_cd - dt)
        self.decision_cd = max(0.0, self.decision_cd - dt)
        self.skill_gap = max(0.0, self.skill_gap - dt)
        self.opening_cd = max(0.0, self.opening_cd - dt)
        self.damage_timer += dt

        if self.phase != "normal":
            self._update_phase(dt, scene)
            return

        if self.state == FighterState.KO:
            self._clear_special_flags()
            self.vx = 0.0
            if self.anim is not None:
                self.anim.update(dt)
            self.stage.move_fighter(self, dt)
            return

        # One-time heal takes priority over every skill and teleport.
        if not self.heal_used and self.hp < self.max_hp * float(
            self.heal_cfg.get("threshold_pct", 0.5)
        ):
            self._start_heal(scene)
            return

        if (
            self.teleport_cd <= 0.0
            and not self.statuses.control_locked()
            and (
                self.teleport_pending
                or self.damage_timer >= float(
                    self.teleport_cfg.get("auto_no_damage", 8.0)
                )
            )
        ):
            self._start_teleport(scene)
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

    # --- teleport -----------------------------------------------------------
    def _pick_teleport_point(self, scene) -> tuple[float, float] | None:
        points = list(scene.stage.teleport_points)
        if not points:
            return None
        nearest = min(
            range(len(points)),
            key=lambda index: (points[index][0] - self.x) ** 2
            + (points[index][1] - self.y) ** 2,
        )
        current = None
        for index, point in enumerate(points):
            if abs(point[0] - self.x) <= 8.0 and abs(point[1] - self.y) <= 8.0:
                current = index
                break
        candidates = [
            point
            for index, point in enumerate(points)
            if index != nearest and index != current
        ]
        if not candidates:
            candidates = [point for index, point in enumerate(points) if index != current]
        if not candidates:
            candidates = points
        return random.choice(candidates)

    def _start_teleport(self, scene) -> None:
        destination = self._pick_teleport_point(scene)
        if destination is None:
            self.teleport_pending = False
            return
        self.phase = "teleport_out"
        self.phase_time = 0.0
        self.teleport_pending = False
        self.teleport_from = (self.x, self.y)
        self.teleport_to = destination
        self.teleport_cd = float(self.teleport_cfg.get("cooldown", 8.0))
        self.damage_timer = 0.0
        self._set_special_flags()
        self.hidden = True
        self.vx = 0.0
        self.vy = 0.0
        self.state = FighterState.IDLE
        if self.anim is not None:
            self.anim.set_clip("teleport_out", reset=True)
        self._teleport_fx(scene, self.x, self.y, "out")

    # --- heal ---------------------------------------------------------------
    def _start_heal(self, scene) -> None:
        self.heal_used = True
        self.phase = "heal_in"
        self.phase_time = 0.0
        self.heal_time = 0.0
        self.heal_tick = 0
        self.heal_return_pos = (self.x, self.y)
        self.heal_start_pos = (self.x, self.y)
        self._set_special_flags()
        self.vx = 0.0
        self.vy = 0.0
        self.statuses.clear()
        self.state = FighterState.IDLE
        if self.anim is not None:
            self.anim.set_clip("fly_takeoff", reset=True)

    def _update_heal_in(self, dt: float, scene) -> None:
        duration = float(self.heal_cfg.get("fly_in", 1.6))
        self.phase_time += dt
        progress = min(1.0, self.phase_time / max(duration, 1e-6))
        sx, sy = self.heal_start_pos
        cx, cy = self._center_target()
        self.x = sx + (cx - sx) * progress
        self.y = sy + (cy - sy) * progress
        if self.anim is not None:
            if self.anim.clip_name == "fly_takeoff" and progress >= 0.4:
                self.anim.set_clip("fly_loop")
            self.anim.update(dt)
        if progress >= 1.0:
            self.phase = "heal_cast"
            self.phase_time = 0.0
            self.heal_time = 0.0
            self.heal_tick = 0
            if self.anim is not None:
                self.anim.set_clip("heal", reset=True)

    def _update_heal_cast(self, dt: float, scene) -> None:
        self.heal_time += dt
        self.statuses.clear()
        if self.anim is not None:
            self.anim.update(dt)
        duration = float(self.heal_cfg.get("duration", 5.0))
        while self.heal_tick < 5 and self.heal_time >= self.heal_tick + 1.0:
            self.heal_tick += 1
            self.hp = min(
                self.max_hp,
                self.hp + self.max_hp * float(
                    self.heal_cfg.get("heal_pct_per_tick", 0.06)
                ),
            )
            self._heal_fx(scene)
        if self.heal_time >= duration + 0.8:
            self.phase = "heal_out"
            self.phase_time = 0.0
            if self.anim is not None:
                self.anim.set_clip("fly_land", reset=True)

    def _update_heal_out(self, dt: float, scene) -> None:
        duration = float(self.heal_cfg.get("fly_out", 1.6))
        self.phase_time += dt
        progress = min(1.0, self.phase_time / max(duration, 1e-6))
        sx, sy = self._center_target()
        rx, ry = self.heal_return_pos
        self.x = sx + (rx - sx) * progress
        self.y = sy + (ry - sy) * progress
        if self.anim is not None:
            if self.anim.clip_name == "fly_land" and progress >= 0.6:
                self.anim.set_clip("fly_loop")
            self.anim.update(dt)
        if progress >= 1.0:
            self._finish_phase()

    # --- fire rain ----------------------------------------------------------
    def _start_fire_rain(self, scene) -> None:
        self.phase = "fire_in"
        self.phase_time = 0.0
        self.fire_time = 0.0
        self.fire_spawned = 0
        self.fire_origin = (self.x, self.y)
        # instruction.docx: skill 4 enters cooldown only after the skill ends.
        self._set_special_flags()
        self.vx = 0.0
        self.vy = 0.0
        self.statuses.clear()
        self.state = FighterState.IDLE
        if self.anim is not None:
            self.anim.set_clip("fly_takeoff", reset=True)

    def _update_fire_in(self, dt: float, scene) -> None:
        duration = float(self.fire_cfg.get("fly_in", 1.6))
        self.phase_time += dt
        progress = min(1.0, self.phase_time / max(duration, 1e-6))
        sx, sy = self.fire_origin
        cx, cy = self._center_target()
        self.x = sx + (cx - sx) * progress
        self.y = sy + (cy - sy) * progress
        if self.anim is not None:
            if self.anim.clip_name == "fly_takeoff" and progress >= 0.4:
                self.anim.set_clip("fly_loop")
            self.anim.update(dt)
        if progress >= 1.0:
            self.phase = "fire_cast"
            self.phase_time = 0.0
            self.fire_time = 0.0
            self.fire_spawned = 0
            if self.anim is not None:
                self.anim.set_clip("fire_rain_intro", reset=True)
            self._fire_pulse_fx(scene)

    def _update_fire_cast(self, dt: float, scene) -> None:
        self.fire_time += dt
        self.statuses.clear()
        if self.anim is not None:
            if self.fire_time < self.fire_intro_duration:
                self.anim.set_clip("fire_rain_intro")
            else:
                self.anim.set_clip("fire_rain_hold")
            self.anim.update(dt)
        target = scene.player
        while (
            self.fire_spawned < int(self.fire_cfg.get("count", 10))
            and target is not None
            and self.fire_time
            >= self.fire_intro_duration
            + self.fire_spawned * float(self.fire_cfg.get("interval", 0.8))
        ):
            self._spawn_fireball(scene, target)
            self.fire_spawned += 1
        total = (
            self.fire_intro_duration
            + (int(self.fire_cfg.get("count", 10)) - 1)
            * float(self.fire_cfg.get("interval", 0.8))
            + 0.2
        )
        if self.fire_spawned >= int(self.fire_cfg.get("count", 10)) and self.fire_time >= total:
            self.phase = "fire_out"
            self.phase_time = 0.0
            if self.anim is not None:
                self.anim.set_clip("fly_land", reset=True)

    def _spawn_fireball(self, scene, target) -> None:
        attack = self.store.attacks["witch_fire_rain"]
        scene.projectiles.append(
            WitchFireball(
                owner=self,
                target=target,
                x=target.x,
                y=-120.0,
                fall_speed=float(self.fire_cfg.get("fall_speed", 900.0)),
                damage=attack_damage(self, attack),
                knockback=0.0,
                hitstun=0.2,
                hitstop=0.04,
            )
        )

    def _update_fire_out(self, dt: float, scene) -> None:
        duration = float(self.fire_cfg.get("fly_out", 1.6))
        self.phase_time += dt
        progress = min(1.0, self.phase_time / max(duration, 1e-6))
        cx, cy = self._center_target()
        ox, oy = self.fire_origin
        self.x = cx + (ox - cx) * progress
        self.y = cy + (oy - cy) * progress
        if self.anim is not None:
            if self.anim.clip_name == "fly_land" and progress >= 0.6:
                self.anim.set_clip("fly_loop")
            self.anim.update(dt)
        if progress >= 1.0:
            self._finish_phase()

    def _update_phase(self, dt: float, scene) -> None:
        if self.phase == "teleport_out":
            self.phase_time += dt
            if self.anim is not None:
                self.anim.update(dt)
            if self.phase_time >= float(self.teleport_cfg.get("out_time", 0.30)):
                self.x, self.y = self.teleport_to
                self.on_ground = True
                self.vx = 0.0
                self.vy = 0.0
                self.phase = "teleport_in"
                self.phase_time = 0.0
                if self.anim is not None:
                    self.anim.set_clip("teleport_in", reset=True)
                self._teleport_fx(scene, self.x, self.y, "in")
            return
        if self.phase == "teleport_in":
            self.phase_time += dt
            if self.anim is not None:
                self.anim.update(dt)
            if self.phase_time >= float(self.teleport_cfg.get("in_time", 0.30)):
                self._finish_phase()
                target = scene.player
                if target is not None and target.hp > 0.0:
                    self.facing = 1 if target.x >= self.x else -1
            return
        if self.phase == "heal_in":
            self._update_heal_in(dt, scene)
            return
        if self.phase == "heal_cast":
            self._update_heal_cast(dt, scene)
            return
        if self.phase == "heal_out":
            self._update_heal_out(dt, scene)
            return
        if self.phase == "fire_in":
            self._update_fire_in(dt, scene)
            return
        if self.phase == "fire_cast":
            self._update_fire_cast(dt, scene)
            return
        if self.phase == "fire_out":
            self._update_fire_out(dt, scene)

    def _finish_phase(self) -> None:
        if self.phase == "fire_out":
            # Skill 4's 15s cooldown starts when the whole skill (including
            # the return flight) ends, not at cast.
            self.fire_cd = self.fire_cd_max
        self.phase = "normal"
        self.phase_time = 0.0
        self.on_ground = True
        self._clear_special_flags()
        self._clear_special_anim()
        self.state = FighterState.IDLE
        if self.anim is not None:
            self.anim.set_clip("idle", reset=True)

    def _clear_special_anim(self) -> None:
        if self.anim is not None and self.anim.clip_name in (
            "teleport_out", "teleport_in", "fly_takeoff", "fly_loop", "fly_land",
        ):
            self.anim.set_clip("idle")

    # --- attacks ------------------------------------------------------------
    def _staff_tip(self) -> tuple[float, float]:
        facing = 1 if self.facing >= 0 else -1
        return self.x + facing * 48.0, self.y - 150.0

    def _choose_lightning_attack(self, scene, target) -> str | None:
        if target is None or target.hp <= 0.0:
            return None
        same_height = abs(target.y - self.y) <= float(
            self.lightning_cfg.get("same_height_tolerance", 80.0)
        )
        if same_height:
            variant = "forward"
        else:
            if abs(target.x - self.x) <= float(
                self.lightning_cfg.get("close_x", 140.0)
            ):
                return None
            variant = "up" if target.y < self.y else "down"
        tip_x, tip_y = self._staff_tip()
        target_y = target.y - target.hurtbox_dims[1] * 0.5
        if scene.stage.segment_hits_blocks(tip_x, tip_y, target.x, target_y):
            return None
        return f"witch_lightning_{variant}"

    def _find_ice_spot(self, scene, target) -> tuple[float, float] | None:
        if target is None or target.hp <= 0.0:
            return None
        surface = scene.stage.surface_at_feet(target.x, target.y)
        if surface is None:
            return None
        toward = 1 if self.x >= target.x else -1
        spot_x = target.x + toward * float(self.ice_cfg.get("spot_offset", 80.0))
        low, high = scene.stage.walls
        for block in scene.stage.platforms:
            if abs(block.top - surface) <= 1.0 and block.left <= target.x <= block.right:
                low = float(block.left)
                high = float(block.right)
                break
        spot_x = max(low + 4.0, min(high - 4.0, spot_x))
        return spot_x, float(surface)

    def start_attack(self, attack_id: str, scene, target) -> bool:
        if attack_id == "witch_lightning":
            attack_id = self._choose_lightning_attack(scene, target)
            if attack_id is None:
                return False
        if attack_id == "witch_fire_rain":
            self.opened_skill = True
            self._start_fire_rain(scene)
            return True
        if attack_id not in self.store.attacks:
            return False
        if target is not None and target.hp > 0.0 and abs(target.x - self.x) > 8.0:
            self.facing = 1 if target.x > self.x else -1
        self.opened_skill = True
        self.attack_id = attack_id
        self.state = FighterState.ATTACK
        self.vx = 0.0
        self.vy = 0.0
        self.ice_spike_spawned = False
        self.ice_spike_spot = None
        if attack_id in LIGHTNING_CLIPS:
            clip = LIGHTNING_CLIPS[attack_id]
            self.lightning_cd = self.lightning_cd_max
        elif attack_id == "witch_ice_spike":
            clip = "ice_spike"
            self.ice_cd = self.ice_cd_max
            self.ice_spike_spot = self._find_ice_spot(scene, target)
        elif attack_id == "witch_potion":
            clip = "potion"
            self.potion_cd = self.potion_cd_max
        else:
            clip = attack_id
        if self.anim is not None:
            self.anim.set_clip(clip, reset=True)
        data = self.store.attacks[attack_id]
        self.attack_runtime = AttackRuntime(self, attack_id, data, target, scene)
        return True

    def _update_attack(self, dt: float, scene) -> None:
        runtime = self.attack_runtime
        if runtime is None:
            self._finish_attack()
            return
        if (
            self.attack_id == "witch_ice_spike"
            and not self.ice_spike_spawned
            and runtime.time >= 0.30
        ):
            self.ice_spike_spawned = True
            if self.ice_spike_spot is not None:
                spot_x, surface = self.ice_spike_spot
                scene.hazards.append(
                    IceSpikeHazard(
                        owner=self,
                        x=spot_x,
                        surface_y=surface,
                        radius=float(self.ice_cfg.get("radius", 65.0)),
                        warning_time=float(self.ice_cfg.get("warning_time", 1.0)),
                        attack_data=self.store.attacks["witch_ice_spike"],
                        freeze_duration=float(
                            self.ice_cfg.get("freeze_duration", 1.5)
                        ),
                    )
                )
        if self.anim is not None:
            self.anim.update(dt)
        runtime.update(dt)
        if runtime.finished:
            self._finish_attack()

    def _finish_attack(self) -> None:
        self.attack_runtime = None
        self.attack_id = None
        self.ice_spike_spot = None
        self.skill_gap = self.skill_gap_max
        self.state = FighterState.IDLE
        self.vx = 0.0
        if self.anim is not None:
            self.anim.set_clip("idle", reset=True)

    # --- AI -----------------------------------------------------------------
    def _think(self, scene, target) -> None:
        distance = abs(target.x - self.x)
        height = abs(target.y - self.y)
        if self.opening_cd > 0.0 or self.decision_cd > 0.0:
            # Between AI decisions, keep walking instead of resetting to idle
            # every tick; otherwise the walk clip only plays one frame.
            if self.state != FighterState.WALK:
                self._hold()
            return
        self.decision_cd = self.decision_interval

        on_platform = (
            self.stage.platform_top_at(self.x, self.y) is not None
        )
        if self.skill_gap <= 0.0:
            # instruction.docx priority: ground 1>2>3>4, platform 3>1>2>4.
            order = (
                ("potion", "lightning", "ice", "fire")
                if on_platform
                else ("lightning", "ice", "potion", "fire")
            )
            for skill in order:
                if self._try_skill(skill, scene, target, distance):
                    return

        if height > 12.0 and not on_platform:
            # She never jumps; hold and let teleport close the gap.
            self._hold()
            return
        if distance > 110.0:
            self.state = FighterState.WALK
            self.vx = self.facing * self.walk_speed * self.statuses.slow_factor()
            if self.anim is not None:
                self.anim.set_clip("walk")
        else:
            self._hold()

    def _try_skill(self, skill: str, scene, target, distance: float) -> bool:
        if skill == "lightning" and self.lightning_cd <= 0.0:
            attack_id = self._choose_lightning_attack(scene, target)
            if attack_id is not None:
                return self.start_attack(attack_id, scene, target)
        elif skill == "ice" and self.ice_cd <= 0.0:
            if self._find_ice_spot(scene, target) is not None:
                return self.start_attack("witch_ice_spike", scene, target)
        elif skill == "potion" and self.potion_cd <= 0.0:
            return self.start_attack("witch_potion", scene, target)
        elif (
            skill == "fire"
            and self.fire_cd <= 0.0
            and self.opened_skill
            and distance >= self.fire_rain_min_range
        ):
            self._start_fire_rain(scene)
            return True
        return False

    # --- reactions ----------------------------------------------------------
    def take_hit(
        self,
        damage: float,
        knockback: float,
        hitstun: float,
        direction: int,
        launch: float = 0.0,
    ) -> bool:
        result = super().take_hit(
            damage, knockback, hitstun, direction, launch=launch
        )
        if result:
            self.damage_timer = 0.0
            if self.phase == "normal":
                if not self.heal_used and self.hp < self.max_hp * float(
                    self.heal_cfg.get("threshold_pct", 0.5)
                ):
                    self.heal_pending = True
                if self.teleport_cd <= 0.0 and not self.statuses.control_locked():
                    self.teleport_pending = True
        return result

    def on_projectile_hit(self, projectile) -> None:
        target = projectile.target
        if target is None or target.hp <= 0.0:
            return
        kind = getattr(projectile, "kind", "")
        if kind.startswith("witch_lightning"):
            target.statuses.add_vulnerable(
                float(self.lightning_cfg.get("vulnerable_pct", 0.20)),
                float(self.lightning_cfg.get("vulnerable_duration", 3.0)),
                int(self.lightning_cfg.get("vulnerable_max_stacks", 3)),
                source="witch_lightning",
            )
            return
        if kind == "witch_potion":
            target.statuses.add_poison(
                "witch_potion_hit",
                float(self.potion_cfg.get("poison_duration", 3.0)),
                target.max_hp * float(
                    self.potion_cfg.get("hit_poison_pct_per_sec", 0.03)
                ),
            )
            target.statuses.add_slow(
                1.0 - float(self.potion_cfg.get("hit_slow", 0.30)),
                float(self.potion_cfg.get("poison_duration", 3.0)),
                source="witch_potion_hit",
            )
            return
        if kind == "witch_fireball":
            target.statuses.add(
                "burn",
                float(self.fire_cfg.get("burn_duration", 3.0)),
                source="witch_fire_rain",
                dps=float(self.fire_cfg.get("burn_dps", 5.0)),
            )

    # --- debug hooks --------------------------------------------------------
    def force_attack(self, scene, target, attack_id: str = "witch_lightning") -> bool:
        if self.hp <= 0.0 or self.state in (FighterState.KO, FighterState.HURT):
            return False
        if self.phase != "normal":
            return False
        if attack_id == "witch_lightning":
            attack_id = self._choose_lightning_attack(scene, target) or "witch_lightning_forward"
        if attack_id in LIGHTNING_CLIPS:
            self.lightning_cd = 0.0
        elif attack_id == "witch_ice_spike":
            self.ice_cd = 0.0
        elif attack_id == "witch_potion":
            self.potion_cd = 0.0
        elif attack_id == "witch_fire_rain":
            self.fire_cd = 0.0
        return self.start_attack(attack_id, scene, target)

    def skill_remaining(self, attack_id: str) -> float:
        if attack_id in LIGHTNING_CLIPS or attack_id == "witch_lightning":
            return self.lightning_cd
        if attack_id == "witch_ice_spike":
            return self.ice_cd
        if attack_id == "witch_potion":
            return self.potion_cd
        if attack_id == "witch_fire_rain":
            return self.fire_cd
        return 0.0

    # --- rendering ----------------------------------------------------------
    def draw(self, surface, tint=None) -> None:
        # The heal_cast frames have both hands open (no staff), so keep the
        # independent staff visible there. The fly frames already hold her own
        # staff, so no prop is drawn in heal_in/heal_out.
        if self.phase == "heal_cast":
            staff = _staff_image()
            if staff is not None:
                if self.facing < 0:
                    staff = pygame.transform.flip(staff, True, False)
                surface.blit(
                    staff,
                    staff.get_rect(
                        center=(
                            round(self.x + self.facing * 95.0),
                            round(self.y - 110.0),
                        )
                    ),
                )
        super().draw(surface, tint)

    # --- reset --------------------------------------------------------------
    def reset(self) -> None:
        x, y = self.spawn
        self.reset_common(x, y, -1)
        self.phase = "normal"
        self.phase_time = 0.0
        self.teleport_cd = 0.0
        self.damage_timer = 0.0
        self.teleport_pending = False
        self.teleport_from = (x, y)
        self.teleport_to = (x, y)
        self.heal_used = False
        self.heal_time = 0.0
        self.heal_tick = 0
        self.heal_return_pos = (x, y)
        self.heal_start_pos = (x, y)
        self.heal_pending = False
        self.fire_time = 0.0
        self.fire_spawned = 0
        self.fire_origin = (x, y)
        self.lightning_cd = 0.0
        self.ice_cd = 0.0
        self.potion_cd = 0.0
        self.fire_cd = 0.0
        self.decision_cd = 0.0
        self.skill_gap = 0.0
        self.opening_cd = self.opening_delay
        self.opened_skill = False
        self.attack_runtime = None
        self.attack_id = None
        self.ice_spike_spot = None
        self.ice_spike_spawned = False
        self._clear_special_flags()
        if self.anim is not None:
            self.anim.set_clip("idle", reset=True)
