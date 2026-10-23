# Design decisions and rule assumptions

The spec (`instruction.docx`) defines real-time side-view combat and Lina's kit qualitatively, but
leaves damage, cooldowns, energy caps, enemy stats and several interaction rules unspecified.
This document records the provisional rules used by the sandbox. Values live in
`game/data/stats.json`, `attacks.json` and `debug.json` and can be changed without code edits.

## Core combat

- Fixed 60Hz simulation; 60ms hitstop (about 4 ticks); 120ms press buffer; 200ms hitstun.
- Arcade feel: attacks lock ground movement with a small forward lunge. Attack direction follows Lina's
  current facing, which is set by A/D; attacks do not auto-face the target. Facing persists while idle,
  so tapping A/D before an attack aims the punch, kick or Q to that side.
- Attack lock-on is off by default. Middle mouse toggles it; while on, Lina's punch/kick/Q start by
  facing the living enemy (8px deadzone), and the attack, lunge and projectile follow that facing.
  Idle facing, movement and Warrior AI are unchanged. Switching character/enemy resets lock-on to
  off; F9 keeps the current setting; startup/F5 are off.
- Presses during an attack go into a one-slot action queue instead of expiring with the 120ms buffer.
  The newest press wins; punch/kick start the opposite limb when the attack ends, and Q or jump also
  wait for the attack to end. E is the exception: it waits only for recovery to begin, then cancels it.
- Presses made during hitstun or a control lock (knock_up/freeze/stun) use the same one-slot queue.
  The newest press survives the lock and executes as soon as control returns, instead of expiring
  with the short input buffer.
- Held movement and crouch are rebuilt from the physical keyboard after pause resume, scene
  reset/rebuild and focus regain, so a key held across those moments keeps working without a re-press.
  Text input is disabled at startup so a Chinese IME does not consume gameplay keys.
- Ground-only LMB/RMB/Q; E can be used in the air. No air normal attacks.
- Knockback is 300px/s for the kick and 150px/s for Q, decaying over 0.35s.
- Lina's attacks follow the docx basic/extra split: punch `atk` (basic + extra), kick
  `1.2 * basic + 0.8 * extra`, Q `basic + 1.5 * extra`. With the initial basic 20 / extra 0 this is
  20 / 24 / 20 damage. `attacks.json` stores `basic_mult` and `extra_mult`; flame bonus and damage
  reduction apply to the result.
- Energy: max 100, starts at 0, no regeneration. Hits grant +15 punch / +20 kick / +20 Q.
- Q cooldown: 8s. E cooldown: 20s. Both start ready at battle start.
- E also costs 100 energy and refreshes Q. While in flame form, hits grant no energy.
- Flame form: 10s. The first damaging hit gets +20%, the second +40%, the third and later +60%.
  The counter resets when E activates and is cleared when the form ends. Duration is not refreshed
  by hits. The bonus does not apply to burn damage.
- Flame hits apply burn: 5 HP/s for 3s, refreshed by subsequent flame hits.
- Q projectile handoff: the sprite shows no air (frame 0), gathering (frame 1), a launched ball
  (frame 2), then a clean hand (frame 3). The in-game projectile spawns at t=0.26s, exactly as the
  sprite's ball disappears, so the ball is never duplicated.

## Second form (flame form) animation set

- `transform_04` is the appearance base: red/black outfit, steady orange fire aura, glowing eyes.
- 41 dedicated flame-form frames were generated from the normal pose references using multi-image
  fusion (pose image + `transform_04`):
  idle 4, walk 6, jump 2, crouch 1, punch_l/r 4+4, kick_l/r 4+4, Q 4, hurt 2, KO 4, revert 2.
- The animation player keeps two clip tables: normal and flame. After the transform clip finishes,
  it switches to the flame table for idle/walk/punch/kick/Q/hurt/KO.
- Jump, crouch, hurt and KO have dedicated flame frames, so they keep the red/black outfit and a
  controlled aura. There is no runtime tint fallback: a flame-variant clip without dedicated art is
  skipped, while a normal-variant frame (such as an interrupted transform) draws untinted. The
  transform clip itself still plays the normal-frame sequence.
- If a hit lands during the normal→flame transform, the spent energy immediately switches the
  animation table to flame; hurt/KO then use flame art instead of leaving Lina invisible.
- The generated flame art has per-frame horizontal framing drift. `flame_offsets` in
  `animations.json` shifts each flame frame at draw time (mirrored when facing left) so the body
  stays at the normal form's world position; transform and revert do not visibly move Lina.
