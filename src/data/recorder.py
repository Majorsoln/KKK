"""DF-04/DF-03 — recorder wa tick feed ya broker (spec §2.2, sharti la 1).

"Kila mwezi usiorekodiwa ni data ya broker iliyopotea bure." Kwa hiyo recorder
hii **inaanza, hauishii**: inavuta ticks (bid/ask + volumes) kutoka chanzo cha
broker, inaandika partition MOJA kwa kila siku ya trading, na kila partition
inapata `provenance: broker` + SHA256 kwenye manifest.

Maamuzi ya muundo yanayolinda spec:

* **Immutability (DF-01).** Partition inaandikwa MARA MOJA, baada ya siku
  kufungwa (+ `day_lag_minutes`). Faili likishakuwepo, recorder hailigusi tena —
  data mpya ya siku ile inarekodiwa kama tofauti kwenye ripoti, si kwa
  kuandika juu.
* **Kujitengeneza baada ya kukatika.** Watermark inahifadhiwa kwenye disk.
  Kila poll inavuta upya siku ambayo bado haijafungwa nzima, kwa hiyo process
  ikifa katikati ya siku hakuna tick inayopotea.
* **Hakuna data ya kubuni.** Siku ya trading isiyokuwa na ticks HAIANDIKWI kama
  partition tupu; inarekodiwa kama `empty_days` na freshness (DF-04)
  inaipandisha kuwa ONYO.
"""

from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import dataclass, field
from datetime import date, datetime, time as dtime, timedelta, timezone
from pathlib import Path
from typing import Any, Protocol

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from .calendar import TradingCalendar, calendar_from_config
from .config import DataConfig
from .manifest import L0Manifest, PROVENANCE_BROKER, code_rev
from .schema import CANONICAL_COLUMNS, CANONICAL_TIMESTAMP_DTYPE

LOG = logging.getLogger("elitefx.recorder")

RECORDER_VERSION = "t0.1"
STATE_DIRNAME = "_state"
STATE_FILENAME = "recorder_state.json"
PARTITION_FILENAME = "ticks.parquet"
MAX_DAYS_PER_POLL = 400


class TickSource(Protocol):
    """Chanzo cha ticks (MT5 kwa live; replay kwa tests)."""

    name: str

    def fetch_ticks(self, symbol: str, start: datetime, end: datetime) -> pd.DataFrame:
        """Ticks za [start, end) kwa schema ya kawaida (spec §2.1) + columns za ziada."""


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _day_start(day: date) -> datetime:
    return datetime.combine(day, dtime.min, tzinfo=timezone.utc)


def _iso(moment: datetime) -> str:
    return moment.astimezone(timezone.utc).isoformat(timespec="seconds")


# --------------------------------------------------------------------------
# Hali ya recorder (inayodumu kwenye disk)
# --------------------------------------------------------------------------


@dataclass
class SymbolState:
    watermark: str  # mwanzo wa siku ya kwanza ambayo bado haijaandikwa (ISO, UTC)
    last_written_day: str | None = None
    last_tick_ts: str | None = None
    empty_days: list[str] = field(default_factory=list)
    skipped_existing: list[str] = field(default_factory=list)

    def watermark_dt(self) -> datetime:
        return datetime.fromisoformat(self.watermark).astimezone(timezone.utc)


