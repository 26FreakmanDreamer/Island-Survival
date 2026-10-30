"""Island Survival — Lina Seabright combat sandbox entry point."""

from __future__ import annotations

import os
import sys

import pygame

from game.combat import resolve_hit
from game.config import ASSETS_DIR, FIXED_DT, SCREEN_H, SCREEN_W, JsonStore
from game.fighter import FighterState
from game.fx import missing_lina_q_assets, missing_veno_web_asset
from game.particles import knock_up_vortex_intensity
from game.projectile import AimedProjectile, CreepyBullet, SonicWave
from game.status import StatusSet
from game.scene import DEBUG_KEYS, ArenaScene
from game.slash_fx import missing_frames as missing_slash_fx_frames


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
    # Isolate the existing single-enemy checks; the group spawn is verified
    # separately at the end of the Veno phase.
    scene.enemy_count_override = 1
    default_enemy_ok = (
        scene.enemy_id == "creepy_shooter"
        and getattr(scene.enemy, "name", "") == "Creepy Shooter"
    )
    startup_ai_off_ok = (
        hasattr(scene.enemy, "ai_enabled") and not scene.enemy.ai_enabled
    )

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
    block = scene.stage.barriers[0]
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

    # Q visual dispatch: sprite colors and cast/impact effects.
    scene.reset()
    scene.enemy.x = scene.player.x + 200.0
    scene.player.facing = 1
    scene.player.start_attack("q", scene, scene.enemy)
    q_cast_fx_ok = False
    q_impact_fx_ok = False
    q_normal_color_ok = False
    for _ in range(90):
        scene.tick(FIXED_DT)
        if scene.projectiles:
            projectile = scene.projectiles[0]
            q_normal_color_ok = (
                not projectile.flame
                and projectile.visual_kind == "lina_q"
                and projectile.hit_color == (80, 230, 225)
            )
        if any(effect.kind == "lina_q_cast" for effect in scene.fx_effects):
            q_cast_fx_ok = True
        if any(effect.kind == "lina_q_impact" for effect in scene.fx_effects):
            q_impact_fx_ok = True
            break

    scene.reset()
    scene.player.flame_time = 5.0
    scene.player.anim.set_variant("flame")
    scene.enemy.x = scene.player.x + 200.0
    scene.player.facing = 1
    scene.player.start_attack("q", scene, scene.enemy)
    q_flame_color_ok = False
    q_flame_cast_ok = False
    for _ in range(30):
        scene.tick(FIXED_DT)
        if scene.projectiles:
            projectile = scene.projectiles[0]
            q_flame_color_ok = (
                projectile.flame
                and projectile.visual_kind == "lina_q_flame"
                and projectile.hit_color == (255, 150, 90)
            )
            q_flame_cast_ok = any(
                effect.kind == "lina_q_flame_cast"
                for effect in scene.fx_effects
            )
            break

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
    reset_ai_off_ok = (
        hasattr(scene.enemy, "ai_enabled") and not scene.enemy.ai_enabled
    )
    ai_default_off_ok = startup_ai_off_ok and reset_ai_off_ok
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
    lina.x = 300.0
    lina.y = scene.stage.ground_y
    lina.on_ground = True
    warrior.x = 300.0
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
    warrior.ai_enabled = True
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
    lane_block = scene.stage.barriers[0]
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
    warrior.ai_enabled = True
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
    block = scene.stage.barriers[0]
    scene.stage.set_blocks_enabled(False)
    scene.player.x = block.left - scene.player.stage_half_width
    scene.stage.move_x(scene.player, 200.0)
    blocks_pass_ok = scene.player.x > block.right
    scene.stage.set_blocks_enabled(True)
    blocks_toggle_ok = blocks_pass_ok and scene.stage.blocks_enabled

    # --- Phase C: Nyra Steel, marks, cooldowns and pass-through dash ---
    scene.set_character("nyra")
    scene.set_enemy("dummy")
    scene.reset()
    nyra = scene.player
    dummy = scene.enemy
    nyra_present = (
        nyra.name == "Nyra Steel"
        and nyra.max_hp == 100.0
        and nyra.basic_atk == 20.0
        and not hasattr(nyra, "energy")
    )

    scene.reset()
    nyra = scene.player
    dummy = scene.enemy
    dummy.x = nyra.x + 80.0
    nyra.facing = 1
    scene.input.buffer.press("punch")
    lmb_fx_seen = False
    for _ in range(30):
        scene.tick(FIXED_DT)
        if scene.slash_effects:
            lmb_fx_seen = True
    nyra_wave_lmb_ok = (
        abs(dummy.hp - 980.0) < 0.01
        and dummy.marks == 1
        and not lmb_fx_seen
    )

    scene.reset()
    nyra = scene.player
    dummy = scene.enemy
    dummy.x = nyra.x + 80.0
    nyra.facing = 1
    wave_burst_seen = False
    for _ in range(4):
        scene.input.buffer.press("punch")
        for _ in range(30):
            scene.tick(FIXED_DT)
            if nyra.mark_detonations > 0 and not wave_burst_seen:
                wave_burst_seen = dummy.mark_burst_time > 0.0
    nyra_wave_burst_ok = (
        wave_burst_seen
        and nyra.mark_detonations == 1
        and dummy.marks == 1
    )
    nyra_wave_burst_damage_ok = abs(dummy.hp - 784.0) < 0.01

    scene.reset()
    nyra = scene.player
    dummy = scene.enemy
    dummy.x = nyra.x + 100.0
    nyra.facing = 1
    scene.input.buffer.press("kick")
    for _ in range(40):
        scene.tick(FIXED_DT)
    nyra_thrust_ok = abs(dummy.hp - 976.0) < 0.01 and dummy.marks == 1

    scene.reset()
    nyra = scene.player
    dummy = scene.enemy
    dummy.x = nyra.x + 120.0
    nyra.facing = 1
    scene.input.buffer.press("q")
    q_slash_fx_seen = False
    q_slash_no_projectile = True
    for _ in range(60):
        scene.tick(FIXED_DT)
        if scene.slash_effects:
            q_slash_fx_seen = True
        if scene.projectiles:
            q_slash_no_projectile = False
    nyra_q_slash_ok = (
        abs(dummy.hp - 970.0) < 0.01
        and dummy.marks == 1
        and q_slash_fx_seen
        and q_slash_no_projectile
    )
    nyra_q_slash_cd_ok = nyra.q_cd > 6.0

    scene.reset()
    nyra = scene.player
    dummy = scene.enemy
    nyra.x = 100.0
    nyra.y = scene.stage.ground_y
    nyra.on_ground = True
    dummy.x = 300.0
    dummy.y = scene.stage.ground_y
    dummy.on_ground = True
    nyra.facing = 1
    scene.input.buffer.press("q")
    for _ in range(20):
        scene.tick(FIXED_DT)
        if nyra.attack_runtime is not None:
            break
    q_slash_out_of_thrust_ok = abs(dummy.hp - 1000.0) < 0.01
    for _ in range(20):
        scene.tick(FIXED_DT)
        if nyra.attack_runtime is None or nyra.attack_runtime.time >= 0.13:
            break
    nyra_q_slash_range_ok = (
        q_slash_out_of_thrust_ok
        and abs(dummy.hp - 970.0) < 0.01
        and dummy.marks == 1
    )

    scene.reset()
    nyra = scene.player
    dummy = scene.enemy
    nyra.x = 100.0
    nyra.y = scene.stage.ground_y
    nyra.on_ground = True
    dummy.x = 900.0
    dummy.y = scene.stage.ground_y
    dummy.on_ground = True
    nyra.facing = 1
    scene.input.buffer.press("q")
    for _ in range(3):
        scene.tick(FIXED_DT)
    q_armor_started = nyra.attack_id == "nyra_slash" and nyra.statuses.has("super_armor")
    q_armor_hp_before = nyra.hp
    nyra.take_hit(10.0, 300.0, 0.4, -1, launch=200.0)
    for kind in ("knockback", "knock_up", "freeze", "stun"):
        nyra.statuses.add(kind, 1.0)
    nyra.statuses.add("slow", 1.0, value=0.5)
    q_armor_immune = not any(
        nyra.statuses.has(kind)
        for kind in ("knockback", "knock_up", "freeze", "stun", "slow")
    )
    nyra_q_armor_ok = (
        q_armor_started
        and nyra.attack_id == "nyra_slash"
        and nyra.state == FighterState.ATTACK
        and abs(nyra.hp - (q_armor_hp_before - 10.0)) < 0.01
        and nyra.hitstun == 0.0
        and nyra.kb_vx == 0.0
        and nyra.vy == 0.0
        and q_armor_immune
    )

    scene.reset()
    nyra = scene.player
    dummy = scene.enemy
    nyra.x = 500.0
    nyra.y = scene.stage.ground_y
    nyra.on_ground = True
    dummy.x = 680.0
    dummy.y = scene.stage.ground_y
    dummy.on_ground = True
    nyra.facing = 1
    scene.input.buffer.press("e")
    for _ in range(50):
        scene.tick(FIXED_DT)
    nyra_dash_ok = abs(dummy.hp - 970.0) < 0.01 and dummy.marks == 0
    nyra_dash_cd_ok = nyra.e_cd > 13.0

    scene.reset()
    nyra = scene.player
    dummy = scene.enemy
    nyra.x = 300.0
    nyra.y = scene.stage.ground_y
    nyra.on_ground = True
    dummy.x = 1000.0
    dummy.y = scene.stage.ground_y
    dummy.on_ground = True
    nyra.facing = 1
    scene.input.buffer.press("e")
    for _ in range(6):
        scene.tick(FIXED_DT)
    e_armor_started = nyra.attack_id == "nyra_dash" and nyra.statuses.has("super_armor")
    e_armor_hp_before = nyra.hp
    nyra.take_hit(10.0, 300.0, 0.4, -1, launch=200.0)
    for kind in ("knockback", "knock_up", "freeze", "stun"):
        nyra.statuses.add(kind, 1.0)
    nyra.statuses.add("slow", 1.0, value=0.5)
    e_armor_immune = not any(
        nyra.statuses.has(kind)
        for kind in ("knockback", "knock_up", "freeze", "stun", "slow")
    )
    nyra_e_armor_ok = (
        e_armor_started
        and nyra.attack_id == "nyra_dash"
        and nyra.state == FighterState.ATTACK
        and abs(nyra.hp - (e_armor_hp_before - 10.0)) < 0.01
        and nyra.hitstun == 0.0
        and nyra.kb_vx == 0.0
        and nyra.vy == 0.0
        and e_armor_immune
    )

    scene.reset()
    nyra = scene.player
    dummy = scene.enemy
    nyra.x = 200.0
    nyra.y = scene.stage.ground_y
    nyra.on_ground = True
    dummy.x = 1000.0
    dummy.y = scene.stage.ground_y
    dummy.on_ground = True
    nyra.facing = 1
    blocks_enabled = scene.stage.blocks_enabled
    scene.stage.blocks_enabled = False
    dash_start_x = nyra.x
    scene.input.buffer.press("e")
    for _ in range(50):
        scene.tick(FIXED_DT)
    dash_distance = nyra.x - dash_start_x
    scene.stage.blocks_enabled = blocks_enabled
    nyra_dash_distance_ok = dash_distance >= 300.0

    scene.reset()
    nyra = scene.player
    dummy = scene.enemy
    dummy.marks = 2
    dummy.mark_burst_time = 0.3
    dummy.mark_burst_damage = 12.0
    scene.reset()
    nyra = scene.player
    dummy = scene.enemy
    nyra_marks_reset_ok = (
        dummy.marks == 0
        and dummy.mark_burst_time == 0.0
        and dummy.mark_burst_damage == 0.0
    )

    scene.reset()
    nyra = scene.player
    dummy = scene.enemy
    dummy.x = nyra.x + 80.0
    dummy.hp = 5.0
    nyra.facing = 1
    scene.input.buffer.press("punch")
    for _ in range(30):
        scene.tick(FIXED_DT)
    nyra_death_clear_ok = dummy.hp <= 0.0 and dummy.marks == 0

    scene.reset()
    nyra = scene.player
    dummy = scene.enemy
    dummy.x = nyra.x - 80.0
    nyra.facing = 1
    scene.toggle_lock_on()
    scene.input.buffer.press("punch")
    for _ in range(30):
        scene.tick(FIXED_DT)
    nyra_lock_ok = nyra.facing == -1 and dummy.hp < dummy.max_hp
    if scene.lock_on:
        scene.toggle_lock_on()

    # Marks are per target: one Veno's stack never fills another's.
    scene.enemy_count_override = None
    scene.set_enemy("veno")
    scene.reset()
    nyra = scene.player
    venos = list(scene.enemies)
    for target in venos:
        target.ai_enabled = False
    nyra.on_hit_success({"marks_on_hit": 1.0}, venos[0], 0.0)
    nyra.on_hit_success({"marks_on_hit": 1.0}, venos[1], 0.0)
    nyra.on_hit_success({"marks_on_hit": 1.0}, venos[1], 0.0)
    nyra_marks_per_target_ok = (
        len(venos) == 3
        and venos[0].marks == 1
        and venos[1].marks == 2
        and venos[2].marks == 0
    )
    scene.enemy_count_override = 1
    scene._rebuild_fighters()

    scene.set_enemy("veno")
    scene.reset()
    nyra = scene.player
    veno = scene.enemy
    veno.ai_enabled = False
    scene.stage.blocks_enabled = False
    nyra.x = 600.0
    nyra.y = scene.stage.ground_y
    nyra.on_ground = True
    veno.x = 680.0
    veno.y = scene.stage.ground_y
    veno.on_ground = True
    nyra.facing = 1
    scene.input.buffer.press("e")
    for _ in range(50):
        scene.tick(FIXED_DT)
    min_dash_distance = nyra.stage_half_width + veno.stage_half_width
    nyra_dash_pass_ok = (
        nyra.x > veno.x
        and abs(veno.x - nyra.x) >= min_dash_distance - 0.5
    )
    scene.stage.blocks_enabled = True
    nyra_missing = len(nyra.anim.missing_paths())
    nyra_slash_fx_missing = len(missing_slash_fx_frames())

    # --- Phase D: Veno-Spider skills, statuses, hover AI and match flow ---
    scene.set_character("lina")
    scene.set_enemy("veno")
    scene.reset()
    veno = scene.enemy
    player = scene.player
    veno_present = (
        veno.name == "Veno-Spider"
        and veno.max_hp == 50.0
        and veno.basic_atk == 10.0
        and veno.skill_slots == ["veno_bite", "veno_poison", "veno_web", None]
        and scene.enemy_spec.get("separates", False)
        and scene.enemy_spec.get("decides_match", False)
    )

    scene.reset()
    veno = scene.enemy
    player = scene.player
    veno.ai_enabled = False
    player.x = veno.x - 80.0
    player.y = scene.stage.ground_y
    player.on_ground = True
    veno.facing = -1
    veno.force_attack(scene, player, "veno_bite")
    veno_bite_hit_fx_ok = False
    for _ in range(40):
        scene.tick(FIXED_DT)
        if any(effect.kind == "veno_bite_hit" for effect in scene.fx_effects):
            veno_bite_hit_fx_ok = True
    veno_bite_ok = abs(player.hp - 85.0) < 0.01
    veno_bite_cd_ok = (
        abs(veno.bite_cd_max - 1.0) < 1e-6
        and veno.skill_remaining("veno_bite") > 0.2
    )

    scene.reset()
    veno = scene.enemy
    player = scene.player
    veno.ai_enabled = False
    # The half-size Veno spits from a lower mouth; keep the block lane clear
    # for the damage/status test.
    scene.stage.blocks_enabled = False
    player.x = veno.x - 300.0
    player.y = scene.stage.ground_y
    player.on_ground = True
    veno.facing = -1
    veno.force_attack(scene, player, "veno_poison")
    poison_hit = False
    veno_poison_cast_ok = False
    veno_poison_impact_ok = False
    for _ in range(90):
        scene.tick(FIXED_DT)
        if any(effect.kind == "veno_poison_cast" for effect in scene.fx_effects):
            veno_poison_cast_ok = True
        if player.hp < player.max_hp:
            poison_hit = True
            veno_poison_impact_ok = any(
                effect.kind == "veno_poison_impact"
                for effect in scene.fx_effects
            )
            break
    poison = player.statuses.poisons[0] if player.statuses.poisons else None
    veno_poison_ok = (
        poison_hit
        and abs(player.hp - 92.0) < 0.01
        and poison is not None
        and abs(poison.dps - 3.0) < 1e-6
        and poison.remaining > 2.5
    )

    before_poison = (
        player.statuses.poisons[0].remaining if player.statuses.poisons else 0.0
    )
    veno.force_attack(scene, player, "veno_poison")
    stack_seen = False
    for _ in range(90):
        scene.tick(FIXED_DT)
        if (
            len(player.statuses.poisons) == 1
            and player.statuses.poisons[0].remaining > before_poison + 1.0
        ):
            stack_seen = True
            break
    veno_poison_stack_ok = stack_seen and len(player.statuses.poisons) == 1

    # Poison settles once per 0.5s (not on the old 0.2s dot tick).
    class _DotTarget:
        def __init__(self) -> None:
            self.hp = 100.0
            self.invincible = False

        def apply_dot(self, amount: float) -> None:
            self.hp -= amount

    dot_target = _DotTarget()
    dot_statuses = StatusSet()
    dot_statuses.add("poison", 3.0, source="smoke", dps=10.0)
    for _ in range(30):
        dot_statuses.update(FIXED_DT, dot_target)
    first_tick_ok = abs(dot_target.hp - 95.0) < 1e-6
    for _ in range(30):
        dot_statuses.update(FIXED_DT, dot_target)
    second_tick_ok = abs(dot_target.hp - 90.0) < 1e-6
    poison_interval_ok = first_tick_ok and second_tick_ok

    # instruction.docx poison stacking: same source extends (2s + 3s = 5s),
    # different sources remain independent.
    stack_target = _DotTarget()
    stack_statuses = StatusSet()
    stack_statuses.add("poison", 3.0, source="A", dps=1.0)
    for _ in range(60):
        stack_statuses.update(FIXED_DT, stack_target)
    stack_statuses.add("poison", 3.0, source="A", dps=1.0)
    same_source_ok = (
        len(stack_statuses.poisons) == 1
        and abs(stack_statuses.poisons[0].remaining - 5.0) < 0.06
    )
    stack_statuses.add("poison", 3.0, source="B", dps=2.0)
    cross_source_ok = (
        len(stack_statuses.poisons) == 2
        and any(abs(p.remaining - 5.0) < 0.06 for p in stack_statuses.poisons)
        and any(abs(p.remaining - 3.0) < 0.06 for p in stack_statuses.poisons)
    )
    poison_stack_rules_ok = same_source_ok and cross_source_ok

    # Whole-body poison tint alternates green/purple every 0.18s.
    scene.reset()
    smoke_player = scene.player
    smoke_player.statuses.add("poison", 3.0, source="smoke", dps=1.0)
    scene.sim_time = 0.0
    green_tint = scene._poison_tint(smoke_player)
    scene.sim_time = 0.18
    purple_tint = scene._poison_tint(smoke_player)
    poison_tint_ok = (
        green_tint == (70, 255, 110)
        and purple_tint == (220, 100, 255)
    )
    smoke_player.statuses.clear()
    scene.sim_time = 0.0

    scene.reset()
    veno = scene.enemy
    player = scene.player
    veno.ai_enabled = False
    scene.stage.blocks_enabled = False
    player.x = veno.x - 300.0
    player.y = scene.stage.ground_y
    player.on_ground = True
    veno.facing = -1
    veno.force_attack(scene, player, "veno_web")
    veno_web_cast_ok = False
    veno_web_impact_ok = False
    veno_web_radius_ok = False
    for _ in range(90):
        scene.tick(FIXED_DT)
        if scene.projectiles:
            web = scene.projectiles[0]
            veno_web_radius_ok = (
                web.kind == "web_bolt" and abs(web.radius - 30.0) < 1e-6
            )
        if any(effect.kind == "veno_web_cast" for effect in scene.fx_effects):
            veno_web_cast_ok = True
        if player.hp < player.max_hp:
            veno_web_impact_ok = any(
                effect.kind == "veno_web_impact"
                for effect in scene.fx_effects
            )
            break
    veno_web_ok = abs(player.hp - 90.0) < 0.01 and player.statuses.has("stun")

    for _ in range(60):
        scene.tick(FIXED_DT)
    fx_cleanup_ok = not scene.fx_effects
    scene.stage.blocks_enabled = True

    lina_q_fx_missing = len(missing_lina_q_assets())
    veno_vfx_missing = len(missing_veno_web_asset())

    scene.reset()
    veno = scene.enemy
    player = scene.player
    player.x = 300.0
    player.y = scene.stage.ground_y
    player.on_ground = True
    veno.x = 600.0
    veno.y = scene.stage.ground_y
    veno.on_ground = True
    veno.mode = "ground"
    veno.hover_time = 0.0
    veno.hover_phase = 0.0
    veno.ai_enabled = True
    ascended = False
    for _ in range(120):
        scene.tick(FIXED_DT)
        if veno.mode in ("ascend", "hover") and veno.y < scene.stage.ground_y - 100.0:
            ascended = True
            break
    veno_ai_ascent_ok = ascended

    scene.reset()
    veno = scene.enemy
    player = scene.player
    veno.ai_enabled = True
    veno.mode = "hover"
    veno.on_ground = False
    veno.y = scene.stage.ground_y - 220.0
    veno.vy = 0.0
    veno.hover_time = 0.6
    veno.poison_cd = veno.poison_cd_max
    veno.web_cd = veno.web_cd_max
    veno.bite_cd = veno.bite_cd_max
    player.x = veno.x - 400.0
    landed = False
    for _ in range(120):
        scene.tick(FIXED_DT)
        if veno.on_ground and veno.mode == "ground":
            landed = True
            break
    veno_ai_descend_ok = landed

    veno_slot_matches = {}
    for key, expected in (
        (pygame.K_v, "veno_bite"),
        (pygame.K_c, "veno_poison"),
        (pygame.K_x, "veno_web"),
    ):
        scene.reset()
        veno = scene.enemy
        veno.ai_enabled = False
        scene.handle_debug_key(key)
        veno_slot_matches[expected] = veno.attack_id == expected
    scene.reset()
    veno = scene.enemy
    veno.ai_enabled = False
    scene.handle_debug_key(pygame.K_z)
    veno_slot_four_ok = veno.attack_id is None and veno.state != FighterState.ATTACK
    veno_slots_ok = all(veno_slot_matches.values()) and veno_slot_four_ok

    scene.reset()
    veno = scene.enemy
    player = scene.player
    veno.ai_enabled = False
    veno.hp = 20.0
    player.x = veno.x - 80.0
    player.facing = 1
    player.start_attack("kick_r", scene, veno)
    for _ in range(30):
        scene.tick(FIXED_DT)
    veno_win_ok = veno.hp <= 0.0 and scene.match_over == "WIN"
    veno_missing = len(veno.anim.missing_paths())

    # Veno group spawn: the roster count is 3 and the group mixes ground/hover.
    scene.enemy_count_override = None
    scene.set_enemy("warrior")
    scene.set_enemy("veno")
    scene.reset()
    group_spawn_ok = (
        len(scene.enemies) == 3
        and any(not enemy.on_ground for enemy in scene.enemies)
        and any(enemy.on_ground for enemy in scene.enemies)
    )
    # Each Veno keeps its own skill cooldowns (bite 1s, poison 5s, web 8s).
    venos = list(scene.enemies)
    venos[0].force_attack(scene, scene.player, "veno_bite")
    veno_group_cooldowns_ok = (
        venos[0].skill_remaining("veno_bite") > 0.5
        and venos[1].skill_remaining("veno_bite") == 0.0
        and venos[2].skill_remaining("veno_bite") == 0.0
        and abs(venos[0].bite_cd_max - 1.0) < 1e-6
        and abs(venos[1].bite_cd_max - 1.0) < 1e-6
        and abs(venos[2].bite_cd_max - 1.0) < 1e-6
        and abs(venos[0].poison_cd_max - 5.0) < 1e-6
        and abs(venos[1].poison_cd_max - 5.0) < 1e-6
        and abs(venos[2].poison_cd_max - 5.0) < 1e-6
        and abs(venos[0].web_cd_max - 8.0) < 1e-6
        and abs(venos[1].web_cd_max - 8.0) < 1e-6
        and abs(venos[2].web_cd_max - 8.0) < 1e-6
    )
    for enemy in scene.enemies:
        enemy.hp = 0.0
    scene.tick(FIXED_DT)
    veno_group_ok = group_spawn_ok and scene.match_over == "WIN"
    scene.enemy_count_override = 1
    scene.set_enemy("warrior")
    scene.reset()

    # --- Phase E: Bat ---
    scene.enemy_count_override = 1
    scene.set_enemy("bat")
    scene.reset()
    bat = scene.enemy
    bat_present = (
        bat.name == "Bat"
        and bat.max_hp == 50.0
        and bat.basic_atk == 10.0
        and bat.extra_atk == 0.0
        and bat.skill_slots == ["bat_dive", "bat_sonic", None, None]
    )
    bat_missing = len(bat.anim.missing_paths())
    bat_count_ok = (
        scene.store.roster["enemies"]["bat"]["count"] == 5
        and len(scene.store.roster["enemies"]["bat"]["spawn_offsets"]) >= 5
    )

    # Flight: no gravity, altitude band, and horizontal pursuit while the AI
    # is on. Keep both skills on cooldown so this check is movement-only.
    bat.ai_enabled = True
    bat.sonic_cd = 999.0
    bat.dive_cd = 999.0
    scene.player.x = 200.0
    scene.player.y = scene.stage.ground_y
    scene.player.hp = scene.player.max_hp
    scene.player.statuses.clear()
    bat.x = 1000.0
    bat.y = bat.flight_max_y
    bat.vx = 0.0
    bat.vy = 0.0
    bat.hp = bat.max_hp
    bat.statuses.clear()
    flight_start_x = bat.x
    for _ in range(40):
        scene.tick(FIXED_DT)
    bat_flight_ok = (
        not bat.on_ground
        and bat.flight_min_y - 0.5 <= bat.y <= bat.flight_max_y + 0.5
        and bat.x < flight_start_x - 20.0
        and bat.flight_max_height >= 420.0
        and bat.flight_min_height <= 40.0
    )

    # Dive: locked direction toward the player's chest, hitbox follows the body.
    scene.stage.set_blocks_enabled(False)
    scene.player.x = 700.0
    scene.player.y = scene.stage.ground_y
    scene.player.hp = scene.player.max_hp
    scene.player.statuses.clear()
    bat.ai_enabled = False
    bat.x = 900.0
    bat.y = scene.stage.ground_y - 150.0
    bat.vx = 0.0
    bat.vy = 0.0
    bat.hp = bat.max_hp
    bat.statuses.clear()
    bat.dive_cd = 0.0
    bat.sonic_cd = 0.0
    dive_hp_before = scene.player.hp
    bat_force_ok = bat.force_attack(scene, scene.player, "bat_dive")
    bat_dive_hit_fx_ok = False
    for _ in range(50):
        scene.tick(FIXED_DT)
        if any(effect.kind == "bat_dive_hit" for effect in scene.fx_effects):
            bat_dive_hit_fx_ok = True
    bat_dive_ok = (
        bat_force_ok
        and abs((dive_hp_before - scene.player.hp) - 10.0) < 1e-6
        and bat.dive_cd > 0.0
    )

    # V/C/X/Z map to dive/sonic/empty/empty.
    scene.reset()
    bat = scene.enemy
    bat.ai_enabled = False
    scene.player.x = 600.0
    bat.x = 900.0
    bat.y = scene.stage.ground_y - 150.0
    bat_v_ok = bat.force_skill(scene, scene.player, 0)
    bat_v_id = bat.attack_id
    bat_c_ok = bat.force_skill(scene, scene.player, 1)
    bat_c_id = bat.attack_id
    bat_x_ok = not bat.force_skill(scene, scene.player, 2)
    bat_z_ok = not bat.force_skill(scene, scene.player, 3)
    bat_slots_ok = (
        bat_v_ok
        and bat_v_id == "bat_dive"
        and bat_c_ok
        and bat_c_id == "bat_sonic"
        and bat_x_ok
        and bat_z_ok
    )

    # Sonic: 24 damage + 1s stun, then return to the owner and die.
    scene.stage.set_blocks_enabled(False)
    scene.reset()
    bat = scene.enemy
    bat.ai_enabled = False
    scene.player.x = 500.0
    scene.player.y = scene.stage.ground_y
    scene.player.hp = scene.player.max_hp
    scene.player.statuses.clear()
    bat.x = 900.0
    bat.y = scene.stage.ground_y - 150.0
    bat.vx = 0.0
    bat.vy = 0.0
    bat.hp = bat.max_hp
    bat.statuses.clear()
    sonic_hp_before = scene.player.hp
    bat.force_attack(scene, scene.player, "bat_sonic")
    sonic_stun_seen = False
    sonic_stun_remaining = 0.0
    sonic_return_seen = False
    bat_sonic_cast_ok = False
    bat_sonic_impact_ok = False
    sonic_wave = None
    for _ in range(240):
        scene.tick(FIXED_DT)
        if any(effect.kind == "bat_sonic_cast" for effect in scene.fx_effects):
            bat_sonic_cast_ok = True
        if scene.player.hp < sonic_hp_before:
            bat_sonic_impact_ok = bat_sonic_impact_ok or any(
                effect.kind == "bat_sonic_impact"
                for effect in scene.fx_effects
            )
        if sonic_wave is None and scene.projectiles:
            sonic_wave = scene.projectiles[0]
        if sonic_wave is not None:
            if sonic_wave.phase == "return":
                sonic_return_seen = True
            if scene.player.statuses.has("stun") and not sonic_stun_seen:
                sonic_stun_seen = True
                effect = scene.player.statuses.get("stun")
                sonic_stun_remaining = effect.remaining if effect else 0.0
            if not sonic_wave.alive:
                break
    bat_sonic_ok = (
        abs((sonic_hp_before - scene.player.hp) - 12.0) < 1e-6
        and sonic_stun_seen
        and 0.5 <= sonic_stun_remaining <= 1.0
    )
    bat_sonic_return_ok = (
        sonic_wave is not None
        and sonic_return_seen
        and not sonic_wave.alive
    )

    # Hitbox: a forward circle +8/r24 reaches the leading WiFi arc, which
    # the old centered 36x36 square could not cover.
    hitbox_probe = SonicWave(
        owner=bat,
        target=scene.player,
        x=760.0,
        y=440.0,
        ux=-1.0,
        uy=0.0,
        speed=420.0,
        max_range=3000.0,
        damage=12.0,
        knockback=0.0,
        hitstun=0.1,
        hitstop=0.05,
        status="stun",
        status_duration=1.0,
        radius=18.0,
        return_height=30.0,
        hitbox_forward=8.0,
        hitbox_radius=24.0,
    )
    old_hitbox = pygame.Rect(742, 422, 36, 36)
    arc_probe = pygame.Rect(732, 438, 2, 4)
    bat_sonic_hitbox_ok = (
        abs(hitbox_probe.hitbox_forward - 8.0) < 1e-6
        and abs(hitbox_probe.hitbox_radius - 24.0) < 1e-6
        and hitbox_probe.hitbox_hits(arc_probe)
        and not old_hitbox.colliderect(arc_probe)
    )

    # Cast lock: 0.65s of no movement, then the AI resumes flying.
    scene.reset()
    bat = scene.enemy
    bat.ai_enabled = True
    scene.player.x = 500.0
    bat.x = 900.0
    bat.y = scene.stage.ground_y - 150.0
    bat.vx = 0.0
    bat.vy = 0.0
    bat.force_attack(scene, scene.player, "bat_sonic")
    lock_x, lock_y = bat.x, bat.y
    for _ in range(36):
        scene.tick(FIXED_DT)
    bat_sonic_lock_ok = (
        abs(bat.x - lock_x) < 0.01 and abs(bat.y - lock_y) < 0.01
    )
    for _ in range(12):
        scene.tick(FIXED_DT)
    bat_sonic_lock_ok = bat_sonic_lock_ok and (
        abs(bat.x - lock_x) > 1.0 or abs(bat.y - lock_y) > 1.0
    )

    # Wall bounce: miss outbound, bounce off the right wall, hit on the way home.
    scene.stage.set_blocks_enabled(False)
    scene.reset()
    bat = scene.enemy
    bat.ai_enabled = False
    scene.player.x = 1100.0
    scene.player.y = scene.stage.ground_y
    scene.player.hp = scene.player.max_hp
    scene.player.statuses.clear()
    bat.x = 1000.0
    bat.y = scene.stage.ground_y - 150.0
    wall_wave = SonicWave(
        owner=bat,
        target=scene.player,
        x=1150.0,
        y=470.0,
        ux=1.0,
        uy=0.0,
        speed=420.0,
        max_range=3000.0,
        damage=12.0,
        knockback=0.0,
        hitstun=0.1,
        hitstop=0.05,
        status="stun",
        status_duration=1.0,
        radius=18.0,
        return_height=30.0,
    )
    wall_hp_before = scene.player.hp
    wall_return_seen = False
    wall_hit_seen = False
    for _ in range(60):
        wall_wave.update(FIXED_DT, scene)
        if wall_wave.phase == "return":
            wall_return_seen = True
        if scene.player.hp < wall_hp_before:
            wall_hit_seen = True
        if not wall_wave.alive:
            break
    bat_sonic_wall_return_ok = (
        wall_return_seen
        and wall_hit_seen
        and abs((wall_hp_before - scene.player.hp) - 12.0) < 1e-6
        and not wall_wave.alive
    )

    # Block bounce: real block rect, low path, then return without damaging
    # the player who is standing behind the block.
    scene.stage.set_blocks_enabled(True)
    scene.reset()
    bat = scene.enemy
    bat.ai_enabled = False
    scene.player.x = 1000.0
    scene.player.y = scene.stage.ground_y
    scene.player.hp = scene.player.max_hp
    scene.player.statuses.clear()
    bat.x = 500.0
    bat.y = scene.stage.ground_y - 150.0
    block_wave = SonicWave(
        owner=bat,
        target=scene.player,
        x=650.0,
        y=555.0,
        ux=1.0,
        uy=0.0,
        speed=420.0,
        max_range=3000.0,
        damage=12.0,
        knockback=0.0,
        hitstun=0.1,
        hitstop=0.05,
        status="stun",
        status_duration=1.0,
        radius=18.0,
        return_height=30.0,
    )
    block_hp_before = scene.player.hp
    block_return_seen = False
    for _ in range(90):
        block_wave.update(FIXED_DT, scene)
        if block_wave.phase == "return":
            block_return_seen = True
        if not block_wave.alive:
            break
    bat_sonic_block_return_ok = (
        block_return_seen
        and not block_wave.alive
        and scene.player.hp == block_hp_before
    )

    # Hurt/stun stay airborne; only KO falls and switches to the landed frame.
    scene.reset()
    bat = scene.enemy
    bat.ai_enabled = False
    bat.take_hit(5.0, 100.0, 0.25, 1)
    bat_hurt_airborne_ok = (
        bat.state == FighterState.HURT
        and not bat.on_ground
        and bat.anim.clip_name == "hurt"
    )
    for _ in range(20):
        scene.tick(FIXED_DT)
    bat.statuses.add("stun", 0.5, source="debug")
    scene.tick(FIXED_DT)
    bat_stun_airborne_ok = (
        bat.anim.clip_name == "stun"
        and not bat.on_ground
        and bat.statuses.has("stun")
    )
    bat.hp = 1.0
    bat.take_hit(999.0, 0.0, 0.2, 1)
    for _ in range(60):
        scene.tick(FIXED_DT)
        if bat.on_ground:
            break
    bat_ko_ok = (
        bat.state == FighterState.KO
        and bat.on_ground
        and bat.anim.clip_name == "ko"
        and bat.anim.frame_index == 1
    )
    bat_win_ok = scene.match_over == "WIN"
    scene.stage.set_blocks_enabled(True)

    # Five-bat group: count=5, five distinct offsets, independent cooldowns,
    # and all-dead WIN.
    scene.enemy_count_override = None
    scene.set_enemy("warrior")
    scene.set_enemy("bat")
    scene.reset()
    bat_group = list(scene.enemies)
    bat_group_spawn_ok = (
        len(bat_group) == 5
        and all(not enemy.on_ground for enemy in bat_group)
        and len({round(enemy.x) for enemy in bat_group}) == 5
        and len({round(enemy.y) for enemy in bat_group}) == 5
        and max(enemy.hover_height for enemy in bat_group) >= 360.0
        and min(enemy.hover_height for enemy in bat_group) <= 200.0
    )
    for enemy in bat_group:
        enemy.sonic_cd = 0.0
    bat_group[0].force_attack(scene, scene.player, "bat_sonic")
    bat_group_cooldowns_ok = (
        bat_group[0].skill_remaining("bat_sonic") > 5.0
        and all(
            enemy.skill_remaining("bat_sonic") == 0.0
            for enemy in bat_group[1:]
        )
    )
    for enemy in bat_group:
        enemy.hp = 0.0
    scene.tick(FIXED_DT)
    bat_group_win_ok = scene.match_over == "WIN"
    bat_group_ok = (
        bat_group_spawn_ok
        and bat_group_cooldowns_ok
        and bat_group_win_ok
    )

    scene.enemy_count_override = 1
    scene.set_enemy("warrior")
    scene.reset()

    scene.set_character("lina")
    scene.set_enemy("warrior")
    scene.reset()

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
    previous_character_ok = scene.character_id == "nyra"
    nyra_switch_ai_off_ok = (
        hasattr(scene.enemy, "ai_enabled") and not scene.enemy.ai_enabled
    )
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
    f7_cycle_ok = scene.enemy_id == "veno"
    scene.handle_debug_key(pygame.K_F7)
    f7_bat_ok = scene.enemy_id == "bat"
    scene.handle_debug_key(pygame.K_F7)
    f7_creepy_ok = scene.enemy_id == "creepy_shooter"
    scene.handle_debug_key(pygame.K_F7)
    f7_dummy_ok = scene.enemy_id == "dummy"
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
    scene.set_enemy("veno")
    veno_switch_ai_off_ok = not scene.enemy.ai_enabled
    scene.handle_debug_key(pygame.K_F8)
    veno_switch_ai_toggle_ok = scene.enemy.ai_enabled
    scene.handle_debug_key(pygame.K_F8)
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
        and nyra_switch_ai_off_ok
        and b_preserved_ok
        and switch_clears_ok
        and f7_cycle_ok
        and f7_bat_ok
        and f7_creepy_ok
        and f7_dummy_ok
        and b_key_ok
        and lock_switch_off_ok
        and veno_slots_ok
        and veno_switch_ai_off_ok
        and veno_switch_ai_toggle_ok
    )
    warrior_missing = len(scene.enemy.anim.missing_paths())
    # Render the Nyra mark layer and panel with a populated target stack.
    scene.set_character("nyra")
    scene.enemy.marks = 2
    scene.enemy.mark_burst_time = 0.2
    scene.enemy.mark_burst_damage = 40.0
    scene.show_overlay = True
    scene.show_panel = True
    scene.draw(screen)
    scene.show_overlay = False
    scene.show_panel = False
    scene.draw(screen)

    # --- platforms, ladders and block penetration ---------------------------
    scene.stage.set_blocks_enabled(True)
    scene.set_character("lina")
    scene.set_enemy("dummy")
    scene.reset()
    platform = scene.stage.platforms[0]
    ladder = scene.stage.ladders[0]

    # Falling body lands on the platform top.
    player = scene.player
    player.x = float(platform.centerx)
    player.y = float(platform.top - 80)
    player.on_ground = False
    player.vy = 0.0
    for _ in range(120):
        scene.tick(FIXED_DT)
        if player.on_ground:
            break
    platform_land_ok = (
        player.on_ground and abs(player.y - float(platform.top)) < 0.5
    )

    # Airborne body stops at the platform side.
    scene.reset()
    player = scene.player
    player.y = float(platform.top + 120)
    player.on_ground = False
    player.vy = 0.0
    player.x = float(platform.right) + player.hurtbox_width * 0.5 + 1.0
    scene.stage.move_x(player, -120.0)
    platform_side_ok = player.x >= (
        float(platform.right) + player.hurtbox_width * 0.5 - 0.5
    )

    # Rising body stops against the platform underside.
    scene.reset()
    player = scene.player
    body_height = player.hurtbox_dims[1]
    player.x = float(platform.centerx)
    player.y = float(platform.bottom) + body_height + 1.0
    player.on_ground = False
    player.vy = -500.0
    scene.tick(FIXED_DT)
    platform_bottom_bump_ok = (
        abs(player.y - (float(platform.bottom) + body_height)) < 0.5
        and abs(player.vy) < 0.01
    )

    # B off lets the same body pass through the platform side.
    scene.reset()
    player = scene.player
    scene.stage.set_blocks_enabled(False)
    player.y = float(platform.top + 120)
    player.on_ground = False
    player.x = float(platform.right) + player.hurtbox_width * 0.5 + 1.0
    scene.stage.move_x(player, -120.0)
    platform_toggle_ok = player.x < float(platform.right)
    scene.stage.set_blocks_enabled(True)

    # W climbs the long ladder and stands on the platform.
    scene.reset()
    player = scene.player
    scene.input.clear()
    player.x = float(ladder.rect.centerx)
    player.y = float(ladder.bottom_y)
    player.on_ground = True
    player.vy = 0.0
    scene.input.key_down(pygame.K_w)
    ladder_climb_ok = False
    for _ in range(240):
        scene.tick(FIXED_DT)
        if player.on_ground and abs(player.y - float(ladder.top_y)) < 0.5:
            ladder_climb_ok = True
            break
    scene.input.key_up(pygame.K_w)

    # S climbs back down; Shift must not.
    ladder_down_ok = False
    scene.input.key_down(pygame.K_s)
    for _ in range(240):
        scene.tick(FIXED_DT)
        if player.on_ground and abs(player.y - float(ladder.bottom_y)) < 0.5:
            ladder_down_ok = True
            break
    scene.input.key_up(pygame.K_s)

    scene.reset()
    player = scene.player
    scene.input.clear()
    player.x = float(ladder.rect.centerx)
    player.y = float(ladder.top_y)
    player.on_ground = True
    player.vy = 0.0
    scene.input.key_down(pygame.K_LSHIFT)
    for _ in range(30):
        scene.tick(FIXED_DT)
    ladder_shift_no_down_ok = (
        abs(player.y - float(ladder.top_y)) < 0.5 and not player.climbing
    )
    scene.input.key_up(pygame.K_LSHIFT)

    # Climb animation: back view, 2 frames, up 0->1, down 1->0, hold, facing.
    scene.reset()
    player = scene.player
    scene.input.clear()
    player.facing = -1
    player.x = float(ladder.rect.centerx)
    player.y = float(ladder.bottom_y)
    player.on_ground = True
    player.vy = 0.0
    scene.input.key_down(pygame.K_w)
    scene.tick(FIXED_DT)
    climb_anim = player.anim
    up_start_ok = (
        player.climbing
        and climb_anim.clip_name == "climb"
        and len(climb_anim.clip["frames"]) == 2
        and climb_anim.frame_index == 0
    )
    for _ in range(16):
        scene.tick(FIXED_DT)
    up_advance_ok = (
        climb_anim.clip_name == "climb" and climb_anim.frame_index == 1
    )
    scene.input.key_up(pygame.K_w)
    held_index = climb_anim.frame_index
    for _ in range(20):
        scene.tick(FIXED_DT)
    hold_ok = (
        player.climbing
        and climb_anim.clip_name == "climb"
        and climb_anim.frame_index == held_index
    )
    lina_climb_anim_ok = up_start_ok and up_advance_ok and hold_ok

    # Descending starts at frame 1 and advances toward frame 0.
    scene.reset()
    player = scene.player
    scene.input.clear()
    player.facing = -1
    player.x = float(ladder.rect.centerx)
    player.y = float(ladder.top_y)
    player.on_ground = True
    player.vy = 0.0
    scene.input.key_down(pygame.K_s)
    scene.tick(FIXED_DT)
    down_start_ok = (
        player.climbing
        and player.anim.clip_name == "climb"
        and player.anim.frame_index == 1
    )
    for _ in range(16):
        scene.tick(FIXED_DT)
    down_advance_ok = (
        player.climbing
        and player.anim.clip_name == "climb"
        and player.anim.frame_index == 0
    )
    lina_climb_anim_ok = lina_climb_anim_ok and down_start_ok and down_advance_ok
    lina_climb_facing_ok = player.climbing and player.facing == 1
    scene.input.key_down(pygame.K_SPACE)
    scene.tick(FIXED_DT)
    scene.input.key_up(pygame.K_SPACE)
    scene.input.key_up(pygame.K_s)
    lina_climb_facing_ok = (
        lina_climb_facing_ok
        and not player.climbing
        and player.facing == -1
    )

    # Flame form uses its own two-frame climb art.
    scene.set_character("lina")
    scene.reset()
    player = scene.player
    scene.input.clear()
    player.flame_time = 5.0
    player.anim.set_variant("flame")
    player.x = float(ladder.rect.centerx)
    player.y = float(ladder.bottom_y)
    player.on_ground = True
    player.vy = 0.0
    scene.input.key_down(pygame.K_w)
    scene.tick(FIXED_DT)
    flame_climb_anim = player.anim
    lina_flame_climb_anim_ok = (
        player.climbing
        and flame_climb_anim.variant == "flame"
        and flame_climb_anim.clip_name == "climb"
        and flame_climb_anim.current_is_flame_frame
        and len(flame_climb_anim.clip["frames"]) == 2
        and flame_climb_anim.frame_index == 0
    )
    for _ in range(16):
        scene.tick(FIXED_DT)
    lina_flame_climb_anim_ok = (
        lina_flame_climb_anim_ok
        and flame_climb_anim.clip_name == "climb"
        and flame_climb_anim.frame_index == 1
    )
    scene.input.key_up(pygame.K_w)

    # A ladder never blocks a projectile.
    scene.reset()
    enemy = scene.enemy
    enemy.ai_enabled = False
    enemy.x = 1150.0
    enemy.y = scene.stage.ground_y
    ladder_wave = AimedProjectile(
        owner=scene.player,
        target=None,
        x=450.0,
        y=500.0,
        vx=500.0,
        vy=0.0,
        max_range=200.0,
        damage=0.0,
        knockback=0.0,
        hitstun=0.0,
        hitstop=0.0,
        kind="venom_glob",
        radius=10.0,
    )
    for _ in range(20):
        ladder_wave.update(FIXED_DT, scene)
    ladder_no_block_ok = (
        ladder_wave.alive and ladder_wave.x > float(ladder.rect.right)
    )

    # Every roster group spawns clear of solid scene geometry, including
    # roster spawn_offsets/heights (resolve_overlap runs on reset).
    platform_spawn_clear_ok = True
    previous_enemy = scene.enemy_id
    scene.set_character("lina")
    for enemy_id in scene.store.roster.get("enemies", {}):
        scene.set_enemy(enemy_id)
        scene.reset()
        for fighter in [scene.player, *scene.enemies]:
            body = scene.stage.body_rect(fighter)
            if any(
                body.colliderect(solid) for solid in scene.stage.blocks
            ):
                platform_spawn_clear_ok = False
                break
        if not platform_spawn_clear_ok:
            break
    scene.set_enemy(previous_enemy)
    scene.reset()

    # penetrates_blocks lets a projectile cross a barrier; default dies.
    barrier = scene.stage.barriers[0]
    scene.reset()
    enemy = scene.enemy
    enemy.ai_enabled = False
    enemy.x = 1150.0

    def _aimed_at_barrier(penetrates: bool) -> AimedProjectile:
        return AimedProjectile(
            owner=scene.player,
            target=None,
            x=float(barrier.left - 40),
            y=float(barrier.centery),
            vx=500.0,
            vy=0.0,
            max_range=400.0,
            damage=0.0,
            knockback=0.0,
            hitstun=0.0,
            hitstop=0.0,
            kind="venom_glob",
            radius=10.0,
            penetrates_blocks=penetrates,
        )

    default_wave = _aimed_at_barrier(False)
    piercing_wave = _aimed_at_barrier(True)
    for _ in range(40):
        default_wave.update(FIXED_DT, scene)
        piercing_wave.update(FIXED_DT, scene)
    penetration_flag_ok = (not default_wave.alive) and piercing_wave.alive

    # Nyra shares the same climb path.
    scene.set_character("nyra")
    scene.reset()
    nyra = scene.player
    scene.input.clear()
    nyra.x = float(ladder.rect.centerx)
    nyra.y = float(ladder.bottom_y)
    nyra.on_ground = True
    nyra.vy = 0.0
    scene.input.key_down(pygame.K_w)
    scene.tick(FIXED_DT)
    nyra_climb_anim = nyra.anim
    nyra_climb_anim_ok = (
        nyra.climbing
        and nyra_climb_anim.clip_name == "climb"
        and len(nyra_climb_anim.clip["frames"]) == 2
        and nyra_climb_anim.frame_index == 0
    )
    for _ in range(16):
        scene.tick(FIXED_DT)
    nyra_climb_anim_ok = (
        nyra_climb_anim_ok
        and nyra_climb_anim.clip_name == "climb"
        and nyra_climb_anim.frame_index == 1
    )
    nyra_climb_ok = False
    for _ in range(240):
        scene.tick(FIXED_DT)
        if nyra.on_ground and abs(nyra.y - float(ladder.top_y)) < 0.5:
            nyra_climb_ok = True
            break
    scene.input.key_up(pygame.K_w)

    # --- Creepy Shooter phase -------------------------------------------------
    scene.set_character("lina")
    scene.set_enemy("creepy_shooter")
    scene.reset()
    scene.enemy_count_override = 1
    scene.stage.set_blocks_enabled(True)
    creepy = scene.enemy
    creepy_player = scene.player
    creepy.ai_enabled = False
    scene.input.clear()
    creepy_present = (
        creepy.name == "Creepy Shooter"
        and creepy.max_hp == 200.0
        and abs(creepy.atk - 20.0) < 1e-6
        and creepy.skill_slots == [
            "creepy_shot", "creepy_homing_shot",
            "creepy_roll_shot", "creepy_jump_shot",
        ]
        and bool(scene.enemy_spec.get("decides_match"))
        and bool(scene.enemy_spec.get("separates"))
    )
    long_platform = next(r for r in scene.stage.platforms if r.top == 220)
    short_platform = next(r for r in scene.stage.platforms if r.top == 268)
    creepy_stage_ok = (
        long_platform.left == 601
        and long_platform.right == 1080
        and short_platform.left == 170
        and short_platform.right == 484
        and abs(creepy.x - 1000.0) < 0.5
        and abs(creepy.y - 220.0) < 0.5
        and scene.stage.spawn("player_spawn") == (280, 620)
    )
    creepy_missing = len(creepy.anim.missing_paths()) if creepy.anim else -1
    creepy_fx_dir = ASSETS_DIR / "frames" / "creepy_shooter" / "fx"
    creepy_fx_missing = sum(
        1
        for name in (
            "creepy_bullet_00.png", "creepy_bullet_01.png",
            "creepy_homing_bullet_00.png", "creepy_homing_bullet_01.png",
            "creepy_homing_bullet_02.png",
            "creepy_lock_00.png", "creepy_lock_01.png", "creepy_lock_02.png",
        )
        if not (creepy_fx_dir / name).exists()
    )

    def _place_creepy(x, y):
        creepy.x = float(x)
        creepy.y = float(y)
        creepy.vx = 0.0
        creepy.vy = 0.0
        creepy.kb_vx = 0.0
        creepy.kb_time = 0.0
        creepy.on_ground = True
        creepy.state = FighterState.IDLE
        creepy.anim.set_clip("idle")

    def _place_player(x, y):
        creepy_player.x = float(x)
        creepy_player.y = float(y)
        creepy_player.vx = 0.0
        creepy_player.vy = 0.0
        creepy_player.on_ground = True
        creepy_player.hp = creepy_player.max_hp
        creepy_player.statuses = StatusSet()
        creepy_player.state = FighterState.IDLE
        if creepy_player.anim is not None:
            creepy_player.anim.set_clip("idle")

    def _reset_creepy():
        scene.reset()
        creepy.ai_enabled = False
        scene.input.clear()
        creepy_player.hp = creepy_player.max_hp

    # Skill 1: horizontal mid-lane shot, cooldown, ground miss, block collision.
    _reset_creepy()
    _place_creepy(800, 220)
    _place_player(950, 220)
    creepy.facing = 1
    creepy.force_attack(scene, creepy_player, "creepy_shot")
    for _ in range(42):
        scene.tick(FIXED_DT)
    shot_damage_ok = abs(creepy_player.hp - (creepy_player.max_hp - 30.0)) < 0.01
    shot_cd_ok = creepy.shot_cd > 0.2

    _reset_creepy()
    _place_creepy(800, 220)
    _place_player(800, 620)
    creepy.force_attack(scene, creepy_player, "creepy_shot")
    for _ in range(42):
        scene.tick(FIXED_DT)
    ground_miss_ok = creepy_player.hp == creepy_player.max_hp

    _reset_creepy()
    shot_barrier = scene.stage.barriers[0]
    test_bullet = CreepyBullet(
        owner=creepy, target=creepy_player,
        x=float(shot_barrier.left - 40.0), y=float(shot_barrier.centery),
        direction=1, speed=600.0, max_range=400.0,
        damage=1.0, knockback=0.0, hitstun=0.0, hitstop=0.0, radius=9.0,
    )
    for _ in range(30):
        test_bullet.update(FIXED_DT, scene)
    block_collision_ok = not test_bullet.alive
    creepy_shot_ok = (
        shot_damage_ok and shot_cd_ok and ground_miss_ok and block_collision_ok
    )

    # Skill 2: interruptible 1s wind-up, lock reticle, platform penetration.
    _reset_creepy()
    _place_creepy(800, 220)
    _place_player(800, 620)
    creepy.force_attack(scene, creepy_player, "creepy_homing_shot")
    for _ in range(30):
        scene.tick(FIXED_DT)
    lock_marker_ok = creepy.lock_marker_progress() is not None
    scene.draw(screen)
    for _ in range(40):
        scene.tick(FIXED_DT)
    homing_spawned = any(
        getattr(p, "visual_kind", "") == "creepy_homing_bullet"
        for p in scene.projectiles
    )
    for _ in range(80):
        scene.tick(FIXED_DT)
    homing_hit_ok = abs(creepy_player.hp - (creepy_player.max_hp - 20.0)) < 0.01
    lock_marker_cleared_ok = creepy.lock_marker_progress() is None

    _reset_creepy()
    _place_creepy(800, 220)
    _place_player(950, 220)
    creepy.force_attack(scene, creepy_player, "creepy_homing_shot")
    for _ in range(12):
        scene.tick(FIXED_DT)
    creepy.take_hit(5.0, 0.0, 0.1, 1)
    for _ in range(70):
        scene.tick(FIXED_DT)
    homing_interrupt_ok = (
        creepy.homing_cd > 6.0
        and not any(
            getattr(p, "visual_kind", "") == "creepy_homing_bullet"
            for p in scene.projectiles
        )
    )
    creepy_homing_ok = (
        lock_marker_ok and homing_spawned and homing_hit_ok
        and lock_marker_cleared_ok and homing_interrupt_ok
    )
    creepy_lock_ok = lock_marker_ok and lock_marker_cleared_ok

    # Skill 3: back-roll distance, shot damage, no i-frames, cooldown.
    _reset_creepy()
    _place_creepy(800, 220)
    _place_player(700, 220)
    roll_start_x = creepy.x
    creepy.force_attack(scene, creepy_player, "creepy_roll_shot")
    for _ in range(30):
        scene.tick(FIXED_DT)
    roll_distance_ok = abs((creepy.x - roll_start_x) - 140.0) < 4.0
    roll_damage_ok = (
        abs(creepy_player.hp - (creepy_player.max_hp - 24.0)) < 0.01
    )
    roll_cd_ok = creepy.roll_cd > 8.0

    _reset_creepy()
    _place_creepy(800, 220)
    _place_player(700, 220)
    creepy.force_attack(scene, creepy_player, "creepy_roll_shot")
    for _ in range(5):
        scene.tick(FIXED_DT)
    creepy.take_hit(5.0, 0.0, 0.1, 1)
    roll_no_iframes_ok = abs(creepy.hp - 195.0) < 0.01

    _reset_creepy()
    _place_creepy(1050, 220)
    _place_player(950, 220)
    roll_edge_ok = creepy.force_attack(scene, creepy_player, "creepy_roll_shot")
    for _ in range(50):
        scene.tick(FIXED_DT)
    roll_edge_ok = (
        roll_edge_ok and creepy.y > 300.0 and not creepy.on_ground
    )
    creepy_roll_ok = (
        roll_distance_ok and roll_damage_ok and roll_cd_ok
        and roll_no_iframes_ok and roll_edge_ok
    )

    # Skill 4: two platform heights, downward shot, no-platform refusal.
    _reset_creepy()
    _place_creepy(545, 620)
    _place_player(660, 620)
    long_jump_ok = creepy.force_attack(scene, creepy_player, "creepy_jump_shot")
    for _ in range(80):
        scene.tick(FIXED_DT)
    long_jump_ok = (
        long_jump_ok
        and abs(creepy.y - 220.0) < 1.0
        and creepy.on_ground
        and abs(creepy_player.hp - (creepy_player.max_hp - 24.0)) < 0.01
    )

    _reset_creepy()
    _place_creepy(540, 620)
    _place_player(300, 620)
    short_jump_ok = creepy.force_attack(scene, creepy_player, "creepy_jump_shot")
    for _ in range(80):
        scene.tick(FIXED_DT)
    short_jump_ok = short_jump_ok and abs(creepy.y - 268.0) < 1.0

    _reset_creepy()
    _place_creepy(1136, 620)
    _place_player(1100, 620)
    right_jump_ok = creepy.force_attack(scene, creepy_player, "creepy_jump_shot")
    for _ in range(80):
        scene.tick(FIXED_DT)
    right_jump_ok = right_jump_ok and abs(creepy.y - 220.0) < 1.0

    _reset_creepy()
    _place_creepy(800, 220)
    _place_player(950, 220)
    no_platform_ok = not creepy.force_attack(
        scene, creepy_player, "creepy_jump_shot"
    )
    creepy_jump_ok = (
        long_jump_ok and short_jump_ok and right_jump_ok and no_platform_ok
    )

    # AI priorities: far shot, blocked homing, near roll, grounded shot.
    _reset_creepy()
    _place_creepy(800, 220)
    _place_player(1000, 220)
    creepy.ai_enabled = True
    creepy.decision_cd = 0.0
    for _ in range(12):
        scene.tick(FIXED_DT)
    ai_far_shot_ok = creepy.attack_id == "creepy_shot"

    _reset_creepy()
    _place_creepy(800, 220)
    _place_player(1000, 620)
    creepy.ai_enabled = True
    creepy.decision_cd = 0.0
    for _ in range(12):
        scene.tick(FIXED_DT)
    ai_blocked_homing_ok = creepy.attack_id == "creepy_homing_shot"

    _reset_creepy()
    _place_creepy(800, 220)
    _place_player(700, 220)
    creepy.ai_enabled = True
    creepy.decision_cd = 0.0
    for _ in range(12):
        scene.tick(FIXED_DT)
    ai_near_roll_ok = creepy.attack_id == "creepy_roll_shot"

    _reset_creepy()
    _place_creepy(1000, 620)
    _place_player(300, 620)
    creepy.ai_enabled = True
    creepy.decision_cd = 0.0
    for _ in range(12):
        scene.tick(FIXED_DT)
    ai_ground_ok = creepy.attack_id == "creepy_shot"

    _reset_creepy()
    _place_creepy(300, 620)
    _place_player(1000, 620)
    creepy.ai_enabled = True
    creepy.decision_cd = 0.0
    ai_hop_ok = False
    for _ in range(150):
        scene.tick(FIXED_DT)
        if creepy.x > 490.0:
            ai_hop_ok = True
    creepy_ai_ok = (
        ai_far_shot_ok and ai_blocked_homing_ok and ai_near_roll_ok and ai_ground_ok
        and ai_hop_ok
    )

    # Slots V/C/X/Z map to the four skills; Z needs a valid takeoff.
    creepy_slot_checks = {}
    for key, expected in (
        (pygame.K_v, "creepy_shot"),
        (pygame.K_c, "creepy_homing_shot"),
        (pygame.K_x, "creepy_roll_shot"),
    ):
        _reset_creepy()
        _place_creepy(800, 220)
        _place_player(950, 220)
        scene.handle_debug_key(key)
        creepy_slot_checks[expected] = creepy.attack_id == expected
    _reset_creepy()
    _place_creepy(545, 620)
    _place_player(660, 620)
    scene.handle_debug_key(pygame.K_z)
    creepy_slot_checks["creepy_jump_shot"] = (
        creepy.attack_id == "creepy_jump_shot"
    )
    creepy_slots_ok = all(creepy_slot_checks.values())

    # KO -> WIN and projectile cleanup on switch.
    _reset_creepy()
    creepy.hp = 1.0
    creepy.take_hit(5.0, 0.0, 0.1, 1)
    scene.tick(FIXED_DT)
    creepy_win_ok = scene.match_over == "WIN"

    _reset_creepy()
    _place_creepy(800, 220)
    _place_player(800, 620)
    creepy.force_attack(scene, creepy_player, "creepy_homing_shot")
    for _ in range(65):
        scene.tick(FIXED_DT)
    had_homing = any(
        getattr(p, "visual_kind", "") == "creepy_homing_bullet"
        for p in scene.projectiles
    )
    scene.set_enemy("warrior")
    creepy_cleanup_ok = had_homing and not scene.projectiles
    creepy_stage_switch_ok = (
        scene.stage.platforms[0].left == 170 and scene.enemy.name == "Warrior"
    )
    scene.reset()

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
        f"q_cast_fx_ok={q_cast_fx_ok} q_impact_fx_ok={q_impact_fx_ok} "
        f"q_normal_color_ok={q_normal_color_ok} "
        f"q_flame_color_ok={q_flame_color_ok} q_flame_cast_ok={q_flame_cast_ok} "
        f"lina_q_fx_missing={lina_q_fx_missing} "
        f"nyra_present={nyra_present} nyra_wave_lmb_ok={nyra_wave_lmb_ok} "
        f"nyra_wave_burst_ok={nyra_wave_burst_ok} nyra_wave_burst_damage_ok={nyra_wave_burst_damage_ok} "
        f"nyra_thrust_ok={nyra_thrust_ok} nyra_q_slash_ok={nyra_q_slash_ok} "
        f"nyra_q_slash_cd_ok={nyra_q_slash_cd_ok} nyra_q_slash_range_ok={nyra_q_slash_range_ok} "
        f"nyra_q_armor_ok={nyra_q_armor_ok} nyra_e_armor_ok={nyra_e_armor_ok} "
        f"nyra_dash_distance_ok={nyra_dash_distance_ok} "
        f"nyra_dash_ok={nyra_dash_ok} "
        f"nyra_dash_cd_ok={nyra_dash_cd_ok} nyra_marks_reset_ok={nyra_marks_reset_ok} "
        f"nyra_marks_per_target_ok={nyra_marks_per_target_ok} "
        f"nyra_death_clear_ok={nyra_death_clear_ok} nyra_lock_ok={nyra_lock_ok} "
        f"nyra_dash_pass_ok={nyra_dash_pass_ok} "
        f"nyra_missing_frames={nyra_missing} "
        f"nyra_slash_fx_missing={nyra_slash_fx_missing} "
        f"veno_present={veno_present} veno_bite_ok={veno_bite_ok} "
        f"veno_bite_cd_ok={veno_bite_cd_ok} veno_poison_ok={veno_poison_ok} "
        f"veno_poison_stack_ok={veno_poison_stack_ok} "
        f"poison_interval_ok={poison_interval_ok} "
        f"poison_tint_ok={poison_tint_ok} "
        f"poison_stack_rules_ok={poison_stack_rules_ok} "
        f"veno_web_ok={veno_web_ok} "
        f"veno_web_radius_ok={veno_web_radius_ok} "
        f"veno_bite_hit_fx_ok={veno_bite_hit_fx_ok} "
        f"veno_poison_cast_ok={veno_poison_cast_ok} "
        f"veno_poison_impact_ok={veno_poison_impact_ok} "
        f"veno_web_cast_ok={veno_web_cast_ok} "
        f"veno_web_impact_ok={veno_web_impact_ok} "
        f"veno_vfx_missing={veno_vfx_missing} fx_cleanup_ok={fx_cleanup_ok} "
        f"veno_ai_ascent_ok={veno_ai_ascent_ok} veno_ai_descend_ok={veno_ai_descend_ok} "
        f"veno_slots_ok={veno_slots_ok} veno_win_ok={veno_win_ok} "
        f"veno_group_ok={veno_group_ok} "
        f"veno_group_cooldowns_ok={veno_group_cooldowns_ok} "
        f"veno_missing_frames={veno_missing} "
        f"bat_present={bat_present} default_enemy_ok={default_enemy_ok} "
        f"bat_flight_ok={bat_flight_ok} bat_dive_ok={bat_dive_ok} "
        f"bat_dive_hit_fx_ok={bat_dive_hit_fx_ok} "
        f"bat_slots_ok={bat_slots_ok} bat_hurt_airborne_ok={bat_hurt_airborne_ok} "
        f"bat_stun_airborne_ok={bat_stun_airborne_ok} bat_ko_ok={bat_ko_ok} "
        f"bat_win_ok={bat_win_ok} bat_sonic_ok={bat_sonic_ok} "
        f"bat_sonic_cast_ok={bat_sonic_cast_ok} "
        f"bat_sonic_impact_ok={bat_sonic_impact_ok} "
        f"bat_sonic_hitbox_ok={bat_sonic_hitbox_ok} "
        f"bat_sonic_return_ok={bat_sonic_return_ok} "
        f"bat_sonic_wall_return_ok={bat_sonic_wall_return_ok} "
        f"bat_sonic_block_return_ok={bat_sonic_block_return_ok} "
        f"bat_sonic_lock_ok={bat_sonic_lock_ok} bat_count_ok={bat_count_ok} "
        f"bat_group_ok={bat_group_ok} "
        f"bat_group_spawn_ok={bat_group_spawn_ok} "
        f"bat_group_cooldowns_ok={bat_group_cooldowns_ok} "
        f"bat_group_win_ok={bat_group_win_ok} "
        f"bat_missing_frames={bat_missing} "
        f"creepy_present={creepy_present} creepy_stage_ok={creepy_stage_ok} "
        f"creepy_shot_ok={creepy_shot_ok} creepy_homing_ok={creepy_homing_ok} "
        f"creepy_lock_ok={creepy_lock_ok} creepy_roll_ok={creepy_roll_ok} "
        f"creepy_roll_edge={roll_edge_ok} "
        f"creepy_jump_ok={creepy_jump_ok} "
        f"creepy_jump_long={long_jump_ok} creepy_jump_short={short_jump_ok} "
        f"creepy_jump_right={right_jump_ok} "
        f"creepy_jump_none={no_platform_ok} creepy_ai_ok={creepy_ai_ok} "
        f"creepy_ai_hop={ai_hop_ok} "
        f"creepy_slots_ok={creepy_slots_ok} creepy_win_ok={creepy_win_ok} "
        f"creepy_cleanup_ok={creepy_cleanup_ok} "
        f"creepy_stage_switch_ok={creepy_stage_switch_ok} "
        f"creepy_missing_frames={creepy_missing} creepy_fx_missing={creepy_fx_missing} "
        f"warrior_present={warrior_present} warrior_hp={warrior_hp:.1f} "
        f"warrior_hurt_ok={warrior_hurt_ok} super_armor_ok={super_armor_ok} "
        f"armor_interrupt_ok={armor_interrupt_ok} "
        f"warrior_attack_ok={warrior_attack_ok} "
        f"axe_slash_damage_ok={axe_slash_damage_ok} "
        f"lose_ok={lose_ok} win_ok={win_ok} "
        f"ai_default_off_ok={ai_default_off_ok} "
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
        f"platform_land_ok={platform_land_ok} "
        f"platform_side_ok={platform_side_ok} "
        f"platform_bottom_bump_ok={platform_bottom_bump_ok} "
        f"platform_toggle_ok={platform_toggle_ok} "
        f"ladder_climb_ok={ladder_climb_ok} ladder_down_ok={ladder_down_ok} "
        f"ladder_shift_no_down_ok={ladder_shift_no_down_ok} "
        f"lina_climb_anim_ok={lina_climb_anim_ok} "
        f"lina_climb_facing_ok={lina_climb_facing_ok} "
        f"lina_flame_climb_anim_ok={lina_flame_climb_anim_ok} "
        f"ladder_no_block_ok={ladder_no_block_ok} "
        f"nyra_climb_ok={nyra_climb_ok} "
        f"nyra_climb_anim_ok={nyra_climb_anim_ok} "
        f"platform_spawn_clear_ok={platform_spawn_clear_ok} "
        f"penetration_flag_ok={penetration_flag_ok} "
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
        and q_cast_fx_ok
        and q_impact_fx_ok
        and q_normal_color_ok
        and q_flame_color_ok
        and q_flame_cast_ok
        and lina_q_fx_missing == 0
        and nyra_present
        and nyra_wave_lmb_ok
        and nyra_wave_burst_ok
        and nyra_wave_burst_damage_ok
        and nyra_thrust_ok
        and nyra_q_slash_ok
        and nyra_q_slash_cd_ok
        and nyra_q_slash_range_ok
        and nyra_q_armor_ok
        and nyra_e_armor_ok
        and nyra_dash_distance_ok
        and nyra_dash_ok
        and nyra_dash_cd_ok
        and nyra_marks_reset_ok
        and nyra_marks_per_target_ok
        and nyra_death_clear_ok
        and nyra_lock_ok
        and nyra_dash_pass_ok
        and nyra_missing == 0
        and nyra_slash_fx_missing == 0
        and veno_present
        and veno_bite_ok
        and veno_bite_cd_ok
        and veno_poison_ok
        and veno_poison_stack_ok
        and poison_interval_ok
        and poison_tint_ok
        and poison_stack_rules_ok
        and veno_web_ok
        and veno_web_radius_ok
        and veno_bite_hit_fx_ok
        and veno_poison_cast_ok
        and veno_poison_impact_ok
        and veno_web_cast_ok
        and veno_web_impact_ok
        and veno_vfx_missing == 0
        and fx_cleanup_ok
        and veno_ai_ascent_ok
        and veno_ai_descend_ok
        and veno_slots_ok
        and veno_win_ok
        and veno_group_ok
        and veno_group_cooldowns_ok
        and veno_missing == 0
        and bat_present
        and default_enemy_ok
        and bat_flight_ok
        and bat_dive_ok
        and bat_dive_hit_fx_ok
        and bat_slots_ok
        and bat_hurt_airborne_ok
        and bat_stun_airborne_ok
        and bat_ko_ok
        and bat_win_ok
        and bat_sonic_ok
        and bat_sonic_cast_ok
        and bat_sonic_impact_ok
        and bat_sonic_hitbox_ok
        and bat_sonic_return_ok
        and bat_sonic_wall_return_ok
        and bat_sonic_block_return_ok
        and bat_sonic_lock_ok
        and bat_count_ok
        and bat_group_ok
        and bat_missing == 0
        and creepy_present
        and creepy_stage_ok
        and creepy_shot_ok
        and creepy_homing_ok
        and creepy_lock_ok
        and creepy_roll_ok
        and creepy_jump_ok
        and creepy_ai_ok
        and creepy_slots_ok
        and creepy_win_ok
        and creepy_cleanup_ok
        and creepy_stage_switch_ok
        and creepy_missing == 0
        and creepy_fx_missing == 0
        and warrior_present
        and warrior_hurt_ok
        and super_armor_ok
        and armor_interrupt_ok
        and warrior_attack_ok
        and axe_slash_damage_ok
        and lose_ok
        and win_ok
        and ai_default_off_ok
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
        and platform_land_ok
        and platform_side_ok
        and platform_bottom_bump_ok
        and platform_toggle_ok
        and ladder_climb_ok
        and ladder_down_ok
        and ladder_shift_no_down_ok
        and lina_climb_anim_ok
        and lina_climb_facing_ok
        and lina_flame_climb_anim_ok
        and ladder_no_block_ok
        and nyra_climb_ok
        and nyra_climb_anim_ok
        and platform_spawn_clear_ok
        and penetration_flag_ok
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
