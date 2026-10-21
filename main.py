"""Island Survival — Lina Seabright combat sandbox entry point."""

from __future__ import annotations

import os
import sys

import pygame

from game.combat import resolve_hit
from game.config import FIXED_DT, SCREEN_H, SCREEN_W, JsonStore
from game.fighter import FighterState
from game.particles import knock_up_vortex_intensity
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
        "F7 / [ ]  Enemy / character",
        "F8     AI / invincibility",
        "V/C/X/Z  Skill slots 1-4",
        "MMB    Attack lock-on (default off)",
        "B      Toggle blocks",
    ]
    for index, line in enumerate(lines):
        image = text.render(line, True, (224, 224, 234))
        surface.blit(image, (SCREEN_W // 2 - image.get_width() // 2, 300 + index * 30))


def _smoke_test(scene: ArenaScene, screen: pygame.Surface) -> int:
    # --- Phase A: Lina regression checks against the training dummy ---
    scene.set_enemy("dummy")
    scene.reset()

    for _ in range(30):
        scene.tick(FIXED_DT)

    scene.enemy.x = scene.player.x + 80.0
    scene.input.buffer.press("punch")
    for _ in range(40):
        scene.tick(FIXED_DT)
        scene.draw(screen)

    damaged = scene.enemy.hp < scene.enemy.max_hp
    gained = scene.player.energy > 0.0
    punch_hp = scene.enemy.hp
    punch_damage_ok = abs(punch_hp - 980.0) < 0.01
    punch_energy = scene.player.energy

    # Middle-mouse lock-on: attacks face the enemy; default is off.
    lock_default_off = not scene.lock_on
    scene.reset()
    scene.enemy.x = scene.player.x - 80.0
    scene.player.facing = 1
    scene.toggle_lock_on()
    scene.input.buffer.press("punch")
    for _ in range(30):
        scene.tick(FIXED_DT)
    lock_on_ok = (
        scene.player.facing == -1 and scene.enemy.hp < scene.enemy.max_hp
    )
    scene.reset()
    scene.enemy.x = scene.player.x - 80.0
    scene.player.facing = 1
    scene.toggle_lock_on()
    scene.input.buffer.press("punch")
    for _ in range(30):
        scene.tick(FIXED_DT)
    lock_off_ok = (
        scene.player.facing == 1 and scene.enemy.hp == scene.enemy.max_hp
    )
    lock_ok = lock_default_off and lock_on_ok and lock_off_ok

    # A second kick pressed during the first kick must queue, not be dropped.
    scene.reset()
    scene.enemy.x = scene.player.x + 80.0
    scene.input.buffer.press("kick")
    scene.tick(FIXED_DT)
    scene.input.buffer.press("kick")
    for _ in range(90):
        scene.tick(FIXED_DT)
    kick_damage_ok = abs(scene.enemy.hp - (scene.enemy.max_hp - 48.0)) < 0.01
    kick_energy_ok = abs(scene.player.energy - 40.0) < 0.01
    queued_kick_ok = scene.enemy.hp <= scene.enemy.max_hp - 48.0

    # A lunge next to a block must not embed Lina in it.
    scene.reset()
    block = scene.stage.blocks[0]
    scene.player.x = block.left - scene.player.stage_half_width
    scene.input.mouse_down(1)
    for _ in range(30):
        scene.tick(FIXED_DT)
    scene.input.mouse_up(1)
    block_lunge_ok = scene.player.x <= block.left - scene.player.stage_half_width + 0.5

    # Q must spawn at fist height relative to Lina's feet, including on a block.
    scene.reset()
    scene.player.x = float(block.centerx)
    scene.player.y = float(block.top)
    scene.player.on_ground = True
    scene.enemy.x = 800.0
    expected_lane_y = scene.stage.lane_y("fist", scene.player.y)
    scene.input.buffer.press("q")
    q_block_ok = False
    for _ in range(30):
        scene.tick(FIXED_DT)
        if scene.projectiles:
            q_block_ok = abs(scene.projectiles[0].y - expected_lane_y) < 0.5
            break

    # Q damage follows the docx basic + 1.5*extra formula (20 at 20/0).
    scene.reset()
    scene.enemy.x = scene.player.x + 200.0
    scene.player.facing = 1
    scene.input.buffer.press("q")
    for _ in range(45):
        scene.tick(FIXED_DT)
    q_damage_ok = abs(scene.enemy.hp - (scene.enemy.max_hp - 20.0)) < 0.01

    scene.reset()
    scene.player.energy = scene.player.max_energy
    scene.input.buffer.press("e")
    for _ in range(60):
        scene.tick(FIXED_DT)
    scene.draw(screen)
    flame_ok = scene.player.anim.variant == "flame" and scene.player.flame_time > 0.0
    missing_frames = len(scene.player.anim.missing_paths())

    # --- Phase B: Warrior target, attacks, armor and match flow ---
    scene.set_enemy("warrior")
    scene.reset()
    warrior = scene.enemy
    warrior_present = (
        warrior.name == "Warrior"
        and warrior.max_hp == 300.0
        and warrior.basic_atk == 20.0
    )
    warrior.ai_enabled = False

    scene.player.x = warrior.x - 80.0
    scene.player.facing = 1
    scene.input.buffer.press("punch")
    for _ in range(40):
        scene.tick(FIXED_DT)
    warrior_hp = warrior.hp
    warrior_hurt_ok = warrior.hp < warrior.max_hp

    # Startup/active hits are armored: damage lands but the swing continues.
    scene.reset()
    warrior = scene.enemy
    warrior.ai_enabled = False
    scene.player.x = warrior.x + 80.0
    scene.player.facing = -1
    warrior.facing = 1
    warrior.start_attack("axe_slash", scene, scene.player)
    scene.player.start_attack("punch_r", scene, warrior)
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
    scene.player.x = warrior.x - 80.0
    warrior.facing = -1
    warrior.start_attack("axe_slash", scene, scene.player)
    for _ in range(70):
        scene.tick(FIXED_DT)
    warrior_attack_ok = scene.player.hp < scene.player.max_hp
    axe_slash_damage_ok = abs(scene.player.hp - 76.0) < 0.01

    # Lina at 10 HP is KO'd by one axe hit -> LOSE.
    scene.reset()
    warrior = scene.enemy
    warrior.ai_enabled = False
    scene.player.hp = 10.0
    scene.player.x = warrior.x - 80.0
    warrior.facing = -1
    warrior.start_attack("axe_slash", scene, scene.player)
    for _ in range(70):
        scene.tick(FIXED_DT)
    lose_ok = scene.player.state == FighterState.KO and scene.match_over == "LOSE"

    # Warrior at 20 HP is KO'd by one punch -> WIN.
    scene.reset()
    warrior = scene.enemy
    warrior.ai_enabled = False
    warrior.hp = 20.0
    scene.player.x = warrior.x - 80.0
    scene.player.facing = 1
    scene.player.start_attack("punch_r", scene, warrior)
    for _ in range(30):
        scene.tick(FIXED_DT)
    win_ok = warrior.hp <= 0.0 and scene.match_over == "WIN"

    scene.reset()
    reset_ok = (
        scene.player.hp == scene.player.max_hp
        and scene.enemy.hp == scene.enemy.max_hp
        and scene.match_over is None
    )

    # Bodies must separate instead of stacking; facing must stay stable.
    scene.reset()
    warrior = scene.enemy
    lina = scene.player
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
    overlap_ok = abs(warrior.x - lina.x) >= 109.5 and facing_flips <= 1

    # Near a block, the enemy must not flip across the player.
    scene.reset()
    warrior = scene.enemy
    warrior.ai_enabled = False
    scene.player.x = 300.0
    scene.player.y = scene.stage.ground_y
    scene.player.on_ground = True
    warrior.x = 310.0
    warrior.y = scene.stage.ground_y
    warrior.on_ground = True
    max_warrior_step = 0.0
    crossed_player = False
    previous_warrior_x = warrior.x
    for _ in range(20):
        scene.tick(FIXED_DT)
        max_warrior_step = max(
            max_warrior_step, abs(warrior.x - previous_warrior_x)
        )
        crossed_player = crossed_player or warrior.x < scene.player.x
        previous_warrior_x = warrior.x
    separation_step = (
        float(scene.store.stats["combat"]["separation_speed"]) * FIXED_DT
    )
    separation_block_ok = (
        not crossed_player
        and max_warrior_step <= separation_step + 0.01
        and abs(warrior.x - scene.player.x) >= 109.5
    )

    # A hit during the transform must not leave Lina invisible.
    scene.reset()
    warrior = scene.enemy
    lina = scene.player
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
    lina = scene.player
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
    scene.player.x = warrior.x - 80.0
    warrior.facing = -1
    warrior.start_attack("axe_slash", scene, scene.player)
    for _ in range(60):
        scene.tick(FIXED_DT)
        if warrior.state != FighterState.ATTACK:
            break
    gap_started = warrior.skill_cd > 0.0
    scene.player.x = warrior.x - 80.0
    scene.player.hp = scene.player.max_hp
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
    scene.player.x = 300.0
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
        if scene.player.hp < scene.player.max_hp:
            break
    ai_ok = (
        warrior.x < start_x
        and saw_air
        and saw_attack
        and scene.player.hp < scene.player.max_hp
    )

    # Dash: 30 damage plus a 1.5s knock-up. Blocks off to keep the path clear.
    scene.reset()
    scene.stage.set_blocks_enabled(False)
    warrior = scene.enemy
    warrior.ai_enabled = False
    scene.player.x = warrior.x - 200.0
    warrior.force_attack(scene, scene.player, "dash")
    launched = False
    dash_hitstop_ok = False
    hitstop_seen = False
    air_pose_ok = False
    for _ in range(50):
        scene.tick(FIXED_DT)
        launched = launched or scene.player.vy < 0.0 or scene.player.y < scene.stage.ground_y
        if not hitstop_seen and scene.player.hp < scene.player.max_hp:
            dash_hitstop_ok = abs(scene.hitstop - 0.08) < 1e-6
            hitstop_seen = True
        if scene.player.hitstun <= 0.0 and not scene.player.on_ground:
            air_pose_ok = (
                scene.player.state == FighterState.AIR
                and scene.player.anim.clip_name == "jump"
            )
    dash_ok = (
        abs(scene.player.hp - 70.0) < 0.01
        and scene.player.statuses.has("knock_up")
        and launched
    )

    # A lethal dash KOs in place instead of launching the body.
    scene.reset()
    warrior = scene.enemy
    warrior.ai_enabled = False
    scene.player.hp = 10.0
    scene.player.x = warrior.x - 200.0
    warrior.force_attack(scene, scene.player, "dash")
    for _ in range(40):
        scene.tick(FIXED_DT)
    dash_ko_ok = (
        scene.player.state == FighterState.KO
        and not scene.player.statuses.has("knock_up")
        and scene.player.vy == 0.0
    )

    # Status super armor takes the damage but suppresses launch and knock_up.
    scene.reset()
    warrior = scene.enemy
    warrior.ai_enabled = False
    scene.player.x = warrior.x - 200.0
    scene.player.statuses.add("super_armor", 3.0)
    warrior.force_attack(scene, scene.player, "dash")
    for _ in range(40):
        scene.tick(FIXED_DT)
    dash_armor_ok = (
        abs(scene.player.hp - 70.0) < 0.01
        and not scene.player.statuses.has("knock_up")
        and scene.player.vy == 0.0
    )

    # Warrior startup armor ignores a launch event and gains no knock_up status.
    scene.reset()
    warrior = scene.enemy
    warrior.ai_enabled = False
    scene.player.x = warrior.x - 80.0
    warrior.facing = -1
    warrior.start_attack("axe_slash", scene, scene.player)
    scene.tick(FIXED_DT)
    resolve_hit(
        scene,
        scene.player,
        warrior,
        {"basic_mult": 0.0, "extra_mult": 0.0},
        {"damage": 1.0, "launch": 760.0, "knock_up": 1.5},
    )
    armor_knockup_ok = (
        abs(warrior.hp - (warrior.max_hp - 1.0)) < 0.01
        and not warrior.statuses.has("knock_up")
        and warrior.state == FighterState.ATTACK
    )
    scene.stage.set_blocks_enabled(True)

    # Knock-up vortex: progress follows the status and drawing changes nothing.
    scene.reset()
    scene.stage.set_blocks_enabled(False)
    warrior = scene.enemy
    warrior.ai_enabled = False
    scene.player.x = warrior.x - 200.0
    warrior.force_attack(scene, scene.player, "dash")
    progress_seen = None
    for _ in range(40):
        scene.tick(FIXED_DT)
        progress_seen = scene.knock_up_effect_progress(scene.player)
        if progress_seen is not None:
            break
    before_draw = (
        scene.player.state,
        scene.player.anim.clip_name,
        scene.player.anim.frame_index,
        scene.player.x,
        scene.player.y,
    )
    scene.draw(screen)
    after_draw = (
        scene.player.state,
        scene.player.anim.clip_name,
        scene.player.anim.frame_index,
        scene.player.x,
        scene.player.y,
    )
    draw_unchanged_ok = before_draw == after_draw
    fx_start_ok = progress_seen is not None and progress_seen > 0.5
    for _ in range(20):
        scene.tick(FIXED_DT)
    progress_later = scene.knock_up_effect_progress(scene.player)
    fx_shrinks_ok = (
        progress_later is not None
        and progress_seen is not None
        and progress_later < progress_seen
    )
    for _ in range(200):
        scene.tick(FIXED_DT)
        if scene.knock_up_effect_progress(scene.player) is None:
            break
    fx_expires_ok = scene.knock_up_effect_progress(scene.player) is None
    fx_cfg = scene.store.stats["combat"]["knock_up_fx"]
    end_scale, end_alpha = knock_up_vortex_intensity(0.01, fx_cfg)
    fx_end_visible_ok = (
        end_scale >= float(fx_cfg["min_scale"]) - 1e-6
        and end_alpha
        >= float(fx_cfg["alpha"]) * float(fx_cfg["min_alpha"]) - 1e-6
    )
    knockup_fx_ok = (
        fx_start_ok
        and fx_shrinks_ok
        and fx_expires_ok
        and fx_end_visible_ok
        and draw_unchanged_ok
    )
    scene.stage.set_blocks_enabled(True)

    # An attack pressed during the lock waits and fires when control returns.
    scene.reset()
    scene.stage.set_blocks_enabled(False)
    warrior = scene.enemy
    warrior.ai_enabled = False
    scene.player.x = warrior.x - 200.0
    warrior.force_attack(scene, scene.player, "dash")
    for _ in range(40):
        scene.tick(FIXED_DT)
        if scene.player.statuses.has("knock_up"):
            break
    scene.input.buffer.press("punch")
    buffered_attack_started = False
    landing_tick = None
    attack_tick = None
    for i in range(140):
        scene.tick(FIXED_DT)
        if landing_tick is None and scene.player.on_ground:
            landing_tick = i
        if scene.player.attack_id is not None:
            buffered_attack_started = True
            attack_tick = i
            break
    lock_buffer_ok = (
        buffered_attack_started
        and landing_tick is not None
        and attack_tick is not None
        and attack_tick - landing_tick <= 3
        and scene.player.state == FighterState.ATTACK
        and not scene.player.statuses.has("knock_up")
    )
    scene.stage.set_blocks_enabled(True)

    # Throw: high lane, one hit out and one back, then returns to the hand.
    scene.reset()
    scene.stage.set_blocks_enabled(False)
    warrior = scene.enemy
    warrior.ai_enabled = False
    scene.player.x = warrior.x - 300.0
    warrior.force_attack(scene, scene.player, "axe_throw")
    saw_axe = False
    both_axe_hits = False
    for _ in range(150):
        scene.tick(FIXED_DT)
        axes = [p for p in scene.projectiles if getattr(p, "kind", "") == "axe_throw"]
        if axes:
            saw_axe = True
            if axes[0].hit_out and axes[0].hit_return:
                both_axe_hits = True
    throw_ok = both_axe_hits and abs(scene.player.hp - 52.0) < 0.01
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
    scene.player.x = 600.0
    scene.player.y = scene.stage.ground_y
    warrior.facing = 1
    warrior.force_attack(scene, scene.player, "axe_throw")
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
    scene.player.x = 300.0
    # Stand just right of the 400..490 block so the throw must cross it.
    warrior.x = 555.0
    warrior.y = scene.stage.ground_y
    warrior.on_ground = True
    warrior.dash_cd = 999.0
    blocked_before = warrior._block_ahead(scene)
    saw_axe = False
    for _ in range(180):
        scene.tick(FIXED_DT)
        if any(getattr(p, "kind", "") == "axe_throw" for p in scene.projectiles):
            saw_axe = True
        if scene.player.hp < scene.player.max_hp:
            break
    ai_ranged_ok = (
        blocked_before and saw_axe and scene.player.hp < scene.player.max_hp
    )

    # B toggles block collision/visibility; with blocks off, Lina can pass one.
    block = scene.stage.blocks[0]
    scene.stage.set_blocks_enabled(False)
    scene.player.x = block.left - scene.player.stage_half_width
    scene.stage.move_x(scene.player, 200.0)
    blocks_pass_ok = scene.player.x > block.right
    scene.stage.set_blocks_enabled(True)
    blocks_toggle_ok = blocks_pass_ok and scene.stage.blocks_enabled

    smoke_ticks = scene.tick_count
    scene.set_enemy("dummy")
    dummy_ok = scene.enemy.name == "Dummy"
    scene.set_enemy("warrior")
    switch_ok = (
        dummy_ok
        and scene.enemy.name == "Warrior"
        and scene.enemy.max_hp == 300.0
        and scene.enemy.basic_atk == 20.0
    )
    switch_reset_ok = (
        scene.player.hp == scene.player.max_hp
        and scene.enemy.hp == scene.enemy.max_hp
        and not scene.projectiles
        and scene.match_over is None
    )
    switch_ai_off_ok = hasattr(scene.enemy, "ai_enabled") and not scene.enemy.ai_enabled
    scene.handle_debug_key(pygame.K_F8)
    switch_ai_toggle_ok = scene.enemy.ai_enabled
    scene.handle_debug_key(pygame.K_F8)
    scene.toggle_lock_on()
    lock_before_switch = scene.lock_on
    scene.set_enemy("dummy")
    lock_switch_off_ok = lock_before_switch and not scene.lock_on
    scene.set_enemy("warrior")

    # V/C/X/Z resolve through the enemy's data-driven skill slots.
    slot_matches = {}
    for key, expected in (
        (pygame.K_v, "axe_slash"),
        (pygame.K_c, "dash"),
        (pygame.K_x, "axe_throw"),
    ):
        scene.reset()
        warrior = scene.enemy
        warrior.ai_enabled = False
        scene.handle_debug_key(key)
        slot_matches[expected] = warrior.attack_id == expected
    scene.reset()
    warrior = scene.enemy
    warrior.ai_enabled = False
    scene.handle_debug_key(pygame.K_z)
    slot_four_empty_ok = warrior.attack_id is None and warrior.state != FighterState.ATTACK
    slots_ok = all(slot_matches.values()) and slot_four_empty_ok

    scene.set_enemy("dummy")
    dummy = scene.enemy
    dummy_slots_ok = dummy.skill_slots == [None, None, None, None]
    for key in (pygame.K_v, pygame.K_c, pygame.K_x, pygame.K_z):
        scene.handle_debug_key(key)
    dummy_noop_ok = dummy.attack_id is None
    scene.show_overlay = True
    scene.show_panel = True
    scene.draw(screen)
    scene.show_overlay = False
    scene.show_panel = False

    scene.set_enemy("warrior")
    character_noop_ok = not scene.set_character("lina")
    scene.handle_debug_key(pygame.K_LEFTBRACKET)
    previous_character_ok = scene.character_id == "lina"
    scene.handle_debug_key(pygame.K_RIGHTBRACKET)
    next_character_ok = scene.character_id == "lina"

    scene.stage.set_blocks_enabled(False)
    scene.set_enemy("dummy")
    b_preserved_ok = not scene.stage.blocks_enabled
    scene.set_enemy("warrior")
    b_preserved_ok = b_preserved_ok and not scene.stage.blocks_enabled
    scene.stage.set_blocks_enabled(True)

    # F7 and B must work through the debug-key router, not only the helpers.
    scene.handle_debug_key(pygame.K_F7)
    f7_cycle_ok = scene.enemy_id == "dummy"
    b_before = scene.stage.blocks_enabled
    scene.handle_debug_key(pygame.K_b)
    b_key_ok = scene.stage.blocks_enabled != b_before
    scene.handle_debug_key(pygame.K_b)
    b_key_ok = b_key_ok and scene.stage.blocks_enabled == b_before
    scene.set_enemy("warrior")

    # A switch must also clear an active projectile and hitstop.
    scene.reset()
    scene.player.x = 300.0
    scene.enemy.x = 900.0
    scene.player.facing = 1
    scene.input.buffer.press("q")
    for _ in range(20):
        scene.tick(FIXED_DT)
    had_projectile = bool(scene.projectiles)
    scene.set_enemy("dummy")
    switch_clears_ok = (
        had_projectile and not scene.projectiles and scene.hitstop == 0.0
    )
    scene.set_enemy("warrior")

    roster_ok = (
        dummy_ok
        and switch_ok
        and switch_reset_ok
        and switch_ai_off_ok
        and switch_ai_toggle_ok
        and dummy_slots_ok
        and dummy_noop_ok
        and character_noop_ok
        and previous_character_ok
        and next_character_ok
        and b_preserved_ok
        and switch_clears_ok
        and f7_cycle_ok
        and b_key_ok
        and lock_switch_off_ok
    )
    warrior_missing = len(scene.enemy.anim.missing_paths())
    scene.show_overlay = True
    scene.show_panel = True
    scene.draw(screen)
    scene.show_overlay = False
    scene.show_panel = False
    scene.draw(screen)

    print(
        "SMOKE "
        f"ticks={smoke_ticks} "
        f"punch_hp={punch_hp:.1f} "
        f"punch_energy={punch_energy:.1f} "
        f"damaged={damaged} gained={gained} punch_damage_ok={punch_damage_ok} "
        f"queued_kick_ok={queued_kick_ok} kick_damage_ok={kick_damage_ok} "
        f"kick_energy_ok={kick_energy_ok} q_damage_ok={q_damage_ok} "
        f"block_lunge_ok={block_lunge_ok} q_block_ok={q_block_ok} "
        f"lock_on_ok={lock_on_ok} lock_off_ok={lock_off_ok} "
        f"flame_ok={flame_ok} missing_frames={missing_frames} "
        f"warrior_present={warrior_present} warrior_hp={warrior_hp:.1f} "
        f"warrior_hurt_ok={warrior_hurt_ok} super_armor_ok={super_armor_ok} "
        f"armor_interrupt_ok={armor_interrupt_ok} "
        f"warrior_attack_ok={warrior_attack_ok} "
        f"axe_slash_damage_ok={axe_slash_damage_ok} "
        f"lose_ok={lose_ok} win_ok={win_ok} "
        f"ai_ok={ai_ok} switch_ok={switch_ok} reset_ok={reset_ok} "
        f"overlap_ok={overlap_ok} separation_block_ok={separation_block_ok} "
        f"transform_hit_ok={transform_hit_ok} "
        f"revert_ok={revert_ok} flame_offset_ok={flame_offset_ok} "
        f"skill_gap_ok={skill_gap_ok} blocks_toggle_ok={blocks_toggle_ok} "
        f"dash_ok={dash_ok} dash_hitstop_ok={dash_hitstop_ok} "
        f"air_pose_ok={air_pose_ok} dash_ko_ok={dash_ko_ok} "
        f"dash_armor_ok={dash_armor_ok} armor_knockup_ok={armor_knockup_ok} "
        f"knockup_fx_ok={knockup_fx_ok} fx_end_visible_ok={fx_end_visible_ok} "
        f"lock_buffer_ok={lock_buffer_ok} "
        f"throw_ok={throw_ok} throw_return_ok={throw_return_ok} "
        f"throw_lane_ok={throw_lane_ok} ai_ranged_ok={ai_ranged_ok} "
        f"slots_ok={slots_ok} roster_ok={roster_ok} "
        f"warrior_missing_frames={warrior_missing}"
    )
    return 0 if (
        damaged
        and gained
        and punch_damage_ok
        and queued_kick_ok
        and kick_damage_ok
        and kick_energy_ok
        and q_damage_ok
        and lock_ok
        and block_lunge_ok
        and q_block_ok
        and flame_ok
        and missing_frames == 0
        and warrior_present
        and warrior_hurt_ok
        and super_armor_ok
        and armor_interrupt_ok
        and warrior_attack_ok
        and axe_slash_damage_ok
        and lose_ok
        and win_ok
        and ai_ok
        and switch_ok
        and roster_ok
        and reset_ok
        and overlap_ok
        and separation_block_ok
        and transform_hit_ok
        and revert_ok
        and flame_offset_ok
        and skill_gap_ok
        and blocks_toggle_ok
        and dash_ok
        and dash_hitstop_ok
        and air_pose_ok
        and dash_ko_ok
        and dash_armor_ok
        and armor_knockup_ok
        and knockup_fx_ok
        and lock_buffer_ok
        and throw_ok
        and throw_return_ok
        and throw_lane_ok
        and ai_ranged_ok
        and slots_ok
        and warrior_missing == 0
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
                if event.button == 2:
                    scene.toggle_lock_on()
                else:
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
