# 💊 MedFlow Posologie

**Calculateur d'ajustement posologique selon la fonction rénale — propulsé par MedFlow AI**

[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://medflow-posologie.streamlit.app)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-3b82f6.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-10b981.svg)](LICENSE)

---

## Présentation

**MedFlow Posologie** est un outil d'aide à la prescription destiné aux cliniciens. Il calcule le DFG en temps réel (formule de Cockcroft-Gault) et fournit, pour chaque médicament sélectionné, la dose adaptée au stade d'insuffisance rénale chronique du patient, avec les mises en garde cliniques correspondantes.

Conçu pour une utilisation rapide au lit du patient ou lors d'une consultation, sans inscription ni connexion.

---

## Médicaments disponibles

| Catégorie | Médicaments |
|---|---|
| **Immunosuppresseurs (greffe)** | Tacrolimus / Prograf — greffe cardiaque, greffe rénale |
| **Antidiabétiques** | Metformine |
| **Antibiotiques** | Amoxicilline, Amoxicilline-Clavulanate, Ciprofloxacine, Cotrimoxazole (TMP-SMX) |
| **Antiépileptiques / Neuropathiques** | Gabapentine, Prégabaline |
| **Cardiovasculaires** | Ramipril (IEC), Atenolol (BB), Digoxine |
| **Anticoagulants** | Enoxaparine (HBPM curatif), Dabigatran (FA), Rivaroxaban (FA) |
| **Antiviraux** | Aciclovir IV |

> Nouvelles molécules ajoutées régulièrement. Contributions bienvenues via Pull Request.

---

## Fonctionnalités

- **Calcul DFG automatique** — Formule de Cockcroft-Gault à partir de l'âge, du poids, du sexe et de la créatininémie (µmol/L)
- **Stade IRC** — Classification KDIGO G1 à G5 avec code couleur
- **Recommandation posologique** — Palier actif mis en évidence parmi tous les paliers définis
- **Niveaux trough cibles** — Pour le tacrolimus : cibles résiduelles par phase post-greffe (M0–M3, M3–M12, > 1 an)
- **Alertes interactions** — Principales interactions médicamenteuses signalées (CYP3A4, AINS, etc.)
- **Références intégrées** — HAS, KDIGO, ESC, EMA, Vidal/SPC pour chaque molécule
- **Interface sombre optimisée** — Confort visuel en environnement de travail clinique

---

## Démarrage rapide

### Prérequis

```bash
python >= 3.9
```

### Installation

```bash
git clone https://github.com/mamadoulaminetall/medflow-posologie.git
cd medflow-posologie
pip install -r requirements.txt
streamlit run app.py
```

### Dépendances

```
streamlit>=1.30.0
```

---

## Déploiement Streamlit Cloud

1. Forker ce dépôt
2. Connecter à [share.streamlit.io](https://share.streamlit.io)
3. Sélectionner `app.py` comme point d'entrée
4. Déployer en un clic

---

## Formule Cockcroft-Gault

```
DFG (mL/min) = ((140 − âge) × poids × F) / (0.815 × créatinine µmol/L)

F = 1.00 (Homme) | 0.85 (Femme)
```

> Formule recommandée par la HAS et les sociétés savantes françaises pour l'adaptation posologique en pratique clinique courante.

---

## Avertissement médical

> Cet outil est une **aide à la décision clinique**. Il ne remplace pas le jugement du praticien, la lecture des RCP officiels, ni la prise en compte du contexte individuel du patient (hépatopathie, poids extrême, grossesse, interactions médicamenteuses multiples).
>
> **Usage professionnel médical exclusif.**

---

## Structure du projet

```
medflow-posologie/
├── app.py                  # Application principale Streamlit
├── requirements.txt        # Dépendances Python
├── README.md               # Ce fichier
└── LICENSE                 # Licence MIT
```

---

## Roadmap

- [ ] Ajustement hépatique (score Child-Pugh)
- [ ] Mode multi-médicaments (interactions croisées)
- [ ] Export PDF de la fiche patient
- [ ] API REST (intégration SIH / DPI)
- [ ] Version anglaise

---

## Auteur

**Dr. Mamadou Lamine TALL, PhD**
Bioinformatique & Intelligence Artificielle Médicale

- GitHub : [@mamadoulaminetall](https://github.com/mamadoulaminetall)
- Email : mamadoulaminetallgithub@gmail.com
- Plateforme : [MedFlow AI](https://medflowailanding.streamlit.app)

---

## Licence

MIT License — libre d'utilisation, modification et redistribution avec attribution.

---

*Fait partie de la suite **MedFlow AI** — outils IA pour cliniciens.*
