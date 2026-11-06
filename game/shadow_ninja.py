"""Shadow Ninja (normal form): kunai slash, low shadow kunai, dash and marks."""

from __future__ import annotations

from .combat import AttackRuntime
from .config import FIXED_DT
from .fighter import Fighter, FighterState
from .fx import RingBurstFx


class ShadowNinja(Fighter):
    """The normal form only. Skill slot 4 stays empty for the phantom form."""

    show_health_bar = True
    is_shadow_ninja = True

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
        self.slash_cd_max = float(cfg["cooldowns"]["slash"])
        self.throw_cd_max = float(cfg["cooldowns"]["throw"])
        self.dash_cd_max = float(cfg["cooldowns"]["dash"])
        ai = cfg["ai"]
        self.close_range = float(ai["close_range"])
        self.far_range = float(ai["far_range"])
        self.level_tolerance = float(ai["level_tolerance"])
        self.decision_interval = float(ai["decision_interval"])
        self.low_hp_pct = float(ai["low_hp_pct"])
        self.kunai_close_distance = float(ai["kunai_close_distance"])
        self.skill_gap_max = float(ai["skill_gap"])
        self.opening_delay = float(ai["opening_delay"])
        self.jump_cooldown_max = float(ai["jump_cooldown"])
        self.crouch_hold = float(ai["crouch_hold"])
        self.barrier_hop_range = float(ai["barrier_hop_range"])
        self.threat_range = float(ai["threat_range"])
        self.ai_enabled = True
        # Duck-typed by scene._separate_fighters and Stage.move_x.
        self.ignore_separation = False
        self.ignore_terrain = False
        self.slash_cd = 0.0
        self.throw_cd = 0.0
        self.dash_cd = 0.0
        self.decision_cd = 0.0
        self.skill_gap = 0.0
        self.opening_cd = 0.0
        self.jump_cd = 0.0
        self.crouch_timer = 0.0
        self.barrier_hop_x: float | None = None
        self.reset()

    # --- battle-start stat copy --------------------------------------------
    def sync_from_player(self, player, full_heal: bool = True) -> None:
        """Copy the opposing character's HP/ATK and 1.5x move speed.

        Called once after the scene rebuilds or resets; never per tick, so
        temporary in-fight changes are not copied back.
        """
        self.max_hp = float(player.max_hp)
        self.basic_atk = float(player.basic_atk)
        self.extra_atk = float(player.extra_atk)
        self.atk = float(player.atk)
        self.walk_speed = float(getattr(player, "walk_speed", self.walk_speed)) * 1.5
        if full_heal:
            self.hp = self.max_hp

    # --- update -------------------------------------------------------------
    def update(self, dt: float, scene) -> None:
        self.update_common(dt)
        self.slash_cd = max(0.0, self.slash_cd - dt)
        self.throw_cd = max(0.0, self.throw_cd - dt)
        self.dash_cd = max(0.0, self.dash_cd - dt)
        self.decision_cd = max(0.0, self.decision_cd - dt)
        self.skill_gap = max(0.0, self.skill_gap - dt)
        self.opening_cd = max(0.0, self.opening_cd - dt)
        self.jump_cd = max(0.0, self.jump_cd - dt)
        self.crouch_timer = max(0.0, self.crouch_timer - dt)

        if self.state == FighterState.KO:
            self.ignore_separation = False
            self.barrier_hop_x = None
            self.vx = 0.0
            if self.anim is not None:
                self.anim.update(dt)
            self.stage.move_fighter(self, dt)
            return

        if self.state == FighterState.HURT:
            self.ignore_separation = False
            self.crouch_timer = 0.0
            self.barrier_hop_x = None
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

        if self.state == FighterState.CROUCH:
            self.vx = 0.0
            if self.crouch_timer <= 0.0:
                self.state = FighterState.IDLE
                if self.anim is not None:
                    self.anim.set_clip("idle")
            elif self.anim is not None:
                self.anim.set_clip("crouch")
            if self.anim is not None:
                self.anim.update(dt)
            self.stage.move_fighter(self, dt)
            return

        if self.statuses.control_locked():
            self.ignore_separation = False
            self.vx = 0.0
            if self.statuses.has("stun") and self.on_ground:
                self.state = FighterState.IDLE
                if self.anim is not None:
                    self.anim.set_clip("stun")
                    self.anim.set_frame(0)
            else:
                self.set_air_or_idle_anim()
            if self.anim is not None:
                self.anim.update(dt)
            if self.statuses.has("stun") and self.anim is not None:
                self.anim.set_frame(0)
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
        if self.anim is not None:
            self.anim.update(dt)
        self.stage.move_fighter(self, dt)

    def _airborne_step(self, dt: float, scene) -> None:
        if self.barrier_hop_x is not None:
            dx = self.barrier_hop_x - self.x
            if abs(dx) <= 8.0:
                self.vx = 0.0
            else:
                self.vx = (1 if dx > 0.0 else -1) * self.walk_speed * 0.7
        self.set_air_or_idle_anim()
        if self.anim is not None:
            self.anim.update(dt)
        self.stage.move_fighter(self, dt)
        if self.on_ground:
            self.barrier_hop_x = None
            self.vx = 0.0
            self.state = FighterState.IDLE
            if self.anim is not None:
                self.anim.set_clip("idle")

    def _hold(self) -> None:
        self.vx = 0.0
        if self.on_ground:
            self.state = FighterState.IDLE
            if self.anim is not None:
                self.anim.set_clip("idle")

    def _walk_or_hold(self, distance: float) -> None:
        if distance > self.close_range * 0.9:
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

        if self.opening_cd > 0.0:
            self._walk_or_hold(distance)
            return

        if self._try_defense(scene, target):
            return

        if self.skill_gap > 0.0:
            self._walk_or_hold(distance)
            return

        low_hp = self.hp <= self.max_hp * self.low_hp_pct
        if distance <= self.close_range:
            if self.throw_cd <= 0.0:
                self.start_attack("shadow_kunai_throw", scene, target)
                return
            if low_hp and self.dash_cd <= 0.0:
                # Disengage: keep the facing away from the target so the
                # dash's own movement carries the ninja out of range.
                self.facing = -1 if target.x > self.x else 1
                self.start_attack(
                    "shadow_dash", scene, target, face_target=False
                )
                return
            if self.slash_cd <= 0.0:
                self.start_attack("shadow_kunai_slash", scene, target)
                return
            self._walk_or_hold(distance)
            return

        if distance <= self.far_range:
            if self.throw_cd <= 0.0:
                self.start_attack("shadow_kunai_throw", scene, target)
                return
            if self.dash_cd <= 0.0:
                kunai = self._nearest_own_kunai(scene)
                if kunai is None or abs(target.x - kunai.x) <= self.kunai_close_distance:
                    self.start_attack("shadow_dash", scene, target)
                    return
            self._walk_or_hold(distance)
            return

        self._walk_or_hold(distance)

    def _try_defense(self, scene, target) -> bool:
        if self._try_barrier_hop(scene, target):
            return True
        threat = self._incoming_threat(scene)
        if threat == "high" and self.on_ground:
            self.state = FighterState.CROUCH
            self.vx = 0.0
            self.crouch_timer = self.crouch_hold
            if self.anim is not None:
                self.anim.set_clip("crouch", reset=True)
            return True
        if threat == "low" and self.on_ground and self.jump_cd <= 0.0:
            self._jump()
            return True
        return False

    def _try_barrier_hop(self, scene, target) -> bool:
        if not scene.stage.blocks_enabled or not self.on_ground:
            return False
        if self.jump_cd > 0.0:
            return False
        facing = 1 if target.x > self.x else -1
        probe_x = self.x + facing * self.barrier_hop_range
        low_x, high_x = sorted((self.x, probe_x))
        peak = (self.jump_v * self.jump_v) / (2.0 * self.gravity)
        for block in scene.stage.barriers:
            if self.y <= block.top + 1.0:
                continue
            if block.right < low_x or block.left > high_x:
                continue
            if self.y - block.top > peak - 10.0:
                continue
            self.barrier_hop_x = float(block.centerx)
            self.vy = -self.jump_v
            self.on_ground = False
            self.vx = facing * self.walk_speed * 0.7
            self.state = FighterState.AIR
            self.jump_cd = self.jump_cooldown_max
            if self.anim is not None:
                self.anim.set_clip("jump", reset=True)
                self.anim.set_frame(0)
            return True
        return False

    def _jump(self) -> None:
        if not self.on_ground or self.jump_cd > 0.0:
            return
        self.vy = -self.jump_v
        self.on_ground = False
        self.vx = 0.0
        self.state = FighterState.AIR
        self.jump_cd = self.jump_cooldown_max
        if self.anim is not None:
            self.anim.set_clip("jump", reset=True)
            self.anim.set_frame(0)

    def _nearest_own_kunai(self, scene):
        for projectile in scene.projectiles:
            if (
                getattr(projectile, "owner", None) is self
                and getattr(projectile, "kind", "") == "shadow_kunai"
                and getattr(projectile, "alive", False)
            ):
                return projectile
        return None

    def _incoming_threat(self, scene) -> str | None:
        """Return ``"high"`` (crouch), ``"low"`` (jump) or ``None``.

        The decision is based on actual hitbox geometry and projectile lane
        height, so it works for every playable character without hard-coding
        attack ids.
        """
        player = scene.player
        runtime = getattr(player, "attack_runtime", None)
        if runtime is not None:
            dx = self.x - player.x
            cast_facing = int(getattr(runtime, "cast_facing", player.facing))
            for event in runtime.data.get("events", []):
                if event.get("type") != "hitbox":
                    continue
                start = float(event.get("t", 0.0))
                until = float(event.get("until", start + FIXED_DT))
                if not (start <= runtime.time < until):
                    continue
                if dx * cast_facing < 0.0:
                    continue
                box = event.get("box", [0.0, 0.0, 0.0, 0.0])
                if abs(dx) > self.threat_range + abs(float(box[0])) + float(box[2]):
                    continue
                top = (self.y - player.y) - float(box[1])
                bottom = top - float(box[3])
                if bottom > 210.0 or top < 0.0:
                    continue
                if top <= 125.0:
                    return "low"
                if bottom >= 140.0:
                    return "high"

        for projectile in scene.projectiles:
            if getattr(projectile, "owner", None) is not player:
                continue
            dx = self.x - projectile.x
            direction = getattr(projectile, "direction", None)
            if direction is None:
                direction = getattr(projectile, "ux", None)
            if direction is None:
                vx = float(getattr(projectile, "vx", 0.0))
                direction = 1.0 if vx > 0.0 else (-1.0 if vx < 0.0 else 0.0)
            direction = float(direction)
            if direction == 0.0 or direction * dx < 0.0:
                continue
            if abs(dx) > self.threat_range:
                continue
            height = self.y - float(projectile.y)
            if height > 210.0:
                continue
            if height <= 125.0:
                return "low"
            if height >= 140.0:
                return "high"
        return None

    # --- actions ------------------------------------------------------------
    def start_attack(
        self,
        attack_id: str,
        scene,
        target,
        face_target: bool = True,
    ) -> None:
        if (
            face_target
            and target is not None
            and abs(target.x - self.x) > 8.0
        ):
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
        if attack_id == "shadow_kunai_slash":
            self.slash_cd = self.slash_cd_max
        elif attack_id == "shadow_kunai_throw":
            self.throw_cd = self.throw_cd_max
        elif attack_id == "shadow_dash":
            self.dash_cd = self.dash_cd_max

    def _update_attack(self, dt: float, scene) -> None:
        runtime = self.attack_runtime
        if runtime is None:
            self._finish_attack()
            return
        if self.attack_id == "shadow_dash":
            self.ignore_separation = 0.06 <= runtime.time < 0.45
        if self.anim is not None:
            self.anim.update(dt)
        runtime.update(dt)
        if runtime.finished:
            self._finish_attack()

    def _finish_attack(self) -> None:
        self._reset_attack_state()
        self.skill_gap = self.skill_gap_max
        self.state = FighterState.IDLE
        self.vx = 0.0
        self.vy = 0.0
        if self.anim is not None:
            self.anim.set_clip("idle")

    def _reset_attack_state(self) -> None:
        self.attack_runtime = None
        self.attack_id = None
        self.ignore_separation = False

    def cancel_attack(self) -> None:
        self._reset_attack_state()
        super().cancel_attack()

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
            self.ignore_separation = False
            self.crouch_timer = 0.0
            self.barrier_hop_x = None
        return result

    def force_attack(self, scene, target, attack_id: str = "shadow_kunai_slash") -> bool:
        if self.hp <= 0.0 or self.state in (FighterState.KO, FighterState.HURT):
            return False
        if attack_id not in self.store.attacks:
            return False
        self.slash_cd = 0.0
        self.throw_cd = 0.0
        self.dash_cd = 0.0
        if self.state == FighterState.CROUCH:
            self.state = FighterState.IDLE
        self.start_attack(attack_id, scene, target)
        return True

    def skill_remaining(self, attack_id: str) -> float:
        return {
            "shadow_kunai_slash": self.slash_cd,
            "shadow_kunai_throw": self.throw_cd,
            "shadow_dash": self.dash_cd,
        }.get(attack_id, 0.0)

    # --- marks --------------------------------------------------------------
    def on_hit_success(self, attack: dict, target, bonus: float) -> None:
        if target is None or target.hp <= 0.0:
            return
        if self.attack_id not in ("shadow_kunai_slash", "shadow_dash"):
            return
        runtime = self.attack_runtime
        scene = runtime.scene if runtime is not None else None
        if scene is not None:
            self._add_shadow_mark(scene, target)

    def on_projectile_hit(self, projectile) -> None:
        target = projectile.target
        if target is None or target.hp <= 0.0:
            return
        if getattr(projectile, "kind", "") != "shadow_kunai":
            return
        if getattr(projectile, "status", None) == "stun":
            target.statuses.add(
                "stun",
                float(projectile.status_duration),
                source="shadow_kunai_throw",
            )
        scene = getattr(projectile, "scene", None)
        if scene is not None:
            self._add_shadow_mark(scene, target)

    def _add_shadow_mark(self, scene, target) -> None:
        if target is None or target.hp <= 0.0 or target.invincible:
            return
        target.shadow_marks += 1
        if target.shadow_marks < 4:
            return
        amount = self.atk * (1.0 - target.statuses.damage_reduction())
        target.take_hit(amount, 0.0, 0.0, self.facing)
        if target.hp > 0.0:
            target.statuses.add("stun", 1.0, source="shadow_ninja_mark")
        target.shadow_mark_burst_time = 0.4
        target.shadow_mark_burst_damage = amount
        target.shadow_marks = 1 if target.hp > 0.0 else 0
        burst_y = target.y - target.hurtbox_dims[1] * 0.5
        scene.hitstop = max(scene.hitstop, 0.08)
        scene.particles.emit_hit(target.x, burst_y, (205, 150, 255))
        scene.fx_effects.append(
            RingBurstFx(
                target.x,
                burst_y,
                (185, 110, 255),
                life=0.28,
                start_radius=8.0,
                end_radius=46.0,
                width=3,
                sparks=8,
                spark_color=(240, 220, 255),
                kind="shadow_mark_burst",
            )
        )

    # --- reset --------------------------------------------------------------
    def reset(self) -> None:
        self.reset_common(self.spawn[0], self.spawn[1], -1)
        self.slash_cd = 0.0
        self.throw_cd = 0.0
        self.dash_cd = 0.0
        self.decision_cd = 0.0
        self.skill_gap = 0.0
        self.opening_cd = self.opening_delay
        self.jump_cd = 0.0
        self.crouch_timer = 0.0
        self.barrier_hop_x = None
        self.ignore_separation = False
        self.ignore_terrain = False
        self._reset_attack_state()
        if self.anim is not None:
            self.anim.set_clip("idle")
