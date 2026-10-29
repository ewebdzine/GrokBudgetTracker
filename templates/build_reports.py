#!/usr/bin/env python3
"""GrokBudgetTracker report generator: renders a static HTML dashboard + two PDFs
(Monthly Budget Plan, Where the Money Went) from a dashboard_snapshot JSON.
Snapshot = output of  select public.dashboard_snapshot('YYYY-MM-01')  run through the Supabase connector.
No database keys are used or embedded.
Usage: python3 build_reports.py SNAPSHOT.json [--config config.json] [--out DIR]
Try it: python3 build_reports.py sample/snapshot-2026-01.json --out sample/output"""
import json,sys,os,html,datetime as dt
from collections import defaultdict
HERE=os.path.dirname(os.path.abspath(__file__))
args=sys.argv[1:]
def opt(k,d): return args[args.index(k)+1] if k in args else d
CFGP=opt('--config', f'{HERE}/config.json' if os.path.exists(f'{HERE}/config.json') else f'{HERE}/config.example.json')
SNAP=next((a for a in args if a.endswith('.json') and a!=CFGP), f'{HERE}/sample/snapshot-2026-01.json')
CFG=json.load(open(CFGP)); OUT=opt('--out','./output')
S=json.load(open(SNAP)); os.makedirs(OUT,exist_ok=True)
MON=S['month'][:7]
# normalize transactions to tuples: (date, amount, matched, pending, category, description)
S['transactions']=[(t['date'],t['amount'],t.get('matched'),t.get('pending'),t.get('category'),t.get('description') or '') for t in S['transactions']]
D=lambda s: dt.date.fromisoformat(s[:10]) if s else None
def m(x,c=False):
    if x is None: return '—'
    s=f"${abs(x):,.2f}" if (c or round(x)!=x) else f"${abs(x):,.0f}"
    return ('-' if x<0 else '')+s
y,mo=map(int,MON.split('-')); first=dt.date(y,mo,1); MNAME=first.strftime('%B %Y')
TODAY=D(S.get('pulled_at','')[:10]) or dt.date.today()

# ---------- numbers ----------
sm=S['summary']; bills=S['bills']; oo=S['one_offs']; bud=S['budgets']; debts=S['debts']
inc_exp=sum(r['expected'] for r in S['monthly_income'] if r.get('source_id')) if S.get('monthly_income') else sum(i['expected_amount'] for i in S['income_sources'])  # optional: add monthly_income rows for the month to the snapshot
inc_bank=sum(e['amount'] for e in S['income_events'] if e['kind']=='income')
other_in=sum(e['amount'] for e in S['income_events'] if e['kind'] in('one_off_income','transfer_in'))
refunds=sum(e['amount'] for e in S['income_events'] if e['kind']=='refund')
fixed_left=[b for b in bills if b['status']=='unpaid']; oo_left=[o for o in oo if o['status']=='unpaid']
fixed_left_amt=sum(b['amount'] for b in fixed_left); oo_left_amt=sum(o['amount'] for o in oo_left)
bills_left=fixed_left_amt+oo_left_amt
planned_fixed=sum(b['amount'] for b in bills); planned_oo=sum(o['amount'] for o in oo)
spend_plan=sum(b['planned'] for b in bud); spend_spent=sum(b['spent'] for b in bud)
xfer=next((t for t in S['transfers'] if t['to_account']==CFG['spending_account_id']),None)
planned_exp=planned_fixed+planned_oo+spend_plan
able_to_save=inc_bank+other_in-planned_exp
bal=S['balances'][CFG['bills_account_id']]['available']
pending=sum(t[1] for t in S['transactions'] if t[3])
pend_out=sum(t[1] for t in S['transactions'] if t[3] and t[1]<0)
left_after=bal+pending-bills_left; left_after_fixed_only=bal+pending-fixed_left_amt

# ---------- snowball ----------
def simulate(method='snowball',extra=None):
    extra=S['snowball']['extra_per_month'] if extra is None else extra
    ds=[dict(name=d['name'],apr=d['apr'],min=d['min'],bal=d['start']-d['paid'],order=d['order'],clear=None) for d in debts]
    budget=sum(d['min'] for d in ds)+extra; months=0; interest=0; series=[sum(d['bal'] for d in ds)]
    key=(lambda d:d['order']) if method=='snowball' else (lambda d:(-d['apr'],d['order']))
    while any(d['bal']>0.005 for d in ds) and months<600:
        for d in ds:
            if d['bal']>0: i=d['bal']*d['apr']/100/12; d['bal']+=i; interest+=i
        pay=budget
        for d in ds:
            if d['bal']>0: p=min(d['min'],d['bal']); d['bal']-=p; pay-=p
        for d in sorted([d for d in ds if d['bal']>0.005],key=key):
            p=min(pay,d['bal']); d['bal']-=p; pay-=p
            if pay<=0: break
        months+=1
        for d in ds:
            if d['bal']<=0.005 and d['clear'] is None: d['clear']=months
        series.append(max(0,sum(d['bal'] for d in ds)))
    return dict(months=months,interest=interest,debts=ds,series=series,total_pay=budget)
