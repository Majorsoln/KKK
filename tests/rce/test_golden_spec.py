"""GOLDEN TESTS — namba zinatoka `docs/RISK_COST_ENGINE.md` NENO KWA NENO.

Hizi ndizo tests zilizoandikwa **KABLA** ya code (§4.1 ya IMPLEMENTATION_PLAN).
Zikibadilika, ni kwa sababu PD amebadilisha spec — si kwa sababu code
imebadilika. Ndiyo maana kila assert inataja sehemu ya spec inayotoka.
"""

from __future__ import annotations

import pytest

from src.rce.budget import AccountState, compute_budget
from src.rce.cost import (
    SymbolSpec,
    commission_pips,
    order_deviation_points,
    pip_size,
    slippage_cap_pips,
    spread_effective,
)
from src.rce.gate import GateContext, evaluate_gate
from src.rce.sizing import compute_lots

USDJPY = SymbolSpec(
    symbol="USDJPY",
    point=0.001,
    contract_size=100_000,
    volume_min=0.01,
    volume_step=0.01,
    volume_max=100.0,
)


# ===========================================================================
# RCE-01 — jedwali la bajeti (spec §2, safu NNE)
# ===========================================================================


@pytest.mark.parametrize(
    "current_balance, today_profit, today_loss, penalty, budget, risk",
    [
        # | Hali                    | current | penalty | budget | risk/trade |
        (10_000.0, 0.0, 0.0, 0.0, 400.0, 57.1),  # Siku ya kwanza
        (9_800.0, 0.0, 0.0, 100.0, 300.0, 42.9),  # Baada ya DD −$200
        (9_650.0, 0.0, 150.0, 175.0, 75.0, 10.7),  # Leo tayari −$150
        (9_750.0, 100.0, 150.0, 125.0, 175.0, 25.0),  # Leo +$100 baada ya hapo
    ],
)
def test_rce01_jedwali_la_bajeti(
    risk_cfg, current_balance, today_profit, today_loss, penalty, budget, risk
):
    """Spec §2: safu zote nne za jedwali la mfano."""
    result = compute_budget(
        risk_cfg,
        AccountState(
            current_balance=current_balance,
            today_profit=today_profit,
            today_loss=today_loss,
        ),
    )
    assert result.base == pytest.approx(400.0)
    assert result.penalty == pytest.approx(penalty)
    assert result.budget == pytest.approx(budget)
    assert result.risk_per_trade == pytest.approx(risk, abs=0.05)


def test_rce01_penalty_inafuata_dd_ya_jumla_si_ya_leo(risk_cfg):
    """Spec §2: `penalty` HAIRESETIWI — inafuata DD tangu mwanzo."""
    faida_leo = compute_budget(
        risk_cfg, AccountState(current_balance=9_800.0, today_profit=500.0)
    )
    assert faida_leo.penalty == pytest.approx(100.0), (
        "faida ya leo haipaswi kupunguza penalty — DD ya jumla ndiyo msingi"
    )


# ===========================================================================
# RCE-03 — spread: MSETO (spec §3.1)
# ===========================================================================


def test_rce03_spread_effective_ni_max_ya_h1_na_p95_ya_m5(risk_cfg):
    """Spec §3.1: `spread_effective = max(spread_base, spread_vol_adj)`."""
    h1 = [1.0] * 100  # wastani 1.0
    m5 = [0.5] * 287 + [9.0]  # p95 chini ya spike moja
    assert spread_effective(h1, m5, risk_cfg) == pytest.approx(1.0)

    m5_spiky = [0.5] * 200 + [4.0] * 88  # p95 sasa iko juu ya H1
    assert spread_effective(h1, m5_spiky, risk_cfg) == pytest.approx(4.0)


def test_rce03_m5_peke_yake_haiwezi_kushusha_makadirio(risk_cfg):
    """Spec §3.1: kutumia M5 peke yake = kudharau gharama → EV ya bandia."""
    h1 = [2.0] * 100
    m5_ndogo = [0.1] * 288
    assert spread_effective(h1, m5_ndogo, risk_cfg) == pytest.approx(2.0)


# ===========================================================================
# RCE-04 — slippage: CAP inayobana, isiyolegea (spec §3.2)
# ===========================================================================


def test_rce04_cap_inabana_tu(risk_cfg):
    """Spec §3.2: `cap = min(dynamic, backtest)` — soko tulivu → cap ngumu."""
    assert slippage_cap_pips("stop", risk_cfg, dynamic_estimate=0.1) == pytest.approx(0.1)


