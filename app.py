import streamlit as st
import os
from datetime import datetime

try:
    import plotly.graph_objects as go
    PLOTLY_OK = True
except ImportError:
    PLOTLY_OK = False

from calculations import (
    PHASES, REFS, META_DATA, CYP3A4_INTERACTIONS,
    calc_dfg, get_stade, arrondir_05, interp_sodium, interp_potassium,
    recommander_tacrolimus, delta_str, correct_c0_hematocrit,
    MMF_PHASE_TARGETS, MMF_REFS, recommander_mmf,
    PRED_CIBLES, PRED_REFS, recommander_prednisolone,
)
from ai_gen import generate_consultation_summary, AI_OK
from db import (
    init_db, generate_patient_id, upsert_patient, save_consultation,
    get_consultations, count_consultations, get_all_patients, search_patients,
)
from pdf_gen import generate_pdf, PDF_OK

# ─── Auth depuis Streamlit secrets ────────────────────────────────────────────
AUTH_ENABLED = False
_auth        = None
try:
    import streamlit_authenticator as stauth
    if "auth" in st.secrets:
        _s = st.secrets["auth"]
        _credentials = {
            "usernames": {
                _s["username"]: {
                    "email":    _s["email"],
                    "name":     _s["name"],
                    "password": _s["password_hash"],
                }
            }
        }
        _auth = stauth.Authenticate(
            _credentials,
            "medflow_cookie",
            _s["cookie_key"],
            cookie_expiry_days=30,
        )
        AUTH_ENABLED = True
except Exception:
    pass

# ─── Stripe optionnel (Payment Link pré-créé) ─────────────────────────────────
STRIPE_CHECKOUT_URL = os.environ.get("STRIPE_CHECKOUT_URL", "")
STRIPE_ENABLED      = bool(STRIPE_CHECKOUT_URL)

# ─── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Tacrolimus — Greffe Cardiaque · MedFlow AI",
    page_icon="🫀",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
