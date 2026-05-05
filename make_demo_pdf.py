"""Génère 3 PDFs de démo MedFlow AI avec des patients fictifs."""
import sys
sys.path.insert(0, ".")

from calculations import PHASES, calc_dfg, get_stade, recommander_tacrolimus, arrondir_05
from pdf_gen import generate_pdf

CASES = [
    {
        "nom": "MARTIN", "prenom": "Pierre",
        "age": 52, "sexe": "Homme", "poids": 75.0, "creat": 110.0,
        "na": 138.0, "k": 4.2, "phase": "M3 – M12  (maintenance)",
        "c0": 6.5, "dose_act": 4.0, "desc": "sous_dosage",
    },
    {
        "nom": "DURAND", "prenom": "Monique",
        "age": 63, "sexe": "Femme", "poids": 68.0, "creat": 148.0,
        "na": 142.0, "k": 5.2, "phase": "> 1 an  (phase stable)",
        "c0": 16.0, "dose_act": 6.0, "desc": "surdosage_CYP3A4",
    },
    {
        "nom": "BERNARD", "prenom": "Jacques",
        "age": 58, "sexe": "Homme", "poids": 84.0, "creat": 120.0,
        "na": 140.0, "k": 4.5, "phase": "M3 – M12  (maintenance)",
        "c0": 9.0, "dose_act": 5.0, "desc": "NODAT_HTA",
    },
]

AI_SUMMARIES = [
    (
        "Patient de 52 ans (sexe masculin) en post-transplantation cardiaque, phase M3-M12. "
        "La concentration residuelle de tacrolimus (C0 = 6,5 ng/mL) est en dessous de la cible "
        "therapeutique (8-12 ng/mL), exposant le patient a un risque de rejet sous-immunosuppression. "
        "La fonction renale est preservee (DFG 115 mL/min, stade G1) et l'ionogramme est normal. "
        "La dose de tacrolimus est augmentee de 4 mg/j a 4,5 mg/j (2,5 mg matin + 2,0 mg soir, q12h). "
        "Ce reajustement vise a ramener le C0 dans la fenetre therapeutique afin de prevenir un episode de rejet aigu."
        "\n*Genere par MedFlow AI - outil d'aide a la decision*"
    ),
    (
        "Patiente de 63 ans (sexe feminin), phase stable (> 1 an post-greffe cardiaque). "
        "Le C0 tacrolimus est significativement au-dessus de la cible (16 ng/mL vs cible 5-8 ng/mL), "
        "avec une fonction renale moderement alteree (DFG 61 mL/min, stade G2). "
        "Une interaction medicamenteuse avec le diltiazem (inhibiteur CYP3A4) est documentee et "
        "peut expliquer l'elevation des taux residuels ; la kaliemie est a la limite superieure (5,2 mmol/L). "
        "La dose est reduite de 6 mg/j a 5,5 mg/j avec surveillance rapprochee du C0 et de la fonction renale. "
        "La discussion concernant l'arret ou la substitution du diltiazem est recommandee avec l'equipe cardiologique."
        "\n*Genere par MedFlow AI - outil d'aide a la decision*"
    ),
    (
        "Patient de 58 ans (sexe masculin), phase M3-M12 post-transplantation cardiaque. "
        "Le C0 tacrolimus est dans la cible therapeutique (9 ng/mL, cible 8-12 ng/mL) ; la dose est maintenue a 5 mg/j. "
        "La fonction renale est normale (DFG 108 mL/min, stade G1) et l'ionogramme est equilibre. "
        "Par ailleurs, une hyperglycemie a jeun (8,4 mmol/L) evocatrice de NODAT et une hypertension "
        "arterielle (PAS 152 mmHg) sont a surveiller dans le contexte d'une corticotherapie en cours. "
        "Un avis diabetologique et un ajustement de la prednisolone selon le protocole ISHLT sont recommandes."
        "\n*Genere par MedFlow AI - outil d'aide a la decision*"
    ),
]

for i, (case, ai_sum) in enumerate(zip(CASES, AI_SUMMARIES), 1):
    dfg = calc_dfg(case["age"], case["poids"], case["sexe"], case["creat"])
    stade_str, stade_desc_str, _ = get_stade(dfg)

    ph = PHASES[case["phase"]]
    t_min, t_max = ph["min"], ph["max"]
    k_eleve = case["k"] > 5.5

    dose_rec, dose_pk, plafond, fr = recommander_tacrolimus(
        case["dose_act"], case["c0"], t_min, t_max, dfg, case["poids"], k_eleve
    )

    if case["c0"] < t_min:
        c0_statut = "Sous-therapeutique"
        rec_titre = "⚠️ Augmentation recommandee"
    elif case["c0"] > t_max:
        c0_statut = "Supratherapeutique"
        rec_titre = "⚠️ Reduction recommandee"
    else:
        c0_statut = "Dans la cible"
        rec_titre = "✅ Dose maintenue"

    na_label = "Normal"
    k_label  = "Limite haute" if case["k"] > 5.0 else "Normal"
    pat_id   = f"DEMO{i:03d}"

    pdf_bytes = generate_pdf(
        case["nom"], case["prenom"], pat_id,
        case["age"], case["sexe"], case["poids"], case["creat"],
        dfg, stade_str, stade_desc_str,
        case["na"], na_label, case["k"], k_label,
        case["phase"], case["c0"], c0_statut, t_min, t_max,
        case["dose_act"], dose_rec, dose_pk, plafond, fr,
        k_eleve, rec_titre,
        history_rows=[],
        ai_summary=ai_sum,
    )

    fname = f"MedFlow_DEMO_{i}_{case['desc']}_{case['nom']}.pdf"
    with open(fname, "wb") as f:
        f.write(pdf_bytes)
    print(f"[OK] {fname}  (DFG={dfg} mL/min, C0={case['c0']} ng/mL -> dose rec {dose_rec} mg/j)")

print("\nDone — 3 PDFs generes.")
