# pdf_gen.py v2 — MedFlow AI Posologie-AI
# Design: Power BI-inspired dashboard — single page, KPI cards, grid layout

import io
from datetime import datetime

try:
    from fpdf import FPDF
    PDF_OK = True
except ImportError:
    PDF_OK = False

try:
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    MPL_OK = True
except ImportError:
    MPL_OK = False

from calculations import arrondir_05, build_clinical_explanation


# ── Latin-1 encoder (fpdf2 core font constraint) ─────────────────────────────
def _cpdf(text: str) -> str:
    if not isinstance(text, str):
        return str(text) if text else ''
    subs = {
        '—': '-', '–': '-', '·': '-',
        '→': '->', '←': '<-', '↑': '^', '↓': 'v',
        '×': 'x', '≥': '>=', '≤': '<=',
        '⁺': '+', '⁻': '-',
        '’': "'", '‘': "'", '“': '"', '”': '"',
        '¹': '1', '²': '2', '³': '3',
        'é': 'e', 'è': 'e', 'ê': 'e', 'ë': 'e',
        'à': 'a', 'â': 'a', 'ä': 'a',
        'î': 'i', 'ï': 'i',
        'ô': 'o', 'ö': 'o',
        'ù': 'u', 'û': 'u', 'ü': 'u',
        'ç': 'c',
        'É': 'E', 'È': 'E', 'À': 'A', 'Ç': 'C',
    }
    for k, v in subs.items():
        text = text.replace(k, v)
    return text.encode('latin-1', errors='replace').decode('latin-1')


class MedFlowPDF(FPDF if PDF_OK else object):
    def cell(self, *args, **kwargs):
        if len(args) >= 3:
            args = list(args); args[2] = _cpdf(str(args[2])); args = tuple(args)
        elif 'text' in kwargs:
            kwargs['text'] = _cpdf(str(kwargs['text']))
        return super().cell(*args, **kwargs)

    def multi_cell(self, *args, **kwargs):
        if len(args) >= 3:
            args = list(args); args[2] = _cpdf(str(args[2])); args = tuple(args)
        elif 'text' in kwargs:
            kwargs['text'] = _cpdf(str(kwargs['text']))
        return super().multi_cell(*args, **kwargs)


# ── Colors ────────────────────────────────────────────────────────────────────
C_DARK         = (10,  22,  40)
C_NAVY         = (30,  58,  95)
C_BLUE         = (37,  99, 235)
C_BLUE_L       = (219, 234, 254)
C_TEAL         = (14, 116, 144)
C_TEAL_L       = (204, 240, 248)
C_GREEN        = (5,  150, 105)
C_GREEN_L      = (209, 250, 229)
C_RED          = (220,  38,  38)
C_RED_L        = (254, 226, 226)
C_ORANGE       = (234,  88,  12)
C_ORANGE_L     = (255, 237, 213)
C_PURPLE       = (124,  58, 237)
C_PURPLE_L     = (237, 233, 254)
C_GRAY         = (100, 116, 139)
C_GRAY_L       = (248, 250, 252)
C_WHITE        = (255, 255, 255)
C_TEXT         = (15,  23,  42)
C_TEXT2        = (71,  85, 105)
C_BORDER       = (203, 213, 225)


# ── Drawing primitives ────────────────────────────────────────────────────────
def _F(pdf, style='', size=8, color=C_TEXT):
    pdf.set_font('Helvetica', style, size)
    pdf.set_text_color(*color)

def _rect(pdf, x, y, w, h, fill, stroke=None, r=0):
    pdf.set_fill_color(*fill)
    if stroke:
        pdf.set_draw_color(*stroke)
        style = 'FD'
    else:
        style = 'F'
    pdf.rect(x, y, w, h, style)

def _line(pdf, x1, y1, x2, y2, color, w=0.3):
    pdf.set_draw_color(*color)
    pdf.set_line_width(w)
    pdf.line(x1, y1, x2, y2)


