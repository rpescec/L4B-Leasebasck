#!/usr/bin/env python3
import sys, json, os
from io import BytesIO
from datetime import datetime

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm, mm
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Table,
                                 TableStyle, Image, PageBreak)
from reportlab.platypus import KeepTogether

BLUE      = colors.HexColor('#0D5EA6')
GREEN     = colors.HexColor('#2ECC8F')
DARK_BLUE = colors.HexColor('#0A2A4A')
TEAL      = colors.HexColor('#1BA8A0')
TEAL_LIGHT= colors.HexColor('#E8F8F7')
LIGHT_BG  = colors.HexColor('#EEF5FF')
LIGHT_ROW = colors.HexColor('#F7FAFF')
GRAY_TEXT = colors.HexColor('#4A5568')
GRAY_MID  = colors.HexColor('#6B7A8D')
WHITE     = colors.white
BLACK     = colors.HexColor('#1A202C')
GREEN_BG  = colors.HexColor('#E8FAF3')
SEPARATOR = colors.HexColor('#D1E8E6')

W, H = A4

def fmtc(n):   return f"${int(round(n)):,}".replace(',', '.')
def fmtpm(n):  return f"{n:.2f}%"
def fmtuf(n,u): return f"{n/u:,.1f}".replace(',','X').replace('.',',').replace('X','.') if u else '-'

def calcular(d):
    vc  = d['val_comercial']
    pf  = d['pct_financiamiento'] / 100
    tm  = d['tasa_mensual'] / 100
    plz = int(d['plazo_meses'])
    pg  = d['pct_gastos_oper'] / 100
    pfe = d['pct_fee_estructuracion'] / 100
    pff = d.get('pct_fee_fondo', 0) / 100
    cbr = d.get('gastos_cbr', 0)
    deu = d.get('deuda_actual', 0)
    uf  = d.get('uf_clp', 40040)

    vf   = vc * pf
    goA  = vf * pg
    feA  = vf * pfe
    ffA  = vf * pff
    ia1  = vf * tm * 12
    desc = ia1 + feA + ffA
    ml   = vf - desc - deu

    cuota = vf*(tm*(1+tm)**plz)/((1+tm)**plz-1) if plz > 0 else vf
    amort, saldo = [], vf
    for i in range(1, plz+1):
        inte = saldo*tm; cap = cuota-inte; saldo -= cap
        amort.append({'mes':i,'cuota':cuota,'interes':inte,'capital':cap,'saldo':max(0,saldo)})

    return dict(
        val_comercial=vc, pct_fin=pf, valor_financiado=vf,
        gastos_oper=goA, fee_estruct=feA, fee_fondo=ffA, pct_fee_fondo=pff,
        prepago_rentas=0, acreedor=0, cbr=cbr, interes_anio1=ia1,
        descuentos=desc, deuda_actual=deu,
        monto_liquido=ml, valor_recompra=vf, cuota=cuota,
        total_pagado=cuota*plz, costo_fin=cuota*plz-vf,
        tasa_m=tm, tasa_anual=tm*12, plazo=plz,
        pct_gastos=pg, pct_fee=pfe, uf_clp=uf, amort=amort
    )

def chart_intereses_mes(amort, plazo):
    meses = [a['mes'] for a in amort]
    acc, acc_int = 0, []
    for a in amort:
        acc += a['interes']; acc_int.append(acc)
    fig, ax = plt.subplots(figsize=(8.5, 3.4))
    fig.patch.set_facecolor('white'); ax.set_facecolor('white')
    ax.plot(meses, acc_int, color='#1BA8A0', linewidth=2.5, marker='o',
            markersize=4, markerfacecolor='#2ECC8F', markeredgewidth=0)
    ax.fill_between(meses, acc_int, alpha=0.15, color='#1BA8A0')
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v,_: f"${v/1e6:.1f}M"))
    ax.set_xlabel('Mes', fontsize=8, color='#6B7A8D')
    ax.set_title('Intereses acumulados por mes', fontsize=10, fontweight='bold', color='#0A2A4A', pad=6)
    ax.spines['top'].set_visible(False); ax.spines['right'].set_visible(False)
    ax.spines['left'].set_color('#D1E8E6'); ax.spines['bottom'].set_color('#D1E8E6')
    ax.tick_params(colors='#6B7A8D', labelsize=7.5)
    ax.grid(axis='y', linestyle='--', alpha=0.4, color='#D1E8E6')
    plt.tight_layout()
    buf = BytesIO(); plt.savefig(buf, format='png', dpi=160, bbox_inches='tight', facecolor='white')
    plt.close(); buf.seek(0); return buf

def chart_comparacion(vc, vf, vr, label):
    cats = ['Tasación\nComercial', 'Valor\nCompraventa', 'Valor\nRecompra']
    vals = [vc, vf, vr]
    clrs = ['#1BA8A0', '#0D5EA6', '#2ECC8F']
    fig, ax = plt.subplots(figsize=(8, 3.2))
    fig.patch.set_facecolor('white'); ax.set_facecolor('white')
    bars = ax.bar(cats, vals, color=clrs, width=0.45, alpha=0.92)
    for bar, val in zip(bars, vals):
        ax.text(bar.get_x()+bar.get_width()/2, bar.get_height()*1.02,
                f"${val/1e6:.1f}M", ha='center', va='bottom', fontsize=8,
                fontweight='bold', color='#0A2A4A')
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v,_: f"${v/1e6:.0f}M"))
    ax.set_title(f'Comparación de valores', fontsize=10, fontweight='bold', color='#0A2A4A', pad=6)
    ax.spines['top'].set_visible(False); ax.spines['right'].set_visible(False)
    ax.spines['left'].set_color('#D1E8E6'); ax.spines['bottom'].set_color('#D1E8E6')
    ax.tick_params(colors='#6B7A8D', labelsize=8)
    ax.grid(axis='y', linestyle='--', alpha=0.35, color='#D1E8E6')
    plt.tight_layout()
    buf = BytesIO(); plt.savefig(buf, format='png', dpi=160, bbox_inches='tight', facecolor='white')
    plt.close(); buf.seek(0); return buf

