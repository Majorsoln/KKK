"""RS-03 — kalenda ya sessions iliyotengenezwa **KUTOKA KWENYE DATA** (spec §3).

> "Weekend, holiday na rollover si 'gaps' — ni kalenda. Kalenda inatengenezwa
> kwa data yenyewe (bars zinazoonekana) na kuthibitishwa, si kudhaniwa."

`calendar.py` ina kalenda ya muda (Jumamosi/Jumapili + sikukuu mbili) ambayo
recorder inaitumia kujua siku gani ukimya wake ni ONYO. **Hii hapa ndiyo kalenda
halisi**: inasoma ticks zilizopo na kutoa, kwa kila siku:

* `session_open` / `session_close` — tick ya kwanza na ya mwisho (UTC);
* `ticks` — idadi;
* `kind` — `full` · `partial` · `closed`.

Siku inakuwa **`partial`** ikiwa ina ticks lakini chini ya `partial_frac` ya
wastani wa siku kamili za mwezi huo. Hii ndiyo inayonasa sikukuu za nusu-siku
(Christmas Eve, mwaka mpya) bila kuziorodhesha kwa mkono — na ndiyo maana
kalenda inatoka kwenye data.

Kalenda hii ndiyo msingi wa `coverage` ya L1 (§3 check 1): bila kujua siku
ilipaswa kuwa na ticks ngapi, "coverage" ni namba isiyo na maana.
"""

from __future__ import annotations

import json
import statistics
from collections import defaultdict
from dataclasses import asdict, dataclass, field
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable

import pandas as pd

KIND_FULL = "full"
KIND_PARTIAL = "partial"
KIND_CLOSED = "closed"


@dataclass
class SessionDay:
    """Siku moja kama data inavyoionyesha — si kama tunavyodhani."""

    day: str
    kind: str
    ticks: int = 0
    session_open: str | None = None
    session_close: str | None = None
    symbols: int = 0
    minutes: int = 0

    def to_json(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class SessionCalendar:
    """Kalenda ya siku zote zilizoonekana kwenye data.

    `symbol_months` ndiyo **matarajio** ya check 1 ya §3: kwa kila symbol na kila
    mwezi, wastani (median) wa dakika zenye quotes kwenye siku KAMILI za mwezi
    huo. Median, si mean, kwa sababu siku moja iliyoharibika isipotoshe kizingiti
    chake yenyewe. Kwa mwezi, si mwaka, ili DST na misimu visihesabiwe kama
    upungufu wa data.
    """

    days: dict[str, SessionDay] = field(default_factory=dict)
    built_at: str = ""
    source: str = ""
    symbol_months: dict[str, dict[str, float]] = field(default_factory=dict)
    symbol_sessions: dict[str, dict[str, list[float]]] = field(default_factory=dict)

    # ---------- maswali ----------

    def kind_of(self, day: date | str) -> str:
        key = day if isinstance(day, str) else day.isoformat()
        entry = self.days.get(key)
        return entry.kind if entry else KIND_CLOSED

    def is_full_trading_day(self, day: date | str) -> bool:
        return self.kind_of(day) == KIND_FULL

    def full_days(self) -> list[str]:
        return sorted(k for k, v in self.days.items() if v.kind == KIND_FULL)

    def partial_days(self) -> list[str]:
        return sorted(k for k, v in self.days.items() if v.kind == KIND_PARTIAL)

    def expected_ticks(self, day: date | str) -> int:
        key = day if isinstance(day, str) else day.isoformat()
        entry = self.days.get(key)
        return entry.ticks if entry else 0

    def expected_minutes(self, symbol: str | None, day: date | str) -> int:
        """Dakika zinazotarajiwa kuwa na quotes kwa symbol/siku (check 1 ya §3).

        Sifuri = **hatujui**, na `check_coverage` haihukumu. Hiyo ndiyo hali ya
        siku za `partial` (sikukuu za nusu-siku): kuzipima dhidi ya siku kamili
        kungezalisha FAIL za uwongo kila Desemba.
        """
        if not symbol:
            return 0
        key = day if isinstance(day, str) else day.isoformat()
        if self.kind_of(key) != KIND_FULL:
            return 0
        months = self.symbol_months.get(symbol.upper(), {})
        return int(round(months.get(key[:7], 0.0)))

    def expected_session(
        self, symbol: str | None, day: date | str
    ) -> tuple[datetime, datetime] | None:
        """Mipaka ya session inayotarajiwa kwa symbol/siku — **kwa symbol**.

        Median ya mwezi, si mipaka ya siku yenyewe: kutumia siku yenyewe kama
        kipimo chake kungefanya check 6 ipite daima. Na kwa symbol, si kwa
        symbols zote pamoja: XAUUSD haifanyi biashara saa zile zile za EURUSD,
        kwa hiyo mipaka ya pamoja ingeifelisha XAUUSD kila siku.
        """
        if not symbol:
            return None
        key = day if isinstance(day, str) else day.isoformat()
        months = self.symbol_sessions.get(symbol.upper(), {})
        bounds = months.get(key[:7])
        if not bounds:
            return None
        midnight = utc_midnight(date.fromisoformat(key))
        return (
            midnight + timedelta(minutes=float(bounds[0])),
            midnight + timedelta(minutes=float(bounds[1])),
        )

    # ---------- I/O ----------

    def to_json(self) -> dict[str, Any]:
        return {
            "built_at": self.built_at,
            "source": self.source,
            "counts": {
                KIND_FULL: len(self.full_days()),
                KIND_PARTIAL: len(self.partial_days()),
            },
            "symbol_months": {
                sym: {month: round(value, 1) for month, value in sorted(months.items())}
                for sym, months in sorted(self.symbol_months.items())
            },
            "symbol_sessions": {
                sym: {month: [round(v, 1) for v in bounds] for month, bounds in sorted(months.items())}
                for sym, months in sorted(self.symbol_sessions.items())
            },
            "days": {k: v.to_json() for k, v in sorted(self.days.items())},
        }

    def save(self, path: Path) -> Path:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_json(), indent=2) + "\n", encoding="utf-8")
        return path

    @classmethod
    def load(cls, path: Path) -> "SessionCalendar":
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls(
            days={k: SessionDay(**v) for k, v in payload.get("days", {}).items()},
            built_at=payload.get("built_at", ""),
            source=payload.get("source", ""),
            symbol_months={
                sym: {m: float(v) for m, v in months.items()}
                for sym, months in payload.get("symbol_months", {}).items()
            },
            symbol_sessions={
                sym: {m: [float(x) for x in bounds] for m, bounds in months.items()}
                for sym, months in payload.get("symbol_sessions", {}).items()
            },
        )