[data-testid="stAppViewContainer"] { background: #09090b; color: #f1f5f9; }
[data-testid="stSidebar"] { background: #0d0d10; border-right: 1px solid #27272a; }
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
.stTabs [data-baseweb="tab-list"] { background: #111113; border-radius: 10px; padding: 4px; gap: 4px; }
.stTabs [data-baseweb="tab"] { background: transparent; color: #64748b; border-radius: 6px; font-size: 0.82rem; }
.stTabs [aria-selected="true"] { background: #1e1e24 !important; color: #f1f5f9 !important; }
hr { border-color: #27272a; }
footer { visibility: hidden; }
/* ── Login page ── */
[data-testid="stForm"] {
  background: #111113 !important;
  border: 1px solid #27272a !important;
  border-radius: 14px !important;
  padding: 1.6rem 2rem !important;
  max-width: 420px !important;
  margin: 0 auto !important;
}
[data-testid="stForm"] h2 { color: #f1f5f9 !important; }
[data-testid="stForm"] label { color: #94a3b8 !important; font-size: 0.82rem !important; }
[data-testid="stForm"] input {
  background: #18181b !important; border: 1px solid #3f3f46 !important;
  color: #f1f5f9 !important; border-radius: 8px !important; }
[data-testid="stForm"] button[kind="primaryFormSubmit"] {
  background: linear-gradient(135deg,#7c3aed,#2563eb) !important;
  border: none !important; color: white !important;
  width: 100% !important; border-radius: 8px !important;
  font-weight: 700 !important; padding: 0.55rem !important; }
</style>
""", unsafe_allow_html=True)

# ─── Init DB + auth ───────────────────────────────────────────────────────────
init_db()

if AUTH_ENABLED and _auth is not None:
    # Affiche le logo MedFlow AI avant le formulaire de connexion
    _auth_status_check = st.session_state.get("authentication_status")
    if _auth_status_check is not True:
        st.markdown("""
<div style="display:flex;flex-direction:column;align-items:center;padding:2.5rem 0 1rem 0;">
  <svg width="220" height="72" viewBox="0 0 220 72" xmlns="http://www.w3.org/2000/svg">
    <defs>
      <linearGradient id="hg" x1="0%" y1="0%" x2="100%" y2="100%">
        <stop offset="0%" style="stop-color:#7c3aed"/>
        <stop offset="100%" style="stop-color:#2563eb"/>
      </linearGradient>
      <linearGradient id="tg" x1="0%" y1="0%" x2="100%" y2="0%">
        <stop offset="0%" style="stop-color:#a78bfa"/>
        <stop offset="100%" style="stop-color:#60a5fa"/>
      </linearGradient>
    </defs>
    <!-- Heart icon -->
    <path d="M30 18 C30 12 24 8 18 12 C12 16 12 24 18 30 L30 42 L42 30 C48 24 48 16 42 12 C36 8 30 12 30 18Z"
          fill="url(#hg)" opacity="0.95"/>
    <!-- ECG pulse line over heart -->
    <polyline points="14,30 19,30 22,22 25,38 28,26 31,30 38,30 41,30"
              fill="none" stroke="white" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" opacity="0.9"/>
    <!-- MedFlow text -->
    <text x="56" y="32" font-family="'Helvetica Neue',Arial,sans-serif" font-size="22" font-weight="800"
          fill="url(#tg)" letter-spacing="-0.5">MedFlow</text>
    <!-- AI badge -->
    <rect x="158" y="16" width="26" height="18" rx="5" fill="url(#hg)"/>
    <text x="171" y="29" font-family="'Helvetica Neue',Arial,sans-serif" font-size="11" font-weight="700"
          fill="white" text-anchor="middle" letter-spacing="0.5">AI</text>
    <!-- Subtitle -->
    <text x="56" y="52" font-family="'Helvetica Neue',Arial,sans-serif" font-size="11" font-weight="400"
          fill="#94a3b8" letter-spacing="0.3">Aide à la décision posologique</text>
  </svg>
  <p style="color:#64748b;font-size:0.78rem;margin-top:0.5rem;letter-spacing:0.05em;">Transplantation cardiaque · Tacrolimus</p>
</div>
""", unsafe_allow_html=True)

    _auth.login()
    auth_status = st.session_state.get("authentication_status")
    if auth_status is False:
        st.error("Identifiants incorrects — accès refusé")
        st.stop()
    elif auth_status is None:
        st.stop()
    else:
        with st.sidebar:
            _auth.logout()

# ─── Sidebar — Recherche patient ──────────────────────────────────────────────
with st.sidebar:
    st.markdown("<div style='color:#8b5cf6;font-size:0.75rem;font-weight:700;text-transform:uppercase;letter-spacing:.08em;margin-bottom:10px'>🔍 Recherche patient</div>", unsafe_allow_html=True)
    search_q = st.text_input("Nom ou prénom", placeholder="Ex: DUPONT", label_visibility="collapsed", key="sidebar_search")

    if search_q and len(search_q.strip()) >= 2:
        results = search_patients(search_q)
        if results:
            for pid, nom, prenom, _, nb in results:
                label = f"{prenom.capitalize()} {nom} · {nb} bilan(s)"
                if st.button(label, key=f"sb_{pid}", use_container_width=True):
                    st.session_state["nom"]    = nom
                    st.session_state["prenom"] = prenom.capitalize()
                    st.rerun()
        else:
            st.markdown("<div style='color:#64748b;font-size:0.78rem'>Aucun résultat</div>", unsafe_allow_html=True)

    st.markdown("<hr style='border-color:#27272a;margin:12px 0'>", unsafe_allow_html=True)
    st.markdown("<div style='color:#64748b;font-size:0.72rem;font-weight:700;text-transform:uppercase;letter-spacing:.06em;margin-bottom:8px'>📋 Patients enregistrés</div>", unsafe_allow_html=True)

    all_pats = get_all_patients()
    if all_pats:
        for pid, nom, prenom, _, nb in all_pats[:30]:
            st.markdown(
                f"<div style='background:#111113;border:1px solid #27272a;border-radius:6px;padding:6px 8px;margin-bottom:4px'>"
                f"<span style='color:#93c5fd;font-size:0.78rem;font-weight:600'>{prenom.capitalize()} {nom}</span>"
                f"<span style='color:#475569;font-size:0.72rem'> · {nb} bilan(s)</span>"
                f"</div>",
                unsafe_allow_html=True
            )
        if len(all_pats) > 30:
            st.markdown(f"<div style='color:#475569;font-size:0.72rem;margin-top:4px'>… et {len(all_pats)-30} autres</div>", unsafe_allow_html=True)
    else:
        st.markdown("<div style='color:#475569;font-size:0.78rem'>Aucun patient enregistré</div>", unsafe_allow_html=True)

# ─── Tabs ─────────────────────────────────────────────────────────────────────
tab_outil, tab_mmf, tab_pred, tab_mentions = st.tabs(["🫀  Tacrolimus", "💊  MMF / Cellcept®", "🟠  Prednisolone", "⚖️  Mentions légales & CGU"])

# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — OUTIL CLINIQUE
# ══════════════════════════════════════════════════════════════════════════════
with tab_outil:

    # ── EN-TÊTE ───────────────────────────────────────────────────────────────
    st.markdown("""
    <div style="padding:0 0 6px">
      <div style="display:flex;align-items:center;gap:14px">
        <span style="font-size:2rem">🫀</span>
        <div>
          <div style="font-size:1.65rem;font-weight:800;color:#f1f5f9">Tacrolimus — Greffe Cardiaque</div>
          <div style="color:#64748b;font-size:0.82rem;margin-top:2px">Dosage adapté · Ionogramme intégré · Suivi longitudinal · MedFlow AI</div>
        </div>
      </div>
    </div>
    """, unsafe_allow_html=True)
    st.markdown("---")

    # ── IDENTIFICATION PATIENT ────────────────────────────────────────────────
    st.markdown("<div style='color:#8b5cf6;font-size:0.7rem;text-transform:uppercase;letter-spacing:.08em;font-weight:700;margin-bottom:10px'>👤 Identification du patient</div>", unsafe_allow_html=True)
    pid_c1, pid_c2, pid_c3 = st.columns([1, 1, 2], gap="medium")
    with pid_c1:
        pat_nom    = st.text_input("Nom de famille", placeholder="DUPONT", key="nom")
    with pid_c2:
        pat_prenom = st.text_input("Prénom", placeholder="Jean", key="prenom")

    patient_valid = bool(pat_nom.strip() and pat_prenom.strip())
    if patient_valid:
        pat_id  = generate_patient_id(pat_nom, pat_prenom)
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

    # ── FORMULAIRE ────────────────────────────────────────────────────────────
    col_pat, col_ion, col_tac = st.columns([1.1, 0.9, 1], gap="large")

    with col_pat:
        st.markdown("<div style='color:#8b5cf6;font-size:0.7rem;text-transform:uppercase;letter-spacing:.08em;font-weight:700;margin-bottom:8px'>🧬 Données cliniques</div>", unsafe_allow_html=True)
        age   = st.number_input("Âge (ans)",          min_value=18,    max_value=100,    value=55,    step=1)
        sexe  = st.radio("Sexe biologique",            ["Homme", "Femme"], horizontal=True)
        poids = st.number_input("Poids (kg)",          min_value=30.0,  max_value=250.0,  value=70.0,  step=0.5)
        creat = st.number_input("Créatinine (µmol/L)", min_value=20.0,  max_value=2000.0, value=120.0, step=1.0)
        ht_pct = st.number_input(
            "Hématocrite (% — optionnel)",
            min_value=0.0, max_value=70.0, value=0.0, step=0.5,
            help="Si disponible, corrige le C0 mesuré pour l'hématocrite (Størset et al., Transpl Int 2014)"
        )

    with col_ion:
        st.markdown("<div style='color:#06b6d4;font-size:0.7rem;text-transform:uppercase;letter-spacing:.08em;font-weight:700;margin-bottom:8px'>🧪 Ionogramme sanguin</div>", unsafe_allow_html=True)
        na_val = st.number_input("Natrémie — Na⁺ (mmol/L)", min_value=100.0, max_value=170.0, value=140.0, step=1.0)
        k_val  = st.number_input("Kaliémie — K⁺ (mmol/L)",  min_value=1.0,   max_value=10.0,  value=4.5,   step=0.1)

    with col_tac:
        st.markdown("<div style='color:#10b981;font-size:0.7rem;text-transform:uppercase;letter-spacing:.08em;font-weight:700;margin-bottom:8px'>💊 Tacrolimus (Prograf®)</div>", unsafe_allow_html=True)
        phase_label = st.selectbox("Phase post-greffe", list(PHASES.keys()))
        c0_raw      = st.number_input("C0 résiduel (ng/mL)",  min_value=0.1,  max_value=50.0,  value=12.0,  step=0.1)
        dose_tac    = st.number_input("Dose actuelle (mg/j)", min_value=0.5,  max_value=30.0,  value=5.0,   step=0.5)

    with st.expander("📈  Bilan précédent — comparaison longitudinale (optionnel)"):
        lc1, lc2, lc3 = st.columns(3)
        with lc1: creat_prec = st.number_input("Créatinine précédente (µmol/L)", min_value=0.0, max_value=2000.0, value=0.0, step=1.0)
        with lc2: c0_prec    = st.number_input("C0 précédent (ng/mL)",           min_value=0.0, max_value=50.0,   value=0.0, step=0.1)
        with lc3: dose_prec  = st.number_input("Dose Tac précédente (mg/j)",     min_value=0.0, max_value=30.0,   value=0.0, step=0.5)

    # ── INTERACTIONS CYP3A4 sélecteur ─────────────────────────────────────────
    _n_prev = (len(st.session_state.get("sel_inh", [])) +
               len(st.session_state.get("sel_ind", [])) +
               len(st.session_state.get("sel_k",   [])))
    _badge = f" · 🔴 {_n_prev} active(s)" if _n_prev > 0 else " · aucune sélectionnée"
    with st.expander(f"💊  Traitements concomitants — CYP3A4 & kaliémie{_badge}"):
        ci1, ci2, ci3 = st.columns(3)
        with ci1:
            st.markdown("<div style='color:#ef4444;font-size:0.72rem;font-weight:700;margin-bottom:6px'>Inhibiteurs CYP3A4 — ↑ taux Tac</div>", unsafe_allow_html=True)
            sel_inh = st.multiselect("Inhibiteurs", [i["drug"] for i in CYP3A4_INTERACTIONS["inhibiteurs"]], label_visibility="collapsed", key="sel_inh")
        with ci2:
            st.markdown("<div style='color:#f59e0b;font-size:0.72rem;font-weight:700;margin-bottom:6px'>Inducteurs CYP3A4 — ↓ taux Tac</div>", unsafe_allow_html=True)
            sel_ind = st.multiselect("Inducteurs", [i["drug"] for i in CYP3A4_INTERACTIONS["inducteurs"]], label_visibility="collapsed", key="sel_ind")
        with ci3:
            st.markdown("<div style='color:#f97316;font-size:0.72rem;font-weight:700;margin-bottom:6px'>Aggravant hyperkaliémie</div>", unsafe_allow_html=True)
            sel_k   = st.multiselect("Hyper K+", [i["drug"] for i in CYP3A4_INTERACTIONS["hyperkaliemie"]], label_visibility="collapsed", key="sel_k")
        if not (sel_inh or sel_ind or sel_k):
            st.markdown("<div style='color:#475569;font-size:0.78rem'>Sélectionner les traitements concomitants pour activer les alertes automatiques</div>", unsafe_allow_html=True)

    # ── lookup global (utilisé aussi après les calculs) ───────────────────────
    _lookup = {x["drug"]: x for cat in CYP3A4_INTERACTIONS.values() for x in cat}
    _all_inter = (
        [(d, "inhibiteur") for d in sel_inh] +
        [(d, "inducteur")  for d in sel_ind] +
        [(d, "k")          for d in sel_k]
    )

    # ── CALCULS ───────────────────────────────────────────────────────────────
    phase        = PHASES[phase_label]
    t_min, t_max = phase["min"], phase["max"]
    dfg          = calc_dfg(age, poids, sexe, creat)
    stade, stade_desc, stade_color = get_stade(dfg)
    # Partage avec onglets MMF et Prednisolone
    st.session_state["_dfg"]         = dfg
    st.session_state["_phase_label"] = phase_label
    st.session_state["_stade"]       = stade
    st.session_state["_poids"]       = poids

    na_label, na_color, na_icon, na_urgent = interp_sodium(na_val)
    k_label,  k_color,  k_icon,  k_urgent  = interp_potassium(k_val)
    k_eleve = k_val > 5.5

    # Correction hématocrite si disponible
    c0 = correct_c0_hematocrit(c0_raw, ht_pct / 100) if ht_pct > 0 else c0_raw

    dose_rec, dose_pk, plafond, fr = recommander_tacrolimus(dose_tac, c0, t_min, t_max, dfg, poids, k_eleve)
    dose_prise = arrondir_05(dose_rec / 2)

    if   c0 < t_min: c0_statut, c0_color_hex, c0_icon = "subthérapeutique",   "#ef4444", "🔴"
    elif c0 > t_max: c0_statut, c0_color_hex, c0_icon = "suprathérapeutique", "#f59e0b", "⚠️"
    else:            c0_statut, c0_color_hex, c0_icon = "thérapeutique",       "#10b981", "✅"

    var_tac_label, var_tac_color = delta_str(dose_rec, dose_tac)
    dfg_prec      = calc_dfg(age, poids, sexe, creat_prec) if creat_prec > 0 else None
    delta_dfg_val = round(dfg - dfg_prec, 1) if dfg_prec else None
    delta_c0_val  = round(c0 - c0_prec, 1)   if c0_prec > 0 else None

    # Invalider résumé IA si paramètres cliniques modifiés depuis sa génération
    _ai_sig = (round(c0, 2), dose_rec, c0_statut, phase_label)
    if st.session_state.get("ai_summary") and st.session_state.get("_ai_sig") != _ai_sig:
        del st.session_state["ai_summary"]
        st.session_state.pop("_ai_sig", None)

    # ── ALERTES CYP3A4 AUTOMATIQUES ──────────────────────────────────────────
    if _all_inter:
        _has_cyp = any(c in ("inhibiteur", "inducteur") for _, c in _all_inter)
        _border  = "#dc2626" if _has_cyp else "#f97316"
        _cards   = ""
        for _drug, _cat in _all_inter:
            _info  = _lookup.get(_drug, {})
            _col   = "#ef4444" if _cat == "inhibiteur" else ("#f59e0b" if _cat == "inducteur" else "#f97316")
            _label = "Inhibiteur CYP3A4 — ↑ Tac" if _cat == "inhibiteur" else ("Inducteur CYP3A4 — ↓ Tac" if _cat == "inducteur" else "Hyper K⁺")
            _cards += (
                f"<div style='border-left:3px solid {_col};padding:8px 12px;margin-bottom:8px;"
                f"background:#1a0f0f;border-radius:0 6px 6px 0'>"
                f"<div style='display:flex;justify-content:space-between;align-items:center;margin-bottom:3px'>"
                f"<span style='color:{_col};font-weight:700;font-size:0.8rem'>{_drug}</span>"
                f"<span style='background:{_col}33;color:{_col};font-size:0.65rem;padding:2px 7px;"
                f"border-radius:4px;font-weight:700'>{_label}</span></div>"
                f"<div style='color:#fde68a;font-size:0.74rem'>Effet : {_info.get('effect','')}</div>"
                f"<div style='color:#d1d5db;font-size:0.74rem'>→ {_info.get('action','')}</div>"
                f"</div>"
            )
        # Corrélation C0 hors cible
        _corr = ""
        if c0_statut != "thérapeutique" and _has_cyp:
            _dir = "élevé" if c0_statut == "suprathérapeutique" else "bas"
            _cause = "inhibiteur(s) CYP3A4 détecté(s)" if any(c == "inhibiteur" for _, c in _all_inter) else "inducteur(s) CYP3A4 détecté(s)"
            _corr = (
                f"<div style='background:#0f1f0f;border:1px solid #16a34a;border-radius:8px;"
                f"padding:8px 12px;margin-top:4px'>"
                f"<span style='color:#4ade80;font-size:0.76rem;font-weight:700'>🔍 Corrélation détectée —</span>"
                f"<span style='color:#d1d5db;font-size:0.76rem'> C0 {_dir} ({c0} ng/mL) + {_cause} "
                f"→ interaction médicamenteuse à considérer comme cause potentielle</span></div>"
            )
        st.markdown(
            f"<div style='background:#120808;border:1.5px solid {_border};border-radius:12px;"
            f"padding:14px 16px;margin-top:10px'>"
            f"<div style='color:{_border};font-size:0.72rem;font-weight:700;text-transform:uppercase;"
            f"letter-spacing:.06em;margin-bottom:10px'>⚡ {len(_all_inter)} ALERTE(S) MÉDICAMENTEUSE(S) ACTIVE(S)</div>"
            f"{_cards}{_corr}</div>",
            unsafe_allow_html=True
        )

    # ── Alerte correction hématocrite ─────────────────────────────────────────
    if ht_pct > 0 and c0 != c0_raw:
        st.markdown(
            f"<div style='background:#0f1a2e;border:1px solid #3b82f6;border-radius:8px;padding:8px 14px;margin-top:8px'>"
            f"<span style='color:#93c5fd;font-size:0.78rem;font-weight:700'>Correction hématocrite appliquée ·</span>"
            f"<span style='color:#94a3b8;font-size:0.78rem'> Ht={ht_pct}% → C0 {c0_raw} → <strong style='color:#f1f5f9'>{c0} ng/mL</strong>"
            f" (Størset et al., Transpl Int 2014)</span></div>",
            unsafe_allow_html=True
        )

    # ── MÉTRIQUES RÉNALES ─────────────────────────────────────────────────────
    st.markdown("---")
    m1, m2, m3, m4 = st.columns(4)

    def metric_box(label, value, unit, color):
        return f"""<div style="background:#111113;border:1px solid #27272a;border-radius:10px;padding:14px;text-align:center">
          <div style="color:#64748b;font-size:0.7rem;text-transform:uppercase;letter-spacing:.05em">{label}</div>
          <div style="font-size:2rem;font-weight:800;color:{color};margin:4px 0;line-height:1">{value}</div>
          <div style="color:#64748b;font-size:0.72rem">{unit}</div>
        </div>"""

    with m1: st.markdown(metric_box("DFG estimé",      dfg,           "mL/min (CG)",            stade_color),  unsafe_allow_html=True)
    with m2: st.markdown(metric_box("Stade IRC",        stade,         stade_desc,               stade_color),  unsafe_allow_html=True)
    _c0_label = "C0 Ht-corrigé" if (ht_pct > 0 and c0 != c0_raw) else "C0 tacrolimus"
    _c0_unit  = f"ng/mL (mesuré : {c0_raw}) — {c0_statut}" if (ht_pct > 0 and c0 != c0_raw) else f"ng/mL — {c0_statut}"
    with m3: st.markdown(metric_box(_c0_label, c0, _c0_unit, c0_color_hex), unsafe_allow_html=True)
    with m4:
        if var_tac_label:
            st.markdown(metric_box("Variation dose Tac", var_tac_label, "vs dose actuelle", var_tac_color), unsafe_allow_html=True)
        else:
            st.markdown(metric_box("Dose actuelle Tac",  f"{dose_tac}", "mg/j", "#64748b"), unsafe_allow_html=True)

    # ── IONOGRAMME ────────────────────────────────────────────────────────────
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

    # ── TENDANCE ──────────────────────────────────────────────────────────────
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

    # ── RECOMMANDATION ────────────────────────────────────────────────────────
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

    _rec_parts = [
        f'<div style="background:{rec_bg};border:2px solid {rec_border};border-radius:14px;padding:28px 32px">',
        f'<div style="color:#94a3b8;font-size:0.68rem;text-transform:uppercase;letter-spacing:.08em;margin-bottom:14px;font-weight:700">{rec_titre}</div>',
        f'<div style="font-size:3rem;font-weight:900;color:#f1f5f9;line-height:1">{dose_rec} <span style="font-size:1.1rem;color:#94a3b8;font-weight:400">mg/j</span></div>',
        f'<div style="font-size:1.3rem;color:#93c5fd;font-weight:600;margin-top:10px">{dose_prise} mg × 2 /j (q12h)</div>',
        f'<div style="color:#475569;font-size:0.80rem;margin-top:5px">matin + soir — toutes les 12h · capsules Prograf® 0,5 / 1 / 5 mg</div>',
    ]
    if rec_note_html:
        _rec_parts.append(rec_note_html)
    _rec_parts.append('</div>')
    st.markdown(''.join(_rec_parts), unsafe_allow_html=True)

    # ── RAISONNEMENT CLINIQUE ─────────────────────────────────────────────────
    st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)
    st.markdown("<div style='color:#64748b;font-size:0.7rem;text-transform:uppercase;letter-spacing:.08em;margin-bottom:10px'>🔍 Raisonnement clinique</div>", unsafe_allow_html=True)

    r1, r2, r3 = st.columns(3)
    t_mid  = (t_min + t_max) / 2
    raw_pk = round(dose_tac * t_mid / c0, 2) if c0 > 0 else dose_tac

    _c0_detail = (
        f"Mesuré : {c0_raw} → corrigé Ht {ht_pct}% : {c0} ng/mL · cible {t_min}–{t_max} ng/mL"
        if (ht_pct > 0 and c0 != c0_raw) else
        f"{c0} ng/mL · cible {t_min}–{t_max} ng/mL"
    )

    with r1:
        st.markdown(f"""<div style="background:#111113;border:1px solid #27272a;border-radius:10px;padding:14px">
          <div style="color:#64748b;font-size:0.7rem;margin-bottom:8px;font-weight:600">① Statut C0 résiduel</div>
          <div style="color:{c0_color_hex};font-weight:700;font-size:0.95rem">{c0_icon} {c0_statut.capitalize()}</div>
          <div style="color:#94a3b8;font-size:0.78rem;margin-top:6px">{_c0_detail}</div>
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
        k_note_r = f" · K⁺ {k_val} → plafonné à {dose_tac} mg/j" if k_eleve else ""
        st.markdown(f"""<div style="background:#111113;border:1px solid #27272a;border-radius:10px;padding:14px">
          <div style="color:#64748b;font-size:0.7rem;margin-bottom:8px;font-weight:600">③ Plafond néphroprotecteur</div>
          <div style="color:{stade_color};font-weight:700;font-size:0.95rem">Max : {plafond} mg/j</div>
          <div style="color:#94a3b8;font-size:0.78rem;margin-top:6px">{poids} kg × 0,1 mg/kg × facteur {fr} (stade {stade}){k_note_r}</div>
          <div style="color:#64748b;font-size:0.72rem;margin-top:4px">Ojo NEJM 2003 · Naesens CJASN 2009 · Ekberg NEJM 2007</div>
        </div>""", unsafe_allow_html=True)

    k_suffix = f", dose actuelle {dose_tac} [K⁺ > 5,5]" if k_eleve else ""
    st.markdown(f"""<div style="background:#111113;border:1px solid #27272a;border-radius:10px;padding:12px 16px;margin-top:8px">
      <span style="color:#e2e8f0;font-weight:700;font-size:0.88rem">Dose retenue = min(PK {dose_pk}, plafond {plafond}{k_suffix}) = {dose_rec} mg/j</span>
      <span style="color:#64748b;font-size:0.78rem"> — capsule 0,5 mg · q12h → {dose_prise} mg matin + {dose_prise} mg soir</span>
    </div>""", unsafe_allow_html=True)

    # ── BOUTONS SAVE + PDF ────────────────────────────────────────────────────
    st.markdown("<div style='height:18px'></div>", unsafe_allow_html=True)
    btn1, btn2, btn3 = st.columns([1.2, 1.5, 1.2])

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

    with btn3:
        ai_clicked = st.button(
            "🤖 Résumé IA",
            disabled=not patient_valid,
            use_container_width=True,
            help="Génère un résumé prêt pour le DPI" if AI_OK else "Configurer ANTHROPIC_API_KEY dans les secrets Streamlit",
        )

    history_rows = get_consultations(pat_id) if patient_valid else []

    with btn2:
        if patient_valid:
            if STRIPE_ENABLED:
                st.link_button("💳 Souscrire pour le PDF", STRIPE_CHECKOUT_URL, use_container_width=True)
            else:
                pdf_bytes = generate_pdf(
                    pat_nom, pat_prenom, pat_id,
                    age, sexe, poids, creat, dfg, stade, stade_desc,
                    na_val, na_label, k_val, k_label,
                    phase_label, c0, c0_statut, t_min, t_max,
                    dose_tac, dose_rec, dose_pk, plafond, fr,
                    k_eleve, rec_titre, history_rows,
                    ai_summary=st.session_state.get("ai_summary"),
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

    # ── RÉSUMÉ IA ─────────────────────────────────────────────────────────────
    if ai_clicked and patient_valid:
        with st.spinner("Génération du résumé en cours…"):
            _summary = generate_consultation_summary(
                age, sexe, poids, dfg, stade, stade_desc,
                na_val, na_label, k_val, k_label,
                phase_label, c0, c0_statut, t_min, t_max,
                dose_tac, dose_rec, dose_prise,
                k_eleve=k_eleve, ht_pct=ht_pct, c0_raw=c0_raw,
            )
        if _summary:
            st.session_state["ai_summary"] = _summary
            st.session_state["_ai_sig"] = _ai_sig
        else:
            st.warning("⚠️ Clé ANTHROPIC_API_KEY manquante ou erreur API — configurer dans les secrets Streamlit.")

    if st.session_state.get("ai_summary"):
        st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
        st.markdown(
            "<div style='color:#8b5cf6;font-size:0.7rem;text-transform:uppercase;"
            "letter-spacing:.08em;font-weight:700;margin-bottom:8px'>"
            "🤖 Résumé de consultation — MedFlow AI</div>",
            unsafe_allow_html=True,
        )
        st.text_area(
            label="résumé",
            value=st.session_state["ai_summary"],
            height=185,
            label_visibility="collapsed",
            key="ai_summary_box",
        )
        if st.button("🗑 Effacer le résumé", key="clear_ai_summary"):
            del st.session_state["ai_summary"]
            st.rerun()

    # ── HISTORIQUE LONGITUDINAL ───────────────────────────────────────────────
    if patient_valid and history_rows:
        st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
        st.markdown(f"""<div style="color:#3b82f6;font-size:0.7rem;text-transform:uppercase;letter-spacing:.08em;font-weight:700;margin-bottom:10px">
          📈 Suivi longitudinal — {pat_prenom.capitalize()} {pat_nom.upper()} · {len(history_rows)} bilan(s)
        </div>""", unsafe_allow_html=True)

        if PLOTLY_OK and len(history_rows) >= 2:
            dates     = [r[0] for r in history_rows]
            dfg_vals  = [r[5]  for r in history_rows]
            c0_vals   = [r[10] for r in history_rows]
            dose_vals = [r[12] for r in history_rows]
            k_vals    = [r[8]  for r in history_rows]

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
                    marker=dict(size=7, color=color, line=dict(width=1.5, color='#09090b')),
                    hovertemplate='%{x}<br>' + name + ': <b>%{y}</b><extra></extra>'
                ))
                fig.update_layout(
                    template='plotly_dark', paper_bgcolor='#111113', plot_bgcolor='#18181b',
                    font=dict(color='#94a3b8', size=10),
                    margin=dict(l=45, r=15, t=30, b=45), height=220,
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

        with st.expander(f"🗂️  Tableau des {len(history_rows)} consultation(s)", expanded=False):
            hdr    = ["Date", "DFG", "Stade", "C0", "Statut C0", "Na⁺", "K⁺", "Phase", "Dose act.", "Dose rec.", "Plafond"]
            col_ws = [1.4, 0.7, 0.6, 0.6, 1.1, 0.6, 0.6, 1.2, 0.8, 0.8, 0.8]
            hcols  = st.columns(col_ws)
            for hc, ht in zip(hcols, hdr):
                hc.markdown(f"<div style='color:#475569;font-size:0.68rem;text-transform:uppercase;font-weight:700'>{ht}</div>", unsafe_allow_html=True)
            st.markdown("<hr style='border-color:#27272a;margin:4px 0 6px'>", unsafe_allow_html=True)
            alt_bg = ["#111113", "#0f0f11"]
            for i, row in enumerate(reversed(history_rows)):
                bg   = alt_bg[i % 2]
                rcols = st.columns(col_ws)
                vals  = [row[0][:16], f"{row[5]:.0f}", row[6], f"{row[10]:.1f}", row[16],
                         f"{row[7]:.0f}", f"{row[8]:.1f}", row[9].split('(')[0].strip(),
                         f"{row[11]:.1f}", f"{row[12]:.1f}", f"{row[14]:.1f}"]
                for rc, rv in zip(rcols, vals):
                    rc.markdown(f"<div style='background:{bg};padding:5px 4px;border-radius:4px;color:#e2e8f0;font-size:0.75rem'>{rv}</div>", unsafe_allow_html=True)

    # ── FORMULES ──────────────────────────────────────────────────────────────
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
            st.markdown("""<div style="background:#111113;border:1px solid #27272a;border-radius:10px;padding:16px;margin-bottom:8px">
              <div style="color:#f59e0b;font-size:0.75rem;font-weight:700;margin-bottom:8px">③ Plafond néphroprotecteur</div>
              <div style="font-family:monospace;color:#93c5fd;font-size:0.85rem;background:#0f0f11;padding:10px 12px;border-radius:6px;line-height:1.8">
                Plafond = poids × 0,1 mg/kg × facteur_DFG<br><br>
                G1–G2 (DFG ≥ 60)  → facteur 1,00<br>
                G3a   (45 – 59)   → facteur 0,90<br>
                G3b   (30 – 44)   → facteur 0,80<br>
                G4    (15 – 29)   → facteur 0,70<br>
                G5    (&lt; 15)   → facteur 0,50
              </div>
              <div style="color:#64748b;font-size:0.72rem;margin-top:6px">Source : Ojo NEJM 2003 · Naesens CJASN 2009 · Ekberg NEJM 2007</div>
            </div>""", unsafe_allow_html=True)
            st.markdown("""<div style="background:#111113;border:1px solid #27272a;border-radius:10px;padding:16px">
              <div style="color:#06b6d4;font-size:0.75rem;font-weight:700;margin-bottom:8px">⑤ Correction hématocrite</div>
              <div style="font-family:monospace;color:#93c5fd;font-size:0.85rem;background:#0f0f11;padding:10px 12px;border-radius:6px;line-height:1.8">
                C0_corr = C0_mesuré × (1 + 0,75 × (0,45/Ht − 1))<br>
                Ht en fraction décimale (ex : 0,40 pour 40 %)<br>
                75 % du tacrolimus lié aux érythrocytes
              </div>
              <div style="color:#64748b;font-size:0.72rem;margin-top:6px">Størset et al., Transpl Int 2014</div>
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
              <div style="color:#3b82f6;font-size:0.75rem;font-weight:700;margin-bottom:8px">④ Décision finale</div>
              <div style="font-family:monospace;color:#93c5fd;font-size:0.85rem;background:#0f0f11;padding:10px 12px;border-radius:6px;line-height:1.8">
                dose = min(dose_PK, plafond_rénal)<br><br>
                Si K⁺ &gt; 5,5 mmol/L :<br>
                dose = min(dose, dose_actuelle)<br><br>
                Arrondi capsule 0,5 mg — min 0,5 mg/j<br>
                Split q12h : dose / 2 matin + soir
              </div>
              <div style="color:#64748b;font-size:0.72rem;margin-top:6px">Priorité néphroprotection · ISHLT 2016 · Tumlin 1996</div>
            </div>""", unsafe_allow_html=True)

    # ── BASE DE DONNÉES PROBANTES ─────────────────────────────────────────────
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

    # ── MONITORING ────────────────────────────────────────────────────────────
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

    # ── INTERACTIONS (récapitulatif statique) ──────────────────────────────────
    st.markdown("""<div style="background:#1c1208;border:1px solid #92400e;border-radius:10px;padding:14px 18px;margin-top:8px">
      <div style="color:#fbbf24;font-size:0.78rem;font-weight:700;margin-bottom:6px">⚠️ Interactions majeures — vérifier à chaque modification (voir sélecteur interactif ci-dessus)</div>
      <div style="display:flex;gap:32px;flex-wrap:wrap">
        <div style="color:#d97706;font-size:0.76rem"><strong>↑ taux Tac (CYP3A4 inhibiteurs) :</strong> azoles, diltiazem, vérapamil, macrolides, amiodarone, ritonavir</div>
        <div style="color:#d97706;font-size:0.76rem"><strong>↓ taux Tac (CYP3A4 inducteurs) :</strong> rifampicine, phénytoïne, carbamazépine, millepertuis</div>
        <div style="color:#d97706;font-size:0.76rem"><strong>Hyperkaliémie aggravée :</strong> IEC, ARA2, AINS, diurétiques épargneurs K⁺</div>
      </div>
    </div>""", unsafe_allow_html=True)

    # ── RÉFÉRENCES ────────────────────────────────────────────────────────────
    with st.expander("📚  Références scientifiques"):
        for ref_nom, ref_texte in REFS:
            st.markdown(f"""<div style="background:#111113;border-left:3px solid #3b82f6;border-radius:0 8px 8px 0;padding:10px 14px;margin-bottom:8px">
              <div style="color:#93c5fd;font-weight:600;font-size:0.82rem;margin-bottom:4px">{ref_nom}</div>
              <div style="color:#94a3b8;font-size:0.78rem">{ref_texte}</div>
            </div>""", unsafe_allow_html=True)

    # ── DISCLAIMER ────────────────────────────────────────────────────────────
    st.markdown("""<div style="background:#0f0f11;border:1px solid #1e1e21;border-radius:10px;padding:12px 20px;color:#475569;font-size:0.75rem;text-align:center;margin-top:8px">
      ⚕️ <strong style="color:#64748b">Outil d'aide à la décision — ne remplace pas la concertation d'équipe de transplantation.</strong>
      Adapter systématiquement au protocole institutionnel. MedFlow AI — usage professionnel exclusif.
    </div>""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — MMF / CELLCEPT®
# ══════════════════════════════════════════════════════════════════════════════
with tab_mmf:

    st.markdown("""
    <div style="padding:0 0 6px">
      <div style="display:flex;align-items:center;gap:14px">
        <span style="font-size:2rem">💊</span>
        <div>
          <div style="font-size:1.55rem;font-weight:800;color:#f1f5f9">Mycophenolate Mofetil — Cellcept®</div>
          <div style="color:#64748b;font-size:0.82rem;margin-top:2px">Dosage adapté · Hématotoxicité · 1 comprimé = 500 mg · MedFlow AI</div>
        </div>
      </div>
    </div>
    """, unsafe_allow_html=True)
    st.markdown("---")

    # ── Rappel DFG depuis onglet Tacrolimus ───────────────────────────────────
    _dfg_stored    = st.session_state.get("_dfg", 0.0)
    _phase_stored  = st.session_state.get("_phase_label", list(PHASES.keys())[1])
    _stade_stored  = st.session_state.get("_stade", "")

    if _dfg_stored > 0:
        st.markdown(
            f"<div style='background:#0f1a2e;border:1px solid #3b82f6;border-radius:8px;"
            f"padding:8px 16px;margin-bottom:14px;font-size:0.8rem'>"
            f"<span style='color:#93c5fd;font-weight:700'>Données reprises depuis l'onglet Tacrolimus — </span>"
            f"<span style='color:#e2e8f0'>DFG = {_dfg_stored} mL/min (stade {_stade_stored}) · Phase : {_phase_stored.split('(')[0].strip()}</span>"
            f"</div>",
            unsafe_allow_html=True
        )
    else:
        st.info("Remplir l'onglet Tacrolimus en premier pour importer automatiquement le DFG et la phase.", icon="ℹ️")

    # ── FORMULAIRE MMF ────────────────────────────────────────────────────────
    mmf_c1, mmf_c2, mmf_c3 = st.columns([1, 1, 1], gap="large")

    with mmf_c1:
        st.markdown("<div style='color:#8b5cf6;font-size:0.7rem;text-transform:uppercase;letter-spacing:.08em;font-weight:700;margin-bottom:8px'>🧬 Contexte clinique</div>", unsafe_allow_html=True)
        mmf_phase = st.selectbox("Phase post-greffe", list(PHASES.keys()),
                                  index=list(PHASES.keys()).index(_phase_stored) if _phase_stored in PHASES else 1,
                                  key="mmf_phase")
        mmf_dfg = st.number_input("DFG (mL/min)", min_value=0.0, max_value=200.0,
                                   value=float(_dfg_stored) if _dfg_stored > 0 else 60.0,
                                   step=1.0, key="mmf_dfg",
                                   help="Pré-rempli depuis l'onglet Tacrolimus si calculé")

    with mmf_c2:
        st.markdown("<div style='color:#06b6d4;font-size:0.7rem;text-transform:uppercase;letter-spacing:.08em;font-weight:700;margin-bottom:8px'>🩸 NFS — Hématotoxicité</div>", unsafe_allow_html=True)
        mmf_gb  = st.number_input("Globules blancs — GB (G/L)", min_value=0.0, max_value=30.0,
                                   value=0.0, step=0.1, key="mmf_gb",
                                   help="0 = non saisi. Seuils : ⚠️ < 3,0 · 🔴 < 2,0 · ARRÊT < 1,5 G/L")
        mmf_pnn = st.number_input("Polynucléaires neutrophiles — PNN (G/L)", min_value=0.0, max_value=20.0,
                                   value=0.0, step=0.1, key="mmf_pnn",
                                   help="0 = non saisi. Seuils : ⚠️ < 1,5 · 🔴 < 1,0 · ARRÊT < 0,5 G/L")

    with mmf_c3:
        st.markdown("<div style='color:#10b981;font-size:0.7rem;text-transform:uppercase;letter-spacing:.08em;font-weight:700;margin-bottom:8px'>💊 Paramètres MMF</div>", unsafe_allow_html=True)
        mmf_dose_act = st.number_input("Dose actuelle MMF (mg/j)", min_value=0, max_value=4000,
                                        value=2000, step=500, key="mmf_dose_act",
                                        help="Dose totale journalière en mg. Multiples de 500 mg (1 cp).")
        mmf_gi = st.checkbox("Intolérance gastro-intestinale (nausées, diarrhée)", key="mmf_gi",
                              help="Diarrhée ≥ grade 2 ou symptômes GI limitants → réduction ou switch EC-MPA")

    # ── CALCUL MMF ────────────────────────────────────────────────────────────
    mmf_rec, mmf_dm, mmf_ds, mmf_cpm, mmf_cps, mmf_alertes = recommander_mmf(
        mmf_dose_act, mmf_phase, mmf_dfg, mmf_gb, mmf_pnn, mmf_gi
    )

    st.markdown("---")
    st.markdown("<div style='color:#10b981;font-size:0.72rem;text-transform:uppercase;letter-spacing:.08em;font-weight:700;margin-bottom:12px'>📋 Recommandation posologique MMF</div>", unsafe_allow_html=True)

    # Résultat principal
    if mmf_rec == 0:
        st.markdown("""
        <div style="background:#1f0808;border:2px solid #dc2626;border-radius:12px;padding:18px 24px;text-align:center">
          <div style="font-size:1.6rem;font-weight:800;color:#ef4444">ARRÊT MMF</div>
          <div style="color:#fca5a5;font-size:0.88rem;margin-top:4px">Reprendre uniquement après normalisation hématologique</div>
        </div>
        """, unsafe_allow_html=True)
    else:
        delta_mmf = mmf_rec - mmf_dose_act
        delta_sign = f"+{delta_mmf}" if delta_mmf > 0 else str(delta_mmf)
        delta_color = "#10b981" if delta_mmf > 0 else ("#ef4444" if delta_mmf < 0 else "#94a3b8")
        schema_bidi = (
            f"{mmf_dm} mg matin ({mmf_cpm} cp) + {mmf_ds} mg soir ({mmf_cps} cp)"
            if mmf_cpm != mmf_cps else
            f"{mmf_dm} mg × 2/j ({mmf_cpm} cp matin + {mmf_cps} cp soir)"
        )

        rc1, rc2, rc3 = st.columns(3)
        with rc1:
            st.markdown(f"""
            <div style="background:#111827;border:1px solid #27272a;border-radius:12px;padding:16px;text-align:center">
              <div style="color:#94a3b8;font-size:0.72rem;margin-bottom:6px">DOSE RECOMMANDÉE</div>
              <div style="font-size:2rem;font-weight:800;color:#f1f5f9">{mmf_rec} <span style="font-size:1rem">mg/j</span></div>
              <div style="color:{delta_color};font-size:0.8rem;margin-top:4px">{delta_sign} mg vs actuel</div>
            </div>""", unsafe_allow_html=True)
        with rc2:
            st.markdown(f"""
            <div style="background:#111827;border:1px solid #27272a;border-radius:12px;padding:16px;text-align:center">
              <div style="color:#94a3b8;font-size:0.72rem;margin-bottom:6px">SCHÉMA BID</div>
              <div style="font-size:1.1rem;font-weight:700;color:#a78bfa;line-height:1.5">{mmf_dm} mg<br><span style="color:#64748b;font-size:0.75rem">matin · {mmf_cpm} cp</span></div>
            </div>""", unsafe_allow_html=True)
        with rc3:
            st.markdown(f"""
            <div style="background:#111827;border:1px solid #27272a;border-radius:12px;padding:16px;text-align:center">
              <div style="color:#94a3b8;font-size:0.72rem;margin-bottom:6px">SCHÉMA BID</div>
              <div style="font-size:1.1rem;font-weight:700;color:#60a5fa;line-height:1.5">{mmf_ds} mg<br><span style="color:#64748b;font-size:0.75rem">soir · {mmf_cps} cp</span></div>
            </div>""", unsafe_allow_html=True)

        st.markdown(
            f"<div style='background:#0a1628;border:1px solid #1d4ed8;border-radius:8px;padding:10px 16px;margin-top:10px;"
            f"font-size:0.82rem;color:#93c5fd'>📌 Schéma complet : <strong>{schema_bidi}</strong> — 1 comprimé Cellcept® = 500 mg</div>",
            unsafe_allow_html=True
        )

    # ── Alertes MMF ───────────────────────────────────────────────────────────
    if mmf_alertes:
        st.markdown("<div style='margin-top:16px;margin-bottom:6px;color:#f59e0b;font-size:0.72rem;font-weight:700;text-transform:uppercase;letter-spacing:.06em'>⚠️ Alertes cliniques</div>", unsafe_allow_html=True)
        for icone, titre, action in mmf_alertes:
            bg = "#1f0808" if icone == "🔴" else ("#1a1208" if icone == "⚠️" else "#0a1628")
            bd = "#dc2626" if icone == "🔴" else ("#f59e0b" if icone == "⚠️" else "#3b82f6")
            tc = "#fca5a5" if icone == "🔴" else ("#fde68a" if icone == "⚠️" else "#93c5fd")
            st.markdown(
                f"<div style='background:{bg};border-left:3px solid {bd};border-radius:0 8px 8px 0;"
                f"padding:10px 14px;margin-bottom:8px'>"
                f"<span style='color:{tc};font-weight:700;font-size:0.8rem'>{icone} {titre}</span><br>"
                f"<span style='color:#d1d5db;font-size:0.76rem'>→ {action}</span>"
                f"</div>",
                unsafe_allow_html=True
            )
    else:
        st.markdown("<div style='color:#10b981;font-size:0.8rem;margin-top:10px'>✅ Aucune alerte hématologique — NFS normale</div>", unsafe_allow_html=True)

    # ── Cible de dose par phase ───────────────────────────────────────────────
    st.markdown("---")
    with st.expander("📚 Cibles posologiques MMF par phase & références"):
        tc1, tc2 = st.columns(2)
        with tc1:
            st.markdown("<div style='color:#8b5cf6;font-size:0.72rem;font-weight:700;margin-bottom:8px'>CIBLES PAR PHASE (ISHLT 2016)</div>", unsafe_allow_html=True)
            for ph, mg in MMF_PHASE_TARGETS.items():
                ph_short = ph.split('(')[0].strip()
                cp_dose = mg // 1000
                st.markdown(
                    f"<div style='background:#18181b;border-radius:6px;padding:6px 10px;margin-bottom:4px;font-size:0.78rem'>"
                    f"<span style='color:#a78bfa;font-weight:600'>{ph_short}</span>"
                    f"<span style='color:#e2e8f0'> → {mg} mg/j</span>"
                    f"<span style='color:#64748b'> ({cp_dose} cp × 2/j)</span>"
                    f"</div>",
                    unsafe_allow_html=True
                )
            st.markdown(
                "<div style='background:#0a1628;border-radius:6px;padding:8px 10px;margin-top:6px;font-size:0.75rem;color:#93c5fd'>"
                "💡 <strong>EC-MPA (Myfortic®)</strong> : 720 mg ≡ MMF 1000 mg — profil GI amélioré<br>"
                "Comprimés 250 mg (Cellcept® capsules) aussi disponibles pour titration fine"
                "</div>",
                unsafe_allow_html=True
            )
        with tc2:
            st.markdown("<div style='color:#06b6d4;font-size:0.72rem;font-weight:700;margin-bottom:8px'>RÉFÉRENCES CLINIQUES</div>", unsafe_allow_html=True)
            for ref_title, ref_body in MMF_REFS:
                st.markdown(
                    f"<div style='background:#0d1117;border-left:2px solid #3b82f6;padding:6px 10px;margin-bottom:6px;border-radius:0 6px 6px 0'>"
                    f"<div style='color:#60a5fa;font-size:0.72rem;font-weight:700'>{ref_title}</div>"
                    f"<div style='color:#64748b;font-size:0.68rem;margin-top:2px'>{ref_body}</div>"
                    f"</div>",
                    unsafe_allow_html=True
                )


# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 — PREDNISOLONE / PREDNISONE
# ══════════════════════════════════════════════════════════════════════════════
with tab_pred:

    st.markdown("""
    <div style="padding:0 0 6px">
      <div style="display:flex;align-items:center;gap:14px">
        <span style="font-size:2rem">🟠</span>
        <div>
          <div style="font-size:1.55rem;font-weight:800;color:#f1f5f9">Prednisolone / Prednisone</div>
          <div style="color:#64748b;font-size:0.82rem;margin-top:2px">Dégression corticoïdes post-greffe · Glycémie · HTA · Sevrage · MedFlow AI</div>
        </div>
      </div>
    </div>
    """, unsafe_allow_html=True)
    st.markdown("---")

    # ── Rappel depuis onglet Tacrolimus ───────────────────────────────────────
    _dfg_p   = st.session_state.get("_dfg",   0.0)
    _phase_p = st.session_state.get("_phase_label", list(PHASES.keys())[0])
    _poids_p = st.session_state.get("_poids", 70.0)

    if _dfg_p > 0:
        st.markdown(
            f"<div style='background:#0f1a2e;border:1px solid #3b82f6;border-radius:8px;"
            f"padding:8px 16px;margin-bottom:14px;font-size:0.8rem'>"
            f"<span style='color:#93c5fd;font-weight:700'>Données reprises depuis l'onglet Tacrolimus — </span>"
            f"<span style='color:#e2e8f0'>DFG = {_dfg_p} mL/min · Phase : {_phase_p.split('(')[0].strip()} · Poids : {_poids_p} kg</span>"
            f"</div>",
            unsafe_allow_html=True
        )
    else:
        st.info("Remplir l'onglet Tacrolimus en premier pour importer automatiquement la phase post-greffe et le poids.", icon="ℹ️")

    # ── FORMULAIRE PRED ───────────────────────────────────────────────────────
    pred_c1, pred_c2, pred_c3 = st.columns([1, 1, 1], gap="large")

    with pred_c1:
        st.markdown("<div style='color:#f97316;font-size:0.7rem;text-transform:uppercase;letter-spacing:.08em;font-weight:700;margin-bottom:8px'>🟠 Contexte post-greffe</div>", unsafe_allow_html=True)
        pred_phase = st.selectbox(
            "Phase post-greffe", list(PHASES.keys()),
            index=list(PHASES.keys()).index(_phase_p) if _phase_p in PHASES else 0,
            key="pred_phase"
        )
        pred_poids = st.number_input(
            "Poids (kg)", min_value=30.0, max_value=250.0,
            value=float(_poids_p) if _poids_p > 0 else 70.0,
            step=0.5, key="pred_poids"
        )
        pred_dose_act = st.number_input(
            "Dose actuelle prednisone (mg/j)", min_value=0.0, max_value=200.0,
            value=20.0, step=2.5, key="pred_dose_act",
            help="Dose totale quotidienne (prednisone ou prednisolone). Prednisolone 5 mg = Prednisone 5 mg = Méthylprednisolone 4 mg."
        )

    with pred_c2:
        st.markdown("<div style='color:#f59e0b;font-size:0.7rem;text-transform:uppercase;letter-spacing:.08em;font-weight:700;margin-bottom:8px'>🩸 Glycémie & PA</div>", unsafe_allow_html=True)
        pred_glycemie = st.number_input(
            "Glycémie à jeun (mmol/L)", min_value=0.0, max_value=50.0,
            value=0.0, step=0.1, key="pred_glycemie",
            help="0 = non saisi. Norme < 5,6 mmol/L à jeun. NODAT si ≥ 7,0 mmol/L à 2 reprises."
        )
        pred_pas = st.number_input(
            "PA systolique (mmHg)", min_value=0, max_value=300,
            value=0, step=1, key="pred_pas",
            help="0 = non saisi. Cible post-greffe < 130/80 mmHg (ISHLT 2016)."
        )

    with pred_c3:
        st.markdown("<div style='color:#ef4444;font-size:0.7rem;text-transform:uppercase;letter-spacing:.08em;font-weight:700;margin-bottom:8px'>⚠️ Facteurs de risque</div>", unsafe_allow_html=True)
        pred_rejet   = st.checkbox("Rejet aigu récent (< 3 mois)", key="pred_rejet",
                                    help="Rejet cellulaire ou humoral documenté — contre-indique toute réduction de corticoïdes")
        pred_infect  = st.checkbox("Infection active en cours",    key="pred_infection",
                                    help="Infection bactérienne, virale (CMV, EBV) ou fungique active")
        pred_diabete = st.checkbox("NODAT / Diabète cortico-induit connu", key="pred_diabete",
                                    help="New-Onset Diabetes After Transplantation déjà diagnostiqué")

    # ── CALCUL PRED ───────────────────────────────────────────────────────────
    pred_dose_rec, pred_alertes, pred_statut, pred_statut_color = recommander_prednisolone(
        pred_dose_act, pred_phase, pred_poids,
        pred_glycemie, pred_pas, pred_rejet, pred_infect
    )
    if pred_diabete and not any("iabète" in a[1] or "NODAT" in a[1] for a in pred_alertes):
        pred_alertes.append(("⚠️", "NODAT / Diabète cortico-induit connu",
                              "Contrôle glycémique strict · Antidiabétiques oraux ou insuline selon profil · Avis diabétologie"))

    _pred_cible = PRED_CIBLES.get(pred_phase, {"min": 5.0, "max": 10.0, "step": 2.5})

    st.markdown("---")
    st.markdown("<div style='color:#f97316;font-size:0.72rem;text-transform:uppercase;letter-spacing:.08em;font-weight:700;margin-bottom:12px'>📋 Recommandation posologique — Prednisolone</div>", unsafe_allow_html=True)

    # ── MÉTRIQUES ─────────────────────────────────────────────────────────────
    pm1, pm2, pm3, pm4 = st.columns(4)
    delta_pred     = round(pred_dose_rec - pred_dose_act, 1)
    delta_pred_str = f"{delta_pred:+.1f} mg/j" if delta_pred != 0 else "Stable"
    delta_pred_col = "#ef4444" if delta_pred < 0 else ("#f59e0b" if delta_pred > 0 else "#10b981")

    with pm1: st.markdown(metric_box("Dose actuelle",      pred_dose_act,  "mg/j prednisone",         "#94a3b8"),          unsafe_allow_html=True)
    with pm2: st.markdown(metric_box("Dose recommandée",   pred_dose_rec,  "mg/j → prochaine étape",  pred_statut_color),  unsafe_allow_html=True)
    with pm3: st.markdown(metric_box("Cible phase",        f"{_pred_cible['min']}–{_pred_cible['max']}", f"mg/j · {pred_phase.split('(')[0].strip()}", "#8b5cf6"), unsafe_allow_html=True)
    with pm4: st.markdown(metric_box("Variation",          delta_pred_str, "vs dose actuelle",         delta_pred_col),    unsafe_allow_html=True)

    st.markdown(
        f"<div style='background:#111113;border:1.5px solid {pred_statut_color};border-radius:10px;"
        f"padding:14px 18px;margin-top:10px;text-align:center'>"
        f"<div style='color:{pred_statut_color};font-size:1rem;font-weight:700'>{pred_statut}</div>"
        f"<div style='color:#94a3b8;font-size:0.78rem;margin-top:4px'>"
        f"Dose actuelle : {pred_dose_act} mg/j · Cible : {_pred_cible['min']}–{_pred_cible['max']} mg/j · "
        f"Prochaine dose recommandée : {pred_dose_rec} mg/j</div></div>",
        unsafe_allow_html=True
    )

    # ── ALERTES ───────────────────────────────────────────────────────────────
    if pred_alertes:
        st.markdown("<div style='margin-top:16px;margin-bottom:6px;color:#f59e0b;font-size:0.72rem;font-weight:700;text-transform:uppercase;letter-spacing:.06em'>⚠️ Alertes cliniques</div>", unsafe_allow_html=True)
        for icone, titre, action in pred_alertes:
            bg = "#1f0808" if icone == "🔴" else ("#1a1208" if icone == "⚠️" else "#0a1628")
            bd = "#dc2626" if icone == "🔴" else ("#f59e0b" if icone == "⚠️" else "#3b82f6")
            tc = "#fca5a5" if icone == "🔴" else ("#fde68a" if icone == "⚠️" else "#93c5fd")
            st.markdown(
                f"<div style='background:{bg};border-left:3px solid {bd};border-radius:0 8px 8px 0;"
                f"padding:10px 14px;margin-bottom:8px'>"
                f"<span style='color:{tc};font-weight:700;font-size:0.8rem'>{icone} {titre}</span><br>"
                f"<span style='color:#d1d5db;font-size:0.76rem'>→ {action}</span>"
                f"</div>",
                unsafe_allow_html=True
            )
    else:
        st.markdown("<div style='color:#10b981;font-size:0.8rem;margin-top:10px'>✅ Aucune alerte — paramètres dans les normes</div>", unsafe_allow_html=True)

    # ── CALENDRIER DE DÉCROISSANCE ────────────────────────────────────────────
    st.markdown("---")
    st.markdown("<div style='color:#f97316;font-size:0.72rem;text-transform:uppercase;letter-spacing:.08em;font-weight:700;margin-bottom:12px'>📅 Calendrier de décroissance suggéré</div>", unsafe_allow_html=True)

    if pred_rejet:
        st.markdown("<div style='color:#ef4444;font-size:0.82rem'>🔴 Rejet récent — décroissance suspendue. Réévaluation par l'équipe de transplantation avant toute réduction.</div>", unsafe_allow_html=True)
    elif pred_dose_act <= _pred_cible["min"]:
        st.markdown(
            f"<div style='color:#10b981;font-size:0.82rem'>✅ Dose déjà à la cible minimale ({_pred_cible['min']} mg/j). "
            f"Maintenir ou discuter sevrage progressif si patient stable > 1 an.</div>",
            unsafe_allow_html=True
        )
    else:
        # Générer les paliers de décroissance
        tap_steps = []
        d = pred_dose_act
        c_step = _pred_cible["step"]
        c_min  = _pred_cible["min"]
        while d > c_min and len(tap_steps) < 8:
            d_next = round(round(max(d - c_step, c_min) / 0.5) * 0.5, 1)
            tap_steps.append((d, d_next))
            d = d_next

        th1, th2, th3, th4 = st.columns([0.6, 1, 1, 1.8])
        for col, hdr in zip([th1, th2, th3, th4], ["Palier", "Dose actuelle", "→ Suivante", "Intervalle suggéré"]):
            col.markdown(f"<div style='color:#475569;font-size:0.68rem;font-weight:700;text-transform:uppercase'>{hdr}</div>", unsafe_allow_html=True)
        st.markdown("<hr style='border-color:#27272a;margin:4px 0 6px'>", unsafe_allow_html=True)
        for i, (d_from, d_to) in enumerate(tap_steps):
            bg = "#111113" if i % 2 == 0 else "#0f0f11"
            r1, r2, r3, r4 = st.columns([0.6, 1, 1, 1.8])
            r1.markdown(f"<div style='background:{bg};padding:6px 8px;border-radius:4px;color:#8b5cf6;font-size:0.76rem;font-weight:700'>P{i+1}</div>", unsafe_allow_html=True)
            r2.markdown(f"<div style='background:{bg};padding:6px 8px;border-radius:4px;color:#f59e0b;font-size:0.76rem'>{d_from} mg/j</div>", unsafe_allow_html=True)
            r3.markdown(f"<div style='background:{bg};padding:6px 8px;border-radius:4px;color:#10b981;font-size:0.76rem'>{d_to} mg/j</div>", unsafe_allow_html=True)
            r4.markdown(f"<div style='background:{bg};padding:6px 8px;border-radius:4px;color:#64748b;font-size:0.74rem'>2–4 semaines selon tolérance clinique</div>", unsafe_allow_html=True)

    # ── ÉQUIVALENCES CORTICOÏDES ──────────────────────────────────────────────
    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
    st.markdown("""<div style="background:#111113;border:1px solid #27272a;border-radius:10px;padding:14px 18px">
      <div style="color:#f97316;font-size:0.72rem;font-weight:700;text-transform:uppercase;letter-spacing:.06em;margin-bottom:10px">💊 Équivalences corticoïdes</div>
      <div style="display:flex;gap:24px;flex-wrap:wrap">
        <div style="color:#e2e8f0;font-size:0.78rem"><strong style="color:#fb923c">Prednisone 5 mg</strong> = Prednisolone 5 mg = Méthylprednisolone 4 mg = Hydrocortisone 20 mg</div>
        <div style="color:#94a3b8;font-size:0.76rem">Comprimés disponibles : 1 mg · 5 mg · 20 mg (prednisone) — permet titration fine par paliers de 2,5 mg</div>
      </div>
    </div>""", unsafe_allow_html=True)

    # ── MONITORING ────────────────────────────────────────────────────────────
    st.markdown("---")
    mp1, mp2, mp3, mp4 = st.columns(4)
    def mon_box_pred(label, val, col):
        return f"""<div style="background:#111113;border:1px solid #27272a;border-radius:10px;padding:12px">
          <div style="color:#64748b;font-size:0.68rem;text-transform:uppercase;margin-bottom:6px">{label}</div>
          <div style="color:{col};font-size:0.82rem;font-weight:600">{val}</div>
        </div>"""
    with mp1: st.markdown(mon_box_pred("Glycémie à jeun", "Hebdomadaire × 4, puis mensuelle", "#f59e0b"), unsafe_allow_html=True)
    with mp2: st.markdown(mon_box_pred("PA & poids", "À chaque consultation", "#3b82f6"), unsafe_allow_html=True)
    with mp3: st.markdown(mon_box_pred("Densitométrie (DXA)", "M3, puis annuelle si corticoïdes > 3 mois", "#8b5cf6"), unsafe_allow_html=True)
    with mp4: st.markdown(mon_box_pred("Cortisol 8h", "Avant arrêt définitif des corticoïdes", "#94a3b8"), unsafe_allow_html=True)

    # ── RÉFÉRENCES ────────────────────────────────────────────────────────────
    with st.expander("📚 Références scientifiques — Corticoïdes post-greffe cardiaque"):
        for ref_nom, ref_texte in PRED_REFS:
            st.markdown(f"""<div style="background:#111113;border-left:3px solid #f97316;border-radius:0 8px 8px 0;padding:10px 14px;margin-bottom:8px">
              <div style="color:#fb923c;font-weight:600;font-size:0.82rem;margin-bottom:4px">{ref_nom}</div>
              <div style="color:#94a3b8;font-size:0.78rem">{ref_texte}</div>
            </div>""", unsafe_allow_html=True)

    st.markdown("""<div style="background:#0f0f11;border:1px solid #1e1e21;border-radius:10px;padding:12px 20px;color:#475569;font-size:0.75rem;text-align:center;margin-top:8px">
      ⚕️ <strong style="color:#64748b">Outil d'aide à la décision — ne remplace pas la concertation d'équipe de transplantation.</strong>
      Adapter systématiquement au protocole institutionnel. MedFlow AI — usage professionnel exclusif.
    </div>""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# TAB 4 — MENTIONS LÉGALES & CGU
# ══════════════════════════════════════════════════════════════════════════════
with tab_mentions:
    st.markdown("""
    <div style="max-width:860px;margin:0 auto">

    <div style="color:#8b5cf6;font-size:0.7rem;text-transform:uppercase;letter-spacing:.1em;font-weight:700;margin-bottom:16px">
    ⚖️ Mentions légales, CGU & Politique de confidentialité
    </div>

    """, unsafe_allow_html=True)

    def ml_section(titre, contenu):
        st.markdown(f"""
        <div style="background:#111113;border:1px solid #27272a;border-radius:12px;padding:20px 24px;margin-bottom:14px">
          <div style="color:#93c5fd;font-size:0.88rem;font-weight:700;margin-bottom:10px">{titre}</div>
          <div style="color:#94a3b8;font-size:0.82rem;line-height:1.7">{contenu}</div>
        </div>""", unsafe_allow_html=True)

    ml_section("Éditeur", """
        <strong style="color:#e2e8f0">MedFlow AI</strong> — outil développé par <strong style="color:#e2e8f0">Dr. Mamadou Lamine TALL, PhD</strong><br>
        Bioinformatique &amp; Intelligence Artificielle Médicale<br>
        Contact : <a href="mailto:mamadoulaminetallgithub@gmail.com" style="color:#93c5fd">mamadoulaminetallgithub@gmail.com</a><br>
        Plateforme : <a href="https://medflowailanding.streamlit.app" style="color:#93c5fd">medflowailanding.streamlit.app</a>
    """)

    ml_section("Hébergement", """
        L'application est hébergée sur <strong style="color:#e2e8f0">Streamlit Community Cloud</strong> (Streamlit Inc., USA).<br>
        <span style="color:#fbbf24">⚠️ Avertissement HDS :</span> Streamlit Community Cloud n'est <strong>pas certifié Hébergeur de Données de Santé (HDS)</strong>
        au sens de l'article L.1111-8 du Code de la santé publique français. En conséquence, <strong>aucune donnée patient
        identifiante ne doit être saisie</strong> sur la version publique de cet outil. L'utilisation en production nécessite
        un déploiement sur infrastructure HDS-certifiée (ex : OVHcloud Health, Outscale HDS, Microsoft Azure France).
    """)

    ml_section("Nature de l'outil — Dispositif Médical Logiciel", """
        Cet outil est un <strong style="color:#e2e8f0">outil d'aide à la décision clinique (CDSS)</strong>. Il est susceptible
        d'être qualifié de <strong>Dispositif Médical Logiciel (DMSW)</strong> au sens du Règlement (UE) 2017/745 (MDR) et
        de la position MDCG 2019-11.<br><br>
        À ce titre, une évaluation de conformité et un marquage CE pourraient être requis avant commercialisation en Europe.
        L'outil est actuellement distribué à titre de <strong>démonstration et d'évaluation clinique</strong>.
        Tout usage clinique en production engage la responsabilité de l'établissement utilisateur.
    """)

    ml_section("Responsabilité et avertissement clinique", """
        <strong style="color:#ef4444">Cet outil ne remplace pas le jugement clinique du médecin.</strong><br><br>
        Les recommandations posologiques générées sont des <em>propositions algorithmiques</em> fondées sur des modèles
        pharmacocinétiques publiés. Elles doivent systématiquement être :<br>
        &bull; Confrontées aux recommandations institutionnelles et aux RCP officiels du tacrolimus (Prograf®)<br>
        &bull; Validées par le médecin prescripteur et l'équipe de transplantation<br>
        &bull; Adaptées aux particularités individuelles du patient non modélisables (comorbidités, officine, observance…)<br><br>
        L'éditeur décline toute responsabilité en cas d'usage non conforme aux présentes mentions.
    """)

    ml_section("Données personnelles — RGPD", """
        En version locale (<code style="color:#93c5fd">patients.db</code> SQLite), les données sont stockées
        <strong>exclusivement sur l'appareil de l'utilisateur</strong> et ne sont pas transmises à des tiers.<br><br>
        En version déployée sur Streamlit Cloud, <strong>aucune donnée patient identifiante ne doit être saisie</strong>
        (voir avertissement HDS ci-dessus).<br><br>
        Base légale du traitement : intérêt légitime professionnel médical. Durée de conservation : définie par l'utilisateur.
        Droits d'accès, rectification, suppression : contacter l'éditeur par email.
    """)

    ml_section("Propriété intellectuelle", """
        L'ensemble du code source, des algorithmes, de l'interface et de la documentation de MedFlow AI est protégé
        par le droit d'auteur.<br><br>
        Licence : <strong style="color:#e2e8f0">MIT</strong> pour le code open-source publié sur GitHub
        (<a href="https://github.com/mamadoulaminetall/medflow-posologie" style="color:#93c5fd">mamadoulaminetall/medflow-posologie</a>).<br>
        Les algorithmes cliniques sont issus de publications scientifiques référencées dans l'outil.
    """)

    ml_section("Conditions générales d'utilisation (CGU)", """
        &bull; <strong>Utilisateurs autorisés :</strong> professionnels de santé (médecins, pharmaciens, infirmiers spécialisés)<br>
        &bull; <strong>Usage interdit :</strong> automédication, usage par des non-professionnels, usage sans supervision médicale<br>
        &bull; <strong>Modification des données :</strong> l'utilisateur est seul responsable de la qualité des données saisies<br>
        &bull; <strong>Mise à jour :</strong> l'éditeur s'engage à maintenir l'outil conforme aux recommandations scientifiques en vigueur
        mais ne garantit pas l'exhaustivité ni l'absence d'erreur<br>
        &bull; <strong>Accès :</strong> l'éditeur se réserve le droit de restreindre l'accès à tout moment
    """)

    st.markdown("""
    <div style="text-align:center;color:#475569;font-size:0.72rem;margin-top:24px;padding-bottom:12px">
      MedFlow AI · Dr. Mamadou Lamine TALL, PhD · Dernière mise à jour : avril 2026<br>
      <a href="mailto:mamadoulaminetallgithub@gmail.com" style="color:#64748b">mamadoulaminetallgithub@gmail.com</a>
    </div>
    </div>
    """, unsafe_allow_html=True)
