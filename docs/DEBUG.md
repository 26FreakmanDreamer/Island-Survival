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
clearing, lock-on and the pass-through dash (`nyra_dash_pass_ok`). Phase D switches to Lina vs
Veno-Spider and checks bite, poison dps/stacking, web stun, hover ascent/descent, V/C/X/Z slots,
win and `veno_missing_frames`. Phase E switches to Bat and checks the five-Bat group (selected with
F7; the default enemy is Warrior), five spawn/cruise heights, free flight 40–420, dive 10
(height-gated), V/C/X/Z slots, sonic 12 + 1s stun, out/return/wall/barrier/platform bounce, the
0.65s cast lock, hurt/stun staying airborne, KO landing, win, the F7 order, the five-body group
spawn/independent cooldowns/WIN and the sonic-only random stagger.
The scene phase checks platform landing/side/underside (`platform_land_ok`, `platform_side_ok`,
`platform_bottom_bump_ok`), B toggling platforms (`platform_toggle_ok`), ladder up/down/Shift/jump-off
semantics (`ladder_climb_ok`, `ladder_down_ok`, `ladder_shift_no_down_ok`), the two-frame back-view
climb clips (`lina_climb_anim_ok`, `lina_climb_facing_ok`, `lina_flame_climb_anim_ok`), ladders not
blocking projectiles (`ladder_no_block_ok`), Nyra climbing (`nyra_climb_ok`, `nyra_climb_anim_ok`),
spawn clearance (`platform_spawn_clear_ok`), the `penetrates_blocks` flag
(`penetration_flag_ok`) and the default enemy (`default_enemy_ok`). The climb checks verify the
`climb` clip name, both frames, up 0→1 / down 1→0, holding the current frame when stopped, the
restored facing after jump-off, and the flame variant using its flame climb art;
`flame_offset_ok` includes the two new flame climb frames.
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
  feet pivot (Lina 1.2×, Nyra 1.1×); the F1 boxes and combat hurtboxes are not scaled, so the
  climb sprite intentionally looks larger than the green box.
- **F2 panel**: FPS/tick/sim time, current character/enemy ids and roster positions, result, block
  counts (`BARRIERS n PLATFORMS n LADDERS n`), `CLIMB up/down/idle`, and lock-on state, Lina
  state/HP/energy/Q/E cooldowns, flame timer/hits/next bonus, animation
  clip/frame, attack
  clock/queued action, hitstun/knockback, positions/facing, player and current-enemy statuses, the
  enemy's four skill slots with remaining cooldowns (`S1 axe_slash 0.0s ... S4 -`), enemy AI
  flag/attack/armor, last hit, input history/buffer, missing frames, last reload status/error.
  For Nyra the panel shows `Q ... E ...` without an energy line and adds the primary enemy's
  `MARKS n/3 BURST ... LAST ...` plus Nyra's total `BURSTS`.
  For Veno it adds `MODE ground/ascend/hover/descend HOVER n`; for Bat it adds `MODE fly HOVER n`
  (altitude above ground). Poison and stun appear in the status list. The three mark pips above each
  living enemy, the green poison pulse and the stun stars are draw-only.

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
| F7 | Cycle the enemy roster (Warrior → Veno-Spider ×3 → Bat ×5 → training Dummy → …) |
| [ / ] | Cycle the playable character roster (Lina ↔ Nyra) |
| F8 | Toggle enemy AI when present, otherwise invincibility |
| F9 | Full scene reset |
| F10 | Fill energy and force the flame transform |
| F11 | Cycle forced status on the current enemy (burn, poison, stun, freeze, slow, super armor, damage reduction) |
| F12 | Damage Lina by 10, then 999 when low; shows hurt/KO |
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
6. Use F11 to inspect status visuals and timers; F12 to test Lina's hurt/KO frames.
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
10. Bat checks: the five-Bat group is selected with F7 (`count: 5`; the default enemy is Warrior).
    With the x=600 spawn it uses x offsets `[0,-160,160,-80,80]` and altitudes
    `180/320/240/380/280`; they keep those as cruise heights. F7 selects Bat after Veno, and F8
    starts the AI. V dives (locked direction, 10 damage, 2s); it
    only fires when `_dive_can_reach` confirms the dive hitbox can reach the player from the current
    altitude, otherwise the Bat keeps flying. C casts the sonic (0.65s lock, 12 + 1s stun, 10s); the
    sonic is the only randomly-timed skill (random 0-2.5s opening cooldown + 50% cast gate), and a
    0.55s group stagger prevents same-skill overlaps. X/Z are no-ops. The sonic spawns at the mouth
    (46px forward / 30px above the feet), uses a forward circle hitbox (+8px, r24), bounces off
    arena walls and barrier/platform AABBs, returns to the Bat's current position and hits at most
    once. Use B to compare block on/off; ladders are unaffected. F1 shows the 100×66 hurtbox and the dive hitbox
    following the body; F2 shows `MODE fly`, `HOVER` altitude, slots and cooldowns. Flight range is
    40–420 (preferred 240, bob 24, vertical speed 300). Hurt/stun keep it airborne; only KO falls
    and switches to `ko_01`. All five Bats must die for WIN.
11. Scene/props: F1 shows barrier (yellow), platform (cyan) and ladder (magenta) boxes; ladder
    triggers have green/red top/bottom lines. Hold W near a ladder to climb, S to descend, Space to
    jump off; Shift never climbs down. The climb clip is a direct back view: frame 0 has the left
    hand/right leg high, frame 1 the right hand/left leg high; moving loops it, stopping holds the
    frame, and it is not horizontally flipped. Lina normal, Lina flame and Nyra each have their own
    clip; Nyra's sword stays sheathed diagonally on her back. Platform tops/sides/undersides are
    solid; walking off an outer edge falls (no fall damage). F2 shows
    `BARRIERS/PLATFORMS/LADDERS` counts, `CLIMB`, and the current animation clip/frame. Use B to
    remove barriers/platforms from drawing/collision; ladders stay visible/climbable, and B-off at
    a ladder top holds the character on the ladder instead of snapping to the platform. The toggle
    persists across F9 and resets on F5/rebuild.
12. Edit `game/data/*.json` and press F5 to tune values without restarting.
13. If a frame looks wrong, replace the PNG under `assets/frames/<character>/` and press F5; the frame
    cache keys on path + mtime. Climb frames are `assets/frames/lina/climb/`,
    `assets/frames/lina/flame/climb/` and `assets/frames/nyra/climb/`. Projectile FX sprites use the
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
