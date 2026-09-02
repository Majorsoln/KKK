"""Kipimo cha null — DOCTRINE §9.2, §9.7.

Kipimo hiki ndicho kingezuia saa 30 zilizotumika kupima sakafu ya soko
lisilokuwepo (§9.7). Kikiwa na kasoro, kingerudisha kosa lile lile likiwa na
ujasiri.
"""

from __future__ import annotations

import math

import pytest

from src.validation import null_check as NC
from src.validation import surrogates as S


class _Spec:
    symbol = "EURUSD"
    timeframe = "H1"
    n_candidates = 200


class _Out:
    """`SearchResult` ya bandia — kipimo hakiendeshi pipeline nzima."""

    def __init__(self, mamlaka, n_passed=3, **kw):
        self._m = {NC.MAMLAKA: mamlaka, "net_pips_month": mamlaka * 10_000,
                   "sharpe": mamlaka * 100, "profitable_month_fraction": 0.1,
                   "profit_factor": 1.5, "max_drawdown": 400.0}
        self._m.update(kw)
        self.n_passed_economics = n_passed

    def metrics(self):
        return dict(self._m)


def _compare(halisi, bandia, **kw) -> NC.Comparison:
    """`compare()` ikiwa na utafutaji wa bandia — halisi kwanza, kisha surrogate."""
    thamani = [halisi, *bandia]
    hatua = {"i": 0}

    def tafuta(_frame):
        v = thamani[hatua["i"]]
        hatua["i"] += 1
        return _Out(v) if v == v else _Out(float("nan"), n_passed=0)

    n_fam = len(kw.pop("families", S.FAMILIES))
    n_seeds = len(bandia) // n_fam if n_fam and len(bandia) % n_fam == 0 else 1
    return NC.compare(_bars(), _Spec(), cfg_risk=None, seed=1,
                      n_surrogate_seeds=n_seeds, run_search=tafuta, **kw)


def _bars(n=200):
    import numpy as np
    import pandas as pd

    close = 1.10 + np.cumsum(np.random.default_rng(1).normal(0, 3e-4, n))
    return pd.DataFrame({
        "open": close, "high": close + 5e-4, "low": close - 5e-4, "close": close,
        "spread_p50": 1.0,
    }, index=pd.date_range("2020-01-01", periods=n, freq="1h", tz="UTC"))


# ===========================================================================
# Percentile ndiyo hukumu
# ===========================================================================


def test_halisi_ikizidi_ZOTE_ni_MUUNDO():
    """Ndicho kinachotafutwa: soko lina kitu ambacho null haina."""
    c = _compare(0.05, [0.01, 0.02, 0.01, 0.02, 0.01, 0.02])
    assert c.percentile == 1.0
    assert c.hukumu == NC.MUUNDO


def test_halisi_ikizidiwa_na_ZOTE_ni_NULL_RAHISI():
    """Ndiyo kasoro ya §9.7: sakafu ya soko lisilokuwepo."""
    c = _compare(0.001, [0.01, 0.02, 0.01, 0.02, 0.01, 0.02])
    assert c.percentile == 0.0
    assert c.hukumu == NC.RAHISI


def test_halisi_katikati_ni_HAITOFAUTIKI():
    """Namba halisi za EURUSD H1 baada ya kurekebisha `block_resample`."""
    c = _compare(0.0035, [0.0076, 0.0024, 0.0048, 0.0068, 0.0003, 0.0050])
    assert c.percentile == pytest.approx(2 / 6)
    assert c.hukumu == NC.HAITOFAUTIKI


def test_azimio_linategemea_IDADI_ya_surrogate():
    """Jibu bila azimio lake si jibu.

    Kwa surrogate 3, "100%" ina nafasi ya 25% ya kutokea kwa bahati — dokezo,
    si ushahidi.
    """
    chache = _compare(0.05, [0.01, 0.01, 0.01])
    nyingi = _compare(0.05, [0.01] * 9)
    assert chache.azimio == pytest.approx(0.25)
    assert nyingi.azimio == pytest.approx(0.10)
    assert chache.azimio > nyingi.azimio


def test_bila_mshindi_wa_halisi_ni_HAKUNA_ULINGANISHO():
    """Hitimisho kutoka kwenye kutokuwepo kwa data ni kosa baya kuliko ukimya."""
    c = _compare(float("nan"), [0.01, 0.02, 0.01, 0.02, 0.01, 0.02])
    assert math.isnan(c.percentile)
    assert c.hukumu == NC.HAKUNA


def test_bila_mshindi_wa_bandia_ni_HAKUNA_ULINGANISHO():
    c = _compare(0.05, [float("nan")] * 6)
    assert c.hukumu == NC.HAKUNA
    assert c.n_bandia == 0


