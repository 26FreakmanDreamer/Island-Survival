"""Frame animation with per-frame durations and facing flips."""

from __future__ import annotations

from pathlib import Path

import pygame

FRAME_SIZE = (256, 256)


class AnimationPlayer:
    def __init__(
        self,
        clips: dict,
        flame_clips: dict,
        frames_dir: Path,
        fallback_path: Path,
        pivot: tuple[int, int],
        frame_size: tuple[int, int] = FRAME_SIZE,
        frame_offsets: dict[str, int] | None = None,
    ) -> None:
        self.default_clips = clips
        self.flame_clips = flame_clips
        self.variant = "normal"
        self.clips = clips
        self.frames_dir = frames_dir
        self.fallback_path = fallback_path
        self.pivot = (int(pivot[0]), int(pivot[1]))
        self.frame_size = (int(frame_size[0]), int(frame_size[1]))
        self.frame_offsets = frame_offsets or {}
        self.cache: dict[tuple, pygame.Surface] = {}
        self.missing: set[str] = set()
        self.clip_name = "idle"
        self.frame_index = 0
        self.time = 0.0
        self.finished = False

    @property
    def clip(self) -> dict:
        if self.clip_name in self.clips:
            return self.clips[self.clip_name]
        return self.default_clips.get(self.clip_name, self.default_clips["idle"])

    @property
    def current_is_flame_frame(self) -> bool:
        return self.variant == "flame" and self.clip_name in self.flame_clips

    def set_variant(self, variant: str) -> None:
        if variant == self.variant:
            return
        self.variant = variant
        self.clips = self.flame_clips if variant == "flame" else self.default_clips
        if self.clip_name not in self.clips and self.clip_name not in self.default_clips:
            self.clip_name = "idle"
        self.time = 0.0
        self.frame_index = 0
        self.finished = False

    def set_clip(self, name: str, reset: bool = False) -> None:
        if name not in self.clips and name not in self.default_clips:
            name = "idle"
        if name != self.clip_name:
            self.clip_name = name
            self.time = 0.0
            self.frame_index = 0
            self.finished = False
        elif reset:
            self.time = 0.0
            self.frame_index = 0
            self.finished = False

    def set_frame(self, index: int) -> None:
        count = len(self.clip.get("frames", []))
        if count:
            self.frame_index = max(0, min(index, count - 1))

    def update(self, dt: float) -> None:
        if self.finished:
            return
        durations = self.clip.get("durations", [])
        if not durations:
            return
        self.time += dt
        guard = 0
        while self.time >= durations[self.frame_index] and guard < 32:
            guard += 1
            self.time -= durations[self.frame_index]
            if self.frame_index + 1 < len(durations):
                self.frame_index += 1
            elif self.clip.get("loop"):
                self.frame_index = 0
            else:
                self.finished = True
                break

    def current_frame_path(self) -> str:
        frames = self.clip.get("frames", [])
        if not frames:
            return ""
        return frames[min(self.frame_index, len(frames) - 1)]

    def missing_paths(self) -> list[str]:
        """Every configured frame path that is not present on disk."""
        paths: list[str] = []
        seen: set[str] = set()
        for clips in (self.default_clips, self.flame_clips):
            for clip in clips.values():
                for rel in clip.get("frames", []):
                    if rel in seen:
                        continue
                    seen.add(rel)
                    path = self.frames_dir / rel
                    if not path.exists():
                        paths.append(str(path))
        return paths

    def _load(self, path: Path) -> pygame.Surface:
        if path.exists():
            try:
                surface = pygame.image.load(str(path)).convert_alpha()
                self.missing.discard(str(path))
            except pygame.error:
                self.missing.add(str(path))
                surface = self._load_fallback()
            mtime = path.stat().st_mtime
        else:
            self.missing.add(str(path))
            surface = self._load_fallback()
            mtime = 0.0

        if surface.get_size() != self.frame_size:
            surface = pygame.transform.smoothscale(surface, self.frame_size)

        key = (str(path), mtime)
        self.cache[key] = surface
        return surface

    def _load_fallback(self) -> pygame.Surface:
        try:
            surface = pygame.image.load(str(self.fallback_path)).convert_alpha()
        except pygame.error:
            surface = pygame.Surface(self.frame_size, pygame.SRCALPHA)
            pygame.draw.rect(surface, (180, 120, 220, 255), (88, 34, 80, 210))
        if surface.get_size() != self.frame_size:
            surface = pygame.transform.smoothscale(surface, self.frame_size)
        return surface

    def surface(self, facing: int = 1) -> pygame.Surface:
        rel = self.current_frame_path()
        path = self.frames_dir / rel if rel else self.fallback_path
        mtime = path.stat().st_mtime if path.exists() else 0.0
        key = (str(path), mtime, facing)
        if key in self.cache:
            return self.cache[key]

        surface = self._load(path)
        if facing < 0:
            surface = pygame.transform.flip(surface, True, False)
        self.cache[key] = surface
        return surface

    def draw(
        self,
        target: pygame.Surface,
        x: float,
        y: float,
        facing: int = 1,
        tint: tuple[int, int, int] | None = None,
        scale: float = 1.0,
    ) -> None:
        surface = self.surface(facing=facing)
        image = surface
        if tint is not None:
            # Multiply the whole frame so the body flashes without covering
            # the background (unlike a filled hurtbox rectangle).
            image = surface.copy()
            image.fill((*tint, 255), special_flags=pygame.BLEND_RGBA_MULT)
        # Some sprites were staged with a horizontal offset inside the canvas
        # (Lina's flame framing, Eira's wide KO last frame). Apply the baked
        # alignment offset so the feet stay at the fighter's world position;
        # mirror it when flipped. Paths without an entry use 0.
        offset = self.frame_offsets.get(self.current_frame_path(), 0)
        if facing < 0:
            offset = -offset
        pivot_x, pivot_y = self.pivot
        # Optional uniform draw scale for the climb art; the pivot (feet)
        # stays the anchor so the body grows upward.
        if scale != 1.0:
            width, height = image.get_size()
            image = pygame.transform.smoothscale(
                image, (max(1, round(width * scale)), max(1, round(height * scale)))
            )
            offset *= scale
            pivot_x *= scale
            pivot_y *= scale
        if facing < 0:
            pivot_x = image.get_width() - pivot_x
        target.blit(image, (round(x - pivot_x + offset), round(y - pivot_y)))
