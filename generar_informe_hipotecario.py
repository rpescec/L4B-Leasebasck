"""
generar_informe_hipotecario.py
Generador de informe PDF para crédito hipotecario — Asesorías Loans4B
Uso: generate_pdf_hipotecario(data, output_path, logo_path)
"""
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.platypus import (BaseDocTemplate, Frame, PageTemplate,
    Paragraph, Spacer, Table, TableStyle, HRFlowable, Image)
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT, TA_JUSTIFY
import datetime, random, math


# ── Colores ────────────────────────────────────────────────────────────────
BLUE       = colors.HexColor('#2B7BB9')
BLUE_DARK  = colors.HexColor('#1A5F9A')
BLUE_LIGHT = colors.HexColor('#EBF4FC')
BLUE_BORDER= colors.HexColor('#2B7BB9')
GREEN      = colors.HexColor('#4DC8A0')
GRAY_BG    = colors.HexColor('#F7FAFC')
GRAY_LINE  = colors.HexColor('#D1E4F4')
GRAY_TEXT  = colors.HexColor('#4A5568')
GRAY_SOFT  = colors.HexColor('#8FA3B8')
WHITE      = colors.white
NEAR_BLACK = colors.HexColor('#1A202C')

PAGE_W, PAGE_H = A4
MARGIN    = 18 * mm
CONTENT_W = PAGE_W - 2 * MARGIN

HDR_TOP    = PAGE_H - 14 * mm
HDR_H      = 92.0
HDR_BOTTOM = HDR_TOP - HDR_H
GAP        = 6 * mm
FRM_TOP    = HDR_BOTTOM - GAP
FRM_BTM    = 22 * mm
FRM_H      = FRM_TOP - FRM_BTM


# ── Helpers ────────────────────────────────────────────────────────────────
def _p(uf, uv):  return '$' + f"{round(uf * uv):,}".replace(',', '.')
def _u(uf):      return f"UF {uf:,.2f}".replace(',', '.')
def _u1(uf):     return f"UF {uf:,.1f}".replace(',', '.')
def _S(name, **kw): return ParagraphStyle(name, **kw)

def _divider():
    return HRFlowable(width='100%', thickness=0.5, color=GRAY_LINE, spaceAfter=4, spaceBefore=2)

def _section(txt):
    return [Spacer(1, 3*mm),
            Paragraph(txt.upper(), _S('Sec', fontSize=8.5, fontName='Helvetica-Bold',
                                      textColor=BLUE, leading=12, spaceBefore=8, spaceAfter=2)),
            _divider()]

def _highlight(lines, bg=BLUE_LIGHT, border=BLUE):
    data = [[Paragraph('<br/>'.join(lines),
                       _S('hb', fontSize=9.5, fontName='Helvetica',
                          textColor=GRAY_TEXT, leading=15))]]
    t = Table(data, colWidths=[CONTENT_W])
    t.setStyle(TableStyle([
        ('BACKGROUND',   (0,0),(-1,-1), bg),
        ('LINEBEFORE',   (0,0),(0,-1),  2.5, border),
        ('TOPPADDING',   (0,0),(-1,-1), 8),
        ('BOTTOMPADDING',(0,0),(-1,-1), 8),
        ('LEFTPADDING',  (0,0),(-1,-1), 10),
        ('RIGHTPADDING', (0,0),(-1,-1), 10),
    ]))
    return t


