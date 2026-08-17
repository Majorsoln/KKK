"""R1 — ukaguzi wa labels (T2, rejista DF-09..DF-11, DF-20, DF-21, K1-07, RS-04).

Hii **haijengi chochote**. Inasoma L4 iliyoandikwa diski na kuuliza maswali
saba ambayo, yakikosa majibu, kila namba ya R2+ inakuwa haina maana:

1. **Jiometri (RS-04).** Bila drift, `p_tp/(p_tp+p_sl) ≈ sl/(sl+tp)` — BILA
   timeout. Fomula ya `p_tp_first` peke yake haiwezi kufikia jiometri pale
   timeout ipo, na ingeonyesha "hitilafu" kila mara.
2. **Utulivu kwa miaka.** Base rate inayotembea kwa miaka si base rate.
3. **Timeout share** (§5.5, kikomo 0.35).
4. **Tie-break** (§5.2, >1% → PD).
5. **Setup dhidi ya control** (DF-20) — je filter inachagua trades bora, au
   inachagua tu trades chache? Bila control, "4.46%" ni idadi, si ushahidi.
6. **Quantile: MID dhidi ya bei ya trade** (§5.1) — uamuzi wa PD upimwe kwa
   namba, si kwa hoja.
7. **M1 dhidi ya tick** — §5 inasema bar haiwezi kusema ipi iligusa kwanza.
   Hapa hoja hiyo inakuwa asilimia.

**G2:** takwimu za holdout ni MARUFUKU. Ukaguzi uko hapa TENA (build tayari
inachuja) kwa sababu ripoti ndiyo inayosomwa; kinga inayolinda faili pekee
haizuii namba iliyokwishaandikwa kwenye ripoti.

**Gharama:** spread ishaingia kwenye path (§5.2 — barrier inatatuliwa kwa bei
ya trade). Kwa hiyo `cost_pips` ya L-D ni **commission + swap PEKEE**, na
mamlaka yake ni RCE (§6.2 F6), si hapa. R1 inatoa mkunjo wa unyeti kwa
gharama zilizotajwa wazi; namba halisi inakuja T7.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from .labels import MARKET_FILL_PRIOR, SL_FIRST, TIMEOUT, TP_FIRST, quality_bucket

R1_REPORT_VERSION = 1


@dataclass
class R1Report:
    ok: bool = True
    problems: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    payload: dict[str, Any] = field(default_factory=dict)

    def fail(self, message: str) -> None:
        self.ok = False
        self.problems.append(message)


# --------------------------------------------------------------------------
# Kupakia
# --------------------------------------------------------------------------


def load_labels(root: Path, symbols: list[str] | None = None) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Points na barriers zote za L4 kutoka `L4_labels/labels/symbol=*/`."""
    points: list[pd.DataFrame] = []
    barriers: list[pd.DataFrame] = []
    for folder in sorted(root.glob("symbol=*")):
        symbol = folder.name.split("=", 1)[1]
        if symbols and symbol not in symbols:
            continue
        for path in sorted(folder.glob("points-*.parquet")):
            points.append(pd.read_parquet(path))
        for path in sorted(folder.glob("barriers-*.parquet")):
            barriers.append(pd.read_parquet(path))
    empty = pd.DataFrame()
    return (
        pd.concat(points, ignore_index=True) if points else empty,
        pd.concat(barriers, ignore_index=True) if barriers else empty,
    )


def holdout_violations(frame: pd.DataFrame, holdout_start: date) -> int:
    """G2 — points zozote kuanzia `holdout_start` ni kosa, si onyo."""
    if frame.empty:
        return 0
    return int((frame["decision_time"].dt.date >= holdout_start).sum())


def attach_flags(barriers: pd.DataFrame, points: pd.DataFrame) -> pd.DataFrame:
    """`is_setup`/`is_control` kutoka points → cells (join kwa symbol + muda)."""
    if barriers.empty or points.empty:
        return barriers
    keys = points[["symbol", "decision_time", "is_setup", "is_control", "atr_pips"]]
    return barriers.merge(keys, on=["symbol", "decision_time"], how="left")


# --------------------------------------------------------------------------
# 1. Base rates + jiometri (RS-04)
# --------------------------------------------------------------------------


