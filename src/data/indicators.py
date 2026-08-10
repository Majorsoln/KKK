"""Viashiria vya msingi — fomula MOJA kwa kila kiasi (spec §6.1 sheria ya 6).

ATR ya H1 inatumiwa na SETUP-v1 (§4.3), na labels zote nne (§5), na baadaye
familia za features (§6.2). Ikihesabiwa mahali pawili, siku moja zitatofautiana
— hoja ile ile ya `cost_pips` ya KAIROS-1 §4.2. Kwa hiyo inaishi hapa, na kila
mtumiaji anaiagiza; **kuiandika upya ni ukiukaji wa DF-12**.

Kila kitu hapa ni **point-in-time kwa muundo**: rolling/expanding ya nyuma
pekee, na dirisha lisilojaa linatoa NaN (sheria ya 7 — NaN ni NaN, si sifuri).
"""

from __future__ import annotations

import numpy as np
import pandas as pd

ATR_PERIOD = 14  # kipindi kimoja kilichotangazwa; kubadilisha = dataset mpya (§5.5)


def true_range(bars: pd.DataFrame) -> pd.Series:
    """TR ya kila bar: max(high−low, |high−close₋₁|, |low−close₋₁|).

    Bar ya kwanza haina `close₋₁` — TR yake ni NaN, si `high−low`. Kuanza na
    `high−low` kungeficha pengo la weekend ndani ya kipimo cha volatility.
    """
    prev_close = bars["close"].shift(1)
    ranges = pd.concat(
        [
            bars["high"] - bars["low"],
            (bars["high"] - prev_close).abs(),
            (bars["low"] - prev_close).abs(),
        ],
        axis=1,
    )
    return ranges.max(axis=1, skipna=False)


def atr(bars: pd.DataFrame, period: int = ATR_PERIOD) -> pd.Series:
    """ATR ya Wilder — units za BEI (mid), point-in-time.

    Wilder smoothing ni EMA yenye `alpha = 1/period`, ikianzishwa kwa wastani
    wa TR za kipindi cha kwanza. Bars za mwanzo (chini ya `period`) ni NaN —
    dirisha halijajaa, na sheria ya 7 inakataa kubuni thamani.
    """
    tr = true_range(bars)
    out = tr.ewm(alpha=1.0 / period, adjust=False, min_periods=period).mean()
    out.name = f"atr{period}"
    return out


def rolling_median(series: pd.Series, window: int, min_periods: int | None = None) -> pd.Series:
    """Median ya dirisha la NYUMA pekee — bar ya sasa (iliyofungwa) inahesabiwa.

    Bar iliyofungwa ni historia halali kwa as-of (§4.1); kilicho marufuku ni
    bars za BAADAYE. `rolling` ya pandas inaangalia nyuma kwa muundo, kwa hiyo
    hakuna kitu cha baadaye kinachoingia — sentinel ya §4.2 inathibitisha.
    """
    return series.rolling(window, min_periods=min_periods or window).median()


def rolling_pct_rank(series: pd.Series, window: int, min_periods: int | None = None) -> pd.Series:
    """Nafasi ya thamani ya SASA ndani ya dirisha lake la nyuma, [0, 1].

    `(idadi ya thamani za nyuma ≤ ya sasa) ÷ ukubwa wa dirisha`. Kila kipimo
    kinatumia historia yake pekee — hakuna global rank (uvujaji wa kawaida
    kabisa, §6.1 sheria ya 2).
    """
    need = min_periods or window

    def _rank(values: np.ndarray) -> float:
        current = values[-1]
        if np.isnan(current):
            return np.nan
        past = values[~np.isnan(values)]
        if len(past) < need:
            return np.nan
        return float((past <= current).mean())

    return series.rolling(window, min_periods=need).apply(_rank, raw=True)
