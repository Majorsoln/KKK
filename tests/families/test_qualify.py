"""Malango matatu ya sifa — DOCTRINE §6.

Dai kuu si "function inarudisha bool" bali kwamba lango linakataa vitu
vinavyostahili kukataliwa **kwa hesabu iliyoandikwa mbele**, na kwamba
kukataa kwake hakugharimu α wakati kukubali kunagharimu.
"""

from __future__ import annotations

import pytest

from src.families import f0
from src.families.qualify import (
    COST_BUDGET,
    Z_STAR,
    QualifyError,
    qualify,
    required_events,
    table,
)


def sifa(**kw):
    msingi = dict(
        family=f0.FAMILY, symbol=f0.SYMBOL,
        mechanism_ok=True, mechanism_note="saa za Ulaya na Marekani",
        cost_pips=1.6, sigma_pips=38.0,
        n_events=1924, sharpe_per_event=0.09,
    )
    return qualify(**{**msingi, **kw})


# ===========================================================================
# 6.1 — sababu
# ===========================================================================


def test_bila_mekanizimu_symbol_HAIINGII_hata_ikiwa_nafuu():
    """Lango la kwanza si la hesabu. Gharama nafuu si sababu ya kuingiza
    symbol kwenye familia ambayo mekanizimu wake haiihusu."""
    q = sifa(mechanism_ok=False, mechanism_note="EURGBP haina saa za dola",
             cost_pips=0.1, sigma_pips=100.0)
    assert not q.passed and q.failed == ["sababu"]


# ===========================================================================
# 6.2 — gharama
# ===========================================================================


def test_gharama_inayozidi_asilimia_NANE_ya_sigma_inakataliwa():
    q = sifa(cost_pips=4.0, sigma_pips=38.0)          # 10.5%
    assert not q.passed and q.failed == ["gharama"]


def test_gharama_ya_F0_kwa_EURUSD_INAPITA():
    """spread 1.6p kwenye dirisha lenye σ ≈ 38p ni 4.2% — ndani ya bajeti."""
    q = sifa()
    gharama = [g for g in q.gates if g.name == "gharama"][0]
    assert gharama.measured == pytest.approx(1.6 / 38.0)
    assert gharama.measured < COST_BUDGET
    assert q.passed


def test_sigma_ya_SIKU_ingepitisha_kila_kitu_kimya():
    """Ndiyo maana lango linadai σ ya **dirisha la kushikilia**. σ ya siku ni
    kubwa mara mbili au tatu, na kila symbol ingepita bila kupimwa."""
    dirisha = sifa(cost_pips=4.0, sigma_pips=38.0)
    siku_nzima = sifa(cost_pips=4.0, sigma_pips=110.0)
    assert not dirisha.passed and siku_nzima.passed


def test_sigma_sifuri_INALIPUKA():
    with pytest.raises(QualifyError, match="σ"):
        sifa(sigma_pips=0.0)


# ===========================================================================
# 6.3 — mzunguko
# ===========================================================================


def test_matukio_yanayohitajika_ni_t_juu_ya_s_MRABA():
    assert required_events(0.09) == 975
    assert required_events(0.18) == 244            # s mara mbili → n robo
    assert required_events(0.09, z_star=1.645) == 335


def test_F0_ina_matukio_ya_KUTOSHA():
    q = sifa()
    mz = [g for g in q.gates if g.name == "mzunguko"][0]
    assert mz.passed and mz.measured == 1924 and mz.limit == 975


def test_familia_isiyoweza_KUFIKIA_kizingiti_inakataliwa():
    """Kufeli hapa si "hakuna edge" — ni "hakuna jibu". Ndilo lengo (§12)."""
    q = sifa(n_events=99, sharpe_per_event=0.09)
    assert not q.passed and q.failed == ["mzunguko"]


def test_F1_yenye_matukio_99_inahitaji_Sharpe_kwa_tukio_ya_0_28():
    """`(2.81/s)² ≤ 99` → `s ≥ 0.282`. Ndiyo gharama halisi ya familia ya mara
    moja kwa mwezi, ikiwa namba."""
    assert required_events(0.283) <= 99
    assert required_events(0.281) > 99


def test_Sharpe_isiyo_chanya_INALIPUKA():
    with pytest.raises(QualifyError, match="Sharpe"):
        required_events(0.0)


# ===========================================================================
# Jedwali
# ===========================================================================


def test_jedwali_linaonyesha_ndani_na_nje():
    zote = [sifa(), sifa(symbol="EURGBP", mechanism_ok=False,
                         mechanism_note="hakuna saa za dola")]
    t = table(zote)
    assert "EURUSD" in t and "INAINGIA" in t
    assert "EURGBP" in t and "HAIINGII" in t


def test_z_star_ni_ile_ya_MAJARIBIO_NANE():
    """§9: 0.020/8 = 0.0025 → z ≈ 2.81. Ikibadilika, bajeti ya α imebadilika."""
    assert Z_STAR == 2.81
