"""Persistent skill hazards: falling ice, ice spikes and poison zones.

Hazards are duck-typed like projectiles: ``alive``, ``behind``,
``update(dt, scene)`` and ``draw(surface)``. ``ArenaScene.tick`` advances
them after projectiles; ``ArenaScene.draw`` renders them in two passes.
"""

from __future__ import annotations

import math

import pygame

from .combat import apply_direct_damage, attack_damage
from .config import ASSETS_DIR
from .fx import SpriteStripFx


EIRA_FX_DIR = ASSETS_DIR / "frames" / "eira" / "fx"
WITCH_FX_DIR = ASSETS_DIR / "frames" / "crooked_witch" / "fx"

_IMAGE_CACHE: dict[tuple[str, float, float], pygame.Surface | None] = {}


def _image(path, scale: float = 1.0) -> pygame.Surface | None:
    try:
        mtime = path.stat().st_mtime
    except OSError:
        return None
    key = (str(path), mtime, round(scale, 4))
    if key in _IMAGE_CACHE:
        cached = _IMAGE_CACHE[key]
        return cached.copy() if cached is not None else None
    try:
        image = pygame.image.load(str(path)).convert_alpha()
    except (OSError, pygame.error):
        _IMAGE_CACHE[key] = None
        return None
    if abs(scale - 1.0) > 1e-6:
        image = pygame.transform.smoothscale(
            image,
            (
                max(1, round(image.get_width() * scale)),
                max(1, round(image.get_height() * scale)),
            ),
        )
    _IMAGE_CACHE[key] = image
    return image.copy()


def _circle_hits_rect(cx: float, cy: float, radius: float, rect: pygame.Rect) -> bool:
    nearest_x = max(rect.left, min(cx, rect.right))
    nearest_y = max(rect.top, min(cy, rect.bottom))
    return math.hypot(cx - nearest_x, cy - nearest_y) <= radius


