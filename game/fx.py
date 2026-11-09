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


PHANTOM_FX_DIR = ASSETS_DIR / "frames" / "shadow_ninja" / "phantom" / "fx"
_phantom_fx_cache: dict[tuple[str, float, int, int], pygame.Surface | None] = {}


def phantom_fx_image(
    prefix: str,
    frame: int,
    frame_count: int,
    width: int,
) -> pygame.Surface | None:
    """Load one approved phantom FX frame and scale it to a fixed width."""
    index = frame % frame_count
    path = PHANTOM_FX_DIR / f"{prefix}_{index:02d}.png"
    try:
        mtime = path.stat().st_mtime
    except OSError:
        mtime = 0.0
    key = (str(path), mtime, index, width)
    if key in _phantom_fx_cache:
        cached = _phantom_fx_cache[key]
        return cached.copy() if cached is not None else None
    try:
        image = pygame.image.load(str(path)).convert_alpha()
    except (OSError, pygame.error):
        _phantom_fx_cache[key] = None
        return None
    if width > 0 and image.get_width() != width:
        height = max(1, round(image.get_height() * width / image.get_width()))
        image = pygame.transform.smoothscale(image, (width, height))
    _phantom_fx_cache[key] = image
    return image.copy()


class FxEffect:
    """Base class for short, draw-only effects."""

    kind = "fx"
    # Draw before the fighters when the effect belongs behind the body.
    behind = False

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


class PhantomClawFx(FxEffect):
    """P1 影爪: the long claw trail drawn separately from the character."""

    kind = "phantom_claw"
    behind = True

    def __init__(
        self, attacker, life: float = 0.36, delay: float = 0.18
    ) -> None:
        super().__init__(life, "phantom_claw")
        self.attacker = attacker
        self.delay = float(delay)

    def draw(self, surface: pygame.Surface) -> None:
        if self.age < self.delay:
            return
        facing = 1 if self.attacker.facing >= 0 else -1
        frame = min(2, int((self.age - self.delay) / 0.06))
        image = phantom_fx_image("phantom_rend_trail", frame, 3, 384)
        ax = self.attacker.x + facing * 30.0
        ay = self.attacker.y - 150.0
        if image is not None:
            if facing < 0:
                image = pygame.transform.flip(image, True, False)
            if facing > 0:
                rect = image.get_rect(midleft=(round(ax), round(ay)))
            else:
                rect = image.get_rect(midright=(round(ax), round(ay)))
            surface.blit(image, rect)
            return
        # Placeholder trail until the approved strip exists.
        for index in range(3):
            start = (
                round(self.attacker.x + facing * (24 + index * 8)),
                round(self.attacker.y - 158 + index * 6),
            )
            end = (
                round(self.attacker.x + facing * (120 + index * 55)),
                round(self.attacker.y - 158 + index * 14),
            )
            pygame.draw.line(
                surface, (190, 120, 255), start, end, max(1, 4 - index)
            )
            pygame.draw.line(
                surface, (235, 215, 255), start, end, 1
            )


class PhantomSharkFx(FxEffect):
    """P3 影闪: the shark silhouette drawn over the charging body."""

    kind = "phantom_shark"

    def __init__(self, attacker, life: float = 0.40) -> None:
        super().__init__(life, "phantom_shark")
        self.attacker = attacker

    def draw(self, surface: pygame.Surface) -> None:
        facing = 1 if self.attacker.facing >= 0 else -1
        frame = min(2, int(self.age / 0.104))
        image = phantom_fx_image("phantom_shark", frame, 3, 320)
        if image is not None:
            if facing < 0:
                image = pygame.transform.flip(image, True, False)
            rect = image.get_rect(
                midbottom=(
                    round(self.attacker.x),
                    round(self.attacker.y + 6.0),
                )
            )
            surface.blit(image, rect)
            return
        # Placeholder: black snout + purple dorsal fin.
        x = self.attacker.x
        y = self.attacker.y
        pygame.draw.polygon(
            surface,
            (26, 10, 42),
            [
                (round(x + facing * 100), round(y - 30)),
                (round(x - facing * 90), round(y - 12)),
                (round(x - facing * 70), round(y - 58)),
                (round(x + facing * 40), round(y - 58)),
            ],
        )
        pygame.draw.polygon(
            surface,
            (145, 75, 235),
            [
                (round(x - facing * 10), round(y - 52)),
                (round(x - facing * 44), round(y - 100)),
                (round(x + facing * 28), round(y - 58)),
            ],
        )
        pygame.draw.circle(
            surface, (215, 165, 255),
            (round(x + facing * 62), round(y - 42)), 4,
        )


_PHANTOM_BIND_FRAME_DURATIONS = (0.07, 0.09, 0.11, 0.51, 0.13, 0.09)


