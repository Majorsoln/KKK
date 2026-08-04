"""GOLDEN TESTS — namba za spec `docs/RISK_COST_ENGINE.md` kama test vectors.

Hizi ziliandikwa **KABLA ya code** (§4.1 ya IMPLEMENTATION_PLAN: "test inaandikwa
kwanza kutoka kwenye namba za spec ... code inaandikwa mpaka test ipite").
Hakuna namba hapa iliyobuniwa: kila moja inatoka kwenye jedwali la §2 au mfano
wa §6 wa spec.

Rejista: RCE-01 (jedwali la bajeti §2), RCE-09 + RCE-13 (mfano wa §6 — lots 0.16,
hasara $34.88), G7 (lango la CI: golden test kila commit).
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from src.rce.budget import AccountState, compute_budget
from src.rce.config import load_risk_config
from src.rce.cost import CostRequest, compute_cost
from src.rce.engine import Proposal, RiskCostEngine
from src.rce.gate import GateInputs, evaluate_gate
from src.rce.lots import compute_lots
from src.rce.symbols import SymbolSpec

# --------------------------------------------------------------------------
# Muktadha wa mfano wa §6: USDJPY BUY, akaunti USD $10,000
# --------------------------------------------------------------------------

# pip_value (USDJPY, 1 lot, akaunti USD) ≈ $6.70 (spec §6).
# 0.01 (pip) × 100,000 (contract) = 1,000 JPY kwa pip → × rate(JPY→USD) = 6.70.
USDJPY_RATE_JPY_TO_USD = 6.70 / 1000.0

USDJPY = SymbolSpec(
    name="USDJPY",
    digits=3,
    point=0.001,
    pip_size=0.01,  # spec §3.1: 0.01 kwa JPY/XAU
    contract_size=100_000,
    base_ccy="USD",
    quote_ccy="JPY",
    volume_min=0.01,
    volume_step=0.01,
    volume_max=50.0,
    commission_usd_round_turn=7.0,  # spec §6: "commission $7/lot round-turn"
    swap_long=0.0,
    swap_short=0.0,
    swap_mode="CURRENCY",
)


@pytest.fixture
def cfg():
    return load_risk_config()


@pytest.fixture
def rates():
    return {("JPY", "USD"): USDJPY_RATE_JPY_TO_USD}


# --------------------------------------------------------------------------
# RCE-01 — jedwali la bajeti la §2 (safu 4 kama test vectors)
# --------------------------------------------------------------------------

# | Hali | current_balance | penalty | budget | risk/trade |
BUDGET_TABLE = [
    ("Siku ya kwanza", 10_000.0, 0.0, 0.0, 0.0, 400.0, 57.1),
    ("Baada ya DD -$200", 9_800.0, 0.0, 0.0, 100.0, 300.0, 42.9),
    ("Leo tayari -$150", 9_650.0, 0.0, 150.0, 175.0, 75.0, 10.7),
    ("Leo +$100 baada ya hapo", 9_750.0, 100.0, 150.0, 125.0, 175.0, 25.0),
]


@pytest.mark.parametrize(
    "hali,balance,today_profit,today_loss,penalty,budget,risk", BUDGET_TABLE
)
def test_jedwali_la_bajeti_la_spec_2(cfg, hali, balance, today_profit, today_loss, penalty, budget, risk):
    """Safu zote 4 za jedwali la §2 — base $400, max_open_trades 7."""
    result = compute_budget(
        AccountState(
            current_balance=balance,
            today_profit=today_profit,
            today_loss=today_loss,
        ),
        cfg,
    )
    assert result.base == pytest.approx(400.0), hali
    assert result.penalty == pytest.approx(penalty), hali
    assert result.budget == pytest.approx(budget), hali
    assert result.risk_per_trade == pytest.approx(risk, abs=0.05), hali


# --------------------------------------------------------------------------
# RCE-13 — mfano kamili wa §6 (end-to-end)
# --------------------------------------------------------------------------

SPEC6_ACCOUNT = AccountState(
    current_balance=9_800.0,  # DD ya jumla -$200 (spec §6)
    today_profit=0.0,
    today_loss=50.0,  # leo -$50
    open_positions=2,
)


def test_spec_6_bajeti_na_risk_per_trade(cfg):
    """penalty $100 · budget $250 · risk_per_trade $35.71."""
    result = compute_budget(SPEC6_ACCOUNT, cfg)
    assert result.penalty == pytest.approx(100.0)
    assert result.budget == pytest.approx(250.0)
    assert result.risk_per_trade == pytest.approx(35.71, abs=0.01)


def test_spec_6_cost_pips(cfg, rates):
    """spread 1.2 + slippage 0.3 (stop) + commission 1.04 + swap 0 = 2.54."""
    cost = compute_cost(
        CostRequest(
            symbol=USDJPY,
            direction="BUY",
            order_type="stop",
            spread_pips=1.2,
            nights=0.0,  # intraday
            entry_time=datetime(2026, 8, 4, 10, 0, tzinfo=timezone.utc),
        ),
        cfg,
        rates=rates,
    )
    assert cost.pip_value_acct == pytest.approx(6.70, abs=0.005)
    assert cost.spread_pips == pytest.approx(1.2)
    assert cost.slippage_pips == pytest.approx(0.3)
    assert cost.commission_pips == pytest.approx(1.04, abs=0.005)
    assert cost.swap_pips == pytest.approx(0.0)
    assert cost.cost_pips == pytest.approx(2.54, abs=0.005)


def test_spec_6_lots_ni_0_16_na_hasara_34_88(cfg, rates):
    """lots = 35.71 ÷ ((30 + 2.54) × 6.70) = 0.164 → 0.16; SL → $34.88 ≈ risk."""
    budget = compute_budget(SPEC6_ACCOUNT, cfg)
    cost = compute_cost(
        CostRequest(
            symbol=USDJPY,
            direction="BUY",
            order_type="stop",
            spread_pips=1.2,
            nights=0.0,
            entry_time=datetime(2026, 8, 4, 10, 0, tzinfo=timezone.utc),
        ),
        cfg,
        rates=rates,
    )
    lots = compute_lots(
        risk_per_trade=budget.risk_per_trade,
        sl_pips=30.0,
        cost=cost,
        symbol=USDJPY,
    )
    assert lots.lots_raw == pytest.approx(0.164, abs=0.001)
    assert lots.lots == pytest.approx(0.16)
    assert not lots.rejected
    assert lots.loss_at_sl == pytest.approx(34.88, abs=0.01)
    # Hasara halisi ≈ risk iliyotengwa (tofauti ni kuzungusha kwenda volume_step).
    assert abs(lots.loss_at_sl - budget.risk_per_trade) < 1.0


def test_spec_6_gate_inapita(cfg):
    """open 2 < 7 · correlated ✓ · today_loss 50 < 300 · DD 200 < 1000 · spread 1.2 ≤ 2.0 · news ✓."""
    result = evaluate_gate(
        GateInputs(
            symbol="USDJPY",
            spread_pips=1.2,
            account=SPEC6_ACCOUNT,
            open_symbols=["EURUSD", "GBPUSD"],
            news_soon=False,
        ),
        cfg,
    )
    assert result.passed
    assert result.reason is None
    assert [check.name for check in result.checks] == [
        "max_open_trades",
        "max_correlated",
        "daily_loss_brake",
        "max_total_dd",
        "max_spread",
        "news",
    ]


def test_spec_6_engine_nzima_inatoa_trade_ya_0_16_lots(cfg, rates):
    """Mnyororo mzima wa §6: pendekezo la model → trade tayari kufunguliwa."""
    engine = RiskCostEngine(cfg, rates=rates, symbols={"USDJPY": USDJPY})
    decision = engine.evaluate(
        Proposal(
            symbol="USDJPY",
            direction="BUY",
            entry=157.500,
            sl_pips=30.0,
            tp_pips=60.0,
            order_type="stop",
            nights=0.0,
            entry_time=datetime(2026, 8, 4, 10, 0, tzinfo=timezone.utc),
        ),
        account=SPEC6_ACCOUNT,
        spread_pips=1.2,
        open_symbols=["EURUSD", "GBPUSD"],
    )
    assert decision.approved
    assert decision.lots == pytest.approx(0.16)
    assert decision.cost.cost_pips == pytest.approx(2.54, abs=0.005)
    assert decision.risk_per_trade == pytest.approx(35.71, abs=0.01)
    assert decision.loss_at_sl == pytest.approx(34.88, abs=0.01)
    assert decision.reject_reason is None
