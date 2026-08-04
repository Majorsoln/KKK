"""Namba za broker: `config/broker_costs.yaml` (spec §3.3, §3.4, §4).

Sheria inayolindwa hapa: **hakuna sizing kwa namba za kubuni.** Namba za broker
ni za PD; zisipokuwepo au zisipothibitishwa, RCE inasimama badala ya kukisia.
"""

from __future__ import annotations

import pytest
import yaml

from src.rce.config import default_broker_costs_path, load_risk_config
from src.rce.symbols import SymbolSpecError, missing_broker_numbers, pip_size_for, symbol_spec

FULL_ENTRY = {
    "digits": 3,
    "point": 0.001,
    "contract_size": 100_000,
    "base_ccy": "USD",
    "quote_ccy": "JPY",
    "volume_min": 0.01,
    "volume_step": 0.01,
    "volume_max": 50.0,
    "commission_usd_round_turn": 7.0,
}


def _config_with_costs(tmp_path, costs: dict, cfg):
    tmp_path.mkdir(parents=True, exist_ok=True)
    path = tmp_path / "broker_costs.yaml"
    path.write_text(yaml.safe_dump(costs), encoding="utf-8")
    return load_risk_config(cfg.path, broker_costs_path=path)


def test_template_ya_repo_haijathibitishwa_bado(cfg):
    """Hadhi ya sasa: nafasi tupu — PD anajaza namba za broker."""
    assert default_broker_costs_path().is_file()
    assert cfg.broker_costs.get("confirmed_by_pd") is False


def test_symbols_zote_12_zipo_kwenye_template(cfg):
    listed = set(cfg.broker_costs.get("symbols", {}))
    assert len(listed) == 12
    assert {"EURUSD", "USDJPY", "XAUUSD", "GBPJPY", "EURCHF"} <= listed


def test_template_isiyothibitishwa_inazuia_sizing(cfg):
    with pytest.raises(SymbolSpecError, match="confirmed_by_pd"):
        symbol_spec(cfg, "USDJPY")


def test_ripoti_ya_mapengo_inamwambia_pd_kinachokosekana(cfg):
    gaps = missing_broker_numbers(cfg)
    assert any("USDJPY" in gap for gap in gaps)
    assert any("commission_usd_round_turn" in gap for gap in gaps)


def test_symbol_iliyojazwa_inatoa_spec_kamili(cfg, tmp_path):
    costs = {"confirmed_by_pd": True, "symbols": {"USDJPY": FULL_ENTRY}}
    filled = _config_with_costs(tmp_path, costs, cfg)
    spec = symbol_spec(filled, "USDJPY")
    assert spec.commission_usd_round_turn == 7.0
    assert spec.pip_size == 0.01  # spec §3.1: JPY → 0.01
    assert spec.pips_per_point == pytest.approx(10.0)


def test_defaults_zinaunganishwa_na_symbol(cfg, tmp_path):
    costs = {
        "confirmed_by_pd": True,
        "defaults": {"volume_min": 0.01, "volume_step": 0.01, "volume_max": 50.0},
        "symbols": {
            "USDJPY": {k: v for k, v in FULL_ENTRY.items() if not k.startswith("volume")}
        },
    }
    filled = _config_with_costs(tmp_path, costs, cfg)
    assert symbol_spec(filled, "USDJPY").volume_step == 0.01


def test_field_iliyokosekana_inatajwa_kwa_jina(cfg, tmp_path):
    entry = {k: v for k, v in FULL_ENTRY.items() if k != "commission_usd_round_turn"}
    filled = _config_with_costs(tmp_path, {"confirmed_by_pd": True, "symbols": {"USDJPY": entry}}, cfg)
    with pytest.raises(SymbolSpecError, match="commission_usd_round_turn"):
        symbol_spec(filled, "USDJPY")


def test_symbol_isiyo_kwenye_faili_inakataliwa(cfg, tmp_path):
    filled = _config_with_costs(tmp_path, {"confirmed_by_pd": True, "symbols": {"USDJPY": FULL_ENTRY}}, cfg)
    with pytest.raises(SymbolSpecError, match="GBPUSD"):
        symbol_spec(filled, "GBPUSD")


def test_pip_size_inafuata_sheria_ya_spec_3_1():
    assert pip_size_for("USDJPY") == 0.01
    assert pip_size_for("XAUUSD") == 0.01
    assert pip_size_for("EURUSD") == 0.0001
    assert pip_size_for("EURGBP") == 0.0001


def test_broker_costs_inaingia_kwenye_fingerprint(cfg, tmp_path):
    """Namba za broker zikibadilika, fingerprint ya uamuzi inabadilika pia."""
    first = _config_with_costs(tmp_path / "a", {"confirmed_by_pd": True, "symbols": {}}, cfg)
    second = _config_with_costs(
        tmp_path / "b", {"confirmed_by_pd": True, "symbols": {"USDJPY": FULL_ENTRY}}, cfg
    )
    assert first.fingerprint != second.fingerprint
