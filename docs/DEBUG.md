# Debugging the sandbox

## Launch checks

```bat
run.bat
run.bat --smoke-test
```

`--smoke-test` runs a headless 60Hz simulation. Phase A repeats Lina's punch/kick/Q/block/flame
checks against the training dummy; Phase B switches to Warrior and verifies hurt, startup super
armor, recovery interruption, axe damage/KO, dash damage + knock-up (`dash_ok`), airborne jump pose
(`air_pose_ok`), KO-in-place (`dash_ko_ok`), super-armor launch suppression (`dash_armor_ok`,
`armor_knockup_ok`), the draw-only knock-up vortex (`knockup_fx_ok`), throw out-and-back damage
(`throw_ok`), the inter-skill gap, win/loss, AI
approach + barrier jump, body separation/facing stability (`overlap_ok`), capped separation with no
enemy flip across a barrier (`separation_block_ok`), interrupted-transform
visibility (`transform_hit_ok`), flame revert, flame alignment coverage (`flame_offset_ok`), roster
switching (`roster_ok`), and the data-driven V/C/X/Z slots (`slots_ok`). Phase C switches to Nyra
against the Dummy and checks wave/thrust damage, 4-hit mark detonation (`nyra_wave_burst_ok`,
`nyra_wave_burst_damage_ok`), Q slash hitbox/FX plus the extended-range window
(`nyra_q_slash_range_ok`), Q/E super armor (`nyra_q_armor_ok`, `nyra_e_armor_ok`), E dash distance
(`nyra_dash_distance_ok`), the six-frame slash FX existence (`nyra_slash_fx_missing`), E dash
damage/cooldowns, per-target mark independence (`nyra_marks_per_target_ok`) and reset/death
clearing, lock-on and the pass-through dash (`nyra_dash_pass_ok`). Phase C2 checks Rhea against the
Dummy/Creepy Shooter/Warrior: LMB clip alternation and the +1s passive (`rhea_lmb_ok`,
`rhea_passive_ok`), steel/poison shuriken damage, 900 range and the point-blank body check
(`rhea_rmb_ok`, `rhea_q_ok`, `rhea_range_ok`, `rhea_close_range_ok`), Q's 8% actual-max-HP bonus,
5s/3% poison and same-source +5s (`rhea_q_300_ok`, `rhea_q_dummy_ok`, `rhea_q_dr_ok`,
`rhea_q_stack_ok`, `rhea_q_kill_ok`), zero knockback on RMB/Q/E plus LMB's 60
(`rhea_knockback_ok`), E's two groups, return to `cast_x`, 1.00s full armor and 15% poison bonus
(`rhea_dash_ok`, `rhea_e_poison_ok`, `rhea_e_poison_300_ok`, `rhea_e_dr_ok`, `rhea_e_armor_ok`,
`rhea_e_block_ok`), projectile/block/cleanup checks and `rhea_missing_frames` / `rhea_fx_missing`.
`default_hit_group_ok` also verifies Nyra's multi-hitbox attack still hits once. Phase D switches to
Lina vs Veno-Spider and checks bite, poison dps/stacking, web stun, hover ascent/descent, V/C/X/Z
slots, win and `veno_missing_frames`. Phase E switches to Bat and checks the five-Bat group
(selected with
F7; the startup default is Creepy Shooter), five initial altitudes, the 5-flight 3-high/2-low
cycle in 40–477 with random waypoints and a 2s low stay, dive 10 (height-gated), V/C/X/Z slots,
sonic 12 + 0.8s stun (high flights only), out/return/wall/barrier/platform bounce, the 0.65s cast
lock, hurt/stun staying airborne, KO landing, win, the F7 order, the five-body group
spawn/independent cooldowns/WIN and the sonic-only random stagger.
Phase F switches to Creepy Shooter and checks the mirrored stage variant, HP/ATK/slots, the straight
shot (30, block collision), the 1s lock wind-up and three-frame reticle, the homing bolt (platform
penetration, 20 once, 8s lifetime, survives owner KO), the back-roll (140px, 24, no i-frames, 10s,
falling off a platform edge), the jump shot (220/268 surfaces, right takeoff 1136, 24 downward,
no-platform rejection), barrier hopping (`creepy_ai_hop`), AI priority, V/C/X/Z mapping, WIN,
cleanup, stage switching, ladder hits (`creepy_ladder_hit_mid_ok`, `creepy_ladder_hit_platform_ok`,
`creepy_ladder_hit_top_ok`, `creepy_ladder_hit_ok`) and `creepy_missing_frames` /
`creepy_fx_missing`.
Phase G switches to Mech-Crab and checks the no-barrier stage variant (long platform 170–649 at
surface 268, short 796–1110 at 220, spawn 1000,620), HP 400/ATK 30 and the four skill slots, full
super armor through every skill (damage still applies and HP 0 still KOs), the core laser (1.0s
warning, 1.5s active at 90°/s, 36 once per target, platform blocking, stationary caster), the
locked-direction charge (5s cooldown, 1.0s warning, 45), the player-side claw slam (30 + 1.2s
stun), the leap slam (8s cooldown, 0.8s warning, fixed reticle, terrain-ignoring flight, 60 in a
100px AoE, platform landing), the 1s skill gap, V/C/X/Z mapping, WIN, cleanup, AI priority and
`mech_crab_missing_frames` / `mech_crab_fx_missing`.
Phase H switches to Shadow Ninja and checks its flat stage variant (spawn 1000,620), HP/ATK copied
from the current character, 1.5× walk, the four slots with slot 4 `shadow_phantom_form`, the 0.35s/0.5s high
slash (standing hit, crouching dodge), the 5s low kunai (1.2atk, 1s stun, one mark, no block
penetration), the 8s dash (~640px, player pass-through, low jump-dodgeable hitbox), the independent
mark stack (1→2→3→detonate→1, extra atk + 1s stun, KO/reset clears, super armor only blocks the
stun), the close/far/low-HP AI, crouch/jump defense, barrier hop, WIN/cleanup and
`shadow_ninja_missing_frames` / `shadow_ninja_fx_missing`.
Phase I switches to the phantom form and checks slot 4 `shadow_phantom_form`, the Z transform, the
11-frame/1.36s transform with frame-0 invincibility and self-clear, no-hitbox pass-through, P1/P2/P3,
one-use flags, auto-revert (6 frames/0.60s), the 15s cooldown after revert, the AI trigger/order,
reset, and `shadow_ninja_phantom_missing_frames` / `shadow_ninja_phantom_fx_missing`.
The Crooked Witch phase checks the F7 caster on its no-barrier platform variant (spawn 965,220;
four teleport points), HP 400 / ATK 30 and the four slots: the 8s teleport (damage priority, 8s
no-damage auto-teleport, nearest-point exclusion, invincible/no-hitbox/hidden), the one-time <50%
heal (5×24, return to the trigger position), lightning 36 + 20% vulnerable ×3 (damage first), the
1s ice-spike warning (30 + 1.5s freeze, dodgeable), the potion's direct 24 + 3%/s poison + 30% slow
versus its 6s miss zone (2%/s + 20% slow, independent source), fire rain (15s cooldown starting
after the skill, 10×0.8s x-locked vertical fireballs, 36 + burn, no first-skill use), the ground
1>2>3>4 / platform 3>1>2>4 AI priority, reset and `crooked_witch_missing_frames` /
`crooked_witch_fx_missing`.
The Eira phase checks the fourth playable character (15 clips / 48 frames, roster order, Lina still
the startup default): LMB 20 + 20 freeze and crouch dodge, RMB 20 + 20 with one hitbox,
Q 24/44 with pierce and +30 freeze, the E state machine (12s normal / 6s cancel cooldown, 0.40s
raise, targeting prompt, 0.08s spawn, ~1s fall, multi-target 30/54, super armor, KO end, 3s ground
FX), freeze threshold/clear/no-gain-while-frozen/equal slow/independent targets, climb, reset and
`eira_missing_frames` / `eira_fx_missing`.
The scene phase checks platform landing/side/underside (`platform_land_ok`, `platform_side_ok`,
`platform_bottom_bump_ok`), B toggling platforms (`platform_toggle_ok`), ladder up/down/Shift/jump-off
semantics (`ladder_climb_ok`, `ladder_down_ok`, `ladder_shift_no_down_ok`), the early midpoint mount
(`ladder_mount_early_ok`), jump-off platform-overlap immunity (`ladder_jump_overlap_ok`), the
two-frame back-view climb clips (`lina_climb_anim_ok`, `lina_climb_facing_ok`,
`lina_flame_climb_anim_ok`), ladders not blocking projectiles (`ladder_no_block_ok`), Nyra climbing
(`nyra_climb_ok`, `nyra_climb_anim_ok`), Rhea climbing (`rhea_climb_ok`), spawn clearance
(`platform_spawn_clear_ok`), the `penetrates_blocks` flag (`penetration_flag_ok`) and the default
enemy (`default_enemy_ok`). The climb checks verify the `climb` clip name, both frames, up 0→1 /
down 1→0, holding the current frame when stopped, the restored facing after jump-off, and the flame
variant using its flame climb art; `flame_offset_ok` includes the two new flame climb frames.
`ladder_mount_early_ok` checks the feet reach the platform midpoint threshold (last climbing y≈255
on the default long platform) before snapping to y=220; `ladder_jump_overlap_ok` jumps from a
ladder inside a platform and verifies x stays at the ladder center.
It also checks the projectile VFX dispatch (`q_cast_fx_ok`, `q_impact_fx_ok`, `q_normal_color_ok`,
`q_flame_color_ok`, `q_flame_cast_ok`, `veno_bite_hit_fx_ok`, `veno_poison_cast_ok`,
`veno_poison_impact_ok`, `veno_web_cast_ok`, `veno_web_impact_ok`, `bat_dive_hit_fx_ok`,
`bat_sonic_cast_ok`, `bat_sonic_impact_ok`, `bat_sonic_hitbox_ok`), poison cadence/tint/stacking
(`poison_interval_ok`, `poison_tint_ok`, `poison_stack_rules_ok`), web collision radius
(`veno_web_radius_ok`), the 3-Veno group spawn, per-instance cooldowns and all-dead WIN
(`veno_group_ok`, `veno_group_cooldowns_ok`), asset presence
(`lina_q_fx_missing`, `veno_vfx_missing`) and effect cleanup (`fx_cleanup_ok`). These are
file/effect checks only; appearance is reviewed with `tools/preview_fx.py` or in-game.
It prints one `SMOKE ...` line and exits non-zero on failure. It uses SDL's dummy video driver.