def base_rates(barriers: pd.DataFrame) -> pd.DataFrame:
    """Kwa kila cell: p_tp BILA timeout, dhidi ya jiometri `sl/(sl+tp)`.

    Timeout haitupwi — inaripotiwa kama darasa lake (§5.5). Lakini swali la
    jiometri ni "kati ya zilizofika mahali, ngapi zilifika TP", na timeout
    haikufika popote. Kuijumuisha ni kulinganisha vitu viwili tofauti.

    ## `diff` INAAMINIKA TU TIMEOUT IKIWA NDOGO

    `sl/(sl+tp)` ni uwezekano wa kugusa kwa **horizon isiyo na mwisho**. Kwa
    horizon ya bars 24, kuchuja "zilizofika mahali" kunaleta upendeleo:
    **barrier ILIYO KARIBU inaguswa mapema, kwa hiyo inashinda kwa uwiano
    mkubwa kati ya zilizofika**. Upendeleo huo unakua na timeout.

    Kwa hiyo `diff > 0` kwenye cell yenye `tp < sl` **si edge** — inaweza kuwa
    truncation pekee. Grid ilipopanuliwa hadi `sl 3.0 / tp 0.5` (T5), cell hiyo
    ilitoa `p_tp` 0.916 dhidi ya jiometri 0.857 — SE 3.2 juu — ikiwa na timeout
    kubwa. Kwenye grid ya awali (`sl ≤ 2.0`) hakuna cell iliyofikia hali hiyo,
    kwa hiyo dosari haikuonekana (2026-08-17).

    Safu `geometry_reliable` na `geometry_bias` zinasema hilo kwa kila cell,
    ili `diff` isisomwe kama edge pale ambapo ni jiometri ya truncation.
    """
    if barriers.empty:
        return pd.DataFrame()
    grouped = barriers.groupby(["sl_atr", "tp_atr"], sort=True)
    rows = []
    for (sl_atr, tp_atr), chunk in grouped:
        n = len(chunk)
        n_tp = int((chunk["outcome"] == TP_FIRST).sum())
        n_sl = int((chunk["outcome"] == SL_FIRST).sum())
        n_to = int((chunk["outcome"] == TIMEOUT).sum())
        resolved = n_tp + n_sl
        p_tp = n_tp / resolved if resolved else float("nan")
        geometry = sl_atr / (sl_atr + tp_atr)
        rows.append(
            {
                "sl_atr": sl_atr,
                "tp_atr": tp_atr,
                "n": n,
                "n_tp": n_tp,
                "n_sl": n_sl,
                "n_timeout": n_to,
                "timeout_frac": n_to / n if n else float("nan"),
                "p_tp": p_tp,
                "geometry": geometry,
                "diff": p_tp - geometry,
                # Upendeleo wa truncation unaelekea barrier ILIYO KARIBU.
                "geometry_reliable": bool(n and (n_to / n) <= 0.05),
                "geometry_bias": (
                    "none" if tp_atr == sl_atr else ("tp" if tp_atr < sl_atr else "sl")
                ),
                # Kosa la kawaida la uwiano — "tofauti" ndogo kuliko hili si tofauti.
                "se": float(np.sqrt(p_tp * (1 - p_tp) / resolved)) if resolved else float("nan"),
                "ev_r": expected_r(chunk),
            }
        )
    return pd.DataFrame(rows)


def expected_r(cells: pd.DataFrame, cost_pips: float = 0.0) -> float:
    """E[R] kwa madarasa MATATU (§2.1 ya KAIROS-1): TP, SL, na timeout.

    Timeout haina thamani ya sifuri — ina `timeout_return_r` yake. Kuiweka
    sifuri ni kudhani kwamba setup isiyofika popote iliishia pale ilipoanzia.
    """
    if cells.empty:
        return float("nan")
    gross = np.where(
        cells["outcome"] == TP_FIRST,
        cells["tp_atr"] / cells["sl_atr"],
        np.where(cells["outcome"] == SL_FIRST, -1.0, cells["timeout_return_r"].fillna(0.0)),
    )
    if cost_pips:
        gross = gross - cost_pips / cells["sl_pips"].to_numpy()
    return float(np.nanmean(gross))


