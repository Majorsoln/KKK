"""Feature Engine — DOCTRINE §5.

> Kwa kila bar `t`, maelezo ya hali ya soko yanayotumia **data iliyokuwa
> inajulikana wakati huo tu**.

Sheria mbili zisizovunjika, na zote mbili zimetekelezwa hapa kama code, si kama
nidhamu:

**1 · Rolling extremes zinatumia `[t−1]`, si `[t]`.** `dist_from_high_20` ya bar
`t` inapima umbali kutoka kilele cha bars `[t−20 … t−1]`. Kikijumuisha `t`
yenyewe, bar iliyoweka kilele ingepata umbali wa sifuri kwa ufafanuzi — feature
ingekuwa inarudia swali badala ya kulijibu.

**2 · Kila percentile inatangaza dirisha lake ndani ya JINA lake.**
`ATR_percentile` bila dirisha hairuhusiwi kuwepo. Percentile juu ya sample nzima
ingempa bar ya 2017 taarifa ya volatility ya 2020 — uvujaji ambao hakuna test
itakayouona, na utakaojionyesha kama ustadi.

---

**`hour` inategemea tz, na tz inategemea chanzo (§8.6).**

Kipimo cha 2026-08-23 kilionyesha feeds mbili hazitumii mkataba mmoja wa muda:
Toleo A linafuata saa ya ndani inayohama na DST, Toleo B linatua kwenye saa
thabiti ya UTC. Kwa hiyo `hour_tz` ni **parameter**, si constant — na mpigaji
simu analazimika kuchagua. Chaguo la kimya lingekuwa sahihi kwa symbols tisa na
kosa kwa tatu, nusu ya mwaka.
"""

from __future__ import annotations

from typing import Sequence

from src.rce.cost import pip_size

# Madirisha yanayotumika. Kila moja linaonekana kwenye jina la feature yake.
EMA_PERIODS = (20, 50, 100, 200)
RETURN_PERIODS = (1, 3, 5, 10, 20, 50)
EXTREME_PERIODS = (20, 50)
ATR_PERIOD = 14
RSI_PERIOD = 14
ADX_PERIOD = 14
PERCENTILE_WINDOW = 252    # `_252d` — §21


class FeatureError(RuntimeError):
    """Features haziwezi kujengwa kutoka bars zilizotolewa."""


REQUIRED = ("open", "high", "low", "close")


