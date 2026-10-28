"""Author 24 transparent, scalable skill and item emblems."""
from pathlib import Path
import json

ROOT=Path(__file__).parent
OUT=ROOT/'skill-icons'
OUT.mkdir(exist_ok=True)

GROUPS={
 'lina-seabright': {
  'colors':('#70d8e6','#8d75e5'),
  'skills':[
   ('passive','Battle Rhythm','battle-rhythm','Energy rises with each successful hit.'),
   ('left-mouse','Breaker Punch','breaker-punch','Alternating punches.'),
   ('right-mouse','Surge Kick','surge-kick','Knockback kick.'),
   ('q','Gale Fist','gale-fist','Air-current punch.'),
   ('e','Flamewake','flamewake','Flame transformation.'),
  ]},
 'nyra-steel': {
  'colors':('#dbe7f5','#6b9be8'),
  'skills':[
   ('passive','Steelbrand','steelbrand','Stack and detonate sword marks.'),
   ('left-mouse','Edge Slash','edge-slash','Forward sword slash.'),
   ('right-mouse','Piercing Thrust','piercing-thrust','Extended sword thrust.'),
   ('q','Blade Arc','blade-arc','Broad sword wave.'),
   ('e','Steel Rush','steel-rush','Armored fighter dashes through enemies.'),
  ]},
 'rhea-thorn': {
  'colors':('#7bd3a0','#a975d0'),
  'skills':[
   ('passive','Lingering Venom','lingering-venom','Extend existing poison.'),
   ('left-mouse','Thorn Cut','thorn-cut','Alternating hand-held shuriken slashes.'),
   ('right-mouse','Razor Throw','razor-throw','Throw a regular shuriken.'),
   ('q','Nightshade Shuriken','nightshade-shuriken','Throw a poisoned shuriken.'),
   ('e','Rebound Strike','rebound-strike','Strike while dashing out and back.'),
  ]},
 'eira-frostveil': {
  'colors':('#a8edff','#729dec'),
  'skills':[
   ('passive','Frostbind','frostbind','Build freeze value.'),
   ('left-mouse','Snowbolt','snowbolt','Ranged snowball.'),
   ('right-mouse','Staff Strike','staff-strike','Close staff attack.'),
   ('q','Crystal Shard','crystal-shard','Triangular ice projectile.'),
   ('e','Winterfall','winterfall','Targeted falling ice sphere.'),
  ]},
}
ITEMS=[
 ('Sacred Shield','sacred-shield','Prevent damage for 2 seconds.',('#ebcb7c','#f7e3af')),
 ('Steadfast Charm','steadfast-charm','Prevent control effects for 3 seconds.',('#a7badf','#e6dcb7')),
 ('Purity Seal','purity-seal','Cleanse, then prevent negative effects for 3 seconds.',('#90e4c8','#c8f5e5')),
 ('Vitality Tonic','vitality-tonic','Restore level-scaled HP plus 35% max HP.',('#f29591','#ffd5a5')),
]