class RecorderState:
    """Watermarks + siku tupu, zinazodumu kati ya restarts."""

    def __init__(self, path: Path, started_at: str | None = None) -> None:
        self.path = Path(path)
        self.started_at = started_at or _iso(utcnow())
        self.symbols: dict[str, SymbolState] = {}

    @classmethod
    def load_or_new(cls, path: Path, now: datetime | None = None) -> "RecorderState":
        path = Path(path)
        if not path.is_file():
            return cls(path, started_at=_iso(now) if now is not None else None)
        payload = json.loads(path.read_text(encoding="utf-8"))
        state = cls(path, started_at=payload.get("started_at"))
        for symbol, raw in payload.get("symbols", {}).items():
            state.symbols[symbol] = SymbolState(
                watermark=raw["watermark"],
                last_written_day=raw.get("last_written_day"),
                last_tick_ts=raw.get("last_tick_ts"),
                empty_days=list(raw.get("empty_days", [])),
                skipped_existing=list(raw.get("skipped_existing", [])),
            )
        return state

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "started_at": self.started_at,
            "updated_at": _iso(utcnow()),
            "recorder_version": RECORDER_VERSION,
            "symbols": {
                symbol: {
                    "watermark": s.watermark,
                    "last_written_day": s.last_written_day,
                    "last_tick_ts": s.last_tick_ts,
                    "empty_days": s.empty_days,
                    "skipped_existing": s.skipped_existing,
                }
                for symbol, s in sorted(self.symbols.items())
            },
        }
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        os.replace(tmp, self.path)

    def for_symbol(self, symbol: str, default_watermark: datetime) -> SymbolState:
        if symbol not in self.symbols:
            self.symbols[symbol] = SymbolState(watermark=_iso(default_watermark))
        return self.symbols[symbol]


# --------------------------------------------------------------------------
# Matokeo ya poll
# --------------------------------------------------------------------------


@dataclass
class WrittenPartition:
    symbol: str
    day: str
    path: str
    rows: int
    sha256: str


@dataclass
class PollResult:
    written: list[WrittenPartition] = field(default_factory=list)
    empty_days: list[tuple[str, str]] = field(default_factory=list)
    skipped_existing: list[tuple[str, str]] = field(default_factory=list)
    errors: list[dict[str, str]] = field(default_factory=list)
    buffered_days: dict[str, str] = field(default_factory=dict)

    def summary(self) -> str:
        return (
            f"written={len(self.written)} empty={len(self.empty_days)} "
            f"skipped={len(self.skipped_existing)} errors={len(self.errors)}"
        )


# --------------------------------------------------------------------------
# Recorder
# --------------------------------------------------------------------------


@dataclass
class RecorderSettings:
    """Vigezo vyote vinatoka `config/data.yaml` (§recorder) — hakuna default kwenye code."""

    l0_root: Path
    manifest_path: Path
    symbols: list[str]
    provenance: str = PROVENANCE_BROKER
    poll_seconds: int = 60
    day_lag_minutes: int = 15
    initial_backfill_days: int = 3
    compression: str = "zstd"

    @classmethod
    def from_config(cls, cfg: DataConfig) -> "RecorderSettings":
        return cls(
            l0_root=cfg.l0_root,
            manifest_path=cfg.l0_manifest_path,
            symbols=cfg.recorder_symbols,
            provenance=str(cfg.get("recorder.provenance_tag", PROVENANCE_BROKER)),
            poll_seconds=int(cfg.get("recorder.poll_seconds", 60)),
            day_lag_minutes=int(cfg.get("recorder.day_lag_minutes", 15)),
            initial_backfill_days=int(cfg.get("recorder.initial_backfill_days", 3)),
            compression=str(cfg.get("recorder.compression", "zstd")),
        )


