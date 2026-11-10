# Island Survival — Lina / Nyra / Rhea / Eira vs Warrior / Veno / Bat / Creepy Shooter / Mech-Crab / Shadow Ninja / Crooked Witch Combat Sandbox

A 2D side-view combat sandbox for testing Lina Seabright, Nyra Steel, Rhea Thorn and Eira Frostveil against the Warrior, Veno-Spider, Bat, Creepy Shooter, Mech-Crab, Shadow Ninja and Crooked Witch before the full survival game is built.
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
checks `missing_frames == 0` for Lina, Nyra, Rhea, Eira, Veno, Warrior, Bat, Creepy Shooter,
Mech-Crab and Crooked Witch, including Rhea's six shuriken FX. The Bat phase
verifies the five-Bat group (selected with F7; the startup default is Creepy Shooter), five
initial altitudes, the 5-flight 3-high/2-low cycle in 40–477 with random waypoints and a 2s low
stay, dive 10, V/C/X/Z slots, sonic 12 + 0.8s stun (high flights only), out/return/wall/barrier/
platform bounce, the 0.65s cast lock, hurt/stun staying airborne, KO landing, and the five-body
group spawn/independent cooldowns/WIN.
The Creepy Shooter phase checks the dedicated mirrored stage (long platform 601–1080, short
170–484, only the right ground barrier, spawn 1000,220), HP/ATK/slots, the straight shot
(30, cooldown ~1s, block collision), the
1s lock wind-up and three-frame reticle, the homing bolt (penetrates platforms, 20 once, 8s
lifetime), the back-roll (140px, 24 damage, no i-frames, cooldown 10, falling off a platform edge),
the platform jump shot (surfaces 220/268, right takeoff 1136, 24 downward, no-platform rejection),
barrier hopping, AI priority, V/C/X/Z mapping, WIN, cleanup, stage switching, ladder hits
(`creepy_ladder_hit_mid_ok`, `creepy_ladder_hit_platform_ok`, `creepy_ladder_hit_top_ok`), and
`creepy_missing_frames == 0` / `creepy_fx_missing == 0`.
The Mech-Crab phase selects the front-facing boss and checks its no-barrier stage variant (long
platform 170–649 at surface 268, short 796–1110 at 220, spawn 1000,620), HP 400 / ATK 30 and the
four skill slots, full super armor through every skill (damage still applies, KO still ends it),
the 90°/s core laser (1.0s warning, 1.5s active, 36 once per target, blocked by platforms), the
locked-direction charge (5s cooldown, 1.0s warning, 45), the player-side claw slam (30 + 1.2s
stun), the leap slam (8s cooldown, 0.8s warning, terrain-ignoring flight, 60 in a 100px AoE,
platform landing), the 1s skill gap, V/C/X/Z mapping, WIN/cleanup, AI priority, and
`mech_crab_missing_frames == 0` / `mech_crab_fx_missing == 0`.
The Shadow Ninja phase checks the normal form on its flat stage variant (spawn 1000,620), HP/ATK copied from the current character, 1.5× walk, the 0.35s/0.5s high slash, the 5s low kunai (1.2atk, 1s stun, no block penetration), the 8s dash (~640px, player pass-through, jump-dodgeable low hitbox), the independent mark stack (1→2→3→detonate→1, extra atk + 1s stun), crouch/jump defense, barrier hop, WIN/cleanup, and
`shadow_ninja_missing_frames == 0` / `shadow_ninja_fx_missing == 0`.
The phantom phase checks skill 4: the 11-frame/1.36s transform (no-aura → shadow hold 0.50s → no-aura), the 6-frame/0.60s revert, frame-0 invincibility, self-clear, no hitbox/terrain phase, the three one-use skills (影爪/影缚/影闪), auto-revert after the third, the 15s cooldown starting after revert, and `shadow_ninja_phantom_missing_frames == 0` / `shadow_ninja_phantom_fx_missing == 0`.
The Eira phase checks the fourth playable character: 15 clips / 48 frames in roster order with Lina
still the startup default, LMB 20 + 20 freeze (crouch dodge), RMB 20 + 20 freeze with one hit,
Q 24 (44 vs frozen) with pierce and +30, the E state machine (12s/6s cooldowns, 0.40s raise,
targeting prompt, 0.08s spawn, ~1s fall, multi-target 30/54, super armor, KO end, 3s ground FX),
freeze threshold/clear/no-gain-while-frozen/equal slow/independent targets, climb, reset and
`eira_missing_frames == 0` / `eira_fx_missing == 0`.
The Crooked Witch phase checks the F7 caster on its no-barrier platform variant (spawn 965,220,
four teleport points), HP 400 / ATK 30 and the four slots, the 8s teleport (damage priority, 8s
no-damage auto-teleport, nearest-point exclusion, invincible/no-hitbox/hidden), the one-time
<50% heal (5×24, return to the trigger position), lightning 36 with 20% vulnerable ×3 (damage
first), the 1s ice-spike warning with 30 + 1.5s freeze and a dodgeable spot, the potion's direct
24 + 3%/s poison + 30% slow versus its 6s miss zone (2%/s + 20% slow, independent source), fire
rain (15s cooldown starting after the skill, 10×0.8s, x-locked vertical fireballs, 36 + burn,
no first-skill use), the ground 1>2>3>4 / platform 3>1>2>4 AI priority, reset and
`crooked_witch_missing_frames == 0` / `crooked_witch_fx_missing == 0`.
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
Phase L checks the shared special skills: the four data entries and V5 frame presence
(`special_skills_present`, `special_fx_missing`), key 1–4 mapping plus same-window dual-key
consumption (`special_input_ok`), Sacred Shield (`special_shield_ok`: use during hitstun, zero HP
loss, full stagger with no hurt clip/flash, on-hit statuses still applied, DoT blocked, direct/
projectile/hazard paths, gold block FX, armor branches, expiry, once), Purity Seal
(`special_purity_ok`: cleanse while frozen/stunned, 3s rejection, buffs kept, damage/stagger,
expiry, once), Fury Unbound (`special_fury_ok`: melee/projectile/direct ×2, DoT not doubled,
expiry, once), Vitality Tonic (`special_heal_ok`: formula, full-HP message/no consume, overflow),
once/reset/character-switch sharing (`special_once_ok`, `special_switch_ok`, `special_reset_ok`)
and the HUD/F2 mixed READY/active/USED state (`special_ui_ok`).

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
| 1 | Sacred Shield — 2s HP-damage immunity (one use per match, shared) |
| 2 | Purity Seal — cleanse + 3s negative immunity (one use per match, shared) |
| 3 | Fury Unbound — 5s direct-damage ×2 (one use per match, shared) |
| 4 | Vitality Tonic — heal 50 + 35% max HP (one use per match, shared) |
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