# Every motif is drawn at 128 px with a unique central silhouette. The common
# octagonal rim keeps unrelated effects coherent in the game's skill bar.
MOTIFS={
 'battle-rhythm': '''<circle cx="64" cy="64" r="18" fill="none" stroke="{a}" stroke-width="7"/><path d="M18 65h20l8-21 15 41 10-25h18l8-18 12 24h6" fill="none" stroke="{b}" stroke-width="7" stroke-linecap="round" stroke-linejoin="round"/><path d="M27 37c6-9 16-15 28-17M101 91c-7 10-17 16-29 18" fill="none" stroke="{a}" stroke-width="5" stroke-linecap="round"/>''',
 'breaker-punch': '''<path d="M36 76 48 57l7-13 10 4 8-9 8 8 8 0 5 10-7 20-20 15-21 6z" fill="{a}" stroke="#e7faff" stroke-width="4" stroke-linejoin="round"/><path d="m46 56 31 14M57 48l25 13M68 44l19 8" stroke="#386a92" stroke-width="4"/><path d="M24 47 14 40m17-13-3-14M94 32l12-12M99 82l15 5" fill="none" stroke="{b}" stroke-width="7" stroke-linecap="round"/>''',
 'surge-kick': '''<path d="M24 83c21 4 31-14 39-42l16 6-2 25 31 16-6 15-39-8-15-14-16 18z" fill="{a}" stroke="#e8ffff" stroke-width="4" stroke-linejoin="round"/><path d="M27 103c38 11 68-8 81-27M14 70c25 2 41-19 46-41" fill="none" stroke="{b}" stroke-width="6" stroke-linecap="round"/><path d="m98 29 10-10m-5 30 14-2" stroke="{a}" stroke-width="5"/>''',
 'gale-fist': '''<path d="M31 65c9-13 20-23 35-26l13 9-2 27-24 15-25-4z" fill="{a}" stroke="#e9ffff" stroke-width="4"/><path d="M71 48 54 64m23-4-19 12" stroke="#2d728d" stroke-width="4"/><path d="M23 37c30-28 79-13 86 19M17 77c8 29 49 41 73 20M28 51 14 55m82 20 17 7" fill="none" stroke="{b}" stroke-width="6" stroke-linecap="round"/>''',
 'flamewake': '''<path d="M66 13c10 17 6 25 1 34 18-10 14-23 14-23 27 25 29 56 12 73-19 20-56 19-72-2-15-20-7-45 9-59-1 16 9 20 15 18-4-14 4-27 21-41Z" fill="#e8685f" stroke="#ffd097" stroke-width="4"/><path d="M60 55c9 12 5 17 2 23 8-4 12-11 12-11 9 12 9 24 3 29-9 9-27 7-32-4-5-10 1-23 15-37Z" fill="#ffd471"/><path d="m27 25-9-11m83 25 10-8" stroke="{b}" stroke-width="5" stroke-linecap="round"/>''',
 'steelbrand': '''<path d="m35 26 12 49M58 18l12 60M81 25l12 49" stroke="{a}" stroke-width="9" stroke-linecap="round"/><path d="m30 85 16 14 18-14 15 15 20-16" fill="none" stroke="{b}" stroke-width="6"/><path d="m101 30 5 13 12 4-12 5-5 13-5-13-12-5 12-4z" fill="#e6c884"/>''',
 'edge-slash': '''<path d="m24 88 46-49 10-22 18 16-22 12-46 49z" fill="{a}" stroke="#f9fbff" stroke-width="4"/><path d="m20 77 20 19m-18-8 16 15" stroke="#d9c78f" stroke-width="7"/><path d="M31 31c15-14 39-21 65-11M28 22l-8 17" fill="none" stroke="{b}" stroke-width="6" stroke-linecap="round"/>''',
 'piercing-thrust': '''<path d="M14 63h66l23-22 14 23-14 23-23-22H14z" fill="{a}" stroke="#f5fbff" stroke-width="4"/><path d="M32 46v36M22 49v30" stroke="#d6ba83" stroke-width="6"/><path d="M15 38h54M9 87h60" stroke="{b}" stroke-width="5" stroke-linecap="round"/>''',
 'blade-arc': '''<path d="M23 90c19-55 51-76 82-65-18 5-35 23-50 47 22-10 42-6 58 8-31-6-60 9-90 10Z" fill="{a}" stroke="#f5fbff" stroke-width="4"/><path d="M34 95c31-13 54-11 76 3M27 36c15-13 30-17 50-16" fill="none" stroke="{b}" stroke-width="6" stroke-linecap="round"/>''',
 'steel-rush': '''<path d="M35 99 77 29l16-11-1 19-42 70z" fill="{a}" stroke="#f5fbff" stroke-width="4"/><path d="M16 45h43M11 65h41M17 85h31" stroke="{b}" stroke-width="7" stroke-linecap="round"/><path d="m80 57 23 4-9 18" fill="none" stroke="#d9c78f" stroke-width="6"/>''',
 'blade-arc-v2': '''<path d="M33 92 75 41 86 20 94 17 89 35 48 83z" fill="#fbfdff" stroke="#b8d9f7" stroke-width="3" stroke-linejoin="round"/><path d="m34 80 21 17m-16-14-16 21" fill="none" stroke="#e9c985" stroke-width="6" stroke-linecap="round"/><path d="M78 27 109 31 91 45 114 52 94 65 113 75 82 78" fill="none" stroke="#4b9fe9" stroke-width="9" stroke-linecap="round" stroke-linejoin="round"/><path d="M80 26 108 30 90 45 113 52 93 65 111 75" fill="none" stroke="#c8efff" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/><path d="M56 97c18 4 36 1 48-7" fill="none" stroke="{b}" stroke-width="5" stroke-linecap="round"/>''',
 'steel-rush-v2': '''<path d="M17 47h26M12 65h31M15 84h24" fill="none" stroke="{b}" stroke-width="6" stroke-linecap="round"/><path d="M62 49 78 53 72 77 55 80 49 66z" fill="#f7fbff" stroke="#a8c8eb" stroke-width="3" stroke-linejoin="round"/><circle cx="81" cy="37" r="10" fill="#f7fbff" stroke="#a8c8eb" stroke-width="3"/><path d="m74 31 7-7 11 7-2 4" fill="{b}"/><path d="M69 57 89 62 103 53" fill="none" stroke="#e6f5ff" stroke-width="9" stroke-linecap="round" stroke-linejoin="round"/><path d="M57 57 42 49 32 58" fill="none" stroke="#b8d9f7" stroke-width="8" stroke-linecap="round" stroke-linejoin="round"/><path d="M63 76 83 85 101 100" fill="none" stroke="#f7fbff" stroke-width="11" stroke-linecap="round" stroke-linejoin="round"/><path d="M60 77 45 91 30 100" fill="none" stroke="#a8c8eb" stroke-width="10" stroke-linecap="round" stroke-linejoin="round"/><path d="m94 102 13 2M25 102l-10 3" fill="none" stroke="{b}" stroke-width="6" stroke-linecap="round"/>''',
 'lingering-venom': '''<path d="M64 21c10 20 27 36 27 56a27 27 0 0 1-54 0c0-20 17-36 27-56Z" fill="{a}" stroke="#d4ffe5" stroke-width="4"/><path d="M45 77a19 19 0 0 0 28 16M44 47c-18 7-26 20-25 38m91-22c3 20-6 39-25 47" fill="none" stroke="{b}" stroke-width="6" stroke-linecap="round"/><circle cx="61" cy="68" r="5" fill="{b}"/><circle cx="74" cy="80" r="4" fill="{b}"/>''',
 'thorn-cut': '''<path d="m26 31 20 20 25-26 8 8-25 26 28 29-9 9-29-28-18 20-10-10 20-20-19-20z" fill="{a}" stroke="#e2ffec" stroke-width="3"/><path d="m78 33 20-14-7 23M26 77 12 99l23-8" fill="{b}" stroke="{b}" stroke-width="3"/>''',
 'razor-throw': '''<path d="M64 17 76 47l34-11-22 29 24 25-35-8-13 29-12-30-35 9 23-27-23-27 34 11z" fill="{a}" stroke="#e9ffed" stroke-width="4"/><circle cx="64" cy="64" r="11" fill="#123c35" stroke="{b}" stroke-width="4"/><path d="M19 23c17-11 32-13 43-8M104 104c-13 9-26 11-39 9" fill="none" stroke="{b}" stroke-width="5" stroke-linecap="round"/>''',
 'nightshade-shuriken': '''<path d="M64 14 76 47l37-10-24 28 23 27-37-10-11 32-12-32-37 10 23-27-24-28 37 10z" fill="{a}" stroke="#e7ffed" stroke-width="4"/><circle cx="64" cy="64" r="15" fill="{b}" stroke="#d3a9f1" stroke-width="3"/><path d="M64 53c8 11 9 16 9 19a9 9 0 0 1-18 0c0-3 1-8 9-19Z" fill="#b7f28e"/><circle cx="94" cy="27" r="5" fill="{b}"/><circle cx="28" cy="99" r="4" fill="{b}"/>''',
 'rebound-strike': '''<path d="M26 43c17-22 56-22 75 0l-12 7 20 3-6-24-6 9M102 83c-16 23-57 23-76 1l12-7-20-3 7 24 6-9" fill="none" stroke="{a}" stroke-width="8" stroke-linecap="round" stroke-linejoin="round"/><path d="m48 53 16-20 16 20-16 13z" fill="{b}" stroke="#eaffec" stroke-width="3"/><path d="m48 75 16 20 16-20-16-13z" fill="{a}" stroke="#eaffec" stroke-width="3"/>''',
 'frostbind': '''<path d="M64 17v94M23 41l82 46M23 87l82-46" stroke="{a}" stroke-width="8" stroke-linecap="round"/><path d="m52 22 12-9 12 9M52 106l12 9 12-9M28 53l-14-7 1-15M99 75l14 8-1 15M28 75l-14 8 1 15M99 53l14-7-1-15" fill="none" stroke="{b}" stroke-width="5" stroke-linejoin="round"/><circle cx="64" cy="64" r="16" fill="#bceaf7" stroke="#f8ffff" stroke-width="3"/>''',
 'snowbolt': '''<circle cx="73" cy="56" r="27" fill="{a}" stroke="#f8ffff" stroke-width="5"/><path d="M15 55h27M10 74h32M20 91h27" stroke="{b}" stroke-width="7" stroke-linecap="round"/><path d="m73 35 7 11 11 1-8 9 3 11-13-6-9 7 1-13-10-7 13-2z" fill="#f5ffff"/>''',
 'staff-strike': '''<path d="m30 106 62-84" stroke="#d9c395" stroke-width="11" stroke-linecap="round"/><path d="m84 18 14 2 3 16-13 11-13-9z" fill="{a}" stroke="#f7ffff" stroke-width="4"/><path d="m30 100 13 8M59 40l13 10" stroke="{b}" stroke-width="5"/><path d="M20 54 10 48m18-14-6-14m77 46 17 3" stroke="{a}" stroke-width="6" stroke-linecap="round"/>''',
 'crystal-shard': '''<path d="M105 17 91 98 47 110 20 81Z" fill="{a}" stroke="#f8ffff" stroke-width="5" stroke-linejoin="round"/><path d="m105 17-56 58-2 35m2-35 42 23M20 81l29-6" fill="none" stroke="{b}" stroke-width="4"/><path d="M17 26 10 16m22 8-2-12" stroke="#f7ffff" stroke-width="5" stroke-linecap="round"/>''',
 'winterfall': '''<circle cx="66" cy="69" r="37" fill="{a}" stroke="#f9ffff" stroke-width="5"/><path d="m45 42 16 19-14 15 22 21m20-51-21 17 13 21" fill="none" stroke="{b}" stroke-width="5"/><path d="M34 11v21M64 7v20M95 12v19" stroke="#f9ffff" stroke-width="7" stroke-linecap="round"/><path d="M20 106h88" stroke="{a}" stroke-width="5" stroke-linecap="round"/>''',
 'sacred-shield': '''<path d="M64 17 99 31v33c0 28-19 43-35 50-16-7-35-22-35-50V31z" fill="{a}" stroke="#fff3cb" stroke-width="5"/><path d="M64 39v48m-22-24h44" stroke="#fff6d6" stroke-width="10" stroke-linecap="round"/><path d="M36 21a48 48 0 0 1 56 0" fill="none" stroke="{b}" stroke-width="5"/>''',
 'steadfast-charm': '''<path d="M48 26 64 15 80 26v18l18 18-11 43H41L30 62l18-18z" fill="{a}" stroke="#f7f2db" stroke-width="5"/><circle cx="64" cy="68" r="18" fill="#233f5e" stroke="{b}" stroke-width="4"/><path d="M55 70v-7a9 9 0 0 1 18 0v7m-19 0h20v14H54z" fill="none" stroke="#f7f2db" stroke-width="5" stroke-linejoin="round"/>''',
 'purity-seal': '''<circle cx="64" cy="64" r="41" fill="{a}" stroke="#e4fff4" stroke-width="5"/><circle cx="64" cy="64" r="29" fill="none" stroke="#eafff2" stroke-width="3"/><path d="M64 36v56M36 64h56m-48-20 40 40m0-40L44 84" stroke="#f4fff8" stroke-width="5"/><circle cx="64" cy="64" r="9" fill="{b}"/><path d="M24 24 14 12m90 12 10-12M24 104l-10 12m90-12 10 12" stroke="{b}" stroke-width="5" stroke-linecap="round"/>''',
 'vitality-tonic': '''<path d="M52 15h24v18l13 20v40c0 13-9 20-25 20s-25-7-25-20V53l13-20z" fill="{a}" stroke="#ffe3d5" stroke-width="5"/><path d="M45 61h38v28c0 10-7 17-19 17S45 99 45 89z" fill="#ec6e74"/><path d="M64 87 50 75c-7-7 2-17 10-10l4 4 4-4c8-7 17 3 10 10z" fill="#fff0da"/><path d="M49 16h30" stroke="{b}" stroke-width="7" stroke-linecap="round"/>''',
}

