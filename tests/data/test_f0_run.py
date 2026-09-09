"""Mtiririko wa `backtest.driver` — DOCTRINE §4, §6, §7.

Driver hii ndiyo PD anayoiendesha kwenye GB 33, kwa familia zote. Haiwezi
kupimwa kwenye data hiyo hapa, kwa hiyo inapimwa kwenye L0 ndogo yenye
**muundo ule ule**: folda za `provenance=/symbol=/year=/month=/day=`.

Dai kubwa kuliko yote: **stop haina lookahead**. Kwenye mtiririko wa mwezi kwa
mwezi ni rahisi mno kwa mwendo wa leo kuingia kwenye historia kabla ya kikapu
cha leo kujengwa — na kosa hilo halionekani kwenye matokeo, linaonekana tu
kama curve laini isiyo ya kawaida.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src.analysis.control import _nanos
from src.backtest import driver as D
from src.data import ticks as TK
from src.families import f0
from src.rce.config import load_config

REPO = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def L0(tmp_path_factory):
    """Siku 60 za kazi, ticks kwenye ncha NNE pekee — kama F0 inavyosoma."""
    root = tmp_path_factory.mktemp("L0")
    rng = np.random.default_rng(11)
    zote = [date(2021, 1, 1) + timedelta(days=i) for i in range(90)]
    siku = f0.eligible_days(zote)

    for d in siku:
        ncha = []
        for s in f0.sessions_for(d):
            ncha += [s.entry_at, s.exit_at]
        idx = pd.DatetimeIndex(
            sorted({t for n in ncha
                    for t in pd.date_range(n, periods=f0.WINDOW_SECONDS,
                                           freq="1s", tz="UTC")}))
        # `_nanos`, si `astype`: pandas inahifadhi kwa mikrosekunde, na mapengo
        # ya masaa kati ya madirisha yangebanwa hadi sekunde moja.
        ns = _nanos(pd.Series(idx))
        sekunde = np.diff(ns, prepend=ns[0]) / 1e9
        sd = 13 * 0.0001 / np.sqrt(3600.0)
        hatua = rng.normal(0.0, sd, len(idx)) * np.sqrt(
            np.maximum(sekunde, 1.0))
        mid = 1.20 + np.cumsum(hatua)
        folda = (root / "provenance=aggregator" / "symbol=EURUSD"
                 / f"year={d.year}" / f"month={d.month:02d}" / f"day={d.day:02d}")
        folda.mkdir(parents=True, exist_ok=True)
        pd.DataFrame({"timestamp": idx, "bid": mid - 0.00008,
                      "ask": mid + 0.00008}).to_parquet(
            folda / "ticks.parquet", index=False)
    return root, siku


@pytest.fixture(scope="module")
def sweep(L0):
    root, siku = L0
    inv = TK.discover(root)
    cfg = load_config(REPO / "config" / "risk.yaml")
    sw = D.sweep(f0, inv, siku, D.RunSpec(), cfg=cfg)
    return dict(inv=inv, siku=siku, trades=sw.trades, mwendo=sw.moves,
                kukosekana=sw.missing, kukataliwa=sw.rejected, sw=sw)


# ===========================================================================
# Mtiririko unafanya kazi
# ===========================================================================


def test_kila_kikao_kinapata_mwendo(sweep):
    assert len(sweep["mwendo"]) == 2 * len(sweep["siku"])
    assert not sweep["kukosekana"], sweep["kukosekana"][:3]
    assert all(v > 0 for v in sweep["mwendo"].values())


def test_vikao_vya_kwanza_10_HAVINA_stop_kwa_hiyo_havitradiwi(sweep):
    """Gharama ya kuanzia, si uteuzi: `SL_MIN_SESSIONS` ya kwanza kwa kila leg
    haina historia ya kutosha."""
    kwa_leg = {}
    for t in sweep["trades"]:
        kwa_leg.setdefault(t.basket_id[-1], []).append(t)
    for leg in (f0.LEG_A, f0.LEG_B):
        assert len(kwa_leg[leg]) == len(sweep["siku"]) - f0.SL_MIN_SESSIONS


def test_hakuna_kikapu_KILICHOKATALIWA_na_RCE(sweep):
    assert not sweep["kukataliwa"], sweep["kukataliwa"][:3]


def test_mielekeo_ni_kama_ILIVYOTANGAZWA(sweep):
    a = {t.side for t in sweep["trades"] if t.basket_id.endswith(":A")}
    b = {t.side for t in sweep["trades"] if t.basket_id.endswith(":B")}
    assert a == {"SELL"} and b == {"BUY"}


# ===========================================================================
# Lookahead — dai kubwa kuliko yote
# ===========================================================================


def test_stop_ya_siku_ni_wastani_wa_MWENDO_ULIOTANGULIA(sweep):
    """Kila trade inahifadhi stop iliyotumika. Hapa inajengwa upya kutoka
    kwenye mwendo wa siku **zilizotangulia pekee**, na lazima ilingane hasa.

    Ikiwa mwendo wa leo ungeingia, siku zenye mwendo mkubwa zingepata lots
    ndogo *kwa sababu* mwendo ulikuwa mkubwa — na curve ingeonekana laini
    kuliko soko lilivyo.
    """
    mwendo = sweep["mwendo"]
    for leg in (f0.LEG_A, f0.LEG_B):
        mfululizo = [mwendo[(d, leg)] for d in sweep["siku"]]
        for i, d in enumerate(sweep["siku"]):
            trade = next((t for t in sweep["trades"]
                          if t.basket_id == f"F0:{d.isoformat()}:{leg}"), None)
            inatarajiwa = f0.stop_from_history(mfululizo[:i])
            if inatarajiwa is None:
                assert trade is None, d
                continue
            # `sl_pips` haihifadhiwi kwenye Trade; inarudishwa kutoka R:
            # R = net_pips / (sl_pips + cost_pips).
            assert trade is not None, d
            sl = trade.net_pips / trade.r - (
                trade.spread_rce_pips + trade.commission_pips)
            assert sl == pytest.approx(f0.SL_MOVE_MULT * inatarajiwa, rel=0.02), (
                leg, d, sl, f0.SL_MOVE_MULT * inatarajiwa)


def test_historia_INAKUA_kuvuka_mpaka_wa_MWEZI(sweep):
    """Mtiririko unasoma mwezi mmoja kwa wakati. Historia ikianzishwa upya
    kila mwezi, siku 10 za kwanza za kila mwezi zingekosa stop kimya."""
    kwa_mwezi = {}
    for t in sweep["trades"]:
        kwa_mwezi.setdefault(t.entry_at.strftime("%Y-%m"), 0)
        kwa_mwezi[t.entry_at.strftime("%Y-%m")] += 1
    # Mwezi wa kwanza pekee ndio unaokosa (siku 10 × legs 2).
    miezi = sorted(kwa_mwezi)
    assert kwa_mwezi[miezi[0]] < kwa_mwezi[miezi[1]]
    kamili = [kwa_mwezi[m] for m in miezi[1:]]
    assert all(n == 2 * len([d for d in sweep["siku"]
                             if d.strftime("%Y-%m") == m])
               for m, n in zip(miezi[1:], kamili))


# ===========================================================================
# Vipimo vinavyoingia kwenye lango la §6
# ===========================================================================


def test_leg_A_ina_sigma_KUBWA_kuliko_leg_B(sweep):
    """Leg A ni masaa 9, leg B ni 4.4. `σ ∝ √muda`, kwa hiyo uwiano wa gharama
    wa leg B ni mbaya zaidi — na ndiyo maana lango linapimwa kwa KILA leg."""
    import statistics as st
    a = st.fmean(v for (_, l), v in sweep["mwendo"].items() if l == f0.LEG_A)
    b = st.fmean(v for (_, l), v in sweep["mwendo"].items() if l == f0.LEG_B)
    assert a > b
    assert b / a == pytest.approx((4.42 / 9.0) ** 0.5, rel=0.20)


def test_pengo_la_spread_ni_karibu_SIFURI_kwa_spread_thabiti(sweep):
    """Kwenye ticks zenye spread isiyobadilika, kadirio la RCE ni sahihi kabisa.
    Kwenye data ya PD ndipo namba hii itakuwa na maana (Lango 3)."""
    assert max(abs(t.spread_gap_pips) for t in sweep["trades"]) < 0.05
