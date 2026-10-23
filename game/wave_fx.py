"""Cast-anchored sprite effect for Nyra's Q sword wave."""

from __future__ import annotations

import os

import pygame

from .config import ASSETS_DIR


FX_DIR = ASSETS_DIR / "frames" / "nyra" / "nyra_wave_fx"
FRAME_DURATIONS = (0.04, 0.04, 0.05, 0.08, 0.05, 0.05)
FRAME_SIZE = (384, 384)
PIVOT = (192, 372)


class WaveEffect:
    _right_frames: tuple[pygame.Surface, ...] | None = None
    _left_frames: tuple[pygame.Surface, ...] | None = None
    _stamp: tuple[float, ...] | None = None

    def __init__(self, x: float, y: float, facing: int, event: dict) -> None:
        self.start_x = float(x)
        self.base_y = float(y)
        self.facing = 1 if facing >= 0 else -1
        self.age = 0.0
        self.alive = True
        self.frame_index = 0

    @classmethod
    def _current_stamp(cls) -> tuple[float, ...]:
        return tuple(
            os.path.getmtime(FX_DIR / f"nyra_wave_fx_{index:02d}.png")
            for index in range(len(FRAME_DURATIONS))
        )

    @classmethod
    def _frames(cls, facing: int) -> tuple[pygame.Surface, ...]:
        stamp = cls._current_stamp()
        if cls._right_frames is None or cls._stamp != stamp:
            frames = tuple(
                pygame.image.load(str(FX_DIR / f"nyra_wave_fx_{index:02d}.png")).convert_alpha()
                for index in range(len(FRAME_DURATIONS))
            )
            if any(frame.get_size() != FRAME_SIZE for frame in frames):
                raise ValueError("Nyra Q effect frames must be 384x384")
            cls._right_frames = frames
            cls._left_frames = tuple(
                pygame.transform.flip(frame, True, False) for frame in frames
            )
            cls._stamp = stamp
        if facing >= 0:
            return cls._right_frames
        assert cls._left_frames is not None
        return cls._left_frames

    def update(self, dt: float) -> None:
        self.age += dt
        elapsed = 0.0
        for index, duration in enumerate(FRAME_DURATIONS):
            elapsed += duration
            if self.age < elapsed:
                self.frame_index = index
                return
        self.alive = False

    def draw(self, surface: pygame.Surface) -> None:
        if not self.alive:
            return
        frame = self._frames(self.facing)[self.frame_index]
        pivot_x = PIVOT[0] if self.facing >= 0 else frame.get_width() - PIVOT[0]
        surface.blit(frame, (round(self.start_x - pivot_x), round(self.base_y - PIVOT[1])))