def addm(n): k=first.month-1+n; return dt.date(first.year+k//12,k%12+1,1)
SB=simulate('snowball'); AV=simulate('avalanche')
# debt-free date = start month + N months
debt_free=addm(SB['months']); owed=sum(d['start']-d['paid'] for d in debts)

# ---------- HTML ----------
E=html.escape
def chip(txt,kind): return f'<span class="chip {kind}">{E(txt)}</span>'
def week_of(d): return min((d.day-1)//7+1,4) if d else 1  # 1-7, 8-14, 15-21, 22-end (29-31 fold into week 4)
WK={1:'1st–7th',2:'8th–14th',3:'15th–21st',4:'22nd–end'}
rows=defaultdict(list)
def _wk(b):
    d=D(b['due_date'])
    return week_of(d) if d and (d.year,d.month)==(first.year,first.month) else 1
for b in bills: rows[_wk(b)].append(('fixed',b))
for o in oo: rows[_wk(o)].append(('oneoff',o))
if xfer: rows[1].append(('xfer',xfer))
def billrow(k,b):
    if k=='xfer':
        return f'''<div class="row paid"><div class="ck on">✓</div><div class="nm">Move the budget to the spending account<div class="sub"><span class="tag">TRANSFER</span> planned {m(b['planned_amount'])}, moved {m(b['amount'])}</div></div>{chip('Done','ok')}<div class="amt">{m(b['amount'])}</div></div>'''
    name=b.get('name') or b.get('payee'); paid=b['status']!='unpaid'; d=D(b['due_date'])
    sub=(b.get('category') or '') + (' · carried over' if b.get('carried_over_from') else '')
    if b.get('unverified'): sub+=' · unverified'
    if paid: st=chip('Cleared' if b['status']=='cleared' else 'Paid','ok')
    elif d and d<TODAY: st=chip(f'Past due {d.strftime("%-m/%-d")}','bad')
    else: st=chip(f'Due {d.strftime("%-m/%-d")}','warn')
    amt=b.get('paid_amount') if paid and b.get('paid_amount') else b['amount']
    cls='paid' if paid else ('late' if d and d<TODAY else 'due')
    return f'<div class="row {cls}"><div class="ck {"on" if paid else ""}">{"✓" if paid else ""}</div><div class="dt">{d.strftime("%a %-m/%-d") if d else "—"}</div><div class="nm">{E(name)} <span class="tag{"" if k=="fixed" else " oo"}">{"FIXED" if k=="fixed" else "ONE-OFF"}</span><div class="sub">{E(sub.strip(" ·"))}</div></div>{st}<div class="amt">{m(amt,True)}</div></div>'
weeks_html=''
for w in sorted(rows):
    its=sorted(rows[w],key=lambda r:(r[0]=='xfer',(r[1].get('due_date') or '')))
    unpaid=sum(r[1]['amount'] for r in its if r[0]!='xfer' and r[1]['status']=='unpaid')
    tot=sum((r[1].get('paid_amount') or r[1]['amount']) for r in its)
    this=' <span class="tag dark">THIS WEEK</span>' if week_of(TODAY)==w else ''
    weeks_html+=f'<div class="wk"><b>WEEK {w}</b> <span class="mut">{WK[w]}</span>{this}<span class="r"><span class="gold">{m(unpaid,True)} unpaid</span> <span class="mut mono">{len([r for r in its if r[0]=="xfer" or r[1]["status"]!="unpaid"])} of {len(its)} done</span></span></div>'+''.join(billrow(*r) for r in its)
inc_rows=''
for i in S['income_sources']:
    ev=next((e for e in S['income_events'] if e.get('source_id')==i['id']),None)
    inc_rows+=f'<div class="row {"paid" if ev else "due"}"><div class="ck {"on" if ev else ""}">{"✓" if ev else ""}</div><div class="nm">{E(i["name"])}<div class="sub">deposit{" · "+E(ev["notes"]) if ev else ""}</div></div>{chip("Received "+D(ev["received_date"]).strftime("%-m/%-d"),"ok") if ev else chip("Not in yet · 1st","warn")}<div class="amt">{m(i["expected_amount"])}</div></div>'
for e in S['income_events']:
    if e['kind']!='income':
        lab={'one_off_income':'One-off income','transfer_in':'Transfer in','refund':'Refund (not income)'}[e['kind']]
        inc_rows+=f'<div class="row extra"><div class="ck on">+</div><div class="nm">{E(e["notes"])}<div class="sub">{lab}</div></div>{chip(D(e["received_date"]).strftime("%-m/%-d"),"ok" if e["kind"]!="refund" else "warn")}<div class="amt">{m(e["amount"],True)}</div></div>'
bud_rows=''.join(f'<div class="brow"><div class="bn">{E(b["name"])}</div><div class="bar"><i style="width:{min(100,100*b["spent"]/b["planned"]):.0f}%"></i></div><div class="mono">{m(b["spent"])} of {m(b["planned"])}</div></div>' for b in bud)
tx_rows=''.join(f'<tr class="{"pend" if t[3] else ""}"><td class="mono">{D(t[0]).strftime("%-m/%-d")}</td><td>{E(t[5])}{" <span class=tag>PENDING</span>" if t[3] else ""}</td><td class="mut">{E(t[2] and "✓ "+t[2] or (t[4] or ""))}</td><td class="mono {"pos" if t[1]>0 else ""}">{m(t[1],True)}</td></tr>' for t in S['transactions'])
# SVG chart
ser=SB['series']; W,H=520,120; mx=max(ser)
pts=' '.join(f'{W*i/(len(ser)-1):.1f},{H-(H*v/mx):.1f}' for i,v in enumerate(ser))
svg=f'<svg viewBox="0 -4 {W} {H+8}" preserveAspectRatio="none" class="chart"><defs><linearGradient id="g" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#1f6f5c" stop-opacity=".35"/><stop offset="1" stop-color="#1f6f5c" stop-opacity=".03"/></linearGradient></defs>'+''.join(f'<line x1="0" x2="{W}" y1="{H*k/4}" y2="{H*k/4}" stroke="#d9dedb" stroke-width=".6"/>' for k in range(5))+f'<polygon points="0,{H} {pts} {W},{H}" fill="url(#g)"/><polyline points="{pts}" fill="none" stroke="#1f6f5c" stroke-width="1.6"/><circle cx="{W}" cy="{H}" r="3" fill="#1f6f5c"/></svg>'
def drow(d,i):
    sd=next(x for x in SB['debts'] if x['name']==d['name']); cl=addm(sd['clear']).strftime('%b %Y') if sd['clear'] else '—'
    tgt='<b class="tgt">SNOWBALL TARGET</b> ' if i==0 else ''
    return f'<div class="debt {"first" if i==0 else ""}"><div class="dh"><span class="n">{d["order"]}</span><div><b>{E(d["name"])}</b><div class="mono mut">{d["apr"]:.2f}% APR · {m(d["min"])}/mo minimum</div></div><div class="r"><div class="big mono">{m(d["start"]-d["paid"])}</div><div class="mono mut">of {m(d["start"])}</div></div></div><div class="bar"><i style="width:{100*d["paid"]/d["start"]:.0f}%"></i></div><div class="mut sm">{tgt}Projected clear {cl} · {100*d["paid"]/d["start"]:.0f}% retired</div></div>'
debt_html=''.join(drow(d,i) for i,d in enumerate(debts))
CSS='''body{margin:0;background:#f6f6f3;font:14px/1.45 -apple-system,"Segoe UI",Inter,Helvetica,Arial,sans-serif;color:#1d211f}
.w{max-width:860px;margin:0 auto;padding:36px 20px 60px}h1{font:700 34px/1.1 Georgia,"Times New Roman",serif;letter-spacing:-.5px;margin:0 0 8px}
.lede{color:#5d6561;max-width:470px}.top{display:flex;justify-content:space-between;align-items:flex-end;margin-bottom:22px}.pill{border:1px solid #d6d9d6;background:#fff;border-radius:8px;padding:7px 18px;font-weight:600}
.mono{font-family:"SF Mono",Menlo,Consolas,monospace;font-size:12px}.mut{color:#7a827e}.sm{font-size:12px}.r{margin-left:auto;text-align:right}
.cards{display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin-bottom:12px}.card{background:#fff;border:1px solid #e1e3e0;border-radius:10px;padding:13px 15px;box-shadow:0 1px 2px #0000000a}
.card .l{font:600 10px/1 Menlo,monospace;letter-spacing:1.2px;color:#8a918d;text-transform:uppercase}.card .v{font:700 24px/1.3 Menlo,Consolas,monospace;margin:6px 0 2px}.card .s{font-size:12px;color:#6b736f}
.card.good{background:linear-gradient(135deg,#eaf5f1,#fff);border-color:#b9dccf}.card.good .v{color:#1f6f5c}
.tabs{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin-bottom:18px}.tab{background:#eef0ed;border:1px solid #dfe2de;border-radius:7px;padding:8px 12px;display:flex;font-weight:600;font-size:13px}.tab span{margin-left:auto;font:12px Menlo,monospace;color:#7a827e}.tab .red{color:#b3402f}
.sec{background:#fff;border:1px solid #e1e3e0;border-radius:12px;margin-bottom:16px;overflow:hidden}.sh{padding:16px 18px;background:#f8f9f7;border-bottom:1px solid #eceeeb;display:flex;align-items:center}.sh h2{margin:0;font-size:17px}.sh .mut{font-size:12.5px}
.row{display:flex;align-items:center;gap:12px;padding:10px 18px;border-top:1px solid #f0f1ef;border-left:3px solid transparent}.row.paid{border-left-color:#1f6f5c}.row.late{border-left-color:#b3402f}.row.due{border-left-color:#b98a2e}.row.extra{border-left-color:#8fb8aa;background:#fbfcfb}
.row.paid .nm{color:#7a827e}.ck{width:17px;height:17px;border:1.5px solid #c5cac6;border-radius:4px;display:grid;place-items:center;font-size:11px;color:#fff;flex:none}.ck.on{background:#1f6f5c;border-color:#1f6f5c}
.nm{flex:1;font-weight:600}.sub{font-weight:400;font-size:11.5px;color:#8a918d}.amt{width:110px;text-align:right;font:700 13.5px Menlo,monospace}
.chip{font-size:11px;padding:2px 9px;border-radius:10px;white-space:nowrap}.chip.ok{background:#dcefe8;color:#1f6f5c}.chip.bad{background:#fbe2dd;color:#a3341f}.chip.warn{background:#fbf0d8;color:#8a6516}
.tag{font:600 9.5px Menlo,monospace;letter-spacing:.8px;background:#e3ece8;color:#1f6f5c;border-radius:4px;padding:1px 5px}.tag.oo{background:#efe6f6;color:#6b3fa0}.dt{font-weight:400;color:#555;min-width:64px;font-variant-numeric:tabular-nums}.tag.dark{background:#1f6f5c;color:#fff}
.wk{padding:9px 18px;background:#f3f5f3;border-top:1px solid #e6e8e5;font-size:11px;letter-spacing:1px;display:flex;gap:8px;align-items:center}.gold{color:#9a6b12;font:600 12px Menlo,monospace}
.brow{display:flex;align-items:center;gap:14px;padding:10px 18px;border-top:1px solid #f0f1ef}.bn{width:130px;font-weight:600}.bar{flex:1;height:6px;background:#e3e7e4;border-radius:4px;overflow:hidden}.bar i{display:block;height:100%;background:#1f6f5c}
table{width:100%;border-collapse:collapse;font-size:12.5px}td{padding:6px 18px;border-top:1px solid #f0f1ef}td:last-child{text-align:right;white-space:nowrap}tr.pend td{background:#fffaf0}.pos{color:#1f6f5c}
.sbg{display:grid;grid-template-columns:1fr 2fr;gap:12px;padding:16px 18px}.box{background:#eef1ee;border-radius:10px;padding:14px 16px}.huge{font:700 44px/1 Georgia,serif;color:#1f6f5c;margin:8px 0}.chart{width:100%;height:130px}
.debt{margin:0 18px 10px;border:1px solid #e1e3e0;border-radius:10px;padding:12px 14px}.debt.first{border-color:#7fb9a6;background:#f4faf7}.dh{display:flex;gap:10px;align-items:center}.n{width:22px;height:22px;border-radius:5px;background:#e8ebe8;display:grid;place-items:center;font-weight:700;font-size:12px}.first .n{background:#1f6f5c;color:#fff}
.debt .bar{margin:9px 0 6px}.big{font-size:17px;font-weight:700}.tgt{color:#1f6f5c;font:700 10px Menlo,monospace;letter-spacing:1px}.seg{display:flex;border:1px solid #cfd4d0;border-radius:6px;overflow:hidden;font-size:12px}.seg b{padding:4px 10px;background:#1f6f5c;color:#fff}.seg span{padding:4px 10px}
.note{font-size:12px;color:#6b736f;padding:10px 18px;border-top:1px solid #f0f1ef}footer{font-size:11.5px;color:#8a918d;text-align:center;margin-top:20px}'''
H=f'''<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Budget &amp; Snowball · {MNAME}</title><style>{CSS}</style></head><body><div class="w">
<div class="top"><div><h1>Budget &amp; Snowball</h1><div class="lede">What you planned to pay and spend this month, what is left, and how fast the debt disappears.</div></div><div style="display:flex;gap:8px;align-items:center"><div class="pill">{MNAME}</div><span class="mut sm">● Snapshot {TODAY.strftime("%-m/%-d")}</span></div></div>
<div class="cards">
<div class="card"><div class="l">Income expected</div><div class="v">{m(inc_exp)}</div><div class="s">{m(inc_bank)} banked · {m(inc_exp-inc_bank)} to go</div></div>
<div class="card"><div class="l">Planned expenses</div><div class="v">{m(planned_exp)}</div><div class="s">{len(bills)} fixed · {len(bud)} budgets · {len(oo)} one-off</div></div>
<div class="card good"><div class="l">Able to save</div><div class="v">{m(able_to_save)}</div><div class="s">all income in minus planned expenses</div></div>
<div class="card"><div class="l">Bills left to pay</div><div class="v">{m(bills_left,True)}</div><div class="s">{len(fixed_left)} fixed + {len(oo_left)} one-off still due</div></div>
<div class="card"><div class="l">Left in bills account after bills</div><div class="v">{m(left_after,True)}</div><div class="s">{m(bal,True)} now + pending {m(pending,True)} − bills left</div></div>
<div class="card"><div class="l">Debt-free</div><div class="v">{debt_free.strftime("%b %Y")}</div><div class="s">{m(owed)} to go · {SB["months"]} months</div></div></div>
<div class="tabs"><div class="tab">Income <span>{m(inc_bank)} of {m(inc_exp)}</span></div><div class="tab">Bills <span class="red">{m(bills_left,True)} left · {len(fixed_left)+len(oo_left)} due</span></div><div class="tab">Spending <span>{m(spend_spent)} of {m(spend_plan)}</span></div></div>
<div class="sec"><div class="sh"><div><h2>Income</h2><div class="mut">{m(inc_bank)} of {m(inc_exp)} collected · plus {m(other_in,True)} other in, {m(refunds,True)} refund pending</div></div></div>{inc_rows}</div>
<div class="sec"><div class="sh"><div><h2>Bills</h2><div class="mut">{m(bills_left,True)} left across {len(fixed_left)+len(oo_left)} bills · <span style="color:#b3402f">{len([o for o in oo_left if o.get("carried_over_from")])} carried over</span></div></div><div class="r seg"><span>Calendar</span><b>By week</b><span>By date</span></div></div>{weeks_html}
<div class="note">Paid amounts are shown where they differ from plan. Items marked unverified have not been confirmed against a bill or bank charge.</div></div>
<div class="sec"><div class="sh"><div><h2>Spending</h2><div class="mut">{E(CFG["spending_account_label"])} · {m(spend_plan)} planned, {m(xfer["amount"]) if xfer else "$0"} moved</div></div></div>{bud_rows}</div>
<div class="sec"><div class="sh"><div><h2>Transactions</h2><div class="mut">{E(CFG["bills_account_label"])} · {len(S["transactions"])} this month · ✓ = matched to a bill</div></div></div><table>{tx_rows}</table></div>
<div class="sec"><div class="sh"><div><h2>Debt snowball</h2><div class="mut">{m(owed)} outstanding across {len(debts)} accounts</div></div><div class="r" style="display:flex;gap:8px;align-items:center"><div class="seg"><b>Snowball</b><span>Avalanche</span></div><span class="mut sm">Extra / mo <b class="mono">{S["snowball"]["extra_per_month"]}</b></span></div></div>
<div class="sbg"><div class="box"><div class="card l" style="all:unset;font:600 10px Menlo;letter-spacing:1.2px;color:#8a918d">MONTHS TO DEBT-FREE</div><div class="huge">{SB["months"]}</div><b class="mono">{debt_free.strftime("%b %Y")}</b><div class="mut sm" style="margin-top:8px">{m(SB["interest"],True)} of interest along the way · {m(SB["total_pay"])} a month total. Avalanche: {AV["months"]} months, {m(AV["interest"],True)} interest.</div></div>
<div class="box"><div style="font:600 10px Menlo;letter-spacing:1.2px;color:#8a918d">TOTAL BALANCE, PROJECTED</div>{svg}<div class="mut sm" style="display:flex"><span>{first.strftime("%b %Y")}</span><span class="r">{debt_free.strftime("%b %Y")}</span></div></div></div>{debt_html}</div>
<footer>Static snapshot from Supabase · generated {dt.datetime.now().strftime("%-m/%-d/%Y %-I:%M %p")} {CFG["timezone_label"]} · no live database access from this page</footer></div></body></html>'''
open(f'{OUT}/{MON}.html','w').write(H)

# ---------- PDFs (reportlab, same style as template/build_plan.py) ----------
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,Table,TableStyle,KeepTogether
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
pdfmetrics.registerFont(TTFont('DJ','/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'))
Hs=ParagraphStyle('h',fontName='Helvetica-Bold',fontSize=20,leading=24,spaceAfter=2); Sub=ParagraphStyle('s',fontName='Helvetica',fontSize=10,leading=13,textColor=colors.HexColor('#333333'))
H2=ParagraphStyle('h2',fontName='Helvetica-Bold',fontSize=12,leading=15,spaceBefore=9,spaceAfter=3); N=ParagraphStyle('n',fontName='Helvetica',fontSize=8.5,leading=10.5,textColor=colors.HexColor('#444444'),spaceBefore=2)
grid=colors.HexColor('#BBBBBB'); hdr=colors.HexColor('#F2F2F2'); sub_bg=colors.HexColor('#F7F7F7')
CHK=lambda on: Paragraph(f'<font name="DJ" size="11">{"☑" if on else "☐"}</font>',ParagraphStyle('c',alignment=1,fontSize=10,leading=12))
def o_(d): return {1:'1st',2:'2nd',3:'3rd',21:'21st',22:'22nd',23:'23rd'}.get(d,f'{d}th')
def table(head,body,widths,right=(),center=(),groups=(),total=True):
    rows=[head]+body; t=Table(rows,colWidths=[w*inch for w in widths],repeatRows=1)
    st=[('FONT',(0,0),(-1,-1),'Helvetica',9.5),('FONT',(0,0),(-1,0),'Helvetica-Bold',9.5),('GRID',(0,0),(-1,-1),0.4,grid),('BACKGROUND',(0,0),(-1,0),hdr),('VALIGN',(0,0),(-1,-1),'MIDDLE'),('TOPPADDING',(0,0),(-1,-1),1.5),('BOTTOMPADDING',(0,0),(-1,-1),2)]
    for c in right: st.append(('ALIGN',(c,0),(c,-1),'RIGHT'))
    for c in center: st.append(('ALIGN',(c,0),(c,-1),'CENTER'))
    for r in groups: st+=[('SPAN',(0,r),(-1,r)),('FONT',(0,r),(-1,r),'Helvetica-Bold',9.5),('BACKGROUND',(0,r),(-1,r),sub_bg)]
    if total: st+=[('FONT',(0,-1),(-1,-1),'Helvetica-Bold',9.5),('BACKGROUND',(0,-1),(-1,-1),hdr)]
    t.setStyle(TableStyle(st)); return t
GROUP=CFG['bill_groups']
ORDER=CFG['bill_group_order']
def grouped_bills(cols):
    g=defaultdict(list)
    for b in bills: g[GROUP.get(b['category'],'Other')].append(b)
    body=[];grp=[]
    for k in ORDER+[k for k in g if k not in ORDER]:
        if k not in g: continue
        grp.append(len(body)+1); body.append([k]+['']*(len(cols(None))-1))
        for b in sorted(g[k],key=lambda b:b['due_date']): body.append(cols(b))
    return body,grp
def foot_for(title):
    def f(cv,d): cv.saveState(); cv.setFont('Helvetica',8); cv.setFillColor(colors.HexColor('#666666')); cv.drawString(0.75*inch,0.5*inch,f'{title} · {MNAME} · generated from Supabase'); cv.drawRightString(7.75*inch,0.5*inch,f'Page {d.page}'); cv.restoreState()
    return f
doc=lambda p: SimpleDocTemplate(p,pagesize=letter,leftMargin=0.75*inch,rightMargin=0.75*inch,topMargin=0.6*inch,bottomMargin=0.75*inch)
# 1) Monthly Budget Plan
st=[Paragraph('Monthly Budget Plan',Hs),Paragraph(E(CFG['owner_label']+'. '+CFG['account_note']),Sub),Spacer(1,4),
    Paragraph(f'<b>Month:</b> {MNAME} &nbsp;&nbsp; <b>Date planned:</b> {TODAY.strftime("%m/%d/%Y")} (from Supabase snapshot)',Sub),Paragraph('Income plan',H2)]
ib=[[i['name'],m(i['expected_amount']),'1st',CHK(any(e.get('source_id')==i['id'] for e in S['income_events']))] for i in S['income_sources']]
ib+=[[('Other: '+e['notes'])[:48],m(e['amount'],True),D(e['received_date']).strftime('%-m/%-d'),CHK(True)] for e in S['income_events'] if e['kind'] in('one_off_income','transfer_in')]
ib.append(['Total income',f'{m(inc_exp)} + other {m(other_in,True)}','',''])
st.append(table(['Income','Expected','Date','Received'],ib,[3.6,1.6,0.6,1.2],right=(1,),center=(2,3)))
ob=[[o['payee']+(' (carried over)' if o.get('carried_over_from') else '')+(' *' if o['unverified'] else ''),D(o['due_date']).strftime('%-m/%-d'),m(o['amount'],True),CHK(o['status']!='unpaid')] for o in oo]
ob.append(['Total one-offs','',m(planned_oo,True),f'{m(oo_left_amt,True)} left'])
# Bills timeline: one heading per week, every bill (fixed + one-off) in due-date order on a dotted rail
from reportlab.platypus import Flowable
def bill_week(b):
    d=D(b['due_date'])
    if d and (d.year,d.month)==(first.year,first.month): return week_of(d),d,False
    return 1,d,bool(b.get('carried_over_from'))  # carried over from an earlier month with no due date this month
class Rail(Flowable):
    def __init__(s,h,top,bot,color): Flowable.__init__(s); s.h=h; s.top=top; s.bot=bot; s.c=color
    def wrap(s,aw,ah): s.w=aw; return aw,s.h
    def draw(s):
        cv=s.canv; x=s.w/2; y=s.h/2; cv.setStrokeColor(colors.HexColor('#C9C9C9')); cv.setLineWidth(0.6)
        cv.line(x,0 if not s.bot else y,x,s.h if not s.top else y)
        cv.setFillColor(s.c); cv.setStrokeColor(colors.white); cv.circle(x,y,2.2,fill=1,stroke=0)
GREY=colors.HexColor('#777777'); HAIR=colors.HexColor('#D6D6D6')
OK='#1F6F5C'; WARN='#8A6516'; BAD='#A3341F'
def tl_status(b,d):
    if b['status']!='unpaid': return ('Cleared' if b['status']=='cleared' else 'Paid'),OK
    if d and d<TODAY: return 'Past due',BAD
    return 'Unpaid',WARN
wk=defaultdict(list)
for b in bills: w,d,c=bill_week(b); wk[w].append((d,b['name'],'Fixed',b,c))
for o in oo: w,d,c=bill_week(o); wk[w].append((d,o['payee'],'One-off',o,c or bool(o.get('carried_over_from'))))
NB=sum(len(v) for v in wk.values())
TWO=NB>44                       # two columns (weeks 1-2 | 3-4) only when one column can't fit a page
FS=8 if TWO or NB>30 else 8.5; RH=FS+4.5; HH=FS+7
def week_table(w,width):
    its=sorted(wk.get(w,[]),key=lambda r:(r[0] or first))
    tot=sum(r[3]['amount'] for r in its); un=sum(r[3]['amount'] for r in its if r[3]['status']=='unpaid')
    subtot=(f'{m(tot,True)}'+(f' · {m(un,True)} unpaid' if un else ' · all paid')) if its else 'no bills'
    head=f'<font name="Helvetica-Bold" size="{FS-1}" color="#777777">WEEK {w} · {WK[w]}</font>&nbsp;&nbsp;<font size="{FS-1}" color="#999999">{subtot}</font>'
    rows=[[Paragraph(head,ParagraphStyle('wh',fontName='Helvetica',fontSize=FS-1,leading=FS+1)),'','','','']]
    for k,(d,name,kind,b,carried) in enumerate(its):
        txt,col=tl_status(b,d)
        amt=b.get('paid_amount') if b['status']!='unpaid' and b.get('paid_amount') else b['amount']
        tag=f'<font name="Helvetica-Bold" size="{FS-2.5}" color="#888888">{"FIXED" if kind=="Fixed" else "ONE-OFF"}</font>'
        extra=(f' <font size="{FS-1.5}" color="#A3341F">carried over</font>' if carried else '')+(' *' if b.get('unverified') else '')
        rows.append([d.strftime('%a %-m/%-d') if d else '—',Rail(RH,k==0,k==len(its)-1,colors.HexColor(col)),
                     Paragraph(f'{E(name)}&nbsp;{tag}{extra}',ParagraphStyle('tl',fontName='Helvetica',fontSize=FS,leading=FS+1.5)),m(amt,True),txt])
    f=width/7.0
    t=Table(rows,colWidths=[w_*f*inch for w_ in ([0.75,0.2,4.25,0.95,0.85] if not TWO else [0.95,0.25,3.4,1.2,1.2])],rowHeights=[HH]+[RH]*len(its))
    sty=[('FONT',(0,1),(-1,-1),'Helvetica',FS),('FONT',(0,1),(0,-1),'Helvetica',FS),('TEXTCOLOR',(0,1),(0,-1),colors.HexColor('#555555')),('ALIGN',(0,1),(0,-1),'RIGHT'),('ALIGN',(3,1),(4,-1),'RIGHT'),
         ('VALIGN',(0,0),(-1,-1),'MIDDLE'),('TOPPADDING',(0,0),(-1,-1),0),('BOTTOMPADDING',(0,0),(-1,-1),0),('LEFTPADDING',(0,0),(-1,-1),3),('RIGHTPADDING',(0,0),(-1,-1),3),
         ('LEFTPADDING',(1,0),(1,-1),0),('RIGHTPADDING',(1,0),(1,-1),0),('SPAN',(0,0),(-1,0)),('LINEBELOW',(0,0),(-1,0),0.25,HAIR),('VALIGN',(0,0),(-1,0),'BOTTOM')]
    for r,(d,_,_,b,_) in enumerate(its,1): sty.append(('TEXTCOLOR',(4,r),(4,r),colors.HexColor(tl_status(b,d)[1])))
    t.setStyle(TableStyle(sty)); return t
blk=[Paragraph('Bills timeline',H2),Paragraph(f'All {NB} bills, fixed and one-off, by the date they come out. Week 4 runs from the 22nd to month end.',N),Spacer(1,2)]
if TWO:
    L=[week_table(1,3.45),Spacer(1,4),week_table(2,3.45)]; R=[week_table(3,3.45),Spacer(1,4),week_table(4,3.45)]
    two=Table([[L,R]],colWidths=[3.5*inch,3.5*inch]); two.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),0),('RIGHTPADDING',(0,0),(-1,-1),0)]))
    blk.append(two)
