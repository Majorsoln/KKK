"""RCE-12 (hakuna signal queue), RCE-11 (DD haifungi positions), mnyororo wa engine.

Spec: `RISK_COST_ENGINE.md` §5b, §5, § mchoro wa mtiririko

Sehemu ya pili ya faili hii ni **AUDIT ya code**: inasoma `src/rce/*.py` kwa
`ast` na kukagua **majina ya vitambulisho** (si maandishi ya comments), kwa
sababu rejista inataka uthibitisho kwamba njia ya kurudia signal HAIPO kabisa —
si kwamba haikutumika leo.
"""

from __future__ import annotations

import ast
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path

import pytest

from src.rce.budget import AccountState
from src.rce.engine import Proposal, RiskCostEngine
from src.rce.gate import REASON_MAX_OPEN
from src.rce.lots import REASON_BELOW_VOLUME_MIN

RCE_DIR = Path(__file__).resolve().parents[2] / "src" / "rce"
ENTRY_TIME = datetime(2026, 8, 4, 10, 0, tzinfo=timezone.utc)


def _proposal(**overrides) -> Proposal:
    base = {
        "symbol": "USDJPY",
        "direction": "BUY",
        "entry": 157.500,
        "sl_pips": 30.0,
        "order_type": "stop",
        "entry_time": ENTRY_TIME,
        "tp_pips": 60.0,
    }
    base.update(overrides)
    return Proposal(**base)


@pytest.fixture
def engine(cfg, rates, usdjpy):
    return RiskCostEngine(cfg, rates=rates, symbols={"USDJPY": usdjpy})


HEALTHY = AccountState(current_balance=9_800.0, today_loss=50.0, open_positions=2)


# --------------------------------------------------------------------------
# Mnyororo wa hatua 1–5
# --------------------------------------------------------------------------


def test_pendekezo_zuri_linatoa_trade_tayari_kufunguliwa(engine):
    decision = engine.evaluate(_proposal(), account=HEALTHY, spread_pips=1.2)
    assert decision.approved
    assert decision.lots > 0
    assert decision.deviation_points == 3  # cap 0.3 pips × (0.01 ÷ 0.001)
    assert decision.to_log()["lifecycle"] == "APPROVED"


def test_gate_ikikataa_hakuna_lots_wala_trade(engine, cfg):
    account = AccountState(current_balance=9_800.0, open_positions=cfg.max_open_trades)
    decision = engine.evaluate(_proposal(), account=account, spread_pips=1.2)
    assert not decision.approved
    assert decision.reject_reason == REASON_MAX_OPEN
    assert decision.lots == 0.0
    assert decision.loss_at_sl == 0.0


def test_lots_chini_ya_volume_min_zinasimamisha_kabla_ya_gate(engine):
    """§4 REJECT inatokea kwenye hatua ya 4 — gate haifiki (mtiririko wa spec)."""
    broke = AccountState(current_balance=9_990.0, today_loss=395.0, open_positions=0)
    decision = engine.evaluate(_proposal(), account=broke, spread_pips=1.2)
    assert not decision.approved
    assert decision.reject_reason == REASON_BELOW_VOLUME_MIN
    assert decision.gate is None


def test_kila_uamuzi_una_config_fingerprint(engine, cfg):
    decision = engine.evaluate(_proposal(), account=HEALTHY, spread_pips=1.2)
    assert decision.config_fingerprint == cfg.fingerprint
    assert decision.to_log()["config_fingerprint"] == cfg.fingerprint


def test_swap_ya_usiku_inaingia_kwenye_gharama(engine, cfg, rates, usdjpy):
    """Pendekezo lenye usiku linabeba swap; intraday halibebi."""
    overnight_engine = RiskCostEngine(
        cfg, rates=rates, symbols={"USDJPY": replace(usdjpy, swap_long=2.0)}
    )
    intraday = overnight_engine.evaluate(_proposal(nights=0.0), HEALTHY, spread_pips=1.2)
    overnight = overnight_engine.evaluate(_proposal(nights=2.0), HEALTHY, spread_pips=1.2)
    assert intraday.cost.swap_pips == 0.0
    assert overnight.cost.swap_pips > 0.0
    assert overnight.cost.cost_pips > intraday.cost.cost_pips


