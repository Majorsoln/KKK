"""Takwimu ndogo — `src/stats.py`.

Hesabu iliyoandikwa kwa mkono badala ya `scipy` inahitaji ushahidi kwamba ni
sahihi. Ushahidi hapa ni **jedwali la t lililochapishwa**: thamani zilizoko
kwenye kila kitabu cha takwimu, si zilizotoka kwenye code hii yenyewe.
"""

from __future__ import annotations

import math

import pytest

from src import stats as ST

# Jedwali la Student-t, upande MMOJA, α = 0.05. Chanzo: jedwali la kawaida.
JEDWALI = {
    1: 6.314, 2: 2.920, 3: 2.353, 4: 2.132, 5: 2.015,
    10: 1.812, 15: 1.753, 20: 1.725, 25: 1.708, 30: 1.697,
    40: 1.684, 60: 1.671, 120: 1.658,
}


# ===========================================================================
# `t_one_sided` dhidi ya jedwali
# ===========================================================================


@pytest.mark.parametrize("df,tarajio", sorted(JEDWALI.items()))
def test_t_inalingana_na_jedwali_lililochapishwa(df, tarajio):
    assert ST.t_one_sided(df) == pytest.approx(tarajio, abs=0.001)


def test_t_ya_0_99_pia_inalingana():
    """Kiwango kingine kinathibitisha kuwa ni CDF, si jedwali lililopachikwa."""
    assert ST.t_one_sided(10, 0.99) == pytest.approx(2.764, abs=0.001)
    assert ST.t_one_sided(30, 0.99) == pytest.approx(2.457, abs=0.001)


def test_t_inapungua_df_inapoongezeka():
    thamani = [ST.t_one_sided(df) for df in (1, 2, 5, 10, 30, 100, 1000)]
    assert thamani == sorted(thamani, reverse=True)


def test_t_inakaribia_z_kwa_df_kubwa():
    """`df → ∞` inatoa quantile ya normal, 1.6449."""
    assert ST.t_one_sided(100_000) == pytest.approx(1.6449, abs=0.001)


def test_df_sifuri_inalipuka():
    """Uchunguzi mmoja hauna standard error — si kosa la kuepukika, ni ufafanuzi."""
    with pytest.raises(ST.StatsError, match="df"):
        ST.t_one_sided(0)


def test_p_nje_ya_masafa_inalipuka():
    with pytest.raises(ST.StatsError, match="p"):
        ST.t_one_sided(10, 0.4)


# ===========================================================================
# `mean_lower_bound`
# ===========================================================================


def test_ukingo_ni_chini_ya_wastani():
    x = [1.0, 2.0, 3.0, 4.0, 5.0]
    assert ST.mean_lower_bound(x) < sum(x) / len(x)


def test_ukingo_unalingana_na_hesabu_ya_mkono():
    import numpy as np

    x = [10.0, 12.0, 8.0, 14.0, 11.0]
    a = np.asarray(x)
    tarajio = a.mean() - ST.t_one_sided(4) * a.std(ddof=1) / math.sqrt(5)
    assert ST.mean_lower_bound(x) == pytest.approx(tarajio)


def test_sampuli_MOJA_haina_ukingo():
    """Si sifuri na si wastani wenyewe — zote mbili zingekuwa jibu lililobuniwa."""
    assert math.isnan(ST.mean_lower_bound([7.0]))
    assert math.isnan(ST.mean_lower_bound([]))


def test_sampuli_isiyobadilika_ina_ukingo_sawa_na_wastani():
    """`s = 0`: hakuna kutokuwa na uhakika kunakoweza kupimwa."""
    assert ST.mean_lower_bound([3.0] * 8) == pytest.approx(3.0)


def test_sampuli_kubwa_ina_adhabu_NDOGO_kuliko_ndogo():
    """Ndicho kiini: `2×` ile ile, lakini sampuli ndogo inaadhibiwa.

    Mtawanyiko ni ule ule; kinachotofautiana ni `n` pekee.
    """
    import numpy as np

    rng = np.random.default_rng(4)
    ndogo = rng.normal(10.0, 5.0, 3)
    kubwa = np.concatenate([ndogo, rng.normal(10.0, 5.0, 297)])

    adhabu_ndogo = ndogo.mean() - ST.mean_lower_bound(ndogo)
    adhabu_kubwa = kubwa.mean() - ST.mean_lower_bound(kubwa)
    assert adhabu_ndogo > 5 * adhabu_kubwa


def test_NaN_zinaondolewa_kabla_ya_hesabu():
    safi = ST.mean_lower_bound([1.0, 2.0, 3.0])
    na_nan = ST.mean_lower_bound([1.0, float("nan"), 2.0, 3.0])
    assert na_nan == pytest.approx(safi)
