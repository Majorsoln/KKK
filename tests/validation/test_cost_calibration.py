"""Calibration A — DOCTRINE §8.3, R12, R16.

Gharama iliyopimwa vibaya haitoi kosa; inatoa EV. Kwa hiyo tests hizi zinalinda:

* **chanzo** — upande wa live unatoka RCE, hauhesabiwi hapa (R12)
* **kipimo** — spread na slippage zinatoka kwenye tick, si kwenye dhana
* **ukaguzi** — `live < research` inasimamisha injini, haitoi onyo (R16)
"""

from __future__ import annotations

import json

import numpy as np
import pandas as pd
import pytest

from src.data.bars import build
from src.data.window import Stage, Window
from src.rce.cost import SymbolSpec, spread_effective
from src.validation import cost_calibration as CA

SPEC = SymbolSpec(
    symbol="EURUSD", point=0.00001, contract_size=100_000,
    volume_min=0.01, volume_step=0.01, volume_max=50.0,
)
PIP = 0.0001
T0 = pd.Timestamp("2020-06-01 00:00", tz="UTC")
STAGE = Stage(
    window=Window(pd.Timestamp("2020-01-01", tz="UTC"), pd.Timestamp("2020-12-31", tz="UTC")),
    name="calib", purpose="Calibration A",
)


def _ticks(n=8_000, *, spread_pips=1.2, seed=5, freq="1min", jump=0.0):
    """Ticks za dakika; `jump` inaongeza mwendo kwenye kila tick ya saa kamili."""
    rng = np.random.default_rng(seed)
    mid = 1.10 + np.cumsum(rng.normal(0, 2e-5, n))
    stamps = pd.date_range(T0, periods=n, freq=freq, tz="UTC")
    if jump:
        mid = mid + jump * PIP * (stamps.minute == 0)
    half = spread_pips * PIP / 2.0
    return pd.DataFrame({"timestamp": stamps, "bid": mid - half, "ask": mid + half})


def _bars(ticks, tf="H1"):
    return build(ticks, tf, STAGE).bars


def _broker(**kw) -> CA.Broker:
    base = dict(spec=SPEC, pip_value_acct=10.0, commission_round_turn=7.0)
    base.update(kw)
    return CA.Broker(**base)


def _cell(cfg_risk, ticks=None, *, spread_pips=1.2, live_spread=1.5, **kw):
    ticks = _ticks(spread_pips=spread_pips) if ticks is None else ticks
    base = dict(
        timeframe="H1", ticks=ticks, bars=_bars(ticks), cfg_risk=cfg_risk,
        broker=_broker(), h1_spreads=[live_spread] * 100, m5_spreads=[live_spread] * 288,
    )
    base.update(kw)
    return CA.calibrate_cell(**base)


# ===========================================================================
# Kipimo kinatoka kwenye tick
# ===========================================================================


def test_spread_inapimwa_kwenye_quote_ya_kujaza(cfg_risk):
    row = _cell(cfg_risk, spread_pips=2.4)
    assert row.spread_mean_pips == pytest.approx(2.4, abs=1e-6)
    assert row.spread_p50_pips == pytest.approx(2.4, abs=1e-6)


def test_slippage_ni_kutoka_quote_ya_UAMUZI_hadi_ya_KUJAZA(cfg_risk):
    """Hakuna dhana ya latency: tick inayofuata ndiyo jibu la data yenyewe."""
    ticks = _ticks(jump=5.0)
    row = _cell(cfg_risk, ticks)
    # Kila mpaka wa H1 una mruko wa pips 5 kwenye tick ya kwanza baada yake.
    assert row.slippage_mean_pips == pytest.approx(5.0, abs=0.2)


def test_slippage_ya_soko_tulivu_ni_ndogo(cfg_risk):
    row = _cell(cfg_risk)
    assert 0 < row.slippage_mean_pips < 1.0


def test_pointi_zisizo_na_quote_pande_zote_zinatolewa_nje():
    """Kujaza kwa jirani kungebuni bei ambayo haikuwahi kuwepo."""
    ticks = _ticks()
    bars = _bars(ticks)
    kati = ticks.iloc[2_000:4_000].reset_index(drop=True)

    zote = CA.measure_execution(ticks, bars, "H1", symbol="EURUSD")
    chache = CA.measure_execution(kati, bars, "H1", symbol="EURUSD")
    assert chache["n_points"] < zote["n_points"]
    # Mipaka iliyobaki ni ile iliyo NDANI ya ticks zilizopo: saa 33 kati ya 2,000
    # dakika, ukiondoa ya kwanza (haina quote ya uamuzi).
    assert chache["n_points"] == pytest.approx(2_000 / 60, abs=2)


def test_bila_mpaka_wenye_quote_pande_zote_inalipuka():
    ticks = _ticks()
    bars = _bars(ticks)
    baadaye = ticks.copy()
    baadaye["timestamp"] = baadaye["timestamp"] + pd.Timedelta(days=365)
    with pytest.raises(CA.CalibrationAError, match="pande zote mbili"):
        CA.measure_execution(baadaye, bars, "H1", symbol="EURUSD")


def test_ticks_bila_bid_ask_zinalipuka():
    frame = pd.DataFrame({"timestamp": [T0], "close": [1.10]})
    with pytest.raises(CA.CalibrationAError, match="bid"):
        CA.measure_execution(frame, _bars(_ticks()), "H1", symbol="EURUSD")


def test_atr_inapimwa_kwa_pips(cfg_risk):
    row = _cell(cfg_risk)
    assert row.atr_pips > 0
    assert row.research_cost_atr == pytest.approx(row.research_cost_pips / row.atr_pips)


