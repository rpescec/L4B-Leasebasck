#!/usr/bin/env python3
"""Loans4B — Generador PDF Leaseback v2 — Estilo Reporte Financiero Premium"""
import sys, json, os, math
from io import BytesIO
from datetime import datetime

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import matplotlib.patches as mpatches
import numpy as np
from PIL import Image as PILImage, ImageDraw

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm, mm
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Table,
                                 TableStyle, Image, PageBreak, HRFlowable)
from reportlab.pdfgen import canvas as CV
from reportlab.platypus.flowables import Flowable

# ── Paleta corporativa ────────────────────────────────────────────────────────
DARK_BLUE  = colors.HexColor('#0A2A4A')   # fondo portada / headers
MID_BLUE   = colors.HexColor('#0D5EA6')   # azul Loans4B
BLUE       = MID_BLUE
LIGHT_BG   = colors.HexColor('#EEF5FF')
LIGHT_ROW  = colors.HexColor('#F7FAFF')
TEAL       = colors.HexColor('#1BA8A0')   # teal tablas simulación
TEAL_LIGHT = colors.HexColor('#E8F8F7')   # fondo claro teal
GREEN      = colors.HexColor('#2ECC8F')   # acento verde logo
GREEN_DARK = colors.HexColor('#0E9B6A')
WHITE      = colors.white
GRAY_LIGHT = colors.HexColor('#F5F7FA')
GRAY_TEXT  = colors.HexColor('#3D4A5C')
GRAY_MID   = colors.HexColor('#6B7A8D')
SEPARATOR  = colors.HexColor('#D1E8E6')
BLACK      = colors.HexColor('#111827')
ROW_ALT    = colors.HexColor('#F0FAFA')

W, H = A4

def fmtc(n):   return f"${int(round(n)):,}".replace(',', '.')
def fmtuf(n):  return f"{n:,.1f}".replace(',','X').replace('.',',').replace('X','.')
def fmtpm(n):  return f"{n:.1f}%"
def fmtpm2(n): return f"{n:.2f}%"

# ── Cálculo ───────────────────────────────────────────────────────────────────
def calcular(d):
    vc  = d['val_comercial']
    pf  = d['pct_financiamiento'] / 100
    tm  = d['tasa_mensual'] / 100
    plz = int(d['plazo_meses'])
    pg  = d['pct_gastos_oper'] / 100
    pfe = d['pct_fee_estructuracion'] / 100
    pre = d.get('prepago_rentas', 0)
    acr = d.get('acreedor', 0)
    cbr = d.get('gastos_cbr', 0)
    uf  = d.get('uf_clp', 40000)

    vf   = vc * pf
    goA  = vf * pg
    feA  = vf * pfe
    ia1  = vf * tm * 12
    desc = pre + goA + feA + ia1 + acr + cbr
    ml   = vf - desc
    cuota = vf*(tm*(1+tm)**plz)/((1+tm)**plz-1)

    amort, saldo = [], vf
    for i in range(1, plz+1):
        inte = saldo*tm; cap = cuota-inte; saldo -= cap
        amort.append({'mes':i,'cuota':cuota,'interes':inte,'capital':cap,'saldo':max(0,saldo)})

    return dict(
        val_comercial=vc, pct_fin=pf, valor_financiado=vf,
        gastos_oper=goA, fee_estruct=feA, prepago_rentas=pre,
        acreedor=acr, cbr=cbr, interes_anio1=ia1, descuentos=desc,
        monto_liquido=ml, valor_recompra=vf, cuota=cuota,
        total_pagado=cuota*plz, costo_fin=cuota*plz-vf,
        tasa_m=tm, tasa_anual=tm*12, plazo=plz,
        pct_gastos=pg, pct_fee=pfe, uf_clp=uf, amort=amort
    )

# ── Gráficos ──────────────────────────────────────────────────────────────────
def chart_intereses_mes(amort, plazo, titulo='Intereses acumulados por mes'):
    meses  = [a['mes']    for a in amort]
    # acumulado
    acc_int = []
    acc = 0
    for a in amort:
        acc += a['interes']
        acc_int.append(acc)

    fig, ax = plt.subplots(figsize=(8.5, 3.4))
    fig.patch.set_facecolor('white')
    ax.set_facecolor('white')
    ax.plot(meses, acc_int, color='#1BA8A0', linewidth=2.5, marker='o',
            markersize=4, markerfacecolor='#2ECC8F', markeredgewidth=0)
    ax.fill_between(meses, acc_int, alpha=0.15, color='#1BA8A0')
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v,_: f"${v/1e6:.1f}M"))
    ax.set_xlabel('Mes', fontsize=8, color='#6B7A8D')
    ax.set_title(titulo, fontsize=10, fontweight='bold', color='#0A2A4A', pad=6)
    ax.spines['top'].set_visible(False); ax.spines['right'].set_visible(False)
    ax.spines['left'].set_color('#D1E8E6'); ax.spines['bottom'].set_color('#D1E8E6')
    ax.tick_params(colors='#6B7A8D', labelsize=7.5)
    ax.grid(axis='y', linestyle='--', alpha=0.4, color='#D1E8E6')
    plt.tight_layout()
    buf = BytesIO(); plt.savefig(buf, format='png', dpi=160, bbox_inches='tight', facecolor='white')
    plt.close(); buf.seek(0); return buf

def chart_comparacion_activos(vc, vf, vr, label='Propiedad'):
    cats  = ['Tasación\nComercial', 'Valor\nCompraventa', 'Valor\nRecompra']
    vals  = [vc, vf, vr]
    clrs  = ['#1BA8A0', '#0D5EA6', '#2ECC8F']
    fig, ax = plt.subplots(figsize=(8, 3.2))
    fig.patch.set_facecolor('white'); ax.set_facecolor('white')
    bars = ax.bar(cats, vals, color=clrs, width=0.45, alpha=0.92)
    for bar, val in zip(bars, vals):
        ax.text(bar.get_x()+bar.get_width()/2, bar.get_height()*1.02,
                f"${val/1e6:.1f}M", ha='center', va='bottom', fontsize=8,
                fontweight='bold', color='#0A2A4A')
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v,_: f"${v/1e6:.0f}M"))
    ax.set_title(f'Comparación de valores — {label}', fontsize=10, fontweight='bold', color='#0A2A4A', pad=6)
    ax.spines['top'].set_visible(False); ax.spines['right'].set_visible(False)
    ax.spines['left'].set_color('#D1E8E6'); ax.spines['bottom'].set_color('#D1E8E6')
    ax.tick_params(colors='#6B7A8D', labelsize=8)
    ax.grid(axis='y', linestyle='--', alpha=0.35, color='#D1E8E6')
    plt.tight_layout()
    buf = BytesIO(); plt.savefig(buf, format='png', dpi=160, bbox_inches='tight', facecolor='white')
    plt.close(); buf.seek(0); return buf

def chart_dona_activos(ml, desc, costo):
    total  = ml + desc + costo
    vals   = [max(ml,0), max(desc,0), max(costo,0)]
    labels = ['Activo Tangible\n(Monto líquido)', 'Costos\n(Descuentos)', 'Deuda\n(Costo fin.)']
    clrs   = ['#0A2A4A', '#2ECC8F', '#1BA8A0']
    pcts   = [f"{v/total*100:.1f}%" if total else "0%" for v in vals]
    fig, ax = plt.subplots(figsize=(4.2, 3.4))
    fig.patch.set_facecolor('white')
    wedges, _ = ax.pie(vals, colors=clrs, startangle=90,
                       wedgeprops={'width':0.55,'edgecolor':'white','linewidth':2.5})
    for i,(w,p,l) in enumerate(zip(wedges,pcts,labels)):
        ang = (w.theta1+w.theta2)/2; r=0.75
        x,y = r*np.cos(np.deg2rad(ang)), r*np.sin(np.deg2rad(ang))
        ax.annotate(p, xy=(x,y), ha='center', va='center',
                    fontsize=8.5, fontweight='bold', color='white')
    ax.legend(wedges, [f"{l.replace(chr(10),' ')} ({p})" for l,p in zip(labels,pcts)],
              loc='lower center', bbox_to_anchor=(0.5,-0.18), ncol=1, fontsize=7.5,
              framealpha=0, labelcolor='#3D4A5C')
    plt.tight_layout()
    buf = BytesIO(); plt.savefig(buf, format='png', dpi=160, bbox_inches='tight', facecolor='white')
    plt.close(); buf.seek(0); return buf

