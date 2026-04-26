# calculations.py — fonctions cliniques MedFlow AI Tacrolimus

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
    ("Correction hématocrite",  "Størset E et al. Transpl Int. 2014;27(2):216–224. Influence de l'hématocrite sur la mesure du C0 tacrolimus."),
]

META_DATA = [
    ("Ojo et al.",            "N Engl J Med 2003",           "69 321",    "16,5 % IRC sévère à 5 ans sous CNI (greffe cardiaque)",           "Justifie le plafond rénal 0,1 mg/kg × facteur DFG"),
    ("Ekberg et al. SYMPHONY","N Engl J Med 2007",           "1 645",     "DFG +8,3 mL/min si CNI réduit vs standard (p < 0,001)",          "Valide la réduction de dose par stade IRC"),
    ("Naesens et al.",        "CJASN 2009",                  "revue syst.","Toxicité CNI dose-dépendante ; réduction ↓ progression IRC",     "Justifie les facteurs de correction G1–G5"),
    ("ISHLT Registry",        "J Heart Lung Transplant 2022",">140 000",  "Tacrolimus = protocole dominant (> 95 % des greffes cardiaques)", "Valide les cibles C0 par phase post-greffe"),
    ("Staatz & Tett",         "Clin Pharmacokinet 2004",     "revue PK",  "Corrélation C0/AUC r = 0,89 — ajustement proportionnel validé",  "Base de la règle de trois PK de l'outil"),
    ("Tumlin et al.",         "Am J Kidney Dis 1996",        "série",     "Hyperkaliémie CNI : bloc tubulaire aldostérone-like",             "Justifie l'alerte K⁺ et la limite de dose si K > 5,5"),
]

CYP3A4_INTERACTIONS = {
    "inhibiteurs": [
        {"drug": "Fluconazole / Voriconazole / Itraconazole",    "effect": "Taux Tac ×2–×5",           "action": "Réduire dose Tac 30–50 % + C0 à J3 et J7"},
        {"drug": "Diltiazem / Vérapamil",                         "effect": "Taux Tac +20–40 %",         "action": "Réduire dose Tac 10–25 % + C0 à J7"},
        {"drug": "Azithromycine / Clarithromycine / Érythromycine","effect": "Taux Tac +20–30 %",        "action": "Surveiller C0 à J5–J7"},
        {"drug": "Amiodarone",                                    "effect": "Inhibition prolongée (semaines)", "action": "Monitoring hebdomadaire × 4–6 semaines"},
        {"drug": "Ritonavir / Cobicistat (ARV)",                  "effect": "Taux Tac ×10–×20",          "action": "Contre-indication relative — avis expert urgent"},
        {"drug": "Pamplemousse / Grapefruit",                     "effect": "Taux Tac +20–100 % (variable)", "action": "Interdire la consommation"},
    ],
    "inducteurs": [
        {"drug": "Rifampicine",                                   "effect": "Taux Tac −70–80 %",          "action": "Éviter — si indispensable : dose ×2–3 + monitoring intensif"},
        {"drug": "Phénytoïne / Carbamazépine / Phénobarbital",    "effect": "Taux Tac −30–50 %",          "action": "Augmenter dose Tac + C0 à J7"},
        {"drug": "Millepertuis (St John's Wort)",                 "effect": "Taux Tac −50–65 %",          "action": "Contre-indication ABSOLUE — arrêter immédiatement"},
    ],
    "hyperkaliemie": [
        {"drug": "IEC (ramipril, énalapril, périndopril…)",       "effect": "Majoration hyperkaliémie",   "action": "Surveiller K⁺ à J3–J7"},
        {"drug": "ARA2 (losartan, valsartan, irbesartan…)",       "effect": "Majoration hyperkaliémie",   "action": "Surveiller K⁺ à J3–J7"},
        {"drug": "AINS (ibuprofène, naproxène, diclofénac)",      "effect": "Rétention K⁺ + néphrotoxicité","action": "Éviter si DFG < 60 mL/min"},
        {"drug": "Spironolactone / Éplérénone",                   "effect": "Hyperkaliémie sévère",       "action": "Contre-indiqué si K⁺ > 5,0 mmol/L"},
    ],
}


