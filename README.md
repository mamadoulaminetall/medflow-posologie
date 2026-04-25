# MedFlow AI — Tacrolimus · Greffe Cardiaque

**Outil d'aide à la décision posologique pour le suivi thérapeutique du tacrolimus post-transplantation cardiaque**

[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://medflow-posologie.streamlit.app)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-3b82f6.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-10b981.svg)](LICENSE)

---

## Présentation

**MedFlow AI Posologie** est un outil clinique spécialisé dans le suivi thérapeutique du **tacrolimus (Prograf®)** chez les patients greffés cardiaques. Il combine pharmacocinétique, néphroprotection et ionogramme pour proposer une posologie individualisée, documentée et traçable.

Conçu pour une utilisation rapide en consultation ou en visite, sans inscription requise.

---

## Fonctionnalités

### Identification et suivi patient
- Saisie nom / prénom → **ID unique déterministe** (SHA-256, 8 caractères)
- Détection automatique patient connu avec badge *N bilans enregistrés*
- Base de données SQLite locale — aucune donnée transmise à l'extérieur

### Calculs cliniques
- **DFG Cockcroft-Gault** en temps réel (âge, poids, sexe, créatinine µmol/L)
- **Stade KDIGO** G1 à G5 avec code couleur
- **Ajustement PK proportionnel** du tacrolimus (Staatz & Tett, 2004) : dose × (C0-cible / C0-mesuré)
- **Plafond néphroprotecteur** individualisé : 0,1 mg/kg × facteur DFG par stade (Ojo 2003, Ekberg 2007, Naesens 2009)
- **Gestion hyperkaliémie** : plafonnement automatique si K⁺ > 5,5 mmol/L (Tumlin 1996)
- Cibles C0 par phase post-greffe : M0–M3 (10–15), M3–M12 (8–12), > 1 an (5–10 ng/mL)

### Rapport PDF multipage
- En-tête MedFlow AI avec identité patient et ID
- Bilan actuel en deux colonnes (biologie rénale / tacrolimus + ionogramme)
- Bloc recommandation coloré (vert / orange / rouge selon criticité)
- **Interprétation clinique détaillée** — justification de la dose paragraphe par paragraphe :
  - Contexte clinique (DFG, stade KDIGO)
  - Analyse C0 résiduel et calcul PK
  - Application du plafond néphroprotecteur avec références bibliographiques
  - Contrainte hyperkaliémie si applicable
  - Conclusion posologique
- Raisonnement méthodologique (4 étapes avec formules)
- Tableau historique de tous les bilans
- Graphiques d'évolution (DFG, C0, dose, K⁺) dès le 2e bilan

### Suivi longitudinal
- Enregistrement de chaque bilan avec horodatage
- Graphiques Plotly interactifs (thème sombre) : DFG, C0, dose recommandée, kaliémie
- Bandes de référence visuelles (zone thérapeutique C0, normokaliémie)

### Ionogramme
- Interprétation natrémie (Na⁺) et kaliémie (K⁺)
- Alertes cliniques graduées (normale → urgence métabolique)
- Intégration dans la décision posologique

---

## Bases scientifiques

| Référence | Contribution dans l'outil |
|---|---|
| Staatz & Tett, *Clin Pharmacokinet* 2004 | Ajustement PK proportionnel (r C0/AUC = 0,89) |
| Ojo et al., *NEJM* 2003 (n = 69 321) | Plafond rénal 0,1 mg/kg — 16,5 % IRC sévère à 5 ans sous CNI |
| Ekberg et al. SYMPHONY, *NEJM* 2007 (n = 1 645) | Facteurs DFG — +8,3 mL/min si CNI réduit |
| Naesens et al., *CJASN* 2009 | Néphrotoxicité dose-dépendante des CNI |
| Kobashigawa et al. ISHLT, *J Heart Lung Transplant* 2016 | Cibles C0 par phase post-greffe cardiaque |
| Tumlin et al., *Am J Kidney Dis* 1996 | Hyperkaliémie induite par CNI — mécanisme aldostérone-like |
| Cockcroft & Gault, *Nephron* 1976 | Formule d'estimation du DFG |

---

## Installation

```bash
git clone https://github.com/mamadoulaminetall/medflow-posologie.git
cd medflow-posologie
pip install -r requirements.txt
streamlit run app.py
```

### Dépendances

```
streamlit>=1.30.0
fpdf2>=2.7.9
matplotlib>=3.7.0
plotly>=5.18.0
```

> SQLite est inclus dans la bibliothèque standard Python (aucune installation supplémentaire).

---

## Formule Cockcroft-Gault

```
DFG (mL/min) = ((140 − âge) × poids × F) / (0,815 × créatinine µmol/L)

F = 1,00 (Homme)  |  F = 0,85 (Femme)
```

---

## Structure du projet

```
medflow-posologie/
├── app.py            # Application Streamlit (calculs, PDF, historique)
├── requirements.txt  # Dépendances Python
├── patients.db       # Base SQLite locale (générée automatiquement, non versionnée)
└── README.md
```

---

## Déploiement Streamlit Cloud

1. Connecter le dépôt sur [share.streamlit.io](https://share.streamlit.io)
2. Point d'entrée : `app.py`
3. Déploiement automatique à chaque `git push`

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