def cell_coverage(barriers: pd.DataFrame, folds: list) -> pd.DataFrame:
    """Labels kwa cell ndani ya kila fold — kwa **mizani miwili**.

    `min_labels_per_cell` ikipimwa pooled juu ya data YOTE haiwezi kufeli:
    kila decision point inapata cells zote 25, kwa hiyo kila cell ina idadi ILE
    ILE (setups zote). Ukaguzi unaotoa jibu lile lile kwa muundo, bila kujali
    data, ni ule ule ulioficha `clock_drift` kwa 0/34,089 kwenye T1.

    Mizani inayohesabu ni ile ya **mahali mafunzo yanapofanyika**:

    * `scope="pooled"` — cell × fold, symbols zote kwa pamoja. Huu ndio
      utaratibu uliotangazwa (DATA_SPLIT_PLAN §2: "symbols ZOTE ziko kwenye
      fold ile ile"; KAIROS-1 ni model MMOJA kwa symbols 12, ndiyo maana
      features ni scale-free). **Hiki ndicho kigezo.**
    * `scope="symbol"` — cell × symbol × fold. Si kigezo, ni **uchunguzi**:
      kinaonyesha symbol ipi ina njaa wapi. Kigezo hapa kingekuwa kikali
      kuliko utaratibu wenyewe wa mafunzo.
    """
    if barriers.empty or not folds:
        return pd.DataFrame()
    days = barriers["decision_time"].dt.date
    rows = []
    for fold in folds:
        inside = (days >= fold.val_start) & (days <= fold.val_end)
        chunk = barriers[inside]
        if chunk.empty:
            rows.append(
                {"scope": "pooled", "fold": fold.index, "symbol": "*", "n_min": 0, "cells": 0}
            )
            continue
        pooled = chunk.groupby(["sl_atr", "tp_atr"], sort=False).size()
        rows.append(
            {
                "scope": "pooled",
                "fold": fold.index,
                "symbol": "*",
                "n_min": int(pooled.min()),
                "cells": int(len(chunk)),
            }
        )
        counts = chunk.groupby(["symbol", "sl_atr", "tp_atr"], sort=False).size()
        for symbol, n_min in counts.groupby(level="symbol").min().items():
            rows.append(
                {
                    "scope": "symbol",
                    "fold": fold.index,
                    "symbol": str(symbol),
                    "n_min": int(n_min),
                    "cells": int((chunk["symbol"] == symbol).sum()),
                }
            )
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------
# 2. Utulivu kwa miaka
# --------------------------------------------------------------------------


def year_stability(barriers: pd.DataFrame) -> pd.DataFrame:
    """p_tp (bila timeout), timeout share na E[R] kwa kila mwaka.

    Hii ndiyo "curve ya utulivu": base rate inayotofautiana kwa miaka si base
    rate — ni wastani wa masoko mawili tofauti yaliyochanganywa.
    """
    if barriers.empty:
        return pd.DataFrame()
    years = barriers["decision_time"].dt.year
    rows = []
    for year, chunk in barriers.groupby(years, sort=True):
        n_tp = int((chunk["outcome"] == TP_FIRST).sum())
        n_sl = int((chunk["outcome"] == SL_FIRST).sum())
        n_to = int((chunk["outcome"] == TIMEOUT).sum())
        resolved = n_tp + n_sl
        rows.append(
            {
                "year": int(year),
                "cells": len(chunk),
                "p_tp": n_tp / resolved if resolved else float("nan"),
                "timeout_frac": n_to / len(chunk),
                "ev_r": expected_r(chunk),
            }
        )
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------
# 3. Setup dhidi ya control (DF-20)
# --------------------------------------------------------------------------


