import streamlit as st
import math

st.set_page_config(
    page_title="Tacrolimus Greffe Cardiaque — MedFlow AI",
    page_icon="🫀",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.markdown("""
<style>
[data-testid="stAppViewContainer"] { background: #09090b; color: #f1f5f9; }
[data-testid="stSidebar"] { display: none; }
[data-testid="stHeader"] { background: transparent; }
[data-testid="stMainBlockContainer"] { padding-top: 2rem; }
.stNumberInput label, .stSelectbox label, .stRadio label { color: #94a3b8 !important; font-size: 0.82rem !important; }
.stNumberInput input { background: #18181b !important; border: 1px solid #27272a !important; color: #f1f5f9 !important; border-radius: 8px !important; }
.stSelectbox > div > div { background: #18181b !important; border: 1px solid #27272a !important; color: #f1f5f9 !important; border-radius: 8px !important; }
div[data-baseweb="radio"] > label > div:first-child { background: #27272a !important; border-color: #3f3f46 !important; }
.stRadio [data-testid="stMarkdownContainer"] p { color: #d1d5db; font-size: 0.88rem; }
h1, h2, h3 { color: #f1f5f9 !important; }
hr { border-color: #27272a; }
footer { visibility: hidden; }
[data-testid="stVerticalBlock"] { gap: 0.5rem; }
</style>
""", unsafe_allow_html=True)

# ─── Constantes ───────────────────────────────────────────────────────────────
PHASES = {
    "M0 – M3  (phase précoce)":    {"min": 10, "max": 15, "label": "M0–M3"},
    "M3 – M12  (maintenance)":     {"min": 8,  "max": 12, "label": "M3–M12"},
    "> 1 an  (phase stable)":      {"min": 5,  "max": 10, "label": ">1 an"},
}

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

def recommander_dose(dose_act, c0, t_min, t_max, dfg, poids):
    """
    Étape 1 — ajustement PK proportionnel vers le milieu de la cible.
    Étape 2 — plafond néphroprotecteur selon le DFG.
    Étape 3 — plancher (ne jamais tomber sous 0.5 mg/j).
    """
    # Cible milieu de fourchette
    t_mid = (t_min + t_max) / 2

    # Dose PK proportionnelle (règle de trois tacrolimus)
    if c0 > 0:
        dose_pk = dose_act * (t_mid / c0)
    else:
        dose_pk = dose_act

    # Plafond rénal : 0.1 mg/kg/j max × facteur DFG
    if   dfg >= 60: facteur_renal = 1.00
    elif dfg >= 45: facteur_renal = 0.90
    elif dfg >= 30: facteur_renal = 0.80
    elif dfg >= 15: facteur_renal = 0.70
    else:           facteur_renal = 0.50

    plafond = poids * 0.1 * facteur_renal

    dose_finale = min(dose_pk, plafond)
    dose_finale = max(dose_finale, 0.5)
    return arrondir_05(dose_finale), arrondir_05(dose_pk), arrondir_05(plafond)

def statut_c0(c0, t_min, t_max):
    if c0 < t_min:
        return "subthérapeutique", "#ef4444", f"{c0} ng/mL < {t_min} ng/mL (cible min)", "🔴"
    if c0 > t_max:
        return "suprathérapeutique", "#f59e0b", f"{c0} ng/mL > {t_max} ng/mL (cible max)", "⚠️"
    return "thérapeutique", "#10b981", f"{c0} ng/mL ∈ [{t_min}–{t_max}] ng/mL", "✅"

# ─── EN-TÊTE ──────────────────────────────────────────────────────────────────
st.markdown("""
<div style="display:flex;align-items:center;gap:16px;padding:0 0 8px">
  <div style="font-size:2.2rem">🫀</div>
  <div>
    <h1 style="margin:0;font-size:1.75rem;font-weight:800">Tacrolimus — Greffe Cardiaque</h1>
    <p style="margin:0;color:#64748b;font-size:0.88rem">
      Calcul du dosage adapté à la fonction rénale · Cockcroft-Gault · MedFlow AI
    </p>
  </div>
</div>
<hr style="margin:12px 0 20px">
""", unsafe_allow_html=True)

# ─── FORMULAIRE ───────────────────────────────────────────────────────────────
col_pat, col_tac = st.columns([1, 1], gap="large")

with col_pat:
    st.markdown("<div style='color:#94a3b8;font-size:0.72rem;text-transform:uppercase;letter-spacing:.08em;margin-bottom:10px'>👤 Données patient</div>", unsafe_allow_html=True)
    age   = st.number_input("Âge (ans)",            min_value=18,   max_value=100,  value=55,  step=1)
    sexe  = st.radio("Sexe biologique",              ["Homme", "Femme"], horizontal=True)
    poids = st.number_input("Poids (kg)",            min_value=30.0, max_value=250.0, value=70.0, step=0.5)
    creat = st.number_input("Créatininémie (µmol/L)", min_value=20.0, max_value=2000.0, value=120.0, step=1.0)

with col_tac:
    st.markdown("<div style='color:#94a3b8;font-size:0.72rem;text-transform:uppercase;letter-spacing:.08em;margin-bottom:10px'>💊 Tacrolimus (dernier bilan)</div>", unsafe_allow_html=True)
    phase_label = st.selectbox("Phase post-greffe", list(PHASES.keys()))
    c0    = st.number_input("Taux résiduel C0 (ng/mL)", min_value=0.1, max_value=50.0, value=12.0, step=0.1)
    dose_act = st.number_input("Dose actuelle (mg/j)", min_value=0.5, max_value=30.0, value=5.0, step=0.5)

# ─── CALCULS ──────────────────────────────────────────────────────────────────
phase      = PHASES[phase_label]
t_min, t_max = phase["min"], phase["max"]
dfg        = calc_dfg(age, poids, sexe, creat)
stade, stade_desc, stade_color = get_stade(dfg)
c0_statut, c0_color, c0_detail, c0_icon = statut_c0(c0, t_min, t_max)
dose_rec, dose_pk, plafond = recommander_dose(dose_act, c0, t_min, t_max, dfg, poids)
dose_prise = arrondir_05(dose_rec / 2)

variation   = round((dose_rec - dose_act) / dose_act * 100, 1) if dose_act else 0
var_label   = f"+{variation} %" if variation > 0 else f"{variation} %"
var_color   = "#10b981" if variation > 0 else ("#ef4444" if variation < -5 else "#f59e0b")

# ─── MÉTRIQUES RAPIDES ────────────────────────────────────────────────────────
st.markdown("<hr style='margin:20px 0 16px'>", unsafe_allow_html=True)
m1, m2, m3, m4 = st.columns(4)

with m1:
    creat_mgdl = round(creat / 88.42, 2)
    st.markdown(f"""
    <div style="background:#111113;border:1px solid #27272a;border-radius:10px;padding:14px;text-align:center">
      <div style="color:#64748b;font-size:0.7rem;text-transform:uppercase;letter-spacing:.06em">DFG estimé</div>
      <div style="font-size:2rem;font-weight:800;color:{stade_color};margin:4px 0">{dfg}</div>
      <div style="color:#64748b;font-size:0.72rem">mL/min (CG)</div>
    </div>""", unsafe_allow_html=True)

with m2:
    st.markdown(f"""
    <div style="background:#111113;border:1px solid #27272a;border-radius:10px;padding:14px;text-align:center">
      <div style="color:#64748b;font-size:0.7rem;text-transform:uppercase;letter-spacing:.06em">Stade IRC</div>
      <div style="font-size:2rem;font-weight:800;color:{stade_color};margin:4px 0">{stade}</div>
      <div style="color:#64748b;font-size:0.72rem">{stade_desc}</div>
    </div>""", unsafe_allow_html=True)

with m3:
    st.markdown(f"""
    <div style="background:#111113;border:1px solid #27272a;border-radius:10px;padding:14px;text-align:center">
      <div style="color:#64748b;font-size:0.7rem;text-transform:uppercase;letter-spacing:.06em">C0 actuel</div>
      <div style="font-size:2rem;font-weight:800;color:{c0_color};margin:4px 0">{c0}</div>
      <div style="color:#64748b;font-size:0.72rem">ng/mL — {c0_statut}</div>
    </div>""", unsafe_allow_html=True)

with m4:
    st.markdown(f"""
    <div style="background:#111113;border:1px solid #27272a;border-radius:10px;padding:14px;text-align:center">
      <div style="color:#64748b;font-size:0.7rem;text-transform:uppercase;letter-spacing:.06em">Variation dose</div>
      <div style="font-size:2rem;font-weight:800;color:{var_color};margin:4px 0">{var_label}</div>
      <div style="color:#64748b;font-size:0.72rem">vs dose actuelle</div>
    </div>""", unsafe_allow_html=True)

# ─── RECOMMANDATION PRINCIPALE ────────────────────────────────────────────────
st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)

