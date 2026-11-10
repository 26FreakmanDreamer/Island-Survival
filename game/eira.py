"""Eira Frostveil: snowball, staff strike, piercing ice shard and ice ball."""

from __future__ import annotations

from .combat import AttackRuntime
from .config import ASSETS_DIR
from .fighter import Fighter, FighterState
from .fx import SpriteStripFx
from .hazards import IceBallHazard

EIRA_CLIMB_DRAW_SCALE = 1.15

ATTACK_CLIPS = {
    "eira_snowball": "snowball",
    "eira_staff_strike": "staff_strike",
    "eira_ice_shard": "ice_shard",
}


class Eira(Fighter):
    def __init__(self, store, stage, entry: dict, anim) -> None:
        cfg = store.stats[entry["stats"]]
        combat_cfg = store.stats["combat"]
        x, y = stage.spawn(entry["spawn"])
        super().__init__(
            x=x,
            y=y,
            facing=1,
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
        self.combat_cfg = combat_cfg
        self.spawn = (float(x), float(y))
        self.climb_draw_scale = EIRA_CLIMB_DRAW_SCALE
        self.set_attack_stats(cfg)
        self.knock_up_gravity = float(
            combat_cfg.get("knock_up_gravity", self.gravity)
        )
        self.q_cd_max = float(cfg["cooldowns"]["q"])
        self.e_cd_max = float(cfg["cooldowns"]["e"])
        self.walk_speed = float(cfg["move"]["walk"])
        self.jump_v = float(cfg["move"]["jump_v"])
        self.freeze_cfg = dict(cfg.get("freeze", {}))
        self.ice_ball_cfg = dict(cfg.get("ice_ball", {}))
        self.e_cast_cfg = dict(cfg.get("e_cast", {}))

        self.q_cd = 0.0
        self.e_cd = 0.0
        self.attack_runtime: AttackRuntime | None = None
        self.attack_id: str | None = None
        self.staff_fx_02_spawned = False
        self.staff_fx_03_spawned = False
        self.shard_charge_spawned = False
        self.staff_fx_02: SpriteStripFx | None = None
        self.staff_fx_03: SpriteStripFx | None = None
        self.queued_action: str | None = None

        self.e_phase: str | None = None
        self.e_phase_time = 0.0
        self.e_hold_time = 0.0
        self.e_targeting = False
        self.e_selected_x = 0.0
        self.e_spawn_pending = 0.0
        self.e_ball_spawned = False
        self.reset()

    # --- passive ------------------------------------------------------------
    def apply_freeze(self, target, amount: float, was_frozen=None) -> None:
        """Add freeze value, equal-percent slow, and freeze at 100."""
        if target is None or target.hp <= 0.0:
            return
        if was_frozen is None:
            was_frozen = target.statuses.has("freeze")
        if was_frozen:
            return
        amount = float(amount)
        if amount <= 0.0:
            return
        target.eira_freeze = float(getattr(target, "eira_freeze", 0.0)) + amount
        slow_duration = float(self.freeze_cfg.get("slow_duration", 2.0))
        target.statuses.add_slow(
            max(0.0, 1.0 - amount / 100.0),
            slow_duration,
            source="eira_freeze",
        )
        threshold = float(self.freeze_cfg.get("threshold", 100.0))
        if target.eira_freeze >= threshold:
            target.eira_freeze = 0.0
            target.statuses.add(
                "freeze",
                float(self.freeze_cfg.get("duration", 2.0)),
                source="eira_freeze",
            )

    def on_hit_success(self, attack: dict, target, bonus: float) -> None:
        gain = float(attack.get("freeze_gain", 0.0))
        if gain > 0.0:
            self.apply_freeze(target, gain)

    def on_projectile_hit(self, projectile) -> None:
        gain = float(getattr(projectile, "freeze_gain", 0.0))
        if gain <= 0.0:
            return
        was_frozen = getattr(projectile, "hit_target_was_frozen", None)
        self.apply_freeze(projectile.target, gain, was_frozen)

    def _spawn_eira_fx(
        self,
        scene,
        prefix: str,
        count: int,
        durations: list[float],
        x: float,
        y: float,
        *,
        scale: float = 0.5,
        start: int = 0,
        kind: str = "eira_fx",
        pivot: tuple[float, float] | None = None,
    ) -> SpriteStripFx:
        frames = [
            ASSETS_DIR / "frames" / "eira" / "fx"
            / f"{prefix}_{index:02d}.png"
            for index in range(start, start + count)
        ]
        effect = SpriteStripFx(
            frames, durations, x, y, scale=scale, pivot=pivot, kind=kind,
        )
        scene.fx_effects.append(effect)
        return effect

    def _spawn_staff_fx(self, scene, frame: int) -> SpriteStripFx:
        """Overlay the small frame-02/03 staff trail on the same canvas.

        The approved FX were authored on the same 1408 canvas as the
        character frames and normalized to 384x384 with pivot (192,372),
        so they must use the fighter's feet pivot with no extra offset.
        """
        frames = [
            ASSETS_DIR / "frames" / "eira" / "fx"
            / f"eira_staff_strike_v2_fx_{frame:02d}.png"
        ]
        effect = SpriteStripFx(
            frames,
            [0.08 if frame == 2 else 0.14],
            self.x,
            self.y,
            pivot=(192.0, 372.0),
            scale=1.0,
            flip=self.facing < 0,
            kind=f"eira_staff_arc_{frame:02d}",
        )
        scene.fx_effects.append(effect)
        return effect

    def _update_attack_fx(self, scene) -> None:
        """Spawn and retire attack FX on the exact pose frames they belong to.

        Staff trails are tied to frames 2/3 instead of a wall-clock lifetime:
        fx_02 must be gone on the first tick of frame 3, and fx_03 on frame 4.
        The Q charge sparkle sits on the blue staff crystal of frame 1
        (measured offset 59.5, -223.4 from the feet pivot).
        """
        if self.anim is None:
            return
        frame = self.anim.frame_index
        if self.attack_id == "eira_staff_strike":
            if frame == 2 and not self.staff_fx_02_spawned:
                self.staff_fx_02 = self._spawn_staff_fx(scene, 2)
                self.staff_fx_02_spawned = True
            elif frame > 2:
                self._retire_staff_fx("staff_fx_02")
            if frame == 3 and not self.staff_fx_03_spawned:
                self.staff_fx_03 = self._spawn_staff_fx(scene, 3)
                self.staff_fx_03_spawned = True
            elif frame > 3:
                self._retire_staff_fx("staff_fx_03")
        elif (
            self.attack_id == "eira_ice_shard"
            and not self.shard_charge_spawned
            and frame == 1
        ):
            self._spawn_eira_fx(
                scene,
                "eira_ice_shard_v1_fx_charge",
                3,
                [0.03, 0.03, 0.04],
                self.x + self.facing * 59.5,
                self.y - 223.4,
                scale=0.4,
                kind="eira_ice_shard_charge",
                pivot=(84.0, 103.0),
            )
            self.shard_charge_spawned = True

    def _retire_staff_fx(self, attr: str) -> None:
        effect = getattr(self, attr)
        if effect is not None:
            effect.alive = False
            setattr(self, attr, None)

    # --- E cast -------------------------------------------------------------
    def _set_e_armor(self) -> None:
        self.statuses.add("super_armor", 99.0, source="eira_e")

    def _clear_e_armor(self) -> None:
        effect = self.statuses.effects.get("super_armor")
        if effect is not None and effect.source == "eira_e":
            self.statuses.effects.pop("super_armor", None)

    def _clear_e_state(self) -> None:
        self.e_phase = None
        self.e_phase_time = 0.0
        self.e_hold_time = 0.0
        self.e_targeting = False
        self.e_spawn_pending = 0.0
        self._clear_e_armor()

    def _end_e(self) -> None:
        self._clear_e_state()
        self.state = FighterState.IDLE
        if self.anim is not None:
            self.anim.set_clip("idle", reset=True)

    def _cancel_e(self) -> None:
        self.e_phase = "recover"
        self.e_phase_time = 0.0
        self.e_targeting = False
        self.e_spawn_pending = 0.0
        self.e_cd = float(self.e_cast_cfg.get("cancel_cooldown", 6.0))
        if self.anim is not None:
            self.anim.set_clip("e_recover", reset=True)

    def _force_end_e(self) -> None:
        self._clear_e_state()
        self.attack_runtime = None
        self.attack_id = None

    def _start_e(self, scene) -> bool:
        if (
            self.e_phase is not None
            or not self.on_ground
            or self.e_cd > 0.0
            or self.state in (FighterState.HURT, FighterState.KO)
            or self.statuses.control_locked()
        ):
            return False
        self.e_phase = "raise"
        self.e_phase_time = 0.0
        self.e_hold_time = 0.0
        self.e_targeting = False
        self.e_selected_x = 0.0
        self.e_spawn_pending = 0.0
        self.e_ball_spawned = False
        self.e_cd = self.e_cd_max
        self.state = FighterState.ATTACK
        self.vx = 0.0
        self._set_e_armor()
        if self.anim is not None:
            self.anim.set_clip("e_raise", reset=True)
        self._spawn_eira_fx(
            scene,
            "eira_e_release_v1_fx_charge",
            3,
            [0.09, 0.09, 0.10],
            self.x + self.facing * 45.0,
            self.y - 200.0,
            scale=0.5,
            kind="eira_e_charge",
        )
        return True

    def _update_e(self, dt: float, input_state, target, scene) -> None:
        self.vx = 0.0
        self.e_phase_time += dt
        if self.e_phase == "raise":
            if self.anim is not None:
                self.anim.update(dt)
            if self.e_phase_time >= 0.40:
                self.e_phase = "hold"
                self.e_phase_time = 0.0
                self.e_hold_time = 0.0
                self.e_targeting = True
                # A click made during the raise must not select immediately.
                input_state.buffer.consume("punch")
                if self.anim is not None:
                    self.anim.set_clip("e_hold", reset=True)
            return

        if self.e_phase == "hold":
            self.e_hold_time += dt
            if self.anim is not None:
                self.anim.update(dt)
            if input_state.buffer.has("kick"):
                input_state.buffer.consume("kick")
                self._cancel_e()
                return
            timeout = float(self.e_cast_cfg.get("select_timeout", 8.0))
            if self.e_hold_time >= timeout:
                self._cancel_e()
                return
            if input_state.buffer.has("punch"):
                input_state.buffer.consume("punch")
                low, high = scene.stage.walls
                self.e_selected_x = max(low, min(high, float(scene.mouse_x)))
                self.e_targeting = False
                self.e_phase = "release"
                self.e_phase_time = 0.0
                self.e_spawn_pending = float(
                    self.e_cast_cfg.get("release_spawn_delay", 0.08)
                )
                if self.anim is not None:
                    self.anim.set_clip("e_release", reset=True)
            return

        if self.e_phase == "release":
            if self.anim is not None:
                self.anim.update(dt)
            if not self.e_ball_spawned and self.e_phase_time >= self.e_spawn_pending:
                self._spawn_ice_ball(scene)
                self.e_ball_spawned = True
            if self.e_phase_time >= 0.30:
                self.e_phase = "recover"
                self.e_phase_time = 0.0
                if self.anim is not None:
                    self.anim.set_clip("e_recover", reset=True)
            return

        if self.e_phase == "recover":
            if self.anim is not None:
                self.anim.update(dt)
            if self.e_phase_time >= 0.30:
                self._end_e()

    def _spawn_ice_ball(self, scene) -> None:
        attack = self.store.attacks["eira_ice_ball"]
        scene.hazards.append(
            IceBallHazard(
                owner=self,
                x=self.e_selected_x,
                ground_y=scene.stage.ground_y,
                radius=float(self.ice_ball_cfg.get("radius", 80.0)),
                fall_speed=float(self.ice_ball_cfg.get("fall_speed", 740.0)),
                attack_data=attack,
                freeze_gain=float(self.freeze_cfg.get("gain", {}).get("e", 50.0)),
            )
        )

    # --- hit reaction -------------------------------------------------------
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
        shielded = self.statuses.has("sacred_shield")
        if shielded:
            damage = 0.0
        if self.e_phase is not None:
            # Super armor: damage lands, but the cast is not interrupted.
            if shielded:
                self.blocked_hits += 1
            self.hp = max(0.0, self.hp - damage)
            self.flash = 0.0 if shielded else 0.12
            if self.hp <= 0.0:
                self._force_end_e()
                self.state = FighterState.KO
                self.hitstun = 0.0
                self.kb_vx = 0.0
                self.kb_time = 0.0
                self.vy = 0.0
                if self.anim is not None:
                    self.anim.set_clip("ko", reset=True)
            return True
        return super().take_hit(
            damage, knockback, hitstun, direction, launch=launch
        )

    # --- update -------------------------------------------------------------
    def update(self, dt: float, input_state, target, scene) -> None:
        self.update_common(dt)
        self.q_cd = max(0.0, self.q_cd - dt)
        self.e_cd = max(0.0, self.e_cd - dt)

        if self.state == FighterState.KO:
            self.vx = 0.0
            self._force_end_e()
            if self.anim is not None:
                self.anim.update(dt)
            self.stage.move_fighter(self, dt)
            return

        if self.e_phase is not None:
            self._update_e(dt, input_state, target, scene)
            self.stage.move_fighter(self, dt)
            return

        if self.state == FighterState.HURT:
            self.vx = 0.0
            self._capture_locked_input(input_state)
            if self.anim is not None:
                self.anim.update(dt)
            if self.hitstun <= 0.0 and self.hp > 0.0:
                self.set_air_or_idle_anim()
            self.stage.move_fighter(self, dt)
            return

        if self.climbing:
            self._update_climb(dt, input_state, scene)
            return

        if self.state == FighterState.ATTACK:
            self._update_attack(dt, input_state, target, scene)
            self.stage.move_fighter(self, dt)
            return

        if self.statuses.control_locked():
            self.vx = 0.0
            self._capture_locked_input(input_state)
            self.set_air_or_idle_anim()
            if self.anim is not None:
                self.anim.update(dt)
            self.stage.move_fighter(self, dt)
            return

        self._handle_control(dt, input_state, target, scene)
        if not self.climbing:
            self.stage.move_fighter(self, dt)

    def _capture_locked_input(self, input_state) -> None:
        action = input_state.buffer.consume_newest(("punch", "kick", "q", "e", "jump"))
        if action is not None:
            self.queued_action = action

    def _update_attack(self, dt, input_state, target, scene) -> None:
        self.vx = 0.0
        runtime = self.attack_runtime
        if runtime is None:
            self.state = FighterState.IDLE
            return
        action = input_state.buffer.consume_newest(("punch", "kick", "q", "e", "jump"))
        if action is not None:
            self.queued_action = action
        runtime.update(dt)
        if self.anim is not None:
            self.anim.update(dt)
        self._update_attack_fx(scene)
        if not runtime.finished:
            return
        self.attack_runtime = None
        self.attack_id = None
        if self._execute_queued(input_state, scene, target):
            return
        self.state = FighterState.IDLE
        if self.anim is not None:
            self.anim.set_clip("idle", reset=True)

    def _execute_queued(self, input_state, scene, target) -> bool:
        action = self.queued_action
        self.queued_action = None
        if not action:
            return False
        left = input_state.is_held("left")
        right = input_state.is_held("right")
        if left and not right:
            self.facing = -1
        elif right and not left:
            self.facing = 1
        if action == "punch":
            return self._start_snowball(scene, target)
        if action == "kick":
            return self._start_staff(scene, target)
        if action == "q":
            return self._start_q(scene, target)
        if action == "e":
            return self._start_e(scene)
        if action == "jump":
            return self._start_jump()
        return False

    def _handle_control(self, dt, input_state, target, scene) -> None:
        if self.queued_action is not None:
            ground_action = self.queued_action in ("punch", "kick", "q", "e", "jump")
            if not (ground_action and not self.on_ground):
                if self._execute_queued(input_state, scene, target):
                    return

        left = input_state.is_held("left")
        right = input_state.is_held("right")
        if left and not right:
            self.facing = -1
        elif right and not left:
            self.facing = 1

        if input_state.buffer.has("e"):
            if self._start_e(scene):
                input_state.buffer.consume("e")
                return
            input_state.buffer.consume("e")

        if input_state.buffer.has("q") and self._start_q(scene, target):
            input_state.buffer.consume("q")
            return

        if input_state.buffer.has("punch") and self._start_snowball(scene, target):
            input_state.buffer.consume("punch")
            return

        if input_state.buffer.has("kick") and self._start_staff(scene, target):
            input_state.buffer.consume("kick")
            return

        if self.try_start_climb(input_state, scene):
            input_state.buffer.consume("jump")
            return

        if input_state.buffer.has("jump") and self._start_jump():
            input_state.buffer.consume("jump")

        crouch = input_state.is_held("crouch") and self.on_ground
        slow = self.statuses.slow_factor()

        if crouch:
            self.state = FighterState.CROUCH
            self.vx = 0.0
            if self.anim is not None:
                self.anim.set_clip("crouch")
        elif not self.on_ground:
            self.state = FighterState.AIR
            if self.anim is not None:
                self.anim.set_clip("jump")
                self.anim.set_frame(0 if self.vy < 0.0 else 1)
            if left and not right:
                self.vx = -self.walk_speed * slow
            elif right and not left:
                self.vx = self.walk_speed * slow
            else:
                self.vx = 0.0
        else:
            if left and not right:
                self.vx = -self.walk_speed * slow
                self.state = FighterState.WALK
                if self.anim is not None:
                    self.anim.set_clip("walk")
                    self.anim.update(dt)
            elif right and not left:
                self.vx = self.walk_speed * slow
                self.state = FighterState.WALK
                if self.anim is not None:
                    self.anim.set_clip("walk")
                    self.anim.update(dt)
            else:
                self.vx = 0.0
                self.state = FighterState.IDLE
                if self.anim is not None:
                    self.anim.set_clip("idle")
                    self.anim.update(dt)

    # --- actions ------------------------------------------------------------
    def start_attack(self, attack_id: str, scene, target) -> None:
        scene.face_target_if_locked(self, target)
        self.attack_id = attack_id
        self.state = FighterState.ATTACK
        self.vx = 0.0
        clip = ATTACK_CLIPS[attack_id]
        if self.anim is not None:
            self.anim.set_clip(clip, reset=True)
        self.staff_fx_02_spawned = False
        self.staff_fx_03_spawned = False
        self.shard_charge_spawned = False
        self.staff_fx_02 = None
        self.staff_fx_03 = None
        data = self.store.attacks[attack_id]
        self.attack_runtime = AttackRuntime(self, attack_id, data, target, scene)

    def _start_snowball(self, scene, target) -> bool:
        if not self.on_ground:
            return False
        self.start_attack("eira_snowball", scene, target)
        return True

    def _start_staff(self, scene, target) -> bool:
        if not self.on_ground:
            return False
        self.start_attack("eira_staff_strike", scene, target)
        return True

    def _start_q(self, scene, target) -> bool:
        if not self.on_ground or self.q_cd > 0.0:
            return False
        self.q_cd = self.q_cd_max
        self.start_attack("eira_ice_shard", scene, target)
        return True

    def _start_jump(self) -> bool:
        if not self.on_ground:
            return False
        self.attack_runtime = None
        self.attack_id = None
        self.vy = -self.jump_v
        self.on_ground = False
        self.state = FighterState.AIR
        if self.anim is not None:
            self.anim.set_clip("jump")
        return True

    # --- reset --------------------------------------------------------------
    def reset(self) -> None:
        x, y = self.spawn
        self.reset_common(x, y, 1)
        self.q_cd = 0.0
        self.e_cd = 0.0
        self.attack_runtime = None
        self.attack_id = None
        self.staff_fx_02_spawned = False
        self.staff_fx_03_spawned = False
        self.shard_charge_spawned = False
        self.staff_fx_02 = None
        self.staff_fx_03 = None
        self.queued_action = None
        self._clear_e_state()
        if self.anim is not None:
            self.anim.set_clip("idle", reset=True)
