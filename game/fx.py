"""Visual-only sprite loading and short-lived projectile/impact effects."""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from pathlib import Path

import pygame

from .config import ASSETS_DIR


LINA_Q_FX_DIR = ASSETS_DIR / "frames" / "lina" / "q_fx"
LINA_Q_FLAME_FX_DIR = ASSETS_DIR / "frames" / "lina" / "flame" / "q_fx"
VENO_WEB_FX_DIR = ASSETS_DIR / "frames" / "veno" / "veno_web_fx"
VENO_WEB_SPRITE_PATH = VENO_WEB_FX_DIR / "veno_web_05_web.png"

Q_WAVE_FRAME_COUNT = 1
Q_WAVE_FRAME_SIZE = (96, 96)
Q_WAVE_ANCHOR = (64, 48)
Q_WAVE_DRAW_OFFSET_Y = -7.0
Q_WAVE_FRAME_DURATIONS = (0.06,) * Q_WAVE_FRAME_COUNT


@dataclass(frozen=True)
class StripSpec:
    directory: Path
    names: tuple[str, ...]
    durations: tuple[float, ...]
    frame_size: tuple[int, int]
    anchor: tuple[int, int]
    loop: bool = True


LINA_Q_SPECS = {
    "normal": StripSpec(
        directory=LINA_Q_FX_DIR,
        names=tuple(f"q_wave_{index:02d}.png" for index in range(Q_WAVE_FRAME_COUNT)),
        durations=Q_WAVE_FRAME_DURATIONS,
        frame_size=Q_WAVE_FRAME_SIZE,
        anchor=Q_WAVE_ANCHOR,
    ),
    "flame": StripSpec(
        directory=LINA_Q_FLAME_FX_DIR,
        names=tuple(f"q_wave_{index:02d}.png" for index in range(Q_WAVE_FRAME_COUNT)),
        durations=Q_WAVE_FRAME_DURATIONS,
        frame_size=Q_WAVE_FRAME_SIZE,
        anchor=Q_WAVE_ANCHOR,
    ),
}


_strip_cache: dict[
    tuple[str, tuple[str, ...]],
    tuple[tuple[float | None, ...], tuple[pygame.Surface, ...] | None],
] = {}
_strip_flip_cache: dict[tuple[str, tuple[str, ...]], tuple[pygame.Surface, ...]] = {}
_web_cache: dict[tuple[str, float], pygame.Surface] = {}
_web_scaled_cache: dict[tuple[str, float, int], pygame.Surface] = {}
_web_rotate_cache: dict[tuple[str, float, int, int], pygame.Surface] = {}


def _strip_key(spec: StripSpec) -> tuple[str, tuple[str, ...]]:
    return (str(spec.directory), spec.names)


def _strip_stamp(spec: StripSpec) -> tuple[float | None, ...]:
    stamp: list[float | None] = []
    for name in spec.names:
        path = spec.directory / name
        try:
            stamp.append(path.stat().st_mtime)
        except OSError:
            stamp.append(None)
    return tuple(stamp)


def _load_strip(spec: StripSpec) -> tuple[pygame.Surface, ...] | None:
    key = _strip_key(spec)
    stamp = _strip_stamp(spec)
    cached = _strip_cache.get(key)
    if cached is not None and cached[0] == stamp and cached[1] is not None:
        return cached[1]
    if any(value is None for value in stamp):
        _strip_cache[key] = (stamp, None)
        _strip_flip_cache.pop(key, None)
        return None

    frames: list[pygame.Surface] = []
    for name in spec.names:
        try:
            image = pygame.image.load(str(spec.directory / name)).convert_alpha()
        except (pygame.error, FileNotFoundError):
            _strip_cache[key] = (stamp, None)
            _strip_flip_cache.pop(key, None)
            return None
        if image.get_size() != spec.frame_size:
            image = pygame.transform.smoothscale(image, spec.frame_size)
        frames.append(image)
    result = tuple(frames)
    _strip_cache[key] = (stamp, result)
    _strip_flip_cache.pop(key, None)
    return result


def _flipped_strip(
    spec: StripSpec, frames: tuple[pygame.Surface, ...]
) -> tuple[pygame.Surface, ...]:
    key = _strip_key(spec)
    cached = _strip_flip_cache.get(key)
    if cached is not None and len(cached) == len(frames):
        return cached
    flipped = tuple(pygame.transform.flip(frame, True, False) for frame in frames)
    _strip_flip_cache[key] = flipped
    return flipped


