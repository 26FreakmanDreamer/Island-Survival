"""Lina Seabright: four moves, energy, cooldowns and flame form."""

from __future__ import annotations

from .animation import AnimationPlayer
from .combat import AttackRuntime
from .config import CANONICAL_LINA_V1, FRAMES_DIR
from .fighter import Fighter, FighterState


class Lina(Fighter):
    name = "Lina"

    def __init__(self, store, stage) -> None:
        cfg = store.stats["lina"]
        combat_cfg = store.stats["combat"]
        anim = AnimationPlayer(
            store.animations["clips"],
            store.animations.get("flame_clips", {}),
            FRAMES_DIR,
            CANONICAL_LINA_V1,
            store.animations["pivot"],
        )
        x, y = stage.player_spawn
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
        )

        self.store = store
        self.cfg = cfg
        self.combat_cfg = combat_cfg
        self.atk = float(cfg["basic_atk"] + cfg["extra_atk"])
        self.max_energy = float(cfg["energy"]["max"])
        self.energy_start = float(cfg["energy"]["start"])
        self.energy_regen = float(cfg["energy"]["regen"])
        self.energy_gain = cfg["energy"]["gain"]
        self.q_cd_max = float(cfg["cooldowns"]["q"])
        self.e_cd_max = float(cfg["cooldowns"]["e"])
        self.flame_duration = float(cfg["flame"]["duration"])
        self.flame_step = float(cfg["flame"]["bonus_step"])
        self.flame_cap = float(cfg["flame"]["bonus_cap"])
        self.burn_dps = float(combat_cfg["burn_dps"])
        self.burn_duration = float(combat_cfg["burn_duration"])
        self.walk_speed = float(cfg["move"]["walk"])
        self.jump_v = float(cfg["move"]["jump_v"])

        self.energy = self.energy_start
        self.q_cd = 0.0
        self.e_cd = 0.0
        self.flame_time = 0.0
        self.flame_hits = 0
        self.next_punch = "punch_r"
        self.next_kick = "kick_r"
        self.attack_runtime: AttackRuntime | None = None
        self.attack_id: str | None = None
        self.attack_recovery_start = 0.0
        self.queued_action: str | None = None
        self.reset()

    # --- public state -------------------------------------------------------
    def can_start_e(self) -> bool:
        return (
            self.state not in (FighterState.HURT, FighterState.KO, FighterState.TRANSFORM)
            and self.e_cd <= 0.0
            and self.energy >= self.max_energy
        )

    def current_flame_bonus(self) -> float:
        if self.flame_time <= 0.0:
            return 0.0
        return min((self.flame_hits + 1) * self.flame_step, self.flame_cap)

    def take_hit(self, damage: float, knockback: float, hitstun: float, direction: int) -> bool:
        self.queued_action = None
        return super().take_hit(damage, knockback, hitstun, direction)

    # --- update -------------------------------------------------------------
    def update(self, dt: float, input_state, target, scene) -> None:
        self.update_common(dt)
        self.q_cd = max(0.0, self.q_cd - dt)
        self.e_cd = max(0.0, self.e_cd - dt)
        if self.pending_variant and self.state in (
            FighterState.IDLE,
            FighterState.WALK,
            FighterState.CROUCH,
            FighterState.AIR,
        ):
            self._apply_pending_variant()

        if self.flame_time > 0.0:
            self.flame_time = max(0.0, self.flame_time - dt)
            if self.flame_time <= 0.0:
                self.flame_hits = 0
                self.pending_variant = "normal"
                if self.state in (
                    FighterState.IDLE,
                    FighterState.WALK,
                    FighterState.CROUCH,
                    FighterState.AIR,
                ):
                    self._apply_pending_variant()

        if self.state == FighterState.KO:
            self.vx = 0.0
            self.anim.update(dt)
            self.stage.move_fighter(self, dt)
            return

        if self.state == FighterState.HURT:
            self.vx = 0.0
            self.anim.update(dt)
            if self.hitstun <= 0.0 and self.hp > 0.0:
                self.state = FighterState.IDLE
                self.anim.set_clip("idle")
                self._apply_pending_variant()
            self.stage.move_fighter(self, dt)
            return

        if self.state == FighterState.TRANSFORM:
            self.vx = 0.0
            self.anim.update(dt)
            if self.anim.finished:
                self.state = FighterState.IDLE
                self.anim.set_variant("flame")
                self.anim.set_clip("idle", reset=True)
            self.stage.move_fighter(self, dt)
            return

        if self.state == FighterState.ATTACK:
            self._update_attack(dt, input_state, target, scene)
            self.stage.move_fighter(self, dt)
            return

        if self.statuses.control_locked():
            self.vx = 0.0
            self.state = FighterState.IDLE
            self.anim.set_clip("idle")
            self.anim.update(dt)
            self.stage.move_fighter(self, dt)
            return

        self._handle_control(dt, input_state, target, scene)
        self.stage.move_fighter(self, dt)

    def _update_attack(self, dt: float, input_state, target, scene) -> None:
        self.vx = 0.0
        runtime = self.attack_runtime
        if runtime is None:
            self.state = FighterState.IDLE
            self.anim.set_clip("idle")
            return

        # Keep the newest action pressed during the attack. It waits until the
        # attack ends instead of expiring with the short input buffer.
        action = input_state.buffer.consume_newest(("punch", "kick", "q", "e", "jump"))
        if action is not None:
            self.queued_action = action

        # E can cancel the recovery portion of an attack.
        if (
            self.queued_action == "e"
            and self.can_start_e()
            and runtime.time >= self.attack_recovery_start
        ):
            self.queued_action = None
            self.start_transform()
            return

        runtime.update(dt)
        self.anim.update(dt)

        if runtime.finished:
            if self._execute_queued(input_state, scene, target):
                return
            self.state = FighterState.IDLE
            self.attack_runtime = None
            self.attack_id = None
            self.anim.set_clip("idle")
            self._apply_pending_variant()

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
            return self._start_punch(scene, target)
        if action == "kick":
            return self._start_kick(scene, target)
        if action == "q":
            return self._start_q(scene, target)
        if action == "jump":
            return self._start_jump()
        if action == "e" and self.can_start_e():
            self.start_transform()
            return True
        return False

    def _start_punch(self, scene, target) -> bool:
        if not self.on_ground:
            return False
        attack_id = self.next_punch
        self.next_punch = "punch_l" if attack_id == "punch_r" else "punch_r"
        self.start_attack(attack_id, scene, target)
        return True

    def _start_kick(self, scene, target) -> bool:
        if not self.on_ground:
            return False
        attack_id = self.next_kick
        self.next_kick = "kick_l" if attack_id == "kick_r" else "kick_r"
        self.start_attack(attack_id, scene, target)
        return True

    def _start_q(self, scene, target) -> bool:
        if not self.on_ground or self.q_cd > 0.0:
            return False
        self.q_cd = self.q_cd_max
        self.start_attack("q", scene, target)
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
        left = input_state.is_held("left")
        right = input_state.is_held("right")
        if left and not right:
            self.facing = -1
        elif right and not left:
            self.facing = 1

        # E has priority and can be used in the air.
        if input_state.buffer.has("e") and self.can_start_e():
            input_state.buffer.consume("e")
            self.start_transform()
            return

        if input_state.buffer.has("q") and self._start_q(scene, target):
            input_state.buffer.consume("q")
            return

        if input_state.buffer.has("punch") and self._start_punch(scene, target):
            input_state.buffer.consume("punch")
            return

        if input_state.buffer.has("kick") and self._start_kick(scene, target):
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
        self.attack_id = attack_id
        self.state = FighterState.ATTACK
        self.vx = 0.0
        self.anim.set_clip(attack_id, reset=True)

        data = self.store.attacks[attack_id]
        self.attack_runtime = AttackRuntime(self, attack_id, data, target, scene)
        last_event = 0.0
        for event in data.get("events", []):
            last_event = max(last_event, float(event.get("until", event.get("t", 0.0))))
        self.attack_recovery_start = (
            last_event if last_event > 0.0 else float(data["duration"]) * 0.5
        )
        self.queued_action = None

    def start_transform(self) -> None:
        self.energy = 0.0
        self.e_cd = self.e_cd_max
        self.q_cd = 0.0
        self.flame_time = self.flame_duration
        self.flame_hits = 0
        self.state = FighterState.TRANSFORM
        self.anim.set_variant("normal")
        self.anim.set_clip("transform", reset=True)
        self.vx = 0.0
        self.attack_runtime = None
        self.attack_id = None
        self.queued_action = None

    def on_hit_success(self, attack: dict, target, bonus: float) -> None:
        if self.flame_time > 0.0:
            self.flame_hits += 1
            target.statuses.add(
                "burn",
                self.burn_duration,
                source="lina_flame",
                dps=self.burn_dps,
            )
        else:
            gain = float(attack.get("energy_gain", 0.0))
            self.energy = min(self.max_energy, self.energy + gain)

    def on_projectile_hit(self, projectile) -> None:
        if projectile.flame:
            self.flame_hits += 1
            projectile.target.statuses.add(
                "burn",
                self.burn_duration,
                source="lina_flame",
                dps=self.burn_dps,
            )
        elif projectile.grant_energy:
            self.energy = min(self.max_energy, self.energy + projectile.energy_gain)

    def _apply_pending_variant(self) -> None:
        if not self.pending_variant:
            return
        variant = self.pending_variant
        self.pending_variant = None
        self.anim.set_variant(variant)
        clip = {
            FighterState.IDLE: "idle",
            FighterState.WALK: "walk",
            FighterState.CROUCH: "crouch",
            FighterState.AIR: "jump",
        }.get(self.state)
        if clip:
            self.anim.set_clip(clip, reset=True)

    # --- reset --------------------------------------------------------------
    def reset(self) -> None:
        x, y = self.stage.player_spawn
        self.reset_common(x, y, 1)
        self.energy = self.energy_start
        self.q_cd = 0.0
        self.e_cd = 0.0
        self.flame_time = 0.0
        self.flame_hits = 0
        self.next_punch = "punch_r"
        self.next_kick = "kick_r"
        self.attack_runtime = None
        self.attack_id = None
        self.queued_action = None
        self.pending_variant = None
        self.anim.set_variant("normal")
        self.anim.set_clip("idle", reset=True)
