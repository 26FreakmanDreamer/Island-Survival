# Animation asset pipeline

## Source rules

- `Image/Character/lina-seabright-v1-256.png` is the appearance reference; `v2` is the red/black
  palette reference. `Image/Enemy/` is for later enemy work. Never overwrite `Image/`.
- The approved side-view base is `assets/generated/base/lina_side_base.png`. All normal frames are
  generated from it and imported with a fixed scale of body height 210px.
- Normal frames live in `assets/frames/lina/<action>/`; flame-form frames live in
  `assets/frames/lina/flame/<action>/`.
- `game/data/animations.json` defines the normal `clips` and the `flame_clips`.

## Frame inventory

- Normal (45): idle 4, walk 6, jump 2, crouch 1, punch_l/r 4+4, kick_l/r 4+4, Q 4,
  transform 6, hurt 2, KO 4.
- Flame form (33): idle 4, walk 6, jump 2, crouch 1, punch_l/r 4+4, kick_l/r 4+4, Q 4.
- 256x256 RGBA. Pivot is feet-center (128,244); the character body is about 210px tall.
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

`collect_frames.py` copies the newest matching Seedream output per custom name into an action folder.
`import_frames.py` normalizes to 256x256 with feet-center anchoring; for flame frames, the pose
reference supplies the body scale/position while the fire aura may be larger than the body.
`contact_sheet.py` renders a labeled checkerboard sheet with the pivot cross for approval.

The importer's background removal is two-stage: a corner flood fill for uniform gray/white backdrops,
plus a connected near-white mask for checkerboards. In `--pose-ref` mode it also removes remaining
near-white pixels outside the pose silhouette, without touching the character's white clothing.
Near-transparent pixels (alpha < 10) are cleared.

## Approval and install

1. Generate candidates into `assets/generated/raw/lina_frames/`.
2. Collect the chosen files into `assets/generated/raw/<action>/`.
3. Import into `assets/generated/staged/<action>/`.
4. Build a contact sheet and review it (pose, limb identity, feet alignment, effects).
5. Copy approved frames to `assets/frames/lina/<action>/` or `assets/frames/lina/flame/<action>/`.
6. Press F5 in-game after replacing frames; the animation cache invalidates on path + mtime.

Canonical `Image/` files are read-only. Generated candidates, staging folders and contact sheets are
kept under `assets/generated/` for traceability.
