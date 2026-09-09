"""Njia kati ya kuingia na kutoka — DOCTRINE §4.2, §11.

Toleo la kwanza lilidhania stop haigongwi. Kipimo cha F0 (2026-09-08)
kilikataa dhana hiyo: **3.0%** ya vikao 200, si 0.3% ya kanuni ya normal.
Upendeleo unaotokana nayo ni **+0.036 R/siku** — kubwa kuliko athari yenyewe
tuliyokuwa tunaipima (0.023).

Dai kuu hapa ni **usawa halisi, si takribani**: trade iliyogongwa stop inatoa
`R = −1.0` kamili, kwa sababu RCE inapima lots ili iwe hivyo. Ikiwa ni −0.98
au −1.02, sizing ya RCE na hesabu ya R hazikubaliani, na tofauti hiyo
ingejilimbikiza kwenye kila trade iliyogongwa.

Dai la pili ni **kutoathiri kile kisichogongwa**: trade isiyofika stop lazima
iwe **bit kwa bit** ile ile iliyokuwa kabla ya kipimo hiki kuwepo.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src.analysis.probe import PIP, ProbeSpec, _market
from src.backtest.runner import ExecuteError, excursion, execute
from src.portfolio.basket import Basket, Leg
from src.rce.config import load_config

REPO = Path(__file__).resolve().parents[2]

T0 = datetime(2021, 6, 15, 8, 0, tzinfo=timezone.utc)
T1 = T0 + timedelta(hours=4)
DIRISHA = 300
SL = 25.0
SPREAD = 1.6


@pytest.fixture(scope="module")
def cfg():
    return load_config(REPO / "config" / "risk.yaml")


def ticks(*, spike_pips=0.0, spike_at=None, base=1.2000):
    """Ticks za sekunde moja kwenye ncha mbili + njia ya kila dakika.

    `spike_pips` ni mwendo MBAYA kwa SELL (bei inapanda) kwenye `spike_at`.
    """
    stamps = list(pd.date_range(T0, periods=DIRISHA, freq="1s", tz="UTC"))
    stamps += list(pd.date_range(T0 + timedelta(seconds=DIRISHA),
                                 T1 - timedelta(seconds=1), freq="60s", tz="UTC"))
    stamps += list(pd.date_range(T1, periods=DIRISHA, freq="1s", tz="UTC"))
    idx = pd.DatetimeIndex(sorted(set(stamps)))

    mid = np.full(len(idx), base)
    if spike_pips and spike_at is not None:
        wapi = idx.get_indexer([pd.Timestamp(spike_at)], method="nearest")[0]
        mid[wapi] += spike_pips * PIP
    nusu = SPREAD * PIP / 2
    return pd.DataFrame({"timestamp": idx, "bid": mid - nusu, "ask": mid + nusu})


def kikapu(side="SELL", weight=1.0):
    return Basket(
        family="MTIHANI", basket_id=f"MTIHANI:{side}",
        legs=(Leg(symbol="EURUSD", side=side, sl_pips=SL, weight=weight),),
        entry_at=T0, planned_exit_at=T1, priority=1)


def endesha(cfg, frame, *, side="SELL", weight=1.0, njia=True):
    spec = ProbeSpec(sl_pips=SL, spread_pips=SPREAD)
    return execute(
        kikapu(side, weight), cfg=cfg,
        ticks_by_symbol={"EURUSD": frame},
        market={"EURUSD": _market(spec)},
        window_seconds=DIRISHA,
        path_ticks={"EURUSD": frame} if njia else None,
    )


# ===========================================================================
# Dai kuu: −1R HASA
# ===========================================================================


def test_stop_iliyogongwa_inatoa_R_ya_MOJA_HASI_kamili(cfg):
    """Si −0.98 wala −1.02. RCE inapima lots ili hasara kwenye stop iwe hasa
    `risk_at_stop`; kama R si −1.000, sizing na hesabu hazikubaliani."""
    out = endesha(cfg, ticks(spike_pips=40.0, spike_at=T0 + timedelta(hours=2)))
    t = out.trades[0]
    assert t.stopped is True
    assert t.r == pytest.approx(-1.0, abs=1e-12)
    assert t.pnl_account == pytest.approx(-t.risk_unit, abs=1e-9)


def test_hasara_ni_net_pips_ya_stop_pamoja_na_GHARAMA(cfg):
    """`net_pips = −(sl + cost)` ndiyo inayofanya P&L ifuate njia ile ile ya
    trade ya kawaida — hakuna tawi la pekee kwenye hesabu ya pesa."""
    out = endesha(cfg, ticks(spike_pips=40.0, spike_at=T0 + timedelta(hours=2)))
    t = out.trades[0]
    gharama = t.net_pips + SL
    assert -gharama > 0                       # gharama ni chanya
    assert t.gross_pips == pytest.approx(-SL)
    assert t.pnl_account == pytest.approx(
        t.net_pips * t.lots * t.pip_value_acct, rel=1e-9)


def test_uzito_NUSU_unatoa_R_ya_NUSU_HASI(cfg):
    """R ni **mchango**, si ufanisi: leg ya uzito 0.5 inapoteza nusu ya 1R."""
    out = endesha(cfg, ticks(spike_pips=40.0, spike_at=T0 + timedelta(hours=2)),
                  weight=0.5)
    assert out.trades[0].r == pytest.approx(-0.5, abs=1e-12)


def test_saa_ya_kutoka_ni_tick_ya_KWANZA_inayovuka(cfg):
    """Si saa ya kupanga, na si tick ya mwisho: ya kwanza inayovuka."""
    wakati = T0 + timedelta(hours=2)
    out = endesha(cfg, ticks(spike_pips=40.0, spike_at=wakati))
    t = out.trades[0]
    assert t.exit_at == wakati
    assert t.exit_at < T1


def test_bei_ya_kutoka_ni_kiwango_cha_STOP(cfg):
    out = endesha(cfg, ticks(spike_pips=40.0, spike_at=T0 + timedelta(hours=2)))
    t = out.trades[0]
    assert t.exit_price == pytest.approx(t.entry_price + SL * PIP)


# ===========================================================================
# Dai la pili: kisichogongwa hakibadiliki
# ===========================================================================


def test_mwendo_CHINI_ya_stop_haubadilishi_LOLOTE(cfg):
    """Bit kwa bit ile ile iliyokuwa kabla ya kipimo hiki kuwepo."""
    frame = ticks(spike_pips=20.0, spike_at=T0 + timedelta(hours=2))
    na_njia = endesha(cfg, frame).trades[0]
    bila_njia = endesha(cfg, frame, njia=False).trades[0]

    assert na_njia.stopped is False
    assert na_njia.r == bila_njia.r
    assert na_njia.net_pips == bila_njia.net_pips
    assert na_njia.exit_at == bila_njia.exit_at == T1
    assert na_njia.pnl_account == bila_njia.pnl_account


def test_MAE_inarekodiwa_hata_isipogonga(cfg):
    """Ndiyo namba inayotuambia stop iko karibu kiasi gani na soko.

    Mruko ni pips 20, lakini MAE ni **21.6**: SELL inaingia kwa `bid` na
    kufungwa kwa `ask`, kwa hiyo spread NZIMA (si nusu) imo ndani ya kila
    mwendo. Ndiyo maana stop ya pips 25 iko karibu na soko kuliko namba 25
    inavyoonyesha — na ndiyo sababu mojawapo ya kugongwa 3.0% badala ya 0.3%.
    """
    out = endesha(cfg, ticks(spike_pips=20.0, spike_at=T0 + timedelta(hours=2)))
    t = out.trades[0]
    assert t.mae_pips == pytest.approx(20.0 + SPREAD, abs=1e-6)
    assert t.mae_pips < SL and not t.stopped


# ===========================================================================
# Mipaka ya dirisha la kupima
# ===========================================================================


def test_dirisha_la_KUINGIA_halihesabiwi(cfg):
    """Dakika tano za kujaza: position bado haijakamilika."""
    out = endesha(cfg, ticks(spike_pips=60.0, spike_at=T0 + timedelta(seconds=100)))
    assert out.trades[0].stopped is False


def test_dirisha_la_KUTOKA_halihesabiwi(cfg):
    """Tayari tunatoka; stop hapo isingebadilisha lolote."""
    out = endesha(cfg, ticks(spike_pips=60.0, spike_at=T1 + timedelta(seconds=100)))
    assert out.trades[0].stopped is False


def test_bila_path_ticks_hakuna_kinachodaiwa_kupimwa(cfg):
    """`path_modelled=False` ni ili matokeo yasidaiwe kuwa yamepimwa."""
    out = endesha(cfg, ticks(spike_pips=60.0, spike_at=T0 + timedelta(hours=2)),
                  njia=False)
    t = out.trades[0]
    assert t.path_modelled is False and t.stopped is False and t.mae_pips == 0.0


# ===========================================================================
# Upande wa bei — kasoro iliyokuwa ndani ya `--angalia-stop`
# ===========================================================================


def test_SELL_inapimwa_kwa_ASK_si_bid(cfg):
    """SELL inafungwa kwa `ask`. Kutumia `bid` kungepunguza kila mwendo kwa
    spread nzima na kuripoti kugongwa kuchache kuliko halisi.

    Kipimo kinachotofautisha: soko lisilotembea hata kidogo. Kwa `ask`, MAE ni
    **spread nzima**; kwa `bid` ingekuwa **sifuri**. Hiyo ndiyo kasoro
    iliyokuwa ndani ya `f0_run --angalia-stop` toleo la kwanza, na ndiyo maana
    3.0% ilikuwa kikomo cha chini.
    """
    bid_ya_kuingia = 1.2000 - SPREAD * PIP / 2
    e = excursion(ticks(), side="SELL", entry_price=bid_ya_kuingia,
                  sl_pips=SL, pip=PIP, start=T0, end=T1)
    assert e.mae_pips == pytest.approx(SPREAD, abs=1e-9)
    assert not e.stopped


def test_BUY_inapimwa_kwa_BID(cfg):
    out = endesha(cfg, ticks(spike_pips=-40.0, spike_at=T0 + timedelta(hours=2)),
                  side="BUY")
    t = out.trades[0]
    assert t.stopped is True
    assert t.r == pytest.approx(-1.0, abs=1e-12)
    assert t.exit_price == pytest.approx(t.entry_price - SL * PIP)


def test_BUY_haigongwi_na_mruko_wa_KUPANDA(cfg):
    out = endesha(cfg, ticks(spike_pips=+60.0, spike_at=T0 + timedelta(hours=2)),
                  side="BUY")
    assert out.trades[0].stopped is False


# ===========================================================================
# Lango 3 halichafuliwi
# ===========================================================================


def test_spread_ya_trade_iliyogongwa_ni_NAN(cfg):
    """Dirisha la kutoka halikutumika: hakuna spread ya kwenda-na-kurudi
    iliyolipwa. Namba hapo ingechafua kipimo cha Lango 3."""
    out = endesha(cfg, ticks(spike_pips=40.0, spike_at=T0 + timedelta(hours=2)))
    t = out.trades[0]
    assert np.isnan(t.spread_realised_pips)
    assert np.isnan(t.spread_gap_pips)


def test_spread_ya_trade_ISIYOGONGWA_inabaki_namba(cfg):
    out = endesha(cfg, ticks())
    t = out.trades[0]
    assert np.isfinite(t.spread_realised_pips)
    assert t.spread_realised_pips == pytest.approx(SPREAD, abs=0.01)


# ===========================================================================
# Ulinzi
# ===========================================================================


def test_sl_isiyo_chanya_INALIPUKA():
    with pytest.raises(ExecuteError, match="sl_pips"):
        excursion(ticks(), side="SELL", entry_price=1.2, sl_pips=0.0,
                  pip=PIP, start=T0, end=T1)


def test_ticks_zisizo_na_upande_wa_kufunga_ZINALIPUKA():
    frame = ticks().drop(columns=["ask"])
    with pytest.raises(ExecuteError, match="ask"):
        excursion(frame, side="SELL", entry_price=1.2, sl_pips=SL,
                  pip=PIP, start=T0, end=T1)


def test_dirisha_TUPU_halidai_kwamba_haikugongwa():
    """Inarudisha `mae 0`, lakini mwitaji ndiye anayeamua kwa `path_modelled` —
    "hakuna ushahidi" si sawa na "haikugongwa"."""
    e = excursion(ticks(), side="SELL", entry_price=1.2, sl_pips=SL, pip=PIP,
                  start=T1 + timedelta(days=1), end=T1 + timedelta(days=2))
    assert e.mae_pips == 0.0 and not e.stopped