def test_symbol_bila_namba_za_broker_haipewi_thamani_za_kubuni(cfg, rates):
    """Sizing kwa namba za kubuni hairuhusiwi (spec §3.3/§4)."""
    from src.rce.symbols import SymbolSpecError

    engine = RiskCostEngine(cfg, rates=rates, symbols={})
    with pytest.raises(SymbolSpecError):
        engine.evaluate(_proposal(symbol="GBPUSD"), account=HEALTHY, spread_pips=1.0)


# --------------------------------------------------------------------------
# RCE-12 — signal iliyokataliwa HAIRUDISHWI
# --------------------------------------------------------------------------


def test_engine_haihifadhi_pendekezo_lililokataliwa(engine, cfg):
    """§5b: hakuna foleni. Baada ya REJECT, engine haina kumbukumbu yake."""
    account = AccountState(current_balance=9_800.0, open_positions=cfg.max_open_trades)
    before = dict(engine.__dict__)
    engine.evaluate(_proposal(), account=account, spread_pips=1.2)
    assert engine.__dict__.keys() == before.keys()
    assert engine.__dict__ == before  # hakuna kilichoongezwa popote


def test_tathmini_ni_mpya_kila_wito(engine):
    """Kila bar ni tathmini mpya: bei/spread mpya → gharama na lots mpya."""
    first = engine.evaluate(_proposal(), HEALTHY, spread_pips=1.2)
    second = engine.evaluate(_proposal(entry=157.700), HEALTHY, spread_pips=3.0)
    assert second.cost.spread_pips == 3.0
    assert second.lots != first.lots


def test_uamuzi_hauna_njia_ya_kurudia(engine, cfg):
    """REJECT haina `retry_at`, `queue_id` wala kitu chochote cha kurudi nacho."""
    account = AccountState(current_balance=9_800.0, open_positions=cfg.max_open_trades)
    decision = engine.evaluate(_proposal(), account=account, spread_pips=1.2)
    fields = set(decision.__dataclass_fields__)
    assert not {"retry_at", "queue_id", "pending", "resubmit_after"} & fields


# --------------------------------------------------------------------------
# AUDIT ya code (RCE-12 + RCE-11)
# --------------------------------------------------------------------------


def _identifiers(path: Path) -> set[str]:
    """Majina yote ya vitambulisho kwenye module (si comments wala strings)."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            names.add(node.name)
        elif isinstance(node, ast.Name):
            names.add(node.id)
        elif isinstance(node, ast.Attribute):
            names.add(node.attr)
        elif isinstance(node, ast.arg):
            names.add(node.arg)
        elif isinstance(node, ast.keyword) and node.arg:
            names.add(node.arg)
    return {name.lower() for name in names}


def _all_identifiers() -> dict[str, set[str]]:
    return {path.name: _identifiers(path) for path in sorted(RCE_DIR.glob("*.py"))}


def test_hakuna_njia_ya_foleni_wala_retry_kwenye_src_rce():
    """RCE-12 (AUD): njia ya kurudia signal haipo kwenye code."""
    forbidden = ("queue", "requeue", "retry", "resubmit", "backlog", "pending_signal")
    offenders = {
        module: sorted(name for name in names if any(bad in name for bad in forbidden))
        for module, names in _all_identifiers().items()
    }
    assert not any(offenders.values()), offenders


def test_hakuna_function_inayofunga_positions_zilizo_wazi():
    """RCE-11 (AUD): DD inazuia entries mpya PEKEE — RCE haina njia ya kufunga."""
    forbidden = ("close_position", "position_close", "order_close", "close_all", "liquidate", "flatten")
    offenders = {
        module: sorted(name for name in names if any(bad in name for bad in forbidden))
        for module, names in _all_identifiers().items()
    }
    assert not any(offenders.values()), offenders


def test_modules_zote_za_rce_zimekaguliwa():
    """Audit isiwe ya bahati: kila module ya src/rce inapitiwa."""
    modules = set(_all_identifiers())
    assert modules >= {
        "budget.py",
        "config.py",
        "cost.py",
        "engine.py",
        "fills.py",
        "gate.py",
        "lots.py",
        "symbols.py",
    }
