"""Background, ground, walls, solid blocks and climbable ladders."""

from __future__ import annotations

from dataclasses import dataclass

import pygame

from .config import BACKGROUND_PATH, SCREEN_H, SCREEN_W, STAGE_SPRITE_DIR


@dataclass
class Block:
    """One solid scene entity. ``kind`` is ``barrier`` or ``platform``."""

    kind: str
    rect: pygame.Rect
    sprite_name: str | None = None
    sprite_rect: pygame.Rect | None = None
    surface: pygame.Surface | None = None


@dataclass
class Ladder:
    """Climb trigger and sprite. Ladders are never added to ``Stage.blocks``."""

    rect: pygame.Rect
    top_y: float
    bottom_y: float
    sprite_name: str | None = None
    sprite_rect: pygame.Rect | None = None
    surface: pygame.Surface | None = None


class Stage:
    def __init__(self, stage_cfg: dict) -> None:
        self.ground_y = float(stage_cfg["ground_y"])
        self.walls = (float(stage_cfg["walls"][0]), float(stage_cfg["walls"][1]))
        # Lane heights are offsets above the attacker's feet, not world Y.
        self.lane_heights = {
            name: float(height) for name, height in stage_cfg["lane_heights"].items()
        }
        self.block_specs = self._parse_blocks(stage_cfg["blocks"])
        # Solid view used by movement, AI, separation and projectiles.
        self.blocks = [block.rect for block in self.block_specs]
        self.barriers = [
            block.rect for block in self.block_specs if block.kind == "barrier"
        ]
        self.platforms = [
            block.rect for block in self.block_specs if block.kind == "platform"
        ]
        self.ladders = self._parse_ladders(stage_cfg["ladders"])
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

    def _parse_blocks(self, entries) -> list[Block]:
        blocks: list[Block] = []
        for entry in entries:
            if isinstance(entry, (list, tuple)):
                kind = "barrier"
                rect_data = entry
                sprite_name = None
                sprite_rect_data = None
                surface_y = None
            else:
                kind = str(entry.get("kind", "barrier"))
                rect_data = entry["rect"]
                sprite_name = entry.get("sprite")
                sprite_rect_data = entry.get("sprite_rect")
                surface_y = entry.get("surface_y")
            rect = pygame.Rect(
                int(rect_data[0]),
                int(rect_data[1]),
                int(rect_data[2]),
                int(rect_data[3]),
            )
            if surface_y is not None:
                rect.top = int(surface_y)
            sprite_rect = (
                pygame.Rect(
                    int(sprite_rect_data[0]),
                    int(sprite_rect_data[1]),
                    int(sprite_rect_data[2]),
                    int(sprite_rect_data[3]),
                )
                if sprite_rect_data is not None
                else None
            )
            surface = (
                self._load_sprite(sprite_name, sprite_rect.size)
                if sprite_rect is not None
                else None
            )
            blocks.append(Block(kind, rect, sprite_name, sprite_rect, surface))
        return blocks

    def _parse_ladders(self, entries) -> list[Ladder]:
        ladders: list[Ladder] = []
        for entry in entries:
            rect_data = entry["rect"]
            sprite_rect_data = entry["sprite_rect"]
            rect = pygame.Rect(
                int(rect_data[0]),
                int(rect_data[1]),
                int(rect_data[2]),
                int(rect_data[3]),
            )
            sprite_rect = pygame.Rect(
                int(sprite_rect_data[0]),
                int(sprite_rect_data[1]),
                int(sprite_rect_data[2]),
                int(sprite_rect_data[3]),
            )
            sprite_name = entry.get("sprite")
            surface = self._load_sprite(sprite_name, sprite_rect.size)
            ladders.append(
                Ladder(
                    rect=rect,
                    top_y=float(entry["top_y"]),
                    bottom_y=float(entry["bottom_y"]),
                    sprite_name=sprite_name,
                    sprite_rect=sprite_rect,
                    surface=surface,
                )
            )
        return ladders

    @staticmethod
    def _load_sprite(
        name: str | None, size: tuple[int, int]
    ) -> pygame.Surface | None:
        if not name:
            return None
        try:
            image = pygame.image.load(str(STAGE_SPRITE_DIR / name)).convert_alpha()
        except (pygame.error, FileNotFoundError):
            return None
        if image.get_size() != size:
            image = pygame.transform.smoothscale(image, size)
        return image

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

    def platform_top_at(self, x: float, feet_y: float) -> float | None:
        """Return the platform top under a fighter's feet, if any."""
        for rect in self.platforms:
            if rect.left <= x <= rect.right and abs(feet_y - rect.top) <= 1.0:
                return float(rect.top)
        return None

    def segment_hits_blocks(
        self, x0: float, y0: float, x1: float, y1: float
    ) -> bool:
        """True when a segment crosses any solid block (line-of-sight probe)."""
        if not self.blocks_enabled:
            return False
        return any(
            self._segment_hits_rect(x0, y0, x1, y1, block) for block in self.blocks
        )

    @staticmethod
    def _segment_hits_rect(
        x0: float, y0: float, x1: float, y1: float, rect: pygame.Rect
    ) -> bool:
        """Liang-Barsky segment/AABB intersection."""
        dx = x1 - x0
        dy = y1 - y0
        t0, t1 = 0.0, 1.0
        for p, q in (
            (-dx, x0 - rect.left),
            (dx, rect.right - x0),
            (-dy, y0 - rect.top),
            (dy, rect.bottom - y0),
        ):
            if abs(p) < 1e-9:
                if q < 0.0:
                    return False
                continue
            t = q / p
            if p < 0.0:
                if t > t1:
                    return False
                t0 = max(t0, t)
            else:
                if t < t0:
                    return False
                t1 = min(t1, t)
        return True

    def set_blocks_enabled(self, enabled: bool) -> None:
        self.blocks_enabled = bool(enabled)

    def toggle_blocks(self) -> bool:
        self.blocks_enabled = not self.blocks_enabled
        return self.blocks_enabled

    def ladder_for(self, fighter) -> Ladder | None:
        """Return the ladder whose trigger overlaps the fighter, if any."""
        if not self.ladders:
            return None
        body = self.body_rect(fighter)
        for ladder in self.ladders:
            if fighter.y < ladder.top_y - 2.0:
                continue
            if fighter.y > ladder.bottom_y + 2.0:
                continue
            # A fighter standing on the platform top has its feet exactly on
            # the trigger's top edge; colliderect() treats that as no overlap,
            # so allow a small tolerance for grabbing down.
            if body.right <= ladder.rect.left or body.left >= ladder.rect.right:
                continue
            if body.bottom < ladder.rect.top - 2.0:
                continue
            if body.top > ladder.rect.bottom:
                continue
            return ladder
        return None

    def draw(self, surface: pygame.Surface) -> None:
        surface.blit(self.background, (0, 0))
        if self.blocks_enabled:
            for block in self.block_specs:
                if block.kind == "platform":
                    self._draw_platform(surface, block)
            for block in self.block_specs:
                if block.kind == "barrier":
                    self._draw_barrier(surface, block.rect)
        # Ladders have no volume and stay visible while blocks are toggled off.
        for ladder in self.ladders:
            self._draw_ladder(surface, ladder)

    @staticmethod
    def _draw_barrier(surface: pygame.Surface, block: pygame.Rect) -> None:
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

    @staticmethod
    def _draw_platform(surface: pygame.Surface, block: Block) -> None:
        if block.surface is not None and block.sprite_rect is not None:
            surface.blit(block.surface, block.sprite_rect.topleft)
            return
        pygame.draw.rect(surface, (74, 112, 64), block.rect)
        pygame.draw.rect(surface, (128, 168, 96), block.rect.inflate(-6, -6), 2)
        pygame.draw.line(
            surface,
            (176, 210, 120),
            (block.rect.left + 4, block.rect.top + 2),
            (block.rect.right - 4, block.rect.top + 2),
            3,
        )

    @staticmethod
    def _draw_ladder(surface: pygame.Surface, ladder: Ladder) -> None:
        if ladder.surface is not None and ladder.sprite_rect is not None:
            surface.blit(ladder.surface, ladder.sprite_rect.topleft)
            return
        rail = 8
        left = ladder.rect.left + 8
        right = ladder.rect.right - 8 - rail
        top = ladder.rect.top
        bottom = ladder.rect.bottom
        pygame.draw.rect(surface, (128, 82, 40), (left, top, rail, bottom - top))
        pygame.draw.rect(surface, (128, 82, 40), (right, top, rail, bottom - top))
        rung_gap = 28
        for y in range(top + 16, bottom - 8, rung_gap):
            pygame.draw.rect(
                surface, (168, 112, 52), (left, y, right + rail - left, 5)
            )

    def draw_bounds(self, surface: pygame.Surface) -> None:
        """Debug-only wall/block/ladder outlines."""
        pygame.draw.line(surface, (255, 210, 80), (self.walls[0], 0), (self.walls[0], SCREEN_H), 1)
        pygame.draw.line(surface, (255, 210, 80), (self.walls[1], 0), (self.walls[1], SCREEN_H), 1)
        if self.blocks_enabled:
            for block in self.block_specs:
                color = (255, 210, 80) if block.kind == "barrier" else (90, 220, 255)
                pygame.draw.rect(surface, color, block.rect, 1)
        for ladder in self.ladders:
            pygame.draw.rect(surface, (255, 90, 220), ladder.rect, 1)
            pygame.draw.line(
                surface,
                (90, 255, 120),
                (ladder.rect.left, round(ladder.top_y)),
                (ladder.rect.right, round(ladder.top_y)),
                2,
            )
            pygame.draw.line(
                surface,
                (255, 90, 90),
                (ladder.rect.left, round(ladder.bottom_y)),
                (ladder.rect.right, round(ladder.bottom_y)),
                2,
            )

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
        if getattr(fighter, "ladder_fall", False):
            # Dropped from a ladder: the platform behind the ladder must not
            # shove the body sideways while it falls past the platform.
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

    def move_fighter(self, fighter, dt: float, apply_gravity: bool = True) -> None:
        """AABB movement against walls, ground and block top/side/bottom."""
        total_vx = fighter.vx + fighter.kb_vx
        self.move_x(fighter, total_vx * dt)

        previous_y = fighter.y
        if not fighter.on_ground and apply_gravity:
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

            # Full AABB: a rising body stops against the underside. A fighter
            # released from a ladder (jump/knock-off) ignores it until landing.
            if fighter.vy < 0.0 and not getattr(fighter, "ladder_fall", False):
                height = fighter.hurtbox_dims[1]
                half = self.body_half(fighter)
                previous_top = previous_y - height
                current_top = fighter.y - height
                for block in self.blocks:
                    if previous_top < block.bottom or current_top >= block.bottom:
                        continue
                    if fighter.x + half <= block.left or fighter.x - half >= block.right:
                        continue
                    fighter.y = float(block.bottom + height)
                    fighter.vy = 0.0
                    break

        fighter.on_ground = landed

    def resolve_overlap(self, fighter) -> bool:
        """Push a fighter out of a solid to the nearest free side.

        Used when blocks are re-enabled under a character. Climbers are
        skipped because they deliberately pass through solids.
        """
        if getattr(fighter, "climbing", False) or not self.blocks_enabled:
            return True
        for _ in range(4):
            body = self.body_rect(fighter)
            hit = next(
                (block for block in self.blocks if body.colliderect(block)),
                None,
            )
            if hit is None:
                return True
            half = self.body_half(fighter)
            height = fighter.hurtbox_dims[1]
            candidates = (
                (abs(hit.left - half - fighter.x), "x", hit.left - half),
                (abs(hit.right + half - fighter.x), "x", hit.right + half),
                (abs(hit.top - fighter.y), "top", float(hit.top)),
                (
                    abs(hit.bottom + height - fighter.y),
                    "bottom",
                    float(hit.bottom + height),
                ),
            )
            _, mode, value = min(candidates, key=lambda item: item[0])
            if mode == "x":
                fighter.x = value
                fighter.kb_vx = 0.0
                low, high = self.walls
                fighter.x = max(low + half, min(high - half, fighter.x))
            elif mode == "top":
                fighter.y = value
                fighter.vy = 0.0
                # A flyer pushed to a platform top must not start grounded;
                # its own flight update would clear this on the next tick.
                fighter.on_ground = not getattr(fighter, "flying", False)
            else:
                fighter.y = value
                fighter.vy = 0.0
                fighter.on_ground = False
        body = self.body_rect(fighter)
        return not any(body.colliderect(block) for block in self.blocks)
