# pdf_gen.py — génération PDF MedFlow AI Tacrolimus

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


# Helvetica (fpdf2 core font) = Latin-1 only → strip/replace all non-Latin1 chars
def _cpdf(text: str) -> str:
    if not isinstance(text, str):
        return str(text) if text else ''
    subs = {
        '—': '-', '–': '-',
        '·': '-',
        '→': '->', '←': '<-',
        '↑': '^',  '↓': 'v',
        '×': 'x',
        '≥': '>=', '≤': '<=',
        '⁺': '+',  '⁻': '-',
        ''': "'",  ''': "'",
        '"': '"',  '"': '"',
        '¹': '1',  '²': '2', '³': '3',
    }
    for k, v in subs.items():
        text = text.replace(k, v)
    return text.encode('latin-1', errors='replace').decode('latin-1')


class MedFlowPDF(FPDF if PDF_OK else object):
    def cell(self, *args, **kwargs):
        if len(args) >= 3:
            args = list(args); args[2] = _cpdf(args[2]); args = tuple(args)
        elif 'text' in kwargs:
            kwargs['text'] = _cpdf(kwargs['text'])
        return super().cell(*args, **kwargs)

    def multi_cell(self, *args, **kwargs):
        if len(args) >= 3:
            args = list(args); args[2] = _cpdf(args[2]); args = tuple(args)
        elif 'text' in kwargs:
            kwargs['text'] = _cpdf(kwargs['text'])
        return super().multi_cell(*args, **kwargs)


def make_pdf_chart(dates, values, ylabel, color_hex, ref_min=None, ref_max=None):
    if not MPL_OK or len(values) < 2:
        return None
    r = int(color_hex[1:3], 16) / 255
    g_c = int(color_hex[3:5], 16) / 255
    b = int(color_hex[5:7], 16) / 255
    fig, ax = plt.subplots(figsize=(5.2, 2.8))
    fig.patch.set_facecolor('#f8fafc')
    ax.set_facecolor('#f1f5f9')
    x_pos = list(range(len(dates)))
    ax.plot(x_pos, values, 'o-', color=(r, g_c, b), linewidth=2, markersize=5, zorder=3)
    if ref_min is not None and ref_max is not None:
        ax.axhspan(ref_min, ref_max, alpha=0.18, color='green', label=f'Cible {ref_min}–{ref_max}')
        ax.legend(fontsize=7, loc='upper right', framealpha=0.7)
    ax.set_xticks(x_pos)
    ax.set_xticklabels([d[5:10] for d in dates], fontsize=7, rotation=45)
    ax.set_ylabel(ylabel, fontsize=7.5, color='#475569')
    ax.tick_params(colors='#64748b', labelsize=7)
    ax.grid(True, alpha=0.3, linestyle='--', zorder=0)
    ax.spines[['top', 'right']].set_visible(False)
    ax.spines[['left', 'bottom']].set_color('#cbd5e1')
    plt.tight_layout(pad=0.6)
    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=150, bbox_inches='tight', facecolor='#f8fafc')
    plt.close(fig)
    buf.seek(0)
    return buf


def pdf_section(pdf, title):
    pdf.set_fill_color(30, 58, 95)
    pdf.set_draw_color(30, 58, 95)
    y = pdf.get_y()
    pdf.rect(15, y, 180, 8, 'F')
    pdf.set_text_color(241, 245, 249)
    pdf.set_font('Helvetica', 'B', 8)
    pdf.set_xy(19, y + 1.2)
    pdf.cell(0, 5.5, title)
    pdf.set_y(y + 10)


def pdf_box(pdf, x, y, w, title, rows, title_rgb=(30, 58, 95)):
    h_title = 7.5
    h_row   = 6.5
    total_h = h_title + len(rows) * h_row + 3
    pdf.set_fill_color(245, 247, 250)
    pdf.set_draw_color(203, 213, 225)
    pdf.rect(x, y, w, total_h, 'FD')
    pdf.set_fill_color(*title_rgb)
    pdf.rect(x, y, w, h_title, 'F')
    pdf.set_text_color(241, 245, 249)
    pdf.set_font('Helvetica', 'B', 7.5)
    pdf.set_xy(x + 3, y + 1.2)
    pdf.cell(w - 6, 5, title)
    for i, (lbl, val) in enumerate(rows):
        ry = y + h_title + 1.5 + i * h_row
        pdf.set_xy(x + 3, ry)
        pdf.set_text_color(100, 116, 139)
        pdf.set_font('Helvetica', '', 7)
        pdf.cell(w * 0.44, 5, lbl + ':')
        pdf.set_xy(x + 3 + w * 0.44, ry)
        pdf.set_text_color(30, 41, 59)
        pdf.set_font('Helvetica', 'B', 7.5)
        pdf.cell(w * 0.52, 5, str(val))
    return total_h


