"""RCE-03, RCE-04 — spread ya mseto na slippage cap.

Spec: `RISK_COST_ENGINE.md` §3.1 (spread MSETO) na §3.2 (cap, si utabiri)
"""

from __future__ import annotations

import pytest

from src.rce.cost import CostError, deviation_points, slippage_cap, spread_effective, spread_pips


# --------------------------------------------------------------------------
# RCE-03 — spread_effective = max(H1 base, M5 p95)
# --------------------------------------------------------------------------


def test_spread_pips_kutoka_bid_ask():
    """`spread_pips = (Ask − Bid) ÷ PipSize`."""
    assert spread_pips(1.09000, 1.09012, 0.0001) == pytest.approx(1.2)
    assert spread_pips(157.500, 157.512, 0.01) == pytest.approx(1.2)


def test_p95_ya_m5_inashinda_pale_kuna_spikes(cfg):
    """H1 tulivu + spikes za M5 → M5 p95 ndiyo inayotumika (kinga ya spikes)."""
    result = spread_effective([1.0] * 100, [1.0] * 268 + [5.0] * 20, cfg)
    assert result.base == pytest.approx(1.0)
    assert result.spike > result.base
    assert result.effective == result.spike
    assert result.source == "M5_p95"


def test_wastani_wa_h1_unashinda_pale_m5_ni_tulivu(cfg):
    """Bila spikes, msingi wa H1 ndio unaotumika (entry inatokea H1)."""
    result = spread_effective([2.0] * 100, [1.0] * 288, cfg)
    assert result.effective == pytest.approx(2.0)
    assert result.source == "H1_base"


def test_effective_kamwe_haishuki_chini_ya_vipimo_viwili(cfg):
    """`max` — kutumia M5 pekee ni kudharau gharama (spec §3.1)."""
    result = spread_effective([1.5] * 100, [0.8] * 288, cfg)
    assert result.effective >= result.base
    assert result.effective >= result.spike


def test_windows_za_config_ndizo_zinazotumika(cfg):
    """base_window 100 (H1) na spike_window 288 (M5) — data ya zamani haiingii."""
    assert (cfg.spread_base_window, cfg.spread_spike_window) == (100, 288)
    old_then_calm = [50.0] * 500 + [1.0] * 100
    result = spread_effective(old_then_calm, [1.0] * 288, cfg)
    assert result.base == pytest.approx(1.0)


def test_quantile_ni_ile_ya_config(cfg):
    assert cfg.spread_spike_quantile == 0.95
    values = list(range(1, 101))  # p95 kwa interpolation ya linear = 95.05
    result = spread_effective([1.0] * 100, values, cfg)
    assert result.spike == pytest.approx(95.05, abs=0.01)


def test_combine_isiyo_max_inakataliwa(cfg):
    """Spec §3.1 inafafanua `max` pekee — combine nyingine si spec."""
    changed = dict(cfg.raw)
    changed["spread_model"] = {**cfg.raw["spread_model"], "combine": "mean"}
    broken = type(cfg)(
        raw=changed,
        path=cfg.path,
        broker_costs=cfg.broker_costs,
        broker_costs_path=cfg.broker_costs_path,
        fingerprint=cfg.fingerprint,
    )
    with pytest.raises(CostError, match="max"):
        spread_effective([1.0] * 100, [1.0] * 288, broken)


# --------------------------------------------------------------------------
# RCE-04 — slippage ni CAP: inabana TU, hailegei
# --------------------------------------------------------------------------


def test_cap_za_config_ni_zile_za_episodes(cfg):
    """`SLIP_MARKET = 0.1` · `SLIP_STOP = 0.3` (kanuni ya dhahabu ya §3.2)."""
    assert cfg.slippage_cap_pips == {"market": 0.1, "stop": 0.3}


def test_dynamic_kubwa_kuliko_dhana_haipandishi_cap(cfg):
    """Soko likichafuka, cap HAIZIDI dhana ya backtest — "live ≤ backtest"."""
    cap = slippage_cap(cfg, "stop", dynamic_estimate_pips=5.0)
    assert cap.cap_pips == pytest.approx(0.3)
    assert cap.binding == "backtest_assumption"


def test_dynamic_ndogo_inabana_cap(cfg):
    """Soko likiwa tulivu, M5 inaruhusu cap ngumu zaidi (fills bora)."""
    cap = slippage_cap(cfg, "stop", dynamic_estimate_pips=0.12)
    assert cap.cap_pips == pytest.approx(0.12)
    assert cap.binding == "dynamic"


def test_bila_dynamic_cap_ni_dhana_ya_backtest(cfg):
    assert slippage_cap(cfg, "market").cap_pips == pytest.approx(0.1)


def test_order_type_isiyo_kwenye_config_inakataliwa(cfg):
    """`limit` haina cap kwenye spec/config — code haibuni kikomo (G10)."""
    with pytest.raises(CostError, match="limit"):
        slippage_cap(cfg, "limit")


def test_deviation_inatolewa_kwa_points(usdjpy, eurusd):
    """`order.deviation = cap × (PipSize ÷ point)` — MT5 inatumia POINTS."""
    assert usdjpy.pips_per_point == pytest.approx(10.0)
    assert deviation_points(0.3, usdjpy) == 3
    assert deviation_points(0.1, eurusd) == 1
    assert deviation_points(2.5, eurusd) == 25
