# Island Survival — Lina Seabright Combat Sandbox

A 2D side-view combat sandbox for testing Lina Seabright before the full survival game is built.
Python 3.14 + pygame-ce 2.5.8; all gameplay tuning is hot-reloadable JSON.

## Run

Double-click `run.bat`. On the first run it creates `.venv`, installs the dependencies, and starts the game.
For a headless launch check:

```bat
run.bat --smoke-test
```

The smoke test verifies that a punch deals damage and grants energy, and that E switches to the flame-form animation set.

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

## Debug controls

| Key | Action |
|---|---|
| F1 | Toggle hitbox/hurtbox, lane, wall and block overlay |
| F2 | Toggle the live debug panel |
| F3 | Pause / resume |
| F4 | Step one simulation tick (pauses) |
| F5 | Hot-reload all JSON and soft-reset the scene |
| F6 | Cycle time scale 0.25x / 0.5x / 1x / 2x |
| F7 | Toggle dummy invincibility |
| F8 | Reset dummy HP/position |
| F9 | Full scene reset |
| F10 | Flame-form demo (energy + forced transform) |
| F11 | Cycle a forced status on the dummy |
| F12 | Damage Lina / show KO |
| Arrow keys | Move the dummy horizontally |
| PgUp / PgDn | Dummy HP +/-100 |

## Current scope

- One playable character (Lina) vs. a training dummy in a single arena.
- 45 normal animation frames and 33 flame-form animation frames (78 total).
- Frame data, hitboxes, cooldowns, damage and stage geometry are in `game/data/*.json`.
- Not included: daily loop, food/fullness, shop/gold, saves, character select, audio, full HUD, other characters, enemy AI, packaging.
- No pytest suite or file logging; verification is through the sandbox, contact sheets and `--smoke-test`.

## Layout

```text
main.py                  entry point and fixed-step loop
game/                    runtime modules and data
game/data/               stats, attacks, animations, debug geometry
assets/frames/lina/      normal frames + flame/<action> frames
assets/generated/        raw candidates, staged frames, contact sheets
tools/                   collect_frames.py, import_frames.py, contact_sheet.py
docs/                    design decisions, asset pipeline, debugging guide
Image/                   canonical character/enemy art (never overwritten)
PLAN.md                  original approved implementation plan
```

See [docs/DESIGN_DECISIONS.md](docs/DESIGN_DECISIONS.md), [docs/ASSET_PIPELINE.md](docs/ASSET_PIPELINE.md) and [docs/DEBUG.md](docs/DEBUG.md).