def strip_frame(
    spec: StripSpec, age: float, facing: int
) -> pygame.Surface | None:
    """Return the strip frame for ``age``, flipped for left-facing."""
    frames = _load_strip(spec)
    if frames is None:
        return None
    total = sum(spec.durations)
    if total <= 0.0:
        index = 0
    else:
        if spec.loop:
            t = max(0.0, age) % total
        else:
            t = min(max(0.0, age), total - 1e-6)
        elapsed = 0.0
        index = len(frames) - 1
        for frame_index, duration in enumerate(spec.durations):
            elapsed += duration
            if t < elapsed:
                index = frame_index
                break
    if facing < 0:
        frames = _flipped_strip(spec, frames)
    return frames[min(index, len(frames) - 1)]


def missing_lina_q_assets() -> list[str]:
    missing: list[str] = []
    for spec in LINA_Q_SPECS.values():
        for name in spec.names:
            path = spec.directory / name
            if not path.exists():
                missing.append(str(path))
    return missing


def missing_veno_web_asset() -> list[str]:
    return [] if VENO_WEB_SPRITE_PATH.exists() else [str(VENO_WEB_SPRITE_PATH)]


def missing_assets() -> list[str]:
    return missing_lina_q_assets() + missing_veno_web_asset()


def load_web_sprite() -> pygame.Surface | None:
    """Load the approved web crop, trimming transparent margins."""
    path = VENO_WEB_SPRITE_PATH
    try:
        mtime = path.stat().st_mtime
    except OSError:
        return None
    key = (str(path), mtime)
    cached = _web_cache.get(key)
    if cached is not None:
        return cached
    try:
        image = pygame.image.load(str(path)).convert_alpha()
    except (pygame.error, FileNotFoundError):
        return None
    bounds = image.get_bounding_rect(min_alpha=1)
    if bounds.width > 0 and bounds.height > 0:
        image = image.subsurface(bounds).copy()
    _web_cache[key] = image
    for cache in (_web_scaled_cache, _web_rotate_cache):
        stale = [old for old in cache if old[0] == str(path) and old[1] != mtime]
        for old in stale:
            del cache[old]
    return image


def web_sprite(height: int, angle: float) -> pygame.Surface | None:
    """Return the web crop scaled to ``height`` and quantized to 5 degrees."""
    image = load_web_sprite()
    if image is None:
        return None
    try:
        mtime = VENO_WEB_SPRITE_PATH.stat().st_mtime
    except OSError:
        return None
    height = max(1, int(round(height)))
    base_key = (str(VENO_WEB_SPRITE_PATH), mtime, height)
    scaled = _web_scaled_cache.get(base_key)
    if scaled is None:
        scale = height / max(1, image.get_height())
        size = (max(1, round(image.get_width() * scale)), height)
        scaled = pygame.transform.smoothscale(image, size)
        _web_scaled_cache[base_key] = scaled
    quantized = int(round(angle / 5.0)) * 5 % 360
    rotate_key = (*base_key, quantized)
    rotated = _web_rotate_cache.get(rotate_key)
    if rotated is None:
        rotated = pygame.transform.rotozoom(scaled, quantized, 1.0)
        if len(_web_rotate_cache) >= 64:
            _web_rotate_cache.clear()
        _web_rotate_cache[rotate_key] = rotated
    return rotated


class FxEffect:
    """Base class for short, draw-only effects."""

    kind = "fx"

    def __init__(self, life: float, kind: str | None = None) -> None:
        self.life = max(0.001, float(life))
        self.age = 0.0
        self.alive = True
        if kind is not None:
            self.kind = kind

    @property
    def progress(self) -> float:
        return max(0.0, min(1.0, self.age / self.life))

    def update(self, dt: float) -> None:
        self.age += dt
        if self.age >= self.life:
            self.alive = False

    def draw(self, surface: pygame.Surface) -> None:
        raise NotImplementedError