## Overlay and panel

- **F1 overlay**: hitboxes (red), hurtboxes (green), pivot/facing markers, projectile lane lines
  measured upward from Lina's feet (high/fist/mid/low), wall/barrier/platform/ladder bounds and
  entity state labels. Barrier boxes are yellow, platform boxes cyan; ladder trigger boxes are
  magenta with green/red top/bottom lines. The green box is the combat hurtbox; grounded stage
  movement uses a wider invisible body (`stage_body_width`), so Lina stops with her boots short of
  a barrier/platform before the green box touches it. Climb sprites are draw-scaled around the
  feet pivot (Lina 1.2×, Nyra 1.1×, Rhea 1.1×, Eira 1.15×); the F1 boxes and combat hurtboxes are not scaled,
  so the climb sprite intentionally looks larger than the green box.
- **F2 panel**: FPS/tick/sim time, current character/enemy ids and roster positions, result, block
  counts (`BARRIERS n PLATFORMS n LADDERS n`), `CLIMB up/down/idle`, and lock-on state, Lina
  state/HP/energy/Q/E cooldowns, flame timer/hits/next bonus, animation
  clip/frame, attack
  clock/queued action, hitstun/knockback, positions/facing, player and current-enemy statuses, the
  enemy's four skill slots with remaining cooldowns (`S1 axe_slash 0.0s ... S4 -`), enemy AI
  flag/attack/armor, last hit, input history/buffer, missing frames, last reload status/error.
  For Nyra the panel shows `Q ... E ...` without an energy line and adds the primary enemy's
  `MARKS n/3 BURST ... LAST ...` plus Nyra's total `BURSTS`. For Rhea it shows `CHAR rhea 3/3`,
  Q/E cooldowns and the target's `poison[rhea_poison]` line without an energy or passive gauge.
  For Eira it shows `EIRA E <raise/hold/release/recover> TARGET ON/OFF X <selected x> FREEZE
  <n>/100` plus the Q/E cooldowns; the hold phase draws the `Click the left mouse to choose an
  area.` prompt and the vertical mouse guide.
  For Veno it adds `MODE ground/ascend/hover/descend HOVER n`; for Bat it adds `MODE fly HOVER n`
  (altitude above ground); for Creepy Shooter the four slots show `creepy_shot`,
