"""Rhea Thorn: alternating shuriken slashes, poison throws and a dash-return."""

from __future__ import annotations

import math

import pygame

from .combat import AttackRuntime
from .fighter import Fighter, FighterState

# The back-view climb frames are staged at the standing scale; the shared
# climb draw scale matches Nyra's approved 1.1x silhouette.
RHEA_CLIMB_DRAW_SCALE = 1.1


class Rhea(Fighter):
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
        self.climb_draw_scale = RHEA_CLIMB_DRAW_SCALE
        self.set_attack_stats(cfg)
        self.knock_up_gravity = float(
            combat_cfg.get("knock_up_gravity", self.gravity)
        )
        self.q_cd_max = float(cfg["cooldowns"]["q"])
        self.e_cd_max = float(cfg["cooldowns"]["e"])
        self.walk_speed = float(cfg["move"]["walk"])
        self.jump_v = float(cfg["move"]["jump_v"])

        self.q_cd = 0.0
        self.e_cd = 0.0
        self.slash_right = True
        self.poison_source = "rhea_poison"
        self.poison_extended_targets: set[int] = set()
        self.attack_runtime: AttackRuntime | None = None
        self.attack_id: str | None = None
        self.attack_recovery_start = 0.0
        self.armor_applied = False
        self.queued_action: str | None = None
        # E is a three-phase skill: outbound dash, a free-control return
        # window, then an optional return dash. e_cd starts only when the
        # whole skill ends.
        self.e_phase: str | None = None
        self.e_window = 0.0
        self.e_buffered_return = False
        self.e_cast_x = 0.0
        self.e_cast_y = 0.0
        self.e_cast_facing = 1
        self.e_return_from_x = 0.0
        self.e_return_from_y = 0.0
        self.ignore_terrain = False
        self.reset()

    # --- public state -------------------------------------------------------
    def can_start_e(self) -> bool:
        return (
            self.e_phase is None
            and self.state not in (FighterState.HURT, FighterState.KO)
            and self.e_cd <= 0.0
        )

    def _clear_phase_armor(self) -> None:
        effect = self.statuses.effects.get("super_armor")
        if effect is not None and effect.source in (
            "rhea_dash",
            "rhea_dash_return",
        ):
            self.statuses.effects.pop("super_armor", None)

    def _clear_e_state(self) -> None:
        self.e_phase = None
        self.e_window = 0.0
        self.e_buffered_return = False
        self.ignore_terrain = False
        self._clear_phase_armor()

    def _finish_e_skill(self) -> None:
        self.e_window = 0.0
        self.e_phase = None
        self.e_buffered_return = False
        self.ignore_terrain = False
        self.e_cd = self.e_cd_max
        self._clear_phase_armor()
        if self.queued_action == "e":
            self.queued_action = None

    def take_hit(
        self,
        damage: float,
        knockback: float,
        hitstun: float,
        direction: int,
        launch: float = 0.0,
    ) -> bool:
        # An ignored/invincible hit must not cancel the return window.
        if self.invincible or self.hp <= 0.0:
            return False
        shielded = self.statuses.has("sacred_shield")
        if shielded:
            damage = 0.0
        if self.statuses.has("super_armor"):
            if shielded:
                self.blocked_hits += 1
            self.hp = max(0.0, self.hp - damage)
            self.flash = 0.0 if shielded else 0.12
            if self.hp <= 0.0:
                self.state = FighterState.KO
                self.hitstun = 0.0
                self.kb_vx = 0.0
                self.kb_time = 0.0
                self.attack_runtime = None
                self.attack_id = None
                self.armor_applied = False
                self.queued_action = None
                self._clear_e_state()
                if self.anim is not None:
                    self.anim.set_clip("ko", reset=True)
            return True
        # A non-armored hit during the window (or an edge-case hit at the
        # end of a dash phase) ends the whole skill and starts the cooldown.
        if self.e_phase is not None:
            self._finish_e_skill()
        self.queued_action = None
        return super().take_hit(damage, knockback, hitstun, direction, launch=launch)

    def cancel_attack(self) -> None:
        e_active = self.e_phase is not None
        self._clear_e_state()
        if e_active:
            self.e_cd = self.e_cd_max
        self.queued_action = None
        super().cancel_attack()

    # --- update -------------------------------------------------------------
    def update(self, dt: float, input_state, target, scene) -> None:
        self.update_common(dt)
        self.q_cd = max(0.0, self.q_cd - dt)
        self.e_cd = max(0.0, self.e_cd - dt)

        if self.e_phase is not None and self.state in (
            FighterState.KO,
            FighterState.HURT,
        ):
            self._clear_e_state()
        elif self.e_phase == "window":
            self.e_window = max(0.0, self.e_window - dt)
            if self.e_window <= 0.0:
                self._finish_e_skill()

        if self.state == FighterState.KO:
            self.vx = 0.0
            self.attack_runtime = None
            self.attack_id = None
            self.armor_applied = False
            self.queued_action = None
            self._clear_e_state()
            self.anim.update(dt)
            self.stage.move_fighter(self, dt)
            return

        if self.state == FighterState.HURT:
            self.vx = 0.0
            self._capture_locked_input(input_state)
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
            if self.attack_id not in ("rhea_dash", "rhea_dash_return"):
                self.stage.move_fighter(self, dt)
            return

        if self.statuses.control_locked():
            self.vx = 0.0
            self._capture_locked_input(input_state)
            self.set_air_or_idle_anim()
            self.anim.update(dt)
            self.stage.move_fighter(self, dt)
            return

        self._handle_control(dt, input_state, target, scene)
        if not self.climbing:
            self.stage.move_fighter(self, dt)

    def _update_attack(self, dt, input_state, target, scene) -> None:
        self.vx = 0.0
        runtime = self.attack_runtime
        if runtime is None:
            self.state = FighterState.IDLE
            self.anim.set_clip("idle")
            return

        action = input_state.buffer.consume_newest(("punch", "kick", "q", "e", "jump"))
        if action == "e" and self.attack_id == "rhea_dash":
            self.e_buffered_return = True
        elif action is not None:
            self.queued_action = action

        runtime.update(dt)
        if self.attack_id in ("rhea_dash", "rhea_dash_return"):
            self._update_dash_motion(runtime, dt, scene)

        armor_from = float(runtime.data.get("armor_from", 0.0))
        armor_until = float(runtime.data.get("armor_until", 0.0))
        if (
            not self.armor_applied
            and armor_until > 0.0
            and runtime.time >= armor_from
        ):
            self.statuses.add(
                "super_armor",
                max(0.0, armor_until - armor_from),
                source=self.attack_id,
            )
            self.armor_applied = True
        self.anim.update(dt)

        if not runtime.finished:
            return

        if self.attack_id == "rhea_dash":
            if self._finish_outbound(scene, target):
                return
            if self._execute_queued(input_state, scene, target):
                return
            self.state = FighterState.IDLE
            self.anim.set_clip("idle")
            return

        if self.attack_id == "rhea_dash_return":
            if target is not None:
                scene.push_apart(self, target)
            self._finish_e_skill()
            self.attack_runtime = None
            self.attack_id = None
            self.armor_applied = False
            self.state = FighterState.IDLE
            self.anim.set_clip("idle")
            if self._execute_queued(input_state, scene, target):
                return
            return

        if self._execute_queued(input_state, scene, target):
            return
        self.state = FighterState.IDLE
        self.attack_runtime = None
        self.attack_id = None
        self.anim.set_clip("idle")

    def _finish_outbound(self, scene, target) -> bool:
        """Open the 2s window, or start the buffered return immediately."""
        self.e_phase = "window"
        self.e_window = 2.0
        self.ignore_terrain = False
        self._clear_phase_armor()
        buffered = self.e_buffered_return
        self.e_buffered_return = False
        self.attack_runtime = None
        self.attack_id = None
        self.armor_applied = False
        self.state = FighterState.IDLE
        self.anim.set_clip("idle")
        if not buffered:
            return False
        # An early E takes priority over any other queued action.
        self.queued_action = None
        return self._start_return(scene, target)

    def _update_dash_motion(self, runtime: AttackRuntime, dt: float, scene) -> None:
        """Outbound burst, then a lerped return to the original cast point."""
        if self.attack_id == "rhea_dash":
            if 0.06 <= runtime.time <= 0.60:
                scene.stage.move_x(
                    self, self.facing * 1100.0 * dt, ignore_blocks=True
                )
            return
        if self.attack_id == "rhea_dash_return":
            progress = min(1.0, runtime.time / max(runtime.duration, 1e-6))
            desired_x = self.e_return_from_x + (
                self.e_cast_x - self.e_return_from_x
            ) * progress
            desired_y = self.e_return_from_y + (
                self.e_cast_y - self.e_return_from_y
            ) * progress
            scene.stage.move_x(
                self, desired_x - self.x, ignore_blocks=True
            )
            self.y = desired_y
            if progress >= 1.0:
                self.on_ground = True

    def _capture_locked_input(self, input_state) -> None:
        action = input_state.buffer.consume_newest(("punch", "kick", "q", "e", "jump"))
        if action is not None:
            self.queued_action = action

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
            return self._start_slash(scene, target)
        if action == "kick":
            return self._start_throw(scene, target)
        if action == "q":
            return self._start_q(scene, target)
        if action == "e":
            return self._start_e(scene, target)
        if action == "jump":
            return self._start_jump()
        return False

    def _start_slash(self, scene, target) -> bool:
        if not self.on_ground:
            return False
        self.start_attack("rhea_slash", scene, target)
        return True

    def _start_throw(self, scene, target) -> bool:
        if not self.on_ground:
            return False
        self.start_attack("rhea_throw", scene, target)
        return True

    def _start_q(self, scene, target) -> bool:
        if not self.on_ground or self.q_cd > 0.0:
            return False
        self.q_cd = self.q_cd_max
        self.start_attack("rhea_poison_throw", scene, target)
        return True

    def _start_e(self, scene, target) -> bool:
        if self.e_phase == "window":
            if not self.on_ground:
                return False
            return self._start_return(scene, target)
        if self.e_phase is not None or not self.on_ground or not self.can_start_e():
            return False
        self.e_phase = "out"
        self.e_window = 0.0
        self.e_buffered_return = False
        self.e_cast_x = self.x
        self.e_cast_y = self.y
        self.ignore_terrain = True
        self.start_attack("rhea_dash", scene, target)
        self.e_cast_facing = self.facing
        return True

    def _start_return(self, scene, target) -> bool:
        if not self.on_ground:
            return False
        dx = self.e_cast_x - self.x
        dy = self.e_cast_y - self.y
        duration = max(0.12, math.hypot(dx, dy) / 1500.0)
        data = dict(self.store.attacks["rhea_dash_return"])
        data["duration"] = duration
        data["armor_until"] = duration
        self.e_phase = "return"
        self.e_window = 0.0
        self.e_buffered_return = False
        self.e_return_from_x = self.x
        self.e_return_from_y = self.y
        self.ignore_terrain = True
        self.facing = self.e_cast_facing
        self.start_attack(
            "rhea_dash_return",
            scene,
            target,
            data_override=data,
            face_target=False,
        )
        return True

    def _start_jump(self) -> bool:
        if not self.on_ground:
            return False
        self.attack_runtime = None
        self.attack_id = None
        self.vy = -self.jump_v
        self.on_ground = False
        self.state = FighterState.AIR
        self.anim.set_clip("jump")
        return True

    def _handle_control(self, dt: float, input_state, target, scene) -> None:
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
            if self._start_e(scene, target):
                input_state.buffer.consume("e")
                return
            if self.e_phase == "window":
                # Airborne E is ignored; consume it so the 0.12s buffer
                # cannot fire a return after landing.
                input_state.buffer.consume("e")
                if self.queued_action == "e":
                    self.queued_action = None

        if input_state.buffer.has("q") and self._start_q(scene, target):
            input_state.buffer.consume("q")
            return

        if input_state.buffer.has("punch") and self._start_slash(scene, target):
            input_state.buffer.consume("punch")
            return

        if input_state.buffer.has("kick") and self._start_throw(scene, target):
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
            self.anim.set_clip("crouch")
        elif not self.on_ground:
            self.state = FighterState.AIR
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
                self.anim.set_clip("walk")
                self.anim.update(dt)
            elif right and not left:
                self.vx = self.walk_speed * slow
                self.state = FighterState.WALK
                self.anim.set_clip("walk")
                self.anim.update(dt)
            else:
                self.vx = 0.0
                self.state = FighterState.IDLE
                self.anim.set_clip("idle")
                self.anim.update(dt)

    # --- actions ------------------------------------------------------------
    def start_attack(
        self,
        attack_id: str,
        scene,
        target,
        data_override: dict | None = None,
        face_target: bool = True,
    ) -> None:
        if face_target:
            scene.face_target_if_locked(self, target)
        self.attack_id = attack_id
        self.state = FighterState.ATTACK
        self.vx = 0.0
        if attack_id == "rhea_slash":
            clip = "rhea_slash_r" if self.slash_right else "rhea_slash_l"
            self.slash_right = not self.slash_right
        else:
            clip = attack_id
        self.anim.set_clip(clip, reset=True)

        data = data_override or self.store.attacks[attack_id]
        armor_from = float(data.get("armor_from", 0.0))
        armor_until = float(data.get("armor_until", 0.0))
        self.armor_applied = False
        if armor_until > 0.0 and armor_from <= 0.0:
            self.statuses.add("super_armor", armor_until, source=attack_id)
            self.armor_applied = True
        self.attack_runtime = AttackRuntime(self, attack_id, data, target, scene)
        last_event = 0.0
        for event in data.get("events", []):
            last_event = max(last_event, float(event.get("until", event.get("t", 0.0))))
        self.attack_recovery_start = (
            last_event if last_event > 0.0 else float(data["duration"]) * 0.5
        )
        self.poison_extended_targets.clear()
        self.queued_action = None

    # --- passive ------------------------------------------------------------
    def on_hit_success(self, attack: dict, target, bonus: float) -> None:
        if not attack.get("extends_poison"):
            return
        self._extend_poison(target)

    def on_projectile_hit(self, projectile) -> None:
        target = projectile.target
        if target is None or target.hp <= 0.0 or target.invincible:
            return
        if projectile.status == "poison":
            dps = target.max_hp * float(projectile.status_dps_pct)
            target.statuses.add(
                "poison",
                float(projectile.status_duration),
                source=self.poison_source,
                dps=dps,
            )
            return
        if getattr(projectile, "extends_poison", False):
            self._extend_poison(target)

    def _extend_poison(self, target) -> None:
        if target.hp <= 0.0 or target.invincible:
            return
        if id(target) in self.poison_extended_targets:
            return
        if target.statuses.extend_poison(self.poison_source, 1.0):
            self.poison_extended_targets.add(id(target))

    # --- rendering ----------------------------------------------------------
    def draw(self, surface, tint=None) -> None:
        runtime = self.attack_runtime
        motion = 0
        if (
            runtime is not None
            and self.e_phase == "out"
            and 0.06 <= runtime.time <= 0.60
        ):
            motion = self.facing
        elif runtime is not None and self.e_phase == "return":
            motion = -self.facing
        if motion:
            pivot_x, pivot_y = self.anim.pivot
            for index, alpha in ((1, 64), (2, 34)):
                ghost = self.anim.surface(self.facing).copy()
                ghost.fill((255, 255, 255, alpha), special_flags=pygame.BLEND_RGBA_MULT)
                surface.blit(
                    ghost,
                    (
                        round(self.x - motion * index * 22.0 - pivot_x),
                        round(self.y - pivot_y),
                    ),
                )
        super().draw(surface, tint)

    # --- reset --------------------------------------------------------------
    def reset(self) -> None:
        x, y = self.spawn
        self.reset_common(x, y, 1)
        self.q_cd = 0.0
        self.e_cd = 0.0
        self.slash_right = True
        self.poison_extended_targets.clear()
        self.attack_runtime = None
        self.attack_id = None
        self.attack_recovery_start = 0.0
        self.armor_applied = False
        self.queued_action = None
        self.e_phase = None
        self.e_window = 0.0
        self.e_buffered_return = False
        self.e_cast_x = 0.0
        self.e_cast_y = 0.0
        self.e_cast_facing = 1
        self.e_return_from_x = 0.0
        self.e_return_from_y = 0.0
        self.ignore_terrain = False
        self._clear_phase_armor()
        if self.anim is not None:
            self.anim.set_clip("idle", reset=True)
