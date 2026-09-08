"""Udhibiti chanya — DOCTRINE §7.1, LANGO 1.

Kasoro mbili za kipimo cha muda zilipatikana hapa wakati wa ujenzi
(2026-09-08), na zote mbili zingekuwa **kimya**:

1. `astype("int64")` kwenye pandas mpya inatoa MIKROSEKUNDE. Kulinganisha na
   `timestamp() × 1e9` kulitoa mask tupu — edge iliyopandwa haikuwahi kugusa
   bei, na udhibiti ungeripoti "injini ni kipofu".
2. Kipimo kilekile kwenye muda kati ya ticks kilifanya mfululizo usisonge kati
   ya madirisha — σ ilikuwa ndogo mara kumi, na probe ingekuwa rahisi mno.

Jaribio la kwanza hapa chini linalinda dhidi ya la kwanza kwa kudai kwamba bei
**zimebadilika kweli**.
"""

from __future__ import annotations

import math
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd
import pytest

from src.analysis import control as C

UTC = ZoneInfo("UTC")
PIP = 0.0001
T0 = datetime(2021, 6, 15, 8, 0, tzinfo=UTC)


def _ticks(n=7200, mid=1.2000, spread=0.00016, start=None):
    stamps = pd.date_range(start or T0, periods=n, freq="1s", tz="UTC")
    return pd.DataFrame({"timestamp": stamps,
                         "bid": np.full(n, mid - spread / 2),
                         "ask": np.full(n, mid + spread / 2)})


def _w(hours=4, side="SELL", start=None):
    s = start or T0
    return C.Window(s, s + timedelta(hours=hours), side)


# ===========================================================================
# Kupanda kunagusa BEI — kasoro iliyokuwa kimya
# ===========================================================================


def test_kupanda_KUNABADILISHA_bei():
    """Kasoro ya µs/ns ilifanya hii ishindwe kimya: mask tupu, bei zilezile."""
    ticks = _ticks()
    baada = C.inject(ticks, [_w()], [5.0], pip=PIP)
    assert not np.allclose(ticks["bid"], baada["bid"])
    assert (ticks["bid"] != baada["bid"]).sum() > 1000


def test_SELL_inashusha_bei_kwa_pips_zilizoombwa():
    ticks = _ticks(n=20000)
    w = _w(hours=4, side="SELL")
    baada = C.inject(ticks, [w], [5.0], pip=PIP)

    kabla_mid = (ticks["bid"] + ticks["ask"]) / 2
    baada_mid = (baada["bid"] + baada["ask"]) / 2
    i0 = 0
    i1 = int((w.end - w.start).total_seconds()) - 1
    hamisho = (baada_mid.iloc[i1] - baada_mid.iloc[i0]) - \
              (kabla_mid.iloc[i1] - kabla_mid.iloc[i0])
    assert hamisho / PIP == pytest.approx(-5.0, abs=0.01)


def test_BUY_inapandisha_bei():
    ticks = _ticks(n=20000)
    w = _w(hours=4, side="BUY")
    baada = C.inject(ticks, [w], [5.0], pip=PIP)
    mid = (baada["bid"] + baada["ask"]) / 2
    n = int((w.end - w.start).total_seconds())
    assert (mid.iloc[n - 1] - mid.iloc[0]) / PIP == pytest.approx(5.0, abs=0.01)


def test_spread_HAIBADILIKI():
    """Tunapanda edge, si ukwasi."""
    ticks = _ticks()
    baada = C.inject(ticks, [_w()], [7.0], pip=PIP)
    assert np.allclose(baada["ask"] - baada["bid"], ticks["ask"] - ticks["bid"])


def test_drift_INABAKI_baada_ya_dirisha():
    """Bila hivyo kungekuwa na mruko wa bandia kwenye mpaka wa dirisha."""
    ticks = _ticks(n=30000)
    w = _w(hours=4, side="SELL")
    baada = C.inject(ticks, [w], [5.0], pip=PIP)
    mid = (baada["bid"] + baada["ask"]) / 2
    n = int((w.end - w.start).total_seconds())
    assert mid.iloc[-1] == pytest.approx(mid.iloc[n], abs=1e-12)


