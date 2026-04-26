# MedFlow AI — Posologie · Greffe Cardiaque

**Suite tri-module d'aide à la décision posologique post-transplantation cardiaque**  
Tacrolimus · MMF / Cellcept® · Prednisolone — Compte-rendu PDF + Résumé IA

[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://medflow-posologie.streamlit.app)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-3b82f6.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-10b981.svg)](LICENSE)

---

## Présentation

**MedFlow AI Posologie** est une suite clinique spécialisée dans le suivi thérapeutique post-transplantation cardiaque. Elle couvre les trois piliers de l'immunosuppression de maintenance en un seul outil :

| Module | Traitement | Références |
|---|---|---|
| 🫀 Tacrolimus | Prograf® — ajustement PK + plafond rénal | ISHLT 2016, Staatz & Tett 2004, Ojo 2003 |
| 💊 MMF | Cellcept® — seuils hématologiques + schéma BID | ISHLT 2016, Kobashigawa 2006, Kaplan 2014 |
| 🟠 Prednisolone | Corticothérapie — sevrage progressif + NODAT | ISHLT 2016, Kushwaha 2001, Hjelmesaeth 1997 |

Le clinicien remplit les 3 onglets, génère un **compte-rendu PDF multimodule** et un **résumé IA prêt pour le DPI** en un clic — sans recopie manuelle.

---

## Fonctionnalités

### 🫀 Module Tacrolimus
- **DFG Cockcroft-Gault** en temps réel (âge, poids, sexe, créatinine µmol/L)
- **Stade KDIGO** G1 à G5 avec code couleur
- **Ajustement PK proportionnel** : dose × (C0-cible / C0-mesuré) — Staatz & Tett 2004
- **Plafond néphroprotecteur** : 0,1 mg/kg × facteur DFG par stade KDIGO
- **Correction hématocrite** optionnelle (C0 laboratoire → C0 corrigé)
- Gestion hyperkaliémie : plafonnement automatique si K⁺ > 5,5 mmol/L
- Cibles C0 par phase : M0–M3 (10–15), M3–M12 (8–12), >1 an (5–10 ng/mL)
- Alertes interactions CYP3A4 (inhibiteurs / inducteurs)

### 💊 Module MMF / Cellcept®
- Dose recommandée par phase post-greffe et stade rénal
- Seuils hématologiques : GB < 3,0 G/L → réduction ; GB < 2,0 / PNN < 1,0 → arrêt
- Schéma BID en comprimés Cellcept® 500 mg (matin/soir individualisé)
- Alertes intolérance gastro-intestinale avec adaptation de schéma

### 🟠 Module Prednisolone
- Cibles par phase : M0–M3 (15–30 mg/j), M3–M12 (10–15 mg/j), >1 an (5–10 mg/j)
- **Calendrier de sevrage progressif** par paliers (protocole ISHLT 2016)
- Alertes NODAT (glycémie > 7 mmol/L), HTA (PAS > 140 mmHg), ostéoporose
- Contre-indication à l'arrêt si rejet récent ou infection active
- Équivalences corticoïdes (prednisone / méthylprednisolone / hydrocortisone)
- Grille de surveillance : DXA, cortisol 8h, glycémie, PA

### 📄 Rapport PDF multimodule
- En-tête MedFlow AI + identité patient + ID SHA-256
- Bilan Tacrolimus complet (biologie rénale, C0, recommandation, raisonnement PK)
- Section MMF : posologie, schéma BID, alertes hématologiques
- Section Prednisolone : dose, cible, statut, glycémie, PA, alertes
- Interprétation clinique détaillée + raisonnement méthodologique (4 étapes)
- Historique des bilans + graphiques d'évolution (DFG, C0, dose, K⁺)
- **Résumé IA** (Claude) tri-module prêt pour le DPI

### 🤖 Résumé IA (Claude)
- Prompt médical structuré — rédaction à la 3ème personne, style note médicale
- Couvre les 3 traitements en 6–8 phrases si tous les onglets sont remplis
- Prêt à coller directement dans le DPI sans modification

### 🗃️ Suivi longitudinal
- Base SQLite : ID patient déterministe (SHA-256, 8 caractères)
- Enregistrement horodaté de chaque bilan
- Graphiques Plotly interactifs (thème sombre) : DFG, C0, dose, kaliémie
- Comparaison bilan précédent / bilan actuel

---

## Bases scientifiques

| Référence | Module | Contribution |
|---|---|---|
| Kobashigawa et al. ISHLT, *J Heart Lung Transplant* 2016 | Tous | Protocole immunosuppression post-greffe cardiaque |
| Staatz & Tett, *Clin Pharmacokinet* 2004 | Tacrolimus | Ajustement PK proportionnel (r C0/AUC = 0,89) |
| Ojo et al., *NEJM* 2003 (n = 69 321) | Tacrolimus | Plafond rénal 0,1 mg/kg |
| Ekberg et al. SYMPHONY, *NEJM* 2007 | Tacrolimus | Facteurs DFG par stade KDIGO |
| Naesens et al., *CJASN* 2009 | Tacrolimus | Néphrotoxicité dose-dépendante CNI |
| Tumlin et al., *Am J Kidney Dis* 1996 | Tacrolimus | Hyperkaliémie sous CNI |
| Kaplan et al., *Transplantation* 2014 | MMF | Seuils hématologiques MMF post-greffe |
| Kobashigawa et al., *Transplantation* 2006 | MMF | Doses MMF en transplantation cardiaque |
| Kushwaha et al., *J Heart Lung Transplant* 2001 | Prednisolone | Sevrage stéroïdes post-greffe cardiaque |
| Hjelmesaeth et al., *Nephrol Dial Transplant* 1997 | Prednisolone | NODAT / Diabète corticoïdes |
| Adler et al., *J Bone Miner Res* 2017 | Prednisolone | Prévention ostéoporose corticoïdes |

---

## Installation

```bash
git clone https://github.com/mamadoulaminetall/medflow-posologie.git
cd medflow-posologie
pip install -r requirements.txt
streamlit run app.py
```

### Variables d'environnement (optionnelles)

```toml
# .streamlit/secrets.toml
ANTHROPIC_API_KEY = "sk-ant-..."              # Résumé IA (Claude)
STRIPE_CHECKOUT_URL = "https://buy.stripe.com/..."  # Paywall PDF Pro
```

### Dépendances

```
streamlit>=1.30.0
fpdf2>=2.7.9
matplotlib>=3.7.0
plotly>=5.18.0
anthropic>=0.25.0
```

---

## Structure du projet

```
medflow-posologie/
├── app.py              # Application Streamlit principale (4 onglets)
├── calculations.py     # Logique clinique : Tacrolimus, MMF, Prednisolone
├── pdf_gen.py          # Génération PDF multimodule (fpdf2)
├── ai_gen.py           # Résumé IA tri-module (Claude API)
├── db.py               # Base SQLite patients & consultations
├── requirements.txt
└── README.md
```

---

## Workflow clinique

```
① Onglet Tacrolimus   →  DFG · C0 · dose · ionogramme
② Onglet MMF          →  GB · PNN · schéma BID
③ Onglet Prednisolone →  dose · glycémie · PA · sevrage
④ Retour Tacrolimus   →  [📄 PDF] ou [🤖 Résumé IA]
                         → rapport tri-module en un clic
```

---

## Déploiement Streamlit Cloud

1. Connecter le dépôt sur [share.streamlit.io](https://share.streamlit.io)
2. Point d'entrée : `app.py`
3. Configurer les secrets (`ANTHROPIC_API_KEY`, `STRIPE_CHECKOUT_URL`)
4. Déploiement automatique à chaque `git push`

---

## Avertissement

> Outil d'**aide à la décision clinique** exclusivement. Ne remplace pas la concertation de l'équipe de transplantation, la lecture des RCP officiels, ni le jugement clinique individuel. Adapter systématiquement au protocole institutionnel.
>
> **Usage professionnel médical exclusif — MedFlow AI.**

---

## Auteur

**Dr. Mamadou Lamine TALL, PhD**  
Bioinformatique & Intelligence Artificielle Médicale

- GitHub : [@mamadoulaminetall](https://github.com/mamadoulaminetall)
- Email : mamadoulaminetallgithub@gmail.com
- Plateforme : [MedFlow AI](https://medflowailanding.streamlit.app)

---

*Composant de la suite **MedFlow AI** — outils IA pour cliniciens.*
