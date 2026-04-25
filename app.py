import streamlit as st
import sqlite3
import hashlib
import io
import os
from datetime import datetime

try:
    from fpdf import FPDF
    PDF_OK = True
except ImportError:
    PDF_OK = False

try:
    import plotly.graph_objects as go
    PLOTLY_OK = True
except ImportError:
    PLOTLY_OK = False

try:
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    MPL_OK = True
except ImportError:
    MPL_OK = False

# Helvetica (fpdf2 core font) = Latin-1 only → strip/replace all non-Latin1 chars
def _cpdf(text: str) -> str:
    if not isinstance(text, str):
        return str(text) if text else ''
    subs = {
        '—': '-', '–': '-',   # — –  em/en dash
        '·': '-',                   # ·  middle dot
        '→': '->', '←': '<-',  # → ←
        '↑': '^',  '↓': 'v',  # ↑ ↓
        '×': 'x',                   # ×
        '≥': '>=', '≤': '<=',  # ≥ ≤
        '⁺': '+',  '⁻': '-',  # ⁺ ⁻
        '’': "'",  '‘': "'",  # ' '
        '“': '"',  '”': '"',  # " "
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

# ─── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Tacrolimus — Greffe Cardiaque · MedFlow AI",
    page_icon="🫀",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.markdown("""
<style>
[data-testid="stAppViewContainer"] { background: #09090b; color: #f1f5f9; }
[data-testid="stSidebar"] { display: none; }
[data-testid="stHeader"] { background: transparent; }
[data-testid="stMainBlockContainer"] { padding-top: 1.5rem; }
.stNumberInput label, .stSelectbox label, .stRadio label,
.stTextInput label { color: #94a3b8 !important; font-size: 0.82rem !important; }
.stNumberInput input, .stTextInput input {
  background: #18181b !important; border: 1px solid #27272a !important;
  color: #f1f5f9 !important; border-radius: 8px !important; }
.stSelectbox > div > div {
  background: #18181b !important; border: 1px solid #27272a !important;
  color: #f1f5f9 !important; border-radius: 8px !important; }
div[data-baseweb="radio"] > label > div:first-child {
  background: #27272a !important; border-color: #3f3f46 !important; }
.stRadio [data-testid="stMarkdownContainer"] p { color: #d1d5db; font-size: 0.88rem; }
.stExpander { background: #111113 !important; border: 1px solid #27272a !important;
  border-radius: 10px !important; }
.stExpander summary { color: #94a3b8 !important; }
.stButton > button { border-radius: 8px !important; font-weight: 600 !important; }
.stDownloadButton > button { border-radius: 8px !important; font-weight: 600 !important; }
hr { border-color: #27272a; }
footer { visibility: hidden; }
</style>
""", unsafe_allow_html=True)

# ─── Base de données SQLite ────────────────────────────────────────────────────
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "patients.db")

def init_db():
    con = sqlite3.connect(DB_PATH)
    con.execute("""CREATE TABLE IF NOT EXISTS patients (
        id TEXT PRIMARY KEY,
        nom TEXT NOT NULL,
        prenom TEXT NOT NULL,
        created_at TEXT NOT NULL
    )""")
    con.execute("""CREATE TABLE IF NOT EXISTS consultations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        patient_id TEXT NOT NULL,
        date_consult TEXT NOT NULL,
        age INTEGER,
        sexe TEXT,
        poids REAL,
        creatinine REAL,
        dfg REAL,
        stade TEXT,
        na_val REAL,
        k_val REAL,
        phase TEXT,
        c0 REAL,
        dose_actuelle REAL,
        dose_recommandee REAL,
        dose_pk REAL,
        plafond REAL,
        facteur_dfg REAL,
        c0_statut TEXT,
        na_statut TEXT,
        k_statut TEXT,
        FOREIGN KEY (patient_id) REFERENCES patients(id)
    )""")
    con.commit()
    con.close()

init_db()

def generate_patient_id(nom: str, prenom: str) -> str:
    key = f"{prenom.strip().lower()}{nom.strip().lower()}"
    return hashlib.sha256(key.encode()).hexdigest()[:8].upper()

def upsert_patient(pid: str, nom: str, prenom: str):
    con = sqlite3.connect(DB_PATH)
    con.execute(
        "INSERT OR IGNORE INTO patients (id, nom, prenom, created_at) VALUES (?,?,?,?)",
        (pid, nom.strip().upper(), prenom.strip().capitalize(), datetime.now().isoformat())
    )
    con.commit()
    con.close()

