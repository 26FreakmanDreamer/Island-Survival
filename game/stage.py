"""Background, ground, walls and solid blocks."""

from __future__ import annotations

from pathlib import Path

import pygame

from .config import BACKGROUND_PATH, SCREEN_H, SCREEN_W


class Stage:
    def __init__(self, stage_cfg: dict) -> None:
        self.ground_y = float(stage_cfg["ground_y"])
        self.walls = (float(stage_cfg["walls"][0]), float(stage_cfg["walls"][1]))
        # Lane heights are offsets above the attacker's feet, not world Y.
        self.lane_heights = {
            name: float(height) for name, height in stage_cfg["lane_heights"].items()
        }
        self.blocks = [pygame.Rect(int(x), int(y), int(w), int(h)) for x, y, w, h in stage_cfg["blocks"]]
        self.blocks_enabled = True
        self.land_margin = float(stage_cfg.get("land_margin", 8.0))
        self.spawns = {
            key: tuple(value)
            for key, value in stage_cfg.items()
            if key.endswith("_spawn")
        }
        self.player_spawn = self.spawns["player_spawn"]
        self.dummy_spawn = self.spawns["dummy_spawn"]
        self.warrior_spawn = self.spawns["warrior_spawn"]
        self.background = self._load_background()

    def spawn(self, key: str) -> tuple[float, float]:
        return self.spawns[key]

    @staticmethod
    def _load_background() -> pygame.Surface:
        try:
            image = pygame.image.load(str(BACKGROUND_PATH)).convert()
        except pygame.error:
            image = pygame.Surface((SCREEN_W, SCREEN_H))
            image.fill((38, 64, 88))
        return pygame.transform.smoothscale(image, (SCREEN_W, SCREEN_H))

    def lane_y(self, name: str, feet_y: float) -> float:
        height = self.lane_heights.get(name, self.lane_heights["mid"])
        return feet_y - height

    def set_blocks_enabled(self, enabled: bool) -> None:
        self.blocks_enabled = bool(enabled)

    def toggle_blocks(self) -> bool:
        self.blocks_enabled = not self.blocks_enabled
        return self.blocks_enabled

    def draw(self, surface: pygame.Surface) -> None:
        surface.blit(self.background, (0, 0))
        if not self.blocks_enabled:
            return
        for block in self.blocks:
            pygame.draw.rect(surface, (94, 64, 42), block)
            pygame.draw.rect(surface, (132, 94, 60), block.inflate(-6, -6))
            pygame.draw.line(
                surface,
                (168, 126, 82),
                (block.left + 6, block.top + 8),
                (block.right - 6, block.top + 8),
                2,
            )
            pygame.draw.line(
                surface,
                (60, 38, 24),
                (block.centerx, block.top + 10),
                (block.centerx, block.bottom - 4),
                2,
            )

    def draw_bounds(self, surface: pygame.Surface) -> None:
        """Debug-only wall/block outlines."""
        pygame.draw.line(surface, (255, 210, 80), (self.walls[0], 0), (self.walls[0], SCREEN_H), 1)
        pygame.draw.line(surface, (255, 210, 80), (self.walls[1], 0), (self.walls[1], SCREEN_H), 1)
        if not self.blocks_enabled:
            return
        for block in self.blocks:
            pygame.draw.rect(surface, (255, 210, 80), block, 1)

    @staticmethod
    def body_half(fighter) -> float:
        """Wide while grounded to cover the stride; combat width in the air.

        The wide grounded body stops the front boot from entering a block.
        In the air the narrower hurtbox avoids snapping the character away
        when she steps off a ledge and her trailing leg grazes it.
        """
        if fighter.on_ground:
            return fighter.stage_half_width
        return fighter.hurtbox_width * 0.5

    def body_rect(self, fighter, half: float | None = None) -> pygame.Rect:
        """Movement body, wider than the combat hurtbox to cover the legs."""
        if half is None:
            half = self.body_half(fighter)
        _, height = fighter.hurtbox_dims
        return pygame.Rect(
            round(fighter.x - half),
            round(fighter.y - height),
            round(half * 2),
            round(height),
        )

    def move_x(self, fighter, dx: float) -> None:
        """Move horizontally and resolve walls and block sides.

        Also used by attack lunges, which previously changed x directly and
        could embed the character inside a block.
        """
        half = self.body_half(fighter)
        fighter.x += dx

        low, high = self.walls
        if fighter.x - half < low:
            fighter.x = low + half
            fighter.kb_vx = 0.0
        elif fighter.x + half > high:
            fighter.x = high - half
            fighter.kb_vx = 0.0

        if not self.blocks_enabled:
            return

        body = self.body_rect(fighter)
        for block in self.blocks:
            if fighter.y <= block.top + 1 or not body.colliderect(block):
                continue
            # Resolve to the nearer side. Using the movement sign alone can
            # push a character through the block when stepping off its edge.
            if fighter.x < block.centerx:
                fighter.x = block.left - half
            else:
                fighter.x = block.right + half
            fighter.kb_vx = 0.0
            body = self.body_rect(fighter)

    def move_fighter(self, fighter, dt: float) -> None:
        """AABB movement against walls, ground and block tops/sides."""
        total_vx = fighter.vx + fighter.kb_vx
        self.move_x(fighter, total_vx * dt)

        previous_y = fighter.y
        if not fighter.on_ground:
            gravity = fighter.gravity
            if fighter.statuses.has("knock_up"):
                gravity = getattr(fighter, "knock_up_gravity", gravity)
            fighter.vy += gravity * dt
        fighter.y += fighter.vy * dt

        landed = False
        if fighter.y >= self.ground_y:
            fighter.y = self.ground_y
            fighter.vy = 0.0
            landed = True

        if self.blocks_enabled:
            for block in self.blocks:
                if fighter.vy >= 0 and previous_y <= block.top + 1 and fighter.y >= block.top:
                    if block.left - self.land_margin <= fighter.x <= block.right + self.land_margin:
                        fighter.y = float(block.top)
                        fighter.vy = 0.0
                        landed = True

        fighter.on_ground = landed
