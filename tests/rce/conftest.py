"""Fixtures za tests za RCE.

Symbol specs hapa ni **za test**, si za broker halisi: namba halisi za broker
(commission, swap, volumes) zinatoka `config/broker_costs.yaml` na PD ndiye
anazitoa. Thamani zilizotumika hapa zinatokana na mfano wa §6 wa spec ili
tests ziwe na uhusiano wa moja kwa moja na maneno ya spec.
"""

from __future__ import annotations

import pytest

from src.rce.config import load_risk_config
from src.rce.symbols import SymbolSpec

# Rates za test (spec §3.5): quote -> account (USD).
RATES = {
    ("JPY", "USD"): 6.70 / 1000.0,  # inatoa pip_value ya USDJPY ≈ $6.70 (§6)
    ("GBP", "USD"): 1.27,
    ("CHF", "USD"): 1.10,
}


@pytest.fixture
def cfg():
    return load_risk_config()


@pytest.fixture
def rates():
    return dict(RATES)


@pytest.fixture
def usdjpy() -> SymbolSpec:
    return SymbolSpec(
        name="USDJPY",
        digits=3,
        point=0.001,
        pip_size=0.01,
        contract_size=100_000,
        base_ccy="USD",
        quote_ccy="JPY",
        volume_min=0.01,
        volume_step=0.01,
        volume_max=50.0,
        commission_usd_round_turn=7.0,
        swap_long=0.0,
        swap_short=0.0,
        swap_mode="CURRENCY",
    )


@pytest.fixture
def eurusd() -> SymbolSpec:
    return SymbolSpec(
        name="EURUSD",
        digits=5,
        point=0.00001,
        pip_size=0.0001,
        contract_size=100_000,
        base_ccy="EUR",
        quote_ccy="USD",
        volume_min=0.01,
        volume_step=0.01,
        volume_max=50.0,
        commission_usd_round_turn=7.0,
    )


@pytest.fixture
def eurgbp() -> SymbolSpec:
    """Quote ni GBP — akaunti ya USD inahitaji conversion (spec §3.5)."""
    return SymbolSpec(
        name="EURGBP",
        digits=5,
        point=0.00001,
        pip_size=0.0001,
        contract_size=100_000,
        base_ccy="EUR",
        quote_ccy="GBP",
        volume_min=0.01,
        volume_step=0.01,
        volume_max=50.0,
        commission_usd_round_turn=7.0,
    )
