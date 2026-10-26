# Project asset memory

- If you are Codex, read `CODEX-README.md` before taking action at the start of every new session working on or running this project. Other agents may ignore its rules.

- Use the pictures in `Image/` as the default visual source for this project.
- `Image/Character/` contains the current character pictures; `Image/Enemy/` contains the current enemy pictures. Preserve the categories and character names reflected by their filenames when referring to or using them.
- For character and enemy artwork, prefer these files over the older pictures in `assets/characters/` and `assets/enemies/` unless the user specifies otherwise.
- Where `Image/` contains multiple named versions of a character, keep the version distinction and use the version the user requests or the context identifies.
- Before any image generation, read `docs/IMAGE_GENERATION_RULES.md` and apply its body-layering, weapon-hand/grip, no-interpenetration and size-lock checks.

## Design and documentation workflow

- When designing or modifying character animations, animation effects (VFX), game code, or JSON data/smoke tests that change runtime behavior, finish the implementation and verification first. Do **not** update the explanatory text immediately; this avoids repeated edits.
- "Text" here means reader-facing documentation: `README.md`, `docs/*.md`, `AGENTS.md`, and `CODEX-README.md`. Code comments and docstrings change with the code and are not covered by this rule; `instruction.docx` is the authoritative spec and must never be modified proactively.
- Only after the user explicitly confirms the design/modification (for example "confirm", "OK", "this effect works", "keep it") may the text be updated. Passing smoke tests, completing the code, or generating preview images do **not** count as confirmation.
- After every confirmation, ask once: **"Should this design/modification be written into the text/docs?"** Only write after the user agrees; if the user says no, leave the text as is. Even if the original request mentioned updating docs, ask first; skip the question only when the user explicitly says "write directly" or "don't ask".
- Pure documentation cleanup, asset archiving, and similar work do not trigger this workflow.
