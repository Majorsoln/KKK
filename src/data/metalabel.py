"""Meta-labelling — SETUP-v1 inaweka upande, model inaamua chukua au acha.

Wataalamu wote wawili walichagua umbo hili bila kuonana. Sababu ni ile ile:
kujaribu kufundisha *mwelekeo* na *ubora* kwa algorithm moja kunazalisha
generalization mbaya; kuvitenganisha kunaboresha precision bila kupoteza
recall, na kunapunguza complexity inayoweza kuoverfit.

**Hakuna label mpya. Hakuna rebuild.** Points 25,374 zilizosainiwa tayari.

Vigezo vitatu vya kufaulu, vyote vya lazima — vikiwa vimeandikwa kabla ya run:

1. **Calibration** — reliability slope ∈ [0.8, 1.2]. Bila hii EV gate ni
   mapambo: probability isiyoaminika ikizidishwa na payoff inatoa namba
   inayoonekana kama EV lakini si.
2. **Discrimination** — Spearman ρ ≥ 0.7 kwenye deciles 10. Hii ndiyo test
   yenye nguvu: inakopa taarifa kutoka **mgawanyo mzima** badala ya kudai
   nukta ya tail, ambayo kwa N yetu ni observations ~100 na SE ya 0.049.
3. **Kiuchumi** — fitted top-decile ≥ breakeven + δ_MER, na mpaka wa chini wa
   block bootstrap juu ya breakeven.

**Logistic, si isotonic** (§8 ya T3_PLAN). Top bin ya isotonic **ni** wastani
wa empirical wa bin hiyo — inarudisha SE ile ile na hainunui nguvu yoyote.
Faida yote inatokana na pooling ya parameters mbili kwenye N nzima. Kwa hiyo
chaguo la calibration family ndilo linaloamua kama kigezo cha 3 kinapitika —
na linatangazwa, halijifichi.

**Goodness-of-fit gate**: fitted ikaribiane na empirical ndani ya 1 SE kwenye
deciles mbili za juu. Ikizidi, njia ya parametric inakataliwa **na kigezo cha 3
kinaanguka**. Bila kifungu hiki, (3) ingekuwa njia ya kununua CI nyembamba kwa
kudai kitu ambacho hukukipima.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Sequence

import numpy as np
import pandas as pd

METALABEL_VERSION = 1


@dataclass
class Gate:
    name: str
    value: float
    threshold: float
    passed: bool
    detail: str = ""

    def to_json(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "value": self.value,
            "threshold": self.threshold,
            "passed": self.passed,
            "detail": self.detail,
        }


@dataclass
class MetaResult:
    n: int = 0
    n_eff: float = 0.0
    n_required: float = 0.0
    breakeven: float = 0.0
    delta_mer: float = 0.0
    gates: list[Gate] = field(default_factory=list)
    deciles: list[dict[str, Any]] = field(default_factory=list)
    inconclusive: bool = False
    notes: list[str] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return bool(self.gates) and all(g.passed for g in self.gates) and not self.inconclusive

    def to_json(self) -> dict[str, Any]:
        return {
            "version": METALABEL_VERSION,
            "n": self.n,
            "n_eff": self.n_eff,
            "n_required": self.n_required,
            "breakeven": self.breakeven,
            "delta_mer": self.delta_mer,
            "verdict": "INCONCLUSIVE" if self.inconclusive else ("PASS" if self.passed else "FAIL"),
            "gates": [g.to_json() for g in self.gates],
            "deciles": self.deciles,
            "notes": self.notes,
        }


# --------------------------------------------------------------------------
# Calibration — logistic kwa parameters MBILI
# --------------------------------------------------------------------------


def logistic_calibrate(score: np.ndarray, outcome: np.ndarray, weight: np.ndarray | None = None):
    """Platt scaling: `p = σ(a·s + b)`, ikifit kwa Newton–Raphson.

    Parameters mbili pekee — ndiyo sababu inanunua nguvu. Kila observation
    kati ya N inachangia kwenye a na b, kwa hiyo thamani ya top decile ni
    **extrapolation kutoka mkunjo mzima**, si wastani wa observations 100.
    """
    x = np.asarray(score, dtype=float)
    y = np.asarray(outcome, dtype=float)
    w = np.ones_like(y) if weight is None else np.asarray(weight, dtype=float)
    a, b = 0.0, float(np.log((y @ w + 1e-9) / ((1 - y) @ w + 1e-9)))

    for _ in range(100):
        z = a * x + b
        p = 1.0 / (1.0 + np.exp(-np.clip(z, -30, 30)))
        v = w * p * (1 - p)
        grad = np.array([(w * (y - p)) @ x, (w * (y - p)).sum()])
        hess = np.array(
            [[(v * x * x).sum(), (v * x).sum()], [(v * x).sum(), v.sum()]]
        )
        hess += np.eye(2) * 1e-9
        step = np.linalg.solve(hess, grad)
        a, b = a + step[0], b + step[1]
        if np.max(np.abs(step)) < 1e-10:
            break
    return float(a), float(b)


def apply_calibration(score: np.ndarray, a: float, b: float) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-np.clip(a * np.asarray(score, dtype=float) + b, -30, 30)))


def reliability_slope(prob: np.ndarray, outcome: np.ndarray, bins: int = 10) -> float:
    """Mteremko wa mkunjo wa uaminifu: 1.0 = "zilizopewa 70% zilishinda 70%".

    Chini ya 1 = model ina ujasiri kupita kiasi; juu ya 1 = ina woga kupita
    kiasi. Zote mbili zinavunja EV gate kwa njia tofauti.
    """
    p, y = np.asarray(prob, dtype=float), np.asarray(outcome, dtype=float)
    order = np.argsort(p)
    groups = np.array_split(order, bins)
    xs = np.array([p[g].mean() for g in groups if len(g)])
    ys = np.array([y[g].mean() for g in groups if len(g)])
    if len(xs) < 3 or np.ptp(xs) == 0:
        return float("nan")
    return float(np.polyfit(xs, ys, 1)[0])


# --------------------------------------------------------------------------
# Discrimination — mtiririko kwenye deciles
# --------------------------------------------------------------------------


def decile_table(
    score: np.ndarray,
    outcome: np.ndarray,
    bins: int = 10,
    calibration: tuple[float, float] | None = None,
) -> pd.DataFrame:
    """Deciles kwa score, pamoja na `fitted` ikiombwa.

    **`fitted` ni wastani wa probabilities, si probability ya wastani.**
    `σ` si linear, kwa hiyo `E[σ(a·s+b)] ≠ σ(a·E[s]+b)` (Jensen). Kwenye decile
    ya juu, ambapo mgawanyo wa score umeegemea upande mmoja, tofauti hiyo ni
    kubwa vya kutosha kufelisha goodness-of-fit kwa model iliyofit vizuri
    kabisa — kasoro iliyokamatwa 2026-08-14.
    """
    x = np.asarray(score, dtype=float)
    y = np.asarray(outcome, dtype=float)
    order = np.argsort(x)
    groups = np.array_split(order, bins)
    rows = []
    for i, g in enumerate(groups):
        if not len(g):
            continue
        row = {
            "decile": i + 1,
            "n": int(len(g)),
            "score_mean": float(x[g].mean()),
            "empirical": float(y[g].mean()),
        }
        if calibration is not None:
            row["fitted"] = float(apply_calibration(x[g], *calibration).mean())
        rows.append(row)
    return pd.DataFrame(rows)


def spearman(x: Sequence[float], y: Sequence[float]) -> float:
    a = pd.Series(x).rank().to_numpy()
    b = pd.Series(y).rank().to_numpy()
    if len(a) < 3 or np.std(a) == 0 or np.std(b) == 0:
        return float("nan")
    return float(np.corrcoef(a, b)[0, 1])


# --------------------------------------------------------------------------
# Kigezo cha 3 — kiuchumi, kwa fitted value na block bootstrap
# --------------------------------------------------------------------------


def top_decile_fitted(
    score: np.ndarray, outcome: np.ndarray, blocks: np.ndarray, n_boot: int, seed: int
) -> tuple[float, float, float]:
    """Fitted `p̂` ya decile ya juu + mpaka wa chini wa 5% (block bootstrap).

    Blocks ni **miaka**, si rows. Resampling ya rows ingedhania uhuru ambao
    labels zinazopishana na symbols zinazohusiana hazina.
    """
    x, y = np.asarray(score, dtype=float), np.asarray(outcome, dtype=float)
    cutoff = float(np.quantile(x, 0.9))
    a, b = logistic_calibrate(x, y)
    # Wastani wa fitted juu ya wanachama, si fitted ya score ya wastani (Jensen).
    point = float(apply_calibration(x[x >= cutoff], a, b).mean())

    if n_boot <= 0:
        return point, float("nan"), cutoff

    rng = np.random.RandomState(seed)
    levels = np.unique(blocks)
    samples: list[float] = []
    for _ in range(n_boot):
        picked = rng.choice(levels, size=len(levels), replace=True)
        idx = np.concatenate([np.flatnonzero(blocks == level) for level in picked])
        if len(idx) < 100 or len(np.unique(y[idx])) < 2:
            continue
        aa, bb = logistic_calibrate(x[idx], y[idx])
        top = x[idx] >= cutoff
        if not top.any():
            continue
        samples.append(float(apply_calibration(x[idx][top], aa, bb).mean()))
    low = float(np.percentile(samples, 5)) if len(samples) >= 20 else float("nan")
    return point, low, cutoff


def goodness_of_fit(deciles: pd.DataFrame, top_k: int = 2) -> tuple[bool, str]:
    """Fitted ikaribiane na empirical kwenye deciles za juu, ndani ya 1 SE.

    Hatari halisi: uhusiano wa score→outcome ukilalia kwenye tail — jambo
    linalotokea wakati scores za juu zinaendeshwa na outliers badala ya signal
    — logistic itakadiria decile ya juu **juu kuliko ukweli**. Hiyo ndiyo
    failure mode kamili ya njia hii, kwa hiyo inapimwa moja kwa moja.
    """
    if "fitted" not in deciles.columns:
        return False, "jedwali halina `fitted` — calibration haikupitishwa"
    for _, row in deciles.tail(top_k).iterrows():
        se = float(np.sqrt(max(row["empirical"] * (1 - row["empirical"]), 1e-9) / row["n"]))
        if abs(row["fitted"] - row["empirical"]) > se:
            return False, (
                f"decile {int(row['decile'])}: fitted {row['fitted']:.4f} dhidi ya empirical "
                f"{row['empirical']:.4f}, tofauti > 1 SE ({se:.4f})"
            )
    return True, ""


# --------------------------------------------------------------------------
# Jaribio kamili
# --------------------------------------------------------------------------


def evaluate(
    score: np.ndarray,
    outcome: np.ndarray,
    blocks: np.ndarray,
    breakeven: float,
    delta_mer: float,
    n_eff: float,
    n_required: float,
    slope_range: tuple[float, float] = (0.8, 1.2),
    rho_min: float = 0.7,
    n_boot: int = 500,
    seed: int = 20260814,
) -> MetaResult:
    """Vigezo vitatu, vyote vya lazima, vikiwa vimeandikwa kabla ya run."""
    result = MetaResult(
        n=int(len(score)),
        n_eff=float(n_eff),
        n_required=float(n_required),
        breakeven=float(breakeven),
        delta_mer=float(delta_mer),
    )

    # Kifungu cha nguvu: N_eff isipotosha, matokeo hayana maana yoyote —
    # yakiwa mazuri au mabaya. Kupita kwa bahati kwenye sampuli isiyotosha
    # ndiyo njia inayowezekana zaidi ya jaribio hili kuzalisha uongo.
    if n_eff < n_required:
        result.inconclusive = True
        result.notes.append(
            f"N_eff {n_eff:,.0f} < N_req {n_required:,.0f} — jaribio ni INCONCLUSIVE "
            "bila kujali matokeo"
        )
        return result

    a, b = logistic_calibrate(np.asarray(score, dtype=float), np.asarray(outcome, dtype=float))
    prob = apply_calibration(score, a, b)

    slope = reliability_slope(prob, outcome)
    result.gates.append(
        Gate(
            "calibration",
            slope,
            slope_range[0],
            bool(np.isfinite(slope) and slope_range[0] <= slope <= slope_range[1]),
            f"mteremko unatakiwa uwe ndani ya [{slope_range[0]}, {slope_range[1]}]",
        )
    )

    table = decile_table(score, outcome, calibration=(a, b))
    result.deciles = table.to_dict(orient="records")
    rho = spearman(table["decile"], table["empirical"])
    result.gates.append(
        Gate("discrimination", rho, rho_min, bool(np.isfinite(rho) and rho >= rho_min),
             "Spearman kwenye deciles 10")
    )

    point, low, cutoff = top_decile_fitted(score, outcome, blocks, n_boot, seed)
    fit_ok, fit_detail = goodness_of_fit(table)
    target = breakeven + delta_mer
    economic = bool(
        fit_ok and np.isfinite(point) and point >= target
        and np.isfinite(low) and low > breakeven
    )
    detail = f"lengo {target:.4f} · mpaka wa chini {low:.4f} dhidi ya breakeven {breakeven:.4f}"
    if not fit_ok:
        detail = f"goodness-of-fit IMEKATALIWA — {fit_detail}"
    result.gates.append(Gate("kiuchumi", point, target, economic, detail))
    result.notes.append(f"cutoff ya decile ya juu: score ≥ {cutoff:.4f}")
    return result
