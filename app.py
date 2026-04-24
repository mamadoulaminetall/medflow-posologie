import streamlit as st
import math

st.set_page_config(
    page_title="Tacrolimus + CellCept — Greffe Cardiaque · MedFlow AI",
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
.stNumberInput label, .stSelectbox label, .stRadio label, .stCheckbox label { color: #94a3b8 !important; font-size: 0.82rem !important; }
.stNumberInput input { background: #18181b !important; border: 1px solid #27272a !important; color: #f1f5f9 !important; border-radius: 8px !important; }
.stSelectbox > div > div { background: #18181b !important; border: 1px solid #27272a !important; color: #f1f5f9 !important; border-radius: 8px !important; }
div[data-baseweb="radio"] > label > div:first-child { background: #27272a !important; border-color: #3f3f46 !important; }
.stRadio [data-testid="stMarkdownContainer"] p { color: #d1d5db; font-size: 0.88rem; }
.stExpander { background: #111113 !important; border: 1px solid #27272a !important; border-radius: 10px !important; }
.stExpander summary { color: #94a3b8 !important; }
h1, h2, h3 { color: #f1f5f9 !important; }
hr { border-color: #27272a; }
footer { visibility: hidden; }
</style>
""", unsafe_allow_html=True)

# ─── Constantes ───────────────────────────────────────────────────────────────
PHASES = {
    "M0 – M3  (phase précoce)":  {"min": 10, "max": 15, "label": "M0–M3"},
    "M3 – M12  (maintenance)":   {"min": 8,  "max": 12, "label": "M3–M12"},
    "> 1 an  (phase stable)":    {"min": 5,  "max": 10, "label": ">1 an"},
}

REFS = [
    ("ISHLT Guidelines 2016", "Kobashigawa J et al. J Heart Lung Transplant. 2016;35(1):1–23. Recommandations immunosuppression post-greffe cardiaque."),
    ("ISHLT Registry 2022",   "Stehlik J et al. J Heart Lung Transplant. 2022;41(10):1336–1347. Registre international données survie et immunosuppression."),
    ("CNI Néphrotoxicité",    "Naesens M et al. Clin J Am Soc Nephrol. 2009;4(2):481–508. Mécanismes et gestion de la toxicité rénale aux inhibiteurs de calcineurine."),
    ("Greffe non rénale IRC",  "Ojo AO et al. N Engl J Med. 2003;349:931–940. Insuffisance rénale chronique après greffe d'organe solide non rénal — tacrolimus identifié facteur indépendant."),
    ("MMF Greffe cardiaque",  "Kobashigawa JA et al. J Heart Lung Transplant. 1998;17(6):587–591. MMF vs azathioprine — réduction rejet aigu et meilleure préservation rénale."),
    ("Cockcroft-Gault",       "Cockcroft DW, Gault MH. Nephron. 1976;16(1):31–41. Formule de référence pour l'estimation de la clairance de la créatinine."),
    ("Tacrolimus PK ajustement", "Staatz CE, Tett SE. Clin Pharmacokinet. 2004;43(10):623–653. Revue PK/PD tacrolimus : base de l'ajustement par taux résiduel."),
]

# ─── Fonctions ────────────────────────────────────────────────────────────────
def calc_dfg(age, poids, sexe, creat_umol):
    F = 1.0 if sexe == "Homme" else 0.85
    return max(round(((140 - age) * poids * F) / (0.815 * creat_umol), 1), 0.0)

def get_stade(dfg):
    if dfg >= 90: return "G1", "Normale",           "#10b981"
    if dfg >= 60: return "G2", "Légèrement ↓",      "#84cc16"
    if dfg >= 45: return "G3a","Légère–modérée ↓",  "#f59e0b"
    if dfg >= 30: return "G3b","Modérée–sévère ↓",  "#f97316"
    if dfg >= 15: return "G4", "Sévèrement ↓",      "#ef4444"
    return              "G5",  "Terminale",          "#dc2626"

def arrondir_05(v):
    return round(round(v / 0.5) * 0.5, 1)

def recommander_tacrolimus(dose_act, c0, t_min, t_max, dfg, poids):
    t_mid = (t_min + t_max) / 2
    dose_pk = dose_act * (t_mid / c0) if c0 > 0 else dose_act
    if   dfg >= 60: fr = 1.00
    elif dfg >= 45: fr = 0.90
    elif dfg >= 30: fr = 0.80
    elif dfg >= 15: fr = 0.70
    else:           fr = 0.50
    plafond = poids * 0.1 * fr
    dose_finale = min(dose_pk, plafond)
    dose_finale = max(dose_finale, 0.5)
    return arrondir_05(dose_finale), arrondir_05(dose_pk), arrondir_05(plafond), fr

def recommander_mmf(dose_mmf_act, dfg, pnn=None):
    """
    Ajustement MMF (CellCept) selon DFG et neutrophiles.
    Retourne (dose_recommandée_j, commentaire, niveau)
    """
    # Plafond rénal
    if dfg >= 25:
        plafond_mmf = 3.0
        note_dfg = "Pas de restriction rénale"
    elif dfg >= 10:
        plafond_mmf = 2.0
        note_dfg = "Max 2 g/j (DFG < 25 mL/min)"
    else:
        plafond_mmf = 2.0
        note_dfg = "Max 2 g/j — dialyse possible"

    # Ajustement leucocytes
    note_pnn = ""
    facteur_pnn = 1.0
    niveau = "normal"
    if pnn is not None:
        if pnn < 1.0:
            facteur_pnn = 0.0
            note_pnn = "Suspendre MMF (PNN < 1.0 × 10⁹/L)"
            niveau = "contraindicated"
        elif pnn < 1.5:
            facteur_pnn = 0.5
            note_pnn = "Réduire MMF de 50 % (PNN 1.0–1.5)"
            niveau = "warning"
        else:
            note_pnn = "NFS acceptable"

    if facteur_pnn == 0.0:
        dose_rec = 0.0
    else:
        dose_rec = min(dose_mmf_act * facteur_pnn, plafond_mmf)
        dose_rec = max(arrondir_05(dose_rec), 0.5) if dose_rec > 0 else 0

    commentaire = note_dfg + (f" · {note_pnn}" if note_pnn else "")
    return dose_rec, commentaire, niveau

# ─── EN-TÊTE ──────────────────────────────────────────────────────────────────
st.markdown("""
<div style="padding:0 0 6px">
  <div style="display:flex;align-items:center;gap:14px">
    <span style="font-size:2rem">🫀</span>
    <div>
      <div style="font-size:1.65rem;font-weight:800;color:#f1f5f9">Tacrolimus + CellCept — Greffe Cardiaque</div>
      <div style="color:#64748b;font-size:0.82rem;margin-top:2px">Dosage adapté à la fonction rénale · Suivi longitudinal · MedFlow AI</div>
    </div>
  </div>
</div>
""", unsafe_allow_html=True)
st.markdown("---")

# ─── FORMULAIRE ───────────────────────────────────────────────────────────────
col_pat, col_tac, col_mmf = st.columns([1.1, 1, 1], gap="large")

with col_pat:
    st.markdown("<div style='color:#8b5cf6;font-size:0.7rem;text-transform:uppercase;letter-spacing:.08em;font-weight:700;margin-bottom:8px'>👤 Patient</div>", unsafe_allow_html=True)
    age   = st.number_input("Âge (ans)",             min_value=18,   max_value=100,   value=55,   step=1)
    sexe  = st.radio("Sexe biologique",               ["Homme", "Femme"], horizontal=True)
    poids = st.number_input("Poids (kg)",             min_value=30.0, max_value=250.0, value=70.0, step=0.5)
    creat = st.number_input("Créatinine (µmol/L)",    min_value=20.0, max_value=2000.0, value=120.0, step=1.0)

with col_tac:
    st.markdown("<div style='color:#10b981;font-size:0.7rem;text-transform:uppercase;letter-spacing:.08em;font-weight:700;margin-bottom:8px'>💊 Tacrolimus (Prograf)</div>", unsafe_allow_html=True)
    phase_label = st.selectbox("Phase post-greffe", list(PHASES.keys()))
    c0    = st.number_input("C0 résiduel (ng/mL)",    min_value=0.1, max_value=50.0, value=12.0, step=0.1)
    dose_tac = st.number_input("Dose actuelle (mg/j)", min_value=0.5, max_value=30.0, value=5.0, step=0.5)

with col_mmf:
    st.markdown("<div style='color:#3b82f6;font-size:0.7rem;text-transform:uppercase;letter-spacing:.08em;font-weight:700;margin-bottom:8px'>🔵 MMF / CellCept</div>", unsafe_allow_html=True)
    dose_mmf = st.number_input("Dose MMF actuelle (g/j)", min_value=0.0, max_value=4.0, value=2.0, step=0.5)
    with_pnn  = st.checkbox("Saisir les neutrophiles (PNN)", value=False)
    pnn_val   = None
    if with_pnn:
        pnn_val = st.number_input("PNN (× 10⁹/L)", min_value=0.0, max_value=15.0, value=2.0, step=0.1)

# ─── Suivi longitudinal ───────────────────────────────────────────────────────
with st.expander("📈  Bilan précédent (suivi longitudinal — optionnel)"):
    lc1, lc2, lc3 = st.columns(3)
    with lc1:
        creat_prec = st.number_input("Créatinine précédente (µmol/L)", min_value=0.0, max_value=2000.0, value=0.0, step=1.0)
    with lc2:
        c0_prec    = st.number_input("C0 précédent (ng/mL)", min_value=0.0, max_value=50.0, value=0.0, step=0.1)
    with lc3:
        dose_prec  = st.number_input("Dose Tac précédente (mg/j)", min_value=0.0, max_value=30.0, value=0.0, step=0.5)

# ─── CALCULS ──────────────────────────────────────────────────────────────────
phase       = PHASES[phase_label]
t_min, t_max = phase["min"], phase["max"]
dfg         = calc_dfg(age, poids, sexe, creat)
stade, stade_desc, stade_color = get_stade(dfg)
dose_rec, dose_pk, plafond, fr = recommander_tacrolimus(dose_tac, c0, t_min, t_max, dfg, poids)
dose_prise  = arrondir_05(dose_rec / 2)
dose_mmf_rec, mmf_comment, mmf_niveau = recommander_mmf(dose_mmf, dfg, pnn_val)
dose_mmf_prise = arrondir_05(dose_mmf_rec / 2) if dose_mmf_rec > 0 else 0

# Statut C0
if   c0 < t_min: c0_statut, c0_color, c0_icon = "subthérapeutique", "#ef4444", "🔴"
elif c0 > t_max: c0_statut, c0_color, c0_icon = "suprathérapeutique","#f59e0b", "⚠️"
else:            c0_statut, c0_color, c0_icon = "thérapeutique",     "#10b981", "✅"

# Variation
def delta_str(new, old):
    if old <= 0: return None, "#94a3b8"
    d = round((new - old) / old * 100, 1)
    return (f"+{d} %" if d > 0 else f"{d} %"), ("#10b981" if d > 0 else ("#ef4444" if d < -5 else "#f59e0b"))

var_tac_label, var_tac_color = delta_str(dose_rec, dose_tac)

# Longitudinal deltas
dfg_prec = calc_dfg(age, poids, sexe, creat_prec) if creat_prec > 0 else None
delta_dfg_val  = round(dfg - dfg_prec, 1) if dfg_prec else None
delta_c0_val   = round(c0 - c0_prec, 1)   if c0_prec > 0 else None

# ─── MÉTRIQUES ────────────────────────────────────────────────────────────────
st.markdown("---")
m1, m2, m3, m4 = st.columns(4)

def metric_box(label, value, unit, color):
    return f"""<div style="background:#111113;border:1px solid #27272a;border-radius:10px;padding:14px;text-align:center">
      <div style="color:#64748b;font-size:0.7rem;text-transform:uppercase;letter-spacing:.05em">{label}</div>
      <div style="font-size:2rem;font-weight:800;color:{color};margin:4px 0;line-height:1">{value}</div>
      <div style="color:#64748b;font-size:0.72rem">{unit}</div>
    </div>"""

with m1: st.markdown(metric_box("DFG estimé", dfg, "mL/min (CG)", stade_color), unsafe_allow_html=True)
with m2: st.markdown(metric_box("Stade IRC", stade, stade_desc, stade_color), unsafe_allow_html=True)
with m3: st.markdown(metric_box("C0 tacrolimus", c0, f"ng/mL — {c0_statut}", c0_color), unsafe_allow_html=True)
with m4:
    if var_tac_label:
        st.markdown(metric_box("Variation dose Tac", var_tac_label, "vs dose actuelle", var_tac_color), unsafe_allow_html=True)
    else:
        st.markdown(metric_box("Dose actuelle Tac", f"{dose_tac}", "mg/j", "#64748b"), unsafe_allow_html=True)

# ─── TENDANCE LONGITUDINALE ───────────────────────────────────────────────────
if dfg_prec or delta_c0_val is not None:
    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
    t1, t2, t3 = st.columns(3)
    with t1:
        if delta_dfg_val is not None:
            arrow = "↑" if delta_dfg_val > 0 else ("↓" if delta_dfg_val < 0 else "→")
            col   = "#10b981" if delta_dfg_val >= 0 else "#ef4444"
            st.markdown(f"""<div style="background:#111113;border:1px solid #27272a;border-radius:10px;padding:12px;text-align:center">
              <div style="color:#64748b;font-size:0.68rem;text-transform:uppercase">Évolution DFG</div>
              <div style="font-size:1.5rem;font-weight:700;color:{col}">{arrow} {abs(delta_dfg_val)} mL/min</div>
              <div style="color:#64748b;font-size:0.72rem">{dfg_prec} → {dfg} mL/min</div>
            </div>""", unsafe_allow_html=True)
    with t2:
        if delta_c0_val is not None:
            arrow = "↑" if delta_c0_val > 0 else ("↓" if delta_c0_val < 0 else "→")
            col   = "#f59e0b" if delta_c0_val > 2 else ("#10b981" if abs(delta_c0_val) <= 2 else "#3b82f6")
            st.markdown(f"""<div style="background:#111113;border:1px solid #27272a;border-radius:10px;padding:12px;text-align:center">
              <div style="color:#64748b;font-size:0.68rem;text-transform:uppercase">Évolution C0</div>
              <div style="font-size:1.5rem;font-weight:700;color:{col}">{arrow} {abs(delta_c0_val)} ng/mL</div>
              <div style="color:#64748b;font-size:0.72rem">{c0_prec} → {c0} ng/mL</div>
            </div>""", unsafe_allow_html=True)
    with t3:
        if dose_prec > 0:
            d_dose = round(dose_rec - dose_prec, 1)
            arrow = "↑" if d_dose > 0 else ("↓" if d_dose < 0 else "→")
            col   = "#10b981" if d_dose == 0 else "#f59e0b"
            st.markdown(f"""<div style="background:#111113;border:1px solid #27272a;border-radius:10px;padding:12px;text-align:center">
              <div style="color:#64748b;font-size:0.68rem;text-transform:uppercase">Évolution dose Tac</div>
              <div style="font-size:1.5rem;font-weight:700;color:{col}">{arrow} {abs(d_dose)} mg/j</div>
              <div style="color:#64748b;font-size:0.72rem">{dose_prec} → {dose_rec} mg/j</div>
            </div>""", unsafe_allow_html=True)

# ─── RECOMMANDATIONS CÔTE À CÔTE ─────────────────────────────────────────────
st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
rec1, rec2 = st.columns([1, 1], gap="medium")

# ── Tacrolimus
with rec1:
    if dfg < 15:
        bg, border = "#1c0505", "#dc2626"
        titre = "🚫 Avis expert impératif"
        note  = "IRC terminale — calcul auto non applicable. Concertation multidisciplinaire."
    elif dose_pk > plafond and c0 < t_min:
        bg, border = "#1c1005", "#f97316"
        titre = "⚠️ Conflit PK / néphroprotection"
        note  = f"PK suggère {dose_pk} mg/j mais plafond rénal = {plafond} mg/j. Dose retenue = plafond."
    else:
        bg, border = "#071a10", "#10b981"
        titre = "✅ Tacrolimus recommandé"
        note  = None

    st.markdown(f"""<div style="background:{bg};border:2px solid {border};border-radius:14px;padding:22px 24px;height:100%">
      <div style="color:#94a3b8;font-size:0.68rem;text-transform:uppercase;letter-spacing:.08em;margin-bottom:12px;font-weight:700">{titre}</div>
      <div style="font-size:2.6rem;font-weight:900;color:#f1f5f9;line-height:1">{dose_rec} <span style="font-size:1rem;color:#94a3b8;font-weight:400">mg/j</span></div>
      <div style="font-size:1.2rem;color:#93c5fd;font-weight:600;margin-top:8px">{dose_prise} mg × 2 /j &nbsp;(q12h)</div>
      <div style="color:#475569;font-size:0.78rem;margin-top:4px">matin + soir — toutes les 12h</div>
      {f'<div style="background:#0f0f11;border-radius:6px;padding:10px;margin-top:12px;color:#fbbf24;font-size:0.78rem">{note}</div>' if note else ''}
    </div>""", unsafe_allow_html=True)

# ── MMF / CellCept
with rec2:
    mmf_colors = {
        "normal":         ("#071629", "#3b82f6", "✅ MMF recommandé"),
        "warning":        ("#1c1208", "#f59e0b", "⚠️  MMF réduit"),
        "contraindicated":("#1c0505", "#ef4444", "🚫 MMF suspendu"),
    }
    mmf_bg, mmf_border, mmf_titre = mmf_colors[mmf_niveau]

    if dose_mmf_rec == 0:
        mmf_dose_str  = "Suspendre"
        mmf_prise_str = "Arrêt temporaire"
    else:
        mmf_dose_str  = f"{dose_mmf_rec} g/j"
        mmf_prise_str = f"{dose_mmf_prise} g × 2 /j (q12h)"

    st.markdown(f"""<div style="background:{mmf_bg};border:2px solid {mmf_border};border-radius:14px;padding:22px 24px;height:100%">
      <div style="color:#94a3b8;font-size:0.68rem;text-transform:uppercase;letter-spacing:.08em;margin-bottom:12px;font-weight:700">{mmf_titre}</div>
      <div style="font-size:2.6rem;font-weight:900;color:#f1f5f9;line-height:1">{mmf_dose_str}</div>
      <div style="font-size:1.2rem;color:#93c5fd;font-weight:600;margin-top:8px">{mmf_prise_str}</div>
      <div style="color:#475569;font-size:0.78rem;margin-top:4px">Mycophenolate mofetil — CellCept®</div>
      <div style="background:#0f0f11;border-radius:6px;padding:10px;margin-top:12px;color:#94a3b8;font-size:0.78rem">{mmf_comment}</div>
    </div>""", unsafe_allow_html=True)

# ─── RAISONNEMENT CLINIQUE ────────────────────────────────────────────────────
st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
st.markdown("<div style='color:#64748b;font-size:0.7rem;text-transform:uppercase;letter-spacing:.08em;margin-bottom:10px'>🔍 Raisonnement clinique</div>", unsafe_allow_html=True)

r1, r2, r3 = st.columns(3)
t_mid = (t_min + t_max) / 2
raw_pk = round(dose_tac * t_mid / c0, 2) if c0 > 0 else dose_tac

with r1:
    st.markdown(f"""<div style="background:#111113;border:1px solid #27272a;border-radius:10px;padding:14px">
      <div style="color:#64748b;font-size:0.7rem;margin-bottom:8px;font-weight:600">① Statut C0 résiduel</div>
      <div style="color:{c0_color};font-weight:700;font-size:0.95rem">{c0_icon} {c0_statut.capitalize()}</div>
      <div style="color:#94a3b8;font-size:0.78rem;margin-top:6px">{c0} ng/mL · cible {t_min}–{t_max} ng/mL</div>
      <div style="color:#64748b;font-size:0.72rem;margin-top:4px">Phase {phase['label']} post-greffe</div>
    </div>""", unsafe_allow_html=True)

with r2:
    st.markdown(f"""<div style="background:#111113;border:1px solid #27272a;border-radius:10px;padding:14px">
      <div style="color:#64748b;font-size:0.7rem;margin-bottom:8px;font-weight:600">② Ajustement PK proportionnel</div>
      <div style="color:#e2e8f0;font-weight:700;font-size:0.95rem">Dose PK : {dose_pk} mg/j</div>
      <div style="color:#94a3b8;font-size:0.78rem;margin-top:6px">{dose_tac} × ({t_mid} / {c0}) = {raw_pk} → arrondi {dose_pk}</div>
      <div style="color:#64748b;font-size:0.72rem;margin-top:4px">Règle de trois PK tacrolimus (Staatz & Tett, 2004)</div>
    </div>""", unsafe_allow_html=True)

with r3:
    st.markdown(f"""<div style="background:#111113;border:1px solid #27272a;border-radius:10px;padding:14px">
      <div style="color:#64748b;font-size:0.7rem;margin-bottom:8px;font-weight:600">③ Plafond néphroprotecteur</div>
      <div style="color:{stade_color};font-weight:700;font-size:0.95rem">Max : {plafond} mg/j</div>
      <div style="color:#94a3b8;font-size:0.78rem;margin-top:6px">{poids} kg × 0.1 mg/kg × facteur {fr} (stade {stade})</div>
      <div style="color:#64748b;font-size:0.72rem;margin-top:4px">Ojo et al. NEJM 2003 · Naesens et al. CJASN 2009</div>
    </div>""", unsafe_allow_html=True)

st.markdown(f"""<div style="background:#111113;border:1px solid #27272a;border-radius:10px;padding:12px 16px;margin-top:8px">
  <span style="color:#e2e8f0;font-weight:700;font-size:0.88rem">Dose retenue = min(PK {dose_pk}, plafond rénal {plafond}) = {dose_rec} mg/j</span>
  <span style="color:#64748b;font-size:0.78rem"> — arrondi capsule 0.5 mg · split q12h → {dose_prise} mg matin + {dose_prise} mg soir</span>
</div>""", unsafe_allow_html=True)

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
with mon3: st.markdown(mon_box("NFS / neutrophiles", "À chaque contrôle", "#94a3b8"), unsafe_allow_html=True)
with mon4: st.markdown(mon_box("Kaliémie + PA", "À chaque contrôle", "#94a3b8"), unsafe_allow_html=True)

# ─── INTERACTIONS ─────────────────────────────────────────────────────────────
st.markdown("""<div style="background:#1c1208;border:1px solid #92400e;border-radius:10px;padding:14px 18px;margin-top:8px">
  <div style="color:#fbbf24;font-size:0.78rem;font-weight:700;margin-bottom:6px">⚠️ Interactions majeures — vérifier à chaque modification du traitement</div>
  <div style="display:flex;gap:32px;flex-wrap:wrap">
    <div style="color:#d97706;font-size:0.76rem"><strong>↑ taux Tac :</strong> azithromycine, fluconazole, voriconazole, diltiazem, vérapamil, amiodarone</div>
    <div style="color:#d97706;font-size:0.76rem"><strong>↓ taux Tac :</strong> rifampicine, phénytoïne, carbamazépine, millepertuis</div>
    <div style="color:#d97706;font-size:0.76rem"><strong>MMF :</strong> antiacides (↓ absorption), ciclosporine (↓ taux MMF) — espacer +2h</div>
  </div>
</div>""", unsafe_allow_html=True)

# ─── RÉFÉRENCES ───────────────────────────────────────────────────────────────
with st.expander("📚  Références scientifiques"):
    for titre, texte in REFS:
        st.markdown(f"""<div style="background:#111113;border-left:3px solid #3b82f6;border-radius:0 8px 8px 0;padding:10px 14px;margin-bottom:8px">
          <div style="color:#93c5fd;font-weight:600;font-size:0.82rem;margin-bottom:4px">{titre}</div>
          <div style="color:#94a3b8;font-size:0.78rem">{texte}</div>
        </div>""", unsafe_allow_html=True)

# ─── DISCLAIMER ───────────────────────────────────────────────────────────────
st.markdown("""<div style="background:#0f0f11;border:1px solid #1e1e21;border-radius:10px;padding:12px 20px;color:#475569;font-size:0.75rem;text-align:center;margin-top:8px">
  ⚕️ <strong style="color:#64748b">Outil d'aide à la décision — ne remplace pas la concertation d'équipe de transplantation.</strong>
  Adapter systématiquement au protocole institutionnel. MedFlow AI — usage professionnel exclusif.
</div>""", unsafe_allow_html=True)
