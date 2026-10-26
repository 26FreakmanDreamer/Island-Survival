# Animation asset pipeline

> **Before generating any image, read `docs/IMAGE_GENERATION_RULES.md`.** It is the mandatory
> pre-flight and contact-sheet gate for near/far limb layering, weapon-hand grip, no
> interpenetration, and size/proportion lock.

## Source rules

- `Image/Character/lina-seabright-v1-256.png` is Lina's appearance reference; `v2` is the red/black
  palette reference. `Image/Enemy/warrior-336.png` is Warrior's only visual source. Never overwrite
  `Image/`.
- Lina's approved side-view base is `assets/generated/base/lina_side_base.png` (body height 210px).
  Warrior's approved side-view base is `assets/generated/base/warrior_side_base.png` (body height
  about 230px, 384x384 canvas, pivot 192,372).
- Lina frames live in `assets/frames/lina/<action>/`; flame-form frames in
  `assets/frames/lina/flame/<action>/`; Warrior frames in `assets/frames/warrior/<action>/`;
  Bat frames in `assets/frames/bat/<action>/`.
- `game/data/animations.json` defines Lina's `clips`/`flame_clips`, Warrior's
  `warrior_clips`/`warrior_frame_size`/`warrior_pivot`, and Bat's
  `bat_clips`/`bat_frame_size`/`bat_pivot`.

## Frame inventory

- Normal (45): idle 4, walk 6, jump 2, crouch 1, punch_l/r 4+4, kick_l/r 4+4, Q 4,
  transform 6, hurt 2, KO 4.
- Flame form (41): idle 4, walk 6, jump 2, crouch 1, punch_l/r 4+4, kick_l/r 4+4, Q 4, hurt 2, KO 4, revert 2.
- Warrior (36): idle 4, walk 6, jump 2, axe_slash 6, axe_throw 7, dash 5, hurt 2, KO 4.
- Bat (14): wing 4 (shared idle/fly), bat_dive 3, bat_sonic 3, hurt 1, stun 1, KO 2.
- Lina: 256x256 RGBA, feet-center pivot (128,244), body about 210px. Warrior: 384x384 RGBA, pivot
  (192,372), body about 230px. Bat: 384x384 source / 192x192 runtime, pivot (115,143), body about
  150px.
- Durations are per action in `animations.json`; punch is 0.25s and kick is 0.4s per the spec.

## Normal frame generation

Use Seedream `image_to_image` with the side-view base as the single RGBA reference,
`background="transparent"`, `size="1K"`, `output_format="png"`. Keep the prompt prefix stable and
only change the pose sentence. Generate 1-2 candidates per frame, collect the chosen one, import to
staging, and make a contact sheet before copying into the game.

Common prompt prefix:

```text
Use the reference image as the exact character, costume, camera and scale reference.
Lina Seabright: long purple hair, white star hair clip, pearl earrings, blue anchor cropped jacket,
purple sash, black leggings, blue boots. 2D side-scrolling fighting game sprite, right-facing
three-quarter side view, full body, feet visible, centered with margin, flat transparent background,
no shadow, no text, no border, no scenery. Pixel-art style, crisp outline. Keep the exact same
outfit, colors, proportions, hairstyle, camera distance, character scale, foot position and
lighting as the reference.
```

**Size/centering note (all character prompts):** `centered with margin` is a composition instruction
only. Never zoom, scale, stretch or shrink the character to center it or to fit the full body/weapon.
This applies whether the weapon is raised, lowered or held horizontally. If the weapon makes the
silhouette taller/wider, expand the generation canvas/margins or adjust the framing instead. The
final runtime frame must use the character's canonical canvas/pivot; if the full weapon cannot fit
at the fixed scale, stop and ask the user — do not shrink the character or crop the weapon.

Then add the action/pose, e.g. "This is punch frame 2 of 4: the FRONT arm drives straight forward...".

## Flame-form generation

Use Seedream `multi_image_fusion` with two images:

1. the normal pose frame for the action (image 1, pose reference);
2. `assets/generated/raw/transform/transform_04.png` (image 2, red/black flame appearance).

Prompt: preserve image 1's exact pose and position, apply image 2's red/black outfit and steady
orange fire aura, keep the attacking limb readable, request a pure white/transparent background where
possible. Generate one frame at a time; re-generate any frame whose pose or limbs drift.