- When the 10s flame form ends, the game waits for the current neutral state, then plays the 2-frame
  `revert` clip (0.24s, control locked) and switches back to the normal table. A hit during the fade
  queues the revert to resume after hitstun; KO keeps the flame frames. An attack that started in
  flame form finishes with flame frames before the revert.

## Status effects

- The data model includes all nine spec statuses: knockback, burn, poison, slow, knock_up, freeze,
  stun, super_armor, damage_reduction.
- Burn: 5 HP/s, 3s, refreshes.
- Poison: 2% max HP/s. Same source reapplies and extends the duration; different sources keep
  independent instances that each deal damage. Poison is data-only in the first milestone and can be
  forced from the debug controls.
- Super armor makes the fighter immune to control effects (knockback, knock_up, freeze, stun,
  slow) while it is active; damage still applies and damage reduction is a separate percentage
  multiplier. Nyra's Q and E use it during their armor windows.

- The sandbox naturally triggers burn (flame hits), knockback (kick/Q), and knock-up (Warrior dash);
  stun, freeze, slow, poison, super armor and damage reduction are available through F11.

## Stage and projectile heights

- 1280x720 logical resolution; background scaled from 1664x936; fixed camera.
- Ground y=620; walls at x=90 and x=1190; two solid blocks at x=400..490 and x=760..850.
- Lina spawns at x=280; the dummy and Warrior spawn at x=1000.
- Fighters keep a minimum center distance equal to the sum of their stage body half-widths
  (Lina 50 + Warrior 60 = 110px). The enemy yields first on his current side; if a wall/block
  blocks that side, he is not flipped across the player — Lina is pushed to the free side instead.
  Separation moves at most `combat.separation_speed × dt` (600px/s), so a deep overlap slides apart
  over a few ticks instead of teleporting. Warrior facing ignores targets within an 8px deadzone,
  so overlapping bodies cannot flip the sprite every tick.
- Stage collision uses a wider grounded body than the 56px combat hurtbox: Lina's
  `stage_body_width` is 100px, so her front boot stops at the block edge instead of entering it.
  While airborne, collision falls back to the hurtbox width so stepping off a ledge does not snap
  the character sideways. Attack lunges use the same stage collision, not a direct x change.
- Overlapping a block resolves to the nearer side; landing on a block top requires the feet center
  to be within 8px of the block span (`land_margin`).
- B toggles both block drawing and collision for observation; the AI also stops jumping when blocks
  are off. The toggle persists across F9 and resets on F5/rebuild.
- Projectile lane heights are measured upward from the attacker's feet: high 180px, fist 142px,
  mid 120px, low 60px. Lina Q spawns at `attacker.y - 142`, so it is screen y 478 on flat ground
  and y 418 while she stands on a 60px block. The ball keeps that spawn height in flight.
- This makes the Q trajectory follow Lina vertically instead of staying on a fixed world lane.
- Lina's sprite body height is approximately 210px, anchored at the feet-center pivot (128,244) on a
  256x256 canvas. Warrior uses a 384x384 canvas with pivot (192,372) and a body height of about 230px.

## Warrior (Phase 2)

- Warrior is the default enemy; the training Dummy remains available through F7. Dummy mode is
  training-only and does not show a win/loss banner.
- Canvas: 384x384, feet-center pivot (192,372), body about 230px. Lina stays 256x256 / (128,244).
- Frames (36): idle 4, walk 6, jump 2, axe_slash 6, axe_throw 7, dash 5, hurt 2, KO 4. Axe slash
  frame 01 is a mid-lift between the low rear guard and the high wind-up; frames 03/04 use a
  one-handed rear grip based on the follow-through pose.
- Stats: HP 300, basic ATK 20, extra ATK 0, `stage_body_width` 120, hurtbox 84x230, walk 160,
  jump_v 700, gravity 2200. Damage is `basic_mult * basic + extra_mult * extra`; Warrior skills use
  equal multipliers, i.e. `1.2 / 1.5 / 1.2 * atk`.
- Axe slash: 0.75s total, startup 0.25s (frames 0-2), active 0.30s (frames 3-4), recovery 0.20s
  (frame 5); hitbox `[36,-205,150,110]` active t=0.25..0.55; 24 damage; knockback 380; hitstun 0.3;
  hitstop 0.08; cooldown 0.9s after the attack ends.
