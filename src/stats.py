"""Takwimu ndogo zinazohitajika mahali pengi — hakuna dependency mpya.

Project hii ina `numpy` na `pandas` pekee (`pyproject.toml`). Kuongeza `scipy`
kwa ajili ya kipimo kimoja kungeongeza uso wa utegemezi kwa faida ndogo, kwa
hiyo `t_one_sided` inahesabiwa hapa — kwa njia ya kawaida ya kitabu, na
inathibitishwa dhidi ya **jedwali la t lililochapishwa** kwenye tests.

---

**Kwa nini `t` na si `z`.**

Sampuli ndogo ndiyo tatizo lote. `z` inadhani `n` ni kubwa: kwa `n = 2`
ingetoa ukingo ule ule wa `n = 200`, na mgombea wa trades mbili angepita kwa
ujasiri asiokuwa nao. `t` inaadhibu ujinga wa sampuli ndogo kwa ujenzi wake:
`df = 1` inadai mara 6.31 ya standard error, `df = 29` inadai 1.70.

`df = 0` (yaani `n = 1`) haina `t` — na hilo ni jibu sahihi, si kosa:
uchunguzi mmoja hauna standard error, kwa hiyo hauna ukingo wa uhakika.
"""

from __future__ import annotations

import math
from functools import lru_cache

# Kiwango cha uhakika. **Si namba mpya**: ni p95 ile ile inayotumika kila mahali
# kwenye mfumo huu — sakafu ya kelele (§9.2), spike-guard ya spread (§3.1), na
# cap ya slippage (Calibration A). Kubadilisha hapa peke yake kungeleta viwango
# viwili vya uhakika kwenye mfumo mmoja.
CONFIDENCE = 0.95

_MAX_ITER = 200
_EPS = 3.0e-15
_FPMIN = 1.0e-300


class StatsError(ValueError):
    """Kipimo kimeombwa nje ya masafa yake."""


@lru_cache(maxsize=512)
def t_one_sided(df: int, p: float = CONFIDENCE) -> float:
    """Quantile ya upande MMOJA ya Student-t: `t` ambayo `P(T ≤ t) = p`.

    Inatafutwa kwa bisection juu ya CDF, kisha inahifadhiwa — inategemea `df`
    pekee, kwa hiyo run ya wagombea 1,000 inaihesabu mara chache tu.
    """
    if df < 1:
        raise StatsError(f"df {df} < 1 — uchunguzi mmoja hauna ukingo wa uhakika")
    if not 0.5 < p < 1.0:
        raise StatsError(f"p {p} nje ya (0.5, 1.0)")

    lo, hi = 0.0, 1.0
    while _t_cdf(hi, df) < p:
        hi *= 2.0
        if hi > 1e6:                                  # pragma: no cover
            return hi
    for _ in range(_MAX_ITER):
        kati = (lo + hi) / 2.0
        if _t_cdf(kati, df) < p:
            lo = kati
        else:
            hi = kati
        if hi - lo < 1e-12:
            break
    return (lo + hi) / 2.0


def mean_lower_bound(values, p: float = CONFIDENCE) -> float:
    """Mpaka wa CHINI wa uhakika wa wastani: `x̄ − t·s/√n`.

    Hii ndiyo namba inayopaswa kulinganishwa na kizingiti pale sampuli ni ndogo.
    Wastani wenyewe hausemi chochote kuhusu ukubwa wa sampuli iliyoutoa —
    trades moja na trades mia zote zinatoa "wastani".

    `NaN` ikiwa `n < 2`: hakuna standard error, kwa hiyo hakuna mpaka. Si sifuri
    na si wastani wenyewe — zote mbili zingekuwa jibu lililobuniwa.
    """
    import numpy as np

    x = np.asarray(list(values), dtype=float)
    x = x[np.isfinite(x)]
    n = len(x)
    if n < 2:
        return float("nan")

    sd = float(x.std(ddof=1))
    if sd == 0.0:
        # Kila uchunguzi ni sawa: hakuna kutokuwa na uhakika kunakoweza kupimwa,
        # kwa hiyo wastani wenyewe ndio mpaka.
        return float(x.mean())
    return float(x.mean() - t_one_sided(n - 1, p) * sd / math.sqrt(n))


# ===========================================================================
# CDF ya Student-t, kupitia incomplete beta
# ===========================================================================


def _t_cdf(t: float, df: int) -> float:
    x = df / (df + t * t)
    nusu = 0.5 * _betai(0.5 * df, 0.5, x)
    return 1.0 - nusu if t > 0 else nusu


def _betai(a: float, b: float, x: float) -> float:
    """Beta isiyokamilika iliyodhibitiwa, `I_x(a, b)`."""
    if x <= 0.0:
        return 0.0
    if x >= 1.0:
        return 1.0
    mbele = math.exp(
        math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b)
        + a * math.log(x) + b * math.log1p(-x)
    )
    if x < (a + 1.0) / (a + b + 2.0):
        return mbele * _betacf(a, b, x) / a
    return 1.0 - mbele * _betacf(b, a, 1.0 - x) / b


def _betacf(a: float, b: float, x: float) -> float:
    """Sehemu inayoendelea ya `_betai` — mbinu ya kawaida ya Lentz."""
    qab, qap, qam = a + b, a + 1.0, a - 1.0
    c = 1.0
    d = 1.0 - qab * x / qap
    if abs(d) < _FPMIN:
        d = _FPMIN
    d = 1.0 / d
    h = d

    for m in range(1, _MAX_ITER + 1):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1.0 + aa * d
        if abs(d) < _FPMIN:
            d = _FPMIN
        c = 1.0 + aa / c
        if abs(c) < _FPMIN:
            c = _FPMIN
        d = 1.0 / d
        h *= d * c

        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1.0 + aa * d
        if abs(d) < _FPMIN:
            d = _FPMIN
        c = 1.0 + aa / c
        if abs(c) < _FPMIN:
            c = _FPMIN
        d = 1.0 / d
        delta = d * c
        h *= delta
        if abs(delta - 1.0) < _EPS:
            break
    return h