if dfg < 15:
    rec_bg, rec_border = "#1c0505", "#dc2626"
    rec_titre = "🚫 Avis néphrologue et transplanteur impératif"
    rec_note  = "IRC terminale. Le dosage ne peut pas être calculé automatiquement. Concertation multidisciplinaire urgente. Discuter switch vers schéma sans calcineurine."
elif dose_pk > plafond and c0 < t_min:
    rec_bg, rec_border = "#1c1005", "#f97316"
    rec_titre = "⚠️ Conflit PK / Néphroprotection"
    rec_note  = f"La PK nécessiterait {dose_pk} mg/j pour atteindre la cible, mais le plafond rénal (DFG {dfg} mL/min) impose {plafond} mg/j max. Dose retenue = plafond. Surveillance biopsique à envisager."
else:
    rec_bg, rec_border = "#071a10", "#10b981"
    rec_titre = "✅ Dosage recommandé calculé"
    rec_note  = None

st.markdown(f"""
<div style="background:{rec_bg};border:2px solid {rec_border};border-radius:16px;padding:28px 32px;margin-bottom:8px">
  <div style="color:#94a3b8;font-size:0.72rem;text-transform:uppercase;letter-spacing:.08em;margin-bottom:14px;font-weight:600">
    {rec_titre}
  </div>
  <div style="display:flex;align-items:center;gap:40px;flex-wrap:wrap">
    <div>
      <div style="color:#64748b;font-size:0.75rem;margin-bottom:4px">Dose journalière</div>
      <div style="font-size:3rem;font-weight:900;color:#f1f5f9;line-height:1">{dose_rec} <span style="font-size:1.2rem;color:#94a3b8">mg/j</span></div>
    </div>
    <div style="width:1px;height:56px;background:#27272a"></div>
    <div>
      <div style="color:#64748b;font-size:0.75rem;margin-bottom:4px">Répartition q12h</div>
      <div style="font-size:2rem;font-weight:700;color:#93c5fd">{dose_prise} mg  ×  2 /j</div>
      <div style="color:#475569;font-size:0.75rem">matin + soir (toutes les 12h)</div>
    </div>
    <div style="width:1px;height:56px;background:#27272a"></div>
    <div>
      <div style="color:#64748b;font-size:0.75rem;margin-bottom:4px">Dose actuelle</div>
      <div style="font-size:1.5rem;font-weight:600;color:#64748b">{dose_act} mg/j</div>
      <div style="color:{var_color};font-size:0.85rem;font-weight:600">{var_label}</div>
    </div>
  </div>
  {f'<div style="background:#0f0f11;border-radius:8px;padding:12px;margin-top:16px;color:#fbbf24;font-size:0.83rem">{rec_note}</div>' if rec_note else ''}
</div>
""", unsafe_allow_html=True)

