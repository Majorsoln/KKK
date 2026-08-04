"""RCE-10, RCE-11 — viability gate: checks 6 kwa mpangilio + REJECT reasons.

Spec: `RISK_COST_ENGINE.md` §5
"""

from __future__ import annotations

import pytest

from src.rce.budget import AccountState
from src.rce.gate import (
    CHECK_ORDER,
    REASON_DAILY_LOSS,
    REASON_MAX_CORRELATED,
    REASON_MAX_OPEN,
    REASON_MAX_SPREAD,
    REASON_MAX_TOTAL_DD,
    REASON_NEWS,
    GateInputs,
    evaluate_gate,
)
from src.rce.config import RiskConfig

HEALTHY = AccountState(current_balance=10_000.0, open_positions=1)


def _inputs(**overrides) -> GateInputs:
    base = {
        "symbol": "EURUSD",
        "spread_pips": 1.0,
        "account": HEALTHY,
        "open_symbols": ["USDJPY"],
        "news_soon": False,
    }
    base.update(overrides)
    return GateInputs(**base)


def _with(cfg: RiskConfig, **overrides) -> RiskConfig:
    return RiskConfig(
        raw={**cfg.raw, **overrides},
        path=cfg.path,
        broker_costs=cfg.broker_costs,
        broker_costs_path=cfg.broker_costs_path,
        fingerprint=cfg.fingerprint,
    )


def test_gate_safi_inapita_na_checks_zote_sita(cfg):
    result = evaluate_gate(_inputs(), cfg)
    assert result.passed and result.reason is None
    assert [c.name for c in result.checks] == list(CHECK_ORDER)


# ---------- check 1 ----------


def test_max_open_trades(cfg):
    account = AccountState(current_balance=10_000.0, open_positions=cfg.max_open_trades)
    result = evaluate_gate(_inputs(account=account), cfg)
    assert result.reason == REASON_MAX_OPEN
    assert [c.name for c in result.checks] == ["max_open_trades"]  # zilizobaki hazikimbii


# ---------- check 2 ----------


def test_max_correlated_inahesabu_makundi_yote_ya_pair(cfg):
    """EURUSD iko USD_group NA EUR_group — kundi lolote likijaa, ni REJECT."""
    assert set(cfg.groups_of("EURUSD")) == {"USD_group", "EUR_group"}
    result = evaluate_gate(
        _inputs(open_symbols=["EURJPY", "EURGBP", "EURUSD"]), cfg
    )
    assert result.reason == f"{REASON_MAX_CORRELATED}:EUR_group"


def test_exposure_chini_ya_kikomo_inapita(cfg):
    result = evaluate_gate(_inputs(open_symbols=["EURJPY", "EURGBP"]), cfg)
    assert result.passed


def test_symbol_isiyo_na_kundi_haizuiwi(cfg):
    result = evaluate_gate(_inputs(symbol="XAUUSD", spread_pips=10.0), cfg)
    assert result.passed


# ---------- check 3 ----------


def test_daily_loss_brake_inahitaji_positions_wazi(cfg):
    """`today_loss ≥ 0.75 × base` NA open > 0 → kataa. Bila positions wazi → inapita."""
    brake = cfg.daily_loss_stop_frac * cfg.base_percentage * cfg.base_balance
    assert brake == pytest.approx(300.0)

    with_open = AccountState(current_balance=9_700.0, today_loss=brake, open_positions=1)
    assert evaluate_gate(_inputs(account=with_open), cfg).reason == REASON_DAILY_LOSS

    flat = AccountState(current_balance=9_700.0, today_loss=brake, open_positions=0)
    assert evaluate_gate(_inputs(account=flat), cfg).passed


def test_hasara_chini_ya_kizingiti_inapita(cfg):
    account = AccountState(current_balance=9_750.0, today_loss=250.0, open_positions=1)
    assert evaluate_gate(_inputs(account=account), cfg).passed


# ---------- check 4 (RCE-11) ----------


