"""RCE end-to-end — pendekezo → uamuzi (spec §0, §6) + mkataba na KAIROS-1 (§4)."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from src.rce.budget import AccountState
from src.rce.cost import SymbolSpec
from src.rce.engine import MarketContext, Proposal, cost_context_for_model, evaluate
from src.rce.gate import REJECT_MAX_OPEN
from src.rce.sizing import REJECT_BELOW_MIN_LOT

USDJPY = SymbolSpec(
    symbol="USDJPY",
    point=0.001,
    contract_size=100_000,
    volume_min=0.01,
    volume_step=0.01,
    volume_max=100.0,
)


def _ctx(**kwargs) -> MarketContext:
    base = dict(
        account=AccountState(current_balance=9_800.0, today_loss=50.0, open_positions=2),
        spec=USDJPY,
        h1_spreads=[1.2] * 100,
        m5_spreads=[1.0] * 288,
        pip_value_acct=6.70,
        commission_round_turn=7.0,
        open_symbols=("EURUSD", "GBPUSD"),
        now=datetime(2026, 8, 6, 12, 0, tzinfo=timezone.utc),
    )
    base.update(kwargs)
    return MarketContext(**base)


PROPOSAL = Proposal(
    symbol="USDJPY",
    direction="BUY",
    entry=155.0,
    sl_pips=30.0,
    tp_pips=60.0,
    order_type="stop",
)


def test_end_to_end_inatoa_namba_za_spec_6(risk_cfg):
    """Mfano wa §6 ukipita mnyororo mzima: lots 0.16, hasara ≈ $34.88."""
    order = evaluate(risk_cfg, PROPOSAL, _ctx())
    assert order.approved, order.reason
    assert order.cost.cost_pips == pytest.approx(2.54, abs=0.01)
    assert order.lots == pytest.approx(0.16)
    assert order.sizing.risk_at_stop == pytest.approx(34.88, abs=0.05)
    assert order.deviation_points == 3


def test_cost_pips_ni_ILE_ILE_kwa_model_na_kwa_sizing(risk_cfg):
    """§4.2: chanzo KIMOJA, matumizi MAWILI — hakuna kuhesabu mara mbili."""
    ctx = _ctx()
    order = evaluate(risk_cfg, PROPOSAL, ctx)
    kwa_model = cost_context_for_model(risk_cfg, ctx, order_type="stop")
    assert kwa_model["cost_pips"] == pytest.approx(order.cost.cost_pips)
    assert kwa_model["slots_remaining"] == 5


def test_gate_ikikataa_hakuna_lots(risk_cfg):
    order = evaluate(
        risk_cfg,
        PROPOSAL,
        _ctx(account=AccountState(current_balance=9_800.0, open_positions=7)),
    )
    assert not order.approved
    assert order.reason == REJECT_MAX_OPEN
    assert order.lots == 0.0
    assert order.to_log()["lifecycle"] == "REJECTED"


def test_risk_ndogo_kuliko_lot_ya_chini_ni_reject(risk_cfg):
    """§4: budget ndogo → lots chini ya `volume_min` → REJECT yenye sababu."""
    order = evaluate(
        risk_cfg,
        PROPOSAL,
        _ctx(account=AccountState(current_balance=9_100.0, today_loss=350.0)),
    )
    assert not order.approved
    assert order.reason == REJECT_BELOW_MIN_LOT


def test_rce_hairudi_kubadilisha_entry_wala_mwelekeo(risk_cfg):
    """§4.3: RCE inaamua ukubwa na ruhusa; model inaamua entry na mwelekeo."""
    order = evaluate(risk_cfg, PROPOSAL, _ctx())
    assert order.proposal.entry == PROPOSAL.entry
    assert order.proposal.direction == PROPOSAL.direction
    assert order.proposal.sl_pips == PROPOSAL.sl_pips
    assert not hasattr(order.proposal, "lots")