class TickRecorder:
    """Inavuta ticks kutoka chanzo cha broker na kuandika partitions za L0."""

    def __init__(
        self,
        source: TickSource,
        cfg: DataConfig,
        settings: RecorderSettings | None = None,
        calendar: TradingCalendar | None = None,
        clock=utcnow,
    ) -> None:
        self.source = source
        self.cfg = cfg
        self.settings = settings or RecorderSettings.from_config(cfg)
        self.calendar = calendar or calendar_from_config(cfg)
        self.clock = clock
        # `started_at` inatoka kwenye saa ya recorder — ndiyo mwanzo wa dirisha
        # la DF-04: siku kabla ya recorder kuanza si "siku isiyorekodiwa".
        self.state = RecorderState.load_or_new(
            self.settings.l0_root / STATE_DIRNAME / STATE_FILENAME, now=self.clock()
        )

    # ---------- njia za partitions ----------

    def partition_dir(self, symbol: str, day: date) -> Path:
        return (
            self.settings.l0_root
            / f"provenance={self.settings.provenance}"
            / f"symbol={symbol}"
            / f"date={day.isoformat()}"
        )

    def partition_path(self, symbol: str, day: date) -> Path:
        return self.partition_dir(symbol, day) / PARTITION_FILENAME

    # ---------- kuandika ----------

    def _write_partition(self, symbol: str, day: date, frame: pd.DataFrame) -> Path:
        """Andika partition ya siku moja kwa njia ya atomiki. Ikiwepo → ManifestError."""
        target = self.partition_path(symbol, day)
        if target.exists():
            raise FileExistsError(str(target))
        target.parent.mkdir(parents=True, exist_ok=True)

        table = pa.Table.from_pandas(frame, preserve_index=False)
        metadata = {
            b"provenance": self.settings.provenance.encode(),
            b"symbol": symbol.encode(),
            b"date": day.isoformat().encode(),
            b"schema": ",".join(CANONICAL_COLUMNS).encode(),
            b"schema_variant": b"A",
            b"timestamp_tz": b"UTC",
            b"source": str(getattr(self.source, "name", "unknown")).encode(),
            b"recorder_version": RECORDER_VERSION.encode(),
            b"recorded_at": _iso(self.clock()).encode(),
            b"config_hash": self.cfg.config_hash.encode(),
            b"code_rev": code_rev().encode(),
            b"rows": str(len(frame)).encode(),
        }
        existing = table.schema.metadata or {}
        table = table.replace_schema_metadata({**existing, **metadata})

        tmp = target.with_suffix(".parquet.tmp")
        pq.write_table(table, tmp, compression=self.settings.compression)
        os.replace(tmp, target)
        return target

    def _prepare_frame(self, frame: pd.DataFrame) -> pd.DataFrame:
        """Hakikisha schema ya kawaida + mpangilio wa muda kabla ya kuandika."""
        missing = [c for c in CANONICAL_COLUMNS if c not in frame.columns]
        if missing:
            raise ValueError(f"chanzo hakikutoa columns {missing} (spec §2.1)")
        extras = [c for c in frame.columns if c not in CANONICAL_COLUMNS]
        out = frame.loc[:, list(CANONICAL_COLUMNS) + extras].copy()
        out["timestamp"] = pd.to_datetime(out["timestamp"], utc=True).astype(
            CANONICAL_TIMESTAMP_DTYPE
        )
        for column in ("bid", "ask", "bid_vol", "ask_vol"):
            out[column] = pd.to_numeric(out[column], errors="coerce").astype("float64")
        return out.sort_values("timestamp", kind="stable").reset_index(drop=True)

    # ---------- poll moja ----------

    def poll_once(self, manifest: L0Manifest | None = None) -> PollResult:
        """Vuta ticks mpya kwa kila symbol na uandike siku zilizofungwa."""
        result = PollResult()
        now = self.clock()
        cutoff = now - timedelta(minutes=self.settings.day_lag_minutes)
        last_complete_day = (cutoff - timedelta(days=1)).date()
        own_manifest = manifest is None
        manifest = manifest or L0Manifest.load_or_new(
            self.settings.manifest_path, self.settings.l0_root, self.cfg.config_hash
        )

        for symbol in self.settings.symbols:
            default_wm = _day_start((now - timedelta(days=self.settings.initial_backfill_days)).date())
            state = self.state.for_symbol(symbol, default_wm)
            try:
                self._poll_symbol(symbol, state, now, last_complete_day, manifest, result)
            except Exception as exc:  # chanzo kikikataa, symbol nyingine zinaendelea
                LOG.warning("%s: poll imeshindikana: %s", symbol, exc)
                result.errors.append({"symbol": symbol, "error": f"{type(exc).__name__}: {exc}"})

        self.state.save()
        if own_manifest or result.written:
            manifest.save()
        return result

    def _poll_symbol(
        self,
        symbol: str,
        state: SymbolState,
        now: datetime,
        last_complete_day: date,
        manifest: L0Manifest,
        result: PollResult,
    ) -> None:
        start = state.watermark_dt()
        frame = self.source.fetch_ticks(symbol, start, now)
        frame = self._prepare_frame(
            frame if frame is not None else pd.DataFrame(columns=list(CANONICAL_COLUMNS))
        )
        if not frame.empty:
            state.last_tick_ts = _iso(frame["timestamp"].max().to_pydatetime())

        by_day = {
            day: group for day, group in frame.groupby(frame["timestamp"].dt.date, sort=True)
        }
        open_day = now.date()
        if open_day in by_day:
            result.buffered_days[symbol] = f"{open_day.isoformat()}:{len(by_day[open_day])}"

        cursor = start.date()
        days_done = 0
        while cursor <= last_complete_day and days_done < MAX_DAYS_PER_POLL:
            days_done += 1
            group = by_day.get(cursor)
            if group is None or group.empty:
                if self.calendar.is_full_trading_day(cursor):
                    label = cursor.isoformat()
                    if label not in state.empty_days:
                        state.empty_days.append(label)
                    result.empty_days.append((symbol, label))
            elif self.partition_path(symbol, cursor).exists():
                label = cursor.isoformat()
                if label not in state.skipped_existing:
                    state.skipped_existing.append(label)
                result.skipped_existing.append((symbol, label))
            else:
                written = self._write_day(symbol, cursor, group, manifest)
                result.written.append(written)
                state.last_written_day = cursor.isoformat()
            cursor += timedelta(days=1)

        state.watermark = _iso(_day_start(cursor))

    def _write_day(
        self, symbol: str, day: date, group: pd.DataFrame, manifest: L0Manifest
    ) -> WrittenPartition:
        path = self._write_partition(symbol, day, group.reset_index(drop=True))
        entry = manifest.record(
            path,
            self.cfg,
            provenance=self.settings.provenance,
            schema_variant="A",
            rows=int(len(group)),
            first_ts=group["timestamp"].min().isoformat(),
            last_ts=group["timestamp"].max().isoformat(),
        )
        LOG.info("%s %s: ticks %d -> %s", symbol, day, len(group), path)
        return WrittenPartition(
            symbol=symbol,
            day=day.isoformat(),
            path=str(path),
            rows=int(len(group)),
            sha256=entry.sha256,
        )

    # ---------- mzunguko usioisha ----------

    def run_forever(self, max_polls: int | None = None, stop=None, sleeper=time.sleep) -> int:
        """Anza kurekodi na usiishie (§2.2). Hitilafu ya poll haiui process."""
        polls = 0
        LOG.info(
            "recorder imeanza: symbols=%d provenance=%s l0_root=%s",
            len(self.settings.symbols),
            self.settings.provenance,
            self.settings.l0_root,
        )
        while True:
            if stop is not None and stop():
                LOG.info("recorder imesimamishwa kwa ombi")
                return polls
            try:
                outcome = self.poll_once()
                LOG.info("poll #%d: %s", polls + 1, outcome.summary())
            except Exception as exc:  # pragma: no cover - kinga ya mwisho
                LOG.exception("poll imeshindikana kabisa: %s", exc)
            polls += 1
            if max_polls is not None and polls >= max_polls:
                return polls
            sleeper(self.settings.poll_seconds)


def recorder_status(cfg: DataConfig) -> dict[str, Any]:
    """Hali ya recorder kwa ripoti (hakuna athari kwenye disk)."""
    state_path = cfg.l0_root / STATE_DIRNAME / STATE_FILENAME
    if not state_path.is_file():
        return {"status": "haijaanza", "state_path": str(state_path)}
    state = RecorderState.load_or_new(state_path)
    return {
        "status": "inaendelea",
        "state_path": str(state_path),
        "started_at": state.started_at,
        "symbols": {
            symbol: {
                "watermark": s.watermark,
                "last_written_day": s.last_written_day,
                "empty_days": len(s.empty_days),
            }
            for symbol, s in sorted(state.symbols.items())
        },
    }
