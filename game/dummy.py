"""Training dummy: no AI, takes hits, can be configured from the sandbox."""

from __future__ import annotations

import pygame

from .fighter import Fighter, FighterState


class Dummy(Fighter):
    name = "Dummy"

    def __init__(self, store, stage) -> None:
        cfg = store.stats["dummy"]
        x, y = stage.dummy_spawn
        super().__init__(
            x=x,
            y=y,
            facing=-1,
            anim=None,
            hurtbox_config={"standing": cfg["hurtbox"], "crouching": cfg["hurtbox"]},
            max_hp=cfg["hp"],
            stage=stage,
            gravity=store.stats["lina"]["move"]["gravity"],
            knockback_decay=store.stats["combat"]["knockback_decay"],
        )
        self.store = store
        self.spawn = (float(x), float(y))
        self.default_invincible = bool(cfg.get("invincible", False))
        self.reset()

    def reset(self) -> None:
        self.reset_common(self.spawn[0], self.spawn[1], -1)
        self.invincible = self.default_invincible

    def update(self, dt: float, scene) -> None:
        self.update_common(dt)
        if self.state == FighterState.HURT and self.hitstun <= 0.0 and self.hp > 0.0:
            self.state = FighterState.IDLE
        if self.state != FighterState.KO:
            self.stage.move_fighter(self, dt)

    def draw(self, surface: pygame.Surface) -> None:
        body_color = (112, 74, 46)
        if self.statuses.has("burn"):
            body_color = (156, 74, 36)
        elif self.statuses.has("poison"):
            phase = (pygame.time.get_ticks() // 150) % 2
            body_color = (120, 62, 152) if phase else (70, 150, 70)

        post = pygame.Rect(round(self.x - 28), round(self.y - 175), 56, 175)
        pygame.draw.rect(surface, body_color, post)
        pygame.draw.rect(surface, (66, 42, 26), post, 3)
        pygame.draw.rect(surface, (82, 54, 32), (post.left, post.top, post.width, 18))
        pygame.draw.line(
            surface,
            (78, 50, 30),
            (post.centerx, post.top + 18),
            (post.centerx, post.bottom - 4),
            3,
        )

        target_y = round(self.y - 120)
        pygame.draw.circle(surface, (224, 214, 192), (round(self.x), target_y), 21)
        pygame.draw.circle(surface, (196, 58, 48), (round(self.x), target_y), 21, 3)
        pygame.draw.circle(surface, (196, 58, 48), (round(self.x), target_y), 6)

        bar_width = 120
        bar_height = 10
        bar_x = round(self.x - bar_width * 0.5)
        bar_y = round(self.y - 215)
        pygame.draw.rect(surface, (20, 20, 20), (bar_x, bar_y, bar_width, bar_height))
        fill = max(0.0, min(1.0, self.hp / self.max_hp))
        pygame.draw.rect(
            surface,
            (214, 70, 58),
            (bar_x + 1, bar_y + 1, round((bar_width - 2) * fill), bar_height - 2),
        )
        if self.invincible:
            pygame.draw.rect(surface, (120, 220, 255), (bar_x, bar_y, bar_width, bar_height), 1)
        if self.flash > 0.0:
            pygame.draw.rect(surface, (255, 255, 255), self.hurtbox(), 2)
