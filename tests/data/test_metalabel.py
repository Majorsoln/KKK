"""Meta-labelling — vigezo vitatu vinavyoweza KUFELI.

Somo kubwa la mradi huu: kigezo kisichoweza kufeli si kigezo. Kwa hiyo kila
lango hapa lina test inayolilazimisha lifeli, si kupita tu.
"""

from __future__ import annotations

import numpy as np
import pytest

from src.data.metalabel import (
    apply_calibration,
    decile_table,
    evaluate,
    goodness_of_fit,
    logistic_calibrate,
    reliability_slope,
    spearman,
    top_decile_fitted,
)


def _data(n: int = 20_000, strength: float = 1.0, seed: int = 0):
    """Score yenye signal `strength`, outcome ya binary, blocks kwa mwaka."""
    rng = np.random.RandomState(seed)
    score = rng.normal(0, 1, n)
    prob = 1.0 / (1.0 + np.exp(-(strength * score - 0.2)))
    outcome = (rng.uniform(size=n) < prob).astype(float)
    blocks = rng.randint(2016, 2024, n)
    return score, outcome, blocks


# ===========================================================================
# Calibration
# ===========================================================================


def test_logistic_inarudisha_parameters_zilizotengeneza_data():
    score, outcome, _ = _data(n=40_000, strength=1.3, seed=1)
    a, b = logistic_calibrate(score, outcome)
    assert a == pytest.approx(1.3, rel=0.10)
    assert b == pytest.approx(-0.2, abs=0.05)


def test_mteremko_wa_uaminifu_ni_moja_kwa_model_iliyocalibiwa():
    score, outcome, _ = _data(n=40_000, strength=1.0, seed=2)
    a, b = logistic_calibrate(score, outcome)
    slope = reliability_slope(apply_calibration(score, a, b), outcome)
    assert slope == pytest.approx(1.0, abs=0.12)


def test_mteremko_unagundua_ujasiri_wa_kupita_kiasi():
    """Probability iliyonyooshwa kuelekea 0/1 ni model yenye ujasiri wa uongo.

    Lango la EV linalolishwa probability kama hii linatoa namba inayoonekana
    kama EV lakini si.
    """
    score, outcome, _ = _data(n=40_000, strength=1.0, seed=3)
    a, b = logistic_calibrate(score, outcome)
    overconfident = apply_calibration(score, a * 3.0, b)
    assert reliability_slope(overconfident, outcome) < 0.8


# ===========================================================================
# Discrimination
# ===========================================================================


def test_deciles_zinapanda_kwa_model_yenye_signal():
    score, outcome, _ = _data(n=30_000, strength=1.2, seed=4)
    table = decile_table(score, outcome)
    assert len(table) == 10
    assert spearman(table["decile"], table["empirical"]) > 0.9


def test_score_ya_kelele_haipiti_lango_la_discrimination():
    """Ranking ya nasibu lazima ianguke. Ndilo lango lenyewe."""
    rng = np.random.RandomState(5)
    n = 20_000
    outcome = (rng.uniform(size=n) < 0.45).astype(float)
    table = decile_table(rng.normal(0, 1, n), outcome)
    assert abs(spearman(table["decile"], table["empirical"])) < 0.7


# ===========================================================================
# Kigezo cha kiuchumi
# ===========================================================================


def test_fitted_ina_nguvu_zaidi_ya_wastani_wa_decile():
    """Faida nzima ya logistic ni pooling — CI yake iwe nyembamba kuliko empirical.

    Empirical top decile ni observations ~n/10 pekee. Fitted inatumia zote.
    """
    score, outcome, blocks = _data(n=20_000, strength=1.2, seed=6)
    point, low, cutoff = top_decile_fitted(score, outcome, blocks, n_boot=60, seed=1)
    top = score >= cutoff
    empirical_se = float(np.sqrt(outcome[top].mean() * (1 - outcome[top].mean()) / top.sum()))
    assert np.isfinite(point) and np.isfinite(low)
    assert (point - low) < 3.0 * empirical_se


def test_goodness_of_fit_inakataa_uhusiano_uliolalia_kwenye_tail():
    """Logistic ikikadiria decile ya juu juu kuliko ukweli, kigezo kianguke.

    Hii ndiyo failure mode kamili ya kutumia fitted value: scores za juu
    zikiendeshwa na outliers badala ya signal, parametric inanunua CI
    nyembamba kwa kudai kitu ambacho haikupima.
    """
    score, outcome, _ = _data(n=20_000, strength=1.2, seed=7)
    a, b = logistic_calibrate(score, outcome)
    table = decile_table(score, outcome, calibration=(a, b))
    ok, _ = goodness_of_fit(table)
    assert ok, "model iliyofit vizuri lazima ipite"

    # Bapisha tail: outcome halisi ya deciles mbili za juu inashuka.
    bent = table.copy()
    bent.loc[bent.index[-2:], "empirical"] = 0.30
    bad, detail = goodness_of_fit(bent)
    assert not bad and "1 SE" in detail


# ===========================================================================
# Jaribio kamili
# ===========================================================================


def test_kifungu_cha_nguvu_kinatangaza_inconclusive_hata_matokeo_yakiwa_mazuri():
    """N_eff isipotosha, matokeo hayana maana — yakiwa mazuri au mabaya.

    Kupita kwa bahati kwenye sampuli isiyotosha ndiyo njia inayowezekana zaidi
    ya jaribio hili kuzalisha uongo wa kusadikisha.
    """
    score, outcome, blocks = _data(n=20_000, strength=1.5, seed=8)
    result = evaluate(
        score, outcome, blocks, breakeven=0.40, delta_mer=0.02,
        n_eff=1_000, n_required=3_553, n_boot=0,
    )
    assert result.inconclusive
    assert not result.passed
    assert not result.gates, "hakuna lango linalopimwa kabla ya N kuthibitishwa"


def test_signal_yenye_nguvu_inapita_malango_yote_matatu():
    score, outcome, blocks = _data(n=30_000, strength=1.4, seed=9)
    result = evaluate(
        score, outcome, blocks, breakeven=0.40, delta_mer=0.02,
        n_eff=10_168, n_required=3_553, n_boot=60,
    )
    assert result.passed, [g.to_json() for g in result.gates]
    assert {g.name for g in result.gates} == {"calibration", "discrimination", "kiuchumi"}


def test_kelele_inafeli_na_inasema_lango_lipi():
    rng = np.random.RandomState(10)
    n = 20_000
    outcome = (rng.uniform(size=n) < 0.45).astype(float)
    result = evaluate(
        rng.normal(0, 1, n), outcome, rng.randint(2016, 2024, n),
        breakeven=0.40, delta_mer=0.02, n_eff=10_168, n_required=3_553, n_boot=60,
    )
    assert not result.passed
    failed = {g.name for g in result.gates if not g.passed}
    assert "discrimination" in failed


def test_signal_dhaifu_inafeli_lango_la_kiuchumi_pekee():
    """Ranking inayofanya kazi lakini isiyofika δ_MER ni jibu tofauti na kelele.

    Tofauti hiyo ndiyo inayoamua kama tunabadilisha muundo au tunaacha kabisa.
    """
    score, outcome, blocks = _data(n=30_000, strength=0.35, seed=11)
    result = evaluate(
        score, outcome, blocks, breakeven=0.44, delta_mer=0.30,
        n_eff=10_168, n_required=3_553, n_boot=60,
    )
    assert not result.passed
    economic = next(g for g in result.gates if g.name == "kiuchumi")
    assert not economic.passed
