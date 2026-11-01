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
- Knockback is 300px/s for Lina's kick and 150px/s for Q, 160/220/250 for Nyra's wave/thrust/dash,
  and 60 for Rhea's LMB; Rhea's RMB/Q/E are zero. It decays over 0.35s.
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
- 43 dedicated flame-form frames were generated from the normal pose references using multi-image
  fusion (pose image + `transform_04`):
  idle 4, walk 6, jump 2, crouch 1, punch_l/r 4+4, kick_l/r 4+4, Q 4, hurt 2, KO 4, revert 2,
  climb 2.
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
- Poison: Veno's glob uses 2% max HP/s for 3s; Rhea's Q uses 3% max HP/s for 5s from the
  `rhea_poison` source. Same source reapplies and extends the duration; different sources keep
  independent instances that each deal damage. Poison settles every 0.5s. `StatusSet.extend_poison`
  only extends an existing source and never creates one; Rhea's LMB/RMB extend `rhea_poison` by 1s,
  while Q does not trigger the passive.
- Super armor makes the fighter immune to control effects (knockback, knock_up, freeze, stun,
  slow) while it is active; damage still applies and damage reduction is a separate percentage
  multiplier. Nyra's Q and E and Rhea's E (0.0–1.00s) use it during their armor windows.

- The sandbox naturally triggers burn (flame hits), knockback (kick/Q), and knock-up (Warrior dash);
  stun, freeze, slow, poison, super armor and damage reduction are available through F11.

## Stage and projectile heights

- 1280x720 logical resolution; background scaled from 1664x936; fixed camera.
- Ground y=620; walls at x=90 and x=1190. The default stage has two ground barriers:
  x=400..490 and x=700..790. The Creepy Shooter variant keeps only the right barrier
  x=790..880; its left barrier (400..490) was removed on 2026-11-01 at the user's request.
  Two platforms: x=170..649 at surface y=220 and x=796..1110 at surface y=268; each collision
  rect is 78px tall. Ladders: x=508..572 (long, 400px) and x=921..985 (medium, 352px).
- Lina spawns at x=280; the dummy, Warrior, Veno and Bat base spawns are at x=600 (Bat base y=470).
  Creepy Shooter spawns at (1000, 220) on its stage variant. The current default enemy is Creepy
  Shooter; F7 selects the others.
- Fighters keep a minimum center distance equal to the sum of their stage body half-widths
  (Lina 50 + Warrior 60 = 110px). The enemy yields first on his current side; if a wall/barrier/platform
  blocks that side, he is not flipped across the player — Lina is pushed to the free side instead.
  Separation moves at most `combat.separation_speed × dt` (600px/s), so a deep overlap slides apart
  over a few ticks instead of teleporting. Warrior facing ignores targets within an 8px deadzone,
  so overlapping bodies cannot flip the sprite every tick.
- Stage collision uses a wider grounded body than the 56px combat hurtbox: Lina's
  `stage_body_width` is 100px, so her front boot stops at a barrier/platform edge instead of
  entering it. While airborne, collision falls back to the hurtbox width so stepping off a ledge
  does not snap the character sideways. Attack lunges use the same stage collision, not a direct
  x change.
- Barriers are solid AABBs. Platforms are full AABBs: the top is standable, the sides block
  horizontal movement, and the underside stops a rising body. Landing on a top requires the feet
  center to be within 8px of the span (`land_margin`). A fighter embedded by a B re-enable or a
  spawn is pushed to the nearest free side (`Stage.resolve_overlap`). Platform outer edges are
  inset 80px from the walls so a character can walk off; there is no fall damage.
- B toggles barrier + platform drawing and collision for observation; ladders have no volume and
  stay visible/climbable. With B off, reaching a ladder top holds the character on the ladder
  instead of mounting the platform. The AI also stops jumping when blocks are off. The toggle
  persists across F9 and resets on F5/rebuild.
- A climber on a ladder with a top platform mounts early once the feet reach
  `platform.top + (platform.bottom - platform.top) / 2 - 6px` (the platform's vertical midpoint
  slightly upward), instead of waiting for the ladder's `top_y`. The character snaps to the platform
  surface, exits the climb and stands; holding/repressing W around the threshold completes the
  mount. The old hold-at-top behavior remains only when blocks are off or the ladder has no
  platform.
