"""DF-05 — L1: checks 8 za ubora + `quality_report.json` (spec §3).

Kila partition inapita ukaguzi huu. Ikifeli → **haitumiki kwa training**
(`fail_action: exclude`) na ripoti inaandikwa.

| # | Ukaguzi | FAIL reason |
|---|---|---|
| 1 | coverage | `low_coverage` |
| 2 | monotonicity | `bad_timestamps` |
| 3 | gaps ndani ya session | `intrasession_gap` |
| 4 | OHLC sanity | `ohlc_violation` |
| 5 | quote sanity | `quote_violation` |
| 6 | DST/session | `session_mismatch` |
| 7 | clock drift | `clock_drift` |
| 8 | flat bars | `stale_feed` |

**Ukaguzi wa 4 (OHLC) unafanyika L2, si hapa.** L0 ni ticks (uamuzi wa PD
2026-08-04); ticks hazina OHLC. Bars zinapojengwa (L2) ndipo `low ≤ min(open,
close) ≤ max(open, close) ≤ high` inakuwa na maana, na hapo ndipo inakaguliwa
(`bars.py`). Ripoti inaonyesha wazi ukaguzi upi ulifanyika tabaka lipi.

**Sera ya NaN (§3):** hakuna imputation ya kubuni. Tick isiyokamilika inabeba
`is_valid=false`; haifutwi kimya.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

# Sababu za FAIL — majina yale yale ya spec §3.
FAIL_LOW_COVERAGE = "low_coverage"
FAIL_BAD_TIMESTAMPS = "bad_timestamps"
FAIL_INTRASESSION_GAP = "intrasession_gap"
FAIL_OHLC = "ohlc_violation"
FAIL_QUOTE = "quote_violation"
FAIL_SESSION_MISMATCH = "session_mismatch"
FAIL_CLOCK_DRIFT = "clock_drift"
FAIL_STALE_FEED = "stale_feed"


@dataclass
class CheckResult:
    """Ukaguzi mmoja: umepita au la, na **namba** iliyosababisha."""

    name: str
    passed: bool
    reason: str = ""
    value: float | None = None
    threshold: float | None = None
    detail: str = ""

    def to_json(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class PartitionQuality:
    """Matokeo ya partition moja — checks zote, si ile ya kwanza iliyofeli."""

    partition: str
    symbol: str | None
    provenance: str
    rows: int = 0
    checks: list[CheckResult] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return all(c.passed for c in self.checks)

    @property
    def fail_reasons(self) -> list[str]:
        return [c.reason for c in self.checks if not c.passed and c.reason]

    def to_json(self) -> dict[str, Any]:
        return {
            "partition": self.partition,
            "symbol": self.symbol,
            "provenance": self.provenance,
            "rows": self.rows,
            "passed": self.passed,
            "fail_reasons": self.fail_reasons,
            "checks": [c.to_json() for c in self.checks],
        }


# --------------------------------------------------------------------------
# Checks (kila moja ni function huru — inajaribika peke yake)
# --------------------------------------------------------------------------


def check_coverage(rows: int, expected_rows: int, min_coverage: float) -> CheckResult:
    """1 — vipande vilivyopo ÷ vinavyotarajiwa (kalenda ya session, si dhana).

    Spec §3 inasema "**bars** zilizopo ÷ bars zinazotarajiwa". Kwenye tabaka la
    ticks kipimo kinacholingana ni **dakika zenye quote** dhidi ya median ya
    dakika za siku kamili za mwezi ule (`SessionCalendar.expected_minutes`).
    Kuhesabu ticks badala ya dakika kungefanya kizingiti kisiwe na maana: idadi
    ya ticks kwa siku inatofautiana mara mbili-tatu kwa kawaida kabisa, wakati
    dakika zenye quote ni thabiti — na pengo la saa mbili linaonekana mara moja.
    """
    if expected_rows <= 0:
        return CheckResult(
            name="coverage",
            passed=True,
            detail="hakuna matarajio ya kalenda kwa siku hii — haijahukumiwa",
        )
    ratio = rows / expected_rows
    return CheckResult(
        name="coverage",
        passed=ratio >= min_coverage,
        reason="" if ratio >= min_coverage else FAIL_LOW_COVERAGE,
        value=round(ratio, 6),
        threshold=min_coverage,
    )


def check_monotonicity(frame: pd.DataFrame) -> CheckResult:
    """2 — timestamps zinapanda, hakuna duplicate."""
    ts = frame["timestamp"]
    non_monotonic = int((ts.diff() < pd.Timedelta(0)).sum())
    duplicates = int(ts.duplicated().sum())
    passed = non_monotonic == 0 and duplicates == 0
    return CheckResult(
        name="monotonicity",
        passed=passed,
        reason="" if passed else FAIL_BAD_TIMESTAMPS,
        value=float(non_monotonic + duplicates),
        threshold=0.0,
        detail=f"zilizorudi nyuma={non_monotonic} duplicates={duplicates}",
    )


def check_gaps(frame: pd.DataFrame, max_gap_seconds: float) -> CheckResult:
    """3 — pengo kubwa zaidi **ndani ya session** (si wikendi/rollover)."""
    if len(frame) < 2:
        return CheckResult(name="gaps", passed=True, detail="ticks chache mno kupima")
    gaps = frame["timestamp"].diff().dt.total_seconds().dropna()
    largest = float(gaps.max()) if len(gaps) else 0.0
    passed = largest <= max_gap_seconds
    return CheckResult(
        name="gaps",
        passed=passed,
        reason="" if passed else FAIL_INTRASESSION_GAP,
        value=round(largest, 3),
        threshold=max_gap_seconds,
        detail=f"pengo kubwa zaidi = {largest / 60:.1f} min",
    )


def check_quote_sanity(frame: pd.DataFrame, max_spread_pips: float, pip: float) -> CheckResult:
    """5 — `bid < ask`, `spread > 0`, `spread ≤ max_plausible`."""
    bid, ask = frame["bid"], frame["ask"]
    crossed = int((bid >= ask).sum())
    spread_pips = (ask - bid) / pip
    too_wide = int((spread_pips > max_spread_pips).sum())
    non_positive = int((bid <= 0).sum() + (ask <= 0).sum())
    bad = crossed + too_wide + non_positive
    return CheckResult(
        name="quote_sanity",
        passed=bad == 0,
        reason="" if bad == 0 else FAIL_QUOTE,
        value=float(bad),
        threshold=0.0,
        detail=(
            f"crossed={crossed} spread>{max_spread_pips}pips={too_wide} "
            f"bei<=0={non_positive}"
        ),
    )


def check_session_match(
    frame: pd.DataFrame,
    expected_open: datetime | None,
    expected_close: datetime | None,
    tolerance_minutes: float,
    hour_step_ok: bool = False,
) -> CheckResult:
    """6 — mipaka ya session inalingana na kalenda (DST inanaswa hapa).

    `hour_step_ok`: hatua ya **saa moja kamili** ni mabadiliko ya DST, si data
    mbovu. Soko linahamia saa moja mara mbili kwa mwaka; kuziita siku hizo
    `session_mismatch` kungetupa siku 24 nzuri kila mwaka bila sababu (§3:
    "weekend, holiday na rollover si gaps — ni kalenda"). Zinaripotiwa kwenye
    `detail` ili DST ilinganishwe na kalenda ya broker, lakini haziondolewi.
    """
    if expected_open is None or expected_close is None:
        return CheckResult(
            name="session_match", passed=True, detail="kalenda haina siku hii — haijahukumiwa"
        )
    first = frame["timestamp"].min().to_pydatetime()
    last = frame["timestamp"].max().to_pydatetime()
    drift_open = abs((first - expected_open).total_seconds()) / 60.0
    drift_close = abs((last - expected_close).total_seconds()) / 60.0
    worst = max(drift_open, drift_close)

    dst_step = hour_step_ok and abs(worst - 60.0) <= tolerance_minutes
    passed = worst <= tolerance_minutes or dst_step
    detail = f"open ±{drift_open:.1f} min · close ±{drift_close:.1f} min"
    if dst_step:
        detail += " — hatua ya saa 1 (DST), si hitilafu"
    return CheckResult(
        name="session_match",
        passed=passed,
        reason="" if passed else FAIL_SESSION_MISMATCH,
        value=round(worst, 2),
        threshold=tolerance_minutes,
        detail=detail,
    )


def check_clock_drift(frame: pd.DataFrame, max_future_seconds: float = 60.0) -> CheckResult:
    """7 — hakuna tick ya baadaye; tz ni UTC (tofauti ya server↔UTC ni thabiti)."""
    ts = frame["timestamp"]
    tz = getattr(ts.dtype, "tz", None)
    if tz is None or str(tz) != "UTC":
        return CheckResult(
            name="clock_drift",
            passed=False,
            reason=FAIL_CLOCK_DRIFT,
            detail=f"timestamp si UTC (tz={tz})",
        )
    now = pd.Timestamp.now(tz="UTC")
    future = float((ts.max() - now).total_seconds())
    passed = future <= max_future_seconds
    return CheckResult(
        name="clock_drift",
        passed=passed,
        reason="" if passed else FAIL_CLOCK_DRIFT,
        value=round(future, 2),
        threshold=max_future_seconds,
        detail="tick ya baadaye ni dalili ya saa ya server kupotoka",
    )


def check_stale_feed(frame: pd.DataFrame, max_stale_seconds: float) -> CheckResult:
    """8 — feed iliyoganda, ikipimwa kwa **MUDA**, si kwa idadi ya ticks.

    Spec §3 inasema "mfululizo wa **bars** zenye `high==low`" — kipimo cha bars,
    kinachofanyika L2 (`bars.check_flat_bars`), sawa na ukaguzi wa 4. Kwenye
    ticks, kuhesabu mfululizo wa ticks ni kipimo kisicho na maana: dakika moja
    tulivu ya Asia inaweza kuwa na ticks 40 zenye quote ile ile, na hiyo si feed
    iliyoganda — ni soko tulivu.

    Kinachomaanisha kitu ni **muda**: quote ile ile kwa nusu saa wakati session
    iko wazi ni feed iliyoganda, iwe imeleta ticks 5 au 5,000.
    """
    if len(frame) < 2:
        return CheckResult(name="stale_feed", passed=True, detail="ticks chache mno kupima")
    changed = (frame["bid"].diff() != 0) | (frame["ask"].diff() != 0)
    # Nyakati za mabadiliko + tick ya mwisho: mkia wa siku nao ni ukimya.
    marks = pd.concat([frame.loc[changed, "timestamp"], frame["timestamp"].iloc[-1:]])
    longest = float(marks.diff().max().total_seconds()) if len(marks) > 1 else 0.0
    passed = longest <= max_stale_seconds
    return CheckResult(
        name="stale_feed",
        passed=passed,
        reason="" if passed else FAIL_STALE_FEED,
        value=round(longest, 1),
        threshold=float(max_stale_seconds),
        detail=f"quote ile ile kwa dakika {longest / 60:.1f}",
    )


# --------------------------------------------------------------------------
# Kuendesha checks kwa partition
# --------------------------------------------------------------------------


def check_partition(
    path: Path,
    cfg,
    calendar=None,
    expected_minutes: int | None = None,
) -> PartitionQuality:
    """Checks zote za L1 kwa partition moja (spec §3).

    Partition inayovuka siku nyingi inahukumiwa kwa **siku mbaya zaidi** kwenye
    coverage: siku moja iliyokatika ndani ya mwezi haipaswi kufichwa na wastani
    wa mwezi mzima.
    """
    from .manifest import provenance_from_path, symbol_from_path
    from .schema import read_quotes

    path = Path(path)
    symbol = symbol_from_path(path, cfg)
    provenance = provenance_from_path(path, cfg)
    frame = read_quotes(path, cfg)

    result = PartitionQuality(
        partition=str(path),
        symbol=symbol,
        provenance=provenance,
        rows=int(len(frame)),
    )
    if frame.empty:
        result.checks.append(
            CheckResult(
                name="coverage",
                passed=False,
                reason=FAIL_LOW_COVERAGE,
                value=0.0,
                detail="partition haina ticks",
            )
        )
        return result

    max_spread = _max_plausible_spread(cfg, symbol)
    pip = _pip_size(symbol)
    max_gap = float(cfg.get("quality.max_gap_seconds", 3600))
    tolerance = float(cfg.get("quality.session_tolerance_minutes", 15))
    min_coverage = float(cfg.get("quality.min_coverage", 0.995))

    def _coverage(day, group: pd.DataFrame) -> CheckResult:
        expected = int(
            expected_minutes
            if expected_minutes is not None
            else (calendar.expected_minutes(symbol, day) if calendar is not None else 0)
        )
        observed = int(group["timestamp"].dt.floor("min").nunique())
        check = check_coverage(observed, expected, min_coverage)
        if expected > 0:
            check.detail = f"{day}: dakika {observed}/{expected}"
        return check

    def _session(day, group: pd.DataFrame) -> CheckResult:
        bounds = calendar.expected_session(symbol, day) if calendar is not None else None
        check = check_session_match(
            group,
            bounds[0] if bounds else None,
            bounds[1] if bounds else None,
            tolerance,
            hour_step_ok=True,  # DST ni kalenda, si data mbovu (§3)
        )
        if bounds:
            check.detail = f"{day}: {check.detail}"
        return check

    result.checks = [
        _worst_by_day(frame, _coverage),
        check_monotonicity(frame),
        _worst_by_day(frame, lambda day, group: check_gaps(group, max_gap)),
        check_quote_sanity(frame, max_spread, pip),
        _worst_by_day(frame, _session),
        check_clock_drift(frame),
        _worst_by_day(
            frame,
            lambda day, group: check_stale_feed(
                group, float(cfg.get("quality.max_stale_seconds", 1800))
            ),
        ),
    ]
    return result


def _worst_by_day(frame: pd.DataFrame, check) -> CheckResult:
    """Endesha ukaguzi kwa **kila siku** ndani ya partition, rudisha mbaya zaidi.

    Partition ya mwezi (Toleo B) ina siku ~22. Kuikagua kama kipande kimoja
    kungetoa majibu mawili ya uwongo: pengo la usiku kati ya sessions
    lingehesabiwa kama `intrasession_gap`, na mipaka ya session ingelinganishwa
    na siku ya kwanza pekee. Weekend/rollover si gaps — ni kalenda (§3).
    """
    results = [check(day, group) for day, group in frame.groupby(frame["timestamp"].dt.date)]
    if not results:
        return CheckResult(name="?", passed=True, detail="hakuna siku ya kupima")
    failed = [r for r in results if not r.passed]
    if failed:
        # Mbaya zaidi = thamani mbali zaidi na kizingiti; sifuri isipopimika.
        return max(failed, key=lambda r: abs(r.value if r.value is not None else 0.0))
    return results[0]


def _max_plausible_spread(cfg, symbol: str | None) -> float:
    limits = cfg.get("quality.max_plausible_spread_pips", {}) or {}
    if symbol and symbol in limits:
        return float(limits[symbol])
    return float(limits.get("default", 50.0))


def _pip_size(symbol: str | None) -> float:
    if not symbol:
        return 0.0001
    upper = symbol.upper()
    if upper.startswith(("XAU", "XAG")) or upper[3:6] == "JPY":
        return 0.01
    return 0.0001


# --------------------------------------------------------------------------
# Ripoti
# --------------------------------------------------------------------------


@dataclass
class QualityReport:
    """`quality_report.json` — deliverable ya R0 (spec §3, RS-03)."""

    partitions: list[PartitionQuality] = field(default_factory=list)
    built_at: str = ""
    config_hash: str = ""
    thresholds: dict[str, Any] = field(default_factory=dict)
    calendar_comparison: dict[str, Any] = field(default_factory=dict)

    @property
    def passed(self) -> list[PartitionQuality]:
        return [p for p in self.partitions if p.passed]

    @property
    def failed(self) -> list[PartitionQuality]:
        return [p for p in self.partitions if not p.passed]

    def by_symbol_year(self) -> dict[str, dict[str, int]]:
        """Muhtasari kwa symbol/mwaka — ndivyo R0 inavyoulizwa (§R0)."""
        summary: dict[str, dict[str, int]] = {}
        for part in self.partitions:
            year = _year_of(part.partition)
            key = f"{part.symbol}/{year}"
            slot = summary.setdefault(key, {"passed": 0, "failed": 0, "rows": 0})
            slot["passed" if part.passed else "failed"] += 1
            slot["rows"] += part.rows
        return dict(sorted(summary.items()))

    def reason_counts(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for part in self.failed:
            for reason in part.fail_reasons:
                counts[reason] = counts.get(reason, 0) + 1
        return dict(sorted(counts.items(), key=lambda kv: -kv[1]))

    def to_json(self) -> dict[str, Any]:
        return {
            "built_at": self.built_at,
            "config_hash": self.config_hash,
            "thresholds": self.thresholds,
            "totals": {
                "partitions": len(self.partitions),
                "passed": len(self.passed),
                "failed": len(self.failed),
            },
            "fail_reasons": self.reason_counts(),
            "by_symbol_year": self.by_symbol_year(),
            "calendar_comparison": self.calendar_comparison,
            "partitions": [p.to_json() for p in self.partitions],
        }

    def save(self, path: Path) -> Path:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_json(), indent=2) + "\n", encoding="utf-8")
        return path

    def render(self) -> str:
        lines = [
            f"L1 quality: partitions={len(self.partitions)} "
            f"passed={len(self.passed)} failed={len(self.failed)}"
        ]
        for reason, count in self.reason_counts().items():
            lines.append(f"  ! {reason}: {count}")
        return "\n".join(lines)


def _year_of(partition: str) -> str:
    """Mwaka wa partition kutoka kwenye njia — miundo yote inayotumika L0.

    Data halisi ina `.../symbol=EURUSD/2026/2026-08-03.parquet` (folda ya mwaka
    si Hive). Kudai `year=` pekee kungefanya ripoti nzima ya R0 iwe `symbol/?`.
    """
    path = Path(partition)
    for part in path.parts:
        if part.startswith("year="):
            return part.split("=", 1)[1]
        if part.startswith("date="):
            return part.split("=", 1)[1][:4]
        if len(part) == 4 and part.isdigit():
            return part
    stem = path.stem
    if len(stem) >= 4 and stem[:4].isdigit():
        return stem[:4]
    return "?"


# --------------------------------------------------------------------------
# Kupanga vizingiti KWA DATA (si kwa kubuni)
# --------------------------------------------------------------------------

# Upande unaofelisha kwa kila ukaguzi: `min` = thamani ndogo ni mbaya
# (coverage); `max` = thamani kubwa ni mbaya (kila kingine).
CHECK_DIRECTION: dict[str, str] = {
    "coverage": "min",
    "monotonicity": "max",
    "gaps": "max",
    "quote_sanity": "max",
    "session_match": "max",
    "clock_drift": "max",
    "stale_feed": "max",
}


def threshold_study(report: dict[str, Any]) -> dict[str, Any]:
    """Mgawanyo wa thamani zilizopimwa + partitions zingefeli kwa kizingiti gani.

    Kizingiti kilichobuniwa mezani ni nadhani; kizingiti kilichotokana na
    mgawanyo wa data ni uamuzi. Kazi hii inasoma `quality_report.json`
    iliyoshaandikwa — **hakuna kusoma parquet tena** — na kuonyesha, kwa kila
    ukaguzi, thamani halisi zilivyotawanyika na ni partitions ngapi zingefeli
    kwa kila kizingiti kinachopendekezwa. PD ndiye anayechagua.
    """
    quantiles = [0.001, 0.01, 0.05, 0.10, 0.50, 0.90, 0.95, 0.99, 0.999]
    values: dict[str, list[float]] = {}
    thresholds: dict[str, float] = {}
    offenders: dict[str, dict[str, int]] = {}

    for part in report.get("partitions", []):
        for check in part.get("checks", []):
            name = check.get("name", "?")
            if check.get("value") is None:
                continue
            values.setdefault(name, []).append(float(check["value"]))
            if check.get("threshold") is not None:
                thresholds[name] = float(check["threshold"])
            if not check.get("passed", True):
                key = f"{part.get('symbol')}/{_year_of(part.get('partition', ''))}"
                offenders.setdefault(name, {})[key] = offenders.setdefault(name, {}).get(key, 0) + 1

    out: dict[str, Any] = {"partitions": len(report.get("partitions", [])), "checks": {}}
    for name, series in sorted(values.items()):
        data = pd.Series(series, dtype="float64")
        direction = CHECK_DIRECTION.get(name, "max")
        current = thresholds.get(name)
        candidates = (
            [round(float(data.quantile(q)), 4) for q in (0.001, 0.01, 0.05, 0.10)]
            if direction == "min"
            else [round(float(data.quantile(q)), 4) for q in (0.90, 0.95, 0.99, 0.999)]
        )
        out["checks"][name] = {
            "direction": direction,
            "measured": len(data),
            "current_threshold": current,
            "would_fail_now": (
                int((data < current).sum())
                if direction == "min" and current is not None
                else int((data > current).sum())
                if current is not None
                else None
            ),
            "quantiles": {f"p{q * 100:g}": round(float(data.quantile(q)), 4) for q in quantiles},
            "min": round(float(data.min()), 4),
            "max": round(float(data.max()), 4),
            "candidates": [
                {
                    "threshold": value,
                    "would_fail": int((data < value).sum())
                    if direction == "min"
                    else int((data > value).sum()),
                }
                for value in sorted(set(candidates))
            ],
            "top_offenders": dict(
                sorted(offenders.get(name, {}).items(), key=lambda kv: -kv[1])[:8]
            ),
        }
    return out


def render_threshold_study(study: dict[str, Any]) -> str:
    lines = [f"partitions zilizopimwa: {study['partitions']}", ""]
    for name, entry in study["checks"].items():
        arrow = "chini ni mbaya" if entry["direction"] == "min" else "juu ni mbaya"
        lines.append(
            f"{name}  ({arrow}) · kizingiti cha sasa = {entry['current_threshold']} "
            f"→ zinafeli {entry['would_fail_now']}/{entry['measured']}"
        )
        q = entry["quantiles"]
        lines.append(
            f"   p1={q['p1']} p5={q['p5']} p10={q['p10']} p50={q['p50']} "
            f"p90={q['p90']} p95={q['p95']} p99={q['p99']}  [min={entry['min']} max={entry['max']}]"
        )
        picks = " · ".join(
            f"{c['threshold']}→{c['would_fail']}" for c in entry["candidates"]
        )
        lines.append(f"   chaguo (kizingiti→zitakazofeli): {picks}")
        if entry["top_offenders"]:
            top = " · ".join(f"{k}={v}" for k, v in entry["top_offenders"].items())
            lines.append(f"   zinazoongoza kufeli: {top}")
        lines.append("")
    return "\n".join(lines)


def new_report(cfg) -> QualityReport:
    return QualityReport(
        built_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        config_hash=getattr(cfg, "config_hash", ""),
        thresholds={
            "min_coverage": cfg.get("quality.min_coverage", 0.995),
            "max_gap_seconds": cfg.get("quality.max_gap_seconds", 3600),
            "max_flat_bars": cfg.get("quality.max_flat_bars", 10),
            "session_tolerance_minutes": cfg.get("quality.session_tolerance_minutes", 15),
            "fail_action": cfg.get("quality.fail_action", "exclude"),
        },
    )