def generate_pdf(pat_nom, pat_prenom, pat_id,
                 age, sexe, poids, creat, dfg, stade, stade_desc,
                 na_val, na_label, k_val, k_label,
                 phase_label, c0, c0_statut, t_min, t_max,
                 dose_act, dose_rec, dose_pk, plafond, fr,
                 k_eleve, rec_titre, history_rows) -> bytes | None:
    if not PDF_OK:
        return None

    pdf = MedFlowPDF()
    pdf.set_auto_page_break(auto=True, margin=18)
    pdf.add_page()

    # ── En-tête ──────────────────────────────────────────────────────────────
    pdf.set_fill_color(9, 9, 11)
    pdf.rect(0, 0, 210, 32, 'F')
    pdf.set_fill_color(139, 92, 246)
    pdf.rect(0, 0, 5, 32, 'F')
    pdf.set_text_color(241, 245, 249)
    pdf.set_font('Helvetica', 'B', 17)
    pdf.set_xy(14, 6)
    pdf.cell(0, 9, 'MedFlow AI')
    pdf.set_font('Helvetica', '', 10)
    pdf.set_text_color(148, 163, 184)
    pdf.set_xy(14, 17)
    pdf.cell(0, 7, 'Rapport de suivi therapeutique - Tacrolimus - Greffe Cardiaque')
    pdf.set_xy(14, 25)
    pdf.set_font('Helvetica', 'I', 8)
    pdf.set_text_color(71, 85, 105)
    pdf.cell(0, 5, f'Genere le {datetime.now().strftime("%d/%m/%Y a %H:%M")}')
    pdf.set_y(38)

    # ── Bandeau patient ───────────────────────────────────────────────────────
    pdf.set_fill_color(239, 246, 255)
    pdf.set_draw_color(147, 197, 253)
    pdf.rect(15, pdf.get_y(), 180, 14, 'FD')
    pdf.set_xy(19, pdf.get_y() + 3)
    pdf.set_font('Helvetica', 'B', 11)
    pdf.set_text_color(30, 41, 59)
    full_name = f"{pat_prenom.capitalize()} {pat_nom.upper()}"
    pdf.cell(90, 7, full_name)
    pdf.set_font('Helvetica', '', 9)
    pdf.set_text_color(71, 85, 105)
    pdf.cell(45, 7, f'ID Patient : {pat_id}')
    n_hist = len(history_rows)
    pdf.cell(0, 7, f'{n_hist} bilan(s) enregistre(s)')
    pdf.set_y(pdf.get_y() + 14 + 6)

    # ── Bilan actuel ─────────────────────────────────────────────────────────
    pdf_section(pdf, 'BILAN ACTUEL')
    y0 = pdf.get_y()
    h1 = pdf_box(pdf, 15, y0, 88, 'Patient & Biologie renale', [
        ('Age / Sexe',            f'{age} ans - {sexe}'),
        ('Poids',                 f'{poids} kg'),
        ('Creatinine',            f'{creat} umol/L'),
        ('DFG (Cockcroft-Gault)', f'{dfg} mL/min'),
        ('Stade KDIGO',           f'{stade} - {stade_desc}'),
    ])
    h2 = pdf_box(pdf, 107, y0, 88, 'Tacrolimus & Ionogramme', [
        ('Phase post-greffe', phase_label.split('(')[0].strip()[:30]),
        ('C0 residuel',       f'{c0} ng/mL ({c0_statut})'),
        ('Cible C0',          f'{t_min}-{t_max} ng/mL'),
        ('Dose actuelle',     f'{dose_act} mg/j'),
        ('Natremie Na+',      f'{na_val} mmol/L - {na_label}'),
        ('Kaliemie K+',       f'{k_val} mmol/L - {k_label}'),
    ])
    pdf.set_y(y0 + max(h1, h2) + 6)

    # ── Recommandation ────────────────────────────────────────────────────────
    dose_prise = arrondir_05(dose_rec / 2)
    if 'urgent' in rec_titre.lower() or 'impératif' in rec_titre.lower() or 'Avis expert' in rec_titre:
        box_rgb = (28, 5, 5); border_rgb = (220, 38, 38)
    elif '⚠' in rec_titre:
        box_rgb = (28, 16, 5); border_rgb = (249, 115, 22)
    else:
        box_rgb = (7, 26, 16); border_rgb = (16, 185, 129)

    rec_y = pdf.get_y()
    pdf.set_fill_color(*box_rgb)
    pdf.set_draw_color(*border_rgb)
    pdf.rect(15, rec_y, 180, 28, 'FD')
    rec_titre_clean = rec_titre.replace('✅', '').replace('⚠️', '').replace('🚫', '').strip()
    pdf.set_xy(20, rec_y + 3)
    pdf.set_text_color(100, 116, 139)
    pdf.set_font('Helvetica', 'B', 7)
    pdf.cell(0, 5, rec_titre_clean)
    pdf.set_xy(20, rec_y + 9)
    pdf.set_text_color(241, 245, 249)
    pdf.set_font('Helvetica', 'B', 20)
    pdf.cell(55, 12, f'{dose_rec} mg/j')
    pdf.set_xy(78, rec_y + 12)
    pdf.set_font('Helvetica', '', 10)
    pdf.set_text_color(147, 197, 253)
    pdf.cell(0, 8, f'{dose_prise} mg matin + {dose_prise} mg soir  (q12h, capsules Prograf)')
    pdf.set_y(rec_y + 32)

    # ── Interprétation clinique ───────────────────────────────────────────────
    pdf.ln(3)
    pdf_section(pdf, 'INTERPRETATION CLINIQUE - JUSTIFICATION DE LA RECOMMANDATION')
    expl_items = build_clinical_explanation(
        age, sexe, poids, dfg, stade, stade_desc,
        phase_label, c0, c0_statut, t_min, t_max,
        dose_act, dose_rec, dose_pk, plafond, fr,
        k_val, k_eleve
    )
    for num, (title_e, body_e) in enumerate(expl_items, 1):
        if pdf.get_y() > 260:
            pdf.add_page()
        ty = pdf.get_y()
        pdf.set_fill_color(14, 116, 144)
        pdf.rect(15, ty, 180, 7, 'F')
        pdf.set_xy(19, ty + 1)
        pdf.set_font('Helvetica', 'B', 7.5)
        pdf.set_text_color(255, 255, 255)
        pdf.cell(0, 5, f'{num}. {title_e}')
        pdf.set_y(ty + 7)
        pdf.set_fill_color(240, 249, 255)
        pdf.set_text_color(30, 41, 59)
        pdf.set_font('Helvetica', '', 8)
        pdf.set_xy(18, pdf.get_y())
        pdf.multi_cell(177, 5, body_e, fill=True)
        pdf.set_y(pdf.get_y() + 2)
    pdf.ln(3)

    # ── Raisonnement clinique ─────────────────────────────────────────────────
    if pdf.get_y() > 230:
        pdf.add_page()
    pdf.ln(1)
    pdf_section(pdf, 'RAISONNEMENT CLINIQUE ET METHODOLOGIE')
    t_mid_val = (t_min + t_max) / 2
    raw_pk = round(dose_act * t_mid_val / c0, 2) if c0 > 0 else dose_act
    k_note = f' | K+ {k_val} > 5.5 => dose plafonnee a dose actuelle ({dose_act} mg/j)' if k_eleve else ''
    lines = [
        ('1. Cockcroft-Gault (1976)',
         f'DFG = ((140-{age}) x {poids} x {"1.00" if sexe == "Homme" else "0.85"}) / (0.815 x {creat}) = {dfg} mL/min => {stade}'),
        ('2. Ajustement PK proportionnel (Staatz & Tett, 2004)',
         f'{dose_act} mg/j x ({t_mid_val} / {c0}) = {raw_pk} mg/j => arrondi capsule 0.5 mg => {dose_pk} mg/j'),
        ('3. Plafond nephroprotecteur (Ojo 2003, Naesens 2009, Ekberg 2007)',
         f'{poids} kg x 0.1 mg/kg x facteur DFG {fr} (stade {stade}) = {plafond} mg/j'),
        ('4. Decision finale',
         f'min(PK {dose_pk}, plafond {plafond}{k_note}) = {dose_rec} mg/j => {dose_prise} mg x 2 /j (q12h)'),
    ]
    ry = pdf.get_y()
    total_lines_h = len(lines) * 14 + 6
    pdf.set_fill_color(248, 250, 252)
    pdf.set_draw_color(226, 232, 240)
    pdf.rect(15, ry, 180, total_lines_h, 'FD')
    pdf.set_y(ry + 3)
    for step_lbl, step_val in lines:
        pdf.set_xy(19, pdf.get_y())
        pdf.set_font('Helvetica', 'B', 7.5)
        pdf.set_text_color(30, 58, 95)
        pdf.cell(0, 5, step_lbl)
        pdf.set_xy(22, pdf.get_y() + 5)
        pdf.set_font('Helvetica', '', 7.5)
        pdf.set_text_color(30, 41, 59)
        pdf.cell(0, 5, step_val)
        pdf.set_y(pdf.get_y() + 6)
    pdf.ln(4)

    # ── Historique ────────────────────────────────────────────────────────────
    if history_rows:
        if pdf.get_y() > 210:
            pdf.add_page()
        pdf_section(pdf, f'HISTORIQUE DES BILANS ({len(history_rows)} consultation(s))')
        cols   = ['Date & Heure', 'DFG (mL/min)', 'Stade', 'C0 (ng/mL)', 'Dose rec. (mg/j)', 'K+ (mmol/L)', 'Na+ (mmol/L)', 'Statut C0']
        widths = [35, 22, 13, 22, 24, 22, 22, 22]
        th = pdf.get_y()
        pdf.set_fill_color(51, 65, 85)
        pdf.set_text_color(241, 245, 249)
        pdf.set_font('Helvetica', 'B', 6.5)
        x0 = 15
        for col, w in zip(cols, widths):
            pdf.set_xy(x0, th)
            pdf.cell(w, 6, col, fill=True)
            x0 += w
        pdf.set_y(th + 6)
        alt = [(248, 250, 252), (241, 245, 249)]
        for i, row in enumerate(history_rows):
            if pdf.get_y() > 270:
                pdf.add_page()
                th2 = pdf.get_y()
                pdf.set_fill_color(51, 65, 85)
                pdf.set_text_color(241, 245, 249)
                pdf.set_font('Helvetica', 'B', 6.5)
                x0 = 15
                for col, w in zip(cols, widths):
                    pdf.set_xy(x0, th2)
                    pdf.cell(w, 6, col, fill=True)
                    x0 += w
                pdf.set_y(th2 + 6)
            bg = alt[i % 2]
            pdf.set_fill_color(*bg)
            pdf.set_text_color(30, 41, 59)
            pdf.set_font('Helvetica', '', 6.5)
            vals = [
                row[0][:16],
                f"{row[5]:.0f}",
                row[6],
                f"{row[10]:.1f}",
                f"{row[12]:.1f}",
                f"{row[8]:.1f}",
                f"{row[7]:.0f}",
                row[16],
            ]
            row_y = pdf.get_y()
            x0 = 15
            for val, w in zip(vals, widths):
                pdf.set_xy(x0, row_y)
                pdf.cell(w, 5.5, val, fill=True)
                x0 += w
            pdf.set_y(row_y + 5.5)
        pdf.ln(5)

        # Graphiques d'évolution
        if MPL_OK and len(history_rows) >= 2:
            if pdf.get_y() > 160:
                pdf.add_page()
            pdf_section(pdf, "GRAPHIQUES D'EVOLUTION")
            dates  = [r[0] for r in history_rows]
            charts = [
                (dates, [r[5]  for r in history_rows], "DFG (mL/min)",        "#3b82f6", None, None),
                (dates, [r[10] for r in history_rows], "C0 residuel (ng/mL)", "#8b5cf6", 5, 15),
                (dates, [r[12] for r in history_rows], "Dose rec. (mg/j)",    "#10b981", None, None),
                (dates, [r[8]  for r in history_rows], "Kaliemie K+ (mmol/L)","#f59e0b", 3.5, 5.0),
            ]
            cy = pdf.get_y()
            bufs = [make_pdf_chart(*c) for c in charts]
            for idx, buf in enumerate(bufs):
                if buf is None:
                    continue
                col_x  = 15 if idx % 2 == 0 else 107
                row_y2 = cy if idx < 2 else (cy + 62)
                pdf.image(buf, x=col_x, y=row_y2, w=88)
            pdf.set_y(cy + 62 * 2 + 4)

    # ── Disclaimer ────────────────────────────────────────────────────────────
    if pdf.get_y() > 270:
        pdf.add_page()
    pdf.ln(4)
    dy = pdf.get_y()
    pdf.set_fill_color(248, 250, 252)
    pdf.set_draw_color(203, 213, 225)
    pdf.rect(15, dy, 180, 16, 'FD')
    pdf.set_xy(19, dy + 3)
    pdf.set_font('Helvetica', 'I', 7.5)
    pdf.set_text_color(100, 116, 139)
    pdf.multi_cell(172, 5,
        "Outil d'aide a la decision clinique - Ne remplace pas la concertation d'equipe de transplantation. "
        "Adapter systematiquement au protocole institutionnel. "
        "MedFlow AI - Usage professionnel exclusif.")

    # ── Numéros de page ───────────────────────────────────────────────────────
    total_pages = len(pdf.pages)
    for p in range(1, total_pages + 1):
        pdf.page = p
        pdf.set_y(-12)
        pdf.set_font('Helvetica', '', 7)
        pdf.set_text_color(100, 116, 139)
        pdf.cell(0, 5, f'Page {p}/{total_pages}  |  MedFlow AI - Tacrolimus Greffe Cardiaque', align='C')

    pdf.page = total_pages
    return bytes(pdf.output())
