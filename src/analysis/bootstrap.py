"""Block bootstrap ya mfululizo tegemezi — DOCTRINE §7.2.

`p-value` ya curve ya siku haiwezi kutoka kwenye t-test. Sababu mbili:

1. **P&L ya siku ina mfululizo.** Siku ya leo inahusiana na ya jana — kwa
   volatility, kwa regime, kwa position zinazoendelea. t-test inadhania uhuru,
   na inatoa `p` ndogo kuliko inavyostahili.
2. **Mgawanyo si wa kawaida.** Siku nyingi ni sifuri, chache ni kubwa. Mkia
   mzito unavunja dhana ya normal, hasa kwenye ncha ambayo ndiyo tunayoipima.

Stationary bootstrap (Politis–Romano 1994) inashughulikia zote mbili: inachukua
**vipande** vya urefu wa nasibu wa kijiometri, kwa hiyo muundo wa muda ndani ya
kipande unabaki.

---

**Urefu wa kipande haubuniwi.** Politis–White (2004) inauhesabu kutoka kwenye
autocovariance ya mfululizo wenyewe. Kikomo cha chini kabisa ni **siku 21** —
mzunguko kamili wa mwisho wa mwezi lazima utoshe ndani ya kipande kimoja,
vinginevyo bootstrap ingevunja tukio la F1 katikati na kudai uhuru usiokuwepo.

Kikomo hicho ni **cha kutangazwa**, si cha kuhesabiwa; kinaandikwa hapa mara
moja na kinaingia kwenye ledger.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

# Mzunguko wa mwisho wa mwezi lazima utoshe ndani ya kipande kimoja.
MIN_BLOCK_DAYS = 21

# Kikomo cha juu: kipande kirefu kuliko robo ya sampuli kinatoa resamples
# chache zinazojirudia — bootstrap ingekuwa ikichukua nakala za mfululizo mmoja.
MAX_BLOCK_FRACTION = 0.25

B_DEVELOPMENT = 1_000
B_CERTIFICATION = 10_000


class BootstrapError(RuntimeError):
    """Bootstrap haiwezi kuendeshwa kama ilivyoombwa."""


# ===========================================================================
# Urefu wa kipande — Politis & White (2004)
# ===========================================================================


def _flat_top(t: float) -> float:
    """Taper ya Politis–White: 1 kwa |t| ≤ ½, inashuka mstari hadi 1, kisha 0."""
    a = abs(t)
    if a <= 0.5:
        return 1.0
    if a <= 1.0:
        return 2.0 * (1.0 - a)
    return 0.0


def optimal_block_length(x) -> int:
    """Urefu wa kipande kutoka kwenye mfululizo wenyewe, si kwa kubuni.

    Politis & White (2004), *Automatic block-length selection for the dependent
    bootstrap*:

    ```
    b_opt = ( 2 Ĝ² / D̂ )^(1/3) · N^(1/3)
    ```

    ambapo `Ĝ = Σ λ(k/M)|k|R(k)` na `D̂ = 2 ĝ(0)²` kwa stationary bootstrap,
    `ĝ(0) = Σ λ(k/M) R(k)`. `M = 2m`, na `m` ni lag ndogo kabisa ambapo
    autocorrelation inakuwa isiyo na maana kwa lags `K_N` mfululizo.

    Matokeo yanabanwa kati ya `MIN_BLOCK_DAYS` na robo ya sampuli.
    """
    import numpy as np

    a = np.asarray(list(x), dtype=float)
    a = a[np.isfinite(a)]
    n = a.size
    if n < 8:
        raise BootstrapError(
            f"pointi {n} ni chache mno kwa kukadiria urefu wa kipande"
        )

    kati = a - a.mean()
    sd = kati.std()
    if sd == 0.0:
        return MIN_BLOCK_DAYS

    kikomo = min(n - 1, int(math.ceil(10.0 * math.log10(n))))
    acov = np.array([float((kati[: n - k] * kati[k:]).sum() / n)
                     for k in range(kikomo + 1)])
    acf = acov / acov[0]

    # `m`: lag ndogo kabisa ambapo `K_N` lags mfululizo ziko chini ya kizingiti.
    kizingiti = 2.0 * math.sqrt(math.log10(n) / n)
    K_N = max(5, int(math.ceil(math.sqrt(math.log10(n)))))
    m = 0
    for k in range(1, kikomo + 1):
        dirisha = acf[k: min(k + K_N, kikomo + 1)]
        if dirisha.size and np.all(np.abs(dirisha) < kizingiti):
            m = k - 1
            break
    else:
        m = kikomo

    M = min(2 * max(m, 1), kikomo)
    lags = np.arange(-M, M + 1)
    w = np.array([_flat_top(k / M) for k in lags])
    R = np.array([acov[abs(int(k))] for k in lags])

    g = float((w * R).sum())
    G = float((w * np.abs(lags) * R).sum())
    D = 2.0 * g * g
    if D <= 0 or G <= 0:
        return MIN_BLOCK_DAYS

    b = ((2.0 * G * G) / D) ** (1.0 / 3.0) * n ** (1.0 / 3.0)
    juu = max(MIN_BLOCK_DAYS, int(n * MAX_BLOCK_FRACTION))
    return int(min(max(round(b), MIN_BLOCK_DAYS), juu))


# ===========================================================================
# Stationary bootstrap
# ===========================================================================


def _resample_means(a, block: int, B: int, rng):
    """Wastani wa resamples `B`, kila moja ya urefu `n`."""
    import numpy as np

    n = a.size
    p = 1.0 / block
    out = np.empty(B, dtype=float)
    for i in range(B):
        idx = np.empty(n, dtype=np.int64)
        j = int(rng.integers(0, n))
        for t in range(n):
            idx[t] = j
            # Urefu wa kipande ni wa kijiometri: ndicho kinachofanya bootstrap
            # iwe **stationary** — mfululizo uliorudishwa una mgawanyo ule ule
            # bila kujali ulipoanzia.
            j = int(rng.integers(0, n)) if rng.random() < p else (j + 1) % n
        out[i] = a[idx].mean()
    return out


@dataclass(frozen=True)
class BootstrapResult:
    """`p-value` ya upande mmoja, pamoja na kila kitu kilichoitengeneza."""

    mean: float
    p_value: float
    block: int
    n: int
    n_active: int
    B: int
    ci_low: float
    ci_high: float

    @property
    def resolution(self) -> float:
        """`p` ndogo kabisa inayoweza kutofautishwa: `1/(B+1)`."""
        return 1.0 / (self.B + 1)

    def render(self) -> str:
        return (f"BOOTSTRAP · wastani {self.mean:+.5f}R · p {self.p_value:.4f} "
                f"(azimio {self.resolution:.4f}) · kipande {self.block} siku · "
                f"n {self.n:,} (hai {self.n_active:,}) · B {self.B:,}\n"
                f"   CI 95%: [{self.ci_low:+.5f}, {self.ci_high:+.5f}]")

    def to_json(self) -> dict[str, Any]:
        return {"mean": self.mean, "p_value": self.p_value, "block": self.block,
                "n": self.n, "n_active": self.n_active, "B": self.B,
                "ci_low": self.ci_low, "ci_high": self.ci_high,
                "resolution": self.resolution}


def test_mean_positive(
    curve,
    *,
    B: int = B_DEVELOPMENT,
    seed: int = 0,
    block: int | None = None,
) -> BootstrapResult:
    """`H0: wastani wa R kwa siku = 0` dhidi ya `H1: > 0`.

    Mfululizo **uliowekwa katikati** ndio unaosampuliwa: chini ya `H0` wastani
    ni sifuri, kwa hiyo mgawanyo wa null unajengwa kwa kuondoa wastani
    uliopimwa. `p` ni fungu la resamples zenye wastani usiopungua uliopimwa,
    kwa fomu ya `(k+1)/(B+1)` — ile ile ya §9.8, isiyoruhusu `p = 0`.

    Bootstrap inaendeshwa juu ya mfululizo **kamili**, sifuri zikiwemo: siku
    isiyo na trade ni siku yenye matokeo ya sifuri, na muundo wa muda ni sehemu
    ya kile kinachopimwa.
    """
    import numpy as np

    a = curve.values() if hasattr(curve, "values") else np.asarray(curve, float)
    a = a[np.isfinite(a)]
    if a.size < 8:
        raise BootstrapError(f"siku {a.size} ni chache mno")
    if B < 100:
        raise BootstrapError(f"B = {B} — azimio la `p` lingekuwa {1/(B+1):.3f}")

    b = int(block) if block else optimal_block_length(a)
    rng = np.random.default_rng(seed)
    uliopimwa = float(a.mean())

    kati = a - uliopimwa
    null = _resample_means(kati, b, B, rng)
    k = int((null >= uliopimwa).sum())

    # CI inatoka kwenye resamples ZISIZOWEKWA katikati — ni ya wastani wenyewe.
    tukio = _resample_means(a, b, B, np.random.default_rng(seed + 1))
    lo, hi = np.quantile(tukio, [0.025, 0.975])

    n_active = getattr(curve, "n_active", int((a != 0).sum()))
    return BootstrapResult(
        mean=uliopimwa, p_value=(k + 1) / (B + 1), block=b,
        n=int(a.size), n_active=int(n_active), B=int(B),
        ci_low=float(lo), ci_high=float(hi),
    )


__all__ = ["MIN_BLOCK_DAYS", "MAX_BLOCK_FRACTION", "B_DEVELOPMENT",
           "B_CERTIFICATION", "BootstrapError", "BootstrapResult",
           "optimal_block_length", "test_mean_positive"]