- Dash: 0.5s; dash event moves at 900px/s during 0.06..0.34s; hitbox `[20,-190,120,140]` deals
  30 damage (`1.5 * atk`), `launch` 760, `knock_up` 1.5s, knockback 0, hitstun 0.3, hitstop 0.08;
  armor until 0.34s; cooldown 2.5s from the start. `combat.knock_up_gravity` (1013.333) replaces the
  normal gravity while `knock_up` is active, so the target stays airborne for about 1.5s.
- Axe throw: 1.2s; projectile at 0.35s on the high lane, speed 1250, range 420, 24 damage per pass
  (`1.2 * atk`; one hit out and one back, 48 total), knockback 150, hitstun 0.3, hitstop 0.08; armor
  until 0.34s; cooldown 2.8s from the start.
- Knock-up: `launch` sets `vy = -760` and `on_ground = false`; the target takes 0.3s hitstun and
  receives the `knock_up` status for 1.5s at hit time. While the status is active,
  `combat.knock_up_gravity` (1013.333) replaces normal gravity, so the target lands as the 1.5s
  window ends instead of standing locked on the ground for the remainder. The animation uses the
  jump frames while airborne; landing returns to idle and control. A lethal dash KOs in place without
  applying launch or `knock_up`. Super armor (the status effect or Warrior startup armor) suppresses
  both launch and the `knock_up` status. The hitstop is 0.08s. The wall-clock air time is slightly
  longer than 1.5s because hitstop pauses both the status timer and the physics.
- While a fighter has `knock_up`, a procedural cyan-white three-arm vortex with an elliptical outer
  ring is drawn behind its feet. It follows the airborne fighter for the full status duration and
  shrinks/fades linearly with `remaining / total` down to a minimum visible size and alpha
  (`min_scale` 0.75 / `min_alpha` 0.55), so it stays readable until the 1.5s window ends and then
  disappears immediately with the status. It resets to full on a refresh. Tuning lives in
  `combat.knock_up_fx`. The effect is draw-only: it does not change animation frames, state,
  collision, movement or hitstop.
- AI: always faces Lina; approaches when outside 160px; jumps when a block is in front; attacks when
  within 160px and the cooldown is ready; no crouch, no second attack, no pathfinding beyond jumps.
- Super armor: during axe startup+active (runtime time < 0.55s), a hit deals damage and flash but
  does not clear the attack, enter HURT, or apply hitstun/knockback. Recovery is interruptible. A
  lethal armored hit still KOs.
- Tick order: Lina updates first, then the enemy, then the hitstop gate. This gives the player the
  same-tick trade and lets startup armor complete visibly.
- Match flow: for enemies with `decides_match`, WIN is set when their HP reaches 0 and LOSE when
  Lina HP reaches 0; R restarts after a result and F9 resets at any time.

## Nyra Steel

- Playable character. Canonical art `Image/Character/nyra-steel-256.png`; fallback uses the same
  canonical file. Canvas 384x384, feet-center pivot (192,372), body about 214px.
- Frames (29 minimal set): idle 2, walk 2, jump 2, crouch 1, hurt 1, KO 2, sword slash 6 (Q), thrust 5,
  wave 5 (LMB), dash 3. Only right-facing frames are stored; the runtime mirrors for left. The crouch
  frame is imported at ~170px, midway between the original 212px crouch and the 128px deep-crouch
  variant, so it reads smaller than the 214px standing body without becoming tiny. The crouching
  hurtbox remains 56×130; only the image was changed.
- Stats: HP 100, basic ATK 20, extra ATK 0, `stage_body_width` 100, hurtbox 56x210 standing /
  56x130 crouching, walk 260, jump_v 760, gravity 2200. No energy resource. Q cooldown 8s,
  E cooldown 15s; both start ready.
- LMB sword wave: `1.0 * basic + 1.0 * extra` = 20, 0.30s; cast-anchored per-frame hitboxes active
  for the whole attack, knockback 160, hitstun 0.25, hitstop 0.06, one hit per target; adds 1 mark.
  The RMB thrust box `[28,-165,130,48]` applies during t=0..0.06 and 0.24..0.30; the extended box
  `[28,-212,162,123]` (reach 190) applies during t=0.06..0.24. It does not spawn a projectile and has
  no FX. The 5-frame clip is timed 0.06/0.06/0.06/0.06/0.06 (0.30s): high wind-up (sword about
  55-60° above horizontal), raise transition (~30°), horizontal contact, down transition (~20°
  below), and forward-down follow-through (~45°).