Hurt and KO use the same recipe with `assets/generated/raw/hurt` and `assets/generated/raw/ko` as the
pose references. The lying KO frames may come back with a gray ground shadow; remove it with a
connected neutral-light background pass before import.

The 2-frame flame-to-normal `revert` uses the normal idle frame as the pose reference and asks for a
progressive fade: frame 00 keeps a strong broken aura with the outfit partly back to blue/white,
frame 01 is nearly normal with last embers at the boots and hair tips. Import it with the idle pose
reference copied under the matching `revert_00/revert_01` names.

Generated flame art can drift horizontally within its frame. `animations.json` stores a
`flame_offsets` integer for every flame frame; `AnimationPlayer.draw` applies it in flame form and
mirrors it when facing left. This keeps the body at the same world x as the normal form, so the
transform and revert do not visibly move Lina. Recompute the table if flame frames are replaced.

## Warrior generation

Warrior's only visual source is `Image/Enemy/warrior-336.png`; the poster is design reference only.
Generate the approved base with `image_to_image`, `size="1K"`, transparent PNG, and the source as the
only input. It must be a right-facing near-profile 3/4 side view with the full body and full crescent
axe in frame. Keep the axe low in the base so the `--body-height 230` calibration measures the body
rather than the weapon.

Warrior uses a 384x384 canvas and pivot (192,372), body height about 230px. Generate 2 candidates per
frame from the approved base, import, and approve a contact sheet with
`--cell 384 --pivot-x 192 --pivot-y 372`.

Stable prefix:

```text
Use the reference image as the exact character, costume, weapon, camera and scale reference.
Warrior: adult muscular male, spiky dark red hair, red headband with flowing tails,
red-and-black open sleeveless battle costume, exposed powerful chest and arms, ornate gold
shoulder armor, black bracers with gold studs, layered red waist cloth, gold-trimmed black
trousers, heavy red-black boots, one massive single crescent-bladed silver battle axe with dark
swirl motif, gold hardware and red tassels. 2D side-scrolling fighting game sprite, RIGHT-FACING
near-profile three-quarter side view, full body, both feet visible, entire axe fully inside the
frame, centered with generous margin, flat transparent background, no shadow, no text, no border,
no scenery. Pixel-art style, crisp outline. Keep the exact same outfit, colors, proportions,
hairstyle, weapon design, camera distance, character scale, foot position and lighting as the
reference. Do not mirror the character. Do not crop the axe or the boots.
```

Axe slash uses 6 frames: low rear guard (00), mid-lift transition (01), high wind-up (02), swing
contact (03), follow-through (04), recovery (05). Durations are `0.08, 0.08, 0.09, 0.15, 0.15, 0.20`;
the hitbox is active at 0.25-0.55s. Frame 01 is generated against the idle body/axe scale so the
wind-up does not shrink, and frames 03/04 use the one-handed rear grip (the hand sits near the gold
pommel with a long empty haft section ahead of it) from the follow-through reference. The axe has a
single upper crescent blade; the lower side is a blunt counterweight.

## Nyra Steel (2026-10-22)

- Approved side base: `assets/generated/base/nyra_side_base.png`; canonical source
  `Image/Character/nyra-steel-256.png`. Canvas 384x384, pivot (192,372), body height 214.
- Visual lock: short asymmetrical silver-white bob with a side fringe and dark ornament, red eyes,
  black high-collared combat coat with silver piping and dark-blue lining, belted waist, layered
  split skirt/coattails, dark thigh-high stockings with upper-thigh bands, fingerless gloves, black
  boots with blue details, one long narrow silver sword with a cool-blue edge in the RIGHT hand.
  No eyepatch. Do not mirror or duplicate the sword.
