"""Lina's Q air wave."""

from __future__ import annotations

import math

import pygame

from .combat import resolve_projectile_hit
from .config import AXE_SPRITE_PATH
from .fx import (
    LINA_Q_SPECS,
    Q_WAVE_DRAW_OFFSET_Y,
    strip_frame,
    web_sprite,
)


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
        self.age = 0.0
        self.visual_kind = "lina_q_flame" if flame else "lina_q"
        self.hit_color = (255, 150, 90) if flame else (80, 230, 225)
        self.alive = True
        self.hit = False
        self.rect = pygame.Rect(0, 0, 44, 34)
        self.rect.center = (round(self.x), round(self.y))

    def update(self, dt: float, scene) -> None:
        if not self.alive:
            return
        self.age += dt
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

        if not self.hit:
            for target in scene.targets_for(self.owner):
                if target.hp > 0.0 and self.rect.colliderect(target.hurtbox()):
                    self.hit = True
                    self.target = target
                    resolve_projectile_hit(scene, self)
                    self.alive = False
                    break

    def draw(self, surface: pygame.Surface) -> None:
        spec = LINA_Q_SPECS["flame" if self.flame else "normal"]
        frame = strip_frame(spec, self.age, self.direction)
        if frame is None:
            return
        anchor_x = (
            spec.anchor[0]
            if self.direction >= 0
            else spec.frame_size[0] - spec.anchor[0]
        )
        surface.blit(
            frame,
            (
                round(self.x - anchor_x),
                round(self.y + Q_WAVE_DRAW_OFFSET_Y - spec.anchor[1]),
            ),
        )


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


class SwordWave:
    """Legacy Nyra sword-wave projectile; unused by current attack data."""

    kind = "sword_wave"

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
        self.flame_bonus = 0.0
        self.alive = True
        self.hit = False
        self.rect = pygame.Rect(0, 0, 70, 48)
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

        low, high = scene.stage.walls
        if self.x <= low or self.x >= high:
            self.alive = False
            return

        if scene.stage.blocks_enabled:
            for block in scene.stage.blocks:
                if self.rect.colliderect(block):
                    self.alive = False
                    return

        if not self.hit:
            for target in scene.targets_for(self.owner):
                if target.hp > 0.0 and self.rect.colliderect(target.hurtbox()):
                    self.hit = True
                    self.target = target
                    resolve_projectile_hit(scene, self)
                    self.alive = False
                    break

    def draw(self, surface: pygame.Surface) -> None:
        size = 104
        wave = pygame.Surface((size, size), pygame.SRCALPHA)
        center = size // 2
        trail_direction = -self.direction
        for index in range(4):
            offset = (index + 1) * 8
            alpha = max(0, 150 - index * 34)
            pygame.draw.circle(
                wave,
                (120, 200, 255, alpha),
                (center + trail_direction * offset, center),
                max(2, 12 - index * 2),
            )
        arc_rect = pygame.Rect(center - 30, center - 38, 60, 76)
        if self.direction < 0:
            start, stop = 0.35, 1.35
        else:
            start, stop = -1.35, -0.35
        pygame.draw.arc(wave, (190, 235, 255, 235), arc_rect, start, stop, 8)
        pygame.draw.arc(wave, (245, 255, 255, 210), arc_rect.inflate(-10, -10), start, stop, 3)
        surface.blit(wave, (round(self.x - size * 0.5), round(self.y - size * 0.5)))


