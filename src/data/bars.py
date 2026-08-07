"""DF-06 — L2: bars za TF 7 zilizojengwa kutoka TICKS + spread stats (spec §4).

> "Bars zote saba zinajengwa kutoka TICKS kwenye repo yetu, si kupakuliwa
> kutoka broker. Sababu: broker anaweza kutumia mipaka tofauti ya bar;
> tukijenga wenyewe, D1/H4/H2/H1/M30/M15/M5 zote zinatoka chanzo kimoja na
> zinalingana kikamilifu."

Kila bar inabeba, zaidi ya OHLCV:

```
spread_mean · spread_p50 · spread_p95 · spread_max      ← malighafi ya RCE §3.1
n_ticks · is_valid
```

**Bei ya OHLC ni MID** (`(bid + ask) / 2`). Sababu: features ni scale-free na
zinahitaji bei moja isiyo na upendeleo wa upande; spread inahifadhiwa **kando**
kama takwimu, si kuchanganywa na bei. Labels za touch hazitegemei bars hata
kidogo — zinatatuliwa kwa ticks kwa bei ya kufungia (§5 ya standard).

**Ukaguzi wa 4 wa L1 (OHLC sanity) unafanyika HAPA**, kwa sababu ticks hazina
OHLC — bar ndipo inapopatikana (`check_ohlc_sanity`).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import pandas as pd

from .quality import FAIL_OHLC, CheckResult

# Spec §4 / config `bars.timeframes`. Kila TF ina kazi yake (§0 ya RCE).
TIMEFRAME_RULES: dict[str, str] = {
    "D1": "1D",
    "H4": "4h",
    "H2": "2h",
    "H1": "1h",
    "M30": "30min",
    "M15": "15min",
    "M5": "5min",
}

BAR_COLUMNS: tuple[str, ...] = (
    "open",
    "high",
    "low",
    "close",
    "volume",
    "spread_mean",
    "spread_p50",
    "spread_p95",
    "spread_max",
    "n_ticks",
    "is_valid",
)


@dataclass(frozen=True)
class BarBuildResult:
    timeframe: str
    bars: pd.DataFrame

    @property
    def rows(self) -> int:
        return int(len(self.bars))


def _pip_size(symbol: str) -> float:
    upper = symbol.upper()
    if upper.startswith(("XAU", "XAG")) or upper[3:6] == "JPY":
        return 0.01
    return 0.0001


def build_bars(ticks: pd.DataFrame, timeframe: str, symbol: str) -> pd.DataFrame:
    """Bars za TF moja kutoka ticks (schema ya kawaida ya §2.1).

    Mipaka ya bar ni ya **UTC**, imefungwa kushoto (`[open, close)`) — ndiyo
    maana D1 inaanza 00:00 UTC na si saa ya broker. Timezone ya broker
    inahusika kwenye rollover/swap pekee (§3.4 ya RCE), si kwenye bars.
    """
    if timeframe not in TIMEFRAME_RULES:
        raise ValueError(f"TF {timeframe!r} haipo kwenye spec §4 ({sorted(TIMEFRAME_RULES)})")
    if ticks.empty:
        return _empty_bars()

    pip = _pip_size(symbol)
    frame = ticks.loc[:, ["timestamp", "bid", "ask", "bid_vol", "ask_vol"]].copy()
    frame["mid"] = (frame["bid"] + frame["ask"]) / 2.0
    frame["spread_pips"] = (frame["ask"] - frame["bid"]) / pip
    frame["vol"] = frame["bid_vol"].fillna(0.0) + frame["ask_vol"].fillna(0.0)
    frame = frame.set_index("timestamp").sort_index()

    grouped = frame.resample(TIMEFRAME_RULES[timeframe], label="left", closed="left")
    bars = pd.DataFrame(
        {
            "open": grouped["mid"].first(),
            "high": grouped["mid"].max(),
            "low": grouped["mid"].min(),
            "close": grouped["mid"].last(),
            "volume": grouped["vol"].sum(),
            "spread_mean": grouped["spread_pips"].mean(),
            "spread_p50": grouped["spread_pips"].quantile(0.50),
            "spread_p95": grouped["spread_pips"].quantile(0.95),
            "spread_max": grouped["spread_pips"].max(),
            "n_ticks": grouped["mid"].count(),
        }
    )
    # Bar bila tick hata moja HAIPO — si bar tupu. Data ya kubuni ni marufuku (§3).
    bars = bars[bars["n_ticks"] > 0]
    bars["is_valid"] = True
    bars.index.name = "timestamp"
    return bars[list(BAR_COLUMNS)]


def _empty_bars() -> pd.DataFrame:
    empty = pd.DataFrame({name: pd.Series(dtype="float64") for name in BAR_COLUMNS})
    empty["n_ticks"] = pd.Series(dtype="int64")
    empty["is_valid"] = pd.Series(dtype="bool")
    empty.index = pd.DatetimeIndex([], tz="UTC", name="timestamp")
    return empty


def build_all_timeframes(
    ticks: pd.DataFrame, symbol: str, timeframes: Iterable[str]
) -> dict[str, pd.DataFrame]:
    """TF zote kutoka ticks ZILE ZILE — ndiyo maana zinalingana kikamilifu."""
    return {tf: build_bars(ticks, tf, symbol) for tf in timeframes}


def check_ohlc_sanity(bars: pd.DataFrame) -> CheckResult:
    """Ukaguzi wa 4 wa §3, ukifanyika mahali pake: `low ≤ min(o,c) ≤ max(o,c) ≤ high`."""
    if bars.empty:
        return CheckResult(name="ohlc_sanity", passed=True, detail="hakuna bars")
    lo = bars["low"]
    hi = bars["high"]
    body_low = bars[["open", "close"]].min(axis=1)
    body_high = bars[["open", "close"]].max(axis=1)
    violations = int(((lo > body_low) | (body_high > hi) | (lo > hi)).sum())
    return CheckResult(
        name="ohlc_sanity",
        passed=violations == 0,
        reason="" if violations == 0 else FAIL_OHLC,
        value=float(violations),
        threshold=0.0,
        detail=f"bars {violations} kati ya {len(bars)} zimekiuka",
    )


def write_bars(bars: pd.DataFrame, root: Path, symbol: str, timeframe: str) -> Path:
    """Andika L2 kwa `symbol=<SYM>/tf=<TF>/bars.parquet` (spec §9)."""
    target = Path(root) / f"symbol={symbol}" / f"tf={timeframe}" / "bars.parquet"
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_suffix(".parquet.tmp")
    bars.reset_index().to_parquet(tmp, index=False, compression="zstd")
    tmp.replace(target)
    return target


def read_bars(root: Path, symbol: str, timeframe: str) -> pd.DataFrame:
    path = Path(root) / f"symbol={symbol}" / f"tf={timeframe}" / "bars.parquet"
    frame = pd.read_parquet(path)
    return frame.set_index("timestamp").sort_index()