def write_icon(target,slug,a,b):
    motif=MOTIFS[slug].format(a=a,b=b)
    svg=f'''<svg xmlns="http://www.w3.org/2000/svg" width="128" height="128" viewBox="0 0 128 128">
<defs><linearGradient id="ground" x1="0" y1="0" x2="1" y2="1"><stop stop-color="#18384c"/><stop offset="1" stop-color="#071925"/></linearGradient></defs>
<path d="M33 5H95l28 28v62l-28 28H33L5 95V33z" fill="url(#ground)" fill-opacity=".94" stroke="{a}" stroke-width="4"/>
<path d="M36 13H92l23 23v56l-23 23H36L13 92V36z" fill="none" stroke="{b}" stroke-opacity=".48" stroke-width="2"/>
<path d="M26 13h16M102 13H86M26 115h16m60 0H86" stroke="{a}" stroke-width="3" stroke-linecap="round"/>
{motif}
</svg>'''
    target.write_text(svg,encoding='utf-8')

REDESIGNS={'blade-arc':'blade-arc-v2','steel-rush':'steel-rush-v2'}
catalog={'characters':{},'items':[]}
for char,group in GROUPS.items():
    folder=OUT/char;folder.mkdir(exist_ok=True)
    a,b=group['colors'];entries=[]
    for slot,name,slug,effect in group['skills']:
        original=f'{char}/{slot}-{slug}.svg';write_icon(OUT/original,slug,a,b)
        relative=f'{char}/{slot}-{REDESIGNS[slug]}.svg' if slug in REDESIGNS else original
        if slug in REDESIGNS: write_icon(OUT/relative,REDESIGNS[slug],a,b)
        entry={'slot':slot,'name':name,'effect':effect,'svg':relative,'png128':relative.replace('.svg','.png').replace(char+'/',char+'/png128/')}
        if slug in REDESIGNS: entry['originalSvg']=original
        entries.append(entry)
    catalog['characters'][char]=entries
folder=OUT/'items';folder.mkdir(exist_ok=True)
for name,slug,effect,(a,b) in ITEMS:
    relative=f'items/{slug}.svg';write_icon(OUT/relative,slug,a,b)
    catalog['items'].append({'name':name,'effect':effect,'svg':relative,'png128':relative.replace('items/','items/png128/').replace('.svg','.png')})
(OUT/'catalog.json').write_text(json.dumps(catalog,indent=2,ensure_ascii=False),encoding='utf-8')
print('Wrote 24 active skill and item SVG icons plus two preserved originals')
