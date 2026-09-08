"""Udhibiti chanya — DOCTRINE §7.1, LANGO 1.

Toleo la kwanza lilikalibrisha **kiwango cha kukosea kwa kupitisha** na
halikuwahi kupima **uwezo wa kuona**. Kwa hiyo halikuweza kutofautisha:

```
"hakuna edge kwenye soko"        dhidi ya        "kipimo hakiwezi kuiona"
```

Miezi sita ya matokeo ya sifuri, na hakuna njia ya kujua yalimaanisha lipi.

---

**Kupanda kunafanywa kwenye BEI, kabla ya uteuzi.**

Kuongeza pips kwenye P&L ya trades **zilizoshachaguliwa** kungepima lango la
takwimu pekee. Kila kitu kingine — spread, sizing ya RCE, kubana kwa lango,
atomiki ya kikapu — kingekuwa kimeepukwa, na curve ya nguvu ingekuwa ya
matumaini kupita kiasi.

Hapa drift inaongezwa kwenye **ticks zenyewe** ndani ya dirisha la kushikilia.
Familia inachukua bei zake kutoka kwenye mfululizo uliopandwa, RCE inahesabu
gharama juu yake, na kila hatua ya chini inaitikia kama ingeitikia kwa edge
halisi.

---

**Maumbo matatu, si moja.**

Edge halisi si thabiti. `INJECT_CONSTANT` ni **kikomo cha juu** — ni mbadala
ambao kila kipimo cha wastani kina nguvu kubwa zaidi dhidi yake. Kupanga kwa
umbo hilo pekee kungekadiria uwezo wa kuona kwa juu.

* `CONSTANT`   — pips zilezile kila tukio
* `CLUSTERED`  — edge ipo kwenye ~30% ya miezi pekee, sifuri kwingine
* `SERIAL`     — edge inabadilika kwa AR(1) kati ya matukio

---

**Kuripoti ni dhidi ya `δ`, si gridi ya (pips, matukio).**

```
δ = (μ / σ) · √n
```

Kila kitu kinaingia kupitia namba hiyo moja. Nguvu ya kinadharia ni
`Φ(δ − z_α)`. **Pengo kati ya curve iliyopimwa na ya kinadharia ndiyo
upungufu wa injini** — na ndiyo namba ambayo haikuwahi kuonekana.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any, Sequence

CONSTANT = "CONSTANT"
CLUSTERED = "CLUSTERED"
SERIAL = "SERIAL"
SHAPES = (CONSTANT, CLUSTERED, SERIAL)

# Fungu la miezi lenye edge kwenye umbo la `CLUSTERED`. Limetangazwa hapa
# mara moja; si kigezo cha kurekebishwa baada ya kuona matokeo.
CLUSTER_FRACTION = 0.30
SERIAL_RHO = 0.7


class ControlError(RuntimeError):
    """Udhibiti hauwezi kuendeshwa kama ulivyoombwa."""


# ===========================================================================
# Kupanda edge kwenye ticks
# ===========================================================================


@dataclass(frozen=True)
class Window:
    """Dirisha la kushikilia, na upande ambao familia inabet."""

    start: datetime
    end: datetime
    side: str                       # BUY / SELL — mwelekeo wa familia

    def __post_init__(self) -> None:
        if self.end <= self.start:
            raise ControlError("dirisha lisilo halali")


def edge_per_window(
    windows: Sequence[Window],
    pips: float,
    shape: str,
    *,
    seed: int = 0,
) -> list[float]:
    """Pips za kupanda kwa kila dirisha, kwa umbo lililoombwa.

    Wastani unahifadhiwa kwa maumbo yote: `CLUSTERED` inatoa `pips/0.30` kwa
    miezi iliyochaguliwa na sifuri kwingine, kwa hiyo wastani wa jumla unabaki
    `pips`. Bila hilo, maumbo yangekuwa yakipima `δ` tofauti na ulinganisho
    ungekuwa wa vitu viwili.
    """
    import numpy as np

    if shape not in SHAPES:
        raise ControlError(f"umbo halijulikani: {shape!r} — ni {SHAPES}")
    n = len(windows)
    if n == 0:
        return []
    rng = np.random.default_rng(seed)

    if shape == CONSTANT:
        return [pips] * n

    if shape == CLUSTERED:
        miezi = sorted({(w.start.year, w.start.month) for w in windows})
        k = max(1, int(round(len(miezi) * CLUSTER_FRACTION)))
        teule = set(map(tuple, rng.permutation(np.array(miezi))[:k].tolist()))
        kiwango = pips / (k / len(miezi))
        return [kiwango if (w.start.year, w.start.month) in teule else 0.0
                for w in windows]

    # SERIAL — AR(1) yenye wastani `pips`, isiyoruhusu kupinduka kwa ishara
    # kuwa mara kwa mara: ni edge inayobadilika, si inayogeuka.
    x = np.empty(n)
    x[0] = rng.normal(0.0, 1.0)
    for i in range(1, n):
        x[i] = SERIAL_RHO * x[i - 1] + rng.normal(
            0.0, math.sqrt(1 - SERIAL_RHO ** 2))
    return list(pips * (1.0 + 0.6 * x))


def inject(ticks, windows: Sequence[Window], pips: Sequence[float], *,
           pip: float):
    """Ongeza drift kwenye ticks ndani ya kila dirisha. **Bei, si P&L.**

    Drift inapanda kwa mstari ndani ya dirisha kisha **inabaki**, ili
    mfululizo usiwe na mruko wa bandia kwenye mpaka wa dirisha. Familia inauza
    → drift ni ya kushuka; inanunua → ya kupanda.

    `bid` na `ask` zinasogezwa kwa kiasi kilekile, kwa hiyo **spread
    haibadiliki** — tunapanda edge, si ukwasi.
    """
    import numpy as np
    import pandas as pd

    if len(windows) != len(pips):
        raise ControlError(f"madirisha {len(windows)} dhidi ya pips {len(pips)}")

    out = ticks.copy()
    t = _nanos(out["timestamp"])
    offset = np.zeros(len(out), dtype=float)

    for w, p in zip(windows, pips):
        if p == 0.0:
            continue
        a, b = _nano(w.start), _nano(w.end)
        ishara = -1.0 if w.side.upper() == "SELL" else 1.0
        jumla = ishara * p * pip

        ndani = (t >= a) & (t < b)
        baada = t >= b
        if ndani.any():
            sehemu = (t[ndani] - a) / (b - a)
            offset[ndani] += jumla * sehemu
        offset[baada] += jumla

    out["bid"] = out["bid"].to_numpy(dtype=float) + offset
    out["ask"] = out["ask"].to_numpy(dtype=float) + offset
    return out


def _nanos(series):
    """Nanosekunde kama `int64`. **Si `astype("int64")` peke yake.**

    Pandas mpya inahifadhi datetime kwa mikrosekunde, kwa hiyo
    `astype("int64")` inatoa µs. Kulinganisha na `datetime.timestamp() × 1e9`
    kunatoa tofauti ya mara 1,000 — na mask inakuwa TUPU kimya, si kosa.

    Kasoro hii ilipatikana ikiwa imefanya kupanda edge kutokuwa na athari
    yoyote (2026-09-08). Udhibiti chanya ungetoa jibu la uongo: "injini ni
    kipofu" wakati bei hazikuwa zimebadilishwa hata kidogo.
    """
    import pandas as pd

    s = pd.to_datetime(series, utc=True)
    return s.dt.as_unit("ns").astype("int64").to_numpy()


def _nano(moment) -> int:
    import pandas as pd

    return int(pd.Timestamp(moment).as_unit("ns").value)


# ===========================================================================
# Curve ya nguvu
# ===========================================================================


def delta(curve, *, mean: float | None = None) -> float:
    """`δ = (μ/σ)·√n` — parameter isiyo ya kati ya kipimo.

    Kila kitu kinaingia kupitia namba hii moja: ukubwa wa edge, mtawanyiko wa
    P&L, na idadi ya siku. Ndiyo maana kuripoti dhidi yake kunafichua upungufu
    wa injini, wakati gridi ya (pips, matukio) ingeuficha.
    """
    import numpy as np

    x = curve.values() if hasattr(curve, "values") else np.asarray(curve, float)
    x = x[np.isfinite(x)]
    sd = float(x.std(ddof=1)) if x.size > 1 else 0.0
    if sd == 0.0:
        return float("inf") if (mean if mean is not None else x.mean()) > 0 else 0.0
    mu = float(x.mean()) if mean is None else mean
    return (mu / sd) * math.sqrt(x.size)


def theoretical_power(d: float, alpha: float = 0.05) -> float:
    """`Φ(δ − z_α)` — nguvu ya kipimo bora chini ya normal.

    Ni **kikomo cha juu**, si lengo: kinadhania uhuru, normality, na kwamba
    kipimo kinajua `σ`. Injini halisi itakuwa chini yake. Pengo ndilo swali.
    """
    if not math.isfinite(d):
        return 1.0
    z = 1.6448536269514722                      # Φ⁻¹(0.95)
    if alpha != 0.05:
        z = _probit(1.0 - alpha)
    return 0.5 * math.erfc(-(d - z) / math.sqrt(2.0))


def _probit(p: float) -> float:
    """`Φ⁻¹` kwa bisection — hakuna scipy kwenye dependencies."""
    lo, hi = -10.0, 10.0
    for _ in range(200):
        mid = (lo + hi) / 2.0
        if 0.5 * math.erfc(-mid / math.sqrt(2.0)) < p:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2.0


@dataclass(frozen=True)
class PowerPoint:
    """Nukta moja kwenye curve ya nguvu."""

    shape: str
    pips: float
    n_replicates: int
    detected: int
    delta_median: float
    n_days_median: float
    n_active_median: float

    @property
    def rate(self) -> float:
        return self.detected / self.n_replicates if self.n_replicates else 0.0

    @property
    def theoretical(self) -> float:
        return theoretical_power(self.delta_median)

    @property
    def gap(self) -> float:
        """Kinadharia − iliyopimwa. **Ndio upungufu wa injini.**"""
        return self.theoretical - self.rate

    def render(self) -> str:
        return (f"{self.shape:<10} {self.pips:>5.2f}p  δ {self.delta_median:>6.2f}  "
                f"iliyopimwa {self.rate:>5.1%}  kinadharia {self.theoretical:>5.1%}  "
                f"pengo {self.gap:>+5.1%}  "
                f"siku {self.n_days_median:>5.0f} (hai {self.n_active_median:>4.0f})")

    def to_json(self) -> dict[str, Any]:
        return {"shape": self.shape, "pips": self.pips,
                "n_replicates": self.n_replicates, "detected": self.detected,
                "rate": self.rate, "delta": self.delta_median,
                "theoretical": self.theoretical, "gap": self.gap,
                "n_days": self.n_days_median, "n_active": self.n_active_median}


__all__ = ["CONSTANT", "CLUSTERED", "SERIAL", "SHAPES", "CLUSTER_FRACTION",
           "SERIAL_RHO", "ControlError", "Window", "edge_per_window", "inject",
           "delta", "theoretical_power", "PowerPoint"]
