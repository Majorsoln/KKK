"""Bar Builder — ticks → TF saba, DOCTRINE §4.1, R1.

Bars **hazipakuliwi**; zinajengwa kutoka ticks za bid/ask. Sababu ni §4.1: bila
bid/ask hakuna spread halisi kwa kila bar, na bila hiyo hakuna Calibration A,
hakuna lango la uchumi, na hakuna gharama ya RCE.

Sheria mbili zinazolinda dhidi ya kuona ya baadaye (R1):

**1. Bar isiyofungwa haitolewi.** Bar `[t0, t1)` inahesabiwa kuwa imefungwa pale
tu tulipoona tick kwa muda `≥ t1`. Bar ya mwisho ya dataset karibu daima ni ya
nusu; ikitolewa, feature ya bar hiyo ingekuwa imejengwa kwa data ambayo live
isingekuwa nayo bado.

**2. Bar tupu haitengenezwi.** Wikendi na likizo hazipati bars. Kujaza mbele
(`forward fill`) kungetengeneza bei isiyowahi kuwepo — na bei hiyo ingeonekana
inayoweza kutradiwa kwenye backtest.

OHLC inatoka **mid** = `(bid + ask) ÷ 2`. Njia ya trade (ingia kwa ask, toka kwa
bid) inahifadhiwa kando kama takwimu za spread, si kuchanganywa ndani ya OHLC.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .window import Stage

# TF → urefu. `D1` ni ya pekee: mpaka wake ni siku ya BROKER, si ya UTC.
INTRADAY: dict[str, str] = {
    "M5": "5min", "M15": "15min", "M30": "30min",
    "H1": "1h", "H2": "2h", "H4": "4h",
}
DAILY = "D1"
TIMEFRAMES = (DAILY, "H4", "H2", "H1", "M30", "M15", "M5")

BAR_COLUMNS = (
    "open", "high", "low", "close",
    "spread_mean", "spread_p50", "spread_p95", "spread_max",
    "n_ticks", "n_m1_bars",
)


class BarError(RuntimeError):
    """Ticks haziwezi kugeuzwa kuwa bars kwa TF iliyoombwa."""


@dataclass(frozen=True)
class BuildResult:
    symbol: str
    timeframe: str
    stage: Stage
    bars: Any
    n_ticks_in: int
    n_bars_out: int
    dropped_open_bar: bool

    def render(self) -> str:
        return (
            f"BARS — {self.symbol} · {self.timeframe} · ticks {self.n_ticks_in:,} "
            f"→ bars {self.n_bars_out:,}"
            + ("  (bar ya mwisho isiyofungwa imeachwa)" if self.dropped_open_bar else "")
        )

    def to_json(self) -> dict[str, Any]:
        return {
            "symbol": self.symbol, "timeframe": self.timeframe,
            "n_ticks_in": self.n_ticks_in, "n_bars_out": self.n_bars_out,
            "dropped_open_bar": self.dropped_open_bar, **self.stage.to_json(),
        }


def build(frame, timeframe: str, stage: Stage, *, day_tz: str = "UTC") -> BuildResult:
    """Jenga bars za `timeframe` kutoka ticks zilizokatwa kwa `stage`.

    `day_tz` inatumika kwa `D1` pekee: siku ya soko la FX haianzi saa sita usiku
    UTC. Inatoka config (`time.day_reset_tz`), si kudhaniwa hapa.
    """
    import pandas as pd

    if timeframe != DAILY and timeframe not in INTRADAY:
        raise BarError(f"TF isiyojulikana: {timeframe!r} — zinazoruhusiwa {TIMEFRAMES}")
    missing = {"timestamp", "bid", "ask"} - set(frame.columns)
    if missing:
        raise BarError(f"safu hazipo: {sorted(missing)} — §4.1 inadai bid/ask")

    symbol = str(frame.attrs.get("symbol", "?"))
    n_in = len(frame)
    if frame.empty:
        return BuildResult(symbol, timeframe, stage,
                           pd.DataFrame(columns=list(BAR_COLUMNS)), 0, 0, False)

    work = pd.DataFrame({
        "timestamp": pd.to_datetime(frame["timestamp"], utc=True),
        "mid": (frame["bid"].to_numpy(dtype=float) + frame["ask"].to_numpy(dtype=float)) / 2.0,
        "spread": frame["ask"].to_numpy(dtype=float) - frame["bid"].to_numpy(dtype=float),
    })
    work["minute"] = work["timestamp"].dt.floor("1min")

    # ---- mpaka wa bar ----
    #
    # `_localize` inatumika mara mbili: kwa mwanzo wa bar na kwa mwisho wake.
    # `ambiguous=False` na `nonexistent="shift_forward"` ni chaguo la KUAMUA,
    # si la kubahatisha — DST ya Ulaya inabadilika saa 02:00/03:00, si usiku wa
    # manane, kwa hiyo mpaka wa siku hauguswi. Chaguo lipo ili config ya tz
    # nyingine isilipuke kimya.
    if timeframe == DAILY:
        local_midnight = (
            work["timestamp"].dt.tz_convert(day_tz).dt.normalize().dt.tz_localize(None)
        )
        work["bar"] = _localize(local_midnight, day_tz).dt.tz_convert("UTC")
    else:
        work["bar"] = work["timestamp"].dt.floor(INTRADAY[timeframe])

    grouped = work.groupby("bar", sort=True)
    bars = pd.DataFrame({
        "open": grouped["mid"].first(),
        "high": grouped["mid"].max(),
        "low": grouped["mid"].min(),
        "close": grouped["mid"].last(),
        "spread_mean": grouped["spread"].mean(),
        "spread_p50": grouped["spread"].median(),
        "spread_p95": grouped["spread"].quantile(0.95),
        "spread_max": grouped["spread"].max(),
        "n_ticks": grouped["mid"].size(),
        "n_m1_bars": grouped["minute"].nunique(),
    })

    # ---- R1: bar isiyofungwa haitolewi ----
    #
    # Bar imefungwa pale TU tulipoona tick kwa muda `≥ mwisho wake`. Bila
    # ushahidi huo, bar ya mwisho ni ya nusu — na feature yake ingekuwa
    # imejengwa kwa data ambayo live isingekuwa nayo bado.
    last_tick = work["timestamp"].max()
    ends = bar_ends(bars.index, timeframe, day_tz)
    closed = ends <= last_tick
    dropped = bool((~closed).any())
    bars = bars[closed]

    bars.index.name = "timestamp"
    return BuildResult(symbol, timeframe, stage, bars, n_in, len(bars), dropped)


def _localize(naive, tz):
    """Weka timezone kwa chaguo la KUAMUA, si la kubahatisha."""
    return naive.dt.tz_localize(tz, ambiguous=False, nonexistent="shift_forward")


def bar_ends(index, timeframe: str, day_tz: str):
    """Mwisho halisi wa kila bar.

    Kwa TF za ndani ya siku, urefu ni thabiti. Kwa `D1` si hivyo: siku ya DST
    ina saa 23 au 25, na kutumia `+1 day` kungehesabu bar kuwa imefungwa saa moja
    kabla au baada ya ukweli — mara mbili kwa mwaka, kimya kimya.
    """
    import pandas as pd

    if timeframe != DAILY:
        return index + pd.Timedelta(INTRADAY[timeframe])
    local = pd.Series(index.tz_convert(day_tz).tz_localize(None) + pd.Timedelta(days=1))
    return pd.DatetimeIndex(_localize(local, day_tz)).tz_convert("UTC")


def check_ohlc(bars) -> tuple[bool, int]:
    """`low ≤ open, close ≤ high` kwa kila bar — §4.3.

    Ikivunjika, aggregation ina kasoro, na kila feature inayotokana nayo ni ya
    uongo kwa namna isiyoonekana kwenye matokeo.
    """
    import numpy as np

    if bars.empty:
        return True, 0
    o, h, l, c = (bars[k].to_numpy(dtype=float) for k in ("open", "high", "low", "close"))
    bad = int(np.sum(~((l <= o) & (o <= h) & (l <= c) & (c <= h) & (l <= h))))
    return bad == 0, bad
