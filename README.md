# Island Survival — Lina / Nyra vs Warrior / Veno Combat Sandbox

A 2D side-view combat sandbox for testing Lina Seabright and Nyra Steel against the Warrior and Veno-Spider before the full survival game is built.
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
It then runs Nyra against the dummy (slash/thrust damage, mark stacking and detonation, Q wave
hitbox/FX, pass-through dash, cooldowns, lock-on) and Veno-Spider against Lina (bite, poison stacking, stun web,
hover ascent/descent, V/C/X slots, win), and checks `missing_frames == 0` for Lina, Nyra, Veno and
Warrior.

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

Lina uses the table above. Nyra Steel uses the same movement, crouch and lock-on controls with:

| Input | Action |
|---|---|
| Left mouse | Sword slash (1.0×atk; adds 1 mark) |
| Right mouse | Thrust (1.2×basic + 1.3×extra; larger range; adds 1 mark) |
| Q | Sword-wave slash (1.5×atk, 8s cooldown; per-frame forward hitboxes + blue sword FX) |
| E | Pass-through dash thrust (1.5×basic + 1.8×extra, 15s cooldown) |

Nyra has no energy bar. Instead, melee hits stack marks on the enemy (max 3); the 4th melee hit
detonates them for `1.8×atk + 10% target max HP` and leaves 1 mark. Q/E neither add nor detonate
marks. The 3 marks are drawn above the enemy's head; the burst ring plays on detonation.

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

Warrior is the default enemy. Press F7 to cycle the enemy roster (Warrior → Veno-Spider → training
Dummy → back); `[` / `]` cycle the playable character roster (Lina ↔ Nyra). Switching performs a full
match reset and leaves the enemy AI off for manual testing; press F8 to turn it back on. The dummy has
no AI and is useful for isolated tests; Warrior and Veno are the full 1v1 opponents. After VICTORY or
DEFEATED, press R to restart; F9 resets at any time. Warrior's dash knock-up draws a cyan vortex at
the target's feet; it follows the body, stays visible at a minimum strength through the 1.5s window,
then vanishes. Extended knock-up gravity keeps the target airborne for that window, so landing and
control return together.

Veno-Spider is a single 50 HP enemy (the docx `n=3` group is future work). It bites at close range,
spits a straight-line poison glob (3% max HP/s for 3s, same-source hits extend the duration) and
shoots a stunning web (1s). It webs itself up to a variable hover height (base 220px, 140–300px
range) when the player is outside bite range and a ranged skill is ready; while airborne it
prioritizes venom/web, then descends to bite. Its visual hover is a hanging pose with a draw-only
web strand above it.

## Debug controls

| Key | Action |
|---|---|
| F1 | Toggle hitbox/hurtbox, lane, wall and block overlay |
| F2 | Toggle the live debug panel |
| F3 | Pause / resume |
| F4 | Step one simulation tick (pauses) |
| F5 | Hot-reload all JSON and soft-reset the scene |
| F6 | Cycle time scale 0.25x / 0.5x / 1x / 2x |
| F7 | Cycle the enemy roster (Warrior → Veno-Spider → training Dummy → …) |
| [ / ] | Cycle the playable character roster (Lina ↔ Nyra) |
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

- Two playable characters (Lina, Nyra) vs. Warrior or Veno-Spider in a single arena; the training Dummy remains available through F7. A `roster.json` registry drives character/enemy construction.
- Lina: 45 normal + 41 flame-form frames (86); damage follows the docx formulas (punch 20, kick 24, Q 20 at the starting stats). Nyra: 25 minimal frames (idle 2, walk 2, jump 2, crouch 1, hurt 1, KO 2, slash 6, thrust 3, wave 3, dash 3) on a 384x384 canvas with pivot (192,372), body 214. Warrior: 36 frames (idle 4, walk 6, jump 2, axe_slash 6, axe_throw 7, dash 5, hurt 2, KO 4) on a 384x384 canvas with pivot (192,372). Veno-Spider: 20 minimal frames (idle 2, walk 2, hover 2, jump 2, hurt 1, KO 2, bite/poison/web 3 each) on a 320x320 canvas with pivot (160,308), body 150.
- Nyra: HP 100, basic ATK 20; LMB slash 20, RMB thrust 24, Q wave 30 (8s), E dash 30 (15s). Q uses cast-anchored per-frame hitboxes for the whole 0.40s (no projectile): the RMB thrust box `[28,-165,130,48]` during the blank lead-in/tail (t=0–0.12s and 0.30–0.40s), and the extended `[28,-212,162,123]` (reach 190) during effect frames 02–04 (t=0.12–0.30s). Its separate six-frame blue sword FX appears on effect frame 02, peaks on 03, fades in place on 04, and disappears on 05. Melee hits add 1 mark (max 3); the 4th melee hit detonates for `1.8×atk + 10% target max HP` and leaves 1 mark. E passes through the enemy but respects walls/blocks and pushes the enemy out at the end.
- Warrior AI approaches, jumps blocks, attacks with a telegraphed axe slash, has startup/active super armor, and supports win/loss/restart. Its damage is `atk`-scaled: axe slash 24, dash 30 + 1.5s knock-up, axe throw 24 per pass. The dash knock-up uses a reduced knock-up gravity so the target stays airborne for the 1.5s window, and draws a procedural cyan vortex at the launched fighter's feet for the full status duration.
- Veno-Spider: HP 50, ATK 10; bite 15, poison glob 8 + 3% max HP/s for 3s (same-source extension), web 10 + 1s stun. It hovers on a web at 140–300px (base 220), prioritizes bite on the ground and venom/web while airborne, and uses a draw-only web strand. Single spawn only; the docx `n=3` group is future work.
- `V/C/X/Z` read the current enemy's four skill slots from data; undefined slots are safe no-ops and show `-` in F2.
- Frame data, hitboxes, cooldowns, damage and stage geometry are in `game/data/*.json`.
- Not included: daily loop, food/fullness, shop/gold, saves, audio, full HUD, multi-enemy encounters, other playable characters/enemies, packaging.
- No pytest suite or file logging; verification is through the sandbox, contact sheets and `--smoke-test`.

## Layout

```text
main.py                  entry point and fixed-step loop
game/                    runtime modules and data (including lina.py, nyra.py, warrior.py, veno.py)
game/data/               stats, attacks, animations, roster and debug geometry
assets/frames/lina/      normal frames + flame/<action> frames
assets/frames/nyra/      Nyra frames on the 384x384 canvas
assets/frames/warrior/   Warrior frames on the 384x384 canvas
assets/frames/veno/      Veno-Spider frames on the 320x320 canvas
assets/generated/        raw candidates, staged frames, contact sheets
tools/                   collect_frames.py, import_frames.py, contact_sheet.py
docs/                    design decisions, asset pipeline, debugging guide
Image/                   canonical character/enemy art (never overwritten)
PLAN.md                  original approved implementation plan
```

See [docs/DESIGN_DECISIONS.md](docs/DESIGN_DECISIONS.md), [docs/ASSET_PIPELINE.md](docs/ASSET_PIPELINE.md) and [docs/DEBUG.md](docs/DEBUG.md).
