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
It then runs Nyra against the dummy (wave/thrust damage, mark stacking and detonation, Q slash
hitbox/FX, pass-through dash, cooldowns, per-target marks, lock-on) and Veno-Spider against Lina
(bite, poison stacking, stun web, hover ascent/descent, V/C/X slots, win). It also checks that each
Veno keeps independent skill cooldowns and that the 3-body group wins only when all are dead, and
checks `missing_frames == 0` for Lina, Nyra, Veno and Warrior. It checks the projectile VFX dispatch
(`q_cast_fx_ok`, `q_impact_fx_ok`, `q_normal_color_ok`, `q_flame_color_ok`, `veno_poison_cast_ok`,
`veno_poison_impact_ok`, `veno_web_cast_ok`, `veno_web_impact_ok`, `veno_bite_hit_fx_ok`), poison
settlement cadence (`poison_interval_ok`, `poison_tint_ok`), web collision radius
(`veno_web_radius_ok`), asset presence
(`lina_q_fx_missing`, `veno_vfx_missing`) and effect cleanup (`fx_cleanup_ok`).

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
| Left mouse | Sword wave (1.0×atk; 5-frame wave animation, 0.30s; adds 1 mark; no FX) |
| Right mouse | Thrust (1.2×basic + 1.3×extra; 5-frame, 0.40s; larger range; adds 1 mark) |
| Q | Sword slash (1.5×atk, 8s cooldown; 6-frame slash animation + blue slash FX; adds 1 mark; super armor during the slash) |
| E | Pass-through dash thrust (1.5×basic + 1.8×extra, 15s cooldown; ~330px dash; super armor during the dash) |

Nyra has no energy bar. Instead, LMB/RMB/Q hits stack marks on the enemy (max 3); the 4th LMB/RMB/Q
hit detonates them for `1.8×atk + 10% target max HP` and leaves 1 mark. E neither adds nor detonates
marks. Marks are stored on each target, so every Veno in a group keeps an independent stack and
detonates on its own; the 3 pips are drawn above each living enemy, and the burst ring plays on the
detonated target.

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

The Veno-Spider 3-body group is the default enemy. Press F7 to cycle the enemy roster
(Veno-Spider → training Dummy → Warrior → back); `[` / `]` cycle the playable character roster
(Lina ↔ Nyra). A switch performs a full
match reset and leaves the enemy AI off for manual testing. The AI also starts off on launch and after
any reset (F5 reload, F9, R); press F8 to turn it on. The dummy has
no AI and is useful for isolated tests; Warrior and Veno are the full 1v1 opponents. After VICTORY or
DEFEATED, press R to restart; F9 resets at any time. Warrior's dash knock-up draws a cyan vortex at
the target's feet; it follows the body, stays visible at a minimum strength through the 1.5s window,
then vanishes. Extended knock-up gravity keeps the target airborne for that window, so landing and
control return together.

Veno-Spider spawns as a group of three 50 HP enemies (one ground + two hovering by default). It bites at close range,
spits a straight-line poison glob (3% max HP/s for 3s, same-source hits extend the duration) and
shoots a stunning web (1s). It webs itself up to a variable hover height (base 220px, 140–300px
range) when the player is outside bite range and a ranged skill is ready; while airborne it
prioritizes venom/web, then descends to bite. Each spider tracks its own bite (1s), poison (5s) and
web (8s) cooldowns, so one Veno attacking never delays the others. Its visual hover is a hanging
pose with a draw-only web strand above it.

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
- Lina: 45 normal + 41 flame-form frames (86); damage follows the docx formulas (punch 20, kick 24, Q 20 at the starting stats). Q launches a fist-sized static sprite projectile: a pixel-art teal glass ball (white rim/highlights, short trail) drawn slightly above the fist lane in normal form, orange/red fire in flame form, with matching teal/orange cast and impact colors. Nyra: 29 minimal frames (idle 2, walk 2, jump 2, crouch 1, hurt 1, KO 2, slash 6 (Q), thrust 5, wave 5 (LMB), dash 3) on a 384x384 canvas with pivot (192,372), body 214. Warrior: 36 frames (idle 4, walk 6, jump 2, axe_slash 6, axe_throw 7, dash 5, hurt 2, KO 4) on a 384x384 canvas with pivot (192,372). Veno-Spider: 20 minimal frames (idle 2, walk 2, hover 2, jump 2, hurt 1, KO 2, bite/poison/web 3 each) on a 320x320 canvas with pivot (160,308), body 150.
- Nyra: HP 100, basic ATK 20; LMB wave 20 (0.30s), RMB thrust 24, Q slash 30 (8s), E dash 30 (15s). LMB uses a 5-frame wave animation (0.06s each) and cast-anchored hitboxes (no projectile): the RMB thrust box `[28,-165,130,48]` during t=0–0.06s and 0.24–0.30s, and the extended `[28,-212,162,123]` (reach 190) during t=0.06–0.24s; it adds 1 mark and has no FX. Q uses a 6-frame slash animation (0.40s) and cast-anchored hitboxes: the thrust box during t=0–0.12s and 0.30–0.40s, and the extended box during t=0.12–0.30s; it adds 1 mark, has super armor for its 0.40s, and plays the separate six-frame blue slash FX (visible frames 02–04 align with the character's 02–04 frames and overlap the extended window). RMB uses a 5-frame thrust animation (0.08s each, 0.40s) with a single hitbox `[28,-165,130,48]` active t=0.16–0.24s. Melee hits add 1 mark (max 3); the 4th melee hit detonates for `1.8×atk + 10% target max HP` and leaves 1 mark. E dashes at 1100px/s for t=0.06–0.36s (~330px) with super armor during the dash, passes through the enemy but respects walls/blocks, and pushes the enemy out at the end.
- Warrior AI approaches, jumps blocks, attacks with a telegraphed axe slash, has startup/active super armor, and supports win/loss/restart. Its damage is `atk`-scaled: axe slash 24, dash 30 + 1.5s knock-up, axe throw 24 per pass. The dash knock-up uses a reduced knock-up gravity so the target stays airborne for the 1.5s window, and draws a procedural cyan vortex at the launched fighter's feet for the full status duration.
- Veno-Spider: half-size body (160×160 runtime frames, 75×75 hurtbox, `stage_body_width` 70, bite range 75); HP 50, ATK 10; bite 15, poison glob 8 + 3% max HP/s for 3s, web 10 + 1s stun. Cooldowns are bite 1s, poison 5s and web 8s, tracked independently by each spider. Selecting Veno spawns a group of **3** (default 1 ground + 2 hovering; `roster.json` `count`/`spawn_offsets`/`spawn_modes`); the player's attacks and projectiles can hit any living Veno and the match is won when all 3 die. Nyra's marks stack independently on each Veno. Same-source poison reapplication adds the new duration to the remaining time (2s + 3s = 5s); different sources — including different Venos — keep independent damage instances. Poison settles every 0.5s. It hovers on a web at 140–300px (base 220), prioritizes bite on the ground and venom/web while airborne, and uses a draw-only curved web strand. Poison is dark green (layered glob, cast mist and splash) and a poisoned body flashes green/purple every 0.18s; web uses the approved web_05 crop at 64px with a 150–170px impact decal, a procedural silk trail and collision radius 30; a connected bite adds a short green arc.
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
