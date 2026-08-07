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

from .quality import FAIL_OHLC, FAIL_STALE_FEED, CheckResult

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
    "n_m1_bars",
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
    # `n_m1_bars` (spec §4): dakika ngapi ndani ya bar zilikuwa na quote. Ndicho
    # kipimo cha ukamilifu WA KILA BAR: bar ya H1 yenye n_m1_bars=12 ilikuwa
    # kimya dakika 48, hata kama ilipokea ticks 5,000 kwenye dakika hizo 12.
    frame["minute"] = frame["timestamp"].dt.floor("min")
    # `kind="stable"`: ticks zenye timestamp ILE ILE (MT5 inatoa nyingi kama
    # hizo) zinabaki kwa mpangilio wa kufika. Bila hii, `open`/`close` ya bar
    # ingeweza kubadilika kati ya run na run — dataset isiyoweza kuzalishwa
    # upya (§8).
    frame = frame.set_index("timestamp").sort_index(kind="stable")

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
            "n_m1_bars": grouped["minute"].nunique(),
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
    empty["n_m1_bars"] = pd.Series(dtype="int64")
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


def check_bar_gaps(bars: pd.DataFrame, timeframe: str, max_gap_bars: int) -> CheckResult:
    """Ukaguzi wa 3 wa §3 kwa upande wa L2: `pengo ≤ max_gap_bars`.

    Pengo linahesabiwa **ndani ya siku** — usiku kati ya sessions na wikendi ni
    kalenda, si mapengo (§3). Bar isiyokuwepo ni dakika zilizokosa quote kabisa;
    mfululizo mrefu wa bars zisizokuwepo ndani ya siku moja ni pengo la kweli.
    """
    from .asof import TIMEFRAME_DURATION
    from .quality import FAIL_INTRASESSION_GAP

    if len(bars) < 2:
        return CheckResult(name="bar_gaps", passed=True, detail="bars chache mno kupima")
    step = TIMEFRAME_DURATION[timeframe]
    worst = 0
    for _, group in bars.groupby(bars.index.date):
        if len(group) < 2:
            continue
        missing = (group.index.to_series().diff().dropna() / step) - 1
        worst = max(worst, int(missing.max()) if len(missing) else 0)
    passed = worst <= max_gap_bars
    return CheckResult(
        name="bar_gaps",
        passed=passed,
        reason="" if passed else FAIL_INTRASESSION_GAP,
        value=float(worst),
        threshold=float(max_gap_bars),
        detail=f"bars {worst} mfululizo zisizokuwepo ndani ya siku moja",
    )


def check_flat_bars(bars: pd.DataFrame, max_flat: int) -> CheckResult:
    """Ukaguzi wa 8 wa §3 ukifanyika mahali pake: mfululizo wa bars `high == low`.

    Bar yenye `high == low` ilipokea quote **moja** kwa kipindi chote cha bar.
    Moja inatokea; mfululizo mrefu ni feed iliyoganda. Kipimo hiki kinahitaji
    bars — ndiyo maana kiko hapa, si L1 (§3).
    """
    if bars.empty:
        return CheckResult(name="flat_bars", passed=True, detail="hakuna bars")
    flat = bars["high"] == bars["low"]
    groups = (~flat).cumsum()
    longest = int(flat.groupby(groups).sum().max()) if len(flat) else 0
    passed = longest <= max_flat
    return CheckResult(
        name="flat_bars",
        passed=passed,
        reason="" if passed else FAIL_STALE_FEED,
        value=float(longest),
        threshold=float(max_flat),
        detail=f"bars {longest} mfululizo zenye high == low",
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
