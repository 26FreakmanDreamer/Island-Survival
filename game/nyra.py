"""Nyra Steel: sword combo, mark detonation and a pass-through dash."""

from __future__ import annotations

from .combat import AttackRuntime
from .fighter import Fighter, FighterState


class Nyra(Fighter):
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
        self.marks = 0
        self.mark_burst_time = 0.0
        self.mark_burst_damage = 0.0
        self.mark_detonations = 0
        self.attack_runtime: AttackRuntime | None = None
        self.attack_id: str | None = None
        self.attack_recovery_start = 0.0
        self.armor_applied = False
        self.queued_action: str | None = None
        self.reset()

    # --- public state -------------------------------------------------------
    def can_start_e(self) -> bool:
        return (
            self.state not in (FighterState.HURT, FighterState.KO)
            and self.e_cd <= 0.0
        )

    def take_hit(
        self,
        damage: float,
        knockback: float,
        hitstun: float,
        direction: int,
        launch: float = 0.0,
    ) -> bool:
        if self.statuses.has("super_armor") and not self.invincible and self.hp > 0.0:
            self.hp = max(0.0, self.hp - damage)
            self.flash = 0.12
            if self.hp <= 0.0:
                self.state = FighterState.KO
                self.hitstun = 0.0
                self.kb_vx = 0.0
                self.kb_time = 0.0
                self.attack_runtime = None
                self.attack_id = None
                if self.anim is not None:
                    self.anim.set_clip("ko", reset=True)
            return True
        self.queued_action = None
        return super().take_hit(damage, knockback, hitstun, direction, launch=launch)

    def cancel_attack(self) -> None:
        self.queued_action = None
        super().cancel_attack()

    # --- update -------------------------------------------------------------
    def update(self, dt: float, input_state, target, scene) -> None:
        self.update_common(dt)
        self.q_cd = max(0.0, self.q_cd - dt)
        self.e_cd = max(0.0, self.e_cd - dt)
        self.mark_burst_time = max(0.0, self.mark_burst_time - dt)
        if target is None or target.hp <= 0.0:
            self.marks = 0

        if self.state == FighterState.KO:
            self.vx = 0.0
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

        if self.state == FighterState.ATTACK:
            self._update_attack(dt, input_state, target, scene)
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
        self.stage.move_fighter(self, dt)

    def _update_attack(self, dt, input_state, target, scene) -> None:
        self.vx = 0.0
        runtime = self.attack_runtime
        if runtime is None:
            self.state = FighterState.IDLE
            self.anim.set_clip("idle")
            return

        action = input_state.buffer.consume_newest(("punch", "kick", "q", "e", "jump"))
        if action is not None:
            self.queued_action = action

        runtime.update(dt)
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

        if runtime.finished:
            if self.attack_id == "nyra_dash" and target is not None:
                scene.push_apart(self, target)
            if self._execute_queued(input_state, scene, target):
                return
            self.state = FighterState.IDLE
            self.attack_runtime = None
            self.attack_id = None
            self.anim.set_clip("idle")

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
            return self._start_wave(scene, target)
        if action == "kick":
            return self._start_thrust(scene, target)
        if action == "q":
            return self._start_q(scene, target)
        if action == "e":
            return self._start_e(scene, target)
        if action == "jump":
            return self._start_jump()
        return False

    def _start_wave(self, scene, target) -> bool:
        if not self.on_ground:
            return False
        self.start_attack("nyra_wave", scene, target)
        return True

    def _start_thrust(self, scene, target) -> bool:
        if not self.on_ground:
            return False
        self.start_attack("nyra_thrust", scene, target)
        return True

    def _start_q(self, scene, target) -> bool:
        if not self.on_ground or self.q_cd > 0.0:
            return False
        self.q_cd = self.q_cd_max
        self.start_attack("nyra_slash", scene, target)
        return True

    def _start_e(self, scene, target) -> bool:
        if not self.on_ground or not self.can_start_e():
            return False
        self.e_cd = self.e_cd_max
        self.start_attack("nyra_dash", scene, target)
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

        if input_state.buffer.has("e") and self._start_e(scene, target):
            input_state.buffer.consume("e")
            return

        if input_state.buffer.has("q") and self._start_q(scene, target):
            input_state.buffer.consume("q")
            return

        if input_state.buffer.has("punch") and self._start_wave(scene, target):
            input_state.buffer.consume("punch")
            return

        if input_state.buffer.has("kick") and self._start_thrust(scene, target):
            input_state.buffer.consume("kick")
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
    def start_attack(self, attack_id: str, scene, target) -> None:
        scene.face_target_if_locked(self, target)
        self.attack_id = attack_id
        self.state = FighterState.ATTACK
        self.vx = 0.0
        self.anim.set_clip(attack_id, reset=True)

        data = self.store.attacks[attack_id]
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
        self.queued_action = None

    # --- passive ------------------------------------------------------------
    def on_hit_success(self, attack: dict, target, bonus: float) -> None:
        if float(attack.get("marks_on_hit", 0.0)) <= 0.0:
            return
        if target.hp <= 0.0:
            self.marks = 0
            return
        self.marks += 1
        if self.marks < 4:
            return
        if target.invincible:
            return

        amount = 1.8 * self.atk + 0.10 * target.max_hp
        amount *= 1.0 - target.statuses.damage_reduction()
        target.take_hit(amount, 0.0, 0.0, self.facing)

        self.mark_burst_time = 0.4
        self.mark_burst_damage = amount
        self.mark_detonations += 1
        self.marks = 1 if target.hp > 0.0 else 0

        runtime = self.attack_runtime
        scene = runtime.scene if runtime is not None else None
        if scene is not None:
            scene.hitstop = max(scene.hitstop, 0.10)
            scene.particles.emit_hit(
                target.x,
                target.y - target.hurtbox_dims[1] * 0.5,
                (190, 220, 255),
            )

    # --- reset --------------------------------------------------------------
    def reset(self) -> None:
        x, y = self.spawn
        self.reset_common(x, y, 1)
        self.q_cd = 0.0
        self.e_cd = 0.0
        self.marks = 0
        self.mark_burst_time = 0.0
        self.mark_burst_damage = 0.0
        self.mark_detonations = 0
        self.attack_runtime = None
        self.attack_id = None
        self.attack_recovery_start = 0.0
        self.armor_applied = False
        self.queued_action = None
        if self.anim is not None:
            self.anim.set_clip("idle", reset=True)
