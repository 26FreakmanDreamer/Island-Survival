"""Island Survival — Lina Seabright combat sandbox entry point."""

from __future__ import annotations

import os
import sys

import pygame

from game.config import FIXED_DT, SCREEN_H, SCREEN_W, JsonStore
from game.scene import DEBUG_KEYS, ArenaScene


def _font(size: int, bold: bool = False) -> pygame.font.Font:
    try:
        return pygame.font.SysFont("consolas", size, bold=bold)
    except Exception:  # noqa: BLE001
        return pygame.font.Font(None, size)


def _draw_pause(surface: pygame.Surface, big: pygame.font.Font, text: pygame.font.Font) -> None:
    overlay = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 178))
    surface.blit(overlay, (0, 0))

    title = big.render("PAUSED", True, (242, 242, 250))
    surface.blit(title, (SCREEN_W // 2 - title.get_width() // 2, 230))
    lines = [
        "Esc  Resume",
        "R    Restart",
        "Q    Quit",
        "F4   Step one tick",
        "F1/F2/F5-F12   Debug controls",
    ]
    for index, line in enumerate(lines):
        image = text.render(line, True, (224, 224, 234))
        surface.blit(image, (SCREEN_W // 2 - image.get_width() // 2, 300 + index * 30))


def _smoke_test(scene: ArenaScene, screen: pygame.Surface) -> int:
    for _ in range(30):
        scene.tick(FIXED_DT)

    scene.dummy.x = scene.lina.x + 80.0
    scene.input.buffer.press("punch")
    for _ in range(40):
        scene.tick(FIXED_DT)
        scene.draw(screen)

    damaged = scene.dummy.hp < scene.dummy.max_hp
    gained = scene.lina.energy > 0.0
    punch_hp = scene.dummy.hp
    punch_energy = scene.lina.energy

    # A second kick pressed during the first kick must queue, not be dropped.
    scene.reset()
    scene.dummy.x = scene.lina.x + 80.0
    scene.input.buffer.press("kick")
    scene.tick(FIXED_DT)
    scene.input.buffer.press("kick")
    for _ in range(90):
        scene.tick(FIXED_DT)
    queued_kick_ok = scene.dummy.hp <= scene.dummy.max_hp - 60.0

    # A lunge next to a block must not embed Lina in it.
    scene.reset()
    block = scene.stage.blocks[0]
    scene.lina.x = block.left - scene.lina.stage_half_width
    scene.input.mouse_down(1)
    for _ in range(30):
        scene.tick(FIXED_DT)
    scene.input.mouse_up(1)
    block_lunge_ok = scene.lina.x <= block.left - scene.lina.stage_half_width + 0.5

    # Q must spawn at fist height relative to Lina's feet, including on a block.
    scene.reset()
    scene.lina.x = float(block.centerx)
    scene.lina.y = float(block.top)
    scene.lina.on_ground = True
    scene.dummy.x = 800.0
    expected_lane_y = scene.stage.lane_y("fist", scene.lina.y)
    scene.input.buffer.press("q")
    q_block_ok = False
    for _ in range(30):
        scene.tick(FIXED_DT)
        if scene.projectiles:
            q_block_ok = abs(scene.projectiles[0].y - expected_lane_y) < 0.5
            break

    scene.reset()
    scene.lina.energy = scene.lina.max_energy
    scene.input.buffer.press("e")
    for _ in range(60):
        scene.tick(FIXED_DT)
    scene.draw(screen)
    flame_ok = scene.lina.anim.variant == "flame" and scene.lina.flame_time > 0.0

    print(
        "SMOKE "
        f"ticks={scene.tick_count} "
        f"punch_hp={punch_hp:.1f} "
        f"punch_energy={punch_energy:.1f} "
        f"damaged={damaged} gained={gained} queued_kick_ok={queued_kick_ok} "
        f"block_lunge_ok={block_lunge_ok} q_block_ok={q_block_ok} "
        f"flame_ok={flame_ok} missing_frames={len(scene.lina.anim.missing)}"
    )
    return 0 if (
        damaged
        and gained
        and queued_kick_ok
        and block_lunge_ok
        and q_block_ok
        and flame_ok
    ) else 1


def main() -> int:
    smoke = "--smoke-test" in sys.argv
    if smoke:
        os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

    store = JsonStore()
    if not store.last_ok:
        print("CONFIG ERROR:", store.last_error)
        return 1

    pygame.init()
    # A Chinese IME can swallow gameplay keys while composing text.
    pygame.key.stop_text_input()
    pygame.display.set_caption("Island Survival - Lina Combat Sandbox")
    screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
    clock = pygame.time.Clock()

    scene = ArenaScene(store)

    if smoke:
        code = _smoke_test(scene, screen)
        pygame.quit()
        return code

    paused = False
    frame_step = False
    accumulator = 0.0
    running = True
    big_font = _font(34, bold=True)
    pause_font = _font(20)

    while running:
        real_dt = min(clock.tick(60) / 1000.0, 0.25)
        scene.fps = clock.get_fps()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    paused = not paused
                    frame_step = False
                    scene.input.clear()
                    accumulator = 0.0
                    if not paused:
                        scene.input.sync_held(pygame.key.get_pressed())
                    continue

                if paused:
                    if event.key == pygame.K_F3:
                        paused = False
                        frame_step = False
                        scene.input.clear()
                        scene.input.sync_held(pygame.key.get_pressed())
                        accumulator = 0.0
                    elif event.key == pygame.K_r:
                        scene.reset()
                        scene.input.sync_held(pygame.key.get_pressed())
                        accumulator = 0.0
                    elif event.key == pygame.K_q:
                        running = False
                    elif event.key == pygame.K_F4:
                        scene.tick(FIXED_DT)
                    elif event.key in DEBUG_KEYS:
                        scene.handle_debug_key(event.key)
                        scene.input.sync_held(pygame.key.get_pressed())
                    continue

                if event.key == pygame.K_F3:
                    paused = True
                    frame_step = False
                    scene.input.clear()
                    accumulator = 0.0
                elif event.key == pygame.K_F4:
                    paused = True
                    frame_step = False
                    scene.tick(FIXED_DT)
                    accumulator = 0.0
                elif event.key in DEBUG_KEYS:
                    scene.handle_debug_key(event.key)
                    scene.input.sync_held(pygame.key.get_pressed())
                else:
                    scene.input.key_down(event.key)
            elif event.type == pygame.KEYUP:
                scene.input.key_up(event.key)
            elif event.type == pygame.MOUSEBUTTONDOWN:
                scene.input.mouse_down(event.button)
            elif event.type == pygame.MOUSEBUTTONUP:
                scene.input.mouse_up(event.button)
            elif event.type == pygame.WINDOWFOCUSLOST:
                scene.input.clear()
            elif event.type == pygame.WINDOWFOCUSGAINED:
                scene.input.sync_held(pygame.key.get_pressed())

        if not paused:
            accumulator += real_dt * scene.time_scale
            steps = 0
            while accumulator >= FIXED_DT and steps < 5:
                scene.tick(FIXED_DT)
                accumulator -= FIXED_DT
                steps += 1
            if steps == 5:
                accumulator = 0.0
        elif frame_step:
            scene.tick(FIXED_DT)
            frame_step = False

        scene.draw(screen)
        if paused:
            _draw_pause(screen, big_font, pause_font)
        pygame.display.flip()

    pygame.quit()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
