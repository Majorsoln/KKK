"""Feature Engine — DOCTRINE §5, R1.

Uvujaji wa feature hauonekani kama kosa. Unaonekana kama ustadi: model
inayojua kilele cha kesho itaonekana bora kuliko yoyote, na hakuna metric
itakayosema kwa nini.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.data import features as F
from src.data.bars import build
from src.data.window import Stage, Window

STAGE = Stage(
    window=Window(pd.Timestamp("2020-01-01", tz="UTC"), pd.Timestamp("2020-12-31", tz="UTC")),
    name="feat", purpose="§5",
)


def _bars(n=900, *, seed=5, symbol="EURUSD"):
    """Bars za H1 zilizojengwa kutoka ticks — njia ile ile ya injini."""
    rng = np.random.default_rng(seed)
    stamps = pd.date_range("2020-02-01", periods=n * 60, freq="1min", tz="UTC")
    mid = 1.10 + np.cumsum(rng.normal(0, 2e-5, len(stamps)))
    half = 0.6e-4
    ticks = pd.DataFrame({"timestamp": stamps, "bid": mid - half, "ask": mid + half})
    ticks.attrs["symbol"] = symbol
    out = build(ticks, "H1", STAGE).bars
    out.attrs["symbol"] = symbol
    return out


# ===========================================================================
# R1 — hakuna data ya baadaye
# ===========================================================================


def test_kukata_bars_za_baadaye_HAKUBADILISHI_features_za_nyuma():
    """Ukaguzi wenye nguvu zaidi: feature inayotumia baadaye itabadilika.

    Isiyoitumia haitabadilika hata kidogo — na hakuna test nyingine inayoweza
    kusema hilo kwa uhakika ule ule.
    """
    bars = _bars(n=900)
    feats = F.build(bars, symbol="EURUSD")
    sawa, mbaya = F.check_no_lookahead(feats, bars, n=200)
    assert sawa, f"features zinazobadilika zikikatwa: {mbaya}"


def test_rolling_extremes_zinatumia_t_MOJA_KABLA():
    """Bar iliyoweka kilele haipati umbali wa sifuri.

    Ikijumuisha `t`, feature ingekuwa inarudia swali badala ya kulijibu.
    """
    n = 60
    stamps = pd.date_range("2020-02-03", periods=n * 60, freq="1min", tz="UTC")
    mid = np.linspace(1.10, 1.13, len(stamps))          # inapanda daima
    ticks = pd.DataFrame({"timestamp": stamps, "bid": mid - 6e-5, "ask": mid + 6e-5})
    ticks.attrs["symbol"] = "EURUSD"
    bars = build(ticks, "H1", STAGE).bars
    bars.attrs["symbol"] = "EURUSD"

    feats = F.build(bars, symbol="EURUSD")
    dist = feats["dist_from_high_20"].dropna()
    # Bei inapanda daima, kwa hiyo kila bar iko JUU ya kilele cha bars 20
    # zilizopita. Ikijumuisha `t`, ingekuwa sifuri kila mahali.
    assert (dist > 0).all()


def test_percentile_ina_dirisha_kwenye_JINA():
    feats = F.build(_bars(), symbol="EURUSD")
    for col in feats.columns:
        if "percentile" in col:
            assert col.endswith("d"), col


def test_percentile_ya_bar_haitegemei_bars_za_baadaye():
    bars = _bars(n=900)
    kamili = F.build(bars, symbol="EURUSD")
    fupi = F.build(bars.iloc[:-300], symbol="EURUSD")
    col = "ATR_percentile_252d"
    a = kamili[col].iloc[: len(fupi)].to_numpy()
    b = fupi[col].to_numpy()
    assert np.allclose(a, b, equal_nan=True)


# ===========================================================================
# Warmup
# ===========================================================================


def test_features_za_warmup_ni_NaN_si_thamani_ya_kubuni():
    feats = F.build(_bars(n=400), symbol="EURUSD")
    assert feats["EMA_200"].iloc[:199].isna().all()
    assert feats["ATR_14"].iloc[:13].isna().all()
    assert feats["EMA_200"].iloc[250:].notna().all()


# ===========================================================================
# Usahihi wa hesabu
# ===========================================================================


def test_RSI_iko_kati_ya_sifuri_na_mia():
    rsi = F.build(_bars(), symbol="EURUSD")["RSI_14"].dropna()
    assert rsi.between(0.0, 100.0).all()


def test_ADX_si_hasi():
    adx = F.build(_bars(), symbol="EURUSD")["ADX_14"].dropna()
    assert (adx >= 0).all()


def test_close_pos_in_range_iko_kati_ya_sifuri_na_moja():
    pos = F.build(_bars(), symbol="EURUSD")["close_pos_in_range"].dropna()
    assert pos.between(0.0, 1.0).all()


def test_ATR_kwa_pips_inategemea_symbol():
    """JPY ina pip mara mia; ATR ya pips lazima ionyeshe hilo."""
    bars = _bars(symbol="EURUSD")
    eur = F.build(bars, symbol="EURUSD")["ATR_pips"].dropna().median()

    jpy_bars = bars.copy() * 100.0
    jpy_bars["n_ticks"] = bars["n_ticks"]
    jpy_bars.attrs["symbol"] = "USDJPY"
    jpy = F.build(jpy_bars, symbol="USDJPY")["ATR_pips"].dropna().median()
    assert jpy == pytest.approx(eur, rel=0.01)


def test_spread_per_atr_inatumia_pips_pande_ZOTE_MBILI():
    feats = F.build(_bars(), symbol="EURUSD")
    row = feats[["spread_p50", "ATR_pips", "spread_per_atr"]].dropna().iloc[10]
    assert row["spread_per_atr"] == pytest.approx(row["spread_p50"] / row["ATR_pips"])


# ===========================================================================
# §8.6 — `hour` inategemea tz, na tz ni chaguo
# ===========================================================================


def test_hour_inategemea_tz_iliyotolewa():
    """Feeds mbili hazitumii mkataba mmoja wa muda (§8.6).

    Chaguo la kimya lingekuwa sahihi kwa symbols tisa na kosa kwa tatu, nusu ya
    mwaka — kwa hiyo mpigaji simu analazimika kuchagua.
    """
    bars = _bars(n=100)
    utc = F.build(bars, symbol="EURUSD", hour_tz="UTC")["hour"]
    berlin = F.build(bars, symbol="EURUSD", hour_tz="Europe/Berlin")["hour"]
    assert not utc.equals(berlin)
    assert set(berlin.unique()) <= set(range(24))


def test_tz_inarekodiwa_kwenye_frame():
    feats = F.build(_bars(n=100), symbol="EURUSD", hour_tz="Europe/Berlin")
    assert feats.attrs["hour_tz"] == "Europe/Berlin"


# ===========================================================================
# Mikataba
# ===========================================================================


def test_bars_bila_OHLC_zinalipuka():
    with pytest.raises(F.FeatureError, match="OHLC"):
        F.build(pd.DataFrame({"close": [1.1]}), symbol="EURUSD")


def test_bars_tupu_zinalipuka():
    tupu = pd.DataFrame(columns=["open", "high", "low", "close"])
    with pytest.raises(F.FeatureError, match="hakuna bars"):
        F.build(tupu, symbol="EURUSD")


def test_ukaguzi_wa_lookahead_unadai_bars_za_kutosha():
    with pytest.raises(F.FeatureError, match="hazitoshi"):
        bars = _bars(n=100)
        F.check_no_lookahead(F.build(bars, symbol="EURUSD"), bars, n=200)
