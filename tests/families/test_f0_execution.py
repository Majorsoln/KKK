"""F0 kutoka tangazo hadi `p` — DOCTRINE §4, §5, §7.

`test_f0.py` inapima **ufafanuzi**. Hapa tunapima kwamba ufafanuzi huo
**unapitika**: vikapu vya F0 vinapita RCE, vinatoa trades, vinajenga curve ya
siku, na bootstrap inaisoma.

Ticks ni za bandia. Lengo si kujua kama F0 ina edge — hilo linahitaji data ya
PD. Lengo ni kwamba pale edge **ipo**, mnyororo wa F0 unaiona; na pale
haipo, hauitangazi. Ni Lango 1 likiendeshwa kwenye kalenda halisi ya F0
badala ya kwenye umbo lake.
"""

from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

import pytest

from src.analysis import bootstrap as BS
from src.analysis.control import CONSTANT, Window, edge_per_window, inject
from src.analysis.curve import daily_r
from src.analysis.probe import PIP, ProbeSpec, _market, synthetic_ticks
from src.backtest.runner import execute
from src.families import f0
from src.rce.config import load_config

REPO = Path(__file__).resolve().parents[2]


def siku_zote(a: date, b: date) -> list[date]:
    out, d = [], a
    while d <= b:
        out.append(d)
        d += timedelta(days=1)
    return out


@pytest.fixture(scope="module")
def cfg():
    return load_config(REPO / "config" / "risk.yaml")


def _windows(vikapu):
    """Dirisha la kushikilia la kila kikapu, pamoja na upande wake."""
    return [Window(k.entry_at, k.planned_exit_at, k.legs[0].side) for k in vikapu]


def _run(cfg, siku, *, pips=0.0, seed=1, mwendo=20.0):
    """F0 kamili: vikapu → ticks → RCE → trades → curve."""
    spec = ProbeSpec(sl_pips=f0.SL_MOVE_MULT * mwendo)
    vikapu = f0.baskets(siku, move_pips=lambda d, leg: mwendo)
    madirisha = _windows(vikapu)
    ticks = synthetic_ticks(madirisha, spec, seed=seed)

    if pips:
        kiasi = edge_per_window(madirisha, pips, CONSTANT, seed=seed + 7919)
        ticks = inject(ticks, madirisha, kiasi, pip=PIP)

    from src.analysis.control import _nano, _nanos
    t = _nanos(ticks["timestamp"])
    dirisha = f0.WINDOW_SECONDS * 1_000_000_000
    soko = {f0.SYMBOL: _market(spec)}

    trades, zilizokataliwa = [], []
    for k in vikapu:
        a, b = _nano(k.entry_at), _nano(k.planned_exit_at)
        ndani = ((t >= a) & (t < a + dirisha)) | ((t >= b) & (t < b + dirisha))
        out = execute(k, cfg=cfg, ticks_by_symbol={f0.SYMBOL: ticks.loc[ndani]},
                      market=soko, window_seconds=f0.WINDOW_SECONDS)
        if out.executed:
            trades.extend(out.trades)
        else:
            zilizokataliwa.append(out)

    hai = sorted({k.entry_at.date() for k in vikapu})
    return vikapu, trades, zilizokataliwa, daily_r(trades, days=hai)


MWEZI_MMOJA = siku_zote(date(2021, 6, 1), date(2021, 6, 30))


# ===========================================================================
# Mnyororo unapitika
# ===========================================================================


def test_kila_kikapu_kinatoa_trade_MOJA(cfg):
    vikapu, trades, kataa, _ = _run(cfg, MWEZI_MMOJA)
    assert not kataa, [x.render() for x in kataa]
    assert len(trades) == len(vikapu) > 0
    assert {t.symbol for t in trades} == {f0.SYMBOL}


