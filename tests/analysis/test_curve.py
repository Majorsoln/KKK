"""Curve ya siku — DOCTRINE §7.2.

Toleo la kwanza lilipima t-statistic juu ya trades zilizokusanywa. Trades 33
zilizojilimbikiza kwenye miezi 2 zilihesabiwa kama uchunguzi 33 wakati zilikuwa
2 hadi 6, na kila `p-value` ikawa anti-conservative kwa `√(33/4) ≈ 2.9`.

Curve ya siku inaondoa kosa hilo kwa ujenzi: legs sita za F1 ni **siku moja**.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from src.analysis import curve as CV

UTC = ZoneInfo("UTC")


@dataclass
class _T:
    exit_at: datetime
    r: float


def _t(y, m, d, r, hour=14):
    return _T(datetime(y, m, d, hour, 0, tzinfo=UTC), r)


# ===========================================================================
# Legs kadhaa za siku moja ni uchunguzi MMOJA
# ===========================================================================


def test_legs_sita_za_siku_moja_ni_SIKU_MOJA():
    """Kiini cha §7.2. F1 ina matukio 99, si 594."""
    c = CV.daily_r([_t(2021, 6, 15, 0.1) for _ in range(6)])
    assert c.n == 1
    assert c.n_trades_total == 6
    assert c.r[0] == pytest.approx(0.6)


def test_siku_tofauti_ni_uchunguzi_tofauti():
    c = CV.daily_r([_t(2021, 6, 15, 0.2), _t(2021, 6, 16, -0.1)])
    assert c.n == 2 and c.n_active == 2
    assert c.total_r == pytest.approx(0.1)


# ===========================================================================
# Siku ya soko, si ya kalenda
# ===========================================================================


def test_baada_ya_17_00_NY_ni_siku_INAYOFUATA():
    """Mpaka ni rollover, si usiku wa manane wa UTC."""
    kabla = CV.daily_r([_T(datetime(2021, 6, 15, 20, 0, tzinfo=UTC), 1.0)])
    baada = CV.daily_r([_T(datetime(2021, 6, 15, 22, 0, tzinfo=UTC), 1.0)])
    assert kabla.days == (date(2021, 6, 15),)
    assert baada.days == (date(2021, 6, 16),)


# ===========================================================================
# Dirisha na siku HAI
# ===========================================================================


def test_siku_zisizo_na_trade_zinajazwa_SIFURI():
    """Mwezi usio na trade ni mwezi wenye matokeo ya sifuri, si usiokuwepo."""
    dirisha = [date(2021, 6, 14) + timedelta(days=i) for i in range(5)]
    c = CV.daily_r([_t(2021, 6, 16, 0.5)], days=dirisha)
    assert c.n == 5 and c.n_active == 1
    assert c.total_r == pytest.approx(0.5)
    assert list(c.r) == [0.0, 0.0, 0.5, 0.0, 0.0]


def test_siku_HAI_zinaripotiwa_kando():
    """F1 ni sifuri kwa siku 2,100 kati ya 2,151. Kusoma bootstrap kana kwamba
    ina uchunguzi 2,151 kungekuwa kudai nguvu isiyokuwepo."""
    dirisha = [date(2021, 1, 1) + timedelta(days=i) for i in range(300)]
    c = CV.daily_r([_t(2021, 1, 15, 1.0), _t(2021, 3, 15, 1.0)], days=dirisha)
    assert c.n == 300
    assert c.n_active == 2
    assert "hai 2" in c.render()


def test_trade_NJE_ya_dirisha_inalipuka():
    """R18 — kila hatua inatangaza dirisha lake."""
    dirisha = [date(2021, 6, 14) + timedelta(days=i) for i in range(3)]
    with pytest.raises(CV.CurveError, match="NJE ya dirisha"):
        CV.daily_r([_t(2021, 12, 25, 1.0)], days=dirisha)


def test_active_values_inatoa_siku_HAI_pekee():
    dirisha = [date(2021, 6, 14) + timedelta(days=i) for i in range(5)]
    c = CV.daily_r([_t(2021, 6, 16, 0.5)], days=dirisha)
    assert list(c.active_values()) == [0.5]
    assert len(c.values()) == 5


# ===========================================================================
# Kuunganisha familia
# ===========================================================================


def test_familia_mbili_za_siku_moja_ni_SIKU_MOJA():
    a = CV.daily_r([_t(2021, 6, 15, 0.3)])
    b = CV.daily_r([_t(2021, 6, 15, -0.1), _t(2021, 6, 16, 0.2)])
    c = CV.combine([a, b])
    assert c.n == 2
    assert c.r[0] == pytest.approx(0.2)          # 0.3 − 0.1
    assert c.n_trades[0] == 2
    assert c.total_r == pytest.approx(0.4)


def test_kuunganisha_bila_curve_kunalipuka():
    with pytest.raises(CV.CurveError, match="hakuna curve"):
        CV.combine([])


def test_urefu_usiotoshana_unalipuka():
    with pytest.raises(CV.CurveError, match="hautoshani"):
        CV.Curve(days=(date(2021, 1, 1),), r=(1.0, 2.0), n_trades=(1,))


# ===========================================================================
# Mnyororo: curve → bootstrap
# ===========================================================================


def test_curve_inaingia_kwenye_bootstrap_moja_kwa_moja():
    import numpy as np

    from src.analysis import bootstrap as BS

    rng = np.random.default_rng(5)
    siku = [date(2020, 1, 1) + timedelta(days=i) for i in range(500)]
    trades = [_T(datetime.combine(d, datetime.min.time(), tzinfo=UTC)
                 + timedelta(hours=14), float(rng.normal(0.05, 0.4)))
              for d in siku]
    c = CV.daily_r(trades, days=siku)
    r = BS.test_mean_positive(c, B=500, seed=1)
    assert r.n == 500 and r.n_active == 500
    assert r.p_value < 0.05                       # edge ya 0.05R kwa siku