def chart_dona(r):
    vals  = [r['monto_liquido'], r['descuentos'], r['gastos_oper']+r['cbr']]
    labs  = ['Monto\nlíquido', 'Costos\nfinancieros', 'Gastos\noperativos']
    clrs  = ['#0A2A4A', '#2ECC8F', '#1BA8A0']
    vals  = [max(v,0) for v in vals]; total = sum(vals) or 1
    fig, ax = plt.subplots(figsize=(5.5, 3.8))
    fig.patch.set_facecolor('white')
    wedges, _ = ax.pie(vals, colors=clrs, startangle=90,
                       wedgeprops={'width':0.55,'edgecolor':'white','linewidth':2.5})
    pcts = [f"{v/total*100:.1f}%" for v in vals]
    for i,(w,p) in enumerate(zip(wedges,pcts)):
        ang = (w.theta1+w.theta2)/2; r2=0.75
        x,y = r2*np.cos(np.deg2rad(ang)), r2*np.sin(np.deg2rad(ang))
        ax.annotate(p, xy=(x,y), ha='center', va='center',
                    fontsize=8.5, fontweight='bold', color='white')
    ax.legend(wedges, [f"{l.replace(chr(10),' ')} ({p})" for l,p in zip(labs,pcts)],
              loc='lower center', bbox_to_anchor=(0.5,-0.18), ncol=1, fontsize=7.5,
              framealpha=0, labelcolor='#3D4A5C')
    plt.tight_layout()
    buf = BytesIO(); plt.savefig(buf, format='png', dpi=160, bbox_inches='tight', facecolor='white')
    plt.close(); buf.seek(0); return buf

class HF:
    def __init__(self, logo_path, cli, fecha):
        self.logo=logo_path; self.cli=cli; self.fecha=fecha; self.num_label=''
    def __call__(self, canv, doc):
        canv.saveState()
        canv.setFillColor(DARK_BLUE); canv.rect(0,H-46,W,46,fill=1,stroke=0)
        canv.setFillColor(TEAL); canv.rect(0,H-49,W,3,fill=1,stroke=0)
        if self.logo and os.path.exists(self.logo):
            canv.drawImage(self.logo,14*mm,H-41,width=50*mm,height=28,
                           preserveAspectRatio=True,mask=None)
        canv.setFillColor(WHITE); canv.setFont('Helvetica-Bold',10)
        num_s = getattr(self,'num_label','')
        titulo = f'REPORTE FINANCIERO LEASEBACK  {num_s}' if num_s else 'REPORTE FINANCIERO LEASEBACK'
        canv.drawRightString(W-14*mm,H-22,titulo)
        canv.setFont('Helvetica',8); canv.setFillColor(colors.HexColor('#8FB8D8'))
        canv.drawRightString(W-14*mm,H-34,f'{self.cli}  ·  {self.fecha}')
        canv.setFillColor(DARK_BLUE); canv.rect(0,0,W,24,fill=1,stroke=0)
        canv.setFillColor(TEAL); canv.rect(0,24,W,2,fill=1,stroke=0)
        canv.setFillColor(WHITE); canv.setFont('Helvetica',7)
        canv.drawString(14*mm,8,'Just Loans 4 Business  |  Av. La Dehesa 1500 piso 4, Lo Barnechea  |  +56 9 8270 1655')
        canv.drawRightString(W-14*mm,8,f'www.loans4b.com  |  Pág. {doc.page}')
        canv.restoreState()

class CoverPage:
    def __init__(self, logo_path, cli, rut, fecha):
        self.logo=logo_path; self.cli=cli; self.rut=rut; self.fecha=fecha; self.num_label=''
    def __call__(self, canv, doc):
        canv.saveState()
        canv.setFillColor(WHITE); canv.rect(0,0,W,H,fill=1,stroke=0)
        canv.setFillColor(TEAL); canv.rect(0,0,6,H,fill=1,stroke=0)
        logo_cover = os.path.join(os.path.dirname(os.path.abspath(self.logo)),'logo_cover.png')
        logo_to_use = logo_cover if os.path.exists(logo_cover) else self.logo
        if logo_to_use and os.path.exists(logo_to_use):
            canv.drawImage(logo_to_use, W/2-110, H-105,
                           width=220, height=72, preserveAspectRatio=True, mask=None)
        canv.setFont('Helvetica',9); canv.setFillColor(GRAY_TEXT)
        canv.drawCentredString(W/2,H-118,'Just Loans 4 Business')
        canv.setStrokeColor(TEAL); canv.setLineWidth(0.8)
        canv.line(W/2-112,H-115,W/2-84,H-115)
        canv.line(W/2+84, H-115,W/2+112,H-115)
        canv.setStrokeColor(colors.HexColor('#E2EAF0')); canv.setLineWidth(0.5)
        canv.line(22,H-130,W-22,H-130)
        canv.setFillColor(colors.HexColor('#F8FAFC'))
        canv.roundRect(22,H-285,W-44,130,5,fill=1,stroke=0)
        canv.setStrokeColor(colors.HexColor('#D8E6EE')); canv.setLineWidth(0.6)
        canv.roundRect(22,H-285,W-44,130,5,fill=0,stroke=1)
        canv.setFillColor(TEAL); canv.roundRect(22,H-285,5,130,2,fill=1,stroke=0)
        canv.setFillColor(DARK_BLUE); canv.setFont('Helvetica-Bold',52)
        canv.drawCentredString(W/2+10,H-197,'REPORTE')
        canv.drawCentredString(W/2+10,H-251,'FINANCIERO')
        canv.setFont('Helvetica',9.5); canv.setFillColor(GRAY_TEXT)
        canv.drawCentredString(W/2+10,H-273,'Leaseback Inmobiliario  ·  Resumen Financiero Proyectado')
        canv.setFillColor(TEAL); canv.circle(W-48,H-210,18,fill=1,stroke=0)
        canv.setFillColor(WHITE); canv.setFont('Helvetica-Bold',7)
        canv.drawCentredString(W-48,H-213,'L4B')
        CLI_Y = H-390
        canv.setStrokeColor(colors.HexColor('#D0DDE8')); canv.setLineWidth(0.6)
        canv.roundRect(22,CLI_Y,W-44,82,4,fill=0,stroke=1)
        canv.setFillColor(TEAL); canv.roundRect(22,CLI_Y,5,82,2,fill=1,stroke=0)
        canv.setFont('Helvetica',7); canv.setFillColor(TEAL)
        canv.drawString(40,CLI_Y+66,'C L I E N T E')
        canv.setFont('Helvetica-Bold',17); canv.setFillColor(DARK_BLUE)
        canv.drawString(40,CLI_Y+44,self.cli)
        canv.setFont('Helvetica',9); canv.setFillColor(GRAY_TEXT)
        if self.rut and self.rut != '-':
            canv.drawString(40,CLI_Y+27,f'RUT  {self.rut}')
        canv.drawRightString(W-40,CLI_Y+27,self.fecha)
        canv.setStrokeColor(colors.HexColor('#EBF3F8')); canv.setLineWidth(0.5)
        canv.line(40,CLI_Y+19,W-40,CLI_Y+19)
        canv.setFont('Helvetica',8); canv.setFillColor(TEAL)
        canv.drawString(40,CLI_Y+8,'● Leaseback Inmobiliario')
        if self.num_label:
            canv.setFont('Helvetica-Bold',8)
            canv.setFillColor(TEAL)
            canv.drawRightString(W-40,CLI_Y+66,self.num_label)
        canv.setFillColor(GRAY_TEXT)
        canv.drawRightString(W-40,CLI_Y+8,'www.loans4b.com')
        MET_Y = CLI_Y-100
        metrics = [('+15 años','de experiencia',DARK_BLUE),('+800','empresas atendidas',TEAL),('18%','tasa anual referencial',DARK_BLUE)]
        bw=(W-44)/3; x0=22
        canv.setStrokeColor(colors.HexColor('#D8E6EE')); canv.setLineWidth(0.6)
        canv.roundRect(x0,MET_Y,W-44,72,4,fill=0,stroke=1)
        canv.setFillColor(colors.HexColor('#F8FAFC'))
        canv.roundRect(x0,MET_Y,W-44,72,4,fill=1,stroke=0)
        canv.roundRect(x0,MET_Y,W-44,72,4,fill=0,stroke=1)
        for i,(val,lbl,col) in enumerate(metrics):
            cx=x0+i*bw+bw/2
            if i>0:
                canv.setStrokeColor(colors.HexColor('#D8E6EE')); canv.setLineWidth(0.5)
                canv.line(x0+i*bw,MET_Y+10,x0+i*bw,MET_Y+62)
            canv.setFont('Helvetica-Bold',24); canv.setFillColor(col)
            canv.drawCentredString(cx,MET_Y+38,val)
            canv.setFont('Helvetica',8); canv.setFillColor(GRAY_TEXT)
            canv.drawCentredString(cx,MET_Y+23,lbl)
        canv.setStrokeColor(colors.HexColor('#D0DDE8')); canv.setLineWidth(0.5)
        canv.line(22,42,W-22,42)
        canv.setFont('Helvetica',7.5); canv.setFillColor(GRAY_TEXT)
        canv.drawString(22,28,'Av. La Dehesa 1500, piso 4, Lo Barnechea, Santiago')
        canv.drawRightString(W-22,28,'Info@loans4b.com  ·  +56 9 8270 1655')
        canv.setFillColor(TEAL); canv.circle(W/2,32,1.5,fill=1,stroke=0)
        canv.restoreState()