class IceBallHazard:
    """Eira's E ice ball: falls through blocks, hits each target once."""

    behind = False

    def __init__(
        self,
        owner,
        x: float,
        ground_y: float,
        radius: float,
        fall_speed: float,
        attack_data: dict,
        freeze_gain: float,
    ) -> None:
        self.owner = owner
        self.x = float(x)
        self.y = -120.0
        self.ground_y = float(ground_y)
        self.radius = float(radius)
        self.fall_speed = float(fall_speed)
        self.attack_data = dict(attack_data)
        self.freeze_gain = float(freeze_gain)
        self.age = 0.0
        self.landed = False
        self.land_time = 0.0
        self.alive = True
        self.hit_ids: set[int] = set()

    def _hit_fx(self, scene, target, was_frozen: bool) -> None:
        prefix = "eira_e_release_v1_fx_frozen_hit" if was_frozen else "eira_e_release_v1_fx_hit"
        frames = [EIRA_FX_DIR / f"{prefix}_{index:02d}.png" for index in range(3)]
        y = target.y - target.hurtbox_dims[1] * 0.5
        scene.fx_effects.append(
            SpriteStripFx(
                frames, [0.05, 0.07, 0.10], target.x, y,
                scale=0.55, kind="eira_ice_ball_hit",
            )
        )
        color = (160, 225, 255) if not was_frozen else (210, 245, 255)
        scene.particles.emit_burst(target.x, y, color, 6, speed=170.0)

    def update(self, dt: float, scene) -> None:
        if not self.alive:
            return
        self.age += dt
        if self.landed:
            self.land_time += dt
            if self.land_time >= 3.0:
                self.alive = False
            return

        self.y += self.fall_speed * dt
        for target in scene.targets_for(self.owner):
            if target.hp <= 0.0 or id(target) in self.hit_ids:
                continue
            if _circle_hits_rect(self.x, self.y, self.radius, target.hurtbox()):
                self.hit_ids.add(id(target))
                was_frozen = target.statuses.has("freeze")
                damage = attack_damage(self.owner, self.attack_data)
                if was_frozen:
                    damage += self.owner.atk * float(
                        self.attack_data.get("bonus_vs_frozen_atk_mult", 0.0)
                    )
                    damage += self.owner.extra_atk * float(
                        self.attack_data.get("bonus_vs_frozen_extra_mult", 0.0)
                    )
                apply_direct_damage(
                    scene, self.owner, target, damage,
                    hitstun=float(self.attack_data.get("hitstun", 0.2)),
                    hitstop=float(self.attack_data.get("hitstop", 0.06)),
                )
                apply_freeze = getattr(self.owner, "apply_freeze", None)
                if apply_freeze is not None:
                    apply_freeze(target, self.freeze_gain)
                self._hit_fx(scene, target, was_frozen)

        if self.y >= self.ground_y:
            self.y = self.ground_y
            self.landed = True
            self._ground_fx(scene)

    def _ground_fx(self, scene) -> None:
        frames = [
            EIRA_FX_DIR / f"eira_e_release_v1_fx_ground_{index:02d}.png"
            for index in range(4)
        ]
        scene.fx_effects.append(
            SpriteStripFx(
                frames, [0.05, 0.07, 0.09, 0.12], self.x, self.ground_y,
                scale=0.55, kind="eira_ice_ball_ground",
            )
        )
        scene.particles.emit_burst(
            self.x, self.ground_y - 20.0, (190, 235, 255), 12, speed=240.0
        )

    def draw(self, surface: pygame.Surface) -> None:
        if self.landed:
            self._draw_ground(surface)
            return
        self._draw_ball(surface)

    def _draw_ball(self, surface: pygame.Surface) -> None:
        scale = max(0.2, (self.radius * 2.0) / 438.0)
        image = _image(EIRA_FX_DIR / "eira_e_release_v4_fx_ball.png", scale)
        if image is not None:
            trail_scale = 1.00
            trail = _image(
                EIRA_FX_DIR / "eira_e_release_v1_fx_fall_trail.png",
                trail_scale,
            )
            if trail is not None:
                surface.blit(
                    trail,
                    (
                        round(self.x - 160.0 * trail_scale),
                        round(self.y - 302.0 * trail_scale),
                    ),
                )
            surface.blit(
                image, image.get_rect(center=(round(self.x), round(self.y)))
            )
            return
        pygame.draw.circle(
            surface, (170, 225, 255), (round(self.x), round(self.y)),
            round(self.radius),
        )
        pygame.draw.circle(
            surface, (225, 248, 255), (round(self.x - 12), round(self.y - 12)),
            max(4, round(self.radius * 0.45)),
        )

    def _draw_ground(self, surface: pygame.Surface) -> None:
        """Four separate chunks spread outward, per the v2 manifest.

        ``chunk_00..03`` are individual pieces (upper left, upper right,
        lower left, lower right), not an animation sequence. The intact
        ball is shown for the 60ms crack, then all four pieces settle over
        740ms and remain for the 3s fragment lifetime.
        """
        settle = min(1.0, max(0.0, self.land_time / 0.74))
        ease = 1.0 - (1.0 - settle) ** 2
        arc = 4.0 * settle * (1.0 - settle)
        fade = min(1.0, max(0.0, (3.0 - self.land_time) / 0.5))
        if fade <= 0.0:
            return
        pieces = (
            (-190.0, 0.0),
            (190.0, -6.0),
            (-65.0, 2.0),
            (65.0, -3.0),
        )
        piece_starts = (
            (-30.0, -30.0),
            (30.0, -30.0),
            (-30.0, 30.0),
            (30.0, 30.0),
        )
        chunk_scales = (0.30, 0.27, 0.29, 0.25)
        chunk_heights = (70.0, 100.0, 80.0, 110.0)
        for index, (offset_x, offset_y) in enumerate(pieces):
            chunk = _image(
                EIRA_FX_DIR / f"eira_e_release_v2_fx_chunk_{index:02d}.png",
                chunk_scales[index],
            )
            if chunk is None:
                continue
            if fade < 1.0:
                chunk = chunk.copy()
                chunk.fill(
                    (255, 255, 255, round(255 * fade)),
                    special_flags=pygame.BLEND_RGBA_MULT,
                )
            start_x, start_y = piece_starts[index]
            start_center_x = self.x + start_x
            start_center_y = self.y + start_y
            start_bottom = start_center_y + chunk.get_height() * 0.5
            final_x = self.x + offset_x
            final_bottom = self.ground_y + 8.0 + offset_y
            x = start_center_x + (final_x - start_center_x) * ease
            bottom = (
                start_bottom
                + (final_bottom - start_bottom) * ease
                - chunk_heights[index] * arc
            )
            surface.blit(
                chunk,
                chunk.get_rect(midbottom=(round(x), round(bottom))),
            )
        fragment_placements = (
            (-245.0, 0.0, 0, False, 28.0),
            (-220.0, -3.0, 1, True, 46.0),
            (-190.0, 2.0, 2, False, 34.0),
            (-160.0, -5.0, 0, True, 52.0),
            (-125.0, 1.0, 1, False, 30.0),
            (-85.0, -2.0, 2, True, 44.0),
            (-45.0, 3.0, 0, False, 38.0),
            (45.0, -3.0, 1, True, 50.0),
            (85.0, 2.0, 2, False, 32.0),
            (125.0, -5.0, 0, True, 48.0),
            (160.0, 1.0, 1, False, 36.0),
            (195.0, -2.0, 2, True, 42.0),
            (225.0, 2.0, 0, False, 30.0),
            (250.0, -4.0, 1, True, 54.0),
        )
        fragment_starts = (
            (-18.0, -16.0),
            (16.0, -18.0),
            (26.0, 2.0),
            (-12.0, 18.0),
            (2.0, 0.0),
            (-28.0, 4.0),
            (22.0, -24.0),
            (-24.0, -24.0),
            (10.0, 24.0),
            (-26.0, 24.0),
            (28.0, 18.0),
            (0.0, -30.0),
            (-30.0, -6.0),
            (30.0, -8.0),
        )
        for index, (
            offset_x, offset_y, frame_index, flip, bounce_height
        ) in enumerate(fragment_placements):
            fragment = _image(
                EIRA_FX_DIR
                / f"eira_e_release_v1_fx_fragment_{frame_index:02d}.png",
                0.55,
            )
            if fragment is None:
                continue
            if flip:
                fragment = pygame.transform.flip(fragment, True, False)
            if fade < 1.0:
                fragment = fragment.copy()
                fragment.fill(
                    (255, 255, 255, round(255 * fade)),
                    special_flags=pygame.BLEND_RGBA_MULT,
                )
            start_x, start_y = fragment_starts[index]
            start_center_x = self.x + start_x
            start_center_y = self.y + start_y
            start_bottom = start_center_y + fragment.get_height() * 0.5
            final_x = self.x + offset_x
            final_bottom = self.ground_y + 4.0 + offset_y
            x = start_center_x + (final_x - start_center_x) * ease
            bottom = (
                start_bottom
                + (final_bottom - start_bottom) * ease
                - bounce_height * arc
            )
            surface.blit(
                fragment,
                fragment.get_rect(midbottom=(round(x), round(bottom))),
            )


