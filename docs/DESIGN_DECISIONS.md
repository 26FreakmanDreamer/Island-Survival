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
- 33 dedicated flame-form frames were generated from the normal pose references using multi-image
  fusion (pose image + `transform_04`):
  idle 4, walk 6, jump 2, crouch 1, punch_l/r 4+4, kick_l/r 4+4, Q 4.
- The animation player keeps two clip tables: normal and flame. After the transform clip finishes,
  it switches to the flame table for idle/walk/punch/kick/Q.
- Jump and crouch have dedicated flame frames, so they keep the red/black outfit and a controlled
  aura instead of being tinted as a full-body flame silhouette. If the flame table lacks a clip
  (hurt, KO), the normal clip is used and receives the runtime red/orange tint. The transform clip
  itself and dedicated flame frames are never tinted.
- When the 10s flame form ends, the game waits for the current neutral state and switches back to the
  normal table. An attack that started in flame form finishes with flame frames.

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
- Lina spawns at x=280; the dummy at x=1000.
- Stage collision uses a wider grounded body than the 56px combat hurtbox: Lina's
  `stage_body_width` is 100px, so her front boot stops at the block edge instead of entering it.
  While airborne, collision falls back to the hurtbox width so stepping off a ledge does not snap
  the character sideways. Attack lunges use the same stage collision, not a direct x change.
- Overlapping a block resolves to the nearer side; landing on a block top requires the feet center
  to be within 8px of the block span (`land_margin`).
- Projectile lane heights are measured upward from the attacker's feet: high 180px, fist 142px,
  mid 120px, low 60px. Lina Q spawns at `attacker.y - 142`, so it is screen y 478 on flat ground
  and y 418 while she stands on a 60px block. The ball keeps that spawn height in flight.
- This makes the Q trajectory follow Lina vertically instead of staying on a fixed world lane.
- Character sprite body height is approximately 210px, anchored at the feet-center pivot (128,244)
  on a 256x256 canvas.

## Out of scope in the first milestone

Daily phases, food/fullness, shop/gold, saves, character selection, audio, the full HUD, other
characters, enemy AI, packaging and automated tests/logs. The training dummy is a debug tool, not a
spec enemy.
