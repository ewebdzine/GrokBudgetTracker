#!/usr/bin/env python3
"""Blank, printable monthly templates (fill in by pencil):
  monthly-budget-plan-blank.pdf  and  where-the-money-went-blank.pdf
Bill names, budget amounts and groups come from config (blank_template section).
Usage: python3 build_blank.py [--config config.json] [--out DIR]"""
import json,os,sys
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,Table,TableStyle,KeepTogether
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
HERE=os.path.dirname(os.path.abspath(__file__)); a=sys.argv[1:]
opt=lambda k,d: a[a.index(k)+1] if k in a else d
CFG=json.load(open(opt('--config',f'{HERE}/config.json' if os.path.exists(f'{HERE}/config.json') else f'{HERE}/config.example.json')))
T=CFG['blank_template']; OUT=opt('--out','./output'); os.makedirs(OUT,exist_ok=True)
FONT='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
if os.path.exists(FONT): pdfmetrics.registerFont(TTFont('DJ',FONT)); BOX='<font name="DJ" size="11">\u2610</font>'
else: BOX='[ ]'
m=lambda x:f"${x:,.2f}" if x!=int(x) else f"${x:,.0f}"
H=ParagraphStyle('h',fontName='Helvetica-Bold',fontSize=20,leading=24); Sub=ParagraphStyle('s',fontName='Helvetica',fontSize=10,leading=13,textColor=colors.HexColor('#333333'))
F=ParagraphStyle('f',fontName='Helvetica',fontSize=10.5,leading=20); H2=ParagraphStyle('h2',fontName='Helvetica-Bold',fontSize=12,leading=15,spaceBefore=8,spaceAfter=3)
C=ParagraphStyle('c',alignment=1,fontSize=10,leading=12); grid=colors.HexColor('#BBBBBB'); hdr=colors.HexColor('#F2F2F2'); sub=colors.HexColor('#F7F7F7')
box=lambda: Paragraph(BOX,C)
def tbl(rows,w,right=(),center=(),groups=(),total=True):
    t=Table(rows,colWidths=[x*inch for x in w],rowHeights=[16]+[17]*(len(rows)-1),repeatRows=1)
    st=[('FONT',(0,0),(-1,-1),'Helvetica',10),('FONT',(0,0),(-1,0),'Helvetica-Bold',10),('GRID',(0,0),(-1,-1),.4,grid),('BACKGROUND',(0,0),(-1,0),hdr),('VALIGN',(0,0),(-1,-1),'MIDDLE')]
    st+=[('ALIGN',(c,0),(c,-1),'RIGHT') for c in right]+[('ALIGN',(c,0),(c,-1),'CENTER') for c in center]
    for r in groups: st+=[('SPAN',(0,r),(-1,r)),('FONT',(0,r),(-1,r),'Helvetica-Bold',9.5),('BACKGROUND',(0,r),(-1,r),sub)]
    if total: st+=[('FONT',(0,-1),(-1,-1),'Helvetica-Bold',10),('BACKGROUND',(0,-1),(-1,-1),hdr)]
    t.setStyle(TableStyle(st)); return t
def fixed(cols):
    rows=[cols]; g=[]; tot=0
    for name,items in T['fixed_bills']:
        g.append(len(rows)); rows.append([name]+['']*(len(cols)-1))
        for n,d,amt in items: rows.append([n,d,m(amt),'$']+[box() for _ in cols[4:]]); tot+=amt
    rows.append(['Total fixed bills','',m(tot),'$']+['']*(len(cols)-4)); return rows,g
def foot(title):
    def f(cv,d): cv.setFont('Helvetica',8); cv.drawString(.7*inch,.45*inch,f'{title} (blank). Month: ____________'); cv.drawRightString(letter[0]-.7*inch,.45*inch,f'Page {d.page}')
    return f