`creepy_homing_shot`, `creepy_roll_shot` and `creepy_jump_shot` with their remaining cooldowns;
for Mech-Crab they show `mech_laser`, `mech_charge`, `mech_claw_slam` and `mech_leap_slam`; for
Shadow Ninja they show `shadow_kunai_slash`, `shadow_kunai_throw`, `shadow_dash` and
`shadow_phantom_form`; during the phantom form the panel adds `PHANTOM n/3 P1/P2/P3 READY/USED`,
`PHANTOM FLASH <phase>`, `PHANTOM TRANSFORM`/`PHANTOM REVERT` and, after revert, `PHANTOM CD
15.0s`, while S1–S3 keep the normal cooldowns. The panel also adds `SHADOW MARKS n/3 BURST ...
LAST ...` for the player-side marks. For the Crooked Witch the panel adds `WITCH PHASE <phase>`,
`HEAL READY/USED`, `TP <cooldown>s`, `WITCH CD L/I/P/F`, `WITCH NO HITBOX/HIDDEN/INVINCIBLE` flags
and `WITCH VULN <percent>`; F1 also draws the four teleport points. Both lock reticles are
draw-only. Poison, vulnerable and stun appear in the status list. The three mark pips above each
living enemy, the three purple pips above the player during a Shadow Ninja fight, the green poison
pulse and the stun stars are draw-only.

