"""T1 — uendeshaji wa ukaguzi wa R0 juu ya L0 nzima (DF-05, DF-06, RS-03).

Modules za T1 zina **sheria** (kalenda, checks, bars, as-of, sentinel, splits).
Hapa ndipo sheria hizo zinapokutana na partitions 25,000 na ticks bilioni 3.4.
Kwa hiyo mambo matatu ya vitendo yanashughulikiwa hapa, si kwenye sheria:

1. **Gharama ya kusoma.** Kalenda inasoma column ya timestamp PEKEE; L1 pekee
   ndiyo inasoma bid/ask. Kutochanganya haya ni tofauti ya dakika na masaa.
2. **Kuendelea baada ya kukatika.** Kazi ya masaa lazima iweze kusimama na
   kuendelea. Kila hatua ina cache ya JSONL yenye ufunguo wa partition.
3. **Kumbukumbu.** Bars zinajengwa kwa vipande vinavyokatwa kwenye mipaka ya
   SIKU za UTC — TF zote saba zinagawanyika sawasawa hapo, kwa hiyo matokeo ni
   sawa kabisa na kujenga kila kitu kwa mkupuo mmoja.
"""

from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Iterable, Sequence

import pandas as pd

from .manifest import iter_partitions, symbol_from_path
from .quality import QualityReport, _pip_size, check_partition, new_report
from .session_calendar import (
    DayObservation,
    SessionCalendar,
    build_calendar,
    compare_with_assumed,
    observe_timestamps,
)

ProgressFn = Callable[[int, int, str], None]


# --------------------------------------------------------------------------
# Kuchagua partitions
# --------------------------------------------------------------------------


def select_partitions(
    cfg,
    root: Path,
    symbols: Sequence[str] | None = None,
    provenance: str | None = None,
) -> list[Path]:
    """Partitions za L0 zilizochujwa kwa symbol/provenance, kwa mpangilio thabiti."""
    from .manifest import provenance_from_path

    wanted = {s.upper() for s in symbols} if symbols else None
    out: list[Path] = []
    for path in iter_partitions(Path(root)):
        if wanted is not None:
            symbol = symbol_from_path(path, cfg)
            if not symbol or symbol.upper() not in wanted:
                continue
        if provenance and provenance_from_path(path, cfg) != provenance:
            continue
        out.append(path)
    return out


# --------------------------------------------------------------------------
# Cache ya kuendelea (JSONL: mstari mmoja kwa partition)
# --------------------------------------------------------------------------


def _cache_key(path: Path, context: str = "") -> str:
    stat = path.stat()
    key = f"{path}|{stat.st_size}|{int(stat.st_mtime)}"
    # `context` tupu haiongezi kitu — hivyo scan isiyo na muktadha (kalenda)
    # haiharibu cache yake kila mara muundo wa ufunguo unapopanuka.
    return f"{key}|{context}" if context else key


def _judgement_fingerprint(cfg, calendar: SessionCalendar | None, symbol: str | None) -> str:
    """Alama ya **kile kinachohukumu** partition hii: vizingiti + kalenda yake.

    Bila hii, cache ingekuwa hatari: ukikimbiza symbols mbili leo na kumi na mbili
    kesho, kalenda inajengwa upya, lakini matokeo ya L1 ya jana yangetumika tena
    kimya — yakiwa yamehukumiwa kwa kalenda ya zamani. Kubadilisha kizingiti
    chochote cha `config/data.yaml` kunafanya vivyo hivyo.

    Kinachoingia: `config_hash` (vizingiti vyote), matarajio ya **symbol hii**
    (dakika + mipaka ya session kwa mwezi), na siku zisizo `full` (kwa sababu
    `expected_minutes` inarudi 0 kwa hizo, yaani "haijahukumiwa").
    """
    import hashlib

    key = str(symbol or "?").upper()
    payload = {
        "config_hash": getattr(cfg, "config_hash", ""),
        "expect": (calendar.symbol_expect.get(key) if calendar else None),
        "non_full_days": (calendar.partial_days() if calendar else []),
    }
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
    ).hexdigest()[:16]