class IceSpikeHazard:
    """Crooked Witch's ice spike: one second of warning, then damage+freeze."""

    @property
    def behind(self) -> bool:
        # The warning ring lies under the feet; the erupted spike draws in
        # front so its full (Witch-height) silhouette reads.
        return not self.triggered

    # The approved FX live on 1254px canvases with different bottom padding.
    # Measured visible-bottom insets keep the warning ring and the spike base
    # on the ground at the target's feet (scale 0.25 / 0.25). The spike is
    # scaled to the Witch's visual height (~219px), not the old 0.6 (526px).
    WARNING_GROUND_INSET = 5.0
    SPIKE_GROUND_INSETS = (18.5, 18.5, 18.5, 17.5, 17.5, 28.5, 28.5)

    def __init__(
        self,
        owner,
        x: float,
        surface_y: float,
        radius: float,
        warning_time: float,
        attack_data: dict,
        freeze_duration: float,
    ) -> None:
        self.owner = owner
        self.x = float(x)
        self.surface_y = float(surface_y)
        self.radius = float(radius)
        self.warning_time = float(warning_time)
        self.attack_data = dict(attack_data)
        self.freeze_duration = float(freeze_duration)
        self.age = 0.0
        self.spike_time = 0.0
        self.triggered = False
        self.alive = True

    def _circle_center(self) -> tuple[float, float]:
        return self.x, self.surface_y - 60.0

    def update(self, dt: float, scene) -> None:
        if not self.alive:
            return
        self.age += dt
        if not self.triggered:
            if self.age < self.warning_time:
                return
            self.triggered = True
            cx, cy = self._circle_center()
            for target in scene.targets_for(self.owner):
                if target.hp <= 0.0:
                    continue
                if abs(target.y - self.surface_y) > 10.0:
                    continue
                if not _circle_hits_rect(cx, cy, self.radius, target.hurtbox()):
                    continue
                damage = attack_damage(self.owner, self.attack_data)
                apply_direct_damage(
                    scene, self.owner, target, damage,
                    hitstun=float(self.attack_data.get("hitstun", 0.2)),
                    hitstop=float(self.attack_data.get("hitstop", 0.06)),
                )
                target.statuses.add(
                    "freeze", self.freeze_duration, source="witch_ice_spike"
                )
            return

        self.spike_time += dt
        if self.spike_time >= 0.70:
            self.alive = False

    def draw(self, surface: pygame.Surface) -> None:
        if not self.triggered:
            frame = min(4, int(self.age / 0.20))
            image = _image(
                WITCH_FX_DIR / f"crooked_witch_ice_warning_v1_{frame:02d}.png",
                0.25,
            )
            if image is not None:
                surface.blit(
                    image,
                    image.get_rect(
                        midbottom=(
                            round(self.x),
                            round(self.surface_y + self.WARNING_GROUND_INSET),
                        )
                    ),
                )
            else:
                pygame.draw.circle(
                    surface, (90, 180, 255),
                    (round(self.x), round(self.surface_y - 20)),
                    round(self.radius), 2,
                )
            return

        frame = min(6, int(self.spike_time / 0.10))
        image = _image(
            WITCH_FX_DIR / f"crooked_witch_ice_spike_fx_v1_{frame:02d}.png",
            0.25,
        )
        if image is not None:
            inset = self.SPIKE_GROUND_INSETS[
                min(frame, len(self.SPIKE_GROUND_INSETS) - 1)
            ]
            surface.blit(
                image,
                image.get_rect(
                    midbottom=(
                        round(self.x),
                        round(self.surface_y + inset),
                    )
                ),
            )
            return
        pygame.draw.polygon(
            surface, (170, 225, 255),
            [
                (round(self.x - 30), round(self.surface_y)),
                (round(self.x), round(self.surface_y - 120)),
                (round(self.x + 30), round(self.surface_y)),
            ],
        )


