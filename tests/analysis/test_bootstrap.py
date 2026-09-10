"""Block bootstrap — DOCTRINE §7.2.

Dai kuu si "code inaendesha" bali **`p-value` ina ukubwa sahihi**: chini ya
`H0`, `p < 0.05` inapaswa kutokea takribani 5% ya mara. Kipimo hicho ndicho
kinachotofautisha kipimo na mapambo.

Na dai la pili: mfululizo **tegemezi** unapaswa kutoa `p` kubwa kuliko ile ya
t-test, kwa sababu t-test inadhania uhuru usiokuwepo. Kama haitoi, block
bootstrap haifanyi kazi yake.
"""

from __future__ import annotations

import math

import numpy as np
import pytest

from src.analysis import bootstrap as BS


def _ar1(n, rho, sd=1.0, seed=0):
    """Mfululizo wenye mfululizo wa lag-1 — kama P&L ya siku halisi."""
    rng = np.random.default_rng(seed)
    x = np.empty(n)
    x[0] = rng.normal(0, sd)
    for t in range(1, n):
        x[t] = rho * x[t - 1] + rng.normal(0, sd * math.sqrt(1 - rho ** 2))
    return x


# ===========================================================================
# Urefu wa kipande
# ===========================================================================


def test_kipande_kinakua_MFULULIZO_ukiongezeka():
    """Ndicho kiini cha Politis–White: urefu unatoka kwenye data, si kwa kubuni."""
    fupi = BS.optimal_block_length(_ar1(2000, 0.0, seed=1))
    refu = BS.optimal_block_length(_ar1(2000, 0.9, seed=1))
    assert refu > fupi


def test_kipande_hakishuki_chini_ya_SIKU_21():
    """Mzunguko wa mwisho wa mwezi lazima utoshe ndani ya kipande kimoja."""
    huru = BS.optimal_block_length(_ar1(2000, 0.0, seed=3))
    assert huru == BS.MIN_BLOCK_DAYS


def test_kipande_hakizidi_robo_ya_sampuli():
    """Kipande kirefu mno kingetoa resamples zinazojirudia."""
    x = _ar1(200, 0.98, seed=5)
    assert BS.optimal_block_length(x) <= max(BS.MIN_BLOCK_DAYS, int(200 * 0.25))


def test_mfululizo_usiobadilika_unarudisha_kikomo_cha_chini():
    assert BS.optimal_block_length(np.zeros(500)) == BS.MIN_BLOCK_DAYS


def test_pointi_chache_mno_zinalipuka():
    with pytest.raises(BS.BootstrapError, match="chache"):
        BS.optimal_block_length([1.0, 2.0, 3.0])


# ===========================================================================
# Ukubwa wa `p` — dai kuu
# ===========================================================================


@pytest.mark.parametrize("rho", [0.0, 0.5])
def test_kiwango_cha_kukosea_ni_karibu_5_asilimia(rho):
    """Chini ya `H0` (wastani = 0), `p < 0.05` inatokea ~5% ya mara.

    Hii ndiyo inayofanya `p` iwe kipimo. Bila hii, namba ni mapambo.
    """
    walipita = 0
    N = 120
    for s in range(N):
        x = _ar1(600, rho, seed=1000 + s)
        r = BS.test_mean_positive(x, B=200, seed=s)
        walipita += int(r.p_value < 0.05)
    kiwango = walipita / N
    assert 0.01 <= kiwango <= 0.12, kiwango


def test_edge_halisi_INAONEKANA():
    """Nguvu: mfululizo wenye wastani chanya dhahiri unapaswa kupita."""
    x = _ar1(600, 0.3, seed=7) * 0.5 + 0.30
    r = BS.test_mean_positive(x, B=1000, seed=1)
    assert r.p_value < 0.01
    assert r.mean > 0


def test_edge_HASI_haipiti():
    x = _ar1(600, 0.3, seed=9) * 0.5 - 0.30
    assert BS.test_mean_positive(x, B=500, seed=1).p_value > 0.9