# ── Component: KPI card ───────────────────────────────────────────────────────
def _kpi(pdf, x, y, w, h, label, value, sub, accent, bg=None):
    bg = bg or C_WHITE
    _rect(pdf, x, y, w, h, bg, C_BORDER, r=2)
    _rect(pdf, x, y, w, 3.5, accent)                    # top accent bar

    _F(pdf, '', 6, C_GRAY)
    pdf.set_xy(x + 3, y + 5.5)
    pdf.cell(w - 6, 4, label)

    _F(pdf, 'B', 14, accent)
    pdf.set_xy(x + 3, y + 10.5)
    pdf.cell(w - 6, 7, str(value))

    if sub:
        _F(pdf, '', 5.5, C_GRAY)
        pdf.set_xy(x + 3, y + 19)
        pdf.cell(w - 6, 4, str(sub)[:24])


# ── Component: section header bar ─────────────────────────────────────────────
def _section(pdf, x, y, w, title, color=None, h=7):
    color = color or C_NAVY
    _rect(pdf, x, y, w, h, color)
    _F(pdf, 'B', 7.5, C_WHITE)
    pdf.set_xy(x + 4, y + 1.3)
    pdf.cell(w - 8, 5, _cpdf(title))
    return y + h + 1


# ── Component: drug card ───────────────────────────────────────────────────────
def _drug_card(pdf, x, y, w, h, drug_name, dose_str, schema, note, accent):
    _rect(pdf, x, y, w, h, C_GRAY_L, C_BORDER, r=2)
    _rect(pdf, x, y, w, 3.5, accent)                    # accent bar

    _F(pdf, 'B', 7.5, accent)
    pdf.set_xy(x + 3, y + 5.5)
    pdf.cell(w - 6, 4.5, _cpdf(drug_name))

    _F(pdf, 'B', 18, C_TEXT)
    pdf.set_xy(x + 3, y + 11)
    pdf.cell(w - 6, 9, str(dose_str))

    _F(pdf, '', 6.5, C_TEXT2)
    pdf.set_xy(x + 3, y + 21.5)
    pdf.multi_cell(w - 6, 4, _cpdf(str(schema)[:55]))

    if note:
        _F(pdf, 'I', 6, C_GRAY)
        pdf.set_xy(x + 3, y + h - 7)
        pdf.cell(w - 6, 4, _cpdf(str(note)[:38]))


# ── Component: alert row ──────────────────────────────────────────────────────
def _alert(pdf, x, y, w, severity, title, detail):
    palette = {
        'INFO':      (C_BLUE,   C_BLUE_L),
        'ATTENTION': (C_ORANGE, C_ORANGE_L),
        'URGENT':    (C_RED,    C_RED_L),
    }
    accent, bg = palette.get(severity, (C_BLUE, C_BLUE_L))
    rh = 11
    _rect(pdf, x, y, w, rh, bg)
    _rect(pdf, x, y, 2.5, rh, accent)                   # left accent bar

    _F(pdf, 'B', 6, accent)
    pdf.set_xy(x + 4.5, y + 1.5)
    pdf.cell(20, 4, severity[:10])

    _F(pdf, 'B', 6.5, C_TEXT)
    pdf.set_xy(x + 25, y + 1.5)
    pdf.cell(w * 0.32, 4, _cpdf(title)[:28])

    _F(pdf, '', 6, C_TEXT2)
    pdf.set_xy(x + 25, y + 6.5)
    pdf.cell(w - 32, 4, _cpdf(detail)[:72])
    return rh + 1.5