def test_rce04_cap_hailegei_soko_likichafuka(risk_cfg):
    """Spec §3.2: cap **HAIZIDI** dhana ya backtest — dhamana ya live ≤ backtest."""
    assert slippage_cap_pips("stop", risk_cfg, dynamic_estimate=5.0) == pytest.approx(0.3)
    assert slippage_cap_pips("market", risk_cfg, dynamic_estimate=5.0) == pytest.approx(0.1)


def test_rce04_deviation_ni_points_si_pips():
    """Spec §3.2: MT5 inatumia POINTS — `cap × (PipSize ÷ point)`.

    Broker wa digiti 5: pip = points 10, kwa hiyo pips 0.3 = points 3.
    Broker wa digiti 4 (pip == point): pips 0.3 hazionyeshiki — inashuka hadi 0,
    yaani "hakuna slippage inayoruhusiwa". Hiyo ni sahihi kwa §3.2 (cap INABANA,
    hailegei) lakini inapunguza fill rate — DF-04/`fill_rate` itaionyesha.
    """
    assert order_deviation_points(0.3, "USDJPY", point=0.001) == 3
    assert order_deviation_points(0.3, "EURUSD", point=0.00001) == 3
    assert order_deviation_points(1.0, "EURUSD", point=0.00001) == 10
    assert order_deviation_points(0.3, "EURUSD", point=0.0001) == 0


# ===========================================================================
# RCE-06 — commission ni round-turn (spec §3.3)
# ===========================================================================


def test_rce06_commission_pips_ya_mfano_wa_spec():
    """Spec §6: `commission_pips = 7 ÷ 6.70 = 1.04`."""
    assert commission_pips(7.0, 6.70) == pytest.approx(1.04, abs=0.005)


# ===========================================================================
# RCE-13 — MFANO KAMILI end-to-end (spec §6)
# ===========================================================================


def test_rce13_mfano_kamili_wa_spec(risk_cfg):
    """Spec §6, mstari kwa mstari.

    Akaunti $10,000 · base 4% · DD ya jumla −$200 · leo −$50 · positions 2
    USDJPY BUY · SL 30 pips · spread 1.2 · stop-order · commission $7 · usiku 0
    """
    state = AccountState(current_balance=9_800.0, today_loss=50.0, open_positions=2)
    budget = compute_budget(risk_cfg, state)
    assert budget.penalty == pytest.approx(100.0)
    assert budget.budget == pytest.approx(250.0)
    assert budget.risk_per_trade == pytest.approx(35.71, abs=0.01)

    pip_value = 6.70
    spread = 1.2
    slippage = slippage_cap_pips("stop", risk_cfg)
    comm = commission_pips(7.0, pip_value)
    swap = 0.0  # intraday
    cost_pips = spread + slippage + comm + swap

    assert slippage == pytest.approx(0.3)
    assert cost_pips == pytest.approx(2.54, abs=0.01)

    sizing = compute_lots(
        risk_per_trade=budget.risk_per_trade,
        sl_pips=30.0,
        cost_pips=cost_pips,
        pip_value_acct=pip_value,
        spec=USDJPY,
    )
    assert sizing.lots_raw == pytest.approx(0.164, abs=0.001)
    assert sizing.lots == pytest.approx(0.16)

    # Uthibitisho wa spec: 0.16 × 32.54 × 6.70 = $34.88 ≈ risk iliyotengwa
    assert sizing.risk_at_stop == pytest.approx(34.88, abs=0.05)
    assert sizing.risk_at_stop <= budget.risk_per_trade, (
        "hasara kwenye SL HAIPASWI kuzidi risk iliyotengwa (§4)"
    )

    decision = evaluate_gate(
        risk_cfg,
        GateContext(
            symbol="USDJPY",
            open_positions=2,
            open_symbols=("EURUSD", "GBPUSD"),
            current_balance=9_800.0,
            today_loss=50.0,
            spread_pips=spread,
        ),
    )
    assert decision.passed, f"spec §6 inasema PASS, tumepata {decision.reason}"


def test_rce09_pip_size_ya_symbols():
    """Spec §3.1: JPY/XAU → 0.01; nyingine → 0.0001."""
    assert pip_size("USDJPY") == 0.01
    assert pip_size("EURJPY") == 0.01
    assert pip_size("XAUUSD") == 0.01
    assert pip_size("EURUSD") == 0.0001
    assert pip_size("GBPUSD") == 0.0001