- Frame inventory (29 minimal): idle 2, walk 2, jump 2, crouch 1, hurt 1, KO 2, nyra_slash 6 (Q),
  nyra_thrust 5, nyra_wave 5 (LMB), nyra_dash 3. The base's sword is held horizontally for clean
  `--body-height` calibration. The 1-frame crouch is imported with `--body-height 173`, producing
  a ~170px visible body (midway between the original 212px crouch and the 128px deep crouch); the
  crouching hurtbox stays 56×130 and other clips use 214. The 6-frame slash (Q) follows: initial
  front-down 45°; transition with
  the sword at 10-20° below horizontal and the arm starting to extend; the redrawn v11 arm-forward
  frame (219px tall, feet aligned at 372); the thrust_v5_01 long-sword contact; and two recovery
  frames. Durations are 0.05/0.04/0.05/0.14/0.07/0.05 (0.40s). The 5-frame wave (LMB) starts with
  a high wind-up (sword ~55-60° above horizontal), then a raise transition (~30°), horizontal
  contact, a down transition (~20° below), and a forward-down follow-through; durations
  0.06/0.06/0.06/0.06/0.06 (0.30s). The 5-frame thrust (RMB) is timed
  0.08/0.08/0.08/0.08/0.08 (0.40s); its single hitbox is active 0.16-0.24. Keep the energy wave
  separate from the character frames:
  `game/slash_fx.py` plays six transparent sprites from
  `assets/frames/nyra/nyra_slash_fx/`, anchored at the Q cast position. Frames 00/01/05 are
  transparent; 02-04 are visible (durations 0.02/0.02/0.05/0.14/0.07/0.05; the event is flagged at
  t=0.04 but first fires on the 60Hz t≈0.05 tick) and align with the character's 02-04 frames; LMB
  uses the extended `[28,-212,162,123]` box during t=0.06-0.24 (RMB thrust box outside), while Q
  uses it during t=0.12-0.30 (RMB thrust box outside).
- Import:

```text
py tools/import_frames.py --action <action> --src assets/generated/raw/nyra/<action>_flat --out assets/generated/staged/nyra/<action> --base assets/generated/base/nyra_side_base.png --body-height 214 --canvas 384 --pivot-x 192 --pivot-y 372 --expect <n>
py tools/contact_sheet.py --action nyra_<action> --frames assets/generated/staged/nyra/<action> --out assets/generated/contact_sheets/nyra_<action>_v1.png --durations <durations> --cell 384 --pivot-x 192 --pivot-y 372
```

- The lying KO frame can include a neutral gray ground rectangle from the generator even with a
  transparent request. Remove it with `--remove-bg` first; if the rectangle remains, clear neutral
  gray pixels (`110 <= r <= 180`, channel spread < 12) in the ground band before installing.

## Veno-Spider (2026-10-22)

- Approved side base: `assets/generated/base/veno_side_base.png`; canonical source
  `Image/Enemy/veno-spider-128.png`. Source canvas 320x320, pivot (160,308), body height 150.
  The 2026-10-24 small-body variant keeps these source PNGs but runs them at **160x160,
  pivot (80,154), body ~75** via `animations.json`; the hitbox is 75x75 and `stage_body_width`
  is 70. Do not regenerate the source frames just to change the runtime size.
- Visual lock: giant black chitinous spider with a swollen high abdomen, sharp lime-green venom
  patterns, green eyes, fangs, eight jointed legs with green bands and pale tips. Head and fangs
  point right; abdomen trails left. All eight legs must remain distinct; no extra legs.
- Frame inventory (20 minimal): idle 2, walk 2, hover 2, jump 2, hurt 1, KO 2, veno_bite 3,
  veno_poison 3, veno_web 3. Idle and jump currently reuse a shared frame where the generator
  drifted in size; hover is a hanging pose with no baked-in web line.
- Import:

```text
py tools/import_frames.py --action <action> --src assets/generated/raw/veno/<action>_flat --out assets/generated/staged/veno/<action> --base assets/generated/base/veno_side_base.png --body-height 150 --canvas 320 --pivot-x 160 --pivot-y 308 --expect <n>
py tools/contact_sheet.py --action veno_<action> --frames assets/generated/staged/veno/<action> --out assets/generated/contact_sheets/veno_<action>_v1.png --durations <durations> --cell 320 --pivot-x 160 --pivot-y 308
```

- Bite frames should show the mouth wide open on the rear/lunge frames; poison/web frames should
  only show the pose, with the projectile drawn by the game. Hover frames must not include a web
  strand; the scene draws it.
- The generator's body-size lock is strict: reject or reuse a frame if the abdomen/head changes
  size between frames of the same clip.

## Bat (2026-10-25; code/values 2026-10-26)