class RingBurstFx(FxEffect):
    """Expanding ring used for cast flashes and elemental hit bursts."""

    kind = "ring"

    def __init__(
        self,
        x: float,
        y: float,
        color: tuple[int, int, int],
        *,
        life: float = 0.18,
        start_radius: float = 6.0,
        end_radius: float = 36.0,
        width: int = 3,
        sparks: int = 0,
        spark_color: tuple[int, int, int] | None = None,
        kind: str | None = None,
    ) -> None:
        super().__init__(life, kind)
        self.x = float(x)
        self.y = float(y)
        self.color = tuple(color)
        self.start_radius = float(start_radius)
        self.end_radius = float(end_radius)
        self.width = max(1, int(width))
        self.sparks = max(0, int(sparks))
        self.spark_color = tuple(spark_color or color)

    def draw(self, surface: pygame.Surface) -> None:
        progress = self.progress
        radius = self.start_radius + (self.end_radius - self.start_radius) * progress
        alpha = max(0, round(230 * (1.0 - progress)))
        pad = max(1, round(radius)) + self.width + 10
        layer = pygame.Surface((pad * 2, pad * 2), pygame.SRCALPHA)
        center = pad
        pygame.draw.circle(
            layer, (*self.color, alpha), (center, center),
            max(1, round(radius)), self.width,
        )
        pygame.draw.circle(
            layer, (*self.color, max(0, round(alpha * 0.45))), (center, center),
            max(1, round(radius * 0.62)), max(1, self.width // 2),
        )
        for index in range(self.sparks):
            angle = self.age * 9.0 + index * math.tau / max(1, self.sparks)
            sx = center + math.cos(angle) * radius * 0.9
            sy = center + math.sin(angle) * radius * 0.9
            pygame.draw.circle(
                layer, (*self.spark_color, max(0, round(alpha * 0.9))),
                (round(sx), round(sy)), 2,
            )
        surface.blit(layer, (round(self.x - center), round(self.y - center)))


class PoisonSplashFx(FxEffect):
    """Acid-green droplet spray with a short mist residue."""

    kind = "veno_poison_impact"

    def __init__(
        self, x: float, y: float, *, life: float = 0.22, kind: str | None = None
    ) -> None:
        super().__init__(life, kind)
        self.x = float(x)
        self.y = float(y)
        rng = random.Random(1337)
        self.droplets = [
            (rng.uniform(-math.pi, 0.2), rng.uniform(35.0, 90.0),
             rng.uniform(1.5, 3.5), rng.uniform(0.6, 1.0))
            for _ in range(9)
        ]
        self.mist = [
            (rng.uniform(-12.0, 12.0), rng.uniform(-14.0, 6.0), rng.uniform(6.0, 12.0))
            for _ in range(3)
        ]

    def draw(self, surface: pygame.Surface) -> None:
        progress = self.progress
        alpha = 200.0 * (1.0 - progress)
        pad = 48
        layer = pygame.Surface((pad * 2, pad * 2), pygame.SRCALPHA)
        center = pad
        for dx, dy, radius in self.mist:
            drift = 0.6 + 0.6 * progress
            pygame.draw.circle(
                layer, (35, 110, 50, max(0, round(alpha * 0.35))),
                (round(center + dx * drift), round(center + dy * drift)),
                max(1, round(radius * (0.8 + 0.6 * progress))),
            )
        for angle, speed, radius, strength in self.droplets:
            distance = speed * self.age
            dx = math.cos(angle) * distance
            dy = math.sin(angle) * distance + 40.0 * self.age * self.age
            pygame.draw.circle(
                layer, (80, 185, 95, max(0, round(alpha * strength))),
                (round(center + dx), round(center + dy)),
                max(1, round(radius * (1.0 - progress * 0.5))),
            )
        surface.blit(layer, (round(self.x - center), round(self.y - center)))


class WebImpactFx(FxEffect):
    """Web decal plus a white flash ring and a few stun sparks."""

    kind = "veno_web_impact"

    def __init__(
        self, x: float, y: float, *, life: float = 0.20, kind: str | None = None
    ) -> None:
        super().__init__(life, kind)
        self.x = float(x)
        self.y = float(y)

    def draw(self, surface: pygame.Surface) -> None:
        progress = self.progress
        alpha = max(0, round(255 * (1.0 - progress)))
        sprite = web_sprite(int(round(150 + 20 * progress)), 0.0)
        if sprite is not None:
            tinted = sprite.copy()
            tinted.set_alpha(alpha)
            surface.blit(
                tinted, tinted.get_rect(center=(round(self.x), round(self.y)))
            )

        radius = 14.0 + 32.0 * progress
        pad = max(1, round(radius)) + 6
        ring = pygame.Surface((pad * 2, pad * 2), pygame.SRCALPHA)
        center = pad
        pygame.draw.circle(
            ring, (245, 255, 235, max(0, round(220 * (1.0 - progress)))),
            (center, center), max(1, round(radius)), 2,
        )
        surface.blit(ring, (round(self.x - center), round(self.y - center)))

        for index in range(3):
            angle = -0.8 + index * 0.8
            distance = 24.0 + 30.0 * progress
            sx = self.x + math.cos(angle) * distance
            sy = self.y + math.sin(angle) * distance
            pygame.draw.circle(
                surface, (255, 224, 90), (round(sx), round(sy)),
                max(1, round(3 * (1.0 - progress))),
            )


class BiteArcFx(FxEffect):
    """Small green crescent at the target's near edge for a connected bite."""

    kind = "veno_bite_hit"

    def __init__(
        self,
        x: float,
        y: float,
        facing: int,
        *,
        life: float = 0.12,
        kind: str | None = None,
    ) -> None:
        super().__init__(life, kind)
        self.x = float(x)
        self.y = float(y)
        self.facing = 1 if facing >= 0 else -1

    def draw(self, surface: pygame.Surface) -> None:
        progress = self.progress
        radius = 18.0 + 22.0 * progress
        alpha = max(0, round(245 * (1.0 - progress)))
        pad = max(1, round(radius)) + 12
        layer = pygame.Surface((pad * 2, pad * 2), pygame.SRCALPHA)
        center = pad
        rect = pygame.Rect(
            center - round(radius), center - round(radius),
            max(1, round(radius * 2)), max(1, round(radius * 2)),
        )
        if self.facing >= 0:
            start, stop = -0.95, 0.95
        else:
            start, stop = math.pi - 0.95, math.pi + 0.95
        pygame.draw.arc(
            layer, (120, 255, 90, max(0, round(alpha * 0.45))),
            rect.inflate(10, 10), start, stop, 6,
        )
        pygame.draw.arc(layer, (170, 255, 120, alpha), rect, start, stop, 4)
        pygame.draw.arc(
            layer, (245, 255, 225, alpha),
            rect.inflate(-10, -10), start, stop, 2,
        )
        for index in range(4):
            angle = start + (stop - start) * (0.15 + index * 0.23)
            dx = math.cos(angle) * (radius + 4.0)
            dy = math.sin(angle) * (radius + 4.0)
            pygame.draw.circle(
                layer, (220, 255, 170, max(0, round(alpha * 0.8))),
                (round(center + dx), round(center + dy)), 2,
            )
        surface.blit(layer, (round(self.x - center), round(self.y - center)))


class SilkCastFx(FxEffect):
    """Procedural silk strands sprayed from Veno's mouth."""

    kind = "veno_web_cast"

    def __init__(
        self,
        x: float,
        y: float,
        ux: float,
        uy: float,
        *,
        life: float = 0.12,
        kind: str | None = None,
    ) -> None:
        super().__init__(life, kind)
        self.x = float(x)
        self.y = float(y)
        self.base_angle = math.atan2(float(uy), float(ux))
        rng = random.Random(4242)
        self.strands = [
            (rng.uniform(-0.35, 0.35), rng.uniform(22.0, 52.0), rng.uniform(0.0, math.tau))
            for _ in range(5)
        ]

    def draw(self, surface: pygame.Surface) -> None:
        progress = self.progress
        alpha = max(0, round(220 * (1.0 - progress)))
        pad = 64
        layer = pygame.Surface((pad * 2, pad * 2), pygame.SRCALPHA)
        center = pad
        for angle_offset, length, phase in self.strands:
            angle = self.base_angle + angle_offset
            points: list[tuple[int, int]] = []
            for step in range(7):
                t = step / 6.0
                distance = length * t * (0.4 + 0.6 * progress)
                wobble = math.sin(phase + t * 4.0 + self.age * 12.0) * 3.0 * t
                px = center + math.cos(angle) * distance - math.sin(angle) * wobble
                py = center + math.sin(angle) * distance + math.cos(angle) * wobble
                points.append((round(px), round(py)))
            pygame.draw.lines(layer, (210, 255, 190, alpha), False, points, 2)
            pygame.draw.lines(layer, (250, 255, 240, alpha), False, points, 1)
        surface.blit(layer, (round(self.x - center), round(self.y - center)))