def save_consultation(pid, age, sexe, poids, creat, dfg, stade, na, k, phase,
                      c0, dose_act, dose_rec, dose_pk, plafond, fr,
                      c0_statut, na_statut, k_statut):
    con = sqlite3.connect(DB_PATH)
    con.execute("""INSERT INTO consultations
        (patient_id, date_consult, age, sexe, poids, creatinine, dfg, stade,
         na_val, k_val, phase, c0, dose_actuelle, dose_recommandee, dose_pk,
         plafond, facteur_dfg, c0_statut, na_statut, k_statut)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (pid, datetime.now().strftime("%Y-%m-%d %H:%M"),
         age, sexe, poids, creat, dfg, stade, na, k, phase,
         c0, dose_act, dose_rec, dose_pk, plafond, fr,
         c0_statut, na_statut, k_statut))
    con.commit()
    con.close()

def get_consultations(pid: str) -> list:
    con = sqlite3.connect(DB_PATH)
    cur = con.execute("""SELECT date_consult, age, sexe, poids, creatinine,
        dfg, stade, na_val, k_val, phase, c0, dose_actuelle, dose_recommandee,
        dose_pk, plafond, facteur_dfg, c0_statut, na_statut, k_statut
        FROM consultations WHERE patient_id=? ORDER BY date_consult""", (pid,))
    rows = cur.fetchall()
    con.close()
    return rows

def count_consultations(pid: str) -> int:
    con = sqlite3.connect(DB_PATH)
    n = con.execute("SELECT COUNT(*) FROM consultations WHERE patient_id=?", (pid,)).fetchone()[0]
    con.close()
    return n

# ─── Constantes ───────────────────────────────────────────────────────────────
PHASES = {
    "M0 – M3  (phase précoce)":  {"min": 10, "max": 15, "label": "M0–M3"},
    "M3 – M12  (maintenance)":   {"min": 8,  "max": 12, "label": "M3–M12"},
    "> 1 an  (phase stable)":    {"min": 5,  "max": 10, "label": ">1 an"},
}

REFS = [
    ("ISHLT Guidelines 2016",   "Kobashigawa J et al. J Heart Lung Transplant. 2016;35(1):1–23. Recommandations immunosuppression post-greffe cardiaque."),
    ("ISHLT Registry 2022",     "Stehlik J et al. J Heart Lung Transplant. 2022;41(10):1336–1347. Registre international — survie et immunosuppression."),
    ("CNI Néphrotoxicité",      "Naesens M et al. Clin J Am Soc Nephrol. 2009;4(2):481–508. Mécanismes et gestion de la toxicité rénale aux CNI."),
    ("Greffe non rénale / IRC", "Ojo AO et al. N Engl J Med. 2003;349:931–940. IRC chronique après greffe non rénale — CNI facteur indépendant."),
    ("SYMPHONY / CNI réduit",   "Ekberg H et al. N Engl J Med. 2007;357:2562–2575. Réduction exposition CNI → meilleure préservation rénale à 1 an."),
    ("Cockcroft-Gault",         "Cockcroft DW, Gault MH. Nephron. 1976;16(1):31–41. Formule de référence pour la clairance de la créatinine."),
    ("Tacrolimus PK",           "Staatz CE, Tett SE. Clin Pharmacokinet. 2004;43(10):623–653. PK/PD tacrolimus — ajustement par taux résiduel."),
    ("Hyperkaliémie / CNI",     "Tumlin JA et al. Am J Kidney Dis. 1996;28(4):505–511. Hyperkaliémie induite par les CNI : mécanisme et prise en charge."),
]

META_DATA = [
    ("Ojo et al.",            "N Engl J Med 2003",           "69 321",    "16,5 % IRC sévère à 5 ans sous CNI (greffe cardiaque)",           "Justifie le plafond rénal 0,1 mg/kg × facteur DFG"),
    ("Ekberg et al. SYMPHONY","N Engl J Med 2007",           "1 645",     "DFG +8,3 mL/min si CNI réduit vs standard (p < 0,001)",          "Valide la réduction de dose par stade IRC"),
    ("Naesens et al.",        "CJASN 2009",                  "revue syst.","Toxicité CNI dose-dépendante ; réduction ↓ progression IRC",     "Justifie les facteurs de correction G1–G5"),
    ("ISHLT Registry",        "J Heart Lung Transplant 2022",">140 000",  "Tacrolimus = protocole dominant (> 95 % des greffes cardiaques)", "Valide les cibles C0 par phase post-greffe"),
    ("Staatz & Tett",         "Clin Pharmacokinet 2004",     "revue PK",  "Corrélation C0/AUC r = 0,89 — ajustement proportionnel validé",  "Base de la règle de trois PK de l'outil"),
    ("Tumlin et al.",         "Am J Kidney Dis 1996",        "série",     "Hyperkaliémie CNI : bloc tubulaire aldostérone-like",             "Justifie l'alerte K⁺ et la limite de dose si K > 5,5"),
]

# ─── Fonctions de calcul ──────────────────────────────────────────────────────
def calc_dfg(age, poids, sexe, creat_umol):
    F = 1.0 if sexe == "Homme" else 0.85
    return max(round(((140 - age) * poids * F) / (0.815 * creat_umol), 1), 0.0)

def get_stade(dfg):
    if dfg >= 90: return "G1",  "Normale",           "#10b981"
    if dfg >= 60: return "G2",  "Légèrement ↓",      "#84cc16"
    if dfg >= 45: return "G3a", "Légère–modérée ↓",  "#f59e0b"
    if dfg >= 30: return "G3b", "Modérée–sévère ↓",  "#f97316"
    if dfg >= 15: return "G4",  "Sévèrement ↓",      "#ef4444"
    return               "G5",  "Terminale",          "#dc2626"

def arrondir_05(v):
    return round(round(v / 0.5) * 0.5, 1)

def interp_sodium(na):
    if na < 125:  return "Hyponatrémie sévère", "#dc2626", "🔴", True
    if na < 135:  return "Hyponatrémie",        "#f97316", "⚠️", False
    if na <= 145: return "Normal",              "#10b981", "✅", False
    return               "Hypernatrémie",       "#f97316", "⚠️", False

def interp_potassium(k):
    if k > 6.0:  return "Hyperkaliémie urgente", "#dc2626", "🔴", True
    if k > 5.5:  return "Hyperkaliémie sig.",     "#ef4444", "🔴", True
    if k > 5.0:  return "Hyperkaliémie légère",   "#f97316", "⚠️", False
    if k >= 3.5: return "Normal",                 "#10b981", "✅", False
    if k >= 3.0: return "Hypokaliémie",           "#f97316", "⚠️", False
    return              "Hypokaliémie sévère",    "#dc2626", "🔴", True

def recommander_tacrolimus(dose_act, c0, t_min, t_max, dfg, poids, k_eleve=False):
    t_mid   = (t_min + t_max) / 2
    dose_pk = dose_act * (t_mid / c0) if c0 > 0 else dose_act
    if   dfg >= 60: fr = 1.00
    elif dfg >= 45: fr = 0.90
    elif dfg >= 30: fr = 0.80
    elif dfg >= 15: fr = 0.70
    else:           fr = 0.50
    plafond     = poids * 0.1 * fr
    dose_finale = min(dose_pk, plafond)
    if k_eleve:
        dose_finale = min(dose_finale, dose_act)
    dose_finale = max(dose_finale, 0.5)
    return arrondir_05(dose_finale), arrondir_05(dose_pk), arrondir_05(plafond), fr

def delta_str(new_val, old_val):
    if old_val <= 0: return None, "#94a3b8"
    d = round((new_val - old_val) / old_val * 100, 1)
    return (f"+{d} %" if d > 0 else f"{d} %"), ("#10b981" if d > 0 else ("#ef4444" if d < -5 else "#f59e0b"))

# ─── Graphiques Matplotlib pour PDF ──────────────────────────────────────────
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

# ─── Interprétation clinique ─────────────────────────────────────────────────
def build_clinical_explanation(age, sexe, poids, dfg, stade, stade_desc,
                                phase_label, c0, c0_statut, t_min, t_max,
                                dose_act, dose_rec, dose_pk, plafond, fr,
                                k_val, k_eleve):
    """Retourne une liste de (titre, corps) paragraphes cliniques justifiant la dose."""
    phase_short = phase_label.split('(')[0].strip()
    stade_clean = stade_desc.replace('↓', 'dim.').replace('–', '-').replace('—', '-')
    t_mid = round((t_min + t_max) / 2, 1)
    items = []

    # 1. Contexte clinique
    items.append((
        "Contexte clinique",
        f"Patient de {age} ans ({sexe}), {poids} kg, greffe cardiaque en phase {phase_short}. "
        f"Fonction renale estimee par Cockcroft-Gault : DFG = {dfg} mL/min, stade KDIGO {stade} "
        f"({stade_clean}). C'est ce contexte renal qui conditionne le plafond de dose de tacrolimus."
    ))

    # 2. Analyse pharmacocinétique C0
    if "sub" in c0_statut.lower():
        c0_body = (
            f"C0 = {c0} ng/mL est subtherapeutique (cible {t_min}-{t_max} ng/mL pour la phase "
            f"{phase_short}). Un taux residuel insuffisant expose au risque de rejet aigu cellulaire "
            f"ou humoral, particulierement critique en periode post-greffe precoce. "
            f"L'ajustement PK proportionnel (Staatz & Tett, Clin Pharmacokinet 2004 — r C0/AUC = 0,89) "
            f"recommande une dose de {dose_pk} mg/j pour atteindre C0 ~ {t_mid} ng/mL."
        )
    elif "supra" in c0_statut.lower():
        c0_body = (
            f"C0 = {c0} ng/mL est supratherapeutique (cible {t_min}-{t_max} ng/mL). "
            f"Un taux excessif majore les risques de nephrotoxicite (fibrose interstitielle), "
            f"de neurotoxicite (tremblements, encephalopathie) et d'infections opportunistes. "
            f"La reduction est necessaire ; l'ajustement PK proportionnel suggere {dose_pk} mg/j."
        )
    else:
        c0_body = (
            f"C0 = {c0} ng/mL est dans la cible therapeutique ({t_min}-{t_max} ng/mL). "
            f"L'immunosuppression est optimale pour la phase {phase_short}. "
            f"L'ajustement PK confirme {dose_pk} mg/j comme dose de maintien."
        )
    items.append(("Analyse pharmacocinetique (C0 residuel)", c0_body))

    # 3. Plafond nephroprotecteur
    if dose_rec == plafond and abs(dose_pk - plafond) > 0.1:
        nephro_body = (
            f"La dose calculee par PK ({dose_pk} mg/j) depasse le plafond nephroprotecteur "
            f"({plafond} mg/j). Ce plafond est issu de la formule : {poids} kg x 0,1 mg/kg x "
            f"facteur DFG {fr} (stade {stade}). La nephrotoxicite du tacrolimus est dose-dependante "
            f"(Naesens et al., CJASN 2009 ; Ojo et al., NEJM 2003 : 16,5% d'IRC severe a 5 ans sous "
            f"CNI, n = 69 321 greffes non renales). L'etude SYMPHONY (Ekberg et al., NEJM 2007, "
            f"n = 1 645) demontre qu'une exposition reduite aux CNI ameliore le DFG de +8,3 mL/min. "
            f"La protection de la fonction renale residuelle prime sur l'optimisation PK : "
            f"dose retenue = {plafond} mg/j."
        )
        items.append(("Plafond nephroprotecteur — priorite renale", nephro_body))
    elif dose_rec > dose_act:
        items.append(("Augmentation de dose",
            f"La dose augmente de {dose_act} mg/j a {dose_rec} mg/j conformement a l'ajustement PK, "
            f"en restant sous le plafond nephroprotecteur de {plafond} mg/j (stade {stade}, facteur {fr})."))
    elif dose_rec < dose_act and not k_eleve:
        items.append(("Reduction de dose",
            f"La dose est reduite de {dose_act} mg/j a {dose_rec} mg/j pour corriger le surdosage "
            f"et limiter la toxicite, dans le respect du plafond nephroprotecteur de {plafond} mg/j."))

    # 4. Hyperkaliémie
    if k_eleve:
        items.append(("Hyperkaliemie — contrainte additionnelle",
            f"K+ = {k_val} mmol/L (> 5,5 mmol/L). Le tacrolimus inhibe la reabsorption tubulaire "
            f"du potassium via un mecanisme aldosterone-like (Tumlin et al., Am J Kidney Dis 1996), "
            f"aggravant l'hyperkaliemie de facon dose-dependante. Toute augmentation est contre-indiquee. "
            f"Dose maintenue a {dose_act} mg/j. Prise en charge : regime pauvre en K+, resines "
            f"echangeuses (patiromer, zirconium), correction etiologique, avis nephrologue si > 6 mmol/L."))

    # 5. Conclusion
    dose_prise_c = arrondir_05(dose_rec / 2)
    items.append(("Conclusion et posologie",
        f"Dose recommandee : {dose_rec} mg/j soit {dose_prise_c} mg matin + {dose_prise_c} mg soir "
        f"(q12h, capsules Prograf). Cette posologie represente le meilleur compromis entre l'efficacite "
        f"immunosuppressive et la preservation de la fonction renale, conformement aux recommandations "
        f"ISHLT 2016 (Kobashigawa et al., J Heart Lung Transplant) et aux donnees de la litterature."))

    return items


def _estimate_expl_height(items, cpl=85, lh=5, th=5.5, gap=3):
    """Estime la hauteur PDF (mm) d'un bloc d'explication clinique."""
    total = 6
    for _, body in items:
        total += th + max(1, -(-len(body) // cpl)) * lh + gap
    return total


# ─── Génération PDF ───────────────────────────────────────────────────────────
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
    pdf.cell(0, 7, 'Rapport de suivi therapeutique — Tacrolimus · Greffe Cardiaque')
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
        ('Age / Sexe',   f'{age} ans — {sexe}'),
        ('Poids',        f'{poids} kg'),
        ('Creatinine',   f'{creat} umol/L'),
        ('DFG (Cockcroft-Gault)', f'{dfg} mL/min'),
        ('Stade KDIGO',  f'{stade} — {stade_desc}'),
    ])
    h2 = pdf_box(pdf, 107, y0, 88, 'Tacrolimus & Ionogramme', [
        ('Phase post-greffe', phase_label.split('(')[0].strip()[:30]),
        ('C0 residuel',  f'{c0} ng/mL ({c0_statut})'),
        ('Cible C0',     f'{t_min}–{t_max} ng/mL'),
        ('Dose actuelle',f'{dose_act} mg/j'),
        ('Natremie Na+', f'{na_val} mmol/L — {na_label}'),
        ('Kalieme K+',   f'{k_val} mmol/L — {k_label}'),
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
    rec_titre_clean = rec_titre.replace('✅','').replace('⚠️','').replace('🚫','').strip()
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
    pdf_section(pdf, 'INTERPRETATION CLINIQUE — JUSTIFICATION DE LA RECOMMANDATION')
    expl_items = build_clinical_explanation(
        age, sexe, poids, dfg, stade, stade_desc,
        phase_label, c0, c0_statut, t_min, t_max,
        dose_act, dose_rec, dose_pk, plafond, fr,
        k_val, k_eleve
    )
    pdf.set_fill_color(240, 249, 255)
    for num, (title_e, body_e) in enumerate(expl_items, 1):
        if pdf.get_y() > 260:
            pdf.add_page()
            pdf.set_fill_color(240, 249, 255)
        # Barre titre teal
        ty = pdf.get_y()
        pdf.set_fill_color(14, 116, 144)
        pdf.rect(15, ty, 180, 7, 'F')
        pdf.set_xy(19, ty + 1)
        pdf.set_font('Helvetica', 'B', 7.5)
        pdf.set_text_color(255, 255, 255)
        pdf.cell(0, 5, f'{num}. {title_e}')
        pdf.set_y(ty + 7)
        # Corps
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
         f'DFG = ((140-{age}) x {poids} x {"1.00" if sexe=="Homme" else "0.85"}) / (0.815 x {creat}) = {dfg} mL/min => {stade}'),
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
        # Table
        cols  = ['Date & Heure', 'DFG (mL/min)', 'Stade', 'C0 (ng/mL)', 'Dose rec. (mg/j)', 'K+ (mmol/L)', 'Na+ (mmol/L)', 'Statut C0']
        widths = [35, 22, 13, 22, 24, 22, 22, 22]
        # Header row
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
                (dates, [r[8]  for r in history_rows], "Kalieme K+ (mmol/L)", "#f59e0b", 3.5, 5.0),
            ]
            cy = pdf.get_y()
            bufs = [make_pdf_chart(*c) for c in charts]
            for idx, buf in enumerate(bufs):
                if buf is None:
                    continue
                col_x = 15 if idx % 2 == 0 else 107
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
        "Outil d'aide a la decision clinique — Ne remplace pas la concertation d'equipe de transplantation. "
        "Adapter systematiquement au protocole institutionnel. "
        "MedFlow AI — Usage professionnel exclusif.")

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

# ─── EN-TÊTE ──────────────────────────────────────────────────────────────────
st.markdown("""
<div style="padding:0 0 6px">
  <div style="display:flex;align-items:center;gap:14px">
    <span style="font-size:2rem">🫀</span>
    <div>
      <div style="font-size:1.65rem;font-weight:800;color:#f1f5f9">Tacrolimus — Greffe Cardiaque</div>
      <div style="color:#64748b;font-size:0.82rem;margin-top:2px">Dosage adapté · Ionogramme intégré · Suivi patient longitudinal · MedFlow AI</div>
    </div>
  </div>
</div>
""", unsafe_allow_html=True)
st.markdown("---")

# ─── IDENTIFICATION PATIENT ───────────────────────────────────────────────────
st.markdown("<div style='color:#8b5cf6;font-size:0.7rem;text-transform:uppercase;letter-spacing:.08em;font-weight:700;margin-bottom:10px'>👤 Identification du patient</div>", unsafe_allow_html=True)
pid_c1, pid_c2, pid_c3 = st.columns([1, 1, 2], gap="medium")
with pid_c1:
    pat_nom    = st.text_input("Nom de famille", placeholder="DUPONT", key="nom")
with pid_c2:
    pat_prenom = st.text_input("Prénom", placeholder="Jean", key="prenom")

patient_valid = bool(pat_nom.strip() and pat_prenom.strip())
if patient_valid:
    pat_id = generate_patient_id(pat_nom, pat_prenom)
    nb_hist = count_consultations(pat_id)
    with pid_c3:
        if nb_hist > 0:
            st.markdown(f"""<div style="background:#0f1a2e;border:1px solid #3b82f6;border-radius:10px;padding:12px 16px;margin-top:22px">
              <span style="color:#93c5fd;font-size:0.9rem;font-weight:700">#{pat_id}</span>
              <span style="color:#64748b;font-size:0.8rem"> — Patient connu · </span>
              <span style="color:#10b981;font-weight:600;font-size:0.8rem">{nb_hist} bilan(s) enregistré(s)</span>
            </div>""", unsafe_allow_html=True)
        else:
            st.markdown(f"""<div style="background:#111113;border:1px solid #3f3f46;border-radius:10px;padding:12px 16px;margin-top:22px">
              <span style="color:#93c5fd;font-size:0.9rem;font-weight:700">#{pat_id}</span>
              <span style="color:#64748b;font-size:0.8rem"> — Nouveau patient</span>
            </div>""", unsafe_allow_html=True)
else:
    with pid_c3:
        st.markdown("""<div style="background:#111113;border:1px dashed #3f3f46;border-radius:10px;padding:12px 16px;margin-top:22px;color:#475569;font-size:0.82rem">
          Saisir nom et prénom pour identifier le patient
        </div>""", unsafe_allow_html=True)
    pat_id = None

st.markdown("---")

# ─── FORMULAIRE ───────────────────────────────────────────────────────────────
col_pat, col_ion, col_tac = st.columns([1.1, 0.9, 1], gap="large")

with col_pat:
    st.markdown("<div style='color:#8b5cf6;font-size:0.7rem;text-transform:uppercase;letter-spacing:.08em;font-weight:700;margin-bottom:8px'>🧬 Données cliniques</div>", unsafe_allow_html=True)
    age   = st.number_input("Âge (ans)",           min_value=18,    max_value=100,    value=55,    step=1)
    sexe  = st.radio("Sexe biologique",             ["Homme", "Femme"], horizontal=True)
    poids = st.number_input("Poids (kg)",           min_value=30.0,  max_value=250.0,  value=70.0,  step=0.5)
    creat = st.number_input("Créatinine (µmol/L)",  min_value=20.0,  max_value=2000.0, value=120.0, step=1.0)

with col_ion:
    st.markdown("<div style='color:#06b6d4;font-size:0.7rem;text-transform:uppercase;letter-spacing:.08em;font-weight:700;margin-bottom:8px'>🧪 Ionogramme sanguin</div>", unsafe_allow_html=True)
    na_val = st.number_input("Natrémie — Na⁺ (mmol/L)", min_value=100.0, max_value=170.0, value=140.0, step=1.0)
    k_val  = st.number_input("Kaliémie — K⁺ (mmol/L)",  min_value=1.0,   max_value=10.0,  value=4.5,   step=0.1)

with col_tac:
    st.markdown("<div style='color:#10b981;font-size:0.7rem;text-transform:uppercase;letter-spacing:.08em;font-weight:700;margin-bottom:8px'>💊 Tacrolimus (Prograf®)</div>", unsafe_allow_html=True)
    phase_label = st.selectbox("Phase post-greffe", list(PHASES.keys()))
    c0          = st.number_input("C0 résiduel (ng/mL)",   min_value=0.1,  max_value=50.0,  value=12.0,  step=0.1)
    dose_tac    = st.number_input("Dose actuelle (mg/j)",  min_value=0.5,  max_value=30.0,  value=5.0,   step=0.5)

with st.expander("📈  Bilan précédent — comparaison longitudinale (optionnel)"):
    lc1, lc2, lc3 = st.columns(3)
    with lc1: creat_prec = st.number_input("Créatinine précédente (µmol/L)", min_value=0.0, max_value=2000.0, value=0.0, step=1.0)
    with lc2: c0_prec    = st.number_input("C0 précédent (ng/mL)",           min_value=0.0, max_value=50.0,   value=0.0, step=0.1)
    with lc3: dose_prec  = st.number_input("Dose Tac précédente (mg/j)",     min_value=0.0, max_value=30.0,   value=0.0, step=0.5)

# ─── CALCULS ──────────────────────────────────────────────────────────────────
phase        = PHASES[phase_label]
t_min, t_max = phase["min"], phase["max"]
dfg          = calc_dfg(age, poids, sexe, creat)
stade, stade_desc, stade_color = get_stade(dfg)

na_label, na_color, na_icon, na_urgent = interp_sodium(na_val)
k_label,  k_color,  k_icon,  k_urgent  = interp_potassium(k_val)
k_eleve = k_val > 5.5

dose_rec, dose_pk, plafond, fr = recommander_tacrolimus(dose_tac, c0, t_min, t_max, dfg, poids, k_eleve)
dose_prise = arrondir_05(dose_rec / 2)

if   c0 < t_min: c0_statut, c0_color_hex, c0_icon = "subthérapeutique",  "#ef4444", "🔴"
elif c0 > t_max: c0_statut, c0_color_hex, c0_icon = "suprathérapeutique","#f59e0b", "⚠️"
else:            c0_statut, c0_color_hex, c0_icon = "thérapeutique",      "#10b981", "✅"

var_tac_label, var_tac_color = delta_str(dose_rec, dose_tac)
dfg_prec      = calc_dfg(age, poids, sexe, creat_prec) if creat_prec > 0 else None
delta_dfg_val = round(dfg - dfg_prec, 1) if dfg_prec else None
delta_c0_val  = round(c0 - c0_prec, 1)   if c0_prec > 0 else None

# ─── MÉTRIQUES RÉNALES ────────────────────────────────────────────────────────
st.markdown("---")
m1, m2, m3, m4 = st.columns(4)

def metric_box(label, value, unit, color):
    return f"""<div style="background:#111113;border:1px solid #27272a;border-radius:10px;padding:14px;text-align:center">
      <div style="color:#64748b;font-size:0.7rem;text-transform:uppercase;letter-spacing:.05em">{label}</div>
      <div style="font-size:2rem;font-weight:800;color:{color};margin:4px 0;line-height:1">{value}</div>
      <div style="color:#64748b;font-size:0.72rem">{unit}</div>
    </div>"""

with m1: st.markdown(metric_box("DFG estimé",      dfg,           "mL/min (CG)",             stade_color),   unsafe_allow_html=True)
with m2: st.markdown(metric_box("Stade IRC",        stade,         stade_desc,                stade_color),   unsafe_allow_html=True)
with m3: st.markdown(metric_box("C0 tacrolimus",    c0,            f"ng/mL — {c0_statut}",    c0_color_hex),  unsafe_allow_html=True)
with m4:
    if var_tac_label:
        st.markdown(metric_box("Variation dose Tac", var_tac_label, "vs dose actuelle", var_tac_color), unsafe_allow_html=True)
    else:
        st.markdown(metric_box("Dose actuelle Tac",  f"{dose_tac}", "mg/j", "#64748b"), unsafe_allow_html=True)

# ─── IONOGRAMME ───────────────────────────────────────────────────────────────
st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
i1, i2, i3 = st.columns([1, 1, 2])

def ion_box(label, val, unit, statut, color, icon, ref_range):
    return f"""<div style="background:#111113;border:1px solid #27272a;border-radius:10px;padding:14px;text-align:center">
      <div style="color:#64748b;font-size:0.7rem;text-transform:uppercase;letter-spacing:.05em">{label}</div>
      <div style="font-size:1.9rem;font-weight:800;color:{color};margin:4px 0;line-height:1">{val} <span style="font-size:0.85rem;color:#64748b;font-weight:400">{unit}</span></div>
      <div style="color:{color};font-size:0.78rem;font-weight:600">{icon} {statut}</div>
      <div style="color:#475569;font-size:0.68rem;margin-top:3px">Réf : {ref_range}</div>
    </div>"""

with i1: st.markdown(ion_box("Natrémie Na⁺", na_val, "mmol/L", na_label, na_color, na_icon, "135–145"), unsafe_allow_html=True)
with i2: st.markdown(ion_box("Kaliémie K⁺",  k_val,  "mmol/L", k_label,  k_color,  k_icon,  "3,5–5,0"), unsafe_allow_html=True)
with i3:
    k_msg = (
        "🔴 K⁺ > 6,0 mmol/L — urgence métabolique : ECG, traitement immédiat, avis néphro"        if k_val > 6.0 else
        "🔴 K⁺ > 5,5 mmol/L — hyperkaliémie significative : tacrolimus bloque aldostérone → dose plafonnée à la dose actuelle"
        if k_val > 5.5 else
        "⚠️ K⁺ légèrement élevé — surveiller : régime pauvre en potassium, éviter IEC/ARA2 si possible"
        if k_val > 5.0 else
        "✅ Kaliémie normale — pas de restriction liée au K⁺"
    )
    na_msg = (
        "🔴 Hyponatrémie sévère — volume de distribution tacrolimus altéré, interprétation C0 à pondérer" if na_val < 125 else
        "⚠️ Hyponatrémie — surveiller hydratation et osmolalité"  if na_val < 135 else
        "⚠️ Hypernatrémie — risque de déshydratation, adapter les apports" if na_val > 145 else
        "✅ Natrémie normale"
    )
    st.markdown(f"""<div style="background:#111113;border:1px solid #27272a;border-radius:10px;padding:14px">
      <div style="color:#06b6d4;font-size:0.7rem;text-transform:uppercase;letter-spacing:.08em;font-weight:700;margin-bottom:10px">Interprétation ionogramme</div>
      <div style="color:#94a3b8;font-size:0.78rem;margin-bottom:6px">{k_msg}</div>
      <div style="color:#94a3b8;font-size:0.78rem">{na_msg}</div>
    </div>""", unsafe_allow_html=True)

# ─── TENDANCE ─────────────────────────────────────────────────────────────────
if dfg_prec or delta_c0_val is not None:
    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
    lt1, lt2, lt3 = st.columns(3)
    with lt1:
        if delta_dfg_val is not None:
            arrow = "↑" if delta_dfg_val > 0 else ("↓" if delta_dfg_val < 0 else "→")
            col   = "#10b981" if delta_dfg_val >= 0 else "#ef4444"
            st.markdown(f"""<div style="background:#111113;border:1px solid #27272a;border-radius:10px;padding:12px;text-align:center">
              <div style="color:#64748b;font-size:0.68rem;text-transform:uppercase">Évolution DFG</div>
              <div style="font-size:1.5rem;font-weight:700;color:{col}">{arrow} {abs(delta_dfg_val)} mL/min</div>
              <div style="color:#64748b;font-size:0.72rem">{dfg_prec} → {dfg} mL/min</div>
            </div>""", unsafe_allow_html=True)
    with lt2:
        if delta_c0_val is not None:
            arrow = "↑" if delta_c0_val > 0 else ("↓" if delta_c0_val < 0 else "→")
            col   = "#f59e0b" if delta_c0_val > 2 else ("#10b981" if abs(delta_c0_val) <= 2 else "#3b82f6")
            st.markdown(f"""<div style="background:#111113;border:1px solid #27272a;border-radius:10px;padding:12px;text-align:center">
              <div style="color:#64748b;font-size:0.68rem;text-transform:uppercase">Évolution C0</div>
              <div style="font-size:1.5rem;font-weight:700;color:{col}">{arrow} {abs(delta_c0_val)} ng/mL</div>
              <div style="color:#64748b;font-size:0.72rem">{c0_prec} → {c0} ng/mL</div>
            </div>""", unsafe_allow_html=True)
    with lt3:
        if dose_prec > 0:
            d_dose = round(dose_rec - dose_prec, 1)
            arrow  = "↑" if d_dose > 0 else ("↓" if d_dose < 0 else "→")
            col    = "#10b981" if d_dose == 0 else "#f59e0b"
            st.markdown(f"""<div style="background:#111113;border:1px solid #27272a;border-radius:10px;padding:12px;text-align:center">
              <div style="color:#64748b;font-size:0.68rem;text-transform:uppercase">Évolution dose Tac</div>
              <div style="font-size:1.5rem;font-weight:700;color:{col}">{arrow} {abs(d_dose)} mg/j</div>
              <div style="color:#64748b;font-size:0.72rem">{dose_prec} → {dose_rec} mg/j</div>
            </div>""", unsafe_allow_html=True)

# ─── RECOMMANDATION ───────────────────────────────────────────────────────────
st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)

if dfg < 15:
    rec_bg, rec_border = "#1c0505", "#dc2626"
    rec_titre = "🚫 Avis expert impératif"
    rec_note  = "IRC terminale — calcul automatique non applicable. Concertation multidisciplinaire obligatoire."
elif k_val > 6.0:
    rec_bg, rec_border = "#1c0505", "#dc2626"
    rec_titre = "🚫 Hyperkaliémie urgente — traiter avant tout ajustement"
    rec_note  = f"K⁺ = {k_val} mmol/L : urgence métabolique. Stabiliser la kaliémie (ECG, résines, ± dialyse) avant toute modification du tacrolimus."
elif dose_pk > plafond and c0 < t_min:
    rec_bg, rec_border = "#1c1005", "#f97316"
    rec_titre = "⚠️ Conflit PK / néphroprotection"
    rec_note  = f"PK suggère {dose_pk} mg/j mais plafond rénal = {plafond} mg/j. Dose retenue = plafond — priorité néphroprotection."
elif k_eleve:
    rec_bg, rec_border = "#1a1005", "#f97316"
    rec_titre = "⚠️ Dose limitée — hyperkaliémie liée au Tac"
    rec_note  = f"K⁺ = {k_val} mmol/L (> 5,5) : tacrolimus bloque aldostérone → dose plafonnée à {dose_rec} mg/j même si C0 subthérapeutique."
else:
    rec_bg, rec_border = "#071a10", "#10b981"
    rec_titre = "✅ Tacrolimus recommandé"
    rec_note  = None

rec_note_html = f'<div style="background:#0f0f11;border-radius:6px;padding:10px;margin-top:14px;color:#fbbf24;font-size:0.80rem">{rec_note}</div>' if rec_note else ''

st.markdown(f"""<div style="background:{rec_bg};border:2px solid {rec_border};border-radius:14px;padding:28px 32px">
  <div style="color:#94a3b8;font-size:0.68rem;text-transform:uppercase;letter-spacing:.08em;margin-bottom:14px;font-weight:700">{rec_titre}</div>
  <div style="font-size:3rem;font-weight:900;color:#f1f5f9;line-height:1">{dose_rec} <span style="font-size:1.1rem;color:#94a3b8;font-weight:400">mg/j</span></div>
  <div style="font-size:1.3rem;color:#93c5fd;font-weight:600;margin-top:10px">{dose_prise} mg × 2 /j (q12h)</div>
  <div style="color:#475569;font-size:0.80rem;margin-top:5px">matin + soir — toutes les 12h · capsules Prograf® 0,5 / 1 / 5 mg</div>
  {rec_note_html}
</div>""", unsafe_allow_html=True)

# ─── RAISONNEMENT CLINIQUE ────────────────────────────────────────────────────
st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)
st.markdown("<div style='color:#64748b;font-size:0.7rem;text-transform:uppercase;letter-spacing:.08em;margin-bottom:10px'>🔍 Raisonnement clinique</div>", unsafe_allow_html=True)

r1, r2, r3 = st.columns(3)
t_mid  = (t_min + t_max) / 2
raw_pk = round(dose_tac * t_mid / c0, 2) if c0 > 0 else dose_tac

with r1:
    st.markdown(f"""<div style="background:#111113;border:1px solid #27272a;border-radius:10px;padding:14px">
      <div style="color:#64748b;font-size:0.7rem;margin-bottom:8px;font-weight:600">① Statut C0 résiduel</div>
      <div style="color:{c0_color_hex};font-weight:700;font-size:0.95rem">{c0_icon} {c0_statut.capitalize()}</div>
      <div style="color:#94a3b8;font-size:0.78rem;margin-top:6px">{c0} ng/mL · cible {t_min}–{t_max} ng/mL</div>
      <div style="color:#64748b;font-size:0.72rem;margin-top:4px">Phase {phase['label']} post-greffe</div>
    </div>""", unsafe_allow_html=True)

with r2:
    st.markdown(f"""<div style="background:#111113;border:1px solid #27272a;border-radius:10px;padding:14px">
      <div style="color:#64748b;font-size:0.7rem;margin-bottom:8px;font-weight:600">② Ajustement PK proportionnel</div>
      <div style="color:#e2e8f0;font-weight:700;font-size:0.95rem">Dose PK : {dose_pk} mg/j</div>
      <div style="color:#94a3b8;font-size:0.78rem;margin-top:6px">{dose_tac} × ({t_mid} / {c0}) = {raw_pk} → arrondi {dose_pk}</div>
      <div style="color:#64748b;font-size:0.72rem;margin-top:4px">Règle de trois PK tacrolimus (Staatz &amp; Tett, 2004)</div>
    </div>""", unsafe_allow_html=True)

with r3:
    k_note = f" · K⁺ {k_val} → plafonné à {dose_tac} mg/j" if k_eleve else ""
    st.markdown(f"""<div style="background:#111113;border:1px solid #27272a;border-radius:10px;padding:14px">
      <div style="color:#64748b;font-size:0.7rem;margin-bottom:8px;font-weight:600">③ Plafond néphroprotecteur</div>
      <div style="color:{stade_color};font-weight:700;font-size:0.95rem">Max : {plafond} mg/j</div>
      <div style="color:#94a3b8;font-size:0.78rem;margin-top:6px">{poids} kg × 0,1 mg/kg × facteur {fr} (stade {stade}){k_note}</div>
      <div style="color:#64748b;font-size:0.72rem;margin-top:4px">Ojo NEJM 2003 · Naesens CJASN 2009 · Ekberg NEJM 2007</div>
    </div>""", unsafe_allow_html=True)

k_suffix = f", dose actuelle {dose_tac} [K⁺ > 5,5]" if k_eleve else ""
st.markdown(f"""<div style="background:#111113;border:1px solid #27272a;border-radius:10px;padding:12px 16px;margin-top:8px">
  <span style="color:#e2e8f0;font-weight:700;font-size:0.88rem">Dose retenue = min(PK {dose_pk}, plafond {plafond}{k_suffix}) = {dose_rec} mg/j</span>
  <span style="color:#64748b;font-size:0.78rem"> — capsule 0,5 mg · q12h → {dose_prise} mg matin + {dose_prise} mg soir</span>
</div>""", unsafe_allow_html=True)

# ─── BOUTONS SAVE + PDF ───────────────────────────────────────────────────────
st.markdown("<div style='height:18px'></div>", unsafe_allow_html=True)
btn1, btn2, btn3 = st.columns([1.2, 1.5, 3])

with btn1:
    save_clicked = st.button(
        "💾 Enregistrer ce bilan",
        type="primary",
        disabled=not patient_valid,
        use_container_width=True,
    )

if save_clicked and patient_valid:
    upsert_patient(pat_id, pat_nom, pat_prenom)
    save_consultation(
        pat_id, age, sexe, poids, creat, dfg, stade,
        na_val, k_val, phase_label, c0, dose_tac,
        dose_rec, dose_pk, plafond, fr,
        c0_statut, na_label, k_label
    )
    st.success(f"✅ Bilan enregistré pour {pat_prenom.capitalize()} {pat_nom.upper()} (#{pat_id})")

# Récupérer l'historique pour le PDF et la section suivi
history_rows = get_consultations(pat_id) if patient_valid else []

with btn2:
    if patient_valid:
        pdf_bytes = generate_pdf(
            pat_nom, pat_prenom, pat_id,
            age, sexe, poids, creat, dfg, stade, stade_desc,
            na_val, na_label, k_val, k_label,
            phase_label, c0, c0_statut, t_min, t_max,
            dose_tac, dose_rec, dose_pk, plafond, fr,
            k_eleve, rec_titre, history_rows
        )
        if pdf_bytes:
            fname = f"MedFlow_{pat_id}_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf"
            st.download_button(
                label="📄 Télécharger rapport PDF",
                data=pdf_bytes,
                file_name=fname,
                mime="application/pdf",
                use_container_width=True,
            )
        elif not PDF_OK:
            st.warning("fpdf2 non installé — `pip install fpdf2`")

# ─── HISTORIQUE LONGITUDINAL ──────────────────────────────────────────────────
if patient_valid and history_rows:
    st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
    st.markdown(f"""<div style="color:#3b82f6;font-size:0.7rem;text-transform:uppercase;letter-spacing:.08em;font-weight:700;margin-bottom:10px">
      📈 Suivi longitudinal — {pat_prenom.capitalize()} {pat_nom.upper()} · {len(history_rows)} bilan(s)
    </div>""", unsafe_allow_html=True)

    # Graphiques Plotly
    if PLOTLY_OK and len(history_rows) >= 2:
        dates     = [r[0] for r in history_rows]
        dfg_vals  = [r[5]  for r in history_rows]
        c0_vals   = [r[10] for r in history_rows]
        dose_vals = [r[12] for r in history_rows]
        k_vals    = [r[8]  for r in history_rows]
        na_vals_h = [r[7]  for r in history_rows]

        def plotly_line(x, y, name, color, ref_min=None, ref_max=None, ref_label=None):
            fig = go.Figure()
            if ref_min is not None and ref_max is not None:
                fig.add_hrect(y0=ref_min, y1=ref_max,
                              fillcolor="rgba(16,185,129,0.12)", line_width=0,
                              annotation_text=ref_label or f"Cible {ref_min}–{ref_max}",
                              annotation_position="top right",
                              annotation_font_size=9, annotation_font_color="#10b981")
            fig.add_trace(go.Scatter(
                x=x, y=y, mode='lines+markers', name=name,
                line=dict(color=color, width=2),
                marker=dict(size=7, color=color,
                            line=dict(width=1.5, color='#09090b')),
                hovertemplate='%{x}<br>' + name + ': <b>%{y}</b><extra></extra>'
            ))
            fig.update_layout(
                template='plotly_dark',
                paper_bgcolor='#111113',
                plot_bgcolor='#18181b',
                font=dict(color='#94a3b8', size=10),
                margin=dict(l=45, r=15, t=30, b=45),
                height=220,
                showlegend=False,
                xaxis=dict(gridcolor='#27272a', tickangle=-30, tickfont_size=9),
                yaxis=dict(gridcolor='#27272a'),
            )
            return fig

        g1, g2 = st.columns(2)
        with g1:
            st.markdown("<div style='color:#3b82f6;font-size:0.72rem;font-weight:600;margin-bottom:4px'>DFG (mL/min)</div>", unsafe_allow_html=True)
            st.plotly_chart(plotly_line(dates, dfg_vals, "DFG", "#3b82f6"), use_container_width=True, key="chart_dfg")
        with g2:
            st.markdown("<div style='color:#8b5cf6;font-size:0.72rem;font-weight:600;margin-bottom:4px'>C0 résiduel (ng/mL)</div>", unsafe_allow_html=True)
            st.plotly_chart(plotly_line(dates, c0_vals, "C0", "#8b5cf6", t_min, t_max, f"Cible {t_min}–{t_max}"), use_container_width=True, key="chart_c0")

        g3, g4 = st.columns(2)
        with g3:
            st.markdown("<div style='color:#10b981;font-size:0.72rem;font-weight:600;margin-bottom:4px'>Dose recommandée (mg/j)</div>", unsafe_allow_html=True)
            st.plotly_chart(plotly_line(dates, dose_vals, "Dose", "#10b981"), use_container_width=True, key="chart_dose")
        with g4:
            st.markdown("<div style='color:#f59e0b;font-size:0.72rem;font-weight:600;margin-bottom:4px'>Kaliémie K⁺ (mmol/L)</div>", unsafe_allow_html=True)
            st.plotly_chart(plotly_line(dates, k_vals, "K⁺", "#f59e0b", 3.5, 5.0, "Norme 3,5–5,0"), use_container_width=True, key="chart_k")

    elif PLOTLY_OK and len(history_rows) == 1:
        st.info("Enregistrer au moins 2 bilans pour afficher les courbes d'évolution.")

    # Tableau historique
    with st.expander(f"🗂️  Tableau des {len(history_rows)} consultation(s)", expanded=False):
        hdr = ["Date", "DFG", "Stade", "C0", "Statut C0", "Na⁺", "K⁺", "Phase", "Dose act.", "Dose rec.", "Plafond"]
        col_ws = [1.4, 0.7, 0.6, 0.6, 1.1, 0.6, 0.6, 1.2, 0.8, 0.8, 0.8]
        hcols = st.columns(col_ws)
        for hc, ht in zip(hcols, hdr):
            hc.markdown(f"<div style='color:#475569;font-size:0.68rem;text-transform:uppercase;font-weight:700'>{ht}</div>", unsafe_allow_html=True)
        st.markdown("<hr style='border-color:#27272a;margin:4px 0 6px'>", unsafe_allow_html=True)
        alt_bg = ["#111113", "#0f0f11"]
        for i, row in enumerate(reversed(history_rows)):
            bg = alt_bg[i % 2]
            rcols = st.columns(col_ws)
            vals = [row[0][:16], f"{row[5]:.0f}", row[6], f"{row[10]:.1f}", row[16],
                    f"{row[7]:.0f}", f"{row[8]:.1f}", row[9].split('(')[0].strip(),
                    f"{row[11]:.1f}", f"{row[12]:.1f}", f"{row[14]:.1f}"]
            for rc, rv in zip(rcols, vals):
                rc.markdown(f"<div style='background:{bg};padding:5px 4px;border-radius:4px;color:#e2e8f0;font-size:0.75rem'>{rv}</div>", unsafe_allow_html=True)

# ─── FORMULES ─────────────────────────────────────────────────────────────────
st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
with st.expander("📐  Formules utilisées — transparence algorithmique"):
    fa1, fa2 = st.columns(2)
    with fa1:
        st.markdown("""<div style="background:#111113;border:1px solid #27272a;border-radius:10px;padding:16px;margin-bottom:8px">
          <div style="color:#8b5cf6;font-size:0.75rem;font-weight:700;margin-bottom:8px">① DFG — Cockcroft-Gault (1976)</div>
          <div style="font-family:monospace;color:#93c5fd;font-size:0.85rem;background:#0f0f11;padding:10px 12px;border-radius:6px;line-height:1.8">
            DFG = ((140 − âge) × poids × F) / (0,815 × créatinine)<br>
            F = 1,00 (Homme) | 0,85 (Femme)<br>
            créatinine en µmol/L → DFG en mL/min
          </div>
          <div style="color:#64748b;font-size:0.72rem;margin-top:6px">Recommandée HAS · Sociétés savantes françaises</div>
        </div>""", unsafe_allow_html=True)
        st.markdown("""<div style="background:#111113;border:1px solid #27272a;border-radius:10px;padding:16px">
          <div style="color:#f59e0b;font-size:0.75rem;font-weight:700;margin-bottom:8px">③ Plafond néphroprotecteur</div>
          <div style="font-family:monospace;color:#93c5fd;font-size:0.85rem;background:#0f0f11;padding:10px 12px;border-radius:6px;line-height:1.8">
            Plafond = poids × 0,1 mg/kg × facteur_DFG<br><br>
            G1–G2 (DFG ≥ 60)  → facteur 1,00<br>
            G3a   (45 – 59)   → facteur 0,90<br>
            G3b   (30 – 44)   → facteur 0,80<br>
            G4    (15 – 29)   → facteur 0,70<br>
            G5    (< 15)      → facteur 0,50
          </div>
          <div style="color:#64748b;font-size:0.72rem;margin-top:6px">Source : Ojo NEJM 2003 · Naesens CJASN 2009 · Ekberg NEJM 2007</div>
        </div>""", unsafe_allow_html=True)
    with fa2:
        st.markdown("""<div style="background:#111113;border:1px solid #27272a;border-radius:10px;padding:16px;margin-bottom:8px">
          <div style="color:#10b981;font-size:0.75rem;font-weight:700;margin-bottom:8px">② Ajustement PK proportionnel</div>
          <div style="font-family:monospace;color:#93c5fd;font-size:0.85rem;background:#0f0f11;padding:10px 12px;border-radius:6px;line-height:1.8">
            dose_PK = dose_actuelle × (C0_cible / C0_mesuré)<br><br>
            C0_cible = milieu fourchette cible par phase<br>
            Corrélation C0/AUC r = 0,89 (Staatz 2004)
          </div>
          <div style="color:#64748b;font-size:0.72rem;margin-top:6px">Linéarité PK tacrolimus validée · Standard international</div>
        </div>""", unsafe_allow_html=True)
        st.markdown("""<div style="background:#111113;border:1px solid #27272a;border-radius:10px;padding:16px">
          <div style="color:#06b6d4;font-size:0.75rem;font-weight:700;margin-bottom:8px">④ Décision finale</div>
          <div style="font-family:monospace;color:#93c5fd;font-size:0.85rem;background:#0f0f11;padding:10px 12px;border-radius:6px;line-height:1.8">
            dose = min(dose_PK, plafond_rénal)<br><br>
            Si K⁺ &gt; 5,5 mmol/L :<br>
            dose = min(dose, dose_actuelle)<br><br>
            Arrondi capsule 0,5 mg — min 0,5 mg/j<br>
            Split q12h : dose / 2 matin + soir
          </div>
          <div style="color:#64748b;font-size:0.72rem;margin-top:6px">Priorité néphroprotection · ISHLT 2016 · Tumlin 1996</div>
        </div>""", unsafe_allow_html=True)

# ─── BASE DE DONNÉES PROBANTES ────────────────────────────────────────────────
with st.expander("📊  Base de données probantes — études et méta-analyses"):
    st.markdown("""<div style="color:#64748b;font-size:0.75rem;margin-bottom:12px">
      Données extraites des études validant chaque paramètre de l'algorithme — greffe cardiaque sous tacrolimus.
    </div>""", unsafe_allow_html=True)
    h1c, h2c, h3c, h4c, h5c = st.columns([1.2, 1.0, 0.55, 1.9, 1.7])
    for col, txt in zip([h1c, h2c, h3c, h4c, h5c],
                        ["Étude", "Journal · Année", "N", "Résultat clé", "Application dans l'outil"]):
        col.markdown(f"<div style='color:#475569;font-size:0.68rem;text-transform:uppercase;font-weight:700;padding:4px 0'>{txt}</div>", unsafe_allow_html=True)
    st.markdown("<hr style='border-color:#27272a;margin:4px 0 8px'>", unsafe_allow_html=True)
    alt = ["#111113", "#0f0f11"]
    for i, (auteur, journal, n, resultat, application) in enumerate(META_DATA):
        bg_r = alt[i % 2]
        c1, c2, c3, c4, c5 = st.columns([1.2, 1.0, 0.55, 1.9, 1.7])
        c1.markdown(f"<div style='background:{bg_r};padding:8px 6px;border-radius:4px;color:#93c5fd;font-size:0.78rem;font-weight:600'>{auteur}</div>", unsafe_allow_html=True)
        c2.markdown(f"<div style='background:{bg_r};padding:8px 6px;border-radius:4px;color:#94a3b8;font-size:0.75rem'>{journal}</div>", unsafe_allow_html=True)
        c3.markdown(f"<div style='background:{bg_r};padding:8px 6px;border-radius:4px;color:#64748b;font-size:0.75rem'>{n}</div>", unsafe_allow_html=True)
        c4.markdown(f"<div style='background:{bg_r};padding:8px 6px;border-radius:4px;color:#e2e8f0;font-size:0.75rem'>{resultat}</div>", unsafe_allow_html=True)
        c5.markdown(f"<div style='background:{bg_r};padding:8px 6px;border-radius:4px;color:#10b981;font-size:0.75rem'>{application}</div>", unsafe_allow_html=True)

# ─── MONITORING ───────────────────────────────────────────────────────────────
st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
if dfg >= 45:
    creat_freq, trough_freq, mc = "Mensuelle × 3, puis / 3 mois", "J7–J14 après chaque changement", "#10b981"
elif dfg >= 30:
    creat_freq, trough_freq, mc = "Bimensuelle × 3, puis mensuelle", "J7–J14–J21 — cible bas fourchette", "#f59e0b"
else:
    creat_freq, trough_freq, mc = "Hebdomadaire — surveillance rapprochée", "2×/semaine minimum", "#ef4444"

mon1, mon2, mon3, mon4 = st.columns(4)
def mon_box(label, val, col):
    return f"""<div style="background:#111113;border:1px solid #27272a;border-radius:10px;padding:12px">
      <div style="color:#64748b;font-size:0.68rem;text-transform:uppercase;margin-bottom:6px">{label}</div>
      <div style="color:{col};font-size:0.82rem;font-weight:600">{val}</div>
    </div>"""
with mon1: st.markdown(mon_box("Créatinine / DFG", creat_freq, mc), unsafe_allow_html=True)
with mon2: st.markdown(mon_box("Taux résiduel C0", trough_freq, mc), unsafe_allow_html=True)
with mon3: st.markdown(mon_box("Ionogramme Na⁺ K⁺", "À chaque contrôle", "#06b6d4"), unsafe_allow_html=True)
with mon4: st.markdown(mon_box("NFS · PA · glycémie", "À chaque contrôle", "#94a3b8"), unsafe_allow_html=True)

# ─── INTERACTIONS ─────────────────────────────────────────────────────────────
st.markdown("""<div style="background:#1c1208;border:1px solid #92400e;border-radius:10px;padding:14px 18px;margin-top:8px">
  <div style="color:#fbbf24;font-size:0.78rem;font-weight:700;margin-bottom:6px">⚠️ Interactions majeures — vérifier à chaque modification du traitement</div>
  <div style="display:flex;gap:32px;flex-wrap:wrap">
    <div style="color:#d97706;font-size:0.76rem"><strong>↑ taux Tac (CYP3A4 inhibiteurs) :</strong> azithromycine, fluconazole, voriconazole, diltiazem, vérapamil, amiodarone</div>
    <div style="color:#d97706;font-size:0.76rem"><strong>↓ taux Tac (CYP3A4 inducteurs) :</strong> rifampicine, phénytoïne, carbamazépine, millepertuis</div>
    <div style="color:#d97706;font-size:0.76rem"><strong>Hyperkaliémie aggravée :</strong> IEC, ARA2, AINS, diurétiques épargneurs de K⁺ — surveiller K⁺ systématiquement</div>
  </div>
</div>""", unsafe_allow_html=True)

# ─── RÉFÉRENCES ───────────────────────────────────────────────────────────────
with st.expander("📚  Références scientifiques"):
    for ref_nom, ref_texte in REFS:
        st.markdown(f"""<div style="background:#111113;border-left:3px solid #3b82f6;border-radius:0 8px 8px 0;padding:10px 14px;margin-bottom:8px">
          <div style="color:#93c5fd;font-weight:600;font-size:0.82rem;margin-bottom:4px">{ref_nom}</div>
          <div style="color:#94a3b8;font-size:0.78rem">{ref_texte}</div>
        </div>""", unsafe_allow_html=True)

# ─── DISCLAIMER ───────────────────────────────────────────────────────────────
st.markdown("""<div style="background:#0f0f11;border:1px solid #1e1e21;border-radius:10px;padding:12px 20px;color:#475569;font-size:0.75rem;text-align:center;margin-top:8px">
  ⚕️ <strong style="color:#64748b">Outil d'aide à la décision — ne remplace pas la concertation d'équipe de transplantation.</strong>
  Adapter systématiquement au protocole institutionnel. MedFlow AI — usage professionnel exclusif.
</div>""", unsafe_allow_html=True)
