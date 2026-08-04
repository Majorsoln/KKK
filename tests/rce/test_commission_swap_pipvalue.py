"""RCE-06, RCE-07, RCE-08 — commission, swap (modes 3 + triple WED), pip conversion.

Spec: `RISK_COST_ENGINE.md` §3.3, §3.4, §3.5
"""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone

import pytest

from src.rce.config import RiskConfig
from src.rce.cost import (
    CostError,
    commission_pips,
    pip_value_account,
    swap_nights_weight,
    swap_per_night,
    swap_pips,
)

WED = datetime(2026, 8, 5, 10, 0, tzinfo=timezone.utc)  # Jumatano
TUE = datetime(2026, 8, 4, 10, 0, tzinfo=timezone.utc)  # Jumanne
THU = datetime(2026, 8, 6, 10, 0, tzinfo=timezone.utc)  # Alhamisi


def _with_commission_side(cfg: RiskConfig, side: str) -> RiskConfig:
    return RiskConfig(
        raw={**cfg.raw, "commission_side": side},
        path=cfg.path,
        broker_costs=cfg.broker_costs,
        broker_costs_path=cfg.broker_costs_path,
        fingerprint=cfg.fingerprint,
    )


# --------------------------------------------------------------------------
# RCE-06 — commission round-turn
# --------------------------------------------------------------------------


def test_commission_pips_ni_round_turn_kugawa_pip_value(cfg, usdjpy):
    """`commission_pips = commission_per_lot_round_turn ÷ pip_value_per_lot` (§6: 7 ÷ 6.70)."""
    assert cfg.commission_side == "round_turn"
    assert commission_pips(usdjpy, 6.70, cfg) == pytest.approx(7.0 / 6.70)


def test_bei_ya_upande_mmoja_inaongezwa_maradufu(cfg, usdjpy):
    """"Broker akitoa bei ya upande mmoja, inaongezwa maradufu" (§3.3)."""
    one_side = _with_commission_side(cfg, "one_side")
    assert commission_pips(usdjpy, 6.70, one_side) == pytest.approx(2 * 7.0 / 6.70)


def test_commission_side_isiyojulikana_inakataliwa(cfg, usdjpy):
    with pytest.raises(CostError):
        commission_pips(usdjpy, 6.70, _with_commission_side(cfg, "per_million"))


# --------------------------------------------------------------------------
# RCE-08 — pip conversion (§3.5)
# --------------------------------------------------------------------------


def test_quote_sawa_na_akaunti_haihitaji_rate(eurusd):
    """EURUSD, akaunti USD: pip_value = 0.0001 × 100,000 = $10."""
    assert pip_value_account(eurusd, "USD", {}) == pytest.approx(10.0)


def test_usdjpy_inabadilishwa_kwa_rate_ya_jpy(usdjpy, rates):
    """1,000 JPY kwa pip × rate(JPY→USD) ≈ $6.70 (mfano wa §6)."""
    assert pip_value_account(usdjpy, "USD", rates) == pytest.approx(6.70, abs=0.005)


def test_eurgbp_inategemea_gbpusd(eurgbp, rates):
    """Mfano wa §3.5: akaunti USD, EURGBP → pip_value inategemea GBPUSD."""
    assert pip_value_account(eurgbp, "USD", rates) == pytest.approx(10.0 * 1.27)


def test_rate_ya_kinyume_inatumika_ikiwa_ndiyo_iliyotolewa(eurgbp):
    assert pip_value_account(eurgbp, "USD", {("USD", "GBP"): 1 / 1.27}) == pytest.approx(12.7)


def test_rate_isiyopatikana_ni_hitilafu_si_dhana(usdjpy):
    with pytest.raises(CostError, match="rate"):
        pip_value_account(usdjpy, "USD", {})


def test_commission_pips_inafuata_conversion_ya_pip_value(cfg, eurgbp, rates):
    """§3.5: conversion inatumika kwenye lots NA kwenye commission/swap."""
    pip_value = pip_value_account(eurgbp, "USD", rates)
    assert commission_pips(eurgbp, pip_value, cfg) == pytest.approx(7.0 / 12.7)


# --------------------------------------------------------------------------
# RCE-07 — swap: mwelekeo · modes 3 · triple WED
# --------------------------------------------------------------------------