class AimedProjectile:
    """Veno's straight-line venom glob / web bolt.

    The direction is fixed at fire time; it does not home. ``direction`` is
    the horizontal sign used by ``resolve_projectile_hit`` for knockback.
    """

    def __init__(
        self,
        owner,
        target,
        x: float,
        y: float,
        vx: float,
        vy: float,
        max_range: float,
        damage: float,
        knockback: float,
        hitstun: float,
        hitstop: float,
        kind: str = "venom_glob",
        radius: float = 14.0,
        status: str | None = None,
        status_duration: float = 0.0,
        status_dps_pct: float = 0.0,
    ) -> None:
        self.owner = owner
        self.target = target
        self.x = float(x)
        self.y = float(y)
        speed = math.hypot(vx, vy)
        if speed < 1e-6:
            vx, vy, speed = 1.0, 0.0, 1.0
        self.ux = float(vx) / speed
        self.uy = float(vy) / speed
        self.speed = float(speed)
        self.direction = 1 if vx >= 0.0 else -1
        self.max_range = float(max_range)
        self.traveled = 0.0
        self.damage = float(damage)
        self.knockback = float(knockback)
        self.hitstun = float(hitstun)
        self.hitstop = float(hitstop)
        self.flame_bonus = 0.0
        self.kind = kind
        self.radius = float(radius)
        self.age = 0.0
        self.visual_kind = "veno_poison" if kind == "venom_glob" else "veno_web"
        self.hit_color = (
            (65, 170, 75) if kind == "venom_glob" else (200, 240, 170)
        )
        self.status = status
        self.status_duration = float(status_duration)
        self.status_dps_pct = float(status_dps_pct)
        self.alive = True
        self.hit = False
        self.rect = pygame.Rect(0, 0, round(radius * 2), round(radius * 2))
        self.rect.center = (round(self.x), round(self.y))

    def update(self, dt: float, scene) -> None:
        if not self.alive:
            return
        self.age += dt
        step = self.speed * dt
        self.x += self.ux * step
        self.y += self.uy * step
        self.traveled += step
        self.rect.center = (round(self.x), round(self.y))

        if self.traveled >= self.max_range:
            self.alive = False
            return

        low, high = scene.stage.walls
        if self.rect.right <= low or self.rect.left >= high:
            self.alive = False
            return
        if self.y >= scene.stage.ground_y:
            self.alive = False
            return

        if scene.stage.blocks_enabled:
            for block in scene.stage.blocks:
                if self.rect.colliderect(block):
                    self.alive = False
                    return

        if not self.hit:
            for target in scene.targets_for(self.owner):
                if target.hp > 0.0 and self.rect.colliderect(target.hurtbox()):
                    self.hit = True
                    self.target = target
                    resolve_projectile_hit(scene, self)
                    self.alive = False
                    break

    def draw(self, surface: pygame.Surface) -> None:
        if self.kind == "web_bolt":
            self._draw_web(surface)
        else:
            self._draw_venom(surface)

    def _draw_venom(self, surface: pygame.Surface) -> None:
        radius = max(4, round(self.radius))
        size = radius * 4 + 24
        image = pygame.Surface((size, size), pygame.SRCALPHA)
        center = size // 2

        # Droplets trail in the direction opposite to travel.
        for index in range(4):
            distance = 10.0 + index * 8.0
            tx = center - self.ux * distance
            ty = center - self.uy * distance
            alpha = max(20, 150 - index * 32)
            pygame.draw.circle(
                image, (50, 140, 65, alpha),
                (round(tx), round(ty)), max(1, 6 - index),
            )

        pygame.draw.circle(image, (16, 72, 34, 220), (center, center), radius)
        pygame.draw.circle(image, (42, 138, 60, 225), (center, center), radius - 3)
        pygame.draw.circle(
            image, (75, 170, 85, 130), (center, center), radius, 1
        )
        pygame.draw.circle(
            image, (120, 210, 120, 235),
            (center - 4, center - 5), max(2, radius // 3),
        )
        for index in range(4):
            angle = self.age * 3.0 + index * math.tau / 4.0
            bx = center + math.cos(angle) * radius * 0.45
            by = center + math.sin(angle) * radius * 0.35
            pygame.draw.circle(
                image, (90, 185, 95, 200),
                (round(bx), round(by)), max(1, radius // 5),
            )
        surface.blit(
            image, (round(self.x - center), round(self.y - center))
        )

    def _draw_web(self, surface: pygame.Surface) -> None:
        pad = 64
        trail = pygame.Surface((pad * 2, pad * 2), pygame.SRCALPHA)
        center = pad
        perp_x, perp_y = -self.uy, self.ux
        for index in range(2):
            width = 2 if index == 0 else 1
            color = (
                (100, 165, 90, 185) if index == 0 else (235, 255, 215, 225)
            )
            points: list[tuple[int, int]] = []
            for step in range(5):
                t = step / 4.0
                distance = 8.0 + 44.0 * t
                offset = (
                    math.sin(self.age * 8.0 + t * 3.0 + index * 1.7)
                    * 2.5 * t
                )
                points.append(
                    (
                        round(center - self.ux * distance + perp_x * offset),
                        round(center - self.uy * distance + perp_y * offset),
                    )
                )
            pygame.draw.lines(trail, color, False, points, width)
        surface.blit(trail, (round(self.x - center), round(self.y - center)))

        sprite = web_sprite(
            64, self.age * 55.0 * (1 if self.direction > 0 else -1)
        )
        if sprite is not None:
            glow = pygame.Surface((112, 112), pygame.SRCALPHA)
            pygame.draw.circle(glow, (200, 255, 170, 35), (56, 56), 50)
            pygame.draw.circle(glow, (235, 255, 210, 55), (56, 56), 30)
            surface.blit(glow, (round(self.x - 56), round(self.y - 56)))
            surface.blit(
                sprite, sprite.get_rect(center=(round(self.x), round(self.y)))
            )
            return
        self._draw_web_fallback(surface)

    def _draw_web_fallback(self, surface: pygame.Surface) -> None:
        radius = max(4, round(self.radius))
        size = radius * 4
        image = pygame.Surface((size, size), pygame.SRCALPHA)
        center = size // 2
        pygame.draw.circle(image, (225, 232, 240, 70), (center, center), radius)
        pygame.draw.circle(image, (235, 242, 250, 220), (center, center), radius, 2)
        for index in range(6):
            angle = index * math.pi / 3.0
            end_x = center + math.cos(angle) * radius
            end_y = center + math.sin(angle) * radius
            pygame.draw.line(
                image, (210, 220, 235, 190),
                (center, center), (end_x, end_y), 1,
            )
        pygame.draw.line(
            image, (245, 250, 255, 200),
            (center - radius * 0.7, center), (center + radius * 0.7, center), 1,
        )
        surface.blit(image, (round(self.x - size * 0.5), round(self.y - size * 0.5)))


class SonicWave:
    """Bat's sonic wave: fly out, bounce, return to the owner, hit once.

    The wave is deliberately not an AimedProjectile: it must pass through
    the player on the return trip, home on the owner's current position and
    carry its own ``bat_sonic`` visual kind.
    """

    kind = "sonic_wave"

    def __init__(
        self,
        owner,
        target,
        x: float,
        y: float,
        ux: float,
        uy: float,
        speed: float,
        max_range: float,
        damage: float,
        knockback: float,
        hitstun: float,
        hitstop: float,
        status: str | None = None,
        status_duration: float = 0.0,
        radius: float = 18.0,
        return_height: float = 30.0,
        hitbox_forward: float = 8.0,
        hitbox_radius: float = 24.0,
    ) -> None:
        length = math.hypot(ux, uy)
        if length < 1e-6:
            ux, uy, length = 1.0, 0.0, 1.0
        self.owner = owner
        self.target = target
        self.x = float(x)
        self.y = float(y)
        self.ux = ux / length
        self.uy = uy / length
        self.speed = float(speed)
        self.max_range = float(max_range)
        self.traveled = 0.0
        self.damage = float(damage)
        self.knockback = float(knockback)
        self.hitstun = float(hitstun)
        self.hitstop = float(hitstop)
        self.status = status
        self.status_duration = float(status_duration)
        self.radius = float(radius)
        self.return_height = float(return_height)
        self.hitbox_forward = float(hitbox_forward)
        self.hitbox_radius = float(hitbox_radius)
        # dir_* is the current travel direction: fixed while outbound, then
        # re-aimed at the owner on the return leg so the arcs and hitbox both
        # point where the wave is actually going.
        self.dir_x = self.ux
        self.dir_y = self.uy
        self.direction = 1 if self.ux >= 0.0 else -1
        self.visual_kind = "bat_sonic"
        self.hit_color = (210, 190, 255)
        self.flame_bonus = 0.0
        self.phase = "out"
        self.hit_out = False
        self.hit_return = False
        self.age = 0.0
        self.timeout = 8.0
        self.owner_dead_time = 0.0
        self.alive = True
        self._sync_rect()

    def hitbox_center(self) -> tuple[float, float]:
        """Circle centre, pushed forward along the current travel direction."""
        return (
            self.x + self.dir_x * self.hitbox_forward,
            self.y + self.dir_y * self.hitbox_forward,
        )

    @staticmethod
    def _circle_hits_rect(
        cx: float,
        cy: float,
        radius: float,
        rect: pygame.Rect,
    ) -> bool:
        nearest_x = max(float(rect.left), min(float(rect.right), cx))
        nearest_y = max(float(rect.top), min(float(rect.bottom), cy))
        dx = cx - nearest_x
        dy = cy - nearest_y
        return dx * dx + dy * dy <= radius * radius

    def hitbox_hits(self, rect: pygame.Rect) -> bool:
        cx, cy = self.hitbox_center()
        return self._circle_hits_rect(cx, cy, self.hitbox_radius, rect)

    def _sync_rect(self) -> None:
        cx, cy = self.hitbox_center()
        size = max(1, round(self.hitbox_radius * 2))
        self.rect = pygame.Rect(
            round(cx - self.hitbox_radius),
            round(cy - self.hitbox_radius),
            size,
            size,
        )

    def _to_return(self) -> None:
        self.phase = "return"

    def _overlapping_target(self, scene):
        for target in scene.targets_for(self.owner):
            if target.hp > 0.0 and self.hitbox_hits(target.hurtbox()):
                return target
        return None

    def _push_hitbox_out_of_block(self, block: pygame.Rect) -> None:
        """Leave the block volume after an outbound bounce."""
        cx, cy = self.hitbox_center()
        radius = self.hitbox_radius
        left = block.left - radius - cx
        right = block.right + radius - cx
        top = block.top - radius - cy
        bottom = block.bottom + radius - cy
        dx = left if abs(left) <= abs(right) else right
        dy = top if abs(top) <= abs(bottom) else bottom
        if abs(dx) <= abs(dy):
            self.x += dx
        else:
            self.y += dy
        self._sync_rect()

    def update(self, dt: float, scene) -> None:
        if not self.alive:
            return
        self.age += dt
        if self.age > self.timeout:
            self.alive = False
            return
        if self.owner.hp <= 0.0:
            self.owner_dead_time += dt
            if self.owner_dead_time >= 0.5:
                self.alive = False
                return

        step = self.speed * dt
        if self.phase == "out":
            self.dir_x, self.dir_y = self.ux, self.uy
            self.x += self.ux * step
            self.y += self.uy * step
            self.traveled += step
            self._sync_rect()

            if self.traveled >= self.max_range:
                self._to_return()
                return

            low, high = scene.stage.walls
            hx, hy = self.hitbox_center()
            radius = self.hitbox_radius
            bounced = False
            if hx - radius <= low:
                hx = low + radius
                bounced = True
            elif hx + radius >= high:
                hx = high - radius
                bounced = True
            if hy - radius <= 0.0:
                hy = radius
                bounced = True
            elif hy + radius >= scene.stage.ground_y:
                hy = scene.stage.ground_y - radius
                bounced = True
            if bounced:
                self.x = hx - self.dir_x * self.hitbox_forward
                self.y = hy - self.dir_y * self.hitbox_forward
                self._sync_rect()
                self._to_return()
                return

            if scene.stage.blocks_enabled:
                for block in scene.stage.blocks:
                    if self._circle_hits_rect(hx, hy, radius, block):
                        self._push_hitbox_out_of_block(block)
                        self._to_return()
                        return

            if not self.hit_out:
                target = self._overlapping_target(scene)
                if target is not None:
                    self.target = target
                    self.hit_out = True
                    # The outbound hit must also latch the return guard:
                    # otherwise the wave would settle inside the player's
                    # hurtbox for a tick and deal 24 damage twice.
                    self.hit_return = True
                    resolve_projectile_hit(scene, self)
                    self._to_return()
            return

        # Return to the owner's current position (not the launch point).
        target_x = float(self.owner.x)
        target_y = float(self.owner.y) - self.return_height
        dx = target_x - self.x
        dy = target_y - self.y
        distance = math.hypot(dx, dy)
        if distance > 1e-6:
            self.dir_x = dx / distance
            self.dir_y = dy / distance
            self._sync_rect()
        if distance <= max(step, 16.0):
            self.x = target_x
            self.y = target_y
            self.alive = False
            return
        self.x += dx / distance * step
        self.y += dy / distance * step
        self._sync_rect()

        low, high = scene.stage.walls
        hx, hy = self.hitbox_center()
        radius = self.hitbox_radius
        hx = max(low + radius, min(high - radius, hx))
        hy = max(radius, min(scene.stage.ground_y - radius, hy))
        self.x = hx - self.dir_x * self.hitbox_forward
        self.y = hy - self.dir_y * self.hitbox_forward
        self._sync_rect()

        if scene.stage.blocks_enabled:
            for block in scene.stage.blocks:
                if self._circle_hits_rect(hx, hy, radius, block):
                    # A block on the way home absorbs the wave instead of
                    # trapping it in a bounce loop.
                    self.alive = False
                    return

        if not self.hit_return:
            target = self._overlapping_target(scene)
            if target is not None:
                self.target = target
                self.hit_return = True
                resolve_projectile_hit(scene, self)
                # Pass through the player and keep returning to the owner.

    def draw(self, surface: pygame.Surface) -> None:
        # --- old ring/arc version, kept for approval ---
        # radius = max(8.0, self.radius)
        # pulse = math.sin(self.age * 26.0) * 2.0
        # pad = round(radius * 2.4 + 14)
        # size = pad * 2
        # image = pygame.Surface((size, size), pygame.SRCALPHA)
        # center = pad
        #
        # for index in range(3):
        #     distance = 10.0 + index * 9.0
        #     tx = center - self.ux * distance
        #     ty = center - self.uy * distance
        #     alpha = max(20, 95 - index * 24)
        #     pygame.draw.circle(
        #         image, (210, 190, 255, alpha),
        #         (round(tx), round(ty)), max(1, 6 - index * 2), 1,
        #     )
        #
        # rings = (
        #     (1.0, (245, 235, 255, 215), 2),
        #     (0.72, (210, 190, 255, 180), 1),
        #     (0.45, (245, 235, 255, 150), 1),
        # )
        # for index, (scale, color, width) in enumerate(rings):
        #     rr = max(2, round(radius * scale + pulse * (index + 1) * 0.35))
        #     pygame.draw.circle(image, color, (center, center), rr, width)
        #
        # angle = math.atan2(self.uy, self.ux)
        # for offset in (-0.62, 0.0, 0.62):
        #     arc_radius = max(3, round(radius * 1.12 + pulse))
        #     box = pygame.Rect(
        #         center - arc_radius,
        #         center - arc_radius,
        #         arc_radius * 2,
        #         arc_radius * 2,
        #     )
        #     pygame.draw.arc(
        #         image, (245, 235, 255, 190), box,
        #         angle - 0.72 + offset, angle + 0.72 + offset, 2,
        #     )
        #
        # pygame.draw.circle(
        #     image, (245, 235, 255, 235),
        #     (center, center), max(2, round(radius * 0.28)),
        # )
        # pygame.draw.circle(
        #     image, (210, 190, 255, 120),
        #     (center, center), max(3, round(radius * 0.55)), 1,
        # )
        # surface.blit(
        #     image,
        #     (round(self.x - center), round(self.y - center)),
        # )

        # --- ultrasonic waveform version, kept for approval ---
        # # --- ultrasonic waveform version ---
        # # A short oscilloscope packet aligned with the travel direction. The
        # # wavefront bar at the head keeps the projectile readable at speed.
        # radius = max(8.0, self.radius)
        # length = radius * 3.0
        # amplitude = radius * 0.52
        # pad = round(length * 0.5 + amplitude + 18)
        # size = pad * 2
        # image = pygame.Surface((size, size), pygame.SRCALPHA)
        # center = pad
        # phase = self.age * 30.0
        # cycles = 2.6
        # samples = 29
        #
        # # forward = travel direction; side = perpendicular to it.
        # fx, fy = self.ux, self.uy
        # sx, sy = -self.uy, self.ux
        #
        # def point(
        #     u: float,
        #     side_offset: float,
        #     phase_offset: float,
        # ) -> tuple[int, int]:
        #     along = (u - 0.5) * length
        #     envelope = math.sin(math.pi * u) ** 0.75
        #     wave = math.sin(math.tau * cycles * u - phase + phase_offset)
        #     offset = side_offset + amplitude * envelope * wave
        #     return (
        #         round(center + fx * along + sx * offset),
        #         round(center + fy * along + sy * offset),
        #     )
        #
        # for side_offset, phase_offset, glow_color, glow_width, color, width in (
        #     (
        #         radius * 0.38, 1.4,
        #         (150, 120, 235, 55), 6, (200, 180, 255, 120), 2,
        #     ),
        #     (
        #         0.0, 0.0,
        #         (180, 150, 255, 70), 7, (245, 238, 255, 235), 2,
        #     ),
        # ):
        #     points = [
        #         point(index / (samples - 1), side_offset, phase_offset)
        #         for index in range(samples)
        #     ]
        #     pygame.draw.lines(image, glow_color, False, points, glow_width)
        #     pygame.draw.lines(image, color, False, points, width)
        #
        # # Bright leading wavefront, perpendicular to travel.
        # head_x = center + fx * length * 0.5
        # head_y = center + fy * length * 0.5
        # half = radius * 0.55
        # pygame.draw.line(
        #     image, (190, 165, 255, 120),
        #     (round(head_x - sx * half), round(head_y - sy * half)),
        #     (round(head_x + sx * half), round(head_y + sy * half)),
        #     5,
        # )
        # pygame.draw.line(
        #     image, (252, 248, 255, 235),
        #     (round(head_x - sx * half), round(head_y - sy * half)),
        #     (round(head_x + sx * half), round(head_y + sy * half)),
        #     2,
        # )
        #
        # # Fading droplets behind the packet.
        # for index in range(3):
        #     distance = length * (0.18 + index * 0.16)
        #     tx = center - fx * distance
        #     ty = center - fy * distance
        #     alpha = max(20, 110 - index * 30)
        #     pygame.draw.circle(
        #         image, (210, 190, 255, alpha),
        #         (round(tx), round(ty)), max(1, 4 - index), 1,
        #     )
        #
        # # Bright core at the wave center.
        # pygame.draw.circle(
        #     image, (180, 155, 255, 90),
        #     (center, center), max(2, round(radius * 0.22)),
        # )
        # pygame.draw.circle(
        #     image, (250, 245, 255, 220),
        #     (center, center), max(1, round(radius * 0.12)),
        # )
        #
        # surface.blit(
        #     image,
        #     (round(self.x - center), round(self.y - center)),
        # )

        # --- wifi-signal waveform version ---
        # Three nested arcs open toward the travel direction, with a bright
        # emitter dot at the centre: the classic signal-wave silhouette.
        radius = max(8.0, self.radius)
        pad = round(radius * 2.1 + 16)
        size = pad * 2
        image = pygame.Surface((size, size), pygame.SRCALPHA)
        center = pad
        # pygame.draw.arc measures angles with screen y treated as up, so
        # negate the vertical component to open the arc in the real travel
        # direction. dir_* follows the return leg as well.
        angle = math.atan2(-self.dir_y, self.dir_x)
        spread = 0.95
        pulse = math.sin(self.age * 18.0) * 1.5

        # Soft bloom behind the emitter.
        pygame.draw.circle(
            image, (150, 120, 235, 55),
            (center, center), max(4, round(radius * 0.9)),
        )

        # Near -> far arcs: white in front, lavender/purple behind.
        arcs = (
            (radius * 0.55, (252, 248, 255, 235), 3),
            (radius * 1.05, (235, 225, 255, 190), 3),
            (radius * 1.55, (200, 175, 255, 140), 2),
        )
        for arc_radius, color, width in arcs:
            rr = max(2, round(arc_radius + pulse))
            box = pygame.Rect(
                center - rr,
                center - rr,
                rr * 2,
                rr * 2,
            )
            pygame.draw.arc(
                image, color, box,
                angle - spread, angle + spread, width,
            )

        # Emitter dot at the source of the signal.
        pygame.draw.circle(
            image, (170, 145, 255, 170),
            (center, center), max(3, round(radius * 0.34)),
        )
        pygame.draw.circle(
            image, (252, 248, 255, 245),
            (center, center), max(2, round(radius * 0.2)),
        )

        # Short trail behind the emitter sells the forward motion.
        for index in range(2):
            distance = radius * (0.7 + index * 0.55)
            tx = center - self.dir_x * distance
            ty = center - self.dir_y * distance
            alpha = max(20, 85 - index * 30)
            pygame.draw.circle(
                image, (210, 190, 255, alpha),
                (round(tx), round(ty)), max(1, 3 - index), 1,
            )

        surface.blit(
            image,
            (round(self.x - center), round(self.y - center)),
        )