# ── Header / Footer ────────────────────────────────────────────────────────
def _make_header_cb(logo_path, cot_id, hoy, vigencia, uf_val):
    def draw_header(c, doc):
        # Fondo blanco con borde azul
        c.setFillColor(WHITE)
        c.setStrokeColor(BLUE_BORDER)
        c.setLineWidth(1.2)
        c.roundRect(MARGIN, HDR_BOTTOM, CONTENT_W, HDR_H, 7, fill=1, stroke=1)

        # Franja azul inferior
        c.setFillColor(BLUE)
        c.setLineWidth(0)
        c.rect(MARGIN + 1, HDR_BOTTOM + 1, CONTENT_W - 2, 5, fill=1, stroke=0)

        # Logo
        logo_w = 54 * mm
        logo_h = logo_w * (273 / 765)
        logo_x = MARGIN + 6 * mm
        logo_y = HDR_BOTTOM + 5 + (HDR_H - 5 - logo_h) / 2
        try:
            c.drawImage(logo_path, logo_x, logo_y,
                        width=logo_w, height=logo_h,
                        preserveAspectRatio=True, mask='auto')
        except Exception:
            c.setFont("Helvetica-Bold", 18)
            c.setFillColor(BLUE)
            c.drawString(logo_x, logo_y + 8, "loan$4B.com")

        # Separador vertical
        sep_x = MARGIN + logo_w + 14 * mm
        c.setStrokeColor(GRAY_LINE)
        c.setLineWidth(0.8)
        c.line(sep_x, HDR_BOTTOM + 15, sep_x, HDR_TOP - 10)

        # Bloque derecho
        tx  = sep_x + 8 * mm
        mid = HDR_BOTTOM + 5 + (HDR_H - 5) / 2
        c.setFont("Helvetica-Bold", 13)
        c.setFillColor(BLUE_DARK)
        c.drawString(tx, mid + 22, "Simulacion de Credito Hipotecario")
        c.setFont("Helvetica", 8.5)
        c.setFillColor(GRAY_TEXT)
        c.drawString(tx, mid + 8,  f"ID COT: {cot_id}   \u00b7   Fecha: {hoy}   \u00b7   Vigente hasta: {vigencia}")
        c.drawString(tx, mid - 5,  f"Valor UF referencial: ${uf_val:,}".replace(',', '.'))
        c.setFont("Helvetica-Oblique", 8)
        c.setFillColor(GREEN)
        c.drawString(tx, mid - 18, "Financiamiento simple, rapido y confiable.")

        # Footer
        c.setStrokeColor(GRAY_LINE)
        c.setLineWidth(0.4)
        c.line(MARGIN, 16 * mm, PAGE_W - MARGIN, 16 * mm)
        c.setFont("Helvetica", 7.5)
        c.setFillColor(GRAY_SOFT)
        c.drawCentredString(PAGE_W / 2, 10 * mm,
            "Asesorias Loans4B  \u2022  www.loans4b.com  \u2022  Simulacion con caracter referencial")
    return draw_header


class _L4BDoc(BaseDocTemplate):
    def __init__(self, fname, header_cb, **kw):
        super().__init__(fname, **kw)
        frame = Frame(MARGIN, FRM_BTM, CONTENT_W, FRM_H,
                      leftPadding=0, rightPadding=0,
                      topPadding=4, bottomPadding=0, id='body')
        self.addPageTemplates([
            PageTemplate('main', frames=[frame], onPage=header_cb)
        ])


