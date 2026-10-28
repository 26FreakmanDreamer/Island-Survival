"""Create the approved English skill and item name register."""
from pathlib import Path
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

ROOT=Path(__file__).parent
OUT=ROOT/'Island Survival Character Skills and Items.docx'

characters={
    'Lina Seabright':[
        ('Passive','Battle Rhythm','Gain energy when attacks hit.'),
        ('Left mouse','Breaker Punch','Alternating punches; gain 15 energy on hit.'),
        ('Right mouse','Surge Kick','Alternating knockback kicks; gain 20 energy on hit.'),
        ('Q','Gale Fist','Send an air current forward; gain 20 energy on hit.'),
        ('E','Flamewake','Spend 100 energy to enter a 10 second flame form and refresh Q.'),
    ],
    'Nyra Steel':[
        ('Passive','Steelbrand','Stack marks on hit; the fourth hit detonates them.'),
        ('Left mouse','Edge Slash','Slash forward once.'),
        ('Right mouse','Piercing Thrust','Thrust forward with increased reach.'),
        ('Q','Blade Arc','Release a broad sword wave.'),
        ('E','Steel Rush','Dash through the path and damage enemies along it.'),
    ],
    'Rhea Thorn':[
        ('Passive','Lingering Venom','Left and right attacks extend an existing poison effect.'),
        ('Left mouse','Thorn Cut','Alternate close-range shuriken strikes.'),
        ('Right mouse','Razor Throw','Throw a shuriken at an enemy.'),
        ('Q','Nightshade Shuriken','Throw a poisoned shuriken that deals damage over time.'),
        ('E','Rebound Strike','Dash into enemies, then return along the path.'),
    ],
    'Eira Frostveil':[
        ('Passive','Frostbind','Build freeze value; freeze an enemy at 100.'),
        ('Left mouse','Snowbolt','Send a ranged snowball that adds freeze value.'),
        ('Right mouse','Staff Strike','Strike at close range and add freeze value.'),
        ('Q','Crystal Shard','Launch a triangular ice shard; bonus damage to frozen enemies.'),
        ('E','Winterfall','Choose a horizontal target area for a falling ice sphere.'),
    ],
}
items=[
    ('Sacred Shield','Prevent all damage for 2 seconds.'),
    ('Steadfast Charm','Prevent control effects for 3 seconds.'),
    ('Purity Seal','Clear current negative effects, then prevent them for 3 seconds.'),
    ('Vitality Tonic','Restore 50 × Level + 35% of maximum HP.'),
]

def shade(cell,fill):
    tcPr=cell._tc.get_or_add_tcPr(); shd=OxmlElement('w:shd'); shd.set(qn('w:fill'),fill); tcPr.append(shd)
def border(cell,color='D9D9D9'):
    tcPr=cell._tc.get_or_add_tcPr(); borders=tcPr.first_child_found_in('w:tcBorders')
    if borders is None: borders=OxmlElement('w:tcBorders'); tcPr.append(borders)
    for edge in ('top','left','bottom','right'):
        el=OxmlElement('w:'+edge); el.set(qn('w:val'),'single'); el.set(qn('w:sz'),'4'); el.set(qn('w:color'),color); borders.append(el)
def margin(cell,top=95,start=125,bottom=95,end=125):
    tcPr=cell._tc.get_or_add_tcPr(); mar=tcPr.first_child_found_in('w:tcMar')
    if mar is None: mar=OxmlElement('w:tcMar'); tcPr.append(mar)
    for edge,val in [('top',top),('start',start),('bottom',bottom),('end',end)]:
        el=OxmlElement('w:'+edge);el.set(qn('w:w'),str(val));el.set(qn('w:type'),'dxa');mar.append(el)
def cell_text(cell,text,bold=False,white=False):
    cell.text='';p=cell.paragraphs[0];p.paragraph_format.space_before=Pt(0);p.paragraph_format.space_after=Pt(0)
    run=p.add_run(text);run.bold=bold;run.font.name='Aptos';run.font.size=Pt(9.5);run.font.color.rgb=RGBColor(255,255,255) if white else RGBColor(24,43,54)
    cell.vertical_alignment=WD_CELL_VERTICAL_ALIGNMENT.CENTER
def table(headers,rows,widths):
    t=doc.add_table(rows=1, cols=len(headers));t.autofit=False
    for c,w in zip(t.columns,widths):c.width=Inches(w)
    for j,h in enumerate(headers):
        c=t.rows[0].cells[j];c.width=Inches(widths[j]);shade(c,'17394B');margin(c,105,125,105,125);border(c);cell_text(c,h,True,True)
    for i,row in enumerate(rows):
        cells=t.add_row().cells
        for j,value in enumerate(row):
            c=cells[j];c.width=Inches(widths[j]);shade(c,'F1F6F7' if i%2 else 'FFFFFF');margin(c);border(c);cell_text(c,value,j==1 if len(headers)==3 else j==0)
    doc.add_paragraph().paragraph_format.space_after=Pt(0)
    return t

doc=Document();sec=doc.sections[0];sec.page_width=Inches(8.5);sec.page_height=Inches(11)
sec.top_margin=Inches(.67);sec.bottom_margin=Inches(.65);sec.left_margin=Inches(.7);sec.right_margin=Inches(.7)
styles=doc.styles
styles['Normal'].font.name='Aptos';styles['Normal'].font.size=Pt(10);styles['Normal'].font.color.rgb=RGBColor(24,43,54)
styles['Normal'].paragraph_format.space_after=Pt(5)
for style,size in [('Title',20),('Heading 1',13)]:
    s=styles[style];s.font.name='Aptos Display' if style=='Title' else 'Aptos';s.font.size=Pt(size);s.font.bold=True;s.font.color.rgb=RGBColor(0,0,0)
    s.paragraph_format.space_before=Pt(8 if style=='Heading 1' else 0);s.paragraph_format.space_after=Pt(7)
    if style=='Title':
        ppr=s._element.get_or_add_pPr()
        for rule in ppr.findall(qn('w:pBdr')): ppr.remove(rule)

doc.add_paragraph('Island Survival Character Skills and Items','Title')
p=doc.add_paragraph('Approved English names for the four playable characters and four items in instruction.docx. Each name is paired with its control and a short effect summary so icon design can follow the intended mechanic.')
p.paragraph_format.space_after=Pt(12)
for name,rows in characters.items():
    heading=doc.add_paragraph(name,'Heading 1')
    if name=='Eira Frostveil': heading.paragraph_format.page_break_before=True
    table(('Control','Approved name','Effect'),rows,(1.05,2.0,4.05))
doc.add_paragraph('Items','Heading 1')
table(('Approved name','Effect'),items,(2.2,4.9))

footer=sec.footer.paragraphs[0];footer.alignment=WD_ALIGN_PARAGRAPH.CENTER
r=footer.add_run('Island Survival  •  Approved name register');r.font.size=Pt(8);r.font.color.rgb=RGBColor(102,117,124)
doc.save(OUT)
print(OUT)