- RMB thrust: `1.2 * basic + 1.3 * extra` = 24, 0.40s; 5-frame clip timed
  0.08/0.08/0.08/0.08/0.08; hitbox `[28,-165,130,48]` active t=0.16..0.24; knockback 220; hitstun
  0.25; hitstop 0.07; adds 1 mark. The animation uses a longer blade than the base so the reach
  reads clearly.
- Q sword slash: `1.5 * basic + 1.5 * extra` = 30, 0.40s; cast-anchored hitboxes: the RMB thrust box
  during t=0..0.12 and 0.30..0.40, the extended box during t=0.12..0.30; same
  knockback/hitstun/hitstop as LMB, one hit per target. Adds 1 mark and can detonate the 4th; has
  super armor for the whole 0.40s (`armor_until: 0.4`). It does not spawn a projectile. The 6-frame
  slash clip is retimed 0.05/0.04/0.05/0.14/0.07/0.05 (0.40s):
  initial front-down 45° blade; a transition with the sword at 10-20° below horizontal and the arm
  extending; the redrawn v11 arm-forward frame (219px tall, feet aligned at 372); the thrust_v5_01
  long-sword contact; and two recovery frames. `game/slash_fx.py` plays six separate 384x384
  transparent blue slash-effect frames, triggered at t=0.04 and anchored at the cast position. Its
  durations are 0.02/0.02/0.05/0.14/0.07/0.05 (0.35s). The event is flagged at t=0.04 but first
  fires on the 60Hz t≈0.05 tick; the two short transparent frames compensate so effect frames 02-04
  align with the character's 02-04 frames at t=0.09-0.14 / 0.14-0.28 / 0.28-0.35 and overlap the
  extended hitbox window, ending at t≈0.40. Frames 00/01/05 are transparent; 02 appears, 03 peaks, 04 fades in place. The effect is
  never baked into the character frames.
- E dash thrust: `1.5 * basic + 1.8 * extra` = 30, 0.45s; dash event moves at 1100px/s during
  0.06..0.36s (~330px); hitbox `[0,-180,90,180]` active 0.06..0.36; knockback 250; hitstun 0.3;
  hitstop 0.08; super armor during the dash (`armor_until: 0.36`). `pass_through_enemy` skips body
  separation during the attack; walls and blocks still stop the dash. At dash end, `scene.push_apart`
  pushes the enemy to the far side, or pushes Nyra back if the enemy cannot be moved. Does not add or
  detonate marks.
- Marks: LMB/RMB/Q add exactly 1 mark per connecting attack (multi-hit/projectile events count
  once). Max 3. The 4th melee hit detonates all marks for `1.8 * atk + 10% target max HP`, applies
  damage reduction, then leaves exactly 1 mark. The burst adds 0.10s hitstop, emits particles and
  draws an expanding ring above the enemy. E neither adds nor detonates marks; Q adds and can
  detonate. Marks clear on reset and when the target dies.
- Mark display: 3 pips are drawn above the enemy's head, filled by current stacks; F2 shows
  `MARKS n/3 BURST ... LAST ...`. There is no numeric mark bar in the HUD.
- HUD: Nyra has no energy bar; the Q/E cooldown badges are shown for any player with `q_cd`/`e_cd`.
- Lock-on: `start_attack` calls `scene.face_target_if_locked`, so middle-mouse lock-on turns Nyra
  toward the living enemy at attack start.

## Veno-Spider

- Enemy. Canonical art `Image/Enemy/veno-spider-128.png`; fallback uses the same canonical file.
  Canvas 320x320, feet-center pivot (160,308), body about 150px.
- Frames (20 minimal set): idle 2, walk 2, hover 2, jump 2, hurt 1, KO 2, bite 3, poison 3, web 3.
  The hover clip is a hanging pose; the visible web strand is drawn by the scene, not baked into
  the frames. Idle and jump use a shared frame where necessary to keep body size locked.
- Stats: HP 50 (strict docx value), basic ATK 10, extra ATK 0, `stage_body_width` 140, hurtbox
  150x150, walk 320, jump_v 700, gravity 2200. Cooldowns: bite 1.8s, poison 3.5s, web 5.0s.
  Hover: base 220, min 140, max 300, vertical_speed 170, descend_speed 260, oscillation 80,
  oscillation_rate 1.2. AI: bite_range 150, close_range 140, ranged_range 700, hover_min_time 0.3.
