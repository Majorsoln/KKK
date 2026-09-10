"""Kikapu → trades → R — DOCTRINE §4.1, §5, R12.

Hatari kubwa hapa ni **kuhesabu gharama mara mbili**. Bei za utekelezaji
zinajumuisha spread; `cost_pips` ya RCE nayo inaijumuisha, lakini kwa ajili ya
**sizing**. Kuitoa tena kwenye P&L kungefanya kila trade ionekane mbaya kwa
spread nzima ya ziada — na hilo lisingeonekana kama kosa, lingeonekana kama
soko gumu.

Utambulisho unaolifichua:

```
spread iliyolipwa = gross_pips − net_pips − commission − swap
```
"""

from __future__ import annotations

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd
import pytest

from src.backtest import runner as X
from src.portfolio import basket as BK
from src.rce.budget import AccountState
from src.rce.cost import SymbolSpec, slippage_cap_pips


def _slippage(cfg):
    return slippage_cap_pips("market", cfg, None, symbol="EURUSD")

UTC = ZoneInfo("UTC")
T0 = datetime(2021, 6, 15, 14, 0, tzinfo=UTC)      # Jumanne — hakuna swap
NJE = T0 + timedelta(minutes=75)
PIP = 0.0001


def _ticks(bid0=1.2000, spread=0.00016, hatua=0.0, n=7200, start=None):
    """Ticks za sekunde moja, spread thabiti, mwelekeo `hatua` kwa tick."""
    stamps = pd.date_range(start or (T0 - timedelta(minutes=5)),
                           periods=n, freq="1s", tz="UTC")
    bids = bid0 + np.arange(n) * hatua
    return pd.DataFrame({"timestamp": stamps, "bid": bids, "ask": bids + spread})


def _market(pip_value=10.0, commission=7.0, spread_h1=1.6, spread_m5=1.6,
            balance=10_000.0):
    return {
        "spec": SymbolSpec(symbol="EURUSD", point=0.00001, contract_size=100_000,
                           volume_min=0.01, volume_step=0.01, volume_max=50.0),
        "account": AccountState(current_balance=balance, today_profit=0.0,
                                today_loss=0.0, open_positions=0),
        "h1_spreads": [spread_h1] * 120,
        "m5_spreads": [spread_m5] * 300,
        "pip_value_acct": pip_value,
        "commission_round_turn": commission,
        "pip": PIP,
    }


def _basket(symbols=("EURUSD",), sides=None, sl=25.0, weights=None):
    sides = sides or ["BUY"] * len(symbols)
    weights = weights or [1.0] * len(symbols)
    return BK.Basket(
        family="F0", basket_id="F0:2021-06-15",
        legs=tuple(BK.Leg(symbol=s, side=d, sl_pips=sl, weight=w)
                   for s, d, w in zip(symbols, sides, weights)),
        entry_at=T0, planned_exit_at=NJE, priority=1)


def _run(basket, cfg, ticks=None, market=None, **kw):
    t = ticks if ticks is not None else _ticks()
    return X.execute(basket, cfg=cfg,
                     ticks_by_symbol={s: t for s in basket.symbols},
                     market={s: (market or _market()) for s in basket.symbols},
                     **kw)


# ===========================================================================
# Spread haihesabiwi mara mbili
# ===========================================================================


def test_utambulisho_wa_upatanisho(cfg_risk):
    """`gross − net = spread iliyolipwa + commission + swap`. Daima."""
    out = _run(_basket(), cfg_risk)
    t = out.trades[0]
    assert (t.gross_pips - t.net_pips) == pytest.approx(
        t.spread_realised_pips + t.commission_pips + t.swap_pips)


def test_spread_iliyolipwa_ni_spread_KAMILI_si_nusu(cfg_risk):
    """Kununua kwa ask na kuuza kwa bid kunalipa spread NZIMA."""
    out = _run(_basket(), cfg_risk, ticks=_ticks(spread=0.00016))
    assert out.trades[0].spread_realised_pips == pytest.approx(1.6, abs=1e-6)


def test_soko_lisilobadilika_linatoa_gross_SIFURI(cfg_risk):
    """Bila mwelekeo, mid→mid ni sifuri; hasara yote ni gharama."""
    out = _run(_basket(), cfg_risk, ticks=_ticks(hatua=0.0))
    t = out.trades[0]
    assert t.gross_pips == pytest.approx(0.0, abs=1e-9)
    assert t.net_pips < 0
    assert t.net_pips == pytest.approx(
        -(t.spread_realised_pips + t.commission_pips + t.swap_pips))


