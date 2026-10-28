"""Build editable vector UI resources for Island Survival."""
from pathlib import Path

ROOT = Path(__file__).parent
ICONS = ROOT / "icons"
CHROME = ROOT / "chrome"
ICONS.mkdir(exist_ok=True)
CHROME.mkdir(exist_ok=True)

INK = '#e8d3a0'
GOLD = '#e9b96d'
RED = '#e97570'
BLUE = '#83cee2'

def svg(body, size=64, stroke=INK):
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 64 64" fill="none" stroke="{stroke}" stroke-width="3" stroke-linecap="round" stroke-linejoin="round">{body}</svg>'''

shapes = {
    'settings': '<circle cx="32" cy="32" r="10"/><path d="M27 5h10l2 7 6 3 7-3 6 9-5 6v10l5 6-6 9-7-3-6 3-2 7H27l-2-7-6-3-7 3-6-9 5-6V27l-5-6 6-9 7 3 6-3z"/>',
    'level': '<path d="M32 5 39 21l17 2-13 11 4 18-15-9-15 9 4-18L8 23l17-2z"/><path d="M32 20v17m-5-12 5-5 5 5"/>',
    'exp': '<path d="M32 5 50 22 43 49 32 58 21 49 14 22z"/><path d="M32 14 40 27 32 48 24 27z"/>',
    'hp': '<path d="M32 54 9 32C-1 19 14 3 27 16l5 6 5-6C50 3 65 19 55 32z"/><path d="M20 32h7l4-7 4 14 4-7h6"/>',
    'atk': '<path d="M28 5h8v6h5v23h5v6H18v-6h5V11h5z" fill="#a9d8dd"/><path d="M28 40h8v14h-8z" fill="#c5964d"/><path d="M23 54h18v5H23z" fill="#e9bd75"/><path d="M28 11h8"/>',
    'basic-atk': '<path d="M28 5h8v6h5v23h5v6H18v-6h5V11h5z" fill="#a9d8dd"/><path d="M28 40h8v14h-8z" fill="#c5964d"/><path d="M23 54h18v5H23z" fill="#e9bd75"/><path d="M28 18h8" stroke="#e9bd75"/>',
    'extra-atk': '<path d="M28 5h8v6h5v23h5v6H18v-6h5V11h5z" fill="#a9d8dd"/><path d="M28 40h8v14h-8z" fill="#c5964d"/><path d="M23 54h18v5H23z" fill="#e9bd75"/><path d="m49 6 2 5 5 2-5 2-2 5-2-5-5-2 5-2z" fill="#81d3d9"/>',
    'gold': '<ellipse cx="32" cy="32" rx="23" ry="23"/><ellipse cx="32" cy="32" rx="16" ry="16"/><path d="M37 23c-7-5-14-2-14 4 0 8 17 3 17 12 0 6-9 9-17 4m9-26v30"/>',
    'fullness': '<path d="M13 45c-4-2-6-9-4-16 2-8 10-13 18-10 5-6 15-6 20 1 8 1 12 8 10 15-1 5-5 8-9 10z"/><path d="M13 45v7h35v-7m-22-24-4 11m17-11-3 11"/>',
    'mouse-left': '<rect x="17" y="6" width="30" height="50" rx="15"/><path d="M32 6v22M17 28h30M24 13v9"/>',
    'mouse-right': '<rect x="17" y="6" width="30" height="50" rx="15"/><path d="M32 6v22M17 28h30M40 13v9"/>',
    'mouse-middle': '<rect x="17" y="6" width="30" height="50" rx="15"/><path d="M32 6v22M17 28h30M32 12v8"/>',
    'passive': '<circle cx="32" cy="32" r="21"/><path d="m32 15 4 13 13 4-13 4-4 13-4-13-13-4 13-4z"/>',
    'skill-q': '<circle cx="32" cy="32" r="22"/><path d="M18 39c10-24 22-22 28-10 5 12-5 21-17 16m10-7 11 11"/>',
    'skill-e': '<circle cx="32" cy="32" r="22"/><path d="M42 20H24v24h19M24 32h15"/>',
    'volume': '<path d="M10 26h10l12-10v32L20 38H10zM40 24c7 4 7 12 0 16m6-23c12 8 12 22 0 30"/>',
    'chevron': '<path d="m23 13 19 19-19 19"/>',
    'close': '<path d="M17 17 47 47M47 17 17 47"/>',
    'back': '<path d="m39 12-20 20 20 20M20 32h32"/>',
}
for name, shape in shapes.items():
    color = RED if name == 'hp' else BLUE if name in ('exp','skill-q') else GOLD if name in ('gold','level','atk','basic-atk','extra-atk') else INK
    (ICONS / f'{name}.svg').write_text(svg(shape, stroke=color), encoding='utf-8')

button = '<rect x="2" y="2" width="316" height="76" rx="8" fill="{fill}" stroke="{stroke}" stroke-width="2"/><path d="M16 16h12M16 16v12M304 16h-12M304 16v12M16 64h12M16 64V52M304 64h-12M304 64V52" stroke="{stroke}" stroke-width="2"/>'
for name, fill, stroke in [('default','#152d3a','#b49765'),('hover','#274654','#f4cf85'),('selected','#37636a','#f7d899'),('disabled','#24313a','#677680')]:
    s=f'<svg xmlns="http://www.w3.org/2000/svg" width="320" height="80" viewBox="0 0 320 80">{button.format(fill=fill,stroke=stroke)}</svg>'
    (CHROME/f'button-{name}.svg').write_text(s, encoding='utf-8')

(CHROME/'panel.svg').write_text('''<svg xmlns="http://www.w3.org/2000/svg" width="640" height="720" viewBox="0 0 640 720"><rect width="640" height="720" rx="10" fill="#0a1f2d" fill-opacity=".94" stroke="#bc9b67" stroke-width="3"/><path d="M24 24h80M24 24v80M616 24h-80M616 24v80M24 696h80M24 696v-80M616 696h-80M616 696v-80" fill="none" stroke="#e8c384" stroke-width="3"/><path d="M40 110h560M40 610h560" stroke="#6b7b77" stroke-width="1"/></svg>''',encoding='utf-8')
print(f'Wrote {len(shapes)} icons and 5 chrome assets')
