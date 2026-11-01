# Island Survival — Lina / Nyra / Rhea vs Warrior / Veno / Bat / Creepy Shooter Combat Sandbox

A 2D side-view combat sandbox for testing Lina Seabright, Nyra Steel and Rhea Thorn against the Warrior, Veno-Spider, Bat and Creepy Shooter before the full survival game is built.
Python 3.14 + pygame-ce 2.5.8; all gameplay tuning is hot-reloadable JSON.

## Run

Double-click `run.bat`. On the first run it creates `.venv`, installs the dependencies, and starts the game.
For a headless launch check:

```bat
run.bat --smoke-test
```

The smoke test first repeats Lina's punch/kick/Q/block/flame checks against the training dummy, then
switches to Warrior and verifies hurt, startup super armor, recovery interruption, axe damage/KO,
dash knock-up, throw out-and-back damage, the inter-skill gap, win/loss, AI approach and barrier jump,
body separation/facing stability (no enemy flip across a barrier; capped separation slide), interrupted-transform visibility, flame revert, roster switching,
the data-driven V/C/X/Z skill slots, and the F7 plus `[` / `]` roster switches.
It then runs Nyra against the dummy (wave/thrust damage, mark stacking and detonation, Q slash
hitbox/FX, pass-through dash, cooldowns, per-target marks, lock-on), Rhea against the dummy/Creepy
Shooter/Warrior (alternating LMB clips, +1s poison extension, steel/poison shuriken damage, 900px
range and point-blank checks, Q's 8% max-HP bonus and 5s/3%-per-second poison, E's two hit groups,
return to `cast_x`, full armor and 15% poison bonus), and Veno-Spider against Lina
(bite, poison stacking, stun web, hover ascent/descent, V/C/X slots, win). It also checks that each
Veno keeps independent skill cooldowns and that the 3-body group wins only when all are dead, and
checks `missing_frames == 0` for Lina, Nyra, Rhea, Veno, Warrior, Bat and Creepy Shooter, including
Rhea's six shuriken FX. The Bat phase
verifies the five-Bat group (selected with F7; the startup default is Creepy Shooter), five
spawn/cruise heights, free flight (40–420), dive 10, V/C/X/Z slots, sonic 12 + 1s stun,
out/return/wall/barrier/platform bounce, the 0.65s cast lock, hurt/stun staying airborne, KO
landing, and the five-body group spawn/independent cooldowns/WIN.
The Creepy Shooter phase checks the dedicated mirrored stage (long platform 601–1080, short
170–484, only the right ground barrier, spawn 1000,220), HP/ATK/slots, the straight shot
(30, cooldown ~1s, block collision), the
1s lock wind-up and three-frame reticle, the homing bolt (penetrates platforms, 20 once, 8s
lifetime), the back-roll (140px, 24 damage, no i-frames, cooldown 10, falling off a platform edge),
the platform jump shot (surfaces 220/268, right takeoff 1136, 24 downward, no-platform rejection),
barrier hopping, AI priority, V/C/X/Z mapping, WIN, cleanup, stage switching, ladder hits
(`creepy_ladder_hit_mid_ok`, `creepy_ladder_hit_platform_ok`, `creepy_ladder_hit_top_ok`), and
`creepy_missing_frames == 0` / `creepy_fx_missing == 0`.
The scene phase checks platform landing/side/underside (`platform_land_ok`, `platform_side_ok`,
`platform_bottom_bump_ok`), B toggling platforms (`platform_toggle_ok`), ladder up/down/Shift/jump-off
semantics (`ladder_climb_ok`, `ladder_down_ok`, `ladder_shift_no_down_ok`), the early midpoint
mount (`ladder_mount_early_ok`), jump-off platform-overlap immunity (`ladder_jump_overlap_ok`), the
two-frame back-view climb clips (`lina_climb_anim_ok`, `lina_climb_facing_ok`,
`lina_flame_climb_anim_ok`), ladders not blocking projectiles (`ladder_no_block_ok`), Nyra
climbing (`nyra_climb_ok`, `nyra_climb_anim_ok`), Rhea climbing (`rhea_climb_ok`), spawn clearance
(`platform_spawn_clear_ok`), the `penetrates_blocks` flag (`penetration_flag_ok`) and the default
enemy (`default_enemy_ok`).
It checks the projectile VFX dispatch
(`q_cast_fx_ok`, `q_impact_fx_ok`, `q_normal_color_ok`, `q_flame_color_ok`, `veno_poison_cast_ok`,
`veno_poison_impact_ok`, `veno_web_cast_ok`, `veno_web_impact_ok`, `veno_bite_hit_fx_ok`,
`bat_dive_hit_fx_ok`, `bat_sonic_cast_ok`, `bat_sonic_impact_ok`, `bat_sonic_hitbox_ok`), poison
settlement cadence (`poison_interval_ok`, `poison_tint_ok`), web collision radius
(`veno_web_radius_ok`), asset presence
(`lina_q_fx_missing`, `veno_vfx_missing`) and effect cleanup (`fx_cleanup_ok`).