def test_SELL_inageuza_ishara(cfg_risk):
    """Bei ikipanda, BUY inapata, SELL inapoteza — kwa kiasi kilekile cha gross."""
    ticks = _ticks(hatua=1e-7)
    kununua = _run(_basket(sides=["BUY"]), cfg_risk, ticks=ticks).trades[0]
    kuuza = _run(_basket(sides=["SELL"]), cfg_risk, ticks=ticks).trades[0]
    assert kununua.gross_pips == pytest.approx(-kuuza.gross_pips)
    assert kununua.gross_pips > 0
    # Zote mbili zinalipa spread ileile.
    assert kununua.spread_realised_pips == pytest.approx(kuuza.spread_realised_pips)


def test_commission_inatoka_kwa_RCE_si_kwa_bei(cfg_risk):
    bila = _run(_basket(), cfg_risk, market=_market(commission=0.0)).trades[0]
    na = _run(_basket(), cfg_risk, market=_market(commission=7.0)).trades[0]
    assert bila.commission_pips == 0.0
    assert na.commission_pips > 0
    assert na.net_pips < bila.net_pips
    assert na.gross_pips == pytest.approx(bila.gross_pips)   # bei hazibadiliki


# ===========================================================================
# Kipimo cha RCE dhidi ya ticks — Lango 3
# ===========================================================================


def test_pengo_la_spread_linapimwa(cfg_risk):
    """RCE ikidharau spread, pengo ni CHANYA. Ndiyo namba ya Lango 3."""
    # Ticks zina spread 3.0 pips; RCE inadhani 1.6 kutoka madirisha ya nyuma.
    out = _run(_basket(), cfg_risk, ticks=_ticks(spread=0.00030),
               market=_market(spread_h1=1.6, spread_m5=1.6))
    t = out.trades[0]
    assert t.spread_realised_pips == pytest.approx(3.0, abs=1e-6)
    assert t.spread_rce_pips == pytest.approx(1.6)
    assert t.spread_gap_pips == pytest.approx(1.4, abs=1e-6)


def test_pengo_ni_SIFURI_RCE_ikiwa_sahihi(cfg_risk):
    out = _run(_basket(), cfg_risk, ticks=_ticks(spread=0.00016),
               market=_market(spread_h1=1.6, spread_m5=1.6))
    assert out.trades[0].spread_gap_pips == pytest.approx(0.0, abs=1e-6)


# ===========================================================================
# Vipimo vya R
# ===========================================================================


def test_R_ni_utambulisho_wa_pips_kwa_hatari(cfg_risk):
    """`R = net_pips / (sl_pips + cost_pips)`.

    Utambulisho huu ndio unaofanya R iwe kipimo: hautegemei lots, bajeti, wala
    salio la akaunti — vitu vyote vinavyobadilika kwa sababu zisizohusiana na
    ubora wa trade.
    """
    out = _run(_basket(sl=25.0), cfg_risk)
    t = out.trades[0]
    gharama = (t.spread_rce_pips + t.commission_pips + t.swap_pips
               + _slippage(cfg_risk))
    assert t.r == pytest.approx(t.net_pips / (25.0 + gharama), rel=1e-6)


def test_R_HAITEGEMEI_bajeti_wala_salio(cfg_risk):
    """DD ikipunguza bajeti, lots zinapungua — lakini R inabaki ileile."""
    ticks = _ticks(hatua=1e-7)
    a = _run(_basket(), cfg_risk, ticks=ticks, market=_market(balance=10_000.0)).trades[0]
    b = _run(_basket(), cfg_risk, ticks=ticks, market=_market(balance=9_500.0)).trades[0]
    assert b.lots < a.lots                       # DD → bajeti ndogo → lots ndogo
    assert a.r == pytest.approx(b.r, rel=1e-9)   # R haijabadilika HATA KIDOGO


