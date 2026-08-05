"""DF-04 — lango la ONYO: siku ya trading bila data mpya ya broker.

Rejista inasema: *"CI/alert: siku ya trading bila data mpya → ONYO"*. Kipimo
kiko hapa, na kinaendeshwa na `python -m src.data.cli check-freshness`.

Hadhi zinazoweza kutoka:

| Hadhi | Maana | Exit code |
|---|---|---|
| `OK` | kila siku kamili ya trading tangu recorder ianze ina partition | 0 |
| `SKIPPED` | storage ya research haipatikani (mf. CI ya repo) | 0 |
| `NOT_STARTED` | `recorder.enabled: true` lakini hakuna partition ya broker | 1 |
| `ALERT` | siku ya trading ipo bila data — data ya broker inapotea SASA | 1 |
| `NO_CLOSED_DAYS` | recorder imeanza; hakuna siku iliyofungwa bado — **hakuna kilichopimwa** | 0 |
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from .calendar import TradingCalendar, calendar_from_config
from .config import DataConfig
from .manifest import L0Manifest, PROVENANCE_BROKER
from .recorder import STATE_DIRNAME, STATE_FILENAME, RecorderState

STATUS_OK = "OK"
STATUS_ALERT = "ALERT"
STATUS_NOT_STARTED = "NOT_STARTED"
STATUS_SKIPPED = "SKIPPED"
STATUS_NO_CLOSED_DAYS = "NO_CLOSED_DAYS"


@dataclass
class SymbolFreshness:
    symbol: str
    last_partition_day: str | None
    missing_days: list[str] = field(default_factory=list)
    partitions: int = 0

    @property
    def ok(self) -> bool:
        return not self.missing_days


@dataclass
class FreshnessReport:
    status: str
    checked_at: str
    reason: str = ""
    window_start: str | None = None
    window_end: str | None = None
    symbols: list[SymbolFreshness] = field(default_factory=list)

    @property
    def exit_code(self) -> int:
        # NO_CLOSED_DAYS si kufeli (hakuna la kufanya) wala si PASS ya kupimwa —
        # exit 0 ili CI isilalamike siku ya kwanza, lakini hadhi inaonekana kwenye ripoti.
        return 0 if self.status in (STATUS_OK, STATUS_SKIPPED, STATUS_NO_CLOSED_DAYS) else 1

    def to_json(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "checked_at": self.checked_at,
            "reason": self.reason,
            "window_start": self.window_start,
            "window_end": self.window_end,
            "symbols": [
                {
                    "symbol": s.symbol,
                    "last_partition_day": s.last_partition_day,
                    "partitions": s.partitions,
                    "missing_days": s.missing_days,
                }
                for s in self.symbols
            ],
        }

    def render(self) -> str:
        lines = [f"DF-04 freshness: {self.status} ({self.checked_at})"]
        if self.reason:
            lines.append(f"  sababu: {self.reason}")
        if self.window_start:
            lines.append(f"  dirisha: {self.window_start} -> {self.window_end}")
        for symbol in self.symbols:
            mark = "OK " if symbol.ok else "ONYO"
            missing = ", ".join(symbol.missing_days[:10])
            if len(symbol.missing_days) > 10:
                missing += f", ... (+{len(symbol.missing_days) - 10})"
            lines.append(
                f"  [{mark}] {symbol.symbol}: partitions={symbol.partitions} "
                f"mwisho={symbol.last_partition_day or '—'}"
                + (f" · zilizokosekana: {missing}" if missing else "")
            )
        return "\n".join(lines)


def _day_from_key(key: str) -> str | None:
    for part in Path(key).parts:
        if part.startswith("date="):
            return part.split("=", 1)[1]
    return None


def check_freshness(
    cfg: DataConfig,
    now: datetime | None = None,
    calendar: TradingCalendar | None = None,
    require_storage: bool = False,
) -> FreshnessReport:
    """Kagua kama kila siku kamili ya trading ina partition ya broker."""
    now = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    checked_at = now.isoformat(timespec="seconds")
    calendar = calendar or calendar_from_config(cfg)
    grace_hours = float(cfg.get("recorder.freshness_alert.grace_hours", 26))
    enabled = bool(cfg.get("recorder.enabled", True))

    if not enabled:
        return FreshnessReport(
            status=STATUS_SKIPPED,
            checked_at=checked_at,
            reason="recorder.enabled: false kwenye config/data.yaml",
        )

    try:
        manifest_path = cfg.l0_manifest_path
        l0_root = cfg.l0_root
    except Exception as exc:
        if require_storage:
            raise
        return FreshnessReport(
            status=STATUS_SKIPPED, checked_at=checked_at, reason=f"storage haijawekwa: {exc}"
        )

    if not manifest_path.is_file():
        reason = f"manifest ya L0 haipo ({manifest_path})"
        status = STATUS_NOT_STARTED if require_storage else STATUS_SKIPPED
        return FreshnessReport(status=status, checked_at=checked_at, reason=reason)

    manifest = L0Manifest.load(manifest_path)
    broker_entries = manifest.entries_by_provenance(PROVENANCE_BROKER)
    if not broker_entries:
        return FreshnessReport(
            status=STATUS_NOT_STARTED,
            checked_at=checked_at,
            reason=(
                "hakuna partition yenye `provenance: broker`. Spec §2.2: kila mwezi "
                "usiorekodiwa ni data ya broker iliyopotea bure."
            ),
        )

    # Dirisha: kuanzia recorder ilipoanza (au partition ya kwanza) hadi siku ya
    # mwisho ya trading iliyofungwa zaidi ya `grace_hours`.
    state_path = l0_root / STATE_DIRNAME / STATE_FILENAME
    start_day: date | None = None
    if state_path.is_file():
        state = RecorderState.load_or_new(state_path)
        start_day = datetime.fromisoformat(state.started_at).astimezone(timezone.utc).date()

    days_by_symbol: dict[str, list[str]] = {}
    for entry in broker_entries:
        day = _day_from_key(entry.partition) or (entry.first_ts or "")[:10]
        if not entry.symbol or not day:
            continue
        days_by_symbol.setdefault(entry.symbol, []).append(day)

    earliest = min(min(days) for days in days_by_symbol.values())
    window_start = start_day or date.fromisoformat(earliest)
    window_end = (now - timedelta(hours=grace_hours)).date()

    symbols: list[SymbolFreshness] = []
    checked_days = 0
    for symbol in sorted(days_by_symbol):
        recorded = set(days_by_symbol[symbol])
        # Dirisha la symbol linaanza pale data yake inapoanza — hata kama hiyo ni
        # kabla ya `started_at` (mf. backfill au state iliyoanzishwa upya). Vinginevyo
        # pengo lililo ndani ya kipindi kilichorekodiwa lingepita bila kuonekana.
        symbol_start = min(window_start, date.fromisoformat(min(recorded)))
        expected = calendar.full_trading_days(symbol_start, window_end)
        checked_days += len(expected)
        missing = [day.isoformat() for day in expected if day.isoformat() not in recorded]
        symbols.append(
            SymbolFreshness(
                symbol=symbol,
                last_partition_day=max(recorded),
                missing_days=missing,
                partitions=len(recorded),
            )
        )

    status = STATUS_OK if all(s.ok for s in symbols) else STATUS_ALERT
    reason = "" if status == STATUS_OK else "siku za trading bila data mpya (spec §2.2 / DF-04)"
    if checked_days == 0 and status == STATUS_OK:
        # Hakuna SIKU hata moja iliyopimwa (recorder imeanza tu; hakuna siku ya
        # trading iliyofungwa zaidi ya `grace_hours`). Kusema "OK" hapa kungekuwa
        # kupita kwa uwongo — falsafa ile ile ya SKIPPED ya malango (§4.2).
        status = STATUS_NO_CLOSED_DAYS
        reason = (
            f"recorder imeanza {window_start.isoformat()}; hakuna siku ya trading "
            f"iliyofungwa zaidi ya saa {grace_hours} bado — hakuna kilichopimwa."
        )
    return FreshnessReport(
        status=status,
        checked_at=checked_at,
        reason=reason,
        window_start=window_start.isoformat(),
        window_end=window_end.isoformat(),
        symbols=symbols,
    )
