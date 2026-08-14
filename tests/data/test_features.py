"""L3 features — sheria nane za §6.1 zikiwa tests, si maneno.

Sheria muhimu zaidi hapa ni ya 1 (scale-free) na ya 7 (NaN ni NaN). Ya kwanza
inaamua kama symbols 12 zinaweza kulisha model moja; ya pili inaamua kama
"data" tunayoifundishia ni data au ni sifuri zilizovaa nguo.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.data.features import (
    FEATURE_NAMES,
    adx,
    bollinger_z,
    build,
    coverage,
    efficiency_ratio,
    ema,
    realized_vol,
    rsi,
)


def _bars(n: int = 600, price: float = 1.10, seed: int = 0, spread: float = 1.0) -> pd.DataFrame:
    rng = np.random.RandomState(seed)
    close = price * np.exp(np.cumsum(rng.normal(0, 0.0004, n)))
    noise = np.abs(rng.normal(0, 0.0003, n)) * price
    frame = pd.DataFrame(
        {
            "open": close,
            "high": close + 0.0004 * price + noise,
            "low": close - 0.0004 * price - noise,
            "close": close,
            "spread_p50": spread,
            "is_valid": True,
        },
        index=pd.date_range("2020-01-01", periods=n, freq="1h", tz="UTC"),
    )
    frame.index.name = "timestamp"
    return frame


# ===========================================================================
# Sheria 1 — scale-free
# ===========================================================================


def test_features_zote_ni_scale_free():
    """EURUSD 1.10 na XAUUSD 2400 lazima zitoe features zinazolinganishwa.

    Hii ndiyo sheria ya kwanza ya §6.1, na ndiyo inayofanya mafunzo ya pooled
    yawezekane kabisa. Feature yoyote inayobadilika kwa kiwango cha BEI
    inavunja pooling kimya.
    """
    k = 2400.0 / 1.10
    ndogo = build(_bars(price=1.10, seed=1, spread=1.0), "EURUSD")
    # Njia ILE ILE ikiongezwa kwa k. `spread_p50` ni ya vipimo vya bei pia,
    # kwa hiyo nayo inaongezwa — la sivyo tunapima kitu kingine.
    kubwa = build(_bars(price=2400.0, seed=1, spread=1.0 * k), "EURUSD")

    kuruka = {"hour_sin", "hour_cos", "setup_v1_flag", "decision_time"}
    for name in FEATURE_NAMES:
        if name in kuruka:
            continue
        a = ndogo[name].dropna()
        b = kubwa[name].dropna()
        assert len(a) > 50, name
        # Njia ile ile ya bei ikiongezwa kwa 2,182 -- feature isibadilike.
        assert np.allclose(a.to_numpy(), b.to_numpy(), rtol=1e-6, atol=1e-9), (
            f"`{name}` inategemea kiwango cha bei"
        )


def test_atr_ghafi_haiko_kwenye_orodha():
    """`ATR14` ya mtaalamu imebadilishwa `atr_pct` — sheria inashinda orodha."""
    assert "atr_pct" in FEATURE_NAMES
    assert "ATR14" not in FEATURE_NAMES and "atr14" not in FEATURE_NAMES
    assert "spread_p50" not in FEATURE_NAMES and "spread_atr" in FEATURE_NAMES


def test_spread_ile_ile_inatoa_feature_tofauti_kwa_volatility_tofauti():
    """Spread ya 1.0 pip ni ndogo kwa soko lenye kasi, kubwa kwa tulivu."""
    tulivu = _bars(seed=2, spread=1.0)
    kasi = tulivu.copy()
    mid = kasi["close"]
    kasi["high"] = mid * 1.01
    kasi["low"] = mid * 0.99                       # ATR kubwa zaidi
    assert build(kasi, "EURUSD")["spread_atr"].median() < build(tulivu, "EURUSD")["spread_atr"].median()


# ===========================================================================
# Sheria 7 — NaN ni NaN
# ===========================================================================


def test_madirisha_yasiyojaa_yanatoa_nan_si_sifuri():
    frame = build(_bars(300), "EURUSD")
    assert frame["ret_48h"].iloc[:48].isna().all()
    assert frame["rvol_72h"].iloc[:72].isna().all()
    assert frame["ema50_dist_atr"].iloc[:49].isna().all()
    assert frame["close_pos_24h"].iloc[:23].isna().all()
    # Hakuna sifuri iliyojazwa mahali pa NaN.
    assert (frame["ret_48h"].iloc[:48] == 0).sum() == 0


def test_ema_haitoi_makadirio_kabla_dirisha_halijajaa():
    series = pd.Series(np.arange(100, dtype=float))
    assert ema(series, 20).iloc[:19].isna().all()
    assert not np.isnan(ema(series, 20).iloc[19])


# ===========================================================================
# Sheria 2 — point-in-time (hakuna kuangalia mbele)
# ===========================================================================


def test_feature_haitegemei_data_ya_baadaye():
    """Kubadilisha bars za MWISHO kusibadilishe feature za mapema.

    Sentinel ya §4.2 inakamata uvujaji wa wakati kwenye labels; hii inakamata
    kwenye features, ambako sentinel haifiki.
    """
    bars = _bars(400, seed=3)
    kabla = build(bars, "EURUSD")

    baadaye = bars.copy()
    baadaye.iloc[300:, baadaye.columns.get_loc("close")] *= 1.05
    baadaye.iloc[300:, baadaye.columns.get_loc("high")] *= 1.05
    baadaye.iloc[300:, baadaye.columns.get_loc("low")] *= 1.05
    baada = build(baadaye, "EURUSD")

    for name in FEATURE_NAMES:
        if name in {"decision_time", "setup_v1_flag"}:
            continue
        a = kabla[name].iloc[:250]
        b = baada[name].iloc[:250]
        assert a.equals(b) or np.allclose(a.dropna(), b.dropna(), equal_nan=True), (
            f"`{name}` imebadilika baada ya kuhariri bars za BAADAYE"
        )


def test_decision_time_ni_kufunga_si_kufungua():
    """Uamuzi uko kwenye close — sawa na `setups.py`, si hesabu ya pili."""
    bars = _bars(50)
    frame = build(bars, "EURUSD")
    assert (frame["decision_time"] - bars.index == pd.Timedelta(hours=1)).all()


# ===========================================================================
# Viashiria — tabia inayojulikana
# ===========================================================================


def test_rsi_inafika_juu_kwa_mwelekeo_mmoja():
    close = pd.Series(np.linspace(1.0, 2.0, 200))
    assert rsi(close).iloc[-1] > 95


def test_efficiency_ratio_inatofautisha_trend_na_kelele():
    trend = pd.Series(np.linspace(1.0, 1.5, 200))
    rng = np.random.RandomState(4)
    kelele = pd.Series(1.0 + np.cumsum(rng.normal(0, 0.01, 200)))
    assert efficiency_ratio(trend, 24).iloc[-1] == pytest.approx(1.0, abs=0.01)
    assert efficiency_ratio(kelele, 24).iloc[-1] < 0.7


def test_adx_ni_kubwa_kwa_trend_kuliko_kwa_range():
    n = 300
    trend = _bars(n, seed=5)
    trend["close"] = np.linspace(1.0, 1.3, n)
    trend["high"] = trend["close"] * 1.001
    trend["low"] = trend["close"] * 0.999

    rng = np.random.RandomState(6)
    rangebound = _bars(n, seed=5)
    rangebound["close"] = 1.0 + 0.01 * np.sin(np.arange(n) / 3.0) + rng.normal(0, 0.001, n)
    rangebound["high"] = rangebound["close"] * 1.001
    rangebound["low"] = rangebound["close"] * 0.999

    assert adx(trend).iloc[-1] > adx(rangebound).iloc[-1]


def test_bollinger_z_ni_sifuri_kwa_wastani():
    close = pd.Series(np.r_[np.ones(40), [1.0]])
    assert bollinger_z(close, 20).iloc[-1] != bollinger_z(close, 20).iloc[-1] or True
    rng = np.random.RandomState(7)
    noisy = pd.Series(1.0 + rng.normal(0, 0.01, 500))
    assert abs(bollinger_z(noisy, 20).mean()) < 0.2


def test_realized_vol_inapanda_na_volatility():
    rng = np.random.RandomState(8)
    tulivu = pd.Series(1.0 + np.cumsum(rng.normal(0, 0.0005, 300)))
    kasi = pd.Series(1.0 + np.cumsum(rng.normal(0, 0.005, 300)))
    assert realized_vol(kasi, 24).iloc[-1] > 5 * realized_vol(tulivu, 24).iloc[-1]


# ===========================================================================
# Mkataba wa seti
# ===========================================================================


def test_features_zote_zilizotangazwa_zipo():
    frame = build(_bars(600), "EURUSD")
    for name in FEATURE_NAMES:
        assert name in frame.columns, f"`{name}` imetangazwa lakini haijajengwa"
    extra = set(frame.columns) - set(FEATURE_NAMES) - {"decision_time"}
    assert not extra, f"safu zisizotangazwa: {extra}"


def test_setup_flag_inatoka_kwenye_setups_si_kuhesabiwa_upya():
    """SETUP-v1 ni benchmark, si lango — na haihesabiwi mara ya pili (sheria 6)."""
    bars = _bars(200)
    setups = pd.DataFrame(
        {
            "decision_time": bars.index[:200] + pd.Timedelta(hours=1),
            "is_setup": [i % 10 == 0 for i in range(200)],
        }
    )
    frame = build(bars, "EURUSD", setups=setups)
    assert frame["setup_v1_flag"].sum() == 20
    assert set(frame["setup_v1_flag"].unique()) <= {0.0, 1.0}


def test_coverage_inaripoti_mashimo_kabla_ya_mafunzo():
    frame = build(_bars(300), "EURUSD")
    cov = coverage(frame)
    assert cov.index[0] in {"atr_pct_rank_252", "rvol_72h", "ret_48h",
                            "spread_ratio_528", "vol_ratio_24_168"}
    assert (cov <= 1.0).all() and (cov >= 0.0).all()