# ─── Fonctions de calcul ──────────────────────────────────────────────────────
def calc_dfg(age: int, poids: float, sexe: str, creat_umol: float) -> float:
    F = 1.0 if sexe == "Homme" else 0.85
    return max(round(((140 - age) * poids * F) / (0.815 * creat_umol), 1), 0.0)


def get_stade(dfg: float):
    if dfg >= 90: return "G1",  "Normale",           "#10b981"
    if dfg >= 60: return "G2",  "Légèrement ↓",      "#84cc16"
    if dfg >= 45: return "G3a", "Légère–modérée ↓",  "#f59e0b"
    if dfg >= 30: return "G3b", "Modérée–sévère ↓",  "#f97316"
    if dfg >= 15: return "G4",  "Sévèrement ↓",      "#ef4444"
    return               "G5",  "Terminale",          "#dc2626"


def arrondir_05(v: float) -> float:
    return round(round(v / 0.5) * 0.5, 1)


def interp_sodium(na: float):
    if na < 125:  return "Hyponatrémie sévère", "#dc2626", "🔴", True
    if na < 135:  return "Hyponatrémie",        "#f97316", "⚠️", False
    if na <= 145: return "Normal",              "#10b981", "✅", False
    return               "Hypernatrémie",       "#f97316", "⚠️", False


def interp_potassium(k: float):
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


