"""Create labeled contact sheets for reviewing the icon family."""
from pathlib import Path
import json
from PIL import Image, ImageDraw, ImageFont

ROOT=Path(__file__).parent
BASE=ROOT/'skill-icons'
CAT=json.loads((BASE/'catalog.json').read_text(encoding='utf-8'))
FONT='C:/Windows/Fonts/segoeui.ttf'
BOLD='C:/Windows/Fonts/segoeuib.ttf'

def font(n,bold=False):return ImageFont.truetype(BOLD if bold else FONT,n)
def tile(img,d,x,y,entry,w=270):
    d.rounded_rectangle((x,y,x+w,y+204),12,fill='#0f2a3b',outline='#526f73',width=2)
    path=BASE/entry['png128'].replace('png128','png256')
    mark=Image.open(path).convert('RGBA').resize((148,148),Image.Resampling.LANCZOS)
    img.alpha_composite(mark,(x+(w-148)//2,y+10))
    label=entry['name'];f=font(19,True)
    while d.textbbox((0,0),label,font=f)[2]>w-22:f=font(f.size-1,True)
    d.text((x+w//2,y+170),label,font=f,fill='#f4e8c8',anchor='mm')

im=Image.new('RGBA',(1510,1170),'#071c2a');d=ImageDraw.Draw(im)
d.text((52,38),'Character Skills',font=font(38,True),fill='#f4e8c8')
for row,(char,entries) in enumerate(CAT['characters'].items()):
    y=95+row*264
    d.text((53,y),char.replace('-',' ').title(),font=font(22,True),fill='#81d3d9')
    for col,entry in enumerate(entries):tile(im,d,53+col*290,y+34,entry)
im.convert('RGB').save(BASE/'character-skills-sheet.png')

im=Image.new('RGBA',(1230,330),'#071c2a');d=ImageDraw.Draw(im)
d.text((45,25),'Items',font=font(34,True),fill='#f4e8c8')
for col,entry in enumerate(CAT['items']):tile(im,d,45+col*295,85,entry,w=275)
im.convert('RGB').save(BASE/'item-icons-sheet.png')

variants=Image.new('RGBA',(1230,340),'#071c2a');vd=ImageDraw.Draw(variants)
vd.text((45,25),'Nyra Steel · Original and Redesigned',font=font(34,True),fill='#f4e8c8')
redesigned=[entry for entry in CAT['characters']['nyra-steel'] if 'originalSvg' in entry]
for pair,entry in enumerate(redesigned):
    old=dict(entry)
    old['name']=entry['name']+' · Original'
    old['png128']=entry['originalSvg'].replace('nyra-steel/','nyra-steel/png128/').replace('.svg','.png')
    new=dict(entry)
    new['name']=entry['name']+' · New'
    tile(variants,vd,45+pair*590,85,old,w=275)
    tile(variants,vd,45+pair*590+295,85,new,w=275)
variants.convert('RGB').save(BASE/'nyra-steel-variants-sheet.png')
print('Wrote character and item contact sheets')
