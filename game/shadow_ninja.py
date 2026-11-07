"""Shadow Ninja: normal kunai form plus the phantom second form."""

from __future__ import annotations

from .combat import AttackRuntime, attack_damage
from .config import FIXED_DT
from .fighter import Fighter, FighterState
from .fx import PhantomClawFx, PhantomSharkFx, RingBurstFx


class ShadowNinja(Fighter):
    """Normal form (slash/throw/dash) and phantom form (three one-use skills)."""

    show_health_bar = True
    is_shadow_ninja = True
    _PHANTOM_SKILL_IDS = (
        "shadow_phantom_rend",
        "shadow_phantom_bind",
        "shadow_phantom_flash",
    )
    # P3 phase boundaries, in AttackRuntime seconds.
    _FLASH_APPEAR_T = 0.30
    _FLASH_ATTACK_T = 0.60
    _FLASH_FLIGHT_T = 0.84
    _FLASH_FAR_T = 1.15
    _FLASH_PAUSE_T = 1.45
    _FLASH_EMERGE_T = 1.75
    _FLASH_CHARGE_T = 1.96
    _FLASH_RECOVER_T = 2.272
    _FLASH_END_T = 2.482

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
        phantom = cfg["phantom"]
        self.transform_cd_max = float(cfg["cooldowns"]["phantom_form"])
        self.phantom_damage_threshold = float(phantom["damage_threshold_pct"])
        self.phantom_claw_range = float(phantom["claw_range"])
        self.phantom_bind_range = float(phantom["bind_range"])
        self.phantom_flash_range = float(phantom["flash_range"])
        self.phantom_behind_offset = float(phantom["behind_offset"])
        self.phantom_wall_margin = float(phantom["appear_min_wall_margin"])
        self.phantom_shadow_range = float(phantom["shadow_max_range"])
        self.phantom_shadow_speed = float(phantom["shadow_speed"])
        self.phantom_shark_distance = float(phantom["shark_charge_distance"])
        self.phantom_shark_speed = float(phantom["shark_charge_speed"])
        self.phantom_form = False
        self.phantom_phase = "normal"
        self.phantom_used: dict[str, bool] = {}
        self.phantom_hidden = False
        self.phantom_flash_hit = False
        self.phantom_flash_phase = ""
        self.phantom_flash_stop_x = 0.0
        self.phantom_flash_behind_x = 0.0
        self.transform_cd = 0.0
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
        if self.phantom_form:
            # Backstop for F11/scripted status effects: the phantom form is
            # immune to every negative effect from frame 0 through revert.
            self.statuses.clear()
        self.update_common(dt)
        self.slash_cd = max(0.0, self.slash_cd - dt)
        self.throw_cd = max(0.0, self.throw_cd - dt)
        self.dash_cd = max(0.0, self.dash_cd - dt)
        self.decision_cd = max(0.0, self.decision_cd - dt)
        self.skill_gap = max(0.0, self.skill_gap - dt)
        self.opening_cd = max(0.0, self.opening_cd - dt)
        self.jump_cd = max(0.0, self.jump_cd - dt)
        self.crouch_timer = max(0.0, self.crouch_timer - dt)
        if self.phantom_phase == "normal":
            self.transform_cd = max(0.0, self.transform_cd - dt)

        if self.state == FighterState.TRANSFORM:
            self._update_transform(dt, scene)
            return

        if self.phantom_phase == "phantom":
            self._update_phantom(dt, scene)
            return

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
        if self._should_transform(scene, scene.player):
            if self.start_transform(scene):
                return
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

    # --- phantom form -------------------------------------------------------
    def start_transform(self, scene=None) -> bool:
        if self.phantom_form or self.hp <= 0.0 or self.transform_cd > 0.0:
            return False
        if self.state not in (
            FighterState.IDLE, FighterState.WALK, FighterState.AIR
        ):
            return False
        if self.statuses.control_locked() or self.anim is None:
            return False
        self.state = FighterState.TRANSFORM
        self.phantom_phase = "transform"
        self.phantom_form = True
        self.invincible = True
        self.ignore_terrain = True
        self.ignore_separation = False
        self.vx = 0.0
        self.kb_vx = 0.0
        self.kb_time = 0.0
        self.hitstun = 0.0
        self.flash = 0.0
        self.marks = 0
        self.mark_burst_time = 0.0
        self.mark_burst_damage = 0.0
        self.shadow_marks = 0
        self.shadow_mark_burst_time = 0.0
        self.shadow_mark_burst_damage = 0.0
        self.statuses.clear()
        self.attack_runtime = None
        self.attack_id = None
        self.crouch_timer = 0.0
        self.barrier_hop_x = None
        self.phantom_used = {
            attack_id: False for attack_id in self._PHANTOM_SKILL_IDS
        }
        self.phantom_hidden = False
        self.phantom_flash_hit = False
        self.phantom_flash_phase = ""
        self.anim.set_variant("normal")
        self.anim.set_clip("transform", reset=True)
        if scene is not None:
            scene.hitstop = max(scene.hitstop, 0.10)
            scene.fx_effects.append(
                RingBurstFx(
                    self.x, self.y - 100.0, (175, 100, 255),
                    life=0.30, start_radius=10.0, end_radius=70.0,
                    width=4, sparks=10, spark_color=(240, 220, 255),
                    kind="shadow_phantom_transform",
                )
            )
            scene.particles.emit_burst(
                self.x, self.y - 80.0, (205, 150, 255), 12,
                speed=220.0, life=(0.15, 0.35),
            )
        return True

    def _update_transform(self, dt: float, scene) -> None:
        self.vx = 0.0
        if self.anim is not None:
            self.anim.update(dt)
        self.stage.move_fighter(self, dt)
        if self.anim is None or not self.anim.finished:
            return
        if self.phantom_phase == "transform":
            self.phantom_phase = "phantom"
            self.state = FighterState.IDLE
            self.anim.set_variant("flame")
            self.anim.set_clip("idle", reset=True)
        elif self.phantom_phase == "revert":
            self.phantom_phase = "normal"
            self.phantom_form = False
            self.invincible = False
            self.ignore_terrain = False
            self.transform_cd = self.transform_cd_max
            self.state = FighterState.IDLE
            self.anim.set_variant("normal")
            self.anim.set_clip("idle", reset=True)

    def _start_revert(self) -> None:
        self.phantom_hidden = False
        self.phantom_flash_phase = ""
        self.attack_runtime = None
        self.attack_id = None
        self.ignore_separation = False
        if self.anim is None:
            self.phantom_phase = "normal"
            self.phantom_form = False
            self.invincible = False
            self.ignore_terrain = False
            self.transform_cd = self.transform_cd_max
            self.state = FighterState.IDLE
            return
        self.phantom_phase = "revert"
        self.state = FighterState.TRANSFORM
        self.vx = 0.0
        self.anim.set_variant("flame")
        self.anim.set_clip("revert", reset=True)

    def _update_phantom(self, dt: float, scene) -> None:
        if self.state == FighterState.ATTACK:
            self._update_attack(dt, scene)
            return
        target = scene.player
        if not self.on_ground:
            self.vx = 0.0
            self._set_phantom_anim(False)
            if self.anim is not None:
                self.anim.update(dt)
            self.stage.move_fighter(self, dt)
            if self.on_ground:
                self.state = FighterState.IDLE
            return
        if self.ai_enabled and scene.match_over is None and target.hp > 0.0:
            self._think_phantom(scene, target)
        else:
            self._hold_phantom()
        if self.state == FighterState.ATTACK:
            return
        if self.anim is not None:
            self.anim.update(dt)
        self.stage.move_fighter(self, dt)

    def _set_phantom_anim(self, moving: bool) -> None:
        if self.anim is not None:
            self.anim.set_clip("walk" if moving else "idle")

    def _hold_phantom(self) -> None:
        self.vx = 0.0
        self.state = FighterState.IDLE
        self._set_phantom_anim(False)

    def _walk_phantom(self, distance: float) -> None:
        if distance > self.close_range * 0.9:
            self.state = FighterState.WALK
            self.vx = self.facing * self.walk_speed
            self._set_phantom_anim(True)
        else:
            self._hold_phantom()

    def _prepare_phantom_flash(self, scene, target) -> None:
        low, high = scene.stage.walls
        margin = self.phantom_wall_margin
        behind = target.x - target.facing * self.phantom_behind_offset
        if low + margin <= behind <= high - margin:
            self.phantom_flash_behind_x = behind
        else:
            front = target.x + target.facing * self.phantom_behind_offset
            self.phantom_flash_behind_x = min(
                high - margin, max(low + margin, front)
            )
        self.phantom_flash_phase = "vanish"
        self.phantom_flash_hit = False
        self.phantom_hidden = False
        self.phantom_flash_stop_x = self.phantom_flash_behind_x

    def _compute_flash_stop_x(self, scene) -> None:
        low, high = scene.stage.walls
        direction = self.facing
        spawn_x = self.x + direction * 30.0
        radius = 18.0
        if direction > 0:
            wall_x = high - radius
            travel = min(self.phantom_shadow_range, max(0.0, wall_x - spawn_x))
        else:
            wall_x = low + radius
            travel = min(self.phantom_shadow_range, max(0.0, spawn_x - wall_x))
        self.phantom_flash_stop_x = spawn_x + direction * travel

    def _flash_has_behind_space(self, scene, target) -> bool:
        low, high = scene.stage.walls
        margin = self.phantom_wall_margin
        behind = target.x - target.facing * self.phantom_behind_offset
        return low + margin <= behind <= high - margin

    def _update_phantom_flash(self, dt: float, scene, runtime) -> None:
        runtime.update(dt)
        t = runtime.time
        phase = self.phantom_flash_phase
        target = scene.player
        if phase == "vanish":
            self.vx = 0.0
            if self.anim is not None:
                self.anim.update(dt)
            self.stage.move_fighter(self, dt)
            if t >= self._FLASH_APPEAR_T:
                self.x = self.phantom_flash_behind_x
                if abs(target.x - self.x) > 0.5:
                    self.facing = 1 if target.x > self.x else -1
                self.phantom_flash_phase = "appear"
                if self.anim is not None:
                    self.anim.set_clip("phantom_appear", reset=True)
            return
        if phase == "appear":
            self.vx = 0.0
            if self.anim is not None:
                self.anim.update(dt)
            self.stage.move_fighter(self, dt)
            if t >= self._FLASH_ATTACK_T:
                # Recompute after body separation has settled her position.
                self._compute_flash_stop_x(scene)
                self.phantom_flash_phase = "attack"
                if self.anim is not None:
                    self.anim.set_clip("phantom_flash_attack", reset=True)
            return
        if phase == "attack":
            self.vx = 0.0
            if self.anim is not None:
                self.anim.update(dt)
            self.stage.move_fighter(self, dt)
            if t >= self._FLASH_FLIGHT_T:
                self.phantom_flash_phase = "flight"
                if self.anim is not None:
                    self.anim.set_clip("phantom_vanish", reset=True)
            return
        if phase == "flight":
            self.vx = 0.0
            if self.anim is not None and not self.phantom_hidden:
                self.anim.update(dt)
                if self.anim.finished:
                    self.phantom_hidden = True
            if t >= self._FLASH_FAR_T:
                self.x = self.phantom_flash_stop_x
                if abs(target.x - self.x) > 0.5:
                    self.facing = 1 if target.x > self.x else -1
                self.phantom_hidden = False
                self.phantom_flash_phase = "appear_far"
                if self.anim is not None:
                    self.anim.set_clip("phantom_appear", reset=True)
            return
        if phase == "appear_far":
            self.vx = 0.0
            if self.anim is not None:
                self.anim.update(dt)
            if t >= self._FLASH_PAUSE_T:
                self.phantom_flash_phase = "pause"
                if self.anim is not None:
                    self.anim.set_clip("phantom_pause", reset=True)
            return
        if phase == "pause":
            self.vx = 0.0
            if self.anim is not None:
                self.anim.update(dt)
            if t >= self._FLASH_EMERGE_T:
                self.phantom_flash_phase = "emerge"
                if self.anim is not None:
                    self.anim.set_clip("phantom_shark_emerge", reset=True)
            return
        if phase == "emerge":
            self.vx = 0.0
            if self.anim is not None:
                self.anim.update(dt)
            if t >= self._FLASH_CHARGE_T:
                self.phantom_flash_phase = "charge"
                self.ignore_separation = True
                if self.anim is not None:
                    self.anim.set_clip("phantom_shark_charge", reset=True)
                scene.fx_effects.append(PhantomSharkFx(self, life=0.40))
            return
        if phase == "charge":
            if self.anim is not None:
                self.anim.update(dt)
            if t >= self._FLASH_RECOVER_T:
                self.ignore_separation = False
                self.phantom_flash_phase = "recover"
                if self.anim is not None:
                    self.anim.set_clip("phantom_shark_recover", reset=True)
            return
        if phase == "recover":
            self.vx = 0.0
            if self.anim is not None:
                self.anim.update(dt)
            if t >= self._FLASH_END_T:
                self._finish_attack()

    # --- AI -----------------------------------------------------------------
    def _should_transform(self, scene, target) -> bool:
        if self.phantom_form or self.transform_cd > 0.0:
            return False
        if self.hp <= 0.0 or target is None or target.hp <= 0.0:
            return False
        if scene.match_over is not None:
            return False
        if self.state not in (
            FighterState.IDLE, FighterState.WALK, FighterState.AIR
        ):
            return False
        if self.statuses.control_locked():
            return False
        if self.hp <= self.max_hp * self.low_hp_pct:
            return True
        return (
            self._incoming_damage(scene)
            >= self.max_hp * self.phantom_damage_threshold
        )

    def _incoming_damage(self, scene) -> float:
        """Largest single hit the player is about to land on this fighter.

        Mirrors the geometry scan in ``_incoming_threat`` but returns damage
        instead of a high/low dodge hint.
        """
        player = scene.player
        best = 0.0
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
                best = max(best, attack_damage(player, runtime.data, event))
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
            best = max(best, float(getattr(projectile, "damage", 0.0)))
        return best

    def _think_phantom(self, scene, target) -> None:
        if self.decision_cd > 0.0:
            return
        self.decision_cd = self.decision_interval
        dx = target.x - self.x
        if abs(dx) > 8.0:
            self.facing = 1 if dx > 0.0 else -1
        distance = abs(dx)
        if self.skill_gap > 0.0:
            self._walk_phantom(distance)
            return
        used = self.phantom_used
        p1, p2, p3 = self._PHANTOM_SKILL_IDS
        if distance <= self.close_range:
            if not used.get(p2):
                self.start_attack(p2, scene, target)
                return
            if not used.get(p1):
                self.start_attack(p1, scene, target)
                return
            if not used.get(p3):
                self.start_attack(p3, scene, target)
                return
            self._walk_phantom(distance)
            return
        if not used.get(p2) and distance <= self.phantom_bind_range:
            self.start_attack(p2, scene, target)
            return
        if (
            not used.get(p3)
            and distance <= self.phantom_flash_range
            and self._flash_has_behind_space(scene, target)
        ):
            self.start_attack(p3, scene, target)
            return
        if not used.get(p1) and distance <= self.phantom_claw_range:
            self.start_attack(p1, scene, target)
            return
        if (
            not used.get(p3)
            and used.get(p1)
            and used.get(p2)
            and distance <= self.phantom_flash_range
        ):
            # Only 影闪 remains: use it even when the player is against a
            # wall; start_attack will place her in front instead.
            self.start_attack(p3, scene, target)
            return
        self._walk_phantom(distance)

    def _think(self, scene, target) -> None:
        if self._should_transform(scene, target):
            if self.start_transform(scene):
                return
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
        is_phantom = attack_id in self._PHANTOM_SKILL_IDS
        if self.phantom_phase == "phantom":
            if not is_phantom or self.phantom_used.get(attack_id, False):
                return
            self.phantom_used[attack_id] = True
        elif is_phantom:
            return
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
        if attack_id == "shadow_phantom_flash":
            self._prepare_phantom_flash(scene, target)
            if self.anim is not None:
                self.anim.set_clip("phantom_vanish", reset=True)
        elif self.anim is not None:
            self.anim.set_clip(attack_id, reset=True)
        if attack_id == "shadow_phantom_rend" and scene is not None:
            scene.fx_effects.append(PhantomClawFx(self, life=0.36, delay=0.18))
        data = self.store.attacks[attack_id]
        self.attack_runtime = AttackRuntime(self, attack_id, data, target, scene)
        if self.phantom_phase == "phantom":
            return
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
        if self.attack_id == "shadow_phantom_flash":
            self._update_phantom_flash(dt, scene, runtime)
            return
        if self.attack_id == "shadow_dash":
            self.ignore_separation = 0.06 <= runtime.time < 0.45
        if self.anim is not None:
            self.anim.update(dt)
        runtime.update(dt)
        if runtime.finished:
            self._finish_attack()

    def _finish_attack(self) -> None:
        was_phantom = self.phantom_phase == "phantom"
        self._reset_attack_state()
        self.phantom_hidden = False
        self.phantom_flash_phase = ""
        self.skill_gap = self.skill_gap_max
        self.state = FighterState.IDLE
        self.vx = 0.0
        self.vy = 0.0
        if was_phantom:
            if all(
                self.phantom_used.get(attack_id, False)
                for attack_id in self._PHANTOM_SKILL_IDS
            ):
                self._start_revert()
                return
            if self.anim is not None:
                self.anim.set_clip("idle", reset=True)
        elif self.anim is not None:
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
        if attack_id == "shadow_phantom_form":
            return self.start_transform(scene)
        if self.phantom_phase == "phantom":
            # V/C/X keep their normal slot ids; map them onto the three
            # one-use phantom skills while the form is active.
            attack_id = {
                "shadow_kunai_slash": "shadow_phantom_rend",
                "shadow_kunai_throw": "shadow_phantom_bind",
                "shadow_dash": "shadow_phantom_flash",
            }.get(attack_id, attack_id)
            if (
                attack_id not in self._PHANTOM_SKILL_IDS
                or self.phantom_used.get(attack_id, False)
            ):
                return False
            self.start_attack(attack_id, scene, target)
            return True
        is_phantom = attack_id in self._PHANTOM_SKILL_IDS
        if is_phantom:
            return False
        self.slash_cd = 0.0
        self.throw_cd = 0.0
        self.dash_cd = 0.0
        if self.state == FighterState.CROUCH:
            self.state = FighterState.IDLE
        self.start_attack(attack_id, scene, target)
        return True

    def skill_remaining(self, attack_id: str) -> float:
        if attack_id == "shadow_phantom_form":
            return 0.0 if self.phantom_form else self.transform_cd
        if attack_id in self._PHANTOM_SKILL_IDS:
            return 0.0
        return {
            "shadow_kunai_slash": self.slash_cd,
            "shadow_kunai_throw": self.throw_cd,
            "shadow_dash": self.dash_cd,
        }.get(attack_id, 0.0)

    def skill_used(self, attack_id: str) -> bool:
        """Debug-panel helper for the one-use phantom skills."""
        return bool(self.phantom_used.get(attack_id, False))

    # --- marks --------------------------------------------------------------
    def on_hit_success(self, attack: dict, target, bonus: float) -> None:
        if target is None or target.hp <= 0.0:
            return
        if (
            self.attack_id == "shadow_phantom_flash"
            and self.phantom_flash_phase == "attack"
        ):
            self.phantom_flash_hit = True
            return
        if self.phantom_phase == "phantom":
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
        kind = getattr(projectile, "kind", "")
        if kind == "shadow_phantom_bind":
            if getattr(projectile, "status", None) == "stun":
                target.statuses.add(
                    "stun",
                    float(projectile.status_duration),
                    source="shadow_phantom_bind",
                )
            return
        if kind == "shadow_phantom_flash":
            self.phantom_flash_hit = True
            return
        if kind != "shadow_kunai":
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
        self.transform_cd = 0.0
        self.phantom_form = False
        self.phantom_phase = "normal"
        self.phantom_used = {
            attack_id: False for attack_id in self._PHANTOM_SKILL_IDS
        }
        self.phantom_hidden = False
        self.phantom_flash_hit = False
        self.phantom_flash_phase = ""
        self.phantom_flash_stop_x = 0.0
        self.phantom_flash_behind_x = 0.0
        self.invincible = False
        self.ignore_separation = False
        self.ignore_terrain = False
        self._reset_attack_state()
        if self.anim is not None:
            self.anim.set_variant("normal")
            self.anim.set_clip("idle", reset=True)
