"""T2 — kujenga L4 kwa decision points zote (DF-09/10/11, K1-07).

Kazi hii ndiyo kubwa kuliko zote za tabaka la data: decision points ~52,000,
kila moja ikitatuliwa kwa **path ya ticks** kwa grid ya 5×5. Kwa hiyo mambo
matatu ya vitendo yanashughulikiwa hapa, si kwenye sheria za `labels.py`:

1. **Dirisha la ticks linatiririka.** Decision points zinachakatwa kwa
   mpangilio wa muda, na buffer inabeba tu kile kinachohitajika sasa. Kusoma
   partitions upya kwa kila point kungekuwa kusoma L0 mara 52,000.
2. **Horizon ni BARS, si masaa.** `horizon_bars: 24` ni bars 24 za H1. Ijumaa
   jioni, bars 24 zinavuka wikendi — dirisha la muda ni siku 3, si saa 24.
   Mwisho unatoka kwenye **index ya bars**, si `timedelta`.
3. **Kuendelea baada ya kukatika.** Hali inahifadhiwa kwa `(symbol, mwaka)`;
   kukatika kunapoteza mwaka mmoja, si kazi yote.

**Gharama HAIINGII hapa.** Labels ni ukweli kuhusu bei — cost ni ya RCE
(§6.2 F6: "RCE ndiyo mamlaka ya `cost_pips`; hakuna gharama mbili kwenye
mfumo"). L-D (§5.4) inatokana na L-B + gharama, kwa hiyo malighafi yake
(`sl_pips`, `spread_entry_pips`, `nights`) inahifadhiwa na R_net inahesabiwa
pale mawazo ya gharama yanapotajwa wazi.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterable, Sequence

import numpy as np
import pandas as pd

from .labels import epoch_us, resolve_arrays, resolve_m1_arrays

ProgressFn = Callable[[int, int, str], None]

# Muundo wa matokeo ya L4. Ukibadilika, kazi ya masaa haiwezi kuendelea
# ilipoishia — hali ya zamani inatupwa badala ya kuchanganywa kimya.
#
# 2 (2026-08-12): `touch_price` kwa kila cell (L-C slippage), `terminal_trade` +
#     `quantile_y_trade` (§5.1 mid-dhidi-ya-trade), na ukaguzi wa M1-dhidi-ya-tick
#     kwa sampuli. Vipimo vitatu vya R1 ambavyo toleo 1 halikurekodi; kuvipima
#     baadaye kungehitaji kupita kwenye ticks mara ya pili.
LABEL_BUILD_VERSION = 3


class TickWindow:
    """Buffer inayotiririka juu ya partitions za L0 za symbol MOJA.

    Inabeba `timestamp/bid/ask` pekee — volumes hazitumiki kwenye labels, na
    kuziacha kunapunguza kumbukumbu kwa nusu. Kwa Toleo B (faili za mwezi,
    rows ~6.6M) hiyo ni tofauti ya GB, si MB.
    """

    def __init__(self, cfg, paths: Sequence[Path]):
        self._cfg = cfg
        self._paths = list(paths)
        self._next = 0
        self._frames: list[pd.DataFrame] = []
        self._ends: list[int] = []          # µs ya tick ya mwisho ya kila frame
        self._stamps = np.empty(0, dtype="int64")
        self._bid = np.empty(0, dtype="float64")
        self._ask = np.empty(0, dtype="float64")
        # Muhimu: hii inasasishwa KILA frame inapoingia, si baada ya kitanzi.
        # Ikisasishwa baada, sharti la `ensure` halibadiliki kamwe na kitanzi
        # kinasoma L0 NZIMA — ticks milioni 289 na `MemoryError` (2026-08-11).
        self._last = -(2**62)
        self.partitions_read = 0
        self.partitions_skipped = 0

    @property
    def last_stamp(self) -> int:
        return self._last

    @property
    def rows(self) -> int:
        return int(len(self._stamps))

    def _rebuild(self) -> None:
        if not self._frames:
            self._stamps = np.empty(0, dtype="int64")
            self._bid = np.empty(0, dtype="float64")
            self._ask = np.empty(0, dtype="float64")
            return
        joined = (
            pd.concat(self._frames, ignore_index=True)
            if len(self._frames) > 1
            else self._frames[0]
        )
        # `kind="stable"`: ticks zenye timestamp ILE ILE zinabaki kwa mpangilio
        # wa kufika. Tie-break ya §5.2 inategemea "ya kwanza" kuwa na maana moja.
        joined = joined.sort_values("timestamp", kind="stable", ignore_index=True)
        self._stamps = epoch_us(joined["timestamp"])
        self._bid = joined["bid"].to_numpy()
        self._ask = joined["ask"].to_numpy()

    def seek(self, start: pd.Timestamp) -> None:
        """Ruka partitions zinazoishia kabla ya `start` BILA kuzisoma.

        Decision point ya kwanza iko miezi ~6 ndani ya data (ATR band
        inahitaji historia). Bila hii, `ensure` ingesoma partitions 130 za
        Januari–Juni ili tu kuzitupa mara moja. Tarehe inatoka kwenye NJIA —
        parquet haiguswi hata kidogo.
        """
        if self._frames:
            return   # buffer ina data; kuruka sasa kungetoboa shimo
        limit = pd.Timestamp(start)
        while self._next < len(self._paths):
            end = _partition_end(self._paths[self._next])
            if end is None or end >= limit:
                break
            self._next += 1
            self.partitions_skipped += 1

    def ensure(self, end: pd.Timestamp) -> None:
        """Soma partitions hadi buffer ifunike `end` (au L0 iishe)."""
        from .schema import read_quotes

        target = pd.Timestamp(end).value // 1_000
        grew = False
        while self._last < target and self._next < len(self._paths):
            frame = read_quotes(self._paths[self._next], self._cfg)
            self._next += 1
            self.partitions_read += 1
            if frame.empty:
                continue
            stamps = epoch_us(frame["timestamp"])
            self._frames.append(frame.loc[:, ["timestamp", "bid", "ask"]])
            self._ends.append(int(stamps[-1]))
            self._last = max(self._last, int(stamps[-1]))
            grew = True
        if grew:
            self._rebuild()

    def trim(self, start: pd.Timestamp) -> None:
        """Tupa frames zilizoisha kabla ya `start` — hazitahitajika tena.

        Points zinachakatwa kwa mpangilio wa muda, kwa hiyo kilichopita
        hakirudi. Bila hii, buffer ingekua hadi L0 nzima. Mwisho wa kila frame
        umehifadhiwa wakati wa kusoma; kuuhesabu upya hapa kungekuwa O(n) kwa
        kila decision point.
        """
        cut = pd.Timestamp(start).value // 1_000
        keep = [(f, e) for f, e in zip(self._frames, self._ends) if e >= cut]
        if len(keep) != len(self._frames):
            self._frames = [f for f, _ in keep]
            self._ends = [e for _, e in keep]
            self._rebuild()

    def arrays(self) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        return self._stamps, self._bid, self._ask


_HIVE = re.compile(r"year=(\d{4}).*?month=(\d{2})(?:.*?day=(\d{2}))?", re.DOTALL)
_IN_NAME = re.compile(r"(\d{4})-(\d{2})(?:-(\d{2}))?")


def _partition_end(path: Path) -> pd.Timestamp | None:
    """Kadirio la JUU la tick ya mwisho ya partition, kutoka NJIA yake.

    L0 ina mipangilio miwili (`iter_partitions` inakubali yote): Hive
    (`year=2016/month=07/day=14/ticks.parquet`) na ya jina
    (`2016/2016-07-14.parquet`). Zote mbili zinashughulikiwa **kwa uwazi** —
    regex moja ya kubahatisha ilikuwa inasoma `2024/2024-01-15` kama mwezi wa
    20 na kurudisha None kimya, kwa hiyo hakuna kilichorukwa.

    Kadirio linaongezwa **siku 3**: Toleo B ni la mwezi na linaingia siku ya
    kwanza ya mwezi unaofuata (linakata saa 05:00 UTC, §3). Bora kusoma
    partition isiyohitajika kuliko kuruka inayohitajika. Isipoeleweka → None,
    na hakuna kinachorukwa.
    """
    text = str(path).replace("\\", "/")
    match = _HIVE.search(text) or _IN_NAME.search(Path(text).name)
    if not match:
        return None
    year, month, day = match.group(1), match.group(2), match.group(3)
    try:
        if day:
            stamp = pd.Timestamp(int(year), int(month), int(day), tz="UTC")
        else:
            stamp = pd.Timestamp(int(year), int(month), 1, tz="UTC") + pd.offsets.MonthEnd(1)
    except (ValueError, TypeError):
        return None
    return stamp + pd.Timedelta(days=3)


@dataclass
class SymbolLabels:
    symbol: str
    points: pd.DataFrame
    barriers: pd.DataFrame
    stats: dict[str, Any] = field(default_factory=dict)

    def render(self) -> str:
        s = self.stats
        return (
            f"{self.symbol}: points {s['points']} (setup {s['setups']} · control "
            f"{s['controls']}) · cells {s['cells']} · timeout {s['timeout_frac']:.1%} · "
            f"tie-break {s['tie_breaks']} ({s['tie_break_frac']:.2%}) · "
            f"M1≠tick {s['m1_disagree_frac']:.2%} (cells {s['m1_cells']:,}) · "
            f"bila ticks {s['no_ticks']}"
        )


def horizon_ends(decision_times: pd.Series, horizon_bars: int) -> pd.Series:
    """Mwisho wa horizon kwa kila bar — kwa BARS, si masaa (§5.5).

    `horizon_bars: 24` ni bars 24 za H1. Ijumaa jioni, bars 24 zinavuka
    wikendi: kwa saa 24 za wall-clock tungeishia Jumamosi, soko likiwa
    limefungwa, na label ingesoma "timeout" kwa sababu ya kalenda badala ya
    soko. Bars za mwisho hazina horizon — hazipati label (§5.5: "Label yoyote
    inayohitaji data baada ya `t + H` haipo").
    """
    return decision_times.shift(-horizon_bars)


def build_labels_for_symbol(
    cfg,
    l0_root: Path,
    symbol: str,
    setups: pd.DataFrame,
    on_progress: ProgressFn | None = None,
    provenance: str | None = None,
) -> SymbolLabels:
    """L4 kwa symbol moja: setups + controls, kwa mpangilio wa muda."""
    from .audit import select_partitions

    horizon_bars = int(cfg.get("labels.horizon_bars"))
    sl_grid = [float(x) for x in cfg.get("labels.barrier.sl_atr")]
    tp_grid = [float(x) for x in cfg.get("labels.barrier.tp_atr")]
    pip = _pip(symbol)
    m1_frac = float(cfg.get("labels.m1_check_frac"))
    m1_seed = int(cfg.get("labels.m1_check_seed"))

    frame = setups.sort_index(kind="stable").copy()
    frame["horizon_end"] = horizon_ends(frame["decision_time"], horizon_bars)
    wanted = frame[(frame["is_setup"] | frame["is_control"]) & frame["horizon_end"].notna()]

    paths = select_partitions(cfg, l0_root, [symbol], provenance)
    window = TickWindow(cfg, paths)

    point_rows: list[dict[str, Any]] = []
    cell_rows: list[dict[str, Any]] = []
    no_ticks = 0
    total = len(wanted)
    m1_checked = m1_agree = m1_ambiguous = 0

    for index, (stamp, row) in enumerate(wanted.iterrows(), start=1):
        decision_time = pd.Timestamp(row["decision_time"])
        horizon_end = pd.Timestamp(row["horizon_end"])
        window.seek(decision_time)
        window.ensure(horizon_end)
        window.trim(decision_time)
        stamps, bid, ask = window.arrays()

        result = resolve_arrays(
            stamps, bid, ask, decision_time, horizon_end,
            int(row["direction"]), float(row["atr"]), sl_grid, tp_grid,
        )
        if on_progress and (index % 200 == 0 or index == total):
            on_progress(index, total, f"{symbol} {decision_time:%Y-%m-%d}")
        if result is None:
            no_ticks += 1
            continue

        # M1-dhidi-ya-tick kwa sampuli (§5 hoja ya "bar haisemi ipi ilianza").
        # Sampuli, si zote: gharama ni ya kuhesabu tu, lakini points 52,000 x
        # dakika 1,440 ni kazi ya bure pale 5% inapotoa jibu lile lile.
        m1_disagree_here = None
        if _m1_pick(m1_seed, symbol, decision_time, m1_frac):
            m1 = resolve_m1_arrays(
                stamps, bid, ask, decision_time, horizon_end,
                int(row["direction"]), float(row["atr"]), sl_grid, tp_grid,
            )
            if m1 is not None and len(m1.outcomes) == len(result.cells):
                same = sum(
                    1 for cell, out in zip(result.cells, m1.outcomes) if cell.outcome == out
                )
                m1_checked += len(m1.outcomes)
                m1_agree += same
                m1_ambiguous += int(sum(m1.ambiguous))
                m1_disagree_here = len(m1.outcomes) - same

        spread_entry = (result.entry_trade - result.entry_mid) * 2.0 / pip
        spread_exit = (result.terminal_mid - result.terminal_trade) * 2.0 / pip
        point_rows.append(
            {
                "symbol": symbol,
                "decision_time": result.decision_time,
                "bar_open": stamp,
                "horizon_end": result.horizon_end,
                "direction": result.direction,
                "is_setup": bool(row["is_setup"]),
                "is_control": bool(row["is_control"]),
                "entry_trade": result.entry_trade,
                "entry_mid": result.entry_mid,
                "atr_price": result.atr_price,
                "atr_pips": result.atr_price / pip,
                "terminal_mid": result.terminal_mid,
                "terminal_trade": result.terminal_trade,
                # Malighafi ya L-D (§5.4): R_net inahesabiwa na RCE, si hapa.
                "spread_entry_pips": abs(spread_entry),
                "spread_exit_pips": abs(spread_exit),
                "quantile_y": result.quantile_y,
                "quantile_y_trade": result.quantile_y_trade,
                "terminal_atr": result.terminal_atr,
                "terminal_atr_trade": result.terminal_atr_trade,
                "ticks_seen": result.ticks_seen,
                "m1_disagree": m1_disagree_here,
            }
        )
        for cell in result.cells:
            barrier_price = (
                result.entry_trade - cell.sl_atr * result.atr_price * result.direction
                if cell.outcome == 0
                else result.entry_trade + cell.tp_atr * result.atr_price * result.direction
            )
            cell_rows.append(
                {
                    "symbol": symbol,
                    "decision_time": result.decision_time,
                    "sl_atr": cell.sl_atr,
                    "tp_atr": cell.tp_atr,
                    "outcome": cell.outcome,
                    "tie_break": cell.tie_break,
                    "timeout_return_r": cell.timeout_return_r,
                    # sl kwa pips — RCE inahitaji hii kugeuza cost_pips kuwa R.
                    "sl_pips": cell.sl_atr * result.atr_price / pip,
                    # L-C (§5.3): umbali bei ilivyopita barrier kabla ya tick
                    # ya kwanza kuionekana — daima ≥ 0 kwa muundo. Ishara
                    # haihifadhiwi hapa kwa makusudi: kwa SL (stop) umbali huu
                    # ni HASARA, kwa TP (limit) ni sifuri kwako (limit inajaza
                    # kwa bei yake). `outcome` iko safu ile ile; R1 inatenganisha.
                    "touch_past_pips": (
                        None
                        if cell.touch_price is None
                        else abs(cell.touch_price - barrier_price) / pip
                    ),
                }
            )

    points = pd.DataFrame(point_rows)
    barriers = pd.DataFrame(cell_rows)
    ties = int(barriers["tie_break"].sum()) if not barriers.empty else 0
    timeouts = int((barriers["outcome"] == 2).sum()) if not barriers.empty else 0
    stats = {
        "symbol": symbol,
        "version": LABEL_BUILD_VERSION,
        "candidates": total,
        "points": len(points),
        "no_ticks": no_ticks,
        "setups": int(points["is_setup"].sum()) if not points.empty else 0,
        "controls": int(points["is_control"].sum()) if not points.empty else 0,
        "cells": len(barriers),
        "timeouts": timeouts,
        "timeout_frac": timeouts / len(barriers) if len(barriers) else 0.0,
        "tie_breaks": ties,
        # §5.2: R1 inaripoti mzunguko wa tie-break; > 1% ya labels → inapanda kwa PD.
        "tie_break_frac": ties / len(barriers) if len(barriers) else 0.0,
        "partitions_read": window.partitions_read,
        "partitions_skipped": window.partitions_skipped,
        # M1-dhidi-ya-tick: cells zilizoangaliwa mara mbili, si points.
        "m1_cells": m1_checked,
        "m1_disagree": m1_checked - m1_agree,
        "m1_disagree_frac": (m1_checked - m1_agree) / m1_checked if m1_checked else 0.0,
        "m1_ambiguous": m1_ambiguous,
        "m1_ambiguous_frac": m1_ambiguous / m1_checked if m1_checked else 0.0,
    }
    return SymbolLabels(symbol=symbol, points=points, barriers=barriers, stats=stats)


def _m1_pick(seed: int, symbol: str, stamp: pd.Timestamp, frac: float) -> bool:
    """Sampuli ya ukaguzi wa M1 — hash, si `random`.

    Sababu ile ile ya control sample (§4.3): point ile ile inaangaliwa kila
    run, kwenye kila mashine. Ukaguzi unaobadilika kila run hauwezi
    kulinganishwa na wa jana.
    """
    import hashlib

    if frac <= 0:
        return False
    if frac >= 1:
        return True
    digest = hashlib.sha256(f"m1|{seed}|{symbol}|{stamp.isoformat()}".encode()).digest()
    return int.from_bytes(digest[:8], "big") / 2**64 < frac


def _pip(symbol: str) -> float:
    from .quality import _pip_size

    return _pip_size(symbol)


# --------------------------------------------------------------------------
# Hali ya kuendelea (kwa symbol/mwaka)
# --------------------------------------------------------------------------


def load_state(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    if int(payload.get("version", 0)) != LABEL_BUILD_VERSION:
        return {}   # muundo umebadilika — kazi ya zamani haiwezi kuchanganywa
    return payload


def save_state(path: Path, done: Iterable[str], config_hash: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "version": LABEL_BUILD_VERSION,
                "config_hash": config_hash,
                "updated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "done": sorted(done),
            },
            indent=2,
        ),
        encoding="utf-8",
    )


def split_by_year(frame: pd.DataFrame) -> dict[int, pd.DataFrame]:
    """Kazi inagawanywa kwa MWAKA: kukatika kunapoteza mwaka, si kila kitu."""
    if frame.empty:
        return {}
    years = frame["decision_time"].dt.year
    return {int(year): frame[years == year] for year in sorted(years.unique())}


def holdout_guard(frame: pd.DataFrame, holdout_start: date) -> pd.DataFrame:
    """G2 — takwimu za holdout ni MARUFUKU kabla ya R8.

    Kuchuja hapa si urembo: `detect-setups` inaweka alama `in_holdout`, lakini
    mjenzi wa labels ndiye anayegusa ticks. Ukaguzi wa pili kwenye mpaka
    wenyewe ndio unaozuia kosa la mkono lisifike kwenye data.
    """
    if frame.empty:
        return frame
    return frame[frame["decision_time"].dt.date < holdout_start]