### Special skills (keys 1–4)

All four playable characters share one set of uses per match. The HUD row under the left panel
shows READY, active seconds or USED; F2 adds `1 SACRED SHIELD …` through `4 VITALITY TONIC …`
and `SPEC LEVEL 1 USED n/4`.

- **1 Sacred Shield (2s)** — HP damage from every source is 0. A blocked hit still fully staggers:
  hitstun, knockback, HURT state, attack cancel and hitstop all happen, and the attacker's on-hit
  statuses (burn/poison/stun/marks) still apply. The hurt animation and white flash are suppressed;
  a gold block ring plays instead. DoT is blocked while the shield is active; hazard statuses
  applied outside damage resolution (ice-ball freeze, poison zone) still apply. The player's own
  super armor still suppresses stagger.
- **2 Purity Seal (3s)** — cleanses burn, poison, slow, freeze, stun, knock_up and vulnerable
  (including all poison instances), then rejects new ones for 3s. Buffs (`super_armor`,
  `damage_reduction`, the three special statuses) are preserved; damage and stagger still land.
- **3 Fury Unbound (5s)** — doubles direct hit damage (melee, projectiles and direct-contact
  hazards) at resolve time, after freeze/poison bonuses and before the target's
  `damage_reduction`/`vulnerable`. DoT ticks and Nyra/Shadow mark detonations are not doubled.
- **4 Vitality Tonic** — immediately heals `level*50 + 35% max HP` with `level = 1`. At full HP it
  does not consume the use and shows `You are at full HP. You do not need to heal.` above the player.

Specials are usable whenever the player is alive (HP > 0): airborne, mid-attack, during hitstun/
freeze/stun, during Eira's E cast and while climbing (the character stays on the ladder). They are
unavailable when KO'd or after the match ends. Uses are shared for the whole match; switching
characters keeps the spent uses but drops the old body's active effect. F9/R and F5 restore all
uses. The V5 sprite strips live in `assets/frames/special_skills/` (shield/purity/fury loop and
follow the player; tonic plays once); their source frames and generator are in
`assets/generated/contact_sheets/special_skills_ingame_v5/`.

## Combat modes

The default enemy is a single **Creepy Shooter** (200 HP); the five-Bat group and the other enemies
are selectable with F7. Press F7 to cycle the enemy roster (Warrior → Veno-Spider ×3 → Bat ×5 →
Creepy Shooter → Mech-Crab → Shadow Ninja → Crooked Witch → training Dummy → back); `[` / `]` cycle the playable character roster
(Lina ↔ Nyra ↔ Rhea ↔ Eira). A switch performs a full
match reset and leaves the enemy AI off for manual testing. The AI also starts off on launch and after
any reset (F5 reload, F9, R); press F8 to turn it on. The dummy has
no AI and is useful for isolated tests; Warrior, Veno, Bat, Creepy Shooter, Mech-Crab, Shadow Ninja and Crooked Witch are the full opponents. After VICTORY or
DEFEATED, press R to restart; F9 resets at any time. Warrior's dash knock-up draws a cyan vortex at
the target's feet; it follows the body, stays visible at a minimum strength through the 1.5s window,
then vanishes. Extended knock-up gravity keeps the target airborne for that window, so landing and
control return together.

