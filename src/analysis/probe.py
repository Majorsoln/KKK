"""Mnyororo wa udhibiti chanya — DOCTRINE §7.1, LANGO 1.

```
ticks → vikapu → KUPANDA EDGE → RCE → trades → curve ya siku → bootstrap
                      ↑
             hapa, si kwenye P&L
```

Familia inayotumika hapa ni ya **umbo la F0**: nanga ya kalenda, leg moja,
bila ishara. Si dhana ya F0 inayopimwa — ni **injini**. Ndiyo maana udhibiti
unaendeshwa kabla ya familia yoyote kujengwa: kama injini haioni edge
iliyopandwa, hakuna sababu ya kujenga kitu cha kuipitisha ndani yake.

---

**Ticks zinazalishwa kwa madirisha yanayosomwa pekee.** `execute` inasoma
sekunde 300 kuzunguka kuingia na kutoka. Kuzalisha mfululizo mzima wa miaka
minane kungekuwa rows milioni 250 ambazo 99.9% yake hazitasomwa kamwe.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any, Sequence

from src.analysis.bootstrap import test_mean_positive
from src.analysis.control import (
    CONSTANT,
    _nano,
    _nanos,
    PowerPoint,
    Window,
    delta,
    edge_per_window,
    inject,
)
from src.analysis.curve import daily_r
from src.backtest.runner import execute
from src.events.clock import LONDON_OPEN, NY_NOON, ni_siku_ya_kazi
from src.portfolio.basket import Basket, Leg

PIP = 0.0001
WINDOW_SECONDS = 300


@dataclass(frozen=True)
class ProbeSpec:
    """Vigezo vyote vya udhibiti. Vinaingia kwenye ripoti kama vilivyo."""

    n_days: int = 500
    sl_pips: float = 25.0
    spread_pips: float = 1.6
    sigma_pips_per_hour: float = 13.0
    commission: float = 7.0
    pip_value: float = 10.0
    balance: float = 10_000.0
    start: date = date(2018, 1, 1)

    def days(self) -> list[date]:
        out, d = [], self.start
        while len(out) < self.n_days:
            if ni_siku_ya_kazi(d):
                out.append(d)
            d += timedelta(days=1)
        return out


def windows_for(days: Sequence[date]) -> list[Window]:
    """Madirisha ya umbo la F0 mguu A: 08:00 London → 12:00 New York, SELL."""
    return [Window(LONDON_OPEN.at(d), NY_NOON.at(d), "SELL") for d in days]


def synthetic_ticks(windows: Sequence[Window], spec: ProbeSpec, *, seed: int):
    """Ticks kwa madirisha yanayosomwa pekee: `[t, t+300s)` kwa kila ncha.

    Bei ni random walk isiyo na edge. `sigma_pips_per_hour` inatawala
    mtawanyiko; spread ni thabiti kwa sababu tunapanda **edge**, si ukwasi.
    """
    import numpy as np
    import pandas as pd

    rng = np.random.default_rng(seed)
    vipande = []
    for w in windows:
        vipande.append((w.start, WINDOW_SECONDS))
        vipande.append((w.end, WINDOW_SECONDS))

    stamps = []
    for t0, n in vipande:
        stamps.append(pd.date_range(t0, periods=n, freq="1s", tz="UTC"))
    idx = stamps[0].append(stamps[1:]) if len(stamps) > 1 else stamps[0]
    idx = idx.sort_values()

    # Random walk juu ya muda HALISI kati ya ticks — mapengo kati ya madirisha
    # yanatoa mwendo mkubwa, kama soko linavyofanya.
    #
    # `_nanos`, si `astype("int64")`: pandas inahifadhi kwa mikrosekunde, kwa
    # hiyo `astype` ingetoa sekunde 0.001 badala ya 1. Mapengo ya masaa
    # yangebanwa hadi sekunde moja na mfululizo usingesonga kati ya madirisha —
    # σ ingekuwa ndogo mara kumi kuliko soko, na probe ingekuwa rahisi mno.
    sekunde = np.diff(_nanos(pd.Series(idx))) / 1e9
    sd = spec.sigma_pips_per_hour * PIP / math.sqrt(3600.0)
    hatua = rng.normal(0.0, sd, size=len(idx) - 1) * np.sqrt(
        np.maximum(sekunde, 1.0))
    mid = 1.20 + np.concatenate([[0.0], np.cumsum(hatua)])
    nusu = spec.spread_pips * PIP / 2.0

    return pd.DataFrame({"timestamp": idx, "bid": mid - nusu, "ask": mid + nusu})


def _market(spec: ProbeSpec) -> dict:
    from src.rce.budget import AccountState
    from src.rce.cost import SymbolSpec

    return {
        "spec": SymbolSpec(symbol="EURUSD", point=0.00001, contract_size=100_000,
                           volume_min=0.01, volume_step=0.01, volume_max=50.0),
        "account": AccountState(current_balance=spec.balance, today_profit=0.0,
                                today_loss=0.0, open_positions=0),
        "h1_spreads": [spec.spread_pips] * 120,
        "m5_spreads": [spec.spread_pips] * 300,
        "pip_value_acct": spec.pip_value,
        "commission_round_turn": spec.commission,
        "pip": PIP,
    }


def run_once(
    spec: ProbeSpec,
    *,
    cfg,
    pips: float,
    shape: str = CONSTANT,
    seed: int = 0,
    B: int = 500,
) -> tuple[Any, Any]:
    """Run moja kamili: kupanda → utekelezaji → curve → bootstrap.

    Inarudisha `(curve, matokeo ya bootstrap)`.
    """
    import pandas as pd

    siku = spec.days()
    madirisha = windows_for(siku)
    ticks = synthetic_ticks(madirisha, spec, seed=seed)

    if pips != 0.0:
        kiasi = edge_per_window(madirisha, pips, shape, seed=seed + 7919)
        ticks = inject(ticks, madirisha, kiasi, pip=PIP)

    t = _nanos(ticks["timestamp"])
    soko = {"EURUSD": _market(spec)}

    trades = []
    for d, w in zip(siku, madirisha):
        # Ticks za tukio hili pekee — VWAP isipite mfululizo mzima.
        a, b = _nano(w.start), _nano(w.end)
        dirisha = WINDOW_SECONDS * 1_000_000_000
        ndani = ((t >= a) & (t < a + dirisha)) | ((t >= b) & (t < b + dirisha))
        kipande = ticks.loc[ndani]

        kikapu = Basket(
            family="PROBE", basket_id=f"PROBE:{d}",
            legs=(Leg(symbol="EURUSD", side="SELL", sl_pips=spec.sl_pips),),
            entry_at=w.start, planned_exit_at=w.end, priority=1,
        )
        out = execute(kikapu, cfg=cfg, ticks_by_symbol={"EURUSD": kipande},
                      market=soko, window_seconds=WINDOW_SECONDS)
        trades.extend(out.trades)

    curve = daily_r(trades, days=siku)
    return curve, test_mean_positive(curve, B=B, seed=seed + 104729)


def power_curve(
    spec: ProbeSpec,
    *,
    cfg,
    grid: Sequence[float],
    shape: str = CONSTANT,
    n_replicates: int = 20,
    alpha: float = 0.05,
    B: int = 500,
    seed: int = 0,
    progress=None,
) -> list[PowerPoint]:
    """Kiwango cha kuona dhidi ya `δ`, kwa kila ukubwa wa edge."""
    import numpy as np

    out = []
    for pips in grid:
        deltas, siku, hai, walipita = [], [], [], 0
        for i in range(n_replicates):
            curve, r = run_once(spec, cfg=cfg, pips=pips, shape=shape,
                                seed=seed + i * 1_000_003, B=B)
            deltas.append(delta(curve))
            siku.append(curve.n)
            hai.append(curve.n_active)
            walipita += int(r.p_value < alpha)
            if progress:
                progress(f"   {shape} {pips:>5.2f}p  {i + 1}/{n_replicates}  "
                         f"p {r.p_value:.4f}")
        out.append(PowerPoint(
            shape=shape, pips=pips, n_replicates=n_replicates,
            detected=walipita,
            delta_median=float(np.median(deltas)),
            n_days_median=float(np.median(siku)),
            n_active_median=float(np.median(hai)),
        ))
    return out


__all__ = ["PIP", "WINDOW_SECONDS", "ProbeSpec", "windows_for",
           "synthetic_ticks", "run_once", "power_curve"]