def test_total_dd_inakataa_entry_mpya(cfg):
    account = AccountState(current_balance=cfg.base_balance - cfg.max_total_dd, open_positions=1)
    result = evaluate_gate(_inputs(account=account), cfg)
    assert result.reason == REASON_MAX_TOTAL_DD


def test_dd_inazuia_entries_mpya_pekee_haifungi_positions(cfg):
    """RCE-11: gate inarudisha REJECT ya pendekezo — haina njia ya kufunga positions."""
    account = AccountState(current_balance=8_500.0, open_positions=3)
    result = evaluate_gate(_inputs(account=account), cfg)
    assert result.reason == REASON_MAX_TOTAL_DD
    log = result.to_log("EURUSD")
    assert log["lifecycle"] == "REJECTED"
    assert not any(
        key in str(log).lower() for key in ("close_positions", "flatten", "liquidate")
    )


# ---------- check 5 ----------


def test_max_spread_kwa_symbol(cfg):
    assert cfg.max_spread["EURUSD"] == 2.0
    assert evaluate_gate(_inputs(spread_pips=2.0), cfg).passed  # `≤` ni sehemu ya spec
    assert evaluate_gate(_inputs(spread_pips=2.1), cfg).reason == REASON_MAX_SPREAD


def test_symbol_isiyo_na_max_spread_inaripotiwa_kama_pengo_la_config(cfg):
    """Code haibuni kikomo; inaripoti pengo ili PD alijaze."""
    result = evaluate_gate(_inputs(symbol="EURJPY", spread_pips=99.0), cfg)
    assert result.passed
    assert "max_spread_unset:EURJPY" in result.warnings


# ---------- check 6 ----------


def test_news_inazuia_pale_trade_news_ni_false(cfg):
    no_news = _with(cfg, trade_news=False)
    assert evaluate_gate(_inputs(news_soon=True), no_news).reason == REASON_NEWS
    assert evaluate_gate(_inputs(news_soon=False), no_news).passed


def test_trade_news_ikiwa_true_haizuii(cfg):
    assert evaluate_gate(_inputs(news_soon=True), cfg).passed


# ---------- mpangilio + fingerprint ----------


def test_mpangilio_ndio_unaoamua_sababu_pale_nyingi_zinafeli(cfg):
    """Checks nyingi zikifeli, ya kwanza kwa mpangilio wa §5 ndiyo sababu."""
    account = AccountState(
        current_balance=8_000.0,  # DD (check 4)
        today_loss=400.0,  # brake (check 3)
        open_positions=cfg.max_open_trades,  # check 1
    )
    result = evaluate_gate(_inputs(account=account, spread_pips=99.0), cfg)
    assert result.reason == REASON_MAX_OPEN


def test_mpangilio_wa_pili_ni_correlated_kisha_brake(cfg):
    account = AccountState(current_balance=8_000.0, today_loss=400.0, open_positions=3)
    result = evaluate_gate(
        _inputs(account=account, open_symbols=["EURJPY", "EURGBP", "EURUSD"]), cfg
    )
    assert result.reason == f"{REASON_MAX_CORRELATED}:EUR_group"


def test_kila_reject_ina_sababu_na_config_fingerprint(cfg):
    """§5: rekodi ya `lifecycle=REJECTED` + sababu + config-fingerprint."""
    account = AccountState(current_balance=10_000.0, open_positions=cfg.max_open_trades)
    result = evaluate_gate(_inputs(account=account), cfg)
    log = result.to_log("EURUSD")
    assert log["lifecycle"] == "REJECTED"
    assert log["reason"] == REASON_MAX_OPEN
    assert log["config_fingerprint"] == cfg.fingerprint
    assert len(cfg.fingerprint) == 64
    assert cfg.short_fingerprint == cfg.fingerprint[:12]


def test_fingerprint_inabadilika_config_ikibadilika(cfg, tmp_path):
    from src.rce.config import load_risk_config

    edited = tmp_path / "risk.yaml"
    edited.write_text(cfg.path.read_text().replace("max_open_trades:       7", "max_open_trades:       5"))
    assert load_risk_config(edited).fingerprint != cfg.fingerprint