def test_trades_zinabeba_leg_na_mwelekeo_wake(cfg):
    _, trades, _, _ = _run(cfg, MWEZI_MMOJA)
    a = [t for t in trades if t.basket_id.endswith(":A")]
    b = [t for t in trades if t.basket_id.endswith(":B")]
    assert len(a) == len(b) > 0
    assert {t.side for t in a} == {"SELL"}
    assert {t.side for t in b} == {"BUY"}


def test_curve_ina_siku_MOJA_kwa_kila_siku_ya_soko(cfg):
    """Legs mbili za siku moja zinaungana kuwa R moja ya siku hiyo. Ndiyo
    maana `n` ya bootstrap ni siku 1,924, si legs 3,848."""
    vikapu, trades, _, curve = _run(cfg, MWEZI_MMOJA)
    siku_za_vikapu = {k.entry_at.date() for k in vikapu}
    assert curve.n == len(siku_za_vikapu)
    assert curve.n_active == curve.n
    assert len(trades) == 2 * curve.n


def test_hakuna_swap_kwa_sababu_hakuna_usiku(cfg):
    _, trades, _, _ = _run(cfg, MWEZI_MMOJA)
    assert {t.swap_pips for t in trades} == {0.0}


def test_pengo_la_spread_LINAPIMWA_kwa_kila_trade(cfg):
    """Namba inayoamua kama RCE v2 inahitajika (Lango 3). Kwenye ticks za
    bandia zenye spread thabiti inapaswa kuwa ~sifuri; kwenye data ya PD
    ndipo itakuwa na maana."""
    _, trades, _, _ = _run(cfg, MWEZI_MMOJA)
    pengo = [t.spread_gap_pips for t in trades]
    assert len(pengo) == len(trades)
    assert max(abs(x) for x in pengo) < 0.05


def test_R_ni_net_pips_juu_ya_stop_pamoja_na_gharama(cfg):
    """Utambulisho wa §5: `R = net_pips / (sl_pips + cost_pips)`."""
    _, trades, _, _ = _run(cfg, MWEZI_MMOJA, mwendo=20.0)
    t = trades[0]
    gharama = t.spread_rce_pips + t.commission_pips
    # `cost_pips` ya RCE inajumuisha spread + commission + slippage; slippage
    # ni ndogo lakini si sifuri, kwa hiyo ulinganisho ni wa takribani.
    assert t.r == pytest.approx(
        t.net_pips / (f0.SL_MOVE_MULT * 20.0 + gharama), rel=0.05)


def test_mwendo_mkubwa_unatoa_lots_NDOGO(cfg):
    """§5.1 — kulenga volatility bila mfumo wa pili."""
    _, ndogo, _, _ = _run(cfg, MWEZI_MMOJA, mwendo=10.0)
    _, kubwa, _, _ = _run(cfg, MWEZI_MMOJA, mwendo=40.0)
    assert kubwa[0].lots < ndogo[0].lots
    assert kubwa[0].lots == pytest.approx(ndogo[0].lots / 4, rel=0.25)


# ===========================================================================
# Lango 1 kwenye kalenda halisi ya F0
# ===========================================================================


@pytest.mark.parametrize("pips,inaonekana", [(0.0, False), (12.0, True)])
def test_edge_iliyopandwa_INAONEKANA_na_ya_sifuri_HAIONEKANI(cfg, pips,
                                                             inaonekana):
    """Kupanda kunafanywa kwenye **bei**, ndani ya madirisha ya F0 yenyewe.

    Kwenye `pips = 0` wastani wa kweli ni hasi (gharama), kwa hiyo hii si
    kipimo cha ukubwa wa bootstrap — ukubwa umepimwa kwenye
    `test_bootstrap.py`. Ni kipimo kwamba F0 haitangazi kile isichokiona.
    """
    siku = siku_zote(date(2021, 1, 1), date(2021, 12, 31))
    _, trades, kataa, curve = _run(cfg, siku, pips=pips, seed=3)
    assert not kataa
    r = BS.test_mean_positive(curve, B=400, seed=11)
    assert (r.p_value < 0.05) is inaonekana, (pips, r.p_value, r.mean)