def setup_vs_control(barriers: pd.DataFrame) -> dict[str, Any]:
    """Je SETUP-v1 inachagua trades BORA, au inachagua tu trades chache?

    Hili ndilo swali ambalo control sample ilikuwepo kwa ajili yake (§4.3).
    Filter inayotoa p_tp ile ile ya bars za nasibu haijafanya kazi yoyote —
    imepunguza tu idadi, na kupunguza idadi si makali.
    """
    if barriers.empty or "is_setup" not in barriers:
        return {}
    out: dict[str, Any] = {}
    for name, mask in (("setup", barriers["is_setup"]), ("control", barriers["is_control"])):
        chunk = barriers[mask.fillna(False)]
        n_tp = int((chunk["outcome"] == TP_FIRST).sum())
        n_sl = int((chunk["outcome"] == SL_FIRST).sum())
        n_to = int((chunk["outcome"] == TIMEOUT).sum())
        resolved = n_tp + n_sl
        p_tp = n_tp / resolved if resolved else float("nan")
        out[name] = {
            "cells": len(chunk),
            "p_tp": p_tp,
            "se": float(np.sqrt(p_tp * (1 - p_tp) / resolved)) if resolved else float("nan"),
            "timeout_frac": n_to / len(chunk) if len(chunk) else float("nan"),
            "ev_r": expected_r(chunk),
            "atr_pips_median": float(chunk["atr_pips"].median()) if "atr_pips" in chunk else None,
        }
    if "setup" in out and "control" in out:
        d = out["setup"]["p_tp"] - out["control"]["p_tp"]
        se = float(np.sqrt(out["setup"]["se"] ** 2 + out["control"]["se"] ** 2))
        out["delta_p_tp"] = d
        out["delta_se"] = se
        out["delta_z"] = d / se if se else float("nan")
        out["delta_ev_r"] = out["setup"]["ev_r"] - out["control"]["ev_r"]
    return out


# --------------------------------------------------------------------------
# 4. Quantile: MID dhidi ya bei ya trade (§5.1)
# --------------------------------------------------------------------------


def quantile_mid_vs_trade(points: pd.DataFrame, quantiles: list[float]) -> pd.DataFrame:
    """Tofauti ya L-A ikipimwa kwa MID dhidi ya bei ya trade, kwa symbol.

    §5.1 iliamua MID kwa hoja (spread inaingia path na RCE — si mara tatu).
    Symbols pana (XAUUSD, GBPJPY) ndizo zinazoweza kuipinga hoja hiyo kwa
    namba, kwa hiyo zinaonyeshwa peke yake pia.

    **Tofauti LAZIMA ipewe ishara ya trade.** `quantile_y_trade` haina
    mwelekeo: BUY inanunua kwa ask na kufunga kwa bid, kwa hiyo iko CHINI ya
    ya mid; SELL ni kinyume kabisa, iko JUU. Ukichukua wastani wa pamoja,
    upendeleo wa BUY unafuta wa SELL na jibu linakuwa ~0 kwa symbol yoyote —
    ikiwemo XAUUSD yenye spread ya pips 35. Namba hiyo ya sifuri ingesomeka
    kama "uamuzi hauna athari", wakati ukweli ni kwamba athari ipo pande zote
    mbili kwa ukubwa ule ule, ikielekea pande tofauti (kosa langu, 2026-08-13).
    Kipimo sahihi ni `direction × (mid − trade)`: gharama kwa units za ATR,
    daima chanya.
    """
    if points.empty or not {"quantile_y_trade", "direction"} <= set(points.columns):
        return pd.DataFrame()
    rows = []
    for symbol, chunk in points.groupby("symbol", sort=True):
        chunk = chunk.dropna(subset=["quantile_y", "quantile_y_trade"])
        if chunk.empty:
            continue
        mid = chunk["quantile_y"]
        trade = chunk["quantile_y_trade"]
        shift = chunk["direction"] * (mid - trade)
        row: dict[str, Any] = {
            "symbol": symbol,
            "n": len(chunk),
            "spread_entry_p50": float(chunk["spread_entry_pips"].median()),
            "spread_exit_p50": (
                float(chunk["spread_exit_pips"].median())
                if "spread_exit_pips" in chunk
                else None
            ),
            "atr_pips_p50": float(chunk["atr_pips"].median()) if "atr_pips" in chunk else None,
            # Kipimo chenyewe: L-A ingehama kwa kiasi gani (ATR) ikigeuzwa trade.
            "shift_mean": float(shift.mean()),
            "shift_p50": float(shift.median()),
            "shift_p90": float(shift.quantile(0.90)),
            # Ulinganisho huru: (spread ya kuingia + ya kutoka) ÷ 2 ÷ ATR.
            # Ikitofautiana sana na `shift_p50`, mmoja kati ya hivi viwili ni kosa.
            "shift_expected_p50": (
                float(
                    (
                        (chunk["spread_entry_pips"] + chunk["spread_exit_pips"])
                        / 2.0
                        / chunk["atr_pips"]
                    ).median()
                )
                if {"spread_exit_pips", "atr_pips"} <= set(chunk.columns)
                else None
            ),
            # Wastani wa pamoja — unabaki ili ionekane KWA NINI ni ~0.
            "pooled_mean_diff": float(mid.mean() - trade.mean()),
        }
        for q in quantiles:
            row[f"shift_q{q:g}"] = float(shift.quantile(q))
        rows.append(row)
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------
# 5. L-C — fill/slippage kwenye barrier (K1-07, §5.3)
# --------------------------------------------------------------------------