def build(bars, *, symbol: str, hour_tz: str = "UTC"):
    """Features zote za §5 zinazotumiwa na maktaba ya masharti (§10.3).

    `bars` ni matokeo ya `data.bars.build` — index ni muda wa **mwanzo** wa bar,
    na bar zote zilizomo zimefungwa (R1 imeshatekelezwa hapo).
    """
    import numpy as np
    import pandas as pd

    missing = [c for c in REQUIRED if c not in bars.columns]
    if missing:
        raise FeatureError(f"bars hazina {missing} — §5 inahitaji OHLC")
    if len(bars) == 0:
        raise FeatureError("hakuna bars")

    pip = pip_size(symbol)
    close = bars["close"].astype(float)
    high = bars["high"].astype(float)
    low = bars["low"].astype(float)

    out = pd.DataFrame(index=bars.index)

    # ---- returns ----
    for k in RETURN_PERIODS:
        out[f"return_{k}"] = close.pct_change(k)

    # ---- ATR na volatility ----
    prev_close = close.shift(1)
    tr = pd.concat([
        high - low,
        (high - prev_close).abs(),
        (low - prev_close).abs(),
    ], axis=1).max(axis=1)
    atr = tr.rolling(ATR_PERIOD, min_periods=ATR_PERIOD).mean()
    out["ATR_14"] = atr
    out["ATR_pips"] = atr / pip

    # Percentile ya rolling, ikiwa na dirisha kwenye jina lake. `rank(pct=True)`
    # inahesabu nafasi ya thamani ya SASA ndani ya dirisha lake la nyuma pekee.
    out[f"ATR_percentile_{PERCENTILE_WINDOW}d"] = atr.rolling(
        PERCENTILE_WINDOW, min_periods=ATR_PERIOD
    ).rank(pct=True)

    # ---- EMA na umbali ----
    for p in EMA_PERIODS:
        out[f"EMA_{p}"] = close.ewm(span=p, adjust=False, min_periods=p).mean()
    out["dist_from_EMA200"] = (close - out["EMA_200"]) / out["EMA_200"]

    # ---- RSI ----
    delta = close.diff()
    gain = delta.clip(lower=0.0)
    loss = (-delta).clip(lower=0.0)
    avg_gain = gain.ewm(alpha=1.0 / RSI_PERIOD, adjust=False, min_periods=RSI_PERIOD).mean()
    avg_loss = loss.ewm(alpha=1.0 / RSI_PERIOD, adjust=False, min_periods=RSI_PERIOD).mean()
    rs = avg_gain / avg_loss.replace(0.0, np.nan)
    out["RSI_14"] = (100.0 - 100.0 / (1.0 + rs)).where(avg_loss > 0, 100.0)

    # ---- ADX ----
    up = high.diff()
    down = -low.diff()
    plus_dm = ((up > down) & (up > 0)).astype(float) * up.fillna(0.0)
    minus_dm = ((down > up) & (down > 0)).astype(float) * down.fillna(0.0)
    atr_w = tr.ewm(alpha=1.0 / ADX_PERIOD, adjust=False, min_periods=ADX_PERIOD).mean()
    plus_di = 100.0 * plus_dm.ewm(
        alpha=1.0 / ADX_PERIOD, adjust=False, min_periods=ADX_PERIOD).mean() / atr_w
    minus_di = 100.0 * minus_dm.ewm(
        alpha=1.0 / ADX_PERIOD, adjust=False, min_periods=ADX_PERIOD).mean() / atr_w
    dx = 100.0 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0.0, np.nan)
    out["ADX_14"] = dx.ewm(alpha=1.0 / ADX_PERIOD, adjust=False,
                           min_periods=ADX_PERIOD).mean()

    # ---- nafasi sokoni: rolling extremes za `[t−1]`, si `[t]` ----
    #
    # `.shift(1)` ndiyo sheria nzima. Bila yake, bar iliyoweka kilele ingepata
    # `dist_from_high = 0` kwa ufafanuzi, na feature ingekuwa inarudia swali.
    for p in EXTREME_PERIODS:
        kilele = high.rolling(p, min_periods=p).max().shift(1)
        bonde = low.rolling(p, min_periods=p).min().shift(1)
        out[f"dist_from_high_{p}"] = (close - kilele) / kilele
        out[f"dist_from_low_{p}"] = (close - bonde) / bonde

    # ---- muundo wa candle (ndani ya bar yenyewe — inajulikana ikifungwa) ----
    rng = (high - low).replace(0.0, np.nan)
    out["close_pos_in_range"] = (close - low) / rng

    # ---- spread na shughuli ----
    if "spread_p50" in bars.columns:
        out["spread_p50"] = bars["spread_p50"].astype(float)
        out["spread_per_atr"] = out["spread_p50"] / out["ATR_pips"].replace(0.0, np.nan)
    if "spread_p95" in bars.columns:
        # p95 ya spread NDANI ya bar. RCE (§3.1) inatumia p95 ya M5 kama
        # spike-guard kwa sababu H1 inaficha spikes za ndani ya bar — na hii
        # ndiyo kipimo hicho hicho, kilichopimwa moja kwa moja badala ya
        # kukadiriwa kwa bar ndogo zaidi.
        out["spread_p95"] = bars["spread_p95"].astype(float)
    if "n_ticks" in bars.columns:
        ticks = bars["n_ticks"].astype(float)
        out["tick_count"] = ticks
        out[f"tick_count_percentile_{PERCENTILE_WINDOW}d"] = ticks.rolling(
            PERCENTILE_WINDOW, min_periods=ATR_PERIOD
        ).rank(pct=True)

    # ---- muda ----
    index = pd.DatetimeIndex(out.index)
    local = index if hour_tz.upper() == "UTC" else index.tz_convert(hour_tz)
    out["hour"] = local.hour.astype(float)
    out["day_of_week"] = local.dayofweek.astype(float)

    out.attrs["symbol"] = symbol
    out.attrs["hour_tz"] = hour_tz
    return out


def check_no_lookahead(features, bars, *, n: int = 200) -> tuple[bool, list[str]]:
    """Kata bars za mwisho, jenga upya, na linganisha (R1).

    Feature inayotumia data ya baadaye itabadilika pale bars za baadaye
    zinapoondolewa. Isiyoitumia haitabadilika hata kidogo. Hakuna test nyingine
    inayoweza kusema hilo kwa uhakika ule ule.
    """
    import numpy as np

    if len(bars) <= n + PERCENTILE_WINDOW:
        raise FeatureError(f"bars {len(bars)} hazitoshi kwa ukaguzi wa {n}")

    fupi = build(bars.iloc[:-n], symbol=str(bars.attrs.get("symbol", "?")),
                 hour_tz=str(features.attrs.get("hour_tz", "UTC")))
    mbaya: list[str] = []
    for col in fupi.columns:
        a = features[col].iloc[: len(fupi)].to_numpy(dtype=float)
        b = fupi[col].to_numpy(dtype=float)
        sawa = np.isclose(a, b, rtol=1e-9, atol=1e-12, equal_nan=True)
        if not sawa.all():
            mbaya.append(col)
    return not mbaya, mbaya


def required_columns(names: Sequence[str]) -> tuple[str, ...]:
    """Safu zinazohitajika kwa majina yaliyotolewa, bila kujirudia."""
    return tuple(dict.fromkeys(names))
