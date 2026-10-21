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
approach + block jump, body separation/facing stability (`overlap_ok`), capped separation with no
enemy flip across a block (`separation_block_ok`), interrupted-transform
visibility (`transform_hit_ok`), flame revert, flame alignment coverage (`flame_offset_ok`), roster
switching (`roster_ok`), and the data-driven V/C/X/Z slots (`slots_ok`). It prints one `SMOKE ...`
line and exits non-zero on failure. It uses SDL's dummy video driver.

## Overlay and panel

- **F1 overlay**: hitboxes (red), hurtboxes (green), pivot/facing markers, projectile lane lines
  measured upward from Lina's feet (high/fist/mid/low), wall/block bounds and entity state labels.
  The green box is the combat hurtbox; grounded stage movement uses a wider invisible body
  (`stage_body_width`), so Lina stops with her boots short of a block before the green box touches it.
- **F2 panel**: FPS/tick/sim time, current character/enemy ids and roster positions, result, block
  and lock-on state, Lina state/HP/energy/Q/E cooldowns, flame timer/hits/next bonus, animation
  clip/frame, attack
  clock/queued action, hitstun/knockback, positions/facing, player and current-enemy statuses, the
  enemy's four skill slots with remaining cooldowns (`S1 axe_slash 0.0s ... S4 -`), enemy AI
  flag/attack/armor, last hit, input history/buffer, missing frames, last reload status/error.

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
| F7 | Cycle the enemy roster (Warrior → training Dummy → …) |
| [ / ] | Cycle the playable character roster (currently Lina only) |
| F8 | Toggle enemy AI when present, otherwise invincibility |
| F9 | Full scene reset |
| F10 | Fill energy and force the flame transform |
| F11 | Cycle forced status on the current enemy (burn, poison, stun, freeze, slow, super armor, damage reduction) |
| F12 | Damage Lina by 10, then 999 when low; shows hurt/KO |
| V / C / X / Z | Trigger the enemy's skill slots 1/2/3/4; undefined slots are no-ops and show `-` in F2 |
| Middle mouse | Toggle attack lock-on (default off; resets off on character/enemy switch) |
| B | Toggle block collision and visibility (HUD shows BLOCKS OFF) |
| Arrow keys | Move the current enemy -20/+20px |
| PgUp/PgDn | Current enemy HP +/-100 |
| R | Restart after VICTORY/DEFEATED (normal mode) |

## Debugging workflow

1. Use F1 to confirm hit/hurt boxes and lane positions.
2. Use F2 to inspect state, clip/frame, cooldown, energy, flame tiers, lock-on and status timers;
   middle mouse toggles attack lock-on and the HUD shows `LOCK-ON` while it is active.
3. Use F3/F4 to freeze a frame; F6 to slow the simulation for timing checks.
4. Use F7 to cycle the enemy roster and `[` / `]` for the character roster; a switch performs a full
   reset and leaves AI off. F8 isolates damage (AI off) or toggles dummy invincibility; F9 resets a
   scenario.
5. Use F10 to test the full flame-form animation set and flame bonus tiers.
6. Use F11 to inspect status visuals and timers; F12 to test Lina's hurt/KO frames.
7. Warrior checks: V/C/X start axe slash/dash/throw and Z is a safe no-op; F1 shows the active
   hitbox; F2 shows the four slots, cooldowns, the `armor_until` window and AI flag. Use F8 to stop
   the AI while testing hitboxes. C launches Lina (air jump frames; 1.5s `knock_up` including
   hitstun; `combat.knock_up_gravity` keeps her airborne for that window, so landing and control
   return together) and the cyan vortex at her feet shrinks/fades with the remaining time; PgDn to 0
   shows the KO and VICTORY banner; F12 at low Lina HP shows DEFEATED; R restarts.
8. Use B to remove both blocks from drawing and collision when observing approach/attacks; this also
   stops the AI from jumping over them. The toggle persists across F9 and resets on F5/rebuild.
9. Edit `game/data/*.json` and press F5 to tune values without restarting.
10. If a frame looks wrong, replace the PNG under `assets/frames/<character>/` and press F5; the frame
    cache keys on path + mtime.

## Input checks

- An action pressed during an attack is queued, not dropped. The F2 `ATTACK` line shows
  `queue=<action>` until it executes; playback starts when the attack ends (E cancels recovery).
- An action pressed during hitstun or a control lock (knock_up/freeze/stun) is also queued; F2 shows
  `queue=<action>` while control is locked, and the action starts when control returns.
- Pause/resume, F5/F9 resets and window focus regain resync held movement/crouch keys. Q/E/jump are
  press-only, so they still need a fresh press after those transitions.
- `pygame.key.stop_text_input()` runs at startup; if keys are still swallowed, switch the Windows IME
  to English before launching the sandbox.

There is intentionally no pytest suite and no file logging in this sandbox; failures are reported in
the debug panel and through the smoke test.