# ─── RATIONALE ────────────────────────────────────────────────────────────────
st.markdown(f"""
<div style="background:#111113;border:1px solid #27272a;border-radius:12px;padding:20px 24px;margin-bottom:8px">
  <div style="color:#64748b;font-size:0.72rem;text-transform:uppercase;letter-spacing:.08em;margin-bottom:14px">🔍 Raisonnement clinique</div>
  <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:16px">

    <div style="background:#09090b;border-radius:8px;padding:12px">
      <div style="color:#64748b;font-size:0.72rem;margin-bottom:6px">① Statut C0</div>
      <div style="color:{c0_color};font-weight:600;font-size:0.9rem">{c0_icon} {c0_statut.capitalize()}</div>
      <div style="color:#94a3b8;font-size:0.78rem;margin-top:4px">{c0_detail}</div>
      <div style="color:#64748b;font-size:0.75rem;margin-top:4px">Cible phase {phase['label']} : {t_min}–{t_max} ng/mL</div>
    </div>

    <div style="background:#09090b;border-radius:8px;padding:12px">
      <div style="color:#64748b;font-size:0.72rem;margin-bottom:6px">② Ajustement PK</div>
      <div style="color:#e2e8f0;font-weight:600;font-size:0.9rem">Dose PK : {dose_pk} mg/j</div>
      <div style="color:#94a3b8;font-size:0.78rem;margin-top:4px">
        {dose_act} mg/j × ({(t_min+t_max)/2} / {c0}) = {round(dose_act * ((t_min+t_max)/2) / c0, 2)} mg/j → arrondi {dose_pk} mg/j
      </div>
    </div>

    <div style="background:#09090b;border-radius:8px;padding:12px">
      <div style="color:#64748b;font-size:0.72rem;margin-bottom:6px">③ Plafond rénal (DFG {dfg})</div>
      <div style="color:{stade_color};font-weight:600;font-size:0.9rem">Max : {plafond} mg/j</div>
      <div style="color:#94a3b8;font-size:0.78rem;margin-top:4px">
        {poids} kg × 0.1 mg/kg × facteur {round(({'G1':1.0,'G2':1.0,'G3a':0.9,'G3b':0.8,'G4':0.7,'G5':0.5}[stade]),1)} (stade {stade}) = {plafond} mg/j
      </div>
    </div>

  </div>
  <div style="background:#09090b;border-radius:8px;padding:12px;margin-top:12px;color:#94a3b8;font-size:0.8rem">
    <strong style="color:#e2e8f0">Dose retenue = min(PK {dose_pk}, plafond rénal {plafond}) = {dose_rec} mg/j</strong>
    — arrondi capsule 0.5 mg · split q12h → {dose_prise} mg matin + {dose_prise} mg soir
  </div>
</div>
""", unsafe_allow_html=True)

