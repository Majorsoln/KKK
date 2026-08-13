"""Gharama HALISI kwa R — pamoja na kile stop iliyoruka ilichogharimu.

Hesabu yote ya T3 inasimama juu ya namba moja: `cost_R`. Kutoka hapo hutoka
`n_max` (biashara ngapi kwa mwaka), kisha `δ_MER` (edge inayohitajika), kisha
`N_req` (data inayohitajika). Namba hiyo ikiwa mbaya, kila kitu kilicho juu
yake ni mbaya.

**Kile kilichokuwa kikikosekana.** R1 ilitoza **−1.0 R sawasawa** kila SL
inapogongwa. Lakini bei haisimami kwenye barrier — inairuka. Tulirekodi
`touch_past_pips` kwa kila touch (§5.6 ya standard), na hatujawahi kuitumia:

    p50 = 0.12 · p90 = 1.06 · p99 = 14.59 · max = 2,503.7 pips

Mkia mzito. Hasara halisi ya stop ni:

    R_stop = −(1 + overshoot_pips ÷ sl_pips)

Kwa hiyo `cost_R` kamili si commission pekee; ni commission **jumlisha wastani
wa overshoot kwenye trades zinazogongwa SL**. Kama nyongeza hiyo ni kubwa kama
commission yenyewe, `n_max` inashuka kwa **mara nne**, na hilo ni tofauti kati
ya mfumo na jaribio la kitaaluma.

**Commission haitoki hapa.** Mamlaka ya `cost_pips` ni RCE (§6.2 F6). Namba ya
$7/lot round-turn inageuzwa kuwa pips na RCE wakati wa T7; hapa inaingizwa kama
parameter iliyotangazwa, na ripoti inaandika thamani iliyotumika. Spread
haiingii — ishaingia kwenye path (§5.2), na kuihesabu tena ni kuihesabu mara
mbili.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd

from .labels import SL_FIRST, TIMEOUT, TP_FIRST

# Vipimo vya identity za T3. Vikibadilika, kila namba iliyotokana navyo
# inabatilika — kwa hiyo vinaandikwa hapa mara moja, si kwenye kila wito.
COST_AUDIT_VERSION = 1


@dataclass
class CellCost:
    """Uchambuzi wa gharama kwa cell moja ya grid."""

    sl_atr: float
    tp_atr: float
    n: int
    sl_pips_median: float
    commission_r: float
    # Overshoot inaathiri SL PEKEE. Kwa TP (limit) bei kuruka zaidi haikupi
    # bei bora — limit inajaza kwa bei yake. Kwa hiyo TP haichangii gharama.
    p_stopped: float
    overshoot_r_mean_given_stop: float
    overshoot_r_p99_given_stop: float
    overshoot_r_max_given_stop: float
    # Gharama halisi kwa trade: commission + sehemu ya overshoot inayotarajiwa.
    cost_r_total: float
    ev_r_naive: float          # SL = −1.0 sawasawa (jinsi R1 ilivyohesabu)
    ev_r_realized: float       # SL = −(1 + overshoot/sl_pips)
    ev_r_net: float            # ...ikitolewa commission

    def to_json(self) -> dict[str, Any]:
        return {k: getattr(self, k) for k in self.__dataclass_fields__}


@dataclass
class CostAudit:
    cells: list[CellCost] = field(default_factory=list)
    commission_pips: float = 0.0
    notes: list[str] = field(default_factory=list)

    def frame(self) -> pd.DataFrame:
        return pd.DataFrame([c.to_json() for c in self.cells])


def realized_r(barriers: pd.DataFrame, commission_pips: float = 0.0) -> np.ndarray:
    """R halisi kwa kila cell, ikiwemo kile stop iliyoruka.

    * `TP_FIRST` → `+tp/sl`. Bei kuruka juu ya TP **hailipi** — limit inajaza
      kwa bei yake, si kwa bei ya soko iliyopita.
    * `SL_FIRST` → `−(1 + overshoot/sl_pips)`. Stop inatekelezwa pale bei
      ilipofikia, si pale ilipoombwa.
    * `TIMEOUT` → `timeout_return_r` kama ilivyorekodiwa.

    Commission inatolewa kwa kila trade kwa `commission_pips ÷ sl_pips`.
    """
    sl = barriers["sl_atr"].to_numpy(dtype=float)
    tp = barriers["tp_atr"].to_numpy(dtype=float)
    outcome = barriers["outcome"].to_numpy()
    sl_pips = barriers["sl_pips"].to_numpy(dtype=float)
    past = barriers["touch_past_pips"].fillna(0.0).to_numpy(dtype=float)
    timeout_r = barriers["timeout_return_r"].fillna(0.0).to_numpy(dtype=float)

    with np.errstate(divide="ignore", invalid="ignore"):
        overshoot_r = np.where(outcome == SL_FIRST, past / sl_pips, 0.0)
        commission_r = commission_pips / sl_pips
    overshoot_r = np.nan_to_num(overshoot_r, nan=0.0, posinf=0.0)
    commission_r = np.nan_to_num(commission_r, nan=0.0, posinf=0.0)

    gross = np.where(
        outcome == TP_FIRST,
        tp / sl,
        np.where(outcome == SL_FIRST, -(1.0 + overshoot_r), timeout_r),
    )
    return gross - commission_r


def audit(barriers: pd.DataFrame, commission_pips: float = 0.7) -> CostAudit:
    """Gharama kwa kila cell — naive dhidi ya halisi."""
    out = CostAudit(commission_pips=float(commission_pips))
    if barriers.empty:
        out.notes.append("hakuna barriers")
        return out
    if "touch_past_pips" not in barriers.columns:
        out.notes.append(
            "`touch_past_pips` haipo — labels ni za toleo la 1. Gharama ya stop "
            "zilizoruka HAIWEZI kupimwa; jenga upya kwa toleo la 2."
        )
        return out

    for (sl_atr, tp_atr), chunk in barriers.groupby(["sl_atr", "tp_atr"], sort=True):
        sl_pips = chunk["sl_pips"].to_numpy(dtype=float)
        stopped = (chunk["outcome"] == SL_FIRST).to_numpy()
        n = len(chunk)

        with np.errstate(divide="ignore", invalid="ignore"):
            over_r = np.nan_to_num(
                chunk["touch_past_pips"].fillna(0.0).to_numpy(dtype=float) / sl_pips,
                nan=0.0, posinf=0.0,
            )
            comm_r = float(np.nanmean(np.nan_to_num(commission_pips / sl_pips, posinf=0.0)))

        stop_over = over_r[stopped]
        p_stopped = float(stopped.mean())
        mean_over_given = float(stop_over.mean()) if stop_over.size else 0.0

        realized = realized_r(chunk, commission_pips=0.0)
        naive_gross = np.where(
            chunk["outcome"].to_numpy() == TP_FIRST,
            (chunk["tp_atr"] / chunk["sl_atr"]).to_numpy(dtype=float),
            np.where(
                chunk["outcome"].to_numpy() == SL_FIRST,
                -1.0,
                chunk["timeout_return_r"].fillna(0.0).to_numpy(dtype=float),
            ),
        )

        out.cells.append(
            CellCost(
                sl_atr=float(sl_atr),
                tp_atr=float(tp_atr),
                n=int(n),
                sl_pips_median=float(np.nanmedian(sl_pips)),
                commission_r=comm_r,
                p_stopped=p_stopped,
                overshoot_r_mean_given_stop=mean_over_given,
                overshoot_r_p99_given_stop=(
                    float(np.percentile(stop_over, 99)) if stop_over.size else 0.0
                ),
                overshoot_r_max_given_stop=float(stop_over.max()) if stop_over.size else 0.0,
                # Gharama inayotarajiwa kwa trade = commission + P(stop)·E[overshoot|stop]
                cost_r_total=comm_r + p_stopped * mean_over_given,
                ev_r_naive=float(np.nanmean(naive_gross)),
                ev_r_realized=float(np.nanmean(realized)),
                ev_r_net=float(np.nanmean(realized) - comm_r),
            )
        )
    return out


# --------------------------------------------------------------------------
# Identities za T3 — hapa mara MOJA, si kwenye kila hesabu
# --------------------------------------------------------------------------


def n_max_from_cost(cost_r: float, sr_target: float, kappa: float) -> float:
    """Biashara ngapi kwa mwaka kabla gharama haijala return inayolengwa.

    Gharama inakua kama `n`; return inayolengwa inakua kama `√n` (sd ya mwaka
    ni `√n` kwa sd ya 1 R kwa trade). Kwa hiyo uwiano wa gharama kwa return
    unakua kama `√n` — na kikomo cha KIUCHUMI kinabana kabla ya cha kitakwimu.

        n·cost_R ≤ κ·SR*·√n     →     √n ≤ κ·SR* ÷ cost_R

    `κ` ni sehemu ya return inayolengwa unayokubali kuipoteza kwa gharama.
    """
    if cost_r <= 0:
        raise ValueError("cost_r lazima iwe chanya")
    return float((kappa * sr_target / cost_r) ** 2)


def delta_mer(sr_target: float, n_per_year: float, dev_dp: float = 2.0) -> float:
    """Edge ndogo kabisa yenye maana ya KIUCHUMI, kwa units za p_tp.

    `SR* = e·√n` ambapo `e` ni EV kwa trade (R), sd ya trade ≈ 1 R.

    **`dev_dp = 1 + tp/sl`, si 2.0 daima.** TP inalipa `tp/sl` R na SL
    inagharimu 1 R, kwa hiyo kuhamisha uzito kutoka SL kwenda TP kunabadilisha
    EV kwa `1 + tp/sl` kwa kila unit ya `p_tp`. Ni 2.0 kwa cell yenye
    `tp/sl = 1` pekee; kwa 2.0/3.0 ni **2.5**, na kutumia 2.0 kunavimbisha
    `δ_MER` kwa 25% (kosa la 2026-08-13).

    Hii ndiyo iliyochukua nafasi ya "je inazidi breakeven": kupima kwa usahihi
    wa breakeven ni kujenga jaribio ambalo, likifaulu, linarudisha Sharpe ~0.24
    — ambayo kwa MinBTL inaruhusu config **moja**. Hakuna mradi hapo.
    """
    if n_per_year <= 0:
        raise ValueError("n_per_year lazima iwe chanya")
    return float(sr_target / (dev_dp * np.sqrt(n_per_year)))


def n_required(
    delta: float,
    p: float = 0.5,
    alpha: float = 0.05,
    power: float = 0.80,
    two_sided: bool = True,
) -> float:
    """Observations HURU zinazohitajika kutambua `delta` — **ONE-SAMPLE**.

    Ni one-sample kwa sababu swali ni "je p_tp inazidi breakeven
    **iliyofahamika**", si "je makundi mawili yanatofautiana". Formula ya
    two-sample ingedai mara mbili ya data — kosa lililokaribia kufelisha mradi
    kwenye karatasi (mapitio ya nje, 2026-08-13).

    **`two_sided=True` ni chaguo, si usahihi.** Hypothesis yenyewe ni ya upande
    mmoja (tunachukua hatua tu ikiwa JUU ya breakeven), na one-sided ingedai
    31,500 badala ya 40,000 kwa δ = 0.007. Tumechagua ya tahadhari kwa makusudi:
    lango linaloruhusu pesa halisi kupita linapaswa kuwa gumu kuliko lazima, si
    rahisi kuliko lazima. Chaguo hili linaandikwa kwenye ripoti ili lisiwe
    limejificha ndani ya default.

    `NormalDist` ya standard library, si scipy — dependency mpya kwa quantile
    mbili ni gharama isiyo na sababu.
    """
    from statistics import NormalDist

    dist = NormalDist()
    z_a = dist.inv_cdf(1.0 - alpha / 2.0) if two_sided else dist.inv_cdf(1.0 - alpha)
    z_b = dist.inv_cdf(power)
    return float((z_a + z_b) ** 2 * p * (1.0 - p) / delta**2)


def config_budget(sr_target: float, years: float) -> float:
    """Configs HURU ngapi zinaweza kujaribiwa kabla matokeo hayajawa kelele.

    MinBTL (Bailey & López de Prado): `MinBTL < 2·ln(N) ÷ E[maxSR]²`, ikigeuzwa
    kutafuta N. Bajeti si mali ya dataset pekee — ni **function ya kile
    unachotarajia kupata**. SR* ya juu inatoa bajeti kubwa kwa sababu ni ahadi
    kubwa; SR* ya chini inabana kwa sababu kelele inaifunika kwa urahisi.

        SR* 1.0 → ~62 · SR* 0.7 → ~8 · SR* 0.5 → ~3
    """
    return float(np.exp(sr_target**2 * years / 2.0))
