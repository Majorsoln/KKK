"""DF-07 — AS-OF RULE: kinga kuu dhidi ya uvujaji (spec §4.1).

```
Wakati wa uamuzi t (= close ya bar ya H1):
   kwa kila TF k:  bar inayotumika = bar ya MWISHO yenye close_time ≤ t
```

Mfano wa spec: uamuzi wa H1 saa 10:00 UTC → D1 ni ya **jana iliyofungwa**,
H4 ni ile iliyofungwa 08:00, M15 ni ya 09:45. **Bar isiyofungwa HAITUMIKI kamwe.**

TF saba = nafasi saba za uvujaji. Module hii ndiyo sehemu MOJA inayojua sheria
hii; kila familia ya features inaipitia hapa, kwa hiyo hakuna mahali pa kuisahau.
"""

from __future__ import annotations

from datetime import timedelta
from typing import Mapping

import numpy as np
import pandas as pd

# Muda wa kila TF — unatumika kupata `close_time` kutoka index ya bar (open time).
TIMEFRAME_DURATION: dict[str, timedelta] = {
    "D1": timedelta(days=1),
    "H4": timedelta(hours=4),
    "H2": timedelta(hours=2),
    "H1": timedelta(hours=1),
    "M30": timedelta(minutes=30),
    "M15": timedelta(minutes=15),
    "M5": timedelta(minutes=5),
}


def close_times(bars: pd.DataFrame, timeframe: str) -> pd.DatetimeIndex:
    """`close_time` ya kila bar. Index ya bars ni **open time** (label='left')."""
    if timeframe not in TIMEFRAME_DURATION:
        raise ValueError(f"TF {timeframe!r} haipo kwenye spec §4")
    return bars.index + TIMEFRAME_DURATION[timeframe]


def asof_bar(bars: pd.DataFrame, timeframe: str, t: pd.Timestamp) -> pd.Series | None:
    """Bar ya MWISHO yenye `close_time ≤ t`. Isipokuwepo → `None`.

    Sawa-sawa (`close_time == t`) **inaruhusiwa**: bar imeshafungwa wakati ule
    ule wa uamuzi. Kubwa kuliko `t` haiwezi kamwe — hiyo ndiyo bar isiyofungwa.
    """
    if bars.empty:
        return None
    closes = close_times(bars, timeframe)
    usable = np.asarray(closes <= t)
    if not usable.any():
        return None
    return bars.iloc[int(np.flatnonzero(usable)[-1])]


def asof_snapshot(
    bars_by_tf: Mapping[str, pd.DataFrame], t: pd.Timestamp
) -> dict[str, pd.Series | None]:
    """Bars za TF zote kama zilivyokuwa wakati wa uamuzi `t` (spec §4.1)."""
    return {tf: asof_bar(bars, tf, t) for tf, bars in bars_by_tf.items()}


def decision_points(bars_h1: pd.DataFrame) -> pd.DatetimeIndex:
    """Nyakati za uamuzi = **close** za bars za H1 (spec §4.1, `decision_tf`)."""
    return pd.DatetimeIndex(close_times(bars_h1, "H1"), name="decision_time")


def assert_no_future_bars(
    bars_by_tf: Mapping[str, pd.DataFrame], t: pd.Timestamp
) -> None:
    """Kinga ya wazi: bar yoyote isiyofungwa ikichukuliwa → hitilafu, si onyo."""
    for tf, bars in bars_by_tf.items():
        bar = asof_bar(bars, tf, t)
        if bar is None:
            continue
        closed_at = bar.name + TIMEFRAME_DURATION[tf]
        if closed_at > t:
            raise AssertionError(
                f"UKIUKAJI WA AS-OF (§4.1): bar ya {tf} inayofungwa {closed_at} "
                f"imechukuliwa kwa uamuzi wa {t}"
            )
