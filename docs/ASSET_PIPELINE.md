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
  `assets/frames/lina/flame/<action>/`; Warrior frames in `assets/frames/warrior/<action>/`.
- `game/data/animations.json` defines Lina's `clips`/`flame_clips` and Warrior's
  `warrior_clips`/`warrior_frame_size`/`warrior_pivot`.

## Frame inventory

- Normal (45): idle 4, walk 6, jump 2, crouch 1, punch_l/r 4+4, kick_l/r 4+4, Q 4,
  transform 6, hurt 2, KO 4.
- Flame form (41): idle 4, walk 6, jump 2, crouch 1, punch_l/r 4+4, kick_l/r 4+4, Q 4, hurt 2, KO 4, revert 2.
- Warrior (36): idle 4, walk 6, jump 2, axe_slash 6, axe_throw 7, dash 5, hurt 2, KO 4.
- Lina: 256x256 RGBA, feet-center pivot (128,244), body about 210px. Warrior: 384x384 RGBA, pivot
  (192,372), body about 230px.
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