def correct_c0_hematocrit(c0: float, ht: float) -> float:
    """Correction C0 pour hématocrite — tacrolimus 75 % lié aux érythrocytes.
    C0_corr = C0 × (1 + 0.75 × (0.45/Ht − 1))  ·  Størset et al., Transpl Int 2014
    ht : fraction décimale (ex : 0.40 pour 40 %)
    """
    if ht <= 0 or ht > 1:
        return c0
    return round(c0 * (1 + 0.75 * (0.45 / ht - 1)), 2)


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
            f"L'ajustement PK proportionnel (Staatz & Tett, Clin Pharmacokinet 2004 - r C0/AUC = 0,89) "
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

    # 3. Plafond néphroprotecteur
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
        items.append(("Plafond nephroprotecteur - priorite renale", nephro_body))
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
        items.append(("Hyperkaliemie - contrainte additionnelle",
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


# ─── MMF (Mycophenolate Mofetil) ─────────────────────────────────────────────
MMF_TAB_MG = 500  # 1 comprimé = 500 mg

MMF_PHASE_TARGETS = {
    "M0 – M3  (phase précoce)":  3000,
    "M3 – M12  (maintenance)":   2000,
    "> 1 an  (phase stable)":    1500,
}

MMF_REFS = [
    ("ISHLT 2016 — MMF",      "Kobashigawa J et al. J Heart Lung Transplant. 2016;35(1):1–23. Dose MMF standard : 1–1,5 g × 2/j en post-greffe cardiaque."),
    ("Myfortic equiv.",       "Salvadori M et al. Am J Transplant. 2004;4(2):231–236. EC-MPA 720 mg ≡ MMF 1000 mg en efficacité/tolérance."),
    ("Leucopénie / MMF",      "Remuzzi G et al. Transplantation. 2004;78(4):491–496. Leucopénie dose-dépendante sous MMF — seuils GB < 3,0 G/L."),
    ("MMF DFG < 25",          "Ransom JT. Ther Drug Monit. 1995. Accumulation métabolite MPAG si DFG < 25 — dose max 2 × 1 g/j recommandée."),
]


def recommander_mmf(dose_act_mg, phase_key, dfg=60.0, gb=0.0, pnn=0.0, gi_intolerance=False):
    """Recommande la dose MMF totale (mg/j) avec posologie BID.
    1 comprimé Cellcept® = 500 mg.
    Retourne: (dose_rec, dose_matin, dose_soir, cp_matin, cp_soir, alertes)
    alertes = liste de (icône, titre, action)
    """
    TAB = MMF_TAB_MG
    alertes = []

    target = MMF_PHASE_TARGETS.get(phase_key, 2000)
    dose = dose_act_mg if dose_act_mg >= TAB else target

    # Correction rénale (DFG < 25 → max 2000 mg/j)
    if 0 < dfg < 25:
        dose = min(dose, 2000)
        alertes.append(("⚠️", "DFG < 25 mL/min",
                         "Dose max : 2000 mg/j (accumulation MPAG) — Ransom et al., Ther Drug Monit 1995"))

    # Leucopénie (GB)
    if gb > 0:
        if gb < 1.5:
            dose = 0
            alertes.append(("🔴", f"GB = {gb} G/L < 1,5 — LEUCOPÉNIE SÉVÈRE",
                             "ARRÊT MMF IMMÉDIAT · Avis infectiologue + hématologue urgent · Ne pas reprendre sans NFS normalisée"))
        elif gb < 2.0:
            dose = max(dose - 1000, 0)
            alertes.append(("🔴", f"GB = {gb} G/L < 2,0 — leucopénie sévère",
                             "Réduction −1000 mg/j · NFS de contrôle à J3 · Avis hématologue si persistant"))
        elif gb < 3.0:
            dose = max(dose - 500, 500)
            alertes.append(("⚠️", f"GB = {gb} G/L < 3,0 — leucopénie modérée",
                             "Réduction −500 mg/j · NFS de contrôle à J7"))

    # Neutropénie (PNN)
    if pnn > 0:
        if pnn < 0.5:
            dose = 0
            alertes.append(("🔴", f"PNN = {pnn} G/L < 0,5 — AGRANULOCYTOSE",
                             "ARRÊT IMMÉDIAT MMF · G-CSF à discuter · Isolement protecteur"))
        elif pnn < 1.0:
            dose = max(dose - 1000, 0)
            alertes.append(("🔴", f"PNN = {pnn} G/L < 1,0 — neutropénie sévère",
                             "Réduction −1000 mg/j · NFS à J3"))
        elif pnn < 1.5:
            dose = max(dose - 500, 500)
            alertes.append(("⚠️", f"PNN = {pnn} G/L < 1,5 — neutropénie modérée",
                             "Réduction −500 mg/j · NFS à J7"))

    # Intolérance GI
    if gi_intolerance and dose > 0:
        dose = max(dose - 500, 1000)
        alertes.append(("ℹ️", "Intolérance GI documentée",
                         "Réduction −500 mg/j ou switch EC-MPA (Myfortic® 720 mg ≡ MMF 1000 mg) · Fractionnement des prises à envisager"))

    # Arrondir au multiple de 500 mg
    dose = round(dose / TAB) * TAB
    dose = max(dose, 0)

    # Calcul BID (matin + soir)
    if dose == 0:
        dose_matin, dose_soir, cp_matin, cp_soir = 0, 0, 0, 0
    else:
        half = dose / 2
        if half % TAB == 0:  # symétrique
            cp_matin = cp_soir = int(half // TAB)
            dose_matin = dose_soir = int(half)
        else:  # asymétrique (ex: 1500 mg/j → 1000 matin + 500 soir)
            cp_matin = int(half // TAB) + 1
            cp_soir  = int(half // TAB)
            dose_matin = cp_matin * TAB
            dose_soir  = cp_soir  * TAB

    return dose, dose_matin, dose_soir, cp_matin, cp_soir, alertes


# ─── Prednisolone / Prednisone post-greffe cardiaque ─────────────────────────
PRED_CIBLES = {
    "M0 – M3  (phase précoce)":  {"min": 15.0, "max": 30.0, "step": 5.0},
    "M3 – M12  (maintenance)":   {"min": 10.0, "max": 15.0, "step": 2.5},
    "> 1 an  (phase stable)":    {"min":  5.0, "max": 10.0, "step": 2.5},
}

PRED_REFS = [
    ("ISHLT 2016 — Corticoïdes",  "Kobashigawa J et al. J Heart Lung Transplant. 2016;35(1):1–23. Protocole corticoïdes post-greffe cardiaque — dégression progressive."),
    ("Sevrage stéroïdes",         "Kushwaha SS et al. J Heart Lung Transplant. 2001;20(4):430–438. Sevrage possible chez patients stables > 1 an sans rejet récent."),
    ("NODAT / Diabète cortisone", "Hjelmesaeth J et al. Nephrol Dial Transplant. 1997;12(12):2625–2631. Hyperglycémie cortico-induite — facteur de risque CV et infectieux."),
    ("Ostéoporose corticoïdes",   "Adler RA et al. J Bone Miner Res. 2017;32(3):447–457. Calcium + Vit D + bisphosphonates si corticoïdes > 3 mois ≥ 7,5 mg/j."),
]


def recommander_prednisolone(dose_act, phase_key, poids=70.0,
                              glycemie=0.0, pas=0,
                              rejet_recent=False, infection_active=False):
    cible = PRED_CIBLES.get(phase_key, PRED_CIBLES["> 1 an  (phase stable)"])
    c_min, c_max, step = cible["min"], cible["max"], cible["step"]
    alertes = []

    if glycemie > 0:
        if glycemie > 11.0:
            alertes.append(("🔴", f"Glycémie = {glycemie} mmol/L — diabète cortico-induit sévère",
                             "Insuline requise en urgence · Avis diabétologie · Envisager réduction corticoïdes si possible"))
        elif glycemie > 7.0:
            alertes.append(("⚠️", f"Glycémie = {glycemie} mmol/L — hyperglycémie cortico-induite",
                             "Surveillance glycémique quotidienne · Régime + activité · Discuter antidiabétiques oraux"))

    if pas > 0:
        if pas > 160:
            alertes.append(("🔴", f"PAS = {pas} mmHg — HTA sévère cortico-induite",
                             "Traitement antihypertenseur urgent · Calcium-bloquants en 1ère intention post-greffe · Avis cardiologue"))
        elif pas > 140:
            alertes.append(("⚠️", f"PAS = {pas} mmHg — HTA modérée",
                             "Renforcer traitement antihypertenseur · Attention interaction CYP3A4 avec Tac si diltiazem/vérapamil"))

    if rejet_recent:
        alertes.append(("🔴", "Rejet aigu récent documenté",
                         "Ne pas réduire les corticoïdes · Maintenir dose actuelle · Réévaluation en équipe de transplantation"))

    if infection_active:
        alertes.append(("⚠️", "Infection active en cours",
                         "Tension immunosuppression / contrôle infectieux · Avis infectiologue + équipe transplantation urgent"))

    if dose_act >= 7.5:
        alertes.append(("ℹ️", "Prévention ostéoporose sous corticoïdes chroniques",
                         "Calcium 1000–1200 mg/j + Vitamine D 800 UI/j systématiques · Bisphosphonates si > 3 mois (Adler et al., JBMR 2017)"))

    if rejet_recent:
        dose_rec = max(dose_act, c_min)
        statut = "Maintenu — rejet récent" if dose_rec == dose_act else "Augmenté — rejet récent"
        statut_color = "#ef4444"
    elif dose_act > c_max:
        dose_rec = max(dose_act - step, c_max)
        statut, statut_color = "Au-dessus — réduire par palier", "#f59e0b"
    elif dose_act < c_min:
        dose_rec = dose_act
        statut, statut_color = "En dessous — surveiller (insuffisance surrénale)", "#3b82f6"
        alertes.append(("ℹ️", f"Dose < cible phase ({c_min} mg/j minimum)",
                         "Ne pas arrêter brutalement — risque d'insuffisance surrénalienne · Réévaluer avec l'équipe"))
    else:
        dose_rec = dose_act
        statut, statut_color = "Dans la cible — maintenir", "#10b981"

    if phase_key == "> 1 an  (phase stable)" and dose_act <= 5.0 and not rejet_recent and not infection_active:
        alertes.append(("ℹ️", "Sevrage stéroïdes envisageable (> 1 an, dose ≤ 5 mg, patient stable)",
                         "Réduction par paliers de 1 mg/mois · Vérifier cortisol 8h avant arrêt définitif · ISHLT 2016"))

    dose_rec = round(round(dose_rec / 0.5) * 0.5, 1)
    dose_rec = max(dose_rec, 0.0)
    return dose_rec, alertes, statut, statut_color


def _estimate_expl_height(items, cpl=85, lh=5, th=5.5, gap=3):
    """Estime la hauteur PDF (mm) d'un bloc d'explication clinique."""
    total = 6
    for _, body in items:
        total += th + max(1, -(-len(body) // cpl)) * lh + gap
    return total
