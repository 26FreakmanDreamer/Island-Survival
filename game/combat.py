"""Attack window scheduling, hit resolution and damage pipeline."""

from __future__ import annotations

import pygame

from .config import FIXED_DT
from .fighter import FighterState


def attack_damage(attacker, attack: dict, event: dict | None = None) -> float:
    """Damage before flame/damage-reduction modifiers.

    The spec separates basic and extra ATK for Lina's kick/Q; Warrior skills
    use the combined ``atk`` via equal multipliers. An explicit event
    ``damage`` value still overrides everything for special attacks.
    """
    if event is not None and "damage" in event:
        return float(event["damage"])
    if "basic_mult" in attack or "extra_mult" in attack:
        return (
            getattr(attacker, "basic_atk", 0.0) * float(attack.get("basic_mult", 0.0))
            + getattr(attacker, "extra_atk", 0.0) * float(attack.get("extra_mult", 0.0))
        )
    multiplier = float((event or {}).get("damage_mult", attack.get("damage_mult", 1.0)))
    return getattr(attacker, "atk", 0.0) * multiplier


def local_box_to_rect(
    fighter,
    box: list[float],
    origin_x: float | None = None,
    origin_y: float | None = None,
    facing: int | None = None,
) -> pygame.Rect:
    x, y, width, height = box
    if origin_x is None:
        origin_x = fighter.x
    if origin_y is None:
        origin_y = fighter.y
    if facing is None:
        facing = fighter.facing
    if facing >= 0:
        left = origin_x + x
    else:
        left = origin_x - x - width
    top = origin_y + y
    return pygame.Rect(round(left), round(top), int(width), int(height))


class AttackRuntime:
    """One active attack: advances its clock and fires frame events."""

    def __init__(self, attacker, attack_id: str, data: dict, target, scene) -> None:
        self.attacker = attacker
        self.attack_id = attack_id
        self.data = data
        self.target = target
        self.targets = tuple(scene.targets_for(attacker))
        self.scene = scene
        self.time = 0.0
        self.finished = False
        # Hitboxes with the same group share one hit-per-target guard. Rhea's
        # dash uses separate outbound/return groups; every existing attack
        # stays in the implicit "default" group.
        self.hit_targets: dict[str, set[int]] = {}
        self.lunge_done = False
        self.spawned_events: set[int] = set()
        self.cast_x = float(attacker.x)
        self.cast_y = float(attacker.y)
        self.cast_facing = 1 if attacker.facing >= 0 else -1

    @property
    def duration(self) -> float:
        return float(self.data["duration"])

    def update(self, dt: float) -> None:
        self.time += dt

        if not self.lunge_done and self.time >= float(self.data.get("lunge_time", 0.0)):
            self.lunge_done = True
            lunge = float(self.data.get("lunge", 0.0))
            if lunge and self.attacker.on_ground:
                self.scene.stage.move_x(self.attacker, self.attacker.facing * lunge)

        for index, event in enumerate(self.data.get("events", [])):
            event_time = float(event.get("t", 0.0))
            if event["type"] == "hitbox":
                until = float(event.get("until", event_time + FIXED_DT))
                if event_time <= self.time < until:
                    if event.get("anchor") == "cast":
                        rect = local_box_to_rect(
                            self.attacker,
                            event["box"],
                            self.cast_x,
                            self.cast_y,
                            self.cast_facing,
                        )
                    else:
                        rect = local_box_to_rect(self.attacker, event["box"])
                    self.scene.debug_hitboxes.append(rect)
                    group = event.get("hit_group", "default")
                    hit_targets = self.hit_targets.setdefault(group, set())
                    for target in self.targets:
                        if target.invincible or target.hp <= 0.0:
                            continue
                        if id(target) in hit_targets:
                            continue
                        if target.hurtbox().colliderect(rect):
                            hit_targets.add(id(target))
                            resolve_hit(
                                self.scene, self.attacker, target, self.data, event
                            )
            elif event["type"] == "dash":
                until = float(event.get("until", event_time + FIXED_DT))
                if event_time <= self.time < until:
                    speed = float(event.get("speed", 0.0))
                    if speed:
                        self.scene.stage.move_x(
                            self.attacker,
                            self.attacker.facing * speed * dt,
                        )
            elif event["type"] == "projectile":
                if self.time >= event_time and index not in self.spawned_events:
                    self.spawned_events.add(index)
                    self.scene.spawn_projectile_from_event(self.attacker, self.data, event)
            elif event["type"] == "fx":
                if self.time >= event_time and index not in self.spawned_events:
                    self.spawned_events.add(index)
                    self.scene.spawn_slash_effect(
                        self.attacker,
                        event,
                        cast_x=self.cast_x,
                        cast_y=self.cast_y,
                        cast_facing=self.cast_facing,
                    )

        if self.time >= self.duration:
            self.finished = True