# ── Función principal ──────────────────────────────────────────────────────
def generate_pdf_hipotecario(data, output_path, logo_path):
    """
    Genera el informe PDF de simulación hipotecaria.

    data: dict con los parámetros de la simulación:
        nombre, rut, asesor, tipo_persona ('n'/'j'),
        vi, pie, plazo, tasa, tipo_tasa,
        subsidio_aplica, subsidio_monto,
        seg_d, seg_i, seg_c,
        hon_pct, uf_val, cot_id (opcional)
    output_path: ruta del PDF a generar
    logo_path: ruta del logo PNG
    """
    # ── Extraer parámetros ─────────────────────────────────────────────────
    UFV       = float(data.get('uf_val', 39908))
    NOMBRE    = data.get('nombre', '[Nombre del Cliente]') or '[Nombre del Cliente]'
    RUT       = data.get('rut', '')
    ASESOR    = data.get('asesor', 'Asesor Loans4B') or 'Asesor Loans4B'
    tipo_raw  = data.get('tipo_persona', 'n')
    TIPO_PERS = 'Juridica' if tipo_raw == 'j' else 'Natural'
    VI        = float(data.get('vi', 4000))
    PIE       = float(data.get('pie', 800))
    SUB       = float(data.get('subsidio_monto', 0)) if data.get('subsidio_aplica') else 0
    MONTO     = max(0.0, VI - PIE - SUB)
    PLAZO     = int(data.get('plazo', 20))
    TASA      = float(data.get('tasa', 4.5))
    TIPO_TASA = data.get('tipo_tasa', 'fija')
    SEG_DEG   = float(data.get('seg_d', 0.90))
    SEG_INC   = float(data.get('seg_i', 0.40))
    SEG_CES   = float(data.get('seg_c', 0.30))
    SEG_TOT   = SEG_DEG + SEG_INC + SEG_CES
    HON_PCT   = float(data.get('hon_pct', 3.0))
    HON_UF    = MONTO * (HON_PCT / 100)
    PRE_EVAL  = 15 if tipo_raw == 'j' else 6
    COT_ID    = data.get('cot_id', random.randint(1000, 9999))

    # ── Cálculos ───────────────────────────────────────────────────────────
    n   = PLAZO * 12
    r   = TASA / 100 / 12
    ci  = MONTO * (r * (1+r)**n) / ((1+r)**n - 1) if r > 0 else (MONTO / n if n > 0 else 0)
    ct  = ci + SEG_TOT
    tot_int = max(0.0, ci * n - MONTO)
    cae = ((1 + r)**12 - 1) * 100

    HOY      = datetime.date.today().strftime('%d/%m/%Y')
    VIGENCIA = (datetime.date.today() + datetime.timedelta(days=5)).strftime('%d/%m/%Y')

    fc  = lambda uf: _p(uf, UFV)
    u   = lambda uf: _u(uf)
    u1  = lambda uf: _u1(uf)

    # ── Estilos ────────────────────────────────────────────────────────────
    ST_GREETING = _S('Gr',  fontSize=11,  fontName='Helvetica-Bold', textColor=NEAR_BLACK, leading=16)
    ST_BODY     = _S('Bd',  fontSize=10,  fontName='Helvetica',      textColor=GRAY_TEXT,  leading=16, alignment=TA_JUSTIFY, spaceBefore=4)
    ST_KV_V     = _S('KVV', fontSize=9,   fontName='Helvetica-Bold', textColor=NEAR_BLACK, leading=13)
    ST_SMALL    = _S('Sm',  fontSize=8.5, fontName='Helvetica',      textColor=GRAY_TEXT,  leading=12)
    ST_DISC     = _S('Dc',  fontSize=7.5, fontName='Helvetica',      textColor=GRAY_SOFT,  leading=11, alignment=TA_JUSTIFY)

    # ── Documento ──────────────────────────────────────────────────────────
    header_cb = _make_header_cb(logo_path, COT_ID, HOY, VIGENCIA, int(UFV))
    doc = _L4BDoc(output_path, header_cb, pagesize=A4,
                  topMargin=0, bottomMargin=FRM_BTM,
                  leftMargin=MARGIN, rightMargin=MARGIN)
    story = []

    # ── Saludo ─────────────────────────────────────────────────────────────
    story.append(Spacer(1, 3*mm))
    greeting = f"Estimado/a: <b>{NOMBRE}</b>"
    if RUT:
        greeting += f" / Rut {RUT}"
    story.append(Paragraph(greeting + ":", ST_GREETING))
    story.append(Spacer(1, 3*mm))

    # ── Cuerpo narrativo ───────────────────────────────────────────────────
    story.append(Paragraph(
        f"Nos complace presentarle esta simulacion referencial de credito hipotecario gestionada por "
        f"<b>ASESORIAS LOANS4B</b>. Tras revisar preliminarmente su perfil financiero como "
        f"<b>Persona {TIPO_PERS}</b>, la entidad financiera podra evaluar un credito equivalente al "
        f"<b>{round((MONTO/VI)*100) if VI > 0 else 0}% del valor total del inmueble</b>, lo que "
        f"representa <b>{u(MONTO)}</b> ({fc(MONTO)}). "
        f"El aporte inicial (pie) asciende a <b>{u(PIE)}</b> ({fc(PIE)}), "
        f"correspondiente al {round((PIE/VI)*100) if VI > 0 else 0}% del valor de la propiedad.",
        ST_BODY))

    if SUB > 0:
        story.append(Paragraph(
            f"El financiamiento contempla ademas un <b>subsidio habitacional de {u(SUB)}</b> "
            f"({fc(SUB)}), el cual se descuenta del monto a financiar.",
            ST_BODY))

    story.append(Paragraph(
        f"El financiamiento se estructura a un plazo de <b>{PLAZO} anos</b>, con una tasa nominal "
        f"anual <b>{TIPO_TASA} del {TASA}%</b> y una Carga Anual Equivalente (CAE) estimada de "
        f"<b>{cae:.2f}%</b>. La cuota mensual total estimada — que ya contempla los seguros "
        f"obligatorios — asciende a <b>{u1(ct)}</b> mensuales ({fc(ct)}).",
        ST_BODY))

    story.append(Spacer(1, 3*mm))

    # ── Cuota destacada ────────────────────────────────────────────────────
    cuota_data = [[
        Paragraph('<font color="#1A5F9A"><b>Cuota mensual estimada</b></font><br/>'
                  '<font size="8" color="#8FA3B8">Capital + interes + seguros</font>',
                  _S('cl', fontSize=9.5, fontName='Helvetica-Bold',
                     textColor=BLUE_DARK, leading=14)),
        Paragraph(f'<font color="#1A5F9A" size="20"><b>{u1(ct)}</b></font>',
                  _S('cv', fontSize=20, fontName='Helvetica-Bold',
                     textColor=BLUE_DARK, leading=24, alignment=TA_CENTER)),
        Paragraph(f'<font color="#2B7BB9"><b>{fc(ct)}</b></font><br/>'
                  f'<font size="8" color="#8FA3B8">al valor UF vigente</font>',
                  _S('cp', fontSize=10, fontName='Helvetica-Bold',
                     textColor=BLUE, leading=14, alignment=TA_RIGHT)),
    ]]
    cb = Table(cuota_data, colWidths=[CONTENT_W*0.38, CONTENT_W*0.30, CONTENT_W*0.32])
    cb.setStyle(TableStyle([
        ('BACKGROUND',   (0,0),(-1,-1), BLUE_LIGHT),
        ('LINEBEFORE',   (0,0),(0,-1),  3, BLUE),
        ('TOPPADDING',   (0,0),(-1,-1), 10),
        ('BOTTOMPADDING',(0,0),(-1,-1), 10),
        ('LEFTPADDING',  (0,0),(-1,-1), 10),
        ('RIGHTPADDING', (0,0),(-1,-1), 10),
        ('VALIGN',       (0,0),(-1,-1), 'MIDDLE'),
    ]))
    story.append(cb)

    # ── Seguros ────────────────────────────────────────────────────────────
    story += _section("Coberturas de seguro incluidas en la cuota")
    story.append(Paragraph(
        "La cuota mensual contempla tres seguros que protegen tanto al cliente como a la propiedad "
        "durante toda la vigencia del credito:",
        ST_BODY))
    story.append(Spacer(1, 2*mm))

    seg_rows = [
        [Paragraph("<b>Seguro Desgravamen</b>", ST_KV_V),
         Paragraph("Cubre el saldo del credito ante fallecimiento o invalidez total del deudor, "
                   "liberando a su familia de la deuda.", ST_SMALL),
         Paragraph(f"<b>{u(SEG_DEG)}/mes</b><br/><font color='#8FA3B8'>{fc(SEG_DEG)}</font>",
                   _S('sr', fontSize=8.5, fontName='Helvetica-Bold',
                      textColor=BLUE, leading=12, alignment=TA_RIGHT))],
        [Paragraph("<b>Seguro Incendio y Sismo</b>", ST_KV_V),
         Paragraph("Protege la propiedad ante danos estructurales por incendio, temblor o sismo, "
                   "resguardando el bien hipotecado.", ST_SMALL),
         Paragraph(f"<b>{u(SEG_INC)}/mes</b><br/><font color='#8FA3B8'>{fc(SEG_INC)}</font>",
                   _S('sr2', fontSize=8.5, fontName='Helvetica-Bold',
                      textColor=BLUE, leading=12, alignment=TA_RIGHT))],
        [Paragraph("<b>Seguro Cesantia</b>", ST_KV_V),
         Paragraph("Subsidia el pago de cuotas ante la perdida involuntaria del empleo, "
                   "evitando incumplimientos durante periodos de desocupacion.", ST_SMALL),
         Paragraph(f"<b>{u(SEG_CES)}/mes</b><br/><font color='#8FA3B8'>{fc(SEG_CES)}</font>",
                   _S('sr3', fontSize=8.5, fontName='Helvetica-Bold',
                      textColor=BLUE, leading=12, alignment=TA_RIGHT))],
    ]
    seg_t = Table(seg_rows, colWidths=[CONTENT_W*0.26, CONTENT_W*0.49, CONTENT_W*0.25])
    seg_t.setStyle(TableStyle([
        ('ROWBACKGROUNDS', (0,0),(-1,-1), [WHITE, GRAY_BG]),
        ('LINEBELOW',     (0,0),(-1,-2), 0.3, GRAY_LINE),
        ('LINEBELOW',     (0,-1),(-1,-1),0.3, GRAY_LINE),
        ('TOPPADDING',    (0,0),(-1,-1), 7),
        ('BOTTOMPADDING', (0,0),(-1,-1), 7),
        ('LEFTPADDING',   (0,0),(-1,-1), 8),
        ('RIGHTPADDING',  (0,0),(-1,-1), 8),
        ('VALIGN',        (0,0),(-1,-1), 'TOP'),
        ('LINEAFTER',     (0,0),(1,-1),  0.3, GRAY_LINE),
    ]))
    story.append(seg_t)
    story.append(Spacer(1, 1*mm))
    story.append(Paragraph(
        f"El total de seguros incluidos en la cuota asciende a <b>{u(SEG_TOT)}</b> mensual "
        f"({fc(SEG_TOT)}). Este monto puede variar segun la entidad financiera evaluadora.",
        ST_SMALL))

    # ── Honorarios ─────────────────────────────────────────────────────────
    story += _section("Servicio de asesoria y costos asociados")
    story.append(Paragraph(
        f"Por la asesoria integral en la gestion de este credito — que incluye tramitacion legal, "
        f"coordinacion con la entidad financiera, apoyo notarial y acompanamiento durante todo el "
        f"proceso — los honorarios de gestion ascienden a <b>{u(HON_UF)}</b> ({fc(HON_UF)}), "
        f"equivalentes al <b>{HON_PCT:.0f}% del monto financiado</b>.",
        ST_BODY))
    story.append(Spacer(1, 2*mm))
    story.append(Paragraph(
        f"Adicionalmente, el proceso de <b>pre-evaluacion crediticia</b> tiene un costo de "
        f"<b>{PRE_EVAL} UF</b> ({fc(PRE_EVAL)}) para Persona {TIPO_PERS}. Esta etapa permite "
        f"conocer anticipadamente las condiciones que la entidad financiera ofrecera, antes de "
        f"iniciar la tramitacion formal del credito.",
        ST_BODY))
    story.append(Spacer(1, 2*mm))
    story.append(_highlight([
        f"  \u2713  Honorarios de gestion ({HON_PCT:.0f}%):  {u(HON_UF)}  ({fc(HON_UF)})",
        f"  \u2713  Pre-evaluacion crediticia (Persona {TIPO_PERS}):  {PRE_EVAL} UF  ({fc(PRE_EVAL)})",
        f"  \u2713  Propuesta valida hasta el {VIGENCIA}",
    ]))

    # ── Resumen ────────────────────────────────────────────────────────────
    story += _section("Resumen de la operacion")
    story.append(Paragraph(
        f"En terminos globales, la operacion contempla un inmueble valorado en <b>{u(VI)}</b> "
        f"({fc(VI)}). El cliente aporta un pie del <b>{round((PIE/VI)*100) if VI > 0 else 0}%</b>, "
        f"mientras que el <b>{round((MONTO/VI)*100) if VI > 0 else 0}% restante</b> se financia a "
        f"traves de este credito hipotecario. A lo largo de los {PLAZO} anos de vigencia, el costo "
        f"estimado en intereses es de <b>{u1(tot_int)}</b>, considerando la tasa nominal "
        f"{TIPO_TASA} del {TASA}% anual.",
        ST_BODY))
    story.append(Spacer(1, 2*mm))
    story.append(Paragraph(
        f"Para acceder a este financiamiento, se estima que el solicitante debe acreditar un "
        f"<b>ingreso liquido mensual minimo de {fc(ct/0.25)}</b>, de modo que la cuota no supere "
        f"el 25% de sus ingresos, criterio habitualmente utilizado por las entidades financieras "
        f"en su proceso de evaluacion.",
        ST_BODY))

    # ── Cierre ─────────────────────────────────────────────────────────────
    story.append(Spacer(1, 4*mm))
    story.append(_divider())
    story.append(Spacer(1, 3*mm))
    story.append(Paragraph(
        "No dude en contactarnos para aclarar cualquier duda o proceder con la solicitud formal. "
        "Estamos comprometidos a acompanarle en cada etapa del proceso y agradecemos profundamente "
        "su confianza.",
        _S('cls', fontSize=9.5, fontName='Helvetica-Oblique',
           textColor=GRAY_TEXT, leading=15, alignment=TA_JUSTIFY)))
    story.append(Spacer(1, 5*mm))

    # ── Firma ──────────────────────────────────────────────────────────────
    try:
        logo_sig = Image(logo_path, width=30*mm, height=30*mm*(273/765))
        logo_cell = logo_sig
    except Exception:
        logo_cell = Paragraph('<font color="#2B7BB9"><b>loan$4B.com</b></font>',
                              _S('lc', fontSize=14, fontName='Helvetica-Bold',
                                 textColor=BLUE, leading=18, alignment=TA_RIGHT))

    sig_data = [[
        Paragraph(f"Atentamente,<br/><br/><b>{ASESOR}</b><br/>"
                  "<font color='#8FA3B8' size='8.5'>Asesor de Credito Hipotecario</font>",
                  ST_SMALL),
        logo_cell,
    ]]
    sig_t = Table(sig_data, colWidths=[CONTENT_W*0.65, CONTENT_W*0.35])
    sig_t.setStyle(TableStyle([
        ('TOPPADDING',   (0,0),(-1,-1), 0),
        ('BOTTOMPADDING',(0,0),(-1,-1), 0),
        ('LEFTPADDING',  (0,0),(-1,-1), 0),
        ('RIGHTPADDING', (0,0),(-1,-1), 0),
        ('VALIGN',       (0,0),(-1,-1), 'MIDDLE'),
        ('ALIGN',        (1,0),(1,-1),  'RIGHT'),
    ]))
    story.append(sig_t)
    story.append(Spacer(1, 3*mm))

    # ── Cláusula ───────────────────────────────────────────────────────────
    story.append(_divider())
    story.append(Spacer(1, 1*mm))
    story.append(Paragraph(
        "<b>Clausula de Responsabilidad y Transparencia:</b> La presente simulacion tiene caracter "
        "informativo y no representa una oferta formal ni vinculante. Asesorias Loans4B actua como "
        "intermediario en la gestion de creditos hipotecarios, sin representar a ninguna entidad "
        "financiera ni comprometer la aprobacion del credito. La tasa de interes, cuota y "
        "condiciones estan sujetas a evaluacion crediticia por parte del banco o institucion "
        "correspondiente. Las simulaciones estan sujetas a la evaluacion de entidades financieras "
        "debidamente autorizadas por la CMF, asi como a modelos de financiamiento de fondos "
        "privados que operan conforme a la legislacion civil y comercial vigente en Chile.",
        ST_DISC))

    doc.build(story)
