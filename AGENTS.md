# Project asset memory

- Use the pictures in `Image/` as the default visual source for this project.
- `Image/Character/` contains the current character pictures; `Image/Enemy/` contains the current enemy pictures. Preserve the categories and character names reflected by their filenames when referring to or using them.
- For character and enemy artwork, prefer these files over the older pictures in `assets/characters/` and `assets/enemies/` unless the user specifies otherwise.
- Where `Image/` contains multiple named versions of a character, keep the version distinction and use the version the user requests or the context identifies.
- Before any image generation, read `docs/IMAGE_GENERATION_RULES.md` and apply its body-layering, weapon-hand/grip, no-interpenetration and size-lock checks.