def _load_cache(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    out: dict[str, Any] = {}
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:  # mstari uliokatika wakati wa kuzimika
                continue
            out[payload["key"]] = payload["value"]
    return out


def _append_cache(path: Path, key: str, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps({"key": key, "value": value}) + "\n")
        handle.flush()


# --------------------------------------------------------------------------
# RS-03 — kalenda kutoka L0
# --------------------------------------------------------------------------


@dataclass
class CalendarBuild:
    calendar: SessionCalendar
    comparison: dict[str, Any]
    partitions: int = 0
    reused: int = 0
    failed: list[dict[str, str]] = field(default_factory=list)
    by_variant: dict[str, Any] = field(default_factory=dict)

    def render(self) -> str:
        cal = self.calendar
        lines = [
            f"kalenda: siku {len(cal.days)} "
            f"(full {len(cal.full_days())} · partial {len(cal.partial_days())}) "
            f"kutoka partitions {self.partitions} (zilizotumika tena: {self.reused})",
            f"  siku tulizodhani zina data lakini hazina : {len(self.comparison['silent_but_expected'])}",
            f"  Jumapili zenye ticks (ufunguzi wa wiki — inatarajiwa): {len(self.comparison['weekend_open'])}",
            f"  Jumamosi/sikukuu zenye ticks (INAHITAJI MAELEZO): {len(self.comparison['unexpected_active'])}",
            f"  siku za nusu (zilizogunduliwa na data): {len(self.comparison['partial_days'])}",
        ]
        for name, entry in sorted(self.by_variant.items()):
            lines.append(
                f"  Toleo {name}: symbols {len(entry['symbols'])} · siku {entry['days']} "
                f"({entry['first_day']} → {entry['last_day']}) · "
                f"session median {entry['session_open']}–{entry['session_close']} UTC"
            )
        for failure in self.failed:
            lines.append(f"  ! {failure['partition']}: {failure['error']}")
        return "\n".join(lines)


def build_session_calendar(
    cfg,
    root: Path,
    symbols: Sequence[str] | None = None,
    cache_path: Path | None = None,
    on_progress: ProgressFn | None = None,
    limit: int | None = None,
) -> CalendarBuild:
    """Kalenda ya sessions kutoka DATA (spec §3), si kutoka orodha ya sikukuu."""
    from .calendar import TradingCalendar

    partitions = select_partitions(cfg, root, symbols)
    if limit:
        partitions = partitions[:limit]
    cache = _load_cache(cache_path) if cache_path else {}

    observations: list[DayObservation] = []
    failed: list[dict[str, str]] = []
    reused = 0
    for index, path in enumerate(partitions, start=1):
        key = _cache_key(path)
        payload = cache.get(key)
        if payload is None:
            try:
                payload = [obs.to_json() for obs in observe_timestamps(path, cfg)]
            except Exception as exc:  # partition moja mbovu haisimamishi ukaguzi
                failed.append({"partition": str(path), "error": f"{type(exc).__name__}: {exc}"})
                if on_progress:
                    on_progress(index, len(partitions), path.name)
                continue
            if cache_path:
                _append_cache(cache_path, key, payload)
        else:
            reused += 1
        observations.extend(DayObservation.from_json(item) for item in payload)
        if on_progress:
            on_progress(index, len(partitions), path.name)

    calendar = build_calendar(
        observations,
        partial_frac=float(cfg.get("quality.partial_day_frac", 0.25)),
        source=str(root),
    )
    return CalendarBuild(
        calendar=calendar,
        comparison=compare_with_assumed(calendar, TradingCalendar()),
        partitions=len(partitions),
        reused=reused,
        failed=failed,
        by_variant=_calendar_by_variant(cfg, calendar),
    )


def _calendar_by_variant(cfg, calendar: SessionCalendar) -> dict[str, Any]:
    """Kalenda ikithibitishwa kwa **kila toleo la schema kando** (R0, kazi ya 2).

    Toleo B linatoka chanzo tofauti (EURCHF/GBPJPY/XAUUSD). Kama mipaka ya
    session au wigo wa siku unatofautiana na Toleo A, hiyo ni dalili ya chanzo
    tofauti — na inagusa kila feature ya symbols hizo. Kalenda ya pamoja
    ingeificha.
    """
    out: dict[str, Any] = {}
    for symbol, rows in calendar.symbol_expect.items():
        variant = cfg.variant_of_symbol(symbol) or "A"
        slot = out.setdefault(
            variant, {"symbols": [], "days": set(), "opens": [], "closes": []}
        )
        slot["symbols"].append(symbol)
        slot["days"].update(rows)
        slot["opens"].extend(v[1] for v in rows.values())
        slot["closes"].extend(v[2] for v in rows.values())

    summary: dict[str, Any] = {}
    for variant, slot in out.items():
        days = sorted(slot["days"])
        summary[variant] = {
            "symbols": sorted(slot["symbols"]),
            "days": len(days),
            "first_day": days[0] if days else None,
            "last_day": days[-1] if days else None,
            "session_open": _hhmm(slot["opens"]),
            "session_close": _hhmm(slot["closes"]),
        }
    return summary


def _hhmm(minutes: list[float]) -> str | None:
    if not minutes:
        return None
    value = float(pd.Series(minutes).median())
    return f"{int(value) // 60:02d}:{int(value) % 60:02d}"


# --------------------------------------------------------------------------
# DF-05 — L1 quality audit
# --------------------------------------------------------------------------


def run_quality_audit(
    cfg,
    root: Path,
    calendar: SessionCalendar | None = None,
    symbols: Sequence[str] | None = None,
    on_progress: ProgressFn | None = None,
    limit: int | None = None,
    cache_path: Path | None = None,
) -> QualityReport:
    """Checks 7 za L1 kwa kila partition (ya 4, OHLC, iko L2 — `bars.py`)."""
    partitions = select_partitions(cfg, root, symbols)
    if limit:
        partitions = partitions[:limit]
    cache = _load_cache(cache_path) if cache_path else {}

    report = new_report(cfg)
    fingerprints: dict[str, str] = {}
    for index, path in enumerate(partitions, start=1):
        symbol = symbol_from_path(path, cfg)
        marker = fingerprints.get(str(symbol))
        if marker is None:
            marker = _judgement_fingerprint(cfg, calendar, symbol)
            fingerprints[str(symbol)] = marker
        key = _cache_key(path, marker)
        payload = cache.get(key)
        if payload is None:
            try:
                payload = check_partition(path, cfg, calendar=calendar).to_json()
            except Exception as exc:
                payload = {
                    "partition": str(path),
                    "symbol": symbol,
                    "provenance": "?",
                    "rows": 0,
                    "passed": False,
                    "fail_reasons": ["unreadable"],
                    "checks": [
                        {
                            "name": "read",
                            "passed": False,
                            "reason": "unreadable",
                            "detail": f"{type(exc).__name__}: {exc}",
                        }
                    ],
                }
            if cache_path:
                _append_cache(cache_path, key, payload)
        report.partitions.append(_quality_from_json(payload))
        if on_progress:
            on_progress(index, len(partitions), path.name)

    if calendar is not None:
        from .calendar import TradingCalendar

        report.calendar_comparison = compare_with_assumed(calendar, TradingCalendar())
    report.coverage_by_symbol = _coverage_by_symbol(cfg, report, calendar)
    return report


def _coverage_by_symbol(cfg, report: QualityReport, calendar: SessionCalendar | None):
    """Muhtasari wa R0 kwa symbol: miaka, siku, na sehemu iliyopita — dhidi ya `min_years`."""
    min_years = float(cfg.get("source.min_years", 0) or 0)
    days_by_symbol: dict[str, list[str]] = defaultdict(list)
    if calendar is not None:
        for symbol, rows in calendar.symbol_expect.items():
            days_by_symbol[symbol] = sorted(rows)

    out: dict[str, Any] = {}
    for symbol in sorted({str(p.symbol) for p in report.partitions if p.symbol}):
        parts = [p for p in report.partitions if p.symbol == symbol]
        days = days_by_symbol.get(symbol.upper(), [])
        years = (
            (date.fromisoformat(days[-1]) - date.fromisoformat(days[0])).days / 365.25
            if len(days) > 1
            else 0.0
        )
        out[symbol] = {
            "partitions": len(parts),
            "passed": sum(1 for p in parts if p.passed),
            "pass_rate": round(sum(1 for p in parts if p.passed) / len(parts), 4) if parts else 0.0,
            "trading_days": len(days),
            "first_day": days[0] if days else None,
            "last_day": days[-1] if days else None,
            "years": round(years, 2),
            "min_years": min_years,
            "meets_min_years": years >= min_years if min_years else None,
        }
    return out


def _quality_from_json(payload: dict[str, Any]):
    from .quality import CheckResult, PartitionQuality

    return PartitionQuality(
        partition=payload["partition"],
        symbol=payload.get("symbol"),
        provenance=payload.get("provenance", ""),
        rows=int(payload.get("rows", 0)),
        checks=[
            CheckResult(
                name=item.get("name", "?"),
                passed=bool(item.get("passed")),
                reason=item.get("reason", ""),
                value=item.get("value"),
                threshold=item.get("threshold"),
                detail=item.get("detail", ""),
            )
            for item in payload.get("checks", [])
        ],
    )


# --------------------------------------------------------------------------
# RS-03 — ulinganisho wa Toleo A ↔ Toleo B (spec §2.1)
# --------------------------------------------------------------------------


def compare_variants(cfg, root: Path, calendar: SessionCalendar | None = None) -> dict[str, Any]:
    """Toleo A dhidi ya Toleo B baada ya normalization (spec §2.1).

    Swali si "je, columns zina majina tofauti" — hilo tunalijua. Swali ni: je,
    baada ya normalization, **data yenyewe inalingana**? Toleo B lina precision
    ya ms na A ina µs; kama B ina dakika chache zenye quote au spread pana zaidi
    kwa utaratibu, hiyo si tofauti ya schema — ni tofauti ya feed, na inagusa
    kila feature inayotumia symbols hizo.
    """
    from .schema import read_partition, variant_specs

    specs = variant_specs(cfg)
    partitions = select_partitions(cfg, root)
    by_variant: dict[str, list[Path]] = defaultdict(list)
    symbol_variant: dict[str, str] = {}
    for path in partitions:
        symbol = symbol_from_path(path, cfg)
        if not symbol:
            continue
        variant = cfg.variant_of_symbol(symbol) or "A"
        symbol_variant[symbol.upper()] = variant
        by_variant[variant].append(path)

    summary: dict[str, Any] = {
        "built_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "config_hash": getattr(cfg, "config_hash", ""),
        "variants": {},
        "canonical_schema_identical": True,
    }
    canonical: dict[str, list[str]] = {}

    for name, spec in specs.items():
        paths = by_variant.get(name, [])
        symbols = sorted(s for s, v in symbol_variant.items() if v == name)
        entry: dict[str, Any] = {
            "declared_columns": list(spec.columns),
            "precision": spec.precision,
            "symbols": symbols,
            "partitions": len(paths),
        }
        if paths:
            sample = paths[len(paths) // 2]
            frame = read_partition(sample, cfg)
            canonical[name] = list(frame.columns)
            entry["sample_partition"] = str(sample)
            entry["sample_symbol"] = symbol_from_path(sample, cfg)
            entry["canonical_columns"] = list(frame.columns)
            entry["timestamp_dtype"] = str(frame["timestamp"].dtype)
            if not frame.empty:
                spread_pips = (frame["ask"] - frame["bid"]) / _pip_size(
                    symbol_from_path(sample, cfg)
                )
                entry["sample_stats"] = {
                    "rows": int(len(frame)),
                    "minutes_with_quotes": int(frame["timestamp"].dt.floor("min").nunique()),
                    "spread_p50_pips": round(float(spread_pips.median()), 4),
                    "spread_p95_pips": round(float(spread_pips.quantile(0.95)), 4),
                    "first_ts": frame["timestamp"].min().isoformat(),
                    "last_ts": frame["timestamp"].max().isoformat(),
                }
        summary["variants"][name] = entry

    values = [tuple(v) for v in canonical.values()]
    summary["canonical_schema_identical"] = len(set(values)) <= 1
    if calendar is not None:
        summary["median_minutes_by_symbol"] = {
            symbol: round(
                float(pd.Series([v[0] for v in rows.values()]).median()) if rows else 0.0, 1
            )
            for symbol, rows in sorted(calendar.symbol_expect.items())
        }
    return summary


# --------------------------------------------------------------------------
# R0 — ULINGANISHO AGGREGATOR ↔ BROKER (spec §2.2 sharti 2)
# --------------------------------------------------------------------------


def compare_provenance(
    cfg,
    root: Path,
    symbols: Sequence[str] | None = None,
    on_progress: ProgressFn | None = None,
) -> dict[str, Any]:
    """Chanzo cha kihistoria dhidi ya feed ya broker kwa siku ZINAZOPISHANA.

    Hili ndilo swali linalofungua au kufunga attestation nzima ya gharama: models
    zinafunzwa kwa data ya aggregator, lakini zitafanya biashara kwa feed ya
    broker. **Spread ndiyo gharama** (§3.1 ya RCE). Kama spread ya broker ni
    pana kwa utaratibu kuliko ya aggregator, kila EV iliyohesabiwa kwa data ya
    kihistoria ni ya matumaini — na kiasi cha upendeleo ndicho tunachopima hapa.

    Siku zinazopishana ndizo pekee zinazoruhusu ulinganisho wa haki: siku ile
    ile, symbol ile ile, soko lile lile. Ukilinganisha vipindi tofauti,
    unapima soko lililobadilika, si feed.
    """
    from .quality import _pip_size
    from .schema import read_quotes

    by_key: dict[tuple[str, str, date], list[Path]] = defaultdict(list)
    for provenance in ("aggregator", "broker"):
        for path in select_partitions(cfg, root, symbols, provenance=provenance):
            symbol = symbol_from_path(path, cfg)
            if not symbol:
                continue
            for day in _days_of_partition(cfg, path):
                by_key[(provenance, symbol.upper(), day)].append(path)

    overlap = sorted(
        {
            (symbol, day)
            for (provenance, symbol, day) in by_key
            if provenance == "aggregator" and ("broker", symbol, day) in by_key
        }
    )

    rows: list[dict[str, Any]] = []
    for index, (symbol, day) in enumerate(overlap, start=1):
        pip = _pip_size(symbol)
        stats: dict[str, dict[str, float]] = {}
        for provenance in ("aggregator", "broker"):
            frames = [read_quotes(p, cfg) for p in by_key[(provenance, symbol, day)]]
            frame = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
            if not frame.empty:
                frame = frame[frame["timestamp"].dt.date == day]
            if frame.empty:
                continue
            spread = (frame["ask"] - frame["bid"]) / pip
            stats[provenance] = {
                "ticks": int(len(frame)),
                "minutes": int(frame["timestamp"].dt.floor("min").nunique()),
                "spread_p50": round(float(spread.median()), 4),
                "spread_p95": round(float(spread.quantile(0.95)), 4),
                "spread_mean": round(float(spread.mean()), 4),
            }
        if len(stats) == 2:
            agg, brk = stats["aggregator"], stats["broker"]
            rows.append(
                {
                    "symbol": symbol,
                    "day": day.isoformat(),
                    "aggregator": agg,
                    "broker": brk,
                    "spread_p50_diff_pips": round(brk["spread_p50"] - agg["spread_p50"], 4),
                    "spread_p50_ratio": round(
                        brk["spread_p50"] / agg["spread_p50"], 4
                    )
                    if agg["spread_p50"]
                    else None,
                    "tick_ratio": round(brk["ticks"] / agg["ticks"], 4) if agg["ticks"] else None,
                }
            )
        if on_progress:
            on_progress(index, len(overlap), f"{symbol} {day}")

    ratios = [r["spread_p50_ratio"] for r in rows if r["spread_p50_ratio"]]
    return {
        "built_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "config_hash": getattr(cfg, "config_hash", ""),
        "overlap_days": sorted({r["day"] for r in rows}),
        "symbols": sorted({r["symbol"] for r in rows}),
        "comparisons": len(rows),
        "spread_p50_ratio": {
            "median": round(float(pd.Series(ratios).median()), 4) if ratios else None,
            "min": round(min(ratios), 4) if ratios else None,
            "max": round(max(ratios), 4) if ratios else None,
        },
        "rows": rows,
    }


def _days_of_partition(cfg, path: Path) -> list[date]:
    """Siku zilizomo kwenye partition — kutoka footer, bila kusoma ticks."""
    from .schema import partition_metadata

    try:
        meta = partition_metadata(path, cfg)
    except Exception:
        return []
    if not meta.get("first_ts") or not meta.get("last_ts"):
        return []
    first = pd.Timestamp(meta["first_ts"]).date()
    last = pd.Timestamp(meta["last_ts"]).date()
    return [first + timedelta(days=i) for i in range((last - first).days + 1)]


# --------------------------------------------------------------------------
# DF-06 — L2 bars kutoka L0 nzima
# --------------------------------------------------------------------------


@dataclass
class BarsBuild:
    symbol: str
    rows: dict[str, int] = field(default_factory=dict)
    ohlc_violations: dict[str, int] = field(default_factory=dict)
    longest_flat: dict[str, int] = field(default_factory=dict)
    bar_gaps: dict[str, int] = field(default_factory=dict)
    span: tuple[str, str] | None = None
    years: float = 0.0
    ticks: int = 0
    chunks: int = 0

    @property
    def ok(self) -> bool:
        return not any(self.ohlc_violations.values())

    @property
    def flat_offenders(self) -> dict[str, int]:
        """TF zenye mfululizo wa bars `high == low` unaozidi kizingiti (§3 check 8)."""
        return {tf: value for tf, value in self.longest_flat.items() if value}

    @property
    def gap_offenders(self) -> dict[str, int]:
        return {tf: value for tf, value in self.bar_gaps.items() if value}

    def to_json(self) -> dict[str, Any]:
        return {
            "symbol": self.symbol,
            "ticks": self.ticks,
            "chunks": self.chunks,
            "span": list(self.span) if self.span else None,
            "years": round(self.years, 2),
            "rows": self.rows,
            "ohlc_violations": self.ohlc_violations,
            "longest_flat": self.longest_flat,
            "bar_gaps": self.bar_gaps,
        }

    def render(self) -> str:
        bars = " · ".join(f"{tf}={rows}" for tf, rows in self.rows.items())
        status = "" if self.ok else f"  ! OHLC: {self.ohlc_violations}"
        if self.flat_offenders:
            status += f"  ! bars tulivu mfululizo: {self.flat_offenders}"
        if self.gap_offenders:
            status += f"  ! mapengo ya bars: {self.gap_offenders}"
        return (
            f"{self.symbol}: ticks={self.ticks:,} miaka={self.years:.1f} "
            f"vipande={self.chunks} | {bars}{status}"
        )


def _day_chunks(
    cfg, paths: Sequence[Path], max_rows: int
) -> list[list[Path]]:
    """Vipande vinavyokatwa kwenye mipaka ya SIKU za UTC pekee.

    Sababu: TF zote saba (M5…D1) zinagawanyika sawasawa kwenye mpaka wa siku.
    Kukata mahali pengine kungetengeneza bar mbili nusu badala ya bar moja.
    """
    from .schema import partition_metadata

    spans: list[tuple[Path, date | None, date | None, int]] = []
    for path in paths:
        try:
            meta = partition_metadata(path, cfg)
            first = pd.Timestamp(meta["first_ts"]).date() if meta["first_ts"] else None
            last = pd.Timestamp(meta["last_ts"]).date() if meta["last_ts"] else None
            spans.append((path, first, last, int(meta["rows"])))
        except Exception:
            spans.append((path, None, None, 0))
    spans.sort(key=lambda item: (item[1] or date.min, str(item[0])))

    chunks: list[list[Path]] = []
    current: list[Path] = []
    rows = 0
    previous_last: date | None = None
    for path, first, last, count in spans:
        starts_new_day = first is None or previous_last is None or first > previous_last
        if current and rows >= max_rows and starts_new_day:
            chunks.append(current)
            current, rows = [], 0
        current.append(path)
        rows += count
        previous_last = last if last is not None else previous_last
    if current:
        chunks.append(current)
    return chunks


def build_l2_for_symbol(
    cfg,
    symbol: str,
    l0_root: Path,
    l2_root: Path,
    timeframes: Sequence[str],
    max_rows_per_chunk: int = 5_000_000,
    on_progress: ProgressFn | None = None,
) -> BarsBuild:
    """Bars za TF zote kwa symbol moja, kwa vipande, kisha kuandikwa L2."""
    from .bars import (
        build_all_timeframes,
        check_bar_gaps,
        check_flat_bars,
        check_ohlc_sanity,
        write_bars,
    )
    from .schema import read_partition

    paths = select_partitions(cfg, l0_root, [symbol])
    chunks = _day_chunks(cfg, paths, max_rows_per_chunk)
    result = BarsBuild(symbol=symbol, chunks=len(chunks))
    pieces: dict[str, list[pd.DataFrame]] = {tf: [] for tf in timeframes}

    for index, chunk in enumerate(chunks, start=1):
        frames = [read_partition(path, cfg) for path in chunk]
        ticks = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
        if not ticks.empty:
            ticks = ticks.sort_values("timestamp", kind="mergesort")
            result.ticks += int(len(ticks))
            for tf, bars in build_all_timeframes(ticks, symbol, timeframes).items():
                if not bars.empty:
                    pieces[tf].append(bars)
        if on_progress:
            on_progress(index, len(chunks), f"{symbol} kipande {index}")

    for tf in timeframes:
        bars = (
            pd.concat(pieces[tf]).sort_index()
            if pieces[tf]
            else build_all_timeframes(pd.DataFrame(), symbol, [tf])[tf]
        )
        bars = bars[~bars.index.duplicated(keep="last")]
        result.rows[tf] = int(len(bars))
        sanity = check_ohlc_sanity(bars)
        result.ohlc_violations[tf] = int(sanity.value or 0) if not sanity.passed else 0
        flat = check_flat_bars(bars, int(cfg.get("quality.max_flat_bars", 10)))
        result.longest_flat[tf] = int(flat.value or 0) if not flat.passed else 0
        gaps = check_bar_gaps(bars, tf, int(cfg.get("quality.max_gap_bars", 3)))
        result.bar_gaps[tf] = int(gaps.value or 0) if not gaps.passed else 0
        if tf == str(cfg.get("bars.decision_tf", "H1")) and not bars.empty:
            # Wigo wa miaka unapimwa kwa TF ya uamuzi — ndiyo inayotumika kwa
            # kila decision point, kwa hiyo ndiyo yenye maana kwa `min_years`.
            first, last = bars.index[0], bars.index[-1]
            result.span = (first.isoformat(), last.isoformat())
            result.years = (last - first).days / 365.25
        write_bars(bars, l2_root, symbol, tf)
    return result


def _l2_fingerprint(cfg, paths: Sequence[Path], timeframes: Sequence[str]) -> str:
    """Alama ya kile kinachozalisha L2 ya symbol: partitions + TF + config."""
    import hashlib

    payload = "|".join(
        sorted(f"{p}:{p.stat().st_size}:{int(p.stat().st_mtime)}" for p in paths)
    )
    payload += f"||{','.join(sorted(timeframes))}||{getattr(cfg, 'config_hash', '')}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def build_l2(
    cfg,
    l0_root: Path,
    l2_root: Path,
    symbols: Sequence[str] | None = None,
    timeframes: Iterable[str] | None = None,
    max_rows_per_chunk: int = 5_000_000,
    on_progress: ProgressFn | None = None,
    resume: bool = True,
) -> list[BarsBuild]:
    """L2 kwa symbols zote, **ikiendelea ilipoishia**.

    Hii ni kazi ya masaa (ticks bilioni 3.4). Bila resume, kukatika saa ya nane
    kungemaanisha kuanza upya — na kazi isiyoweza kukatizwa ni kazi
    inayolazimisha mtu kuiacha ikikimbia hata pale anapohitaji mashine yake.

    Symbol inarukwa ikiwa L2 yake ipo NA alama ya `partitions + TF + config_hash`
    haijabadilika. Data mpya ikiingia L0, alama inabadilika na symbol inajengwa
    upya — hakuna njia ya kubaki na bars za zamani kimya.
    """
    tfs = list(timeframes or cfg.get("bars.timeframes"))
    targets = [s.upper() for s in (symbols or cfg.symbols)]
    state_path = Path(l2_root) / "_l2_state.json"
    state: dict[str, Any] = {}
    if resume and state_path.is_file():
        try:
            state = json.loads(state_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            state = {}

    out: list[BarsBuild] = []
    for symbol in targets:
        paths = select_partitions(cfg, l0_root, [symbol])
        marker = _l2_fingerprint(cfg, paths, tfs)
        done = state.get(symbol, {})
        if resume and done.get("fingerprint") == marker:
            skipped = BarsBuild(
                symbol=symbol,
                rows=done.get("rows", {}),
                ticks=int(done.get("ticks", 0)),
                chunks=int(done.get("chunks", 0)),
                span=tuple(done["span"]) if done.get("span") else None,
                years=float(done.get("years", 0.0)),
            )
            if on_progress:
                on_progress(1, 1, f"{symbol} — ipo tayari, imerukwa")
            out.append(skipped)
            continue

        build = build_l2_for_symbol(
            cfg,
            symbol,
            l0_root,
            l2_root,
            tfs,
            max_rows_per_chunk=max_rows_per_chunk,
            on_progress=on_progress,
        )
        out.append(build)
        # Hali inaandikwa BAADA ya kila symbol — kukatika baada ya symbol ya nane
        # kunapoteza ya tisa pekee, si zote nane.
        state[symbol] = {**build.to_json(), "fingerprint": marker}
        state_path.parent.mkdir(parents=True, exist_ok=True)
        state_path.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
    return out