class PhantomBindWrapFx(FxEffect):
    """P2 影缚: v2 front/back tendril wrap around the bound target."""

    kind = "phantom_bind_wrap"
    side = "front"
    behind = False

    def __init__(self, target, life: float = 1.0) -> None:
        super().__init__(life, "phantom_bind_wrap")
        self.target = target

    def _frame_index(self) -> int:
        elapsed = self.age
        total = 0.0
        for index, duration in enumerate(_PHANTOM_BIND_FRAME_DURATIONS):
            total += duration
            if elapsed < total:
                return index
        return len(_PHANTOM_BIND_FRAME_DURATIONS) - 1

    def draw(self, surface: pygame.Surface) -> None:
        target = self.target
        if target is None or getattr(target, "hp", 0.0) <= 0.0:
            return
        image = phantom_fx_image(
            f"phantom_bind_{self.side}", self._frame_index(), 6, 208
        )
        if image is not None:
            surface.blit(
                image,
                (round(target.x - 104.0), round(target.y - 224.0)),
            )
            return
        # Fallback when the approved wrap strip is missing.
        progress = self.progress
        alpha = max(0, round(220 * (1.0 - progress)))
        pad = 80
        layer = pygame.Surface((pad * 2, pad * 2), pygame.SRCALPHA)
        center = pad
        pygame.draw.circle(
            layer, (150, 80, 235, alpha), (center, center), 34, 3
        )
        pygame.draw.circle(
            layer, (215, 175, 255, alpha), (center, center), 24, 2
        )
        for index in range(5):
            angle = index * math.tau / 5.0 + self.age * 2.2
            px = center + math.cos(angle) * 44.0
            py = center + math.sin(angle) * 24.0
            pygame.draw.line(
                layer, (190, 120, 255, alpha),
                (center, center), (round(px), round(py)), 2,
            )
        surface.blit(
            layer,
            (round(target.x - center), round(target.y - 100.0 - center)),
        )


class PhantomBindFrontFx(PhantomBindWrapFx):
    side = "front"
    behind = False


class PhantomBindBackFx(PhantomBindWrapFx):
    side = "back"
    behind = True


_SPRITE_STRIP_CACHE: dict[tuple, pygame.Surface | None] = {}


def _sprite_strip_frame(
    path: str | Path, scale: float, x_scale: float = 1.0
) -> pygame.Surface | None:
    path = Path(path)
    try:
        mtime = path.stat().st_mtime
    except OSError:
        return None
    key = (str(path), mtime, round(scale, 4), round(x_scale, 4))
    if key in _SPRITE_STRIP_CACHE:
        cached = _SPRITE_STRIP_CACHE[key]
        return cached.copy() if cached is not None else None
    try:
        image = pygame.image.load(str(path)).convert_alpha()
    except (OSError, pygame.error):
        _SPRITE_STRIP_CACHE[key] = None
        return None
    if abs(scale - 1.0) > 1e-6 or abs(x_scale - 1.0) > 1e-6:
        image = pygame.transform.smoothscale(
            image,
            (
                max(1, round(image.get_width() * scale * x_scale)),
                max(1, round(image.get_height() * scale)),
            ),
        )
    _SPRITE_STRIP_CACHE[key] = image
    return image.copy()


class SpriteStripFx(FxEffect):
    """One approved frame sequence drawn at a fixed anchor.

    Used for the Eira/Witch FX that are separate from the character frames
    (snowball impact, ice shards, lightning, potion break, fire impact).
    """

    kind = "sprite_strip"

    def __init__(
        self,
        frames,
        durations,
        x: float,
        y: float,
        *,
        pivot: tuple[float, float] | None = None,
        scale: float = 1.0,
        x_scale: float = 1.0,
        x_scale_from: int = 0,
        flip: bool = False,
        behind: bool = False,
        loop: bool = False,
        kind: str | None = None,
    ) -> None:
        durations = [float(value) for value in durations]
        total = sum(durations)
        if total <= 0.0:
            durations = [0.1]
            total = 0.1
        super().__init__(total, kind)
        self.frames = [str(path) for path in frames]
        self.durations = durations
        self.x = float(x)
        self.y = float(y)
        self.pivot = pivot
        self.scale = float(scale)
        self.x_scale = float(x_scale)
        self.x_scale_from = max(0, int(x_scale_from))
        self.flip = bool(flip)
        self.behind = bool(behind)
        self.loop = bool(loop)
        self._frame_x_scales = [
            self.x_scale if index >= self.x_scale_from else 1.0
            for index in range(len(self.frames))
        ]
        self._images = [
            _sprite_strip_frame(path, self.scale, x_scale)
            for path, x_scale in zip(self.frames, self._frame_x_scales)
        ]

    def update(self, dt: float) -> None:
        self.age += dt
        if self.loop:
            if self.age >= self.life:
                self.age %= self.life
        elif self.age >= self.life:
            self.alive = False

    def _frame_index(self) -> int:
        elapsed = 0.0
        for index, duration in enumerate(self.durations):
            elapsed += duration
            if self.age < elapsed:
                return index
        return len(self.durations) - 1

    def draw(self, surface: pygame.Surface) -> None:
        index = self._frame_index()
        if not 0 <= index < len(self._images):
            return
        image = self._images[index]
        if image is None:
            return
        if self.flip:
            image = pygame.transform.flip(image, True, False)
        if self.pivot is None:
            pivot_x = image.get_width() * 0.5
            pivot_y = image.get_height() * 0.5
        else:
            frame_x_scale = self._frame_x_scales[index]
            pivot_x = float(self.pivot[0]) * self.scale * frame_x_scale
            pivot_y = float(self.pivot[1]) * self.scale
        if self.flip and self.pivot is not None:
            pivot_x = image.get_width() - pivot_x
        surface.blit(
            image,
            (round(self.x - pivot_x), round(self.y - pivot_y)),
        )