Veno-Spider spawns as a group of three 50 HP enemies (one ground + two hovering by default) on the
right half of the arena: base `[820, 620]`, offsets 720/820/940, ±40 per spider on every reset.
It bites at close range, spits a straight-line poison glob (3% max HP/s for 3s, same-source hits
extend the duration) and shoots a stunning web (1s). It webs itself up to a variable hover height
(base 220px, 140–300px range) when the player is outside bite range and a ranged skill is ready;
while airborne it prioritizes venom/web, then descends to bite. Each spider tracks its own bite
(1s), poison (5s) and web (8s) cooldowns; a group-level same-skill gap (bite 0.8s, poison/web
1.2s) plus a 0.5s opening delay prevents the three from opening the same skill together, while
different skills may overlap. Its visual hover is a hanging pose with a draw-only web strand above
it. The reusable multi-body contract is in `docs/DESIGN_DECISIONS.md` §Multi-body enemy rules
(2026-11-02).

Five Bats spawn around x=620–1020, mostly on the right half (base `[820, 470]`, offsets
0/−160/160/−80/80, ±40 per Bat), at initial altitudes 180/320/240/380/280px; they fly over
40–477px with no gravity, but honour the arena walls and the solid barrier/platform AABBs.
Each Bat keeps a shuffled 5-flight bag (3 high / 2 low, random order): a free flight lasts 5s,
high flights pick a random 400–477 height (screen y 143–220), and low flights fly at screen
y=550 for 5s and then add a 2s stay. The 477 cap keeps the sprite on screen. During free flight each Bat
picks a random horizontal waypoint (about x=160–1120) and refreshes it every 0.9–1.4s or within
18px, so it keeps moving instead of parking at the old standoff. The dive (10 damage, 2s) is
deterministic and fires when its hitbox can reach the player from the current altitude; the sonic
(12 damage + **0.8s stun**, 10s) is the only randomly-timed skill and is available only on high
flights. A random opening cooldown and a 50% cast gate desynchronise the group, plus a same-skill
group gap (sonic 1.2s, dive 0.8s) and a 0.5s opening delay; different skills may overlap. The
wave flies in the mouth→player direction, bounces off walls and barriers/platforms, and returns
to the Bat's current position, dealing at most one hit. Bats stay airborne through hurt/stun and
only fall on KO. `roster.json` uses `count: 5`, five spawn offsets, five spawn heights and
`spawn_jitter: 40`; the initial flight timers are staggered 5/6/7/8/9s. The group is selected
with F7; the startup default is a single Creepy Shooter. F2 shows the `FLIGHT` side, waypoint,
target, stay and bag. The reusable multi-body contract is in `docs/DESIGN_DECISIONS.md`
§Multi-body enemy rules (2026-11-02).

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

Mech-Crab is a front-facing mechanical boss with HP 400 / ATK 30 and no normal attacks. It spawns at
(1000,620) on a dedicated no-barrier stage variant (long platform 170–649 at surface 268, short
796–1110 at surface 220, ladders at 508 and 921) and walks sideways on six legs; the runtime mirrors
the front art for left/right facing. All four skills grant super armor for their full
warning/active/recovery window (damage still applies) and leave a 1s global skill gap. The core
laser (6s) warns for 1.0s, then sweeps from straight up at 90°/s for 1.5s, dealing 36 once per
target and stopping on platforms; the crab does not move during it. Charge (5s) locks its direction
during a 1.0s warning, then dashes at 700px/s for 0.55s for 45 + 140 knockback. Claw slam (5s)
grows the player-side claw for 0.5s and deals 30 + 1.2s stun. Leap slam (8s) marks a fixed target
during a 0.8s warning, ignores terrain for the 0.65s flight, and deals 60 in a 100px landing AoE on
a platform or the ground. The leap target uses a user-supplied three-frame reticle
(0.22/0.18/0.40s, last frame held through the flight) at 205px (0.8× of the 256px baseline); the HP
bar and name label are lifted 230px (`health_bar_lift`) to clear the shell. The AI leaps when the
player is on another level (or at range when nothing else is ready), claws up close, charges at mid
range, lasers at range with line of sight and within 135° of the core axis, and otherwise walks.
`skill_slots` is `["mech_laser","mech_charge","mech_claw_slam","mech_leap_slam"]`; the enemy is
always a single instance and never uses basic attacks or ladders.