def P(txt, size=9, bold=False, color=GRAY_TEXT, align=TA_LEFT, leading=13):
    return Paragraph(txt, ParagraphStyle('_',
        fontName='Helvetica-Bold' if bold else 'Helvetica',
        fontSize=size, textColor=color, alignment=align, leading=leading))

def section_header(txt, subtitle=None):
    inner = [P(f'<b>{txt}</b>', size=13, color=WHITE, align=TA_CENTER, leading=16)]
    if subtitle:
        inner.append(P(subtitle, size=8.5, color=colors.HexColor('#B5E8E5'), align=TA_CENTER))
    t = Table([[v] for v in inner], colWidths=[W-28*mm])
    t.setStyle(TableStyle([
        ('BACKGROUND',(0,0),(-1,-1),colors.HexColor('#0D4F5A')),
        ('TOPPADDING',(0,0),(-1,-1),10),('BOTTOMPADDING',(0,0),(-1,-1),10),
        ('LEFTPADDING',(0,0),(-1,-1),14),
    ]))
    return t

def irow(label, valor, hl=False):
    bg = GREEN_BG if hl else LIGHT_ROW
    tc = colors.HexColor('#0A6B40') if hl else DARK_BLUE
    lb = P(label, size=8.5, color=GRAY_TEXT)
    vl = P(f'<b>{valor}</b>', size=9, color=tc, align=TA_RIGHT, bold=True)
    t  = Table([[lb,vl]], colWidths=[(W-28*mm)*0.62,(W-28*mm)*0.38])
    t.setStyle(TableStyle([
        ('BACKGROUND',(0,0),(-1,-1),bg),
        ('TOPPADDING',(0,0),(-1,-1),5),('BOTTOMPADDING',(0,0),(-1,-1),5),
        ('LEFTPADDING',(0,0),(-1,-1),11),('RIGHTPADDING',(0,0),(-1,-1),11),
        ('LINEBELOW',(0,0),(-1,-1),0.3,SEPARATOR),
    ]))
    return t

def metric_card_row(items):
    n=len(items); cw=(W-28*mm)/n
    r1=[P(f'<b>{v}</b>',size=s,color=colors.HexColor(c),align=TA_CENTER,leading=s+4) for _,v,c,s in items]
    r2=[P(l,size=7.5,color=GRAY_MID,align=TA_CENTER) for l,_,_,_ in items]
    t=Table([r1,r2],colWidths=[cw]*n)
    t.setStyle(TableStyle([
        ('BACKGROUND',(0,0),(-1,-1),WHITE),
        ('TOPPADDING',(0,0),(-1,0),12),('BOTTOMPADDING',(0,0),(-1,-1),10),
        ('LINEAFTER',(0,0),(-2,-1),0.5,SEPARATOR),
        ('BOX',(0,0),(-1,-1),1,TEAL),
        ('LINEABOVE',(0,0),(-1,0),3,TEAL),
        ('LEFTPADDING',(0,0),(-1,-1),0),('RIGHTPADDING',(0,0),(-1,-1),0),
    ]))
    return t

def analista_footer(analista, mes_anio):
    data=[[
        P(f'<b>Mes y año</b>',size=8,color=WHITE),
        P(mes_anio,size=9,color=WHITE),
        Spacer(1,1),
        P(f'<b>Analista a Cargo</b>',size=8,color=WHITE),
        P(analista,size=9,color=WHITE),
    ]]
    cw=[(W-28*mm)*v for v in [0.15,0.25,0.10,0.22,0.28]]
    t=Table(data,colWidths=cw)
    t.setStyle(TableStyle([
        ('BACKGROUND',(0,0),(1,0),TEAL),
        ('BACKGROUND',(2,0),(2,0),WHITE),
        ('BACKGROUND',(3,0),(4,0),DARK_BLUE),
        ('TOPPADDING',(0,0),(-1,-1),8),('BOTTOMPADDING',(0,0),(-1,-1),8),
        ('LEFTPADDING',(0,0),(-1,-1),10),('RIGHTPADDING',(0,0),(-1,-1),10),
    ]))
    return t

