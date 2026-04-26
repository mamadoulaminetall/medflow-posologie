import os

# AI_OK = True si la clé API est configurée (import anthropic est différé dans la fonction)
AI_OK = bool(os.environ.get("ANTHROPIC_API_KEY", ""))


def generate_consultation_summary(
    age, sexe, poids, dfg, stade, stade_desc,
    na_val, na_label, k_val, k_label,
    phase_label, c0, c0_statut, t_min, t_max,
    dose_act, dose_rec, dose_prise,
    k_eleve=False, ht_pct=0, c0_raw=None,
    mmf_data=None, pred_data=None,
) -> str | None:
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        return None

    if ht_pct > 0 and c0_raw is not None and c0_raw != c0:
        ht_line = f"- C0 mesuré en laboratoire : {c0_raw} ng/mL → corrigé pour hématocrite {ht_pct}% : {c0} ng/mL\n"
    elif ht_pct > 0:
        ht_line = f"- Hématocrite : {ht_pct}% (correction C0 appliquée)\n"
    else:
        ht_line = ""
    k_line = f"- Hyperkaliémie : K⁺ = {k_val} mmol/L > 5,5 — dose plafonnée à la dose actuelle\n" if k_eleve else ""

    # Bloc MMF optionnel
    mmf_block = ""
    if mmf_data:
        mmf_block = (
            "\nMMF / Mycophénolate mofétil :\n"
            f"- Dose actuelle : {mmf_data.get('dose_act', '—')} mg/j → recommandée : {mmf_data.get('dose_rec', '—')} mg/j\n"
            f"- Schéma : {mmf_data.get('schema', '—')}\n"
        )
        alertes_mmf = mmf_data.get("alertes", [])
        if alertes_mmf:
            mmf_block += "- Alertes MMF : " + " | ".join(t for _, t in alertes_mmf) + "\n"

    # Bloc Prednisolone optionnel
    pred_block = ""
    if pred_data:
        pred_block = (
            "\nPrednisolone / Corticothérapie :\n"
            f"- Dose actuelle : {pred_data.get('dose_act', '—')} mg/j → recommandée : {pred_data.get('dose_rec', '—')} mg/j\n"
            f"- Cible phase : {pred_data.get('cible', '—')} — Statut : {pred_data.get('statut', '—')}\n"
        )
        if pred_data.get("glycemie", 0) > 0:
            pred_block += f"- Glycémie à jeun : {pred_data['glycemie']} mmol/L\n"
        if pred_data.get("pas", 0) > 0:
            pred_block += f"- Pression artérielle systolique : {pred_data['pas']} mmHg\n"
        alertes_pred = pred_data.get("alertes", [])
        if alertes_pred:
            pred_block += "- Alertes corticoïdes : " + " | ".join(t for _, t in alertes_pred) + "\n"

    n_modules = 1 + (1 if mmf_data else 0) + (1 if pred_data else 0)
    nb_phrases = "6-8" if n_modules > 1 else "4-5"

    prompt = (
        "Tu es un assistant médical spécialisé en transplantation cardiaque.\n"
        f"Rédige un résumé de consultation en français médical ({nb_phrases} phrases), "
        "prêt à être collé dans un dossier patient informatisé (DPI).\n"
        "IMPORTANT : texte plain uniquement, aucun Markdown (pas de ##, --, **, etc.).\n\n"
        "Données :\n"
        f"- Âge : {age} ans, {sexe}, {poids} kg\n"
        f"- DFG estimé (Cockcroft-Gault) : {dfg} mL/min — Stade IRC {stade} ({stade_desc})\n"
        f"- Phase post-greffe : {phase_label}\n"
        f"- C0 tacrolimus résiduel : {c0} ng/mL ({c0_statut}) — cible {t_min}–{t_max} ng/mL\n"
        f"- Natrémie : {na_val} mmol/L ({na_label})\n"
        f"- Kaliémie : {k_val} mmol/L ({k_label})\n"
        f"- Dose tacrolimus actuelle : {dose_act} mg/j → recommandée : {dose_rec} mg/j "
        f"({dose_prise} mg × 2/j, q12h)\n"
        f"{ht_line}{k_line}"
        f"{mmf_block}{pred_block}\n"
        "Consignes :\n"
        "- Rédiger à la 3ème personne (ex : « Le patient présente… »)\n"
        "- Style note médicale concise, couvrir chaque traitement mentionné\n"
        "- Ne pas inclure de nom de patient ni d'identifiant\n"
        "- Dernière phrase : justification globale des ajustements posologiques\n"
        "- Conclure par la ligne : *Généré par MedFlow AI — outil d'aide à la décision*"
    )

    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
        msg = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=700,
            messages=[{"role": "user", "content": prompt}],
        )
        return msg.content[0].text
    except Exception:
        return None
