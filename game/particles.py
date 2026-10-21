"""Small debug-friendly particle system for flame, hit and knock-up feedback."""

from __future__ import annotations

import math
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


def knock_up_vortex_intensity(progress: float, cfg: dict) -> tuple[float, float]:
    """Return (scale, alpha) for a knock-up vortex at ``progress``.

    The effect keeps a minimum visible size/alpha until the status ends, so it
    does not fade to nothing before the 1.5s window is over.
    """
    progress = max(0.0, min(1.0, progress))
    alpha_max = max(0.0, min(1.0, float(cfg.get("alpha", 0.95))))
    min_alpha = max(0.0, min(1.0, float(cfg.get("min_alpha", 0.55))))
    min_scale = max(0.0, min(1.0, float(cfg.get("min_scale", 0.75))))
    scale = min_scale + (1.0 - min_scale) * progress
    alpha = alpha_max * (min_alpha + (1.0 - min_alpha) * progress)
    return scale, alpha


def draw_knock_up_vortex(
    surface: pygame.Surface,
    x: float,
    y: float,
    progress: float,
    phase: float,
    cfg: dict,
) -> None:
    """Draw a cyan-white spiral vortex at a fighter's feet.

    ``progress`` runs from 1 at the start of knock_up to 0 at the end. The
    whole effect is draw-only: it never touches fighter state or animation.
    """
    progress = max(0.0, min(1.0, progress))
    if progress <= 0.0:
        return

    radius_x = float(cfg.get("radius_x", 28.0))
    radius_y = float(cfg.get("radius_y", 10.0))
    arms = max(1, int(cfg.get("arms", 3)))
    thickness = max(1, int(cfg.get("thickness", 2)))
    color = tuple(int(channel) for channel in cfg.get("color", (190, 240, 255)))
    core_color = tuple(int(channel) for channel in cfg.get("core_color", (245, 255, 255)))
    scale, alpha_value = knock_up_vortex_intensity(progress, cfg)

    rx = radius_x * scale
    ry = radius_y * scale
    pad = thickness + 4
    width = max(1, round(rx * 2.0 + pad * 2))
    height = max(1, round(ry * 2.0 + pad * 2))
    layer = pygame.Surface((width, height), pygame.SRCALPHA)
    cx = width * 0.5
    cy = height * 0.5
    alpha = max(0, min(255, round(255 * alpha_value)))

    pygame.draw.ellipse(
        layer,
        (*color, round(alpha * 0.68)),
        pygame.Rect(
            round(cx - rx), round(cy - ry),
            max(1, round(rx * 2.0)), max(1, round(ry * 2.0)),
        ),
        thickness,
    )

    segments = 14
    for arm in range(arms):
        base = phase + arm * (math.tau / arms)
        points: list[tuple[float, float]] = []
        for step in range(segments + 1):
            t = 0.18 + 0.82 * step / segments
            angle = base + t * math.tau
            points.append((cx + math.cos(angle) * rx * t, cy + math.sin(angle) * ry * t))
        for step, (first, second) in enumerate(zip(points, points[1:])):
            fade = 0.45 + 0.55 * (step + 1) / segments
            pygame.draw.line(
                layer,
                (*color, max(0, min(255, round(alpha * fade)))),
                (round(first[0]), round(first[1])),
                (round(second[0]), round(second[1])),
                max(1, round(thickness * (0.6 + 0.4 * (step + 1) / segments))),
            )

    pygame.draw.ellipse(
        layer,
        (*core_color, round(alpha * 0.35)),
        pygame.Rect(
            round(cx - rx * 0.22), round(cy - ry * 0.22),
            max(1, round(rx * 0.44)), max(1, round(ry * 0.44)),
        ),
    )

    surface.blit(layer, (round(x - cx), round(y - 2.0 - cy)))
