"""Hatua ya kwanza ya utekelezaji — DOCTRINE §11.1–§11.3, R12, R14, R19.

Tests hizi zinapima jambo moja kuu: **signal si trade**, na kila hatua ambayo
signal inaweza kufia ina maana yake tofauti. Zikiunganishwa, swali muhimu zaidi
la uchunguzi halijibiki — *strategy ilikufa kwa kukosa edge au kwa RCE kuzuia
hatari?*

Vilevile zinathibitisha R12: backtest **inaita** RCE, haiigi. Reject reasons
zote zinatoka `src/rce/`, hakuna iliyoandikwa upya hapa.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from src.backtest import ledger as L
from src.backtest.rce_stage import check, classify
from src.rce.budget import AccountState
from src.rce.cost import SymbolSpec
from src.rce.engine import MarketContext, Proposal
from src.rce.gate import (
    REJECT_MAX_CORRELATED, REJECT_MAX_OPEN, REJECT_MAX_SPREAD, REJECT_MAX_TOTAL_DD,
)

NOW = datetime(2020, 6, 1, 9, 0, tzinfo=timezone.utc)

SPEC = SymbolSpec(
    symbol="EURUSD", point=0.00001, contract_size=100_000,
    volume_min=0.01, volume_step=0.01, volume_max=50.0,
)


def _proposal(**kw) -> Proposal:
    base = dict(symbol="EURUSD", direction="BUY", entry=1.10000,
                sl_pips=30.0, tp_pips=60.0, order_type="market")
    base.update(kw)
    return Proposal(**base)


def _ctx(*, balance=10_000.0, today_loss=0.0, today_profit=0.0, open_positions=0,
         spread=1.0, open_symbols=(), spec=SPEC, **kw) -> MarketContext:
    return MarketContext(
        account=AccountState(
            current_balance=balance, today_profit=today_profit,
            today_loss=today_loss, open_positions=open_positions,
        ),
        spec=spec,
        h1_spreads=[spread] * 100,
        m5_spreads=[spread] * 288,
        pip_value_acct=10.0,
        commission_round_turn=7.0,
        open_symbols=tuple(open_symbols),
        now=NOW,
        **kw,
    )


def _check(cfg, proposal=None, ctx=None):
    return check(cfg, proposal or _proposal(), ctx or _ctx(), signal_time=NOW)


# ===========================================================================
# Njia ya kawaida
# ===========================================================================


def test_signal_safi_inapita_rce(cfg_risk):
    a = _check(cfg_risk)
    assert a.rce_outcome == L.PASS and a.approved
    assert a.allowed_lots > 0 and a.budget_at_signal > 0


def test_safu_zote_za_ukaguzi_zinajazwa(cfg_risk):
    """§11.2 — bila hizi, `NO_BUDGET` ni hesabu tupu badala ya uamuzi."""
    a = _check(cfg_risk)
    assert a.budget_at_signal > 0
    assert a.risk_per_trade_at_signal > 0
    assert a.requested_lots > 0
    assert a.broker_min_lot == SPEC.volume_min
    assert a.cost_pips > 0, "gharama inatoka RCE, si kudhaniwa"


def test_hatua_ya_pili_haiguswi_na_hatua_ya_kwanza(cfg_risk):
    """RCE CHECK haijazi `execution_outcome`. Ni hatua tofauti."""
    assert _check(cfg_risk).execution_outcome is None


# ===========================================================================
# R14 — NO_BUDGET si MIN_LOT_REJECT
# ===========================================================================


def test_bajeti_iliyoisha_ni_NO_BUDGET(cfg_risk):
    """DD ya $800 inafuta bajeti (RCE §2). Mfumo umefungwa, si akaunti ndogo."""
    a = _check(cfg_risk, ctx=_ctx(balance=9_200.0))
    assert a.budget_at_signal <= 0
    assert a.rce_outcome == L.NO_BUDGET
    assert not a.approved


def test_bajeti_ndogo_lakini_ipo_ni_MIN_LOT_REJECT(cfg_risk):
    """Bajeti ipo; lots ni ndogo kuliko `volume_min` ya broker.

    Ni ukubwa wa akaunti dhidi ya symbol, si drawdown. Matibabu ni tofauti
    kabisa: hii inatatuliwa kwa mtaji au symbol nyingine, ile kwa kupumzika.
    """
    kubwa = SymbolSpec(
        symbol="EURUSD", point=0.00001, contract_size=100_000,
        volume_min=5.0, volume_step=0.01, volume_max=50.0,
    )
    a = _check(cfg_risk, ctx=_ctx(spec=kubwa))
    assert a.budget_at_signal > 0
    assert a.rce_outcome == L.MIN_LOT_REJECT
    assert 0 < a.requested_lots < a.broker_min_lot


def test_mbili_hizi_hazina_reject_reason_moja_ya_rce(cfg_risk):
    """RCE inatoa `risk_below_min_lot` kwa zote mbili. Tofauti ni ya Doctrine."""
    from src.rce.sizing import REJECT_BELOW_MIN_LOT

    class _Order:
        approved = False
        reason = REJECT_BELOW_MIN_LOT

    assert classify(_Order(), budget_value=0.0) == L.NO_BUDGET
    assert classify(_Order(), budget_value=37.2) == L.MIN_LOT_REJECT


# ===========================================================================
# R12 — reject reasons zinatoka RCE, hazijaandikwa upya
# ===========================================================================


def test_max_open_trades_inapita_kama_ilivyo(cfg_risk):
    a = _check(cfg_risk, ctx=_ctx(open_positions=7))
    assert a.rce_outcome == REJECT_MAX_OPEN


def test_max_spread_inapita_kama_ilivyo(cfg_risk):
    a = _check(cfg_risk, ctx=_ctx(spread=9.0))
    assert a.rce_outcome == REJECT_MAX_SPREAD


def test_max_total_dd_inapita_kama_ilivyo(cfg_risk):
    a = _check(cfg_risk, ctx=_ctx(balance=8_500.0))
    assert a.rce_outcome in (REJECT_MAX_TOTAL_DD, L.NO_BUDGET)


def test_correlated_inapita_ikiwa_na_jina_la_kundi(cfg_risk):
    a = _check(
        cfg_risk,
        ctx=_ctx(open_positions=3, open_symbols=("GBPUSD", "AUDUSD", "NZDUSD")),
    )
    assert a.rce_outcome.startswith(REJECT_MAX_CORRELATED)


# ===========================================================================
# §11.3 — viwango vitatu, denominator tatu
# ===========================================================================


def _attempt(outcome=L.PASS, execution=None) -> L.Attempt:
    return L.Attempt(
        signal_time=NOW, symbol="EURUSD", direction="BUY", requested_price=1.1,
        rce_outcome=outcome, budget_at_signal=400.0, risk_per_trade_at_signal=57.1,
        requested_lots=0.16, allowed_lots=0.16, broker_min_lot=0.01,
        execution_outcome=execution,
    )


def test_fill_rate_denominator_ni_ORDERS_si_signals():
    """Signal iliyokataliwa na RCE haikuwahi kuwa order.

    Ikiwekwa kwenye denominator, `fill_rate` ingeshuka kwa sababu isiyo ya
    utekelezaji — na kipimo kingekuwa kikipima kitu kingine kuliko jina lake.
    """
    led = L.Ledger()
    led.extend([
        _attempt(L.PASS, L.FILL),
        _attempt(L.PASS, L.NO_FILL),
        _attempt(L.NO_BUDGET),
        _attempt(REJECT_MAX_OPEN),
    ])
    assert led.n_signals == 4 and led.n_approved == 2 and led.n_filled == 1
    assert led.fill_rate == pytest.approx(0.5), "denominator si signals"
    assert led.approval_rate == pytest.approx(0.5)


def test_mgawanyo_unajumlisha_signals_zote():
    """Jumla ya `by_outcome()` ni `n_signals`, daima. Hakuna inayopotea."""
    led = L.Ledger()
    led.extend([
        _attempt(L.PASS, L.FILL), _attempt(L.PASS, L.FILL),
        _attempt(L.PASS, L.NO_FILL), _attempt(L.NO_BUDGET),
        _attempt(L.MIN_LOT_REJECT), _attempt(REJECT_MAX_OPEN),
    ])
    assert sum(led.by_outcome().values()) == led.n_signals == 6
    assert led.by_outcome()[L.FILL] == 2


def test_madarasa_matatu_hayaunganishwi_kwenye_ripoti():
    """R14 — `NO_BUDGET`, `MIN_LOT_REJECT`, `NO_FILL` zinaonekana kando."""
    led = L.Ledger()
    led.extend([
        _attempt(L.PASS, L.NO_FILL), _attempt(L.NO_BUDGET), _attempt(L.MIN_LOT_REJECT),
    ])
    text = led.render()
    for key in (L.NO_FILL, L.NO_BUDGET, L.MIN_LOT_REJECT):
        assert key in text
    mgawanyo = led.by_outcome()
    assert mgawanyo[L.NO_BUDGET] == 1 and mgawanyo[L.MIN_LOT_REJECT] == 1


def test_ledger_tupu_hairudishi_sifuri_ya_uongo():
    """`0/0` ni `nan`, si `0.0`. Kipimo kisichoweza kuhesabiwa hakidanganyi."""
    import math

    led = L.Ledger()
    assert math.isnan(led.fill_rate) and math.isnan(led.approval_rate)


def test_ledger_inaandikwa_kwa_kila_jaribio(tmp_path):
    import json

    led = L.Ledger()
    led.extend([_attempt(L.PASS, L.FILL), _attempt(L.NO_BUDGET)])
    payload = json.loads(led.write(tmp_path / "ledger.json").read_text(encoding="utf-8"))
    assert len(payload["attempts"]) == 2
    assert payload["attempts"][1]["rce_outcome"] == L.NO_BUDGET
    assert payload["attempts"][1]["budget_at_signal"] == 400.0
