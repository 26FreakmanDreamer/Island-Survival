"""Attack window scheduling, hit resolution and damage pipeline."""

from __future__ import annotations

import pygame

from .config import FIXED_DT


def local_box_to_rect(fighter, box: list[float]) -> pygame.Rect:
    x, y, width, height = box
    if fighter.facing >= 0:
        left = fighter.x + x
    else:
        left = fighter.x - x - width
    top = fighter.y + y
    return pygame.Rect(round(left), round(top), int(width), int(height))


class AttackRuntime:
    """One active attack: advances its clock and fires frame events."""

    def __init__(self, attacker, attack_id: str, data: dict, target, scene) -> None:
        self.attacker = attacker
        self.attack_id = attack_id
        self.data = data
        self.target = target
        self.scene = scene
        self.time = 0.0
        self.finished = False
        self.hit_targets: set[int] = set()
        self.lunge_done = False
        self.spawned_events: set[int] = set()

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
                    rect = local_box_to_rect(self.attacker, event["box"])
                    self.scene.debug_hitboxes.append(rect)
                    if self.target is not None and id(self.target) not in self.hit_targets:
                        if self.target.hurtbox().colliderect(rect):
                            self.hit_targets.add(id(self.target))
                            resolve_hit(self.scene, self.attacker, self.target, self.data, event)
            elif event["type"] == "projectile":
                if self.time >= event_time and index not in self.spawned_events:
                    self.spawned_events.add(index)
                    self.scene.spawn_projectile_from_event(self.attacker, self.data, event)

        if self.time >= self.duration:
            self.finished = True


def resolve_hit(scene, attacker, target, attack: dict, event: dict) -> None:
    if target.invincible or target.hp <= 0.0:
        return

    bonus = attacker.current_flame_bonus()
    base = attacker.atk * float(event.get("damage_mult", attack.get("damage_mult", 1.0)))
    damage = base * (1.0 + bonus) * (1.0 - target.statuses.damage_reduction())
    damage = max(0.0, damage)

    knockback = float(event.get("knockback", 0.0))
    hitstun = float(attack.get("hitstun", scene.store.stats["combat"]["hitstun"]))
    hitstop = float(attack.get("hitstop", scene.store.stats["combat"]["hitstop"]))

    if damage > 0.0:
        target.take_hit(damage, knockback, hitstun, attacker.facing)
        if target.hp <= 0.0 or target.flash > 0.0:
            scene.particles.emit_hit(target.x, target.y - 120, (255, 210, 120))
        attacker.on_hit_success(attack, target, bonus)
        scene.hitstop = max(scene.hitstop, hitstop)

    scene.last_hit = {
        "attacker": getattr(attacker, "name", "Lina"),
        "target": getattr(target, "name", "Dummy"),
        "damage": damage,
        "bonus": bonus,
        "knockback": knockback,
        "time": scene.sim_time,
    }


def resolve_projectile_hit(scene, projectile) -> None:
    target = projectile.target
    if target is None or target.invincible or target.hp <= 0.0:
        return

    damage = projectile.damage * (1.0 - target.statuses.damage_reduction())
    if damage > 0.0:
        target.take_hit(damage, projectile.knockback, projectile.hitstun, projectile.direction)
        scene.particles.emit_hit(target.x, projectile.y, (120, 230, 255))
        projectile.owner.on_projectile_hit(projectile)
        scene.hitstop = max(scene.hitstop, projectile.hitstop)

    scene.last_hit = {
        "attacker": getattr(projectile.owner, "name", "Lina"),
        "target": getattr(target, "name", "Dummy"),
        "damage": damage,
        "bonus": projectile.flame_bonus,
        "knockback": projectile.knockback,
        "time": scene.sim_time,
    }