## Controls

| Input | Action |
|---|---|
| A / D | Move left / right |
| W | Climb up while a ladder is in reach; otherwise jump |
| Space | Jump; while climbing, jump off the ladder |
| S | Crouch; while climbing, climb down |
| Shift | Crouch only (does not climb) |
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

Rhea Thorn uses the same movement, crouch and lock-on controls with:

| Input | Action |
|---|---|
| Left mouse | Shuriken slash (20; right/left hand alternating; 60 knockback; extends an existing `rhea_poison` by 1s) |
| Right mouse | Steel shuriken throw (24; mid lane, speed 850, range 900, point-blank body check; extends `rhea_poison` by 1s) |
| Q | Poison shuriken (24 + 8% of the target's max HP; applies 5s of 3% max HP/s poison; 8s cooldown; same-source re-hit +5s) |
| E | Dash-return (1.00s; outbound ~594px at 1100px/s, return to `cast_x` at 1500px/s; 14 + 14 damage; first segment +15% max HP on a poisoned target; full 0–1.00s armor; 15s cooldown) |

Rhea has no energy bar. Her passive only extends an existing `rhea_poison` by 1s on an LMB/RMB hit;
it never creates poison, affects Veno's poison, or triggers from Q/E, and extends at most once per
target per attack with no duration cap. LMB starts with the right hand and alternates on each
successful start; RMB/Q/E never change the alternation. RMB/Q are single-hit stars that die on a
hit, range end, wall or solid block; a body-adjacent check makes point-blank throws connect even
when the target is tightly overlapping or slightly crossed. Q does not trigger the +1s passive.

Attacks pressed during an attack are queued (one slot, newest wins) and start when the attack ends;
E cancels attack recovery. Presses made during hitstun or a control lock (including knock-up) also
wait in that slot and execute when control returns. Held movement/crouch keys resync after pause,
scene reset and focus regain.
Attack direction follows the active character's facing: tap A/D to turn left/right; attacks aim that way.
Middle mouse toggles attack lock-on: while on, each attack turns the character toward the living enemy
at attack start. It defaults off and resets to off when the character or enemy is switched; F9 keeps
the current setting.
Q spawns at fist height relative to Lina's feet, so its trajectory rises when she stands on a barrier or platform.
Barriers are solid obstacles. Platforms are full AABB solids: they block from the top, side and underside;
landing on the top requires the feet center to be within `land_margin` of the span. The outer platform edges
are inset from the arena walls so a character can walk off and fall; there is no fall damage. B toggles
barrier + platform drawing and collision; ladders stay visible and climbable. With B off, reaching a
ladder top holds the character on the ladder instead of mounting the platform.

Climbing: walk to a ladder and hold W to climb, S to descend, and Space to jump off. Climbing locks the
character to the ladder and ignores barriers/platforms. The climb art is a two-frame back-view clip:
frame 0 has the left hand high and right leg high, frame 1 the right hand high and left leg high,
0.20s per frame. Moving loops the clip (up 0→1→0, down 1→0→1); releasing W/S holds the current
frame. Climbing never horizontally flips the back view and restores the previous facing on exit.
Lina's normal and flame tables each have their own climb clip, Nyra has a dedicated clip with her
sword still sheathed diagonally across her back, and Rhea has a dedicated back-view clip with both
hands free and the two four-blade shuriken stowed on her back band. The draw scale is
character-specific around the feet pivot (Lina 1.2×, Nyra 1.1×, Rhea 1.1×); combat hurtboxes and
stage collision are unchanged.
A ladder with a top platform mounts early: once the feet reach the platform's vertical midpoint minus
6px, the character snaps to the platform surface and exits the climb; holding or re-pressing W around
that threshold completes the mount, and B-off keeps the old hold-at-top behavior.
Attacks, hits, stun and KO exit the climb; a ladder hit applies the normal knockback immediately. If
the feet are inside a platform rect at the hit, the character snaps to that platform's top and is
treated as grounded; otherwise they are knocked off and fall. A Space jump-off or a ladder fall
ignores platform side/underside collision until landing, so a platform behind the ladder cannot shove
the body sideways; platform-top landing still applies. There is no automatic re-grab after a hit.
Ladders have no collision and never block projectiles.

## Combat modes

The default enemy is a single **Creepy Shooter** (200 HP); the five-Bat group and the other enemies
are selectable with F7. Press F7 to cycle the enemy roster (Warrior → Veno-Spider ×3 → Bat ×5 →
Creepy Shooter → training Dummy → back); `[` / `]` cycle the playable character roster
(Lina ↔ Nyra ↔ Rhea). A switch performs a full
match reset and leaves the enemy AI off for manual testing. The AI also starts off on launch and after
any reset (F5 reload, F9, R); press F8 to turn it on. The dummy has
no AI and is useful for isolated tests; Warrior, Veno, Bat and Creepy Shooter are the full opponents. After VICTORY or
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

Five Bats spawn at different altitudes (180/320/240/380/280px) and keep those as cruise heights;
they fly over 40–420px with no gravity, but honour the arena walls and the solid barrier/platform AABBs.
The dive (10 damage, 2s) is deterministic and only fires when its hitbox can actually reach the
player from the current altitude; otherwise the Bat keeps flying. The sonic (12 damage + 1s stun,
10s) is the only randomly-timed skill: a random opening cooldown and a 50% cast gate desynchronise
the group, plus a 0.55s same-skill stagger. The wave flies in the mouth→player direction, bounces
off walls and barriers/platforms, and returns to the Bat's current position, dealing at most one hit.
Bats stay airborne through hurt/stun and only fall on KO. `roster.json` uses `count: 5`, five spawn
offsets and five spawn heights. The group is selected with F7; the startup default is a single
Creepy Shooter.

Creepy Shooter is a platform sniper with HP 200 / ATK 20 and four skills. It spawns on the right end
of the long platform (1000, 220) on a dedicated mirrored stage variant (long platform 601–1080,
short platform 170–484, only the right ground barrier at 790 after the left one was removed
2026-11-01, mirrored ladders); selecting it with F7 or at startup swaps the stage, and B still
toggles blocks. Its shot is strictly horizontal at the
shooter's mid lane and is blocked by barriers/platforms (30 damage, 1s cooldown); standing on the
long platform therefore cannot hit a ground player with skill 1. The homing bolt is the cross-level
answer: a 1s interruptible wind-up draws a three-frame lock reticle on the player (0.30/0.40/0.30s,
red dot in the middle frame), then a violet bolt homes without limit, penetrates blocks and
platforms, deals 20 once, and survives the shooter's KO (8s cooldown, 8s lifetime). Back-roll fires
when the player is within 180px: it rolls 140px backward over 0.28s with no i-frames, fires at
t=0.30 for 24, and falls off a platform edge instead of being clamped (10s cooldown). Jump shot
walks to a valid takeoff outside a reachable platform, jumps onto the 220 or 268 surface, and fires
downward for 24 inside a ±45° cone (10s cooldown); without a platform `force_attack` rejects it.
Bullets leave the measured muzzle (skill 1 at 163px high / 129px forward), not the waist, and the
AI hops 90px ground barriers with a stronger jump (`jump_v×1.15`, `walk×2.0` horizontal) instead of
stalling. Skill 2 is preferred when the line is blocked, the level differs by more than 60px, or
skill 1 is on cooldown.

## Debug controls

| Key | Action |
|---|---|
| F1 | Toggle hitbox/hurtbox, lane, wall, barrier, platform and ladder overlay |
| F2 | Toggle the live debug panel |
| F3 | Pause / resume |
| F4 | Step one simulation tick (pauses) |
| F5 | Hot-reload all JSON and soft-reset the scene |
| F6 | Cycle time scale 0.25x / 0.5x / 1x / 2x |
| F7 | Cycle the enemy roster (Warrior → Veno-Spider ×3 → Bat ×5 → Creepy Shooter → training Dummy → …) |
| [ / ] | Cycle the playable character roster (Lina ↔ Nyra ↔ Rhea) |
| F8 | Toggle enemy AI when present, otherwise invincibility |
| F9 | Full scene reset |
| F10 | Flame-form demo (energy + forced transform) |
| F11 | Cycle a forced status on the current enemy |
| F12 | Damage the current player / show KO |
| V / C / X / Z | Trigger the enemy's skill slots 1 / 2 / 3 / 4 (undefined slots do nothing) |
| B | Toggle barrier + platform collision and visibility (ladders stay visible and climbable) |
| Arrow keys | Move the current enemy horizontally |
| PgUp / PgDn | Current enemy HP +/-100 |
| R | Restart after VICTORY / DEFEATED |

## Current scope

- Three playable characters (Lina, Nyra, Rhea) vs. Warrior, Veno-Spider, Bat or Creepy Shooter in a single arena; the training Dummy remains available through F7. A `roster.json` registry drives character/enemy construction. The current default enemy is Creepy Shooter; an enemy entry may name a `stage_variant` that replaces the stage when selected.
- Scene: `blocks` use `kind: barrier | platform`; barriers are solid obstacles, platforms are full AABB solids (top/side/underside), and `ladders` are separate non-solid climb triggers. Current default-stage layout: long platform x=170..649 at surface y=220, short platform x=796..1110 at surface y=268, long ladder x=508..572 (400px), medium ladder x=921..985 (352px, native 160px width), ground barriers x=400..490 and x=700..790; player spawn x=280, enemy spawn x=600. The Creepy Shooter variant mirrors the platforms/ladders: long platform x=601..1080, short platform x=170..484, ladders x=708..772 and x=295..359, only the right ground barrier x=790..880 (the left x=400..490 was removed 2026-11-01), Creepy spawn x=1000 at y=220. B toggles barriers/platforms; ladders stay visible and climbable. F1 shows the collision boxes; F2 shows counts and `CLIMB`. `penetrates_blocks` is false by default; only the Creepy Shooter homing bolt sets it true.
- Lina: 47 normal + 43 flame-form frames (90); both tables include the 2-frame back-view climb clip. Damage follows the docx formulas (punch 20, kick 24, Q 20 at the starting stats). Q launches a fist-sized static sprite projectile: a pixel-art teal glass ball (white rim/highlights, short trail) drawn slightly above the fist lane in normal form, orange/red fire in flame form, with matching teal/orange cast and impact colors. Nyra: 31 minimal frames (idle 2, walk 2, jump 2, crouch 1, hurt 1, KO 2, slash 6 (Q), thrust 5, wave 5 (LMB), dash 3, climb 2) on a 384x384 canvas with pivot (192,372), body 214. Warrior: 36 frames (idle 4, walk 6, jump 2, axe_slash 6, axe_throw 7, dash 5, hurt 2, KO 4) on a 384x384 canvas with pivot (192,372). Veno-Spider: 20 minimal frames (idle 2, walk 2, hover 2, jump 2, hurt 1, KO 2, bite/poison/web 3 each) on a 320x320 canvas with pivot (160,308), body 150. Creepy Shooter: 29 frames (idle 2, walk 4, crouch 1, jump 2, hurt 2, KO 2, shot 2, homing 4, roll 6, jump shot 4) on a 384x384 canvas with pivot (192,372), body 214 (the roll set is imported at 0.9×); hurtbox 56×210 standing / 56×130 crouching, excluding the rifle.
- Climb animations: Lina normal/flame, Nyra and Rhea each have two dedicated back-view frames; Nyra's sword stays sheathed on her back and her hands stay free, while Rhea's two shuriken stay stowed on her back band. Lina draws at 1.2×; Nyra and Rhea at 1.1× around the feet pivot; the combat hurtbox and stage body are not scaled. A climb with a top platform mounts early at the platform midpoint minus 6px; ladder jump-offs and knock-offs ignore platform sides/underside until landing, and a hit whose feet are inside a platform snaps to its top. Enemy climb art/AI is not implemented yet.
- Rhea: HP 100, basic ATK 20; 33 frames (idle 2, walk 4, jump 2, crouch 1, hurt 2, KO 3, slash_r/l 3+3, throw 3, poison throw 3, dash 5, climb 2) on 384×384/pivot (192,372), plus six 64×64 star FX; climb draw scale 1.1×. LMB 20 with right/left alternation and 60 knockback; RMB steel star 24, 900 range, 850 speed, mid lane; Q poison star 24 + 8% max HP, then 5s of 3% max HP/s poison (8s cooldown, same-source +5s); passive extends an existing `rhea_poison` by 1s on LMB/RMB, once per target/attack, never creates poison; E is a 1.00s dash-return at 1100/1500px/s (~594px out, back to `cast_x`), 14 + 14 damage, first segment +15% max HP against any poisoned target, full 0–1.00s armor, 15s cooldown. RMB/Q are zero-knockback and use a point-blank body check; only LMB has knockback (60).
- Nyra: HP 100, basic ATK 20; LMB wave 20 (0.30s), RMB thrust 24, Q slash 30 (8s), E dash 30 (15s). LMB uses a 5-frame wave animation (0.06s each) and cast-anchored hitboxes (no projectile): the RMB thrust box `[28,-165,130,48]` during t=0–0.06s and 0.24–0.30s, and the extended `[28,-212,162,123]` (reach 190) during t=0.06–0.24s; it adds 1 mark and has no FX. Q uses a 6-frame slash animation (0.40s) and cast-anchored hitboxes: the thrust box during t=0–0.12s and 0.30–0.40s, and the extended box during t=0.12–0.30s; it adds 1 mark, has super armor for its 0.40s, and plays the separate six-frame blue slash FX (visible frames 02–04 align with the character's 02–04 frames and overlap the extended window). RMB uses a 5-frame thrust animation (0.08s each, 0.40s) with a single hitbox `[28,-165,130,48]` active t=0.16–0.24s. Melee hits add 1 mark (max 3); the 4th melee hit detonates for `1.8×atk + 10% target max HP` and leaves 1 mark. E dashes at 1100px/s for t=0.06–0.36s (~330px) with super armor during the dash, passes through the enemy but respects walls and solid barriers/platforms, and pushes the enemy out at the end.
- Warrior AI approaches, jumps solid barriers/platforms, attacks with a telegraphed axe slash, has startup/active super armor, and supports win/loss/restart. Its damage is `atk`-scaled: axe slash 24, dash 30 + 1.5s knock-up, axe throw 24 per pass. The dash knock-up uses a reduced knock-up gravity so the target stays airborne for the 1.5s window, and draws a procedural cyan vortex at the launched fighter's feet for the full status duration.
- Veno-Spider: half-size body (160×160 runtime frames, 75×75 hurtbox, `stage_body_width` 70, bite range 75); HP 50, ATK 10; bite 15, poison glob 8 + 3% max HP/s for 3s, web 10 + 1s stun. Cooldowns are bite 1s, poison 5s and web 8s, tracked independently by each spider. Selecting Veno spawns a group of **3** (default 1 ground + 2 hovering; `roster.json` `count`/`spawn_offsets`/`spawn_modes`); the player's attacks and projectiles can hit any living Veno and the match is won when all 3 die. Nyra's marks stack independently on each Veno. Same-source poison reapplication adds the new duration to the remaining time (2s + 3s = 5s); different sources — including different Venos — keep independent damage instances. Poison settles every 0.5s. It hovers on a web at 140–300px (base 220), prioritizes bite on the ground and venom/web while airborne, and uses a draw-only curved web strand. Poison is dark green (layered glob, cast mist and splash) and a poisoned body flashes green/purple every 0.18s; web uses the approved web_05 crop at 64px with a 150–170px impact decal, a procedural silk trail and collision radius 30; a connected bite adds a short green arc.
- Bat: 14 frames (wing 4, dive 3, sonic 3, hurt 1, stun 1, KO 2) on a 384×384 source / 192×192 runtime canvas with pivot (115,143); HP 50, ATK 10. Dive 10 (2s), sonic 12 + 1s stun (10s); free flight 40–420 (preferred 240, bob 24, vertical speed 300); five default spawns at 180/320/240/380/280px; hurtbox 100×66, `stage_body_width` 56. It is selected with F7; the startup default is a single Creepy Shooter. The body and the sonic wave collide with the barrier/platform AABBs; platforms are full solids. Dive is height-gated; sonic is the only randomly-timed skill (random opening cooldown + 50% cast gate, 0.55s group same-skill stagger). The sonic hitbox is a forward circle (+8px, r24) matching the Wi-Fi-style arcs. `count: 5` with five `spawn_offsets` and five `spawn_heights`.
- Creepy Shooter: HP 200, ATK 20; straight shot 30 (1s), homing bolt 20 (8s, platform-penetrating, 8s lifetime), back-roll 24 (10s, 140px, no i-frames, falls off platform edges), jump shot 24 (10s, surfaces 220/268, no-platform rejection). Bullets spawn at the measured muzzle (163/129 for skill 1); the homing wind-up draws a user-drawn three-frame reticle (0.30/0.40/0.30s) on the player. It is the default enemy and uses `stage_variants.creepy_shooter` (long platform 601–1080, short 170–484, spawn 1000,220).
- `V/C/X/Z` read the current enemy's four skill slots from data; undefined slots are safe no-ops and show `-` in F2.
- Frame data, hitboxes, cooldowns, damage and stage geometry are in `game/data/*.json`.
- Not included: daily loop, food/fullness, shop/gold, saves, audio, full HUD, group balancing beyond the Veno 3-body group and the five-Bat sandbox, further playable characters/enemies (Rhea Thorn is the newest playable, Creepy Shooter the newest enemy), packaging.
- No pytest suite or file logging; verification is through the sandbox, contact sheets and `--smoke-test`.

## Layout

```text
main.py                  entry point and fixed-step loop
game/                    runtime modules and data (including lina.py, nyra.py, rhea.py, warrior.py, veno.py, bat.py, creepy_shooter.py)
game/data/               stats, attacks, animations, roster and debug geometry
assets/frames/lina/      normal frames + flame/<action> frames
assets/frames/nyra/      Nyra frames on the 384x384 canvas
assets/frames/rhea/      Rhea frames on the 384x384 canvas + fx/ shuriken strips
assets/frames/warrior/   Warrior frames on the 384x384 canvas
assets/frames/veno/      Veno-Spider frames on the 320x320 canvas
assets/frames/bat/       Bat frames on the 384x384 source (192x192 runtime) canvas
assets/frames/creepy_shooter/  Creepy Shooter frames on the 384x384 canvas + fx/ bullets and reticle
assets/sprites/stage/    runtime platform/ladder PNGs copied from the contact sheets
assets/generated/        raw candidates, staged frames, contact sheets
tools/                   collect_frames.py, import_frames.py, contact_sheet.py
docs/                    design decisions, asset pipeline, debugging guide
Image/                   canonical character/enemy art (never overwritten)
PLAN.md                  original approved implementation plan
```

See [docs/DESIGN_DECISIONS.md](docs/DESIGN_DECISIONS.md), [docs/ASSET_PIPELINE.md](docs/ASSET_PIPELINE.md) and [docs/DEBUG.md](docs/DEBUG.md).