def sim_table_full(r, uf):
    vf = r['valor_financiado']
    rows_data = [
        ('DESGLOSE','PORCENTAJE','PESOS','UF','hdr'),
        ('Valor Tasación Comercial','',fmtc(r['val_comercial']),fmtuf(r['val_comercial'],uf),'teal'),
        ('Plazo Operación','',f"{r['plazo']} Meses",'','normal'),
        ('Valor Compraventa',fmtpm(r['pct_fin']*100),fmtc(vf),fmtuf(vf,uf),'teal'),
        ('Tasa Renta Mensual','',fmtpm(r['tasa_m']*100),'','normal'),
        ('Tasa Renta Anual','',fmtpm(r['tasa_anual']*100),'','normal'),
        ('','','','','sep'),
        ('Desglose (Giro bruto)','',fmtc(vf),fmtuf(vf,uf),'normal'),
        ('Prepago de Renta','',fmtc(r['interes_anio1']),'','normal'),
        ('Estructuración Financiera',fmtpm(r['pct_fee']*100),fmtc(r['fee_estruct']),'','normal'),
        ('Fee Estructuración Fondo',fmtpm(r['pct_fee_fondo']*100),fmtc(r['fee_fondo']),'','normal') if r['fee_fondo']>0 else None,
        ('Gastos Operacionales Totales','',fmtc(r['descuentos']),fmtuf(r['descuentos'],uf),'teal_bottom'),
        ('(-) Deuda actual a cancelar','',fmtc(r['deuda_actual']),fmtuf(r['deuda_actual'],uf),'normal') if r['deuda_actual']>0 else None,
        ('Capital Entregado al Deudor','',fmtc(r['monto_liquido']),fmtuf(r['monto_liquido'],uf),'green'),
        ('Valor Recompra Deudor','',fmtc(r['valor_recompra']),fmtuf(r['valor_recompra'],uf),'teal_bottom'),
    ]
    rows_data = [x for x in rows_data if x is not None]

    CW=[(W-28*mm)*v for v in [0.42,0.17,0.26,0.15]]
    table_rows=[]; ts_cmds=[]; row_idx=0
    for row in rows_data:
        *cells,kind=row
        if kind=='hdr':
            table_rows.append([P(f'<b>{c}</b>',size=8.5,color=WHITE,align=TA_CENTER) for c in cells])
            ts_cmds+=[ ('BACKGROUND',(0,row_idx),(-1,row_idx),colors.HexColor('#0D4F5A')),
                       ('TOPPADDING',(0,row_idx),(-1,row_idx),8),('BOTTOMPADDING',(0,row_idx),(-1,row_idx),8)]
        elif kind=='teal':
            table_rows.append([P(f'<b>{c}</b>',size=9,color=WHITE,align=TA_RIGHT if i>0 else TA_LEFT) for i,c in enumerate(cells)])
            ts_cmds+=[ ('BACKGROUND',(0,row_idx),(-1,row_idx),TEAL),
                       ('TOPPADDING',(0,row_idx),(-1,row_idx),7),('BOTTOMPADDING',(0,row_idx),(-1,row_idx),7)]
        elif kind=='teal_bottom':
            table_rows.append([P(f'<b>{c}</b>',size=9,color=WHITE,align=TA_RIGHT if i>0 else TA_LEFT) for i,c in enumerate(cells)])
            ts_cmds+=[ ('BACKGROUND',(0,row_idx),(-1,row_idx),TEAL),
                       ('TOPPADDING',(0,row_idx),(-1,row_idx),7),('BOTTOMPADDING',(0,row_idx),(-1,row_idx),7)]
        elif kind=='green':
            table_rows.append([P(f'<b>{c}</b>',size=10,color=WHITE,align=TA_RIGHT if i>0 else TA_LEFT) for i,c in enumerate(cells)])
            ts_cmds+=[ ('BACKGROUND',(0,row_idx),(-1,row_idx),colors.HexColor('#0D6B50')),
                       ('TOPPADDING',(0,row_idx),(-1,row_idx),9),('BOTTOMPADDING',(0,row_idx),(-1,row_idx),9)]
        elif kind=='sep':
            table_rows.append([P('') for _ in range(4)])
            ts_cmds+=[ ('BACKGROUND',(0,row_idx),(-1,row_idx),BLACK),
                       ('TOPPADDING',(0,row_idx),(-1,row_idx),3),('BOTTOMPADDING',(0,row_idx),(-1,row_idx),3)]
        else:
            rc=[P(cells[0],size=9,color=GRAY_TEXT)]
            rc+=[P(c,size=9,color=GRAY_TEXT,align=TA_RIGHT if i>0 else TA_LEFT) for i,c in enumerate(cells[1:])]
            table_rows.append(rc)
            bg=LIGHT_BG if row_idx%2==0 else WHITE
            ts_cmds+=[ ('BACKGROUND',(0,row_idx),(-1,row_idx),bg),
                       ('TOPPADDING',(0,row_idx),(-1,row_idx),6),('BOTTOMPADDING',(0,row_idx),(-1,row_idx),6)]
        row_idx+=1

    ts_cmds+=[
        ('LEFTPADDING',(0,0),(-1,-1),10),('RIGHTPADDING',(0,0),(-1,-1),10),
        ('LINEBELOW',(0,0),(-1,-2),0.3,SEPARATOR),
        ('ALIGN',(1,0),(-1,-1),'RIGHT'),('ALIGN',(0,0),(0,-1),'LEFT'),
    ]
    t=Table(table_rows,colWidths=CW)
    t.setStyle(TableStyle(ts_cmds))
    return t

def gastos_table(r, uf):
    AW=W-28*mm
    gas_hdr=[P('<b>Concepto</b>',size=8.5,color=WHITE,align=TA_LEFT),
             P('<b>Porcentaje</b>',size=8.5,color=WHITE,align=TA_CENTER),
             P('<b>Monto ($)</b>',size=8.5,color=WHITE,align=TA_RIGHT),
             P('<b>Monto (UF)</b>',size=8.5,color=WHITE,align=TA_RIGHT)]
    gas_rows=[
        gas_hdr,
        [P('Gastos Operativos',size=9,color=GRAY_TEXT),
         P(fmtpm(r['pct_gastos']*100),size=9,color=GRAY_TEXT,align=TA_CENTER),
         P(fmtc(r['gastos_oper']),size=9,color=GRAY_TEXT,align=TA_RIGHT),
         P(fmtuf(r['gastos_oper'],uf),size=9,color=GRAY_TEXT,align=TA_RIGHT)],
        [P('Gastos CBR / Notaría',size=9,color=GRAY_TEXT),
         P('—',size=9,color=GRAY_TEXT,align=TA_CENTER),
         P(fmtc(r['cbr']),size=9,color=GRAY_TEXT,align=TA_RIGHT),
         P(fmtuf(r['cbr'],uf),size=9,color=GRAY_TEXT,align=TA_RIGHT)],
        [P('<b>Total gastos operativos</b>',size=9,bold=True,color=WHITE),
         P('',size=9,color=WHITE,align=TA_CENTER),
         P(f'<b>{fmtc(r["gastos_oper"]+r["cbr"])}</b>',size=9,bold=True,color=WHITE,align=TA_RIGHT),
         P(f'<b>{fmtuf(r["gastos_oper"]+r["cbr"],uf)}</b>',size=9,bold=True,color=WHITE,align=TA_RIGHT)],
    ]
    gas_cws=[AW*0.42,AW*0.17,AW*0.25,AW*0.16]
    gas_t=Table(gas_rows,colWidths=gas_cws)
    gas_t.setStyle(TableStyle([
        ('BACKGROUND',(0,0),(-1,0),colors.HexColor('#0D4F5A')),
        ('BACKGROUND',(0,1),(-1,1),LIGHT_BG),
        ('BACKGROUND',(0,2),(-1,2),WHITE),
        ('BACKGROUND',(0,3),(-1,3),TEAL),
        ('TOPPADDING',(0,0),(-1,-1),7),('BOTTOMPADDING',(0,0),(-1,-1),7),
        ('LEFTPADDING',(0,0),(-1,-1),10),('RIGHTPADDING',(0,0),(-1,-1),10),
        ('LINEBELOW',(0,0),(-1,-2),0.3,SEPARATOR),
        ('ALIGN',(1,0),(-1,-1),'RIGHT'),('ALIGN',(1,0),(1,-1),'CENTER'),('ALIGN',(0,0),(0,-1),'LEFT'),
    ]))
    return gas_t