class PoisonZone:
    """A six-second green pool that poisons and slows the player inside it."""

    behind = True
    # Source px between the 1254px canvas bottom and the visible puddle
    # bottom; grounding this inset puts the pool at the character's feet.
    POOL_BOTTOM_PAD = 225.0

    def __init__(self, x: float, surface_y: float, config: dict) -> None:
        self.x = float(x)
        self.surface_y = float(surface_y)
        self.radius = float(config.get("zone_radius", 80.0))
        self.lifetime = float(config.get("zone_lifetime", 6.0))
        self.poison_pct = float(config.get("zone_poison_pct_per_sec", 0.02))
        self.poison_duration = float(config.get("poison_duration", 3.0))
        self.slow_pct = float(config.get("zone_slow", 0.20))
        self.slow_duration = float(config.get("slow_duration", 3.0))
        self.age = 0.0
        self.alive = True

    def update(self, dt: float, scene) -> None:
        if not self.alive:
            return
        self.age += dt
        if self.age >= self.lifetime:
            self.alive = False
            return
        player = scene.player
        if player.hp <= 0.0:
            return
        if abs(player.y - self.surface_y) > 10.0:
            return
        if abs(player.x - self.x) > self.radius:
            return
        dps = player.max_hp * self.poison_pct
        if not player.statuses.refresh_poison(
            "witch_potion_zone", self.poison_duration, dps
        ):
            player.statuses.add_poison(
                "witch_potion_zone", self.poison_duration, dps
            )
        player.statuses.add_slow(
            1.0 - self.slow_pct, self.slow_duration,
            source="witch_potion_zone",
        )

    def draw(self, surface: pygame.Surface) -> None:
        fade = self.lifetime - self.age
        if fade < 0.30:
            frame = 3
        elif self.age < 0.30:
            frame = 0
        else:
            frame = 1 + int(self.age / 0.20) % 2
        image = _image(
            WITCH_FX_DIR / f"crooked_witch_poison_pool_v1_{frame:02d}.png",
            1.0,
        )
        if image is not None:
            source_w = image.get_width()
            width = max(1, round(self.radius * 2.4))
            height = max(1, round(image.get_height() * width / source_w))
            image = pygame.transform.smoothscale(image, (width, height))
            inset = self.POOL_BOTTOM_PAD * width / source_w
            surface.blit(
                image,
                image.get_rect(
                    midbottom=(round(self.x), round(self.surface_y + inset))
                ),
            )
            return
        pygame.draw.ellipse(
            surface, (55, 150, 65),
            (
                round(self.x - self.radius),
                round(self.surface_y - 24),
                round(self.radius * 2),
                48,
            ),
        )