# ─── MONITORING ───────────────────────────────────────────────────────────────
if dfg >= 45:
    monitor_freq  = "hebdomadaire × 4, puis mensuelle × 3"
    trough_freq   = "J7, J14, J30 après chaque changement de dose"
    monitor_color = "#10b981"
elif dfg >= 30:
    monitor_freq  = "hebdomadaire × 8, puis bimensuelle"
    trough_freq   = "J7, J14, J21 — cible bas de fourchette"
    monitor_color = "#f59e0b"
else:
    monitor_freq  = "bihebdomadaire — surveillance rapprochée"
    trough_freq   = "2×/semaine minimum"
    monitor_color = "#ef4444"

st.markdown(f"""
<div style="background:#111113;border:1px solid #27272a;border-radius:12px;padding:18px 24px;margin-bottom:8px">
  <div style="color:#64748b;font-size:0.72rem;text-transform:uppercase;letter-spacing:.08em;margin-bottom:12px">📋 Plan de surveillance recommandé</div>
  <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:12px">
    <div>
      <div style="color:#64748b;font-size:0.72rem;margin-bottom:4px">Créatinine / DFG</div>
      <div style="color:{monitor_color};font-size:0.85rem;font-weight:600">{monitor_freq}</div>
    </div>
    <div>
      <div style="color:#64748b;font-size:0.72rem;margin-bottom:4px">Taux résiduel C0</div>
      <div style="color:{monitor_color};font-size:0.85rem;font-weight:600">{trough_freq}</div>
    </div>
    <div>
      <div style="color:#64748b;font-size:0.72rem;margin-bottom:4px">Kaliémie + NFS</div>
      <div style="color:#94a3b8;font-size:0.85rem;font-weight:600">À chaque contrôle</div>
    </div>
  </div>
</div>
""", unsafe_allow_html=True)

# ─── INTERACTIONS ─────────────────────────────────────────────────────────────
st.markdown("""
<div style="background:#1c1208;border:1px solid #92400e;border-radius:10px;padding:14px 20px;margin-bottom:8px">
  <div style="color:#fbbf24;font-size:0.8rem;font-weight:600;margin-bottom:6px">⚠️ Interactions majeures à vérifier systématiquement</div>
  <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;color:#d97706;font-size:0.78rem">
    <div>↑ taux (risque toxicité) : azithromycine, fluconazole, voriconazole, diltiazem, vérapamil, amiodarone</div>
    <div>↓ taux (risque rejet) : rifampicine, phénytoïne, carbamazépine, millepertuis</div>
  </div>
  <div style="color:#92400e;font-size:0.75rem;margin-top:6px">Pamplemousse CI · Contrôle C0 systématique après tout ajout/retrait médicamenteux</div>
</div>
""", unsafe_allow_html=True)

# ─── DISCLAIMER ───────────────────────────────────────────────────────────────
st.markdown("""
<div style="background:#0f0f11;border:1px solid #1e1e21;border-radius:10px;padding:12px 20px;color:#475569;font-size:0.75rem;text-align:center">
  ⚕️ <strong style="color:#64748b">Outil d'aide à la décision — ne remplace pas le jugement clinique ni la concertation d'équipe.</strong>
  Vérifier la cohérence avec le protocole institutionnel de transplantation. MedFlow AI — usage professionnel exclusif.
</div>
""", unsafe_allow_html=True)