hdrs=[Paragraph(CFG['owner_label']+'. '+CFG['account_note'],Sub),Spacer(1,6),Paragraph('Month: ____________________ &nbsp;&nbsp; Date planned / filled in: ____/____/____',F)]
# Plan
s=[Paragraph('Monthly Budget Plan',H)]+hdrs+[Paragraph('Income plan',H2)]
inc=[['Income','Expected','Date','Received']]+[[n,m(v),d,box()] for n,v,d in T['income']]+[['Other: ________________','$','',box()],['Total income',m(sum(v for _,v,_ in T['income'])),'','']]
s.append(tbl(inc,[3.6,1.6,.6,1.2],right=(1,),center=(2,3)))
r,g=fixed(['Bill','Due','Planned','Actual','Verified','Paid']); s+=[Paragraph('Fixed bills',H2),tbl(r,[3.1,.6,1,1,.65,.65],right=(2,3),center=(1,4,5),groups=g)]
s+=[KeepTogether([Paragraph('One-off bills',H2),tbl([['Bill','Due','Amount','Paid']]+[['','','',box()] for _ in range(6)]+[['Total one-offs','','$','']],[4.3,.7,1.1,.9],right=(2,),center=(1,3))])]
b=T['budgets']; s+=[KeepTogether([Paragraph('Spending budget ('+CFG['spending_account_label']+')',H2),tbl([['Category','Budget','Spent']]+[[n,m(v),'$'] for n,v in b]+[['Total moved to spending account',m(sum(v for _,v in b)),'$']],[3.6,1.6,1.8],right=(1,2))])]
s+=[KeepTogether([Paragraph('Debt snowball',H2),tbl([['#','Debt','APR','Min','Balance','Paid this month']]+[[str(i),'','%','$','$','$'] for i in range(1,6)]+[['','Total','+ $____/mo extra','','$','$']],[.3,2.3,1.3,.8,1.1,1.2],right=(3,4,5),center=(0,2))])]
SimpleDocTemplate(f'{OUT}/monthly-budget-plan-blank.pdf',pagesize=letter,leftMargin=.7*inch,rightMargin=.7*inch,topMargin=.55*inch,bottomMargin=.65*inch).build(s,onFirstPage=foot('Monthly Budget Plan'),onLaterPages=foot('Monthly Budget Plan'))
# Where the money went
s=[Paragraph('Where the Money Went &mdash; Monthly Report',H)]+hdrs+[Paragraph(f'Sources reviewed: {BOX} {CFG["bills_account_label"]} &nbsp; {BOX} {CFG["spending_account_label"]} &nbsp; {BOX} Credit cards',F),Paragraph('Summary',H2)]
s.append(tbl([['Item','Amount'],['Total spending, all accounts (after exclusions)','$'],['   Bills account','$'],['   Spending account','$'],['   Credit cards (goal: no new spending)','$'],['Overdraft fees this month (goal $0)','#        $'],['Excluded: transfers between own accounts','$'],['Excluded: credit card payments from checking','$']],[4.6,2.5],right=(1,),total=False))
r,g=fixed(['Bill','Due','Budget','Actual','Paid']); s+=[Paragraph('1. Fixed bills',H2),tbl(r,[3.9,.6,1,1,.6],right=(2,3),center=(1,4),groups=g)]
rows=[['Date','Company','Amount','Add to tracker?']]; g=[]
for n,k in T['one_off_groups']: g.append(len(rows)); rows.append([n,'','','']); rows+=[['','','',box()] for _ in range(k)]
rows.append(['Total one-off bills','','$','']); s+=[Paragraph('2. One-off bills',H2),tbl(rows,[.9,3.7,1.2,1.3],right=(2,),center=(3,),groups=g)]
s+=[KeepTogether([Paragraph('3. Budget buckets',H2),tbl([['Bucket','Budget','Actual','Over / Under']]+[[n,m(v),'$','$'] for n,v in b]+[['Total',m(sum(v for _,v in b)),'$','$']],[3.1,1.3,1.3,1.3],right=(1,2,3))])]
s+=[KeepTogether([Paragraph('Top merchants',H2),tbl([['#','Merchant','Category','# charges','Total']]+[[str(i),'','','',''] for i in range(1,11)],[.35,3,1.6,.85,1.2],right=(3,4),center=(0,),total=False)])]
s+=[KeepTogether([Paragraph('Takeaways / cut next month',H2),tbl([['#','Note']]+[[f'{i}.',''] for i in range(1,6)],[.3,6.7],total=False)])]
SimpleDocTemplate(f'{OUT}/where-the-money-went-blank.pdf',pagesize=letter,leftMargin=.7*inch,rightMargin=.7*inch,topMargin=.55*inch,bottomMargin=.65*inch).build(s,onFirstPage=foot('Where the Money Went'),onLaterPages=foot('Where the Money Went'))
print(OUT)
