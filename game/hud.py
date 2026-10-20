"""Minimal English combat HUD: HP, energy, Q/E cooldowns and flame timer."""

from __future__ import annotations

import pygame


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
    ) -> None:
        color = (70, 210, 140) if ready else (160, 160, 170)
        pygame.draw.rect(surface, (18, 20, 26), (x, y, w, h))
        pygame.draw.rect(surface, color, (x, y, w, h), 1)
        text = self.small.render(label, True, color)
        surface.blit(text, (x + (w - text.get_width()) // 2, y + (h - text.get_height()) // 2))

    def draw(self, surface: pygame.Surface, scene) -> None:
        lina = scene.lina
        dummy = scene.dummy

        panel = pygame.Surface((300, 142), pygame.SRCALPHA)
        panel.fill((8, 12, 18, 178))
        surface.blit(panel, (14, 14))

        surface.blit(self.big.render("LINA SEABRIGHT", True, (238, 238, 248)), (24, 20))
        self._bar(
            surface, 24, 52, 264, 18,
            lina.hp / lina.max_hp if lina.max_hp else 0.0,
            (218, 66, 58),
            f"HP {lina.hp:.0f}/{lina.max_hp:.0f}",
        )
        self._bar(
            surface, 24, 80, 264, 14,
            lina.energy / lina.max_energy if lina.max_energy else 0.0,
            (70, 210, 235),
            f"ENERGY {lina.energy:.0f}/{lina.max_energy:.0f}",
        )

        q_label = "Q READY" if lina.q_cd <= 0.0 else f"Q {lina.q_cd:.1f}s"
        if lina.e_cd > 0.0:
            e_label = f"E {lina.e_cd:.1f}s"
        elif lina.energy < lina.max_energy:
            e_label = "E NEED 100"
        else:
            e_label = "E READY"
        self._badge(surface, 24, 106, 126, 28, q_label, lina.q_cd <= 0.0)
        self._badge(
            surface, 158, 106, 130, 28, e_label,
            lina.e_cd <= 0.0 and lina.energy >= lina.max_energy,
        )

        if lina.flame_time > 0.0:
            flame = f"FLAME {lina.flame_time:.1f}s  +{lina.current_flame_bonus():.0%}"
            surface.blit(self.text.render(flame, True, (255, 168, 78)), (24, 138))
        else:
            surface.blit(self.text.render("FLAME -", True, (150, 150, 160)), (24, 138))

        label = self.small.render(
            f"DUMMY {dummy.hp:.0f}/{dummy.max_hp:.0f}",
            True,
            (240, 232, 220),
        )
        surface.blit(
            label,
            (round(dummy.x - label.get_width() * 0.5), round(dummy.y - 236)),
        )
