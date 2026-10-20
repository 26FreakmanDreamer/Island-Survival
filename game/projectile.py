"""Lina's Q air wave."""

from __future__ import annotations

import pygame

from .combat import resolve_projectile_hit


class QWave:
    def __init__(
        self,
        owner,
        target,
        x: float,
        y: float,
        direction: int,
        speed: float,
        max_range: float,
        damage: float,
        knockback: float,
        hitstun: float,
        hitstop: float,
        energy_gain: float,
        flame: bool,
        flame_bonus: float,
        grant_energy: bool,
    ) -> None:
        self.owner = owner
        self.target = target
        self.x = float(x)
        self.y = float(y)
        self.direction = 1 if direction >= 0 else -1
        self.speed = float(speed)
        self.max_range = float(max_range)
        self.traveled = 0.0
        self.damage = float(damage)
        self.knockback = float(knockback)
        self.hitstun = float(hitstun)
        self.hitstop = float(hitstop)
        self.energy_gain = float(energy_gain)
        self.flame = flame
        self.flame_bonus = float(flame_bonus)
        self.grant_energy = grant_energy
        self.alive = True
        self.hit = False
        self.rect = pygame.Rect(0, 0, 44, 34)
        self.rect.center = (round(self.x), round(self.y))

    def update(self, dt: float, scene) -> None:
        if not self.alive:
            return
        step = self.speed * dt
        self.x += step * self.direction
        self.traveled += step
        self.rect.center = (round(self.x), round(self.y))

        if self.traveled >= self.max_range:
            self.alive = False
            return

        for block in scene.stage.blocks:
            if self.rect.colliderect(block):
                self.alive = False
                return

        if not self.hit and self.target is not None and self.rect.colliderect(self.target.hurtbox()):
            self.hit = True
            resolve_projectile_hit(scene, self)
            self.alive = False

    def draw(self, surface: pygame.Surface) -> None:
        size = 64
        orb = pygame.Surface((size, size), pygame.SRCALPHA)
        center = size // 2
        color = (120, 230, 255) if not self.flame else (255, 150, 90)
        trail_direction = -self.direction

        for index in range(3):
            offset = (index + 1) * 7
            alpha = max(0, 120 - index * 30)
            pygame.draw.circle(
                orb,
                (*color, alpha),
                (center + trail_direction * offset, center),
                max(2, 8 - index * 2),
            )

        pygame.draw.circle(orb, (*color, 225), (center, center), 15)
        pygame.draw.circle(orb, (240, 255, 255, 255), (center - 4, center - 4), 6)
        pygame.draw.circle(orb, (255, 255, 255, 180), (center, center), 15, 2)
        surface.blit(orb, (round(self.x - size * 0.5), round(self.y - size * 0.5)))
