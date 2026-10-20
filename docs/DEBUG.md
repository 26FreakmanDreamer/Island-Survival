# Debugging the sandbox

## Launch checks

```bat
run.bat
run.bat --smoke-test
```

`--smoke-test` runs a headless 60Hz simulation, verifies a punch deals damage and grants energy, then
verifies E finishes its transform and switches the animation player to the flame clip set. It prints
a `SMOKE ...` line and exits non-zero on failure. It uses SDL's dummy video driver.

## Overlay and panel

- **F1 overlay**: hitboxes (red), hurtboxes (green), pivot/facing markers, projectile lane lines
  measured upward from Lina's feet (high/fist/mid/low), wall/block bounds and entity state labels.
  The green box is the combat hurtbox; grounded stage movement uses a wider invisible body
  (`stage_body_width`), so Lina stops with her boots short of a block before the green box touches it.
- **F2 panel**: FPS/tick/sim time, Lina state/HP/energy/Q/E cooldowns, flame timer/hits/next bonus,
  current animation clip/frame, attack clock/queued action, hitstun/knockback, positions/facing, Lina and
  dummy statuses, last hit, input history/buffer, missing frames, last reload status/error.

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
| F7 | Dummy invincible toggle |
| F8 | Reset dummy HP/position |
| F9 | Full scene reset |
| F10 | Fill energy and force the flame transform |
| F11 | Cycle forced status on the dummy (burn, poison, stun, freeze, slow, super armor, damage reduction) |
| F12 | Damage Lina by 10, then 999 when low; shows hurt/KO |
| Arrow keys | Move dummy -20/+20px |
| PgUp/PgDn | Dummy HP +/-100 |

## Debugging workflow

1. Use F1 to confirm hit/hurt boxes and lane positions.
2. Use F2 to inspect state, clip/frame, cooldown, energy, flame tiers and status timers.
3. Use F3/F4 to freeze a frame; F6 to slow the simulation for timing checks.
4. Use F7 to isolate damage from dummy death; F8/F9 to reset a scenario.
5. Use F10 to test the full flame-form animation set and flame bonus tiers.
6. Use F11 to inspect status visuals and timers; F12 to test Lina's hurt/KO frames.
7. Edit `game/data/*.json` and press F5 to tune values without restarting.
8. If a frame looks wrong, replace the PNG under `assets/frames/lina/` and press F5; the frame cache
   keys on path + mtime.

## Input checks

- An action pressed during an attack is queued, not dropped. The F2 `ATTACK` line shows
  `queue=<action>` until it executes; playback starts when the attack ends (E cancels recovery).
- Pause/resume, F5/F9 resets and window focus regain resync held movement/crouch keys. Q/E/jump are
  press-only, so they still need a fresh press after those transitions.
- `pygame.key.stop_text_input()` runs at startup; if keys are still swallowed, switch the Windows IME
  to English before launching the sandbox.

There is intentionally no pytest suite and no file logging in the first milestone; failures are
reported in the debug panel and through the smoke test.
