"""Export review PNGs from the Island Survival UI design at 1920x1080."""
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from pathlib import Path
import json

ROOT=Path(__file__).parent
ART=ROOT/'artwork'
OUT=ROOT/'previews'
OUT.mkdir(exist_ok=True)
W,H=1920,1080
GOLD='#e9bd75'; INK='#f4e8c8'; MUTED='#b8c9c4'; SEA='#81d3d9'; DEEP='#0a2231'; RED='#ec8174'
GEORGIA='C:/Windows/Fonts/georgia.ttf'; GEORGIAB='C:/Windows/Fonts/georgiab.ttf'; SEGOE='C:/Windows/Fonts/segoeui.ttf'; SEGOEB='C:/Windows/Fonts/segoeuib.ttf'

def font(size,bold=False,serif=False): return ImageFont.truetype(GEORGIAB if serif and bold else GEORGIA if serif else SEGOEB if bold else SEGOE,size)
def base(dim=.48):
    im=Image.open(ART/'island-start-screen-16x9.png').convert('RGB').resize((W,H),Image.Resampling.LANCZOS).convert('RGBA')
    over=Image.new('RGBA',(W,H),(2,15,27,int(dim*255))); im=Image.alpha_composite(im,over)
    d=ImageDraw.Draw(im);d.line((80,56,1840,56),fill=GOLD,width=2);d.text((1810,45),'✧',font=font(34,serif=True),fill=GOLD)
    d.text((1487,1019),'SURVIVE ANOTHER DAY',font=font(18,bold=True),fill=MUTED)
    return im,d
def panel(d,box,fill=(7,27,41,239)):
    d.rounded_rectangle(box,10,fill=fill,outline='#b89a69',width=3)
    x1,y1,x2,y2=box; c='#e5c082'
    for x,sgn in [(x1+22,1),(x2-22,-1)]:
        for y,ysgn in [(y1+22,1),(y2-22,-1)]:
            d.line((x,y,x+sgn*70,y),fill=c,width=3);d.line((x,y,x,y+ysgn*70),fill=c,width=3)
def translucent_panel(im,box,alpha=153):
    overlay=Image.new('RGBA',(W,H),(0,0,0,0))
    draw=ImageDraw.Draw(overlay)
    draw.rounded_rectangle(box,10,fill=(7,27,41,alpha),outline=(184,154,105,205),width=3)
    im=Image.alpha_composite(im,overlay)
    d=ImageDraw.Draw(im)
    x1,y1,x2,y2=box
    for x,sgn in [(x1+22,1),(x2-22,-1)]:
        for y,ysgn in [(y1+22,1),(y2-22,-1)]:
            d.line((x,y,x+sgn*70,y),fill=GOLD,width=3)
            d.line((x,y,x,y+ysgn*70),fill=GOLD,width=3)
    return im,d
def txt(d,xy,text,size=25,color=INK,bold=False,serif=False,anchor=None):
    d.text(xy,text,font=font(size,bold,serif),fill=color,anchor=anchor)
