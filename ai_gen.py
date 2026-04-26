import os

# AI_OK = True si la clé API est configurée (import anthropic est différé dans la fonction)
AI_OK = bool(os.environ.get("ANTHROPIC_API_KEY", ""))


def generate_consultation_summary(
    age, sexe, poids, dfg, stade, stade_desc,
    na_val, na_label, k_val, k_label,
    phase_label, c0, c0_statut, t_min, t_max,
    dose_act, dose_rec, dose_prise,
    k_eleve=False, ht_pct=0,
) -> str | None:
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        return None

    ht_line = f"- Hématocrite : {ht_pct}% (correction C0 appliquée)\n" if ht_pct > 0 else ""
    k_line  = f"- Hyperkaliémie : K⁺ = {k_val} mmol/L > 5,5 — dose plafonnée à la dose actuelle\n" if k_eleve else ""

    prompt = (
        "Tu es un assistant médical spécialisé en transplantation cardiaque.\n"
        "Rédige un résumé de consultation en français médical (4-5 phrases), "
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
        f"{ht_line}{k_line}\n"
        "Consignes :\n"
        "- Rédiger à la 3ème personne (ex : « Le patient présente… »)\n"
        "- Style note médicale concise, sans répéter chaque chiffre inutilement\n"
        "- Ne pas inclure de nom de patient ni d'identifiant\n"
        "- Dernière phrase : justification courte de l'ajustement posologique\n"
        "- Conclure par la ligne : *Généré par MedFlow AI — outil d'aide à la décision*"
    )

    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
        msg = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=500,
            messages=[{"role": "user", "content": prompt}],
        )
        return msg.content[0].text
    except Exception:
        return None