def fill_bootstrap(barriers: pd.DataFrame, cap_stop: float) -> dict[str, Any]:
    """Bei ilipita barrier kwa kiasi gani kabla ya tick ya kwanza kuionekana?

    Kwa **SL** hii ni stop order: umbali huo ni hasara halisi, na `cap` ya
    RCE inaamua kama fill hiyo ni halali. Kwa **TP** ni limit: bei kuruka
    zaidi hakukupi bei bora — limit inajaza kwa bei yake — kwa hiyo umbali ni
    taarifa, si faida. Market orders hazipimwi hapa kwa makusudi (§5.3):
    kutojazwa live ni latency ya wakati ule, na historia haiwezi kuikisia.
    """
    if barriers.empty or "touch_past_pips" not in barriers:
        return {}
    out: dict[str, Any] = {"market_prior": MARKET_FILL_PRIOR, "cap_stop_pips": cap_stop}
    for name, code in (("stop_sl", SL_FIRST), ("limit_tp", TP_FIRST)):
        past = barriers.loc[barriers["outcome"] == code, "touch_past_pips"].dropna()
        if past.empty:
            continue
        entry = {
            "n": int(len(past)),
            "p50": float(past.median()),
            "p90": float(past.quantile(0.90)),
            "p99": float(past.quantile(0.99)),
            "max": float(past.max()),
        }
        if code == SL_FIRST:
            entry["within_cap"] = float((past <= cap_stop).mean())
            entry["over_cap"] = int((past > cap_stop).sum())
        out[name] = entry
    return out


# --------------------------------------------------------------------------
# 6. L-D — quality buckets (§5.4)
# --------------------------------------------------------------------------


def quality_distribution(
    barriers: pd.DataFrame, thresholds: dict[str, float], cost_grid: list[float]
) -> dict[str, Any]:
    """Mgawanyo wa A+/A/B/reject kwa gharama zilizotajwa WAZI.

    `cost_pips` hapa ni **commission + swap pekee** — spread ishaingia kwenye
    path (§5.2), na kuihesabu tena ni kuihesabu mara mbili. Mamlaka ya namba
    hiyo ni RCE (T7); mkunjo huu ni unyeti, si jibu.
    """
    if barriers.empty:
        return {}
    tp = barriers["tp_atr"].to_numpy()
    sl = barriers["sl_atr"].to_numpy()
    outcome = barriers["outcome"].to_numpy()
    sl_pips = barriers["sl_pips"].to_numpy()
    timeout_r = barriers["timeout_return_r"].fillna(0.0).to_numpy()

    gross = np.where(outcome == TP_FIRST, tp / sl, np.where(outcome == SL_FIRST, -1.0, timeout_r))
    out: dict[str, Any] = {}
    for cost in cost_grid:
        net = gross - cost / sl_pips
        buckets = pd.Series([quality_bucket(float(r), thresholds) for r in net]).value_counts()
        total = int(buckets.sum())
        out[f"{cost:g}"] = {
            "ev_r_net": float(np.nanmean(net)),
            **{k: int(buckets.get(k, 0)) / total for k in ("A+", "A", "B", "reject")},
        }
    return out


# --------------------------------------------------------------------------
# Ripoti
# --------------------------------------------------------------------------


