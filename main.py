"""Island Survival — Lina Seabright combat sandbox entry point."""

from __future__ import annotations

import os
import sys

import pygame

from game.config import FIXED_DT, SCREEN_H, SCREEN_W, JsonStore
from game.fighter import FighterState
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
        "F7/F8  Enemy mode / AI",
        "C/X    Dash / throw",
        "V      Force Warrior axe",
        "B      Toggle blocks",
    ]
    for index, line in enumerate(lines):
        image = text.render(line, True, (224, 224, 234))
        surface.blit(image, (SCREEN_W // 2 - image.get_width() // 2, 300 + index * 30))


def _smoke_test(scene: ArenaScene, screen: pygame.Surface) -> int:
    # --- Phase A: Lina regression checks against the training dummy ---
    scene.set_enemy_mode("dummy")
    scene.reset()

    for _ in range(30):
        scene.tick(FIXED_DT)

    scene.enemy.x = scene.lina.x + 80.0
    scene.input.buffer.press("punch")
    for _ in range(40):
        scene.tick(FIXED_DT)
        scene.draw(screen)

    damaged = scene.enemy.hp < scene.enemy.max_hp
    gained = scene.lina.energy > 0.0
    punch_hp = scene.enemy.hp
    punch_energy = scene.lina.energy

    # A second kick pressed during the first kick must queue, not be dropped.
    scene.reset()
    scene.enemy.x = scene.lina.x + 80.0
    scene.input.buffer.press("kick")
    scene.tick(FIXED_DT)
    scene.input.buffer.press("kick")
    for _ in range(90):
        scene.tick(FIXED_DT)
    queued_kick_ok = scene.enemy.hp <= scene.enemy.max_hp - 60.0

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
    scene.enemy.x = 800.0
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
    missing_frames = len(scene.lina.anim.missing_paths())

    # --- Phase B: Warrior target, attacks, armor and match flow ---
    scene.set_enemy_mode("warrior")
    scene.reset()
    warrior = scene.enemy
    warrior_present = warrior.name == "Warrior" and warrior.max_hp == 300.0
    warrior.ai_enabled = False

    scene.lina.x = warrior.x - 80.0
    scene.lina.facing = 1
    scene.input.buffer.press("punch")
    for _ in range(40):
        scene.tick(FIXED_DT)
    warrior_hp = warrior.hp
    warrior_hurt_ok = warrior.hp < warrior.max_hp

    # Startup/active hits are armored: damage lands but the swing continues.
    scene.reset()
    warrior = scene.enemy
    warrior.ai_enabled = False
    scene.lina.x = warrior.x + 80.0
    scene.lina.facing = -1
    warrior.facing = 1
    warrior.start_attack("axe_slash", scene, scene.lina)
    scene.lina.start_attack("punch_r", scene, warrior)
    for _ in range(8):
        scene.tick(FIXED_DT)
    super_armor_ok = (
        warrior.hp < warrior.max_hp
        and warrior.state == FighterState.ATTACK
        and warrior.attack_runtime is not None
        and warrior.hitstun == 0.0
        and warrior.kb_vx == 0.0
    )

    # Recovery is interruptible: wait until the armor window is over.
    for _ in range(60):
        scene.tick(FIXED_DT)
        runtime = warrior.attack_runtime
        if runtime is not None and runtime.time >= 0.56:
            break
    warrior.take_hit(10.0, 0.0, 0.2, -1)
    armor_interrupt_ok = (
        warrior.state == FighterState.HURT and warrior.attack_runtime is None
    )

    # Warrior axe hits Lina.
    scene.reset()
    warrior = scene.enemy
    warrior.ai_enabled = False
    scene.lina.x = warrior.x - 80.0
    warrior.facing = -1
    warrior.start_attack("axe_slash", scene, scene.lina)
    for _ in range(70):
        scene.tick(FIXED_DT)
    warrior_attack_ok = scene.lina.hp < scene.lina.max_hp

    # Lina at 10 HP is KO'd by one axe hit -> LOSE.
    scene.reset()
    warrior = scene.enemy
    warrior.ai_enabled = False
    scene.lina.hp = 10.0
    scene.lina.x = warrior.x - 80.0
    warrior.facing = -1
    warrior.start_attack("axe_slash", scene, scene.lina)
    for _ in range(70):
        scene.tick(FIXED_DT)
    lose_ok = scene.lina.state == FighterState.KO and scene.match_over == "LOSE"

    # Warrior at 20 HP is KO'd by one punch -> WIN.
    scene.reset()
    warrior = scene.enemy
    warrior.ai_enabled = False
    warrior.hp = 20.0
    scene.lina.x = warrior.x - 80.0
    scene.lina.facing = 1
    scene.lina.start_attack("punch_r", scene, warrior)
    for _ in range(30):
        scene.tick(FIXED_DT)
    win_ok = warrior.hp <= 0.0 and scene.match_over == "WIN"

    scene.reset()
    reset_ok = (
        scene.lina.hp == scene.lina.max_hp
        and scene.enemy.hp == scene.enemy.max_hp
        and scene.match_over is None
    )

    # Bodies must separate instead of stacking; facing must stay stable.
    scene.reset()
    warrior = scene.enemy
    lina = scene.lina
    lina.x = 950.0
    lina.y = scene.stage.ground_y
    lina.on_ground = True
    warrior.x = 950.0
    warrior.y = scene.stage.ground_y
    warrior.on_ground = True
    warrior.attack_cd = 999.0
    warrior.dash_cd = 999.0
    warrior.throw_cd = 999.0
    last_facing = warrior.facing
    facing_flips = 0
    for _ in range(60):
        scene.tick(FIXED_DT)
        if warrior.facing != last_facing:
            facing_flips += 1
            last_facing = warrior.facing
    overlap_ok = abs(warrior.x - lina.x) >= 100.0 and facing_flips <= 1

    # A hit during the transform must not leave Lina invisible.
    scene.reset()
    warrior = scene.enemy
    lina = scene.lina
    warrior.ai_enabled = False
    lina.energy = lina.max_energy
    lina.start_transform()
    lina.x = warrior.x - 120.0
    warrior.facing = -1
    warrior.start_attack("axe_slash", scene, lina)
    transform_hit_ok = False
    for _ in range(40):
        scene.tick(FIXED_DT)
        if lina.state == FighterState.HURT:
            transform_hit_ok = (
                lina.anim.variant == "flame"
                and lina.anim.current_is_flame_frame
                and lina.hp < lina.max_hp
            )
            break

    # Flame expiry must play the 2-frame revert before returning to normal.
    scene.reset()
    lina = scene.lina
    lina.anim.set_variant("flame")
    lina.anim.set_clip("idle", reset=True)
    lina.flame_time = 0.001
    scene.tick(FIXED_DT)
    revert_started = (
        lina.state == FighterState.TRANSFORM
        and lina.anim.clip_name == "revert"
        and lina.anim.current_is_flame_frame
    )
    for _ in range(30):
        scene.tick(FIXED_DT)
        if lina.state != FighterState.TRANSFORM:
            break
    revert_ok = (
        revert_started
        and lina.state == FighterState.IDLE
        and lina.anim.variant == "normal"
        and lina.anim.clip_name == "idle"
    )
    flame_frames = {
        rel
        for clip in lina.anim.flame_clips.values()
        for rel in clip.get("frames", [])
    }
    flame_offset_ok = bool(flame_frames) and flame_frames.issubset(
        lina.anim.frame_offsets
    )

    # A skill must leave a gap before the AI may start another skill.
    scene.reset()
    warrior = scene.enemy
    warrior.ai_enabled = False
    scene.lina.x = warrior.x - 80.0
    warrior.facing = -1
    warrior.start_attack("axe_slash", scene, scene.lina)
    for _ in range(60):
        scene.tick(FIXED_DT)
        if warrior.state != FighterState.ATTACK:
            break
    gap_started = warrior.skill_cd > 0.0
    scene.lina.x = warrior.x - 80.0
    scene.lina.hp = scene.lina.max_hp
    warrior.ai_enabled = True
    scene.tick(FIXED_DT)
    no_attack_in_gap = warrior.state != FighterState.ATTACK
    for _ in range(70):
        scene.tick(FIXED_DT)
        if warrior.state == FighterState.ATTACK:
            break
    skill_gap_ok = (
        gap_started
        and no_attack_in_gap
        and warrior.state == FighterState.ATTACK
    )

    # AI must approach, cross a block and land a hit.
    scene.reset()
    warrior = scene.enemy
    scene.lina.x = 300.0
    warrior.x = 600.0
    warrior.y = scene.stage.ground_y
    warrior.on_ground = True
    # Keep this legacy check on the jump/slash path; dash/throw are tested below.
    warrior.dash_cd = 999.0
    warrior.throw_cd = 999.0
    start_x = warrior.x
    saw_air = False
    saw_attack = False
    for _ in range(360):
        scene.tick(FIXED_DT)
        saw_air = saw_air or warrior.state == FighterState.AIR
        saw_attack = saw_attack or warrior.state == FighterState.ATTACK
        if scene.lina.hp < scene.lina.max_hp:
            break
    ai_ok = (
        warrior.x < start_x
        and saw_air
        and saw_attack
        and scene.lina.hp < scene.lina.max_hp
    )

    # Dash: 30 damage plus a 1.5s knock-up. Blocks off to keep the path clear.
    scene.reset()
    scene.stage.set_blocks_enabled(False)
    warrior = scene.enemy
    warrior.ai_enabled = False
    scene.lina.x = warrior.x - 200.0
    warrior.force_attack(scene, scene.lina, "dash")
    launched = False
    for _ in range(40):
        scene.tick(FIXED_DT)
        launched = launched or scene.lina.vy < 0.0 or scene.lina.y < scene.stage.ground_y
    dash_ok = (
        abs(scene.lina.hp - 70.0) < 0.01
        and scene.lina.statuses.has("knock_up")
        and launched
    )
    scene.stage.set_blocks_enabled(True)

    # Throw: high lane, one hit out and one back, then returns to the hand.
    scene.reset()
    scene.stage.set_blocks_enabled(False)
    warrior = scene.enemy
    warrior.ai_enabled = False
    scene.lina.x = warrior.x - 300.0
    warrior.force_attack(scene, scene.lina, "axe_throw")
    saw_axe = False
    for _ in range(130):
        scene.tick(FIXED_DT)
        if any(getattr(p, "kind", "") == "axe_throw" for p in scene.projectiles):
            saw_axe = True
    throw_ok = saw_axe and scene.lina.hp <= 70.0 + 0.01
    throw_return_ok = saw_axe and not any(
        getattr(p, "kind", "") == "axe_throw" for p in scene.projectiles
    )
    scene.stage.set_blocks_enabled(True)

    # The throw lane is relative to the Warrior's feet, including on a block.
    scene.reset()
    warrior = scene.enemy
    warrior.ai_enabled = False
    lane_block = scene.stage.blocks[0]
    warrior.x = float(lane_block.centerx)
    warrior.y = float(lane_block.top)
    warrior.on_ground = True
    scene.lina.x = 600.0
    scene.lina.y = scene.stage.ground_y
    warrior.facing = 1
    warrior.force_attack(scene, scene.lina, "axe_throw")
    expected_lane_y = scene.stage.lane_y("high", warrior.y)
    throw_lane_ok = False
    for _ in range(30):
        scene.tick(FIXED_DT)
        axes = [p for p in scene.projectiles if getattr(p, "kind", "") == "axe_throw"]
        if axes:
            throw_lane_ok = abs(axes[0].y - expected_lane_y) < 0.5
            break

    # AI should throw over a block when the target is in throw range.
    scene.reset()
    warrior = scene.enemy
    scene.lina.x = 300.0
    warrior.x = 600.0
    warrior.y = scene.stage.ground_y
    warrior.on_ground = True
    warrior.dash_cd = 999.0
    saw_axe = False
    for _ in range(180):
        scene.tick(FIXED_DT)
        if any(getattr(p, "kind", "") == "axe_throw" for p in scene.projectiles):
            saw_axe = True
        if scene.lina.hp < scene.lina.max_hp:
            break
    ai_ranged_ok = saw_axe and scene.lina.hp < scene.lina.max_hp

    # B toggles block collision/visibility; with blocks off, Lina can pass one.
    block = scene.stage.blocks[0]
    scene.stage.set_blocks_enabled(False)
    scene.lina.x = block.left - scene.lina.stage_half_width
    scene.stage.move_x(scene.lina, 200.0)
    blocks_pass_ok = scene.lina.x > block.right
    scene.stage.set_blocks_enabled(True)
    blocks_toggle_ok = blocks_pass_ok and scene.stage.blocks_enabled

    scene.set_enemy_mode("dummy")
    dummy_ok = scene.enemy.name == "Dummy"
    scene.set_enemy_mode("warrior")
    switch_ok = (
        dummy_ok
        and scene.enemy.name == "Warrior"
        and scene.enemy.max_hp == 300.0
    )
    warrior_missing = len(scene.enemy.anim.missing_paths())
    scene.draw(screen)

    print(
        "SMOKE "
        f"ticks={scene.tick_count} "
        f"punch_hp={punch_hp:.1f} "
        f"punch_energy={punch_energy:.1f} "
        f"damaged={damaged} gained={gained} queued_kick_ok={queued_kick_ok} "
        f"block_lunge_ok={block_lunge_ok} q_block_ok={q_block_ok} "
        f"flame_ok={flame_ok} missing_frames={missing_frames} "
        f"warrior_present={warrior_present} warrior_hp={warrior_hp:.1f} "
        f"warrior_hurt_ok={warrior_hurt_ok} super_armor_ok={super_armor_ok} "
        f"armor_interrupt_ok={armor_interrupt_ok} "
        f"warrior_attack_ok={warrior_attack_ok} lose_ok={lose_ok} win_ok={win_ok} "
        f"ai_ok={ai_ok} switch_ok={switch_ok} reset_ok={reset_ok} "
        f"overlap_ok={overlap_ok} transform_hit_ok={transform_hit_ok} "
        f"revert_ok={revert_ok} flame_offset_ok={flame_offset_ok} "
        f"skill_gap_ok={skill_gap_ok} blocks_toggle_ok={blocks_toggle_ok} "
        f"dash_ok={dash_ok} throw_ok={throw_ok} throw_return_ok={throw_return_ok} "
        f"throw_lane_ok={throw_lane_ok} ai_ranged_ok={ai_ranged_ok} "
        f"warrior_missing_frames={warrior_missing}"
    )
    return 0 if (
        damaged
        and gained
        and queued_kick_ok
        and block_lunge_ok
        and q_block_ok
        and flame_ok
        and warrior_present
        and warrior_hurt_ok
        and super_armor_ok
        and armor_interrupt_ok
        and warrior_attack_ok
        and lose_ok
        and win_ok
        and ai_ok
        and switch_ok
        and reset_ok
        and overlap_ok
        and transform_hit_ok
        and revert_ok
        and flame_offset_ok
        and skill_gap_ok
        and blocks_toggle_ok
        and dash_ok
        and throw_ok
        and throw_return_ok
        and throw_lane_ok
        and ai_ranged_ok
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
    pygame.display.set_caption("Island Survival - Warrior Combat Sandbox")
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
                elif event.key == pygame.K_r and scene.match_over is not None:
                    scene.reset()
                    scene.input.sync_held(pygame.key.get_pressed())
                    accumulator = 0.0
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
