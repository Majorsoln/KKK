"""RCE-09 — lots: fomula ya §4 + volume_step/min/max + REJECT.

Spec: `RISK_COST_ENGINE.md` §4
"""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone

import pytest

from src.rce.cost import CostRequest, compute_cost
from src.rce.lots import REASON_BELOW_VOLUME_MIN, compute_lots

ENTRY_TIME = datetime(2026, 8, 4, 10, 0, tzinfo=timezone.utc)


@pytest.fixture
def cost(cfg, usdjpy, rates):
    return compute_cost(
        CostRequest(
            symbol=usdjpy,
            direction="BUY",
            order_type="stop",
            spread_pips=1.2,
            entry_time=ENTRY_TIME,
        ),
        cfg,
        rates=rates,
    )


def test_gharama_iko_kwenye_denominator(cost, usdjpy):
    """`lots = risk ÷ ((sl + cost) × pipval)` — si `sl × pipval` pekee."""
    result = compute_lots(risk_per_trade=35.71, sl_pips=30.0, cost=cost, symbol=usdjpy)
    assert result.denominator == pytest.approx((30.0 + cost.cost_pips) * cost.pip_value_acct)


def test_hasara_ya_sl_ni_risk_iliyotengwa(cost, usdjpy):
    """Ahadi ya §4: SL ikigongwa, hasara (pamoja na gharama) ≈ risk_per_trade."""
    fine_step = replace(usdjpy, volume_step=0.001, volume_min=0.001)
    result = compute_lots(risk_per_trade=35.71, sl_pips=30.0, cost=cost, symbol=fine_step)
    assert result.loss_at_sl == pytest.approx(35.71, abs=0.25)


def test_gharama_kubwa_inapunguza_lots(cost, usdjpy):
    """Gharama ikipanda, position inapungua — si kinyume."""
    small = compute_lots(35.71, 30.0, cost, usdjpy).lots_raw
    expensive = replace(cost, cost_pips=cost.cost_pips * 5)
    assert compute_lots(35.71, 30.0, expensive, usdjpy).lots_raw < small


def test_lots_inazungushwa_chini_kwa_volume_step(cost, usdjpy):
    """Kuzungusha juu kungepitisha hasara juu ya risk — kwa hiyo ni floor."""
    result = compute_lots(35.71, 30.0, cost, usdjpy)
    assert result.lots_raw == pytest.approx(0.1638, abs=0.001)
    assert result.lots == pytest.approx(0.16)
    assert result.lots <= result.lots_raw


def test_step_ya_broker_yenye_0_1_inaheshimiwa(cost, usdjpy):
    coarse = replace(usdjpy, volume_step=0.1, volume_min=0.1)
    result = compute_lots(350.0, 30.0, cost, coarse)
    assert result.lots_raw == pytest.approx(1.605, abs=0.005)
    assert result.lots == pytest.approx(1.6)  # floor kwa step 0.1


def test_chini_ya_volume_min_ni_reject(cost, usdjpy):
    """"risk ndogo kuliko lot ya chini" → REJECT, si kuzungusha juu."""
    result = compute_lots(risk_per_trade=1.0, sl_pips=30.0, cost=cost, symbol=usdjpy)
    assert result.rejected
    assert result.reason == REASON_BELOW_VOLUME_MIN
    assert result.lots == 0.0
    assert result.loss_at_sl == 0.0


def test_volume_max_ni_kikomo_cha_juu(cost, usdjpy):
    limited = replace(usdjpy, volume_max=0.05)
    result = compute_lots(risk_per_trade=35.71, sl_pips=30.0, cost=cost, symbol=limited)
    assert result.lots == pytest.approx(0.05)
    assert result.capped_at_volume_max


def test_budget_hasi_inaishia_reject(cost, usdjpy):
    """Bajeti ikiisha (penalty + hasara ya leo), lots hazipo — REJECT."""
    result = compute_lots(risk_per_trade=-10.0, sl_pips=30.0, cost=cost, symbol=usdjpy)
    assert result.rejected and result.lots == 0.0


def test_sl_isiyo_chanya_inakataliwa(cost, usdjpy):
    with pytest.raises(ValueError):
        compute_lots(35.71, 0.0, cost, usdjpy)