def test_bars_chache_kuliko_dirisha_la_atr_zinalipuka():
    bars = _bars(_ticks(n=8_000)).head(CA.ATR_WINDOW)
    with pytest.raises(CA.CalibrationAError, match="ATR"):
        CA.atr_pips(bars, "EURUSD")


# ===========================================================================
# R12 — upande wa live unatoka RCE
# ===========================================================================


def test_live_spread_ni_ILE_ILE_ya_rce(cfg_risk):
    h1, m5 = [1.4] * 100, [3.0] * 288
    row = _cell(cfg_risk, h1_spreads=h1, m5_spreads=m5)
    assert row.live_spread_pips == pytest.approx(spread_effective(h1, m5, cfg_risk))


def test_slippage_cap_inatoka_risk_yaml(cfg_risk):
    row = _cell(cfg_risk)
    assert row.live_slippage_cap_pips == pytest.approx(
        float(cfg_risk.get("slippage_cap_pips")["market"])
    )


def test_commission_inatoka_rce(cfg_risk):
    row = _cell(cfg_risk)
    assert row.commission_pips == pytest.approx(7.0 / 10.0)


def test_swap_ni_sifuri_pasipo_usiku(cfg_risk):
    assert _cell(cfg_risk).swap_pips == 0.0


# ===========================================================================
# §8.2 — namba TATU, kila moja kwa swali lake
# ===========================================================================


def test_research_ina_slippage_MARA_MBILI(cfg_risk):
    """§8.1: `ENTRY` na `EXIT` zote zina slippage."""
    row = _cell(cfg_risk)
    assert row.research_cost_pips == pytest.approx(
        row.spread_mean_pips + 2 * row.slippage_mean_pips + row.commission_pips, abs=1e-9
    )


def test_live_sizing_ina_slippage_MARA_MOJA_kama_rce(cfg_risk):
    """RCE: `spread_effective + slippage_cap + comm + swap`. Haibadilishwi (R12)."""
    row = _cell(cfg_risk)
    assert row.live_sizing_cost_pips == pytest.approx(
        row.live_spread_pips + row.live_slippage_cap_pips + row.commission_pips, abs=1e-9
    )


def test_pengo_la_slippage_ya_kutoka_LINAONEKANA(cfg_risk):
    """Kile ambacho sizing ya RCE haihesabu hakifichwi."""
    row = _cell(cfg_risk)
    assert row.rce_slippage_gap_pips == pytest.approx(row.live_slippage_cap_pips, abs=1e-9)
    assert "slippage ya kutoka" in CA.CostTable(rows=(row,)).render()


def test_cost_sensitivity_ni_live_kwa_research(cfg_risk):
    row = _cell(cfg_risk)
    assert row.cost_sensitivity == pytest.approx(
        row.live_sizing_cost_pips / row.research_cost_pips
    )


# ===========================================================================
# R16 — `live ≥ research`, na inaposhindikana injini inasimama
# ===========================================================================


def test_gharama_ya_kawaida_inapita_ukaguzi(cfg_risk):
    row = _cell(cfg_risk, spread_pips=1.2, live_spread=1.5)
    assert row.ok


def test_research_kubwa_kuliko_live_INAVUNJA_calibration(cfg_risk):
    """Spread halisi ya pips 20 dhidi ya kadirio la 1.5 — kadirio si la kihafidhina."""
    row = _cell(cfg_risk, spread_pips=20.0, live_spread=1.5)
    assert not row.ok
    with pytest.raises(CA.CalibrationAError, match="R16"):
        CA.CostTable(rows=(row,)).assert_ok()


def test_assert_ok_inarudisha_jedwali_likiwa_zima(cfg_risk):
    table = CA.CostTable(rows=(_cell(cfg_risk),))
    assert table.assert_ok() is table


def test_cells_zilizovunjika_zinatajwa_kwenye_ripoti(cfg_risk):
    mbaya = _cell(cfg_risk, spread_pips=20.0)
    nzuri = _cell(cfg_risk, spread_pips=1.0)
    table = CA.CostTable(rows=(mbaya, nzuri))
    assert len(table.broken) == 1
    assert "VUNJIKA" in table.render()


# ===========================================================================
# Ushahidi wenye tarehe (R5)
# ===========================================================================


def test_jedwali_linaandikwa_na_kusomeka(cfg_risk, tmp_path):
    table = CA.calibrate(
        [dict(timeframe="H1", ticks=_ticks(), bars=_bars(_ticks()), cfg_risk=cfg_risk,
              broker=_broker(), h1_spreads=[1.5] * 100, m5_spreads=[1.5] * 288)],
        source="EURUSD 2020", progress=None,
    )
    path = table.write(tmp_path / "cost.json")
    raw = json.loads(path.read_text(encoding="utf-8"))
    assert raw["created_at"].startswith("20") and raw["source"] == "EURUSD 2020"
    assert raw["rows"][0]["ok"] is True

    rudi = CA.CostTable.read(path)
    assert rudi["EURUSD", "H1"].research_cost_pips == pytest.approx(
        table["EURUSD", "H1"].research_cost_pips
    )


def test_cell_isiyopo_inalipuka(cfg_risk):
    table = CA.CostTable(rows=(_cell(cfg_risk),))
    with pytest.raises(KeyError):
        table["GBPUSD", "H1"]


def test_calibrate_inachapisha_kila_cell(cfg_risk):
    """R23 — hakuna kinachoendeshwa kimya."""
    lines: list[str] = []
    ticks = _ticks()
    CA.calibrate(
        [dict(timeframe="H1", ticks=ticks, bars=_bars(ticks), cfg_risk=cfg_risk,
              broker=_broker(), h1_spreads=[1.5] * 100, m5_spreads=[1.5] * 288)],
        progress=lines.append,
    )
    assert len(lines) == 1 and "EURUSD" in lines[0]