else:
    for w in range(1,5): blk+=[week_table(w,7.0),Spacer(1,3)]
tt=Table([['Total bills',f'{m(planned_fixed+planned_oo,True)} · {m(bills_left,True)} left to pay']],colWidths=[3.5*inch,3.5*inch])
tt.setStyle(TableStyle([('FONT',(0,0),(-1,-1),'Helvetica-Bold',FS+0.5),('ALIGN',(1,0),(1,0),'RIGHT'),('BACKGROUND',(0,0),(-1,-1),hdr),('TOPPADDING',(0,0),(-1,-1),2),('BOTTOMPADDING',(0,0),(-1,-1),2.5)]))
blk+=[Spacer(1,3),tt]
if any(r[3].get('unverified') for v in wk.values() for r in v): blk.append(Paragraph('* Not yet confirmed against a bill or bank charge.',N))
st.append(KeepTogether(blk))   # whole timeline moves to the next page rather than splitting
sbody=[[b['name'],m(b['planned']),m(b['spent'])] for b in bud]+[['Total moved to spending account',m(spend_plan),f'moved {m(xfer["amount"])}' if xfer else '']]
st.append(KeepTogether([Paragraph('Spending budget',H2),table(['Category','Budget','Spent'],sbody,[3.6,1.6,1.8],right=(1,2))]))
from reportlab.platypus import CondPageBreak
st.append(CondPageBreak(2.5*inch)); st.append(Paragraph('Month at a glance',H2))
g=[['Income expected',m(inc_exp)],['All income in (regular + one-off + transfers)',m(inc_bank+other_in,True)],['Planned expenses (fixed + one-offs + spending budget)',m(planned_exp,True)],['Able to save',m(able_to_save,True)],['Bills left to pay',f'{m(bills_left,True)}  ({m(fixed_left_amt,True)} fixed + {m(oo_left_amt,True)} one-off)'],
   ['Bills account available now',m(bal,True)],['Pending (in and out)',m(pending,True)],['Left in bills account after all bills',m(left_after,True)],['Left if unpaid one-offs are not owed',m(left_after_fixed_only,True)]]
