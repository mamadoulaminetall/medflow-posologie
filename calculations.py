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


def _estimate_expl_height(items, cpl=85, lh=5, th=5.5, gap=3):
    """Estime la hauteur PDF (mm) d'un bloc d'explication clinique."""
    total = 6
    for _, body in items:
        total += th + max(1, -(-len(body) // cpl)) * lh + gap
    return total