# ── Component: raisonnement step ──────────────────────────────────────────────
def _step(pdf, x, y, w, num, title, formula):
    h = 18
    _rect(pdf, x, y, w, h, C_GRAY_L, C_BORDER, r=2)

    # Number circle
    pdf.set_fill_color(*C_TEAL)
    pdf.ellipse(x + 2.5, y + 5.5, 6, 6, 'F')
    _F(pdf, 'B', 7, C_WHITE)
    pdf.set_xy(x + 2.5, y + 6)
    pdf.cell(6, 5, str(num), align='C')

    _F(pdf, 'B', 7, C_TEAL)
    pdf.set_xy(x + 11, y + 2.5)
    pdf.cell(w - 14, 4.5, _cpdf(title))

    _F(pdf, '', 6.5, C_TEXT2)
    pdf.set_xy(x + 11, y + 8)
    pdf.multi_cell(w - 14, 4, _cpdf(formula)[:110])


# ── Component: C0 sparkline helpers (pure FPDF) ──────────────────────────────
def _extract_c0_history(history_rows):
    if not history_rows:
        return []
    vals = []
    for row in history_rows[-5:]:
        try:
            if isinstance(row, dict):
                v = float(row.get('c0', row.get('C0', row.get('c0_val', 0))) or 0)
            elif hasattr(row, '__getitem__') and len(row) > 1:
                v = float(row[1] or 0)
            else:
                continue
            if v > 0:
                vals.append(v)
        except (TypeError, ValueError, IndexError):
            pass
    return vals


def _sparkline_fpdf(pdf, x, y, bw, bh, vals, t_min, t_max, accent):
    if len(vals) < 2:
        return
    c0_rng = max(float(t_max) * 1.8, max(vals) * 1.2, 20.0)
    _rect(pdf, x, y, bw, bh, C_GRAY_L)
    zy1 = y + bh * (1 - t_min / c0_rng)
    zy2 = y + bh * (1 - t_max / c0_rng)
    if zy2 < zy1:
        _rect(pdf, x, max(y, zy2), bw, max(0.3, min(y + bh, zy1) - max(y, zy2)), C_GREEN_L)
    n = len(vals)
    pts = [(x + bw * i / (n - 1), y + bh * (1 - min(v, c0_rng) / c0_rng))
           for i, v in enumerate(vals)]
    for i in range(len(pts) - 1):
        _line(pdf, pts[i][0], pts[i][1], pts[i+1][0], pts[i+1][1], accent, 0.4)
    for px, py in pts:
        pdf.set_fill_color(*accent)
        pdf.ellipse(px - 0.8, py - 0.8, 1.6, 1.6, 'F')


# ── Chart helper (kept for backward compat) ───────────────────────────────────
def make_pdf_chart(dates, values, ylabel, color_hex, ref_min=None, ref_max=None):
    if not MPL_OK or len(values) < 2:
        return None
    r = int(color_hex[1:3], 16) / 255
    g_c = int(color_hex[3:5], 16) / 255
    b = int(color_hex[5:7], 16) / 255
    fig, ax = plt.subplots(figsize=(5.2, 2.4))
    fig.patch.set_facecolor('#f8fafc')
    ax.set_facecolor('#f1f5f9')
    xp = list(range(len(dates)))
    ax.plot(xp, values, 'o-', color=(r, g_c, b), linewidth=2, markersize=5, zorder=3)
    if ref_min is not None and ref_max is not None:
        ax.axhspan(ref_min, ref_max, alpha=0.18, color='green',
                   label=f'Cible {ref_min}-{ref_max}')
        ax.legend(fontsize=7, loc='upper right', framealpha=0.7)
    ax.set_xticks(xp)
    ax.set_xticklabels([d[5:10] for d in dates], fontsize=7, rotation=45)
    ax.set_ylabel(ylabel, fontsize=7.5, color='#475569')
    ax.tick_params(colors='#64748b', labelsize=7)
    ax.grid(True, alpha=0.3, linestyle='--', zorder=0)
    ax.spines[['top', 'right']].set_visible(False)
    ax.spines[['left', 'bottom']].set_color('#cbd5e1')
    plt.tight_layout(pad=0.5)
    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=150, bbox_inches='tight', facecolor='#f8fafc')
    plt.close(fig)
    buf.seek(0)
    return buf


