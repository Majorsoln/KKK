"""Effective N — observations HURU ngapi tunazo kweli.

Namba hii inaamua kama swali linaweza kujibiwa kabisa. Ilikuwa **imekadiriwa**
(`~5×` kwenye pendekezo la §3.9) na mapitio ya nje yaliikataa kwa haki: *"You
cannot infer effective N from raw instrument count × historical length ×
sampling density."*

Hakuna scalar moja ya kweli inayobeba dependence zote nne kwa wakati mmoja.
Kutoa namba moja ni kutengeneza **usahihi wa uongo**. Kwa hiyo hapa kuna
makadirio manne huru, na jibu ni **ndogo kuliko zote** — envelope ya tahadhari:

| Kipimo | Dependence inayoshughulikiwa |
|---|---|
| `N_uniq`  | labels zinazopishana kwa muda (concurrency) |
| `N_time`  | autocorrelation ya target yenyewe |
| `N_cross` | symbols 12 kutoka factors ~6 — si huru |
| `N_block` | muda × cross kwa pamoja (blocks zisizopishana) |

**Kosa lililokwisha tokea, likiandikwa hapa lisirudiwe.** Blocks za muda
`8.25 miaka × 6,000 bars ÷ 24 = 2,062` ni **kwa symbol MOJA**. Kuzitumia kama
jumla ya observations huru kunashusha N kwa mara tano na kunageuza hukumu ya
mradi kutoka "inawezekana" kwenda "acha". Mara moja imeshatokea kwenye mapitio
ya nje; `N_block` hapa inazidisha kwa breadth halisi ili isirudie.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd

EFFECTIVE_N_VERSION = 1


@dataclass
class EffectiveN:
    n_raw: int = 0
    n_uniq: float = 0.0
    n_time: float = 0.0
    n_cross: float = 0.0
    n_block: float = 0.0
    tau: float = 1.0
    participation_ratio: float = 1.0
    symbols: int = 0
    horizon_bars: int = 0
    notes: list[str] = field(default_factory=list)

    @property
    def n_eff(self) -> float:
        """Ndogo kuliko zote — envelope, si wastani.

        Wastani ungeficha dependence kali kuliko zote nyuma ya zile hafifu.
        Ukaguzi wa tahadhari unachukua mbaya kuliko zote.
        """
        candidates = [x for x in (self.n_uniq, self.n_time, self.n_cross, self.n_block) if x > 0]
        return float(min(candidates)) if candidates else 0.0

    def to_json(self) -> dict[str, Any]:
        return {
            "version": EFFECTIVE_N_VERSION,
            "n_raw": self.n_raw,
            "n_uniq": self.n_uniq,
            "n_time": self.n_time,
            "n_cross": self.n_cross,
            "n_block": self.n_block,
            "n_eff": self.n_eff,
            "tau": self.tau,
            "participation_ratio": self.participation_ratio,
            "symbols": self.symbols,
            "horizon_bars": self.horizon_bars,
            "notes": self.notes,
        }


# --------------------------------------------------------------------------
# 1. Average uniqueness — labels zinazopishana (López de Prado §4.4)
# --------------------------------------------------------------------------


def average_uniqueness(
    points: pd.DataFrame, horizon_bars: int, bar_minutes: int = 60
) -> tuple[float, pd.Series]:
    """`Σ uᵢ` ambapo `uᵢ = (1/H)·Σ_t 1/C_t` juu ya span ya label.

    `C_t` ni idadi ya labels **hai** wakati `t` **ndani ya symbol ile ile**.

    **Kwa nini si pooled kwa symbols zote.** Toleo la kwanza lilihesabu
    concurrency kwenye timeline moja ya symbols zote. Matokeo: kila label
    ilionekana ikiwa ya kipekee kwa 8.6% — na 8.6% ≈ 1/12, yaani idadi ya
    symbols zetu, si mali yoyote ya data. Symbols 12 zikiwa na labels hai kwa
    wakati mmoja zinatoa `C_t = 12`, na uniqueness inashuka hadi `1/12` hata
    kama symbols hizo hazina uhusiano wowote.

    Hilo linachanganya vitu viwili tofauti:

    * **kupishana kwa MUDA** ndani ya symbol — labels zinazoshiriki bars za
      baadaye. Hii ndiyo redundancy ambayo `uniqueness` inapaswa kuipima.
    * **kutokea kwa WAKATI MMOJA** kwenye symbols tofauti — redundancy ya
      sehemu, inayopimwa kwa usahihi na `participation_ratio` (7.54 kati ya 12
      kwenye data yetu), si kwa `1/12`.

    Kuvichanganya kunahesabu dependence ya cross-sectional **mara mbili**, na
    kunashusha `N_eff` kwa mara nne — kutosha kufunga mradi unaowezekana.
    Kila estimator inapaswa kupima dependence YAKE; `n_eff` inachukua mbaya
    kuliko zote (2026-08-13).

    Inarudisha jumla na uzito wa kila point (uzito huo ndio `max_samples` ya
    bagging — si idadi ghafi).
    """
    if points.empty:
        return 0.0, pd.Series(dtype=float)
    if "symbol" in points.columns and points["symbol"].nunique() > 1:
        totals = 0.0
        pieces = []
        for _, chunk in points.groupby("symbol", sort=False):
            subtotal, weights = average_uniqueness(chunk, horizon_bars, bar_minutes)
            totals += subtotal
            pieces.append(weights)
        return totals, pd.concat(pieces).reindex(points.index)

    start = pd.to_datetime(points["decision_time"], utc=True)
    step = pd.Timedelta(minutes=bar_minutes)
    # Grid ya bars: kila label inashika slots `horizon_bars` kuanzia yake.
    origin = start.min()
    idx = ((start - origin) // step).astype("int64").to_numpy()
    span = int(horizon_bars)
    total_slots = int(idx.max()) + span + 1

    # Concurrency kwa difference array — O(N + T), si O(N·H).
    delta = np.zeros(total_slots + 1, dtype=np.int64)
    np.add.at(delta, idx, 1)
    np.add.at(delta, idx + span, -1)
    concurrency = np.cumsum(delta)[:total_slots]

    inv = np.zeros(total_slots, dtype=float)
    live = concurrency > 0
    inv[live] = 1.0 / concurrency[live]
    prefix = np.concatenate([[0.0], np.cumsum(inv)])

    weights = (prefix[idx + span] - prefix[idx]) / span
    return float(weights.sum()), pd.Series(weights, index=points.index, name="uniqueness")


# --------------------------------------------------------------------------
# 2. Integrated autocorrelation time
# --------------------------------------------------------------------------


def integrated_autocorr_time(series: pd.Series, max_lag: int | None = None) -> float:
    """`τ = 1 + 2·Σρ_k`, ikikatwa kwenye ρ hasi ya kwanza.

    Kukata kwenye ρ hasi ya kwanza (Geyer) ni sheria iliyotangazwa: bila
    truncation rule, jumla inaendelea kwenye kelele na `τ` inakua bila kikomo.
    """
    values = pd.to_numeric(series, errors="coerce").dropna().to_numpy(dtype=float)
    n = len(values)
    if n < 32:
        return 1.0
    values = values - values.mean()
    denom = float((values * values).sum())
    if denom <= 0:
        return 1.0
    cap = int(max_lag or min(n // 4, 200))
    total = 0.0
    for lag in range(1, cap + 1):
        rho = float((values[lag:] * values[:-lag]).sum()) / denom
        if rho <= 0:
            break
        total += rho
    return float(1.0 + 2.0 * total)


# --------------------------------------------------------------------------
# 3. Participation ratio — breadth halisi kati ya symbols
# --------------------------------------------------------------------------


def participation_ratio(panel: pd.DataFrame) -> float:
    """`(Σλ)² ÷ Σλ²` ya correlation matrix — "factors huru" ngapi.

    Symbols 12 zilizojengwa kwa sarafu 6 hazitoi factors 12. Kipimo hiki
    kinajibu kwa data badala ya kudhaniwa: correlation matrix ya identity
    inatoa idadi kamili ya columns; matrix ya rank 1 inatoa 1.
    """
    frame = panel.dropna(axis=1, how="all")
    if frame.shape[1] <= 1:
        return float(frame.shape[1])
    corr = frame.corr(min_periods=32).to_numpy()
    corr = np.nan_to_num(corr, nan=0.0)
    np.fill_diagonal(corr, 1.0)
    eig = np.linalg.eigvalsh(corr)
    eig = np.clip(eig, 0.0, None)
    if eig.sum() <= 0:
        return 1.0
    return float(eig.sum() ** 2 / (eig**2).sum())


# --------------------------------------------------------------------------
# Mkusanyiko
# --------------------------------------------------------------------------


def estimate(
    points: pd.DataFrame,
    horizon_bars: int,
    target: str = "terminal_atr",
    bar_minutes: int = 60,
) -> EffectiveN:
    """Makadirio manne + envelope."""
    out = EffectiveN(horizon_bars=int(horizon_bars))
    if points.empty:
        out.notes.append("hakuna points")
        return out

    frame = points.copy()
    frame["decision_time"] = pd.to_datetime(frame["decision_time"], utc=True)
    frame = frame.sort_values("decision_time", kind="stable")
    out.n_raw = int(len(frame))
    out.symbols = int(frame["symbol"].nunique()) if "symbol" in frame else 1

    # 1 — uniqueness
    out.n_uniq, _ = average_uniqueness(frame, horizon_bars, bar_minutes)

    # 2 — autocorrelation, ikipimwa NDANI ya kila symbol kisha kuwekwa pamoja:
    #     mfululizo wa pooled ungechanganya symbols na kuzalisha τ ya bandia.
    if target in frame.columns:
        taus = [
            integrated_autocorr_time(chunk[target])
            for _, chunk in frame.groupby("symbol", sort=False)
            if len(chunk) >= 32
        ]
        out.tau = float(np.mean(taus)) if taus else 1.0
    else:
        out.notes.append(f"target `{target}` haipo — τ imewekwa 1.0")
    out.n_time = out.n_raw / out.tau if out.tau > 0 else float(out.n_raw)

    # 3 — cross-sectional: panel ya target kwa symbol, ikilinganishwa kwa muda
    if target in frame.columns and out.symbols > 1:
        panel = (
            frame.pivot_table(
                index=frame["decision_time"].dt.floor("1D"),
                columns="symbol",
                values=target,
                aggfunc="mean",
            )
            .sort_index()
        )
        out.participation_ratio = participation_ratio(panel)
    else:
        out.participation_ratio = float(out.symbols)
    out.n_cross = out.n_raw * (out.participation_ratio / max(out.symbols, 1))

    # 4 — blocks zisizopishana × breadth. Hii ndiyo iliyokosewa kwenye mapitio:
    #     blocks ni ZA KILA SYMBOL, kwa hiyo lazima zizidishwe kwa breadth.
    span = frame["decision_time"].max() - frame["decision_time"].min()
    bars = span / pd.Timedelta(minutes=bar_minutes)
    blocks_per_symbol = max(float(bars) / max(horizon_bars, 1), 1.0)
    out.n_block = min(blocks_per_symbol, out.n_raw / max(out.symbols, 1)) * out.participation_ratio

    if out.n_eff and out.n_eff < 0.05 * out.n_raw:
        out.notes.append(
            f"n_eff ({out.n_eff:,.0f}) ni chini ya 5% ya n_raw ({out.n_raw:,}) — "
            "dependence ni kali; takwimu yoyote inayotumia n_raw ni ya uongo"
        )
    return out