def symbol(d,cx,cy,kind,size=45):
    """Tiny raster companion to the editable SVG icon set."""
    s=size/45; x=lambda n:cx+n*s; y=lambda n:cy+n*s
    if kind=='settings':
        d.ellipse((x(-16),y(-16),x(16),y(16)),outline=GOLD,width=max(2,int(3*s)))
        d.ellipse((x(-6),y(-6),x(6),y(6)),outline=GOLD,width=max(2,int(3*s)))
        for dx,dy in [(0,-21),(0,21),(-21,0),(21,0),(-15,-15),(15,15),(-15,15),(15,-15)]:d.ellipse((x(dx-3),y(dy-3),x(dx+3),y(dy+3)),fill=GOLD)
    elif kind=='level':
        pts=[(0,-20),(5,-6),(20,-6),(8,3),(12,19),(0,10),(-12,19),(-8,3),(-20,-6),(-5,-6)]
        d.polygon([(x(a),y(b)) for a,b in pts],outline=GOLD);d.ellipse((x(-3),y(-3),x(3),y(3)),fill=GOLD)
    elif kind=='exp':
        d.polygon([(x(0),y(-21)),(x(15),y(-4)),(x(11),y(12)),(x(0),y(21)),(x(-11),y(12)),(x(-15),y(-4))],outline=SEA)
        d.line((x(0),y(-14),x(0),y(13)),fill=SEA,width=max(2,int(3*s)))
    elif kind=='hp':
        pts=[(-19,-4),(-15,-15),(-6,-17),(0,-9),(6,-17),(15,-15),(19,-4),(17,5),(0,20),(-17,5)]
        d.polygon([(x(a),y(b)) for a,b in pts],fill=RED)
    elif kind in ('atk','basic-atk','extra-atk'):
        d.rectangle((x(-5),y(-20),x(5),y(8)),fill='#a9d8dd',outline=GOLD,width=2);d.rectangle((x(-13),y(8),x(13),y(14)),fill=GOLD);d.rectangle((x(-3),y(14),x(3),y(21)),fill=GOLD)
        if kind=='extra-atk':d.line((x(12),y(-17),x(19),y(-10)),fill=SEA,width=3);d.line((x(19),y(-17),x(12),y(-10)),fill=SEA,width=3)
    elif kind=='gold':
        d.ellipse((x(-19),y(-19),x(19),y(19)),fill=GOLD,outline='#805d2d',width=2);txt(d,(cx,cy-1),'$',25,DEEP,True,anchor='mm')
    elif kind=='fullness':
        d.rounded_rectangle((x(-20),y(-9),x(20),y(16)),8,fill='#dbaa66',outline=GOLD,width=2)
        d.ellipse((x(-20),y(-17),x(0),y(7)),fill='#eac585');d.ellipse((x(-2),y(-18),x(20),y(6)),fill='#eac585')
        d.line((x(-8),y(-8),x(-12),y(4)),fill='#ad7440',width=2);d.line((x(7),y(-8),x(4),y(4)),fill='#ad7440',width=2)
    elif kind=='passive':
        d.ellipse((x(-17),y(-17),x(17),y(17)),outline=GOLD,width=2);d.polygon([(x(0),y(-12)),(x(4),y(-3)),(x(13),y(0)),(x(4),y(3)),(x(0),y(12)),(x(-4),y(3)),(x(-13),y(0)),(x(-4),y(-3))],fill=GOLD)