# ══════════════════════════════════════════════════════════════════════════════
#  MAIN — generate_pdf  (single-page dashboard layout)
# ══════════════════════════════════════════════════════════════════════════════
def generate_pdf(pat_nom, pat_prenom, pat_id,
                 age, sexe, poids, creat, dfg, stade, stade_desc,
                 na_val, na_label, k_val, k_label,
                 phase_label, c0, c0_statut, t_min, t_max,
                 dose_act, dose_rec, dose_pk, plafond, fr,
                 k_eleve, rec_titre, history_rows,
                 ai_summary=None,
                 mmf_data=None, pred_data=None) -> bytes | None:
    if not PDF_OK:
        return None

    pdf = MedFlowPDF()
    pdf.set_auto_page_break(auto=False)
    pdf.add_page()

    ML  = 10        # left margin
    PW  = 190       # usable page width

    dose_prise = arrondir_05(dose_rec / 2)

    # ── Recommendation accent ────────────────────────────────────────────────
    rec_clean = (rec_titre
                 .replace('✅', '').replace('⚠️', '')
                 .replace('⚠', '').replace('\U0001f6ab', '')
                 .replace('❗', '').strip())
    if 'urgent' in rec_titre.lower() or 'imperatif' in rec_titre.lower() or 'Avis expert' in rec_titre:
        rec_accent = C_RED;    rec_bg = C_RED_L
    elif '⚠' in rec_titre or 'attention' in rec_titre.lower():
        rec_accent = C_ORANGE; rec_bg = C_ORANGE_L
    else:
        rec_accent = C_GREEN;  rec_bg = C_GREEN_L

    # ════════════════════════════════════════════════════════════════════════
    # 1 — HEADER
    # ════════════════════════════════════════════════════════════════════════
    _rect(pdf, 0, 0, 210, 27, C_DARK)
    _rect(pdf, 0, 0, 4,  27, C_PURPLE)        # purple left bar

    # Logo
    _F(pdf, 'B', 14, C_WHITE)
    pdf.set_xy(7, 4)
    pdf.cell(70, 7, 'Posologie-AI  |  MedFlow AI')
    _F(pdf, '', 7.5, (148, 163, 184))
    pdf.set_xy(7, 13)
    pdf.cell(85, 5, 'Rapport posologique adaptatif - Transplantation cardiaque')
    pdf.set_xy(7, 20)
    _F(pdf, 'I', 6.5, (100, 116, 139))
    pdf.cell(85, 4, f'Genere le {datetime.now().strftime("%d/%m/%Y a %H:%M")}')

    # Patient info (right side)
    full_name = f'{pat_prenom.capitalize()} {pat_nom.upper()}'
    _F(pdf, 'B', 10, C_WHITE)
    pdf.set_xy(100, 4)
    pdf.cell(70, 5.5, _cpdf(full_name))
    _F(pdf, '', 7.5, (180, 195, 210))
    pdf.set_xy(100, 10.5)
    pdf.cell(70, 4.5, f'{age} ans - {sexe} - {poids} kg')
    pdf.set_xy(100, 16)
    pdf.cell(70, 4.5, f'ID {pat_id} - {_cpdf(phase_label.split("(")[0].strip()[:25])}')

    # Date badge top right
    _F(pdf, 'B', 8, (148, 163, 184))
    pdf.set_xy(170, 7)
    pdf.cell(30, 5, datetime.now().strftime('%d/%m/%Y'), align='R')
    pdf.set_xy(170, 14)
    _F(pdf, '', 7, (100, 116, 139))
    pdf.cell(30, 4, datetime.now().strftime('%H:%M'), align='R')

    y = 30

    # ════════════════════════════════════════════════════════════════════════
    # 2 — KPI ROW  (6 cards)
    # ════════════════════════════════════════════════════════════════════════
    kpi_h = 30
    gap   = 1.5
    kpi_w = (PW - 5 * gap) / 6

    c0_accent  = C_GREEN  if c0_statut == 'Therapeutique' else (C_RED if 'sur' in c0_statut.lower() else C_ORANGE)
    dfg_accent = C_GREEN  if dfg >= 60 else (C_ORANGE if dfg >= 30 else C_RED)
    k_accent   = C_RED    if k_eleve else C_GREEN

    kpis = [
        ('DFG (Cockcroft)',   f'{dfg}',         f'mL/min - {stade}',              dfg_accent),
        ('C0 Tacrolimus',    f'{c0}',           f'ng/mL - {_cpdf(c0_statut[:14])}', c0_accent),
        ('Dose recommandee', f'{dose_rec} mg/j',f'{dose_prise}mg x2 /j (q12h)',   rec_accent),
        ('Na+ (Natremie)',   f'{na_val}',       f'mmol/L - {_cpdf(na_label[:10])}', C_BLUE),
        ('K+ (Kaliemie)',    f'{k_val}',        f'mmol/L - {_cpdf(k_label[:10])}',  k_accent),
        ('Creatinine',       f'{creat}',        'umol/L',                          C_TEAL),
    ]
    for i, (lbl, val, sub, accent) in enumerate(kpis):
        kx = ML + i * (kpi_w + gap)
        _kpi(pdf, kx, y, kpi_w, kpi_h, lbl, val, sub, accent)

    # — DFG mini progress bar (card 0) —
    kpi_bw  = kpi_w - 6
    bar_y   = y + 25
    bx0     = ML + 0 * (kpi_w + gap) + 3
    _rect(pdf, bx0, bar_y, kpi_bw, 2.5, C_BORDER)
    _rect(pdf, bx0, bar_y, kpi_bw * min(1.0, dfg / 90.0), 2.5, dfg_accent)

    # — C0 therapeutic zone gauge (card 1) —
    bx1     = ML + 1 * (kpi_w + gap) + 3
    c0_rng  = max(float(t_max) * 1.6, float(c0) * 1.3, 20.0)
    _rect(pdf, bx1, bar_y, kpi_bw, 2.5, C_BORDER)
    tz1 = bx1 + kpi_bw * float(t_min) / c0_rng
    tz2 = bx1 + kpi_bw * float(t_max) / c0_rng
    _rect(pdf, tz1, bar_y, max(0.5, tz2 - tz1), 2.5, C_GREEN_L)
    cm  = bx1 + kpi_bw * min(1.0, float(c0) / c0_rng)
    _rect(pdf, cm - 0.7, bar_y - 0.3, 1.4, 3.1, c0_accent)

    y += kpi_h + 4

    # ════════════════════════════════════════════════════════════════════════
    # 3 — MAIN ROW: Patient data | Dose recommendation
    # ════════════════════════════════════════════════════════════════════════
    main_h  = 48
    left_w  = 93
    right_w = PW - left_w - 3

    # — Left: Patient + Biology box ——————————————————————————————————————————
    _rect(pdf, ML, y, left_w, main_h, C_WHITE, C_BORDER, r=2)
    ys = _section(pdf, ML, y, left_w, 'PATIENT & BIOLOGIE', C_NAVY, h=7)

    # Two micro-columns
    cw = left_w / 2 - 2
    c1 = ML + 2;  c2 = ML + left_w / 2 + 1

    left_rows = [
        ('Age / Sexe',      f'{age} ans, {sexe}'),
        ('Poids',           f'{poids} kg'),
        ('Creatinine',      f'{creat} umol/L'),
        ('DFG',             f'{dfg} mL/min'),
        ('Stade KDIGO',     f'{stade} - {_cpdf(stade_desc[:12])}'),
    ]
    right_rows = [
        ('Phase greffe',    _cpdf(phase_label.split('(')[0].strip()[:18])),
        ('C0 residuel',     f'{c0} ng/mL'),
        ('Cible C0',        f'{t_min} - {t_max} ng/mL'),
        ('Na+',             f'{na_val} mmol/L - {_cpdf(na_label[:8])}'),
        ('K+',              f'{k_val} mmol/L - {_cpdf(k_label[:8])}'),
    ]
    rh = 5.6
    for i, (lbl, val) in enumerate(left_rows):
        ry = ys + i * rh
        _F(pdf, '',  6.5, C_GRAY);  pdf.set_xy(c1, ry); pdf.cell(cw * 0.52, 4.5, lbl + ':')
        _F(pdf, 'B', 7,   C_TEXT);  pdf.set_xy(c1 + cw * 0.52, ry); pdf.cell(cw * 0.48, 4.5, val)

    for i, (lbl, val) in enumerate(right_rows):
        ry = ys + i * rh
        _F(pdf, '',  6.5, C_GRAY);  pdf.set_xy(c2, ry); pdf.cell(cw * 0.52, 4.5, lbl + ':')
        _F(pdf, 'B', 7,   C_TEXT);  pdf.set_xy(c2 + cw * 0.52, ry); pdf.cell(cw * 0.48, 4.5, val)

    # — Right: Dose Recommendation box ————————————————————————————————————————
    rx = ML + left_w + 3
    _rect(pdf, rx, y, right_w, main_h, rec_bg, rec_accent, r=2)
    _rect(pdf, rx, y, right_w, 3.5, rec_accent)

    _F(pdf, 'B', 7, rec_accent)
    pdf.set_xy(rx + 4, y + 5.5)
    pdf.cell(right_w - 8, 4.5, _cpdf(rec_clean)[:48])

    _F(pdf, 'B', 28, C_TEXT)
    pdf.set_xy(rx + 4, y + 11)
    pdf.cell(62, 13, f'{dose_rec} mg/j')

    _F(pdf, '', 9, C_TEXT2)
    pdf.set_xy(rx + 4, y + 25)
    pdf.cell(right_w - 8, 5, f'{dose_prise} mg matin + {dose_prise} mg soir')

    _F(pdf, '', 7, C_GRAY)
    pdf.set_xy(rx + 4, y + 31)
    pdf.cell(right_w - 8, 5, 'Prises q12h - Capsules Prograf (tacrolimus)')

    _F(pdf, 'I', 6.5, C_TEXT2)
    pdf.set_xy(rx + 4, y + 37)
    pdf.cell(right_w - 8, 4,
             f'Actuelle: {dose_act} mg/j  |  PK: {dose_pk} mg/j  |  Plafond: {plafond} mg/j')

    # — Dose / plafond gauge —
    dp       = min(1.0, float(dose_rec) / float(plafond)) if plafond > 0 else 0.0
    dg_color = C_GREEN if dp < 0.80 else (C_ORANGE if dp < 0.95 else C_RED)
    dg_x = rx + 4;  dg_y = y + 43;  dg_w = right_w - 8
    _F(pdf, '', 5.5, C_GRAY)
    pdf.set_xy(dg_x, dg_y - 3.5)
    pdf.cell(dg_w, 3.5, f'{int(dp * 100)}% du plafond nephroprotecteur', align='R')
    _rect(pdf, dg_x, dg_y, dg_w, 2.5, C_BORDER)
    _rect(pdf, dg_x, dg_y, dg_w * dp, 2.5, dg_color)

    y += main_h + 4

    # ════════════════════════════════════════════════════════════════════════
    # 4 — DRUG ROW  (Tacrolimus | MMF | Prednisolone)
    # ════════════════════════════════════════════════════════════════════════
    n_drugs = 1 + (1 if mmf_data else 0) + (1 if pred_data else 0)
    dg      = 2
    dw      = (PW - (n_drugs - 1) * dg) / n_drugs
    drug_h  = 36

    tac_schema  = f'{dose_prise}mg matin + {dose_prise}mg soir (q12h, Prograf)'
    c0_vals     = _extract_c0_history(history_rows)
    has_spark   = len(c0_vals) >= 2
    tac_note    = None if has_spark else f'C0: {c0} ng/mL ({_cpdf(c0_statut)})'
    _drug_card(pdf, ML, y, dw, drug_h,
               'TACROLIMUS (PROGRAF)',
               f'{dose_rec} mg/j',
               tac_schema,
               tac_note,
               C_PURPLE)
    if has_spark:
        _F(pdf, '', 5.5, C_PURPLE)
        pdf.set_xy(ML + 3, y + drug_h - 10)
        pdf.cell(dw - 6, 4, f'C0: {c0} ng/mL  Historique ({len(c0_vals)} pts):')
        _sparkline_fpdf(pdf, ML + 3, y + drug_h - 6, dw - 6, 4.5,
                        c0_vals, float(t_min), float(t_max), c0_accent)

    di = 1
    if mmf_data:
        mx = ML + di * (dw + dg)
        ms = mmf_data.get('schema', '')
        _drug_card(pdf, mx, y, dw, drug_h,
                   'MMF / CELLCEPT',
                   f"{mmf_data.get('dose_rec', '—')} mg/j",
                   _cpdf(str(ms)[:50]),
                   f"Actuelle: {mmf_data.get('dose_act','—')} mg/j",
                   C_BLUE)
        di += 1

    if pred_data:
        px = ML + di * (dw + dg)
        ps = f"Cible: {_cpdf(str(pred_data.get('cible','—')))}"
        _drug_card(pdf, px, y, dw, drug_h,
                   'PREDNISOLONE',
                   f"{pred_data.get('dose_rec', '—')} mg/j",
                   ps,
                   f"Statut: {_cpdf(str(pred_data.get('statut',''))[:32])}",
                   C_ORANGE)

    y += drug_h + 4

    # ════════════════════════════════════════════════════════════════════════
    # 5 — ALERTS
    # ════════════════════════════════════════════════════════════════════════
    alerts = []
    if c0_statut and 'sous' in c0_statut.lower():
        alerts.append(('ATTENTION', 'C0 sous-therapeutique',
                        f'C0 {c0} ng/mL < {t_min} — Augmentation recommandee'))
    elif c0_statut and ('sur' in c0_statut.lower() or 'toxic' in c0_statut.lower()):
        alerts.append(('URGENT', 'C0 sur-therapeutique',
                        f'C0 {c0} ng/mL > {t_max} — Reduction dose urgente'))

    if k_eleve:
        alerts.append(('ATTENTION', 'Hyperkaliemie',
                        f'K+ {k_val} mmol/L > 5.5 — Surveillance ECG, eviter IEC/ARA2/AINS'))

    if stade in ('G4', 'G5'):
        alerts.append(('URGENT', 'IRC severe',
                        f'DFG {dfg} mL/min — Nephroprotection maximale, avis nephro'))
    elif stade == 'G3b':
        alerts.append(('ATTENTION', 'IRC moderee',
                        f'DFG {dfg} mL/min — Surveillance creatinine renforcee'))

    if mmf_data:
        for icone, titre in mmf_data.get('alertes', [])[:1]:
            alerts.append(('INFO', 'MMF', _cpdf(str(titre)[:65])))
    if pred_data:
        for icone, titre in pred_data.get('alertes', [])[:1]:
            alerts.append(('INFO', 'Prednisolone', _cpdf(str(titre)[:65])))

    # Always add osteoporosis prevention for cardiac transplant (corticotherapy)
    alerts.append(('INFO', 'Prevention osteoporose',
                   'Calcium 1000-1200 mg/j + Vitamine D 800 UI/j si corticotherapie chronique'))

    max_alerts = 4
    alerts = alerts[:max_alerts]

    if alerts:
        y = _section(pdf, ML, y, PW, 'ALERTES CLINIQUES ET SURVEILLANCE RECOMMANDEE',
                     C_TEAL, h=7)
        aw = (PW - 2) / 2
        for idx, (sev, ttl, det) in enumerate(alerts):
            ax = ML if idx % 2 == 0 else ML + aw + 2
            ay = y if idx < 2 else y + 13
            _alert(pdf, ax, ay, aw, sev, ttl, det)
        y += (14 if len(alerts) <= 2 else 27) + 3

    # ════════════════════════════════════════════════════════════════════════
    # 6 — RAISONNEMENT  (4 steps, 2×2 grid)
    # ════════════════════════════════════════════════════════════════════════
    y = _section(pdf, ML, y, PW, 'RAISONNEMENT CLINIQUE ET METHODOLOGIE', C_DARK, h=7)

    t_mid = (t_min + t_max) / 2
    raw_pk = round(dose_act * t_mid / c0, 2) if c0 > 0 else dose_act
    k_note = f' | K+>{k_val}>5.5 => plafond {dose_act}mg/j' if k_eleve else ''
    steps = [
        ('1. Cockcroft-Gault (1976)',
         f'DFG = ((140-{age}) x {poids} x {"1.00" if sexe=="Homme" else "0.85"}) / (0.815 x {creat}) = {dfg} mL/min => {stade}'),
        ('2. Ajustement PK proportionnel (Staatz & Tett, 2004)',
         f'{dose_act} mg/j x ({t_mid} / {c0}) = {raw_pk} mg/j => arrondi capsule 0.5 mg => {dose_pk} mg/j'),
        ('3. Plafond nephroprotecteur (Ojo 2003 - Naesens 2009 - Ekberg 2007)',
         f'{poids} kg x 0.1 mg/kg x facteur DFG {fr} (stade {stade}) = {plafond} mg/j'),
        ('4. Decision finale',
         f'min(PK {dose_pk}, plafond {plafond}{k_note}) = {dose_rec} mg/j => {dose_prise} mg x 2/j (q12h)'),
    ]
    sw = (PW - 2) / 2
    step_h = 19
    for idx, (title, formula) in enumerate(steps):
        sx = ML if idx % 2 == 0 else ML + sw + 2
        sy = y if idx < 2 else y + step_h + 2
        _step(pdf, sx, sy, sw, idx + 1, title, formula)

    y += step_h * 2 + 5

    # ════════════════════════════════════════════════════════════════════════
    # 7 — AI SUMMARY
    # ════════════════════════════════════════════════════════════════════════
    footer_y = 283
    if ai_summary:
        avail = footer_y - y - 12
        if avail > 16:
            y = _section(pdf, ML, y, PW,
                         'RESUME DE CONSULTATION - MEDFLOW AI', C_PURPLE, h=7)
            _rect(pdf, ML, y, PW, avail, C_PURPLE_L)
            _rect(pdf, ML, y, 3, avail, C_PURPLE)   # left purple bar

            _F(pdf, '', 7.5, C_TEXT)
            pdf.set_xy(ML + 5, y + 2)
            # Approx chars that fit in available height
            chars_per_line = int((PW - 8) / 2.1)
            lines_avail    = int(avail / 5)
            max_chars      = chars_per_line * lines_avail
            pdf.multi_cell(PW - 8, 5, _cpdf(ai_summary[:max_chars]))

    # ════════════════════════════════════════════════════════════════════════
    # 8 — FOOTER
    # ════════════════════════════════════════════════════════════════════════
    _rect(pdf, 0, footer_y, 210, 14, C_GRAY_L)
    _line(pdf, 0, footer_y, 210, footer_y, C_BORDER, w=0.5)

    _F(pdf, 'I', 6.5, C_GRAY)
    pdf.set_xy(ML, footer_y + 3)
    pdf.cell(145, 4,
             "Outil d'aide a la decision clinique - Ne remplace pas la concertation d'equipe de transplantation. "
             "MedFlow AI - Usage professionnel exclusif.")

    _F(pdf, 'B', 7, C_TEAL)
    pdf.set_xy(ML + 145, footer_y + 3)
    pdf.cell(35, 4, 'Page 1/1  |  medflow-ai.fr', align='R')

    return bytes(pdf.output())