@dataclass
class DayObservation:
    """Uchunguzi wa siku moja kwa symbol moja — malighafi ya kalenda."""

    day: date
    ticks: int
    first_ts: datetime | None
    last_ts: datetime | None
    symbol: str = ""
    minutes: int = 0

    def to_json(self) -> dict[str, Any]:
        return {
            "day": self.day.isoformat(),
            "ticks": self.ticks,
            "first_ts": self.first_ts.isoformat() if self.first_ts else None,
            "last_ts": self.last_ts.isoformat() if self.last_ts else None,
            "symbol": self.symbol,
            "minutes": self.minutes,
        }

    @classmethod
    def from_json(cls, payload: dict[str, Any]) -> "DayObservation":
        return cls(
            day=date.fromisoformat(payload["day"]),
            ticks=int(payload["ticks"]),
            first_ts=datetime.fromisoformat(payload["first_ts"]) if payload.get("first_ts") else None,
            last_ts=datetime.fromisoformat(payload["last_ts"]) if payload.get("last_ts") else None,
            symbol=payload.get("symbol", ""),
            minutes=int(payload.get("minutes", 0)),
        )


def _observations_from_timestamps(
    timestamps: "pd.Series", symbol: str
) -> list[DayObservation]:
    if timestamps.empty:
        return []
    frame = timestamps.to_frame("timestamp")
    frame["day"] = frame["timestamp"].dt.date
    out: list[DayObservation] = []
    for day, group in frame.groupby("day", sort=True):
        stamps = group["timestamp"]
        out.append(
            DayObservation(
                day=day,
                ticks=int(len(stamps)),
                first_ts=stamps.min().to_pydatetime(),
                last_ts=stamps.max().to_pydatetime(),
                symbol=symbol,
                # Dakika za KIPEKEE zenye quote — hii ndiyo "bars zilizopo" ya
                # check 1 ya §3 kwenye tabaka la ticks.
                minutes=int(stamps.dt.floor("min").nunique()),
            )
        )
    return out


