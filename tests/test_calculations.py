"""Tests unitaires — calculations.py · MedFlow AI Tacrolimus"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
from calculations import (
    calc_dfg, get_stade, arrondir_05,
    interp_sodium, interp_potassium,
    recommander_tacrolimus, delta_str,
    correct_c0_hematocrit, build_clinical_explanation,
)


# ── calc_dfg ──────────────────────────────────────────────────────────────────
class TestCalcDfg:
    def test_homme(self):
        dfg = calc_dfg(55, 70, "Homme", 120)
        assert dfg == pytest.approx(((140 - 55) * 70 * 1.0) / (0.815 * 120), abs=0.2)

    def test_femme(self):
        dfg_f = calc_dfg(55, 70, "Femme", 120)
        dfg_m = calc_dfg(55, 70, "Homme", 120)
        assert dfg_f == pytest.approx(dfg_m * 0.85, abs=0.2)

    def test_minimum_zero(self):
        assert calc_dfg(140, 40, "Homme", 2000) >= 0.0

    def test_high_creatinine_low_dfg(self):
        assert calc_dfg(60, 70, "Homme", 800) < 15


# ── get_stade ─────────────────────────────────────────────────────────────────
class TestGetStade:
    @pytest.mark.parametrize("dfg,stade", [
        (95, "G1"), (75, "G2"), (50, "G3a"), (35, "G3b"), (20, "G4"), (10, "G5"),
    ])
    def test_stades(self, dfg, stade):
        s, _, _ = get_stade(dfg)
        assert s == stade

    def test_returns_color(self):
        _, _, color = get_stade(90)
        assert color.startswith("#")


# ── arrondir_05 ───────────────────────────────────────────────────────────────
class TestArrondir05:
    @pytest.mark.parametrize("val,expected", [
        (2.3, 2.5), (2.8, 3.0), (1.0, 1.0), (0.8, 1.0), (4.2, 4.0),
    ])
    def test_arrondi(self, val, expected):
        assert arrondir_05(val) == expected


# ── interp_sodium ─────────────────────────────────────────────────────────────
class TestInterpSodium:
    def test_normal(self):
        label, _, _, urgent = interp_sodium(140)
        assert label == "Normal"
        assert not urgent

    def test_hypo_severe(self):
        _, _, _, urgent = interp_sodium(120)
        assert urgent

    def test_hyper(self):
        label, _, _, _ = interp_sodium(150)
        assert "Hyper" in label


# ── interp_potassium ──────────────────────────────────────────────────────────
class TestInterpPotassium:
    def test_normal(self):
        label, _, _, urgent = interp_potassium(4.5)
        assert label == "Normal"
        assert not urgent

    def test_urgence(self):
        _, _, _, urgent = interp_potassium(6.5)
        assert urgent

    def test_hypokaliemie_severe(self):
        label, _, _, urgent = interp_potassium(2.8)
        assert "sévère" in label
        assert urgent


# ── recommander_tacrolimus ────────────────────────────────────────────────────
class TestRecommander:
    def test_dose_pk_normal(self):
        dose_rec, dose_pk, plafond, fr = recommander_tacrolimus(5.0, 10, 10, 15, 80, 70)
        assert dose_pk == pytest.approx(arrondir_05(5.0 * (12.5 / 10)), abs=0.1)
        assert fr == 1.0

    def test_plafond_applique(self):
        # Poids léger + DFG bas → plafond très bas
        dose_rec, dose_pk, plafond, fr = recommander_tacrolimus(10.0, 5, 10, 15, 20, 40)
        assert dose_rec <= plafond

    def test_k_eleve_plafond_dose_act(self):
        dose_rec, _, _, _ = recommander_tacrolimus(5.0, 12, 10, 15, 80, 70, k_eleve=True)
        assert dose_rec <= 5.0

    def test_minimum_05(self):
        dose_rec, _, _, _ = recommander_tacrolimus(0.5, 20, 5, 10, 10, 30)
        assert dose_rec >= 0.5

    def test_facteur_dfg(self):
        _, _, _, fr_g1  = recommander_tacrolimus(5, 10, 10, 15, 90, 70)
        _, _, _, fr_g3a = recommander_tacrolimus(5, 10, 10, 15, 50, 70)
        _, _, _, fr_g5  = recommander_tacrolimus(5, 10, 10, 15, 10, 70)
        assert fr_g1  == 1.00
        assert fr_g3a == 0.90
        assert fr_g5  == 0.50


# ── delta_str ─────────────────────────────────────────────────────────────────
class TestDeltaStr:
    def test_augmentation(self):
        label, color = delta_str(6.0, 5.0)
        assert label == "+20.0 %"
        assert color == "#10b981"

    def test_reduction_forte(self):
        label, color = delta_str(4.0, 5.0)
        assert "-" in label
        assert color == "#ef4444"

    def test_zero_old(self):
        label, _ = delta_str(5.0, 0)
        assert label is None


# ── correct_c0_hematocrit ─────────────────────────────────────────────────────
class TestCorrectC0Hematocrit:
    def test_ht_normal(self):
        # Ht=0.45 → correction nulle
        c0 = correct_c0_hematocrit(10.0, 0.45)
        assert c0 == pytest.approx(10.0, abs=0.01)

    def test_ht_bas_augmente_c0(self):
        # Ht < 0.45 → C0 corrigé > C0 mesuré
        c0_corr = correct_c0_hematocrit(10.0, 0.30)
        assert c0_corr > 10.0

    def test_ht_haut_diminue_c0(self):
        # Ht > 0.45 → C0 corrigé < C0 mesuré
        c0_corr = correct_c0_hematocrit(10.0, 0.60)
        assert c0_corr < 10.0

    def test_ht_zero_retourne_c0(self):
        assert correct_c0_hematocrit(10.0, 0) == 10.0

    def test_ht_invalide_retourne_c0(self):
        assert correct_c0_hematocrit(10.0, 1.5) == 10.0


# ── build_clinical_explanation ────────────────────────────────────────────────
class TestBuildClinicalExplanation:
    def _call(self, c0=12, c0_statut="thérapeutique", k_val=4.5, k_eleve=False,
              dose_pk=5.0, dose_rec=5.0, plafond=7.0):
        return build_clinical_explanation(
            age=55, sexe="Homme", poids=70, dfg=75, stade="G2",
            stade_desc="Légèrement ↓",
            phase_label="M3 – M12  (maintenance)", c0=c0,
            c0_statut=c0_statut, t_min=8, t_max=12,
            dose_act=5.0, dose_rec=dose_rec, dose_pk=dose_pk,
            plafond=plafond, fr=1.0, k_val=k_val, k_eleve=k_eleve,
        )

    def test_retourne_liste(self):
        items = self._call()
        assert isinstance(items, list)
        assert len(items) >= 3

    def test_toujours_contexte_et_conclusion(self):
        items = self._call()
        titres = [t for t, _ in items]
        assert any("Contexte" in t for t in titres)
        assert any("Conclusion" in t for t in titres)

    def test_hyperkaliemie_ajoute_item(self):
        items_normal = self._call(k_eleve=False)
        items_k      = self._call(k_val=6.0, k_eleve=True)
        assert len(items_k) > len(items_normal)

    def test_texte_non_vide(self):
        for titre, corps in self._call():
            assert len(titre) > 0
            assert len(corps) > 20