def chart_tasa_anual(tasa_mensual):
    tasas = [t for t in np.arange(0.5, tasa_mensual*12+0.5, 1.5)]
    vals  = [t for t in tasas]
    fig, ax = plt.subplots(figsize=(4.2, 3.4))
    fig.patch.set_facecolor('white'); ax.set_facecolor('white')
    clrs_bar = ['#2ECC8F' if t < tasa_mensual*12 else '#1BA8A0' for t in vals]
    clrs_bar[-1] = '#0D5EA6'
    ax.bar(range(len(tasas)), vals, color=clrs_bar, width=0.65, alpha=0.9)
    ax.set_xticks(range(len(tasas)))
    ax.set_xticklabels([f"{t:.1f}" for t in tasas], fontsize=7, rotation=45)
    ax.set_title('Tasa interés crédito anual (%)', fontsize=9, fontweight='bold', color='#0A2A4A', pad=5)
    ax.spines['top'].set_visible(False); ax.spines['right'].set_visible(False)
    ax.spines['left'].set_color('#D1E8E6'); ax.spines['bottom'].set_color('#D1E8E6')
    ax.tick_params(colors='#6B7A8D', labelsize=7)
    ax.grid(axis='y', linestyle='--', alpha=0.35, color='#D1E8E6')
    plt.tight_layout()
    buf = BytesIO(); plt.savefig(buf, format='png', dpi=160, bbox_inches='tight', facecolor='white')
    plt.close(); buf.seek(0); return buf

def chart_saldo(amort, plazo):
    step = max(1, plazo//50)
    idx  = list(range(0,len(amort),step))
    if len(amort)-1 not in idx: idx.append(len(amort)-1)
    meses  = [amort[i]['mes']   for i in idx]
    saldos = [amort[i]['saldo'] for i in idx]
    fig, ax = plt.subplots(figsize=(8.5, 3.0))
    fig.patch.set_facecolor('white'); ax.set_facecolor('white')
    ax.fill_between(meses, saldos, alpha=0.15, color='#1BA8A0')
    ax.plot(meses, saldos, color='#1BA8A0', linewidth=2.3)
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v,_: f"${v/1e6:.1f}M"))
    ax.set_xlabel('Mes', fontsize=8, color='#6B7A8D')
    ax.set_title('Evolución del saldo insoluto', fontsize=10, fontweight='bold', color='#0A2A4A', pad=5)
    ax.spines['top'].set_visible(False); ax.spines['right'].set_visible(False)
    ax.spines['left'].set_color('#D1E8E6'); ax.spines['bottom'].set_color('#D1E8E6')
    ax.tick_params(colors='#6B7A8D', labelsize=7.5)
    ax.grid(linestyle='--', alpha=0.35, color='#D1E8E6')
    plt.tight_layout()
    buf = BytesIO(); plt.savefig(buf, format='png', dpi=160, bbox_inches='tight', facecolor='white')
    plt.close(); buf.seek(0); return buf

# ── Header/Footer ─────────────────────────────────────────────────────────────
class HF:
    def __init__(self, logo_path, cli, fecha):
        self.logo = logo_path; self.cli = cli; self.fecha = fecha

    def __call__(self, canv, doc):
        canv.saveState()
        # Header
        canv.setFillColor(DARK_BLUE)
        canv.rect(0, H-46, W, 46, fill=1, stroke=0)
        canv.setFillColor(TEAL)
        canv.rect(0, H-49, W, 3, fill=1, stroke=0)
        if self.logo and os.path.exists(self.logo):
            canv.drawImage(self.logo, 14*mm, H-41, width=50*mm, height=28,
                           preserveAspectRatio=True, mask='auto')
        canv.setFillColor(WHITE); canv.setFont('Helvetica-Bold', 10)
        canv.drawRightString(W-14*mm, H-22, 'REPORTE FINANCIERO LEASEBACK')
        canv.setFont('Helvetica', 8); canv.setFillColor(colors.HexColor('#8FB8D8'))
        canv.drawRightString(W-14*mm, H-34, f'{self.cli}  ·  {self.fecha}')
        # Footer
        canv.setFillColor(DARK_BLUE)
        canv.rect(0, 0, W, 24, fill=1, stroke=0)
        canv.setFillColor(TEAL)
        canv.rect(0, 24, W, 2, fill=1, stroke=0)
        canv.setFillColor(WHITE); canv.setFont('Helvetica', 7)
        canv.drawString(14*mm, 8, 'Just Loans 4 Business  |  Av. La Dehesa 1500 piso 4, Lo Barnechea, Santiago  |  +56 9 8270 1655')
        canv.drawRightString(W-14*mm, 8, f'www.loans4b.com  |  Pág. {doc.page}')
        canv.restoreState()