st.append(KeepTogether(table(['Item','Amount'],g,[4.6,2.4],right=(1,),total=False)))
st.append(Paragraph('Debt snowball',H2))
db=[[str(d['order']),d['name'],f"{d['apr']:.2f}%",m(d['min']),m(d['start']-d['paid']),addm(next(x for x in SB['debts'] if x['name']==d['name'])['clear']).strftime('%b %Y')] for d in debts]
db.append(['','Total',f'+{m(S["snowball"]["extra_per_month"])}/mo extra','',m(owed),f'{debt_free.strftime("%b %Y")} ({SB["months"]} mo)'])
st.append(KeepTogether([table(['#','Debt','APR','Min','Balance','Projected clear'],db,[0.3,2.3,1.3,0.8,1.1,1.2],right=(3,4),center=(0,2,5)),Paragraph(f'Snowball: {m(SB["total_pay"])}/mo total, {m(SB["interest"],True)} interest. Avalanche: {AV["months"]} months, {m(AV["interest"],True)} interest.',N)]))
doc(f'{OUT}/{MON}-budget-plan.pdf').build(st,onFirstPage=foot_for('Monthly Budget Plan'),onLaterPages=foot_for('Monthly Budget Plan'))
# 2) Where the Money Went
tx=S['transactions']; posted=[t for t in tx if not t[3]]
def is_own_xfer(t): d=t[5].upper(); return any(k in d for k in CFG['own_transfer_keywords'])
card_pay=[t for t in posted if any(k in t[5].upper() for k in CFG['card_payment_keywords'])]
own=[t for t in posted if is_own_xfer(t)]
fees=[t for t in posted if any(k in t[5].upper() for k in CFG['fee_keywords'])]
out_chk=-sum(t[1] for t in posted if t[1]<0 and t not in own and t not in card_pay)
st=[Paragraph('Where the Money Went — Monthly Report',Hs),Paragraph(E(CFG['owner_label']+'. '+CFG['account_note']),Sub),Spacer(1,4),
    Paragraph(f'<b>Month:</b> {MNAME} &nbsp; <b>Period:</b> {first.strftime("%m/%d/%Y")} to {TODAY.strftime("%m/%d/%Y")} (month to date) &nbsp; <b>Filled in:</b> {TODAY.strftime("%m/%d/%Y")}',Sub),
    Paragraph('<b>Sources reviewed:</b> <font name="DJ">☑</font> '+E(CFG['bills_account_label'])+' &nbsp; <font name="DJ">☐</font> '+E(CFG['spending_account_label'])+' &nbsp; <font name="DJ">☐</font> Credit cards',Sub),Paragraph('Summary',H2)]
