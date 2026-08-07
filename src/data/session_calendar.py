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

    `symbol_expect` ndiyo **matarajio** ya checks 1 na 6 za §3: kwa kila symbol
    na kila siku, `[dakika, session_open, session_close]` zinazotarajiwa.

    Zinatoka kwa median ya **siku za jirani zenye SIKU ILE ILE YA WIKI**. Sababu
    ni kipimo, si nadharia: Ijumaa soko linafunga 21:00 UTC wakati Jumatatu–
    Alhamisi zinaendelea hadi usiku wa manane. Kwa hiyo Ijumaa ina asilimia 87.5
    ya dakika za siku nyingine (`21/24`) na close yake iko **dakika 180** mapema.
    Kuipima Ijumaa kwa wastani wa wiki nzima kunaifelisha kila wiki — na Ijumaa
    ni asilimia 20 ya siku zote za trading.

    Median ya majirani, si ya mwezi mzima, ili DST ifuatwe: mabadiliko ya saa
    yanaathiri majirani wachache, na siku ya mabadiliko yenyewe inaonekana kama
    hatua ya saa 1 (inaandikwa, haifelishi — ona `check_session_match`).
    """

    days: dict[str, SessionDay] = field(default_factory=dict)
    built_at: str = ""
    source: str = ""
    symbol_expect: dict[str, dict[str, list[float]]] = field(default_factory=dict)

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

    def _expect(self, symbol: str | None, day: date | str) -> list[float] | None:
        if not symbol:
            return None
        key = day if isinstance(day, str) else day.isoformat()
        return self.symbol_expect.get(symbol.upper(), {}).get(key)

    def expected_minutes(self, symbol: str | None, day: date | str) -> int:
        """Dakika zinazotarajiwa kuwa na quotes kwa symbol/siku (check 1 ya §3).

        Sifuri = **hatujui**, na `check_coverage` haihukumu. Hiyo ndiyo hali ya
        siku za `partial` (sikukuu za nusu-siku): kuzipima dhidi ya siku kamili
        kungezalisha FAIL za uwongo kila Desemba.
        """
        key = day if isinstance(day, str) else day.isoformat()
        if self.kind_of(key) != KIND_FULL:
            return 0
        expect = self._expect(symbol, key)
        return int(round(expect[0])) if expect else 0

    def expected_session(
        self, symbol: str | None, day: date | str
    ) -> tuple[datetime, datetime] | None:
        """Mipaka ya session inayotarajiwa kwa symbol/siku (check 6 ya §3).

        Si mipaka ya siku yenyewe — hiyo ingefanya check 6 ipite daima. Ni
        median ya siku za jirani zenye siku ile ile ya wiki, kwa symbol ile ile.
        """
        key = day if isinstance(day, str) else day.isoformat()
        expect = self._expect(symbol, key)
        if not expect:
            return None
        midnight = utc_midnight(date.fromisoformat(key))
        return (
            midnight + timedelta(minutes=float(expect[1])),
            midnight + timedelta(minutes=float(expect[2])),
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
            "symbol_expect": {
                sym: {day: [round(v, 1) for v in values] for day, values in sorted(rows.items())}
                for sym, rows in sorted(self.symbol_expect.items())
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
            symbol_expect={
                sym: {d: [float(x) for x in values] for d, values in rows.items()}
                for sym, rows in payload.get("symbol_expect", {}).items()
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

    # Uchunguzi wa siku KAMILI pekee, kwa kila symbol: [dakika, open, close].
    observed: dict[str, dict[date, list[float]]] = defaultdict(dict)
    for (symbol, day), minutes in per_symbol_day.items():
        if days.get(day.isoformat(), SessionDay(day="", kind=KIND_CLOSED)).kind != KIND_FULL:
            continue
        bounds = per_symbol_bounds.get((symbol, day))
        if not bounds:
            continue
        observed[symbol][day] = [
            float(minutes),
            _minute_of_day(bounds[0]),
            _minute_of_day(bounds[1]),
        ]

    symbol_expect = {
        symbol: _weekday_expectations(rows) for symbol, rows in observed.items()
    }

    return SessionCalendar(
        days=days,
        built_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        source=source,
        symbol_expect=symbol_expect,
    )


# Majirani wangapi wa siku ile ile ya wiki yanahitajika kutoa matarajio.
NEIGHBOURS = 5
MIN_SAMPLES = 2


def _weekday_expectations(rows: dict[date, list[float]]) -> dict[str, list[float]]:
    """Matarajio ya kila siku kutoka **majirani wa siku ile ile ya wiki**.

    Siku yenyewe **haiingii** kwenye matarajio yake — vinginevyo siku
    iliyoharibika ingejiwekea kizingiti chake na kupita daima.

    Majirani wa siku ile ile ya wiki wakiwa pungufu ya `MIN_SAMPLES` (mfano
    mwanzoni mwa data, au symbol yenye siku chache), tunarudi kwa majirani wa
    siku yoyote. Ni sahihi kidogo kuliko kutokuwa na kipimo kabisa.
    """
    ordered = sorted(rows)
    by_weekday: dict[int, list[date]] = defaultdict(list)
    for day in ordered:
        by_weekday[day.weekday()].append(day)

    out: dict[str, list[float]] = {}
    for index, day in enumerate(ordered):
        same = [d for d in by_weekday[day.weekday()] if d != day]
        pool = _nearest(same, day, NEIGHBOURS)
        if len(pool) < MIN_SAMPLES:
            pool = _nearest([d for d in ordered if d != day], day, NEIGHBOURS)
        if not pool:
            continue
        out[day.isoformat()] = [
            float(statistics.median([rows[d][slot] for d in pool])) for slot in (0, 1, 2)
        ]
    return out


def _nearest(candidates: list[date], day: date, count: int) -> list[date]:
    return sorted(candidates, key=lambda d: abs((d - day).days))[:count]


def _minute_of_day(stamp: datetime) -> float:
    """Dakika kutoka usiku wa manane UTC — inaruhusu median kuvuka siku."""
    return stamp.hour * 60 + stamp.minute + stamp.second / 60.0


def compare_with_assumed(calendar: SessionCalendar, assumed) -> dict[str, Any]:
    """Kalenda ya data dhidi ya ile ya kudhaniwa (`calendar.py`) — spec §3.

    Inatoa **siku zinazotofautiana**, ambazo ndizo taarifa halisi:
    * `silent_but_expected` — tulidhani ni siku kamili, data haina ticks;
    * `weekend_open` — Jumapili yenye ticks: soko linafunguka jioni (~22:00 UTC).
      Si hitilafu; ni sehemu ya kalenda inayotarajiwa (`is_trading_day`);
    * `unexpected_active` — Jumamosi au sikukuu yenye ticks. **Hii ndiyo
      inayohitaji maelezo**: kalenda ya kudhaniwa inasema soko limefungwa kabisa;
    * `partial_days` — siku za nusu zilizogunduliwa kwa data.

    Kutenganisha mbili za katikati ni muhimu: kwenye miaka 10, Jumapili ni ~550.
    Zikichanganywa na Jumamosi/sikukuu, ripoti inaonyesha "hitilafu 547" wakati
    kuna sifuri, na hitilafu ya kweli — Jumamosi moja yenye ticks — inazama.
    """
    silent: list[str] = []
    weekend_open: list[str] = []
    unexpected: list[str] = []
    observed = set(calendar.days)

    if calendar.days:
        first = date.fromisoformat(min(observed))
        last = date.fromisoformat(max(observed))
        for day in assumed.full_trading_days(first, last):
            if day.isoformat() not in observed:
                silent.append(day.isoformat())

    for key, entry in calendar.days.items():
        day = date.fromisoformat(key)
        if not entry.ticks or assumed.is_full_trading_day(day):
            continue
        (weekend_open if assumed.is_trading_day(day) else unexpected).append(key)

    return {
        "silent_but_expected": sorted(silent),
        "weekend_open": sorted(weekend_open),
        "unexpected_active": sorted(unexpected),
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
