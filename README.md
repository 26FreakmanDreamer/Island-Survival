# Island Survival — Lina & Warrior Combat Sandbox

A 2D side-view combat sandbox for testing Lina Seabright against the Warrior before the full survival game is built.
Python 3.14 + pygame-ce 2.5.8; all gameplay tuning is hot-reloadable JSON.

## Run

Double-click `run.bat`. On the first run it creates `.venv`, installs the dependencies, and starts the game.
For a headless launch check:

```bat
run.bat --smoke-test
```

The smoke test first repeats Lina's punch/queue/block/Q/flame checks against the training dummy, then switches to Warrior and verifies hurt, startup super armor, recovery interruption, axe damage/KO, dash/throw, the inter-skill gap, win/loss, AI approach and block jump, body separation/facing stability, interrupted-transform visibility, flame revert, and the F7 mode switch.

## Controls

| Input | Action |
|---|---|
| A / D | Move left / right |
| W / Space | Jump |
| S / Shift | Crouch |
| Left mouse | Punch (alternating hands) |
| Right mouse | Kick (alternating legs) |
| Q | Air-current punch (8s cooldown, starts ready) |
| E | Flame form (100 energy, 20s cooldown, starts ready, 10s duration) |
| Esc | Pause menu (Resume / Restart / Quit) |

Attacks pressed during an attack are queued (one slot, newest wins) and start when the attack ends;
E cancels attack recovery. Held movement/crouch keys resync after pause, scene reset and focus regain.
Attack direction follows Lina's facing: tap A/D to turn left/right; punches, kicks and Q all aim that way.
Q spawns at fist height relative to Lina's feet, so its trajectory rises when she stands on a block.
Walking and attack lunges stop at block edges; jump onto a block to cross it.

## Combat modes

Warrior is the default enemy. Press F7 to switch to the training dummy and back. The dummy has no AI
and is useful for isolated Lina tests; Warrior is the full 1v1 opponent. After VICTORY or DEFEATED,
press R to restart; F9 resets at any time.

## Debug controls

| Key | Action |
|---|---|
| F1 | Toggle hitbox/hurtbox, lane, wall and block overlay |
| F2 | Toggle the live debug panel |
| F3 | Pause / resume |
| F4 | Step one simulation tick (pauses) |
| F5 | Hot-reload all JSON and soft-reset the scene |
| F6 | Cycle time scale 0.25x / 0.5x / 1x / 2x |
| F7 | Switch enemy mode: Warrior <-> training Dummy |
| F8 | Warrior mode: toggle AI; Dummy mode: toggle invincibility |
| F9 | Full scene reset |
| F10 | Flame-form demo (energy + forced transform) |
| F11 | Cycle a forced status on the current enemy |
| F12 | Damage Lina / show KO |
| V | Force the Warrior's axe attack |
| B | Toggle block collision and visibility |
| Arrow keys | Move the current enemy horizontally |
| PgUp / PgDn | Current enemy HP +/-100 |
| R | Restart after VICTORY / DEFEATED |

## Current scope

- One playable character (Lina) vs. the Warrior in a single arena; the training dummy remains available through F7.
- Lina: 45 normal + 41 flame-form frames (86). Warrior: 24 frames (idle 4, walk 6, jump 2, axe_slash 6, hurt 2, KO 4) on a 384x384 canvas with pivot (192,372).
- Warrior AI approaches, jumps blocks, attacks with a telegraphed axe slash, has startup/active super armor, and supports win/loss/restart.
- Frame data, hitboxes, cooldowns, damage and stage geometry are in `game/data/*.json`.
- Not included: daily loop, food/fullness, shop/gold, saves, character select, audio, full HUD, other characters, other enemies and their AI, packaging.
- No pytest suite or file logging; verification is through the sandbox, contact sheets and `--smoke-test`.

## Layout

```text
main.py                  entry point and fixed-step loop
game/                    runtime modules and data (including warrior.py)
game/data/               stats, attacks, animations, debug geometry
assets/frames/lina/      normal frames + flame/<action> frames
assets/frames/warrior/   Warrior frames on the 384x384 canvas
assets/generated/        raw candidates, staged frames, contact sheets
tools/                   collect_frames.py, import_frames.py, contact_sheet.py
docs/                    design decisions, asset pipeline, debugging guide
Image/                   canonical character/enemy art (never overwritten)
PLAN.md                  original approved implementation plan
```

See [docs/DESIGN_DECISIONS.md](docs/DESIGN_DECISIONS.md), [docs/ASSET_PIPELINE.md](docs/ASSET_PIPELINE.md) and [docs/DEBUG.md](docs/DEBUG.md).