def test_madirisha_mawili_yanajilimbikiza():
    ticks = _ticks(n=40000)
    a = _w(hours=2, side="SELL", start=T0)
    b = _w(hours=2, side="SELL", start=T0 + timedelta(hours=3))
    baada = C.inject(ticks, [a, b], [3.0, 4.0], pip=PIP)
    mid = (baada["bid"] + baada["ask"]) / 2
    assert (mid.iloc[-1] - mid.iloc[0]) / PIP == pytest.approx(-7.0, abs=0.02)


def test_pips_sifuri_hazibadilishi_chochote():
    ticks = _ticks()
    assert np.allclose(C.inject(ticks, [_w()], [0.0], pip=PIP)["bid"], ticks["bid"])


def test_idadi_isiyotoshana_inalipuka():
    with pytest.raises(C.ControlError, match="madirisha"):
        C.inject(_ticks(), [_w(), _w()], [1.0], pip=PIP)


# ===========================================================================
# Maumbo matatu
# ===========================================================================


def _windows(n_days=120):
    return [C.Window(T0 + timedelta(days=i), T0 + timedelta(days=i, hours=4),
                     "SELL") for i in range(n_days)]


@pytest.mark.parametrize("shape", C.SHAPES)
def test_maumbo_yote_yanahifadhi_WASTANI(shape):
    """Bila hivyo, maumbo yangekuwa yakipima `δ` tofauti."""
    w = _windows(150)
    x = C.edge_per_window(w, 4.0, shape, seed=3)
    assert float(np.mean(x)) == pytest.approx(4.0, rel=0.25)


def test_CONSTANT_ni_thabiti():
    x = C.edge_per_window(_windows(50), 3.0, C.CONSTANT)
    assert len(set(x)) == 1 and x[0] == 3.0


def test_CLUSTERED_ni_sifuri_kwa_miezi_mingi():
    """Edge ipo kwenye ~30% ya miezi pekee."""
    x = C.edge_per_window(_windows(300), 3.0, C.CLUSTERED, seed=5)
    sifuri = sum(1 for v in x if v == 0.0)
    assert 0.5 < sifuri / len(x) < 0.9


def test_SERIAL_ina_mfululizo():
    """Edge inabadilika taratibu, si kwa nasibu — ndiyo maana ni ngumu zaidi."""
    x = np.array(C.edge_per_window(_windows(400), 3.0, C.SERIAL, seed=7))
    kati = x - x.mean()
    acf1 = float((kati[1:] * kati[:-1]).sum() / (kati * kati).sum())
    assert acf1 > 0.4


def test_umbo_lisilojulikana_linalipuka():
    with pytest.raises(C.ControlError, match="umbo"):
        C.edge_per_window(_windows(10), 1.0, "MRABA")


# ===========================================================================
# δ na nguvu ya kinadharia
# ===========================================================================


def test_delta_ni_snr_mara_mzizi_wa_n():
    x = np.full(400, 0.1) + np.random.default_rng(1).normal(0, 1.0, 400)
    d = C.delta(x)
    assert d == pytest.approx(x.mean() / x.std(ddof=1) * math.sqrt(400))


def test_nguvu_inapanda_na_delta():
    thamani = [C.theoretical_power(d) for d in (0, 1, 2, 3, 4, 5)]
    assert thamani == sorted(thamani)
    assert thamani[0] == pytest.approx(0.05, abs=0.005)   # δ=0 → α
    assert thamani[-1] > 0.99


def test_nguvu_kwenye_delta_ya_kizingiti():
    """`δ = z_α` inatoa nguvu ya 50% — nukta ya kugeuka."""
    assert C.theoretical_power(1.6448536269514722) == pytest.approx(0.5, abs=1e-6)


def test_PowerPoint_inaripoti_PENGO():
    p = C.PowerPoint(shape=C.CONSTANT, pips=3.0, n_replicates=20, detected=12,
                     delta_median=2.0, n_days_median=500, n_active_median=500)
    assert p.rate == pytest.approx(0.6)
    assert p.gap == pytest.approx(p.theoretical - 0.6)
    assert "pengo" in p.render()