def observe_partition(path: Path, cfg) -> list[DayObservation]:
    """Siku zilizomo kwenye partition moja — **inasoma partition nzima**.

    Inatumika kwa ukaguzi wa partition moja. Kwa L0 nzima tumia
    `observe_timestamps()`, inayosoma column ya timestamp PEKEE.
    """
    from .manifest import symbol_from_path
    from .schema import read_partition

    frame = read_partition(path, cfg)
    if frame.empty:
        return []
    return _observations_from_timestamps(
        frame["timestamp"], symbol_from_path(Path(path), cfg) or ""
    )


def observe_timestamps(path: Path, cfg) -> list[DayObservation]:
    """Uchunguzi wa siku kwa kusoma **column ya timestamp PEKEE**.

    Kalenda inahitaji: siku, idadi ya ticks, mipaka ya session, na dakika zenye
    quotes. Vyote vinatoka kwenye column moja. Kusoma bid/ask/volume hapa
    kungezidisha gharama mara nne bila kuongeza taarifa hata moja.

    (Footer ya parquet ingetosha kwa idadi na mipaka, lakini SI kwa dakika za
    kipekee — na dakika ndizo kizingiti cha coverage. Kwa hiyo tunasoma column.)
    """
    import pyarrow.parquet as pq

    from .manifest import symbol_from_path
    from .schema import _to_utc_microseconds, detect_variant

    path = Path(path)
    pfile = pq.ParquetFile(path)
    spec = detect_variant(list(pfile.schema_arrow.names), cfg)
    ts_column = spec.columns[0]
    series = pq.read_table(path, columns=[ts_column]).column(0).to_pandas()
    if series.empty:
        return []
    return _observations_from_timestamps(
        _to_utc_microseconds(series, spec.time_unit),
        symbol_from_path(path, cfg) or "",
    )


