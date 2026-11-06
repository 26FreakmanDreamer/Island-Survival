# Shadow Ninja animation design (normal form)

Date: 2026-11-06. Status: implemented and approved; the 35 character frames and 2 kunai FX are
installed in `assets/frames/shadow_ninja/`. The phantom form is out of scope for this set.

## Source and drawing basis

- Canonical source: `Image/Enemy/shadow-ninja-256.png`.
- Approved base: `assets/generated/base/shadow_ninja_side_base.png` (derived from the v5_2 side
  candidate). All normal-form frames use this base as the identity, outfit, hairstyle, kunai and
  scale reference.
- Facing: right-facing full side profile. Runtime mirrors left; no left-facing frames are generated.
- Weapon hand: the near/right hand holds the kunai; the far/left hand stays behind the hip. Keep the
  purple blade, silver core and purple ring pommel consistent.
- Frame canvas: 384x384, pivot (192,372), body 214. Hurtbox 56x210 standing / 56x130 crouching;
  `stage_body_width` 100.

## Clip budget

| clip | frames | durations | notes |
|---|---:|---|---|
| `idle` | 4 | 0.30 each | calm breathing, kunai low, ponytail/sash sway |
| `walk` | 6 | 0.10 each | stealth walk, near/right and far/left legs alternate; v5 set fixed-scale normalized to body 214 with the 00 frame as the body/feet reference |
| `jump` | 2 | 0.20 each | rising (knees tucked) / descending (legs extend) |
| `crouch` | 1 | 0.50 hold | deep defensive crouch; visual 188px including hair, gameplay hurtbox 56x130 |
| `hurt` | 2 | 0.10 each | recoil and recovery; kunai stays low |
| `ko` | 4 | 0.25 / 0.20 / 0.25 / 0.30 | balance loss → knees buckle → side fall → fully lying; final frame has closed eyes and is held |
| `shadow_kunai_slash` | 5 | 0.07 each (0.35s) | windup low on the right → high guard → high horizontal slash → follow-through → low recovery; high hitbox `[20,-195,130,55]` |
| `shadow_kunai_throw` | 5 | 0.09 each (0.45s) | low windup → loaded step → **frame 02 release** (no kunai in the character frame) → low follow-through → recovery; deep crouch on 02/03 |
| `shadow_dash` | 5 | 0.09 each (0.45s) | low windup → launch → low forward stride → continuation → recovery; 01/02/03 are more forward-leaning and lower; low hitbox `[0,-80,90,80]` |
| `stun` | 1 | 0.50 hold | dazed head tilt, half-closed eyes, loose arms; no stars or other effects baked in |

Total: 35 character frames.

## Frame notes

- The slash frames 00/01 hold the kunai on the right side of the image; frame 02 uses a
  reverse/icepick grip with the fingers pointing down and the black handle above the fist. Frames
  03/04 keep the original v1 follow-through/recovery.
- The throw frame 02 is the release frame. The character frames 02–04 must not contain a thrown
  kunai; the projectile is the separate two-frame FX. Frame 04 keeps the black fingerless glove on
  the open hand, and frames 02/03 are intentionally deeper than the standing idle.
- The dash frames 00/04 are the original v1 poses; 01/02/03 lean further forward and sit lower.
  Frame 01's kunai is horizontal; frame 02 is the lowest point.
- The KO final frame closes the eyes. The lying frames use the feet pivot and the body extends along
  the ground.
- Do not bake kunai, afterimages, marks, stun stars or hit sparks into character frames. Do not
  zoom, stretch or shrink a frame to fit; regenerate instead.

## Kunai projectile FX

| file | size | notes |
|---|---:|---|
| `assets/frames/shadow_ninja/fx/shadow_kunai_00.png` | 32x32 | horizontally oriented, normal brightness |
| `assets/frames/shadow_ninja/fx/shadow_kunai_01.png` | 32x32 | same orientation, brighter frame |

- Only two frames; the sprite does not rotate. The projectile moves horizontally in code.
- The FX was extracted with Seedream `image_to_image` from a crop of the approved base
  (`assets/generated/contact_sheets/base_kunai_source.png`) and downscaled with the smooth variant
  to a 32x32 transparent canvas. It keeps the base's purple blade, silver core, black handle and
  purple ring.
- `ShadowKunaiProjectile.draw` alternates the two frames at 18 fps (`int(age * 18) % 2`). Do not add
  a third frame or reintroduce rotation.

## Installation and verification

- Runtime files: `assets/frames/shadow_ninja/<clip>/<clip>_NN.png` and
  `assets/frames/shadow_ninja/fx/shadow_kunai_00..01.png`.
- `game/data/animations.json` owns `shadow_ninja_clips`, `shadow_ninja_frame_size` and
  `shadow_ninja_pivot`; the clip durations above match the attack durations (slash 0.35s, throw
  0.45s, dash 0.45s).
- In-game preview: `tools/preview_shadow_ninja.py` writes 14 shots to
  `assets/generated/contact_sheets/shadow_ninja_ingame_v1/`.
- Smoke: Phase H checks `shadow_ninja_missing_frames == 0` and `shadow_ninja_fx_missing == 0`.
- Approved sets are not to be regenerated or re-imported without an explicit user request.

## Out of scope

- Phantom form (skill 4), transform frames, phantoms' three skills, invincibility frames and
  phantom FX.
- Full-game combat HUD, BGM/background switching, shop/levels.
- Any change to `instruction.docx` or `Image/`.