# ── Portada especial ──────────────────────────────────────────────────────────
class CoverPage:
    def __init__(self, logo_path, cli, rut, fecha):
        self.logo=logo_path; self.cli=cli; self.rut=rut; self.fecha=fecha

    def __call__(self, canv, doc):
        canv.saveState()

        # ── Fondo blanco total ───────────────────────────────────────────────
        canv.setFillColor(WHITE)
        canv.rect(0, 0, W, H, fill=1, stroke=0)

        # ══ FRANJA LATERAL IZQUIERDA ════════════════════════════════════════
        canv.setFillColor(TEAL)
        canv.rect(0, 0, 6, H, fill=1, stroke=0)

        # ══ ZONA SUPERIOR — logo sobre fondo blanco puro ════════════════════
        logo_cover = '/home/claude/logo_cover.png'
        if os.path.exists(logo_cover):
            logo_w = 220
            logo_h = 72
            canv.drawImage(logo_cover, W/2 - logo_w/2, H - 105,
                           width=logo_w, height=logo_h,
                           preserveAspectRatio=True, mask=None)

        # Tagline bajo el logo
        canv.setFont('Helvetica', 9)
        canv.setFillColor(GRAY_TEXT)
        canv.drawCentredString(W/2, H - 118, 'Just Loans 4 Business')

        # Líneas decorativas flanqueando el tagline
        canv.setStrokeColor(TEAL)
        canv.setLineWidth(0.8)
        canv.line(W/2 - 112, H - 115, W/2 - 84, H - 115)
        canv.line(W/2 + 84,  H - 115, W/2 + 112, H - 115)

        # Línea separadora sutil
        canv.setStrokeColor(colors.HexColor('#E2EAF0'))
        canv.setLineWidth(0.5)
        canv.line(22, H - 130, W - 22, H - 130)

        # ══ BLOQUE TÍTULO ═══════════════════════════════════════════════════
        # Posición vertical centrada en la página
        TITLE_TOP = H - 155

        # Fondo gris muy suave (ahorra toner)
        canv.setFillColor(colors.HexColor('#F8FAFC'))
        canv.roundRect(22, TITLE_TOP - 130, W - 44, 130, 5, fill=1, stroke=0)

        # Borde fino gris
        canv.setStrokeColor(colors.HexColor('#D8E6EE'))
        canv.setLineWidth(0.6)
        canv.roundRect(22, TITLE_TOP - 130, W - 44, 130, 5, fill=0, stroke=1)

        # Acento teal izquierdo
        canv.setFillColor(TEAL)
        canv.roundRect(22, TITLE_TOP - 130, 5, 130, 2, fill=1, stroke=0)

        # "REPORTE"
        canv.setFillColor(DARK_BLUE)
        canv.setFont('Helvetica-Bold', 52)
        canv.drawCentredString(W/2 + 10, TITLE_TOP - 42, 'REPORTE')

        # "FINANCIERO"
        canv.setFont('Helvetica-Bold', 52)
        canv.drawCentredString(W/2 + 10, TITLE_TOP - 96, 'FINANCIERO')

        # Subtítulo
        canv.setFont('Helvetica', 9.5)
        canv.setFillColor(GRAY_TEXT)
        canv.drawCentredString(W/2 + 10, TITLE_TOP - 118,
                               'Leaseback Inmobiliario  ·  Resumen Financiero Proyectado')

        # Punto decorativo teal (esquina superior derecha del bloque)
        canv.setFillColor(TEAL)
        canv.circle(W - 48, TITLE_TOP - 20, 18, fill=1, stroke=0)
        canv.setFillColor(WHITE)
        canv.setFont('Helvetica-Bold', 7)
        canv.drawCentredString(W - 48, TITLE_TOP - 23, 'L4B')

        # ══ TARJETA CLIENTE ═════════════════════════════════════════════════
        CLI_Y = TITLE_TOP - 210

        # Borde fino con acento teal
        canv.setStrokeColor(colors.HexColor('#D0DDE8'))
        canv.setLineWidth(0.6)
        canv.roundRect(22, CLI_Y, W - 44, 82, 4, fill=0, stroke=1)

        # Acento teal izquierdo
        canv.setFillColor(TEAL)
        canv.roundRect(22, CLI_Y, 5, 82, 2, fill=1, stroke=0)

        # Label CLIENTE
        canv.setFont('Helvetica', 7)
        canv.setFillColor(TEAL)
        canv.drawString(40, CLI_Y + 66, 'C L I E N T E')

        # Nombre
        canv.setFont('Helvetica-Bold', 17)
        canv.setFillColor(DARK_BLUE)
        canv.drawString(40, CLI_Y + 44, self.cli)

        # RUT + Fecha en la misma línea
        canv.setFont('Helvetica', 9)
        canv.setFillColor(GRAY_TEXT)
        if self.rut and self.rut != '-':
            canv.drawString(40, CLI_Y + 27, f'RUT  {self.rut}')
        canv.drawRightString(W - 40, CLI_Y + 27, self.fecha)

        # Separador interno
        canv.setStrokeColor(colors.HexColor('#EBF3F8'))
        canv.setLineWidth(0.5)
        canv.line(40, CLI_Y + 19, W - 40, CLI_Y + 19)

        # Tag operación
        canv.setFont('Helvetica', 8)
        canv.setFillColor(TEAL)
        canv.drawString(40, CLI_Y + 8, '● Leaseback Inmobiliario')
        canv.setFillColor(GRAY_TEXT)
        canv.drawRightString(W - 40, CLI_Y + 8, 'www.loans4b.com')

        # ══ TRES MÉTRICAS ════════════════════════════════════════════════════
        MET_Y = CLI_Y - 100
        metrics = [
            ('+15 años', 'de experiencia',    DARK_BLUE),
            ('+800',     'empresas atendidas', TEAL),
            ('18%',      'tasa anual referencial', DARK_BLUE),
        ]
        bw = (W - 44) / 3
        x0 = 22

        # Borde exterior métricas
        canv.setStrokeColor(colors.HexColor('#D8E6EE'))
        canv.setLineWidth(0.6)
        canv.roundRect(x0, MET_Y, W - 44, 72, 4, fill=0, stroke=1)
        canv.setFillColor(colors.HexColor('#F8FAFC'))
        canv.roundRect(x0, MET_Y, W - 44, 72, 4, fill=1, stroke=0)
        canv.roundRect(x0, MET_Y, W - 44, 72, 4, fill=0, stroke=1)

        for i, (val, lbl, col) in enumerate(metrics):
            cx = x0 + i * bw + bw / 2

            # Separador vertical interno
            if i > 0:
                canv.setStrokeColor(colors.HexColor('#D8E6EE'))
                canv.setLineWidth(0.5)
                canv.line(x0 + i*bw, MET_Y + 10, x0 + i*bw, MET_Y + 62)

            # Valor
            canv.setFont('Helvetica-Bold', 24)
            canv.setFillColor(col)
            canv.drawCentredString(cx, MET_Y + 38, val)

            # Label
            canv.setFont('Helvetica', 8)
            canv.setFillColor(GRAY_TEXT)
            canv.drawCentredString(cx, MET_Y + 23, lbl)

        # ══ FOOTER ══════════════════════════════════════════════════════════
        canv.setStrokeColor(colors.HexColor('#D8E6EE'))
        canv.setLineWidth(0.5)
        canv.line(22, 42, W - 22, 42)

        canv.setFont('Helvetica', 7.5)
        canv.setFillColor(GRAY_TEXT)
        canv.drawString(22, 28, 'Av. La Dehesa 1500, piso 4, Lo Barnechea, Santiago')
        canv.drawRightString(W - 22, 28,
                             'Info@loans4b.com  ·  +56 9 8270 1655')

        canv.setFillColor(TEAL)
        canv.circle(W/2, 32, 1.5, fill=1, stroke=0)

        canv.restoreState()

# ── Helpers de estilos ────────────────────────────────────────────────────────
def P(txt, size=9, bold=False, color=GRAY_TEXT, align=TA_LEFT, leading=13):
    return Paragraph(txt, ParagraphStyle('_',
        fontName='Helvetica-Bold' if bold else 'Helvetica',
        fontSize=size, textColor=color, alignment=align, leading=leading))

def section_header(txt, subtitle=None):
    """Header de sección estilo reporte — fondo teal oscuro"""
    inner = [P(f'<b>{txt}</b>', size=13, color=WHITE, align=TA_CENTER, leading=16)]
    if subtitle:
        inner.append(P(subtitle, size=8.5, color=colors.HexColor('#B5E8E5'), align=TA_CENTER))
    t = Table([[v] for v in inner], colWidths=[W-28*mm])
    t.setStyle(TableStyle([
        ('BACKGROUND',    (0,0),(-1,-1), colors.HexColor('#0D4F5A')),
        ('TOPPADDING',    (0,0),(-1,-1), 10),
        ('BOTTOMPADDING', (0,0),(-1,-1), 10),
        ('LEFTPADDING',   (0,0),(-1,-1), 14),
    ]))
    return t

def teal_row(cells, colws, header=False):
    bg = TEAL if header else TEAL_LIGHT
    tc = WHITE if header else DARK_BLUE
    fn = 'Helvetica-Bold'
    row_data = [P(f'<b>{c}</b>', size=9, color=tc) if header
                else P(str(c), size=9, color=GRAY_TEXT) for c in cells]
    t = Table([row_data], colWidths=colws)
    t.setStyle(TableStyle([
        ('BACKGROUND',    (0,0),(-1,-1), bg),
        ('TOPPADDING',    (0,0),(-1,-1), 7),
        ('BOTTOMPADDING', (0,0),(-1,-1), 7),
        ('LEFTPADDING',   (0,0),(-1,-1), 10),
        ('RIGHTPADDING',  (0,0),(-1,-1), 10),
        ('LINEBELOW',     (0,0),(-1,-1), 0.5, SEPARATOR),
    ]))
    return t