def generate_pdf(data, output_path, logo_path):
    r=calcular(data); d=data
    fecha=datetime.now().strftime('%d de %B de %Y')
    for es,sp in [('January','enero'),('February','febrero'),('March','marzo'),
                  ('April','abril'),('May','mayo'),('June','junio'),('July','julio'),
                  ('August','agosto'),('September','septiembre'),('October','octubre'),
                  ('November','noviembre'),('December','diciembre')]:
        fecha=fecha.replace(es,sp)
    mes_anio=datetime.now().strftime('%B %Y')
    for es,sp in [('January','Enero'),('February','Febrero'),('March','Marzo'),
                  ('April','Abril'),('May','Mayo'),('June','Junio'),('July','Julio'),
                  ('August','Agosto'),('September','Septiembre'),('October','Octubre'),
                  ('November','Noviembre'),('December','Diciembre')]:
        mes_anio=mes_anio.replace(es,sp)

    cli=d.get('nombre_cliente','Cliente'); rut=d.get('rut','-')
    num_sim=d.get('numero_simulacion',None)
    num_label=f'SIM-{num_sim:04d}' if num_sim else ''
    analista=d.get('analista','Karl Brunner Z.'); uf=r['uf_clp']
    cover_cb=CoverPage(logo_path,cli,rut,fecha)
    cover_cb.num_label=num_label
    hf_cb=HF(logo_path,cli,fecha)
    hf_cb.num_label=num_label
    doc=SimpleDocTemplate(output_path,pagesize=A4,
        leftMargin=14*mm,rightMargin=14*mm,topMargin=54,bottomMargin=32)
    SP=lambda n=6:Spacer(1,n)
    story=[]
    AW=W-28*mm

    # ── PORTADA ───────────────────────────────────────────────────────────────
    story.append(Spacer(1,H-100)); story.append(PageBreak())

    # ── PÁG 1: Resumen ejecutivo ──────────────────────────────────────────────
    cover_l4b=Table([[P('<b>Just Loans 4 Business</b>',size=14,bold=True,color=WHITE,align=TA_LEFT),
                      P('<b>loans4b.com</b>',size=10,bold=True,color=GREEN,align=TA_RIGHT)]],
                    colWidths=[AW*0.65,AW*0.35])
    cover_l4b.setStyle(TableStyle([
        ('BACKGROUND',(0,0),(-1,-1),BLUE),('TOPPADDING',(0,0),(-1,-1),10),
        ('BOTTOMPADDING',(0,0),(-1,-1),10),('LEFTPADDING',(0,0),(-1,-1),12),
        ('RIGHTPADDING',(0,0),(-1,-1),12),('LINEBELOW',(0,0),(-1,-1),3,GREEN),
    ]))
    story+=[cover_l4b,SP(5)]
    story+=[section_header('Quiénes somos'),SP(4)]
    story.append(P('En <b>Just Loans 4 Business</b> llevamos más de <b>15 años estructurando financiamiento '
        'internacional</b> para empresas de Latinoamérica. Hemos acompañado a más de <b>800 empresas</b> '
        'en exportaciones, créditos comerciales y proyectos inmobiliarios, conectándolas con '
        'los principales fondos de deuda privada de Estados Unidos.',
        size=8.5,color=GRAY_TEXT,leading=12,align=TA_JUSTIFY))
    story+=[SP(5)]
    story+=[section_header('Nuestros servicios'),SP(4)]

    def srv_card(titulo,desc,color_hex):
        cw_srv=AW/4-5
        t=Table([[P(f'<b>{titulo}</b>',size=8,bold=True,color=colors.HexColor(color_hex),leading=10)],
                 [SP(2)],[P(desc,size=7.5,color=GRAY_TEXT,leading=10)]],
                colWidths=[cw_srv-16])
        wrap=Table([[t]],colWidths=[cw_srv])
        wrap.setStyle(TableStyle([
            ('BACKGROUND',(0,0),(-1,-1),LIGHT_BG),('BOX',(0,0),(-1,-1),0.5,SEPARATOR),
            ('TOPPADDING',(0,0),(-1,-1),7),('BOTTOMPADDING',(0,0),(-1,-1),7),
            ('LEFTPADDING',(0,0),(-1,-1),8),('RIGHTPADDING',(0,0),(-1,-1),8),
            ('LINEABOVE',(0,0),(-1,0),3,colors.HexColor(color_hex)),
        ]))
        return wrap

    GAP=5; CW_SRV=AW/4-4
    srv_row=Table([[
        srv_card('Factoring Internacional','Liquidez inmediata para exportadores. Capital fresco en 24 hrs sin endeudarte.','#0D5EA6'),
        Spacer(GAP,1),
        srv_card('Créditos Comerciales','Financiamiento internacional. Créditos desde USD 3MM hasta USD 50MM.','#2ECC8F'),
        Spacer(GAP,1),
        srv_card('Leaseback Inmobiliario','Obtén liquidez con tu propiedad. Arriéndala y recomprala al final del plazo.','#1BA8A0'),
        Spacer(GAP,1),
        srv_card('LLC & Bancarización EE.UU.','Empresa en EE.UU. y cuenta bancaria internacional en dólares.','#7B5EA7'),
    ]],colWidths=[CW_SRV,GAP,CW_SRV,GAP,CW_SRV,GAP,CW_SRV])
    srv_row.setStyle(TableStyle([
        ('LEFTPADDING',(0,0),(-1,-1),0),('RIGHTPADDING',(0,0),(-1,-1),0),
        ('TOPPADDING',(0,0),(-1,-1),0),('BOTTOMPADDING',(0,0),(-1,-1),0),
        ('VALIGN',(0,0),(-1,-1),'TOP'),
    ]))
    story+=[srv_row,SP(5)]
    story+=[section_header('Por qué elegirnos'),SP(4)]
    CW_MET=AW/3
    met_r1=[P(f'<b>{v}</b>',size=18,color=colors.HexColor(c),align=TA_CENTER,leading=22)
            for v,c in [('+15 años','#0D5EA6'),('+800','#2ECC8F'),('+ USD 2B','#7B5EA7')]]
    met_r2=[P(l,size=7.5,color=GRAY_MID,align=TA_CENTER)
            for l in ['Años de experiencia','Empresas atendidas','En levantamiento de capital']]
    met_t=Table([met_r1,met_r2],colWidths=[CW_MET,CW_MET,CW_MET])
    met_t.setStyle(TableStyle([
        ('BACKGROUND',(0,0),(-1,-1),WHITE),('TOPPADDING',(0,0),(-1,0),10),
        ('BOTTOMPADDING',(0,0),(-1,-1),8),('LINEAFTER',(0,0),(-2,-1),0.5,SEPARATOR),
        ('BOX',(0,0),(-1,-1),1,TEAL),('LINEABOVE',(0,0),(-1,0),3,TEAL),
        ('LEFTPADDING',(0,0),(-1,-1),0),('RIGHTPADDING',(0,0),(-1,-1),0),
    ]))
    story+=[met_t,SP(5)]
    story+=[section_header('¿Qué es un Leaseback Inmobiliario?'),SP(4)]
    CW_L=AW*0.40; CW_R=AW-CW_L-8
    lease_txt=Table([[P('El <b>leaseback</b> es una operación en la que el propietario '
        '<b>vende el inmueble a un inversionista</b> y lo arrienda de vuelta, '
        'manteniendo el uso. Al final del plazo puede '
        '<b>recomprar la propiedad</b> al valor acordado.',
        size=8.5,color=GRAY_TEXT,leading=12,align=TA_JUSTIFY)]],colWidths=[CW_L])
    lease_txt.setStyle(TableStyle([
        ('LEFTPADDING',(0,0),(-1,-1),0),('RIGHTPADDING',(0,0),(-1,-1),0),
        ('TOPPADDING',(0,0),(-1,-1),0),('BOTTOMPADDING',(0,0),(-1,-1),0),
    ]))
    benef_rows=[
        ['Liquidez inmediata','Capital sin vender definitivamente.'],
        ['Sin pérdida de uso','Sigues operando en el mismo inmueble.'],
        ['Mejora el balance','Activo fijo convertido en liquidez.'],
        ['Recompra garantizada','Recupera tu propiedad al vencimiento.'],
    ]
    CW_BL=CW_R*0.40; CW_BR=CW_R*0.60
    ben_data=[[P(f'<b>{b[0]}</b>',size=8,bold=True,color=DARK_BLUE),
               P(b[1],size=8,color=GRAY_TEXT)] for b in benef_rows]
    ben_t=Table(ben_data,colWidths=[CW_BL,CW_BR])
    ben_t.setStyle(TableStyle([
        ('ROWBACKGROUNDS',(0,0),(-1,-1),[LIGHT_ROW,LIGHT_BG]),
        ('TOPPADDING',(0,0),(-1,-1),4),('BOTTOMPADDING',(0,0),(-1,-1),4),
        ('LEFTPADDING',(0,0),(-1,-1),8),('RIGHTPADDING',(0,0),(-1,-1),6),
        ('LINEBELOW',(0,0),(-1,-2),0.3,SEPARATOR),('LINEBEFORE',(0,0),(0,-1),3,GREEN),
    ]))
    two_col=Table([[lease_txt,Spacer(8,1),ben_t]],colWidths=[CW_L,8,CW_R])
    two_col.setStyle(TableStyle([
        ('VALIGN',(0,0),(-1,-1),'TOP'),
        ('LEFTPADDING',(0,0),(-1,-1),0),('RIGHTPADDING',(0,0),(-1,-1),0),
        ('TOPPADDING',(0,0),(-1,-1),0),('BOTTOMPADDING',(0,0),(-1,-1),0),
    ]))
    story+=[two_col,SP(6)]
    CW_C=[AW*0.12,AW*0.40,AW*0.22,AW*0.26]
    ct=Table([[P('<b>Contacto</b>',size=8,bold=True,color=WHITE),
               P('Av. La Dehesa 1500, piso 4, Lo Barnechea, Santiago',size=8,color=colors.HexColor('#B5D4F4')),
               P('+56 9 8270 1655',size=8,color=colors.HexColor('#B5D4F4')),
               P('Info@loans4b.com',size=8,color=GREEN)]],colWidths=CW_C)
    ct.setStyle(TableStyle([
        ('BACKGROUND',(0,0),(-1,-1),DARK_BLUE),
        ('TOPPADDING',(0,0),(-1,-1),8),('BOTTOMPADDING',(0,0),(-1,-1),8),
        ('LEFTPADDING',(0,0),(-1,-1),8),('RIGHTPADDING',(0,0),(-1,-1),8),
        ('LINEABOVE',(0,0),(-1,0),2,GREEN),('VALIGN',(0,0),(-1,-1),'MIDDLE'),
    ]))
    story+=[ct,PageBreak()]

    # ── PÁG 2: Avalúo Fiscal ─────────────────────────────────────────────────
    story+=[section_header('CERTIFICADO DE AVALÚO FISCAL','Avalúos en pesos del '+d.get('periodo_avaluo','1er Semestre 2026')),SP(10)]
    av_data=[[P('<b>DESGLOSE</b>',size=8.5,color=WHITE,align=TA_CENTER),P('<b>VALOR</b>',size=8.5,color=WHITE,align=TA_CENTER)]]
    for lbl,val in [
        ('Comuna',d.get('comuna','-')),('Número de Rol de Avalúo',d.get('rol','-')),
        ('Dirección o Nombre del bien raíz',d.get('direccion','-')),
        ('Destino del bien raíz',d.get('destino','-')),
        ('Período del avalúo',d.get('periodo_avaluo','1er Semestre 2026')),
        ('Fecha de emisión',d.get('fecha_avaluo','-')),
    ]:
        av_data.append([P(lbl,size=9,color=GRAY_TEXT),P(val,size=9,color=DARK_BLUE,align=TA_RIGHT)])
    av_t=Table(av_data,colWidths=[AW*0.6,AW*0.4])
    av_t.setStyle(TableStyle([
        ('BACKGROUND',(0,0),(-1,0),colors.HexColor('#0D4F5A')),
        ('TOPPADDING',(0,0),(-1,-1),7),('BOTTOMPADDING',(0,0),(-1,-1),7),
        ('LEFTPADDING',(0,0),(-1,-1),12),('RIGHTPADDING',(0,0),(-1,-1),12),
        ('LINEBELOW',(0,0),(-1,-2),0.3,SEPARATOR),
        ('ROWBACKGROUNDS',(0,1),(-1,-1),[WHITE,LIGHT_BG]),
    ]))
    story+=[av_t,SP(10)]
    av2_data=[
        [P('<b>AVALÚO TOTAL</b>',size=9,color=WHITE),
         P('$',size=9,color=WHITE,align=TA_CENTER),
         P(f'<b>{fmtc(d.get("avaluo_fiscal_clp",0))}</b>',size=11,color=GREEN,align=TA_RIGHT)],
        [P('AVALÚO EXENTO DE IMPUESTO',size=9,color=colors.HexColor('#B5E8E5')),
         P('$',size=9,color=colors.HexColor('#B5E8E5'),align=TA_CENTER),
         P(fmtc(d.get('avaluo_exento_clp',0)),size=9,color=colors.HexColor('#B5E8E5'),align=TA_RIGHT)],
        [P('AVALÚO AFECTO A IMPUESTO',size=9,color=colors.HexColor('#B5E8E5')),
         P('$',size=9,color=colors.HexColor('#B5E8E5'),align=TA_CENTER),
         P(fmtc(d.get('avaluo_afecto_clp',0)),size=9,color=colors.HexColor('#B5E8E5'),align=TA_RIGHT)],
    ]
    av2_t=Table(av2_data,colWidths=[AW*0.55,AW*0.08,AW*0.37])
    av2_t.setStyle(TableStyle([
        ('BACKGROUND',(0,0),(-1,-1),colors.HexColor('#0D4F5A')),
        ('TOPPADDING',(0,0),(-1,-1),8),('BOTTOMPADDING',(0,0),(-1,-1),8),
        ('LEFTPADDING',(0,0),(-1,-1),12),('RIGHTPADDING',(0,0),(-1,-1),12),
        ('LINEBELOW',(0,0),(-1,-2),0.5,TEAL),
    ]))
    story+=[av2_t,SP(12)]
    story.append(P('<i>NOTA IMPORTANTE: El avalúo que se indica ha sido determinado según el procedimiento de '
        'tasación fiscal para el cálculo del Impuesto Territorial, de acuerdo a la legislación '
        'vigente, y por tanto no corresponde a una tasación comercial de la propiedad.</i>',
        size=8,color=GRAY_MID,leading=12,align=TA_JUSTIFY))
    story+=[SP(16)]
    vc_t=Table([[P('<b>Valor comercial estimado</b>',size=9,color=DARK_BLUE),
                 P(f'<b>{fmtc(d["val_comercial"])}</b>',size=13,color=TEAL,align=TA_RIGHT)]],
               colWidths=[AW*0.6,AW*0.4])
    vc_t.setStyle(TableStyle([
        ('BACKGROUND',(0,0),(-1,-1),TEAL_LIGHT),('TOPPADDING',(0,0),(-1,-1),10),
        ('BOTTOMPADDING',(0,0),(-1,-1),10),('LEFTPADDING',(0,0),(-1,-1),14),
        ('RIGHTPADDING',(0,0),(-1,-1),14),('BOX',(0,0),(-1,-1),1,TEAL),
        ('LINEABOVE',(0,0),(-1,0),3,TEAL),
    ]))
    story+=[vc_t,SP(10),analista_footer(analista,mes_anio),PageBreak()]

    # ── PÁG 3: Simulación ────────────────────────────────────────────────────
    story+=[section_header('SIMULACIÓN DE LEASEBACK INMOBILIARIO'),SP(10)]
    story+=[sim_table_full(r,uf),SP(10)]
    story+=[section_header('DETALLE DE GASTOS OPERATIVOS'),SP(6)]
    story+=[gastos_table(r,uf),SP(6),PageBreak()]

    # ── PÁG 4: Análisis Financiero ───────────────────────────────────────────
    story+=[section_header('ANÁLISIS FINANCIERO','Just Loans 4 Business'),SP(8)]
    story.append(P('El siguiente análisis detalla las condiciones financieras de la operación, '
        'desglosando la estructura de intereses, tasas aplicables y costos financieros totales.',
        size=8.5,color=GRAY_TEXT,leading=13,align=TA_JUSTIFY))
    story+=[SP(12)]

    _mit=[
        (fmtc(r['monto_liquido']),'Capital entregado al deudor','#1BA8A0',12),
        (fmtc(r['valor_recompra']),'Valor recompra','#0D5EA6',12),
        (fmtpm(r['tasa_m']*100),'Tasa de interés mensual','#2ECC8F',20),
        (f"{r['plazo']} M",'Plazo del crédito','#0A2A4A',20),
    ]
    _n=len(_mit); _cw=AW/_n
    _r1=[P(f'<b>{v}</b>',size=s,color=colors.HexColor(c),align=TA_CENTER,leading=s+4) for v,_,c,s in _mit]
    _r2=[P(l,size=7.5,color=GRAY_MID,align=TA_CENTER) for _,l,_,_ in _mit]
    _mt=Table([_r1,_r2],colWidths=[_cw]*_n)
    _mt.setStyle(TableStyle([
        ('BACKGROUND',(0,0),(-1,-1),WHITE),('TOPPADDING',(0,0),(-1,0),12),
        ('BOTTOMPADDING',(0,0),(-1,-1),10),('LINEAFTER',(0,0),(-2,-1),0.5,SEPARATOR),
        ('BOX',(0,0),(-1,-1),1,TEAL),('LINEABOVE',(0,0),(-1,0),3,TEAL),
    ]))
    story+=[_mt,SP(12)]

    box1=Table([[P('<b>Tasación de Activos Tangibles</b>',size=9.5,bold=True,color=DARK_BLUE)],
                [P(f'Tasación comercial total: <b>{fmtc(r["val_comercial"])}</b>',size=8.5,color=GRAY_TEXT)],
                [P(f'Porcentaje de compraventa: <b>{fmtpm(r["pct_fin"]*100)}</b>',size=8.5,color=GRAY_TEXT)],
                [P(f'Plazo aprobado: <b>{r["plazo"]} meses</b>',size=8.5,color=GRAY_TEXT)]],
               colWidths=[AW*0.5-8])
    box1.setStyle(TableStyle([('BOX',(0,0),(-1,-1),1,TEAL),
        ('TOPPADDING',(0,0),(-1,-1),6),('BOTTOMPADDING',(0,0),(-1,-1),6),
        ('LEFTPADDING',(0,0),(-1,-1),12),('RIGHTPADDING',(0,0),(-1,-1),12)]))

    box2_rows=[[P('<b>Riesgo crediticio</b>',size=9.5,bold=True,color=DARK_BLUE),P('')],
               [P('Capital',size=8.5,color=GRAY_TEXT),P(fmtc(r['monto_liquido']),size=8.5,color=DARK_BLUE,align=TA_RIGHT)],
               [P('Recompra',size=8.5,color=GRAY_TEXT),P(fmtc(r['valor_recompra']),size=8.5,color=DARK_BLUE,align=TA_RIGHT)],
               [P('Tasa interés',size=8.5,color=GRAY_TEXT),P(fmtpm(r['tasa_m']*100),size=8.5,color=DARK_BLUE,align=TA_RIGHT)],
               [P('Valor UF',size=8.5,color=GRAY_TEXT),P(fmtc(uf),size=8.5,color=DARK_BLUE,align=TA_RIGHT)]]
    box2=Table(box2_rows,colWidths=[AW*0.25,AW*0.25])
    box2.setStyle(TableStyle([('BOX',(0,0),(-1,-1),1,TEAL),
        ('TOPPADDING',(0,0),(-1,-1),6),('BOTTOMPADDING',(0,0),(-1,-1),6),
        ('LEFTPADDING',(0,0),(-1,-1),12),('RIGHTPADDING',(0,0),(-1,-1),12),
        ('SPAN',(0,0),(-1,0)),('LINEBELOW',(0,1),(-1,-2),0.3,SEPARATOR),
        ('ROWBACKGROUNDS',(0,1),(-1,-1),[WHITE,LIGHT_BG])]))

    boxes=Table([[box1,Spacer(16,1),box2]],colWidths=[AW*0.5,16,AW*0.5])
    boxes.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'TOP'),
        ('LEFTPADDING',(0,0),(-1,-1),0),('RIGHTPADDING',(0,0),(-1,-1),0)]))
    story+=[boxes,SP(12)]
    story+=[Image(chart_intereses_mes(r['amort'],r['plazo']),width=AW,height=7.5*cm),SP(10)]

    kpi_items=[('1','Activos en operación','#0D4F5A'),
               (fmtpm(r['tasa_anual']*100),'Interés anual','#0D4F5A'),
               (f"{r['plazo']} meses",'Plazo del crédito','#0D4F5A')]
    kpi_cw=(AW)/3-6
    kpi_cells=[]
    for val,lbl,bg in kpi_items:
        sub=Table([[P(f'<b>{val}</b>',size=16,color=WHITE,align=TA_CENTER,leading=20)],
                   [P(lbl,size=8,color=colors.HexColor('#B5E8E5'),align=TA_CENTER)]],
                  colWidths=[kpi_cw])
        sub.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,-1),colors.HexColor(bg)),
            ('TOPPADDING',(0,0),(-1,-1),8),('BOTTOMPADDING',(0,0),(-1,-1),8),
            ('LEFTPADDING',(0,0),(-1,-1),6),('RIGHTPADDING',(0,0),(-1,-1),6)]))
        kpi_cells.append(sub)
    kpi=Table([[kpi_cells[0],Spacer(8,1),kpi_cells[1],Spacer(8,1),kpi_cells[2]]],
              colWidths=[kpi_cw,8,kpi_cw,8,kpi_cw])
    kpi.setStyle(TableStyle([('LEFTPADDING',(0,0),(-1,-1),0),('RIGHTPADDING',(0,0),(-1,-1),0),
        ('TOPPADDING',(0,0),(-1,-1),0),('BOTTOMPADDING',(0,0),(-1,-1),0),
        ('VALIGN',(0,0),(-1,-1),'MIDDLE')]))
    story+=[kpi,SP(10),analista_footer(analista,mes_anio),SP(16)]

    # ── NOTA LEGAL ────────────────────────────────────────────────────────────
    nota_items=[
        P('<b>Condiciones y vigencia de la presente simulación</b>',size=9,bold=True,color=DARK_BLUE,leading=13),
        SP(6),
        P('Esta simulación tiene una vigencia de <b>cinco días hábiles</b> y está condicionada al cumplimiento de las siguientes exigencias:',
          size=8,color=GRAY_TEXT,leading=12,align=TA_JUSTIFY),
        SP(5),
    ]
    for num,cond in [
        ('<b>(1)</b>','Que el valor de tasación encargado sea igual o superior al valor estimado indicado en esta simulación.'),
        ('<b>(2)</b>','Que la evaluación de riesgo resulte positiva, a exclusivo criterio y satisfacción de L4B.'),
        ('<b>(3)</b>','Que se prepare, otorgue y suscriba, a satisfacción de L4B, toda la documentación habitual para este tipo de transacciones, incluyendo: (i) Títulos conformes a Derecho; (ii) Contrato de arrendamiento; (iii) Escritura de compraventa; y (iv) Cualquier otra documentación que L4B estime necesaria.'),
        ('<b>(4)</b>','Que el cliente manifieste su aprobación mediante comunicación escrita dirigida a L4B, para efectos de continuar con el proceso de evaluación.'),
    ]:
        row=Table([[P(num,size=8,bold=True,color=DARK_BLUE),
                    P(cond,size=8,color=GRAY_TEXT,leading=12,align=TA_JUSTIFY)]],
                  colWidths=[18,AW-18])
        row.setStyle(TableStyle([('TOPPADDING',(0,0),(-1,-1),3),('BOTTOMPADDING',(0,0),(-1,-1),3),
            ('LEFTPADDING',(0,0),(-1,-1),0),('RIGHTPADDING',(0,0),(-1,-1),0),('VALIGN',(0,0),(-1,-1),'TOP')]))
        nota_items.append(row)

    nota_items+=[
        SP(8),
        P('En consecuencia, esta propuesta es de <b>carácter no vinculante</b> y no constituye compromiso ni obligación alguna para L4B de materializar la(s) respectiva(s) operación(es). L4B se reserva el derecho de modificarla, complementarla o dejarla sin efecto, a su sola discreción, en cualquier momento.',
          size=8,color=GRAY_TEXT,leading=12,align=TA_JUSTIFY),
        SP(8),
        P('Los gastos de tasación, notariales y de inscripción en el Conservador de Bienes Raíces serán de <b>cargo exclusivo del cliente</b>.',
          size=8,color=GRAY_TEXT,leading=12,align=TA_JUSTIFY),
        SP(5),
        P('Los gastos de estudios legales deberán ser provisionados por el cliente previamente a su realización, y serán reembolsados únicamente contra la materialización efectiva de la(s) respectiva(s) compraventa(s). En caso de no producirse dicha materialización, por cualquier causa, dichos gastos no serán reembolsados.',
          size=8,color=GRAY_TEXT,leading=12,align=TA_JUSTIFY),
        SP(10),
        P('<b>(*)</b> La(s) base(s) imponible(s) aplicable(s) a la(s) compraventa(s), rentas de arrendamiento y/o opción(es) de compra dependerá(n) de las características del(de los) inmueble(s) y de las condiciones en que fue(ron) adquirido(s). Dichas bases serán determinadas en el(los) correspondiente(s) estudio(s) tributario(s).',
          size=7.5,color=GRAY_MID,leading=11,align=TA_JUSTIFY),
    ]
    story.append(KeepTogether(nota_items))

    def on_page(canv,doc):
        if doc.page==1: cover_cb(canv,doc)
        elif doc.page==2: pass
        else: hf_cb(canv,doc)

    doc.build(story,onFirstPage=on_page,onLaterPages=on_page)
    print(f"OK:{output_path}")

if __name__=='__main__':
    data=json.loads(sys.argv[1]); output=sys.argv[2]
    logo=sys.argv[3] if len(sys.argv)>3 else os.path.join(os.path.dirname(os.path.abspath(__file__)),'logo_clean.png')
    generate_pdf(data,output,logo)