def test_R_INATEGEMEA_pip_value_kwa_sababu_ya_commission(cfg_risk):
    """Si kasoro — ni uchumi. `commission_pips = commission / pip_value`, kwa
    hiyo symbol yenye pip value ndogo inalipa zaidi KWA PIPS.

    R inasawazisha **ukubwa**, si **muundo wa gharama**.
    """
    ticks = _ticks(hatua=1e-7)
    a = _run(_basket(), cfg_risk, ticks=ticks, market=_market(pip_value=10.0)).trades[0]
    b = _run(_basket(), cfg_risk, ticks=ticks, market=_market(pip_value=7.0)).trades[0]
    assert b.commission_pips > a.commission_pips
    assert b.r < a.r
    # Tofauti inaelezwa KABISA na commission — hakuna kilichobaki.
    assert (a.r - b.r) == pytest.approx(
        a.net_pips / (25.0 + a.spread_rce_pips + a.commission_pips + _slippage(cfg_risk))
        - b.net_pips / (25.0 + b.spread_rce_pips + b.commission_pips + _slippage(cfg_risk)),
        rel=1e-6)


def test_uzito_wa_leg_unapunguza_HATARI_na_MCHANGO(cfg_risk):
    """§5.1 — nguvu ya ishara inapunguza hatari, si lots moja kwa moja.

    `risk_unit` (1R) haibadiliki; `risk_taken` na mchango wa R vinapungua kwa
    uzito. Ndiyo maana jumla ya R za trades ni R ya portfolio.
    """
    ticks = _ticks(hatua=1e-7)
    kamili = _run(_basket(weights=[1.0]), cfg_risk, ticks=ticks).trades[0]
    nusu = _run(_basket(weights=[0.5]), cfg_risk, ticks=ticks).trades[0]

    assert nusu.lots == pytest.approx(kamili.lots * 0.5)
    assert nusu.risk_unit == pytest.approx(kamili.risk_unit)     # 1R haibadiliki
    assert nusu.risk_taken == pytest.approx(kamili.risk_taken * 0.5)
    assert nusu.weight == pytest.approx(0.5)
    assert nusu.r == pytest.approx(kamili.r * 0.5)               # MCHANGO, si ufanisi


# ===========================================================================
# Utekelezaji ni wa atomiki
# ===========================================================================


def test_leg_ikikataliwa_kikapu_KIZIMA_hakitradiwi(cfg_risk):
    """Bajeti ndogo mno → lots chini ya `volume_min` → REJECT.

    Legs zilizopita hazibaki; §6 inasema kikapu ni cha yote-au-hakuna, na
    utekelezaji nao ni sehemu ya sheria hiyo.
    """
    ndogo = _market(balance=10_000.0)
    ndogo["pip_value_acct"] = 1e6            # lots ndogo kupita `volume_min`
    out = _run(_basket(("EURUSD", "USDJPY")), cfg_risk, market=ndogo)
    assert not out.executed
    assert out.trades == []
    assert out.reason.startswith(X.PARTIAL_EXECUTION)


def test_kikapu_chenye_legs_kadhaa_kinatoa_trades_ZOTE(cfg_risk):
    out = _run(_basket(("EURUSD", "USDJPY", "USDCAD")), cfg_risk)
    assert out.executed and len(out.trades) == 3
    assert out.r == pytest.approx(sum(t.r for t in out.trades))


# ===========================================================================
# Swap
# ===========================================================================


def test_trade_ya_ndani_ya_siku_HAILIPI_swap(cfg_risk):
    assert _run(_basket(), cfg_risk).trades[0].swap_pips == 0.0


# ===========================================================================
# Ulinzi
# ===========================================================================


def test_ticks_zisizopo_zinalipuka(cfg_risk):
    with pytest.raises(X.ExecuteError, match="ticks"):
        X.execute(_basket(), cfg=cfg_risk, ticks_by_symbol={},
                  market={"EURUSD": _market()})


def test_muktadha_usiopo_unalipuka(cfg_risk):
    with pytest.raises(X.ExecuteError, match="muktadha"):
        X.execute(_basket(), cfg=cfg_risk,
                  ticks_by_symbol={"EURUSD": _ticks()}, market={})


def test_dirisha_lisilo_na_ticks_linalipuka(cfg_risk):
    from src.events.clock import ClockError

    fupi = _ticks(n=60)                       # dakika moja pekee
    with pytest.raises(ClockError, match="hakuna tick"):
        _run(_basket(), cfg_risk, ticks=fupi)