- Approved side-view base C (streamlined glide): `assets/generated/base/bat_side_base.png`;
  canonical source `Image/Enemy/bat-128.png`. Source canvas 384x384, runtime 192x192 via
  `animations.json` (`bat_frame_size`), pivot (115,143) runtime, mirror pivot x 77. Body about
  150px; hurtbox 100x66. The runtime downscale is handled by `AnimationPlayer`; do not bake a
  second scale into the frames.
- Frame inventory (14): wing 4 (shared `idle`/`fly`), `bat_dive` 3, `bat_sonic` 3, hurt 1,
  stun 1, KO 2. `idle` is the 6-step ping-pong slow wing loop; `fly` is the 4-frame fast loop.
  Only right-facing frames are stored; the runtime mirrors for left. `bat_dive` and `bat_sonic`
  are non-looping 0.75s / 0.65s clips.
- Runtime frames: `assets/frames/bat/wing/`, `assets/frames/bat/bat_dive/`,
  `assets/frames/bat/bat_sonic/`, `assets/frames/bat/hurt/`, `assets/frames/bat/stun/`,
  `assets/frames/bat/ko/`. These 14 files are approved; do not re-import or regenerate them
  without an explicit request.
- Tools: `tools/import_bat_side_frames.py`, `tools/contact_sheet_grid.py`,
  `tools/preview_bat_side_wing.py`, `tools/preview_bat_side_clips.py`. Approval sheets/GIFs are
  under `assets/generated/contact_sheets/bat_v1/`.
- Sonic VFX is procedural: `game/projectile.py::SonicWave` draws three nested Wi-Fi/signal arcs
  opening along the travel direction, plus an emitter dot and a short trail; `RingBurstFx`
  provides the cast/impact flashes. The gameplay hitbox is a forward circle (+8px along travel,
  radius 24). No sonic frames are baked into `bat_sonic_01.png`.
- The 14 frames are 384x384 RGBA; `AnimationPlayer` downscales to 192. If a future action frame
  drifts in body size, use the same one-time body normalization as the wing transition, not
  per-frame repainting.

## Projectile / skill VFX (2026-10-24)

These are visual-only assets. Damage, hitboxes, timing, cooldowns and AI are unchanged.

- **Lina Q** uses one static image per form (no frame loop):
  - Normal: `assets/frames/lina/q_fx/q_wave_00.png` — the supplied teal glass-ball texture,
    pixelated to the character's 2px grid (glossy teal body, white rim, upper-left highlight,
    darker lower-right) plus a short teal pixel trail; ~26px visible (fist-sized), 96×96
    canvas, anchor `(64, 48)`. No procedural ball; `QWave` has no procedural fallback, so the
    PNG must exist. The sprite is drawn 7px above the collision lane
    (`Q_WAVE_DRAW_OFFSET_Y` in `game/fx.py`) to line up with the punching fist; the cast flash
    uses the same offset, while the hit/impact effects stay on the collision point.
    Reference: `assets/generated/raw/lina_q_fx_teal_v1/teal_ball_reference.png`; the texture
    used is the Seedream `image_to_image` result in
    `assets/generated/raw/lina_q_fx_teal_v1/2026-10-24/image_to_image/`.
  - Flame: `assets/frames/lina/flame/q_fx/q_wave_00.png` — Seedream pixel-art fire orb,
    ~32px visible, same canvas/anchor.
  - Runtime specs live in `game/fx.py` (`LINA_Q_SPECS`); the sprite is flipped for
    left-facing shots and drawn at the collision center.
- **Veno web** uses `assets/frames/veno/veno_web_fx/veno_web_05_web.png`, an exact
  130×123 crop at `(492, 155, 622, 278)` from
  `assets/generated/contact_sheets/veno_web_spit_v2_frames/veno_web_spit_web_05.png`.
  The silk thread/trail is procedural; no thread, droplets or padding are baked into the
  sprite. The projectile is drawn at 64px (collision radius 30) and the same crop is reused for
  the impact decal at 150–170px.
- **Veno poison** stays procedural: a dark-green layered glob, bubbles and droplet trail; dark
  green cast mist and splash. The poisoned body uses a green/purple whole-frame tint every 0.18s
  instead of the old hurtbox rectangle; green poison particles remain.
- Do **not** use `veno_web_spit_v2_frames/combined_*` or `spider_*` at runtime; they contain
  Veno's body and would double the character.

