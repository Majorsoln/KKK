"""Je makali ya SETUP-v1 ni utabiri, au ni uteuzi wa volatility?

Swali lililobaki tangu T2. Setups zina ATR p50 ya **16.1 pips**; controls
**14.3**. Kichujio kinachagua bars zenye msukumo mkubwa kwenye masoko yenye
shughuli — **kwa muundo**, si kwa bahati (`min_atr_mult 2.5`, band ya ATR
0.20–0.95). Kwa hiyo `+0.0638R` inaweza kuwa:

* **utabiri** — kichujio kinatambua fursa, au
* **uteuzi** — kichujio kinachagua mazingira yenye p_tp ya juu kwa sababu
  nyingine kabisa, na sisi tunaita hiyo "edge"

Njia ya kutofautisha: **linganisha ndani ya strata**. Setup na control zenye
ATR ile ile, spread ile ile, session ile ile, symbol ile ile, mwaka ule ule —
je bado zinatofautiana?

**Kwa nini stratified bins na si propensity scores.** Treatment hapa ni
*deterministic*: SETUP-v1 ni sheria ya mkono, si kitu kinachotokea kwa
uwezekano fulani. Model ya propensity ingeongeza model ya pili na nafasi ya
pili ya kukosea, ikijaribu kukadiria kitu tunachokijua kwa uhakika.

**Common support ndiyo matokeo ya kwanza, si kikwazo.** Gate ya momentum
inafanya setups ziwe na `|impulse| ≥ 2.5·ATR` **daima**. Controls zenye
msukumo huo ni zile zilizofeli gate NYINGINE (spread au band). Kama ni chache
mno, jibu si "matching imeshindwa" — jibu ni kwamba **athari ya SETUP-v1
haiwezi kutenganishwa na masharti yanayoifafanua**, na hilo ni jibu halali
linalopaswa kuripotiwa kwa uwazi.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Sequence

import numpy as np
import pandas as pd

MATCHING_VERSION = 1

# Vipimo vya strata, vikiwa vimetangazwa. Ubadilishaji wa orodha hii ni
# config mpya na unagharimu bajeti — si urembo.
DEFAULT_STRATA: tuple[str, ...] = (
    "atr_bin",
    "spread_bin",
    "session",
    "symbol",
    "year",
)


@dataclass
class MatchResult:
    cell: tuple[float, float]
    n_setup: int = 0
    n_control: int = 0
    strata_total: int = 0
    strata_both: int = 0
    support_frac: float = 0.0
    raw_diff: float = float("nan")
    matched_diff: float = float("nan")
    ci_low: float = float("nan")
    ci_high: float = float("nan")
    per_stratum: list[dict[str, Any]] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def to_json(self) -> dict[str, Any]:
        return {
            "version": MATCHING_VERSION,
            "cell": list(self.cell),
            "n_setup": self.n_setup,
            "n_control": self.n_control,
            "strata_total": self.strata_total,
            "strata_both": self.strata_both,
            "support_frac": self.support_frac,
            "raw_diff": self.raw_diff,
            "matched_diff": self.matched_diff,
            "ci_low": self.ci_low,
            "ci_high": self.ci_high,
            "shrinkage": (
                None
                if not np.isfinite(self.raw_diff) or self.raw_diff == 0
                else 1.0 - self.matched_diff / self.raw_diff
            ),
            "per_stratum": self.per_stratum[:50],
            "notes": self.notes,
        }


def quantile_bin(values: pd.Series, bins: int, labels_prefix: str) -> pd.Series:
    """Bins za quantile zilizohesabiwa kwa data YOTE (setup + control).

    Kuhesabu bins kwa kila kundi peke yake kungetengeneza bins zisizolingana,
    na ulinganisho ungekuwa wa vitu tofauti vyenye jina moja.
    """
    ranked = values.rank(pct=True, method="average")
    edges = np.linspace(0, 1, bins + 1)
    idx = np.clip(np.searchsorted(edges, ranked.to_numpy(), side="left") - 1, 0, bins - 1)
    out = pd.Series([f"{labels_prefix}{i}" for i in idx], index=values.index)
    out[values.isna()] = "NA"
    return out


def build_strata(
    frame: pd.DataFrame, atr_bins: int = 5, spread_bins: int = 4
) -> pd.DataFrame:
    """Ongeza safu za strata zilizotangazwa."""
    out = frame.copy()
    stamps = pd.to_datetime(out["decision_time"], utc=True)
    out["year"] = stamps.dt.year.astype(str)
    hour = stamps.dt.hour
    # Sessions za FX kwa saa za UTC — mipaka iliyotangazwa, si iliyotunwa.
    out["session"] = np.select(
        [hour < 7, hour < 12, hour < 17],
        ["asia", "london", "overlap"],
        default="ny",
    )
    out["atr_bin"] = quantile_bin(out["atr_pips"], atr_bins, "atr")
    source = "spread_entry_pips" if "spread_entry_pips" in out else "spread_p50"
    out["spread_bin"] = quantile_bin(out[source], spread_bins, "spd")
    return out


def matched_effect(
    frame: pd.DataFrame,
    outcome: str = "r_net",
    strata: Sequence[str] = DEFAULT_STRATA,
    cell: tuple[float, float] = (2.0, 3.0),
    n_boot: int = 500,
    seed: int = 20260813,
) -> MatchResult:
    """Tofauti ya setup–control ndani ya strata, ikiwa na uzito wa ATT.

    Uzito ni `n_setup` kwa kila stratum (Average Treatment effect on the
    Treated): tunapima athari kwenye setups tutakazozitrade, si kwenye
    ulimwengu wa dhahania wa bars zote.

    CI inatoka **block bootstrap kwa mwaka** — resampling ya rows moja moja
    ingedhania uhuru ambao haupo (labels zinapishana, symbols zinahusiana).

    **Bootstrap inafanyika kwenye jedwali lililokusanywa, si kwenye rows.**
    Toleo la kwanza lilijenga frame upya kwa kila sampuli na kuiita function hii
    tena — ikimaanisha `agg("|".join, axis=1)` (row-wise Python) mara 500 juu ya
    rows 52,000. Ni **milioni 26 za string joins**, na PD aliiacha ikikimbia
    **zaidi ya saa tano** bila output hata mstari mmoja. Sasa strata
    zinakusanywa MARA MOJA kwenda `(mwaka, stratum)`, na kila sampuli ni
    `bincount` chache — sekunde, si masaa.
    """
    result = MatchResult(cell=cell)
    if frame.empty:
        result.notes.append("hakuna data")
        return result

    setups = frame[frame["is_setup"].fillna(False)]
    controls = frame[frame["is_control"].fillna(False)]
    result.n_setup, result.n_control = len(setups), len(controls)
    if setups.empty or controls.empty:
        result.notes.append("kundi moja ni tupu — hakuna cha kulinganisha")
        return result

    result.raw_diff = float(setups[outcome].mean() - controls[outcome].mean())

    # Ufungaji wa strata kwa VECTOR, si `agg(axis=1)`. Tofauti ni mara ~200.
    key = frame[strata[0]].astype(str)
    for column in strata[1:]:
        key = key.str.cat(frame[column].astype(str), sep="|")
    work = frame.assign(_stratum=key)
    grouped = work.groupby("_stratum", sort=False)

    rows: list[dict[str, Any]] = []
    for stratum, chunk in grouped:
        s = chunk[chunk["is_setup"].fillna(False)]
        c = chunk[chunk["is_control"].fillna(False)]
        if s.empty:
            continue
        rows.append(
            {
                "stratum": stratum,
                "n_setup": len(s),
                "n_control": len(c),
                "mean_setup": float(s[outcome].mean()),
                "mean_control": float(c[outcome].mean()) if len(c) else float("nan"),
                "diff": float(s[outcome].mean() - c[outcome].mean()) if len(c) else float("nan"),
            }
        )
    result.strata_total = len(rows)
    usable = [r for r in rows if r["n_control"] > 0]
    result.strata_both = len(usable)

    matched_setups = sum(r["n_setup"] for r in usable)
    result.support_frac = matched_setups / result.n_setup if result.n_setup else 0.0
    result.per_stratum = sorted(rows, key=lambda r: -r["n_setup"])

    if not usable:
        result.notes.append(
            "hakuna stratum yenye setup NA control — athari ya SETUP-v1 haiwezi "
            "kutenganishwa na masharti yanayoifafanua"
        )
        return result

    weights = np.array([r["n_setup"] for r in usable], dtype=float)
    diffs = np.array([r["diff"] for r in usable], dtype=float)
    result.matched_diff = float(np.average(diffs, weights=weights))

    if result.support_frac < 0.5:
        result.notes.append(
            f"common support ni {result.support_frac:.0%} pekee — setups nyingi hazina "
            "control inayolingana; makadirio ni ya sehemu ndogo ya kundi"
        )

    if n_boot > 0:
        low, high, note = _block_bootstrap(work, outcome, n_boot, seed)
        result.ci_low, result.ci_high = low, high
        if note:
            result.notes.append(note)
    return result


def _block_bootstrap(
    work: pd.DataFrame, outcome: str, n_boot: int, seed: int
) -> tuple[float, float, str]:
    """CI kwa kuchagua MIAKA upya — ikifanyika kwenye jedwali lililokusanywa.

    Kila sampuli ni `bincount` nne juu ya rows chache elfu za `(mwaka, stratum)`,
    si ujenzi upya wa frame ya rows 52,000. Hakuna Python loop juu ya rows.
    """
    if "year" not in work.columns or work["year"].nunique() < 3:
        return float("nan"), float("nan"), "miaka chini ya 3 — bootstrap haijafanyika"

    is_setup = work["is_setup"].fillna(False).to_numpy()
    values = work[outcome].to_numpy(dtype=float)
    year_code, years = pd.factorize(work["year"], sort=True)
    stratum_code, strata_levels = pd.factorize(work["_stratum"], sort=False)

    n_years, n_strata = len(years), len(strata_levels)
    flat = year_code * n_strata + stratum_code
    size = n_years * n_strata

    # Jedwali lililokusanywa: idadi na jumla kwa kila (mwaka, stratum, kundi).
    n_s = np.bincount(flat[is_setup], minlength=size)
    s_s = np.bincount(flat[is_setup], weights=values[is_setup], minlength=size)
    n_c = np.bincount(flat[~is_setup], minlength=size)
    s_c = np.bincount(flat[~is_setup], weights=values[~is_setup], minlength=size)

    keep = (n_s + n_c) > 0
    cells_year = (np.arange(size) // n_strata)[keep]
    cells_stratum = (np.arange(size) % n_strata)[keep]
    n_s, s_s, n_c, s_c = n_s[keep], s_s[keep], n_c[keep], s_c[keep]

    rng = np.random.RandomState(seed)
    samples = np.empty(n_boot, dtype=float)
    taken = 0
    for _ in range(n_boot):
        multiplicity = np.bincount(
            rng.randint(0, n_years, n_years), minlength=n_years
        ).astype(float)
        weight = multiplicity[cells_year]
        ns = np.bincount(cells_stratum, weights=weight * n_s, minlength=n_strata)
        ss = np.bincount(cells_stratum, weights=weight * s_s, minlength=n_strata)
        nc = np.bincount(cells_stratum, weights=weight * n_c, minlength=n_strata)
        sc = np.bincount(cells_stratum, weights=weight * s_c, minlength=n_strata)
        usable = (ns > 0) & (nc > 0)
        if not usable.any():
            continue
        diff = ss[usable] / ns[usable] - sc[usable] / nc[usable]
        samples[taken] = float(np.average(diff, weights=ns[usable]))
        taken += 1

    if taken < 20:
        return float("nan"), float("nan"), "sampuli chache mno za bootstrap"
    return (
        float(np.percentile(samples[:taken], 5)),
        float(np.percentile(samples[:taken], 95)),
        "",
    )