summ=[['Total spending, all accounts (after exclusions)',m(out_chk,True)+' (checking only so far)'],['  Bills account (bills + one-offs)',m(out_chk,True)],['  Spending account (budget)','see section 3'],
      ['Overdraft fees this month (goal $0)',f'# {len(fees)} / {m(-sum(t[1] for t in fees),True)}'],['Excluded: transfers between own accounts',m(-sum(t[1] for t in own if t[1]<0),True)],['Excluded: credit card payments from checking',m(-sum(t[1] for t in card_pay),True)]]
st.append(table(['Item','Amount'],summ,[4.6,2.4],right=(1,),total=False))
st.append(Paragraph('Excluded items: '+'; '.join(f'{D(t[0]).strftime("%-m/%-d")} {m(t[1],True)} {t[5][:38]}' for t in own+card_pay if t[1]<0),N))
st.append(Paragraph('Where the Money Went by Budget',ParagraphStyle('h1b',parent=Hs,fontSize=15,leading=19,spaceBefore=10)))
st.append(Paragraph('1. Fixed bills',H2))
body,grp=grouped_bills(lambda b: ['','','','',''] if b is None else [b['name']+(' *' if b['unverified'] else ''),o_(D(b['due_date']).day),m(b['amount'],True),m(b.get('paid_amount'),True) if b['status']!='unpaid' else '',CHK(b['status']!='unpaid')])
body.append(['Total fixed bills','',m(planned_fixed,True),m(sum(b.get('paid_amount') or 0 for b in bills if b['status']!='unpaid'),True),''])
st.append(table(['Bill','Due','Budget','Actual','Paid'],body,[3.4,0.6,1.1,1.1,0.8],right=(2,3),center=(1,4),groups=grp))
st.append(Paragraph('2. One-off bills',H2))
st.append(KeepTogether(table(['Bill','Due','Amount','Paid'],ob,[4.3,0.7,1.1,0.9],right=(2,),center=(1,3))))
st.append(Paragraph('3. Spending budget',H2))
st.append(KeepTogether(table(['Category','Budget','Actual'],sbody,[3.6,1.6,1.8],right=(1,2))))
cat=defaultdict(float)
for t in posted:
    if t[1]<0 and not t[2] and t not in own and t not in card_pay: cat[(t[4] or 'Uncategorized').split(' (')[0]]+=-t[1]
