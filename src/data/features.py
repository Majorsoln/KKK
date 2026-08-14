"""L3 — features 25 kwa jaribio la meta-labelling (DF-12, §6.1).

Orodha imetoka kwa mtaalamu wa nje wa 1, ambaye aliitoa **kwa majina** ili
siku ya kwanza ianze bila utafiti mwingine. Imezingatiwa kama ilivyo, **isipokuwa
mahali sheria yetu ya kwanza inapoipinga**.

## Mahali nilipotofautiana na orodha yake, na kwa nini

Sheria ya 1 ya §6.1 (`DF-12`, imesainiwa): *"Scale-free. Kila feature iwe
log-return, ratio, z-score, percentile rank, au ATR-units. **Kamwe raw
price.**"*

| Yake | Yangu | Sababu |
|---|---|---|
| `ATR14` | `atr_pct` = ATR ÷ close | ATR ya XAUUSD ni pips 357, ya EURCHF ni 9.8. Raw haiwezi kulisha model moja |
| `spread_p50` | `spread_atr` = spread ÷ ATR (pips zote mbili) | spread ya 1.0 pip ni ndogo kwa GBPJPY, kubwa kwa EURCHF. Ni **spread ÷ volatility** inayolinganishwa |

Sheria iliyosainiwa inashinda orodha ya mtaalamu. Zote mbili zinabaki na
**taarifa ile ile**, zikiwa zimebadilishwa units pekee.

## Sheria zinazotawala kila safu hapa

* **7 — NaN ni NaN.** Dirisha lisilojaa linatoa `NaN`, si sifuri. Sifuri
  ingekuwa uongo unaoonekana kama data.
* **2 — point-in-time.** Rolling kwa data ya nyuma PEKEE. Hakuna `mean`/`std`
  ya dataset nzima; hiyo ni uvujaji wa kawaida kabisa.
* **3 — as-of.** Bar ya sasa inaingia **ikishafungwa**; uamuzi uko kwenye
  close, na kila feature inatumia bars zilizofungwa hadi hapo.
* **6 — determinism.** `ATR` inatoka `indicators.atr` — function MOJA
  inayotumiwa na setups, labels na features. Haiandikwi upya hapa.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .indicators import ATR_PERIOD, atr, rolling_pct_rank
from .quality import _pip_size

FEATURE_SET_VERSION = 1

# Majina yaliyotangazwa. Orodha hii ni **mkataba**: kuiongeza au kuipunguza ni
# config mpya, na inagharimu bajeti ya majaribio (docs/TRIAL_BUDGET.md).
FEATURE_NAMES: tuple[str, ...] = (
    # A — returns / momentum (6)
    "ret_1h", "ret_4h", "ret_8h", "ret_24h", "ret_48h", "impulse_4h_atr",
    # B — volatility (5)
    "atr_pct", "atr_pct_rank_252", "rvol_24h", "rvol_72h", "vol_ratio_24_168",
    # C — trend structure (5)
    "ema20_dist_atr", "ema50_dist_atr", "ema20_vs_ema50_atr", "adx14", "eff_ratio_24h",
    # D — mean reversion (4)
    "rsi14", "bb_z20", "close_pos_24h", "dist_high_24h_atr",
    # E — market / execution (4)
    "spread_atr", "spread_ratio_528", "hour_sin", "hour_cos",
    # F — benchmark (1)
    "setup_v1_flag",
)


# --------------------------------------------------------------------------
# Viashiria vya ziada — kila kimoja mahali pamoja (sheria 6)
# --------------------------------------------------------------------------


def ema(series: pd.Series, span: int) -> pd.Series:
    """EMA yenye `min_periods` — dirisha lisilojaa linatoa NaN, si makadirio."""
    return series.ewm(span=span, adjust=False, min_periods=span).mean()


def rsi(close: pd.Series, period: int = 14) -> pd.Series:
    """RSI ya Wilder. 50 = usawa; 70/30 ni desturi, si sheria hapa."""
    delta = close.diff()
    gain = delta.clip(lower=0.0)
    loss = (-delta).clip(lower=0.0)
    avg_gain = gain.ewm(alpha=1.0 / period, adjust=False, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=1.0 / period, adjust=False, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace(0.0, np.nan)
    out = 100.0 - 100.0 / (1.0 + rs)
    # Hasara sifuri kwa dirisha zima = mwelekeo mmoja kabisa; RSI ni 100.
    return out.where(avg_loss.notna(), np.nan).fillna(
        pd.Series(np.where(avg_loss.eq(0.0) & avg_gain.gt(0.0), 100.0, np.nan), index=close.index)
    )


def adx(bars: pd.DataFrame, period: int = 14) -> pd.Series:
    """ADX ya Wilder — nguvu ya trend BILA mwelekeo (0–100).

    Haina mwelekeo kwa makusudi: mwelekeo unatoka kwa `impulse`, na kuchanganya
    vyote viwili kwenye feature moja kungeficha kipi kinafanya kazi.
    """
    high, low, close = bars["high"], bars["low"], bars["close"]
    up = high.diff()
    down = -low.diff()
    plus_dm = pd.Series(np.where((up > down) & (up > 0), up, 0.0), index=bars.index)
    minus_dm = pd.Series(np.where((down > up) & (down > 0), down, 0.0), index=bars.index)

    tr = pd.concat(
        [high - low, (high - close.shift()).abs(), (low - close.shift()).abs()], axis=1
    ).max(axis=1)
    alpha = 1.0 / period
    atr_w = tr.ewm(alpha=alpha, adjust=False, min_periods=period).mean()
    plus_di = 100.0 * plus_dm.ewm(alpha=alpha, adjust=False, min_periods=period).mean() / atr_w
    minus_di = 100.0 * minus_dm.ewm(alpha=alpha, adjust=False, min_periods=period).mean() / atr_w
    dx = 100.0 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0.0, np.nan)
    return dx.ewm(alpha=alpha, adjust=False, min_periods=period).mean()


def efficiency_ratio(close: pd.Series, window: int) -> pd.Series:
    """Kaufman: |mwendo halisi| ÷ jumla ya mwendo. 1 = mstari, 0 = kelele.

    Inatofautisha "imepanda pips 50" ya trend safi na ile ya kuzunguka-zunguka
    — vitu viwili tofauti kabisa vyenye return ile ile.
    """
    direction = (close - close.shift(window)).abs()
    volatility = close.diff().abs().rolling(window, min_periods=window).sum()
    return direction / volatility.replace(0.0, np.nan)


def realized_vol(close: pd.Series, window: int) -> pd.Series:
    """sd ya log-returns juu ya dirisha — scale-free kwa muundo."""
    returns = np.log(close / close.shift())
    return returns.rolling(window, min_periods=window).std()


def bollinger_z(close: pd.Series, window: int = 20) -> pd.Series:
    """`(close − mean) ÷ sd` — rolling, si global (sheria 2)."""
    mean = close.rolling(window, min_periods=window).mean()
    sd = close.rolling(window, min_periods=window).std()
    return (close - mean) / sd.replace(0.0, np.nan)


# --------------------------------------------------------------------------
# Mjenzi
# --------------------------------------------------------------------------


def build(
    bars: pd.DataFrame,
    symbol: str,
    setups: pd.DataFrame | None = None,
    spread_window: int = 528,
) -> pd.DataFrame:
    """Features 25 kwa bars za H1 za symbol MOJA.

    `bars` ni L2/H1 (`open, high, low, close, spread_p50, is_valid`). Index ni
    muda wa **kufungua**; uamuzi uko kwenye **kufunga**, kwa hiyo safu
    `decision_time` inaongezwa kwa `index + 1h` — sawa na `setups.py`, si
    hesabu ya pili (sheria 6).

    **`symbol` ni parameter, si `bars.attrs`.** Toleo la kwanza liliisoma kutoka
    `attrs`, ambayo hupotea kwenye karibu kila operesheni ya pandas — na
    ikipotea, `_pip_size(None)` inarudisha 0.0001 kimya. Kwa XAUUSD (pip 0.01)
    hiyo ni kosa la mara 100 kwenye `spread_atr`, likionekana kama namba halali
    kabisa. Tegemezi lililo wazi haliwezi kupotea kimya.
    """
    close = bars["close"]
    out = pd.DataFrame(index=bars.index)
    out["decision_time"] = bars.index + pd.Timedelta(hours=1)

    atr14 = atr(bars, ATR_PERIOD)

    # A — returns / momentum
    for hours in (1, 4, 8, 24, 48):
        out[f"ret_{hours}h"] = np.log(close / close.shift(hours))
    out["impulse_4h_atr"] = (close - close.shift(4)) / atr14

    # B — volatility
    out["atr_pct"] = atr14 / close
    out["atr_pct_rank_252"] = rolling_pct_rank(out["atr_pct"], 252, min_periods=63)
    out["rvol_24h"] = realized_vol(close, 24)
    out["rvol_72h"] = realized_vol(close, 72)
    out["vol_ratio_24_168"] = out["rvol_24h"] / realized_vol(close, 168).replace(0.0, np.nan)

    # C — trend structure
    ema20, ema50 = ema(close, 20), ema(close, 50)
    out["ema20_dist_atr"] = (close - ema20) / atr14
    out["ema50_dist_atr"] = (close - ema50) / atr14
    out["ema20_vs_ema50_atr"] = (ema20 - ema50) / atr14
    out["adx14"] = adx(bars, 14)
    out["eff_ratio_24h"] = efficiency_ratio(close, 24)

    # D — mean reversion
    out["rsi14"] = rsi(close, 14)
    out["bb_z20"] = bollinger_z(close, 20)
    high24 = bars["high"].rolling(24, min_periods=24).max()
    low24 = bars["low"].rolling(24, min_periods=24).min()
    span = (high24 - low24).replace(0.0, np.nan)
    out["close_pos_24h"] = (close - low24) / span
    out["dist_high_24h_atr"] = (high24 - close) / atr14

    # E — market / execution. Spread inagawanywa kwa ATR ya pips ILE ILE.
    atr_pips = atr14 / _pip_size(symbol)
    out["spread_atr"] = bars["spread_p50"] / atr_pips.replace(0.0, np.nan)
    median = bars["spread_p50"].rolling(spread_window, min_periods=spread_window // 4).median()
    out["spread_ratio_528"] = bars["spread_p50"] / median.replace(0.0, np.nan)
    hour = out["decision_time"].dt.hour
    out["hour_sin"] = np.sin(2 * np.pi * hour / 24.0)
    out["hour_cos"] = np.cos(2 * np.pi * hour / 24.0)

    # F — benchmark. SETUP-v1 kama feature, si lango: swali ni je model
    # inaigundua yenyewe, au ina taarifa ya ziada baada ya features zote.
    out["setup_v1_flag"] = 0.0
    if setups is not None and not setups.empty and "is_setup" in setups:
        flags = setups.set_index("decision_time")["is_setup"].astype(float)
        out["setup_v1_flag"] = out["decision_time"].map(flags).fillna(0.0).to_numpy()

    return out


def attach(features: pd.DataFrame, points: pd.DataFrame, symbol: str) -> pd.DataFrame:
    """Unganisha features na decision points kwa `decision_time`.

    Inner join kwa makusudi: point isiyo na features (dirisha halijajaa mwanzoni
    mwa historia) **haiingii**, badala ya kuingia na sifuri. Sheria ya 7.
    """
    wanted = points[points["symbol"] == symbol] if "symbol" in points else points
    if wanted.empty or features.empty:
        return pd.DataFrame()
    merged = wanted.merge(features, on="decision_time", how="inner", suffixes=("", "_feat"))
    return merged


def coverage(frame: pd.DataFrame, names: tuple[str, ...] = FEATURE_NAMES) -> pd.Series:
    """Sehemu ya rows zenye thamani halali kwa kila feature.

    Feature yenye coverage ndogo si feature — ni shimo lenye jina. Inaripotiwa
    kabla ya mafunzo, si baada.
    """
    present = [n for n in names if n in frame.columns]
    return frame[present].notna().mean().sort_values()