def test_p_HAIWEZI_kuwa_sifuri():
    """Fomu ya `(k+1)/(B+1)` — ile ile ya §9.8."""
    x = np.full(500, 5.0) + _ar1(500, 0.0, seed=2) * 1e-6
    r = BS.test_mean_positive(x, B=200, seed=1)
    assert r.p_value == pytest.approx(1 / 201)
    assert r.p_value == r.resolution


# ===========================================================================
# Mfululizo unaadhibiwa — sababu ya kutumia block bootstrap
# ===========================================================================


def test_mfululizo_tegemezi_unatoa_p_KUBWA_kuliko_t_test():
    """t-test inadhania uhuru. Ikikosea, `p` inakuwa ndogo kuliko inavyostahili.

    Hii ndiyo sababu nzima ya block bootstrap. Kama haiadhibu utegemezi,
    haifanyi kazi yake.
    """
    muhimu = []           # pale t-test inaposema "muhimu"
    boot_ikakataa = 0
    for s in range(40):
        x = _ar1(400, 0.85, seed=500 + s) * 0.4 + 0.05
        boot = BS.test_mean_positive(x, B=400, seed=s).p_value

        # `p` ya upande mmoja ya t-test. n=400, kwa hiyo t ≈ z na `erfc`
        # inatosha — hakuna haja ya jedwali la t.
        t = x.mean() / (x.std(ddof=1) / math.sqrt(x.size))
        p_t = 0.5 * math.erfc(t / math.sqrt(2.0))

        if p_t < 0.10:
            muhimu.append((round(p_t, 4), round(boot, 4)))
            boot_ikakataa += int(boot >= 0.05)

    assert len(muhimu) >= 20, "jaribio halina kesi za kutosha"
    # Dai kali: KILA mara t-test inaposema "muhimu", bootstrap inatoa `p`
    # KUBWA zaidi. Kipimo: 27/27 (2026-09-08).
    assert all(boot > p_t for p_t, boot in muhimu), muhimu
    # Na mara nyingi bootstrap inakataa kabisa kile t-test ilichokubali.
    assert boot_ikakataa >= len(muhimu) // 3, (boot_ikakataa, muhimu)


def test_kipande_kilichotolewa_kinatumika():
    x = _ar1(300, 0.5, seed=4)
    assert BS.test_mean_positive(x, B=200, seed=1, block=40).block == 40


# ===========================================================================
# Kuzalishika upya na ulinzi
# ===========================================================================


def test_seed_ile_ile_inatoa_jibu_LILE_LILE():
    x = _ar1(400, 0.4, seed=11)
    a = BS.test_mean_positive(x, B=300, seed=5)
    b = BS.test_mean_positive(x, B=300, seed=5)
    assert a.p_value == b.p_value and a.ci_low == b.ci_low


def test_seed_TOFAUTI_inatoa_jibu_linalokaribiana():
    x = _ar1(400, 0.4, seed=11) + 0.1
    a = BS.test_mean_positive(x, B=2000, seed=5).p_value
    b = BS.test_mean_positive(x, B=2000, seed=6).p_value
    assert abs(a - b) < 0.03


def test_CI_inazunguka_wastani():
    x = _ar1(500, 0.3, seed=13) + 0.2
    r = BS.test_mean_positive(x, B=500, seed=1)
    assert r.ci_low < r.mean < r.ci_high


def test_B_ndogo_mno_inalipuka():
    """Azimio la `p` ni `1/(B+1)`; B=50 lingetoa 0.02 pekee."""
    with pytest.raises(BS.BootstrapError, match="azimio"):
        BS.test_mean_positive(_ar1(200, 0.0), B=50)


def test_siku_chache_mno_zinalipuka():
    with pytest.raises(BS.BootstrapError, match="chache"):
        BS.test_mean_positive(np.array([1.0, 2.0]), B=200)


def test_azimio_linaripotiwa():
    """§ mpango: B=1,000 kwa maendeleo, 10,000 kwa uthibitisho."""
    r = BS.test_mean_positive(_ar1(300, 0.2, seed=1), B=BS.B_DEVELOPMENT, seed=1)
    assert r.resolution == pytest.approx(1 / (BS.B_DEVELOPMENT + 1))
    assert "azimio" in r.render()