## Simulation controls

| Key | Action |
|---|---|
| F3 | Pause/resume |
| F4 | Step one 1/60s tick while paused |
| F5 | Hot-reload all JSON; keeps last-good data on parse/validation failure and shows the error |
| F6 | Cycle time scale 0.25x / 0.5x / 1x / 2x |
| Esc | Pause menu |

## Sandbox controls

| Key | Action |
|---|---|
| F7 | Cycle the enemy roster (Warrior → Veno-Spider ×3 → Bat ×5 → Creepy Shooter → Mech-Crab → Shadow Ninja → Crooked Witch → training Dummy → …) |
| [ / ] | Cycle the playable character roster (Lina ↔ Nyra ↔ Rhea ↔ Eira) |
| F8 | Toggle enemy AI when present, otherwise invincibility |
| F9 | Full scene reset |
| F10 | Fill energy and force the flame transform |
| F11 | Cycle forced status on the current enemy (burn, poison, stun, freeze, slow, super armor, damage reduction) |
| F12 | Damage the current player by 10, then 999 when low; shows hurt/KO |
| V / C / X / Z | Trigger the enemy's skill slots 1/2/3/4; undefined slots are no-ops and show `-` in F2 |
| Middle mouse | Toggle attack lock-on (default off; resets off on character/enemy switch) |
| B | Toggle barrier + platform collision/visibility; ladders stay visible and climbable (HUD shows BLOCKS OFF) |
| Arrow keys | Move the current enemy -20/+20px |
| PgUp/PgDn | Current enemy HP +/-100 |
| R | Restart after VICTORY/DEFEATED (normal mode) |

## Debugging workflow

1. Use F1 to confirm hit/hurt boxes and lane positions.
2. Use F2 to inspect state, clip/frame, cooldown, energy, flame tiers, lock-on and status timers;
   middle mouse toggles attack lock-on and the HUD shows `LOCK-ON` while it is active.
3. Use F3/F4 to freeze a frame; F6 to slow the simulation for timing checks.
4. Use F7 to cycle the enemy roster and `[` / `]` for the character roster; a switch performs a full
   reset and leaves AI off. Startup and every reset (F5/F9/R) also leave AI off. F8 isolates damage
   (AI off) or toggles dummy invincibility; F9 resets a scenario with AI off.
5. Use F10 to test the full flame-form animation set and flame bonus tiers.
6. Use F11 to inspect status visuals and timers; F12 to test the active player's hurt/KO frames.
7. Warrior checks: V/C/X start axe slash/dash/throw and Z is a safe no-op; F1 shows the active
   hitbox; F2 shows the four slots, cooldowns, the `armor_until` window and AI flag. Use F8 to stop
   the AI while testing hitboxes. C launches Lina (air jump frames; 1.5s `knock_up` including
   hitstun; `combat.knock_up_gravity` keeps her airborne for that window, so landing and control
   return together) and the cyan vortex at her feet shrinks/fades with the remaining time; PgDn to 0
   shows the KO and VICTORY banner; F12 at low Lina HP shows DEFEATED; R restarts.