Build/review tools:

```text
py tools/generate_lina_q_fx.py --normal <teal-ball.png> --flame <seedream-flame.png>
py tools/generate_veno_web_bolt.py
py tools/preview_fx.py
```

`generate_lina_q_fx.py` composes the supplied teal-ball texture (normal) and the Seedream flame
texture into the 96×96 runtime frames; it writes candidates and contact sheets to
`assets/generated/contact_sheets/lina_q_fx_v1/`. It no longer generates a procedural orb.
`generate_veno_web_bolt.py` writes the crop and preview to
`assets/generated/contact_sheets/veno_web_fx_v1/`. `preview_fx.py` renders in-game cast/flight/
impact snapshots to `assets/generated/contact_sheets/fx_ingame_preview_v1/`.

Approval gate: review the contact sheet and in-game previews first; only then copy the approved
PNG into `assets/frames/`. `game/fx.py` caches by path + mtime, so replacing a runtime PNG and
pressing F5 refreshes it; changing frame count/size/anchor or effect durations is a Python
constant change and requires restarting the process.

## Commands

```text
py tools/collect_frames.py --action idle --names idle_00,idle_01,idle_02,idle_03 --dest assets/generated/raw/idle
py tools/import_frames.py --action idle --src assets/generated/raw/idle --out assets/generated/staged/idle --expect 4
py tools/contact_sheet.py --action idle --frames assets/generated/staged/idle --out assets/generated/contact_sheets/idle_v1.png --durations 0.12,0.12,0.12,0.12
```

Flame frames use `--remove-bg` and `--pose-ref`:

```text
py tools/import_frames.py --action idle --src assets/generated/raw/flame/idle --out assets/generated/staged/flame/idle --remove-bg --pose-ref assets/generated/raw/idle --expect 4
```

Warrior uses the 384 canvas and pivot overrides:

```text
py tools/import_frames.py --action idle --src assets/generated/raw/warrior/idle --out assets/generated/staged/warrior/idle --base assets/generated/base/warrior_side_base.png --body-height 230 --canvas 384 --pivot-x 192 --pivot-y 372 --expect 4
py tools/contact_sheet.py --action warrior_idle --frames assets/generated/staged/warrior/idle --out assets/generated/contact_sheets/warrior_idle_v1.png --durations 0.18,0.18,0.18,0.18 --cell 384 --pivot-x 192 --pivot-y 372
```

`collect_frames.py` copies the newest matching Seedream output per custom name into an action folder.
`import_frames.py` normalizes to `--canvas` (default 256x256) with feet-center anchoring; for flame
frames, the pose reference supplies the body scale/position while the fire aura may be larger than
the body. `contact_sheet.py` renders a labeled checkerboard sheet with the pivot cross for approval;
`--cell`/`--pivot-x`/`--pivot-y` must match the character's canvas.

`--body-height`/`--canvas` set the character scale and final frame size; centering is done by
foot/pivot placement, never by changing the body scale per frame. If a frame's full weapon cannot
fit the canonical canvas at the approved body height, stop and ask the user; do not shrink the
character, crop the weapon or change the runtime canvas without explicit approval. This applies
whether the weapon is raised, lowered or held horizontally.

The importer's background removal is two-stage: a corner flood fill for uniform gray/white backdrops,
plus a connected near-white mask for checkerboards. In `--pose-ref` mode it also removes remaining
near-white pixels outside the pose silhouette, without touching the character's white clothing.
Near-transparent pixels (alpha < 10) are cleared.

## Approval and install

1. Generate candidates into `assets/generated/raw/<character>_frames/`.
2. Collect the chosen files into `assets/generated/raw/<character>/<action>/`.
3. Import into `assets/generated/staged/<character>/<action>/` with the character's canvas/pivot.
4. Build a contact sheet and review it (pose, limb identity, feet alignment, effects).
5. Copy approved frames to `assets/frames/lina/<action>/`, `assets/frames/lina/flame/<action>/` or
   `assets/frames/warrior/<action>/`.
6. Press F5 in-game after replacing frames; the animation cache invalidates on path + mtime.

Canonical `Image/` files are read-only. Generated candidates, staging folders and contact sheets are
kept under `assets/generated/` for traceability.
