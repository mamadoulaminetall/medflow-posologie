import streamlit as st
import math

st.set_page_config(
    page_title="Ajustement Posologique — MedFlow AI",
    page_icon="💊",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
[data-testid="stAppViewContainer"] { background: #09090b; color: #f1f5f9; }
[data-testid="stSidebar"] { background: #0f0f11; border-right: 1px solid #27272a; }
[data-testid="stHeader"] { background: transparent; }
[data-testid="stMetricValue"] { color: #f1f5f9 !important; font-size: 1.6rem !important; }
[data-testid="stMetricLabel"] { color: #94a3b8 !important; }
.stSelectbox label, .stNumberInput label, .stRadio label { color: #94a3b8 !important; }
.stSelectbox > div > div { background: #18181b !important; border: 1px solid #27272a !important; color: #f1f5f9 !important; }
.stNumberInput input { background: #18181b !important; border: 1px solid #27272a !important; color: #f1f5f9 !important; }
.stRadio [data-testid="stMarkdownContainer"] p { color: #d1d5db; }
div[data-baseweb="radio"] > label > div:first-child { background: #27272a !important; border-color: #3f3f46 !important; }
h1, h2, h3 { color: #f1f5f9 !important; }
hr { border-color: #27272a; }
.stAlert { background: #18181b !important; border: 1px solid #27272a !important; }
footer { visibility: hidden; }
</style>
""", unsafe_allow_html=True)

# ─── Base de données médicaments ───────────────────────────────────────────────
DRUGS = {
    "Tacrolimus (Prograf) — Greffe cardiaque": {
        "classe": "Immunosuppresseur / Inhibiteur calcineurine",
        "indication": "Prévention rejet greffe cardiaque",
        "dose_normale": "0.075–0.1 mg/kg/j en 2 prises (taux résiduel cible)",
        "type": "trough",
        "paliers": [
            {"dfg_min": 30, "dfg_max": 999, "dose": "Dose inchangée — monitoring taux résiduel",
             "niveau": "normal",
             "commentaire": "Tacrolimus métabolisé par le foie (CYP3A4) — insuffisance rénale n'affecte pas directement la PK. Cependant : tacrolimus est NÉPHROTOXIQUE — surveiller créatinine/DFG hebdomadaire les 3 premiers mois."},
            {"dfg_min": 15, "dfg_max": 29, "dose": "Réduire 20–30 % — taux résiduel strict",
             "niveau": "warning",
             "commentaire": "IRC sévère : risque de néphrotoxicité accrue. Viser taux résiduel bas de la fourchette. Dosage 2×/sem minimum. Envisager biopsie si dégradation rapide."},
            {"dfg_min": 0, "dfg_max": 14, "dose": "Dose minimale efficace — avis expert impératif",
             "niveau": "danger",
             "commentaire": "IRC terminale : risque néphrotoxicité majeur. Discuter switch vers MMF/azathioprine pour limiter tacrolimus. Hémodialyse ne retire pas le tacrolimus (liaison protéique > 99%)."},
        ],
        "trough_cibles": [
            {"phase": "M0–M3 (précoce)", "cible": "10–15 ng/mL", "couleur": "#f59e0b"},
            {"phase": "M3–M12 (maintenance)", "cible": "8–12 ng/mL", "couleur": "#10b981"},
            {"phase": "> 1 an (stable)", "cible": "5–10 ng/mL", "couleur": "#3b82f6"},
        ],
        "interactions": "⚠️ Interactions majeures : azithromycine, fluconazole, diltiazem (+taux) / rifampicine, phénytoïne (-taux). Pamplemousse CI.",
        "reference": "ISHLT Guidelines 2023, SPC Astellas"
    },
    "Tacrolimus (Prograf) — Greffe rénale": {
        "classe": "Immunosuppresseur / Inhibiteur calcineurine",
        "indication": "Prévention rejet greffe rénale",
        "dose_normale": "0.1–0.2 mg/kg/j en 2 prises",
        "type": "trough",
        "paliers": [
            {"dfg_min": 30, "dfg_max": 999, "dose": "Dose inchangée — monitoring trough",
             "niveau": "normal",
             "commentaire": "Métabolisme hépatique prédominant. Ajuster selon taux résiduel uniquement. Surveiller fonction rénale du greffon."},
            {"dfg_min": 15, "dfg_max": 29, "dose": "Viser bas de la fourchette thérapeutique",
             "niveau": "warning",
             "commentaire": "Dysfonction chronique du greffon possible. Réduire si créatinine monte sans rejet histologique prouvé."},
            {"dfg_min": 0, "dfg_max": 14, "dose": "Dose minimale — concertation multidisciplinaire",
             "niveau": "danger",
             "commentaire": "Retour en dialyse possible. Maintenir immunosuppression si greffon encore fonctionnel (diurèse résiduelle)."},
        ],
        "trough_cibles": [
            {"phase": "M0–M3", "cible": "10–15 ng/mL", "couleur": "#f59e0b"},
            {"phase": "M3–M12", "cible": "5–10 ng/mL", "couleur": "#10b981"},
            {"phase": "> 1 an", "cible": "3–8 ng/mL", "couleur": "#3b82f6"},
        ],
        "interactions": "⚠️ Mêmes interactions CYP3A4. Éviter AINS (néphrotoxicité additionnelle).",
        "reference": "KDIGO Transplant 2022, HAS"
    },
    "Metformine": {
        "classe": "Antidiabétique oral (biguanide)",
        "indication": "Diabète type 2",
        "dose_normale": "500–2000 mg/j en 2–3 prises",
        "paliers": [
            {"dfg_min": 60, "dfg_max": 999, "dose": "500–2000 mg/j", "niveau": "normal",
             "commentaire": "Aucun ajustement nécessaire."},
            {"dfg_min": 45, "dfg_max": 59, "dose": "500–1500 mg/j", "niveau": "warning",
             "commentaire": "Réduire la dose. Contrôle créatinine tous les 3–6 mois."},
            {"dfg_min": 30, "dfg_max": 44, "dose": "500–1000 mg/j max", "niveau": "danger",
             "commentaire": "Utilisation possible avec précaution extrême. Risque d'acidose lactique. Contrôle créatinine mensuel. Arrêter si chirurgie, iode, déshydratation."},
            {"dfg_min": 0, "dfg_max": 29, "dose": "CONTRE-INDIQUÉ", "niveau": "contraindicated",
             "commentaire": "Risque majeur d'acidose lactique potentiellement fatale. Arrêter immédiatement."},
        ],
        "reference": "HAS 2023, KDIGO CKD Diabetes 2022"
    },
    "Amoxicilline": {
        "classe": "Antibiotique — Pénicilline",
        "indication": "Infections bactériennes (ORL, pulmonaires, urinaires)",
        "dose_normale": "500 mg – 1 g toutes les 8h",
        "paliers": [
            {"dfg_min": 30, "dfg_max": 999, "dose": "500 mg – 1 g q8h", "niveau": "normal",
             "commentaire": "Dose standard, aucun ajustement."},
            {"dfg_min": 10, "dfg_max": 29, "dose": "500 mg q12h", "niveau": "warning",
             "commentaire": "Espacer les prises. Surveiller signes de neurotoxicité (convulsions) à fortes doses."},
            {"dfg_min": 0, "dfg_max": 9, "dose": "500 mg q24h", "niveau": "danger",
             "commentaire": "Une prise quotidienne. Dose supplémentaire après hémodialyse."},
        ],
        "reference": "Vidal/SPC, BNF"
    },
    "Amoxicilline-Clavulanate (Augmentin)": {
        "classe": "Antibiotique — Pénicilline + inhibiteur β-lactamase",
        "indication": "Infections ORL, pulmonaires, urinaires, cutanées",
        "dose_normale": "1 g q8h (875/125 mg)",
        "paliers": [
            {"dfg_min": 30, "dfg_max": 999, "dose": "1 g q8h", "niveau": "normal",
             "commentaire": "Dose standard."},
            {"dfg_min": 10, "dfg_max": 29, "dose": "1 g q12h", "niveau": "warning",
             "commentaire": "Espacer les prises à 12h."},
            {"dfg_min": 0, "dfg_max": 9, "dose": "1 g q24h", "niveau": "danger",
             "commentaire": "Une seule prise quotidienne. Supplément post-dialyse."},
        ],
        "reference": "Vidal/SPC"
    },
    "Ciprofloxacine": {
        "classe": "Antibiotique — Fluoroquinolone",
        "indication": "Infections urinaires, digestives, pulmonaires",
        "dose_normale": "500 mg q12h PO",
        "paliers": [
            {"dfg_min": 50, "dfg_max": 999, "dose": "500 mg q12h", "niveau": "normal",
             "commentaire": "Dose standard."},
            {"dfg_min": 25, "dfg_max": 49, "dose": "250–500 mg q12h", "niveau": "warning",
             "commentaire": "Dose réduite ou intervalle allongé selon sévérité de l'infection."},
            {"dfg_min": 0, "dfg_max": 24, "dose": "250–500 mg q24h", "niveau": "danger",
             "commentaire": "Une prise quotidienne. Risque d'accumulation et de tendinopathie accru."},
        ],
        "reference": "Vidal/SPC, HAS antibiothérapie"
    },
    "Cotrimoxazole (TMP-SMX)": {
        "classe": "Antibiotique — Sulfonamide",
        "indication": "Infections urinaires, pneumocystose (prophylaxie/traitement)",
        "dose_normale": "Curatif : 960 mg q12h | Prophylaxie PCP : 480 mg/j",
        "paliers": [
            {"dfg_min": 30, "dfg_max": 999, "dose": "Dose normale", "niveau": "normal",
             "commentaire": "Standard. Surveiller kaliémie (risque hyperkaliémie)."},
            {"dfg_min": 15, "dfg_max": 29, "dose": "50 % de la dose curative", "niveau": "warning",
             "commentaire": "Réduire de moitié. Prophylaxie PCP : 480 mg 3×/sem acceptable."},
            {"dfg_min": 0, "dfg_max": 14, "dose": "CONTRE-INDIQUÉ (curatif)", "niveau": "contraindicated",
             "commentaire": "CI en curatif. Prophylaxie PCP en dialyse possible après avis infectiologue."},
        ],
        "reference": "Vidal, HAS"
    },
    "Gabapentine": {
        "classe": "Antiépileptique / Antalgique neuropathique",
        "indication": "Douleurs neuropathiques, épilepsie",
        "dose_normale": "300–1200 mg q8h",
        "paliers": [
            {"dfg_min": 60, "dfg_max": 999, "dose": "300–1200 mg q8h", "niveau": "normal",
             "commentaire": "Dose standard."},
            {"dfg_min": 30, "dfg_max": 59, "dose": "300–600 mg q12h", "niveau": "warning",
             "commentaire": "Réduire la dose totale journalière de 50 %."},
            {"dfg_min": 15, "dfg_max": 29, "dose": "150–300 mg q24h", "niveau": "danger",
             "commentaire": "Réduire à 25 % de la dose normale."},
            {"dfg_min": 0, "dfg_max": 14, "dose": "150 mg q24h — supplément dialyse", "niveau": "danger",
             "commentaire": "Dose minimale. Ajouter 125–350 mg après chaque séance d'hémodialyse."},
        ],
        "reference": "Vidal/SPC, Lexicomp"
    },
    "Prégabaline": {
        "classe": "Antiépileptique / Antalgique neuropathique",
        "indication": "Douleurs neuropathiques, épilepsie, anxiété",
        "dose_normale": "150–600 mg/j en 2–3 prises",
        "paliers": [
            {"dfg_min": 60, "dfg_max": 999, "dose": "150–600 mg/j", "niveau": "normal",
             "commentaire": "Dose standard."},
            {"dfg_min": 30, "dfg_max": 59, "dose": "75–300 mg/j", "niveau": "warning",
             "commentaire": "Réduire de 50 %. Passer à 2 prises/j."},
            {"dfg_min": 15, "dfg_max": 29, "dose": "25–150 mg/j", "niveau": "danger",
             "commentaire": "Réduire à 25 % de la dose. 1–2 prises/j."},
            {"dfg_min": 0, "dfg_max": 14, "dose": "25–75 mg/j — supplément dialyse", "niveau": "danger",
             "commentaire": "Dose minimale. 75–150 mg supplémentaires après dialyse."},
        ],
        "reference": "Vidal/SPC, BNF"
    },
    "Ramipril": {
        "classe": "IEC — Inhibiteur de l'enzyme de conversion",
        "indication": "HTA, insuffisance cardiaque, néphroprotection",
        "dose_normale": "2.5–10 mg/j",
        "paliers": [
            {"dfg_min": 60, "dfg_max": 999, "dose": "2.5–10 mg/j", "niveau": "normal",
             "commentaire": "Dose standard. Contrôler kaliémie et créatinine à J7 d'initiation."},
            {"dfg_min": 30, "dfg_max": 59, "dose": "1.25–5 mg/j", "niveau": "warning",
             "commentaire": "Débuter à 1.25 mg/j. Augmenter prudemment. Surveiller kaliémie. Hausse créatinine ≤30 % acceptable."},
            {"dfg_min": 0, "dfg_max": 29, "dose": "1.25–2.5 mg/j max", "niveau": "danger",
             "commentaire": "Dose maximale réduite. Risque hyperkaliémie et hypotension. Arrêter si créatinine +50 % ou kaliémie >6 mmol/L."},
        ],
        "reference": "ESC HF Guidelines 2021, HAS"
    },
    "Atenolol": {
        "classe": "Bêtabloquant cardiosélectif",
        "indication": "HTA, angine de poitrine, post-IDM",
        "dose_normale": "50–100 mg/j",
        "paliers": [
            {"dfg_min": 35, "dfg_max": 999, "dose": "50–100 mg/j", "niveau": "normal",
             "commentaire": "Dose standard."},
            {"dfg_min": 15, "dfg_max": 34, "dose": "50 mg/j max", "niveau": "warning",
             "commentaire": "Réduire à 50 mg/j. Surveiller bradycardie et hypotension."},
            {"dfg_min": 0, "dfg_max": 14, "dose": "25–50 mg tous les 48h", "niveau": "danger",
             "commentaire": "Espacer à 48h. Dose supplémentaire après hémodialyse (atenolol dialysable)."},
        ],
        "reference": "Vidal/SPC"
    },
    "Enoxaparine (Lovenox) — Curatif": {
        "classe": "HBPM — Héparine de bas poids moléculaire",
        "indication": "TVP, EP, SCA — traitement curatif",
        "dose_normale": "1 mg/kg q12h SC (ou 1.5 mg/kg q24h si non-chirurgical)",
        "paliers": [
            {"dfg_min": 30, "dfg_max": 999, "dose": "1 mg/kg q12h SC", "niveau": "normal",
             "commentaire": "Dose standard. Monitoring anti-Xa non systématique sauf cas particuliers."},
            {"dfg_min": 15, "dfg_max": 29, "dose": "1 mg/kg q24h SC", "niveau": "warning",
             "commentaire": "Passer à une injection quotidienne. Contrôle anti-Xa pic systématique (cible 0.5–1 UI/mL à H4)."},
            {"dfg_min": 0, "dfg_max": 14, "dose": "HNF IV préférée", "niveau": "contraindicated",
             "commentaire": "Enoxaparine non recommandée < 15 mL/min. Utiliser héparine non fractionnée IV avec contrôle TCA."},
        ],
        "reference": "ANSM, HAS, RCP Sanofi"
    },
    "Dabigatran (Pradaxa) — FA": {
        "classe": "Anticoagulant oral — Anti-IIa direct",
        "indication": "Prévention AVC — Fibrillation auriculaire non valvulaire",
        "dose_normale": "150 mg q12h (ou 110 mg selon profil)",
        "paliers": [
            {"dfg_min": 50, "dfg_max": 999, "dose": "150 mg q12h (ou 110 mg si ≥80 ans / risque hémorragique)", "niveau": "normal",
             "commentaire": "Dose standard. Évaluer score HAS-BLED."},
            {"dfg_min": 30, "dfg_max": 49, "dose": "110 mg q12h", "niveau": "warning",
             "commentaire": "Réduire à 110 mg. Surveiller fonction rénale tous les 3–6 mois."},
            {"dfg_min": 15, "dfg_max": 29, "dose": "CONTRE-INDIQUÉ (Europe)", "niveau": "contraindicated",
             "commentaire": "Non autorisé en Europe < 30 mL/min. Envisager rivaroxaban 15 mg/j (autorisé jusqu'à 15 mL/min) ou AVK."},
            {"dfg_min": 0, "dfg_max": 14, "dose": "CONTRE-INDIQUÉ", "niveau": "contraindicated",
             "commentaire": "CI absolue. Utiliser AVK avec INR cible 2–3."},
        ],
        "reference": "EMA, ESC AF Guidelines 2020"
    },
    "Rivaroxaban (Xarelto) — FA": {
        "classe": "Anticoagulant oral — Anti-Xa direct",
        "indication": "Prévention AVC — Fibrillation auriculaire non valvulaire",
        "dose_normale": "20 mg/j au dîner",
        "paliers": [
            {"dfg_min": 50, "dfg_max": 999, "dose": "20 mg/j au dîner", "niveau": "normal",
             "commentaire": "Dose standard. Prendre avec de la nourriture (absorption optimale)."},
            {"dfg_min": 15, "dfg_max": 49, "dose": "15 mg/j au dîner", "niveau": "warning",
             "commentaire": "Réduire à 15 mg/j. Surveiller fonction rénale tous les 3 mois."},
            {"dfg_min": 0, "dfg_max": 14, "dose": "CONTRE-INDIQUÉ", "niveau": "contraindicated",
             "commentaire": "CI. Utiliser AVK avec INR cible 2–3 sous surveillance renforcée."},
        ],
        "reference": "EMA, ESC AF Guidelines 2020"
    },
    "Digoxine": {
        "classe": "Digitalique — Inotrope positif",
        "indication": "Insuffisance cardiaque, FA avec réponse ventriculaire rapide",
        "dose_normale": "62.5–250 µg/j",
        "paliers": [
            {"dfg_min": 50, "dfg_max": 999, "dose": "62.5–250 µg/j", "niveau": "normal",
             "commentaire": "Dose standard. Dosage résiduel cible : 0.5–0.9 ng/mL (IC) ou 0.8–2 ng/mL (FA)."},
            {"dfg_min": 10, "dfg_max": 49, "dose": "Réduire de 25–50 %", "niveau": "warning",
             "commentaire": "Risque d'accumulation. Doser la digoxinémie. Surveiller ECG. Préférer 62.5–125 µg/j."},
            {"dfg_min": 0, "dfg_max": 9, "dose": "Réduire de 50–75 % — dosage indispensable", "niveau": "danger",
             "commentaire": "Risque élevé de surdosage. 62.5 µg/j ou tous les 2 jours. Contrôle digoxinémie et ECG réguliers. La digoxine n'est pas dialysable."},
        ],
        "reference": "ESC HF Guidelines 2021, Vidal"
    },
    "Aciclovir (IV)": {
        "classe": "Antiviral — Analogue nucléosidique",
        "indication": "Herpès simplex sévère, Zona, Encéphalite herpétique",
        "dose_normale": "5–10 mg/kg q8h IV",
        "paliers": [
            {"dfg_min": 50, "dfg_max": 999, "dose": "5–10 mg/kg q8h", "niveau": "normal",
             "commentaire": "Dose standard. Perfusion lente sur 1h minimum. Bonne hydratation."},
            {"dfg_min": 25, "dfg_max": 49, "dose": "5–10 mg/kg q12h", "niveau": "warning",
             "commentaire": "Espacer à toutes les 12h."},
            {"dfg_min": 10, "dfg_max": 24, "dose": "5–10 mg/kg q24h", "niveau": "danger",
             "commentaire": "Une perfusion quotidienne. Hydratation +++."},
            {"dfg_min": 0, "dfg_max": 9, "dose": "2.5 mg/kg q24h — supplément dialyse", "niveau": "danger",
             "commentaire": "Réduire à 50 %. Dose supplémentaire de 2.5 mg/kg après hémodialyse (aciclovir dialysable)."},
        ],
        "reference": "Vidal/SPC, Lexicomp"
    },
}

# ─── Cockcroft-Gault ───────────────────────────────────────────────────────────
def calc_dfg(age, poids, sexe, creatinine_umol):
    F = 1.0 if sexe == "Homme" else 0.85
    dfg = ((140 - age) * poids * F) / (0.815 * creatinine_umol)
    return max(round(dfg, 1), 0.0)

def get_ckd_stage(dfg):
    if dfg >= 90:  return "G1", "Normal ou élevé",         "#10b981"
    if dfg >= 60:  return "G2", "Légèrement diminué",      "#84cc16"
    if dfg >= 45:  return "G3a","Légère à modérée",        "#f59e0b"
    if dfg >= 30:  return "G3b","Modérée à sévère",        "#f97316"
    if dfg >= 15:  return "G4", "Sévèrement diminué",      "#ef4444"
    return              "G5",  "Insuffisance rénale terminale", "#dc2626"

def get_palier(paliers, dfg):
    for p in paliers:
        if p["dfg_min"] <= dfg <= p["dfg_max"]:
            return p
    return paliers[-1]

NIVEAU_COLORS = {
    "normal":         ("#10b981", "#052e16", "✅ Dose normale"),
    "warning":        ("#f59e0b", "#1c1408", "⚠️  Dose ajustée"),
    "danger":         ("#ef4444", "#1c0a0a", "🔴 Précaution majeure"),
    "contraindicated":("#dc2626", "#1c0505", "🚫 Contre-indiqué"),
}

# ─── SIDEBAR ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 👤 Paramètres patient")
    st.markdown("---")
    age   = st.number_input("Âge (ans)",          min_value=18,  max_value=100, value=65, step=1)
    sexe  = st.radio("Sexe biologique",            ["Homme", "Femme"])
    poids = st.number_input("Poids (kg)",          min_value=30.0, max_value=250.0, value=70.0, step=0.5)
    creat = st.number_input("Créatininémie (µmol/L)", min_value=20.0, max_value=2000.0, value=90.0, step=1.0)

    st.markdown("---")
    dfg = calc_dfg(age, poids, sexe, creat)
    stage, desc, color = get_ckd_stage(dfg)
    st.markdown(f"""
    <div style="background:#18181b;border-radius:10px;padding:16px;border:1px solid #27272a;text-align:center">
      <div style="font-size:2.2rem;font-weight:800;color:{color}">{dfg}</div>
      <div style="color:#94a3b8;font-size:0.8rem;margin-top:2px">mL/min (Cockcroft-Gault)</div>
      <div style="margin-top:10px;background:#09090b;border-radius:6px;padding:8px">
        <span style="font-weight:700;color:{color};font-size:1rem">Stade {stage}</span><br>
        <span style="color:#d1d5db;font-size:0.82rem">{desc}</span>
      </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")
    creat_mgdl = round(creat / 88.42, 2)
    st.markdown(f"<div style='color:#64748b;font-size:0.78rem'>Créatinine : {creat_mgdl} mg/dL</div>", unsafe_allow_html=True)
    st.markdown("<div style='color:#64748b;font-size:0.78rem'>Formule : Cockcroft-Gault</div>", unsafe_allow_html=True)

# ─── MAIN ─────────────────────────────────────────────────────────────────────
st.markdown("""
<div style="padding:28px 0 8px">
  <h1 style="margin:0;font-size:1.9rem">💊 Ajustement Posologique</h1>
  <p style="color:#64748b;margin-top:6px">Adaptation des doses selon la fonction rénale — basé sur le DFG Cockcroft-Gault</p>
</div>
""", unsafe_allow_html=True)

# Drug selector
drug_name = st.selectbox(
    "Sélectionner le médicament",
    options=list(DRUGS.keys()),
    index=0
)

if drug_name:
    drug = DRUGS[drug_name]
    palier = get_palier(drug["paliers"], dfg)
    niv_color, niv_bg, niv_label = NIVEAU_COLORS[palier["niveau"]]

    # ── Résultat principal
    st.markdown(f"""
    <div style="background:{niv_bg};border:2px solid {niv_color};border-radius:14px;padding:24px 28px;margin:20px 0">
      <div style="display:flex;align-items:center;gap:12px;margin-bottom:14px">
        <span style="font-size:1.5rem">{niv_label}</span>
        <span style="background:{niv_color}22;color:{niv_color};padding:4px 12px;border-radius:20px;font-size:0.82rem;font-weight:600">
          DFG {dfg} mL/min
        </span>
      </div>
      <div style="font-size:1.4rem;font-weight:700;color:#f1f5f9;margin-bottom:10px">
        {palier['dose']}
      </div>
      <div style="color:#cbd5e1;font-size:0.92rem;line-height:1.6">
        {palier['commentaire']}
      </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Infos médicament
    col1, col2 = st.columns([1, 1])
    with col1:
        st.markdown(f"""
        <div style="background:#111113;border:1px solid #27272a;border-radius:10px;padding:16px;height:100%">
          <div style="color:#64748b;font-size:0.75rem;text-transform:uppercase;letter-spacing:.05em;margin-bottom:8px">Classe</div>
          <div style="color:#e2e8f0;font-size:0.9rem">{drug['classe']}</div>
          <div style="color:#64748b;font-size:0.75rem;text-transform:uppercase;letter-spacing:.05em;margin:12px 0 8px">Indication principale</div>
          <div style="color:#e2e8f0;font-size:0.9rem">{drug['indication']}</div>
          <div style="color:#64748b;font-size:0.75rem;text-transform:uppercase;letter-spacing:.05em;margin:12px 0 8px">Dose normale (DFG ≥ 60)</div>
          <div style="color:#e2e8f0;font-size:0.9rem">{drug['dose_normale']}</div>
        </div>
        """, unsafe_allow_html=True)
    with col2:
        st.markdown(f"""
        <div style="background:#111113;border:1px solid #27272a;border-radius:10px;padding:16px;height:100%">
          <div style="color:#64748b;font-size:0.75rem;text-transform:uppercase;letter-spacing:.05em;margin-bottom:8px">Tous les paliers</div>
        """, unsafe_allow_html=True)
        for p in drug["paliers"]:
            pc, _, _ = NIVEAU_COLORS[p["niveau"]]
            dfg_range = f"DFG {p['dfg_min']}–{p['dfg_max'] if p['dfg_max'] < 900 else '∞'}"
            is_current = (p["dfg_min"] <= dfg <= p["dfg_max"])
            border = f"border-left:3px solid {pc}" if is_current else "border-left:3px solid #27272a"
            bg = f"background:{pc}11" if is_current else ""
            st.markdown(f"""
            <div style="{border};{bg};padding:6px 10px;border-radius:4px;margin-bottom:6px">
              <span style="color:{pc};font-size:0.75rem;font-weight:600">{dfg_range}</span>
              <span style="color:#94a3b8;font-size:0.75rem;margin-left:8px">{p['dose']}</span>
              {'<span style="color:#f1f5f9;font-size:0.7rem;margin-left:4px">◀ actuel</span>' if is_current else ''}
            </div>
            """, unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    # ── Niveaux cibles trough (tacrolimus uniquement)
    if "trough_cibles" in drug:
        st.markdown("#### 🎯 Niveaux résiduels cibles (trough C0)")
        cols = st.columns(len(drug["trough_cibles"]))
        for i, tc in enumerate(drug["trough_cibles"]):
            with cols[i]:
                st.markdown(f"""
                <div style="background:#111113;border:1px solid {tc['couleur']}44;border-radius:10px;padding:14px;text-align:center">
                  <div style="color:{tc['couleur']};font-size:1.1rem;font-weight:700">{tc['cible']}</div>
                  <div style="color:#94a3b8;font-size:0.78rem;margin-top:4px">{tc['phase']}</div>
                </div>
                """, unsafe_allow_html=True)

    # ── Interactions (si disponible)
    if "interactions" in drug:
        st.markdown(f"""
        <div style="background:#1c1208;border:1px solid #92400e;border-radius:10px;padding:14px;margin-top:16px">
          <div style="color:#fbbf24;font-size:0.82rem">{drug['interactions']}</div>
        </div>
        """, unsafe_allow_html=True)

    # ── Référence
    st.markdown(f"""
    <div style="margin-top:16px;color:#475569;font-size:0.75rem">
      📚 Références : {drug['reference']}
    </div>
    """, unsafe_allow_html=True)

# ─── Disclaimer ───────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown("""
<div style="background:#0f0f11;border:1px solid #27272a;border-radius:10px;padding:14px;color:#475569;font-size:0.78rem;text-align:center">
  ⚕️ <strong style="color:#64748b">Outil d'aide à la décision — ne remplace pas le jugement clinique.</strong>
  Vérifier systématiquement les RCP et adapter selon le contexte (hépatopathie, interactions, poids, âge physiologique).
  MedFlow AI — usage professionnel médical exclusif.
</div>
""", unsafe_allow_html=True)