8. Nyra checks: use `[` to switch to Nyra; LMB/RMB/Q add marks (watch the 3 pips above the enemy),
   the 4th LMB/RMB/Q hit detonates for `1.8×atk + 10% max HP` and leaves 1 mark; E does not add
   marks. Marks are per target: with the 3-Veno group, hit different spiders and each keeps its own
   pips/stack — detonating one never consumes another's marks.
   LMB plays the 5-frame wave animation (0.06s each, 0.30s) and has no FX; RMB plays the 5-frame
   thrust animation (0.08s each, 0.40s) with a single hitbox active t=0.16-0.24; Q plays the 6-frame
   slash animation and the blue `nyra_slash_fx` effect (visible frames 02-04 align with the
   character's 02-04 frames) and adds 1 mark. Q and E have super armor: Q for its 0.40s, E during the
   0.06-0.36s dash; damage still applies but hitstun/knockback/launch/freeze/stun/slow are ignored.
   LMB uses the RMB thrust box outside t=0.06-0.24 and the extended
   `[28,-212,162,123]` box during t=0.06-0.24; Q uses the thrust box outside t=0.12-0.30 and the
   extended box during t=0.12-0.30. Use F1 to see the box changes. E dashes at 1100px/s for
   t=0.06-0.36s (~330px), passes through the enemy but stops at blocks/walls; at the end the bodies
   are pushed apart. F2 shows `Q/E` cooldowns and `MARKS n/3`; lock-on (middle mouse) turns Nyra at
   attack start.
   Rhea checks: `[` / `]` now cycles Lina → Nyra → Rhea. LMB alternates `rhea_slash_r/l`, deals 20
   and has 60 knockback; RMB is a 24-damage steel star (900 range, point-blank body check); Q is a
   24 + 8% max-HP poison star with 5s / 3%-per-second poison (8s cooldown, same-source +5s). Watch
   F2 for `poison[rhea_poison]` and the Q/E badges. LMB/RMB on an already-poisoned target add +1s;
   Q and E do not. E is a 1.00s dash-return (outbound ~594px, return to `cast_x`), 14 + 14 damage,
   +15% max HP on the first segment only, full 0–1.00s armor and 15s cooldown. The six star FX are
   `assets/frames/rhea/fx/rhea_shuriken_00..02` and `rhea_poison_shuriken_00..02`; E draws two
   procedural afterimages.
9. Veno checks: F7 to Veno spawns the **3-body group** (`roster.json` count/offsets/modes:
   one ground + two hovering by default); F8 toggles AI for all three. Veno is a half-size body
   (160×160 runtime frames, 75×75 hurtbox, `stage_body_width` 70, bite range 75); its mouth origin
   is 50px above the feet, so Lina's punch and ground Q lanes sit above the ground spider — use a
   kick or jump attack. On the ground it chases and bites with a wide-open mouth; at range it
   ascends on a web strand, hovers in a 140–300px sine wave and fires aimed venom/web. Cooldowns
   are per spider (bite 1s, poison 5s, web 8s), so the three can act independently. V/C/X start
   bite/poison/web on the primary and Z is a no-op. Each Veno draws its own health bar; the HUD
   label follows the nearest living primary. WIN requires all three dead. The smoke forces a
   single Veno for isolated checks and verifies the group spawn/all-dead WIN separately
   (`veno_group_ok`). F2 shows `MODE`/`HOVER`, slots and
   cooldowns; F11 shows poison's whole-body green/purple flash and stun stars. Hit it while
   airborne to knock it into descent. The web strand is draw-only, not a frame. Poison now has a
   dark-green mouth mist and hit splash, and poison damage settles once per 0.5s (six full ticks
   over the 3s duration); a poisoned fighter's whole sprite flash-tints green/purple every 0.18s,
   with no hurtbox rectangle. Web has procedural silk at the mouth, a rotating 64px web_05
   projectile with a silk trail and collision radius 30, and a 150–170px web impact decal plus
   yellow stun sparks; a connected bite adds a short green arc.
   Lina's Q projectile is a fist-sized static sprite: the supplied teal glass ball, pixelated with
   a white rim/highlights and a short pixel trail in normal form, orange-red in flame form. It is
   drawn 7px above the collision lane so it lines up with the punching fist; cast/impact effects
   use the same teal/orange family. The normal form has no code-generated ball.
10. Bat checks: the five-Bat group is selected with F7 (`count: 5`; the startup default is Creepy
    Shooter).
    The base is x=820 with per-member `spawn_jitter: 40`. It uses x offsets
    `[0,-160,160,-80,80]` and initial altitudes `180/320/240/380/280`. F7 selects Bat after Veno,
    and F8 starts the AI. Each Bat keeps a shuffled 5-flight bag (3 high / 2 low); a free flight
    lasts 5s, a low flight adds a 2s stay; high targets random 400–477 (screen y 143–220), low
    target is screen y=550; the initial timers are staggered 5/6/7/8/9s. During free flight it
    picks a random x waypoint (about 160–1120) every 0.9–1.4s or within 18px, so it keeps moving.
    V dives (locked direction, 10 damage, 2s); it only fires when `_dive_can_reach` confirms the
    dive hitbox can reach the player from the current altitude, otherwise the Bat keeps flying.
    C casts the sonic (0.65s lock, 12 + **0.8s stun**, 10s); the sonic is available only on high
    flights and is the only randomly-timed skill (random 0-2.5s opening cooldown + 50% cast gate).
    A same-skill group gap (sonic 1.2s / dive 0.8s) plus a 0.5s opening delay prevents same-skill
    overlaps (see DESIGN_DECISIONS §Multi-body enemy rules). X/Z are no-ops. The sonic spawns at
    the mouth (46px forward / 30px above the feet), uses a forward circle hitbox (+8px, r24),
    bounces off arena walls and barrier/platform AABBs, returns to the Bat's current position and
    hits at most once. Use B to compare block on/off; ladders are unaffected. F1 shows the 100×66
    hurtbox and the dive hitbox following the body; F2 shows `MODE fly`, `HOVER` altitude,
    `FLIGHT <high|low> <remaining>s target <height>h wx <waypoint> stay <s> bag <H>H/<L>L`, slots
    and cooldowns. Flight range is 40–477 (preferred 240 only as the reset cruise-height fallback,
    bob 24, vertical speed 300); the 477 cap keeps the sprite on screen. Hurt/stun keep it
    airborne; only KO falls and switches to `ko_01`. All five Bats must die for WIN. Smoke: `bat_flight_cycle_ok` (3H/2L bag, high/low
    heights, 2s low stay, no low-flight sonic, 20-damage punch reach, x span ≥80), `bat_group_gap_ok`
    (12s observation window), `bat_sonic_ok` (0.8s stun).
11. Creepy Shooter checks: the startup default (and the F7 step after Bat) selects it on the
    mirrored stage variant — long platform 601–1080 at y=220, short 170–484 at y=268, only the
    right ground barrier 790–880 (the left 400–490 was removed 2026-11-01), spawn (1000,220).
    Ladder hits are also covered: a mid-ladder shot clears the climb and knocks off without a
    platform side push; a hit with the feet inside a platform snaps to its top; a top shot lands
    on the platform (`creepy_ladder_hit_mid_ok`, `_platform_ok`, `_top_ok`). F8 toggles AI. V fires
    the straight shot (30, 1s); it is
    strictly horizontal, so a platform shot cannot hit a ground player. C starts the 1s lock
    wind-up: the three-frame reticle appears on the player, and a hit during the wind-up cancels the
    bolt but leaves the 8s cooldown. An uninterrupted bolt homes without limit, penetrates
    blocks/platforms, deals 20 once, has an 8s lifetime and is not removed by the shooter's KO. X
    rolls backward 140px, fires for 24 at t=0.30, has no i-frames (10s cooldown), and rolls off a
    platform edge instead of being clamped. Z is the platform jump shot: it starts only at a valid
    takeoff (the far-right ground point is 1136), rises beside the edge, lands on the 220 or 268
    surface and fires down for 24; without a platform it is a no-op. Bullets leave the measured
    muzzle, not the waist. The AI uses skill 1 across a clear level, skill 2 across a blocked line
    or level difference >60px, skill 3 inside 180px, and skill 4 to return to a platform; it hops
    90px ground barriers (`jump_v×1.15`, `walk×2.0` horizontal). F1 shows the collision boxes; F2
    shows the four cooldowns. The remaining ground barrier sits below the flat-ground mid lane, so
    test block collision from the platform or with the smoke's direct `barrier.centery` bullet.
12. Mech-Crab checks: F7 selects it after Creepy Shooter (the startup default remains Creepy
    Shooter) on its no-barrier variant — long platform 170–649 at 268, short 796–1110 at 220, spawn
    (1000,620). It has no basic attack; V/C/X/Z are laser/charge/claw/leap. Every skill is
    super-armored for its full duration, so hits only reduce HP and flash; HP 0 still KOs and
    clears the beam/reticle. F1 shows the 160×150 hurtbox, the laser segment and the fixed landing
    point; F2 shows the four cooldowns, current attack/clip/frame and `skill_gap`. The leap reticle
    is a user-drawn three-frame image (0.22/0.18/0.40s, last frame held in flight) at the landing
    point. The HP bar/name use `health_bar_lift` and sit above the shell. Smoke flags:
    `mech_crab_*` plus `mech_crab_fx_missing == 0`.
12b. Shadow Ninja checks: F7 selects it after Mech-Crab (the startup default remains Creepy
    Shooter) on the flat variant (no blocks/ladders, spawn 1000,620). HP/ATK follow the current
    character and walk is 1.5×; switching Lina/Nyra/Rhea/Eira or F9 keeps them in sync. V/C/X/Z are
    slash/throw/dash/transform in normal form; Z transforms, and in phantom V/C/X map to
    影爪/影缚/影闪 while Z is a no-op. F1 shows the 56×210 standing / 56×130 crouching hurtbox,
    the high slash box, the low dash box and the low lane; while `phantom_form` it hides the enemy
    hurtbox but keeps the phantom skill hitboxes. F2 shows the four slots (S4
    `shadow_phantom_form`), the three normal cooldowns, current clip/frame, `SHADOW MARKS n/3`, and
    the phantom lines listed above. Four consecutive normal hits (slash or throw) stack
    1→2→3→detonate→1 with extra atk damage + 1s stun; the purple pips are above the player and
    coexist with Nyra's blue marks. The kunai is blocked by barriers/platforms; jump over it. A
    full jump clears the dash low hitbox; crouch does not. The normal AI crouches against high
    attacks, jumps against low/mid threats, hops barriers, and tracks its own kunai into a dash.
    Smoke flags: `shadow_ninja_*` plus `shadow_ninja_fx_missing == 0`.
12c. Phantom form checks: Z transforms (11 frames/1.36s: normal → no-aura → shadow hold 0.50s →
    no-aura). Frame 0 is invincible and clears self marks/negatives/hitstun/KB; the player's
    attacks/projectiles pass through (no target, no marks/passives), the phantom phases through
    barriers/platforms, keeps normal cooldowns ticking, and has no jump/crouch/hurt/KO clips.
    V/C/X are 影爪 (high, crouch dodge, 1.0atk), 影缚 (low, jump dodge, 1.2atk + 1s stun, pierces
    barriers) and 影闪 (crouch-dodge the high hand/bolt 0.8, then jump-dodge the low shark 0.8;
    teleport behind, reappear at the bolt's far point, pause, shark charge). Each is one-use; the
    third auto-reverts (6 frames/0.60s); the 15s cooldown starts after the revert. The AI
    transforms at ≤40% HP or when the largest incoming hit is ≥25% max HP, then uses P2→P1 close or
    P2→P3→P1 far; there is no forced revert. F9/F7/reset clears the form. Smoke flags:
    `shadow_ninja_phantom_*`, `shadow_ninja_phantom_missing_frames == 0`,
    `shadow_ninja_phantom_fx_missing == 0`.
12d. Crooked Witch checks: F7 selects it after Shadow Ninja (the startup default remains Creepy
    Shooter) on the no-barrier platform variant (spawn 965,220; platforms 158–472 and 808–1122 at
    220; ladders 420–484 and 796–860). F1 draws the four teleport points; F2 shows `WITCH PHASE`,
    `HEAL READY/USED`, `TP`, the L/I/P/F cooldowns, the no-hitbox/hidden/invincible flags and
    `WITCH VULN`. Teleport triggers on damage (and after 8s without damage), excludes the nearest
    and current points, and is untargetable during the 0.3s out/in. Heal forces once below 50%:
    5×24 HP, untargetable, flies to center and back; while her hands are open the independent
    staff appears on the facing side, and the fly frames keep only her own staff. Lightning resolves
    damage before adding 20% vulnerable (three stacks, 3s). The ice-spike warning ring and the
    erupted spike sit at the target's feet; walking out during the 1s warning dodges it. The potion
    hit applies poison/slow; a miss leaves a grounded 6s pool. Fire rain cannot be the first
    numbered skill; its 15s cooldown starts only after the return flight, the hold pose stays on
    the raised frame, and the summon pillar is staff-width. Walking between AI decisions stays on
    the 4-frame 0.12s walk cycle without flickering to idle. Smoke flags: `crooked_witch_*`,
    `crooked_witch_missing_frames == 0`, `crooked_witch_fx_missing == 0`.
13. Scene/props: F1 shows barrier (yellow), platform (cyan) and ladder (magenta) boxes; ladder
    triggers have green/red top/bottom lines. Hold W near a ladder to climb, S to descend, Space to
    jump off; Shift never climbs down. The climb clip is a direct back view: frame 0 has the left
    hand/right leg high, frame 1 the right hand/left leg high; moving loops it, stopping holds the
    frame, and it is not horizontally flipped. Lina normal, Lina flame, Nyra, Rhea and Eira each
    have their own clip; Nyra's sword stays sheathed diagonally on her back and Rhea's two shuriken
    stay stowed on her back band. Platform tops/sides/undersides are solid; walking off an outer edge
    falls (no fall damage). A climb with a top platform mounts early at the platform midpoint minus
    6px (default long platform: last climb y≈255 → snap y=220). A hit while climbing clears the
    climb and applies knockback; if the feet are inside a platform it snaps to the platform top,
    otherwise the body falls. Ladder jumps/falls ignore platform sides/underside until landing, so
    the platform behind the ladder cannot shove the body sideways; platform-top landing still
    applies. F2 shows `BARRIERS/PLATFORMS/LADDERS` counts, `CLIMB`, and the current animation
    clip/frame. Use B to remove barriers/platforms from drawing/collision; ladders stay
    visible/climbable, and B-off at a ladder top holds the character on the ladder instead of
    mounting the platform. The toggle persists across F9 and resets on F5/rebuild.
14. Edit `game/data/*.json` and press F5 to tune values without restarting.
15. If a frame looks wrong, replace the PNG under `assets/frames/<character>/` and press F5; the frame
    cache keys on path + mtime. Climb frames are `assets/frames/lina/climb/`,
    `assets/frames/lina/flame/climb/`, `assets/frames/nyra/climb/` and `assets/frames/rhea/climb/`.
    Rhea's star strips live in `assets/frames/rhea/fx/`. Projectile FX sprites use the
    same rule: `assets/frames/lina/q_fx/`, `assets/frames/lina/flame/q_fx/` and
    `assets/frames/veno/veno_web_fx/`. Changing `LINA_Q_SPECS` sizes/durations, the climb draw
    scales (`CLIMB_DRAW_SCALE`, `NYRA_CLIMB_DRAW_SCALE`) or any effect duration in `game/fx.py`
    requires restarting Python; F5 only reloads PNG/JSON.

## Input checks

- An action pressed during an attack is queued, not dropped. The F2 `ATTACK` line shows
  `queue=<action>` until it executes; playback starts when the attack ends (E cancels recovery).
- An action pressed during hitstun or a control lock (knock_up/freeze/stun) is also queued; F2 shows
  `queue=<action>` while control is locked, and the action starts when control returns.
- Pause/resume, F5/F9 resets and window focus regain resync held movement/crouch/climb keys. Q/E/jump
  are press-only, so they still need a fresh press after those transitions. W is both jump and
  `climb_up`: away from a ladder it jumps, while near one it climbs. S is crouch and `climb_down`;
  Shift is crouch-only. A deliberate exit (Space/attack/hit) suppresses an immediate re-grab while
  W remains held.
- `pygame.key.stop_text_input()` runs at startup; if keys are still swallowed, switch the Windows IME
  to English before launching the sandbox.

There is intentionally no pytest suite and no file logging in this sandbox; failures are reported in
the debug panel and through the smoke test.
