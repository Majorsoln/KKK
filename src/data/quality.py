"""Ukaguzi wa ubora wa ticks — DOCTRINE §4.3, R1.

Inaendeshwa **kila upakiaji**, si mara moja. Sababu: dataset inaweza kubadilika
kati ya run mbili (partition mpya, backfill, chanzo kilichorekebishwa), na
ukaguzi uliofanywa mwaka jana hauthibitishi kitu kuhusu faili la leo.

Kila ukaguzi una **daraja**:

* `FATAL` — data haiwezi kutumika. Kila namba inayofuata ingekuwa ya uongo, na
  **haitajionyesha kama kosa — itajionyesha kama faida.**
* `WARN`  — inatiliwa shaka, inaripotiwa, haisimamishi.

Hakuna ukaguzi unaokaa kimya. R23.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .window import Stage

FATAL = "FATAL"
WARN = "WARN"


@dataclass(frozen=True)
class Check:
    name: str
    passed: bool
    severity: str
    detail: str
    count: int = 0

    def to_json(self) -> dict[str, Any]:
        return {
            "check": self.name, "passed": self.passed, "severity": self.severity,
            "detail": self.detail, "count": self.count,
        }


@dataclass
class QualityReport:
    symbol: str
    stage: Stage
    n_ticks: int
    checks: list[Check] = field(default_factory=list)

    @property
    def fatal(self) -> list[Check]:
        return [c for c in self.checks if not c.passed and c.severity == FATAL]

    @property
    def warnings(self) -> list[Check]:
        return [c for c in self.checks if not c.passed and c.severity == WARN]

    @property
    def passed(self) -> bool:
        """FATAL moja inatosha. Warnings hazizuii, lakini zinaandikwa."""
        return not self.fatal

    def render(self) -> str:
        lines = [
            f"UBORA WA TICKS — {self.symbol} · {self.stage.window.start} → "
            f"{self.stage.window.end} · ticks {self.n_ticks:,}"
        ]
        for c in self.checks:
            mark = "ok  " if c.passed else (
                "FELI" if c.severity == FATAL else "onyo"
            )
            lines.append(f"   [{mark}] {c.name:<22} {c.detail}")
        lines.append(
            f"   HUKUMU: {'IMEPITA' if self.passed else 'IMEFELI'}"
            + (f" · warnings {len(self.warnings)}" if self.warnings else "")
        )
        return "\n".join(lines)

    def to_json(self) -> dict[str, Any]:
        return {
            "symbol": self.symbol, "n_ticks": self.n_ticks,
            "passed": self.passed, **self.stage.to_json(),
            "checks": [c.to_json() for c in self.checks],
        }

    def write(self, path: Path) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(self.to_json(), indent=2) + "\n", encoding="utf-8", newline="\n"
        )
        return path


class QualityError(RuntimeError):
    """FATAL imepatikana na mpigaji simu ameomba kusimamishwa."""


# --------------------------------------------------------------------------
# Ukaguzi wenyewe
# --------------------------------------------------------------------------


def check_ticks(frame, stage: Stage, *, max_spread_pips: float | None = None,
                pip: float | None = None) -> QualityReport:
    """Kagua frame ya ticks (`timestamp`, `bid`, `ask`) — §4.3.

    `frame` inatakiwa iwe **imeshakatwa** kwa `window.clip(frame, stage)`.
    Ukaguzi hauchagui data; unaikagua.
    """
    import numpy as np
    import pandas as pd

    missing = {"timestamp", "bid", "ask"} - set(frame.columns)
    if missing:
        raise QualityError(f"safu hazipo: {sorted(missing)} — §4.1 inadai bid/ask")

    report = QualityReport(
        symbol=str(frame.attrs.get("symbol", "?")), stage=stage, n_ticks=len(frame)
    )
    add = report.checks.append

    if frame.empty:
        add(Check("tupu", False, FATAL, "hakuna tick hata moja ndani ya dirisha"))
        return report

    stamps = frame["timestamp"]
    bid = frame["bid"].to_numpy(dtype=float)
    ask = frame["ask"].to_numpy(dtype=float)

    # ---- timezone: UTC pekee ----
    tz = getattr(stamps.dtype, "tz", None)
    add(Check(
        "timezone", tz is not None and str(tz) in ("UTC", "utc"), FATAL,
        f"tz = {tz}" if tz is not None else
        "timestamps hazina timezone — 'naive' inamaanisha kudhania, si kujua",
    ))

    # ---- mpangilio: hakuna kurudi nyuma ----
    diffs = stamps.diff().dropna()
    backwards = int((diffs < pd.Timedelta(0)).sum())
    add(Check(
        "mpangilio", backwards == 0, FATAL,
        "timestamps zinapanda" if backwards == 0
        else f"ticks {backwards:,} zinarudi nyuma kwa muda",
        backwards,
    ))

    # ---- duplicates: muda ULE ULE na bei ZILE ZILE ----
    dupes = int(frame.duplicated(subset=["timestamp", "bid", "ask"]).sum())
    add(Check(
        "duplicates", dupes == 0, FATAL,
        "hakuna" if dupes == 0 else f"ticks {dupes:,} zinazorudiwa kikamilifu", dupes,
    ))

    # ---- quotes zilizovuka: bid > ask ----
    #
    # Hii ni FATAL kwa sababu ya kiuchumi, si ya kiufundi. `bid > ask` inatoa
    # spread HASI, ambayo inatoa gharama HASI — yaani pesa ya bure kwenye kila
    # trade inayoigusa. Backtest isiyoikagua ingeonyesha faida isiyokuwepo, na
    # ingeonekana kama edge, si kama data mbovu.
    crossed = int(np.sum(bid > ask))
    add(Check(
        "quotes_zilizovuka", crossed == 0, FATAL,
        "bid ≤ ask kila mahali" if crossed == 0
        else f"ticks {crossed:,} zenye bid > ask (spread HASI = pesa ya bure)",
        crossed,
    ))

    # ---- bei zisizo na maana ----
    bad = int(np.sum(~np.isfinite(bid) | ~np.isfinite(ask) | (bid <= 0) | (ask <= 0)))
    add(Check(
        "bei_halali", bad == 0, FATAL,
        "zote ni chanya na zenye ukomo" if bad == 0
        else f"ticks {bad:,} zenye NaN/inf/≤0", bad,
    ))

    # ---- spread kubwa isiyo ya kawaida (WARN) ----
    if max_spread_pips is not None and pip:
        spread_pips = (ask - bid) / pip
        wild = int(np.sum(spread_pips > max_spread_pips))
        add(Check(
            "spread_kubwa", wild == 0, WARN,
            f"zote ≤ {max_spread_pips:g} pips" if wild == 0
            else f"ticks {wild:,} zenye spread > {max_spread_pips:g} pips "
                 f"(p99.9 = {np.percentile(spread_pips, 99.9):.2f})",
            wild,
        ))

    # ---- wikendi: kanuni MOJA kwa pairs zote ----
    #
    # Soko la FX linafungwa Ijumaa jioni na kufunguliwa Jumapili jioni. Ticks
    # za Jumamosi ni dalili ya chanzo kilichochanganya timezone — na timezone
    # iliyochanganyika inahamisha kila bar, si baadhi.
    saturday = int((stamps.dt.dayofweek == 5).sum())
    add(Check(
        "wikendi", saturday == 0, WARN,
        "hakuna tick ya Jumamosi" if saturday == 0
        else f"ticks {saturday:,} za Jumamosi — angalia timezone ya chanzo",
        saturday,
    ))

    # ---- mpaka wa dirisha ----
    #
    # `clip()` inapaswa kuwa imeshafanya hili. Ukaguzi upo kwa sababu R18 ni
    # muhimu mno kuachwa kwa nidhamu ya mpigaji simu pekee.
    nje = int((~stamps.dt.date.map(stage.window.contains)).sum())
    add(Check(
        "mpaka_wa_dirisha", nje == 0, FATAL,
        "ticks zote ziko ndani ya dirisha lililotangazwa" if nje == 0
        else f"ticks {nje:,} ziko NJE ya {stage.window.start}→{stage.window.end}",
        nje,
    ))

    return report


def calendar_gaps(frame, stage: Stage, *, max_gap_hours: float = 60.0) -> Check:
    """Mapengo yanayozidi ukimya wa wikendi — §4.3.

    Wikendi ya kawaida ni ~saa 48–50 za ukimya. Pengo linalozidi hilo si
    wikendi; ni data iliyokosekana, na **haliwezi kudhaniwa**. Ni `WARN` kwa
    sababu likizo halisi zipo; ni `count` kwa sababu idadi ndiyo inayoamua kama
    ni likizo au ni chanzo kilichokatika.
    """
    import pandas as pd

    if len(frame) < 2:
        return Check("mapengo", True, WARN, "ticks chache mno kupima")
    gaps = frame["timestamp"].diff().dropna()
    big = gaps[gaps > pd.Timedelta(hours=max_gap_hours)]
    return Check(
        "mapengo", big.empty, WARN,
        f"hakuna pengo > saa {max_gap_hours:g}" if big.empty
        else f"mapengo {len(big):,} > saa {max_gap_hours:g} "
             f"(kubwa zaidi {big.max().total_seconds() / 3600:.1f}h)",
        len(big),
    )