def sim_table_full(r, uf):
    """Tabla simulación estilo Loans4B — DESGLOSE / % / PESOS / UF"""
    vf = r['valor_financiado']
    rows_data = [
        # label, pct, pesos, uf — header
        ('DESGLOSE', 'PORCENTAJE', 'PESOS', 'UF', 'hdr'),
        # destacados
        ('Valor Tasación Comercial', '', fmtc(r['val_comercial']), fmtuf(r['val_comercial']/uf), 'teal'),
        ('Plazo Operación', '', f"{r['plazo']} Meses", '', 'normal'),
        ('Valor Compraventa', fmtpm(r['pct_fin']*100), fmtc(vf), fmtuf(vf/uf), 'teal'),
        ('Tasa Renta Mensual', '', fmtpm(r['tasa_m']*100), '', 'normal'),
        ('Tasa Renta Anual', '', fmtpm(r['tasa_anual']*100), '', 'normal'),
        # separador negro
        ('', '', '', '', 'sep'),
        ('Desglose (Giro bruto)', '', fmtc(vf), fmtuf(vf/uf), 'normal'),
        ('Prepago de Renta', '', fmtc(r['interes_anio1']), '', 'normal'),
        (f'Gastos Operativos + CBR/Notaría\n{fmtc(r["gastos_oper"])} + {fmtc(r["cbr"])}', fmtpm(r['pct_gastos']*100), fmtc(r['gastos_oper'] + r['cbr']), '', 'normal_sub'),
        ('Estructuración Financiera', fmtpm(r['pct_fee']*100), fmtc(r['fee_estruct']), '', 'normal'),
        ('Acreedor / Deuda actual', '', fmtc(r['acreedor']), '', 'normal'),
        ('Gastos Operacionales Totales', '', fmtc(r['descuentos']), fmtuf(r['descuentos']/uf), 'teal_bottom'),
        ('Capital Entregado al Deudor', '', fmtc(r['monto_liquido']), fmtuf(r['monto_liquido']/uf), 'teal_bottom'),
        ('Valor Recompra Deudor', '', fmtc(r['valor_recompra']), fmtuf(r['valor_recompra']/uf), 'teal_bottom'),
    ]

    CW = [(W-28*mm)*v for v in [0.42, 0.17, 0.26, 0.15]]
    table_rows = []
    ts_cmds = []
    row_idx = 0

    for row in rows_data:
        *cells, kind = row
        if kind == 'hdr':
            table_rows.append([P(f'<b>{c}</b>', size=8.5, color=WHITE, align=TA_CENTER) for c in cells])
            ts_cmds += [('BACKGROUND',(0,row_idx),(-1,row_idx), colors.HexColor('#0D4F5A')),
                        ('TOPPADDING',(0,row_idx),(-1,row_idx), 8),
                        ('BOTTOMPADDING',(0,row_idx),(-1,row_idx), 8)]
        elif kind == 'teal':
            row_cells = [P(f'<b>{cells[0]}</b>', size=9, color=WHITE, bold=True)]
            row_cells += [P(f'<b>{c}</b>', size=9, color=WHITE, align=TA_RIGHT if i>0 else TA_LEFT) for i,c in enumerate(cells[1:])]
            table_rows.append(row_cells)
            ts_cmds += [('BACKGROUND',(0,row_idx),(-1,row_idx), TEAL),
                        ('TOPPADDING',(0,row_idx),(-1,row_idx), 7),
                        ('BOTTOMPADDING',(0,row_idx),(-1,row_idx), 7)]
        elif kind == 'teal_bottom':
            row_cells = [P(f'<b>{cells[0]}</b>', size=9, color=WHITE)]
            row_cells += [P(f'<b>{c}</b>', size=9, color=WHITE, align=TA_RIGHT if i>0 else TA_LEFT) for i,c in enumerate(cells[1:])]
            table_rows.append(row_cells)
            ts_cmds += [('BACKGROUND',(0,row_idx),(-1,row_idx), TEAL),
                        ('TOPPADDING',(0,row_idx),(-1,row_idx), 7),
                        ('BOTTOMPADDING',(0,row_idx),(-1,row_idx), 7)]
        elif kind == 'sep':
            table_rows.append([P('') for _ in range(4)])
            ts_cmds += [('BACKGROUND',(0,row_idx),(-1,row_idx), BLACK),
                        ('TOPPADDING',(0,row_idx),(-1,row_idx), 3),
                        ('BOTTOMPADDING',(0,row_idx),(-1,row_idx), 3)]
        elif kind == 'normal_sub':
            parts = cells[0].split('\n')
            lbl_main = parts[0]
            lbl_sub  = parts[1] if len(parts) > 1 else ''
            lbl_para = Paragraph(
                f'{lbl_main}<br/><font size="7" color="#8B9BAD"><i>{lbl_sub}</i></font>',
                ParagraphStyle('_sub', fontName='Helvetica', fontSize=9,
                               textColor=GRAY_TEXT, alignment=TA_LEFT, leading=13)
            )
            row_cells = [lbl_para]
            row_cells += [P(c, size=9, color=GRAY_TEXT, align=TA_RIGHT if i>0 else TA_LEFT) for i,c in enumerate(cells[1:])]
            table_rows.append(row_cells)
            bg = GRAY_LIGHT if row_idx%2==0 else WHITE
            ts_cmds += [('BACKGROUND',(0,row_idx),(-1,row_idx), bg),
                        ('TOPPADDING',(0,row_idx),(-1,row_idx), 5),
                        ('BOTTOMPADDING',(0,row_idx),(-1,row_idx), 5)]
        else:
            row_cells = [P(cells[0], size=9, color=GRAY_TEXT)]
            row_cells += [P(c, size=9, color=GRAY_TEXT, align=TA_RIGHT if i>0 else TA_LEFT) for i,c in enumerate(cells[1:])]
            table_rows.append(row_cells)
            bg = GRAY_LIGHT if row_idx%2==0 else WHITE
            ts_cmds += [('BACKGROUND',(0,row_idx),(-1,row_idx), bg),
                        ('TOPPADDING',(0,row_idx),(-1,row_idx), 6),
                        ('BOTTOMPADDING',(0,row_idx),(-1,row_idx), 6)]
        row_idx += 1

    ts_cmds += [
        ('LEFTPADDING',  (0,0),(-1,-1), 10),
        ('RIGHTPADDING', (0,0),(-1,-1), 10),
        ('LINEBELOW',    (0,0),(-1,-2), 0.3, SEPARATOR),
        ('ALIGN',        (1,0),(-1,-1), 'RIGHT'),
        ('ALIGN',        (0,0),(0,-1),  'LEFT'),
    ]
    t = Table(table_rows, colWidths=CW)
    t.setStyle(TableStyle(ts_cmds))
    return t

def metric_card_row(items):
    """items = [(valor_grande, label_abajo, color_acento)]"""
    n = len(items)
    cw = (W-28*mm)/n
    r1 = [P(f'<b>{v}</b>', size=20, color=colors.HexColor(c), align=TA_CENTER, leading=24) for v,_,c in items]
    r2 = [P(l, size=7.5, color=GRAY_MID, align=TA_CENTER) for _,l,_ in items]
    t = Table([r1, r2], colWidths=[cw]*n)
    t.setStyle(TableStyle([
        ('BACKGROUND',    (0,0),(-1,-1), WHITE),
        ('TOPPADDING',    (0,0),(-1,0),  12),
        ('BOTTOMPADDING', (0,0),(-1,-1), 10),
        ('LINEAFTER',     (0,0),(-2,-1), 0.5, SEPARATOR),
        ('BOX',           (0,0),(-1,-1), 1,   TEAL),
        ('LINEABOVE',     (0,0),(-1,0),  3,   TEAL),
    ]))
    return t