st.append(Paragraph('4. Unbudgeted checking spending (not matched to a bill)',H2))
cb=[[k,m(v,True)] for k,v in sorted(cat.items(),key=lambda x:-x[1])]+[['Total',m(sum(cat.values()),True)]]
st.append(KeepTogether(table(['Category','Amount'],cb,[4.6,2.4],right=(1,))))
st.append(KeepTogether([Paragraph('5. Debt payments',H2),table(['Debt','Start of month','Paid this month','End balance'],[[d['name'],m(d['start']),m(d['paid']),m(d['start']-d['paid'])] for d in debts]+[['Total',m(owed),m(0),m(owed)]],[2.8,1.4,1.4,1.4],right=(1,2,3))]))
st.append(Paragraph('Credit card payments from checking this month ('+m(-sum(t[1] for t in card_pay),True)+') should be logged as debt_payments once the statement balance is confirmed.',N))
doc(f'{OUT}/{MON}-where-the-money-went.pdf').build(st,onFirstPage=foot_for('Where the Money Went'),onLaterPages=foot_for('Where the Money Went'))
print(json.dumps(dict(bills_left=bills_left,fixed_left=fixed_left_amt,oneoffs_left=oo_left_amt,bal=bal,pending=pending,left_after=round(left_after,2),left_after_fixed_only=round(left_after_fixed_only,2),able_to_save=able_to_save,planned_exp=planned_exp,
  snowball=dict(months=SB['months'],interest=round(SB['interest'],2),debt_free=str(debt_free),clears=[(d['name'],str(addm(d['clear']))) for d in SB['debts']]),avalanche=dict(months=AV['months'],interest=round(AV['interest'],2))),indent=1))