def test_surrogate_zisizo_na_mshindi_zinarukwa_si_kuhesabiwa_sifuri():
    """Surrogate isiyo na mshindi haikupata sifuri — haikupata chochote."""
    c = _compare(0.05, [0.01, float("nan"), 0.02, float("nan"), 0.01, 0.02])
    assert c.n_bandia == 4
    assert c.percentile == 1.0


# ===========================================================================
# Uwiano ni TAARIFA, si hukumu
# ===========================================================================


def test_uwiano_unaripotiwa_lakini_hauamui():
    c = _compare(0.0035, [0.0076, 0.0024, 0.0048, 0.0068, 0.0003, 0.0050])
    uwiano = c.uwiano()
    assert uwiano[NC.MAMLAKA] > 1.0, "bandia ni kubwa kwa wastani"
    assert c.hukumu == NC.HAITOFAUTIKI, "lakini hukumu inatoka kwa percentile"


# ===========================================================================
# Kupanga symbols — ndilo linaloamua wapi pa kutafuta
# ===========================================================================


def _kwa_symbol(jina: str, pct_halisi: float, bandia: list[float]) -> NC.Comparison:
    return NC.Comparison(
        symbol=jina, timeframe="H1", n_bars=1000, n_candidates=200, seed=1,
        halisi=NC.Run(jina="HALISI", n_passed=3,
                      metrics={NC.MAMLAKA: pct_halisi}),
        bandia=[NC.Run(jina=f"b{i}", n_passed=1, metrics={NC.MAMLAKA: v})
                for i, v in enumerate(bandia)],
    )


def test_symbols_zinapangwa_kwa_percentile():
    zote = [
        _kwa_symbol("EURUSD", 0.003, [0.005, 0.006, 0.007]),   # 0%
        _kwa_symbol("XAUUSD", 0.010, [0.005, 0.006, 0.007]),   # 100%
        _kwa_symbol("GBPJPY", 0.006, [0.005, 0.006, 0.007]),   # 33%
    ]
    assert [c.symbol for c in NC.rank(zote)] == ["XAUUSD", "GBPJPY", "EURUSD"]


def test_symbol_isiyopimika_inaenda_MWISHO():
    """Si symbol iliyofeli — lakini pia si mahali pa kuanzia."""
    zote = [
        _kwa_symbol("EURUSD", float("nan"), [0.005]),
        _kwa_symbol("XAUUSD", 0.010, [0.005, 0.006, 0.007]),
    ]
    assert [c.symbol for c in NC.rank(zote)] == ["XAUUSD", "EURUSD"]


def test_jedwali_linaonyesha_p_pamoja_na_jibu():
    text = NC.render_table([_kwa_symbol("XAUUSD", 0.010, [0.005, 0.006, 0.007])])
    assert "XAUUSD" in text and "3/3" in text and "0.250" in text
    assert NC.MUUNDO in text


# ===========================================================================
# `p_value` — ushahidi, si kile kilichoonekana pekee
# ===========================================================================


def test_p_value_inatofautisha_3_kwa_3_na_6_kwa_6():
    """Zote ni 100%, lakini si ushahidi sawa."""
    chache = _kwa_symbol("A", 0.05, [0.01, 0.01, 0.01])
    nyingi = _kwa_symbol("B", 0.05, [0.01] * 6)
    assert chache.percentile == nyingi.percentile == 1.0
    assert chache.p_value == pytest.approx(0.25)
    assert nyingi.p_value == pytest.approx(1 / 7)


def test_kupanga_kunatumia_p_si_percentile():
    """Kosa la scan ya kwanza: EURCHF (3/3) iliwekwa juu ya GBPUSD (6/6)."""
    zote = [
        _kwa_symbol("EURCHF", 0.0022, [0.0019, 0.0005, 0.0006]),
        _kwa_symbol("GBPUSD", 0.0078, [0.0016, 0.0029, 0.0038,
                                       0.0018, 0.0016, 0.0013]),
    ]
    assert all(c.percentile == 1.0 for c in zote)
    assert [c.symbol for c in NC.rank(zote)] == ["GBPUSD", "EURCHF"]


def test_p_value_ya_kushindwa_kabisa_ni_moja():
    c = _kwa_symbol("A", 0.001, [0.01, 0.02, 0.03])
    assert c.p_value == pytest.approx(1.0)


def test_matarajio_kwa_bahati_yanahesabiwa():
    """§9.1 kwenye ngazi ya symbols: 12 zikipimwa, `p = 0.14` inatarajiwa 1.7."""
    zote = [_kwa_symbol(f"S{i}", 0.01, [0.02] * 6) for i in range(11)]
    zote.append(_kwa_symbol("BORA", 0.05, [0.01] * 6))
    assert NC.expected_by_chance(zote) == pytest.approx(12 / 7)


def test_matarajio_yanapuuza_zisizopimika():
    zote = [_kwa_symbol("A", 0.05, [0.01] * 6),
            _kwa_symbol("B", float("nan"), [0.01] * 6)]
    assert NC.expected_by_chance(zote) == pytest.approx(1 / 7)