def analista_footer(analista, mes_anio):
    data = [[
        P(f'<b>Mes y año</b>', size=8, color=WHITE),
        P(mes_anio, size=9, color=WHITE),
        Spacer(1,1),
        P(f'<b>Analista a Cargo</b>', size=8, color=WHITE),
        P(analista, size=9, color=WHITE),
    ]]
    cw = [(W-28*mm)*v for v in [0.15, 0.25, 0.10, 0.22, 0.28]]
    t  = Table(data, colWidths=cw)
    t.setStyle(TableStyle([
        ('BACKGROUND',    (0,0),(1,0),  TEAL),
        ('BACKGROUND',    (2,0),(2,0),  WHITE),
        ('BACKGROUND',    (3,0),(4,0),  DARK_BLUE),
        ('TOPPADDING',    (0,0),(-1,-1), 8),
        ('BOTTOMPADDING', (0,0),(-1,-1), 8),
        ('LEFTPADDING',   (0,0),(-1,-1), 10),
        ('RIGHTPADDING',  (0,0),(-1,-1), 10),
        ('ROUNDEDCORNERS', [6,6,6,6]),
    ]))
    return t

# ── GENERADOR PRINCIPAL ───────────────────────────────────────────────────────
def generate_pdf(data, output_path, logo_path):
    r     = calcular(data)
    d     = data
    fecha = datetime.now().strftime('%d de %B de %Y').replace(
        'January','enero').replace('February','febrero').replace('March','marzo').replace(
        'April','abril').replace('May','mayo').replace('June','junio').replace(
        'July','julio').replace('August','agosto').replace('September','septiembre').replace(
        'October','octubre').replace('November','noviembre').replace('December','diciembre')
    mes_anio = datetime.now().strftime('%B %Y').replace(
        'January','Enero').replace('February','Febrero').replace('March','Marzo').replace(
        'April','Abril').replace('May','Mayo').replace('June','Junio').replace(
        'July','Julio').replace('August','Agosto').replace('September','Septiembre').replace(
        'October','Octubre').replace('November','Noviembre').replace('December','Diciembre')

    cli      = d.get('nombre_cliente','Cliente')
    rut      = d.get('rut','-')
    analista = d.get('analista','Karl Brunner Z.')
    uf       = r['uf_clp']

    cover_cb = CoverPage(logo_path, cli, rut, fecha)
    hf_cb    = HF(logo_path, cli, fecha)

    doc = SimpleDocTemplate(output_path, pagesize=A4,
                            leftMargin=14*mm, rightMargin=14*mm,
                            topMargin=54, bottomMargin=32)
    SP  = lambda n=6: Spacer(1, n)
    story = []

    # ══ PORTADA (página en blanco para que el callback la dibuje) ══════════════
    story.append(Spacer(1, H-100))
    story.append(PageBreak())

    # ══ PÁGINA 1: Resumen ejecutivo Loans4B ═══════════════════════════════════
    # AW = ancho disponible exacto (515.9pt). Todas las tablas usan AW directamente.
    AW = W - 28*mm   # 515.9 pt

    # ── Tarjeta de bienvenida ──────────────────────────────────────────────────
    cover_l4b = Table([[
        P('<b>Just Loans 4 Business</b>', size=14, bold=True, color=WHITE, align=TA_LEFT),
        P('<b>loans4b.com</b>', size=10, bold=True, color=GREEN, align=TA_RIGHT)
    ]], colWidths=[AW*0.65, AW*0.35])
    cover_l4b.setStyle(TableStyle([
        ('BACKGROUND',    (0,0),(-1,-1), BLUE),
        ('TOPPADDING',    (0,0),(-1,-1), 10), ('BOTTOMPADDING',(0,0),(-1,-1),10),
        ('LEFTPADDING',   (0,0),(-1,-1), 12), ('RIGHTPADDING', (0,0),(-1,-1),12),
        ('LINEBELOW',     (0,0),(-1,-1), 3, GREEN),
    ]))
    story += [cover_l4b, SP(5)]

    # ── Quiénes somos ─────────────────────────────────────────────────────────
    story += [section_header('Quiénes somos'), SP(4)]
    quien = Table([[P(
        'En <b>Just Loans 4 Business</b> llevamos más de <b>15 años estructurando financiamiento '
        'internacional</b> para empresas de Latinoamérica. Hemos acompañado a más de <b>800 empresas</b> '
        'en exportaciones, créditos comerciales y proyectos inmobiliarios, conectándolas con '
        'los principales fondos de deuda privada de Estados Unidos.',
        size=8.5, color=GRAY_TEXT, leading=12, align=TA_JUSTIFY
    )]], colWidths=[AW])
    quien.setStyle(TableStyle([
        ('LEFTPADDING',(0,0),(-1,-1),0),('RIGHTPADDING',(0,0),(-1,-1),0),
        ('TOPPADDING',(0,0),(-1,-1),0),('BOTTOMPADDING',(0,0),(-1,-1),0),
    ]))
    story += [quien, SP(5)]

    # ── Nuestros servicios — 4 tarjetas ───────────────────────────────────────
    story += [section_header('Nuestros servicios'), SP(4)]

    GAP = 5   # espacio entre tarjetas
    CW_SRV = (AW - 3*GAP) / 4   # 124.7pt por tarjeta — ancho exacto

    def srv_card(titulo, desc, color_hex):
        inner_w = CW_SRV - 16   # descontar padding 8+8
        t = Table([
            [P(f'<b>{titulo}</b>', size=8, bold=True,
               color=colors.HexColor(color_hex), leading=10)],
            [SP(2)],
            [P(desc, size=7.5, color=GRAY_TEXT, leading=10)],
        ], colWidths=[inner_w])
        wrap = Table([[t]], colWidths=[CW_SRV])
        wrap.setStyle(TableStyle([
            ('BACKGROUND',    (0,0),(-1,-1), LIGHT_BG),
            ('BOX',           (0,0),(-1,-1), 0.5, SEPARATOR),
            ('TOPPADDING',    (0,0),(-1,-1), 7),
            ('BOTTOMPADDING', (0,0),(-1,-1), 7),
            ('LEFTPADDING',   (0,0),(-1,-1), 8),
            ('RIGHTPADDING',  (0,0),(-1,-1), 8),
            ('LINEABOVE',     (0,0),(-1,0),  3, colors.HexColor(color_hex)),
        ]))
        return wrap

    srv_row = Table([[
        srv_card('Factoring Internacional',
                 'Liquidez inmediata para exportadores. Capital fresco en 24 hrs sin endeudarte.',
                 '#0D5EA6'),
        Spacer(GAP, 1),
        srv_card('Créditos Comerciales',
                 'Financiamiento internacional. Créditos desde USD 3MM hasta USD 50MM.',
                 '#2ECC8F'),
        Spacer(GAP, 1),
        srv_card('Leaseback Inmobiliario',
                 'Obtén liquidez con tu propiedad. Arriéndala y recomprala al final del plazo.',
                 '#1BA8A0'),
        Spacer(GAP, 1),
        srv_card('LLC & Bancarización EE.UU.',
                 'Empresa en EE.UU. y cuenta bancaria internacional en dólares.',
                 '#7B5EA7'),
    ]], colWidths=[CW_SRV, GAP, CW_SRV, GAP, CW_SRV, GAP, CW_SRV])
    srv_row.setStyle(TableStyle([
        ('LEFTPADDING',(0,0),(-1,-1),0),('RIGHTPADDING',(0,0),(-1,-1),0),
        ('TOPPADDING',(0,0),(-1,-1),0),('BOTTOMPADDING',(0,0),(-1,-1),0),
        ('VALIGN',(0,0),(-1,-1),'TOP'),
    ]))
    story += [srv_row, SP(5)]

    # ── Por qué elegirnos — 3 métricas ────────────────────────────────────────
    story += [section_header('Por qué elegirnos'), SP(4)]
    CW_MET = AW / 3
    met_r1 = [P(f'<b>{v}</b>', size=18, color=colors.HexColor(c),
                align=TA_CENTER, leading=22)
              for v, _, c in [('+15 años','','#0D5EA6'),('+800','','#2ECC8F'),('+ USD 2B','','#7B5EA7')]]
    met_r2 = [P(l, size=7.5, color=GRAY_MID, align=TA_CENTER)
              for l in ['Años de experiencia', 'Empresas atendidas', 'En levantamiento de capital']]
    met_t = Table([met_r1, met_r2], colWidths=[CW_MET, CW_MET, CW_MET])
    met_t.setStyle(TableStyle([
        ('BACKGROUND',    (0,0),(-1,-1), WHITE),
        ('TOPPADDING',    (0,0),(-1,0),  10), ('BOTTOMPADDING',(0,0),(-1,-1),8),
        ('LINEAFTER',     (0,0),(-2,-1), 0.5, SEPARATOR),
        ('BOX',           (0,0),(-1,-1), 1, TEAL),
        ('LINEABOVE',     (0,0),(-1,0),  3, TEAL),
        ('LEFTPADDING',   (0,0),(-1,-1), 0),
        ('RIGHTPADDING',  (0,0),(-1,-1), 0),
    ]))
    story += [met_t, SP(5)]

    # ── Leaseback — texto e izquierda, beneficios a la derecha ────────────────
    story += [section_header('¿Qué es un Leaseback Inmobiliario?'), SP(4)]

    CW_L = AW * 0.40          # columna texto: 206pt
    CW_R = AW - CW_L - 8      # columna beneficios: 302pt
    CW_BL = CW_R * 0.40       # label beneficio
    CW_BR = CW_R * 0.60       # desc beneficio

    lease_txt = Table([[P(
        'El <b>leaseback</b> es una operación en la que el propietario '
        '<b>vende el inmueble a un inversionista</b> y lo arrienda de vuelta, '
        'manteniendo el uso. Al final del plazo puede '
        '<b>recomprar la propiedad</b> al valor acordado.',
        size=8.5, color=GRAY_TEXT, leading=12, align=TA_JUSTIFY
    )]], colWidths=[CW_L])
    lease_txt.setStyle(TableStyle([
        ('LEFTPADDING',(0,0),(-1,-1),0),('RIGHTPADDING',(0,0),(-1,-1),0),
        ('TOPPADDING',(0,0),(-1,-1),0),('BOTTOMPADDING',(0,0),(-1,-1),0),
    ]))

    benef_rows = [
        ['Liquidez inmediata',   'Capital sin vender definitivamente.'],
        ['Sin pérdida de uso',   'Sigues operando en el mismo inmueble.'],
        ['Mejora el balance',    'Activo fijo convertido en liquidez.'],
        ['Recompra garantizada', 'Recupera tu propiedad al vencimiento.'],
    ]
    ben_data = [[
        P(f'<b>{b[0]}</b>', size=8, bold=True, color=DARK_BLUE),
        P(b[1], size=8, color=GRAY_TEXT)
    ] for b in benef_rows]
    ben_t = Table(ben_data, colWidths=[CW_BL, CW_BR])
    ben_t.setStyle(TableStyle([
        ('ROWBACKGROUNDS', (0,0),(-1,-1), [LIGHT_ROW, LIGHT_BG]),
        ('TOPPADDING',     (0,0),(-1,-1), 4), ('BOTTOMPADDING',(0,0),(-1,-1),4),
        ('LEFTPADDING',    (0,0),(-1,-1), 8), ('RIGHTPADDING', (0,0),(-1,-1),6),
        ('LINEBELOW',      (0,0),(-1,-2), 0.3, SEPARATOR),
        ('LINEBEFORE',     (0,0),(0,-1),  3, GREEN),
    ]))

    two_col = Table([[lease_txt, Spacer(8,1), ben_t]],
                    colWidths=[CW_L, 8, CW_R])
    two_col.setStyle(TableStyle([
        ('VALIGN',(0,0),(-1,-1),'TOP'),
        ('LEFTPADDING',(0,0),(-1,-1),0),('RIGHTPADDING',(0,0),(-1,-1),0),
        ('TOPPADDING',(0,0),(-1,-1),0),('BOTTOMPADDING',(0,0),(-1,-1),0),
    ]))
    story += [two_col, SP(6)]

    # ── Barra de contacto ─────────────────────────────────────────────────────
    CW_C = [AW*0.12, AW*0.40, AW*0.22, AW*0.26]  # suma exacta = AW
    contact_data = [[
        P('<b>Contacto</b>', size=8, bold=True, color=WHITE),
        P('Av. La Dehesa 1500, piso 4, Lo Barnechea, Santiago', size=8,
          color=colors.HexColor('#B5D4F4')),
        P('+56 9 8270 1655', size=8, color=colors.HexColor('#B5D4F4')),
        P('Info@loans4b.com', size=8, color=GREEN),
    ]]
    ct = Table(contact_data, colWidths=CW_C)
    ct.setStyle(TableStyle([
        ('BACKGROUND',    (0,0),(-1,-1), DARK_BLUE),
        ('TOPPADDING',    (0,0),(-1,-1), 8), ('BOTTOMPADDING',(0,0),(-1,-1),8),
        ('LEFTPADDING',   (0,0),(-1,-1), 8), ('RIGHTPADDING', (0,0),(-1,-1),8),
        ('LINEABOVE',     (0,0),(-1,0),  2, GREEN),
        ('VALIGN',        (0,0),(-1,-1), 'MIDDLE'),
    ]))
    story += [ct, PageBreak()]

    # ══ PÁGINA 2: Avalúo Fiscal ════════════════════════════════════════════════
    story += [section_header('CERTIFICADO DE AVALÚO FISCAL',
                              'Avalúos en pesos del PRIMER SEMESTRE DE 2026'), SP(10)]

    # Tabla avalúo estilo SII
    av_data = [
        [P('<b>DESGLOSE</b>', size=8.5, color=WHITE, align=TA_CENTER),
         P('<b>VALOR</b>', size=8.5, color=WHITE, align=TA_CENTER)],
        [P('Comuna', size=9, color=GRAY_TEXT), P(d.get('comuna','-'), size=9, color=DARK_BLUE, align=TA_RIGHT)],
        [P('Número de Rol de Avalúo', size=9, color=GRAY_TEXT), P(d.get('rol','-'), size=9, color=DARK_BLUE, align=TA_RIGHT)],
        [P('Dirección o Nombre del bien raíz', size=9, color=GRAY_TEXT), P(d.get('direccion','-'), size=9, color=DARK_BLUE, align=TA_RIGHT)],
        [P('Destino del bien raíz', size=9, color=GRAY_TEXT), P(d.get('destino','-'), size=9, color=DARK_BLUE, align=TA_RIGHT)],
        [P('Período del avalúo', size=9, color=GRAY_TEXT), P(d.get('periodo_avaluo','1er Semestre 2026'), size=9, color=DARK_BLUE, align=TA_RIGHT)],
        [P('Fecha de emisión', size=9, color=GRAY_TEXT), P(d.get('fecha_avaluo', fecha), size=9, color=DARK_BLUE, align=TA_RIGHT)],
    ]
    av_ts = [
        ('BACKGROUND', (0,0),(-1,0),  colors.HexColor('#0D4F5A')),
        ('TOPPADDING',    (0,0),(-1,-1), 7), ('BOTTOMPADDING',(0,0),(-1,-1),7),
        ('LEFTPADDING',   (0,0),(-1,-1), 12),('RIGHTPADDING', (0,0),(-1,-1),12),
        ('LINEBELOW',     (0,0),(-1,-2), 0.3, SEPARATOR),
        ('ROWBACKGROUNDS',(0,1),(-1,-1), [WHITE, GRAY_LIGHT]),
    ]
    av_t = Table(av_data, colWidths=[(W-28*mm)*0.6,(W-28*mm)*0.4])
    av_t.setStyle(TableStyle(av_ts))
    story += [av_t, SP(10)]

    # Valores avalúo
    av2_data = [
        [P('<b>AVALÚO TOTAL</b>', size=9, color=WHITE),
         P('$', size=9, color=WHITE, align=TA_CENTER),
         P(f'<b>{fmtc(d.get("avaluo_fiscal_clp",0))}</b>', size=11, color=GREEN, align=TA_RIGHT)],
        [P('AVALÚO EXENTO DE IMPUESTO', size=9, color=colors.HexColor('#B5E8E5')),
         P('$', size=9, color=colors.HexColor('#B5E8E5'), align=TA_CENTER),
         P(fmtc(d.get('avaluo_exento_clp',0)), size=9, color=colors.HexColor('#B5E8E5'), align=TA_RIGHT)],
        [P('AVALÚO AFECTO A IMPUESTO', size=9, color=colors.HexColor('#B5E8E5')),
         P('$', size=9, color=colors.HexColor('#B5E8E5'), align=TA_CENTER),
         P(fmtc(d.get('avaluo_afecto_clp',0)), size=9, color=colors.HexColor('#B5E8E5'), align=TA_RIGHT)],
    ]
    av2_t = Table(av2_data, colWidths=[(W-28*mm)*0.55,(W-28*mm)*0.08,(W-28*mm)*0.37])
    av2_t.setStyle(TableStyle([
        ('BACKGROUND',    (0,0),(-1,-1), colors.HexColor('#0D4F5A')),
        ('TOPPADDING',    (0,0),(-1,-1), 8), ('BOTTOMPADDING',(0,0),(-1,-1),8),
        ('LEFTPADDING',   (0,0),(-1,-1), 12),('RIGHTPADDING', (0,0),(-1,-1),12),
        ('LINEBELOW',     (0,0),(-1,-2), 0.5, TEAL),
    ]))
    story += [av2_t, SP(12)]

    # Nota SII
    story.append(P(
        '<i>NOTA IMPORTANTE: El avalúo que se indica ha sido determinado según el procedimiento de '
        'tasación fiscal para el cálculo del Impuesto Territorial, de acuerdo a la legislación '
        'vigente, y por tanto no corresponde a una tasación comercial de la propiedad.</i>',
        size=8, color=GRAY_MID, leading=12, align=TA_JUSTIFY
    ))
    story += [SP(16)]

    # Valor comercial estimado
    vc_t = Table([[
        P('<b>Valor comercial estimado</b>', size=9, color=DARK_BLUE),
        P(f'<b>{fmtc(d["val_comercial"])}</b>', size=13, color=TEAL, align=TA_RIGHT)
    ]], colWidths=[(W-28*mm)*0.6,(W-28*mm)*0.4])
    vc_t.setStyle(TableStyle([
        ('BACKGROUND',    (0,0),(-1,-1), TEAL_LIGHT),
        ('TOPPADDING',    (0,0),(-1,-1), 10), ('BOTTOMPADDING',(0,0),(-1,-1),10),
        ('LEFTPADDING',   (0,0),(-1,-1), 14), ('RIGHTPADDING', (0,0),(-1,-1),14),
        ('BOX',           (0,0),(-1,-1), 1, TEAL),
        ('LINEABOVE',     (0,0),(-1,0), 3, TEAL),
    ]))
    story += [vc_t, SP(10), analista_footer(analista, mes_anio), PageBreak()]

    # ══ PÁGINA 2: Simulación ══════════════════════════════════════════════════
    story += [section_header('SIMULACIÓN DE LEASEBACK INMOBILIARIO'), SP(10)]
    story += [sim_table_full(r, uf), SP(14)]

    story += [SP(6), PageBreak()]

    # ══ PÁGINA 3: Análisis Financiero ════════════════════════════════════════
    story += [section_header('ANÁLISIS FINANCIERO', 'Just Loans 4 Business'), SP(8)]

    story.append(P(
        'El siguiente análisis financiero detalla minuciosamente las condiciones y cláusulas '
        'específicas a las que queda sujeto el préstamo de capital para el solicitante, '
        'desglosando de manera técnica la estructura de los intereses del crédito, así como '
        'las tasas aplicables y los costos financieros totales derivados de la operación '
        'crediticia propuesta.',
        size=8.5, color=GRAY_TEXT, leading=13, align=TA_JUSTIFY
    ))
    story += [SP(12)]

    # Métricas clave — fuente reducida para montos CLP largos
    _mit = [
        (fmtc(r['monto_liquido']),  'Capital entregado al deudor', '#1BA8A0', 12),
        (fmtc(r['valor_recompra']), 'Valor recompra',              '#0D5EA6', 12),
        (fmtpm(r['tasa_m']*100),    'Tasa de interés mensual',     '#2ECC8F', 20),
        (f"{r['plazo']} M",         'Plazo del crédito',           '#0A2A4A', 20),
    ]
    _n = len(_mit); _cw = (W-28*mm)/_n
    _r1 = [P(f'<b>{v}</b>', size=s, color=colors.HexColor(c),
             align=TA_CENTER, leading=s+4) for v,_,c,s in _mit]
    _r2 = [P(l, size=7.5, color=GRAY_MID, align=TA_CENTER) for _,l,_,_ in _mit]
    _mt = Table([_r1, _r2], colWidths=[_cw]*_n)
    _mt.setStyle(TableStyle([
        ('BACKGROUND',    (0,0),(-1,-1), WHITE),
        ('TOPPADDING',    (0,0),(-1,0),  12),
        ('BOTTOMPADDING', (0,0),(-1,-1), 10),
        ('LINEAFTER',     (0,0),(-2,-1), 0.5, SEPARATOR),
        ('BOX',           (0,0),(-1,-1), 1, TEAL),
        ('LINEABOVE',     (0,0),(-1,0),  3, TEAL),
    ]))
    story.append(_mt)
    story += [SP(12)]

    # Dos tarjetas info
    box1 = Table([[
        P('<b>Tasación de Activos Tangibles</b>', size=9.5, color=DARK_BLUE, bold=True),
    ],[
        P(f'Tasación comercial total: <b>{fmtc(r["val_comercial"])}</b>', size=8.5, color=GRAY_TEXT),
    ],[
        P(f'Porcentaje de compraventa: <b>{fmtpm(r["pct_fin"]*100)}</b>', size=8.5, color=GRAY_TEXT),
    ],[
        P(f'Plazo aprobado: <b>{r["plazo"]} meses</b>', size=8.5, color=GRAY_TEXT),
    ]], colWidths=[(W-28*mm)*0.5 - 8])
    box1.setStyle(TableStyle([
        ('BOX',(0,0),(-1,-1),1,TEAL),
        ('TOPPADDING',(0,0),(-1,-1),6),('BOTTOMPADDING',(0,0),(-1,-1),6),
        ('LEFTPADDING',(0,0),(-1,-1),12),('RIGHTPADDING',(0,0),(-1,-1),12),
    ]))

    box2_data = [
        ['Capital',        fmtc(r['monto_liquido'])],
        ['Recompra',       fmtc(r['valor_recompra'])],
        ['Tasa interés',   fmtpm(r['tasa_m']*100)],
        ['Valor UF',       f"${uf:,.2f}".replace(',','.')],
    ]
    box2_rows = [[P(l, size=8.5, color=GRAY_TEXT), P(f'<b>{v}</b>', size=8.5, color=DARK_BLUE, align=TA_RIGHT)] for l,v in box2_data]
    box2_rows.insert(0,[P('<b>Riesgo crediticio con los clientes</b>', size=9.5, color=DARK_BLUE), P('')])
    box2 = Table(box2_rows, colWidths=[(W-28*mm)*0.25, (W-28*mm)*0.25])
    box2.setStyle(TableStyle([
        ('BOX',(0,0),(-1,-1),1,TEAL),
        ('TOPPADDING',(0,0),(-1,-1),6),('BOTTOMPADDING',(0,0),(-1,-1),6),
        ('LEFTPADDING',(0,0),(-1,-1),12),('RIGHTPADDING',(0,0),(-1,-1),12),
        ('SPAN',(0,0),(-1,0)),
        ('LINEBELOW',(0,1),(-1,-2),0.3,SEPARATOR),
        ('ROWBACKGROUNDS',(0,1),(-1,-1),[WHITE,GRAY_LIGHT]),
    ]))

    boxes = Table([[box1, Spacer(16,1), box2]], colWidths=[(W-28*mm)*0.5, 16, (W-28*mm)*0.5])
    boxes.setStyle(TableStyle([
        ('VALIGN',(0,0),(-1,-1),'TOP'),
        ('LEFTPADDING',(0,0),(-1,-1),0),('RIGHTPADDING',(0,0),(-1,-1),0),
    ]))
    story += [boxes, SP(12)]

    # KPIs laterales — ancho completo, 3 tarjetas
    kpi_items = [
        ('1',                        'Activos en operación',  '#0D4F5A'),
        (fmtpm(r['tasa_anual']*100), 'Interés anual',         '#0D4F5A'),
        (f"{r['plazo']} meses",      'Plazo del crédito',     '#0D4F5A'),
    ]
    kpi_cw = (W-28*mm)/3 - 6
    kpi_cells = []
    for val, lbl, bg in kpi_items:
        sub = Table([
            [P(f'<b>{val}</b>', size=16, color=WHITE, align=TA_CENTER, leading=20)],
            [P(lbl, size=8, color=colors.HexColor('#B5E8E5'), align=TA_CENTER)],
        ], colWidths=[kpi_cw])
        sub.setStyle(TableStyle([
            ('BACKGROUND',    (0,0),(-1,-1), colors.HexColor(bg)),
            ('TOPPADDING',    (0,0),(-1,-1), 8),
            ('BOTTOMPADDING', (0,0),(-1,-1), 8),
            ('LEFTPADDING',   (0,0),(-1,-1), 6),
            ('RIGHTPADDING',  (0,0),(-1,-1), 6),
        ]))
        kpi_cells.append(sub)

    kpi = Table([[kpi_cells[0], Spacer(8,1), kpi_cells[1], Spacer(8,1), kpi_cells[2]]],
                colWidths=[kpi_cw, 8, kpi_cw, 8, kpi_cw])
    kpi.setStyle(TableStyle([
        ('LEFTPADDING',(0,0),(-1,-1),0),('RIGHTPADDING',(0,0),(-1,-1),0),
        ('TOPPADDING',(0,0),(-1,-1),0),('BOTTOMPADDING',(0,0),(-1,-1),0),
        ('VALIGN',(0,0),(-1,-1),'MIDDLE'),
    ]))
    story += [kpi, SP(10), analista_footer(analista, mes_anio), SP(16)]

    # ══ NOTA LEGAL ════════════════════════════════════════════════════════════
    nota_legal = [
        P('<b>Condiciones y vigencia de la presente simulación</b>',
          size=9, bold=True, color=DARK_BLUE, leading=13),
        SP(6),
        P(
            'Esta simulación tiene una vigencia de <b>cinco días hábiles</b> y está condicionada al '
            'cumplimiento de las siguientes exigencias:',
            size=8, color=GRAY_TEXT, leading=12, align=TA_JUSTIFY
        ),
        SP(5),
    ]

    condiciones = [
        ('<b>(1)</b>', 'Que el valor de tasación encargado sea igual o superior al valor estimado indicado en esta simulación.'),
        ('<b>(2)</b>', 'Que la evaluación de riesgo resulte positiva, a exclusivo criterio y satisfacción de L4B.'),
        ('<b>(3)</b>', 'Que se prepare, otorgue y suscriba, a satisfacción de L4B, toda la documentación habitual para este tipo de transacciones, incluyendo: (i) Títulos conformes a Derecho; (ii) Contrato de arrendamiento; (iii) Escritura de compraventa; y (iv) Cualquier otra documentación o antecedente que L4B estime necesario.'),
        ('<b>(4)</b>', 'Que el cliente manifieste su aprobación de esta simulación mediante comunicación escrita dirigida a L4B, para efectos de continuar con el proceso de evaluación.'),
    ]

    for num, cond in condiciones:
        row = Table([[P(num, size=8, bold=True, color=DARK_BLUE),
                      P(cond, size=8, color=GRAY_TEXT, leading=12, align=TA_JUSTIFY)]],
                    colWidths=[18, W-28*mm-18])
        row.setStyle(TableStyle([
            ('TOPPADDING',(0,0),(-1,-1),3),('BOTTOMPADDING',(0,0),(-1,-1),3),
            ('LEFTPADDING',(0,0),(-1,-1),0),('RIGHTPADDING',(0,0),(-1,-1),0),
            ('VALIGN',(0,0),(-1,-1),'TOP'),
        ]))
        nota_legal.append(row)

    nota_legal += [
        SP(8),
        P(
            'En consecuencia, esta propuesta es de <b>carácter no vinculante</b> y no constituye '
            'compromiso ni obligación alguna para L4B de materializar la(s) respectiva(s) operación(es). '
            'L4B se reserva el derecho de modificarla, complementarla o dejarla sin efecto, a su sola '
            'discreción, sin expresión de causa y en cualquier momento durante el proceso.',
            size=8, color=GRAY_TEXT, leading=12, align=TA_JUSTIFY
        ),
        SP(8),
        P(
            'Los gastos de tasación, notariales y de inscripción en el Conservador de Bienes Raíces '
            'serán de <b>cargo exclusivo del cliente</b>.',
            size=8, color=GRAY_TEXT, leading=12, align=TA_JUSTIFY
        ),
        SP(5),
        P(
            'Los gastos de estudios legales deberán ser provisionados por el cliente previamente a su '
            'realización, y serán reembolsados únicamente contra la materialización efectiva de la(s) '
            'respectiva(s) compraventa(s). En caso de no producirse dicha materialización, por '
            'cualquier causa, dichos gastos no serán reembolsados.',
            size=8, color=GRAY_TEXT, leading=12, align=TA_JUSTIFY
        ),
        SP(10),
        P(
            '<b>(*)</b> La(s) base(s) imponible(s) aplicable(s) a la(s) compraventa(s), rentas de '
            'arrendamiento y/o opción(es) de compra dependerá(n) de las características del(de los) '
            'inmueble(s) y de las condiciones en que fue(ron) adquirido(s), entre otros factores. '
            'Dichas bases serán determinadas en el(los) correspondiente(s) estudio(s) tributario(s).',
            size=7.5, color=GRAY_MID, leading=11, align=TA_JUSTIFY
        ),
    ]

    # Caja con borde para la nota legal
    nota_wrap = Table([[nota_legal[i]] for i in range(len(nota_legal))],
                      colWidths=[W-28*mm])
    # Usar KeepTogether para mantener la nota en una sección
    from reportlab.platypus import KeepTogether
    story.append(KeepTogether(nota_legal))

    # ── Build ─────────────────────────────────────────────────────────────────
    def on_page(canv, doc):
        if doc.page == 1:
            cover_cb(canv, doc)
        elif doc.page == 2:
            pass  # resumen ejecutivo sin header/footer
        else:
            hf_cb(canv, doc)

    doc.build(story, onFirstPage=on_page, onLaterPages=on_page)
    print(f"OK:{output_path}")

if __name__ == '__main__':
    data   = json.loads(sys.argv[1])
    output = sys.argv[2]
    logo   = sys.argv[3] if len(sys.argv)>3 else '/home/claude/logo_clean.png'
    generate_pdf(data, output, logo)
