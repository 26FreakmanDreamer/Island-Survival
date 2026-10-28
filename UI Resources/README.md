# Island Survival — main menu and New Game UI

This folder contains the visual design for the main menu and the New Game flow described in `instruction.docx`. Open `preview.html` to move between the designed screens. The preview is a design prototype; it does not write saves, change audio settings, play an intro movie, or launch gameplay.

## Deliverables

| Location | Contents |
| --- | --- |
| `preview.html` | Editable, locally browsable UI prototype with menu, story layout, four character selections, initial status, settings, no-save message, and exit confirmation |
| `previews/` | 1920×1080 screen images, plus 1280×720 checks for the menu and character selection |
| `icons/` | 19 transparent SVG icons, plus 64×64 and 128×128 transparent PNG exports, including Level, EXP, HP, ATK, Basic ATK, Extra ATK, Gold, Fullness, mouse controls, Q/E, Settings, Volume |
| `chrome/` | Transparent SVG and PNG panel, plus four 320×80 button states: default, hover, selected, disabled |
| `artwork/` | Local copies of the existing island background and four canonical character images so this folder is portable |
| `build_assets.py`, `export_vectors.js`, `export_previews.py` | Editable source used to rebuild the vector assets, PNG exports and screen images |
| `Island Survival Character Skills and Items.docx` | Approved English names and effect summaries for 20 character skills and four items |
| `skill-icons/` | 24 individual transparent skill and item icons as editable SVGs and 64×64, 128×128, 256×256 PNGs; `catalog.json` maps names, slots and files |
| `skill-icons/character-skills-sheet.png`, `skill-icons/item-icons-sheet.png` | Review sheets showing the complete icon families |
| `skill-icons/nyra-steel-variants-sheet.png` | Side-by-side comparison of the original and redesigned Blade Arc and Steel Rush icons |
| `build_skill_document.py`, `build_skill_icons.py`, `export_skill_icons.js`, `make_skill_sheets.py` | Sources for rebuilding the name document and icon set |

## Visual system

- Art direction: island expedition at dusk, with deep navy panels, sea-glass highlights, old-paper text and restrained brass accents. The existing pixel landscape and characters remain the visual focus.
- Core colors: deep navy `#071c2a`, ink `#f4e8c8`, muted `#b8c9c4`, brass `#e9bd75`, sea-glass `#81d3d9`, coral `#ec8174`.
- Type: Georgia for titles and primary actions; Segoe UI for descriptions, settings and numbers. The UI text is English.
- Base composition: 1920×1080. `preview.html` scales the 1920×1080 composition uniformly to the browser window. The `1280×720` exports show its intended game-window reduction.
- The character roster preserves the requested names: Lina Seabright, Nyra Steel, Rhea Thorn and Eira Frostveil. Lina v1 is her starting form; Lina v2 is her flame form and is not listed as a fifth character.
- The character selector displays each approved skill name with its corresponding icon. Each character has a distinct five-icon color family; item icons use their own protective or restorative motifs.
- Blade Arc and Steel Rush use redesigned `-v2` icons in the catalog and character selector. Their original SVGs and PNGs remain in `skill-icons/nyra-steel/` for comparison or rollback.
- Three ATK icons use a shared pixel sword silhouette with small variations. Fullness uses bread. The mouse controls are highlighted in coral in Operation Settings.

## Screen flow

`Main Menu → Opening Story layout → Choose One Character → Initial Status → Continue`.

Continue Game without a save shows `No Existing Game`. Settings opens Operation Settings or Sound and Volume. Exit Game opens a confirmation concept that states progress is saved before exit. The opening-story screen specifies the framing and copy for the full-screen video; production footage and playback remain future game work.

## Source and implementation notes

The artwork in `artwork/` is copied from `assets/backgrounds/island-start-screen-16x9.png`, `Image/Character/*.png`, and `Image/Character/Posters/lina-seabright-v1-poster.png`. No character image was generated or modified. Preserve those canonical filenames and versions when integrating the screens into the Pygame UI.

The initial status shows the specification's starting values: Level 1, EXP 0, HP 100, ATK 20, Basic ATK 20, Extra ATK 0, Gold 20, and Fullness 6. The game should compute ATK as Basic ATK + Extra ATK.

The SVG resources are source assets. Pygame can use the ready-to-use PNG copies in `icons/png64/`, `icons/png128/`, `skill-icons/*/png64/`, `skill-icons/*/png128/`, `skill-icons/*/png256/`, and `chrome/png/`. `preview.html` uses SVGs directly. The screenshots in `previews/` are review images and should not be used as clickable game UI.