def test_mwelekeo_unachagua_swap_long_au_short(usdjpy):
    """Hatua 1 ya §3.4: BUY → swap_long · SELL → swap_short."""
    symbol = replace(usdjpy, swap_long=2.0, swap_short=-1.0)
    assert swap_per_night(symbol, "BUY") == pytest.approx(2.0)
    assert swap_per_night(symbol, "SELL") == pytest.approx(-1.0)


def test_mode_currency_inatumika_moja_kwa_moja(usdjpy):
    symbol = replace(usdjpy, swap_long=3.5, swap_mode="CURRENCY")
    assert swap_per_night(symbol, "BUY") == pytest.approx(3.5)


def test_mode_points_ni_swap_x_point_x_contract(usdjpy):
    """POINTS → `swap × point × contract_size` = 5 × 0.001 × 100,000 = 500."""
    symbol = replace(usdjpy, swap_long=5.0, swap_mode="POINTS")
    assert swap_per_night(symbol, "BUY") == pytest.approx(5.0 * 0.001 * 100_000)


def test_mode_interest_ni_asilimia_ya_contract(usdjpy):
    """INTEREST → `(swap ÷ 100) × contract_size` = (2/100) × 100,000 = 2,000."""
    symbol = replace(usdjpy, swap_long=2.0, swap_mode="INTEREST")
    assert swap_per_night(symbol, "BUY") == pytest.approx(2_000.0)


def test_mode_isiyojulikana_inakataliwa(usdjpy):
    from src.rce.symbols import SymbolSpecError

    with pytest.raises(SymbolSpecError):
        replace(usdjpy, swap_mode="MONTHLY")


def test_usiku_wa_jumatano_hadi_alhamisi_ni_mara_tatu(cfg):
    """Hatua 3 ya §3.4: Jumatano → Alhamisi = swap × 3."""
    assert swap_nights_weight(WED, nights=1, cfg=cfg) == pytest.approx(3.0)


def test_usiku_wa_siku_nyingine_ni_mara_moja(cfg):
    assert swap_nights_weight(TUE, nights=1, cfg=cfg) == pytest.approx(1.0)
    assert swap_nights_weight(THU, nights=1, cfg=cfg) == pytest.approx(1.0)


def test_usiku_mbili_zinazovuka_jumatano_ni_nne(cfg):
    """Jumanne→Jumatano (×1) + Jumatano→Alhamisi (×3) = 4."""
    assert swap_nights_weight(TUE, nights=2, cfg=cfg) == pytest.approx(4.0)


def test_usiku_wa_sehemu_unapewa_uzito_wa_sehemu(cfg):
    """Takwimu za strategy zinaweza kutoa 3.5 usiku (mfano wa spec §3.4)."""
    assert swap_nights_weight(WED, nights=1.5, cfg=cfg) == pytest.approx(3.0 + 0.5)


def test_intraday_haina_swap(cfg, usdjpy):
    """"H1 intraday = 0" — swap inatozwa TU kama trade iko wazi wakati wa rollover."""
    assert swap_nights_weight(TUE, nights=0, cfg=cfg) == 0.0
    symbol = replace(usdjpy, swap_long=10.0)
    assert swap_pips(symbol, "BUY", 0.0, TUE, 6.70, cfg) == 0.0


def test_swap_pips_ni_jumla_kugawa_pip_value(cfg, usdjpy):
    """Hatua 4: `swap_pips = jumla ya usiku zote ÷ pip_value_per_lot`."""
    symbol = replace(usdjpy, swap_long=2.0, swap_mode="CURRENCY")
    # Jumanne + usiku 2 → uzito 4 (moja ni ya Jumatano) → jumla 8.0
    assert swap_pips(symbol, "BUY", 2.0, TUE, 6.70, cfg) == pytest.approx(8.0 / 6.70)


def test_swap_ikizimwa_kwenye_config_haiingii_kwenye_gharama(cfg, usdjpy):
    disabled = RiskConfig(
        raw={**cfg.raw, "swap": {**cfg.raw["swap"], "enabled": False}},
        path=cfg.path,
        broker_costs=cfg.broker_costs,
        broker_costs_path=cfg.broker_costs_path,
        fingerprint=cfg.fingerprint,
    )
    symbol = replace(usdjpy, swap_long=2.0)
    assert swap_pips(symbol, "BUY", 3.0, TUE, 6.70, disabled) == 0.0