## Debug controls

| Key | Action |
|---|---|
| F1 | Toggle hitbox/hurtbox, lane, wall, barrier, platform and ladder overlay |
| F2 | Toggle the live debug panel |
| F3 | Pause / resume |
| F4 | Step one simulation tick (pauses) |
| F5 | Hot-reload all JSON and soft-reset the scene |
| F6 | Cycle time scale 0.25x / 0.5x / 1x / 2x |
| F7 | Cycle the enemy roster (Warrior → Veno-Spider ×3 → Bat ×5 → Creepy Shooter → Mech-Crab → Shadow Ninja → Crooked Witch → training Dummy → …) |
| [ / ] | Cycle the playable character roster (Lina ↔ Nyra ↔ Rhea ↔ Eira) |
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

- Four playable characters (Lina, Nyra, Rhea, Eira) vs. Warrior, Veno-Spider, Bat, Creepy Shooter, Mech-Crab, Shadow Ninja or Crooked Witch in a single arena; the training Dummy remains available through F7. A `roster.json` registry drives character/enemy construction. The current default enemy is Creepy Shooter; an enemy entry may name a `stage_variant` that replaces the stage when selected.
- Scene: `blocks` use `kind: barrier | platform`; barriers are solid obstacles, platforms are full AABB solids (top/side/underside), and `ladders` are separate non-solid climb triggers. Current default-stage layout: long platform x=170..649 at surface y=220, short platform x=796..1110 at surface y=268, long ladder x=508..572 (400px), medium ladder x=921..985 (352px, native 160px width), ground barriers x=400..490 and x=700..790; player spawn x=280, enemy spawn x=600. The Creepy Shooter variant mirrors the platforms/ladders: long platform x=601..1080, short platform x=170..484, ladders x=708..772 and x=295..359, only the right ground barrier x=790..880 (the left x=400..490 was removed 2026-11-01), Creepy spawn x=1000 at y=220. The Mech-Crab variant removes both barriers and swaps the platform heights: long platform x=170..649 at surface y=268, short platform x=796..1110 at surface y=220, ladders x=508..572 and x=921..985, Mech-Crab spawn x=1000 at y=620. The Crooked Witch variant also removes both barriers: short platforms x=158..472 and x=808..1122 at surface y=220, long ladders x=420..484 and x=796..860, Witch spawn x=965 at y=220, and teleport points (315/965, 220/620). B toggles barriers/platforms; ladders stay visible and climbable. F1 shows the collision boxes; F2 shows counts and `CLIMB`. `penetrates_blocks` is false by default; only the Creepy Shooter homing bolt sets it true.
- Lina: 47 normal + 43 flame-form frames (90); both tables include the 2-frame back-view climb clip. Damage follows the docx formulas (punch 20, kick 24, Q 20 at the starting stats). Q launches a fist-sized static sprite projectile: a pixel-art teal glass ball (white rim/highlights, short trail) drawn slightly above the fist lane in normal form, orange/red fire in flame form, with matching teal/orange cast and impact colors. Nyra: 35 frames (idle 2, walk 6, jump 2, crouch 1, hurt 1, KO 2, slash 6 (Q), thrust 5, wave 5 (LMB), dash 3, climb 2) on a 384x384 canvas with pivot (192,372), body 214. Warrior: 36 frames (idle 4, walk 6, jump 2, axe_slash 6, axe_throw 7, dash 5, hurt 2, KO 4) on a 384x384 canvas with pivot (192,372). Veno-Spider: 20 minimal frames (idle 2, walk 2, hover 2, jump 2, hurt 1, KO 2, bite/poison/web 3 each) on a 320x320 canvas with pivot (160,308), body 150. Creepy Shooter: 29 frames (idle 2, walk 4, crouch 1, jump 2, hurt 2, KO 2, shot 2, homing 4, roll 6, jump shot 4) on a 384x384 canvas with pivot (192,372), body 214 (the roll set is imported at 0.9×); hurtbox 56×210 standing / 56×130 crouching, excluding the rifle. Mech-Crab: 47 front-facing frames (idle 4, walk 4, jump 2, hurt 2, KO 4, mech_laser 9, mech_charge 7, mech_claw_slam 7, mech_leap_slam 8) on a 640x640 canvas with pivot (320,628), body 230; hurtbox 160×150, `stage_body_width` 170, plus three 205×205 leap-reticle FX. Shadow Ninja: 35 frames (idle 4, walk 6, jump 2, crouch 1, hurt 2, KO 4, slash/throw/dash 5 each, stun 1) on a 384×384 canvas with pivot (192,372), body 214, plus a two-frame 32×32 horizontal kunai FX; hurtbox 56×210 standing / 56×130 crouching, `stage_body_width` 100. Plus a 62-frame phantom set: transform 11, idle 4, walk 6, rend 5, bind 5, vanish/appear 5+5, flash_attack/pause 3+3, shark emerge/charge/recover 3+3+3, revert 6; no jump/crouch/hurt/KO/stun. Phantom FX: trail 3, tentacle 4, bind front/back 6+6, orb 3, shark 3. Eira: 48 frames / 15 clips (idle 4, walk 6, jump 2, crouch 1, climb 4, hurt 2, stun 1, KO 4, snowball 4, staff_strike 5, ice_shard 5, e_raise 3, e_hold 2, e_release 3, e_recover 2) on a 384×384 canvas with pivot (192,372), body 209, plus 44 FX frames and the freeze shell/foot ice; hurtbox 56×210 standing / 56×130 crouching, `stage_body_width` 100, climb draw scale 1.15×. Crooked Witch: 17 clips / 58 frames (idle 4, walk 4 at 0.12s, fly 2+2+2, teleport 3+3, hurt 2, KO 4, heal 6, lightning 4×3, ice_spike 4, potion 4, fire_rain_intro 5, fire_rain_hold 1) on a 640×640 canvas with pivot (320,628), body 230, plus 124 FX files; hurtbox 56×210 standing/crouching, `stage_body_width` 100.
- Climb animations: Lina normal/flame, Nyra and Rhea each have two dedicated back-view frames; Eira uses the approved four-frame v3 back-view clip (0.12s each). Nyra's sword stays sheathed on her back and her hands stay free, while Rhea's two shuriken stay stowed on her back band. Lina draws at 1.2×; Nyra and Rhea at 1.1×; Eira at 1.15× around the feet pivot; the combat hurtbox and stage body are not scaled. A climb with a top platform mounts early at the platform midpoint minus 6px; ladder jump-offs and knock-offs ignore platform sides/underside until landing, and a hit whose feet are inside a platform snaps to its top. Enemy climb art/AI is not implemented yet.
- Rhea: HP 100, basic ATK 20; 33 frames (idle 2, walk 4, jump 2, crouch 1, hurt 2, KO 3, slash_r/l 3+3, throw 3, poison throw 3, dash 5, climb 2) on 384×384/pivot (192,372), plus six 64×64 star FX; climb draw scale 1.1×. LMB 20 with right/left alternation and 60 knockback; RMB steel star 24, 900 range, 850 speed, mid lane; Q poison star 24 + 8% max HP, then 5s of 3% max HP/s poison (8s cooldown, same-source +5s); passive extends an existing `rhea_poison` by 1s on LMB/RMB, once per target/attack, never creates poison; E is a 1.00s dash-return at 1100/1500px/s (~594px out, back to `cast_x`), 14 + 14 damage, first segment +15% max HP against any poisoned target, full 0–1.00s armor, 15s cooldown. RMB/Q are zero-knockback and use a point-blank body check; only LMB has knockback (60).
- Eira Frostveil: HP 100, basic ATK 20, walk 260, hurtbox 56×210 / 56×130 crouch; 48 frames / 15 clips on 384×384/pivot (192,372), body 209, plus 44 FX; climb draw scale 1.15×. Freeze meter per target (LMB/RMB 20, Q 30, E 50) with an equal-percent 2s slow; at 100 it clears and freezes for 2s (no gain while frozen). LMB snowball 20 (+20 freeze, high lane from the frame-2 blue crystal, 112/194, 850 speed, radius 11.2, single hit); RMB staff 20 (1.0/1.2, one hitbox at 0.20–0.36, +20); Q ice shard 24, 44 vs frozen (+1.0 atk), 3s cooldown, high lane from the frame-2 crystal (98/190), 950 speed, radius 14, pierces enemies but not blocks, +30 freeze. E ice ball 30, 54 vs frozen, 12s cooldown (6s when cancelled): raise 0.40s with full super armor, mouse-selected x, click prompt + guide line, spawn 0.08s into release at y=-120, radius 80, 740px/s fall through blocks, multi-target once each, +50 freeze, lands on the ground and shatters into four chunks + 14 fragments for 3s. RMB/8s timeout cancel the cast; KO force-ends it.
- Nyra: HP 100, basic ATK 20; LMB wave 20 (0.30s), RMB thrust 24, Q slash 30 (8s), E dash 30 (15s). LMB uses a 5-frame wave animation (0.06s each) and cast-anchored hitboxes (no projectile): the RMB thrust box `[28,-165,130,48]` during t=0–0.06s and 0.24–0.30s, and the extended `[28,-212,162,123]` (reach 190) during t=0.06–0.24s; it adds 1 mark and has no FX. Q uses a 6-frame slash animation (0.40s) and cast-anchored hitboxes: the thrust box during t=0–0.12s and 0.30–0.40s, and the extended box during t=0.12–0.30s; it adds 1 mark, has super armor for its 0.40s, and plays the separate six-frame blue slash FX (visible frames 02–04 align with the character's 02–04 frames and overlap the extended window). RMB uses a 5-frame thrust animation (0.08s each, 0.40s) with a single hitbox `[28,-165,130,48]` active t=0.16–0.24s. Melee hits add 1 mark (max 3); the 4th melee hit detonates for `1.8×atk + 10% target max HP` and leaves 1 mark. E dashes at 1100px/s for t=0.06–0.36s (~330px) with super armor during the dash, passes through the enemy but respects walls and solid barriers/platforms, and pushes the enemy out at the end.
- Walk sets (2026-11-09): Lina uses the new `lina_walk_v1` six-frame walk and Nyra uses `nyra_walk_v3` six frames; both play at 80ms per frame (0.48s cycle) and are installed under `assets/frames/lina/walk/` and `assets/frames/nyra/walk/`. Nyra's total frame count rises from 31 to 35.
- Warrior AI approaches, jumps solid barriers/platforms, attacks with a telegraphed axe slash, has startup/active super armor, and supports win/loss/restart. Its damage is `atk`-scaled: axe slash 24, dash 30 + 1.5s knock-up, axe throw 24 per pass. The dash knock-up uses a reduced knock-up gravity so the target stays airborne for the 1.5s window, and draws a procedural cyan vortex at the launched fighter's feet for the full status duration.
- Veno-Spider: half-size body (160×160 runtime frames, 75×75 hurtbox, `stage_body_width` 70, bite range 75); HP 50, ATK 10; bite 15, poison glob 8 + 3% max HP/s for 3s, web 10 + 1s stun. Cooldowns are bite 1s, poison 5s and web 8s, tracked independently by each spider; a group-level same-skill gap (bite 0.8s, poison/web 1.2s) plus a 0.5s opening delay prevents simultaneous casts. Selecting Veno spawns a group of **3** (1 ground + 2 hovering; base `[820,620]`, offsets 720/820/940, ±40 per spider; `roster.json` `count`/`spawn_offsets`/`spawn_modes`/`spawn_jitter`); all spawn on the right half, the player's attacks and projectiles can hit any living Veno and the match is won when all 3 die. Nyra's marks stack independently on each Veno. Same-source poison reapplication adds the new duration to the remaining time (2s + 3s = 5s); different sources — including different Venos — keep independent damage instances. Poison settles every 0.5s. It hovers on a web at 140–300px (base 220), prioritizes bite on the ground and venom/web while airborne, and uses a draw-only curved web strand. Poison is dark green (layered glob, cast mist and splash) and a poisoned body flashes green/purple every 0.18s; web uses the approved web_05 crop at 64px with a 150–170px impact decal, a procedural silk trail and collision radius 30; a connected bite adds a short green arc.
- Bat: 14 frames (wing 4, dive 3, sonic 3, hurt 1, stun 1, KO 2) on a 384×384 source / 192×192 runtime canvas with pivot (115,143); HP 50, ATK 10. Dive 10 (2s), sonic 12 + **0.8s stun** (10s); free flight 40–477 (preferred 240 only as the reset cruise-height fallback, bob 24, vertical speed 300); spawns around x=620–1020, mostly right half (base `[820,470]`, offsets 0/−160/160/−80/80, ±40 per Bat), at initial heights 180/320/240/380/280px; hurtbox 100×66, `stage_body_width` 56. It is selected with F7; the startup default is a single Creepy Shooter. The body and the sonic wave collide with the barrier/platform AABBs; platforms are full solids. Each Bat keeps a shuffled 5-flight bag (3 high / 2 low, random): a free flight lasts 5s; high targets random 400–477 (screen y 143–220), low targets screen y=550, then a 2s stay; the 477 cap keeps the sprite on screen. Each free flight picks a random x waypoint (~160–1120) every 0.9–1.4s or within 18px, and initial timers are staggered 5/6/7/8/9s. Dive is height-gated; sonic is available only on high flights and is the only randomly-timed skill (random opening cooldown + 50% cast gate, same-skill group gap sonic 1.2s / dive 0.8s, plus a 0.5s opening delay). The sonic hitbox is a forward circle (+8px, r24) matching the Wi-Fi-style arcs. `count: 5` with five `spawn_offsets`, five `spawn_heights` and `spawn_jitter: 40`; F2 shows the `FLIGHT` side/waypoint/target/stay/bag.
- Creepy Shooter: HP 200, ATK 20; straight shot 30 (1s), homing bolt 20 (8s, platform-penetrating, 8s lifetime), back-roll 24 (10s, 140px, no i-frames, falls off platform edges), jump shot 24 (10s, surfaces 220/268, no-platform rejection). Bullets spawn at the measured muzzle (163/129 for skill 1); the homing wind-up draws a user-drawn three-frame reticle (0.30/0.40/0.30s) on the player. It is the default enemy and uses `stage_variants.creepy_shooter` (long platform 601–1080, short 170–484, spawn 1000,220).
- Mech-Crab: HP 400, ATK 30; 47 front-facing frames (640×640, pivot 320,628, body 230) plus a three-frame leap reticle; hurtbox 160×150, `stage_body_width` 170. Laser 36 (6s, 1.0s warning, 1.5s at 90°/s, once per target, platform-blocked), charge 45 (5s, 1.0s locked-direction warning, 700px/s × 0.55s), claw slam 30 + 1.2s stun (5s, 0.5s wind-up), leap slam 60 in a 100px AoE (8s, 0.8s warning, 0.65s terrain-ignoring flight). Super armor covers every skill; a 1s skill gap follows. It uses `stage_variants.mech_crab` (no barriers; long platform 170–649 at 268, short 796–1110 at 220, spawn 1000,620). The user-drawn three-frame reticle is 205px (0.8× of 256) at 0.22/0.18/0.40s with the last frame held through flight; the HP bar/name are lifted 230px above the shell.
- Shadow Ninja: two forms. Normal form: HP/ATK copy the current character (100/20 at the starting stats), walk 1.5× (390), hurtbox 56×210 standing / 56×130 crouching. Skill 1 is a 0.35s high slash on a 0.5s cooldown; skill 2 is a 5s low kunai (1.2atk, 1s stun, no block penetration); skill 3 is an 8s dash (~640px, passes through the player, low jump-dodgeable hitbox). The passive marks the player 1→2→3→detonate (extra atk + 1s stun, reset to 1); `shadow_marks` keeps Nyra's marks separate, with purple pips above the player. AI approaches at close/far range, tracks its own kunai into a dash, crouches against high attacks, jumps against low attacks, hops barriers. Skill 4 `shadow_phantom_form` (15s cooldown, starts after the revert): an 11-frame/1.36s transform (normal → no-aura → shadow hold 0.50s → no-aura) followed by a 6-frame/0.60s revert. From transform frame 0 it is invincible, clears its own marks/negatives/hitstun/KB, has no combat hitbox (player attacks/projectiles pass through; `targets_for` filters it), cannot receive marks/passives, ignores terrain (`ignore_terrain`), keeps normal cooldowns ticking, and has no jump/crouch/hurt/KO frames. The phantom has three one-use skills: P1 影爪 (5×0.09s, high `[20,-195,240,55]`, 1.0atk, crouch dodge, separate 3-frame trail at 0.18–0.36s); P2 影缚 (5×0.10s, low lane 60, speed 900, range 700, radius 20, 1.2atk + 1s stun, jump dodge, pierces barriers, 4-frame tentacle + v2 front/back wrap); P3 影闪 (2.482s: vanish 0.30 → appear behind → high hand + high shadow bolt 0.8atk once, crouch dodge → vanish → reappear at max → pause 0.30 → shark emerge 0.21 → low 500px charge 0.8atk, jump dodge, pierces barriers/player → recover 0.21). Each skill is marked used at cast start; using all three auto-reverts (no forced timeout); the 15s cooldown starts after the revert. The AI transforms at ≤40% HP or when the largest incoming hit is ≥25% max HP, then uses P2→P1 close or P2→P3→P1 far. It uses `stage_variants.shadow_ninja` (flat, spawn 1000,620).
- Crooked Witch: HP 400, ATK 30, walk 150, hurtbox 56×210; 17 clips / 58 frames on 640×640/pivot (320,628), body 230, plus 124 FX. Uses `stage_variants.crooked_witch` (no barriers; short platforms 158–472 and 808–1122 at 220, long ladders 420–484 and 796–860, spawn 965,220; teleport points (315/965, 220/620)). Teleport (8s, triggered by damage or 8s without damage) picks a random point excluding the nearest and current, with 0.3s out/in invincible/no-hitbox/hidden. Heal triggers once below 50%: 5×24 HP (6%/s), invincible/no-hitbox, flies to center and back; the hands-open cast shows the independent staff on the facing side, while the fly frames use her own. Skill 1 lightning (2s): 36, forward at the same height, up/down when the target is beyond 140px horizontally and unblocked; on hit it first deals damage, then adds 20% vulnerable for 3s, max 3 stacks. Skill 2 ice spike (5s): 1s blue ground warning at the target's feet, then 30 + 1.5s freeze in a 65px radius; spike FX are grounded and scaled to the Witch's height. Skill 3 potion (8s): platform arc or ground low shot; direct hit 24 + 3%/s poison for 3s + 30% slow, miss leaves a 6s zone with 2%/s poison + 20% slow (independent source); the pool is grounded at the feet. Skill 4 fire rain (15s, cooldown starts after the skill ends, cannot open a battle): 10 fireballs at 0.8s intervals, x locked at spawn, vertical and block-ignoring, 36 + burn 5 HP/s for 3s; the Witch is invincible/no-hitbox while flying. AI priority is ground 1>2>3>4 and platform 3>1>2>4, with the heal and teleport passives above it; between decisions she keeps walking continuously instead of flickering to idle.
- `V/C/X/Z` read the current enemy's four skill slots from data; undefined slots are safe no-ops and show `-` in F2. During Shadow Ninja's phantom form V/C/X map to 影爪/影缚/影闪 and Z is a no-op; in normal form Z triggers the phantom transform. For the Crooked Witch they are `witch_lightning`, `witch_ice_spike`, `witch_potion` and `witch_fire_rain`.
- Frame data, hitboxes, cooldowns, damage and stage geometry are in `game/data/*.json`.
- Multi-body enemies (Veno ×3, Bat ×5): 2026-11-02 rule — right-half spawns with per-member `spawn_jitter: 40`, same-skill group gaps (Veno bite 0.8 / poison 1.2 / web 1.2; Bat dive 0.8 / sonic 1.2) and a 0.5s opening delay; `force_attack` bypasses both. Canonical rule: `docs/DESIGN_DECISIONS.md` §Multi-body enemy rules (2026-11-02).
- Shared special skills (keys 1–4, one use each per match across Lina/Nyra/Rhea/Eira): Sacred Shield, Purity Seal, Fury Unbound and Vitality Tonic. HUD row, F2 full-name lines, V5 sprite strips in `assets/frames/special_skills/`, and the Phase L smoke flags. Sacred Shield suppresses the hurt clip and flash on blocked hits while keeping hitstun/knockback/attack cancel/hitstop.
- Final test-sandbox version: the roster and special skills above are the final scope. Lina Shadowtide is not implemented and will not be added; only her poster/source art remains under `Image/Enemy/`.
- Not included: daily loop, food/fullness, shop/gold, saves, audio, full HUD, group balancing beyond the Veno 3-body group and the five-Bat sandbox, further playable characters/enemies (Eira Frostveil is the newest playable, Crooked Witch the newest enemy), Lina Shadowtide, packaging.
- No pytest suite or file logging; verification is through the sandbox, contact sheets and `--smoke-test`.

## Layout

```text
main.py                  entry point and fixed-step loop
game/                    runtime modules and data (including lina.py, nyra.py, rhea.py, eira.py, special_skills.py, warrior.py, veno.py, bat.py, creepy_shooter.py, mech_crab.py, shadow_ninja.py, crooked_witch.py)
game/data/               stats, attacks, animations, roster, special_skills and debug geometry
assets/frames/lina/      normal frames + flame/<action> frames
assets/frames/nyra/      Nyra frames on the 384x384 canvas
assets/frames/rhea/      Rhea frames on the 384x384 canvas + fx/ shuriken strips
assets/frames/eira/      Eira frames on the 384x384 canvas + fx/ snowball/shard/staff/E/status strips
assets/frames/warrior/   Warrior frames on the 384x384 canvas
assets/frames/veno/      Veno-Spider frames on the 320x320 canvas
assets/frames/bat/       Bat frames on the 384x384 source (192x192 runtime) canvas
assets/frames/creepy_shooter/  Creepy Shooter frames on the 384x384 canvas + fx/ bullets and reticle
assets/frames/mech_crab/  Mech-Crab frames on the 640x640 canvas + fx/ leap reticle
assets/frames/shadow_ninja/  normal frames + transform/ + phantom/ (idle, walk, rend, bind, vanish, appear, flash_attack, pause, shark, revert) + fx/ (kunai, trail, tentacle, front/back wrap, orb, shark)
assets/frames/crooked_witch/  frames on the 640x640 canvas + fx/ (lightning, teleport, heal, ice, potion, fire rain)
assets/frames/special_skills/  V5 special-skill strips (shield/purity/fury/tonic, six 320x340 frames each)
assets/sprites/stage/    runtime platform/ladder PNGs copied from the contact sheets
assets/generated/        raw candidates, staged frames, contact sheets (special_skills_ingame_v5 holds the V5 source/generator)
tools/                   collect_frames.py, import_frames.py, contact_sheet.py, preview_special_skills.py
docs/                    design decisions, asset pipeline, debugging guide, NEXT_SESSION_SPECIAL_SKILLS.md
Image/                   canonical character/enemy art (never overwritten)
PLAN.md                  original approved implementation plan
```

See [docs/DESIGN_DECISIONS.md](docs/DESIGN_DECISIONS.md), [docs/ASSET_PIPELINE.md](docs/ASSET_PIPELINE.md) and [docs/DEBUG.md](docs/DEBUG.md).
