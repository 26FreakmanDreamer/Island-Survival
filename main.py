"""Island Survival — Lina Seabright combat sandbox entry point."""

from __future__ import annotations

import os
import sys

import pygame

from game.combat import AttackRuntime, local_box_to_rect, resolve_hit
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
    default_character_ok = scene.character_id == "lina"
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

    # --- Phase C2: Rhea Thorn, poison throws and the dash-return ---
    # The default hit-group guard keeps Nyra's multi-hitbox attacks at one
    # hit per target while Rhea's dash uses separate out/back groups.
    scene.set_character("nyra")
    scene.set_enemy("dummy")
    scene.reset()
    default_group_nyra = scene.player
    default_group_dummy = scene.enemy
    default_group_nyra.x = 300.0
    default_group_dummy.x = 380.0
    default_group_nyra.facing = 1
    scene.input.buffer.press("punch")
    for _ in range(6):
        scene.tick(FIXED_DT)
    default_hit_group_ok = (
        default_group_nyra.attack_runtime is not None
        and set(default_group_nyra.attack_runtime.hit_targets) == {"default"}
        and abs(default_group_dummy.hp - 980.0) < 0.01
    )

    def _rhea_setup(enemy_id: str = "dummy", enemy_x: float = 500.0):
        scene.set_character("rhea")
        scene.set_enemy(enemy_id)
        scene.reset()
        rhea = scene.player
        enemy = scene.enemy
        enemy.ai_enabled = False
        scene.stage.blocks_enabled = False
        rhea.x = 300.0
        rhea.y = scene.stage.ground_y
        rhea.on_ground = True
        enemy.x = enemy_x
        enemy.y = scene.stage.ground_y
        enemy.on_ground = True
        rhea.facing = 1
        return rhea, enemy

    def _rhea_tick_until(predicate, limit: int = 240) -> int:
        """Tick until a predicate holds; hitstop can shift fixed tick counts."""
        ticks = 0
        while not predicate() and ticks < limit:
            scene.tick(FIXED_DT)
            ticks += 1
        return ticks

    rhea_roster_order_ok = (
        list(scene.store.roster.get("characters", {}))
        == ["lina", "nyra", "rhea", "eira"]
    )
    rhea, rhea_enemy = _rhea_setup("dummy", 500.0)
    rhea_present = (
        rhea.name == "Rhea Thorn"
        and rhea.max_hp == 100.0
        and rhea.basic_atk == 20.0
        and not hasattr(rhea, "energy")
        and rhea.poison_source == "rhea_poison"
        and abs(rhea.q_cd_max - 6.0) < 1e-6
        and abs(rhea.e_cd_max - 10.0) < 1e-6
        and abs(rhea.climb_draw_scale - 1.1) < 1e-6
    )
    rhea_default_ok = default_character_ok and default_enemy_ok
    rhea_knockback_ok = (
        float(
            scene.store.attacks["rhea_slash"]["events"][0].get("knockback", 0.0)
        )
        == 60.0
        and all(
            float(event.get("knockback", 0.0)) == 0.0
            for attack_id in (
                "rhea_throw",
                "rhea_poison_throw",
                "rhea_dash",
                "rhea_dash_return",
            )
            for event in scene.store.attacks[attack_id].get("events", [])
            if event.get("type") in ("hitbox", "projectile")
        )
    )

    # LMB: 20 damage, right -> left -> right, other attacks never flip it.
    rhea, rhea_enemy = _rhea_setup("dummy", 380.0)
    scene.input.buffer.press("punch")
    for _ in range(3):
        scene.tick(FIXED_DT)
    lmb_clip_1 = rhea.anim.clip_name
    lmb_right_1 = rhea.slash_right
    for _ in range(30):
        scene.tick(FIXED_DT)
    scene.input.buffer.press("punch")
    for _ in range(3):
        scene.tick(FIXED_DT)
    lmb_clip_2 = rhea.anim.clip_name
    lmb_right_2 = rhea.slash_right
    for _ in range(30):
        scene.tick(FIXED_DT)
    scene.input.buffer.press("punch")
    for _ in range(3):
        scene.tick(FIXED_DT)
    lmb_clip_3 = rhea.anim.clip_name
    lmb_right_3 = rhea.slash_right
    for _ in range(3):
        scene.tick(FIXED_DT)
    lmb_kb_ok = (
        rhea_enemy.kb_start == 60.0
        and rhea_enemy.kb_time > 0.0
        and rhea_enemy.kb_vx > 0.0
    )
    for _ in range(27):
        scene.tick(FIXED_DT)
    lmb_damage = 1000.0 - rhea_enemy.hp
    no_flip_ok = True
    for attack_id in ("rhea_throw", "rhea_poison_throw", "rhea_dash"):
        rhea.slash_right = True
        rhea.start_attack(attack_id, scene, rhea_enemy)
        no_flip_ok = no_flip_ok and rhea.slash_right
        rhea.reset()
    rhea_lmb_ok = (
        lmb_clip_1 == "rhea_slash_r"
        and lmb_clip_2 == "rhea_slash_l"
        and lmb_clip_3 == "rhea_slash_r"
        and not lmb_right_1
        and lmb_right_2
        and not lmb_right_3
        and abs(lmb_damage - 60.0) < 0.01
        and lmb_kb_ok
        and no_flip_ok
    )

    # The slash must reach a grounded Veno's low (75px) hurtbox.
    rhea, rhea_veno = _rhea_setup("veno", 400.0)
    for enemy in scene.enemies:
        enemy.ai_enabled = False
    rhea_veno.on_ground = True
    rhea_veno.y = scene.stage.ground_y
    scene.input.buffer.press("punch")
    for _ in range(30):
        scene.tick(FIXED_DT)
    rhea_lmb_ground_veno_ok = (
        abs((rhea_veno.max_hp - rhea_veno.hp) - 20.0) < 0.01
    )

    # Passive: only an existing rhea_poison is extended, once per target and
    # attack, without a cap; Veno's poison and absent poison stay untouched.
    rhea, rhea_enemy = _rhea_setup("dummy", 500.0)
    rhea_enemy.statuses.clear()
    rhea.poison_extended_targets.clear()
    rhea_enemy.statuses.add_poison("rhea_poison", 2.0, 0.0)
    rhea.on_hit_success({"extends_poison": True}, rhea_enemy, 0.0)
    passive_first = rhea_enemy.statuses.poisons[0].remaining
    rhea.on_hit_success({"extends_poison": True}, rhea_enemy, 0.0)
    passive_second = rhea_enemy.statuses.poisons[0].remaining
    rhea.poison_extended_targets.clear()
    rhea.on_hit_success({"extends_poison": True}, rhea_enemy, 0.0)
    passive_third = rhea_enemy.statuses.poisons[0].remaining
    rhea_enemy.statuses.clear()
    rhea.poison_extended_targets.clear()
    rhea.on_hit_success({"extends_poison": True}, rhea_enemy, 0.0)
    passive_no_create = not rhea_enemy.statuses.poisons
    rhea_enemy.statuses.add_poison("veno_poison", 2.0, 0.0)
    rhea.poison_extended_targets.clear()
    rhea.on_hit_success({"extends_poison": True}, rhea_enemy, 0.0)
    passive_veno = (
        len(rhea_enemy.statuses.poisons) == 1
        and rhea_enemy.statuses.poisons[0].source == "veno_poison"
        and abs(rhea_enemy.statuses.poisons[0].remaining - 2.0) < 1e-6
    )
    rhea_enemy.statuses.clear()
    rhea_enemy.statuses.add_poison("rhea_poison", 100.0, 0.0)
    rhea.poison_extended_targets.clear()
    rhea.on_hit_success({"extends_poison": True}, rhea_enemy, 0.0)
    passive_no_cap = abs(rhea_enemy.statuses.poisons[0].remaining - 101.0) < 1e-6

    rhea, rhea_enemy = _rhea_setup("creepy_shooter", 380.0)
    rhea_enemy.statuses.add_poison("rhea_poison", 10.0, 0.0)
    scene.input.buffer.press("punch")
    for _ in range(30):
        scene.tick(FIXED_DT)
    lmb_extend_actual = (
        len(rhea_enemy.statuses.poisons) == 1
        and rhea_enemy.statuses.poisons[0].remaining > 10.0
    )
    lmb_poison_damage = 200.0 - rhea_enemy.hp
    rhea_passive_ok = (
        abs(passive_first - 3.0) < 1e-6
        and abs(passive_second - 3.0) < 1e-6
        and abs(passive_third - 4.0) < 1e-6
        and passive_no_create
        and passive_veno
        and passive_no_cap
        and lmb_extend_actual
        and abs(lmb_poison_damage - 26.0) < 0.01
    )

    rhea, rhea_enemy = _rhea_setup("warrior", 380.0)
    rhea_enemy.statuses.add_poison("rhea_poison", 10.0, 0.0)
    scene.input.buffer.press("punch")
    for _ in range(30):
        scene.tick(FIXED_DT)
    passive_300_damage = 300.0 - rhea_enemy.hp

    rhea, rhea_enemy = _rhea_setup("dummy", 380.0)
    rhea_enemy.statuses.add_poison("rhea_poison", 10.0, 0.0)
    scene.input.buffer.press("punch")
    for _ in range(30):
        scene.tick(FIXED_DT)
    passive_1000_damage = 1000.0 - rhea_enemy.hp

    rhea, rhea_enemy = _rhea_setup("creepy_shooter", 380.0)
    rhea_enemy.statuses.add_poison("veno_poison", 10.0, 0.0)
    scene.input.buffer.press("punch")
    for _ in range(30):
        scene.tick(FIXED_DT)
    passive_veno_damage = 200.0 - rhea_enemy.hp
    rhea_passive_3pct_ok = (
        abs(passive_300_damage - 29.0) < 0.01
        and abs(passive_1000_damage - 50.0) < 0.01
    )
    rhea_passive_veno_ok = abs(passive_veno_damage - 20.0) < 0.01

    # RMB: 24 damage, steel shuriken, mid lane, and +1s poison extension.
    rhea, rhea_enemy = _rhea_setup("creepy_shooter", 500.0)
    rhea_enemy.statuses.add_poison("rhea_poison", 10.0, 0.0)
    scene.input.buffer.press("kick")
    rmb_projectile = None
    rmb_cast = False
    rmb_impact = False
    for _ in range(60):
        scene.tick(FIXED_DT)
        if scene.projectiles and rmb_projectile is None:
            rmb_projectile = scene.projectiles[0]
        if any(fx.kind == "rhea_shuriken_cast" for fx in scene.fx_effects):
            rmb_cast = True
        if any(fx.kind == "rhea_shuriken_impact" for fx in scene.fx_effects):
            rmb_impact = True
        if rhea_enemy.hp < rhea_enemy.max_hp:
            break
    rhea_rmb_ok = (
        abs(rhea_enemy.hp - 170.0) < 0.01
        and rmb_projectile is not None
        and rmb_projectile.kind == "rhea_shuriken"
        and rmb_projectile.visual_kind == "rhea_shuriken"
        and abs(rmb_projectile.speed - 850.0) < 1e-6
        and abs(rmb_projectile.max_range - 900.0) < 1e-6
        and abs(rmb_projectile.radius - 12.0) < 1e-6
        and abs(rmb_projectile.y - 500.0) < 1e-6
        and rmb_cast
        and rmb_impact
        and len(rhea_enemy.statuses.poisons) == 1
        and rhea_enemy.statuses.poisons[0].remaining > 10.0
    )

    # Q: 8% target max HP at hit time, 5s poison at 3%/s, no passive +1.
    rhea, rhea_enemy = _rhea_setup("creepy_shooter", 500.0)
    scene.input.buffer.press("q")
    q_initial = None
    q_poison = None
    q_describe_ok = False
    q_cast = False
    q_impact = False
    for _ in range(80):
        scene.tick(FIXED_DT)
        if any(fx.kind == "rhea_poison_shuriken_cast" for fx in scene.fx_effects):
            q_cast = True
        if any(fx.kind == "rhea_poison_impact" for fx in scene.fx_effects):
            q_impact = True
        if rhea_enemy.hp < rhea_enemy.max_hp and q_initial is None:
            q_initial = rhea_enemy.max_hp - rhea_enemy.hp
            q_poison = list(rhea_enemy.statuses.poisons)
            q_describe_ok = any(
                "poison[rhea_poison]" in line
                for line in rhea_enemy.statuses.describe()
            )
            break
    q_no_passive = (
        len(q_poison or []) == 1
        and abs(q_poison[0].remaining - 5.0) < 1e-6
        and abs(q_poison[0].dps - 6.0) < 1e-6
    )
    for _ in range(400):
        scene.tick(FIXED_DT)
        if not rhea_enemy.statuses.poisons:
            break
    q_total = 200.0 - rhea_enemy.hp
    rhea_q_ok = (
        q_initial is not None
        and abs(q_initial - 40.0) < 0.01
        and abs(q_total - 70.0) < 0.01
        and q_cast
        and q_impact
        and q_no_passive
        and q_describe_ok
        and rhea.q_cd > 0.0
    )

    rhea, rhea_enemy = _rhea_setup("warrior", 500.0)
    scene.input.buffer.press("q")
    q300_initial = None
    for _ in range(80):
        scene.tick(FIXED_DT)
        if rhea_enemy.hp < rhea_enemy.max_hp:
            q300_initial = rhea_enemy.max_hp - rhea_enemy.hp
            break
    rhea_q_300_ok = (
        q300_initial is not None and abs(q300_initial - 48.0) < 0.01
    )

    rhea, rhea_enemy = _rhea_setup("dummy", 500.0)
    scene.input.buffer.press("q")
    q1000_initial = None
    for _ in range(80):
        scene.tick(FIXED_DT)
        if rhea_enemy.hp < rhea_enemy.max_hp:
            q1000_initial = rhea_enemy.max_hp - rhea_enemy.hp
            break
    rhea_q_dummy_ok = (
        q1000_initial is not None and abs(q1000_initial - 104.0) < 0.01
    )

    rhea, rhea_enemy = _rhea_setup("creepy_shooter", 500.0)
    rhea_enemy.statuses.add("damage_reduction", 20.0, value=0.5)
    scene.input.buffer.press("q")
    qdr_initial = None
    qdr_dps = None
    for _ in range(80):
        scene.tick(FIXED_DT)
        if rhea_enemy.hp < rhea_enemy.max_hp:
            qdr_initial = rhea_enemy.max_hp - rhea_enemy.hp
            qdr_dps = (
                rhea_enemy.statuses.poisons[0].dps
                if rhea_enemy.statuses.poisons
                else None
            )
            break
    for _ in range(400):
        scene.tick(FIXED_DT)
        if not rhea_enemy.statuses.poisons:
            break
    qdr_total = 200.0 - rhea_enemy.hp
    rhea_q_dr_ok = (
        qdr_initial is not None
        and abs(qdr_initial - 20.0) < 0.01
        and abs(qdr_total - 50.0) < 0.01
        and abs((qdr_dps or 0.0) - 6.0) < 1e-6
    )

    rhea, rhea_enemy = _rhea_setup("creepy_shooter", 500.0)
    rhea_enemy.statuses.clear()
    rhea_enemy.statuses.add_poison("rhea_poison", 2.0, 0.0)

    class _FakePoisonProjectile:
        pass

    fake_projectile = _FakePoisonProjectile()
    fake_projectile.target = rhea_enemy
    fake_projectile.status = "poison"
    fake_projectile.status_duration = 5.0
    fake_projectile.status_dps_pct = 0.03
    fake_projectile.extends_poison = False
    rhea.on_projectile_hit(fake_projectile)
    same_source_stack_ok = (
        len(rhea_enemy.statuses.poisons) == 1
        and abs(rhea_enemy.statuses.poisons[0].remaining - 7.0) < 1e-6
    )
    rhea_enemy.statuses.clear()
    rhea_enemy.statuses.add_poison("veno_poison", 2.0, 0.0)
    rhea.on_projectile_hit(fake_projectile)
    cross_source_ok = (
        len(rhea_enemy.statuses.poisons) == 2
        and any(
            poison.source == "veno_poison"
            and abs(poison.remaining - 2.0) < 1e-6
            for poison in rhea_enemy.statuses.poisons
        )
        and any(
            poison.source == "rhea_poison"
            and abs(poison.remaining - 5.0) < 1e-6
            for poison in rhea_enemy.statuses.poisons
        )
    )
    rhea_q_stack_ok = same_source_stack_ok and cross_source_ok

    rhea, rhea_enemy = _rhea_setup("creepy_shooter", 500.0)
    rhea_enemy.hp = 30.0
    scene.input.buffer.press("q")
    for _ in range(80):
        scene.tick(FIXED_DT)
        if rhea_enemy.hp <= 0.0:
            break
    rhea_q_kill_ok = (
        rhea_enemy.hp <= 0.0
        and not rhea_enemy.statuses.poisons
        and scene.match_over == "WIN"
    )

    # Point-blank throws use a body-adjacent check; long throws reach 900px.
    rhea, rhea_enemy = _rhea_setup("dummy", 290.0)
    scene.input.buffer.press("kick")
    for _ in range(40):
        scene.tick(FIXED_DT)
        if rhea_enemy.hp < rhea_enemy.max_hp:
            break
    close_rmb_ok = abs(rhea_enemy.hp - 976.0) < 0.01

    rhea, rhea_enemy = _rhea_setup("dummy", 290.0)
    scene.input.buffer.press("q")
    for _ in range(50):
        scene.tick(FIXED_DT)
        if rhea_enemy.hp < rhea_enemy.max_hp:
            break
    close_q_ok = (
        abs(rhea_enemy.hp - 896.0) < 0.01
        and len(rhea_enemy.statuses.poisons) == 1
    )
    rhea_close_range_ok = close_rmb_ok and close_q_ok

    rhea, rhea_enemy = _rhea_setup("dummy", 1100.0)
    scene.input.buffer.press("kick")
    for _ in range(80):
        scene.tick(FIXED_DT)
        if rhea_enemy.hp < rhea_enemy.max_hp:
            break
    rhea_range_ok = (
        abs(rhea_enemy.hp - 976.0) < 0.01
        and abs(
            float(scene.store.attacks["rhea_throw"]["events"][0].get("range", 0.0))
            - 900.0
        ) < 1e-6
        and abs(
            float(scene.store.attacks["rhea_poison_throw"]["events"][0].get("range", 0.0))
            - 900.0
        ) < 1e-6
    )

    # E: outbound 16, free-control 2s window, manual return 14, cooldown at end.
    rhea, rhea_enemy = _rhea_setup("dummy", 500.0)
    dash_start_x = rhea.x
    scene.input.buffer.press("e")
    _rhea_tick_until(lambda: rhea.e_phase == "window")
    dash_end_x = rhea.x
    outbound_damage = 1000.0 - rhea_enemy.hp
    window_open = (
        rhea.e_phase == "window"
        and rhea.e_window > 1.9
        and rhea.e_cd == 0.0
        and rhea.attack_id is None
        and abs(outbound_damage - 16.0) < 0.01
        and dash_end_x > 850.0
    )
    scene.input.buffer.press("e")
    _rhea_tick_until(lambda: rhea.e_phase is None)
    dash_damage = 1000.0 - rhea_enemy.hp
    rhea_dash_ok = (
        window_open
        and abs(dash_damage - 30.0) < 0.01
        and abs(rhea.x - dash_start_x) < 1.0
        and rhea.e_cd > 8.0
        and rhea.attack_id is None
        and rhea.facing == 1
        and abs(rhea_enemy.x - rhea.x) >= 84.5
    )

    rhea, rhea_enemy = _rhea_setup("dummy", 500.0)
    scene.input.buffer.press("e")
    _rhea_tick_until(lambda: rhea.e_phase == "window")
    no_return_x = rhea.x
    _rhea_tick_until(lambda: rhea.e_phase is None, 300)
    rhea_e_no_return_ok = (
        abs(rhea.x - no_return_x) < 1.0
        and no_return_x > 850.0
        and rhea.e_cd > 8.0
        and abs((1000.0 - rhea_enemy.hp) - 16.0) < 0.01
    )

    rhea, rhea_enemy = _rhea_setup("dummy", 500.0)
    start_x = rhea.x
    scene.input.buffer.press("e")
    for _ in range(6):
        scene.tick(FIXED_DT)
    scene.input.buffer.press("e")
    _rhea_tick_until(lambda: rhea.e_phase is None, 240)
    rhea_e_buffered_ok = (
        abs(rhea.x - start_x) < 1.0
        and abs((1000.0 - rhea_enemy.hp) - 30.0) < 0.01
        and rhea.e_cd > 8.0
    )

    rhea, rhea_enemy = _rhea_setup("dummy", 500.0)
    scene.input.buffer.press("e")
    _rhea_tick_until(lambda: rhea.e_phase == "window")
    window_before = rhea.e_window
    scene.input.buffer.press("jump")
    for _ in range(3):
        scene.tick(FIXED_DT)
    airborne = not rhea.on_ground
    scene.input.buffer.press("e")
    for _ in range(3):
        scene.tick(FIXED_DT)
    ignored_air = rhea.e_phase == "window" and rhea.attack_id is None
    window_after = rhea.e_window
    _rhea_tick_until(lambda: rhea.on_ground, 120)
    scene.input.buffer.press("e")
    _rhea_tick_until(lambda: rhea.e_phase is None, 240)
    rhea_e_air_ok = (
        airborne
        and ignored_air
        and window_after < window_before
        and abs(rhea.x - 300.0) < 1.0
        and rhea.e_cd > 0.0
    )

    rhea, rhea_enemy = _rhea_setup("dummy", 500.0)
    scene.input.buffer.press("e")
    _rhea_tick_until(lambda: rhea.e_phase == "window")
    rhea.take_hit(5.0, 0.0, 0.2, 1)
    rhea_e_hit_cancel_ok = (
        rhea.e_phase is None
        and rhea.e_window == 0.0
        and rhea.e_cd > 8.0
    )

    rhea, rhea_enemy = _rhea_setup("creepy_shooter", 500.0)
    scene.input.buffer.press("e")
    _rhea_tick_until(lambda: rhea.e_phase == "window")
    window_before_q = rhea.e_window
    scene.input.buffer.press("q")
    for _ in range(10):
        scene.tick(FIXED_DT)
    rhea_e_window_q_ok = (
        rhea.e_phase == "window"
        and rhea.e_window < window_before_q
        and rhea.q_cd > 0.0
    )

    rhea, rhea_enemy = _rhea_setup("dummy", 500.0)
    scene.input.buffer.press("e")
    _rhea_tick_until(lambda: rhea.e_phase == "window")
    scene.input.buffer.press("e")
    for _ in range(6):
        scene.tick(FIXED_DT)
    return_armor = (
        rhea.e_phase == "return"
        and rhea.statuses.has("super_armor")
        and rhea.attack_id == "rhea_dash_return"
    )
    return_hp_before = rhea.hp
    rhea.take_hit(10.0, 300.0, 0.4, -1, launch=200.0)
    return_armor_hit = (
        abs(rhea.hp - (return_hp_before - 10.0)) < 0.01
        and rhea.hitstun == 0.0
        and rhea.kb_vx == 0.0
        and rhea.e_phase == "return"
    )
    _rhea_tick_until(lambda: rhea.e_phase is None, 240)
    rhea_e_return_armor_ok = (
        return_armor and return_armor_hit and rhea.e_cd > 8.0
    )

    rhea, rhea_enemy = _rhea_setup("creepy_shooter", 500.0)
    rhea_enemy.statuses.add_poison("rhea_poison", 10.0, 0.0)
    scene.input.buffer.press("e")
    _rhea_tick_until(lambda: rhea.e_phase == "window")
    scene.input.buffer.press("e")
    _rhea_tick_until(lambda: rhea.e_phase is None, 240)
    rhea_e_poison_ok = abs((200.0 - rhea_enemy.hp) - 60.0) < 0.01

    rhea, rhea_enemy = _rhea_setup("creepy_shooter", 500.0)
    rhea_enemy.statuses.add_poison("veno_poison", 10.0, 0.0)
    scene.input.buffer.press("e")
    _rhea_tick_until(lambda: rhea.e_phase == "window")
    scene.input.buffer.press("e")
    _rhea_tick_until(lambda: rhea.e_phase is None, 240)
    rhea_e_veno_no_bonus_ok = abs((200.0 - rhea_enemy.hp) - 30.0) < 0.01

    rhea, rhea_enemy = _rhea_setup("warrior", 500.0)
    rhea_enemy.statuses.add_poison("rhea_poison", 10.0, 0.0)
    scene.input.buffer.press("e")
    _rhea_tick_until(lambda: rhea.e_phase == "window")
    scene.input.buffer.press("e")
    _rhea_tick_until(lambda: rhea.e_phase is None, 240)
    rhea_e_poison_300_ok = abs((300.0 - rhea_enemy.hp) - 75.0) < 0.01

    rhea, rhea_enemy = _rhea_setup("creepy_shooter", 500.0)
    rhea_enemy.statuses.add_poison("rhea_poison", 10.0, 0.0)
    rhea_enemy.statuses.add("damage_reduction", 20.0, value=0.5)
    scene.input.buffer.press("e")
    _rhea_tick_until(lambda: rhea.e_phase == "window")
    scene.input.buffer.press("e")
    _rhea_tick_until(lambda: rhea.e_phase is None, 240)
    e200_dr_damage = 200.0 - rhea_enemy.hp

    rhea, rhea_enemy = _rhea_setup("warrior", 500.0)
    rhea_enemy.statuses.add_poison("rhea_poison", 10.0, 0.0)
    rhea_enemy.statuses.add("damage_reduction", 20.0, value=0.5)
    scene.input.buffer.press("e")
    _rhea_tick_until(lambda: rhea.e_phase == "window")
    scene.input.buffer.press("e")
    _rhea_tick_until(lambda: rhea.e_phase is None, 240)
    e300_dr_damage = 300.0 - rhea_enemy.hp
    rhea_e_dr_ok = (
        abs(e200_dr_damage - 30.0) < 0.01
        and abs(e300_dr_damage - 37.5) < 0.01
    )

    rhea, rhea_enemy = _rhea_setup("dummy", 900.0)
    scene.input.buffer.press("e")
    for _ in range(6):
        scene.tick(FIXED_DT)
    armor_started = (
        rhea.statuses.has("super_armor") and rhea.attack_id == "rhea_dash"
    )
    armor_hp_before = rhea.hp
    rhea.take_hit(10.0, 300.0, 0.4, -1, launch=200.0)
    for kind in ("knockback", "knock_up", "freeze", "stun"):
        rhea.statuses.add(kind, 1.0)
    rhea.statuses.add("slow", 1.0, value=0.5)
    armor_immune = not any(
        rhea.statuses.has(kind)
        for kind in ("knockback", "knock_up", "freeze", "stun", "slow")
    )
    for _ in range(24):
        scene.tick(FIXED_DT)
    armor_mid = rhea.statuses.has("super_armor")
    rhea.take_hit(10.0, 300.0, 0.4, -1)
    armor_anim = rhea.anim.clip_name == "rhea_dash"
    outbound_armor_ok = (
        armor_started
        and rhea.attack_id == "rhea_dash"
        and rhea.state == FighterState.ATTACK
        and armor_mid
        and armor_immune
        and abs(rhea.hp - (armor_hp_before - 20.0)) < 0.01
        and rhea.hitstun == 0.0
        and rhea.kb_vx == 0.0
        and rhea.vy == 0.0
        and armor_anim
    )
    _rhea_tick_until(lambda: rhea.e_phase == "window")
    rhea_e_armor_ok = (
        outbound_armor_ok and not rhea.statuses.has("super_armor")
    )

    rhea, rhea_enemy = _rhea_setup("dummy", 900.0)
    scene.stage.blocks_enabled = True
    scene.input.buffer.press("e")
    _rhea_tick_until(lambda: rhea.e_phase == "window")
    terrain_pass_x = rhea.x
    scene.input.buffer.press("e")
    _rhea_tick_until(lambda: rhea.e_phase is None, 240)
    terrain_returned = abs(rhea.x - 300.0) < 1.0

    rhea, rhea_enemy = _rhea_setup("dummy", 900.0)
    scene.stage.blocks_enabled = True
    rhea.x = 150.0
    scene.input.buffer.press("e")
    _rhea_tick_until(lambda: rhea.e_phase == "window")
    barrier_pushed_out = not any(
        scene.stage.body_rect(rhea).colliderect(block)
        for block in scene.stage.blocks
    )
    rhea_e_terrain_ok = (
        terrain_pass_x > 800.0
        and terrain_returned
        and barrier_pushed_out
    )

    rhea, rhea_enemy = _rhea_setup("dummy", 600.0)
    scene.stage.blocks_enabled = True
    projectile_block = pygame.Rect(430, 460, 40, 80)
    scene.stage.blocks.append(projectile_block)
    scene.input.buffer.press("kick")
    for _ in range(60):
        scene.tick(FIXED_DT)
    rmb_blocked = (
        rhea_enemy.hp == rhea_enemy.max_hp and not scene.projectiles
    )
    rhea.q_cd = 0.0
    scene.input.buffer.press("q")
    for _ in range(80):
        scene.tick(FIXED_DT)
    q_blocked = rhea_enemy.hp == rhea_enemy.max_hp and not scene.projectiles
    scene.stage.blocks.remove(projectile_block)
    scene.stage.blocks_enabled = False
    rhea_projectile_block_ok = rmb_blocked and q_blocked

    rhea, rhea_enemy = _rhea_setup("dummy", 500.0)
    rhea_enemy.statuses.add_poison("rhea_poison", 5.0, 0.0)
    scene.input.buffer.press("q")
    for _ in range(16):
        scene.tick(FIXED_DT)
    had_projectile = bool(scene.projectiles)
    rhea.q_cd = 5.0
    rhea.e_cd = 7.0
    scene.reset()
    rhea_cleanup_ok = (
        had_projectile
        and rhea.q_cd == 0.0
        and rhea.e_cd == 0.0
        and not scene.projectiles
        and not rhea_enemy.statuses.has("poison")
    )

    rhea, rhea_enemy = _rhea_setup("dummy", 500.0)
    scene.input.buffer.press("e")
    _rhea_tick_until(lambda: rhea.e_phase == "window")
    scene.reset()
    rhea_cleanup_window_ok = (
        rhea.e_phase is None
        and rhea.e_window == 0.0
        and rhea.e_cd == 0.0
        and rhea.attack_runtime is None
        and not rhea.ignore_terrain
    )

    scene.set_character("rhea")
    scene.set_enemy("dummy")
    scene.reset()
    rhea = scene.player
    rhea_ladder = scene.stage.ladders[0]
    scene.input.clear()
    rhea.x = float(rhea_ladder.rect.centerx)
    rhea.y = float(rhea_ladder.bottom_y)
    rhea.on_ground = True
    rhea.vy = 0.0
    scene.input.key_down(pygame.K_w)
    scene.tick(FIXED_DT)
    rhea_climb_ok = (
        rhea.climbing
        and rhea.anim.clip_name == "climb"
        and len(rhea.anim.clip["frames"]) == 2
        and rhea.anim.frame_index == 0
        and abs(rhea.climb_draw_scale - 1.1) < 1e-6
    )
    scene.input.key_up(pygame.K_w)
    scene.input.clear()
    rhea_missing = len(rhea.anim.missing_paths())
    rhea_fx_missing = sum(
        1
        for stem in ("rhea_shuriken", "rhea_poison_shuriken")
        for index in range(3)
        if not (
            ASSETS_DIR / "frames" / "rhea" / "fx" / f"{stem}_{index:02d}.png"
        ).exists()
    )
    scene.stage.blocks_enabled = True

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
        and all(enemy.x >= 640.0 for enemy in scene.enemies)
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

    # The 3-Veno group must stagger the same skill; observe real AI starts.
    def _min_start_gap(times):
        ordered = sorted(times)
        if len(ordered) < 2:
            return 0.0
        return min(b - a for a, b in zip(ordered, ordered[1:]))

    scene.enemy_count_override = None
    scene.set_enemy("warrior")
    scene.set_enemy("veno")
    scene.reset()
    scene.player.x = 280.0
    scene.player.y = scene.stage.ground_y
    scene.player.on_ground = True
    scene.player.invincible = True
    for enemy in scene.enemies:
        enemy.ai_enabled = True
    veno_seen = {}
    veno_starts = {"veno_poison": [], "veno_web": []}
    for _ in range(int(4.0 / FIXED_DT)):
        scene.tick(FIXED_DT)
        for enemy in scene.enemies:
            for attack_id in veno_starts:
                started = enemy.last_attack_at.get(attack_id)
                key = (id(enemy), attack_id)
                if started is not None and veno_seen.get(key) != started:
                    veno_seen[key] = started
                    veno_starts[attack_id].append(started)
    veno_poison_gap = _min_start_gap(veno_starts["veno_poison"])
    veno_web_gap = _min_start_gap(veno_starts["veno_web"])
    saved_sim_time = float(scene.sim_time)
    scene.sim_time = 10.0
    veno_a, veno_b = list(scene.enemies)[:2]
    veno_a.note_attack_started(scene, "veno_bite")
    veno_bite_gate = veno_b.group_skill_recent(scene, "veno_bite", 0.8)
    scene.sim_time = 10.8
    veno_bite_gate_clear = not veno_b.group_skill_recent(
        scene, "veno_bite", 0.8
    )
    scene.sim_time = saved_sim_time
    veno_group_gap_ok = (
        len(veno_starts["veno_poison"]) >= 2
        and len(veno_starts["veno_web"]) >= 2
        and veno_poison_gap >= 1.2 - 2 * FIXED_DT
        and veno_web_gap >= 1.2 - 2 * FIXED_DT
        and veno_bite_gate
        and veno_bite_gate_clear
    )

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
        and 0.6 <= sonic_stun_remaining <= 0.85
        and abs(
            scene.store.attacks["bat_sonic"]["events"][0]["status_duration"]
            - 0.8
        ) < 1e-6
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
    # The Bat stage is intentionally empty; inject a barrier for this
    # block-bounce test only.
    injected_block = pygame.Rect(700, 560, 90, 60)
    scene.stage.blocks.append(injected_block)
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
    scene.stage.blocks.remove(injected_block)

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
    bat_xs = [enemy.x for enemy in bat_group]
    bat_flight_remaining = sorted(
        round(enemy.flight_remaining, 3) for enemy in bat_group
    )
    bat_flight_bags_ok = all(
        (1 if enemy.flight_side == "high" else 0)
        + enemy.flight_bag.count("high") == 3
        and (1 if enemy.flight_side == "low" else 0)
        + enemy.flight_bag.count("low") == 2
        for enemy in bat_group
    )
    bat_group_spawn_ok = (
        len(bat_group) == 5
        and all(not enemy.on_ground for enemy in bat_group)
        and len({round(enemy.y) for enemy in bat_group}) == 5
        and max(enemy.hover_height for enemy in bat_group) >= 360.0
        and min(enemy.hover_height for enemy in bat_group) <= 200.0
        and sum(1 for x in bat_xs if x >= 640.0) >= 4
        and max(bat_xs) - min(bat_xs) >= 240.0
        and bat_flight_remaining == [5.0, 6.0, 7.0, 8.0, 9.0]
        and bat_flight_bags_ok
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

    # The 5-Bat group must stagger the same skill; observe real AI starts.
    scene.enemy_count_override = None
    scene.set_enemy("warrior")
    scene.set_enemy("bat")
    scene.reset()
    scene.player.x = 280.0
    scene.player.y = scene.stage.ground_y
    scene.player.on_ground = True
    scene.player.invincible = True
    for enemy in scene.enemies:
        enemy.ai_enabled = True
    bat_seen = {}
    bat_starts = {"bat_sonic": [], "bat_dive": []}
    for _ in range(int(12.0 / FIXED_DT)):
        scene.tick(FIXED_DT)
        for enemy in scene.enemies:
            for attack_id in bat_starts:
                started = enemy.last_attack_at.get(attack_id)
                key = (id(enemy), attack_id)
                if started is not None and bat_seen.get(key) != started:
                    bat_seen[key] = started
                    bat_starts[attack_id].append(started)
    bat_sonic_gap = _min_start_gap(bat_starts["bat_sonic"])
    bat_dive_gap = _min_start_gap(bat_starts["bat_dive"])
    bat_group_gap_ok = (
        len(bat_starts["bat_sonic"]) >= 2
        and len(bat_starts["bat_dive"]) >= 2
        and bat_sonic_gap >= 1.2 - 2 * FIXED_DT
        and bat_dive_gap >= 0.8 - 2 * FIXED_DT
    )

    # Bat free-flight bag: 5 flights with 3 high / 2 low, randomized; a low
    # flight stays 2s at y=550 and must be hittable.
    scene.enemy_count_override = 1
    scene.set_character("lina")
    scene.set_enemy("warrior")
    scene.set_enemy("bat")
    scene.reset()
    flight_bat = scene.enemy
    flight_bat.ai_enabled = True
    scene.player.x = 280.0
    scene.player.y = scene.stage.ground_y
    scene.player.on_ground = True
    scene.player.invincible = True
    high_min_y = scene.stage.ground_y - flight_bat.flight_high_max
    high_max_y = scene.stage.ground_y - flight_bat.flight_high_min
    low_y = scene.stage.ground_y - flight_bat.flight_low_height
    flight_bag_ok = (
        (1 if flight_bat.flight_side == "high" else 0)
        + flight_bat.flight_bag.count("high") == 3
        and (1 if flight_bat.flight_side == "low" else 0)
        + flight_bat.flight_bag.count("low") == 2
    )
    low_stay_seen = False
    low_y_seen = False
    high_y_seen = False
    low_hit = False
    low_fight_done = False
    low_sonic_seen = False
    flight_xs = []
    last_sonic_at = flight_bat.last_attack_at.get("bat_sonic")
    for _ in range(int(32.0 / FIXED_DT)):
        scene.tick(FIXED_DT)
        flight_xs.append(flight_bat.x)
        side = flight_bat.flight_side
        sonic_at = flight_bat.last_attack_at.get("bat_sonic")
        if sonic_at is not None and sonic_at != last_sonic_at:
            last_sonic_at = sonic_at
            if side == "low":
                low_sonic_seen = True
        if side == "low":
            if flight_bat.low_stay_remaining > 1.5:
                low_stay_seen = True
            if abs(flight_bat.y - low_y) <= 30.0:
                low_y_seen = True
            if not low_fight_done and abs(flight_bat.y - low_y) <= 15.0:
                flight_bat.ai_enabled = False
                flight_bat.cancel_attack()
                scene.player.invincible = False
                scene.player.statuses.clear()
                scene.player.hp = scene.player.max_hp
                scene.player.state = FighterState.IDLE
                scene.player.hitstun = 0.0
                scene.player.on_ground = True
                scene.player.x = flight_bat.x - 80.0
                scene.player.y = scene.stage.ground_y
                scene.player.facing = 1
                scene.input.buffer.press("punch")
                for _ in range(30):
                    scene.tick(FIXED_DT)
                low_hit = (
                    abs((flight_bat.max_hp - flight_bat.hp) - 20.0) < 0.01
                )
                low_fight_done = True
                flight_bat.ai_enabled = True
                scene.player.invincible = True
        elif side == "high" and (
            high_min_y - 5.0
            <= flight_bat.y
            <= high_max_y + flight_bat.bob + 5.0
        ):
            high_y_seen = True
    bat_flight_cycle_ok = (
        flight_bag_ok
        and low_stay_seen
        and low_y_seen
        and high_y_seen
        and low_hit
        and not low_sonic_seen
        and max(flight_xs) - min(flight_xs) >= 80.0
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
    previous_character_ok = scene.character_id == "eira"
    rhea_switch_ai_off_ok = (
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
    f7_mech_crab_ok = scene.enemy_id == "mech_crab"
    scene.handle_debug_key(pygame.K_F7)
    f7_shadow_ninja_ok = scene.enemy_id == "shadow_ninja"
    scene.handle_debug_key(pygame.K_F7)
    f7_crooked_witch_ok = scene.enemy_id == "crooked_witch"
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
        and rhea_switch_ai_off_ok
        and b_preserved_ok
        and switch_clears_ok
        and f7_cycle_ok
        and f7_bat_ok
        and f7_creepy_ok
        and f7_mech_crab_ok
        and f7_shadow_ninja_ok
        and f7_crooked_witch_ok
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
    last_climb_y = None
    for _ in range(240):
        if player.climbing:
            last_climb_y = player.y
        scene.tick(FIXED_DT)
        if player.on_ground and abs(player.y - float(ladder.top_y)) < 0.5:
            ladder_climb_ok = True
            break
    scene.input.key_up(pygame.K_w)
    ladder_mount_early_ok = (
        last_climb_y is not None and 250.0 <= last_climb_y <= 258.0
    )

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

    # Jumping off a ladder while the body overlaps a platform must not make
    # the platform's side push the fighter away.
    scene.reset()
    player = scene.player
    scene.input.clear()
    player.x = float(ladder.rect.centerx)
    player.y = 300.0
    player.on_ground = False
    player.climbing = True
    player.climb_ladder = ladder
    player.state = FighterState.CLIMB
    if player.anim is not None:
        player.anim.set_clip("climb", reset=True)
    scene.input.key_down(pygame.K_SPACE)
    scene.tick(FIXED_DT)
    ladder_jump_started = (
        not player.climbing
        and player.vy < 0.0
        and player.ladder_fall
    )
    for _ in range(10):
        scene.tick(FIXED_DT)
    scene.input.key_up(pygame.K_SPACE)
    ladder_jump_overlap_ok = (
        ladder_jump_started
        and abs(player.x - float(ladder.rect.centerx)) < 5.0
        and player.y < 300.0
    )

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

    # Ladder hits knock the player off and clear the climb immediately. A
    # body whose feet are inside a platform rect is treated as grounded, and
    # the platform behind the ladder cannot shove the falling body sideways.
    _reset_creepy()
    ladder = scene.stage.ladders[0]
    _place_creepy(1000, 220)
    creepy.facing = -1
    creepy_player.x = float(ladder.rect.centerx)
    creepy_player.y = 400.0
    creepy_player.on_ground = False
    creepy_player.climbing = True
    creepy_player.climb_ladder = ladder
    creepy_player.state = FighterState.CLIMB
    if creepy_player.anim is not None:
        creepy_player.anim.set_clip("climb", reset=True)
    creepy_player.take_hit(30.0, 40.0, 0.15, -1)
    ladder_mid_climb_cleared = (
        not creepy_player.climbing
        and creepy_player.state == FighterState.HURT
        and creepy_player.anim is not None
        and creepy_player.anim.clip_name == "hurt"
    )
    for _ in range(20):
        scene.tick(FIXED_DT)
    creepy_ladder_hit_mid_ok = (
        ladder_mid_climb_cleared
        and not creepy_player.climbing
        and abs(creepy_player.x - float(ladder.rect.centerx)) < 20.0
        and creepy_player.y > 420.0
        and creepy_player.state in (FighterState.HURT, FighterState.AIR)
    )

    _reset_creepy()
    _place_creepy(1000, 220)
    creepy.facing = -1
    creepy_player.x = float(ladder.rect.centerx)
    creepy_player.y = 230.0
    creepy_player.on_ground = False
    creepy_player.climbing = True
    creepy_player.climb_ladder = ladder
    creepy_player.state = FighterState.CLIMB
    if creepy_player.anim is not None:
        creepy_player.anim.set_clip("climb", reset=True)
    creepy_player.take_hit(30.0, 40.0, 0.15, -1)
    ladder_platform_snap = (
        creepy_player.on_ground
        and abs(creepy_player.y - 220.0) < 0.5
        and not creepy_player.climbing
    )
    for _ in range(20):
        scene.tick(FIXED_DT)
    creepy_ladder_hit_platform_ok = (
        ladder_platform_snap
        and creepy_player.on_ground
        and abs(creepy_player.y - 220.0) < 0.5
        and not creepy_player.climbing
        and creepy_player.state == FighterState.IDLE
    )

    _reset_creepy()
    _place_creepy(1000, 220)
    creepy.facing = -1
    creepy_player.x = float(ladder.rect.centerx)
    creepy_player.y = 220.0
    creepy_player.on_ground = False
    creepy_player.climbing = True
    creepy_player.climb_ladder = ladder
    creepy_player.state = FighterState.CLIMB
    if creepy_player.anim is not None:
        creepy_player.anim.set_clip("climb", reset=True)
    creepy.force_attack(scene, creepy_player, "creepy_shot")
    ladder_top_hit = False
    for _ in range(60):
        scene.tick(FIXED_DT)
        if creepy_player.hp < creepy_player.max_hp:
            ladder_top_hit = True
            break
    for _ in range(20):
        scene.tick(FIXED_DT)
    creepy_ladder_hit_top_ok = (
        ladder_top_hit
        and abs(creepy_player.y - 220.0) < 0.5
        and creepy_player.on_ground
        and not creepy_player.climbing
        and creepy_player.state == FighterState.IDLE
    )
    creepy_ladder_hit_ok = (
        creepy_ladder_hit_mid_ok
        and creepy_ladder_hit_platform_ok
        and creepy_ladder_hit_top_ok
    )

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
        scene.stage.platforms[0].left == 400 and scene.enemy.name == "Warrior"
    )
    scene.reset()

    # --- Phase G: Mech-Crab ---
    scene.enemy_count_override = 1
    scene.set_character("lina")
    scene.set_enemy("mech_crab")
    scene.reset()
    mech = scene.enemy
    mech_player = scene.player
    mech.ai_enabled = False

    mech_crab_present = (
        mech.name == "Mech-Crab"
        and mech.max_hp == 400.0
        and mech.hp == 400.0
        and mech.basic_atk == 30.0
        and mech.atk == 30.0
        and mech.hurtbox_dims == (200.0, 230.0)
        and mech.stage_half_width == 85.0
        and mech.skill_slots
        == ["mech_laser", "mech_charge", "mech_claw_slam", "mech_leap_slam"]
        and mech.entry.get("separates") is True
        and mech.entry.get("decides_match") is True
    )
    mech_crab_stage_ok = (
        len(scene.stage.platforms) == 2
        and [tuple(rect) for rect in scene.stage.platforms]
        == [(170, 268, 479, 78), (796, 220, 314, 78)]
        and len(scene.stage.ladders) == 2
        and [tuple(ladder.rect) for ladder in scene.stage.ladders]
        == [(508, 268, 64, 352), (921, 220, 64, 400)]
        and len(scene.stage.blocks) == 2
        and not scene.stage.barriers
        and scene.stage.spawn("mech_crab_spawn") == (1000.0, 620.0)
    )

    def _place_mech(ex: float, px: float, py: float = 620.0):
        if scene.enemy_id != "mech_crab":
            scene.set_enemy("mech_crab")
        scene.reset()
        crab = scene.enemy
        crab.ai_enabled = False
        crab.x = float(ex)
        crab.y = 620.0
        crab.on_ground = True
        crab.vy = 0.0
        player = scene.player
        player.x = float(px)
        player.y = float(py)
        player.on_ground = True
        player.vy = 0.0
        player.hp = 100.0
        player.statuses.clear()
        return crab, player

    mech_crab_armor_ok = True
    for mech_attack in (
        "mech_laser", "mech_charge", "mech_claw_slam", "mech_leap_slam",
    ):
        crab, player = _place_mech(
            600.0, 700.0 if mech_attack == "mech_claw_slam" else 900.0
        )
        if not crab.force_attack(scene, player, mech_attack):
            mech_crab_armor_ok = False
            break
        for _ in range(5):
            scene.tick(FIXED_DT)
        before_hp = crab.hp
        crab.take_hit(10.0, 120.0, 0.25, 1)
        if not (
            crab.state == FighterState.ATTACK
            and abs(crab.hp - (before_hp - 10.0)) < 0.01
            and crab.hitstun == 0.0
            and crab.kb_vx == 0.0
            and crab.statuses.has("super_armor")
        ):
            mech_crab_armor_ok = False
            break
    crab, player = _place_mech(600.0, 900.0)
    crab.force_attack(scene, player, "mech_laser")
    for _ in range(70):
        scene.tick(FIXED_DT)
    armor_beam_seen = crab.laser_beam is not None
    crab.take_hit(9999.0, 0.0, 0.2, 1)
    mech_crab_armor_ok = (
        mech_crab_armor_ok
        and armor_beam_seen
        and crab.state == FighterState.KO
        and crab.attack_id is None
        and crab.laser_beam is None
    )

    crab, player = _place_mech(600.0, 900.0)
    laser_started = crab.force_attack(scene, player, "mech_laser")
    laser_cd_start = crab.laser_cd
    laser_start_x = crab.x
    laser_beam_seen = False
    laser_damage = 0.0
    laser_hits = 0
    last_hp = player.hp
    for _ in range(220):
        scene.tick(FIXED_DT)
        if crab.laser_beam is not None:
            laser_beam_seen = True
        if player.hp < last_hp:
            laser_hits += 1
            laser_damage += last_hp - player.hp
            last_hp = player.hp
        if crab.attack_id is None and _ > 10:
            break
    laser_ok = (
        laser_started
        and laser_beam_seen
        and abs(laser_cd_start - 6.0) < 1e-6
        and abs(crab.x - laser_start_x) < 0.01
        and laser_hits == 1
        and abs(laser_damage - 36.0) < 0.01
        and crab.laser_beam is None
    )
    crab, player = _place_mech(300.0, 900.0)
    crab.force_attack(scene, player, "mech_laser")
    for _ in range(62):
        scene.tick(FIXED_DT)
    blocked_beam = crab.laser_beam
    laser_block_ok = (
        blocked_beam is not None
        and blocked_beam.blocked
        and blocked_beam.end_y <= 346.5
    )
    mech_crab_laser_ok = laser_ok and laser_block_ok

    crab, player = _place_mech(600.0, 800.0)
    charge_started = crab.force_attack(scene, player, "mech_charge")
    charge_cd_start = crab.charge_cd
    charge_start_x = crab.x
    for _ in range(50):
        scene.tick(FIXED_DT)
    charge_warning_still = abs(crab.x - charge_start_x) < 0.01
    for _ in range(80):
        scene.tick(FIXED_DT)
    charge_damage = 100.0 - player.hp
    crab, player = _place_mech(600.0, 800.0)
    crab.force_attack(scene, player, "mech_charge")
    for _ in range(20):
        scene.tick(FIXED_DT)
    player.x = 300.0
    for _ in range(120):
        scene.tick(FIXED_DT)
    charge_lock_ok = crab.x > 800.0 and player.hp == 100.0
    crab, player = _place_mech(900.0, 1100.0, 220.0)
    crab.force_attack(scene, player, "mech_charge")
    for _ in range(160):
        scene.tick(FIXED_DT)
    charge_wall_ok = abs(crab.x - 1105.0) < 1.0 and player.hp == 100.0
    mech_crab_charge_ok = (
        charge_started
        and abs(charge_cd_start - 5.0) < 1e-6
        and charge_warning_still
        and abs(charge_damage - 45.0) < 0.01
        and charge_lock_ok
        and charge_wall_ok
    )

    crab, player = _place_mech(600.0, 700.0)
    claw_started = crab.force_attack(scene, player, "mech_claw_slam")
    claw_cd_start = crab.claw_cd
    for _ in range(25):
        scene.tick(FIXED_DT)
    claw_early_hp = player.hp
    for _ in range(20):
        scene.tick(FIXED_DT)
    claw_damage = 100.0 - player.hp
    claw_stun_effect = player.statuses.get("stun")
    claw_stun = claw_stun_effect is not None
    claw_stun_left = claw_stun_effect.remaining if claw_stun_effect else 0.0
    crab, player = _place_mech(600.0, 700.0)
    crab.force_attack(scene, player, "mech_claw_slam")
    for _ in range(10):
        scene.tick(FIXED_DT)
    player.x = 500.0
    for _ in range(60):
        scene.tick(FIXED_DT)
    claw_behind_ok = player.hp == 100.0
    mech_crab_claw_ok = (
        claw_started
        and abs(claw_cd_start - 5.0) < 1e-6
        and claw_early_hp == 100.0
        and abs(claw_damage - 30.0) < 0.01
        and claw_stun
        and 0.8 <= claw_stun_left <= 1.3
        and claw_behind_ok
    )

    crab, player = _place_mech(600.0, 900.0)
    leap_started = crab.force_attack(scene, player, "mech_leap_slam")
    leap_cd_start = crab.leap_cd
    leap_marker_x = crab.leap_target_x
    leap_marker_y = crab.leap_target_y
    for _ in range(20):
        scene.tick(FIXED_DT)
    player.x = 1100.0
    leap_marker_fixed = (
        crab.leap_target_x == leap_marker_x
        and crab.leap_target_y == leap_marker_y
    )
    for _ in range(140):
        scene.tick(FIXED_DT)
    leap_dodge_ok = player.hp == 100.0
    crab, player = _place_mech(600.0, 900.0)
    player.y = 220.0
    player.on_ground = True
    crab.force_attack(scene, player, "mech_leap_slam")
    for _ in range(150):
        scene.tick(FIXED_DT)
    leap_platform_ok = (
        abs(crab.y - 220.0) < 0.5 and abs(player.hp - 40.0) < 0.01
    )
    mech_crab_leap_ok = (
        leap_started
        and abs(leap_cd_start - 8.0) < 1e-6
        and leap_marker_fixed
        and leap_dodge_ok
        and leap_platform_ok
    )

    crab, player = _place_mech(600.0, 300.0)
    crab.force_attack(scene, player, "mech_claw_slam")
    for _ in range(70):
        scene.tick(FIXED_DT)
    gap_after = crab.skill_gap
    crab.ai_enabled = True
    crab.decision_cd = 0.0
    for _ in range(10):
        scene.tick(FIXED_DT)
    no_skill_in_gap = crab.attack_id is None
    for _ in range(60):
        scene.tick(FIXED_DT)
    skill_after_gap = crab.attack_id is not None
    mech_crab_gap_ok = (
        gap_after > 0.5 and no_skill_in_gap and skill_after_gap
    )

    mech_slot_results = []
    for mech_key, mech_attack in (
        (pygame.K_v, "mech_laser"),
        (pygame.K_c, "mech_charge"),
        (pygame.K_x, "mech_claw_slam"),
        (pygame.K_z, "mech_leap_slam"),
    ):
        crab, player = _place_mech(600.0, 800.0)
        scene.handle_debug_key(mech_key)
        mech_slot_results.append(crab.attack_id == mech_attack)
    mech_crab_slots_ok = all(mech_slot_results)

    crab, player = _place_mech(600.0, 900.0)
    crab.hp = 1.0
    crab.take_hit(5.0, 0.0, 0.1, 1)
    scene.tick(FIXED_DT)
    mech_crab_win_ok = scene.match_over == "WIN"

    crab, player = _place_mech(600.0, 900.0)
    crab.force_attack(scene, player, "mech_laser")
    for _ in range(70):
        scene.tick(FIXED_DT)
    cleanup_beam_before_reset = crab.laser_beam is not None
    scene.reset()
    crab = scene.enemy
    cleanup_reset_ok = (
        crab.laser_beam is None
        and crab.attack_id is None
        and crab.leap_target_x is None
    )
    crab.force_attack(scene, scene.player, "mech_laser")
    for _ in range(70):
        scene.tick(FIXED_DT)
    cleanup_beam_before_ko = crab.laser_beam is not None
    crab.take_hit(9999.0, 0.0, 0.2, 1)
    cleanup_ko_ok = crab.laser_beam is None and crab.attack_id is None
    scene.set_enemy("warrior")
    cleanup_switch_ok = not scene.projectiles and not scene.fx_effects
    mech_crab_cleanup_ok = (
        cleanup_beam_before_reset
        and cleanup_reset_ok
        and cleanup_beam_before_ko
        and cleanup_ko_ok
        and cleanup_switch_ok
    )

    mech_ai_checks = []
    crab, player = _place_mech(600.0, 700.0)
    crab.ai_enabled = True
    scene.tick(FIXED_DT)
    mech_ai_checks.append(crab.attack_id == "mech_claw_slam")
    crab, player = _place_mech(600.0, 850.0)
    crab.ai_enabled = True
    scene.tick(FIXED_DT)
    mech_ai_checks.append(crab.attack_id == "mech_charge")
    crab, player = _place_mech(600.0, 1150.0)
    crab.ai_enabled = True
    scene.tick(FIXED_DT)
    mech_ai_checks.append(crab.attack_id == "mech_laser")
    crab, player = _place_mech(600.0, 900.0)
    player.y = 220.0
    player.on_ground = True
    crab.ai_enabled = True
    scene.tick(FIXED_DT)
    mech_ai_checks.append(crab.attack_id == "mech_leap_slam")
    mech_crab_ai_ok = all(mech_ai_checks)

    scene.set_enemy("mech_crab")
    scene.reset()
    mech = scene.enemy
    mech_crab_missing = len(mech.anim.missing_paths())
    mech_crab_lock_dir = ASSETS_DIR / "frames" / "mech_crab" / "fx"
    mech_crab_fx_missing = sum(
        not (mech_crab_lock_dir / f"mech_crab_lock_{index:02d}.png").exists()
        for index in range(3)
    )

    # --- Phase H: Shadow Ninja (normal form) ---
    scene.enemy_count_override = 1
    scene.set_character("lina")
    scene.set_enemy("shadow_ninja")
    scene.reset()

    def _place_shadow(ex: float, px: float, py: float = 620.0):
        if scene.enemy_id != "shadow_ninja":
            scene.set_enemy("shadow_ninja")
        scene.reset()
        shadow = scene.enemy
        shadow.ai_enabled = False
        shadow.x = float(ex)
        shadow.y = 620.0
        shadow.on_ground = True
        shadow.vy = 0.0
        shadow.ignore_separation = False
        shadow.crouch_timer = 0.0
        target = scene.player
        target.x = float(px)
        target.y = float(py)
        target.on_ground = True
        target.vy = 0.0
        target.hp = target.max_hp
        target.statuses.clear()
        target.shadow_marks = 0
        target.shadow_mark_burst_time = 0.0
        return shadow, target

    shadow = scene.enemy
    shadow_player = scene.player
    shadow_ninja_present = (
        scene.enemy_id == "shadow_ninja"
        and getattr(shadow, "name", "") == "Shadow Ninja"
        and shadow.__class__.__name__ == "ShadowNinja"
        and len(scene.enemies) == 1
        and shadow.skill_slots
        == [
            "shadow_kunai_slash",
            "shadow_kunai_throw",
            "shadow_dash",
            "shadow_phantom_form",
        ]
    )
    shadow_ninja_stats_ok = (
        shadow.max_hp == shadow_player.max_hp
        and shadow.atk == shadow_player.atk
        and abs(shadow.walk_speed - shadow_player.walk_speed * 1.5) < 1e-6
    )
    for character_id in ("nyra", "rhea", "lina"):
        scene.set_character(character_id)
        scene.reset()
        shadow_check = scene.enemy
        shadow_ninja_stats_ok = shadow_ninja_stats_ok and (
            shadow_check.max_hp == scene.player.max_hp
            and shadow_check.atk == scene.player.atk
            and abs(shadow_check.walk_speed - scene.player.walk_speed * 1.5)
            < 1e-6
        )

    # Slot 4 now triggers the phantom transform; reset before the skill tests.
    shadow, shadow_player = _place_shadow(450.0, 400.0)
    shadow.facing = -1
    shadow_ninja_slots_ok = (
        shadow.force_skill(scene, shadow_player, 3)
        and shadow.phantom_form
        and shadow.state == FighterState.TRANSFORM
    )
    shadow, shadow_player = _place_shadow(450.0, 400.0)
    shadow.facing = -1
    hp_before = shadow_player.hp
    shadow.force_skill(scene, shadow_player, 0)
    slash_cd_set = abs(shadow.slash_cd - shadow.slash_cd_max) < 1e-6
    for _ in range(40):
        scene.tick(FIXED_DT)
    shadow_ninja_slash_ok = (
        slash_cd_set
        and abs((hp_before - shadow_player.hp) - shadow.atk) < 0.01
        and shadow_player.shadow_marks == 1
        and shadow.slash_cd <= 0.0
        and shadow.attack_id is None
    )

    shadow, shadow_player = _place_shadow(400.0, 450.0)
    shadow.facing = 1
    shadow_player.facing = -1
    slash_rect = local_box_to_rect(shadow, [20, -195, 130, 55])
    shadow_player.state = FighterState.IDLE
    slash_standing = slash_rect.colliderect(shadow_player.hurtbox())
    shadow_player.state = FighterState.CROUCH
    slash_crouch_miss = not slash_rect.colliderect(shadow_player.hurtbox())
    shadow_player.state = FighterState.IDLE
    shadow_ninja_crouch_ok = slash_standing and slash_crouch_miss

    # Skill 2: low lane, 1.2 atk, 1s stun, one mark, blocked by a barrier.
    shadow, shadow_player = _place_shadow(400.0, 900.0)
    shadow.force_skill(scene, shadow_player, 1)
    throw_cd_set = abs(shadow.throw_cd - shadow.throw_cd_max) < 1e-6
    throw_low_lane = False
    for _ in range(20):
        scene.tick(FIXED_DT)
        if scene.projectiles:
            kunai = scene.projectiles[0]
            throw_low_lane = (
                getattr(kunai, "kind", "") == "shadow_kunai"
                and abs(kunai.y - (shadow.y - 60.0)) < 0.01
            )
    hp_before = shadow_player.hp
    for _ in range(40):
        scene.tick(FIXED_DT)
    shadow_ninja_throw_ok = (
        throw_cd_set
        and throw_low_lane
        and abs((hp_before - shadow_player.hp) - shadow.atk * 1.2) < 0.01
        and shadow_player.statuses.has("stun")
        and shadow_player.shadow_marks == 1
    )

    shadow, shadow_player = _place_shadow(400.0, 900.0)
    saved_blocks = scene.stage.blocks
    saved_barriers = scene.stage.barriers
    test_barrier = pygame.Rect(600, 560, 90, 60)
    scene.stage.blocks = [test_barrier]
    scene.stage.barriers = [test_barrier]
    shadow.force_skill(scene, shadow_player, 1)
    for _ in range(60):
        scene.tick(FIXED_DT)
    throw_blocked_ok = (
        shadow_player.hp == shadow_player.max_hp
        and shadow_player.shadow_marks == 0
        and not scene.projectiles
    )
    scene.stage.blocks = saved_blocks
    scene.stage.barriers = saved_barriers

    # Skill 3: dash ~630-640px, pass through the player, low hitbox.
    shadow, shadow_player = _place_shadow(400.0, 800.0)
    shadow.facing = 1
    dash_start_x = shadow.x
    shadow.force_skill(scene, shadow_player, 2)
    dash_cd_set = abs(shadow.dash_cd - shadow.dash_cd_max) < 1e-6
    for _ in range(40):
        scene.tick(FIXED_DT)
    shadow_ninja_dash_ok = (
        dash_cd_set
        and 600.0 <= shadow.x - dash_start_x <= 680.0
        and abs((shadow_player.max_hp - shadow_player.hp) - shadow.atk * 1.5)
        < 0.01
        and shadow_player.shadow_marks == 1
        and not shadow.ignore_separation
        and shadow.attack_id is None
    )

    shadow, shadow_player = _place_shadow(400.0, 450.0)
    shadow.facing = 1
    shadow_player.facing = -1
    dash_rect = local_box_to_rect(shadow, [0, -80, 90, 80])
    shadow_player.state = FighterState.IDLE
    dash_standing = dash_rect.colliderect(shadow_player.hurtbox())
    shadow_player.y = 620.0 - 131.0
    shadow_player.on_ground = False
    shadow_player.state = FighterState.AIR
    dash_jump_miss = not dash_rect.colliderect(shadow_player.hurtbox())
    shadow_player.y = 620.0
    shadow_player.on_ground = True
    shadow_player.state = FighterState.IDLE
    shadow_ninja_dash_jump_dodge_ok = dash_standing and dash_jump_miss

    # Marks: 1 -> 2 -> 3 -> burst -> 1, extra atk, stun, KO/reset clear.
    shadow, shadow_player = _place_shadow(450.0, 400.0)
    mark_counts = []
    for _ in range(4):
        shadow._add_shadow_mark(scene, shadow_player)
        mark_counts.append(shadow_player.shadow_marks)
    mark_cycle_ok = mark_counts == [1, 2, 3, 1]
    mark_damage_ok = abs((shadow_player.max_hp - shadow_player.hp) - shadow.atk) < 0.01
    mark_stun_ok = shadow_player.statuses.has("stun")
    mark_burst_ok = shadow_player.shadow_mark_burst_time > 0.0
    shadow_player.shadow_marks = 2
    shadow_player.take_hit(9999.0, 0.0, 0.0, 1)
    mark_ko_clear = shadow_player.shadow_marks == 0
    scene.reset()
    mark_reset_clear = shadow_player.shadow_marks == 0

    shadow, shadow_player = _place_shadow(450.0, 400.0)
    shadow_player.statuses.add("super_armor", 2.0)
    hp_before = shadow_player.hp
    for _ in range(4):
        shadow._add_shadow_mark(scene, shadow_player)
    mark_armor_damage = abs((hp_before - shadow_player.hp) - shadow.atk) < 0.01
    mark_armor_stun = not shadow_player.statuses.has("stun")
    shadow_ninja_marks_ok = (
        mark_cycle_ok
        and mark_damage_ok
        and mark_stun_ok
        and mark_burst_ok
        and mark_ko_clear
        and mark_reset_clear
        and mark_armor_damage
        and mark_armor_stun
    )

    scene.set_character("nyra")
    scene.reset()
    scene.player.marks = 2
    scene.player.shadow_marks = 3
    shadow_marks_independent = (
        scene.player.marks == 2 and scene.player.shadow_marks == 3
    )
    scene.set_character("lina")
    scene.reset()

    # AI: close 2 -> 1, low HP 3 away, far 2 -> 3, very far walk, defense.
    shadow, shadow_player = _place_shadow(450.0, 600.0)
    shadow.opening_cd = 0.0
    shadow.throw_cd = 0.0
    shadow.decision_cd = 0.0
    shadow.skill_gap = 0.0
    shadow._think(scene, shadow_player)
    ai_close_throw = shadow.attack_id == "shadow_kunai_throw"

    shadow, shadow_player = _place_shadow(450.0, 600.0)
    shadow.opening_cd = 0.0
    shadow.throw_cd = 5.0
    shadow.slash_cd = 0.0
    shadow.decision_cd = 0.0
    shadow.skill_gap = 0.0
    shadow._think(scene, shadow_player)
    ai_close_slash = shadow.attack_id == "shadow_kunai_slash"

    shadow, shadow_player = _place_shadow(450.0, 600.0)
    shadow.hp = shadow.max_hp * 0.3
    # Keep skill 4 on cooldown so this test still covers the normal-form
    # disengage dash instead of the phantom transform.
    shadow.transform_cd = shadow.transform_cd_max
    shadow.opening_cd = 0.0
    shadow.throw_cd = 5.0
    shadow.dash_cd = 0.0
    shadow.decision_cd = 0.0
    shadow.skill_gap = 0.0
    shadow._think(scene, shadow_player)
    ai_low_hp_dash = shadow.attack_id == "shadow_dash" and shadow.facing == -1

    shadow, shadow_player = _place_shadow(400.0, 800.0)
    shadow.opening_cd = 0.0
    shadow.throw_cd = 0.0
    shadow.decision_cd = 0.0
    shadow.skill_gap = 0.0
    shadow._think(scene, shadow_player)
    ai_far_throw = shadow.attack_id == "shadow_kunai_throw"

    shadow, shadow_player = _place_shadow(400.0, 800.0)
    scene.projectiles = []
    shadow.opening_cd = 0.0
    shadow.throw_cd = 5.0
    shadow.dash_cd = 0.0
    shadow.decision_cd = 0.0
    shadow.skill_gap = 0.0
    shadow._think(scene, shadow_player)
    ai_far_dash = shadow.attack_id == "shadow_dash"

    shadow, shadow_player = _place_shadow(300.0, 1000.0)
    shadow.opening_cd = 0.0
    shadow.throw_cd = 0.0
    shadow.dash_cd = 0.0
    shadow.decision_cd = 0.0
    shadow.skill_gap = 0.0
    shadow._think(scene, shadow_player)
    ai_very_far_walk = (
        shadow.attack_id is None and shadow.state == FighterState.WALK
    )

    shadow, shadow_player = _place_shadow(450.0, 700.0)
    shadow_player.facing = -1
    shadow_player.attack_runtime = AttackRuntime(
        shadow_player,
        "test_high",
        {
            "duration": 1.0,
            "events": [
                {
                    "t": 0.0,
                    "until": 1.0,
                    "type": "hitbox",
                    "box": [20, -195, 130, 55],
                }
            ],
        },
        shadow,
        scene,
    )
    shadow.opening_cd = 0.0
    shadow.decision_cd = 0.0
    shadow._think(scene, shadow_player)
    ai_crouch = shadow.state == FighterState.CROUCH
    shadow_player.attack_runtime = AttackRuntime(
        shadow_player,
        "test_low",
        {
            "duration": 1.0,
            "events": [
                {
                    "t": 0.0,
                    "until": 1.0,
                    "type": "hitbox",
                    "box": [0, -80, 90, 80],
                }
            ],
        },
        shadow,
        scene,
    )
    shadow.state = FighterState.IDLE
    shadow.on_ground = True
    shadow.y = 620.0
    shadow.jump_cd = 0.0
    shadow.decision_cd = 0.0
    shadow._think(scene, shadow_player)
    ai_jump = shadow.state == FighterState.AIR and shadow.vy < 0.0
    shadow_player.attack_runtime = None

    shadow_ninja_ai_ok = all(
        (
            ai_close_throw,
            ai_close_slash,
            ai_low_hp_dash,
            ai_far_throw,
            ai_far_dash,
            ai_very_far_walk,
            ai_crouch,
            ai_jump,
        )
    )

    # Barrier hop: a temporary barrier is enough to verify the future-stage AI.
    shadow, shadow_player = _place_shadow(420.0, 700.0)
    shadow.facing = 1
    hop_barrier = pygame.Rect(500, 560, 90, 60)
    saved_blocks = scene.stage.blocks
    saved_barriers = scene.stage.barriers
    scene.stage.blocks = [hop_barrier]
    scene.stage.barriers = [hop_barrier]
    hop_started = shadow._try_barrier_hop(scene, shadow_player)
    for _ in range(60):
        shadow.update(FIXED_DT, scene)
    shadow_ninja_barrier_hop_ok = (
        hop_started and abs(shadow.y - 560.0) < 1.0 and shadow.on_ground
    )
    scene.stage.blocks = saved_blocks
    scene.stage.barriers = saved_barriers

    # Win / cleanup / slot 4 safety.
    shadow, shadow_player = _place_shadow(450.0, 400.0)
    shadow.hp = 1.0
    shadow_player.facing = 1
    scene.input.buffer.press("punch")
    for _ in range(40):
        scene.tick(FIXED_DT)
    shadow_ninja_win_ok = scene.match_over == "WIN"
    scene.reset()
    shadow_ninja_cleanup_ok = (
        scene.enemy.hp == scene.enemy.max_hp
        and scene.player.shadow_marks == 0
        and not scene.projectiles
        and not scene.player.statuses.has("stun")
    )
    shadow, shadow_player = _place_shadow(400.0, 900.0)
    shadow.force_skill(scene, shadow_player, 1)
    for _ in range(20):
        scene.tick(FIXED_DT)
    had_kunai = bool(scene.projectiles)
    scene.set_enemy("warrior")
    shadow_ninja_cleanup_ok = (
        shadow_ninja_cleanup_ok and had_kunai and not scene.projectiles
    )

    scene.set_enemy("shadow_ninja")
    scene.reset()
    shadow = scene.enemy
    shadow_ninja_missing_frames = len(shadow.anim.missing_paths())
    shadow_fx_dir = ASSETS_DIR / "frames" / "shadow_ninja" / "fx"
    shadow_ninja_fx_missing = sum(
        not (shadow_fx_dir / f"shadow_kunai_{index:02d}.png").exists()
        for index in range(2)
    )

    # Enemy-specific stage variants: Warrior symmetric, Bat/Veno empty,
    # Dummy on the default stage.
    scene.enemy_count_override = None
    scene.set_enemy("creepy_shooter")
    scene.reset()
    scene.set_enemy("warrior")
    scene.reset()
    warrior_stage = scene.stage
    warrior_stage_ok = (
        len(warrior_stage.platforms) == 1
        and tuple(warrior_stage.platforms[0]) == (400, 220, 479, 78)
        and len(warrior_stage.ladders) == 1
        and tuple(warrior_stage.ladders[0].rect) == (608, 220, 64, 400)
        and [tuple(rect) for rect in warrior_stage.barriers]
        == [(400, 560, 90, 60), (790, 560, 90, 60)]
        and abs(warrior_stage.platforms[0].centerx - 640) <= 1
        and warrior_stage.ladders[0].rect.centerx == 640
        and (
            warrior_stage.barriers[0].centerx
            + warrior_stage.barriers[1].centerx
        )
        == 1280
    )

    scene.set_enemy("bat")
    scene.reset()
    bat_stage_ok = (
        not scene.stage.blocks
        and not scene.stage.ladders
        and len(scene.enemies) == 5
        and all(not enemy.on_ground for enemy in scene.enemies)
    )

    scene.set_enemy("veno")
    scene.reset()
    veno_stage_ok = (
        not scene.stage.blocks
        and not scene.stage.ladders
        and len(scene.enemies) == 3
        and any(not enemy.on_ground for enemy in scene.enemies)
        and any(enemy.on_ground for enemy in scene.enemies)
    )

    scene.stage.set_blocks_enabled(False)
    scene.set_enemy("dummy")
    dummy_blocks_preserved = not scene.stage.blocks_enabled
    dummy_stage = scene.stage
    scene.stage.set_blocks_enabled(True)
    scene.set_enemy("mech_crab")
    scene.reset()
    mech_stage = scene.stage
    mech_variant_ok = (
        len(mech_stage.platforms) == 2
        and [tuple(rect) for rect in mech_stage.platforms]
        == [(170, 268, 479, 78), (796, 220, 314, 78)]
        and len(mech_stage.ladders) == 2
        and [tuple(ladder.rect) for ladder in mech_stage.ladders]
        == [(508, 268, 64, 352), (921, 220, 64, 400)]
        and len(mech_stage.blocks) == 2
        and not mech_stage.barriers
        and mech_stage.spawn("mech_crab_spawn") == (1000.0, 620.0)
    )
    scene.set_enemy("shadow_ninja")
    scene.reset()
    shadow_stage = scene.stage
    shadow_variant_ok = (
        not shadow_stage.blocks
        and not shadow_stage.ladders
        and shadow_stage.spawn("shadow_ninja_spawn") == (1000.0, 620.0)
    )
    scene_variant_switch_ok = (
        dummy_blocks_preserved
        and len(dummy_stage.platforms) == 2
        and len(dummy_stage.ladders) == 2
        and len(dummy_stage.blocks) == 4
        and mech_variant_ok
        and shadow_variant_ok
    )
    scene.reset()

    # --- Phase I: Shadow Ninja phantom form (skill 4) ---
    scene.enemy_count_override = 1
    scene.set_character("lina")
    scene.set_enemy("shadow_ninja")
    scene.reset()

    def _place_phantom(ex: float, px: float, py: float = 620.0):
        shadow, target = _place_shadow(ex, px, py)
        shadow.ai_enabled = False
        return shadow, target

    def _run_phantom_ticks(count: int) -> None:
        for _ in range(count):
            scene.tick(FIXED_DT)

    def _to_phantom(shadow, target):
        shadow.transform_cd = 0.0
        started = shadow.start_transform(scene)
        _run_phantom_ticks(100)
        return started

    shadow, shadow_player = _place_phantom(450.0, 400.0)
    shadow_ninja_phantom_present = (
        shadow.skill_slots[3] == "shadow_phantom_form"
        and "shadow_ninja_phantom_clips" in scene.store.animations
        and all(
            key in scene.store.attacks
            for key in (
                "shadow_phantom_form",
                "shadow_phantom_rend",
                "shadow_phantom_bind",
                "shadow_phantom_flash",
            )
        )
    )

    # Transform: frame 0 invincibility, self-clear, player marks survive.
    shadow, shadow_player = _place_phantom(450.0, 400.0)
    shadow_player.facing = 1
    shadow.facing = -1
    shadow.marks = 2
    shadow.shadow_marks = 3
    shadow.hitstun = 0.3
    shadow.statuses.add("poison", 1.0, dps=2.0)
    shadow_player.shadow_marks = 2
    hp_before = shadow.hp
    transform_started = shadow.start_transform(scene)
    phantom_frame0_ok = (
        shadow.invincible
        and shadow.phantom_form
        and shadow.phantom_phase == "transform"
        and shadow.marks == 0
        and shadow.shadow_marks == 0
        and shadow.hitstun == 0.0
        and not shadow.statuses.has("poison")
    )
    phantom_no_damage = not shadow.take_hit(999.0, 0.0, 0.0, 1)
    _run_phantom_ticks(100)
    shadow_ninja_phantom_transform_ok = (
        transform_started
        and phantom_frame0_ok
        and phantom_no_damage
        and shadow.hp == hp_before
        and shadow.phantom_phase == "phantom"
        and shadow.anim.variant == "flame"
        and shadow.anim.clip_name == "idle"
        and shadow.invincible
        and shadow_player.shadow_marks == 2
    )
    shadow_ninja_phantom_invincible_ok = (
        shadow.invincible
        and not shadow.take_hit(999.0, 0.0, 0.0, 1)
        and shadow.hp == hp_before
    )
    shadow.statuses.add("stun", 0.5)
    shadow.statuses.add("poison", 1.0, dps=2.0)
    _run_phantom_ticks(10)
    shadow_ninja_phantom_clear_ok = (
        phantom_frame0_ok
        and not shadow.statuses.has("stun")
        and not shadow.statuses.has("poison")
    )
    shadow_ninja_phantom_marks_separate_ok = shadow_player.shadow_marks == 2

    # No combat hitbox: player attacks and projectiles pass through.
    shadow, shadow_player = _place_phantom(600.0, 400.0)
    _to_phantom(shadow, shadow_player)
    shadow_player.facing = 1
    phantom_not_targeted = shadow not in scene.targets_for(shadow_player)
    scene.projectiles = []
    phantom_probe_attack = {
        "duration": 1.0,
        "basic_mult": 1.0,
        "events": [
            {
                "type": "projectile",
                "projectile": "q_wave",
                "lane": "mid",
                "speed": 700,
                "range": 900,
            }
        ],
    }
    scene.spawn_projectile_from_event(
        shadow_player, phantom_probe_attack, phantom_probe_attack["events"][0]
    )
    phantom_probe = scene.projectiles[-1]
    phantom_hp_before = shadow.hp
    _run_phantom_ticks(30)
    shadow_ninja_phantom_no_hitbox_ok = (
        phantom_not_targeted
        and phantom_probe.alive
        and shadow.hp == phantom_hp_before
    )

    # P1 影爪: high hitbox, crouch dodge, 1.0 atk, no marks, one use.
    shadow, shadow_player = _place_phantom(450.0, 400.0)
    _to_phantom(shadow, shadow_player)
    rend_rect = local_box_to_rect(shadow, [20, -195, 240, 55])
    shadow_player.state = FighterState.IDLE
    rend_standing = rend_rect.colliderect(shadow_player.hurtbox())
    shadow_player.state = FighterState.CROUCH
    rend_crouch_miss = not rend_rect.colliderect(shadow_player.hurtbox())
    shadow_player.state = FighterState.IDLE
    hp_before = shadow_player.hp
    marks_before = shadow_player.shadow_marks
    rend_started = shadow.force_skill(scene, shadow_player, 0)
    _run_phantom_ticks(45)
    shadow_ninja_phantom_rend_ok = (
        rend_started
        and rend_standing
        and rend_crouch_miss
        and abs((hp_before - shadow_player.hp) - shadow.atk) < 0.01
        and shadow_player.shadow_marks == marks_before
        and shadow.skill_used("shadow_phantom_rend")
        and not shadow.force_skill(scene, shadow_player, 0)
    )

    # P2 影缚: low lane, 1.2 atk + 1s stun, pierces barriers, jump dodge.
    shadow, shadow_player = _place_phantom(400.0, 900.0)
    _to_phantom(shadow, shadow_player)
    saved_blocks = scene.stage.blocks
    saved_barriers = scene.stage.barriers
    phantom_barrier = pygame.Rect(600, 560, 90, 60)
    scene.stage.blocks = [phantom_barrier]
    scene.stage.barriers = [phantom_barrier]
    hp_before = shadow_player.hp
    bind_started = shadow.force_skill(scene, shadow_player, 1)
    _run_phantom_ticks(90)
    bind_damage = hp_before - shadow_player.hp
    bind_stun = shadow_player.statuses.has("stun")
    scene.stage.blocks = saved_blocks
    scene.stage.barriers = saved_barriers
    from game.projectile import ShadowBindProjectile

    bind_probe = ShadowBindProjectile(
        owner=shadow,
        target=shadow_player,
        x=900.0,
        y=560.0,
        direction=1,
        speed=900.0,
        max_range=700.0,
        damage=0.0,
        knockback=0.0,
        hitstun=0.0,
        hitstop=0.0,
        radius=20.0,
    )
    shadow_player.state = FighterState.AIR
    shadow_player.on_ground = False
    shadow_player.y = 489.0
    bind_jump_miss = not bind_probe.rect.colliderect(shadow_player.hurtbox())
    shadow_player.state = FighterState.CROUCH
    shadow_player.y = 620.0
    bind_crouch_hit = bind_probe.rect.colliderect(shadow_player.hurtbox())
    shadow_player.state = FighterState.IDLE
    shadow_player.on_ground = True
    shadow_ninja_phantom_bind_ok = (
        bind_started
        and abs(bind_damage - shadow.atk * 1.2) < 0.01
        and bind_stun
        and bind_jump_miss
        and bind_crouch_hit
        and shadow.skill_used("shadow_phantom_bind")
    )

    # P3 影闪: all phases, one-damage hand/bolt, shark low, crouch/jump mix.
    shadow, shadow_player = _place_phantom(400.0, 900.0)
    _to_phantom(shadow, shadow_player)
    shadow_player.facing = -1
    hp_before = shadow_player.hp
    flash_started = shadow.force_skill(scene, shadow_player, 2)
    flash_phases: set[str] = set()
    for _ in range(65):
        _run_phantom_ticks(1)
        if shadow.phantom_flash_phase:
            flash_phases.add(shadow.phantom_flash_phase)
    flash_first_damage = hp_before - shadow_player.hp
    for _ in range(105):
        _run_phantom_ticks(1)
        if shadow.phantom_flash_phase:
            flash_phases.add(shadow.phantom_flash_phase)
    flash_total_damage = hp_before - shadow_player.hp
    shadow.x = 800.0
    shadow.y = 620.0
    shadow.facing = 1
    hand_box = local_box_to_rect(shadow, [20, -195, 90, 55])
    shark_box = local_box_to_rect(shadow, [-20, -85, 220, 85])
    shadow_player.state = FighterState.CROUCH
    flash_hand_crouch_miss = not hand_box.colliderect(shadow_player.hurtbox())
    shadow_player.state = FighterState.AIR
    shadow_player.on_ground = False
    shadow_player.y = 489.0
    flash_shark_jump_miss = not shark_box.colliderect(shadow_player.hurtbox())
    shadow_player.state = FighterState.IDLE
    shadow_player.on_ground = True
    shadow_player.y = 620.0
    shadow_ninja_phantom_flash_ok = (
        flash_started
        and {
            "vanish",
            "appear",
            "attack",
            "flight",
            "appear_far",
            "pause",
            "emerge",
            "charge",
            "recover",
        }.issubset(flash_phases)
        and abs(flash_first_damage - shadow.atk * 0.8) < 0.01
        and flash_total_damage <= shadow.atk * 1.6 + 0.01
        and flash_hand_crouch_miss
        and flash_shark_jump_miss
        and shadow.skill_used("shadow_phantom_flash")
    )

    # One use per skill, auto revert, cooldown starts after revert.
    shadow, shadow_player = _place_phantom(450.0, 400.0)
    _to_phantom(shadow, shadow_player)
    rend_once = shadow.force_skill(scene, shadow_player, 0)
    _run_phantom_ticks(35)
    rend_again_denied = not shadow.force_skill(scene, shadow_player, 0)
    bind_once = shadow.force_skill(scene, shadow_player, 1)
    _run_phantom_ticks(35)
    flash_once = shadow.force_skill(scene, shadow_player, 2)
    _run_phantom_ticks(160)
    phantom_auto_revert_started = (
        shadow.phantom_phase == "revert"
        and all(
            shadow.phantom_used.get(key, False)
            for key in shadow._PHANTOM_SKILL_IDS
        )
        and shadow.transform_cd == 0.0
    )
    _run_phantom_ticks(40)
    phantom_revert_ok = (
        shadow.phantom_phase == "normal"
        and not shadow.phantom_form
        and not shadow.invincible
        and not shadow.ignore_terrain
        and shadow.anim.variant == "normal"
        and 0.0 < shadow.transform_cd <= shadow.transform_cd_max
    )
    shadow_ninja_phantom_once_ok = (
        rend_once and rend_again_denied and bind_once and flash_once
    )
    shadow_ninja_phantom_auto_revert_ok = (
        phantom_auto_revert_started and phantom_revert_ok
    )
    shadow_ninja_phantom_cd_ok = (
        phantom_auto_revert_started and phantom_revert_ok
    )

    # AI: low HP / incoming big hit trigger, then P2 -> P3 order.
    shadow, shadow_player = _place_phantom(450.0, 600.0)
    shadow.opening_cd = 0.0
    shadow.decision_cd = 0.0
    shadow.skill_gap = 0.0
    shadow.hp = shadow.max_hp * 0.3
    shadow._think(scene, shadow_player)
    ai_phantom_low_hp = shadow.phantom_form and shadow.state == FighterState.TRANSFORM
    _run_phantom_ticks(100)
    shadow.decision_cd = 0.0
    shadow.skill_gap = 0.0
    shadow._think_phantom(scene, shadow_player)
    ai_phantom_bind = shadow.attack_id == "shadow_phantom_bind"
    _run_phantom_ticks(40)
    shadow.decision_cd = 0.0
    shadow.skill_gap = 0.0
    shadow.phantom_used["shadow_phantom_bind"] = True
    shadow_player.x = 900.0
    shadow_player.facing = 1
    shadow._think_phantom(scene, shadow_player)
    ai_phantom_flash = shadow.attack_id == "shadow_phantom_flash"

    shadow, shadow_player = _place_phantom(450.0, 600.0)
    shadow.opening_cd = 0.0
    shadow.decision_cd = 0.0
    shadow.skill_gap = 0.0
    shadow_player.facing = -1
    shadow_player.attack_runtime = AttackRuntime(
        shadow_player,
        "test_phantom_big_hit",
        {
            "duration": 1.0,
            "events": [
                {
                    "t": 0.0,
                    "until": 1.0,
                    "type": "hitbox",
                    "box": [20, -195, 130, 55],
                    "damage": 30.0,
                }
            ],
        },
        shadow,
        scene,
    )
    shadow._think(scene, shadow_player)
    ai_phantom_incoming = shadow.phantom_form
    shadow_player.attack_runtime = None
    shadow_ninja_phantom_ai_ok = (
        ai_phantom_low_hp
        and ai_phantom_incoming
        and ai_phantom_bind
        and ai_phantom_flash
    )

    # Reset leaves no phantom state or projectiles behind.
    shadow, shadow_player = _place_phantom(450.0, 400.0)
    _to_phantom(shadow, shadow_player)
    scene.reset()
    shadow = scene.enemy
    shadow_ninja_phantom_reset_ok = (
        not shadow.phantom_form
        and shadow.phantom_phase == "normal"
        and not shadow.invincible
        and not shadow.ignore_terrain
        and shadow.transform_cd == 0.0
        and shadow.anim.variant == "normal"
        and not scene.projectiles
    )

    shadow_ninja_phantom_missing_frames = 0
    for phantom_clip in shadow.anim.flame_clips.values():
        for rel in phantom_clip.get("frames", []):
            if not (ASSETS_DIR / "frames" / "shadow_ninja" / rel).exists():
                shadow_ninja_phantom_missing_frames += 1
    phantom_fx_dir = ASSETS_DIR / "frames" / "shadow_ninja" / "phantom" / "fx"
    shadow_ninja_phantom_fx_missing = 0
    for prefix, count in (
        ("phantom_rend_trail", 3),
        ("phantom_bind_tentacle", 4),
        ("phantom_bind_front", 6),
        ("phantom_bind_back", 6),
        ("phantom_flash_orb", 3),
        ("phantom_shark", 3),
    ):
        for index in range(count):
            if not (phantom_fx_dir / f"{prefix}_{index:02d}.png").exists():
                shadow_ninja_phantom_fx_missing += 1
    scene.reset()

    # --- Phase J: Crooked Witch (F7 enemy) ---
    scene.enemy_count_override = 1
    scene.set_character("lina")
    scene.set_enemy("crooked_witch")
    scene.reset()
    witch = scene.enemy
    witch_player = scene.player

    def _place_witch(
        wx: float = 900.0,
        wy: float = 620.0,
        px: float = 300.0,
        py: float = 620.0,
    ) -> None:
        for fighter, x, y, facing in (
            (witch, wx, wy, 1 if px >= wx else -1),
            (witch_player, px, py, 1 if wx >= px else -1),
        ):
            fighter.x = float(x)
            fighter.y = float(y)
            fighter.facing = facing
            fighter.vx = 0.0
            fighter.vy = 0.0
            fighter.kb_vx = 0.0
            fighter.kb_time = 0.0
            fighter.hitstun = 0.0
            fighter.hp = fighter.max_hp
            fighter.state = FighterState.IDLE
            fighter.on_ground = True
            fighter.invincible = False
            fighter.statuses.clear()
        witch.phase = "normal"
        witch.phase_time = 0.0
        witch.teleport_cd = 0.0
        witch.damage_timer = 0.0
        witch.teleport_pending = False
        witch.heal_used = False
        witch.heal_pending = False
        witch.attack_runtime = None
        witch.attack_id = None
        witch.no_hitbox = False
        witch.hidden = False
        witch.invincible = False
        witch.ignore_separation = False
        witch.ai_enabled = False
        scene.hazards = []
        scene.projectiles = []
        scene.hitstop = 0.0
        scene.match_over = None
        scene.sim_time = 0.0

    def _witch_ticks(count: int) -> None:
        for _ in range(count):
            scene.tick(FIXED_DT)

    crooked_witch_present = (
        witch.name == "Crooked Witch"
        and witch.max_hp == 400.0
        and witch.basic_atk == 30.0
        and witch.atk == 30.0
        and witch.hurtbox_dims == (56.0, 210.0)
        and witch.skill_slots
        == ["witch_lightning", "witch_ice_spike", "witch_potion", "witch_fire_rain"]
        and scene.enemy_spec.get("stage_variant") == "crooked_witch"
        and len(scene.stage.platforms) == 2
        and len(scene.stage.ladders) == 2
        and len(scene.stage.barriers) == 0
        and scene.stage.spawn("crooked_witch_spawn") == (965.0, 220.0)
        and len(scene.stage.teleport_points) == 4
    )
    crooked_witch_stats_ok = (
        abs(witch.walk_speed - 150.0) < 1e-6
        and abs(witch.lightning_cd_max - 2.0) < 1e-6
        and abs(witch.ice_cd_max - 5.0) < 1e-6
        and abs(witch.potion_cd_max - 8.0) < 1e-6
        and abs(witch.fire_cd_max - 15.0) < 1e-6
        and not hasattr(witch, "energy")
        and len(scene.store.animations["crooked_witch_clips"]) == 17
    )

    _place_witch(900.0, 620.0, 300.0, 620.0)
    points = list(scene.stage.teleport_points)
    nearest_index = min(
        range(len(points)),
        key=lambda index: (points[index][0] - witch.x) ** 2
        + (points[index][1] - witch.y) ** 2,
    )
    teleport_choice = witch._pick_teleport_point(scene)
    teleport_excludes_nearest = (
        teleport_choice is not None
        and teleport_choice != points[nearest_index]
        and teleport_choice != (witch.x, witch.y)
    )
    witch.take_hit(5.0, 0.0, 0.2, -1)
    _witch_ticks(2)
    teleport_started = witch.phase in ("teleport_out", "teleport_in")
    teleport_flags = (
        witch.invincible and witch.no_hitbox and witch.hidden
    )
    _witch_ticks(40)
    teleport_finished = (
        witch.phase == "normal"
        and not witch.invincible
        and not witch.no_hitbox
        and not witch.hidden
        and witch.teleport_cd > 0.0
    )
    _place_witch(900.0, 620.0, 300.0, 620.0)
    witch.damage_timer = 8.0
    _witch_ticks(2)
    teleport_auto = witch.phase in ("teleport_out", "teleport_in")
    _place_witch(900.0, 620.0, 300.0, 620.0)
    witch.hp = 199.0
    witch.teleport_cd = 99.0
    _witch_ticks(5)
    heal_started = witch.phase.startswith("heal") and witch.heal_used
    heal_flags = (
        witch.invincible and witch.no_hitbox and witch.ignore_separation
    )
    _witch_ticks(600)
    heal_finished = (
        witch.phase == "normal"
        and abs(witch.hp - 319.0) < 1e-6
        and abs(witch.x - 900.0) < 2.0
        and abs(witch.y - 620.0) < 2.0
    )
    witch.hp = 100.0
    _witch_ticks(5)
    heal_once = not witch.phase.startswith("heal")
    crooked_witch_teleport_ok = (
        teleport_excludes_nearest
        and teleport_started
        and teleport_flags
        and teleport_finished
        and teleport_auto
    )
    crooked_witch_heal_ok = (
        heal_started
        and heal_flags
        and heal_finished
        and heal_once
    )

    _place_witch(900.0, 620.0, 300.0, 620.0)
    lightning_started = witch.force_attack(scene, witch_player, "witch_lightning")
    lightning_forward = witch.attack_id == "witch_lightning_forward"
    _witch_ticks(80)
    lightning_damage = abs(witch_player.hp - 64.0) < 1e-6
    lightning_vulnerable = (
        abs(witch_player.statuses.vulnerable_amount() - 0.20) < 1e-6
    )
    _place_witch(900.0, 620.0, 700.0, 320.0)
    lightning_up = witch._choose_lightning_attack(scene, witch_player)
    _place_witch(900.0, 220.0, 400.0, 620.0)
    lightning_down = witch._choose_lightning_attack(scene, witch_player)
    _place_witch(900.0, 620.0, 950.0, 320.0)
    lightning_close = witch._choose_lightning_attack(scene, witch_player) is None
    _place_witch(315.0, 620.0, 470.0, 220.0)
    lightning_blocked = witch._choose_lightning_attack(scene, witch_player) is None

    class _FakeLightning:
        def __init__(self, target) -> None:
            self.target = target
            self.kind = "witch_lightning_forward"

    _place_witch(900.0, 620.0, 300.0, 620.0)
    for _ in range(4):
        witch.on_projectile_hit(_FakeLightning(witch_player))
    vulnerability_stacks = (
        abs(witch_player.statuses.vulnerable_amount() - 0.60) < 1e-6
    )
    crooked_witch_lightning_ok = (
        lightning_started
        and lightning_forward
        and lightning_damage
        and lightning_vulnerable
        and lightning_up == "witch_lightning_up"
        and lightning_down == "witch_lightning_down"
        and lightning_close
        and lightning_blocked
        and vulnerability_stacks
    )

    _place_witch(900.0, 620.0, 300.0, 620.0)
    ice_started = witch.force_attack(scene, witch_player, "witch_ice_spike")
    _witch_ticks(120)
    ice_hit = (
        abs(witch_player.hp - 70.0) < 1e-6
        and witch_player.statuses.has("freeze")
    )
    _place_witch(900.0, 620.0, 300.0, 620.0)
    witch.force_attack(scene, witch_player, "witch_ice_spike")
    witch_player.x = 500.0
    _witch_ticks(120)
    ice_dodged = abs(witch_player.hp - 100.0) < 1e-6
    _place_witch(900.0, 620.0, 300.0, 400.0)
    ice_no_surface = witch._find_ice_spot(scene, witch_player) is None
    crooked_witch_ice_spike_ok = (
        ice_started and ice_hit and ice_dodged and ice_no_surface
    )

    _place_witch(900.0, 620.0, 300.0, 620.0)
    potion_started = witch.force_attack(scene, witch_player, "witch_potion")
    _witch_ticks(150)
    potion_direct = (
        witch_player.hp < 100.0
        and witch_player.statuses.has_poison_source("witch_potion_hit")
        and abs(witch_player.statuses.slow_factor() - 0.7) < 1e-6
        and not scene.hazards
    )
    _place_witch(900.0, 220.0, 300.0, 620.0)
    witch.force_attack(scene, witch_player, "witch_potion")
    _witch_ticks(200)
    potion_zone = any(
        hasattr(hazard, "poison_pct") for hazard in scene.hazards
    )
    crooked_witch_potion_ok = potion_started and potion_direct and potion_zone

    _place_witch(900.0, 620.0, 300.0, 620.0)
    witch.teleport_cd = 999.0
    fire_started = witch.force_attack(scene, witch_player, "witch_fire_rain")
    _witch_ticks(5)
    fire_flags = (
        witch.invincible
        and witch.no_hitbox
        and witch.ignore_separation
        and witch.phase in ("fire_in", "fire_cast")
        and witch.fire_cd == 0.0
    )
    for _ in range(900):
        scene.tick(FIXED_DT)
        if witch.phase == "normal":
            break
    fire_finished = (
        witch.phase == "normal"
        and witch.fire_spawned == 10
        and abs(witch.x - 900.0) < 2.0
        and abs(witch.fire_cd - 15.0) < 1e-6
    )
    _place_witch(900.0, 620.0, 300.0, 620.0)
    witch.force_attack(scene, witch_player, "witch_fire_rain")
    _witch_ticks(260)
    fireball = next(
        (
            projectile
            for projectile in scene.projectiles
            if getattr(projectile, "kind", "") == "witch_fireball"
        ),
        None,
    )
    locked_x = None if fireball is None else fireball.x
    if fireball is not None:
        witch_player.x += 160.0
        _witch_ticks(1)
        fire_x_locked = abs(fireball.x - locked_x) < 1e-6
    else:
        fire_x_locked = False
    crooked_witch_fire_rain_ok = (
        fire_started and fire_flags and fire_finished and fire_x_locked
    )

    _place_witch(900.0, 220.0, 300.0, 620.0)
    witch.ai_enabled = True
    witch.fire_cd = 0.0
    witch.lightning_cd = 99.0
    witch.ice_cd = 99.0
    witch.potion_cd = 99.0
    witch.opened_skill = True
    witch.skill_gap = 0.0
    witch.decision_cd = 0.0
    witch.opening_cd = 0.0
    witch._think(scene, witch_player)
    ai_fire = witch.phase == "fire_in"
    _place_witch(900.0, 220.0, 300.0, 620.0)
    witch.ai_enabled = True
    witch.fire_cd = 0.0
    witch.lightning_cd = 99.0
    witch.ice_cd = 99.0
    witch.potion_cd = 99.0
    witch.opened_skill = False
    witch.skill_gap = 0.0
    witch.decision_cd = 0.0
    witch.opening_cd = 0.0
    witch._think(scene, witch_player)
    ai_fire_first_blocked = (
        witch.phase == "normal" and witch.attack_id is None
    )
    _place_witch(900.0, 220.0, 300.0, 620.0)
    witch.ai_enabled = True
    witch.fire_cd = 99.0
    witch.lightning_cd = 99.0
    witch.ice_cd = 99.0
    witch.potion_cd = 0.0
    witch.skill_gap = 0.0
    witch.decision_cd = 0.0
    witch.opening_cd = 0.0
    witch._think(scene, witch_player)
    ai_potion = witch.attack_id == "witch_potion"
    _place_witch(900.0, 620.0, 300.0, 620.0)
    witch.ai_enabled = True
    witch.fire_cd = 99.0
    witch.potion_cd = 99.0
    witch.ice_cd = 99.0
    witch.lightning_cd = 0.0
    witch.skill_gap = 0.0
    witch.decision_cd = 0.0
    witch.opening_cd = 0.0
    witch._think(scene, witch_player)
    ai_lightning = witch.attack_id in (
        "witch_lightning_forward", "witch_lightning_up", "witch_lightning_down",
    )
    witch.ai_enabled = False
    scene.handle_debug_key(pygame.K_F8)
    ai_toggle = witch.ai_enabled
    scene.handle_debug_key(pygame.K_F8)
    crooked_witch_ai_ok = (
        ai_fire and ai_fire_first_blocked and ai_potion and ai_lightning
        and ai_toggle and not witch.ai_enabled
    )

    scene.reset()
    crooked_witch_reset_ok = (
        witch.phase == "normal"
        and witch.lightning_cd == 0.0
        and witch.ice_cd == 0.0
        and witch.potion_cd == 0.0
        and witch.fire_cd == 0.0
        and not witch.heal_used
        and not witch.no_hitbox
        and not witch.hidden
        and not witch.invincible
        and witch.hp == witch.max_hp
        and not scene.hazards
        and not scene.projectiles
    )
    crooked_witch_missing_frames = len(witch.anim.missing_paths())
    crooked_witch_fx_dir = ASSETS_DIR / "frames" / "crooked_witch" / "fx"
    crooked_witch_fx_missing = 0
    for prefix, count in (
        ("crooked_witch_teleport_fx_v1_out_", 6),
        ("crooked_witch_teleport_fx_v1_in_", 6),
        ("crooked_witch_heal_fx_v2_", 20),
        ("crooked_witch_lightning_fx_v2_forward_", 6),
        ("crooked_witch_lightning_fx_v2_up_", 6),
        ("crooked_witch_lightning_fx_v2_down_", 6),
        ("crooked_witch_ice_warning_v1_", 5),
        ("crooked_witch_ice_spike_fx_v1_", 7),
        ("crooked_witch_potion_projectile_v1_", 3),
        ("crooked_witch_potion_break_v1_", 4),
        ("crooked_witch_poison_pool_v1_", 4),
        ("crooked_witch_fire_rain_v7_pulse_", 45),
        ("crooked_witch_fire_impact_v1_", 4),
    ):
        for index in range(count):
            if not (crooked_witch_fx_dir / f"{prefix}{index:02d}.png").exists():
                crooked_witch_fx_missing += 1
    if not (crooked_witch_fx_dir / "crooked_witch_fireball_v1_00.png").exists():
        crooked_witch_fx_missing += 1
    if not (
        crooked_witch_fx_dir / "crooked_witch_heal_staff_prop_v1.png"
    ).exists():
        crooked_witch_fx_missing += 1

    # --- Phase K: Eira Frostveil (playable) ---
    scene.enemy_count_override = 1
    scene.set_character("eira")
    scene.set_enemy("dummy")
    scene.reset()
    eira = scene.player
    eira_dummy = scene.enemy

    def _place_eira(
        px: float = 300.0,
        ex: float = 700.0,
        py: float = 620.0,
        ey: float = 620.0,
    ) -> None:
        for fighter, x, y, facing in (
            (eira, px, py, 1 if ex >= px else -1),
            (eira_dummy, ex, ey, 1 if px >= ex else -1),
        ):
            fighter.x = float(x)
            fighter.y = float(y)
            fighter.facing = facing
            fighter.vx = 0.0
            fighter.vy = 0.0
            fighter.kb_vx = 0.0
            fighter.kb_time = 0.0
            fighter.hitstun = 0.0
            fighter.hp = fighter.max_hp
            fighter.state = FighterState.IDLE
            fighter.on_ground = True
            fighter.invincible = False
            fighter.statuses.clear()
            fighter.eira_freeze = 0.0
        eira.q_cd = 0.0
        eira.e_cd = 0.0
        eira.attack_runtime = None
        eira.attack_id = None
        eira._clear_e_state()
        eira._clear_e_armor()
        eira_dummy.ai_enabled = False
        scene.hazards = []
        scene.projectiles = []
        scene.hitstop = 0.0
        scene.match_over = None
        scene.sim_time = 0.0

    def _eira_ticks(count: int) -> None:
        for _ in range(count):
            scene.tick(FIXED_DT)

    eira_frame_count = sum(
        len(clip.get("frames", []))
        for clip in scene.store.animations["eira_clips"].values()
    )
    eira_present = (
        eira.name == "Eira Frostveil"
        and eira.max_hp == 100.0
        and eira.basic_atk == 20.0
        and eira.extra_atk == 0.0
        and abs(eira.walk_speed - 260.0) < 1e-6
        and abs(eira.jump_v - 760.0) < 1e-6
        and eira.hurtbox_dims == (56.0, 210.0)
        and abs(eira.q_cd_max - 3.0) < 1e-6
        and abs(eira.e_cd_max - 12.0) < 1e-6
        and len(scene.store.animations["eira_clips"]) == 15
        and eira_frame_count == 48
        and list(scene.store.roster["characters"])[-1] == "eira"
        and scene.store.debug["roster"]["default_character"] == "lina"
    )

    _place_eira(300.0, 700.0)
    scene.input.buffer.press("punch")
    _eira_ticks(40)
    lmb_hit = (
        abs(eira_dummy.hp - 980.0) < 1e-6
        and abs(eira_dummy.eira_freeze - 20.0) < 1e-6
        and not scene.projectiles
    )
    _place_eira(300.0, 700.0)
    eira_dummy.hurtbox_config = {
        "standing": [56, 210], "crouching": [56, 130],
    }
    eira_dummy.state = FighterState.CROUCH
    scene.input.buffer.press("punch")
    _eira_ticks(40)
    lmb_crouch_dodge = abs(eira_dummy.hp - 1000.0) < 1e-6
    eira_dummy.hurtbox_config = {"standing": [70, 190], "crouching": [70, 190]}
    eira_lmb_ok = lmb_hit and lmb_crouch_dodge

    _place_eira(300.0, 380.0)
    scene.input.buffer.press("kick")
    _eira_ticks(40)
    eira_rmb_ok = (
        abs(eira_dummy.hp - 980.0) < 1e-6
        and abs(eira_dummy.eira_freeze - 20.0) < 1e-6
    )

    _place_eira(300.0, 700.0)
    scene.input.buffer.press("q")
    _eira_ticks(40)
    q_hit = (
        abs(eira_dummy.hp - 976.0) < 1e-6
        and abs(eira_dummy.eira_freeze - 30.0) < 1e-6
        and eira.q_cd > 0.0
    )
    _place_eira(300.0, 700.0)
    eira_dummy.statuses.add("freeze", 2.0)
    scene.input.buffer.press("q")
    _eira_ticks(40)
    q_frozen = (
        abs(eira_dummy.hp - 956.0) < 1e-6
        and abs(eira_dummy.eira_freeze) < 1e-6
    )
    scene.enemy_count_override = 2
    scene._rebuild_fighters()
    eira = scene.player
    eira_dummy = scene.enemies[0]
    _place_eira(300.0, 700.0)
    scene.enemies[1].x = 900.0
    scene.enemies[1].y = 620.0
    scene.enemies[1].on_ground = True
    scene.input.buffer.press("q")
    _eira_ticks(50)
    q_pierce = (
        abs(scene.enemies[0].hp - 976.0) < 1e-6
        and abs(scene.enemies[1].hp - 976.0) < 1e-6
    )
    scene.enemy_count_override = 1
    scene._rebuild_fighters()
    eira = scene.player
    eira_dummy = scene.enemy
    eira_q_ok = q_hit and q_frozen and q_pierce

    _place_eira(300.0, 700.0)
    scene.input.buffer.press("e")
    _eira_ticks(30)
    e_hold_ok = (
        eira.e_phase == "hold"
        and eira.e_targeting
        and eira.e_cd > 10.0
    )
    scene.mouse_x = 700.0
    scene.input.buffer.press("punch")
    _eira_ticks(10)
    e_spawned = len(scene.hazards) == 1
    _eira_ticks(80)
    e_hit = (
        abs(eira_dummy.hp - 970.0) < 1e-6
        and abs(eira_dummy.eira_freeze - 50.0) < 1e-6
        and eira.e_phase is None
    )
    _place_eira(300.0, 700.0)
    eira_dummy.statuses.add("freeze", 5.0)
    scene.input.buffer.press("e")
    _eira_ticks(30)
    scene.mouse_x = 700.0
    scene.input.buffer.press("punch")
    _eira_ticks(100)
    e_frozen = (
        abs(eira_dummy.hp - 946.0) < 1e-6
        and abs(eira_dummy.eira_freeze) < 1e-6
    )
    _place_eira(300.0, 700.0)
    scene.input.buffer.press("e")
    _eira_ticks(30)
    scene.input.buffer.press("kick")
    _eira_ticks(5)
    e_cancel = (
        eira.e_phase == "recover" and 5.5 <= eira.e_cd <= 6.0
    )
    _place_eira(300.0, 700.0)
    scene.input.buffer.press("e")
    _eira_ticks(30)
    _eira_ticks(480)
    e_timeout = eira.e_phase in (None, "recover") and 5.0 <= eira.e_cd <= 6.0
    _place_eira(300.0, 700.0)
    scene.input.buffer.press("e")
    _eira_ticks(5)
    hp_before_armor = eira.hp
    eira.take_hit(10.0, 50.0, 0.2, -1)
    e_armor = (
        abs(eira.hp - (hp_before_armor - 10.0)) < 1e-6
        and eira.e_phase is not None
        and eira.state == FighterState.ATTACK
    )
    _place_eira(300.0, 700.0)
    scene.input.buffer.press("e")
    _eira_ticks(5)
    eira.hp = 5.0
    eira.take_hit(999.0, 0.0, 0.2, -1)
    e_ko = eira.e_phase is None and eira.state == FighterState.KO
    eira_e_ok = (
        e_hold_ok and e_spawned and e_hit and e_frozen
        and e_cancel and e_timeout and e_armor and e_ko
    )

    _place_eira(300.0, 700.0)
    for _ in range(5):
        eira.apply_freeze(eira_dummy, 20.0)
    freeze_threshold = (
        eira_dummy.statuses.has("freeze")
        and abs(eira_dummy.eira_freeze) < 1e-6
    )
    eira.apply_freeze(eira_dummy, 20.0)
    freeze_no_accum = abs(eira_dummy.eira_freeze) < 1e-6
    eira_dummy.statuses.remove("freeze")
    eira.apply_freeze(eira_dummy, 20.0)
    freeze_resumes = abs(eira_dummy.eira_freeze - 20.0) < 1e-6
    _place_eira(300.0, 700.0)
    eira.apply_freeze(eira_dummy, 30.0)
    freeze_slow = abs(eira_dummy.statuses.slow_factor() - 0.7) < 1e-6
    _place_eira(300.0, 700.0)
    eira.apply_freeze(eira_dummy, 20.0)
    eira.apply_freeze(eira_dummy, 50.0)
    eira.apply_freeze(eira_dummy, 30.0)
    freeze_strongest = abs(eira_dummy.statuses.slow_factor() - 0.5) < 1e-6
    scene.enemy_count_override = 2
    scene._rebuild_fighters()
    eira = scene.player
    _place_eira(300.0, 700.0)
    eira.apply_freeze(scene.enemies[0], 50.0)
    freeze_independent = (
        abs(scene.enemies[0].eira_freeze - 50.0) < 1e-6
        and abs(scene.enemies[1].eira_freeze) < 1e-6
    )
    scene.enemy_count_override = 1
    scene._rebuild_fighters()
    eira = scene.player
    eira_dummy = scene.enemy
    scene.reset()
    freeze_reset = all(
        abs(enemy.eira_freeze) < 1e-6 for enemy in scene.enemies
    )
    eira_freeze_ok = (
        freeze_threshold and freeze_no_accum and freeze_resumes
        and freeze_slow and freeze_strongest and freeze_independent
        and freeze_reset
    )

    _place_eira(300.0, 700.0)
    ladder = scene.stage.ladders[0]
    eira.x = float(ladder.rect.centerx)
    eira.y = float(ladder.bottom_y - 12.0)
    eira.on_ground = True
    scene.input.held.add("climb_up")
    _eira_ticks(10)
    climb_started = (
        eira.climbing and eira.anim.clip_name == "climb"
    )
    eira.take_hit(5.0, 0.0, 0.2, -1)
    _eira_ticks(2)
    climb_interrupted = not eira.climbing
    scene.input.held.discard("climb_up")
    eira_climb_ok = climb_started and climb_interrupted

    _place_eira(300.0, 700.0)
    scene.input.buffer.press("e")
    _eira_ticks(10)
    scene.mouse_x = 700.0
    scene.input.buffer.press("punch")
    _eira_ticks(10)
    scene.reset()
    eira_reset_ok = (
        eira.e_phase is None
        and not eira.e_targeting
        and eira.q_cd == 0.0
        and eira.e_cd == 0.0
        and eira.anim.clip_name == "idle"
        and not scene.hazards
    )
    eira_missing_frames = len(eira.anim.missing_paths())
    eira_fx_dir = ASSETS_DIR / "frames" / "eira" / "fx"
    eira_fx_missing = 0
    for prefix, count in (
        ("eira_snowball_v1_fx_impact_", 4),
        ("eira_ice_shard_v1_fx_charge_", 3),
        ("eira_ice_shard_v1_fx_release_", 2),
        ("eira_ice_shard_v1_fx_hit_", 4),
        ("eira_ice_shard_v1_fx_frozen_hit_", 4),
        ("eira_e_release_v1_fx_charge_", 3),
        ("eira_e_release_v1_fx_hit_", 3),
        ("eira_e_release_v1_fx_frozen_hit_", 3),
        ("eira_e_release_v1_fx_ground_", 4),
        ("eira_e_release_v1_fx_fragment_", 3),
        ("eira_e_release_v2_fx_chunk_", 4),
    ):
        for index in range(count):
            if not (eira_fx_dir / f"{prefix}{index:02d}.png").exists():
                eira_fx_missing += 1
    for index in (2, 3):
        if not (
            eira_fx_dir / f"eira_staff_strike_v2_fx_{index:02d}.png"
        ).exists():
            eira_fx_missing += 1
    for name in (
        "eira_snowball_v1_fx_release.png",
        "eira_snowball_v1_fx_projectile.png",
        "eira_ice_shard_v1_fx_projectile.png",
        "eira_e_release_v1_fx_fall_trail.png",
        "eira_e_release_v4_fx_ball.png",
    ):
        if not (eira_fx_dir / name).exists():
            eira_fx_missing += 1

    scene.enemy_count_override = 1
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
        f"default_character_ok={default_character_ok} "
        f"default_hit_group_ok={default_hit_group_ok} "
        f"rhea_roster_order_ok={rhea_roster_order_ok} "
        f"rhea_present={rhea_present} rhea_default_ok={rhea_default_ok} "
        f"rhea_knockback_ok={rhea_knockback_ok} "
        f"rhea_lmb_ok={rhea_lmb_ok} "
        f"rhea_lmb_ground_veno_ok={rhea_lmb_ground_veno_ok} "
        f"rhea_passive_ok={rhea_passive_ok} "
        f"rhea_passive_3pct_ok={rhea_passive_3pct_ok} "
        f"rhea_passive_veno_ok={rhea_passive_veno_ok} "
        f"rhea_rmb_ok={rhea_rmb_ok} rhea_q_ok={rhea_q_ok} "
        f"rhea_q_300_ok={rhea_q_300_ok} rhea_q_dummy_ok={rhea_q_dummy_ok} "
        f"rhea_q_dr_ok={rhea_q_dr_ok} rhea_q_stack_ok={rhea_q_stack_ok} "
        f"rhea_q_kill_ok={rhea_q_kill_ok} "
        f"rhea_close_range_ok={rhea_close_range_ok} rhea_range_ok={rhea_range_ok} "
        f"rhea_dash_ok={rhea_dash_ok} "
        f"rhea_e_no_return_ok={rhea_e_no_return_ok} "
        f"rhea_e_buffered_ok={rhea_e_buffered_ok} "
        f"rhea_e_air_ok={rhea_e_air_ok} "
        f"rhea_e_hit_cancel_ok={rhea_e_hit_cancel_ok} "
        f"rhea_e_window_q_ok={rhea_e_window_q_ok} "
        f"rhea_e_return_armor_ok={rhea_e_return_armor_ok} "
        f"rhea_e_poison_ok={rhea_e_poison_ok} "
        f"rhea_e_poison_300_ok={rhea_e_poison_300_ok} "
        f"rhea_e_veno_no_bonus_ok={rhea_e_veno_no_bonus_ok} "
        f"rhea_e_dr_ok={rhea_e_dr_ok} rhea_e_armor_ok={rhea_e_armor_ok} "
        f"rhea_e_terrain_ok={rhea_e_terrain_ok} "
        f"rhea_projectile_block_ok={rhea_projectile_block_ok} "
        f"rhea_cleanup_ok={rhea_cleanup_ok} "
        f"rhea_cleanup_window_ok={rhea_cleanup_window_ok} "
        f"rhea_climb_ok={rhea_climb_ok} "
        f"rhea_missing_frames={rhea_missing} rhea_fx_missing={rhea_fx_missing} "
        f"rhea_switch_ai_off_ok={rhea_switch_ai_off_ok} "
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
        f"veno_group_gap_ok={veno_group_gap_ok} "
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
        f"bat_group_gap_ok={bat_group_gap_ok} "
        f"bat_flight_cycle_ok={bat_flight_cycle_ok} "
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
        f"creepy_ladder_hit_ok={creepy_ladder_hit_ok} "
        f"creepy_ladder_hit_mid_ok={creepy_ladder_hit_mid_ok} "
        f"creepy_ladder_hit_platform_ok={creepy_ladder_hit_platform_ok} "
        f"creepy_ladder_hit_top_ok={creepy_ladder_hit_top_ok} "
        f"creepy_cleanup_ok={creepy_cleanup_ok} "
        f"creepy_stage_switch_ok={creepy_stage_switch_ok} "
        f"warrior_stage_ok={warrior_stage_ok} bat_stage_ok={bat_stage_ok} "
        f"veno_stage_ok={veno_stage_ok} "
        f"scene_variant_switch_ok={scene_variant_switch_ok} "
        f"creepy_missing_frames={creepy_missing} creepy_fx_missing={creepy_fx_missing} "
        f"mech_crab_present={mech_crab_present} "
        f"mech_crab_stage_ok={mech_crab_stage_ok} "
        f"mech_crab_armor_ok={mech_crab_armor_ok} "
        f"mech_crab_laser_ok={mech_crab_laser_ok} "
        f"mech_crab_charge_ok={mech_crab_charge_ok} "
        f"mech_crab_claw_ok={mech_crab_claw_ok} "
        f"mech_crab_leap_ok={mech_crab_leap_ok} "
        f"mech_crab_gap_ok={mech_crab_gap_ok} "
        f"mech_crab_slots_ok={mech_crab_slots_ok} "
        f"mech_crab_win_ok={mech_crab_win_ok} "
        f"mech_crab_cleanup_ok={mech_crab_cleanup_ok} "
        f"mech_crab_ai_ok={mech_crab_ai_ok} "
        f"mech_crab_missing_frames={mech_crab_missing} "
        f"mech_crab_fx_missing={mech_crab_fx_missing} "
        f"shadow_ninja_present={shadow_ninja_present} "
        f"shadow_ninja_stats_ok={shadow_ninja_stats_ok} "
        f"shadow_ninja_slots_ok={shadow_ninja_slots_ok} "
        f"shadow_ninja_slash_ok={shadow_ninja_slash_ok} "
        f"shadow_ninja_throw_ok={shadow_ninja_throw_ok} "
        f"shadow_ninja_dash_ok={shadow_ninja_dash_ok} "
        f"shadow_ninja_marks_ok={shadow_ninja_marks_ok} "
        f"shadow_ninja_ai_ok={shadow_ninja_ai_ok} "
        f"shadow_ninja_crouch_ok={shadow_ninja_crouch_ok} "
        f"shadow_ninja_jump_dodge_ok={shadow_ninja_dash_jump_dodge_ok} "
        f"shadow_ninja_barrier_hop_ok={shadow_ninja_barrier_hop_ok} "
        f"shadow_ninja_win_ok={shadow_ninja_win_ok} "
        f"shadow_ninja_cleanup_ok={shadow_ninja_cleanup_ok} "
        f"shadow_marks_independent={shadow_marks_independent} "
        f"shadow_ninja_missing_frames={shadow_ninja_missing_frames} "
        f"shadow_ninja_fx_missing={shadow_ninja_fx_missing} "
        f"shadow_ninja_phantom_present={shadow_ninja_phantom_present} "
        f"shadow_ninja_phantom_transform_ok={shadow_ninja_phantom_transform_ok} "
        f"shadow_ninja_phantom_invincible_ok={shadow_ninja_phantom_invincible_ok} "
        f"shadow_ninja_phantom_clear_ok={shadow_ninja_phantom_clear_ok} "
        f"shadow_ninja_phantom_marks_separate_ok={shadow_ninja_phantom_marks_separate_ok} "
        f"shadow_ninja_phantom_no_hitbox_ok={shadow_ninja_phantom_no_hitbox_ok} "
        f"shadow_ninja_phantom_rend_ok={shadow_ninja_phantom_rend_ok} "
        f"shadow_ninja_phantom_bind_ok={shadow_ninja_phantom_bind_ok} "
        f"shadow_ninja_phantom_flash_ok={shadow_ninja_phantom_flash_ok} "
        f"shadow_ninja_phantom_once_ok={shadow_ninja_phantom_once_ok} "
        f"shadow_ninja_phantom_auto_revert_ok={shadow_ninja_phantom_auto_revert_ok} "
        f"shadow_ninja_phantom_cd_ok={shadow_ninja_phantom_cd_ok} "
        f"shadow_ninja_phantom_ai_ok={shadow_ninja_phantom_ai_ok} "
        f"shadow_ninja_phantom_reset_ok={shadow_ninja_phantom_reset_ok} "
        f"shadow_ninja_phantom_missing_frames={shadow_ninja_phantom_missing_frames} "
        f"shadow_ninja_phantom_fx_missing={shadow_ninja_phantom_fx_missing} "
        f"crooked_witch_present={crooked_witch_present} "
        f"crooked_witch_stats_ok={crooked_witch_stats_ok} "
        f"crooked_witch_teleport_ok={crooked_witch_teleport_ok} "
        f"crooked_witch_heal_ok={crooked_witch_heal_ok} "
        f"crooked_witch_lightning_ok={crooked_witch_lightning_ok} "
        f"crooked_witch_ice_spike_ok={crooked_witch_ice_spike_ok} "
        f"crooked_witch_potion_ok={crooked_witch_potion_ok} "
        f"crooked_witch_fire_rain_ok={crooked_witch_fire_rain_ok} "
        f"crooked_witch_ai_ok={crooked_witch_ai_ok} "
        f"crooked_witch_reset_ok={crooked_witch_reset_ok} "
        f"crooked_witch_missing_frames={crooked_witch_missing_frames} "
        f"crooked_witch_fx_missing={crooked_witch_fx_missing} "
        f"eira_present={eira_present} "
        f"eira_lmb_ok={eira_lmb_ok} "
        f"eira_rmb_ok={eira_rmb_ok} "
        f"eira_q_ok={eira_q_ok} "
        f"eira_e_ok={eira_e_ok} "
        f"eira_freeze_ok={eira_freeze_ok} "
        f"eira_climb_ok={eira_climb_ok} "
        f"eira_reset_ok={eira_reset_ok} "
        f"eira_missing_frames={eira_missing_frames} "
        f"eira_fx_missing={eira_fx_missing} "
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
        f"ladder_mount_early_ok={ladder_mount_early_ok} "
        f"ladder_jump_overlap_ok={ladder_jump_overlap_ok} "
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
        and default_character_ok
        and default_hit_group_ok
        and rhea_roster_order_ok
        and rhea_present
        and rhea_default_ok
        and rhea_knockback_ok
        and rhea_lmb_ok
        and rhea_lmb_ground_veno_ok
        and rhea_passive_ok
        and rhea_passive_3pct_ok
        and rhea_passive_veno_ok
        and rhea_rmb_ok
        and rhea_q_ok
        and rhea_q_300_ok
        and rhea_q_dummy_ok
        and rhea_q_dr_ok
        and rhea_q_stack_ok
        and rhea_q_kill_ok
        and rhea_close_range_ok
        and rhea_range_ok
        and rhea_dash_ok
        and rhea_e_no_return_ok
        and rhea_e_buffered_ok
        and rhea_e_air_ok
        and rhea_e_hit_cancel_ok
        and rhea_e_window_q_ok
        and rhea_e_return_armor_ok
        and rhea_e_poison_ok
        and rhea_e_poison_300_ok
        and rhea_e_veno_no_bonus_ok
        and rhea_e_dr_ok
        and rhea_e_armor_ok
        and rhea_e_terrain_ok
        and rhea_projectile_block_ok
        and rhea_cleanup_ok
        and rhea_cleanup_window_ok
        and rhea_climb_ok
        and rhea_missing == 0
        and rhea_fx_missing == 0
        and rhea_switch_ai_off_ok
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
        and veno_group_gap_ok
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
        and bat_group_gap_ok
        and bat_flight_cycle_ok
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
        and creepy_ladder_hit_ok
        and creepy_cleanup_ok
        and creepy_stage_switch_ok
        and warrior_stage_ok
        and bat_stage_ok
        and veno_stage_ok
        and scene_variant_switch_ok
        and creepy_missing == 0
        and creepy_fx_missing == 0
        and mech_crab_present
        and mech_crab_stage_ok
        and mech_crab_armor_ok
        and mech_crab_laser_ok
        and mech_crab_charge_ok
        and mech_crab_claw_ok
        and mech_crab_leap_ok
        and mech_crab_gap_ok
        and mech_crab_slots_ok
        and mech_crab_win_ok
        and mech_crab_cleanup_ok
        and mech_crab_ai_ok
        and mech_crab_missing == 0
        and mech_crab_fx_missing == 0
        and shadow_ninja_present
        and shadow_ninja_stats_ok
        and shadow_ninja_slots_ok
        and shadow_ninja_slash_ok
        and shadow_ninja_throw_ok
        and shadow_ninja_dash_ok
        and shadow_ninja_marks_ok
        and shadow_ninja_ai_ok
        and shadow_ninja_crouch_ok
        and shadow_ninja_dash_jump_dodge_ok
        and shadow_ninja_barrier_hop_ok
        and shadow_ninja_win_ok
        and shadow_ninja_cleanup_ok
        and shadow_marks_independent
        and shadow_ninja_missing_frames == 0
        and shadow_ninja_fx_missing == 0
        and shadow_ninja_phantom_present
        and shadow_ninja_phantom_transform_ok
        and shadow_ninja_phantom_invincible_ok
        and shadow_ninja_phantom_clear_ok
        and shadow_ninja_phantom_marks_separate_ok
        and shadow_ninja_phantom_no_hitbox_ok
        and shadow_ninja_phantom_rend_ok
        and shadow_ninja_phantom_bind_ok
        and shadow_ninja_phantom_flash_ok
        and shadow_ninja_phantom_once_ok
        and shadow_ninja_phantom_auto_revert_ok
        and shadow_ninja_phantom_cd_ok
        and shadow_ninja_phantom_ai_ok
        and shadow_ninja_phantom_reset_ok
        and shadow_ninja_phantom_missing_frames == 0
        and shadow_ninja_phantom_fx_missing == 0
        and crooked_witch_present
        and crooked_witch_stats_ok
        and crooked_witch_teleport_ok
        and crooked_witch_heal_ok
        and crooked_witch_lightning_ok
        and crooked_witch_ice_spike_ok
        and crooked_witch_potion_ok
        and crooked_witch_fire_rain_ok
        and crooked_witch_ai_ok
        and crooked_witch_reset_ok
        and crooked_witch_missing_frames == 0
        and crooked_witch_fx_missing == 0
        and eira_present
        and eira_lmb_ok
        and eira_rmb_ok
        and eira_q_ok
        and eira_e_ok
        and eira_freeze_ok
        and eira_climb_ok
        and eira_reset_ok
        and eira_missing_frames == 0
        and eira_fx_missing == 0
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
        and ladder_mount_early_ok
        and ladder_jump_overlap_ok
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
            elif event.type == pygame.MOUSEMOTION:
                scene.mouse_x = float(event.pos[0])
            elif event.type == pygame.MOUSEBUTTONDOWN:
                scene.mouse_x = float(event.pos[0])
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