def build_report(
    cfg,
    points: pd.DataFrame,
    barriers: pd.DataFrame,
    holdout_start: date,
    build_stats: dict[str, Any] | None = None,
    cost_grid: list[float] | None = None,
    folds: list | None = None,
) -> R1Report:
    report = R1Report()
    if barriers.empty:
        report.fail("hakuna labels — `build-labels` kwanza")
        return report

    # G2 kwanza: takwimu zisihesabiwe kabla mpaka haujathibitishwa.
    leaked = holdout_violations(points, holdout_start)
    if leaked:
        report.fail(f"G2: points {leaked:,} ziko ndani ya holdout ({holdout_start}) — SIMAMA")
        return report

    barriers = attach_flags(barriers, points)
    # Base rates ni za SETUPS: hizo ndizo zitakazofundisha. Controls zipo
    # kulinganisha (§4.3), na kuzichanganya kwenye base rate kungeifuta tofauti
    # ambayo ndiyo hasa tunaipima.
    trainable = barriers[barriers["is_setup"].fillna(False)] if "is_setup" in barriers else barriers
    rates = base_rates(trainable)
    years = year_stability(trainable)

    min_per_cell = int(cfg.get("labels.barrier.min_labels_per_cell"))
    thin = rates[rates["n"] < min_per_cell]
    if not thin.empty:
        report.fail(
            f"cells {len(thin)} zina labels chini ya {min_per_cell} "
            f"(ndogo kuliko zote: {int(thin['n'].min()):,})"
        )
    else:
        report.notes.append(
            f"`min_labels_per_cell` juu ya data yote ({int(rates['n'].min()):,}) inapita kwa "
            "MUUNDO: kila point inapata cells 25, kwa hiyo cells zote zina idadi ile ile "
            "daima. Kigezo halisi ni cha cell x fold (1b) — mizani ya mafunzo."
        )

    coverage = cell_coverage(trainable, folds or [])
    if not coverage.empty:
        # KIGEZO: mizani ya mafunzo — cell x fold, symbols zote kwa pamoja.
        pooled = coverage[coverage["scope"] == "pooled"]
        thin_pooled = pooled[pooled["n_min"] < min_per_cell]
        if not thin_pooled.empty:
            worst_fold = thin_pooled.loc[thin_pooled["n_min"].idxmin()]
            report.fail(
                f"cell x fold (pooled): folds {len(thin_pooled)} ziko chini ya {min_per_cell} "
                f"(mbaya kuliko zote: fold {int(worst_fold['fold'])} = "
                f"{int(worst_fold['n_min'])})"
            )
        # UCHUNGUZI: symbol ipi ina njaa wapi. Si kigezo — kigezo cha kila
        # symbol peke yake kingekuwa kikali kuliko utaratibu wa mafunzo,
        # ambao ni pooled (DATA_SPLIT_PLAN §2). Lakini kinyamaza si sahihi
        # pia: hesabu ya kila symbol ndiyo inayoonyesha calibration ya symbol
        # moja moja itakapokosa msingi.
        per_symbol = coverage[coverage["scope"] == "symbol"]
        thin_symbol = per_symbol[per_symbol["n_min"] < min_per_cell]
        if not thin_symbol.empty:
            worst = thin_symbol.sort_values("n_min").head(4)
            orodha = " · ".join(
                f"{r['symbol']} fold {int(r['fold'])} = {int(r['n_min'])}"
                for _, r in worst.iterrows()
            )
            report.notes.append(
                f"cell x SYMBOL x fold: michanganyiko {len(thin_symbol)}/{len(per_symbol)} iko "
                f"chini ya {min_per_cell} ({orodha}). Si kigezo — mafunzo ni pooled — lakini "
                "uchambuzi wowote wa symbol MOJA ndani ya folds hizo hauna msingi."
            )

    max_timeout = float(cfg.get("labels.barrier.max_timeout_frac"))
    timeout_frac = float((barriers["outcome"] == TIMEOUT).mean())
    if timeout_frac > max_timeout:
        report.fail(f"timeout {timeout_frac:.1%} > kikomo {max_timeout:.0%} (§5.5)")

    ties = int(barriers["tie_break"].sum())
    tie_frac = ties / len(barriers)
    if tie_frac > 0.01:
        report.fail(f"tie-break {tie_frac:.2%} > 1% — inapanda kwa PD (§5.2)")
    elif ties == 0:
        # Si pengo la kipimo. §5.2 yenyewe inaeleza kwa nini: kwa BUY, SL na TP
        # zote zinapimwa kwa BID, kwa hiyo tick moja ingehitaji SL > TP.
        report.notes.append(
            "tie-break 0 — sheria ya SL-kwanza HAIWEZI kuwaka kwa muundo huu "
            "(BUY: SL na TP zote kwa bid; tick moja haiwezi kuwa ≤ X na ≥ Y ikiwa X < Y). "
            "Ipo kwa ajili ya grid zijazo zinazopima pande mbili tofauti."
        )

    # Jiometri (RS-04): tofauti inapimwa kwa vipimo vya kosa, si kwa jicho.
    rates["z"] = rates["diff"] / rates["se"]
    worst = rates.loc[rates["diff"].abs().idxmax()] if not rates.empty else None

    spread_dir = int((rates["diff"] < 0).sum())
    report.notes.append(
        f"jiometri: cells {spread_dir}/{len(rates)} ziko CHINI ya sl/(sl+tp) — "
        "spread inasogeza chini kwa utaratibu (RS-04 inatarajia hivyo)"
    )

    svc = setup_vs_control(barriers)
    quantiles = [float(q) for q in cfg.get("labels.quantile.quantiles")]
    qcmp = quantile_mid_vs_trade(points, quantiles)

    cap_stop = _cap_stop(cfg)
    fills = fill_bootstrap(barriers, cap_stop)
    buckets = quality_distribution(
        barriers,
        {k: float(v) for k, v in cfg.get("labels.quality_buckets").items()},
        cost_grid or [0.0, 0.5, 1.0],
    )

    m1 = {}
    if build_stats:
        totals = build_stats.get("totals", {})
        m1 = {
            "cells": totals.get("m1_cells", 0),
            "disagree": totals.get("m1_disagree", 0),
            "disagree_frac": totals.get("m1_disagree_frac", 0.0),
            "ambiguous": totals.get("m1_ambiguous", 0),
        }
        if not m1["cells"]:
            report.notes.append(
                "M1-dhidi-ya-tick haijapimwa — label_build.json ni ya toleo la zamani; "
                "jenga upya (`build-labels --no-resume`)"
            )

    if "quantile_y_trade" not in points.columns:
        report.notes.append(
            "quantile ya bei ya trade haipo — points ni za toleo la zamani; "
            "§5.1 haiwezi kupimwa hadi ujenzi upya"
        )

    report.payload = {
        "version": R1_REPORT_VERSION,
        "config_hash": cfg.config_hash,
        # Sahihi za T2 zinahusu sehemu hizi, si faili nzima ya config (§3.8).
        "section_hashes": {
            k: cfg.section_hash(k) for k in ("labels", "setups", "quality", "splits")
        },
        "holdout_start": holdout_start.isoformat(),
        "totals": {
            "points": int(len(points)),
            "cells": int(len(barriers)),
            "setups": int(points["is_setup"].sum()) if "is_setup" in points else None,
            "controls": int(points["is_control"].sum()) if "is_control" in points else None,
            "timeout_frac": timeout_frac,
            "tie_breaks": ties,
            "tie_break_frac": tie_frac,
            "min_labels_per_cell": int(rates["n"].min()),
            "min_labels_per_cell_fold": (
                int(coverage.loc[coverage["scope"] == "pooled", "n_min"].min())
                if not coverage.empty
                else None
            ),
            "min_labels_per_cell_symbol_fold": (
                int(coverage.loc[coverage["scope"] == "symbol", "n_min"].min())
                if not coverage.empty
                else None
            ),
            "ev_r_gross": expected_r(barriers),
            "ev_r_gross_setups": expected_r(trainable),
        },
        "scope": "setups (TRAIN+VAL) kwa base_rates/year_stability; cells zote kwa jumla",
        "base_rates": rates.to_dict(orient="records"),
        "geometry_worst": None if worst is None else worst.to_dict(),
        "year_stability": years.to_dict(orient="records"),
        "cell_coverage": coverage.to_dict(orient="records"),
        "setup_vs_control": svc,
        "quantile_mid_vs_trade": qcmp.to_dict(orient="records"),
        "fill_bootstrap": fills,
        "quality_buckets": buckets,
        "m1_vs_tick": m1,
        "problems": report.problems,
        "notes": report.notes,
    }
    return report


def _cap_stop(cfg) -> float:
    """Cap ya stop kutoka `config/risk.yaml` — chanzo KIMOJA (§6.2 F6).

    RCE haiguswi; inasomwa. Kuiga namba hii kwenye `data.yaml` kungetengeneza
    gharama ya pili kwenye mfumo, ambayo ndiyo hasa F6 inayokataza.
    """
    import yaml

    root = Path(__file__).resolve().parents[2]
    payload = yaml.safe_load((root / "config" / "risk.yaml").read_text(encoding="utf-8"))
    return float(payload["slippage_cap_pips"]["stop"])


def load_build_stats(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