def button(d,box,label,active=False):
    x1,y1,x2,y2=box;d.rounded_rectangle(box,8,fill='#37636a' if active else '#152d3a',outline='#f4cf85' if active else '#b49765',width=3)
    d.line((x1+15,y1+15,x1+35,y1+15),fill=GOLD,width=2);d.line((x2-35,y2-15,x2-15,y2-15),fill=GOLD,width=2)
    txt(d,((x1+x2)//2,(y1+y2)//2),label,25,serif=True,bold=True,anchor='mm')
def sprite(im,name,box):
    sp=Image.open(ART/name).convert('RGBA'); x1,y1,x2,y2=box; size=min(x2-x1,y2-y1)
    sp=sp.resize((size,size),Image.Resampling.NEAREST);im.alpha_composite(sp,(x1+(x2-x1-size)//2,y1+(y2-y1-size)//2))
def save(im,name): im.convert('RGB').save(OUT/name,quality=95)
def heading(d,text):txt(d,(80,82),text,57,serif=True)

im,d=base(.21)
im,d=translucent_panel(im,(260,165,930,920))
txt(d,(335,247),'THE UNKNOWN SHORE',19,GOLD,True)
txt(d,(335,315),'ISLAND',95,serif=True,bold=True)
txt(d,(335,405),'SURVIVAL',95,serif=True,bold=True)
d.rectangle((335,532,416,536),fill=GOLD)
txt(d,(335,561),'An island to explore. A day to survive.',22,MUTED)
button(d,(335,635,775,715),'New Game')
button(d,(335,728,775,808),'Continue Game')
button(d,(335,821,775,901),'Exit Game')
symbol(d,218,1001,'settings',33)
txt(d,(244,985),'SETTINGS',24,INK,True)
txt(d,(1190,655),'Where will your',40,serif=True)
txt(d,(1240,705),'story begin?',40,serif=True)
txt(d,(1261,765),'FOUR HEROES · ONE ISLAND',18,INK,True)
save(im,'01-main-menu.png')

im,d=base(.52);txt(d,(88,90),'←  BACK',21,INK,True);panel(d,(180,232,1130,855));txt(d,(260,302),'OPENING STORY · VIDEO LAYOUT',17,SEA,True);txt(d,(260,345),'The unknown island',75,serif=True);d.rectangle((260,445,340,449),fill=GOLD)
story=['Your team is stranded on an unfamiliar shore.','Defeat enemies to grow stronger. Earn gold to buy','supplies and food. Survive as many days as you can.']
for j,line in enumerate(story):txt(d,(260,500+j*48),line,27)
button(d,(260,716,580,796),'Choose a Hero');button(d,(600,716,920,796),'Skip Intro')
poster=Image.open(ART/'lina-seabright-v1-poster.png').convert('RGBA');poster.thumbnail((450,680));im.alpha_composite(poster,(1340,185));d=ImageDraw.Draw(im);d.rectangle((1336,181,1794,873),outline=GOLD,width=4);save(im,'02-opening-story-layout.png')

characters=[('Lina Seabright','lina-seabright-v1-256.png','BASE FORM · LINA V1','An agile fighter whose hits build energy.','Her flame form is an alternate form.'),('Nyra Steel','nyra-steel-256.png','STEEL MARKS','A close-range striker who marks enemies.','Four marks trigger a burst of damage.'),('Rhea Thorn','rhea-thorn-256.png','THORN & VENOM','A blade specialist with poisonous knives.','Poison effects last longer against her foes.'),('Eira Frostveil','eira-frostveil-256.png','FROST AWAKENING','A frost wielder who builds freezing power.','Full frost briefly freezes an enemy.')]
skill_catalog=json.loads((ROOT/'skill-icons/catalog.json').read_text(encoding='utf-8'))['characters']
skill_order=[('left-mouse','LMB'),('right-mouse','RMB'),('passive','PASSIVE'),('q','Q'),('e','E')]
for ix,(name,file,form,desc1,desc2) in enumerate(characters):
    im,d=base(.50);heading(d,'Choose One Character');panel(d,(70,153,1850,977));d.line((425,154,425,976),fill='#8a8065',width=2);d.line((1080,154,1080,976),fill='#8a8065',width=2)
    txt(d,(119,213),'SELECT YOUR HERO',17,SEA,True)
    for j,c in enumerate(characters):
        y=267+j*111
        if ix==j:d.rounded_rectangle((93,y-12,412,y+70),5,fill='#2e5960');d.rectangle((93,y-12,98,y+70),fill=GOLD)
        txt(d,(116,y+8),c[0],27,GOLD if ix==j else MUTED,serif=True)
        d.line((93,y+83,410,y+83),fill='#627575',width=1)
    txt(d,(474,215),'CHARACTER INTRO',17,SEA,True);txt(d,(474,260),name,48,serif=True);txt(d,(474,344),desc1,21);txt(d,(474,378),desc2,21)
    txt(d,(474,445),'COMBAT ABILITIES',17,SEA,True)
    lookup={entry['slot']:entry for entry in skill_catalog[name.lower().replace(' ','-')]}
    for j,(slot,control) in enumerate(skill_order):
        skill=lookup[slot];y=497+j*73
        icon=Image.open(ROOT/'skill-icons'/skill['png128']).convert('RGBA').resize((52,52),Image.Resampling.LANCZOS)
        im.alpha_composite(icon,(475,y))
        txt(d,(548,y+12),f"{control}  ·  {skill['name']}",20)
    sprite(im,file,(1170,190,1765,752));d=ImageDraw.Draw(im);txt(d,(1445,790),name,36,serif=True,anchor='mm');txt(d,(1445,837),form,18,SEA,True,anchor='mm');button(d,(1435,878,1770,955),'Enter Game  ›');save(im,f'03-character-{ix+1}-{name.lower().replace(" ","-")}.png')

im,d=base(.52);txt(d,(80,82),'←  CHARACTER SELECT',20,INK,True);panel(d,(155,160,1765,940));d.line((665,162,665,938),fill='#718b82',width=2);sprite(im,'lina-seabright-v1-256.png',(210,205,600,748));d=ImageDraw.Draw(im);txt(d,(410,833),'Lina Seabright',37,serif=True,anchor='mm');txt(d,(735,216),'YOUR JOURNEY BEGINS',17,SEA,True);txt(d,(735,257),'Initial Status',59,serif=True);d.rectangle((735,342,815,346),fill=GOLD)
stats=[('LEVEL','1'),('EXP','0'),('HP','100'),('ATK','20'),('BASIC ATK','20'),('EXTRA ATK','0'),('GOLD','20'),('FULLNESS','6')]
for i,(label,value) in enumerate(stats):
    col=i%2; row=i//2; x=735+col*480;y=395+row*90;symbol(d,x+24,y+24,['level','exp','hp','atk','basic-atk','extra-atk','gold','fullness'][i],44);txt(d,(x+69,y+11),label,21,MUTED);txt(d,(x+405,y+11),value,28,INK,True,anchor='ra');d.line((x,y+67,x+418,y+67),fill='#668078',width=1)
txt(d,(735,837),'ATK = Basic ATK + Extra ATK',18,MUTED);button(d,(1330,824,1694,907),'Continue  ›');save(im,'04-initial-status.png')

im,d=base(.71);panel(d,(650,325,1270,760));txt(d,(960,430),'No Existing Game',51,serif=True,anchor='mm');txt(d,(960,510),'Start a new journey to create your first save.',23,MUTED,anchor='mm');button(d,(701,625,946,700),'New Game');button(d,(974,625,1219,700),'Back');save(im,'05-no-save.png')

for sound in (False,True):
    im,d=base(.53);txt(d,(80,88),'←  MAIN MENU',21,INK,True);panel(d,(155,154,1765,934));d.line((605,155,605,933),fill='#6f8179',width=2);txt(d,(210,219),'Settings',50,serif=True)
    for j,(title,icon) in enumerate([('Operation Settings','⚙'),('Sound and Volume','◖')]):
        y=320+j*88
        if (j==1)==sound:d.rounded_rectangle((184,y-15,570,y+55),4,fill='#2a5259')
        symbol(d,225,y+17,'settings' if j==0 else 'exp',28);txt(d,(249,y),title,24,GOLD if (j==1)==sound else MUTED,serif=True);d.line((190,y+66,570,y+66),fill='#607a76',width=1)
    txt(d,(212,581),'More settings can be added',18,MUTED);txt(d,(212,609),'as the game grows.',18,MUTED)
    if not sound:
        txt(d,(682,217),'Operation Settings',53,serif=True);txt(d,(682,294),'Movement, combat, and the keys that carry you through the island.',21,MUTED)
        rows=[('Move left','A'),('Move right','D'),('Jump','W / Space'),('Crouch','S / Shift'),('Skill 1','Q'),('Skill 2','E'),('Character info','C'),('Item slots','1 · 2 · 3 · 4'),('Basic attack 1','Left Mouse'),('Basic attack 2','Right Mouse'),('Lock on / off','Middle Mouse'),('Pause / back','Esc')]
        for i,(label,key) in enumerate(rows):
            col=i%2;row=i//2;x=685+col*510;y=369+row*71;txt(d,(x,y),label,19);color=RED if 'Mouse' in key else GOLD;d.rounded_rectangle((x+265,y-7,x+445,y+32),5,outline=color,width=2);txt(d,(x+355,y+12),key,17,color,True,anchor='mm');d.line((x,y+45,x+445,y+45),fill='#526c6b',width=1)
        name='06-settings-operation.png'
    else:
        txt(d,(682,217),'Sound and Volume',53,serif=True);txt(d,(682,294),'Balance the battle with the atmosphere of the island.',21,MUTED)
        for i,(label,value) in enumerate([('Battle sound','75%'),('Background music','60%')]):
            y=420+i*170;txt(d,(686,y),label,26);txt(d,(1540,y),value,25,GOLD,True);d.rounded_rectangle((686,y+65,1550,y+77),6,fill='#385560');d.rounded_rectangle((686,y+65,686+(648 if i==0 else 518),y+77),6,fill=GOLD);d.ellipse((686+(648 if i==0 else 518)-12,y+57,686+(648 if i==0 else 518)+12,y+85),fill=INK)
        name='07-settings-sound.png'
    button(d,(1459,842,1696,905),'Done');save(im,name)

im,d=base(.71);panel(d,(650,325,1270,760));txt(d,(960,425),'Exit Game?',53,serif=True,anchor='mm');txt(d,(960,510),'Your progress is saved before you leave.',23,MUTED,anchor='mm');button(d,(701,625,946,700),'Stay');button(d,(974,625,1219,700),'Save & Exit');save(im,'08-exit-confirmation.png')

for source,target in [('01-main-menu.png','main-menu-1280x720.png'),('03-character-1-lina-seabright.png','character-select-1280x720.png')]:
    Image.open(OUT/source).resize((1280,720),Image.Resampling.LANCZOS).save(OUT/target)
print('Exported',len(list(OUT.glob('*.png'))),'preview PNGs')
