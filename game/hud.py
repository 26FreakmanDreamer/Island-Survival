"""Minimal English combat HUD: HP, energy, Q/E cooldowns and flame timer."""

from __future__ import annotations

import pygame

from .config import SCREEN_W


def _font(size: int, bold: bool = False) -> pygame.font.Font:
    try:
        return pygame.font.SysFont("consolas", size, bold=bold)
    except Exception:  # noqa: BLE001 - fall back to the default font
        return pygame.font.Font(None, size)


class HUD:
    def __init__(self) -> None:
        self.big = _font(21, bold=True)
        self.text = _font(15)
        self.small = _font(13)

    def _bar(
        self,
        surface: pygame.Surface,
        x: int,
        y: int,
        w: int,
        h: int,
        ratio: float,
        color: tuple[int, int, int],
        label: str,
    ) -> None:
        pygame.draw.rect(surface, (18, 20, 26), (x, y, w, h))
        fill = max(0, min(w - 2, round((w - 2) * max(0.0, min(1.0, ratio)))))
        if fill > 0:
            pygame.draw.rect(surface, color, (x + 1, y + 1, fill, h - 2))
        pygame.draw.rect(surface, (220, 224, 235), (x, y, w, h), 1)
        text = self.small.render(label, True, (245, 245, 250))
        surface.blit(text, (x + 6, y + (h - text.get_height()) // 2 - 1))

    def _badge(
        self,
        surface: pygame.Surface,
        x: int,
        y: int,
        w: int,
        h: int,
        label: str,
        ready: bool,
        color: tuple[int, int, int] | None = None,
    ) -> None:
        if color is None:
            color = (70, 210, 140) if ready else (160, 160, 170)
        pygame.draw.rect(surface, (18, 20, 26), (x, y, w, h))
        pygame.draw.rect(surface, color, (x, y, w, h), 1)
        text = self.small.render(label, True, color)
        surface.blit(text, (x + (w - text.get_width()) // 2, y + (h - text.get_height()) // 2))

    def draw(self, surface: pygame.Surface, scene) -> None:
        player = scene.player
        enemy = scene.enemy

        panel = pygame.Surface((300, 142), pygame.SRCALPHA)
        panel.fill((8, 12, 18, 178))
        surface.blit(panel, (14, 14))

        surface.blit(self.big.render(player.name.upper(), True, (238, 238, 248)), (24, 20))
        self._bar(
            surface, 24, 52, 264, 18,
            player.hp / player.max_hp if player.max_hp else 0.0,
            (218, 66, 58),
            f"HP {player.hp:.0f}/{player.max_hp:.0f}",
        )
        has_energy = hasattr(player, "energy") and hasattr(player, "max_energy")
        if has_energy:
            self._bar(
                surface, 24, 80, 264, 14,
                player.energy / player.max_energy if player.max_energy else 0.0,
                (70, 210, 235),
                f"ENERGY {player.energy:.0f}/{player.max_energy:.0f}",
            )

        if hasattr(player, "q_cd") and hasattr(player, "e_cd"):
            q_label = "Q READY" if player.q_cd <= 0.0 else f"Q {player.q_cd:.1f}s"
            e_phase = getattr(player, "e_phase", None)
            e_window = getattr(player, "e_window", 0.0)
            e_color = None
            if e_phase == "window":
                e_label = f"E RETURN {e_window:.1f}s"
                e_ready = False
                e_color = (235, 180, 70)
            elif e_phase is not None:
                e_label = "E ACTIVE"
                e_ready = False
                e_color = (235, 180, 70)
            elif player.e_cd > 0.0:
                e_label = f"E {player.e_cd:.1f}s"
                e_ready = False
            elif has_energy and player.energy < player.max_energy:
                e_label = "E NEED 100"
                e_ready = False
            else:
                e_label = "E READY"
                e_ready = True
            e_ready = e_ready and player.e_cd <= 0.0
            self._badge(surface, 24, 106, 126, 28, q_label, player.q_cd <= 0.0)
            self._badge(
                surface, 158, 106, 130, 28, e_label, e_ready, e_color
            )

        if hasattr(player, "flame_time") and hasattr(player, "current_flame_bonus"):
            if player.flame_time > 0.0:
                flame = f"FLAME {player.flame_time:.1f}s  +{player.current_flame_bonus():.0%}"
                surface.blit(self.text.render(flame, True, (255, 168, 78)), (24, 138))
            else:
                surface.blit(self.text.render("FLAME -", True, (150, 150, 160)), (24, 138))

        if getattr(scene, "lock_on", False):
            hint = self.text.render("LOCK-ON  (MMB)", True, (255, 210, 80))
            surface.blit(hint, (24, 160))

        label = self.small.render(
            f"{enemy.name.upper()} {enemy.hp:.0f}/{enemy.max_hp:.0f}",
            True,
            (240, 232, 220),
        )
        lift = (
            enemy.health_bar_lift
            if getattr(enemy, "health_bar_lift", None) is not None
            else enemy.hurtbox_dims[1]
        )
        label_y = round(enemy.y - lift - 46.0)
        surface.blit(
            label,
            (round(enemy.x - label.get_width() * 0.5), label_y),
        )

        if not scene.stage.blocks_enabled:
            hint = self.text.render("BLOCKS OFF  (B)", True, (255, 210, 80))
            surface.blit(hint, (SCREEN_W // 2 - hint.get_width() // 2, 18))

        self.draw_result(surface, scene)

    def draw_result(self, surface: pygame.Surface, scene) -> None:
        if scene.match_over is None:
            return

        band = pygame.Surface((SCREEN_W, 130), pygame.SRCALPHA)
        band.fill((8, 10, 16, 190))
        surface.blit(band, (0, 210))

        if scene.match_over == "WIN":
            title, color = "VICTORY", (110, 235, 150)
        else:
            title, color = "DEFEATED", (240, 90, 80)

        image = self.big.render(title, True, color)
        surface.blit(image, (SCREEN_W // 2 - image.get_width() // 2, 236))
        hint = self.text.render("R Restart    F9 Reset", True, (230, 230, 240))
        surface.blit(hint, (SCREEN_W // 2 - hint.get_width() // 2, 282))
