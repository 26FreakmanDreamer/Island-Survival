# Island Survival — Lina & Warrior Combat Sandbox

A 2D side-view combat sandbox for testing Lina Seabright against the Warrior before the full survival game is built.
Python 3.14 + pygame-ce 2.5.8; all gameplay tuning is hot-reloadable JSON.

## Run

Double-click `run.bat`. On the first run it creates `.venv`, installs the dependencies, and starts the game.
For a headless launch check:

```bat
run.bat --smoke-test
```

The smoke test first repeats Lina's punch/kick/Q/block/flame checks against the training dummy, then
switches to Warrior and verifies hurt, startup super armor, recovery interruption, axe damage/KO,
dash knock-up, throw out-and-back damage, the inter-skill gap, win/loss, AI approach and block jump,
body separation/facing stability (no enemy flip across a block; capped separation slide), interrupted-transform visibility, flame revert, roster switching,
the data-driven V/C/X/Z skill slots, and the F7 plus `[` / `]` roster switches.

## Controls

| Input | Action |
|---|---|
| A / D | Move left / right |
| W / Space | Jump |
| S / Shift | Crouch |
| Left mouse | Punch (alternating hands) |
| Right mouse | Kick (alternating legs) |
| Middle mouse | Toggle attack lock-on (default off) |
| Q | Air-current punch (8s cooldown, starts ready) |
| E | Flame form (100 energy, 20s cooldown, starts ready, 10s duration) |
| Esc | Pause menu (Resume / Restart / Quit) |

Attacks pressed during an attack are queued (one slot, newest wins) and start when the attack ends;
E cancels attack recovery. Presses made during hitstun or a control lock (including knock-up) also
wait in that slot and execute when control returns. Held movement/crouch keys resync after pause,
scene reset and focus regain.
Attack direction follows Lina's facing: tap A/D to turn left/right; punches, kicks and Q all aim that way.
Middle mouse toggles attack lock-on: while on, each attack turns Lina toward the living enemy at
attack start. It defaults off and resets to off when the character or enemy is switched; F9 keeps the
current setting.
Q spawns at fist height relative to Lina's feet, so its trajectory rises when she stands on a block.
Walking and attack lunges stop at block edges; jump onto a block to cross it.

## Combat modes

Warrior is the default enemy. Press F7 to cycle the enemy roster (Warrior → training Dummy → back);
`[` / `]` cycle the playable character roster (currently only Lina). Switching performs a full match
reset and leaves the enemy AI off for manual testing; press F8 to turn it back on. The dummy has no AI
and is useful for isolated Lina tests; Warrior is the full 1v1 opponent. After VICTORY or DEFEATED,
press R to restart; F9 resets at any time. Warrior's dash knock-up draws a cyan vortex at the
target's feet; it follows the body, stays visible at a minimum strength through the 1.5s window,
then vanishes. Extended knock-up gravity keeps the target airborne for that window, so landing and
control return together.

## Debug controls

| Key | Action |
|---|---|
| F1 | Toggle hitbox/hurtbox, lane, wall and block overlay |
| F2 | Toggle the live debug panel |
| F3 | Pause / resume |
| F4 | Step one simulation tick (pauses) |
| F5 | Hot-reload all JSON and soft-reset the scene |
| F6 | Cycle time scale 0.25x / 0.5x / 1x / 2x |
| F7 | Cycle the enemy roster (Warrior → training Dummy → …) |
| [ / ] | Cycle the playable character roster (currently Lina only) |
| F8 | Toggle enemy AI when present, otherwise invincibility |
| F9 | Full scene reset |
| F10 | Flame-form demo (energy + forced transform) |
| F11 | Cycle a forced status on the current enemy |
| F12 | Damage Lina / show KO |
| V / C / X / Z | Trigger the enemy's skill slots 1 / 2 / 3 / 4 (undefined slots do nothing) |
| B | Toggle block collision and visibility |
| Arrow keys | Move the current enemy horizontally |
| PgUp / PgDn | Current enemy HP +/-100 |
| R | Restart after VICTORY / DEFEATED |

## Current scope

- One playable character (Lina) vs. the Warrior in a single arena; the training dummy remains available through F7. A `roster.json` registry drives character/enemy construction, but only Lina is installed as playable.
- Lina: 45 normal + 41 flame-form frames (86); damage follows the docx formulas (punch 20, kick 24, Q 20 at the starting stats). Warrior: 36 frames (idle 4, walk 6, jump 2, axe_slash 6, axe_throw 7, dash 5, hurt 2, KO 4) on a 384x384 canvas with pivot (192,372).
- Warrior AI approaches, jumps blocks, attacks with a telegraphed axe slash, has startup/active super armor, and supports win/loss/restart. Its damage is `atk`-scaled: axe slash 24, dash 30 + 1.5s knock-up, axe throw 24 per pass. The dash knock-up uses a reduced knock-up gravity so the target stays airborne for the 1.5s window, and draws a procedural cyan vortex at the launched fighter's feet for the full status duration.
- `V/C/X/Z` read the current enemy's four skill slots from data; undefined slots are safe no-ops and show `-` in F2.
- Frame data, hitboxes, cooldowns, damage and stage geometry are in `game/data/*.json`.
- Not included: daily loop, food/fullness, shop/gold, saves, audio, full HUD, additional playable characters, other enemies and their AI, packaging.
- No pytest suite or file logging; verification is through the sandbox, contact sheets and `--smoke-test`.

## Layout

```text
main.py                  entry point and fixed-step loop
game/                    runtime modules and data (including warrior.py)
game/data/               stats, attacks, animations, roster and debug geometry
assets/frames/lina/      normal frames + flame/<action> frames
assets/frames/warrior/   Warrior frames on the 384x384 canvas
assets/generated/        raw candidates, staged frames, contact sheets
tools/                   collect_frames.py, import_frames.py, contact_sheet.py
docs/                    design decisions, asset pipeline, debugging guide
Image/                   canonical character/enemy art (never overwritten)
PLAN.md                  original approved implementation plan
```

See [docs/DESIGN_DECISIONS.md](docs/DESIGN_DECISIONS.md), [docs/ASSET_PIPELINE.md](docs/ASSET_PIPELINE.md) and [docs/DEBUG.md](docs/DEBUG.md).
