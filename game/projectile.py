"""Lina's Q air wave."""

from __future__ import annotations

import pygame

from .combat import resolve_projectile_hit
from .config import AXE_SPRITE_PATH


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


class AxeThrow:
    """Warrior's returning axe: high lane, one hit out and one hit back."""

    kind = "axe_throw"

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
        sprite_path=None,
    ) -> None:
        self.owner = owner
        self.target = target
        self.x = float(x)
        self.y = float(y)
        self.spawn_x = float(x)
        self.direction = 1 if direction >= 0 else -1
        self.speed = float(speed)
        self.max_range = float(max_range)
        self.damage = float(damage)
        self.knockback = float(knockback)
        self.hitstun = float(hitstun)
        self.hitstop = float(hitstop)
        self.flame_bonus = 0.0
        self.phase = "out"
        self.hit_out = False
        self.hit_return = False
        self.alive = True
        self.spin = 0.0
        self.sprite_path = sprite_path or AXE_SPRITE_PATH
        self._sprite: pygame.Surface | None = None
        self.rect = pygame.Rect(0, 0, 100, 80)
        self.rect.center = (round(self.x), round(self.y))

    def _sync_rect(self) -> None:
        self.rect.center = (round(self.x), round(self.y))

    def _overlaps_target(self) -> bool:
        return (
            self.target is not None
            and self.target.hp > 0.0
            and self.rect.colliderect(self.target.hurtbox())
        )

    def update(self, dt: float, scene) -> None:
        if not self.alive:
            return
        self.spin = (self.spin + 720.0 * dt) % 360.0
        step = self.speed * dt

        if self.phase == "out":
            self.x += step * self.direction
            self._sync_rect()
            if not self.hit_out and self._overlaps_target():
                self.hit_out = True
                resolve_projectile_hit(scene, self)
            low, high = scene.stage.walls
            if (
                abs(self.x - self.spawn_x) >= self.max_range
                or self.x <= low
                or self.x >= high
            ):
                self.phase = "return"
                self.direction = -self.direction
            return

        # Return to the Warrior's hand. The lane follows his current feet, so
        # throwing from a block keeps the whole return path 60px higher.
        owner_x = self.owner.x
        dx = owner_x - self.x
        if abs(dx) <= step:
            self.x = owner_x
            self.alive = False
            return
        self.x += step if dx > 0 else -step
        self.y = scene.stage.lane_y("high", self.owner.y)
        self._sync_rect()
        if not self.hit_return and self._overlaps_target():
            self.hit_return = True
            resolve_projectile_hit(scene, self)

    def draw(self, surface: pygame.Surface) -> None:
        if self._sprite is None:
            self._sprite = self._load_sprite()
        image = pygame.transform.rotate(self._sprite, self.spin)
        surface.blit(
            image,
            image.get_rect(center=(round(self.x), round(self.y))),
        )

    def _load_sprite(self) -> pygame.Surface:
        try:
            image = pygame.image.load(str(self.sprite_path)).convert_alpha()
            scale = 220.0 / max(image.get_width(), image.get_height())
            size = (
                max(1, round(image.get_width() * scale)),
                max(1, round(image.get_height() * scale)),
            )
            return pygame.transform.smoothscale(image, size)
        except (pygame.error, FileNotFoundError):
            return self._fallback_sprite()

    @staticmethod
    def _fallback_sprite() -> pygame.Surface:
        size = 160
        image = pygame.Surface((size, size), pygame.SRCALPHA)
        center = size // 2
        pygame.draw.line(
            image, (90, 60, 40),
            (center - 55, center), (center + 45, center), 10,
        )
        pygame.draw.circle(image, (190, 195, 210), (center + 35, center), 42)
        pygame.draw.circle(image, (120, 80, 40), (center + 35, center), 30)
        return image
