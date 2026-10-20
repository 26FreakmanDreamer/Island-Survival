"""Small debug-friendly particle system for flame and hit feedback."""

from __future__ import annotations

import random
from dataclasses import dataclass

import pygame


@dataclass
class Particle:
    x: float
    y: float
    vx: float
    vy: float
    life: float
    max_life: float
    radius: float
    color: tuple[int, int, int]


class ParticleSystem:
    def __init__(self) -> None:
        self.items: list[Particle] = []

    def _add(self, particle: Particle) -> None:
        if len(self.items) < 320:
            self.items.append(particle)

    def emit_flame(self, x: float, y: float) -> None:
        for _ in range(2):
            life = random.uniform(0.25, 0.55)
            self._add(
                Particle(
                    x=x + random.uniform(-22, 22),
                    y=y - random.uniform(20, 170),
                    vx=random.uniform(-18, 18),
                    vy=random.uniform(-110, -45),
                    life=life,
                    max_life=life,
                    radius=random.uniform(2.0, 5.0),
                    color=random.choice(((255, 150, 40), (255, 90, 30), (255, 220, 90))),
                )
            )

    def emit_hit(self, x: float, y: float, color: tuple[int, int, int]) -> None:
        for _ in range(8):
            life = random.uniform(0.12, 0.28)
            self._add(
                Particle(
                    x=x + random.uniform(-14, 14),
                    y=y + random.uniform(-14, 14),
                    vx=random.uniform(-180, 180),
                    vy=random.uniform(-160, 80),
                    life=life,
                    max_life=life,
                    radius=random.uniform(2.0, 4.5),
                    color=color,
                )
            )

    def update(self, dt: float) -> None:
        for particle in self.items:
            particle.life -= dt
            particle.x += particle.vx * dt
            particle.y += particle.vy * dt
            particle.vy += 260.0 * dt
        self.items = [particle for particle in self.items if particle.life > 0.0]

    def draw(self, surface: pygame.Surface) -> None:
        for particle in self.items:
            alpha = max(0.0, min(1.0, particle.life / particle.max_life))
            radius = max(1, round(particle.radius * (0.5 + alpha * 0.5)))
            pygame.draw.circle(
                surface,
                particle.color,
                (round(particle.x), round(particle.y)),
                radius,
            )
