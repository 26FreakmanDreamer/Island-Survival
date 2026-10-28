"""Quick integrity check for the standalone design deliverables."""
from pathlib import Path
import json
import re
import xml.etree.ElementTree as ET
from PIL import Image
from docx import Document

root = Path(__file__).parent
html = (root / 'preview.html').read_text(encoding='utf-8')
manifest = json.loads((root / 'manifest.json').read_text(encoding='utf-8'))

references = re.findall(r'(?:src="|url\(\x27)([^"\x27]+)', html)
missing = [x for x in references if '${' not in x and not (root / x).exists()]
assert not missing, f'Missing preview assets: {missing}'
for name in ('lina-seabright-v1-256.png', 'nyra-steel-256.png',
             'rhea-thorn-256.png', 'eira-frostveil-256.png'):
    assert (root / 'artwork' / name).exists(), name

svg = list(root.glob('icons/*.svg')) + list(root.glob('chrome/*.svg'))
for path in svg:
    ET.parse(path)

previews = list(root.glob('previews/*.png'))
for path in previews:
    with Image.open(path) as image:
        image.verify()
sizes = {Image.open(path).size for path in previews}
assert sizes == {(1920, 1080), (1280, 720)}, sizes
for value in manifest['screens'].values():
    for name in value if isinstance(value, list) else [value]:
        assert (root / name).exists(), name

icon_png = list(root.glob('icons/png*/*.png'))
chrome_png = list(root.glob('chrome/png/*.png'))
assert len(icon_png) == 38, len(icon_png)
assert len(chrome_png) == 5, len(chrome_png)
for path in icon_png + chrome_png:
    with Image.open(path) as image:
        assert image.mode == 'RGBA', path
        assert image.getextrema()[3][0] == 0, f'No transparency: {path}'

catalog = json.loads((root / manifest['skillIconCatalog']).read_text(encoding='utf-8'))
entries = [entry for character in catalog['characters'].values() for entry in character] + catalog['items']
assert len(catalog['characters']) == 4 and all(len(skills) == 5 for skills in catalog['characters'].values())
assert len(catalog['items']) == 4 and len(entries) == 24
names = [entry['name'] for entry in entries]
assert len(names) == len(set(names)), 'Repeated skill or item name'
document = Document(root / manifest['skillNamesDocument'])
document_text = '\n'.join(cell.text for table in document.tables for row in table.rows for cell in row.cells)
for entry in entries:
    assert entry['name'] in document_text, f"Missing document name: {entry['name']}"
    svg_path = root / 'skill-icons' / entry['svg']
    ET.parse(svg_path)
    for size in (64, 128, 256):
        png_path = root / 'skill-icons' / entry['png128'].replace('/png128/', f'/png{size}/')
        with Image.open(png_path) as image:
            assert image.size == (size, size), png_path
            assert image.mode == 'RGBA' and image.getextrema()[3][0] == 0, png_path
    if entry not in catalog['items']:
        assert entry['svg'] in html and entry['name'] in html, f"Missing UI skill: {entry['name']}"
originals = [entry['originalSvg'] for entry in entries if 'originalSvg' in entry]
assert len(originals) == 2, originals
for svg_name in originals:
    ET.parse(root / 'skill-icons' / svg_name)
    original_png = svg_name.replace('nyra-steel/', 'nyra-steel/png128/').replace('.svg', '.png')
    for size in (64, 128, 256):
        with Image.open(root / 'skill-icons' / original_png.replace('/png128/', f'/png{size}/')) as image:
            assert image.size == (size, size) and image.mode == 'RGBA'
for sheet in manifest['skillIconSheets']:
    with Image.open(root / sheet) as image:
        image.verify()

print(f'OK: {len(previews)} previews, {len(svg)} SVGs, '
      f'{len(icon_png)} icon PNGs, {len(chrome_png)} chrome PNGs, '
      f'{len(entries)} named skill/item icons in three PNG sizes')