def build_calendar(
    observations: Iterable[DayObservation],
    partial_frac: float = 0.25,
    source: str = "",
) -> SessionCalendar:
    """Kalenda kutoka uchunguzi wa siku — hakuna sikukuu iliyoandikwa kwa mkono.

    `partial_frac`: siku yenye ticks chini ya sehemu hii ya **wastani wa mwezi
    wake** ni `partial`. Wastani ni wa mwezi (si wa mwaka) ili majira ya kiangazi
    yenye ukimya wa asili yasihesabiwe kama sikukuu.
    """
    per_day: dict[date, dict[str, Any]] = defaultdict(
        lambda: {"ticks": 0, "first": None, "last": None, "symbols": set(), "minutes": 0}
    )
    per_symbol_day: dict[tuple[str, date], int] = defaultdict(int)
    per_symbol_bounds: dict[tuple[str, date], list[datetime]] = {}
    for obs in observations:
        slot = per_day[obs.day]
        slot["ticks"] += obs.ticks
        slot["symbols"].add(obs.symbol or "?")
        slot["minutes"] = max(slot["minutes"], obs.minutes)
        if obs.first_ts and (slot["first"] is None or obs.first_ts < slot["first"]):
            slot["first"] = obs.first_ts
        if obs.last_ts and (slot["last"] is None or obs.last_ts > slot["last"]):
            slot["last"] = obs.last_ts
        if obs.symbol:
            key = (obs.symbol.upper(), obs.day)
            per_symbol_day[key] += obs.minutes
            if obs.first_ts and obs.last_ts:
                bounds = per_symbol_bounds.setdefault(key, [obs.first_ts, obs.last_ts])
                bounds[0] = min(bounds[0], obs.first_ts)
                bounds[1] = max(bounds[1], obs.last_ts)

    by_month: dict[tuple[int, int], list[int]] = defaultdict(list)
    for day, slot in per_day.items():
        by_month[(day.year, day.month)].append(slot["ticks"])
    median_of_month = {
        key: statistics.median(values) for key, values in by_month.items() if values
    }

    days: dict[str, SessionDay] = {}
    for day, slot in sorted(per_day.items()):
        median = median_of_month.get((day.year, day.month), 0)
        kind = KIND_PARTIAL if median and slot["ticks"] < partial_frac * median else KIND_FULL
        days[day.isoformat()] = SessionDay(
            day=day.isoformat(),
            kind=kind,
            ticks=int(slot["ticks"]),
            session_open=slot["first"].isoformat() if slot["first"] else None,
            session_close=slot["last"].isoformat() if slot["last"] else None,
            symbols=len(slot["symbols"]),
            minutes=int(slot["minutes"]),
        )

    # Matarajio ya coverage: median ya dakika za siku KAMILI, kwa symbol/mwezi.
    minutes_by_symbol_month: dict[str, dict[str, list[int]]] = defaultdict(
        lambda: defaultdict(list)
    )
    for (symbol, day), minutes in per_symbol_day.items():
        if days.get(day.isoformat(), SessionDay(day="", kind=KIND_CLOSED)).kind == KIND_FULL:
            minutes_by_symbol_month[symbol][day.isoformat()[:7]].append(minutes)
    symbol_months = {
        symbol: {
            month: float(statistics.median(values)) for month, values in months.items() if values
        }
        for symbol, months in minutes_by_symbol_month.items()
    }

    # Mipaka ya session kwa symbol/mwezi (dakika kutoka usiku wa manane, UTC).
    bounds_by_symbol_month: dict[str, dict[str, list[list[float]]]] = defaultdict(
        lambda: defaultdict(list)
    )
    for (symbol, day), (first, last) in per_symbol_bounds.items():
        if days.get(day.isoformat(), SessionDay(day="", kind=KIND_CLOSED)).kind != KIND_FULL:
            continue
        bounds_by_symbol_month[symbol][day.isoformat()[:7]].append(
            [_minute_of_day(first), _minute_of_day(last)]
        )
    symbol_sessions = {
        symbol: {
            month: [
                float(statistics.median([b[0] for b in pairs])),
                float(statistics.median([b[1] for b in pairs])),
            ]
            for month, pairs in months.items()
            if pairs
        }
        for symbol, months in bounds_by_symbol_month.items()
    }

    return SessionCalendar(
        days=days,
        built_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        source=source,
        symbol_months=symbol_months,
        symbol_sessions=symbol_sessions,
    )


def _minute_of_day(stamp: datetime) -> float:
    """Dakika kutoka usiku wa manane UTC — inaruhusu median kuvuka siku."""
    return stamp.hour * 60 + stamp.minute + stamp.second / 60.0


def compare_with_assumed(calendar: SessionCalendar, assumed) -> dict[str, Any]:
    """Kalenda ya data dhidi ya ile ya kudhaniwa (`calendar.py`) — spec §3.

    Inatoa **siku zinazotofautiana**, ambazo ndizo taarifa halisi:
    * `silent_but_expected` — tulidhani ni siku kamili, data haina ticks;
    * `active_but_excluded` — tulidhani imefungwa, data ina ticks;
    * `partial_days` — siku za nusu ambazo kalenda ya kudhaniwa haizijui.
    """
    silent: list[str] = []
    active: list[str] = []
    observed = set(calendar.days)

    if calendar.days:
        first = date.fromisoformat(min(observed))
        last = date.fromisoformat(max(observed))
        for day in assumed.full_trading_days(first, last):
            if day.isoformat() not in observed:
                silent.append(day.isoformat())

    for key, entry in calendar.days.items():
        if entry.ticks and not assumed.is_full_trading_day(date.fromisoformat(key)):
            active.append(key)

    return {
        "silent_but_expected": sorted(silent),
        "active_but_excluded": sorted(active),
        "partial_days": calendar.partial_days(),
    }


def session_bounds(calendar: SessionCalendar, day: date) -> tuple[datetime, datetime] | None:
    """Mipaka halisi ya session ya siku (UTC), kama data inavyoionyesha."""
    entry = calendar.days.get(day.isoformat())
    if not entry or not entry.session_open or not entry.session_close:
        return None
    return (
        datetime.fromisoformat(entry.session_open),
        datetime.fromisoformat(entry.session_close),
    )


def utc_midnight(day: date) -> datetime:
    return datetime.combine(day, time.min, tzinfo=timezone.utc)