def resolve_hit(scene, attacker, target, attack: dict, event: dict) -> None:
    if target.invincible or target.hp <= 0.0:
        return

    bonus = attacker.current_flame_bonus()
    damage = attack_damage(attacker, attack, event) * (1.0 + bonus)
    poison_bonus_pct = float(event.get("bonus_vs_poison_max_hp_pct", 0.0))
    if poison_bonus_pct > 0.0 and target.statuses.has("poison"):
        damage += target.max_hp * poison_bonus_pct
    damage = max(0.0, damage * (1.0 - target.statuses.damage_reduction()))

    knockback = float(event.get("knockback", 0.0))
    hitstun = float(attack.get("hitstun", scene.store.stats["combat"]["hitstun"]))
    hitstop = float(attack.get("hitstop", scene.store.stats["combat"]["hitstop"]))
    launch = float(event.get("launch", 0.0))
    if target.statuses.has("super_armor"):
        launch = 0.0
    knock_up_time = float(event.get("knock_up", 0.0))

    if damage > 0.0:
        target.take_hit(damage, knockback, hitstun, attacker.facing, launch=launch)
        if (
            knock_up_time > 0.0
            and launch > 0.0
            and target.hp > 0.0
            and target.state == FighterState.HURT
        ):
            target.statuses.add(
                "knock_up",
                knock_up_time,
                source=getattr(attacker, "name", None),
            )
        if target.hp <= 0.0 or target.flash > 0.0:
            scene.particles.emit_hit(target.x, target.y - 120, (255, 210, 120))
        hit_fx = event.get("hit_fx")
        if hit_fx:
            scene.spawn_hit_fx(hit_fx, attacker, target, event)
        attacker.on_hit_success(attack, target, bonus)
        scene.hitstop = max(scene.hitstop, hitstop)

    scene.last_hit = {
        "attacker": getattr(attacker, "name", "Lina"),
        "target": getattr(target, "name", "Enemy"),
        "damage": damage,
        "bonus": bonus,
        "knockback": knockback,
        "time": scene.sim_time,
    }


def resolve_projectile_hit(scene, projectile) -> None:
    target = projectile.target
    if target is None or target.invincible or target.hp <= 0.0:
        return

    damage = projectile.damage
    max_hp_pct = float(getattr(projectile, "bonus_target_max_hp_pct", 0.0))
    if max_hp_pct > 0.0:
        damage += target.max_hp * max_hp_pct
    damage = max(0.0, damage * (1.0 - target.statuses.damage_reduction()))
    if damage > 0.0:
        target.take_hit(damage, projectile.knockback, projectile.hitstun, projectile.direction)
        hit_color = getattr(projectile, "hit_color", (120, 230, 255))
        scene.particles.emit_hit(target.x, projectile.y, hit_color)
        projectile.owner.on_projectile_hit(projectile)
        scene.spawn_projectile_impact(projectile, target)
        scene.hitstop = max(scene.hitstop, projectile.hitstop)

    scene.last_hit = {
        "attacker": getattr(projectile.owner, "name", "Lina"),
        "target": getattr(target, "name", "Enemy"),
        "damage": damage,
        "bonus": projectile.flame_bonus,
        "knockback": projectile.knockback,
        "time": scene.sim_time,
    }