- Bite: `1.5 * basic + 1.5 * extra` = 15, 0.50s; hitbox `[24,-120,110,90]` active t=0.18..0.30;
  knockback 120; hitstun 0.25; hitstop 0.05. The bite frames show the mouth wide open on frames
  0-1 and closing on frame 2.
- Poison spit: `0.8 * basic + 0.8 * extra` = 8, 0.60s; projectile `venom_glob` spawns at t=0.25,
  origin 100px above the feet, speed 520, range 800, knockback 40; hitstun 0.15; hitstop 0.04.
  On hit, applies poison at 3% of the target's max HP per second for 3s. Repeated hits from the
  same source (`veno_poison`) extend the remaining duration; different sources keep independent
  instances. The projectile aims at the target's position at fire time and does not home.
- Web shot: `1.0 * basic + 1.0 * extra` = 10, 0.65s; projectile `web_bolt` spawns at t=0.30,
  origin 100px above the feet, speed 480, range 800, knockback 60; hitstun 0.1; hitstop 0.04.
  On hit, applies 1s stun. Also aimed at the fire-time target position, no homing.
- AI: on the ground it faces the player and chases, bites when within 150px and the bite is ready,
  and ascends when the player is outside bite range and at least one ranged skill is ready. It can
  hop over a block when both ranged skills are cooling down. While hovering it prioritizes poison,
  then web; it descends when the player is within 140px, when both ranged skills are cooling down
  (after 0.5s of hover), or when hit while airborne. While descending it drifts toward the player
  if beyond bite range. An attack keeps the current mode and altitude.
- Hover height is a sine wave around 220px, clamped to 140-300px. The low part of the cycle brings
  the spider into melee and ground-hitbox reach (including Nyra's Q); the high part needs a jump
  attack. The scene draws a pale web strand from the top of the screen to the spider while
  ascending/hovering.
- Status visuals: poison draws a pulsing green overlay and green particles; stun draws rotating
  yellow stars above the head. F11 can force either status on any enemy for inspection.
- Single spawn only. `skill_slots` is `["veno_bite", "veno_poison", "veno_web", null]`;
  `separates` and `decides_match` are true. The docx `n=3` group is future multi-enemy work.
- Force/skill cooldowns: `force_attack` works on the ground or in the air, clears the three
  cooldowns, starts the requested attack and returns True; an empty Z slot is a safe no-op.
  `skill_remaining` returns the matching cooldown for F2.

## Roster and skill slots

- `game/data/roster.json` is the registry. Each character/enemy entry names its `class`, `stats`
  key, spawn key, animation table keys, frame folder, canonical fallback image, and (for enemies)
  `skill_slots`, `separates` and `decides_match`.
- `game/roster.py` builds the `AnimationPlayer` and the fighter class from that entry; the scene no
  longer constructs Lina/Nyra/Warrior/Veno/Dummy directly. Playable classes keep Lina's
  `update(dt, input_state, target, scene)` signature; Lina and Nyra are installed.
- F7 cycles the enemy roster in roster order (Warrior → Veno-Spider → training Dummy); `[` / `]`
  cycle the playable roster (Lina ↔ Nyra). Switching performs a full match reset: both fighters
  respawn at full HP, and
  projectiles, wave effects, particles, hitstop, statuses, cooldowns, the match result and the input buffer are
  cleared. The B block toggle is preserved; the enemy AI is forced off whenever fighters are rebuilt
  or reset — startup, F5 reload, roster switches, F9 and R — and F8 toggles it during a battle.
- `skill_slots` is a fixed 4-entry list of attack ids or `null`, in slot order. `V/C/X/Z` call
  `Fighter.force_skill(scene, target, 0..3)`, which resolves the id and calls the class's
  `force_attack`. Undefined slots and enemies without `force_attack` (Dummy) are safe no-ops. F2
  prints the four slots and their cooldowns (`-` for empty slots).
- Cooldown values stay in `stats.json` (`ai.attack_cooldown`, `ai.dash_cooldown`,
  `ai.throw_cooldown`); the roster only maps slot order to attack ids.
- Debug: F7 enemy roster, `[` / `]` character roster, F8 AI/invincibility, V/C/X/Z skill slots,
  arrows move the enemy, PgUp/PgDn change enemy HP.

## Out of scope in the current sandbox

Daily phases, food/fullness, shop/gold, saves, audio, the full HUD, playable characters beyond
Lina/Nyra, enemies beyond Warrior/Veno/Dummy and their AI, multi-enemy encounters (`n=3`),
packaging and automated tests/logs. The training dummy is a debug tool, not a spec enemy.