- Projectile lane heights are measured upward from the attacker's feet: high 180px, fist 142px,
  mid 120px, low 60px. Lina Q spawns at `attacker.y - 142`, so it is screen y 478 on flat ground
  and y 418 while she stands on a 60px barrier; on a platform the same offset applies from its
  surface. The ball keeps that spawn height in flight. Rhea's RMB/Q shuriken uses the mid lane,
  speed 850, range 900 and radius 12; a body-adjacent check (Rhea's hurtbox inflated by 24px)
  resolves point-blank throws before the star travels.
- This makes the Q trajectory follow Lina vertically instead of staying on a fixed world lane.
- Lina's sprite body height is approximately 210px, anchored at the feet-center pivot (128,244) on a
  256x256 canvas. Warrior uses a 384x384 canvas with pivot (192,372) and a body height of about 230px.

## Stage props and climbing

- `game/data/debug.json` `stage.blocks` is a list of `{kind, rect, ...}` entries. `kind: "barrier"`
  is a solid obstacle; `kind: "platform"` is a standable solid with an optional sprite.
  `Stage.blocks` is the combined solid-rect view used by movement, AI, separation and projectiles;
  `Stage.barriers` and `Stage.platforms` are filtered views. `stage.ladders` is a separate list of
  `Ladder` objects and is never added to `Stage.blocks`.
- Platform sprites (`platform_tropical_long.png`, `platform_tropical_short.png`) are copied from
  `assets/generated/contact_sheets/` to `assets/sprites/stage/` and rendered at 0.6 scale. The
  `sprite_rect` is separate from the collision `rect`; `surface_y` (or `rect.top`) is the standable
  line. The collision height is 78px, leaving the decorative grass/rock fringe outside the solid.
- Current first-pass layout: long platform x=170..649 at y=220; short platform x=796..1110 at
  y=268; long ladder x=508..572 (400px) using `ladder_tropical_wood.png`; medium ladder x=921..985
  (352px) using `ladder_tropical_wood_medium.png` (native 160px width; the long ladder is rendered
  128px wide). Ground barriers are at x=400..490 and x=700..790. No barriers are placed on the
  platforms in this pass. The Creepy Shooter stage variant (`debug.json`
  `stage_variants.creepy_shooter`) mirrors the platform/ladder layout: long platform 601–1080 at
  y=220, short platform 170–484 at y=268, long ladder 708–772, medium ladder 295–359; its only
  remaining ground barrier is 790–880 (the left 400–490 barrier was removed 2026-11-01). The
  Creepy spawn is (1000,220).
- The short platform bottom is 346px, so a 230px Warrior standing on the ground (head ~390px) and
  a 210px Lina (head ~410px) can walk underneath it. The medium ladder is fully inside the short
  platform's x-span, and both ladders sit under their platforms.
- Climbing: `InputState` exposes `climb_up` (W) and `climb_down` (S) held actions in addition to
  the normal jump/crouch mapping; `Space` is a separate `climb_jump`. On a ladder, W climbs,
  S descends, Space jumps off, and Shift stays crouch-only. The climb state locks x to the ladder
  center, ignores solids, and plays the dedicated back-view climb clip described below. A ladder
  with a top platform mounts at the midpoint threshold described above and sets `on_ground`;
  reaching the bottom returns to the ground. Attacks, hits, stun and KO exit the climb; a short
  suppression prevents held W from immediately re-grabbing after a deliberate exit.
  A ladder hit keeps the knock-off: the climb is cleared immediately and normal knockback/fall
  applies. If the feet are inside a platform `rect` at the hit, the character snaps to that
  platform's top and is treated as grounded; otherwise they fall. A `ladder_fall` flag, also set
  by a Space jump-off, skips platform side and underside collision until landing so a platform
  behind the ladder cannot shove the falling/jumping body sideways; platform-top landing still
  applies. There is no automatic re-grab after a ladder hit. Lina, Nyra and Rhea share the
  implementation in `Fighter`; enemies never call it.
- `penetrates_blocks` is an optional projectile flag on `QWave`, `SwordWave`, `AimedProjectile`,
  `SonicWave` and `ShurikenProjectile`; every block collision site honours it. It defaults to
  false; Creepy Shooter's skill-2 homing bolt sets it true. Eira Frostveil's E ice ball remains
  unimplemented. `AxeThrow` and melee hitboxes remain as before (no block occlusion).
- Debug: F1 draws barrier boxes in yellow, platform boxes in cyan, and ladder trigger boxes in
  magenta with green/red top/bottom lines. F2 shows `BARRIERS n PLATFORMS n` and
  `CLIMB up/down/idle`. B toggles barrier+platform rendering/collision; ladders stay visible and
  climbable.

## Climb animations (playable characters)

- Standard is a direct back view: frame 0 has the character-left hand high and right leg high;
  frame 1 has the right hand high and left leg high. Each frame lasts 0.20s; the clip loops while
  the character moves (up 0→1→0, down 1→0→1) and holds the current frame when the character stops.
  The back view is not horizontally flipped while climbing; the pre-climb facing is restored on
  exit.
- Lina normal (`climb/`) and flame (`flame/climb/`) each have a dedicated two-frame clip;
  `flame_offsets` are 0 for both flame climb frames. Nyra (`climb/`) has her own two-frame clip.
  Nyra's base and frames keep the single long silver sword sheathed diagonally across her back
  (hilt above her right shoulder, tip toward her lower-left hip); both hands are free. In frame 01
  the raised right arm passes in front of the hilt but does not grip it. Rhea (`climb/`) has her
  own two-frame back-view clip with both hands free and the two four-blade shuriken stowed on the
  gold-striped back band.
- Runtime clips live in `game/data/animations.json` under `clips.climb`,
  `flame_clips.climb`, `nyra_clips.climb` and `rhea_clips.climb`; `game/config.py` requires
  `climb` for Lina normal, Lina flame, Nyra and Rhea. `FighterState.CLIMB` plus
  `Fighter.try_start_climb`/`_update_climb` choose the variant-appropriate clip and start frame;
  `_stop_climb` restores facing.
- The climb sprite is drawn with a character-specific visual scale around the feet pivot:
  Lina 1.2× (default `CLIMB_DRAW_SCALE`), Nyra 1.1× (`NYRA_CLIMB_DRAW_SCALE`) and Rhea 1.1×
  (`RHEA_CLIMB_DRAW_SCALE`). `AnimationPlayer.draw(scale=...)` scales the frame and pivot around
  the feet; only the climb clip is scaled. Lina's canonical bbox is ~253px and her climb frames are
  ~209/211px; Nyra's canonical bbox is ~243px and her staged climb frames are ~220/216px; Rhea's
  climb frames are staged at body 214px. Nyra frame 00 is staged 1.02× relative to frame 01 to
  match the silhouette; this is a one-time staging normalization, not per-frame runtime
  auto-scaling. Combat hurtboxes and stage collision are unchanged; F1 shows the unscaled boxes.
- Smoke covers `lina_climb_anim_ok`, `lina_climb_facing_ok`, `lina_flame_climb_anim_ok`,
  `nyra_climb_anim_ok` and `rhea_climb_ok`, plus `ladder_mount_early_ok` (midpoint mount) and
  `ladder_jump_overlap_ok` (jump-off ignores platform sides/underside) and the Creepy ladder-hit
  flags. Enemy climb art/AI is not implemented; the data-driven clip path exists for a future
  explicitly specified enemy, but no enemy currently uses it.

## Warrior (Phase 2)

- The current sandbox default is a single Warrior; the five-Bat group is selectable through F7.
  The training Dummy remains available through F7. Dummy mode is training-only and does not show a
  win/loss banner.
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
- AI: always faces Lina; approaches when outside 160px; jumps when a solid barrier/platform is in front; attacks when
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
- Frames (31 minimal set): idle 2, walk 2, jump 2, crouch 1, hurt 1, KO 2, sword slash 6 (Q), thrust 5,
  wave 5 (LMB), dash 3, climb 2. Only right-facing frames are stored; the runtime mirrors for left.
  The back-view climb is the exception and is not horizontally flipped; the sword stays sheathed
  on her back. The crouch
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
  separation during the attack; walls and solid barriers/platforms still stop the dash. At dash end, `scene.push_apart`
  pushes the enemy to the far side, or pushes Nyra back if the enemy cannot be moved. Does not add or
  detonate marks.
- Marks: LMB/RMB/Q add exactly 1 mark per connecting attack (multi-hit/projectile events count
  once). Max 3. The 4th melee hit detonates all marks for `1.8 * atk + 10% target max HP`, applies
  damage reduction, then leaves exactly 1 mark. The burst adds 0.10s hitstop, emits particles and
  draws an expanding ring above the enemy. E neither adds nor detonates marks; Q adds and can
  detonate. Marks live on each **target** (`Fighter.marks`, `mark_burst_time`,
  `mark_burst_damage`), so every enemy in a multi-enemy encounter has an independent stack and
  detonates separately; a stack clears when that target dies or the scene resets. `Nyra.mark_detonations`
  is only a running total for smoke/F2.
- Mark display: 3 pips are drawn above **each living enemy's** head, filled by that target's stack;
  the burst ring is drawn on the detonated target. F2 shows the primary enemy's
  `MARKS n/3 BURST ... LAST ...` plus Nyra's total `BURSTS`. There is no numeric mark bar in the HUD.
- HUD: Nyra has no energy bar; the Q/E cooldown badges are shown for any player with `q_cd`/`e_cd`.
- Lock-on: `start_attack` calls `scene.face_target_if_locked`, so middle-mouse lock-on turns Nyra
  toward the living enemy at attack start.

## Rhea Thorn (2026-11-01)

- Playable character. Canonical art `Image/Character/rhea-thorn-256.png`; fallback uses the same
  file. Canvas 384x384, feet-center pivot (192,372), body 214px. Only right-facing frames are
  stored; the runtime mirrors for left. The back-view climb clip is never horizontally flipped.
- Frames (33): idle 2, walk 4, jump 2, crouch 1, hurt 2, KO 3, `rhea_slash_r` 3,
  `rhea_slash_l` 3, `rhea_throw` 3, `rhea_poison_throw` 3, `rhea_dash` 5, climb 2. Durations:
  idle 0.30/0.30; walk 0.12×4; jump 0.20/0.20; crouch 0.30; hurt 0.10/0.10; KO
  0.25/0.20/0.25 (kneel → transition → lying head-right); slash clips 0.08/0.08/0.09;
  `rhea_throw` 0.10/0.08/0.17; `rhea_poison_throw` 0.12/0.10/0.23; `rhea_dash`
  0.06/0.20/0.20/0.14/0.40 (1.00s); climb 0.20/0.20. `rhea_slash` is an attack id only; the
  class selects `rhea_slash_r/l`.
- Stats: HP 100, basic ATK 20, extra ATK 0, `stage_body_width` 100, hurtbox 56×210 standing /
  56×130 crouching, walk 260, jump_v 760, gravity 2200. No energy resource. Q cooldown 8s,
  E cooldown 15s; both start ready and are consumed at attack start.
- LMB `rhea_slash`: `1.0×basic + 1.0×extra` = 20, 0.25s, small lunge 18px at t=0.08;
  hitbox `[28,-165,70,48]` active t=0.08–0.14; knockback 60 (the only Rhea attack with
  knockback), hitstun 0.20, hitstop 0.05. The first successful LMB uses the right hand
  (`rhea_slash_r`), the next uses the left (`rhea_slash_l`), then alternates; RMB/Q/E never
  change the alternation. Each connecting LMB extends an existing `rhea_poison` by 1s.
- RMB `rhea_throw`: `1.2×basic + 1.3×extra` = 24, 0.35s, projectile at t=0.14. Steel
  four-blade `ShurikenProjectile`, mid lane (120px above the feet), speed 850, range 900,
  radius 12, knockback 0, hitstun 0.15, hitstop 0.04; single hit, dies on hit/range/wall/block.
  A body-adjacent check (Rhea's hurtbox inflated 24px) resolves the hit at point-blank before
  the star travels; a successful RMB extends an existing `rhea_poison` by 1s. No cooldown.
- Q `rhea_poison_throw`: `1.2×basic + 1.2×extra` = 24 plus 8% of the actual target's max HP,
  resolved at projectile hit time (200 HP → 40, 300 → 48, 1000 → 104), 0.45s, projectile at
  t=0.18. Poison-coated star (green/purple), same mid lane/speed 850/range 900/radius 12/
  knockback 0/block rules as RMB. On hit, applies `poison` from source `rhea_poison` for 5.0s
  at 3% of the target's max HP per second (200 HP → 6/s, 30 total; 300 → 9/s, 45 total;
  1000 → 30/s, 150 total). Same-source reapplication adds +5s to the remaining time (2s → 7s,
  not +6s); different sources remain independent. Q does not trigger the LMB/RMB +1s passive.
  If the initial hit kills the target, no poison is applied. 8s cooldown from attack start.
- Passive `rhea_poison` extension: LMB/RMB only call `StatusSet.extend_poison("rhea_poison", 1.0)`
  when the target is alive, not invincible, and already has that source. It never creates poison,
  does not refresh or change the dps, is capped at one extension per target per attack (the set
  is cleared at every `start_attack`), has no duration cap, and never affects Veno's poison.
- E `rhea_dash`: `0.7×basic + 0.8×extra` = 14 per segment, 1.00s total, 15s cooldown.
  Outbound movement 1100px/s during t=0.06–0.60 (~594px, roughly twice the earlier 300px);
  return at 1500px/s during t=0.60–1.00 (~600px) back to `cast_x`. Facing is not changed during
  the attack; the 5-frame clip's fourth frame carries the turn. `pass_through_enemy` skips body
  separation; walls and solid blocks stop the dash; `scene.push_apart` runs at the end. Two
  hitbox groups: outbound `[0,-170,90,170]` with `hit_group: "out"` during t=0.06–0.60, one
  hit per target, plus 15% of the target's max HP if it has poison from any source; return
  `[-90,-170,90,170]` with `hit_group: "back"` during t=0.60–1.00, one hit per target, no
  poison bonus. Knockback 0, hitstun 0.25, hitstop 0.06. Super armor covers the full
  0.0–1.00s (`armor_from: 0.0`, `armor_until: 1.00`). Damage numbers: 200 HP poisoned
  44+14=58 (50% DR: 22+7=29); 300 HP poisoned 59+14=73 (50% DR: 29.5+7=36.5);
  unpoisoned 14+14=28.
- HUD/F2: no energy bar; Q/E cooldown badges reuse the generic HUD. F2 shows `CHAR rhea 3/3`,
  q/e cooldowns and the target's `poison[rhea_poison]` remaining time; there is no passive
  gauge or `POISON EXT` counter.
- Assets/FX: `assets/frames/rhea/` (33 frames; `rhea_dash` face-aligned to a common anchor);
  `assets/frames/rhea/fx/` has six 64×64 transparent star frames
  (`rhea_shuriken_00..02`, `rhea_poison_shuriken_00..02`, the 0°/30°/60° spin). Steel and poison
  projectiles draw a 48px star; the poison one adds a green/purple trail. Cast/impact FX are
  procedural (steel spark ring, poison splash/ring/particles); E draws two programmatic
  afterimages during the dash. No FX is baked into character frames.
- `ShurikenProjectile` carries `kind`, `visual_kind`, `damage`, `bonus_target_max_hp_pct`,
  `status/status_duration/status_dps_pct`, `extends_poison`, `hit_color`, knockback/hitstun/
  hitstop and `flame_bonus=0`, so `resolve_projectile_hit` works unchanged apart from the added
  max-HP bonus. `AttackRuntime.hit_targets` is a `dict[str, set[int]]` keyed by `hit_group`
  (default `"default"`), preserving existing one-hit behavior for every earlier attack.
- Smoke flags: `rhea_present`, `rhea_roster_order_ok`, `rhea_default_ok`, `rhea_knockback_ok`,
  `rhea_lmb_ok`, `rhea_passive_ok`, `rhea_rmb_ok`, `rhea_q_ok`, `rhea_q_300_ok`,
  `rhea_q_dummy_ok`, `rhea_q_dr_ok`, `rhea_q_stack_ok`, `rhea_q_kill_ok`,
  `rhea_close_range_ok`, `rhea_range_ok`, `rhea_dash_ok`, `rhea_e_poison_ok`,
  `rhea_e_poison_300_ok`, `rhea_e_dr_ok`, `rhea_e_armor_ok`, `rhea_e_block_ok`,
  `rhea_projectile_block_ok`, `rhea_cleanup_ok`, `rhea_climb_ok`,
  `rhea_missing_frames == 0`, `rhea_fx_missing == 0`, plus `default_hit_group_ok`
  (Nyra's multi-hitbox attack still hits once).

## Veno-Spider

- Enemy. Canonical art `Image/Enemy/veno-spider-128.png`; fallback uses the same canonical file.
  Source frames are 320x320 (pivot 160,308, body ~150px), but the 2026-10-24 small-body variant
  renders them at **160x160 / pivot (80,154) / body ~75px** — exactly half size. The source PNGs are
  unchanged; `AnimationPlayer` downscales them at load.
- Frames (20 minimal set): idle 2, walk 2, hover 2, jump 2, hurt 1, KO 2, bite 3, poison 3, web 3.
  The hover clip is a hanging pose; the visible web strand is drawn by the scene, not baked into
  the frames. Idle and jump use a shared frame where necessary to keep body size locked.
- Stats: HP 50 (strict docx value), basic ATK 10, extra ATK 0, `stage_body_width` 70, hurtbox
  75x75, walk 320, jump_v 700, gravity 2200. Cooldowns (per updated instruction.docx, tracked
  independently per Veno): bite 1.0s, poison 5.0s, web 8.0s.
  Hover: base 220, min 140, max 300, vertical_speed 170, descend_speed 260, oscillation 80,
  oscillation_rate 1.2. AI: bite_range 75, close_range 70, ranged_range 700, hover_min_time 0.3.
- Bite: `1.5 * basic + 1.5 * extra` = 15, 0.50s; hitbox `[12,-60,55,45]` active t=0.18..0.30;
  knockback 120; hitstun 0.25; hitstop 0.05. The bite arc is drawn at y-40. The bite frames show
  the mouth wide open on frames 0-1 and closing on frame 2.
- Consequence of the small body: Lina's punch (y 455-503) and Q lane (y 461-495) sit above the
  ground Veno's 75px hurtbox (y 545-620); her kick (y 495-557) still clips it. The smoke win test
  uses a kick. This is the intended trade-off of the half-size body; if the hurtbox is raised or
  the punch/Q lanes are changed later, re-check the Veno match-up.
- Poison spit: `0.8 * basic + 0.8 * extra` = 8, 0.60s; projectile `venom_glob` spawns at t=0.25,
  origin 50px above the feet, speed 520, range 800, knockback 40; hitstun 0.15; hitstop 0.04.
  On hit, applies poison at 3% of the target's max HP per second for 3s. Poison damage settles in
  0.5s chunks (`POISON_TICK`), so a full tick is 1.5 damage at Lina's 100 max HP; the total damage
  over the duration is unchanged. Repeated hits from the same source (`veno_poison`) extend the
  remaining duration; different sources keep independent instances. The projectile aims at the
  target's position at fire time and does not home. The glob and its cast/impact effects use a
  dark-green palette (deep-green shell, mid-green body, light-green highlight).
- Web shot: `1.0 * basic + 1.0 * extra` = 10, 0.65s; projectile `web_bolt` spawns at t=0.30,
  origin 50px above the feet, speed 480, range 800, knockback 60; hitstun 0.1; hitstop 0.04.
  On hit, applies 1s stun. Also aimed at the fire-time target position, no homing. Collision
  radius 30 (visual 64px; impact decal 150–170px).
- AI: on the ground it faces the player and chases, bites when within 75px and the bite is ready,
  and ascends when the player is outside bite range and at least one ranged skill is ready. It can
  hop over a barrier/platform when both ranged skills are cooling down. While hovering it prioritizes poison,
  then web; it descends when the player is within 70px, when both ranged skills are cooling down
  (after 0.5s of hover), or when hit while airborne. While descending it drifts toward the player
  if beyond bite range. An attack keeps the current mode and altitude.
- The lower 50px projectile origins mean the smaller Veno's poison/web are more easily blocked by
  barriers/platforms; the smoke damage/status tests disable block collision to isolate the
  projectile logic. This is a consequence of scaling the mouth to the half-size body.
- Hover height is a sine wave around 220px, clamped to 140-300px. The low part of the cycle brings
  the spider into melee and ground-hitbox reach (including Nyra's Q); the high part needs a jump
  attack. The scene draws a pale web strand from the top of the screen to the spider while
  ascending/hovering.
- Status visuals: poison draws no hurtbox rectangle. The fighter's whole current frame is
  multiplied by a green tint `(70,255,110)` or a purple tint `(220,100,255)`, alternating every
  0.18s; green poison particles are still emitted every 2 ticks. Stun draws rotating yellow stars
  above the head. F11 can force either status on any enemy for inspection.
- Group spawn: `roster.json` sets Veno `count` 3, `spawn_offsets` `[-100, 0, 120]` and
  `spawn_modes` `["ground", "hover", "hover"]`. Selecting Veno creates three half-size Venos
  (default positions 500/600/720 with the x=600 spawn; one ground + two hanging). `scene.enemies` holds the group;
  `scene.enemy` is the nearest living primary for HUD/lock-on/player targeting. The player's melee
  hitboxes test every living enemy (`AttackRuntime.targets`), projectiles hit the first living
  enemy they collide with, and each Veno runs its own AI. Enemies also separate from each other.
  Every Veno owns its own bite/poison/web cooldown timers (`bite_cd`, `poison_cd`, `web_cd`) and
  its own poison source, so one spider's skill use or poison never affects another. Nyra's marks
  are likewise stored per target. The match is won only when all three are dead; the smoke forces
  `enemy_count_override=1` for the isolated single-enemy checks and verifies the 3-body group,
  per-instance cooldowns and all-dead WIN separately.
- Poison stacking (instruction.docx 战斗系统): reapplying poison from the **same source** adds the
  new duration to the remaining time (2s remaining + 3s = 5s); a **different source** creates an
  independent instance (both tick and both deal damage). Each Veno instance uses a unique
  `poison_source` (`veno_poison:<id>`), so poisons from different spiders are independent while a
  spider's own reapplication extends. The smoke checks this exact 2+3=5 and two-source behavior
  (`poison_stack_rules_ok`).
- `skill_slots` is `["veno_bite", "veno_poison", "veno_web", null]`; `separates` and
  `decides_match` are true.
- Force/skill cooldowns: `force_attack` works on the ground or in the air, clears the instance's
  three cooldowns, starts the requested attack and returns True; an empty Z slot is a safe no-op.
  `skill_remaining` returns the matching cooldown for F2. These timers are per Veno instance.

## Bat

- Enemy. Canonical art `Image/Enemy/bat-128.png`; fallback uses the same file. Source frames
  384x384, runtime 192x192 (`AnimationPlayer` downscales); pivot (115,143), body ~150px, hurtbox
  100x66 bottom-anchored.
- Frames (14): wing 4 (shared `idle`/`fly`), dive 3, sonic 3, hurt 1, stun 1, KO 2. `idle` is the
  6-step ping-pong slow wing loop; `fly` is the 4-frame fast loop. Only right-facing frames are
  stored; the runtime mirrors for left. `bat_dive`/`bat_sonic` are non-looping 0.75s/0.65s clips.
- Stats: HP 50, basic ATK 10, extra ATK 0, `stage_body_width` 56, move walk 300, jump_v 0,
  gravity 2200. Gravity is used only for the KO fall; flight never applies it.
- Flight: mode `fly`; no gravity; x clamped to the arena walls; altitude 40-420 above ground
  (y = ground_y - height), preferred 240 with a sine bob of 24 at 1.5 rad/s; vertical speed 300.
  The five-Bat group spawns and cruises at 180/320/240/380/280px, so the group occupies different
  heights. The body respects barrier/platform AABBs; at cruise heights it passes above ground
  barriers, while low flight or a downward path can meet the actual barrier/platform volume.
- Cooldowns are per instance: dive 2.0s, sonic 10.0s, set at attack start. The dive is deterministic:
  it fires when ready and `_dive_can_reach` confirms the dive hitbox can reach the target from the
  current altitude; otherwise the Bat keeps flying. The sonic is the only randomly-timed skill: a
  random 0-2.5s opening cooldown plus a 50% per-decision cast gate. A 0.55s group stagger prevents
  another living Bat from opening the same skill. When the sonic is available, the random gate
  decides whether to cast it; if skipped, the dive fires when reachable; otherwise the Bat keeps
  flying/repositions to standoff 220. The sonic uses the [120,700] range; `decision_interval` 0.15
  throttles attack decisions.
- Dive: 0.75s; the direction is locked at attack start toward the target's mid-hurtbox (no homing);
  520px/s during t=0.05-0.30; hitbox `[0,-70,90,70]` active t=0.12-0.34 follows the body; 10 damage,
  knockback 160, hitstun 0.25, hitstop 0.06, plus a small purple dive hit FX.
- Sonic: 0.65s cast lock; the projectile spawns at t=0.24 from 46px forward / 30px above the Bat's
  feet, aimed at the target's mid-hurtbox at spawn (no homing); speed 420, range 3000 as a leak cap,
  timeout 8s; 12 damage, 1s stun, knockback 0, hitstun 0.1, hitstop 0.05. Its hitbox is a forward
  circle (+8px along travel, radius 24) matching the Wi-Fi arc silhouette; walls, top/ground and
  barrier/platform AABBs bounce it into the return phase; hitting the player deals damage and
  latches the one-hit guard. On return it tracks the owner's current position, vanishes within
  16px, passes through the player and can deal the single hit on the way back; if the owner dies
  it survives at most 0.5s; a barrier/platform on the return path absorbs it. The arc direction
  and hitbox both follow the actual return direction.
- Sonic VFX: procedural Wi-Fi/signal arcs (three nested arcs opening along travel, an emitter dot
  and a short trail), no baked frames; `RingBurstFx` cast and impact flashes use the same palette.
- Match selection: `debug.json` `default_enemy` is `creepy_shooter`; the Bat group is selected with
  F7 and its roster `count` is 5. F7 order is Warrior -> Veno -> Bat -> Creepy Shooter -> Dummy.
  Five spawn offsets and five
  spawn heights (180/320/240/380/280) are used. Hurt/stun stay airborne; only KO falls to the ground
  and switches to `ko_01`. `show_health_bar` is true; F2 shows `MODE fly` and `HOVER` altitude.
- `skill_slots` is `["bat_dive","bat_sonic",null,null]`; `separates` and `decides_match` are true;
  `force_attack` works airborne and clears both timers.

## Creepy Shooter (2026-10-30)

- Enemy. Canonical art `Image/Enemy/creepy-shooter-256.png`; fallback uses the same file. Approved
  side base `assets/generated/base/creepy_shooter_side_base.png`; frames 384x384, pivot (192,372),
  body 214, hurtbox 56x210 standing / 56x130 crouching (the rifle is excluded), `stage_body_width`
  100. Only right-facing frames are stored; the runtime mirrors for left.
- Frames (29): idle 2, walk 4, crouch 1, jump 2, hurt 2, KO 2, `creepy_shot` 2,
  `creepy_homing_shot` 4, `creepy_roll_shot` 6, `creepy_jump_shot` 4. Clip durations are
  `[0.30]` idle loop, `[0.12]*4` walk, `[0.50]` crouch, `[0.20]*2` jump, `[0.10]*2` hurt,
  `[0.35]*2` KO, `creepy_shot` `[0.18,0.27]`, `creepy_homing_shot` `[0.15,0.85,0.10,0.45]`,
  `creepy_roll_shot` `[0.14,0.13,0.13,0.10,0.18,0.22]`, `creepy_jump_shot` `[0.10,0.15,0.70,0.15]`.
  The roll set is imported at 0.9x (body 193); its final standing frame is ~211px, matching Lina's
  ~210px build instead of the earlier 1.10x/234px exception.
- Stats: HP 200, basic ATK 20, extra ATK 0; walk 220, jump_v 700, gravity 2200. Cooldowns are
  `shot` 1s, `homing` 8s, `roll` 10s and `jump` 10s, set at attack start and per instance. AI values:
  `near_range` 180, `far_range` 320, `level_tolerance` 60, `decision_interval` 0.15,
  `roll_distance` 140, `roll_time` 0.28, `platform_reach` 180, `jump_heights` [220, 268].
- Skill 1 `creepy_shot`: 0.45s action, shot at t=0.18; 1.5x ATK = 30; strictly horizontal at the
  mid lane; speed 980, range 900, radius 9, knockback 40; blocked by barriers/platforms. The bullet
  spawns at the measured muzzle, 163px above and 129px forward of the feet, rather than at a lane
  height.
- Skill 2 `creepy_homing_shot`: 1.55s action; 1s interruptible wind-up (a hit or KO cancels the
  shot but the 8s cooldown is already consumed), fired at t=1.0 from 143px up / 111px forward.
  The bolt re-aims at the target's hurtbox center every tick, penetrates blocks and platforms,
  deals 20 once, has an 8s lifetime, speed 520 and radius 14. It is not removed when the owner is
  KO'd after firing. During the wind-up the player carries a three-frame reticle (large / small red
  dot / large at 0.30/0.40/0.30s) drawn at chest height; it is visual only and has no hitbox.
- Skill 3 `creepy_roll_shot`: triggers within 180px; crouch, roll backward 140px over 0.28s with no
  i-frames, fire at t=0.30, then crouch and stand (0.90s total); 1.2x ATK = 24, speed 900, range
  700, radius 9, knockback 40, cooldown 10s. Walls and blocks clip the roll; a platform edge does
  not. Rolling past the edge clears `on_ground` and the shooter falls under gravity for the rest of
  the action. The shot leaves the muzzle 120px up / 100px forward.
- Skill 4 `creepy_jump_shot`: cooldown 10s; 1.10s action. It only starts on the ground and within
  10px of a valid takeoff point beside a reachable platform (surface 220 or 268). Phase 1 rises
  vertically to 80px above the surface, then phase 2 drifts horizontally onto it; the hard timeout
  is 1.6s. The shot fires at t=0.10 from 120px up / 100px forward, aims at the player when the
  target is below and inside a ±45° cone (`atan2(dx, dy)`, `dy > 0`), otherwise straight down;
  1.2x ATK = 24, speed 900, range 600, radius 12, blocked by blocks. With no eligible platform,
  `force_attack` returns False.
- AI: on a platform, within 180px uses skill 3; if the horizontal line to the player is blocked or
  the level differs by more than 60px, uses skill 2; otherwise skill 1, with skill 2 also used at
  `far_range` when ready. On the ground, within 180px uses skill 3; otherwise it plans a platform
  return, uses skill 1 when the line is clear, skill 2 when it is not, walks to the takeoff, and
  uses skill 4 when ready. A ground barrier in the path triggers a hop (`vy = -jump_v*1.15`,
  `vx = facing*walk*2.0`) strong enough to clear a 90px barrier. Attacks and decisions are
  throttled by `decision_interval`; the AI never walks and attacks on the same tick.
- Stage: `debug.json` `stage_variants.creepy_shooter` mirrors the default platform/ladder layout.
  Long platform `[601,220,479,78]`, short platform `[170,268,314,78]`, ladders
  `[708,220,64,400]` and `[295,268,64,352]`, and only the right ground barrier
  `[790,560,90,60]`; the left `[400,560,90,60]` barrier was removed on 2026-11-01 at the user's
  request. Player spawn (280,620); Creepy spawns at (1000,220) on the long platform.
  `roster.json` names the variant and `ArenaScene` selects it by enemy; switching enemies rebuilds
  the Stage and preserves the B block toggle.
- Projectiles: `CreepyBullet` (straight, one hit, dies on range/wall/block/hit, cyan 2-frame
  tracer), `CreepyHomingBullet` (violet 3-frame bolt rotated to travel, one hit, penetrates blocks
  and platforms, 8s lifetime, not owner-KO-bound) and `CreepyDownBullet` (fixed direction set at
  spawn, block collision, dies on ground/range/hit, reuses the tracer rotated). All use the
  muzzle origins above; cast/impact FX are cyan for the normal/down shots and violet for homing.
- Match selection: `debug.json` `default_enemy` is `creepy_shooter`; F7 order is
  Warrior -> Veno -> Bat -> Creepy Shooter -> Dummy. `skill_slots` is
  `["creepy_shot","creepy_homing_shot","creepy_roll_shot","creepy_jump_shot"]`; `separates` and
  `decides_match` are true. `force_attack` rejects KO/HURT/unknown ids, clears all four timers, and
  enforces the skill-4 takeoff rule. `skill_remaining` maps the four ids to the F2 cooldown line.
- Smoke flags: `creepy_present`, `creepy_stage_ok`, `creepy_shot_ok`, `creepy_homing_ok`,
  `creepy_lock_ok`, `creepy_roll_ok` + `creepy_roll_edge`, `creepy_jump_ok` +
  `creepy_jump_long/short/right/none`, `creepy_ai_ok` + `creepy_ai_hop`, `creepy_slots_ok`,
  `creepy_win_ok`, `creepy_cleanup_ok`, `creepy_stage_switch_ok`, `creepy_missing_frames == 0`
  and `creepy_fx_missing == 0`. Ladder-hit smoke: `creepy_ladder_hit_mid_ok` (knocked off,
  climb cleared immediately, no platform side push), `creepy_ladder_hit_platform_ok` (feet inside
  the platform snap to its top), `creepy_ladder_hit_top_ok` (top shot lands on the platform) and
  the combined `creepy_ladder_hit_ok`. The remaining ground barrier sits below the flat-ground
  mid lane, so the shot test spawns a bullet at `barrier.centery` to verify block collision.

## Projectile / skill VFX (2026-10-24)

- Visual-only pass. `q`, `veno_poison` and `veno_web` keep their damage, hitbox, duration, speed,
  range, status, knockback, cooldown, AI and roster data. `veno_bite` only gains a visual
  `hit_fx` field on its existing hitbox event.
- New `game/fx.py` owns sprite-strip loading and short-lived effects (`RingBurstFx`,
  `PoisonSplashFx`, `WebImpactFx`, `BiteArcFx`, `SilkCastFx`). It imports only `pygame` and
  `ASSETS_DIR`, and caches sprite frames/rotations by path + mtime so F5 refreshes PNGs.
- `ArenaScene` gains a separate `fx_effects` list. It updates next to `slash_effects` (so effects
  freeze during hitstop) and draws after `slash_effects`, before player status/marks/HUD. Nyra's
  `SlashEffect` and the `fx` event path are untouched.
- Projectiles carry visual-only `age`, `visual_kind` and `hit_color` fields:
  - `QWave`: `lina_q` / `lina_q_flame`; hit colors teal `(80,230,225)` and orange
    `(255,150,90)`.
  - `AimedProjectile`: `veno_poison` / `veno_web`; hit colors dark green `(65,170,75)` and pale
    web `(200,240,170)`.
  `resolve_projectile_hit` uses the projectile's `hit_color` instead of the old hardcoded cyan and
  calls `spawn_projectile_impact`; `AxeThrow`/legacy `SwordWave` have no visual kind, so their
  behavior is unchanged. `ParticleSystem.emit_hit` is not modified.
- Lina Q is now a single static sprite per form (not a 6-frame strip). Normal is the supplied
  teal glass-ball texture (glossy teal body, white rim, upper-left highlight, darker lower-right),
  pixelated to the same 2px grid as the character art and given a short teal pixel trail; it is
  ~26px (fist-sized). Flame is a Seedream pixel-art fire orb at ~32px. Both are 96×96, anchor
  `(64,48)`. The normal form has **no procedural ball**, and `QWave` has no procedural fallback.
  The projectile spawns at `t=0.26` with collision 44×34 and speed/range unchanged; its sprite is
  drawn 7px above the collision lane (`Q_WAVE_DRAW_OFFSET_Y`) so it lines up with the punching
  fist, and the teal cast flash uses the same offset. The impact effect stays at the collision
  point and uses the teal family.
- Veno web uses the exact 130×123 crop of `veno_web_spit_web_05.png` at
  `(492,155,622,278)` (`assets/frames/veno/veno_web_fx/veno_web_05_web.png`). The spit thread,
  trail and cast strands are procedural; the projectile is drawn at 64px with collision radius 30,
  and the same crop is reused for the impact decal at 150–170px. The `combined_*` and `spider_*`
  frames are never loaded at runtime.
- Veno poison stays procedural: a dark-green layered glob (deep-green outer shell, mid-green body,
  lighter highlight), bubbles, droplet trail, dark-green cast mist and splash. The poisoned body
  uses the whole-frame green/purple flash described above instead of the old rectangle.
  Poison damage is applied in **0.5s** chunks (`POISON_TICK` in `game/status.py`) instead of the
  old 0.2s dot tick; total dps and duration are unchanged. The tick is applied before the
  remaining-time decrement so a 3.0s poison still gets its sixth full tick. Burn keeps the 0.2s
  tick. The hover silk is a draw-only curved strand using `hover_phase`; no state/AI change.
- Bite feedback uses `spawn_hit_fx` from `resolve_hit` (via the `hit_fx` field), not a new `fx`
  event. It spawns a short green crescent at the target's near edge plus a few droplets.
- Smoke covers asset presence (`lina_q_fx_missing`, `veno_vfx_missing`), dispatch
  (`q_*_fx_ok`, `veno_*_cast/impact_ok`, `veno_bite_hit_fx_ok`, `q_flame_color_ok`), poison cadence
  (`poison_interval_ok`) and cleanup (`fx_cleanup_ok`); appearance is reviewed with
  `tools/preview_fx.py` or in-game.

## Roster and skill slots

- `game/data/roster.json` is the registry. Each character/enemy entry names its `class`, `stats`
  key, spawn key, animation table keys, frame folder, canonical fallback image, and (for enemies)
  `skill_slots`, `separates` and `decides_match`.
- `game/roster.py` builds the `AnimationPlayer` and the fighter class from that entry; the scene no
  longer constructs Lina/Nyra/Rhea/Warrior/Veno/Dummy directly. Playable classes keep Lina's
  `update(dt, input_state, target, scene)` signature; Lina, Nyra and Rhea are installed.
- F7 cycles the enemy roster in roster order (Warrior → Veno-Spider → Bat → Creepy Shooter →
  training Dummy); the current default enemy is Creepy Shooter. `[` / `]`
  cycle the playable roster (Lina ↔ Nyra ↔ Rhea). Switching performs a full match reset: both fighters
  respawn at full HP, and
  projectiles, wave effects, particles, hitstop, statuses, cooldowns, the match result and the input buffer are
  cleared. The B block toggle (barriers + platforms; ladders unaffected) is preserved; the enemy AI is forced off whenever fighters are rebuilt
  or reset — startup, F5 reload, roster switches, F9 and R — and F8 toggles it during a battle.
- `skill_slots` is a fixed 4-entry list of attack ids or `null`, in slot order. `V/C/X/Z` call
  `Fighter.force_skill(scene, target, 0..3)`, which resolves the id and calls the class's
  `force_attack`. Undefined slots and enemies without `force_attack` (Dummy) are safe no-ops. F2
  prints the four slots and their cooldowns (`-` for empty slots).
- Cooldown values stay in `stats.json` (`ai.attack_cooldown`, `ai.dash_cooldown`,
  `ai.throw_cooldown` for Warrior; `cooldowns.shot/homing/roll/jump` for Creepy Shooter); the
  roster only maps slot order to attack ids.
- Debug: F7 enemy roster, `[` / `]` character roster, F8 AI/invincibility, V/C/X/Z skill slots,
  arrows move the enemy, PgUp/PgDn change enemy HP.

## Out of scope in the current sandbox

Daily phases, food/fullness, shop/gold, saves, audio, the full HUD, playable characters beyond
Lina/Nyra/Rhea, enemies beyond Warrior/Veno/Bat/Creepy Shooter/Dummy and their AI, group balancing
beyond the Veno 3-body group and the five-Bat sandbox, packaging and automated tests/logs. The training
dummy is a debug tool, not a spec enemy.
