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
- Presses during an attack go into a one-slot action queue instead of expiring with the 120ms buffer.
  The newest press wins; punch/kick start the opposite limb when the attack ends, and Q or jump also
  wait for the attack to end. E is the exception: it waits only for recovery to begin, then cancels it.
- Held movement and crouch are rebuilt from the physical keyboard after pause resume, scene
  reset/rebuild and focus regain, so a key held across those moments keeps working without a re-press.
  Text input is disabled at startup so a Chinese IME does not consume gameplay keys.
- Ground-only LMB/RMB/Q; E can be used in the air. No air normal attacks.
- Knockback is 300px/s for the kick and 150px/s for Q, decaying over 0.35s.
- Lina's attacks use ATK x multiplier: punch 1.0, kick 1.5, Q 1.25.
  With the initial ATK of 20 this is 20 / 30 / 25 damage.
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
- Super armor ignores control effects. Damage reduction is a percentage multiplier.
- First milestone naturally triggers burn (flame hits), knockback (kick/Q), and knock-up/stun through
  debug scenarios; freeze/slow/poison/super armor/damage reduction are available through F11.

## Stage and projectile heights

- 1280x720 logical resolution; background scaled from 1664x936; fixed camera.
- Ground y=620; walls at x=90 and x=1190; two solid blocks at x=400..490 and x=760..850.
- Lina spawns at x=280; the dummy and Warrior spawn at x=1000.
- Fighters keep a minimum center distance equal to the sum of their stage body half-widths
  (Lina 50 + Warrior 60 = 110px). The Warrior yields first; if a wall/block stops him, Lina is
  pushed to the free side. Warrior facing ignores targets within an 8px deadzone, so overlapping
  bodies cannot flip the sprite every tick.
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
- Frames (24): idle 4, walk 6, jump 2, axe_slash 6, hurt 2, KO 4. Axe slash frame 01 is a mid-lift
  between the low rear guard and the high wind-up; frames 03/04 use a one-handed rear grip based on
  the follow-through pose.
- Stats: HP 300, ATK 24, `stage_body_width` 120, hurtbox 84x230, walk 160, jump_v 700, gravity 2200.
- Axe slash: 0.75s total, startup 0.25s (frames 0-2), active 0.30s (frames 3-4), recovery 0.20s
  (frame 5); hitbox `[36,-205,150,110]` active t=0.25..0.55; knockback 380; hitstun 0.3; hitstop
  0.08; cooldown 0.9s after the attack ends.
- AI: always faces Lina; approaches when outside 160px; jumps when a block is in front; attacks when
  within 160px and the cooldown is ready; no crouch, no second attack, no pathfinding beyond jumps.
- Super armor: during axe startup+active (runtime time < 0.55s), a hit deals damage and flash but
  does not clear the attack, enter HURT, or apply hitstun/knockback. Recovery is interruptible. A
  lethal armored hit still KOs.
- Tick order: Lina updates first, then the enemy, then the hitstop gate. This gives the player the
  same-tick trade and lets startup armor complete visibly.
- Match flow: Warrior mode sets WIN when the enemy HP reaches 0 and LOSE when Lina HP reaches 0;
  R restarts after a result and F9 resets at any time.
- Debug: F7 enemy mode; F8 AI (Warrior) / invincibility (Dummy); V force axe; arrows move the current
  enemy; PgUp/PgDn change current enemy HP.

## Out of scope in the first milestone

Daily phases, food/fullness, shop/gold, saves, character selection, audio, the full HUD, other
characters, other enemies and their AI, packaging and automated tests/logs. The training dummy is a
debug tool, not a spec enemy.
